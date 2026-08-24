"""从远程大 zip 里只取需要的条目，不下载整包。

DTU 的 Points.zip 与 SampleSet.zip 各约 7 GB，而 E-zeta 只需要 scan24 的
真值点云与 ObsMask。服务器支持 Range（HTTP 206），因此可以：

  1. 取末尾若干字节，定位中央目录（含 ZIP64 情形）；
  2. Range 取回中央目录，列出全部条目；
  3. 只对匹配的条目 Range 取回其本地头 + 压缩数据，就地解压。

用法：
  python zip_partial.py <url> --list
  python zip_partial.py <url> --get 'stl024|Points/stl/stl024' --out DIR
"""
import argparse
import io
import re
import struct
import sys
import urllib.request
import zlib

UA = {"User-Agent": "Mozilla/5.0 (research)"}


def fetch(url, start=None, end=None, timeout=120):
    """Range 取回 [start, end]（含端点）；start 为负表示取末尾 |start| 字节。"""
    h = dict(UA)
    if start is not None:
        h["Range"] = "bytes=%d" % start if end is None else "bytes=%d-%d" % (start, end)
        if start < 0:
            h["Range"] = "bytes=%d" % start
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout).read()


def total_size(url):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    return int(urllib.request.urlopen(req, timeout=60).headers["Content-Length"])


def find_central_dir(url, size):
    """返回 (cd_offset, cd_size, n_entries)，兼容 ZIP64。"""
    tail_n = min(size, 1 << 16)
    tail = fetch(url, size - tail_n, size - 1)
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        raise RuntimeError("未找到 EOCD")
    n, cd_size, cd_off = struct.unpack("<H", tail[i + 10:i + 12])[0], \
        struct.unpack("<I", tail[i + 12:i + 16])[0], \
        struct.unpack("<I", tail[i + 16:i + 20])[0]

    # ZIP64：字段为 0xFFFFFFFF 时须读 ZIP64 EOCD
    if cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF or n == 0xFFFF:
        j = tail.rfind(b"PK\x06\x07")          # ZIP64 EOCD locator
        if j < 0:
            raise RuntimeError("疑似 ZIP64 但未找到 locator")
        z64_off = struct.unpack("<Q", tail[j + 8:j + 16])[0]
        z64 = fetch(url, z64_off, z64_off + 55)
        if z64[:4] != b"PK\x06\x06":
            raise RuntimeError("ZIP64 EOCD 签名不符")
        n = struct.unpack("<Q", z64[32:40])[0]
        cd_size = struct.unpack("<Q", z64[40:48])[0]
        cd_off = struct.unpack("<Q", z64[48:56])[0]
    return cd_off, cd_size, n


def parse_central(cd):
    """产出 (name, method, comp_size, uncomp_size, local_header_offset)。"""
    out, p = [], 0
    while p + 46 <= len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        method = struct.unpack("<H", cd[p + 10:p + 12])[0]
        csize = struct.unpack("<I", cd[p + 20:p + 24])[0]
        usize = struct.unpack("<I", cd[p + 24:p + 28])[0]
        nlen = struct.unpack("<H", cd[p + 28:p + 30])[0]
        elen = struct.unpack("<H", cd[p + 30:p + 32])[0]
        clen = struct.unpack("<H", cd[p + 32:p + 34])[0]
        lho = struct.unpack("<I", cd[p + 42:p + 46])[0]
        name = cd[p + 46:p + 46 + nlen].decode("utf-8", "replace")
        extra = cd[p + 46 + nlen:p + 46 + nlen + elen]

        # ZIP64 扩展字段：按 0xFFFFFFFF 出现的顺序补齐
        if 0xFFFFFFFF in (csize, usize, lho):
            q = 0
            while q + 4 <= len(extra):
                hid, hsz = struct.unpack("<HH", extra[q:q + 4])
                if hid == 0x0001:
                    vals = extra[q + 4:q + 4 + hsz]
                    k = 0
                    if usize == 0xFFFFFFFF:
                        usize = struct.unpack("<Q", vals[k:k + 8])[0]; k += 8
                    if csize == 0xFFFFFFFF:
                        csize = struct.unpack("<Q", vals[k:k + 8])[0]; k += 8
                    if lho == 0xFFFFFFFF:
                        lho = struct.unpack("<Q", vals[k:k + 8])[0]; k += 8
                    break
                q += 4 + hsz
        out.append((name, method, csize, usize, lho))
        p += 46 + nlen + elen + clen
    return out


def extract(url, entry, out_dir):
    import os
    name, method, csize, usize, lho = entry
    # 本地头长度可变，先取 30 字节读出 name/extra 长度
    lh = fetch(url, lho, lho + 29)
    if lh[:4] != b"PK\x03\x04":
        raise RuntimeError("本地头签名不符: " + name)
    nlen = struct.unpack("<H", lh[26:28])[0]
    elen = struct.unpack("<H", lh[28:30])[0]
    data_off = lho + 30 + nlen + elen
    blob = fetch(url, data_off, data_off + csize - 1)
    if method == 0:
        raw = blob
    elif method == 8:
        raw = zlib.decompress(blob, -15)
    else:
        raise RuntimeError("不支持的压缩方法 %d: %s" % (method, name))
    dst = os.path.join(out_dir, os.path.basename(name))
    os.makedirs(out_dir, exist_ok=True)
    with open(dst, "wb") as f:
        f.write(raw)
    return dst, len(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--grep", default=None, help="只显示匹配的条目名")
    ap.add_argument("--get", default=None, help="取回匹配该正则的条目")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()

    size = total_size(a.url)
    cd_off, cd_size, n = find_central_dir(a.url, size)
    print("包大小 %.2f GB | 中央目录 offset=%d size=%d 条目数=%d"
          % (size / 1e9, cd_off, cd_size, n), flush=True)
    cd = fetch(a.url, cd_off, cd_off + cd_size - 1)
    entries = parse_central(cd)
    print("解析出 %d 条" % len(entries), flush=True)

    if a.list or a.grep:
        pat = re.compile(a.grep) if a.grep else None
        for e in entries:
            if pat and not pat.search(e[0]):
                continue
            print("   %-58s %10.1f MB" % (e[0][:58], e[3] / 1e6))

    if a.get:
        pat = re.compile(a.get)
        hit = [e for e in entries if pat.search(e[0])]
        print("匹配 %d 条，开始取回" % len(hit), flush=True)
        got = 0
        for e in hit:
            dst, nb = extract(a.url, e, a.out)
            got += nb
            print("   -> %s  %.1f MB" % (dst, nb / 1e6), flush=True)
        print("共取回 %.1f MB（整包 %.1f GB）" % (got / 1e6, size / 1e9))


if __name__ == "__main__":
    main()

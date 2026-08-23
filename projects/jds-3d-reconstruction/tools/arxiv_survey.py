"""arXiv 通道：补 CVF 覆盖不到的图形学场馆盲区。

动机：现有语料只来自 CVF open access（ICCV/CVPR/WACV），
而双表示混合与几何正则的工作大量发表于 SIGGRAPH / TOG / TVCG / CGF，
这些不在 CVF 上。多数此类论文会挂 arXiv 的 cs.GR 分类。

流程与 survey.py 相同：按类别与时间窗枚举 → 标题粗筛 → 下载全文 → 探针词正查。
"""
import argparse, json, os, re, time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research survey)"}
API = "http://export.arxiv.org/api/query?"

COARSE = ["gaussian", "splatting", "3dgs", "sdf", "signed distance", "implicit surface",
          "neural field", "radiance", "surface reconstruction", "octree", "level set",
          "mesh", "point cloud", "geometry", "reconstruction"]


def fetch_page(cat, start, n, from_date):
    q = f"cat:{cat}"
    url = API + urllib.parse.urlencode({
        "search_query": q, "start": start, "max_results": n,
        "sortBy": "submittedDate", "sortOrder": "descending"})
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "ignore")


def parse(xml):
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        t = re.search(r"<title>(.*?)</title>", e, re.S)
        i = re.search(r"<id>(.*?)</id>", e)
        d = re.search(r"<published>(.*?)</published>", e)
        s = re.search(r"<summary>(.*?)</summary>", e, re.S)
        if not (t and i):
            continue
        out.append({"title": re.sub(r"\s+", " ", t.group(1)).strip(),
                    "id": i.group(1).strip(),
                    "date": d.group(1)[:10] if d else "",
                    "abstract": re.sub(r"\s+", " ", s.group(1)).strip() if s else ""})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cats", default="cs.GR")
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--per", type=int, default=100)
    ap.add_argument("--since", default="2025-01-01")
    ap.add_argument("--cache", default=os.path.expanduser("~/fastrelight/arxiv_cache"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-download", type=int, default=260)
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)
    from pypdf import PdfReader

    listing = []
    for cat in a.cats.split(","):
        for pg in range(a.pages):
            try:
                items = parse(fetch_page(cat, pg * a.per, a.per, a.since))
            except Exception as e:
                print(f"  [page {pg}] {type(e).__name__}", flush=True)
                break
            if not items:
                break
            listing += items
            oldest = min(x["date"] for x in items if x["date"])
            print(f"  [{cat}] page {pg}: {len(items)} 篇，最早 {oldest}", flush=True)
            if oldest < a.since:
                break
            time.sleep(3.2)   # arXiv 要求礼貌间隔

    listing = [x for x in listing if x["date"] >= a.since]
    seen, uniq = set(), []
    for x in listing:
        if x["id"] in seen:
            continue
        seen.add(x["id"]); uniq.append(x)
    cand = [x for x in uniq if any(k in x["title"].lower() or k in x["abstract"].lower()
                                   for k in COARSE)]
    print(f"\n枚举 {len(uniq)} 篇（{a.since} 起），粗筛通过 {len(cand)} 篇")

    n_new = 0
    for i, x in enumerate(cand[:a.max_download]):
        aid = x["id"].rstrip("/").split("/")[-1]
        key = re.sub(r"[^A-Za-z0-9._-]", "_", aid)
        txt_p = os.path.join(a.cache, key + ".txt")
        if os.path.exists(txt_p):
            continue
        try:
            pdf_url = f"https://arxiv.org/pdf/{aid}"
            pdf_p = os.path.join(a.cache, key + ".pdf")
            req = urllib.request.Request(pdf_url, headers=UA)
            open(pdf_p, "wb").write(urllib.request.urlopen(req, timeout=90).read())
            txt = "\n".join(pp.extract_text() or "" for pp in PdfReader(pdf_p).pages)
            open(txt_p, "w", encoding="utf-8").write(x["title"] + "\n" + txt)
            os.remove(pdf_p)
            n_new += 1
            time.sleep(3.2)
        except Exception as e:
            print(f"  [skip] {x['title'][:52]}: {type(e).__name__}", flush=True)
            continue
        if n_new % 20 == 0:
            print(f"  ...已下载 {n_new}", flush=True)

    json.dump({"listing": uniq, "candidates": cand},
              open(a.out, "w"), indent=2, ensure_ascii=False)
    print(f"\n新下载 {n_new} 篇 -> 缓存 {a.cache}")
    print(f"清单 -> {a.out}")


if __name__ == "__main__":
    main()

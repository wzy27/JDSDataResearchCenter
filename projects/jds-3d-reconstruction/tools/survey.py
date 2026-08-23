"""会议论文全文调研工具。

设计动机：2026-08-23 漏掉 Hierarchy UGP (ICCV 2025)。该文标题为
"Hierarchy Unified Gaussian Primitive for Large-Scale Dynamic Scene Reconstruction"，
不含 pedestrian / human / SMPL 任何一词，其行人区域指标埋在 Table 2 中。
纯主题关键词检索无法发现它——必须做全文正查。

两阶段：
  1. 从 CVF open access 抓取整届论文标题与 PDF 链接，按「宽松」的领域词粗筛；
  2. 只下载粗筛通过者的 PDF，抽取全文，按「精确」的探针词正查并计分。

粗筛词应宽松（宁可多下几十篇），探针词应精确（决定是否真的相关）。
"""
import argparse, json, os, re, sys, time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research survey; contact: local)"}

# 阶段 1：标题粗筛——领域词，宁滥勿缺
COARSE = [
    "gaussian", "splatting", "3dgs", "4dgs", "nerf", "radiance",
    "driving", "urban", "street", "scene reconstruction", "dynamic scene",
    "novel view", "autonomous", "human", "pedestrian", "avatar", "smpl",
]
# 阶段 2：全文探针——决定相关性
PROBES = {
    "pedestrian": 3, "pedestrians": 3, "SMPL": 3, "human region": 5,
    "human-region": 5, "non-rigid": 2, "articulated": 2,
    "OmniRe": 4, "Street Gaussians": 2, "DeformableNodes": 5,
    "Waymo": 1, "nuScenes": 1,
}
# 强信号：报告了行人/人体分区指标
STRONG = [r"pedestrian region", r"human region", r"PSNR\s*\*", r"per-class.{0,40}PSNR",
          r"metrics for the pedestrian", r"human.{0,15}PSNR", r"PSNR.{0,15}human"]


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def list_venue(venue):
    """返回 [(title, pdf_url)]。"""
    html = fetch(f"https://openaccess.thecvf.com/{venue}?day=all", 120).decode("utf-8", "ignore")
    out, seen = [], set()
    for m in re.finditer(r'<dt class="ptitle"><br><a href="([^"]+)">(.*?)</a>', html, re.S):
        href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        pdf = "https://openaccess.thecvf.com" + href.replace("/html/", "/papers/").replace(".html", ".pdf")
        if pdf not in seen:
            seen.add(pdf); out.append((title, pdf))
    return out


def coarse_pass(title):
    t = title.lower()
    return any(k in t for k in COARSE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", default="ICCV2025,CVPR2025")
    ap.add_argument("--cache", default=os.path.expanduser("~/fastrelight/survey_cache"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-download", type=int, default=400)
    ap.add_argument("--sleep", type=float, default=0.4)
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)
    from pypdf import PdfReader

    all_hits, stats = [], {}
    for venue in a.venues.split(","):
        papers = list_venue(venue)
        cand = [(t, u) for t, u in papers if coarse_pass(t)]
        stats[venue] = {"total": len(papers), "coarse_pass": len(cand)}
        print(f"[{venue}] 全量 {len(papers)} 篇，粗筛通过 {len(cand)} 篇", flush=True)
        for i, (title, url) in enumerate(cand[:a.max_download]):
            key = re.sub(r"[^A-Za-z0-9]+", "_", url.split("/")[-1])[:120]
            txt_p = os.path.join(a.cache, key + ".txt")
            if not os.path.exists(txt_p):
                try:
                    pdf_p = os.path.join(a.cache, key + ".pdf")
                    open(pdf_p, "wb").write(fetch(url, 90))
                    txt = "\n".join(p.extract_text() or "" for p in PdfReader(pdf_p).pages)
                    open(txt_p, "w", encoding="utf-8").write(txt)
                    os.remove(pdf_p)
                    time.sleep(a.sleep)
                except Exception as e:
                    print(f"  [skip] {title[:60]}: {type(e).__name__}", flush=True)
                    continue
            txt = open(txt_p, encoding="utf-8", errors="ignore").read()
            flat = re.sub(r"\s+", " ", txt)
            score, found = 0, {}
            for k, w in PROBES.items():
                n = len(re.findall(re.escape(k), flat, re.I))
                if n:
                    score += w * min(n, 6); found[k] = n
            strong = [p for p in STRONG if re.search(p, flat, re.I)]
            if strong:
                score += 30
            if score >= 20:
                all_hits.append({"venue": venue, "title": title, "url": url,
                                 "score": score, "probes": found,
                                 "strong_signals": strong})
            if (i + 1) % 25 == 0:
                print(f"  ...{i+1}/{len(cand)} 已处理，命中 {len(all_hits)}", flush=True)

    all_hits.sort(key=lambda h: -h["score"])
    json.dump({"stats": stats, "probes": PROBES, "hits": all_hits},
              open(a.out, "w"), indent=2, ensure_ascii=False)
    print(f"\n命中 {len(all_hits)} 篇 -> {a.out}")
    for h in all_hits[:25]:
        s = " [强信号]" if h["strong_signals"] else ""
        print(f"  {h['score']:4d}  {h['venue']}  {h['title'][:72]}{s}")


if __name__ == "__main__":
    main()

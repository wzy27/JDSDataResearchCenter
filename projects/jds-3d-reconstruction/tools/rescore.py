"""对已缓存的会议论文全文，按新方向的探针词重新计分。

survey.py 下载并缓存了全文；本脚本只做打分，因此可对同一批缓存反复施加不同的
探针集，不重复下载。缓存随 survey_all.sh 持续增长，可随时重跑。

对应调研方法论的通道 A（会议全量枚举 + 全文正查），针对候选方向：
  甲 = 行人资产库 + 检索式重建
  乙 = 逐 actor 的重建不确定性估计
"""
import glob, json, os, re, sys

CACHE = os.path.expanduser("~/fastrelight/survey_cache")

SETS = {
    "甲 行人资产库/检索式重建": {
        "probes": {
            "asset bank": 6, "asset library": 6, "memory-augmented": 6, "memory bank": 5,
            "retrieval": 4, "retrieve": 2, "asset repository": 6,
            "object insertion": 4, "actor insertion": 5, "insert pedestrian": 8,
            "pedestrian asset": 10, "human asset": 8, "avatar bank": 8,
            "generative prior": 3, "feed-forward human": 6, "template bank": 5,
            "MADrive": 8,
        },
        "strong": [r"pedestrian asset", r"human asset (bank|library)", r"avatar (bank|library)",
                   r"asset (bank|library).{0,60}(pedestrian|human)",
                   r"(pedestrian|human).{0,60}asset (bank|library)"],
        "context": ["pedestrian", "human", "driving", "urban"],
    },
    "乙 重建不确定性/可靠性": {
        "probes": {
            "uncertainty": 4, "uncertainties": 3, "confidence": 2, "calibrat": 4,
            "reliability": 4, "aleatoric": 6, "epistemic": 6,
            "predictive uncertainty": 7, "uncertainty-aware": 6,
            "per-object quality": 8, "reconstruction quality prediction": 9,
            "observability": 6, "reconstructability": 9, "reconstructibility": 9,
            "quality estimation": 5,
        },
        "strong": [r"uncertainty.{0,60}gaussian splatting", r"gaussian splatting.{0,60}uncertainty",
                   r"per-(object|actor|instance).{0,40}uncertainty",
                   r"reconstruct(ability|ibility)"],
        "context": ["gaussian", "splatting", "reconstruction", "driving", "urban", "nerf"],
    },
}


def title_of(path, txt):
    for line in txt.split("\n")[:40]:
        s = line.strip()
        if 18 < len(s) < 160 and not s.lower().startswith(("abstract", "arxiv", "this ")):
            return s
    return os.path.basename(path)[:90]


def main():
    files = sorted(glob.glob(os.path.join(CACHE, "*.txt")))
    print(f"缓存全文 {len(files)} 篇\n")
    out = {}
    for name, cfg in SETS.items():
        hits = []
        for p in files:
            txt = open(p, encoding="utf-8", errors="ignore").read()
            flat = re.sub(r"\s+", " ", txt)
            low = flat.lower()
            if not any(c in low for c in cfg["context"]):
                continue
            score, found = 0, {}
            for k, w in cfg["probes"].items():
                n = len(re.findall(re.escape(k), flat, re.I))
                if n:
                    score += w * min(n, 5)
                    found[k] = n
            strong = [s for s in cfg["strong"] if re.search(s, flat, re.I)]
            if strong:
                score += 40
            if score >= 25:
                hits.append({"file": os.path.basename(p), "title": title_of(p, txt),
                             "score": score, "probes": found, "strong": strong})
        hits.sort(key=lambda h: -h["score"])
        out[name] = hits
        print("=" * 74)
        print(f"### {name} — 命中 {len(hits)} 篇，强信号 {sum(1 for h in hits if h['strong'])} 篇")
        for h in hits[:12]:
            mark = " ★强信号" if h["strong"] else ""
            top = dict(sorted(h["probes"].items(), key=lambda x: -x[1])[:4])
            print(f"  [{h['score']:4d}] {h['title'][:66]}{mark}")
            print(f"         {top}")
            if h["strong"]:
                print(f"         信号: {h['strong']}")
    json.dump(out, open(os.path.expanduser("~/fastrelight/analysis/rescore_directions.json"), "w"),
              indent=2, ensure_ascii=False)
    print("\n-> ~/fastrelight/analysis/rescore_directions.json")


if __name__ == "__main__":
    main()

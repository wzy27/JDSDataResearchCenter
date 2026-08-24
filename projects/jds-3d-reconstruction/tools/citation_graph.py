"""Channel B：Semantic Scholar 引文图。

前四路调研（CVF 全文、arXiv cs.GR 全文、关键词、探针词）都是「按内容找」，
共同盲区是：**引用了同一批奠基工作、但用词完全不同的论文**。
互导优化这个题目尤其吃这个亏——同一件事可以叫 mutual guidance / joint optimization /
alternating refinement / co-training，全文正查很难穷尽。

引文图绕开用词：凡是引用了 GS-Octree、MGSR 或 Neural-Singular-Hessian 的工作，
不管怎么措辞，都会被枚举到。这是对前四路的正交补充。

判定沿用已有词表，但**只在引用者的标题+摘要上打分**（拿不到全文），
因此本路的作用是「点名候选」，不是「定论」——命中的要回到全文通道复核。
"""
import json, os, re, sys, time, urllib.parse, urllib.request

API = "https://api.semanticscholar.org/graph/v1"
UA = {"User-Agent": "Mozilla/5.0 (research survey)"}
OUT = os.path.expanduser("~/fastrelight/analysis")

SEEDS = {
    "GS-Octree":  "arXiv:2406.18199",
    "MGSR":       None,          # 用标题检索
    "NSH":        "arXiv:2309.01793",
    "2DGS":       "arXiv:2403.17888",
    "SuGaR":      "arXiv:2311.12775",
}
SEED_TITLES = {
    "MGSR": "MGSR: Multi-Gaussian Splatting Reconstruction",
}

VOCAB = {
    "互导/相互监督": [r"mutual", r"reciprocal", r"bidirectional", r"each other",
                      r"co-?regulariz", r"cross-?supervis", r"co-?train"],
    "交替优化":      [r"alternat", r"iterative refin", r"block coordinate",
                      r"joint(ly)? optimiz", r"two-?stage"],
    "双表示":        [r"hybrid representation", r"dual", r"explicit and implicit",
                      r"sdf.{0,20}gaussian", r"gaussian.{0,20}sdf", r"mesh and gaussian"],
    "收敛/稳定性":   [r"converg", r"stabilit", r"error (propagat|accumulat)",
                      r"diverg", r"feedback loop", r"fixed point", r"drift"],
    "失败/退化":     [r"fail", r"degrad", r"degenerat", r"collapse",
                      r"local minim", r"artifact"],
}


def get(url):
    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=90))
        except Exception as e:
            code = getattr(e, "code", None)
            if code in (429, 504) or code is None:
                time.sleep(6 * (attempt + 1)); continue
            raise
    return None


def resolve(name):
    pid = SEEDS.get(name)
    if pid:
        return pid
    q = urllib.parse.quote(SEED_TITLES[name])
    r = get(f"{API}/paper/search?query={q}&limit=1&fields=paperId,title")
    if r and r.get("data"):
        print(f"  {name} 解析为: {r[data][0][title][:60]}")
        return r["data"][0]["paperId"]
    return None


def citations(pid, cap=1000):
    out, off = [], 0
    while off < cap:
        r = get(f"{API}/paper/{pid}/citations?offset={off}&limit=100"
                f"&fields=title,abstract,year,venue,externalIds")
        if not r or not r.get("data"):
            break
        out += [c["citingPaper"] for c in r["data"] if c.get("citingPaper")]
        if len(r["data"]) < 100:
            break
        off += 100
        time.sleep(1.2)
    return out


def score(p):
    t = ((p.get("title") or "") + " " + (p.get("abstract") or "")).lower()
    return {k: sum(len(re.findall(x, t)) for x in v) for k, v in VOCAB.items()}


all_papers, by_seed = {}, {}
for name in SEEDS:
    pid = resolve(name)
    if not pid:
        print(f"  [跳过] {name} 未解析"); continue
    cs = citations(pid)
    by_seed[name] = len(cs)
    print(f"{name:12s} 被引 {len(cs)}", flush=True)
    for p in cs:
        k = p.get("paperId") or p.get("title")
        if not k: continue
        if k not in all_papers:
            all_papers[k] = {**p, "_seeds": []}
        all_papers[k]["_seeds"].append(name)
    time.sleep(1.5)

rows = []
for p in all_papers.values():
    s = score(p)
    rows.append({"title": p.get("title"), "year": p.get("year"), "venue": p.get("venue"),
                 "seeds": p["_seeds"], "scores": s,
                 "arxiv": (p.get("externalIds") or {}).get("ArXiv")})

print(f"\n去重后共 {len(rows)} 篇引用者")
print("按种子: " + ", ".join(f"{k}={v}" for k, v in by_seed.items()))

# 关键交叉：既谈互导/交替，又谈收敛/稳定/失败
cross = [r for r in rows
         if (r["scores"]["互导/相互监督"] + r["scores"]["交替优化"]) >= 2
         and (r["scores"]["收敛/稳定性"] + r["scores"]["失败/退化"]) >= 2]
cross.sort(key=lambda r: -(sum(r["scores"].values())))
print(f"\n关键交叉候选 {len(cross)} 篇（标题+摘要口径，需回全文复核）")
for r in cross[:25]:
    s = r["scores"]
    print("  %-4s %-62s 互导%2d 交替%2d 收敛%2d 失败%2d  %s"
          % (r["year"] or "-", (r["title"] or "")[:62],
             s["互导/相互监督"], s["交替优化"], s["收敛/稳定性"], s["失败/退化"],
             ",".join(r["seeds"])))

multi = [r for r in rows if len(r["seeds"]) >= 2]
print(f"\n同时引用 >=2 个种子的 {len(multi)} 篇")
for r in sorted(multi, key=lambda r: -len(r["seeds"]))[:15]:
    print("  %-4s %-64s %s" % (r["year"] or "-", (r["title"] or "")[:64], ",".join(r["seeds"])))

json.dump({"by_seed": by_seed, "rows": rows, "cross": cross},
          open(f"{OUT}/citation_graph.json", "w"), indent=2, ensure_ascii=False)
print(f"\n-> {OUT}/citation_graph.json")

"""引文图的第二层：把点名的双表示工作批量拉全文，用五类探针正查。

第一层（citation_graph.py）只看标题+摘要，只能点名。上一轮我手挑了 8 篇，
其中 6 篇 Semantic Scholar 检索没命中——那 6 篇因此**尚未被排除**，
这是个必须补上的漏洞。这一层改为：从 1674 篇引用者里按分数自动选，
凡有 arXiv id 的就拉全文，不依赖检索式是否写得巧。

判定口径与 position paper 一致：找的不是「有没有互导」，
而是「有没有分析它何时成立/何时失败」。
"""
import json, os, re, time, urllib.request
from pypdf import PdfReader

UA = {"User-Agent": "Mozilla/5.0 (research survey)"}
A = os.path.expanduser("~/fastrelight/analysis")
CACHE = os.path.expanduser("~/fastrelight/deepcheck_cache")
os.makedirs(CACHE, exist_ok=True)

PROBES = {
    "收敛性论述": [r"converge[sd]? (to|when|if)",
                   r"convergence (analysis|guarantee|proof|condition|rate)",
                   r"provabl", r"contraction mapping", r"fixed[- ]point",
                   r"monotonic(ally)? (decreas|improv)"],
    "失败条件":   [r"fail[s]? (when|if)", r"break[s]? down", r"does not converge",
                   r"under what (condition|circumstance)",
                   r"when .{0,30}(guid|supervis).{0,20}(fail|hurt)",
                   r"(harm|hurt|degrade)[sd]? .{0,25}(the other|each other|both branch)"],
    "误差传播":   [r"error (propagat|accumulat|amplif)", r"self-?reinforc",
                   r"feedback loop", r"compounding error"],
    "消融互导环": [r"ablat.{0,45}(mutual|bidirection|guid|loop|feedback)",
                   r"(without|w/o) .{0,25}(mutual|guidance|feedback)",
                   r"one-?way (guidance|supervision)", r"unidirectional"],
    "初始化依赖": [r"initializ.{0,25}(sensitiv|critical|crucial|depend)",
                   r"sensitive to .{0,20}initial", r"poor initializ"],
}

d = json.load(open(f"{A}/citation_graph.json", encoding="utf-8"))
rows = d["rows"]

# 选取：有 arXiv id，且（双表示>=1 或 互导>=1 或 交替>=2）
def pick(r):
    s = r["scores"]
    return r.get("arxiv") and (s["双表示"] >= 1 or s["互导/相互监督"] >= 1
                               or s["交替优化"] >= 2)

cand = [r for r in rows if pick(r)]
cand.sort(key=lambda r: -(r["scores"]["双表示"] * 2 + r["scores"]["互导/相互监督"] * 3
                          + r["scores"]["交替优化"]))
CAP = 200
print(f"1674 篇引用者中，命中筛选的 {len(cand)} 篇；本轮取前 {min(CAP,len(cand))} 篇拉全文")
print(f"（**未取的 {max(0,len(cand)-CAP)} 篇尚未排除**）\n", flush=True)

hit_rows, n_ok, n_fail = [], 0, 0
for i, r in enumerate(cand[:CAP]):
    aid = r["arxiv"]
    key = re.sub(r"[^A-Za-z0-9._-]", "_", aid)
    tp = os.path.join(CACHE, key + ".txt")
    if not os.path.exists(tp):
        try:
            pp = os.path.join(CACHE, key + ".pdf")
            open(pp, "wb").write(urllib.request.urlopen(
                urllib.request.Request(f"https://arxiv.org/pdf/{aid}", headers=UA),
                timeout=120).read())
            t = "\n".join(x.extract_text() or "" for x in PdfReader(pp).pages)
            open(tp, "w", encoding="utf-8").write(t)
            os.remove(pp)
            time.sleep(3)
        except Exception as e:
            n_fail += 1
            print(f"  [取不到 {type(e).__name__}] {(r['title'] or '')[:58]}", flush=True)
            continue
    txt = open(tp, encoding="utf-8").read()
    n_ok += 1
    flat = re.sub(r"\s+", " ", txt)
    cnt, ev = {}, {}
    for name, pats in PROBES.items():
        hs = []
        for pat in pats:
            for m in re.finditer(pat, flat, re.I):
                hs.append(flat[max(0, m.start() - 100):m.end() + 120])
        cnt[name] = len(hs)
        ev[name] = hs[:2]
    hit_rows.append({"title": r["title"], "year": r["year"], "arxiv": aid,
                     "seeds": r["seeds"], "probe": cnt, "ev": ev})
    if (i + 1) % 10 == 0:
        print(f"  ...已处理 {i+1}/{min(CAP,len(cand))}", flush=True)

print(f"\n全文取得 {n_ok} 篇，失败 {n_fail} 篇\n")
print("=" * 92)
print("【核心检验】有没有人分析互导的成立条件")
print("=" * 92)
print("%-58s %5s %5s %5s %5s %5s" % ("论文", "收敛", "失败", "误差", "消融", "初始"))
print("-" * 92)
key_hits = []
for h in sorted(hit_rows, key=lambda x: -(x["probe"]["收敛性论述"] * 3
                                          + x["probe"]["失败条件"] * 2
                                          + x["probe"]["误差传播"] * 2
                                          + x["probe"]["消融互导环"])):
    p = h["probe"]
    if sum(p.values()) == 0:
        continue
    print("%-58s %5d %5d %5d %5d %5d" % ((h["title"] or "")[:58],
          p["收敛性论述"], p["失败条件"], p["误差传播"], p["消融互导环"], p["初始化依赖"]))
    if p["收敛性论述"] >= 2 or p["失败条件"] >= 2 or p["误差传播"] >= 2:
        key_hits.append(h)

n_zero = sum(1 for h in hit_rows if sum(h["probe"].values()) == 0)
print(f"\n五类探针全为 0 的：{n_zero} / {n_ok} 篇")
print(f"收敛性论述 >0 的：{sum(1 for h in hit_rows if h['probe']['收敛性论述']>0)} 篇")

print("\n" + "=" * 92)
print("【需人工判读的证据片段】")
for h in key_hits[:8]:
    print(f"\n### {(h['title'] or '')[:74]}  ({h['year']}, arXiv:{h['arxiv']})")
    for name in ("收敛性论述", "失败条件", "误差传播"):
        for s in h["ev"][name]:
            print(f"  [{name}] ...{s.strip()[:200]}...")

json.dump(hit_rows, open(f"{A}/tier2_fulltext.json", "w"), indent=2, ensure_ascii=False)
print(f"\n-> {A}/tier2_fulltext.json")

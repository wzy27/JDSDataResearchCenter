"""对引文图点名的候选做全文复核。

引文图只看标题+摘要，只能「点名」。position paper 里那句
「双表示互导优化的收敛性/稳定性无人研究」是基于 968 篇全文得出的，
现在引文图冒出 GS-ROR2（Bidirectional-guided）、GSDF、GSurf 等直接相关工作，
必须回到全文确认它们是否已经做了条件/收敛分析——这是对自己论点的证伪检查。
"""
import json, os, re, time, urllib.parse, urllib.request
from pypdf import PdfReader

UA = {"User-Agent": "Mozilla/5.0 (research survey)"}
API = "https://api.semanticscholar.org/graph/v1"
CACHE = os.path.expanduser("~/fastrelight/deepcheck_cache")
os.makedirs(CACHE, exist_ok=True)

TARGETS = [
    "GS-ROR2 Bidirectional-guided 3DGS and SDF for Reflective Object Relighting",
    "GSDF 3DGS Meets SDF for Improved Neural Rendering and Reconstruction",
    "GSurf Learning signed distance fields from splatting opaque Gaussians",
    "MGSR 2D/3D Mutual-boosted Gaussian Splatting for High-fidelity Surface Reconstruction",
    "A survey on surface reconstruction based on 3D Gaussian splatting",
    "SplatlessDF Continuous Distance Field Mapping with Non-Splatting",
    "Gaussian Splatting with Discretized SDF for Relightable Assets",
    "Gaussian-Voxel Duet A Dual-Scaffolding Hybrid Representation",
]

# 关键：不只找「有没有互导」，而是找「有没有分析它何时成立/何时失败」
PROBES = {
    "收敛性论述": [r"converge[sd]? (to|when|if)",
                   r"convergence (analysis|guarantee|proof|condition|rate)",
                   r"provabl", r"contraction", r"fixed[- ]point",
                   r"monotonic(ally)? (decreas|improv)"],
    "失败条件":   [r"fail[s]? (when|if)", r"break[s]? down", r"does not (converge|hold)",
                   r"under what (condition|circumstance)",
                   r"when .{0,30}(guid|supervis).{0,20}(fail|hurt)",
                   r"(harm|hurt|degrade)[sd]? .{0,25}(the other|each other|both)"],
    "误差传播":   [r"error (propagat|accumulat|amplif)", r"self-?reinforc",
                   r"feedback loop", r"drift", r"compounding error"],
    "消融互导环": [r"ablat.{0,40}(mutual|bidirection|guid|loop|feedback)",
                   r"(without|w/o) .{0,25}(mutual|guidance|feedback)",
                   r"one-?way (guidance|supervision)", r"unidirectional"],
    "初始化依赖": [r"initializ.{0,25}(sensitiv|critical|crucial|depend)",
                   r"sensitive to .{0,20}initial", r"poor initializ"],
}


def get(url):
    for i in range(6):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=90))
        except Exception as e:
            if getattr(e, "code", None) in (429, 504, None):
                time.sleep(6 * (i + 1))
                continue
            raise
    return None


for q in TARGETS:
    r = get(f"{API}/paper/search?query={urllib.parse.quote(q)}&limit=1"
            f"&fields=title,year,venue,abstract,externalIds,citationCount")
    if not r or not r.get("data"):
        print(f"[未找到] {q[:50]}", flush=True)
        continue
    p = r["data"][0]
    aid = (p.get("externalIds") or {}).get("ArXiv")
    print("\n" + "=" * 78)
    print(p["title"][:76])
    print("  {} | {} | 被引 {} | arXiv:{}".format(
        p.get("year"), p.get("venue") or "-", p.get("citationCount"), aid), flush=True)

    txt = ""
    if aid:
        key = re.sub(r"[^A-Za-z0-9._-]", "_", aid)
        tp = os.path.join(CACHE, key + ".txt")
        if os.path.exists(tp):
            txt = open(tp, encoding="utf-8").read()
        else:
            try:
                pp = os.path.join(CACHE, key + ".pdf")
                open(pp, "wb").write(urllib.request.urlopen(
                    urllib.request.Request(f"https://arxiv.org/pdf/{aid}", headers=UA),
                    timeout=120).read())
                txt = "\n".join(x.extract_text() or "" for x in PdfReader(pp).pages)
                open(tp, "w", encoding="utf-8").write(txt)
                os.remove(pp)
                time.sleep(3)
            except Exception as e:
                print("  [全文获取失败 {}]".format(type(e).__name__))
    if not txt:
        txt = p.get("abstract") or ""
        print("  [仅摘要口径，结论强度低]")

    flat = re.sub(r"\s+", " ", txt)
    for name, pats in PROBES.items():
        hits = []
        for pat in pats:
            for m in re.finditer(pat, flat, re.I):
                hits.append(flat[max(0, m.start() - 90):m.end() + 90])
        if hits:
            print("  ** {} ({})".format(name, len(hits)))
            seen = set()
            for h in hits[:3]:
                k = h[:40]
                if k in seen:
                    continue
                seen.add(k)
                print("       ..." + h.strip()[:170] + "...")
        else:
            print("     {}: 0".format(name))

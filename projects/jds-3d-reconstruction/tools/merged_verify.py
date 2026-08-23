"""合并 CVF 与 arXiv cs.GR 两路语料，重验核心论点。

CVF 通道覆盖 ICCV/CVPR/WACV；arXiv cs.GR 通道补 SIGGRAPH/TOG/TVCG 盲区
——双表示混合与几何正则的工作常发表于图形学场馆，而后者不在 CVF open access 上。

论点：双表示互导优化的收敛性/稳定性无人研究。
若在补上图形学场馆后仍然成立，则该论点的证据强度显著提高；
若图形学场馆有相关工作，则论点需修正或放弃。
"""
import glob, json, os, re
from collections import defaultdict

CVF = os.path.expanduser("~/fastrelight/survey_cache")
ARX = os.path.expanduser("~/fastrelight/arxiv_cache")
A = os.path.expanduser("~/fastrelight/analysis")
GEO = ["gaussian splatting", "3dgs", "implicit surface", "sdf", "signed distance",
       "neural radiance", "surface reconstruction"]

VOCAB = {
    "互导/相互监督": [r"mutual.{0,15}(supervis|boost|guid|refin|constrain)", r"reciprocal",
                      r"bidirectional.{0,20}(guid|supervis)", r"each other.{0,25}(guid|refin|improv)",
                      r"co-?regulariz", r"cross-?supervis"],
    "交替优化": [r"alternating optimization", r"alternate.{0,20}(optimiz|updat|train)",
                 r"iterative.{0,20}(refin|alternat)", r"block coordinate descent",
                 r"two-?stage.{0,15}alternat"],
    "双表示混合": [r"hybrid representation", r"dual.{0,15}(branch|representation)",
                   r"two representations", r"explicit.{0,15}and.{0,15}implicit",
                   r"sdf.{0,20}gaussian", r"gaussian.{0,20}sdf", r"mesh.{0,15}and.{0,15}gaussian"],
    "收敛性/稳定性分析": [r"convergence analysis", r"converge.{0,25}(guarantee|condition|proof)",
                          r"stability.{0,20}(analysis|condition)", r"error propagation",
                          r"error accumulat", r"divergen.{0,20}(optimiz|train)",
                          r"self-?reinforc.{0,20}error", r"feedback loop",
                          r"fixed point", r"contraction mapping"],
    "初始化敏感/坏极小值": [r"local minim", r"initializ.{0,20}sensitiv", r"poor initializ",
                            r"bad initializ", r"undesirable minim", r"sensitive to initial"],
}
STRONG = [
    r"mutual.{0,30}(supervis|guid).{0,60}(converg|stabilit|fail)",
    r"alternating optimization.{0,60}(converg|guarantee|analysis)",
    r"error.{0,20}(propagat|accumulat).{0,60}(mutual|alternat|two representation)",
    r"when.{0,30}mutual.{0,25}(guid|supervis).{0,25}fail",
    r"convergence.{0,40}(alternating|mutual|two-?branch)",
]


def title_of(raw):
    return next((l.strip() for l in raw.split("\n")[:30] if 18 < len(l.strip()) < 140), "")[:70]


def scan(files, tag):
    sub, strong, both = defaultdict(list), [], []
    n = 0
    for p in files:
        raw = open(p, encoding="utf-8", errors="ignore").read()
        flat = re.sub(r"\s+", " ", raw)
        low = flat.lower()
        if not any(c in low for c in GEO):
            continue
        n += 1
        head, t = low[:1800], title_of(raw)
        hit = {}
        for sname, kws in VOCAB.items():
            c = sum(len(re.findall(k, low)) for k in kws)
            hit[sname] = c
            if any(re.search(k, head) for k in kws) and c >= 6:
                sub[sname].append((tag, t))
        if (hit["互导/相互监督"] + hit["交替优化"] >= 6) and hit["收敛性/稳定性分析"] >= 4:
            both.append((tag, t, hit["互导/相互监督"] + hit["交替优化"], hit["收敛性/稳定性分析"]))
        if any(re.search(s, flat, re.I) for s in STRONG):
            strong.append((tag, t))
    return n, sub, strong, both


nc, sc, gc, bc = scan(sorted(glob.glob(f"{CVF}/*.txt")), "CVF")
na, sa, ga, ba = scan(sorted(glob.glob(f"{ARX}/*.txt")), "arXiv")
print(f"CVF 语料 {nc} 篇（限几何上下文） | arXiv cs.GR 语料 {na} 篇\n")
print("%-22s%10s%10s%10s" % ("子表述", "CVF", "arXiv", "合计"))
print("-" * 56)
for k in VOCAB:
    print("%-22s%10d%10d%10d" % (k, len(sc[k]), len(sa[k]), len(sc[k]) + len(sa[k])))

print(f"\n强信号: CVF {len(set(gc))} + arXiv {len(set(ga))} = {len(set(gc) | set(ga))}")
for tag, t in sorted(set(gc) | set(ga)):
    print(f"  ★ [{tag}] {t}")

print(f"\n关键交叉（互导/交替 且 收敛/稳定性）: CVF {len(bc)} + arXiv {len(ba)} = {len(bc) + len(ba)}")
for tag, t, a_, b_ in sorted(bc + ba, key=lambda x: -(x[2] + x[3]))[:14]:
    print("   [%s] %-58s 互导%3d 收敛%3d" % (tag, t[:58], a_, b_))

print("\n=== arXiv 通道新增的双表示混合论文（CVF 未覆盖）===")
cvf_titles = {t for _, t in sc["双表示混合"]}
for tag, t in sa["双表示混合"]:
    if t not in cvf_titles:
        print("   ·", t)

json.dump({"cvf_n": nc, "arxiv_n": na,
           "counts": {k: {"cvf": len(sc[k]), "arxiv": len(sa[k])} for k in VOCAB},
           "strong": [list(x) for x in sorted(set(gc) | set(ga))],
           "cross": [list(x) for x in bc + ba]},
          open(f"{A}/merged_verify.json", "w"), indent=2, ensure_ascii=False)
print(f"\n-> {A}/merged_verify.json")

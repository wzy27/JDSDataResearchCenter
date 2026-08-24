"""精读 tier2 点名的 5 篇。探针只能点名，判读必须人来做。

对每篇只问一个问题：**它是在「分析互导/交替优化何时成立」，
还是只是「用了这个模式并声称它好」？** 后者不构成对我们论点的威胁。
"""
import json, os, re

A = os.path.expanduser("~/fastrelight/analysis")
CACHE = os.path.expanduser("~/fastrelight/deepcheck_cache")
rows = json.load(open(f"{A}/tier2_fulltext.json", encoding="utf-8"))

FOCUS = ["GEAR", "Radiometrically Consistent", "COREA", "GSO-SLAM",
         "Evolving High-Quality Rendering"]

# 找「论证」而非「使用」：围绕这些词看上下文
ARGUE = [r"we (analyz|prove|show that|derive|characteriz)",
         r"(theorem|lemma|proposition|proof)\b",
         r"(necessary|sufficient) condition",
         r"why .{0,40}(alternat|mutual|coupl|feedback)",
         r"(alternat|mutual|coupl|feedback).{0,60}(because|due to|reason)",
         r"error accumulat", r"self-?correcting", r"local minim",
         r"diverge", r"unstable", r"collapse"]

for r in rows:
    t = r["title"] or ""
    if not any(f.lower() in t.lower() for f in FOCUS):
        continue
    tp = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9._-]", "_", r["arxiv"]) + ".txt")
    if not os.path.exists(tp):
        print(f"[无全文] {t[:60]}")
        continue
    flat = re.sub(r"\s+", " ", open(tp, encoding="utf-8").read())
    print("\n" + "=" * 94)
    print(f"{t[:88]}")
    print(f"  {r['year']} | arXiv:{r['arxiv']} | 引用种子 {r['seeds']} | 探针 {r['probe']}")

    # 摘要
    m = re.search(r"(?i)abstract(.{200,1500}?)(?:1\.? ?Introduction|Index Terms|CCS)", flat)
    if m:
        print("  【摘要】" + m.group(1).strip()[:520] + "...")

    seen = set()
    n = 0
    for pat in ARGUE:
        for mm in re.finditer(pat, flat, re.I):
            s = flat[max(0, mm.start() - 200):mm.end() + 320].strip()
            k = s[:50]
            if k in seen:
                continue
            seen.add(k)
            n += 1
            if n > 7:
                break
            print(f"  · ...{s[:330]}...")
        if n > 7:
            break

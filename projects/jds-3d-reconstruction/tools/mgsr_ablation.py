"""精读 MGSR 的消融，确定它已经回答了什么、没回答什么。

这决定我们的位置：若 MGSR 已证明「双向 BP 优于单向」，那么
「互导有没有用」就不是空位；我们必须问的是「在什么条件下成立」。
"""
import os, re

CACHE = os.path.expanduser("~/fastrelight/deepcheck_cache")
txt = open(os.path.join(CACHE, "2503.05182.txt"), encoding="utf-8").read()
flat = re.sub(r"[ \t]+", " ", txt)

# 消融章节
m = re.search(r"(Ablation|ablation)", flat)
print("=" * 78)
print("【消融相关段落】")
for kw in ["unidirectional", "bidirectional BP", "without mutual", "Mutual-boosted Iterations"]:
    for mm in re.finditer(kw, flat, re.I):
        seg = flat[max(0, mm.start() - 500):mm.end() + 900]
        seg = re.sub(r"\n+", " ", seg)
        print(f"\n--- 命中「{kw}」 ---")
        print(seg[:1400])
        break

print()
print("=" * 78)
print("【表格中与消融有关的行】")
for line in txt.split("\n"):
    s = line.strip()
    if re.search(r"^(Model )?[A-N]\b", s) and re.search(r"\d\.\d", s) and len(s) < 160:
        print("   ", s)

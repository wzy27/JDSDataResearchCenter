"""汇总多届调研结果，输出精简报告（只列高分与强信号命中）。"""
import glob, json, os
rows, stats = [], {}
for p in sorted(glob.glob(os.path.expanduser("~/fastrelight/analysis/survey_*.json"))):
    d = json.load(open(p))
    stats.update(d.get("stats", {}))
    rows += d.get("hits", [])
rows.sort(key=lambda h: -h["score"])

print("=" * 78)
for v, s in sorted(stats.items()):
    print(f"  {v:10s} 全量 {s['total']:5d}  粗筛 {s['coarse_pass']:4d}")
print(f"  命中(score>=20): {len(rows)}   强信号: {sum(1 for r in rows if r['strong_signals'])}")
print("=" * 78)

print("\n### 强信号命中（报告了行人/人体分区指标）")
for r in [x for x in rows if x["strong_signals"]]:
    print(f"  [{r['score']:4d}] {r['venue']} {r['title'][:70]}")
    print(f"         信号={r['strong_signals']}  探针={ {k:v for k,v in r['probes'].items() if k in ('pedestrian','SMPL','OmniRe','human region')} }")

print("\n### 高分命中（前 30，无强信号）")
for r in [x for x in rows if not x["strong_signals"]][:30]:
    p = {k: v for k, v in r["probes"].items() if k in ("pedestrian", "SMPL", "OmniRe", "non-rigid")}
    print(f"  [{r['score']:4d}] {r['venue']} {r['title'][:66]}  {p}")

# 验收：必须命中 Hierarchy UGP
hit = [r for r in rows if "Hierarchy UGP" in r["title"] or "Unified Gaussian Primitive" in r["title"]]
print("\n" + "=" * 78)
print("验收（须命中 Hierarchy UGP）: %s" % (
    f"通过 — score={hit[0]['score']} strong={bool(hit[0]['strong_signals'])}" if hit else "未通过"))
json.dump({"stats": stats, "n_hits": len(rows),
           "acceptance_hierarchy_ugp": bool(hit),
           "hits": rows},
          open(os.path.expanduser("~/fastrelight/analysis/survey_all.json"), "w"),
          indent=2, ensure_ascii=False)

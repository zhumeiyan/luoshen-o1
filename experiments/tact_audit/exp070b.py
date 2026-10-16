# -*- coding: utf-8 -*-
"""逐条独立效应：每次只改写 1 条，其余 28 条原文。"""
import json, os, subprocess, sys, shutil, re, time
from paraphrase import P

base = json.load(open("calibration_cases.json", encoding="utf-8"))
cases = base["cases"]
IDS = [c["id"] for c in cases]

def run_with(tm, tries=3):
    for attempt in range(tries):
        d = json.loads(json.dumps(base))
        for c in d["cases"]:
            if c["id"] in tm:
                c["phenomenon"] = tm[c["id"]]
        p = "_tmp_one"
        os.makedirs(os.path.join(p, "data"), exist_ok=True)
        shutil.copy("engine/tact_run.py", p)
        shutil.copy("engine/data/coordinate_data.json", os.path.join(p, "data"))
        with open(os.path.join(p, "data", "calibration_cases.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        r = subprocess.run([sys.executable, "tact_run.py", "--calibration"],
                           cwd=p, capture_output=True, text=True)
        rows = {}
        for line in r.stdout.splitlines():
            m = re.match(r'^(CAL-\d+)\s+(\S+)\s+(\S+)\s+(OK|~)\s*$', line.strip())
            if m:
                rows[m.group(1)] = m.group(4)
        if len(rows) == len(IDS):
            return rows
        time.sleep(0.2)
    raise RuntimeError(f"解析不完整: {len(rows)}/{len(IDS)} id={tm}")

orig = run_with({})
print("原文基准三轴完全匹配:", sum(1 for v in orig.values() if v == "OK"), "/", len(orig))

rows_out, flips = [], 0
for c in cases:
    cid = c["id"]
    one = run_with({cid: P[cid]})
    before, after = orig[cid], one[cid]
    ge = (c["golden"] == {"L": [], "M": [], "P": []})
    if before == "OK" and after != "OK":
        flips += 1
    rows_out.append({"id": cid, "golden_empty": ge, "before": before,
                     "after": after, "flipped": (before == "OK" and after != "OK")})

print("\n逐条独立效应（每次只改写这一条，其余 28 条原文）")
print(f"{'ID':<9}{'golden空':<10}{'原文':<7}{'改写后':<8}{'翻转'}")
for r in rows_out:
    print(f"{r['id']:<9}{str(r['golden_empty']):<10}{r['before']:<7}{r['after']:<8}{'★' if r['flipped'] else ''}")

ok_b = sum(1 for r in rows_out if r["before"] == "OK")
ok_a = sum(1 for r in rows_out if r["after"] == "OK")
ne_b = sum(1 for r in rows_out if not r["golden_empty"] and r["before"] == "OK")
ne_a = sum(1 for r in rows_out if not r["golden_empty"] and r["after"] == "OK")
print(f"\n原本 OK              : {ok_b}/29")
print(f"仅改该条后仍 OK      : {ok_a}/29   -> 翻转 {flips} 条")
print(f"剔除 golden 全空 2 条: {ne_b}/27 = {ne_b/27:.4f}  ->  {ne_a}/27 = {ne_a/27:.4f}")
json.dump({"orig": orig, "rows": rows_out}, open("result_070b.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

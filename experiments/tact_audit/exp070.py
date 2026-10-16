# -*- coding: utf-8 -*-
import json, os, subprocess, sys, shutil, re
from paraphrase import P

SRC = "engine"
def build(tag, transform):
    d = json.load(open("calibration_cases.json", encoding="utf-8"))
    for c in d["cases"]:
        c["phenomenon"] = transform(c["id"], c["phenomenon"])
    p = f"run_{tag}"
    os.makedirs(os.path.join(p, "data"), exist_ok=True)
    shutil.copy(os.path.join(SRC, "tact_run.py"), p)
    shutil.copy(os.path.join(SRC, "data", "coordinate_data.json"), os.path.join(p, "data"))
    json.dump(d, open(os.path.join(p, "data", "calibration_cases.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return p

def run(p):
    out = subprocess.run([sys.executable, "tact_run.py", "--calibration"],
                         cwd=p, capture_output=True, text=True).stdout
    res = {}
    m = re.search(r"三轴完全匹配:\s*(\d+)/(\d+)", out)
    res["exact"] = (int(m.group(1)), int(m.group(2))) if m else None
    for ax in ("L", "M", "P"):
        m = re.search(rf"^{ax}\s+([\d.]+)% \((\d+)/(\d+)\)", out, re.M)
        if m:
            res[ax] = (float(m.group(1)), int(m.group(2)), int(m.group(3)))
    return res, out

# 三种条件
conds = {
 "原文":        lambda i, t: t,
 "同义改写":     lambda i, t: P[i],
 "标点扰动(无关对照)": lambda i, t: t.replace("，", "，·").replace("。", "。·"),
}

results = {}
for tag, tr in conds.items():
    p = build(tag.replace("(", "_").replace(")", ""), tr)
    res, out = run(p)
    results[tag] = res
    print("=" * 68)
    print(f"【{tag}】")
    if res.get("exact"):
        a, b = res["exact"]
        print(f"  三轴完全匹配 : {a}/{b} = {a/b:.4f}")
    for ax in ("L", "M", "P"):
        if ax in res:
            pct, num, den = res[ax]
            print(f"  {ax} 轴召回    : {pct:5.1f}%  ({num}/{den})")

json.dump({k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v.items()}
           for k, v in results.items()},
          open("result_070.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

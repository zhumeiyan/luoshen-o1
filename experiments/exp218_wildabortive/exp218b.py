#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""218b 不育度扫描：野败必须是"完全不育"吗？"""
import numpy as np, json, os, importlib.util

spec = importlib.util.spec_from_file_location("e218", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "exp218.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

LEAKS = [0.0, 0.05, 0.10, 0.25, 0.50, 0.75, 1.00]
res = []
for lk in LEAKS:
    m.LEAK = lk
    peaks, amins, recs = [], [], []
    for sd in range(m.SEEDS):
        th, aa = m.run("wild_leaky", sd)
        mt = m.metrics(th, aa)
        peaks.append(mt["peak_first"]); amins.append(mt["a_min"]); recs.append(mt["recover"][0])
    r = {"leak": lk,
         "peak": round(float(np.mean(peaks)), 4),
         "a_min": round(float(np.mean(amins)), 4),
         "recover": round(float(np.mean(recs)), 1)}
    res.append(r)
    print(f"leak={lk:<5} 首波峰 {r['peak']:.3f} | a_min {r['a_min']:.3f} | 恢复 {r['recover']} 代")

json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "result218b.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\n已写 result218b.json")

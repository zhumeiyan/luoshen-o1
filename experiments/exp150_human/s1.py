#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 独白 v2：修 v1 bug（初始化即挤出A -> 三臂全0饱和）
工作记忆 CAP=3 正好装下三步；真实时钟抖动决定每轮挤入几个干扰项 -> 产生真实变异
pre=事先写下计划可读回恢复 / post=只写历史 / off=无外部记忆"""
import os, json, math, random, time
from collections import deque
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_DIR = "/data/workspace/luoshen-o1/experiments"
TARGET = ["A", "B", "C"]
CAP = 3

def ci_paired(d):
    d = np.asarray(d, float); n = len(d)
    m = float(d.mean()); se = float(d.std(ddof=1))/math.sqrt(n) if n > 1 else float("nan")
    return m, m-1.96*se, m+1.96*se

def real_jitter(rng):
    """真实时钟抖动 -> 决定本轮挤入几个干扰项（真实噪声源）"""
    t0 = time.perf_counter()
    s = 0.0
    for _ in range(20000): s += (_ ** 0.5)
    return (time.perf_counter() - t0)

def run_arm(arm, seed, T=48):
    fpath = os.path.join(HERE, f"s1_{arm}_{seed}.log")
    f = open(fpath, "w+")   # v3: "w" 不可读, read() 抛 UnsupportedOperation 被 except 吞掉 -> pre 臂读回从未生效
    plan = deque(TARGET, maxlen=CAP)
    done = []
    ndist = 0; jitters = []
    for t in range(T):
        if arm == "pre":
            if t == 0:
                f.seek(0); f.truncate(); json.dump({"plan": TARGET}, f); f.flush()
            f.seek(0)
            try: ext = json.loads(f.read() or "{}")
            except Exception: ext = {}
            for step in ext.get("plan", []):
                if step not in done and step not in plan:
                    plan.append(step)               # 从"事先说过的计划"补回被挤出的步骤
        elif arm == "post":
            if t == 0:
                f.seek(0); f.truncate(); json.dump({"hist": []}, f); f.flush()
            f.seek(0)
            try: ext = json.loads(f.read() or "{}")
            except Exception: ext = {}
        # 真实感知：每 4 tick 真 listdir，挤入数量由真实时钟抖动决定
        if t % 4 == 0:
            try: items = os.listdir(REAL_DIR)
            except Exception: items = ["x"]
            j = real_jitter(None)
            jitters.append(j)
            k = int((j * 1000) % 3)                 # 0~2 个，真机噪声
            for i in range(k):
                nm = items[(t + i) % len(items)] if items else "x"
                plan.append("D:" + nm)
                ndist += 1
        nxt = TARGET[len(done)]
        if nxt in plan:
            plan.remove(nxt); done.append(nxt)
            if arm == "post":
                f.seek(0); f.truncate(); json.dump({"hist": done}, f); f.flush()
        if len(done) == len(TARGET): break
    f.close(); os.remove(fpath)
    return 1.0 if done == TARGET else 0.0, ndist, (float(np.mean(jitters)) if jitters else 0.0)

def main(seeds=12):
    out = {}; sl = list(range(2000, 2000+seeds))
    for arm in ["pre", "post", "off"]:
        vals = []; nd = []
        for s in sl:
            v, n, _ = run_arm(arm, s); vals.append(v); nd.append(n)
        out[arm] = {"rate": float(np.mean(vals)), "vals": vals, "mean_dist": float(np.mean(nd))}
    d1 = [out["pre"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    d2 = [out["post"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    m1, lo1, hi1 = ci_paired(d1); m2, lo2, hi2 = ci_paired(d2)
    out["H1a_pre_minus_off"] = {"mean": m1, "ci":[lo1,hi1], "pass": bool(lo1 > 0)}
    out["H1b_post_minus_off"] = {"mean": m2, "ci":[lo2,hi2], "post_not_better": bool(not(lo2>0))}
    return out

if __name__ == "__main__":
    r = main(12); print(json.dumps(r, ensure_ascii=False, indent=1))
    json.dump(r, open("result_s1.json","w"), ensure_ascii=False, indent=1)

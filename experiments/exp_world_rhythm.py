#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人类社会节律 能不能救坍塌？—— 对比机械轮换 / 随机 / 恒定多维
==============================================================
用户原话：「场景轮换就按照人类社会的，天气啊那些东西那么按」

★ 上一轮（★13）已实测的基线（k_seek=1.0 坍塌态）：
    不推        3/24    份额0 0.9943
    单维恒定    0/24    ← 火上浇油
    恒定多维   18/24    份额0 0.9622
    机械轮换   24/24    份额0 0.2436  ← 真拉出来了
    随机       24/24    份额0 0.8136  ← 只加噪声，没破锁死

★ 本轮问题：真实社会节律（日夜+人群+周+季节+天气惯性）
    能不能达到机械轮换的效果？会不会更好？

★ 关键变量：时间尺度（一拍 = 多少真实分钟）
    太快 → 所有模态都来不及变 = 近似恒定
    太慢 → 只有最慢的模态在动 = 近似恒定
    匹配 → 多频率错相 = 真轮换
    所以扫这个尺度，本身就是发现。

provenance：光/人群/周/季节 = REAL（真时钟真经纬度）
            天气 = SIMULATED（wttr.in 与 open-meteo 均 403，拿不到真的）
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5
from core.world_rhythm import WorldRhythm

N = 8; STEPS = 400; KSEEK = 1.0; AMP = 2.0

def ent(a):
    a = np.asarray(a, float) + 1e-12
    p = a / a.sum()
    return float(-(p * np.log(p)).sum() / np.log(len(p)))

def run(seed, mode, mpt=60.0, steps=STEPS):
    L = Life5(N=N, seed=seed, k_seek=KSEEK)
    L.input_val = 0.0
    W = WorldRhythm(N=N, minutes_per_tick=mpt, seed=seed * 13 + 5)
    rng = np.random.default_rng(seed * 7 + 1)
    es, sh = [], []
    for t in range(steps):
        if not L.alive: break
        if mode == "社会节律":
            nv = W.step(AMP)
        elif mode == "机械轮换":
            nv = np.zeros(N); nv[t % N] = AMP
        elif mode == "随机":
            nv = rng.random(N) * AMP
        elif mode == "恒定多维":
            nv = np.full(N, AMP)
        elif mode == "不推":
            nv = None
        else:
            nv = None
        L.net_push = nv
        r = L.step()
        if r:
            es.append(ent(r["avec"]))
            a = np.asarray(r["avec"], float)
            sh.append(a[0] / a.sum() if a.sum() > 1e-12 else 0.0)
    tail = es[len(es)//2:]
    return dict(alive=L.alive,
                ent=float(np.mean(tail)) if tail else 0.0,
                share0=float(np.mean(sh[-50:])) if sh else 0.0)

def sweep(mode, n=24, **kw):
    rs = [run(s, mode, **kw) for s in range(n)]
    return dict(alive=sum(1 for r in rs if r["alive"]), n=n,
                ent=float(np.mean([r["ent"] for r in rs])),
                share0=float(np.mean([r["share0"] for r in rs])))

if __name__ == "__main__":
    print("=" * 86)
    print(" 人类社会节律 vs 机械轮换 / 随机 / 恒定  (k_seek=1.0 坍塌态, 24 seeds)")
    print("=" * 86)

    print(f"\n[1] 一拍=1小时（能看到日夜，看不到周/季节）")
    print(f"\n{'刺激源':<22}{'存活':>9}{'后段熵':>10}{'份额0':>10}")
    print("-" * 86)
    res = {}
    for lbl in ["不推", "单维恒定", "恒定多维", "机械轮换", "随机", "社会节律"]:
        m = "恒定多维" if lbl == "单维恒定" else lbl
        if lbl == "单维恒定":
            rs = [run(s, "恒定多维") for s in range(24)]
            # 单维：临时改
            import copy
            def run1(seed):
                L = Life5(N=N, seed=seed, k_seek=KSEEK); L.input_val = 0.0
                es, sh = [], []
                for t in range(STEPS):
                    if not L.alive: break
                    nv = np.zeros(N); nv[0] = AMP
                    L.net_push = nv
                    r = L.step()
                    if r:
                        es.append(ent(r["avec"])); a = np.asarray(r["avec"], float)
                        sh.append(a[0]/a.sum() if a.sum()>1e-12 else 0.0)
                tail = es[len(es)//2:]
                return dict(alive=L.alive, ent=float(np.mean(tail)) if tail else 0.0,
                            share0=float(np.mean(sh[-50:])) if sh else 0.0)
            rs = [run1(s) for s in range(24)]
            res[lbl] = dict(alive=sum(1 for r in rs if r["alive"]), n=24,
                            ent=float(np.mean([r["ent"] for r in rs])),
                            share0=float(np.mean([r["share0"] for r in rs])))
        else:
            res[lbl] = sweep(lbl)
        r = res[lbl]
        print(f"{lbl:<22}{r['alive']:>5}/{r['n']}{r['ent']:>10.4f}{r['share0']:>10.4f}")

    print("\n" + "=" * 86)
    print(" [2] 时间尺度扫描（社会节律）—— 一拍代表多久")
    print("=" * 86)
    print(f"\n{'一拍=':>10}{'存活':>9}{'后段熵':>10}{'份额0':>10}   {'能看到什么'}")
    print("-" * 86)
    scales = [(1.0, "1分钟"), (15.0, "15分钟"), (60.0, "1小时"),
              (240.0, "4小时"), (720.0, "12小时"), (1440.0, "1天"), (10080.0, "1周")]
    scan = []
    for mpt, lbl in scales:
        r = sweep("社会节律", mpt=mpt)
        scan.append((lbl, mpt, r))
        see = ("日夜" if mpt >= 60 else "几乎静止") + \
              ("+周" if mpt >= 1440 else "") + ("+季节" if mpt >= 10080 else "")
        print(f"{lbl:>10}{r['alive']:>5}/{r['n']}{r['ent']:>10.4f}{r['share0']:>10.4f}   {see}")

    # ---------------- 判据 ----------------
    print("\n" + "=" * 86)
    print(" 判据（要求真有变化，非永真）")
    print("=" * 86)
    ok = {}
    ok["① 社会节律显著优于不推（存活+10以上）"] = bool(
        res["社会节律"]["alive"] - res["不推"]["alive"] >= 10)
    ok["② 社会节律能破锁死（份额0 < 0.5）"] = bool(res["社会节律"]["share0"] < 0.5)
    ok["③ 社会节律不差于机械轮换（存活）"] = bool(
        res["社会节律"]["alive"] >= res["机械轮换"]["alive"] - 2)
    best = max(scan, key=lambda x: x[2]["alive"])
    ok["④ 存在最优时间尺度（不是所有尺度都一样）"] = bool(
        max(x[2]["alive"] for x in scan) - min(x[2]["alive"] for x in scan) >= 5)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n  ★ 最优尺度：一拍={best[0]}  存活 {best[2]['alive']}/24  "
          f"份额0 {best[2]['share0']:.4f}")
    print(f"  ★ 最差尺度：一拍={min(scan,key=lambda x:x[2]['alive'])[0]}  "
          f"存活 {min(x[2]['alive'] for x in scan)}/24")

    json.dump({"res": res,
               "scan": {lbl: r for lbl, m, r in scan},
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "world_rhythm.json"), "w"),
              ensure_ascii=False, indent=1)

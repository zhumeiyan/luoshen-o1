#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
社会节律 v2：补上饭点 + 集中映射
==================================
★ 上一版实测出的病因（不是我猜的）：
    社会节律(弥散)  存活 0/24，但份额0 = 0.0978（锁死破得最彻底）
    → 注意力被带走了，却没去觅食 = 【饿死】
    实测通道7(摄食)平均收到 0.7397，机械轮换只有 0.2500
    → 收得更多却饿死：因为弥散摊薄了分配，绝对量不够

★ 这一版两处修正（都对应真实人类社会）：
    ① 加 meal 饭点（早7.5/午12/晚18.5 三个强脉冲，REAL 真时钟）
       真实社会节律里本来就有饭点，是我上一版漏了
    ② focused 集中映射
       真实注意力是【集中在少数事】上，不是同时弥散到所有事
       每个模态打一个主通道，主通道随季节缓慢漂移

★ 四个版本对比：
    弥散(无饭点)  上一版  0/24
    弥散+饭点
    集中(无饭点)
    集中+饭点     ← 预期最好
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
    fc = L.forage_ch
    use_meal = ('饭点' in mode)
    W = WorldRhythm(N=N, minutes_per_tick=mpt, seed=seed * 13 + 5,
                     forage_ch=fc, use_meal=use_meal)
    rng = np.random.default_rng(seed * 7 + 1)
    es, sh = [], []
    for t in range(steps):
        if not L.alive: break
        if mode.startswith("社会节律-弥散"):
            nv = W.step(AMP, focused=False)
        elif mode.startswith("社会节律-集中"):
            nv = W.step(AMP, focused=True)
        elif mode == "机械轮换":
            nv = np.zeros(N); nv[t % N] = AMP
        elif mode == "随机":
            nv = rng.random(N) * AMP
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
    return dict(alive=L.alive, ent=float(np.mean(tail)) if tail else 0.0,
                share0=float(np.mean(sh[-50:])) if sh else 0.0)

def sweep(mode, n=24, **kw):
    rs = [run(s, mode, **kw) for s in range(n)]
    return dict(alive=sum(1 for r in rs if r["alive"]), n=n,
                ent=float(np.mean([r["ent"] for r in rs])),
                share0=float(np.mean([r["share0"] for r in rs])))

if __name__ == "__main__":
    print("=" * 88)
    print(" 社会节律 v2：饭点 + 集中映射  (k_seek=1.0 坍塌态, 24 seeds, 一拍=1小时)")
    print("=" * 88)
    print(f"\n{'刺激源':<26}{'存活':>9}{'后段熵':>10}{'份额0':>10}")
    print("-" * 88)
    res = {}
    for lbl in ["不推", "随机", "机械轮换",
                "社会节律-弥散", "社会节律-弥散+饭点",
                "社会节律-集中", "社会节律-集中+饭点"]:
        res[lbl] = sweep(lbl)
        r = res[lbl]
        print(f"{lbl:<26}{r['alive']:>5}/{r['n']}{r['ent']:>10.4f}{r['share0']:>10.4f}")

    print("\n" + "=" * 88)
    print(" 分解：饭点贡献多少？集中贡献多少？")
    print("=" * 88)
    d_meal_diff = res["社会节律-弥散+饭点"]["alive"] - res["社会节律-弥散"]["alive"]
    d_meal_foc = res["社会节律-集中+饭点"]["alive"] - res["社会节律-集中"]["alive"]
    d_foc_nomeal = res["社会节律-集中"]["alive"] - res["社会节律-弥散"]["alive"]
    d_foc_meal = res["社会节律-集中+饭点"]["alive"] - res["社会节律-弥散+饭点"]["alive"]
    print(f"\n  弥散 +饭点: {d_meal_diff:+d} 存活")
    print(f"  集中 +饭点: {d_meal_foc:+d} 存活")
    print(f"  +集中(无饭点): {d_foc_nomeal:+d}")
    print(f"  +集中(有饭点): {d_foc_meal:+d}")

    print("\n" + "=" * 88)
    print(" 判据")
    print("=" * 88)
    best = res["社会节律-集中+饭点"]
    ok = {}
    ok["① 集中+饭点 显著优于不推（+10以上）"] = bool(best["alive"] - res["不推"]["alive"] >= 10)
    ok["② 能破锁死（份额0 < 0.5）"] = bool(best["share0"] < 0.5)
    ok["③ 不差于机械轮换"] = bool(best["alive"] >= res["机械轮换"]["alive"] - 2)
    ok["④ 饭点确实有用（至少一档 +3 以上）"] = bool(max(d_meal_diff, d_meal_foc) >= 3)
    ok["⑤ 集中确实有用（至少一档 +3 以上）"] = bool(max(d_foc_nomeal, d_foc_meal) >= 3)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n  ★ 目标：既活下来（存活高）又破锁死（份额0低）")
    print(f"    机械轮换        存活 {res['机械轮换']['alive']}/24  份额0 {res['机械轮换']['share0']:.4f}")
    print(f"    集中+饭点       存活 {best['alive']}/24  份额0 {best['share0']:.4f}")

    json.dump({"res": res,
               "delta": dict(meal_diff=d_meal_diff, meal_foc=d_meal_foc,
                             foc_nomeal=d_foc_nomeal, foc_meal=d_foc_meal),
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "world_rhythm2.json"), "w"),
              ensure_ascii=False, indent=1)

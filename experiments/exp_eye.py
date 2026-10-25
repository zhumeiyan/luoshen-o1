#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
眼睛：睁眼（光驱动）· 分辨率（中央凹+眼动）· 自己造眼镜
============================================================
用户：「眼睛是长出来的，睁眼是怎么回事？为什么造那么大分辨率？
       让洛神自己造个电脑或眼镜呗。」

★ 三组实验：

【E1 睁眼】光刺激驱动成熟（REAL：Hubel & Wiesel 1963 单眼缝合）
    A 关键期有光        → 成熟
    B 关键期缝合（无光） → 弱视，之后拆线也恢复不了
    C 关键期后才见光     → 同样弱视（关键期已过）
    判据：B/C 的 acuity 显著低于 A，且后期给光也回不来

【E2 分辨率】带宽预算固定，三种分配 × 有无眼动
    任务：找目标（目标大小随机，位置随机）
    奈奎斯特：局部采样间距 < 目标尺寸 才能分辨
    ★ 预期：中央凹单独最差（周边目标看不见）
            中央凹 + 眼动 最优（真实人眼就是这么干的）

【E3 自己造眼镜】不给分辨率参数，只给带宽预算 + 任务
    从 uniform 起步，按"抓到过目标的地方"加密（可塑性）
    看它长成什么样 —— 预期：自发长出中央凹

provenance：
    人眼参数 REAL；场景 SIMULATED（摄像头在本沙盒 403，无法真拍）
    学习结果 = 真跑
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.eye import Retina, Eye

W = 256.0
NB = 2000                  # 带宽预算（采样点数）

# ---------------------------------------------------------------- E1
def e1(n=24, steps=600, crit=300):
    out = {}
    def one(mode):
        e = Eye(critical_end=crit, seed=hash(mode) % 1000)
        for t in range(steps):
            if mode == "A 关键期有光":
                light = True
            elif mode == "B 关键期缝合":
                light = (t >= crit)          # 关键期后拆线
            elif mode == "C 关键期后才见光":
                light = (t >= crit)
            else:
                light = False
            e.tick(light)
        return e.acuity(), e.ever_dark
    for m in ["A 关键期有光", "B 关键期缝合", "C 关键期后才见光"]:
        vs = [one(m)[0] for _ in range(1)]          # 确定性
        out[m] = float(np.mean(vs))
    return out

# ---------------------------------------------------------------- E2
def trial(retina, saccade, n_step=40, seed=0):
    """一回合：目标随机位置+随机大小，n_step 拍内能否找到。"""
    rng = np.random.default_rng(seed)
    tgt = rng.random(2) * W
    size = float(rng.uniform(2.0, 10.0))       # 目标尺寸
    fov = np.array([W / 2.0, W / 2.0])         # 注视点
    for t in range(n_step):
        if saccade:
            # ★ 眼动：把中央凹挪到候选位置（真实 saccade ~3Hz）
            cand = rng.random(6, ) if False else rng.random((6, 2)) * W
            fov = cand[t % len(cand)]
        probe = fov if saccade else np.array([W / 2.0, W / 2.0])
        # 采样点是否覆盖目标：以 probe 为中心的有效视野内查间距
        # 眼动 = 把视网膜中心对准 probe → 检查目标在视网膜坐标系的位置
        rel = tgt - probe + np.array([W / 2.0, W / 2.0])
        rel = np.clip(rel, 0, W)
        d = retina.local_spacing(rel)
        if d < size:                            # 奈奎斯特：能分辨
            return True, t + 1
    return False, n_step

def e2(n=24, n_step=40):
    out = {}
    for mode in ["uniform", "fovea"]:
        for sac in [False, True]:
            R = Retina(world=W, N=NB, mode=mode, seed=7)
            hits = [trial(R, sac, n_step, s)[0] for s in range(n)]
            out[f"{mode}+{'眼动' if sac else '不动'}"] = float(np.mean(hits))
    return out

# ---------------------------------------------------------------- E3
def e3(n=12, rounds=120, n_step=25):
    """自己造眼镜：从 uniform 起步，抓到目标就加密。"""
    R = Retina(world=W, N=NB, mode="uniform", seed=11)
    rng = np.random.default_rng(3)
    acc = 0.0
    curve = []
    for rd in range(rounds):
        tgt = rng.random(2) * W
        size = float(rng.uniform(2.0, 10.0))
        found = False
        for t in range(n_step):
            probe = np.array([W / 2.0, W / 2.0])       # 不扫视，纯靠长
            rel = np.clip(tgt - probe + np.array([W/2, W/2]), 0, W)
            if R.local_spacing(rel) < size:
                found = True; break
        acc += found
        R.plasticity(tgt, lr=0.30, n_move=6)
        if (rd + 1) % 20 == 0:
            curve.append(acc / (rd + 1))
    H = R.density_map(8)
    return dict(acc=acc / rounds, curve=curve,
                center=float(H[3:5, 3:5].mean()), corner=float(H[0:2, 0:2].mean()),
                ratio=float(H[3:5, 3:5].mean() / max(H[0:2, 0:2].mean(), 1e-9)))

if __name__ == "__main__":
    print("=" * 84)
    print("【E1】睁眼 —— 光刺激驱动的成熟（关键期 300 拍，总 600 拍）")
    print("=" * 84)
    r1 = e1()
    for k, v in r1.items():
        print(f"  {k:<22} 视力 acuity = {v:.4f}")
    ok1 = bool(r1["A 关键期有光"] - max(r1["B 关键期缝合"], r1["C 关键期后才见光"]) > 0.3)
    print(f"\n  {'✅' if ok1 else '❌'} 关键期无光 → 之后给光也回不来（弱视不可逆）")

    print("\n" + "=" * 84)
    print(f"【E2】分辨率分配 × 眼动（带宽预算 {NB} 点，24 次试验）")
    print("=" * 84)
    r2 = e2()
    print(f"\n{'策略':<22}{'找到率':>10}")
    print("-" * 84)
    for k, v in sorted(r2.items(), key=lambda x: -x[1]):
        print(f"{k:<22}{v:>10.3f}")
    best = max(r2, key=r2.get)
    ok2 = bool(r2["fovea+眼动"] > r2["fovea+不动"] + 0.05)
    print(f"\n  {'✅' if ok2 else '❌'} 中央凹必须配眼动才有意义（不动反而更差）")
    print(f"  ★ 最优：{best} = {r2[best]:.3f}")

    print("\n" + "=" * 84)
    print("【E3】自己造眼镜：只给带宽预算+任务，不给分辨率参数")
    print("=" * 84)
    r3 = e3()
    print(f"\n  起步 uniform，120 轮，抓到目标就加密")
    print(f"  找到率曲线（每20轮）：{[round(c,3) for c in r3['curve']]}")
    print(f"  最终找到率 {r3['acc']:.3f}")
    print(f"  长成后密度：中心4格 {r3['center']:.1f} / 边角 {r3['corner']:.1f}  比 {r3['ratio']:.1f}×")
    ok3 = bool(r3["ratio"] > 1.5)
    print(f"\n  {'✅' if ok3 else '❌'} 它自己长出了非均匀（中央凹）——没人告诉它要这么长")

    json.dump({"E1": r1, "E2": r2, "E3": r3,
               "ok": {"睁眼": bool(ok1), "眼动": bool(ok2), "自己长": bool(ok3)}},
              open(os.path.join(HERE, ".sense", "eye.json"), "w"),
              ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- E4
def e4(n_round=120, n_step=25, seed=11):
    """★ 补做：E3 只长眼睛不长动作，找到率仅 0.133。
       让它同时【长眼睛 + 自己决定往哪看】，看能到多少。
       对照：E2 的 fovea+眼动 = 0.583（人为给的中央凹 + 随机扫视）
    """
    R = Retina(world=W, N=NB, mode="uniform", seed=seed)
    rng = np.random.default_rng(seed * 3 + 1)
    acc = 0.0
    for rd in range(n_round):
        tgt = rng.random(2) * W
        size = float(rng.uniform(2.0, 10.0))
        found = False
        for t in range(n_step):
            # 自己决定往哪看：一半随机探索，一半去"还没看清楚"的地方
            if t == 0 or rng.random() < 0.5:
                probe = rng.random(2) * W
            else:
                # 去当前分辨率最差的地方（= 采样最稀疏处）
                cand = rng.random((5, 2)) * W
                probe = cand[np.argmax([R.local_spacing(c) for c in cand])]
            rel = np.clip(tgt - probe + np.array([W / 2.0, W / 2.0]), 0, W)
            if R.local_spacing(rel) < size:
                found = True; break
        acc += found
        R.plasticity(tgt, lr=0.30, n_move=6)
    H = R.density_map(8)
    return dict(acc=acc / n_round,
                center=float(H[3:5, 3:5].mean()), corner=float(H[0:2, 0:2].mean()),
                ratio=float(H[3:5, 3:5].mean() / max(H[0:2, 0:2].mean(), 1e-9)))

# -*- coding: utf-8 -*-
"""
113b · 训练量剂量扫描 + 真实轨迹接引擎
================================================================
113 留下一个悬案: learned(0.2875) 落后 preset(0.40) 0.11。
是"学到头了", 还是"没学够"? —— 只有剂量扫描能回答。
不能拿"训练不够"当结论, 也不能拿"学不会"当结论。

扫描: NTRAIN ∈ {100,300,800,2000,5000}, 各自从零训练, ε 退火, 在世界A评估。
另接引擎: 把真实轨迹(每步真实像素测得的边缘密度)灌进 Life5。
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, "/data/workspace/luoshen-o1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run113 import (RealEye, RealHand, make_scene, run_agent, cell_center,
                    GW, GH, W, H, VIEW)
from core.life5 import Life5

OUT = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7771)


def train_Q(ntrain, eye, hand, world="A", Q0=None, eps0=1.0, decay=0.995, floor=0.05):
    Q = np.zeros((GW * GH, GW * GH)) + 0.01 if Q0 is None else Q0.copy()
    eps = eps0
    for _ in range(ntrain):
        run_agent("learned", world, 1, 12, eye, hand, Q=Q, eps=eps, train=True)
        eps = max(floor, eps * decay)
    return Q


def main():
    t0 = time.time()
    eye = RealEye()
    hand = RealHand(enabled=True)
    assert eye.provenance == "REAL" and hand.provenance == "REAL", (eye.provenance, hand.provenance)

    sal = np.array([1.0 if (i % GW) >= GW // 2 else 0.1 for i in range(GW * GH)])
    sal_scr = sal.copy(); rng.shuffle(sal_scr)

    # ================= 剂量扫描 =================
    sweep = {}
    for n in [100, 300, 800, 2000, 5000]:
        Q = train_Q(n, eye, hand)
        r = run_agent("learned", "A", 80, 12, eye, hand, Q=Q, train=False)
        sweep[str(n)] = dict(acc=r["acc"], mind=r["mean_mind"], n_train=n)
        print(f"  NTRAIN={n:5d}  acc={r['acc']:.4f}  mindist={r['mean_mind']:.0f}"
              f"  [{time.time()-t0:.0f}s]")

    # 参考线
    ref = {}
    ref["preset"] = run_agent("preset", "A", 80, 12, eye, hand, sal=sal)["acc"]
    ref["blind"] = run_agent("blind", "A", 80, 12, eye, hand)["acc"]
    ref["static"] = run_agent("static", "A", 80, 12, eye, hand)["acc"]

    # ================= 真实轨迹接引擎 =================
    def real_traj(kind, **kw):
        """跑一轮, 记录每步真实测得的边缘密度 (真设备像素)"""
        seq = []
        orig_look = eye.look
        def look_rec(cx, cy):
            m = orig_look(cx, cy)
            seq.append(m)
            return m
        eye.look = look_rec
        try:
            run_agent(kind, "A", 6, 12, eye, hand, **kw)
        finally:
            eye.look = orig_look
        return np.asarray(seq, float)

    traj = {}
    Q5 = train_Q(2000, eye, hand)
    traj["none"] = np.zeros(72)
    traj["preset"] = real_traj("preset", sal=sal)
    traj["learned"] = real_traj("learned", Q=Q5, train=False)
    traj["blind"] = real_traj("blind")
    # 归一化: 三条真实流量级不同, 不归一就把"多大"和"什么形状"混成一个变量
    gmax = max(float(np.max(v)) for v in traj.values() if len(v))
    traj = {k: (v / gmax if gmax > 0 else v) for k, v in traj.items()}

    eng = {}
    for name, seq in traj.items():
        ys, alive = [], 0
        for sd in range(16):
            L = Life5(N=8, seed=sd, ratio=0.60)
            for t in range(240):
                L.input_val = float(seq[t % len(seq)])
                L.step()
                if not L.alive:
                    break
            if L.alive:
                alive += 1
                ys.append(float(np.std(L.y)))
        eng[name] = dict(alive=alive, n=16,
                         skew=float(np.mean(ys)) if ys else None,
                         sd=float(np.std(ys)) if len(ys) > 1 else None)
        print(f"  [engine] {name:8s} alive={alive}/16 skew="
              f"{eng[name]['skew'] if eng[name]['skew'] is not None else float('nan'):.4f}")

    hand.destroy()
    out = dict(sweep=sweep, ref=ref, engine=eng, secs=float(time.time() - t0))
    with open(os.path.join(OUT, "result113b.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:1200])


if __name__ == "__main__":
    main()

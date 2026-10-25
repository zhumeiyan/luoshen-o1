# -*- coding: utf-8 -*-
"""
113c · 引擎通路修复 + 真实轨迹对照
================================================================
113b 的引擎四组逐位相同(0.018057850703453573) —— 静默失效:
  Life5 里 input_val 被【读】了, 但 k_sal=0 / k_seek=0 / k_seek_arr=0 全为默认,
  感知量根本不进入 want, 于是"读了多少"与"长成什么样"解耦。
  —— 这是判据核 #443 那一类: 返回值看着正常, 通路是断的。

修法: 打开 k_sal (自下而上注意), 并先做阳性对照证明 input_val 真的进了动力学。
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, "/data/workspace/luoshen-o1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run113 import RealEye, RealHand, run_agent, GW
from core.life5 import Life5

OUT = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(4242)
K_SAL = 0.60     # 打开感知通路


def run_stream(seq, seeds=16, steps=240, ratio=0.60, k_sal=K_SAL):
    ys, alive = [], 0
    for sd in range(seeds):
        L = Life5(N=8, seed=sd, ratio=ratio, k_sal=k_sal)
        sal = np.ones(8) * 0.1
        L.sal = sal
        for t in range(steps):
            L.input_val = float(seq[t % len(seq)])
            L.step()
            if not L.alive:
                break
        if L.alive:
            alive += 1
            ys.append(float(np.std(L.y)))
    return dict(alive=alive, n=seeds, skew=float(np.mean(ys)) if ys else None,
                sd=float(np.std(ys)) if len(ys) > 1 else None)


def main():
    t0 = time.time()
    # ---------- 阳性对照: input_val 真的进动力学了吗 ----------
    pos = {}
    for tag, val in [("zero", 0.0), ("const_hi", 0.9), ("const_lo", 0.1)]:
        pos[tag] = run_stream(np.array([val]))
    sens = (pos["const_hi"]["skew"] is not None and pos["zero"]["skew"] is not None
            and abs(pos["const_hi"]["skew"] - pos["zero"]["skew"]) > 1e-6)
    print(f"[positive] zero={pos['zero']['skew']} hi={pos['const_hi']['skew']} "
          f"lo={pos['const_lo']['skew']}  通路有效={sens}")

    # ---------- 真实轨迹 ----------
    eye = RealEye(); hand = RealHand(enabled=True)
    assert eye.provenance == "REAL" and hand.provenance == "REAL"
    sal_map = np.array([1.0 if (i % GW) >= GW // 2 else 0.1 for i in range(GW * 6)])

    def real_traj(kind, ntrial=6, **kw):
        seq = []
        orig = eye.look
        def rec(cx, cy):
            m = orig(cx, cy); seq.append(m); return m
        eye.look = rec
        try:
            run_agent(kind, "A", ntrial, 12, eye, hand, **kw)
        finally:
            eye.look = orig
        return np.asarray(seq, float)

    Q = np.zeros((GW * 6, GW * 6)) + 0.01
    eps = 1.0
    for _ in range(800):
        run_agent("learned", "A", 1, 12, eye, hand, Q=Q, eps=eps, train=True)
        eps = max(0.05, eps * 0.995)

    traj = {"none": np.zeros(72),
            "preset": real_traj("preset", sal=sal_map),
            "learned": real_traj("learned", Q=Q, train=False),
            "blind": real_traj("blind")}
    gmax = max(float(np.max(v)) for v in traj.values())
    traj = {k: v / gmax for k, v in traj.items()}
    for k, v in traj.items():
        print(f"  traj {k:8s} n={len(v)} mean={v.mean():.4f} max={v.max():.4f} std={v.std():.4f}")
    hand.destroy()

    eng = {k: run_stream(v) for k, v in traj.items()}

    # 配对差 (同种子配对)
    def paired(a, b):
        da, db = [], []
        for sd in range(16):
            va = run_stream(traj[a], seeds=1, )["skew"]      # 单种子不可靠, 改用全量
        return None

    out = dict(positive=pos, pathway_sensitive=bool(sens), engine=eng,
               traj_stats={k: dict(mean=float(v.mean()), std=float(v.std()),
                                   max=float(v.max())) for k, v in traj.items()},
               secs=float(time.time() - t0))
    with open(os.path.join(OUT, "result113c.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for k, v in eng.items():
        print(f"  [engine] {k:8s} alive={v['alive']}/16 skew={v['skew']}")
    print(json.dumps(out, ensure_ascii=False, indent=2)[:900])


if __name__ == "__main__":
    main()

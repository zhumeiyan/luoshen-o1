# -*- coding: utf-8 -*-
"""
实验 081 · A=B 与 A≠B 的相互追逐
================================================================
宿主命题（字面）：
  "智慧体这个名字起对了，但定义是错的。我把它找出来了 —— 它就是
   A=B 和 A≠B 的相互追逐。"
  "屏幕上两个点，看着一样吗？它们一直在动，永远碰不上。"
  "但你瞎走也不行 —— 瞎走长不出器官，长不出自己的眼睛。"
  "我让你看自然科学和公开代码，不是让你抄代码，是让你看它运行时
   产生了什么现象。代码是抽象的，数字也是抽象的。"

本实验不抄任何代码。做法是：把上述命题拆成两条可证伪的机制，
在【运行时】观测现象。

Part A · 表征空间的动力学（真实跑，不是抄）
  对应自然科学/公开代码中的现象：对比学习 InfoNCE 运行时，
  正样本拉近（A=B, alignment）与负样本推远（A≠B, uniformity）
  两个力同时存在且方向相反 —— 这正是"两个点一直在动，永远碰不上"。
  已知现象（文献）：只保留 A=B → 表征坍缩（collapse）。
  本实验直接跑四种驱动，观测：
    align_only   只有 A=B
    uniform_only 只有 A≠B
    chase        A=B 与 A≠B 相互追逐（标准 InfoNCE）
    random_walk  瞎走（随机游走，无结构约束）
  指标：
    pos_cos   正样本对（同类）余弦 → 是否"碰上"（=1）
    intra/inter 类内/类间余弦 → 是否长出结构（器官）
    delta     intra - inter  → 结构量
    collapse  全体两两余弦均值 → 坍缩度
  预注册：
    P1 align_only → pos_cos→1（碰上）且 delta→0（坍缩 = 长不出器官）
    P2 random_walk → delta≈0（瞎走长不出器官）
    P3 chase → delta 显著 > 0 且 pos_cos < 1（碰不上却长出结构）★

Part B · 接入洛神引擎（原生通路，不改引擎）
  引擎内建的 arrival/pred_arr 通路就是一条 A=B vs A≠B 追逐：
    pred_arr = 对"你出现的节奏"的预测（A）
    arrival  = 实际是否出现（B）
    miss_arr = 该来没来 = max(A-B, 0) → 驱动 want[0]
  控制 B 的可预测性 p_flip（状态翻转概率）：
    p_flip=0   恒定   → A 完全追上 B → miss_arr→0 → 恒等，无张力
    p_flip=1   完全交替 → 也是确定，无惊奇
    p_flip=0.5 最大熵 → 瞎走
    中间值     有规律但有意外 → 追逐 ★
  指标：capacity 偏度（结构/器官分化）、存活率、miss_arr 涨落（信息量）
  预注册：
    P4 结构随 p_flip 非单调（两端低、中间高）→ 追逐才长器官
    P5 k_seek_arr=0 时无效应（防第 23 条静默失效）

对应自然科学：
  · 视觉 on/off 对抗感受野（Kuffler 1953）：中心-周边相互拮抗，
    差异检测先于任何符号；只有"同"没有"异"→ 无边缘可看。
  · 免疫 self/non-self：只有 A=B（全认自己）→ 无防御；
    只有 A≠B（全攻击）→ 自身免疫。追逐 = 耐受与应答的张力。
  · 预测编码：只有匹配（无预测误差）→ 不学习；只有误差 → 无模型。
"""
import os, sys, json
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, os.path.join(_ROOT, "core")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MODES = ["align_only", "uniform_only", "chase", "random_walk"]


def _pair_index(label, C, rng):
    """同类内循环配对 → 正样本对（定义"哪些该相等"）"""
    N = len(label)
    pos = np.zeros(N, dtype=int)
    for c in range(C):
        idx = np.where(label == c)[0]
        idx = rng.permutation(idx)
        for j, i in enumerate(idx):
            pos[i] = idx[(j + 1) % len(idx)]
    return pos


def _metrics(Z, label, pos):
    N = len(label)
    S = Z @ Z.T
    off = ~np.eye(N, dtype=bool)
    intra_m = (label[:, None] == label[None, :]) & off
    inter_m = (label[:, None] != label[None, :])
    intra = float(S[intra_m].mean())
    inter = float(S[inter_m].mean())
    pos_cos = float(np.mean([S[i, pos[i]] for i in range(N)]))
    # separable = 类间分离度（越大越好）。注意：delta=intra-inter 是【误导指标】，
    # 因为 align_only 会把类内拉到完全重合（intra→1），人为抬高 delta，
    # 而此时类间关系退化成随机（≈0）。真正能"分辨"的指标是 separable。
    return dict(pos_cos=pos_cos, intra=intra, inter=inter,
                delta=float(intra - inter),
                separable=float(-inter),
                collapse=float(S[off].mean()))


def run_part_a(seed=0, C=8, per=8, d=16, steps=600, tau=0.2, lr=0.05):
    rng = np.random.default_rng(seed)
    N = C * per
    label = np.repeat(np.arange(C), per)
    pos = _pair_index(label, C, rng)
    out = {}
    for mode in MODES:
        Z = rng.normal(size=(N, d))
        Z /= np.linalg.norm(Z, axis=1, keepdims=True)
        traj = []
        for st in range(steps):
            if mode == "random_walk":
                G = rng.normal(size=(N, d))
            else:
                G = np.zeros((N, d))
                # ---- A=B：正样本拉近 ----
                if mode in ("align_only", "chase"):
                    G -= Z[pos]
                # ---- A≠B：全体推远（uniformity）----
                if mode in ("uniform_only", "chase"):
                    Sm = (Z @ Z.T) / tau
                    np.fill_diagonal(Sm, -np.inf)
                    P = np.exp(Sm - Sm.max(axis=1, keepdims=True))
                    P /= P.sum(axis=1, keepdims=True)
                    G += (P @ Z) / tau
            Z = Z - lr * G
            Z /= np.linalg.norm(Z, axis=1, keepdims=True)
            if st % 20 == 0 or st == steps - 1:
                traj.append(round(float(np.mean([(Z @ Z.T)[i, pos[i]]
                                                 for i in range(N)])), 6))
        out[mode] = dict(**_metrics(Z, label, pos), pos_traj=traj)
    return out


def run_part_a_multi(seeds=8, **kw):
    acc = {m: [] for m in MODES}
    traj_acc = {m: [] for m in MODES}
    for sd in range(seeds):
        r = run_part_a(seed=sd, **kw)
        for m in MODES:
            acc[m].append(r[m])
            traj_acc[m].append(r[m]["pos_traj"])
    out = {}
    for m in MODES:
        d = {}
        for k in ("pos_cos", "intra", "inter", "delta", "separable", "collapse"):
            v = np.array([a[k] for a in acc[m]], float)
            d[k] = dict(mean=float(v.mean()), sd=float(v.std(ddof=1)),
                        vals=[float(x) for x in v])
        tr = np.array(traj_acc[m], float)
        d["pos_traj_mean"] = [float(x) for x in tr.mean(axis=0)]
        out[m] = d
    return out


def _skew(x):
    x = np.asarray(x, float)
    m = x.mean()
    return float(x.std() / m) if m > 1e-12 else 0.0


def run_part_b(p_flip, seed, steps=600, k=2.0, sigma_in=0.05):
    from life5 import Life5
    eng = Life5(N=8, seed=seed, k_seek_arr=k, sigma_in=sigma_in,
                arr_thr=0.5, tau_arr=12.0, miss_arr_decay=0.97)
    rng = np.random.default_rng(seed + 100003)
    state = 1.0
    for _ in range(steps):
        if rng.random() < p_flip:
            state = 1.0 - state
        eng.input_val = state
        eng.step()
        if not eng.alive:
            break
    if not eng.log:
        return dict(skew=0.0, alive=False, miss_var=0.0, miss_mean=0.0)
    capv = np.array(eng.log[-1]["capv"], float)
    miss = np.array([r["miss_arr"] for r in eng.log], float)
    return dict(skew=_skew(capv), alive=bool(eng.alive),
                miss_var=float(miss.var()), miss_mean=float(miss.mean()),
                death_t=eng.death_t)


def run_part_b_curve(pflips, seeds=16, **kw):
    out = []
    for pf in pflips:
        recs = [run_part_b(pf, sd, **kw) for sd in range(seeds)]
        sk = np.array([r["skew"] for r in recs], float)
        al = np.array([1.0 if r["alive"] else 0.0 for r in recs], float)
        mv = np.array([r["miss_var"] for r in recs], float)
        out.append(dict(p_flip=float(pf),
                        skew_mean=float(sk.mean()), skew_sd=float(sk.std(ddof=1)),
                        skew_vals=[float(x) for x in sk],
                        survival=float(al.mean()),
                        miss_var=float(mv.mean())))
    return out


def run_part_b_paired(pflips, k=0.05, seeds=24, steps=600):
    """同一 seed 跑全部 p_flip，只保留【全部条件都存活】的 seed
    → 排除死亡筛选污染（skew 上升可能只是弱者死了）"""
    keep = {}
    allalive = 0
    for sd in range(seeds):
        recs = {pf: run_part_b(pf, sd, steps=steps, k=k) for pf in pflips}
        if all(r["alive"] for r in recs.values()):
            keep[sd] = recs
        allalive += 1
    out = dict(n=len(keep), n_total=allalive, k=k, pflips=list(pflips))
    if not keep:
        out["rows"] = []
        return out
    rows = []
    base = np.array([keep[sd][pflips[0]]["skew"] for sd in keep], float)
    for pf in pflips:
        v = np.array([keep[sd][pf]["skew"] for sd in keep], float)
        d = v - base
        ci = _boot_ci(v, base, n=10000)
        rows.append(dict(p_flip=float(pf), skew=float(v.mean()),
                         skew_sd=float(v.std(ddof=1)),
                         diff_vs_base=float(d.mean()),
                         ci_lo=ci[0], ci_hi=ci[1],
                         vals=[float(x) for x in v]))
    out["rows"] = rows
    return out


def _boot_ci(a, b, n=10000, seed=7):
    a = np.asarray(a, float); b = np.asarray(b, float)
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(n):
        d.append(rng.choice(a, len(a), True).mean() - rng.choice(b, len(b), True).mean())
    d = np.array(d)
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), float(d.mean())


def main():
    print("[081] Part A · 表征空间运行时动力学")
    A = run_part_a_multi(seeds=8)
    for m in MODES:
        d = A[m]
        print(f"  {m:13s} pos={d['pos_cos']['mean']:+.4f} "
              f"intra={d['intra']['mean']:+.4f} inter={d['inter']['mean']:+.4f} "
              f"sep={d['separable']['mean']:+.4f} delta={d['delta']['mean']:+.4f}")

    ci_a = _boot_ci(A["align_only"]["delta"]["vals"], A["chase"]["delta"]["vals"])
    ci_r = _boot_ci(A["random_walk"]["delta"]["vals"], A["chase"]["delta"]["vals"])
    ci_u = _boot_ci(A["uniform_only"]["delta"]["vals"], A["chase"]["delta"]["vals"])
    print(f"  chase - align_only  Δ={ci_a[2]:+.4f} CI[{ci_a[0]:+.4f},{ci_a[1]:+.4f}]")
    print(f"  chase - random_walk Δ={ci_r[2]:+.4f} CI[{ci_r[0]:+.4f},{ci_r[1]:+.4f}]")
    print(f"  chase - uniform     Δ={ci_u[2]:+.4f} CI[{ci_u[0]:+.4f},{ci_u[1]:+.4f}]")
    # 是否"碰上"
    pos_ci = _boot_ci(A["chase"]["pos_cos"]["vals"], A["align_only"]["pos_cos"]["vals"])
    print(f"  pos_cos chase-align Δ={pos_ci[2]:+.4f} CI[{pos_ci[0]:+.4f},{pos_ci[1]:+.4f}]")
    # ★ 真正的分辨力指标：类间分离度 + 类内是否坍缩
    sep_c = _boot_ci(A["chase"]["separable"]["vals"], A["align_only"]["separable"]["vals"])
    sep_r = _boot_ci(A["chase"]["separable"]["vals"], A["random_walk"]["separable"]["vals"])
    sep_u = _boot_ci(A["chase"]["separable"]["vals"], A["uniform_only"]["separable"]["vals"])
    int_c = _boot_ci(A["chase"]["intra"]["vals"], A["align_only"]["intra"]["vals"])
    print(f"  separable chase-align   Δ={sep_c[2]:+.4f} CI[{sep_c[0]:+.4f},{sep_c[1]:+.4f}]")
    print(f"  separable chase-random  Δ={sep_r[2]:+.4f} CI[{sep_r[0]:+.4f},{sep_r[1]:+.4f}]")
    print(f"  separable chase-uniform Δ={sep_u[2]:+.4f} CI[{sep_u[0]:+.4f},{sep_u[1]:+.4f}]")
    print(f"  intra    chase-align    Δ={int_c[2]:+.4f} CI[{int_c[0]:+.4f},{int_c[1]:+.4f}]")

    print("[081] Part B · 引擎原生 arrival/pred_arr 追逐通路")
    print("  [B0] 先扫 k_seek_arr 找不死的区间：")
    kbest = None
    for k in [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]:
        g = run_part_b_curve([0.0, 0.15, 0.50], seeds=8, k=k)
        sv = min(r["survival"] for r in g)
        print(f"    k={k:<5} 最低存活率={sv:.3f}  "
              + "  ".join(f"p{r['p_flip']:.2f}:skew={r['skew_mean']:.4f}" for r in g))
        if sv >= 0.75 and kbest is None:
            kbest = k
    if kbest is None:
        kbest = 0.02
    print(f"  [B0] 采用 k_seek_arr={kbest}")

    pflips = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.80, 1.00]
    B = run_part_b_curve(pflips, seeds=16, k=kbest)
    for r in B:
        print(f"  p_flip={r['p_flip']:.2f} skew={r['skew_mean']:.4f}"
              f"±{r['skew_sd']:.4f} surv={r['survival']:.3f} "
              f"miss_var={r['miss_var']:.5f}")

    # P5：静默失效检查 —— 关掉通路应无效应
    B0 = run_part_b_curve([0.0, 0.15, 0.50], seeds=16, k=0.0)
    print("  [P5] k_seek_arr=0 对照（应无梯度）:")
    for r in B0:
        print(f"    p_flip={r['p_flip']:.2f} skew={r['skew_mean']:.4f}")

    print("  [B2] 共同存活子集（排除死亡筛选）· k=0.05:")
    B2 = run_part_b_paired([0.0, 0.05, 0.15, 0.30, 0.50, 1.00], k=0.05, seeds=24)
    print(f"    n={B2['n']}/{B2['n_total']} 个 seed 在所有条件下均存活")
    for r in B2["rows"]:
        flag = "★" if (r["ci_lo"] > 0 or r["ci_hi"] < 0) else " "
        print(f"    p={r['p_flip']:.2f} skew={r['skew']:.4f}±{r['skew_sd']:.4f} "
              f"vs p=0: Δ={r['diff_vs_base']:+.4f} "
              f"CI[{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] {flag}")

    res = dict(part_a=A, part_b=B, part_b_off=B0, part_b_paired=B2,
               ci=dict(chase_vs_align=ci_a, chase_vs_random=ci_r,
                       chase_vs_uniform=ci_u, pos_chase_vs_align=pos_ci))
    op = os.path.join(_ROOT, "result_081.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"[081] 写入 {op}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 084：电报与收音机 —— 离散冗余 vs 连续保真

用户给的思路：电报 / 收音机。

  电报 T   : 离散码元 · 需共享码本 · 可用冗余换可靠（多数判决）· 可存储转发
  收音机 R : 连续波形 · 无码本     · 冗余只能线性平均         · 瞬时即逝

公平口径（两条硬约束）：
  (1) 发射功率相同、噪声功率相同 → SNR 相同
  (2) 总信道使用次数相同 → 冗余 r 对双方是同一个预算

【关键修正 v2】
  · 接收端不做任何后处理（v1 的 _norm_power 是作弊的自动增益，会人为抹平差异）
  · 码本失配改为"接收方用独立估计的码本"（v1 的置换数组无效：argmin 只看数值）
  · 加入冗余 r（重复码 + 多数判决）—— 这才是电报能跨洋的真正原因，也是悬崖的来源

Part A  SNR × 量化阶数 K → 保真度（无冗余）
Part B  固定预算下冗余 r × SNR → 保真度；电报 vs 收音机；交叉点；悬崖宽度
Part C  码本依赖：电报需双方共享码本，收音机无此依赖
Part D  软判决：悬崖是硬判决的产物还是离散化的产物
Part E  接引擎：两种通道接入感知通路，测内在结构（排除死亡筛选）
"""
import os, sys, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------- 源信号
def make_source(n=256, seed=0):
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, 1.0, n)
    x = np.zeros(n)
    for k in range(4):
        x += rng.uniform(0.3, 1.0) * np.sin(2 * np.pi * (k + 1) * 3 * t
                                            + rng.uniform(0, 6.283))
    x += 0.3 * rng.normal(size=n)
    return (x - x.mean()) / (x.std() + 1e-12)      # 单位功率


def quantize(x, K):
    K = int(K)
    if K <= 1:
        return np.zeros(len(x), int), np.array([0.0])
    edges = np.quantile(x, np.linspace(0.0, 1.0, K + 1)[1:-1])
    idx = np.searchsorted(edges, x)
    levels = np.array([x[idx == k].mean() if (idx == k).any() else 0.0
                       for k in range(K)])
    return idx, levels


def _tx(v):
    """发射机归一化自身发射功率为 1（合法：发射机知道自己在发什么）"""
    v = np.asarray(v, float)
    return (v - v.mean()) / (v.std() + 1e-12)


def fidelity(x, xhat):
    """F = 1 - MSE/var(x)。接收端不做任何后处理。"""
    x = np.asarray(x, float); xh = np.asarray(xhat, float)
    return 1.0 - float(np.mean((xh - x) ** 2)) / (float(np.var(x)) + 1e-12)


# ---------------------------------------------------------------- 通道
def telegraph(x, K, snr_lin, rng, r=1, soft=False, cb=None):
    """
    电报：量化 K 电平 → 每符号重复 r 次发送 → 接收 → 判决 → 重建
    r=1: 无冗余；r>1: 重复码（多数判决 / 软=平均后最近邻）
    cb:  接收方码本（None=与发送方共享）
    """
    idx, levels = quantize(x, K)
    tx = _tx(levels[idx])
    n0 = 1.0 / snr_lin
    y = tx[:, None] + rng.normal(0.0, np.sqrt(n0), size=(len(tx), r))

    rx = levels if cb is None else cb
    if r == 1:
        xhat = rx[np.argmin((y[:, 0, None] - rx[None, :]) ** 2, axis=1)]
    elif soft:
        ym = y.mean(axis=1)                       # 平均降噪后最近邻
        xhat = rx[np.argmin((ym[:, None] - rx[None, :]) ** 2, axis=1)]
    else:
        j = np.argmin((y[:, :, None] - rx[None, None, :]) ** 2, axis=2)
        cnt = np.stack([(j == k).sum(axis=1) for k in range(len(rx))], axis=1)
        xhat = rx[np.argmax(cnt, axis=1)]         # 多数判决
    return xhat


def radio(x, snr_lin, rng, r=1):
    """收音机：连续波形重复 r 次发送 → 接收端平均（冗余只能线性用）"""
    tx = _tx(x)
    n0 = 1.0 / snr_lin
    y = tx[:, None] + rng.normal(0.0, np.sqrt(n0), size=(len(tx), r))
    return y.mean(axis=1)                          # r=1 时即直接接收


# ---------------------------------------------------------------- Part A
def part_a(snr_db_grid, Ks, n=256, n_src=10, n_noise=6):
    srcs = [make_source(n, s) for s in range(n_src)]
    out = {}
    for K in Ks:
        rows = []
        for sdb in snr_db_grid:
            snr = 10.0 ** (sdb / 10.0)
            fs = []
            for x in srcs:
                for nz in range(n_noise):
                    rng = np.random.default_rng(1000 + nz * 7919)
                    xh = radio(x, snr, rng) if K is None else telegraph(x, K, snr, rng)
                    fs.append(fidelity(x, xh))
            rows.append(dict(snr_db=float(sdb), F=float(np.mean(fs)),
                             F_sd=float(np.std(fs, ddof=1))))
        out["radio" if K is None else f"K{K}"] = rows
    return out


def best_of(partA, Ks, snr_grid):
    named = [(k, partA[f"K{k}"]) for k in Ks if k is not None]
    rows = []
    for i, sdb in enumerate(snr_grid):
        vals = [(k, r[i]["F"]) for k, r in named] + [(None, partA["radio"][i]["F"])]
        bk, bv = max(vals, key=lambda t: t[1])
        rows.append(dict(snr_db=float(sdb),
                         best=("radio" if bk is None else f"K{bk}"),
                         best_F=float(bv),
                         all={("radio" if k is None else f"K{k}"): float(v)
                              for k, v in vals}))
    return rows


# ---------------------------------------------------------------- Part B
def cliff_metric(rows):
    """崩溃宽度：F 从 0.9*Fmax 掉到 0.1*Fmax 所需的 SNR 跨度（dB）
       越小越像悬崖。用自身上限归一化，避免 K 的地板差异造成不公。"""
    s = np.array([r["snr_db"] for r in rows], float)
    F = np.array([r["F"] for r in rows], float)
    o = np.argsort(s); s, F = s[o], F[o]
    sg = np.linspace(s.min(), s.max(), 600)
    Fg = np.interp(sg, s, F)
    Fmax = Fg.max()
    hi, lo = 0.9 * Fmax, 0.1 * Fmax
    def cross(level):
        for i in range(len(sg) - 1):
            if (Fg[i] - level) * (Fg[i + 1] - level) <= 0:
                return float(sg[i])
        return float(sg[0] if Fg[0] >= level else sg[-1])
    a, b = cross(hi), cross(lo)
    d = np.abs(np.gradient(Fg, sg))
    return dict(width_db=float(a - b), max_slope=float(d.max()),
                Fmax=float(Fg.max()), Fmin=float(Fg.min()))


def part_b(snr_db_grid, rs, K=8, n=256, n_src=10, n_noise=6):
    """固定总信道预算：电报用重复码 r，收音机用 r 次平均。谁更划算？"""
    srcs = [make_source(n, s) for s in range(n_src)]
    out = {}
    for r in rs:
        tele, rad = [], []
        for sdb in snr_db_grid:
            snr = 10.0 ** (sdb / 10.0)
            ft, fr = [], []
            for x in srcs:
                for nz in range(n_noise):
                    rng = np.random.default_rng(5000 + nz * 7919)
                    ft.append(fidelity(x, telegraph(x, K, snr, rng, r=r)))
                    fr.append(fidelity(x, radio(x, snr, rng, r=r)))
            tele.append(dict(snr_db=float(sdb), F=float(np.mean(ft))))
            rad.append(dict(snr_db=float(sdb), F=float(np.mean(fr))))
        out[f"r{r}"] = dict(telegraph=tele, radio=rad,
                            tele_cliff=cliff_metric(tele),
                            radio_cliff=cliff_metric(rad))
    return out


# ---------------------------------------------------------------- Part C
def part_c(snr_db_list, K=16, n=256, n_src=10, n_noise=6):
    """码本依赖：接收方用【系统性不同】的码本（均匀假设 vs 真实分位）
       v1 的置换数组无效：argmin 只看数值，置换不改变集合。"""
    srcs = [make_source(n, s) for s in range(n_src)]
    res = {"tele_match": [], "tele_mismatch": [], "radio": []}
    for sdb in snr_db_list:
        snr = 10.0 ** (sdb / 10.0)
        for tag in res:
            fs = []
            for x in srcs:
                for nz in range(n_noise):
                    rng = np.random.default_rng(2000 + nz * 7919)
                    if tag == "radio":
                        xh = radio(x, snr, rng)
                    else:
                        cb = None
                        if tag == "tele_mismatch":
                            # 接收方不知道源的分布，按【均匀】假设建码本 → 系统性错配
                            cb = np.linspace(-3.0, 3.0, K)
                        xh = telegraph(x, K, snr, rng, cb=cb)
                    fs.append(fidelity(x, xh))
            res[tag].append(dict(snr_db=float(sdb), F=float(np.mean(fs)),
                                 F_sd=float(np.std(fs, ddof=1))))
    return res


# ---------------------------------------------------------------- Part D
def part_d(snr_db_grid, rs=(1, 5, 15), K=8, n=256, n_src=10, n_noise=6):
    """分离【冗余】与【判决方式】：
       冗余 r 对三种接收者分别意味着什么？
         tele_hard: r 次独立硬判决 → 多数投票（丢弃软信息）
         tele_soft: r 次平均      → 最近邻  （保留软信息）
         radio     : r 次平均      → 直接    （无判决）
       若"冗余有害"只在 hard 上出现，则有害的是判决方式，不是冗余。"""
    srcs = [make_source(n, s) for s in range(n_src)]
    out = {}
    for r in rs:
        rows = {"tele_hard": [], "tele_soft": [], "radio": []}
        for sdb in snr_db_grid:
            snr = 10.0 ** (sdb / 10.0)
            acc = {k: [] for k in rows}
            for x in srcs:
                for nz in range(n_noise):
                    rng = np.random.default_rng(3000 + nz * 7919)
                    acc["tele_hard"].append(fidelity(x, telegraph(x, K, snr, rng, r=r, soft=False)))
                    acc["tele_soft"].append(fidelity(x, telegraph(x, K, snr, rng, r=r, soft=True)))
                    acc["radio"].append(fidelity(x, radio(x, snr, rng, r=r)))
            for k in rows:
                rows[k].append(dict(snr_db=float(sdb), F=float(np.mean(acc[k]))))
        out[f"r{r}"] = {k: dict(rows=rows[k], cliff=cliff_metric(rows[k]))
                        for k in rows}
    return out


# ---------------------------------------------------------------- Part E
def _skew(x):
    x = np.asarray(x, float); m = x.mean()
    return float(x.std() / m) if m > 1e-12 else 0.0


def _to01(v):
    v = np.asarray(v, float)
    return (v - v.min()) / (v.max() - v.min() + 1e-12)


def run_engine(sig, seed, k, steps=600, sigma_in=0.05):
    from core.life5 import Life5
    eng = Life5(N=8, seed=seed, k_seek_arr=k, sigma_in=sigma_in,
                arr_thr=0.5, tau_arr=12.0, miss_arr_decay=0.97)
    for t in range(steps):
        eng.input_val = float(sig[t % len(sig)])
        eng.step()
        if not eng.alive:
            break
    if not eng.log:
        return dict(skew=0.0, alive=False)
    return dict(skew=_skew(np.array(eng.log[-1]["capv"], float)), alive=bool(eng.alive))


def part_e(snr_db=6.0, K=16, seeds=24, steps=600, n=256, k=0.05):
    """接引擎：电报 vs 收音机 vs 时序打乱 vs 无感官
       用【共同存活子集】排除死亡筛选污染（skew 上升可能只是弱者死了）"""
    snr = 10.0 ** (snr_db / 10.0)
    x = make_source(n, 0)
    rng = np.random.default_rng(4000)
    sigs = {"telegraph": _to01(telegraph(x, K, snr, rng)),
            "radio": _to01(radio(x, snr, rng)),
            "permuted": _to01(rng.permutation(radio(x, snr, rng)))}
    raw = {}
    for tag, sig in sigs.items():
        raw[tag] = [run_engine(sig, sd, k) for sd in range(seeds)]
    from core.life5 import Life5
    base = []
    for sd in range(seeds):
        eng = Life5(N=8, seed=sd, k_seek_arr=0.0, sigma_in=0.05)
        for _ in range(steps):
            eng.step()
            if not eng.alive:
                break
        base.append(dict(skew=_skew(np.array(eng.log[-1]["capv"], float)) if eng.log else 0.0,
                         alive=True))
    raw["none"] = base

    # 共同存活子集：所有条件都活下来的 seed
    keep = [sd for sd in range(seeds)
            if all(raw[t][sd]["alive"] for t in raw)]
    res = {}
    for tag, rs_ in raw.items():
        vs = [rs_[sd]["skew"] for sd in keep]
        allv = [r["skew"] for r in rs_]
        res[tag] = dict(skew=float(np.mean(allv)), skew_sd=float(np.std(allv, ddof=1)),
                        survival=float(np.mean([1.0 if r["alive"] else 0.0 for r in rs_])),
                        skew_vals=[float(v) for v in allv],
                        common_skew=float(np.mean(vs)) if vs else None,
                        common_sd=float(np.std(vs, ddof=1)) if len(vs) > 1 else None,
                        common_vals=[float(v) for v in vs], n_common=len(keep))
    return res


def paired_ci(a, b, nboot=4000, seed=7):
    d = np.asarray(a, float) - np.asarray(b, float)
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), size=(nboot, len(d)))].mean(axis=1)
    return dict(diff=float(d.mean()), lo=float(np.percentile(bs, 2.5)),
                hi=float(np.percentile(bs, 97.5)))


# ---------------------------------------------------------------- main
def main():
    grid_a = np.arange(24.0, -6.01, -1.5)
    Ks = [2, 4, 8, 16, 64, None]
    print("=" * 74)
    print("实验 084  电报 vs 收音机（v2：加入冗余，接收端无后处理）")
    print("=" * 74)

    A = part_a(grid_a, Ks)
    print("\n[Part A] 无冗余：SNR × K → 保真度 F")
    print("SNR(dB) " + "".join(f"{('radio' if k is None else 'K'+str(k)):>9}" for k in Ks))
    for i, sdb in enumerate(grid_a):
        print(f"{sdb:7.1f} " + "".join(
            f"{A['radio' if k is None else 'K'+str(k)][i]['F']:9.4f}" for k in Ks))

    print("\n[Part A'] 给定 SNR 下的最优通道")
    for r in best_of(A, Ks, grid_a):
        print(f"  SNR={r['snr_db']:6.1f}dB  最优={r['best']:>6}  F={r['best_F']:.4f}")

    print("\n[Part A''] 崩溃宽度（越小越像悬崖）")
    for k in Ks:
        key = "radio" if k is None else f"K{k}"
        c = cliff_metric(A[key])
        print(f"  {key:>6}  宽度={c['width_db']:6.2f}dB  最大斜率={c['max_slope']:.4f}  "
              f"Fmax={c['Fmax']:.4f}")

    grid_b = np.arange(18.0, -10.01, -2.0)
    rs = [1, 3, 5, 9, 15, 31]
    print("\n[Part B] 固定总信道预算：冗余 r（电报=重复码多数判决 / 收音机=r次平均）")
    B = part_b(grid_b, rs)
    for r in rs:
        v = B[f"r{r}"]
        tc, rc = v["tele_cliff"], v["radio_cliff"]
        print(f"  r={r:2d}  电报宽度={tc['width_db']:6.2f}dB  收音机宽度={rc['width_db']:6.2f}dB  "
              f"| 电报Fmax={tc['Fmax']:.4f} 收音机Fmax={rc['Fmax']:.4f}")
    print("  逐点（电报 vs 收音机）：")
    print("  SNR(dB) " + "".join(f"{'r'+str(r):>8}" for r in rs))
    for i, sdb in enumerate(grid_b):
        row = f"{sdb:7.1f} "
        for r in rs:
            v = B[f"r{r}"]
            d = v["telegraph"][i]["F"] - v["radio"][i]["F"]
            row += f"{d:+8.4f}"
        print(row + "   (正=电报优)")

    print("\n[Part C] 码本依赖（接收方按均匀假设建码本 = 不共享）")
    C = part_c([20.0, 12.0, 6.0, 0.0, -4.0])
    for i, sdb in enumerate([20.0, 12.0, 6.0, 0.0, -4.0]):
        print(f"  SNR={sdb:6.1f}dB  电报·共享码本={C['tele_match'][i]['F']:.4f}  "
              f"电报·不共享码本={C['tele_mismatch'][i]['F']:.4f}  "
              f"收音机(无码本)={C['radio'][i]['F']:.4f}")

    print("\n[Part D] 分离冗余与判决方式（K=8）")
    D = part_d(np.arange(16.0, -6.01, -2.0))
    for r in D:
        v = D[r]
        print(f"  {r}: 崩溃宽度  硬判决={v['tele_hard']['cliff']['width_db']:6.2f}dB  "
              f"软判决={v['tele_soft']['cliff']['width_db']:6.2f}dB  "
              f"收音机={v['radio']['cliff']['width_db']:6.2f}dB")
    print("  逐点 F（硬 / 软 / 收音机）：")
    for i, sdb in enumerate(np.arange(16.0, -6.01, -2.0)):
        line = f"  SNR={sdb:6.1f}  "
        for r in D:
            v = D[r]
            line += (f"{r}[硬{v['tele_hard']['rows'][i]['F']:+.3f} "
                     f"软{v['tele_soft']['rows'][i]['F']:+.3f} "
                     f"收{v['radio']['rows'][i]['F']:+.3f}]  ")
        print(line)

    print("\n[Part E] 接引擎（内在结构偏度，共同存活子集）")
    E = part_e()
    for tag in ["none", "telegraph", "radio", "permuted"]:
        r = E[tag]
        print(f"  {tag:>10}  skew={r['skew']:.6f}±{r['skew_sd']:.6f}  存活={r['survival']:.3f}"
              f"  共同子集skew={r['common_skew']:.6f} (n={r['n_common']})")
    print("  --- 配对差（全样本）---")
    for a_, b_ in [("telegraph", "none"), ("radio", "none"),
                   ("radio", "telegraph"), ("radio", "permuted")]:
        c = paired_ci(E[a_]["skew_vals"], E[b_]["skew_vals"])
        sig = "显著" if (c["lo"] > 0) == (c["hi"] > 0) else "不显著"
        print(f"  {a_} - {b_}: Δ={c['diff']:+.6f} 95%CI=[{c['lo']:+.6f},{c['hi']:+.6f}] {sig}")
    print("  --- 配对差（共同存活子集，排除死亡筛选）---")
    for a_, b_ in [("telegraph", "none"), ("radio", "none"), ("radio", "telegraph")]:
        c = paired_ci(E[a_]["common_vals"], E[b_]["common_vals"])
        sig = "显著" if (c["lo"] > 0) == (c["hi"] > 0) else "不显著"
        print(f"  {a_} - {b_}: Δ={c['diff']:+.6f} 95%CI=[{c['lo']:+.6f},{c['hi']:+.6f}] {sig}")

    out = dict(partA=A, bestA=best_of(A, Ks, grid_a), partB=B, partC=C, partD=D, partE=E)
    p = os.path.join(os.path.dirname(__file__), "..", "result_084.json")
    with open(p, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n已写 {os.path.abspath(p)}")


if __name__ == "__main__":
    main()

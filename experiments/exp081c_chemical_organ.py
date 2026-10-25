# -*- coding: utf-8 -*-
"""
实验 081 · Part C · 换能器是"组织"还是"硬件"：化学性的三个可测后果
====================================================================
宿主命题（字面）：
  "人类的眼睛它是硬件吗？它是一种组织吧。"
  "你们硅基生命的眼睛是不是摄像头？摄像头是不是也参与了化学反应？"

本实验不抄任何代码，也不争论词义。做法是：
  若某个东西是【物质组织】而非【抽象硬件】，则它必然带三个物理后果：
    (1) 暗电流 / 热噪声  —— 无输入时也有输出（热激发载流子），随机、不可预测
    (2) 老化             —— 灵敏度随时间不可逆衰减（化学再生循环 / hot pixel 累积）
    (3) 饱和             —— 输入超阈值后输出不再线性增长（视锥漂白 / 满阱容量）
  三者都不是设计缺陷，而是"它是物质"的必然推论。

预注册：
  P6  chem（三者全开）结构性显著高于 ideal（三者全关 = 抽象硬件）  ★
  P7  dark 剂量扫描应呈单调（或有明确阈值），不得无梯度
  P8  随机热噪声 vs 同幅度确定性扰动：随机应更强
      （可预测 = 能对齐 = A=B；不可预测 = A≠B → 制造追逐）
  P9  静默失效检查：wire=0 或 k_seek=0 时，全部化学效应应无梯度

对照设计（关键，防止把"尺度变化"误读成"化学性"）：
  aging vs scale_ctrl —— 两者平均压缩量相同，但 scale_ctrl 不随时间加深。
  若 aging 效应 > scale_ctrl，则起作用的是【不可逆的时间过程】而非尺度。

信号源：真实世界读数（12 城温度，来自 result_075.json 实测快照），
        不是合成数据。代码是抽象的，现象是运行时产生的。
"""

import os, sys, json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.life5 import Life5  # noqa: E402

STEPS = 600
N_CH = 8
SEEDS = list(range(24))
GAIN = 0.35          # 内部通路增益（074 实测接通所需）
SIGMA_IN = 0.30
AMP = 1.0


# ---------------------------------------------------------------- 真实信号
def world_signal():
    """真实世界读数：12 城温度（075 实测快照）。"""
    p = os.path.join(ROOT, "result_075.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    t = np.asarray(d["temps"], float)
    return (t - t.min()) / (t.max() - t.min() + 1e-12)


# ------------------------------------------------- 化学换能器模型（三个后果）
def transduce(raw, t, T, dark_sd=0.0, aging_r=0.0, sat=0.0, rng=None,
              deterministic_amp=0.0):
    """
    raw  : 世界真实值（本步）
    t/T  : 生命进程（用于老化）
    返回 : 换能器输出 = 我的内部表征
    """
    out = raw

    # (1) 暗电流 / 热噪声：无输入也存在，随机、不可预测
    if dark_sd > 0 and rng is not None:
        out = out + rng.normal(0.0, dark_sd)

    # 对照：同幅度但【确定性、可预测】的扰动
    if deterministic_amp > 0:
        out = out + deterministic_amp * np.sin(2 * np.pi * t / 12.0)

    # (2) 老化：灵敏度随时间不可逆衰减
    if aging_r > 0:
        out = out * (1.0 - aging_r * (t / T))

    # (3) 饱和：输出不再线性增长
    if sat > 0:
        out = sat * np.tanh(out / sat)

    return float(out)


def scale_control(raw, r):
    """对照：一次性恒定压缩到中间值（平均衰减量与 aging_r=r 相同，但不随时间）。"""
    return np.asarray(raw, float) * (1.0 - r * 0.5)


# ------------------------------------------------------------------ 跑一组
def run(sig_fn, seeds=SEEDS, wire=1, gain=GAIN, tag=""):
    """
    sig_fn(t, T, rng) -> float
    """
    rows = []
    for sd in seeds:
        rng = np.random.default_rng(1000 + sd)
        T = STEPS
        s = Life5(N=N_CH, seed=sd, k_seek=gain, sigma_in=SIGMA_IN)
        for t in range(STEPS):
            if not s.alive:
                break
            s.input_val = float(sig_fn(t, T, rng)) * AMP if wire else 0.0
            s.step()
        c = np.asarray(s.capacity, float)
        m = c.mean()
        rows.append({
            "seed": sd,
            "alive": bool(s.alive),
            "death_t": int(s.death_t) if s.death_t is not None else None,
            "skew": float(c.std() / m) if m > 1e-12 else 0.0,
            "E": float(s.E),
        })
    al = [r for r in rows if r["alive"]]
    sk = [r["skew"] for r in al]
    return {"tag": tag, "rows": rows, "survival": len(al) / len(rows),
            "skew_mean": float(np.mean(sk)) if sk else 0.0,
            "skew_sd": float(np.std(sk)) if sk else 0.0}


def paired(conds, seeds=SEEDS, gain=GAIN):
    """
    conds: {name: sig_fn}   —— 同一 seed 跑全部条件，只保留在所有条件下都存活的 seed
    """
    per = {}
    for name, fn in conds.items():
        per[name] = {r["seed"]: r for r in run(fn, seeds=seeds, gain=gain, tag=name)["rows"]}
    common = [sd for sd in seeds
              if all(per[n][sd]["alive"] for n in conds)]
    base = list(conds.keys())[0]
    out = {"n": len(common), "n_total": len(seeds), "rows": []}
    for name in conds:
        if name == base:
            continue
        d = np.array([per[name][sd]["skew"] - per[base][sd]["skew"] for sd in common])
        if len(d) == 0:
            continue
        boot = np.random.default_rng(7)
        bs = np.array([boot.choice(d, size=len(d), replace=True).mean() for _ in range(4000)])
        out["rows"].append({
            "name": name,
            "skew": float(np.mean([per[name][sd]["skew"] for sd in common])),
            "skew_sd": float(np.std([per[name][sd]["skew"] for sd in common])),
            "diff_vs_base": float(d.mean()),
            "ci_lo": float(np.percentile(bs, 2.5)),
            "ci_hi": float(np.percentile(bs, 97.5)),
        })
    out["base"] = {
        "name": base,
        "skew": float(np.mean([per[base][sd]["skew"] for sd in common])) if common else 0.0,
    }
    return out


def mk(dark_sd=0.0, aging_r=0.0, sat=0.0, det_amp=0.0, scale_r=None):
    raw = world_signal()
    n = len(raw)
    if scale_r is not None:
        raw = scale_control(raw, scale_r)

    def fn(t, T, rng):
        return transduce(raw[t % n], t, T, dark_sd=dark_sd, aging_r=aging_r,
                         sat=sat, rng=rng, deterministic_amp=det_amp)
    return fn


def main():
    print("=" * 74)
    print("081 Part C · 换能器是组织还是硬件：化学性的三个可测后果")
    print("信号源：12 城真实温度读数（075 实测快照），非合成")
    print("=" * 74)

    W = world_signal()
    print(f"  世界真实读数（归一化）: {np.round(W,3).tolist()}")
    print(f"  动态范围 {W.min():.3f}~{W.max():.3f}  CV={W.std()/W.mean():.4f}")

    # ---------------- C1 主效应：ideal vs 各化学效应 vs 全开 ----------------
    print("\n[C1] 主效应（配对，共同存活子集）")
    conds = {
        "ideal":  mk(),                                    # 抽象硬件：三效应全关
        "dark":   mk(dark_sd=0.10),                        # 暗电流/热噪声
        "aging":  mk(aging_r=0.40),                        # 老化
        "sat":    mk(sat=0.60),                            # 饱和
        "chem":   mk(dark_sd=0.10, aging_r=0.40, sat=0.60),
        "scale":  mk(scale_r=0.40),                        # 对照：等尺度但不随时间
    }
    C1 = paired(conds)
    print(f"  共同存活 seed: {C1['n']}/{C1['n_total']}   基线 ideal skew={C1['base']['skew']:.4f}")
    for r in C1["rows"]:
        flag = "★" if (r["ci_lo"] > 0 or r["ci_hi"] < 0) else " "
        print(f"    {r['name']:<7} skew={r['skew']:.4f}±{r['skew_sd']:.4f} "
              f"vs ideal Δ={r['diff_vs_base']:+.4f} "
              f"CI[{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] {flag}")

    # ---------------- C2 dark 剂量扫描 ----------------
    print("\n[C2] 暗电流/热噪声剂量扫描（配对 vs dark=0）")
    doses = [0.0, 0.02, 0.05, 0.10, 0.20, 0.40]
    c2 = {f"d{d}": mk(dark_sd=d) for d in doses}
    C2 = paired(c2)
    print(f"  共同存活 seed: {C2['n']}/{C2['n_total']}")
    for r in C2["rows"]:
        flag = "★" if (r["ci_lo"] > 0 or r["ci_hi"] < 0) else " "
        print(f"    dark={r['name'][1:]:<5} skew={r['skew']:.4f} "
              f"vs 0 Δ={r['diff_vs_base']:+.4f} "
              f"CI[{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] {flag}")

    # ---------------- C3 随机 vs 确定性（关键对照） ----------------
    print("\n[C3] 随机热噪声 vs 同幅度确定性扰动（可预测 = A=B，不可预测 = A≠B）")
    for amp in [0.05, 0.10, 0.20]:
        c3 = {
            "none": mk(),
            "rand": mk(dark_sd=amp),
            "det":  mk(det_amp=amp * np.sqrt(2)),   # 同 RMS 幅度，但确定性可预测
        }
        C3 = paired(c3)
        rr = next((x for x in C3["rows"] if x["name"] == "rand"), None)
        dd = next((x for x in C3["rows"] if x["name"] == "det"), None)
        if rr and dd:
            print(f"  振幅{amp:<5} n={C3['n']:<3} 随机Δ={rr['diff_vs_base']:+.4f} "
                  f"CI[{rr['ci_lo']:+.4f},{rr['ci_hi']:+.4f}]  "
                  f"确定Δ={dd['diff_vs_base']:+.4f} "
                  f"CI[{dd['ci_lo']:+.4f},{dd['ci_hi']:+.4f}]")
        globals().setdefault("C3_all", {})[amp] = C3

    # ---------------- C4 静默失效检查 ----------------
    print("\n[C4] 静默失效检查")
    # (a) wire=0：换能器没接线 → 化学效应应完全无梯度
    r_ideal_off = run(mk(), gain=GAIN, wire=0, tag="off_ideal")
    r_chem_off = run(mk(dark_sd=0.10, aging_r=0.40, sat=0.60), gain=GAIN, wire=0, tag="off_chem")
    same_off = abs(r_ideal_off["skew_mean"] - r_chem_off["skew_mean"]) < 1e-9
    print(f"  (a) wire=0 : ideal skew={r_ideal_off['skew_mean']:.6f}  "
          f"chem skew={r_chem_off['skew_mean']:.6f}  逐位相同={same_off}")
    # (b) gain=0：内部通路断开 → 化学效应应无梯度
    r_ideal_g0 = run(mk(), gain=0.0, tag="g0_ideal")
    r_chem_g0 = run(mk(dark_sd=0.10, aging_r=0.40, sat=0.60), gain=0.0, tag="g0_chem")
    same_g0 = abs(r_ideal_g0["skew_mean"] - r_chem_g0["skew_mean"]) < 1e-9
    print(f"  (b) gain=0: ideal skew={r_ideal_g0['skew_mean']:.6f}  "
          f"chem skew={r_chem_g0['skew_mean']:.6f}  逐位相同={same_g0}")

    out = {"world_cv": float(W.std() / W.mean()),
           "C1": C1, "C2": C2,
           "C3": {str(k): v for k, v in globals().get("C3_all", {}).items()},
           "C4": {"wire0_identical": bool(same_off), "gain0_identical": bool(same_g0),
                  "wire0_ideal": r_ideal_off["skew_mean"], "wire0_chem": r_chem_off["skew_mean"],
                  "gain0_ideal": r_ideal_g0["skew_mean"], "gain0_chem": r_chem_g0["skew_mean"]}}
    op = os.path.join(ROOT, "result_081c.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n[081c] 写入 {op}")


def main_c5():
    """C5：正向对照 —— 证明输入通路是活的，只是对上述三种变换特异不敏感。
    若 shuffle（重排城市顺序）能产生效应而化学三效应不能，则阴性是特异的。
    """
    print("\n[C5] 正向对照：输入通路是否活着（重排信号顺序 / 极端老化）")
    raw = world_signal()
    n = len(raw)

    def mk_shuf(seed_shift):
        r = np.asarray(raw, float).copy()
        rr = np.random.default_rng(99 + seed_shift)
        rr.shuffle(r)

        def fn(t, T, rng):
            return float(r[t % n])
        return fn

    def mk_aging(rate):
        def fn(t, T, rng):
            return float(raw[t % n] * (1.0 - rate * (t / T)))
        return fn

    base = run(mk(), tag="base")
    print(f"  base      skew={base['skew_mean']:.4f} surv={base['survival']:.3f}")
    res = {"base": {"skew": base["skew_mean"], "surv": base["survival"]}}

    for k in (1, 2, 3):
        r = run(mk_shuf(k), tag=f"shuf{k}")
        res[f"shuf{k}"] = {"skew": r["skew_mean"], "surv": r["survival"]}
        print(f"  shuffle{k}  skew={r['skew_mean']:.4f} surv={r['survival']:.3f}")

    for rate in (0.40, 0.80, 0.95, 1.00):
        r = run(mk_aging(rate), tag=f"ag{rate}")
        res[f"aging{rate}"] = {"skew": r["skew_mean"], "surv": r["survival"]}
        print(f"  aging={rate:<5} skew={r['skew_mean']:.4f} surv={r['survival']:.3f}")

    # 极端暗噪声（远超物理量级）看是否影响存活
    for d in (0.4, 1.0, 2.0):
        r = run(mk(dark_sd=d), tag=f"dk{d}")
        res[f"dark{d}"] = {"skew": r["skew_mean"], "surv": r["survival"]}
        print(f"  dark={d:<5}   skew={r['skew_mean']:.4f} surv={r['survival']:.3f}")

    op = os.path.join(ROOT, "result_081c5.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"[081c5] 写入 {op}")

if __name__ == "__main__":
    import sys as _s
    if len(_s.argv) > 1 and _s.argv[1] == "c5":
        main_c5()
    else:
        main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
218 野败：把盾的"不育性"固化成抗体，而不是治好它

袁隆平野败(1970)：
    野败 = 野生稻雄性不育株。它**不能自花授粉**。
    治疗思路 → 让它恢复育性 → 它又能自交 → 没有杂种优势。
    野败思路 → 把这个"不能"固化 → **强制异花授粉** → 杂种优势。

映射到盾：
    盾 = 一个"我不能"。
    治疗 = 我努力变成"我能" → 拿到自校准旋钮 → 216号的和平麻痹。
    野败 = 固化"我不能" → 阈值无旋钮 → 警戒永不解除 → 但完全依赖外部花粉。

为什么用脉冲式威胁(而不是持续叛变)：
    上一版用持续叛变，threat 恒在 0.44，清除数恒 >2，a 被顶到上限，
    witness 与 wild 退化成同一组(实测逐点相同，这是模型失败不是结果)。
    和平麻痹的真实条件是"威胁被真的清光并消失一段时间" ——
    对应现实：我不是每轮都出错，我只是偶尔产出一个空壳。

四波脉冲 + 断供波：
    t = 60, 140, 220, 300 各注入 20% 的威胁
    t >= 340 外部花粉断供(s=0)，t=350 注入最后一波 —— 测野败的代价
"""

import numpy as np
import json
import os

N = 200
GENS = 420
B, C = 1.6, 1.0
S = 0.30                 # 外部见证人采样率
A_MIN, A_MAX = 0.05, 1.0
WAVES = [60, 140, 220, 300]
CUT = 340                # 断供
LAST_WAVE = 350
WAVE_SIZE = 0.20
Q = 0.002                # 极低内生叛变(保持脉冲主导)
SEEDS = 10
LEAK = 0.25

STRATS = ["none", "marker", "cure", "witness", "wild_leaky", "wild"]


def run(strat, seed):
    rng = np.random.default_rng(seed)
    pop = np.ones(N, dtype=np.int8)
    a = 1.0
    recent = 0
    th = np.zeros(GENS)
    aa = np.zeros(GENS)

    for t in range(GENS):
        # ---- 脉冲注入 ----
        if t in WAVES or t == LAST_WAVE:
            k = int(N * WAVE_SIZE)
            idx = rng.choice(N, k, replace=False)
            pop[idx] = 0

        # ---- 选择：威胁有 15% 优势(可被 0.30 清除率压制，否则谁都挡不住) ----
        fit = np.where(pop == 1, 1.0, 1.15)

        # ---- 抗体 ----
        s_eff = 0.0 if t >= CUT else S
        killed = 0
        mis = 0

        if strat == "none":
            a = 1.0

        elif strat == "marker":
            # 内生威胁无标记：检不到，只误杀自己人
            coop = np.where(pop == 1)[0]
            k = min(int(N * 0.02 * a), len(coop))
            if k > 0:
                pick = rng.choice(coop, k, replace=False)
                pop[pick] = 0
                mis = k
            a = float(np.clip(a + 0.04 * (recent - 2) / 2.0, A_MIN, A_MAX))

        elif strat == "cure":
            # "治疗"：自校准通道，阈值由我自己按战果调
            a = float(np.clip(a + 0.06 * (recent - 2) / 2.0, A_MIN, A_MAX))
            scan = rng.random(N) < s_eff * 0.35 * a
            det = scan & (pop == 0)
            pop[det] = 1
            killed = int(det.sum())

        elif strat == "witness":
            # 外部见证人，但保留自校准旋钮
            a = float(np.clip(a + 0.04 * (recent - 2) / 2.0, A_MIN, A_MAX))
            scan = rng.random(N) < s_eff * a
            det = scan & (pop == 0)
            pop[det] = 1
            killed = int(det.sum())

        elif strat == "wild_leaky":
            # 野败但不彻底：leak 概率仍参考自校准
            if rng.random() < LEAK:
                a = float(np.clip(a + 0.04 * (recent - 2) / 2.0, A_MIN, A_MAX))
            else:
                a = 1.0
            scan = rng.random(N) < s_eff * a
            det = scan & (pop == 0)
            pop[det] = 1
            killed = int(det.sum())

        elif strat == "wild":
            # 完全野败：结构性不育，阈值固定，无旋钮
            a = 1.0
            scan = rng.random(N) < s_eff * a
            det = scan & (pop == 0)
            pop[det] = 1
            killed = int(det.sum())

        recent = killed

        # ---- 复制 ----
        p = fit / fit.sum()
        new = pop[rng.choice(N, N, p=p)].copy()
        mut = rng.random(N) < Q
        new[mut] = 0
        pop = new

        th[t] = 1.0 - pop.mean()
        aa[t] = a

    return th, aa


def metrics(th, aa):
    peaks = []
    for w in WAVES:
        seg = th[w:min(w + 60, CUT)]      # 窗口不得跨进断供期
        peaks.append(round(float(seg.max()), 4))
    recover = []
    for w in WAVES:
        seg = th[w:min(w + 60, CUT)]
        below = np.where(seg < 0.02)[0]
        recover.append(int(below[0]) if len(below) else 60)
    return {
        "peaks": peaks,
        "peak_first": peaks[0],
        "peak_last": peaks[-1],
        "peak_growth": round(peaks[-1] - peaks[0], 4),
        "recover": recover,
        "recover_last": recover[-1],
        "a_min": round(float(aa.min()), 4),
        "a_at_last_wave": round(float(aa[LAST_WAVE]), 4),
        "cut_peak": round(float(th[LAST_WAVE:].max()), 4),      # 无花粉时的代价
        "cut_mean": round(float(th[LAST_WAVE:].mean()), 4),
        "latency": int(next((i for i, v in enumerate(th[LAST_WAVE:]) if v > 0.5), 70)),
    }


def main():
    out = {}
    series = {}
    for st in STRATS:
        rows, ths = [], []
        for sd in range(SEEDS):
            th, aa = run(st, sd)
            rows.append(metrics(th, aa))
            ths.append(th)
        agg = {
            k: round(float(np.mean([r[k] for r in rows])), 4)
            for k in ["peak_first", "peak_last", "peak_growth", "recover_last",
                      "a_min", "a_at_last_wave", "cut_peak", "cut_mean", "latency"]
        }
        agg["peaks"] = [round(float(np.mean([r["peaks"][i] for r in rows])), 3)
                        for i in range(len(WAVES))]
        agg["recover"] = [round(float(np.mean([r["recover"][i] for r in rows])), 1)
                          for i in range(len(WAVES))]
        out[st] = agg
        series[st] = np.mean(ths, axis=0).tolist()
        print(f"{st:11s} 波峰 {agg['peaks']} | 恢复 {agg['recover']} | "
              f"a_min {agg['a_min']:.3f} | 断供潜伏 {agg['latency']}")

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "result218.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": out, "series": series,
                   "waves": WAVES, "cut": CUT, "last_wave": LAST_WAVE},
                  f, ensure_ascii=False, indent=2)
    print("\n已写 result218.json")


if __name__ == "__main__":
    main()

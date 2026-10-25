# -*- coding: utf-8 -*-
"""
实验 085c · 主动去看 vs 被动接收（开门次数精确匹配）
------------------------------------------------------------------
085b 对照失效：active 开门率 0.191 vs random 0.243 → 差异可被"看得更少"解释。

085c：
  · 先跑 active（在线规则：开门概率 ∝ 内部需求的历史分位），记录实际开门次数 n_A(s)
  · 再对同 seed 跑 random，开门次数【精确】= n_A(s)
  · 信息内容完全相同（同一个真实世界均值向量），次数完全相同
    → 唯一差异 = 开门时刻是否由内部需求决定
  · 配对（同 seed）+ bootstrap CI + 共同存活子集（防死亡筛选）
"""
import json, os, sys
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'core')); sys.path.insert(0, ROOT)
from core.life5 import Life5

STEPS = 600
SEEDS = list(range(16))
N = 8
WCH = [0, 1, 2]
OUT = os.path.join(ROOT, 'experiments', 'result_085c.json')
RAW = os.path.join(ROOT, 'evidence', 'raw_data', 'world_085b.json')

_w = json.load(open(RAW))
WV = np.array(_w['world'], float).mean(axis=0)
print(f"[世界] 真实采样点 {_w['n_views']} 个，均值向量 {np.round(WV,4)}")


def struct_skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def ch_cap(lf, ch):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(np.mean(c[ch]) / max(c.mean(), 1e-12))


def sim(seed, mask, amp):
    lf = Life5(N=N, seed=seed, ratio=0.45, sigma_in=0.10)
    needs, opens = [], []
    for t in range(STEPS):
        needs.append(float(np.mean(np.maximum(np.asarray(lf.H, float)[WCH], 0.0))))
        push = np.zeros(N)
        if t < len(mask) and mask[t]:
            push[WCH] = amp * WV
        lf.net_push = push
        opens.append(1 if (t < len(mask) and mask[t]) else 0)
        lf.step()
        if not lf.alive: break
    lf.needs = np.array(needs); lf.opens = np.array(opens)
    return lf


def run_active(seed, p, amp, rng):
    """在线：开门概率 ∝ 内部需求的历史分位"""
    lf = Life5(N=N, seed=seed, ratio=0.45, sigma_in=0.10)
    hist, mask = [], []
    a = 2.0 * p
    for t in range(STEPS):
        need = float(np.mean(np.maximum(np.asarray(lf.H, float)[WCH], 0.0)))
        q = 0.5 if not hist else (need - min(hist)) / max(max(hist) - min(hist), 1e-12)
        hist.append(need)
        o = rng.random() < float(np.clip(a * q, 0.0, 1.0))
        mask.append(o)
        push = np.zeros(N)
        if o: push[WCH] = amp * WV
        lf.net_push = push
        lf.step()
        if not lf.alive: break
    lf.needs = np.array(hist); lf.opens = np.array(mask, int)
    return lf, np.array(mask, bool)


def boot_ci(d, B=4000, seed=7):
    d = np.asarray(d, float)
    if len(d) < 2: return float('nan'), float('nan'), float('nan')
    r = np.random.default_rng(seed)
    bs = np.array([r.choice(d, len(d), replace=True).mean() for _ in range(B)])
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    print("=" * 66)
    print("实验 085c · 主动 vs 被动（次数精确匹配）")
    print("=" * 66)
    res = {'matched': [], 'grid': []}

    for amp in (0.005, 0.02):
        print(f"\n######## amp={amp} ########")
        for p in (0.25, 0.5, 0.75):
            A, R = {}, {}
            nA_list = []
            for s in SEEDS:
                lfA, mA = run_active(s, p, amp, np.random.default_rng(s * 977 + 13))
                nA = int(mA.sum())
                rng = np.random.default_rng(s * 977 + 13)
                mR = np.zeros(STEPS, bool)
                mR[rng.choice(STEPS, nA, replace=False)] = True     # 次数精确相同
                lfR = sim(s, mR, amp)
                A[s] = lfA; R[s] = lfR; nA_list.append(nA)
            common = [s for s in SEEDS if A[s].alive and R[s].alive]
            ds = [struct_skew(A[s]) - struct_skew(R[s]) for s in common]
            dc = [ch_cap(A[s], WCH) - ch_cap(R[s], WCH) for s in common]
            ms, l1, h1 = boot_ci(ds); mc, l2, h2 = boot_ci(dc)
            # 操纵检查
            ra = float(np.mean([np.corrcoef(A[s].opens[:len(A[s].needs)], A[s].needs)[0, 1]
                                for s in SEEDS if A[s].opens.std() > 0]))
            rr = float(np.mean([np.corrcoef(R[s].opens[:len(R[s].needs)], R[s].needs)[0, 1]
                                for s in SEEDS if R[s].opens.std() > 0]))
            row = dict(amp=amp, p=p, n_open=float(np.mean(nA_list)),
                       alive_A=int(sum(A[s].alive for s in SEEDS)),
                       alive_R=int(sum(R[s].alive for s in SEEDS)),
                       n_common=len(common),
                       skew_A=float(np.mean([struct_skew(A[s]) for s in common])) if common else float('nan'),
                       skew_R=float(np.mean([struct_skew(R[s]) for s in common])) if common else float('nan'),
                       d_skew=ms, ci_lo=l1, ci_hi=h1, d_chcap=mc, cc_lo=l2, cc_hi=h2,
                       r_active=ra, r_random=rr)
            res['matched'].append(row)
            flag = "★显著" if (l1 > 0 or h1 < 0) else "跨0"
            print(f"  p={p:<5} 开门次数={row['n_open']:.0f}/600 (A=R精确匹配)")
            print(f"        存活 A={row['alive_A']}/R={row['alive_R']} n_common={len(common)}")
            print(f"        操纵检查 r(开门,需求): active={ra:+.4f}  random={rr:+.4f}")
            print(f"        skew A={row['skew_A']:.4f} R={row['skew_R']:.4f} "
                  f"Δ={ms:+.5f} CI[{l1:+.5f},{h1:+.5f}] {flag}")
            print(f"        ΔWCH容量={mc:+.5f} CI[{l2:+.5f},{h2:+.5f}]")

    print("\n######## 总量维度：接收越多越被冲垮？ ########")
    for amp in (0.0, 0.005, 0.01, 0.02, 0.04, 0.08):
        for p in (0.25, 0.5, 1.0):
            nT = int(round(p * STEPS))
            al, sk = [], []
            for s in SEEDS:
                rng = np.random.default_rng(s * 977 + 13)
                m = np.zeros(STEPS, bool)
                if amp > 0: m[rng.choice(STEPS, nT, replace=False)] = True
                lf = sim(s, m, amp)
                if lf.alive: al.append(s); sk.append(struct_skew(lf))
            row = dict(amp=amp, p=p, alive=len(al), n=len(SEEDS),
                       skew=float(np.mean(sk)) if sk else float('nan'))
            res['grid'].append(row)
            print(f"  amp={amp:<6} p={p:<5} 存活 {len(al):>2}/{len(SEEDS)} 偏度 {row['skew']:.4f}")

    json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"\n[OK] {OUT}")


if __name__ == '__main__':
    main()

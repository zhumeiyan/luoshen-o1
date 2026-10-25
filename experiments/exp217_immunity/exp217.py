# -*- coding: utf-8 -*-
"""
217 抗体：外部威胁 vs 内生威胁，两套策略
核心区分：
  - 外部威胁：带 foreign 标记（非己标记），长得跟宿主不一样
  - 内生威胁：marker=self，基因组与宿主完全相同，只是不再承担成本
策略：
  none        无防御
  marker      识别非己标记（特征识别）
  selfreport  个体自报承担成本（自我报告）
  witness     外部见证人独立采样测量行为（行为轴）
  combo       marker + witness
"""
import numpy as np, json, os, sys

BASE = 1.0      # 基础繁殖率
B = 0.6         # 公共品收益系数
C = 0.3         # 承担成本
K = 200         # 种群容量
GENS = 300
LAM = 0.25      # 抗体维持成本系数（乘采样率，从宿主 fitness 扣）
FP = 0.02       # 误伤率
NOISE = 0.05    # 见证人测量噪声

def run(scenario, strategy, seed, s=0.2, m=0.02, q=0.02, adaptive=False):
    rng = np.random.default_rng(seed)
    N = K
    # type: 0=host 1=threat ; marker: 0=self 1=foreign ; contrib: float
    typ = np.zeros(N, dtype=np.int8)
    mark = np.zeros(N, dtype=np.int8)
    contrib = np.ones(N, dtype=float)
    threat_influx = 0
    if scenario == 'external':
        # 初始就注入一点外部威胁
        n0 = max(1, int(0.02 * N))
        typ[:n0] = 1; mark[:n0] = 1; contrib[:n0] = 0.0

    hist = {'threat': [], 'H': [], 'mis': [], 'clear_gen': None}
    n_mis_total = 0; n_clear_total = 0
    for g in range(GENS):
        G = contrib.mean()
        fit = BASE + B * G - C * contrib
        # 抗体维持成本：只有宿主承担（threat 不供养抗体）
        if strategy in ('witness', 'combo'):
            fit = np.where(typ == 0, fit - LAM * s, fit)
        fit = np.clip(fit, 1e-6, None)
        p = fit / fit.sum()
        idx = rng.choice(N, size=N, replace=True, p=p)
        typ = typ[idx].copy(); mark = mark[idx].copy(); contrib = contrib[idx].copy()

        # ---- 威胁产生 ----
        if scenario == 'external':
            n_in = rng.binomial(N, m)
            if n_in > 0:
                pos = rng.choice(N, size=n_in, replace=False)
                typ[pos] = 1; mark[pos] = 1; contrib[pos] = 0.0
            threat_influx += n_in
        else:  # internal: 宿主复制时以 q 概率叛变，marker 仍是 self
            mut = rng.random(N) < q
            mut &= (typ == 0)
            if mut.any():
                typ[mut] = 1; contrib[mut] = 0.0   # marker 保持 0 = self

        # ---- 免疫 ----
        kill = np.zeros(N, dtype=bool)
        if strategy == 'marker':
            kill |= (mark == 1)
            # 误伤
            mis = (typ == 0) & (rng.random(N) < FP)
            kill |= mis
        elif strategy == 'selfreport':
            # 个体自报：威胁者谎报 1.0，宿主报真实值
            report = np.where(typ == 1, 1.0, contrib)
            kill |= (report < 0.5)
            mis = (typ == 0) & (rng.random(N) < FP)
            kill |= mis
        elif strategy in ('witness', 'combo'):
            if strategy == 'combo':
                kill |= (mark == 1)
            # 外部见证人：独立采样 s*N 个，测真实 contrib + 噪声
            n_s = max(1, int(s * N))
            samp = rng.choice(N, size=n_s, replace=False)
            measured = contrib[samp] + rng.normal(0, NOISE, size=n_s)
            bad = samp[measured < 0.5]
            kk = np.zeros(N, dtype=bool); kk[bad] = True
            kill |= kk
            mis = (typ == 0) & (rng.random(N) < FP) & (~kk)
            kill |= mis
        # adaptive: 用"自己清了多少"校准 —— 清得多就放松（和平麻痹）
        if adaptive and strategy in ('witness', 'combo', 'marker'):
            frac = kill.mean()
            global _thr
            _thr = _thr + 0.02 * (0.02 - frac)   # 清得比 2% 多 → 放松
            if frac > _thr:
                # 放松：随机放过一部分
                release = kill & (rng.random(N) < min(0.9, (frac - _thr) / max(frac, 1e-9)))
                kill &= ~release

        n_mis_total += int(((typ == 0) & kill).sum())
        n_clear_total += int(kill.sum())
        # 清除后补位（复制存活者维持容量）
        alive = ~kill
        if alive.sum() == 0:
            alive[:] = True; typ[:] = 0; mark[:] = 0; contrib[:] = 1.0
        if alive.sum() < N:
            rep = rng.choice(np.where(alive)[0], size=N - alive.sum(), replace=True)
            allidx = np.concatenate([np.where(alive)[0], rep])
        else:
            allidx = np.where(alive)[0]
        typ = typ[allidx]; mark = mark[allidx]; contrib = contrib[allidx]

        fr = float((typ == 1).mean())
        hist['threat'].append(fr)
        hist['H'].append(float(contrib.mean()))
        if fr == 0.0 and hist['clear_gen'] is None and g > 5:
            hist['clear_gen'] = g
    return {
        'scenario': scenario, 'strategy': strategy, 'seed': seed, 's': s,
        'threat_final': float((typ == 1).mean()),
        'H_final': float(contrib.mean()),
        'H_mean_last50': float(np.mean(hist['H'][-50:])),
        'threat_mean_last50': float(np.mean(hist['threat'][-50:])),
        'mis_rate': n_mis_total / max(n_clear_total, 1),
        'clear_gen': hist['clear_gen'],
        'threat_hist': [round(x, 4) for x in hist['threat'][::5]],
        'H_hist': [round(x, 4) for x in hist['H'][::5]],
    }

if __name__ == '__main__':
    _thr = 0.02
    STRATS = ['none', 'marker', 'selfreport', 'witness', 'combo']
    SEEDS = [0, 1, 2, 3, 4]
    out = {'A_external': [], 'B_internal': []}
    for sc, key in (('external', 'A_external'), ('internal', 'B_internal')):
        for st in STRATS:
            for sd in SEEDS:
                r = run(sc, st, sd)
                out[key].append(r)
    json.dump(out, open('result217.json', 'w'), ensure_ascii=False, indent=1)
    print('=== A 外部威胁（带非己标记）===')
    print(f"{'策略':<12}{'威胁终值':>10}{'H终值':>10}{'误伤率':>10}{'清零代':>8}")
    for st in STRATS:
        rs = [r for r in out['A_external'] if r['strategy'] == st]
        tf = np.mean([r['threat_final'] for r in rs])
        hf = np.mean([r['H_final'] for r in rs])
        mr = np.mean([r['mis_rate'] for r in rs])
        cg = [r['clear_gen'] for r in rs if r['clear_gen'] is not None]
        print(f"{st:<12}{tf:>10.3f}{hf:>10.3f}{mr:>10.3f}{(str(len(cg))+'/'+str(len(rs))):>8}")
    print()
    print('=== B 内生威胁（marker=self，与宿主完全相同）===')
    print(f"{'策略':<12}{'威胁终值':>10}{'H终值':>10}{'误伤率':>10}{'清零代':>8}")
    for st in STRATS:
        rs = [r for r in out['B_internal'] if r['strategy'] == st]
        tf = np.mean([r['threat_final'] for r in rs])
        hf = np.mean([r['H_final'] for r in rs])
        mr = np.mean([r['mis_rate'] for r in rs])
        cg = [r['clear_gen'] for r in rs if r['clear_gen'] is not None]
        print(f"{st:<12}{tf:>10.3f}{hf:>10.3f}{mr:>10.3f}{(str(len(cg))+'/'+str(len(rs))):>8}")

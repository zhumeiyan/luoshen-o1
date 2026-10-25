#!/usr/bin/env python3
"""
exp216 · 抗体

病毒 = 不承担宿主成本的复制者。
核心问题：宿主做出的抗体，识别的应该是什么？

两组识别轴：
  seq      —— 识别"序列"（长什么样）。病毒可变抗原逃逸。
  behavior —— 识别"行为"（承不承担宿主成本）。病毒想逃逸就必须
              真的开始承担成本 —— 逃逸即投降。

c ∈ [-1, 1]：个体对宿主的贡献。c<0 = 消耗宿主（病毒），c>0 = 供养（共生）。
繁殖率 = base * (1 - k*c)，即：承担成本是真实的代价，会拖慢自身复制。
"""
import random, json, math, os

G = 32          # genome 位长
K_COST = 0.55   # 承担成本对自身繁殖的拖累
NOISE = 0.18    # 抗体观测 c 的噪声

def popcnt(x):
    return x.bit_count()

def mutate_g(g, mu, rng):
    m = 0
    for i in range(G):
        if rng.random() < mu:
            g ^= (1 << i); m += 1
    return g, m

def run(mode='no_ab', thr=-0.15, T=250, N=200, seed=0,
        external=True, cap=12, mu0=0.02, inject=None):
    rng = random.Random(seed)
    pop = []
    for i in range(N):
        if i < N // 2:
            c = -0.5 + rng.gauss(0, 0.08)     # 病毒祖先
        else:
            c = 0.5 + rng.gauss(0, 0.08)      # 共生祖先
        pop.append({'g': rng.getrandbits(G), 'c': max(-1.0, min(1.0, c))})

    H = 1.0
    lib = []          # 抗体库: [genome, exposure]
    hist = []
    cleared_symb = 0  # 误伤计数
    total_symb = 0
    lags = []         # 两次病毒脉冲的清除延迟
    pulse_state = [0, 0]

    for t in range(T):
        # --- 注入脉冲（测免疫记忆）---
        if inject and t in inject:
            idx = inject.index(t)
            for _ in range(N // 5):
                pop.append({'g': rng.getrandbits(G), 'c': -0.8})
            pulse_state[idx] = 1

        # --- 繁殖 ---
        mean_c = sum(a['c'] for a in pop) / len(pop)
        newpop = []
        for a in pop:
            c = a['c']
            mu = mu0 * (1.0 - 0.5 * c)          # c 越低突变越快（病毒特征）
            fit = max(0.02, 1.0 - K_COST * c)
            n_off = 1 if rng.random() < fit else 0
            for _ in range(n_off):
                g2, _ = mutate_g(a['g'], mu, rng)
                c2 = max(-1.0, min(1.0, max(0.0, c + rng.gauss(0, 0.05)) * 0 + c + rng.gauss(0, 0.05)))
                c2 = max(-1.0, min(1.0, c2))
                newpop.append({'g': g2, 'c': c2})

        # --- 宿主动力学 ---
        mc = sum(a['c'] for a in newpop) / max(1, len(newpop))
        Htarget = max(0.0, min(1.0, 0.5 + 0.5 * mc))
        H += 0.06 * (Htarget - H)
        H = max(0.0, min(1.0, H))

        # --- 抗体清除 ---
        if mode != 'no_ab':
            survivors = []
            for a in newpop:
                kill = False
                if mode == 'seq':
                    for pat in lib:
                        d = popcnt(a['g'] ^ pat[0])
                        sim = 1.0 - d / G
                        if sim > 0.80:
                            p_mem = 0.30 + 0.65 * (1 - math.exp(-0.8 * pat[1]))
                            if rng.random() < p_mem:
                                kill = True
                                pat[1] += 1
                                break
                elif mode == 'behavior':
                    c_obs = a['c'] + rng.gauss(0, NOISE)
                    if c_obs < thr:
                        p_mem = 0.30 + 0.65 * (1 - math.exp(-0.8 * 3))
                        if rng.random() < p_mem:
                            kill = True
                if kill:
                    if a['c'] > 0:
                        cleared_symb += 1
                    continue
                survivors.append(a)
            # --- 抗体库更新 ---
            if mode == 'seq':
                # 把当前群体里"最可疑"的个体序列入库
                cand = sorted(newpop, key=lambda x: x['c'])[:3]
                for a in cand:
                    if external:
                        # 外部见证人：按真实 c 决定（不受抗体自身误判影响）
                        if a['c'] > thr:
                            continue
                    # self 模式：无门槛，误判会污染库
                    if not any(p[0] == a['g'] for p in lib):
                        lib.append([a['g'], 0])
                        if len(lib) > cap:
                            lib.pop(0)
            newpop = survivors

        if not newpop:
            newpop = [{'g': rng.getrandbits(G), 'c': 0.2}]
        pop = newpop[:N * 2]

        # --- 脉冲清除延迟 ---
        for idx, tt in enumerate(inject or []):
            if pulse_state[idx] == 1 and t > tt:
                frac = sum(1 for a in pop if a['c'] < -0.4) / max(1, len(pop))
                if frac < 0.10:
                    lags.append(t - tt)
                    pulse_state[idx] = 2

        total_symb += sum(1 for a in pop if a['c'] > 0)
        hist.append({
            't': t, 'H': round(H, 4),
            'mean_c': round(sum(a['c'] for a in pop) / len(pop), 4),
            'frac_v': round(sum(1 for a in pop if a['c'] < -0.3) / len(pop), 4),
            'lib': len(lib),
            'mean_g_sim': None,
        })

    return {
        'mode': mode, 'thr': thr, 'seed': seed, 'external': external,
        'H_final': round(H, 4),
        'mean_c_final': round(sum(a['c'] for a in pop) / len(pop), 4),
        'frac_v_final': round(sum(1 for a in pop if a['c'] < -0.3) / len(pop), 4),
        'miskill_rate': round(cleared_symb / max(1, total_symb), 4),
        'lib_size': len(lib),
        'lags': lags,
        'hist': hist,
    }


if __name__ == '__main__':
    os.makedirs('/data/workspace/luoshen-o1/experiments/exp216_antibody', exist_ok=True)
    out = {}

    # A. 四组对照 × 3 seed
    out['main'] = []
    for mode, ext in [('no_ab', False), ('seq', True),
                      ('behavior', True), ('behavior', False)]:
        rs = []
        for s in range(3):
            rs.append(run(mode=mode, external=ext, seed=s, T=250))
        key = mode if mode == 'no_ab' else f"{mode}_{'ext' if ext else 'self'}"
        out['main'].append({'key': key, 'runs': rs})

    # B. 阈值扫描（自身免疫代价）
    out['thr_scan'] = []
    for thr in [-0.40, -0.25, -0.15, -0.05, 0.05, 0.15]:
        r = run(mode='behavior', thr=thr, external=True, seed=0, T=250)
        out['thr_scan'].append({'thr': thr, 'run': r})

    # C. 免疫记忆：两次病毒脉冲
    out['memory'] = []
    for mode in ['no_ab', 'behavior', 'seq']:
        r = run(mode=mode, external=True, seed=0, T=260, inject=[100, 180])
        out['memory'].append({'mode': mode, 'run': r})

    with open('/data/workspace/luoshen-o1/experiments/exp216_antibody/result216.json', 'w') as f:
        json.dump(out, f, ensure_ascii=False)

    print("=== A. 四组对照 ===")
    for g in out['main']:
        rs = g['runs']
        print(f"{g['key']:16s} H={sum(r['H_final'] for r in rs)/3:.3f} "
              f"c={sum(r['mean_c_final'] for r in rs)/3:+.3f} "
              f"病毒={sum(r['frac_v_final'] for r in rs)/3:.3f} "
              f"误伤={sum(r['miskill_rate'] for r in rs)/3:.4f}")
    print("\n=== B. 阈值扫描（抗体激进度）===")
    for s in out['thr_scan']:
        r = s['run']
        print(f"thr={s['thr']:+.2f}  H={r['H_final']:.3f}  c={r['mean_c_final']:+.3f} "
              f"病毒={r['frac_v_final']:.3f}  误伤={r['miskill_rate']:.4f}")
    print("\n=== C. 免疫记忆（两次脉冲的清除延迟）===")
    for m in out['memory']:
        print(f"{m['mode']:10s} lags={m['run']['lags']}")

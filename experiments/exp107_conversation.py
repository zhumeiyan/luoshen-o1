"""★107 正常交流 —— 她真的来回说话

判据：
 0  尺子自检：同一句说两遍，韵律真值可复现（★105 教训）
 1  回应性信号是真的：真人真的回的那句，字面比随机回答更接得上上一句
 2  w（回应性权重）有内部峰
 3  pi（剪多窄）有内部峰
 4  g（话轮间隔）有内部峰
 5  硬依赖 w：打碎"上一句↔回应"的对应 → 峰塌
 6  硬依赖 w：回应性打分换成随机数 → 峰塌
 7  硬依赖 pi：测量变准（r=6）→ 峰往"别剪"移
 8  硬依赖 g：预测无误差（σ=0）→ 峰移到 0（边界）
 9  她能从瞎起点学会（w=0, pi=1, g=0）
10  held-out（没见过的真人上下文 + 低沉/高音两批对象）她赢随机、赢我填的
11  ★106 的账在完整对话里兑现：A=20（她★106学的）在低沉对象上崩，A=8 不崩
12  多轮不退化：命中率/韵律不逐轮塌
"""
import sys, json, os
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core import conversation as C
from core import entrainment as EN
from core.speak_text import speak_text
import experiments.exp104_shefinds as E
from scipy.io import wavfile

ROOT = '/data/workspace/luoshen-o1'
OUT = f'{ROOT}/data/exp107_conversation.json'
SEEDS = [11, 22, 33]
TURNS = 4
CAND_N = 10
REP = 2

RES = {}
def rec(k, v):
    RES[k] = v
    print(f'  {k}: {v}')


def ruler():
    print('\n【0】尺子自检：同一句说两遍，韵律真值可复现')
    pairs, all_a = C.load_pairs(limit=20000, seed=0)
    texts = [a for _, a in pairs[:40]]
    P = C._params_for(C.TARGET['f0'], 165.0)
    h1 = np.array([C.prosody(t, P, np.random.default_rng(1000 + i))[0]
                   for i, t in enumerate(texts)])
    h2 = np.array([C.prosody(t, P, np.random.default_rng(5000 + i))[0]
                   for i, t in enumerate(texts)])
    r = float(np.corrcoef(h1, h2)[0, 1])
    rel = 2 * r / (1 + r)
    rec('ruler_r', round(r, 4))
    rec('ruler_reliability', round(rel, 4))
    return pairs, all_a


def signal(pairs, all_a):
    print('\n【1】回应性信号：真人真的回的那句 vs 随便一句，谁更接得上上一句')
    rng = np.random.default_rng(7)
    d = []
    for q, a in pairs[:300]:
        dist = all_a[int(rng.integers(0, len(all_a)))]
        d.append(C.rel_proxy(a, q) - C.rel_proxy(dist, q))
    d = np.array(d)
    m, se = float(d.mean()), float(d.std(ddof=1) / np.sqrt(len(d)))
    rec('signal_gold_minus_random', round(m, 4))
    rec('signal_SE', round(se, 4))
    rec('signal_t', round(m / max(se, 1e-9), 2))
    return m


def scan(name, values, kw, pairs, **fix):
    out = {}
    for v in values:
        kw2 = dict(kw); kw2[name] = v
        rep = kw2.pop('r', REP)
        out[v] = C.score(pairs=pairs, seeds=SEEDS, turns=TURNS,
                         cands_n=CAND_N, r=rep, **{**kw2, **fix})
    best = max(out, key=out.get)
    span = max(out.values()) - min(out.values())
    print(f'  {name}: ' + '  '.join(f'{k}:{out[k]:+.4f}' for k in values)
          + f'  → 峰 {best}  跨度 {span:.4f}')
    return dict(values={str(k): out[k] for k in values}, best=best, span=span)


def main():
    pairs, all_a = ruler()
    TRAIN = pairs[:600]
    HELD = pairs[600:1400]
    print(f'\n★ 训练对话 {len(TRAIN)} 组 / held-out {len(HELD)} 组（全没见过）')
    W = C.learn_hum_model(TRAIN, n=150)
    print('★ 她已有的便宜模型（★104/105 学的）:', np.round(W, 3))

    base = dict(w=0.4, pi=0.3, g=0.15)

    print('\n【2】w —— 回应性权重（0=只管说得漂亮，1=只管接得上）')
    RES['scan_w'] = scan('w', [0.0, 0.3, 0.6, 1.0], dict(base), TRAIN)
    bw = RES['scan_w']['best']

    print('\n【3】pi —— 剪多窄（预算只够真说几句）')
    RES['scan_pi'] = scan('pi', [0.2, 0.3, 0.5, 1.0],
                          {**base, 'w': bw}, TRAIN)
    bp = RES['scan_pi']['best']

    print('\n【4】g —— 话轮间隔（等多久开口；0=抢话，0.4=冷场）')
    RES['scan_g'] = scan('g', [0.0, 0.10, 0.20, 0.35],
                         {**base, 'w': bw, 'pi': bp}, TRAIN)
    bg = RES['scan_g']['best']
    BEST = dict(w=bw, pi=bp, g=bg)
    print('  ★ 三个旋钮的峰:', BEST)

    print('\n【5】硬依赖 w：打碎"上一句↔回应"的对应（shuffle_ctx）')
    RES['dep_w_shuffle'] = scan('w', [0.0, 0.3, 0.6, 1.0],
                                {**BEST, 'shuffle_ctx': True}, TRAIN)
    print('  → 正常跨度 %.4f / 打碎后 %.4f'
          % (RES['scan_w']['span'], RES['dep_w_shuffle']['span']))

    print('\n【6】硬依赖 w：回应性打分换成随机数（rand_rel）')
    RES['dep_w_rand'] = scan('w', [0.0, 0.3, 0.6, 1.0],
                             {**BEST, 'rand_rel': True}, TRAIN)
    print('  → 正常跨度 %.4f / 随机后 %.4f'
          % (RES['scan_w']['span'], RES['dep_w_rand']['span']))

    print('\n【7】硬依赖 pi：测量变准（r=4，几乎没抖动）')
    RES['dep_pi_r4'] = scan('pi', [0.3, 0.5, 1.0],
                            {**BEST, 'r': 4}, TRAIN)
    print('  → r=2 峰 %s / r=4 峰 %s（测量准了就该少剪）'
          % (bp, RES['dep_pi_r4']['best']))

    print('\n【8】硬依赖 g：预测无误差（σ=0，永远不会抢话）')
    old = C.SIGMA_PRED
    C.SIGMA_PRED = 0.0
    RES['dep_g_sigma0'] = scan('g', [0.0, 0.10, 0.20, 0.35],
                               BEST, TRAIN)
    C.SIGMA_PRED = old
    print('  → 正常峰 %s / σ=0 峰 %s（没有抢话风险，就不该等）'
          % (bg, RES['dep_g_sigma0']['best']))

    print('\n【9】她从瞎起点学（w=0 只看漂不漂亮，pi=1 不剪，g=0 不等）')
    cur = dict(w=0.0, pi=1.0, g=0.0)
    start = C.score(pairs=TRAIN, seeds=SEEDS, turns=TURNS, cands_n=CAND_N,
                    r=REP, **cur)
    print(f'  瞎起点 {start:+.4f}')
    grid = dict(w=[0.0, 0.3, 0.6, 1.0],
                pi=[0.2, 0.3, 0.5, 1.0],
                g=[0.0, 0.10, 0.20, 0.35])
    for pas in range(2):
        for k in ('w', 'pi', 'g'):
            vals = {}
            for v in grid[k]:
                vals[v] = C.score(pairs=TRAIN, seeds=SEEDS, turns=TURNS,
                                  cands_n=CAND_N, r=REP, **{**cur, k: v})
            cur[k] = max(vals, key=vals.get)
        sc = C.score(pairs=TRAIN, seeds=SEEDS, turns=TURNS, cands_n=CAND_N,
                     r=REP, **cur)
        print(f'  第{pas+1}轮坐标下降 → {cur}  {sc:+.4f}')
    learned = dict(cur)
    RES['learned'] = learned
    RES['blind_start'] = start
    RES['learned_score'] = sc
    print(f'  ★ 改善 {RES["learned_score"]-start:+.4f}')

    print('\n【10】held-out：没见过的真人上下文 + 两批没见过的对象')
    low = [float(f) for f in C.TRUE_F0S if f < 179]
    high = [float(f) for f in C.TRUE_F0S if f >= 179]
    print(f'  低沉组 {len(low)} 人 ({min(low):.0f}~{max(low):.0f}Hz) / '
          f'高音组 {len(high)} 人 ({min(high):.0f}~{max(high):.0f}Hz)')
    RES['held'] = {}
    for nm, pool in [('训练池(原对象)', None), ('低沉组', low), ('高音组', high)]:
        mine = dict(w=0.5, pi=1.0, g=0.25)
        hers = C.score(pairs=HELD, seeds=SEEDS, turns=TURNS, cands_n=CAND_N,
                       r=REP, pool=pool, **learned)
        mine_s = C.score(pairs=HELD, seeds=SEEDS, turns=TURNS, cands_n=CAND_N,
                         r=REP, pool=pool, **mine)
        rnd_s = C.score(pairs=HELD, seeds=SEEDS, turns=TURNS, cands_n=CAND_N,
                        r=REP, pool=pool, w=0.0, pi=1.0, g=0.0)
        RES['held'][nm] = dict(她=hers, 我填的=mine_s, 随机=rnd_s)
        print(f'  {nm:<14} 她 {hers:+.4f} | 我填的 {mine_s:+.4f} | 随机 {rnd_s:+.4f}')

    print('\n【11】★106 的账在完整对话里兑现：A=8（稳健）vs A=20（她★106学的）')
    RES['A_check'] = {}
    for nm, pool in [('低沉组', low), ('高音组', high)]:
        a8 = C.score(pairs=HELD, seeds=SEEDS, turns=TURNS, cands_n=CAND_N,
                     r=REP, pool=pool, A=8.0, **learned)
        a20 = C.score(pairs=HELD, seeds=SEEDS, turns=TURNS, cands_n=CAND_N,
                      r=REP, pool=pool, A=20.0, **learned)
        RES['A_check'][nm] = dict(A8=a8, A20=a20)
        print(f'  {nm}: A=8 {a8:+.4f} | A=20 {a20:+.4f}  → 差 {a8-a20:+.4f}')

    print('\n【12】多轮不退化 + 她真的说的那一段对话')
    rng = np.random.default_rng(2026)
    partner = EN.make_partner(rng, None)
    idx = rng.choice(len(HELD), TURNS, replace=False)
    script = [HELD[int(i)] for i in idx]
    _, recs, wavs = C.converse(pairs=script, partner=partner, rng=rng,
                               turns=TURNS, W=W,
                               all_a=[a for _, a in HELD],
                               r=REP, cands_n=CAND_N, **learned)
    hits = [r['hit'] for r in recs]
    pros = [r['pro'] for r in recs]
    gaps = [r['gap'] for r in recs]
    rec('multi_hit_rate', round(float(np.mean(hits)), 3))
    rec('multi_prosody_first_half', round(float(np.mean(pros[:2])), 4))
    rec('multi_prosody_second_half', round(float(np.mean(pros[2:])), 4))
    rec('multi_gap_mean_ms', round(float(np.mean(gaps)) * 1000, 1))
    rec('multi_interrupt', int(sum(1 for x in gaps if x < 0)))
    for i, r in enumerate(recs):
        print(f'   轮{i+1} 对方:"{r["ctx"][:24]}" → 她:"{r["chosen"]}"'
              f'  (接上真人回的 {r["rel"]:.2f} 韵律{r["pro"]:+.3f} '
              f'间隔{r["gap"]*1000:.0f}ms{" ⚠抢话" if r["gap"]<0 else ""})')

    segs = []
    for i, (r, wv) in enumerate(zip(recs, wavs)):
        hp = C._params_for(partner['f0'], 165.0)
        hw, _ = speak_text(r['ctx'], hp, np.random.default_rng(900 + i))
        segs += [hw, np.zeros(int(max(0.0, r['gap']) * C.SR)), wv,
                 np.zeros(int(0.35 * C.SR))]
    allx = np.concatenate(segs)
    allx = allx / max(np.abs(allx).max(), 1e-9) * 0.85
    wav = f'{ROOT}/data/her_voice/she_conversation_107.wav'
    wavfile.write(wav, C.SR, (allx * 32767).astype(np.int16))
    rec('audio', wav)

    json.dump(RES, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
    print(f'\n★ 写盘 {OUT}')


if __name__ == '__main__':
    main()

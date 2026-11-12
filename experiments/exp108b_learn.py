"""★108b 她从瞎起点学 + 真的开口说（换领域、真发声）"""
import sys, json, os
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core import dialogue108 as D
from core import conversation as C
from core.speak_text import speak_text
from scipy.io import wavfile

ROOT = '/data/workspace/luoshen-o1'
OUT = f'{ROOT}/data/exp108b_learn.json'
RES = {}
DG = [0.0, 0.066, 0.15, 0.18, 0.25, 0.5, 1.0]
AG = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]


def rec(k, v):
    RES[k] = v
    print(f'  {k}: {v}')


def learn(Btr, Bva):
    """坐标下降，公共随机数，训练/验证分开（★82 教训）"""
    d, a = 0.0, 0.0                      # 瞎起点：完全不接 + 不看话题
    hist = [(d, a, D.hit_rate(d, 1, a, Btr))]
    for _ in range(4):
        for grid, name in ((DG, 'd'), (AG, 'a')):
            sc = [(v, D.hit_rate(d if name == 'a' else v, 1,
                                 a if name == 'd' else v, Btr)) for v in grid]
            best = max(sc, key=lambda x: x[1])[0]
            if name == 'd':
                d = best
            else:
                a = best
        hist.append((d, a, D.hit_rate(d, 1, a, Btr)))
    return dict(d=d, a=a), hist


def main():
    items, X, sents = D.build('film')
    # 训练 / 验证 / 测试 三批（★82）
    Btr = D.make_batch(items[:9000], X, n=None, seed=1, n_cand=10)
    Bva = D.make_batch(items[9000:14000], X, n=None, seed=2, n_cand=10)
    Bte = D.make_batch(items[14000:], X, n=None, seed=3, n_cand=10)

    print('★ 她从瞎起点学（d=0 完全不接，a=0 不看话题）')
    got, hist = learn(Btr, Bva)
    for h in hist:
        print(f'   d={h[0]:.3f} a={h[1]:.2f}  训练命中 {h[2]:.4f}')
    rec('learned', dict(d=got['d'], a=got['a']))
    rec('blind_start_hit', round(D.hit_rate(0.0, 1, 0.0, Bte), 4))
    rec('learned_hit_test', round(D.hit_rate(got['d'], 1, got['a'], Bte), 4))

    print('\n★ 完整一轮：挑完之后真的说出来（含韵律 + 话轮）')
    P = dict(f0_base=182.0, f0_variation=0.35, f0_decl=0.10,
             tone_depth=0.55, jitter=0.015)
    it2, X2, s2 = D.build('travel')        # 完全没见过的领域
    B2 = D.make_batch(it2, X2, n=40, seed=5, n_cand=10)
    rows, wavs, pros = [], [], []
    rng = np.random.default_rng(9)
    for si, it in enumerate(B2['sub'][:6]):
        for d, a, tag in [(1.0, 0.0, '复读派'), (got['d'], got['a'], '她')]:
            s = D.pick(d, 1, a, B2)
            b = int(np.argmax(s[si]))
            chosen = s2[B2['C'][si][b]]
            gold = s2[it['gold']]
            prev = s2[it['prev']]
            pr, w = C.prosody(chosen, P, np.random.default_rng(100 + si),
                              syl_dur=0.20, repeats=1)
            rows.append(dict(tag=tag, prev=prev, chosen=chosen, gold=gold,
                             pros=round(pr, 3),
                             hit=1.0 if chosen == gold else 0.0,
                             sp=round(float(B2['SP'][si][b]), 3)))
            if tag == '她':
                wavs.append(w)
                pros.append(pr)
    for r in rows:
        print(f"   [{r['tag']}] 对方:{r['prev'][:22]}")
        print(f"        她:{r['chosen'][:22]}  真人:{r['gold'][:22]}"
              f"  韵律{r['pros']:+.3f} 接话{r['sp']}")
    rec('her_avg_pros', round(float(np.mean(pros)), 4))
    rec('her_hit', round(float(np.mean([r['hit'] for r in rows if r['tag'] == '她'])), 4))
    rec('her_prev_sim', round(float(np.mean([r['sp'] for r in rows if r['tag'] == '她'])), 4))
    rec('dup_prev_sim', round(float(np.mean([r['sp'] for r in rows if r['tag'] == '复读派'])), 4))

    w = np.concatenate([np.asarray(x, dtype=np.float64) for x in wavs])
    w = w / max(1e-9, np.abs(w).max()) * 0.85
    p = f'{ROOT}/data/her_voice/she_talks_108.wav'
    wavfile.write(p, 16000, (w * 32767).astype(np.int16))
    rec('audio', p)
    print(f'\n→ 音频 {p}  {len(w)/16000:.1f}s')
    json.dump(RES, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f'→ {OUT}')


if __name__ == '__main__':
    main()

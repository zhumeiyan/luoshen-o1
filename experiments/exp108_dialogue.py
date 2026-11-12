"""★108 真多轮交流 —— 接话不是复读

语料：thu-coai/KdConv（清华）1200 段真人多轮对话 × 3 领域，平均 24 轮。
★107 用的是 PTT（标题↔推文），那里「跟上一句字面对接」有效；
真对话里真人回应跟上一句的字面重叠中位数只有 0.03 ——
字面最像的那个候选，恰恰是把对方的话原样说回去。

判据：
 0  尺子自检：公共随机数；韵律可复现
 1  真值：真人回应↔上一句 = 0.066（中位 0.030）；完全复读 = 1.0
 2  d（接多少刚刚好）有内部峰
 3  a（话题权重）有内部峰
 4  硬依赖 d：去掉复读诱饵 → 峰塌到 0
 5  硬依赖 a：打碎话题历史（换成别对话的句子）→ 峰塌
 6  她从瞎起点学（d=0 完全不接，a=0）
 7  held-out：换领域（music / travel）她赢随机、赢我填的、赢「真人值」
 8  复读诊断：d=1 时她选的是不是对方原话
 9  真的说出来 + 话轮，产出音频
"""
import sys, json, os
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core import dialogue108 as D
from core import conversation as C
from core import entrainment as EN
from core.speak_text import speak_text
from scipy.io import wavfile

ROOT = '/data/workspace/luoshen-o1'
OUT = f'{ROOT}/data/exp108_dialogue.json'
RES = {}
TURNS = 5
NCAND = 10


def rec(k, v):
    RES[k] = v
    print(f'  {k}: {v}')


# ─────────────────────────────────────────────
def ruler(X, sents, P):
    print('\n【0】尺子自检')
    a = [C.prosody(s, P, np.random.default_rng(1000 + i))[0]
         for i, s in enumerate(sents[100:130])]
    b = [C.prosody(s, P, np.random.default_rng(5000 + i))[0]
         for i, s in enumerate(sents[100:130])]
    r = float(np.corrcoef(a, b)[0, 1])
    rec('ruler_r', round(r, 4))
    rec('ruler_reliability', round(2 * r / (1 + r), 4))


def truth_gt(items, X):
    g = [D.sim(X, it['gold'], it['prev']) for it in items[:1500]]
    rec('gold_prev_mean', round(float(np.mean(g)), 4))
    rec('gold_prev_median', round(float(np.median(g)), 4))
    return float(np.mean(g))


def scan(name, vals, fn):
    out = {v: fn(v) for v in vals}
    best = max(out, key=out.get)
    span = max(out.values()) - min(out.values())
    print(f'  {name}: ' + '  '.join(f'{k}:{out[k]:+.4f}' for k in vals)
          + f'  → 峰 {best}  跨度 {span:.4f}')
    return dict(values={str(k): out[k] for k in vals}, best=best, span=span)


def main():
    print('★ 语料：KdConv 真多轮对话（清华）')
    items, X, sents = D.build('film')
    print(f'   film 轮数 {len(items)}  句子 {X.shape[0]}')
    P = dict(f0_base=182.0, f0_variation=0.35, f0_decl=0.10,
             tone_depth=0.55, jitter=0.015)
    ruler(X, sents, P)

    print('\n【1】真值：真人回应跟「上一句」到底有多像')
    GT = truth_gt(items, X)
    print('   （完全复读对方 = 1.0）')

    B = D.make_batch(items, X, n=1000, seed=0, n_cand=NCAND)
    Bn = D.make_batch(items, X, n=1000, seed=0, n_cand=NCAND, n_decoy=0)
    # 打碎话题：把历史换成别的对话的句子
    rng = np.random.default_rng(3)
    shuf = [dict(prev=it['prev'],
                 hist=[int(rng.integers(0, X.shape[0])) for _ in it['hist']],
                 gold=it['gold']) for it in B['sub']]
    Bs = D.make_batch(shuf, X, n=None, seed=0, n_cand=NCAND)
    Bs['sub'] = shuf

    print('\n【2】d —— 接多少刚刚好（0=完全不接，1=完全复读）')
    RES['scan_d'] = scan('d', [0.0, 0.066, 0.15, 0.18, 0.25, 0.5, 1.0],
                         lambda d: D.hit_rate(d, 1, 1.0, B))
    bd = RES['scan_d']['best']

    print('\n【3】a —— 话题权重（0=只看接不接，越大越看话题）')
    RES['scan_a'] = scan('a', [0.0, 0.25, 0.5, 1.0, 2.0, 4.0],
                         lambda a: D.hit_rate(bd, 1, a, B))
    ba = RES['scan_a']['best']
    BEST = dict(d=bd, a=ba)
    print('  ★ 她要学的:', BEST)

    print('\n【4】硬依赖 d：去掉复读诱饵（候选里没有跟对方很像的句子）')
    RES['dep_d_nodecoy'] = scan('d', [0.0, 0.066, 0.15, 0.18, 0.25, 0.5, 1.0],
                                lambda d: D.hit_rate(d, 1, ba, Bn))
    print('  → 有诱饵跨度 %.4f / 无诱饵 %.4f'
          % (RES['scan_d']['span'], RES['dep_d_nodecoy']['span']))

    print('\n【5】硬依赖 a：打碎话题历史（换成别对话的句子）')
    RES['dep_a_shuffle'] = scan('a', [0.0, 0.25, 0.5, 1.0, 2.0, 4.0],
                                lambda a: D.hit_rate(bd, 1, a, Bs))
    print('  → 正常跨度 %.4f / 打碎后 %.4f'
          % (RES['scan_a']['span'], RES['dep_a_shuffle']['span']))

    print('\n【6】复读诊断：d=1 时她选的是不是对方的原话')
    dup = {}
    for d in [0.0, 0.18, 1.0]:
        s = D.pick(d, 1, ba, B)
        b = np.argmax(s, axis=1)
        dup[d] = round(float(B['SP'][np.arange(len(b)), b].mean()), 4)
    rec('chosen_prev_sim', dup)
    print(f'   ★ 真人回应↔上一句 = {GT:.4f}')

    print('\n【7】held-out：换领域（她只在 film 上学过）')
    held = {}
    for dom in ['music', 'travel']:
        it2, X2, s2 = D.build(dom)
        B2 = D.make_batch(it2, X2, n=1000, seed=7, n_cand=NCAND)
        rng2 = np.random.default_rng(11)
        sc_random = float(np.mean([
            (np.argmax(rng2.random(B2['C'].shape[1])) == 0) for _ in range(len(B2['sub']))]))
        held[dom] = {
            '她': round(D.hit_rate(BEST['d'], 1, BEST['a'], B2), 4),
            '我填的(全接d=1,a=0)': round(D.hit_rate(1.0, 1, 0.0, B2), 4),
            '真人值(d=0.066)': round(D.hit_rate(0.066, 1, 1.0, B2), 4),
            '完全不接(d=0)': round(D.hit_rate(0.0, 1, 1.0, B2), 4),
            '随机': round(sc_random, 4),
        }
        print(f'   {dom}: {held[dom]}')
    rec('held', held)
    rec('learned', BEST)
    json.dump(RES, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f'\n→ {OUT}')


if __name__ == '__main__':
    main()

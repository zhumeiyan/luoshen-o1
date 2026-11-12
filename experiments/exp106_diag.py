"""★106 诊断：为什么 A 的峰跑到 40（边界），而文献说最优 ≈4 Hz"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1')
import core.entrainment as EN
import experiments.exp104_shefinds as E
from core.speak_text import speak_text, text_to_syllables

ROOT = '/data/workspace/luoshen-o1'
T = json.load(open(f'{ROOT}/data/exp105b_pick.json'))
TEXTS = T['said'][:6]
_PER = json.load(open(f'{ROOT}/data/exp103_heard.json'))['per_file']
F0 = np.array([p['f0med'] for p in _PER])


def parts(A, lam=0.5, n=4, seeds=None, pool=None, turns=12, **kw):
    seeds = seeds or [int(np.random.default_rng(7).integers(0, 10**6)) for _ in range(10)]
    acc = dict(conv=[], coord=[], sync=[], rt=[], intel=[], jit=[], jitf0=[], tot=[])
    for sd in seeds:
        rng = np.random.default_rng(sd)
        p = EN.make_partner(rng, pool)
        hist, hf, hw, of, ow = [], [], [], [], []
        for t in range(turns):
            of.append(p['f0'] + p['drift']); ow.append(p['wpm'])
            hist.append(EN.observe(p, rng))
            e = EN.estimate(hist, n)
            gap = e['f0'] - EN.SELF_F0
            move = np.sign(gap) * min(A, abs(gap))
            dev = hist[-1]['f0'] - e['f0']
            tgt = EN.SELF_F0_PARAM + move + lam * dev
            tw = float(np.clip(EN.SELF_WPM + 0.8 * (e['wpm'] - EN.SELF_WPM), 90, 340))
            h = EN.her_turn(TEXTS[t % len(TEXTS)], tgt, tw, rng)
            hf.append(h['f0']); hw.append(h['wpm'])
            p['drift'] += rng.normal(0, 6.0)
        hf, hw, of, ow = map(np.array, (hf, hw, of, ow))
        conv = (hf.mean() - EN.SELF_F0) * np.sign(of.mean() - EN.SELF_F0)
        acc['conv'].append(conv)
        acc['coord'].append(np.exp(-((conv - EN.CONV_TARGET) / EN.CONV_SIGMA) ** 2))
        ok = hf.std() > 1e-9 and of.std() > 1e-9
        acc['sync'].append(float(np.corrcoef(hf, of)[0, 1]) if ok else 0.0)
        acc['rt'].append(abs(hw.mean() - ow.mean()) / EN.S_RT)
        acc['intel'].append(float(np.mean([(max(0.0, w - 250) / 110) ** 2 for w in hw])))
        acc['jit'].append(float(np.mean(np.abs(np.diff(hw)))) / EN.JIT_SCALE)
        acc['jitf0'].append(float(np.mean(np.abs(np.diff(hf)))) / EN.JIT_F0)
        acc['tot'].append(acc['coord'][-1] + acc['sync'][-1] - acc['rt'][-1]
                          - acc['intel'][-1] - acc['jit'][-1] - acc['jitf0'][-1])
    return {k: float(np.mean(v)) for k, v in acc.items()}


if __name__ == '__main__':
    print(f'她自己的 F0 {EN.SELF_F0}；真人对象 F0 {F0.min():.0f}~{F0.max():.0f}'
          f'  中位 {np.median(F0):.0f}')
    print(f'★ 她与对象的音高差 |gap| 中位 {np.median(np.abs(F0-EN.SELF_F0)):.1f} Hz'
          f' 最大 {np.abs(F0-EN.SELF_F0).max():.1f} Hz')
    print(f'★ 文献要的顺应量只有 {EN.CONV_TARGET:.0f} Hz\n')
    print(' A    conv    coord   sync    rt     intel  jit   jitf0   tot')
    for A in [0, 2, 4, 8, 20, 40]:
        r = parts(A)
        print(f'{A:3d}  {r["conv"]:+6.1f}  {r["coord"]:.3f}  {r["sync"]:+.3f}  '
              f'{r["rt"]:.3f}  {r["intel"]:.3f} {r["jit"]:.3f} {r["jitf0"]:.3f}  {r["tot"]:+.3f}')

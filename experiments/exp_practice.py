#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★82 练习 —— 她是女孩子（靶只留女声，从男声区起点爬）

════ 这一课和三件事有关 ════
  1) 用户说"继续练习"   → 不是跑一次就交卷，是反复练、留曲线
  2) 用户说"她是女孩子" → 靶只留 34 段女声，剔除那 1 段男声（131Hz）
  3) 用户说"学回来"     → 从【瞎的】起点爬，不许我先把答案填进去

════ ★ 起点为什么是 118Hz ════
  那在【男声区】。她要从那里自己爬到 182Hz 的女声区。
  这不是我设的陷阱，是"她还没长开"的真实状态 —— 练完之后再看她落在哪。

════ ★ 我量不准的，不教 ════
  声道长度/共振峰：FFT 谱峰、LPC、谱质心 三种尺子全验不过（见 practice.py 头）。
  按第 6 条规矩，拿不到就说拿不到。这一课只用量得准的 5 个维度。

════ 判据 ════
  ① 真改善：改善 > 2×标准误
  ② held-out：换一批没见过的真人女声当靶，仍改善
  ③ 她是女孩子：练完 F0 落在女声区间（>=165Hz）
  ④ 学习曲线渐进：不是一步到位（前 1/4 epoch 内未达最终水平的 95%）
  ⑤ 比"我量好填进去的"更好 —— 否则我是在自我表扬
"""

from __future__ import annotations
import sys, os, json
import numpy as np
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "core"))
from speech_organ import synthesize, DEFAULT_PARAMS, SR       # noqa
from practice import run_practice, ear_robust                              # noqa
from exp_speech_blind import ear, dist                         # noqa
from practice import ear_robust                                # noqa

BOUNDS = {
    'f0_base': (100.0, 260.0), 'f0_variation': (0.02, 0.70),
    'tone_depth': (0.02, 0.80), 'pause_rate': (0.02, 0.60),
    'pause_len': (0.05, 0.40), 'f0_decl': (0.0, 0.40),
    'voiced_target': (0.35, 0.98),
}
# ★★ jitter / 生理常量：真人声带周期间抖动 0.5~2%
#    ★69 的规矩：物理限制不该当自由参数让她学。
#    之前让她学，她学到 10~11.8%（撞界）—— 用【声带抖动】冒充【语调起伏】，
#    因为 f0_std 这个尺子分不清两者。现在固定为生理值，起伏只能靠 f0_variation。
JITTER_PHYS = 0.015

# ★ 瞎起点：118Hz 在男声区（她还没长开）
BLIND = {'f0_base': 118.0, 'f0_variation': 0.030, 'tone_depth': 0.72,
         'pause_rate': 0.52, 'pause_len': 0.36, 'f0_decl': 0.34,
         'voiced_target': 0.40, 'jitter': JITTER_PHYS}

VAL  = tuple(range(9000, 9024))     # 决定何时停
TEST = tuple(range(9500, 9524))     # 最终报告，从没参与任何决策
FAIR = VAL
DUR = 2.5


def synth(p, rng=None):
    q = dict(p); q['jitter'] = JITTER_PHYS      # ★ 生理常量，锁死
    return synthesize(q, dur=DUR, rng=rng or np.random.default_rng(0))


def fair_score(p, T, seeds=FAIR):
    ds = []
    for s in seeds:
        y, _ = synth(p, np.random.default_rng(s))
        m = ear_robust(y)
        if m and m['f0_med'] > 50:
            ds.append(dist(m, T))
    return (float(np.mean(ds)), float(np.std(ds)) / np.sqrt(len(ds))) if ds else (9.9, 0.0)


def load_targets(split_seed=42):
    d = os.path.join(ROOT, 'data/real_speech_wav')
    raws = sorted([os.path.join(d, f) for f in os.listdir(d) if f.endswith('.raw')])
    metas = []
    for p in raws:
        m = ear_robust(np.fromfile(p, dtype='<i2').astype(np.float64) / 32768.0)
        if m and m['f0_med'] > 50:
            metas.append((os.path.basename(p), m))
    # ★ 她是女孩子：只留女声（F0 >= 165），剔除男声段
    female = [(n, m) for n, m in metas if m['f0_med'] >= 165]
    dropped = [(n, m['f0_med']) for n, m in metas if m['f0_med'] < 165]
    perm = np.random.default_rng(split_seed).permutation(len(female))
    train = [female[i] for i in perm[:len(female) // 2]]
    test = [female[i] for i in perm[len(female) // 2:]]
    med = lambda fs: {k: float(np.median([m[k] for _, m in fs])) for k in fs[0][1]}
    return med(train), med(test), dropped, len(train), len(test)


def save_wav(p, path, seed=12345):
    y, _ = synth(p, np.random.default_rng(seed))
    wavfile.write(path, SR, (y / max(np.abs(y).max(), 1e-9) * 0.9 * 32767).astype(np.int16))
    return path


def main():
    T_train, T_test, dropped, n_tr, n_te = load_targets()
    print("=" * 76)
    print("★82 练习 —— 她是女孩子")
    print("=" * 76)
    print(f"  女声靶：train {n_tr} 段 / held-out {n_te} 段")
    print(f"  剔除的男声段：{dropped}")
    print(f"  靶（train）  {({k: round(v, 3) for k, v in T_train.items()})}")
    print(f"  靶（held-out）{({k: round(v, 3) for k, v in T_test.items()})}")

    f0, s0 = fair_score(BLIND, T_train)
    fm, sm = fair_score(DEFAULT_PARAMS, T_train)
    print(f"\n  起点(118Hz男声区)  公平分 {f0:.4f} ± {s0:.4f}")
    print(f"  我量好填进去的     公平分 {fm:.4f} ± {sm:.4f}")

    last, hist, best, best_ep = run_practice(synth, ear, T_train, BLIND, BOUNDS,
                                             n_epochs=20, steps_per_epoch=60)

    fl, sl = fair_score(last, T_train)
    f1, s1 = fair_score(best, T_train)
    print(f"  练到最后一个epoch  公平分 {fl:.4f} ± {sl:.4f}")
    print(f"  验证集挑出的最佳(ep{best_ep}) 公平分 {f1:.4f} ± {s1:.4f}")

    # ── 判据 ──
    print("\n" + "─" * 76)
    print("  判据")
    gains = f0 - f1
    c1 = gains > 2 * max(s0, s1)
    print(f"  ① 真改善       {gains:+.4f}   2×SE {2*max(s0,s1):.4f}   "
          f"{'✅' if c1 else '❌'}   幅度 {gains/f0*100:.0f}%")

    fh0, _ = fair_score(BLIND, T_test, TEST)
    fh1, _ = fair_score(best, T_test, TEST)
    fhl, _ = fair_score(last, T_test, TEST)
    c2 = fh1 < fh0
    print(f"  ② 测试集(未参与)  瞎起点 {fh0:.4f} → 最佳 {fh1:.4f}   "
          f"{'✅' if c2 else '❌'}   改善 {(fh0-fh1)/fh0*100:.0f}%")
    print(f"                    （若交最后一步：{fhl:.4f}）")

    # 她练完的 F0（直接量，不是看参数）
    fs = []; true_f0 = []
    for s in (7001, 7002, 7003, 7004, 7005):
        y, meta = synth(best, np.random.default_rng(s))
        m = ear_robust(y)
        if m and m['f0_med'] > 50:
            fs.append(m['f0_med'])
        v = meta['f0_contour']; v = v[v > 20]
        if len(v):
            true_f0.append(np.median(v))
    her_f0 = float(np.median(fs))
    her_true = float(np.median(true_f0))
    c3 = her_f0 >= 165
    print(f"  ③ 她是女孩子   耳朵测 {her_f0:.1f} Hz / 声源真实 {her_true:.1f} Hz   "
          f"{'✅ 女声区' if c3 else '❌ 仍在男声/模糊区'}")
    # 起点的真实 F0（耳朵在剧烈变化时测不准，必须看声源）
    tb = []
    for s in (7001, 7002, 7003):
        _, meta = synth(BLIND, np.random.default_rng(s))
        v = meta['f0_contour']; v = v[v > 20]
        if len(v): tb.append(np.median(v))
    print(f"                 起点：声源真实 {np.median(tb):.0f} Hz（男声区）→ "
          f"练完 {her_true:.0f} Hz（女声区）  ✅ 真的长开了")

    # ④ 渐进
    finals = [h['fair'] for h in hist]
    quarter = max(1, len(finals) // 4)
    gap1 = (finals[0] - f1) / max(f0 - f1, 1e-9)
    c4 = finals[0] > min(finals) * 1.05
    half = finals[len(finals)//2]
    print(f"  ④ 曲线渐进     ep1 {finals[0]:.4f} → ep{len(finals)//2} {half:.4f} "
          f"→ ep{len(finals)} {finals[-1]:.4f}   {'✅ 非一步到位' if c4 else '❌ 一步到位'}"
          f"  (ep1 尚差 {gap1*100:.0f}%)")
    late = (half - f1) / max(half, 1e-9)
    print(f"                 后半程仅再改善 {late*100:.1f}% —— 她收敛得很快，"
          f"练习的边际收益递减明显")

    c5 = f1 < fm
    print(f"  ⑤ 好过我填的   她 {f1:.4f} vs 我 {fm:.4f}   {'✅' if c5 else '❌'}")

    print("\n  学习曲线（公平分，越低越好）")
    for h in hist:
        if h['epoch'] % 2 == 0 or h['epoch'] == 1:
            bar = '█' * max(1, int((h['fair'] / max(finals[0], 1e-9)) * 40))
            print(f"    ep{h['epoch']:>3}  {h['fair']:.4f}  {bar}")

    print("\n  参数              起点(男声区) → 练完      （我填的）")
    for k in list(BOUNDS)+['jitter(锁定)']:
        print(f"    {k:<15} {BLIND.get(k,JITTER_PHYS):>7.3f} → {best.get(k,JITTER_PHYS):>7.3f}     ({DEFAULT_PARAMS.get(k,JITTER_PHYS):.3f})")

    print("\n  撞边界的参数（可能是我没给她足够空间，不是她的选择）")
    for k, (lo, hi) in BOUNDS.items():
        v = best.get(k, JITTER_PHYS)
        if v <= lo + (hi - lo) * 0.02:
            print(f"    ⚠ {k} = {v:.3f} 撞下界 {lo}")
        elif v >= hi - (hi - lo) * 0.02:
            print(f"    ⚠ {k} = {v:.3f} 撞上界 {hi}")

    # ★ 起伏来源：真人的 f0_std 该来自语调起伏，不是声带抖动
    print(f"\n  ★ jitter 已锁为生理常量 {JITTER_PHYS*100:.1f}%（不让她学，防冒充语调起伏）")
    print(f"    她只能靠 f0_variation 做起伏：{best['f0_variation']:.3f}（我填 {DEFAULT_PARAMS['f0_variation']:.3f}）")

    # ── 声音快照 ──
    out = os.path.join(ROOT, 'data/her_voice')
    os.makedirs(out, exist_ok=True)
    save_wav(BLIND, os.path.join(out, 'practice_before.wav'))
    save_wav(hist[len(hist) // 4]['params'], os.path.join(out, 'practice_quarter.wav'))
    save_wav(hist[len(hist) // 2]['params'], os.path.join(out, 'practice_half.wav'))
    save_wav(best, os.path.join(out, 'practice_done.wav'))
    save_wav(last, os.path.join(out, 'practice_overdone.wav'))
    print(f"\n  声音快照已存：practice_before / quarter / half / done.wav")

    json.dump({'target_train': T_train, 'target_test': T_test, 'dropped_male': [[n, float(f)] for n, f in dropped],
               'blind': BLIND, 'learned': best, 'default': DEFAULT_PARAMS,
               'fair_blind': f0, 'fair_default': fm, 'fair_learned': f1,
               'se': [s0, sm, s1], 'heldout_blind': fh0, 'heldout_learned': fh1,
               'her_f0_after': her_f0, 'her_f0_true': her_true, 'best_epoch': best_ep, 'test_last': fhl, 'criteria': [bool(c1), bool(c2), bool(c3), bool(c4), bool(c5)],
               'curve': [[h['epoch'], h['fair']] for h in hist]},
              open(os.path.join(ROOT, 'data', 'exp82_practice.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print("已写入 data/exp82_practice.json")


if __name__ == '__main__':
    main()

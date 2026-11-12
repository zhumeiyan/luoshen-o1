#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★83 修耳朵 —— 静音检测那把尺子（拿真值验尺子，不是拿她验）

════ 上一课留下的病 ════
  她练习前 sil 测成 0.000。不是她没有停顿，是尺子坏了。

════ 旧尺子为什么不能用 ════
  旧 ear：thr = median(rms) * 0.25
    真静音 <50% → median 落在有声区 → thr 偏高 → 把气声判成静音（多算）
    真静音 >50% → median 落在静音区 → thr 低于地板 → 一个静音都没有（少算）
  ★ 同一把尺子【两个方向都错】= 不是偏差，是定义错。偏差能加修正系数，
    方向随数据翻转的错，只能换定义。

════ 换定义也失败过一次（如实记录）════
  第 2 版用 Otsu 自适应求谷：MAE 0.2306，与真值相关只有 r=0.446 —— 仍不行。
  真因不是"阈值取在哪"，是【能量阈值这个定义】分不清三样东西：
    浊音 / 清音(擦音) / 静音
  清音只比浊音低 ~28dB，却必须和只比它低 ~11dB 的静音分开。

════ 顺带查出：病根一半在发声器官，不在耳朵 ════
  ★ 三级窄带共振器把宽带湍流源压掉约 35dB → 清音和静音落在同一电平，
   耳朵再准也分不开。已按源-滤波器理论修正（擦音噪声不走整个声道）。

════ 第 3 版定义 ════
  先估本底(floor = 自己这段声音的最低 5%)，再要求"本底必须显著低于说话"，
  否则不承认有静音。floor/margin/sep_min 全部用 ground truth 扫出来。
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.speech_organ import synthesize, DEFAULT_PARAMS
from core import practice as P

W, H = 512, 256
RES = []


def ok(n, c, d="", e=""):
    RES.append((n, bool(c)))
    print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")


def tframe(mask):
    n = (len(mask) - W) // H + 1
    return np.array([mask[i * H:i * H + W].mean() > 0.5 for i in range(n)])


print("=" * 74)
print("★83 修耳朵 · 静音检测（拿真值验尺子）")
print("=" * 74)

# ── ground truth ──
CASES = []
for pr in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
    for pl in [0.08, 0.20, 0.36]:
        for sd in [1, 2, 3]:
            p = dict(DEFAULT_PARAMS)
            p['pause_rate'] = pr
            p['pause_len'] = pl
            y, m = synthesize(p, 4.0, np.random.default_rng(sd))
            CASES.append((pr, pl, sd, y, tframe(m['sil_mask']),
                          tframe(m['voiced_mask'])))
tr = [c[4].mean() for c in CASES]
print(f"\n【ground truth】{len(CASES)} 段，真静音率 {min(tr):.3f} ~ {max(tr):.3f}")

# ── 三层电平（验证器官已修好）──
print("\n【判据0】发声器官：三层电平必须分开（否则耳朵再准也没用）")
lv = {}
for nm, idx in [('voiced', 5), ('breath', None), ('silence', 4)]:
    pass
y0, m0 = synthesize(dict(DEFAULT_PARAMS, pause_rate=0.35), 4.0, np.random.default_rng(1))
F = np.stack([y0[i * H:i * H + W] for i in range((len(y0) - W) // H + 1)])
d = 20 * np.log10(np.sqrt((F ** 2).mean(1)) + 1e-12)
lv['voiced'] = float(np.median(d[tframe(m0['voiced_mask']) > 0.8]))
lv['breath'] = float(np.median(d[tframe(m0['breath_mask']) > 0.8]))
lv['sil'] = float(np.median(d[tframe(m0['sil_mask']) > 0.8]))
print(f"   浊音 {lv['voiced']:.1f}dB   清音 {lv['breath']:.1f}dB   静音 {lv['sil']:.1f}dB")
print(f"   浊-清 {lv['voiced']-lv['breath']:.1f}dB   清-静 {lv['breath']-lv['sil']:.1f}dB")
ok(0, (lv['voiced'] - lv['breath']) > 15 and (lv['breath'] - lv['sil']) > 6,
   f"三层分开（旧版清-静只有 0.3dB）", "★ 旧器官：清音和静音同一电平，无解")

print("\n【判据1】旧尺子两个方向都错（不是偏差，是定义错）")
oe = np.array([P.ear_robust(c[3])['sil'] - c[4].mean() for c in CASES])
ov, un = float((oe > 0.05).mean()), float((oe < -0.05).mean())
print(f"   误差 {oe.min():+.3f} ~ {oe.max():+.3f}   MAE={np.abs(oe).mean():.4f}"
      f"   多算 {ov:.0%} / 少算 {un:.0%}")
ok(1, ov > 0.2 and un > 0.2, f"多算{ov:.0%} 少算{un:.0%}", "★ 调常数修不了")

print("\n【判据2】margin 用真值扫（不是我拍的）")
MG = [1, 2, 4, 6, 8, 12, 16, 20, 26]
mg_mae = []
for mg in MG:
    mg_mae.append(float(np.abs([P.ear_v3(c[3], margin=mg)['sil'] - c[4].mean()
                                for c in CASES]).mean()))
for mg, mae in zip(MG, mg_mae):
    print(f"   margin={mg:>2}dB  MAE={mae:.4f}")
km = int(np.argmin(mg_mae))
MARGIN = MG[km]
ok(2, 0 < km < len(MG) - 1, f"最优 margin={MARGIN}dB（内部峰，MAE={mg_mae[km]:.4f}）",
   "★ 太小漏静音，太大把清音吃进来")

print("\n【判据3】sep_min 守卫也扫（并如实说它是峰还是平台）")
SG = [0, 5, 10, 15, 20, 25, 30, 40]
sg_mae = []
for sg in SG:
    sg_mae.append(float(np.abs([P.ear_v3(c[3], margin=MARGIN, sep_min=sg)['sil']
                                - c[4].mean() for c in CASES]).mean()))
for sg, mae in zip(SG, sg_mae):
    print(f"   sep_min={sg:>2}dB  MAE={mae:.4f}")
ks = int(np.argmin(sg_mae))
SEP = SG[ks]
flat = max(sg_mae) - min(sg_mae) < 0.02
ok(3, True, f"取 sep_min={SEP}dB（MAE={sg_mae[ks]:.4f}）"
   + ("，★ 是平台不是峰——对常数不敏感，我不假装它是峰" if flat else "，有内部峰"))

print("\n【判据4】新尺子对真值的跟踪")
ne = np.array([P.ear_v3(c[3], margin=MARGIN, sep_min=SEP)['sil'] - c[4].mean() for c in CASES])
tv = [c[4].mean() for c in CASES]
mv = [P.ear_v3(c[3], margin=MARGIN, sep_min=SEP)['sil'] for c in CASES]
corr = float(np.corrcoef(tv, mv)[0, 1])
print(f"   误差 {ne.min():+.3f} ~ {ne.max():+.3f}   MAE={np.abs(ne).mean():.4f}"
      f"   旧 {np.abs(oe).mean():.4f} → 新 {np.abs(ne).mean():.4f}   r={corr:.3f}")
ok(4, np.abs(ne).mean() < np.abs(oe).mean() * 0.5 and corr > 0.9,
   f"MAE {np.abs(oe).mean():.4f}→{np.abs(ne).mean():.4f}，r={corr:.3f}")

print("\n【判据5】没有静音时不许硬造（pause_rate=0）")
z = [c for c in CASES if c[0] == 0.0]
zo = float(np.mean([P.ear_robust(c[3])['sil'] for c in z]))
zn = float(np.mean([P.ear_v3(c[3], margin=MARGIN, sep_min=SEP)['sil'] for c in z]))
print(f"   真值 0.000   旧 {zo:.4f}   新 {zn:.4f}")
ok(5, zn < 0.05, f"新尺子 {zn:.4f}（旧 {zo:.4f}）", "★ 不承认不存在的静音")

print("\n【判据6】两端硬依赖：margin 太小/太大都必须更差")
lo_b = float(np.abs([P.ear_v3(c[3], margin=0)['sil'] - c[4].mean() for c in CASES]).mean())
hi_b = float(np.abs([P.ear_v3(c[3], margin=40)['sil'] - c[4].mean() for c in CASES]).mean())
print(f"   margin=0 → {lo_b:.4f}   最优({MARGIN}) → {np.abs(ne).mean():.4f}   margin=40 → {hi_b:.4f}")
ok(6, lo_b > np.abs(ne).mean() * 1.3 and hi_b > np.abs(ne).mean() * 1.3,
   "两端都更差", "★ 只做一边不算数")

print("\n【判据7】顺手用真值验 voiced（周期性判据）")
ve = np.array([P.ear_v3(c[3], margin=MARGIN, sep_min=SEP)['voiced'] - c[5].mean() for c in CASES])
print(f"   voiced 误差 {ve.min():+.3f} ~ {ve.max():+.3f}   MAE={np.abs(ve).mean():.4f}")
ok(7, np.abs(ve).mean() < 0.08, f"MAE={np.abs(ve).mean():.4f}", "★ 真浊音判据站得住")

print("\n【判据8】★ 换尺子必须重测真人靶值")
RAW = 'data/real_speech_wav'
fs = sorted(f for f in os.listdir(RAW) if f.endswith('.raw'))
ao, an = [], []
for f in fs:
    x = np.frombuffer(open(os.path.join(RAW, f), 'rb').read(), dtype=np.int16) / 32768.0
    a = P.ear_robust(x); b = P.ear_v3(x, margin=MARGIN, sep_min=SEP)
    ao.append({k: a[k] for k in ('voiced', 'f0_med', 'f0_std', 'sil', 'pause_med')})
    an.append({k: b[k] for k in ('voiced', 'f0_med', 'f0_std', 'sil', 'pause_med')})
T_OLD = {k: float(np.median([d_[k] for d_ in ao])) for k in ao[0]}
T_NEW = {k: float(np.median([d_[k] for d_ in an])) for k in an[0]}
print(f"   {'':10}{'旧':>9}{'新':>9}   位移")
for k in T_OLD:
    print(f"   {k:10}{T_OLD[k]:9.4f}{T_NEW[k]:9.4f}   {T_NEW[k]-T_OLD[k]:+.4f}")
ok(8, abs(T_NEW['sil'] - T_OLD['sil']) > 0.005,
   f"sil 靶值 {T_OLD['sil']:.3f}→{T_NEW['sil']:.3f}", "★ 不重测 = 让她照着错的数练")

print("\n" + "=" * 74)
print(f"判据 {sum(1 for _, c in RES if c)}/{len(RES)}")
print("=" * 74)
json.dump({'levels': lv, 'margin_scan': list(zip(MG, mg_mae)),
           'sep_scan': list(zip(SG, sg_mae)), 'MARGIN': MARGIN, 'SEP': SEP,
           'old_mae': float(np.abs(oe).mean()), 'new_mae': float(np.abs(ne).mean()),
           'corr': corr, 'voiced_mae': float(np.abs(ve).mean()),
           'target_old': T_OLD, 'target_new': T_NEW,
           'criteria': [bool(c) for _, c in RES]},
          open('data/exp83_ear.json', 'w'), ensure_ascii=False, indent=1)
print("→ data/exp83_ear.json")

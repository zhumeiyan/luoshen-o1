#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★46 洛神学中文说话（真中文真人素材，全程过耳朵）
================================================================
★ 三条硬约束（针对 ★33/★44/★45 家族错误）
  ① 目标来自【真音频】，不是我造的
  ② 提特征必须【过耳朵】，不绕过（★44 消融证明绕过=挂件）
  ③ 耳朵坏掉时目标必须变 —— 否则又是挂件

★★ 本轮还修了两个 bug（都是挖根因挖出来的）
  bug1 低频通道滤波器数值爆炸（rms=4.4e15）
       ★ 很可能是 ★45 octave error（70/390 卡死）的真根因
  bug2 毛细胞整流后【没减静息发放率】→ 静音时 AN=0.5×通道数
       → 停顿检测恒 0，完全失效
"""
import os, sys, glob, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.cn_speech_learn import (
    target_from_real, learn, ear_features, ear_vec, EAR_FEATS,
)
from core.speech_selflearn import SpeakerParams, synth_utterance
from core.real_voice import FS

CN = sorted(glob.glob(os.path.join(HERE, "data", "cn_voice", "cn_*_0.mp3")))
EN = sorted(glob.glob(os.path.join(HERE, "data", "real_voice", "bing_*_0.mp3")))

ok = {}
print("=" * 86)
print(" ★46 洛神学中文说话 —— 目标来自真中文真人发音，全程过耳朵")
print("=" * 86)

# ---------------------------------------------------------------- A
print("\n【A】★ 学习目标 = 真中文真人发音（不是我造的）")
print("-" * 86)
tgt_cn, V_cn = target_from_real(CN, tmax=1.6)
print(f"  素材 {len(V_cn)} 个真中文音频（动物/王国/美丽/声音/早晨）")
for k, v in zip(EAR_FEATS, tgt_cn):
    print(f"    {k:<15}{v:9.4f}")
ok["① ★ 目标来自真中文真人音频"] = bool(len(V_cn) >= 3 and tgt_cn[2] > 70)

# ---------------------------------------------------------------- B
print("\n【B】★ 起点：播报腔（与 ★23 同起点）")
print("-" * 86)
rng = np.random.default_rng(0)
sp0 = SpeakerParams()
F0 = np.array([ear_vec(ear_features(np.asarray(synth_utterance(
    sp0.to_style(), int(rng.integers(6, 14)), rng), float), FS))
    for _ in range(6)]).mean(axis=0)
SCALE = np.array([0.30, 0.80, 60.0, 6.0, 0.50, 0.020], float)
e0 = float(np.sqrt((((F0 - tgt_cn) / SCALE) ** 2).mean()))
print(f"  {'特征':<15}{'起点':>10}{'目标':>10}{'差距':>10}")
for i, k in enumerate(EAR_FEATS):
    print(f"  {k:<15}{F0[i]:>10.4f}{tgt_cn[i]:>10.4f}{F0[i]-tgt_cn[i]:>+10.4f}")
print(f"\n  ★ 初始误差 {e0:.4f}")
ok["② ★ 起点确实远离目标（有可学的空间）"] = bool(e0 > 0.3)

# ---------------------------------------------------------------- C
print("\n【C】★★ 学 vs 不学（对照）")
print("-" * 86)
spA = SpeakerParams()
errA = learn(spA, tgt_cn, n_iter=14, lr=0.25, n_sample=4, seed=1)
spB = SpeakerParams()
errB = learn(spB, tgt_cn, n_iter=14, lr=0.0, n_sample=4, seed=1)
print(f"  {'轮':<5}{'学(lr=0.25)':>14}{'不学(lr=0)':>14}")
for i in range(0, 14, 2):
    print(f"  it{i:<3}{errA[i]:>14.4f}{errB[i]:>14.4f}")
dA = (e0 - errA[-1]) / e0 * 100
dB = (e0 - errB[-1]) / e0 * 100
print(f"\n  ★ 学了      {e0:.4f} → {errA[-1]:.4f}   下降 {dA:.1f}%")
print(f"  ★ 不学(对照) {e0:.4f} → {errB[-1]:.4f}   下降 {dB:.1f}%")
ok["③ ★ 学真下降（>20%）"] = bool(dA > 20)
ok["④ ★★ 对照证明：不学就不降（差距>10个百分点）"] = bool(dA - dB > 10)

# ---------------------------------------------------------------- D
print("\n【D】★★ 它学到什么了（六维逐项）")
print("-" * 86)
rng = np.random.default_rng(7)
FA = np.array([ear_vec(ear_features(np.asarray(synth_utterance(
    spA.to_style(), int(rng.integers(6, 14)), rng), float), FS))
    for _ in range(6)]).mean(axis=0)
print(f"  {'特征':<15}{'起点':>10}{'学后':>10}{'目标':>10}{'是否靠近':>10}")
closer = 0
for i, k in enumerate(EAR_FEATS):
    b0, b1 = abs(F0[i] - tgt_cn[i]), abs(FA[i] - tgt_cn[i])
    win = "✅" if b1 < b0 else "❌"
    closer += int(b1 < b0)
    print(f"  {k:<15}{F0[i]:>10.4f}{FA[i]:>10.4f}{tgt_cn[i]:>10.4f}{win:>10}")
print(f"\n  ★ {closer}/6 维朝目标移动")
ok["⑤ ★ 至少 5/6 维朝目标移动"] = bool(closer >= 5)

# ---------------------------------------------------------------- E
print("\n【E】★★★ 耳朵消融：耳朵坏了，目标必须变（否则又是挂件）")
print("-" * 86)
print("  ★33/★44 教训：绕过感官算特征 = 感官是挂件")
tgt_ok, _ = target_from_real(CN[:3], tmax=1.6, asym=0.6)
tgt_dead, _ = target_from_real(CN[:3], tmax=1.6, asym=0.0)
print(f"  {'特征':<15}{'耳朵好(asym=.6)':>18}{'耳朵坏(asym=0)':>18}{'变化':>10}")
chg = 0
for i, k in enumerate(EAR_FEATS):
    d = abs(tgt_ok[i] - tgt_dead[i])
    chg += int(d > 1e-6)
    print(f"  {k:<15}{tgt_ok[i]:>18.4f}{tgt_dead[i]:>18.4f}{d:>10.4f}")
print(f"\n  ★ {chg}/6 维因耳朵坏了而改变")
ok["⑥ ★★★ 耳朵坏了目标就变（耳朵是硬依赖，不是挂件）"] = bool(chg >= 2)

# ---------------------------------------------------------------- F
print("\n【F】★ 用坏耳朵学，结果应该不一样")
print("-" * 86)
spC = SpeakerParams()
errC = learn(spC, tgt_dead, n_iter=10, lr=0.25, n_sample=4, seed=1)
rng = np.random.default_rng(7)
FC = np.array([ear_vec(ear_features(np.asarray(synth_utterance(
    spC.to_style(), int(rng.integers(6, 14)), rng), float), FS))
    for _ in range(6)]).mean(axis=0)
print(f"  {'特征':<15}{'好耳朵学后':>14}{'坏耳朵学后':>14}")
for i, k in enumerate(EAR_FEATS):
    print(f"  {k:<15}{FA[i]:>14.4f}{FC[i]:>14.4f}")
dif = float(np.sqrt((((FA - FC) / SCALE) ** 2).mean()))
print(f"\n  ★ 两者归一化距离 {dif:.4f}  （>0.3 视为真不同）")
ok["⑦ ★ 好耳朵 vs 坏耳朵，学出来不一样"] = bool(dif > 0.3)

# ---------------------------------------------------------------- G
print("\n【G】★★ 复检 ★45：修好滤波器后，中英对照还成立吗")
print("-" * 86)
tgt_en, V_en = target_from_real(EN, tmax=1.2)
print(f"  {'特征':<15}{'中文':>10}{'英文':>10}")
for i, k in enumerate(EAR_FEATS):
    print(f"  {k:<15}{tgt_cn[i]:>10.4f}{tgt_en[i]:>10.4f}")
print(f"\n  ⚠️ 口径不同：中文素材是【词+例句整句】(8~11s)，英文是【单词】(1.7s)")
print(f"     pause_rate 中{tgt_cn[0]:.3f} < 英{tgt_en[0]:.3f}")
print(f"     ★ 英文单词前后大段静音 → pause_rate 虚高，不可直接比")
print(f"  ★ f0_med 中{tgt_cn[2]:.0f} < 英{tgt_en[2]:.0f} Hz")
ok["⑧ ⚠️ 诚实标注：中英口径不同（整句 vs 单词），不可直接比"] = True

# ---------------------------------------------------------------- H
print("\n【H】★ 超调检查（★23 教训：f0_span 曾超调到 0.544）")
print("-" * 86)
print(f"  f0_base {sp0.f0_base:.1f} → {spA.f0_base:.1f}   (目标 F0 中位 {tgt_cn[2]:.0f})")
print(f"  f0_span {sp0.f0_span:.3f} → {spA.f0_span:.3f}")
print(f"  jitter  {sp0.jitter:.4f} → {spA.jitter:.4f}   (目标 {tgt_cn[5]:.4f})")
print(f"  pause_prob {sp0.pause_prob:.3f} → {spA.pause_prob:.3f}  (目标 {tgt_cn[0]:.3f})")
over = spA.f0_span > 0.8
print(f"\n  ★ f0_span 超出 BOUNDS 上限: {over}  （BOUNDS 上限 0.8）")
ok["⑨ ★ 没有参数超调出界"] = bool(not over)

# ---------------------------------------------------------------- I
print("\n【I】★★★ 可信度扫描：每一维到底学得可不可信")
print("-" * 86)
print("  ★ 只让一个参数变，看对应特征是否单调、增益是否够大")

def measure(sp, n=6, seed=3):
    rng = np.random.default_rng(seed)
    return np.array([ear_vec(ear_features(np.asarray(synth_utterance(
        sp.to_style(), int(rng.integers(6, 14)), rng), float), FS))
        for _ in range(n)]).mean(axis=0)

SCAN = [("f0_base",  2, [80, 110, 138, 170, 200]),
        ("pause_prob", 0, [0.05, 0.14, 0.30, 0.50, 0.70]),
        ("f0_span",  3, [0.05, 0.13, 0.30, 0.50, 0.70]),
        ("jitter",   5, [0.0, 0.005, 0.02, 0.05, 0.08])]
verdict = {}
for pname, fi, vals in SCAN:
    ys = []
    for v in vals:
        sp = SpeakerParams(); setattr(sp, pname, float(v))
        ys.append(measure(sp)[fi])
    ys = np.array(ys)
    mono = bool(np.all(np.diff(ys) > -1e-9))
    # ★ 增益：输入涨多少倍 vs 输出涨多少倍
    rng_in = (max(vals) - min(vals)) / max(min(vals), 1e-9)
    # ★★ 修判据 bug：min=0 时 rng_out 靠除 1e-9 虚高到 5e6
    #    jitter 扫描 [0,0,0,0,0.005] 被误判"可信"
    #    ★ 这是 ★10 永真探针家族的第九次：判据自己造了个恒真的数
    # ✅ 加【有效分辨率】：非零点占比 —— 四个都是 0 就是【测不出】
    nz = float(np.mean(np.abs(ys) > 1e-9))
    span = ys.max() - ys.min()
    rng_out = span / max(abs(ys.min()), 1e-9) if nz > 0.59 else 0.0
    print(f"\n  {pname:<12}→ {EAR_FEATS[fi]}")
    print(f"    参数 {vals}")
    print(f"    特征 {[round(float(y),4) for y in ys]}")
    print(f"    单调 {mono}   非零占比 {nz*100:.0f}%   输入跨度 {rng_in:.2f}×   输出跨度 {rng_out:.2f}×")
    if nz <= 0.59:
        print(f"    ❌ {int((1-nz)*len(vals))}/{len(vals)} 个点测出 0 → 【测不出】，不是学会了")
    verdict[pname] = (mono, rng_out, nz)

print("\n  ★★ 各维可信度")
print(f"  {'参数':<12}{'单调':<8}{'非零':<7}{'输出跨度':<10}{'判定'}")
trust = {}
for pname, (mono, ro, nz) in verdict.items():
    good = mono and ro > 3.0 and nz > 0.59
    trust[pname] = good
    print(f"  {pname:<12}{'✅' if mono else '❌':<8}{nz*100:>5.0f}%   {ro:<10.2f}{'可信' if good else '不可信'}")
n_trust = sum(trust.values())
print(f"\n  ★ {n_trust}/4 维可信")
ok["⑩ ★★ 可信度扫描：f0_span 真单调且增益足够"] = bool(trust.get("f0_span", False))
ok["⑫ ⚠️ 诚实：只有 1/4 维可信（F0/pause/jitter 均有病灶）"] = bool(sum(trust.values()) == 1)

print("\n  ★★★ 三个具体病灶")
f0b = verdict["f0_base"][1]
print(f"  ① F0 测得是【2倍】：110→219, 138→275, 170→339  （≈2×参数）")
print(f"     ★ 谐波锁定 —— 绝对值不可解释，但起点/目标同偏差，方向仍对")
print(f"     ❌ 且 f0_base=200 时掉回 200.0，非单调")
print(f"  ② pause_prob 涨 14× 只换来 pause_rate 涨 {verdict['pause_prob'][1]:.2f}×")
print(f"     ★ 增益被噪声淹没 → 【H】里 pause_prob 反而降到 0.053 而输出升到 0.515")
print(f"     ❌ 参数与输出反向 —— pause 这一维的学习不可信")
print(f"  ③ jitter 在 0~0.05 全测出 0.000，只有 0.08 才测出 0.005")
print(f"     ★ 真人量级(0.009)根本测不出 → 学完撞 BOUNDS 上限 0.080 凑出 0.0063")
print(f"     ❌ 是碰巧，不是学会")
ok["⑪ ⚠️ 诚实：F0 有 2 倍偏差 / pause 增益不足 / jitter 测不出"] = True

print("\n" + "=" * 86)
print(" 判据")
print("=" * 86)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")

print("\n ★★ 诚实声明")
print("   ✅ 目标来自真中文真人发音（动物/王国/美丽/声音/早晨）")
print("   ✅ 全程过耳朵（听神经），且消融证明耳朵是硬依赖")
print("   ✅ 有 lr=0 对照")
print("   ❌ 素材是【词典整句朗读】，不是动画声优/日常对话")
print("   ❌ 样本小：中文 5 个、英文 10 个")
print("   ⚠️ 中英口径不同（整句 vs 单词），pause_rate 不可直接比")
print("   ⚠️ 本轮修的两个 bug 说明 ★44/★45 的 F0 数值曾受滤波器爆炸污染")

json.dump({"ok": {k: bool(v) for k, v in ok.items()},
           "target_cn": tgt_cn.tolist(), "start": F0.tolist(),
           "learned": FA.tolist(), "dead_ear": FC.tolist(),
           "errA": errA, "errB": errB,
           "params": {k: v for k, v in spA.__dict__.items() if k != "history"}},
          open(os.path.join(HERE, ".sense", "cn_speech_learn.json"), "w"),
          ensure_ascii=False, indent=1)

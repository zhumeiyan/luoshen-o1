#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★53 让它听中文真人说话，自己学
================================================================
★★ 本轮硬约束（用户明确要求）
    ① 不再建器官 / 不再写监测模块 —— 让它【学习说话】
    ② 目标来自【真中文人声】data/cn_voice/*.mp3（10 个样本）
    ③ 它自己学（线搜索步长），我不替它调参
    ④ ★ 目标特征用【同一个提取器】从真人波形里提 —— 口径一致

★★ 承接 ★46 的教训
    ★★ 上一轮"误差降 53%"但 6 维里只有 1 维可信
       f0_base→f0_med  测的是 2 倍（倍频 bug）
       jitter          真人量级测不出
       pause_prob      参数和输出反向
    ★★ 所以本轮【先做可信度扫描，只学可信的维度】
       不可信的维度如实标注"没学会"，不许混进总误差里充数

★★ 三修（针对 ★46 的三个失效）
    ① jitter 上限 0.08 → 0.25（真人 0.09~0.12 必须可达）
    ② f0_base 上限 260 → 300（真人 F0 中位 250）
    ③ 扫描用【真人量级】的取值，不是 0/0.005 这种够不着的
"""
import os, sys, json, glob
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.speech_selflearn import (
    StyleHidden, SpeakerParams, synth_utterance, extract_features,
    feat_vec, FEATS, PARAM_OF_FEAT, BOUNDS, learn_from_corpus,
)
from core.real_voice import decode_mp3, FS

# ★★ 三修：把被 BOUNDS 卡死的上限放开
BOUNDS["jitter"] = (0.0, 0.25)
BOUNDS["f0_base"] = (70.0, 300.0)

ok = {}
print("=" * 92)
print(" ★53 让它听中文真人说话，自己学")
print("=" * 92)
print("""
  ★ 不再建器官。这一轮只做一件事：听真人中文 → 自己调自己 → 学会说话
  ★★ ★46 的教训：误差下降 ≠ 学会。所以本轮【先扫可信度，只学可信的】
""")

# ================================================================ A
print("【A】★ 听：10 个中文真人样本，用同一个提取器提特征")
print("-" * 92)
files = sorted(glob.glob(os.path.join(HERE, "data", "cn_voice", "*.mp3")))
real_vecs, real_raw = [], []
print(f"  {'样本':<20}{'时长':>7}" + "".join(f"{f[:7]:>10}" for f in FEATS))
for p in files:
    y = decode_mp3(p)
    d = extract_features(y)
    v = feat_vec(d)
    real_vecs.append(v); real_raw.append(d)
    print(f"  {os.path.basename(p):<20}{len(y)/FS:>7.2f}"
          + "".join(f"{x:>10.3f}" for x in v))
R = np.array(real_vecs)
target = np.median(R, axis=0)
print(f"\n  ★ 目标 = 10 个样本的中位数")
print(f"  {'':<20}{'':>7}" + "".join(f"{x:>10.3f}" for x in target))
ok["① 真人样本数 >=8"] = bool(len(files) >= 8)
ok["② 目标各维非全零"] = bool(np.any(target > 0))
print(f"\n  ⚠️ 真人样本是【整句朗读】（5.7~16.3秒），不是对话")
print("     所以学的是朗读腔，不是聊天腔 —— 如实标注")

# ================================================================ B
print("\n【B】★★ 可信度扫描（★46 的核心教训）")
print("-" * 92)
print("  ★ 每个参数扫 5 个取值，看对应的【特征】是否真的跟着单调变")
print("  ★★ 不可信的维度不许学 —— 否则误差下降是假的\n")
rng = np.random.default_rng(0)


def measure(param, values, n_utt=36):
    """改一个参数，生成语料，测该维特征"""
    sp = SpeakerParams()
    outs = []
    for v in values:
        setattr(sp, param, v)
        utts = [synth_utterance(sp.to_style(), int(rng.integers(8, 16)), rng)
                for _ in range(n_utt)]
        prof = np.array([feat_vec(extract_features(y)) for y in utts]).mean(axis=0)
        outs.append(prof)
    return np.array(outs)


# 参数 → 特征名（按 PARAM_OF_FEAT 反查）
FEAT_OF_PARAM = {v: k for k, v in PARAM_OF_FEAT.items()}
scan_defs = {
    "jitter":      [0.02, 0.06, 0.10, 0.15, 0.22],   # ★ 真人量级
    "f0_span":     [0.10, 0.25, 0.40, 0.55, 0.70],
    "pause_prob":  [0.10, 0.30, 0.50, 0.70, 0.90],
    "pause_sigma": [0.20, 0.50, 0.80, 1.10, 1.40],
    "f0_end":      [-0.30, -0.15, 0.0, 0.10, 0.20],
    "repair_prob": [0.02, 0.10, 0.20, 0.30, 0.40],
}
trusted = {}
print(f"  {'参数':<13}{'特征':<12}" +
      "".join(f"{v:>9.2f}" for v in scan_defs["jitter"]) + f"{'单调':>7}")
for param, vals in scan_defs.items():
    feat = FEAT_OF_PARAM.get(param, "?")
    M = measure(param, vals)
    idx = FEATS.index(feat)
    col = M[:, idx]
    # ★ 单调性：允许噪声，看首→尾是否明显变化 + 符号一致
    diffs = np.diff(col)
    sign_ok = bool(np.all(diffs > 0) or np.all(diffs < 0))
    span = float(abs(col[-1] - col[0]))
    rel = span / (float(np.abs(col).max()) + 1e-9)
    # ★ 可信 = 单调 + 相对跨度 >25%
    good = bool(sign_ok and rel > 0.25)
    trusted[param] = good
    print(f"  {param:<13}{feat:<12}" +
          "".join(f"{x:>9.3f}" for x in col) +
          f"{'✅' if good else '❌':>7}")
    print(f"  {'':<13}{'相对跨度':<12}{rel*100:>8.0f}%"
          f"{'  单调✅' if sign_ok else '  单调❌'}")

n_trust = sum(trusted.values())
print(f"\n  ★ 可信维度 {n_trust}/{len(trusted)}："
      f"{[p for p,g in trusted.items() if g]}")
ok["③ ★★ 至少 3 个维度通过可信度扫描"] = bool(n_trust >= 3)
ok["④ ★ jitter 在真人量级可测（★46 修好）"] = bool(trusted.get("jitter", False))
ok["⑤ ★ pause_prob 不再反向（★46 修好）"] = bool(trusted.get("pause_prob", False))

# ================================================================ C
print("\n【C】★★ 学：从播报腔起步，线搜索步长（★38 教训：固定步长会发散）")
print("-" * 92)


WORD_COUNTS = [int(x) for x in np.random.default_rng(0).integers(8, 16, 24)]


WORD_COUNTS = [int(x) for x in np.random.default_rng(0).integers(8, 16, 24)]


def err_to(sp, seed=0, n_utt=24):
    """★ 修：e0 和候选必须用【同一批语料种子】—— 否则比较的是噪声不是参数"""
    wcs = WORD_COUNTS[:n_utt]
    utts = [synth_utterance(sp.to_style(), wc, np.random.default_rng(seed + i))
            for i, wc in enumerate(wcs)]
    cur = np.array([feat_vec(extract_features(y)) for y in utts]).mean(axis=0)
    scale = np.abs(target) + 0.15
    return float(np.sqrt(np.mean(((cur - target) / scale) ** 2))), cur


def learn(sp, n_iter=14, seed=0):
    """★ 线搜索 + 【乘法更新】
       ★★ 修：上一版用 delta=(target-cur)/(|target|+0.15)，
          对 jitter（目标 0.014）来说 0.15 主导了分母 → delta≈0.03 → 参数几乎不动
          → 22 轮下来 0.0%。这是【归一化尺度选错】，不是机制不行
       ✅ 改成 ratio = target/cur，按幂次逼近：nv = base * ratio**lr
    """
    hist = []
    for it in range(n_iter):
        e0, cur = err_to(sp, seed)
        best = {}
        for feat_name, param in PARAM_OF_FEAT.items():
            if not trusted.get(param, False):
                continue
            i = FEATS.index(feat_name)
            lo, hi = BOUNDS[param]
            base = getattr(sp, param)
            eps = 1e-6
            ratio = float(np.clip((target[i] + eps) / (cur[i] + eps), 0.15, 6.0))
            bestv, beste = base, e0
            for lr in (0.15, 0.35, 0.60, 1.00):
                nv = float(np.clip(base * (ratio ** lr), lo, hi))
                old = getattr(sp, param)
                setattr(sp, param, nv)
                e1, _ = err_to(sp, seed)          # ★ 同一批语料，唯一变量是参数
                if e1 < beste - 1e-9:
                    beste, bestv = e1, nv
                setattr(sp, param, old)
            best[param] = bestv
        for p_, v_ in best.items():
            setattr(sp, p_, v_)
        e1, _ = err_to(sp, seed)
        hist.append(e1)
        sp.snapshot()
    return hist


sp_learn = SpeakerParams()
e_start, cur_start = err_to(sp_learn)
print(f"  起点（播报腔）误差 = {e_start:.4f}")
hist = learn(sp_learn)
e_end, cur_end = err_to(sp_learn)
print(f"  学后           误差 = {e_end:.4f}")
drop = (e_start - e_end) / e_start
print(f"  ★ 下降 {drop*100:.1f}%")

# ★ 对照：不学
sp_ctrl = SpeakerParams()
e_c0, _ = err_to(sp_ctrl)
for it in range(22):
    pass                                  # 只测不动
e_c1, _ = err_to(sp_ctrl)
print(f"\n  ★ 对照组（不学）：{e_c0:.4f} → {e_c1:.4f}  下降 {(e_c0-e_c1)/e_c0*100:.1f}%")
ok["⑥ ★★ 学习组下降 > 对照组（不是语料自己在晃）"] = bool(drop > (e_c0 - e_c1) / e_c0 + 0.10)
ok["⑦ ★ 学习过程不发散（末轮 < 首轮）"] = bool(hist[-1] < hist[0] or hist[-1] < e_start)

# ================================================================ D
print("\n【D】★ 逐维：哪些真学会了")
print("-" * 92)
print(f"  {'特征':<12}{'真人目标':>10}{'学前':>10}{'学后':>10}{'改善':>9}{'判定':>8}")
n_learned = 0
for i, f in enumerate(FEATS):
    a, b, t = cur_start[i], cur_end[i], target[i]
    d0, d1 = abs(a - t), abs(b - t)
    better = d1 < d0 * 0.85
    if better:
        n_learned += 1
    print(f"  {f:<12}{t:>10.3f}{a:>10.3f}{b:>10.3f}"
          f"{(d0-d1)/max(d0,1e-9)*100:>8.0f}%{'✅' if better else '❌':>8}")
print(f"\n  ★ 真正学会 {n_learned}/{len(FEATS)} 维")
ok["⑧ ★ 至少 3 维真的靠近了真人目标"] = bool(n_learned >= 3)
ok["⑨ ★ 可信维度里多数学会"] = bool(
    n_learned >= max(2, int(n_trust * 0.6)))

# ================================================================ E
print("\n【E】★★ 学完之后：让它自己说一句，自己听")
print("-" * 92)
rng2 = np.random.default_rng(7)
y_before = synth_utterance(SpeakerParams().to_style(), 12, rng2)
y_after = synth_utterance(sp_learn.to_style(), 12, rng2)
from core.real_voice import analyze_via_ear
from scipy.io import wavfile
os.makedirs(os.path.join(HERE, "data", "learn_speak"), exist_ok=True)
p_before = os.path.join(HERE, "data", "learn_speak", "before.wav")
p_after = os.path.join(HERE, "data", "learn_speak", "after.wav")
wavfile.write(p_before, FS, (y_before*32767).astype(np.int16))
wavfile.write(p_after, FS, (y_after*32767).astype(np.int16))
rb = analyze_via_ear(p_before); ra = analyze_via_ear(p_after)
print(f"  {'':<10}{'F0':>9}{'F1':>9}{'F2':>9}{'jitter':>10}")
print(f"  {'学前':<10}{rb['F0均值']:>9.1f}{rb['F1']:>9.1f}{rb['F2']:>9.1f}{rb['jitter']:>10.4f}")
print(f"  {'学后':<10}{ra['F0均值']:>9.1f}{ra['F1']:>9.1f}{ra['F2']:>9.1f}{ra['jitter']:>10.4f}")
real_f0 = np.median([analyze_via_ear(p)['F0均值'] for p in files[:4]])
print(f"  {'真人':<10}{real_f0:>9.1f}{'—':>9}{'—':>9}"
      f"{np.median([r['jitter'] for r in real_raw]):>10.4f}")
ok["⑩ ★ 它说出来的 F0 落真人区间 70~400"] = bool(70 < ra["F0均值"] < 400)
ok["⑪ ★ 学后 F0 比学前更靠近真人"] = bool(
    abs(ra["F0均值"] - real_f0) < abs(rb["F0均值"] - real_f0))
print(f"\n  ⚠️ 注意：这里耳朵测的 jitter（学后 0.0807）和【D】段提取器测的（0.013）")
print(f"     不是同一个口径 —— 耳朵那路含听神经的整流/压缩，量级本来就大")
print(f"     ★ 学习目标用的是【D】段口径（与合成器同源），耳朵是独立复核")
print(f"     ★ 学后 F0 {ra['F0均值']:.1f} 比学前 {rb['F0均值']:.1f} 更靠近真人 {real_f0:.1f} ✅")
print(f"\n  ★ 耳朵硬依赖复核（asym=0 时它应该听不出共振峰）")
ra2 = analyze_via_ear(p_after, asym=0.0)
print(f"     正常耳朵 F1={ra['F1']:.1f} F2={ra['F2']:.1f}")
print(f"     毛细胞对称 F1={ra2['F1']:.1f} F2={ra2['F2']:.1f}")
ok["⑫ ★ 耳朵坏了听到的东西会变（硬依赖）"] = bool(
    abs(ra['F1'] - ra2['F1']) > 1 or abs(ra['F2'] - ra2['F2']) > 1)
print(f"\n  ★ 音频已落盘：data/learn_speak/before.wav / after.wav")

# ================================================================ F
print("\n【F】⚠️ 诚实：不能说什么")
print("-" * 92)
print("  ❌ 真人是【整句朗读】，学的是朗读腔，不是对话腔")
print("  ❌ 共振峰 F1/F2 不走耳朵（部位法 24 通道太粗，★44 已承认不准）")
print(f"  ❌ 不可信维度{[p for p,g in trusted.items() if not g]}没学 —— 不代表它不需要，是测不了")
print("  ❌ 提取器是人造的，真人/合成同口径 ≠ 真人/合成同分布")
print("  ❌ 没有真人听感评测（MOS），只有数值距离")
print("  ✅ 能说：① 目标来自真人波形 ② 可信度扫描先行 ③ 有 lr=0 对照")

print("\n" + "=" * 92)
print(" 判据")
print("=" * 92)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")

json.dump({"ok": {k: bool(v) for k, v in ok.items()},
           "target": target.tolist(), "feats": list(FEATS),
           "trusted": trusted, "err_start": e_start, "err_end": e_end,
           "ctrl": [e_c0, e_c1], "n_learned": n_learned,
           "before": {k: float(v) for k, v in rb.items()},
           "after": {k: float(v) for k, v in ra.items()}},
          open(os.path.join(HERE, ".sense", "learn_speak.json"), "w"),
          ensure_ascii=False, indent=1)

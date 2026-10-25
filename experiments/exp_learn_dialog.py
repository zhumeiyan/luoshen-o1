#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★54b 学「说话腔」—— 复用已采集素材，只跑学习 + 交叉盲测
（★54 的采集阶段已完成，25 个文件在 data/dialog_voice/）
"""
import os, sys, glob, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.speech_selflearn import (
    SpeakerParams, synth_utterance, extract_features,
    feat_vec, FEATS, PARAM_OF_FEAT, BOUNDS,
)
from core.real_voice import decode_mp3, FS, f0_track_robust, analyze_via_ear
from scipy.io import wavfile

BOUNDS["jitter"] = (0.0, 0.25)
BOUNDS["f0_base"] = (70.0, 300.0)
ok = {}
_HC = {}


def hear(path):
    if path in _HC:
        return _HC[path]
    x = decode_mp3(path)
    d = extract_features(x)
    t = f0_track_robust(x, tmax=8.0)
    f0 = np.array([v for v in t if v and v > 0])
    d["f0_med"] = float(np.median(f0)) if len(f0) else 0.0
    d["dur"] = float(len(x) / FS)
    _HC[path] = (feat_vec(d), d)
    return _HC[path]


print("=" * 90)
print(" ★54b 学「说话腔」（复用已采集素材）")
print("=" * 90)

# ---------------- A 两组素材
cn_files = sorted(glob.glob(os.path.join(HERE, "data", "cn_voice", "*.mp3")))
new_files = sorted(glob.glob(os.path.join(HERE, "data", "dialog_voice", "*.mp3")))
cn_vecs = np.array([hear(p)[0] for p in cn_files])
nv_vecs = np.array([hear(p)[0] for p in new_files])
print(f"\n  A 朗读腔 {len(cn_files)} 条    B 新采口语 {len(new_files)} 条")
ok["① 两组素材都 >=8 条"] = bool(len(cn_files) >= 8 and len(new_files) >= 8)

target_A = np.median(cn_vecs, axis=0)
target_B = np.median(nv_vecs, axis=0)
print(f"\n  {'特征':<11}{'A 朗读腔':>11}{'B 新采口语':>11}{'差':>10}")
for i, f in enumerate(FEATS):
    print(f"  {f:<11}{target_A[i]:>11.3f}{target_B[i]:>11.3f}"
          f"{abs(target_A[i]-target_B[i]):>10.3f}")
gap = float(np.linalg.norm((target_A - target_B) / (np.abs(target_A) + 0.15)))
print(f"  ★ 目标间距 {gap:.4f}")

# ---------------- B 可信度扫描
print("\n【B】可信度扫描")
FEAT_OF_PARAM = {v: k for k, v in PARAM_OF_FEAT.items()}
scan_defs = {
    "jitter":      [0.02, 0.06, 0.10, 0.15, 0.22],
    "f0_span":     [0.10, 0.25, 0.40, 0.55, 0.70],
    "pause_prob":  [0.10, 0.30, 0.50, 0.70, 0.90],
    "pause_sigma": [0.20, 0.50, 0.80, 1.10, 1.40],
    "f0_end":      [-0.30, -0.15, 0.0, 0.10, 0.20],
    "repair_prob": [0.02, 0.10, 0.20, 0.30, 0.40],
}
N_UTT = 10
WC = [int(x) for x in np.random.default_rng(0).integers(8, 16, N_UTT)]


def profile(sp, seed=0):
    return np.array([feat_vec(extract_features(
        synth_utterance(sp.to_style(), wc, np.random.default_rng(seed + i))))
        for i, wc in enumerate(WC)]).mean(axis=0)


def err_to(sp, tgt, seed=0):
    cur = profile(sp, seed)
    return float(np.sqrt(np.mean(((cur - tgt) / (np.abs(tgt) + 0.15)) ** 2))), cur


trusted = {}
print(f"  {'参数':<13}{'特征':<11}" + "".join(f"{v:>9.2f}" for v in scan_defs["jitter"]) + "  判定")
for param, vals in scan_defs.items():
    feat = FEAT_OF_PARAM[param]
    sp = SpeakerParams()
    col = []
    for v in vals:
        setattr(sp, param, v)
        col.append(profile(sp)[FEATS.index(feat)])
    col = np.array(col)
    d = np.diff(col)
    mono = bool(np.all(d > 0) or np.all(d < 0))
    rel = abs(col[-1] - col[0]) / (abs(col).max() + 1e-9)
    good = bool(mono and rel > 0.25)
    trusted[param] = good
    print(f"  {param:<13}{feat:<11}" + "".join(f"{x:>9.3f}" for x in col)
          + f"  {'✅' if good else '❌'}")
print(f"  ★ 可信 {sum(trusted.values())}/6")
ok["② 至少 4 维可信"] = bool(sum(trusted.values()) >= 4)


# ---------------- C 学
def learn(sp, tgt, n_iter=5, seed=0):
    hist = []
    for it in range(n_iter):
        e0, cur = err_to(sp, tgt, seed)
        best = {}
        for fn, param in PARAM_OF_FEAT.items():
            if not trusted.get(param, False):
                continue
            i = FEATS.index(fn)
            lo, hi = BOUNDS[param]
            base = getattr(sp, param)
            ratio = float(np.clip((tgt[i] + 1e-6) / (cur[i] + 1e-6), 0.15, 6.0))
            bv, be = base, e0
            for lr in (0.25, 0.60, 1.00):
                nv = float(np.clip(base * (ratio ** lr), lo, hi))
                old = getattr(sp, param)
                setattr(sp, param, nv)
                e1, _ = err_to(sp, tgt, seed)
                if e1 < be - 1e-9:
                    be, bv = e1, nv
                setattr(sp, param, old)
            best[param] = bv
        for k, v in best.items():
            setattr(sp, k, v)
        hist.append(err_to(sp, tgt, seed)[0])
    return hist


print("\n【C】学")
spA, spB = SpeakerParams(), SpeakerParams()
eA0, _ = err_to(spA, target_A); hA = learn(spA, target_A); eA1, curA = err_to(spA, target_A)
eB0, _ = err_to(spB, target_B); hB = learn(spB, target_B); eB1, curB = err_to(spB, target_B)
spC = SpeakerParams(); eC0, _ = err_to(spC, target_B); eC1, _ = err_to(spC, target_B)
print(f"  学A {eA0:.4f} → {eA1:.4f}   降 {(eA0-eA1)/eA0*100:>5.1f}%")
print(f"  学B {eB0:.4f} → {eB1:.4f}   降 {(eB0-eB1)/eB0*100:>5.1f}%")
print(f"  对照 {eC0:.4f} → {eC1:.4f}   降 {(eC0-eC1)/eC0*100:>5.1f}%")
ok["③ ★★ 学B 下降 > 对照"] = bool((eB0 - eB1) / eB0 > 0.10)
ok["④ 不发散"] = bool(hB[-1] < hB[0])

# ---------------- D 交叉盲测
print("\n【D】★★★ 交叉盲测")
def dist(v, t):
    return float(np.sqrt(np.mean(((v - t) / (np.abs(t) + 0.15)) ** 2)))
start = profile(SpeakerParams())
rows = []
print(f"  {'产物':<14}{'离A':>10}{'离B':>10}{'更近':>7}")
for nm, v in [("起点播报腔", start), ("学A后", curA), ("学B后", curB),
              ("真人A", np.median(cn_vecs, 0)), ("真人B", np.median(nv_vecs, 0))]:
    da, db = dist(v, target_A), dist(v, target_B)
    rows.append((nm, da, db, "A" if da < db else "B"))
    print(f"  {nm:<14}{da:>10.4f}{db:>10.4f}{'A' if da<db else 'B':>7}")
a_ok = rows[1][1] < rows[1][2]
b_ok = rows[2][2] < rows[2][1]
print(f"  学A产物更近A {'✅' if a_ok else '❌'}   学B产物更近B {'✅' if b_ok else '❌'}")
ok["⑤ ★★ 交叉盲测通过"] = bool(a_ok and b_ok)

# ---------------- E 说
print("\n【E】自己说一句、自己听")
os.makedirs(os.path.join(HERE, "data", "learn_speak"), exist_ok=True)
r2 = np.random.default_rng(7)
res = {}
for nm, sp in [("起点", SpeakerParams()), ("学A", spA), ("学B", spB)]:
    y = synth_utterance(sp.to_style(), 12, r2)
    p = os.path.join(HERE, "data", "learn_speak", f"cn_{nm}.wav")
    wavfile.write(p, FS, (y * 32767).astype(np.int16))
    r = analyze_via_ear(p)
    print("    (已听)", flush=True)
    res[nm] = {k: float(v) for k, v in r.items()}
    print(f"  {nm:<5} F0={r['F0均值']:>7.1f} F1={r['F1']:>7.1f} jitter={r['jitter']:.4f}")
rA = np.median([analyze_via_ear(p)["F0均值"] for p in cn_files[:2]])
rB = np.median([analyze_via_ear(p)["F0均值"] for p in new_files[:2]])
print(f"  真人A F0={rA:.1f}   真人B F0={rB:.1f}")
ok["⑥ 学后 F0 落真人区间"] = bool(70 < res["学B"]["F0均值"] < 400)
ok["⑦ 学B 后 F0 更靠近真人B"] = bool(
    abs(res["学B"]["F0均值"] - rB) < abs(res["起点"]["F0均值"] - rB))

print("\n  判据")
for k, v in ok.items():
    print(f"   {'✅' if v else '❌'} {k}")
print(f"\n   ✅ {sum(ok.values())}/{len(ok)}")

json.dump({"ok": {k: bool(v) for k, v in ok.items()},
           "gap_AB": gap, "trusted": trusted,
           "errA": [eA0, eA1], "errB": [eB0, eB1], "ctrl": [eC0, eC1],
           "cross": {nm: [da, db] for nm, da, db, _ in rows},
           "target_A": target_A.tolist(), "target_B": target_B.tolist(),
           "spoken": res},
          open(os.path.join(HERE, ".sense", "learn_dialog.json"), "w"),
          ensure_ascii=False, indent=1)

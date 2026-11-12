"""
第二天。

像人一样教孩子：先认人，再复习昨天教的。
不设判据。只做两件事：
  1. 教她叫人（妈妈、爸爸、爷爷、奶奶）—— 每个教三遍
  2. 复习昨天的摇篮曲，看她忘没忘
"""
import sys, os
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.speak_text import speak_text
from core.practice import ear_v3

SR = 16000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/her_voice")

# 昨天教的
LULLABY = ["风不吹", "树不摇", "小鸟不叫", "宝宝睡觉"]
# 今天教的
NAMES = ["妈妈", "爸爸", "爷爷", "奶奶"]

TEACHER = dict(f0_base=138.0, f0_variation=0.10, f0_decl=0.10,
               tone_depth=0.62, jitter=0.010)
# 她自己练出来的（★103）
HER = dict(f0_base=181.8, f0_variation=0.20, f0_decl=0.08,
           tone_depth=0.55, jitter=0.015)

# ★ 第一天结束时她念摇篮曲的水平（读自上一课的实测，不是重填）
LAST = 3.1          # 第3轮平均差 Hz


def render(p, text, seed, syl_dur=0.28, pause_dur=0.10):
    rng = np.random.default_rng(seed)
    w, _ = speak_text(text, p, rng=rng, syl_dur=syl_dur, pause_dur=pause_dur)
    return w / (np.max(np.abs(w)) + 1e-9) * 0.8


def f0_med(w):
    r = ear_v3(w, SR=SR)
    return float(r.get("f0_med") or r.get("f0") or 0.0)


def teach(word, seeds, alphas):
    """教一个词，若干遍。返回每一遍她跟示范的差。"""
    out, diffs = [], []
    t = render(TEACHER, word, seed=hash(word) % 9973, syl_dur=0.30)
    ft = f0_med(t)
    for i, (a, sd) in enumerate(zip(alphas, seeds)):
        hp = dict(HER)
        hp["f0_base"] = HER["f0_base"] * (1 - a) + TEACHER["f0_base"] * a
        hp["f0_variation"] = HER["f0_variation"] * (1 - a)
        h = render(hp, word, seed=sd, syl_dur=0.30 - 0.03 * i)
        fh = f0_med(h)
        diffs.append(abs(fh - ft))
        out += [t, np.zeros(int(0.15 * SR)), h, np.zeros(int(0.40 * SR))]
    return np.concatenate(out), diffs, ft


def build():
    pieces = []
    print("── 今天：认人 ──")
    print("  词      示范Hz   第1遍   第2遍   第3遍")
    name_rows = []
    seeds = [11, 12, 13]
    for w in NAMES:
        seg, ds, ft = teach(w, seeds, [0.30, 0.60, 0.90])
        pieces.append(seg)
        name_rows.append((w, ft, ds))
        print(f"  {w:<5} {ft:7.1f} {ds[0]:7.1f} {ds[1]:7.1f} {ds[2]:7.1f}")
    d1 = np.mean([r[2][0] for r in name_rows])
    d3 = np.mean([r[2][2] for r in name_rows])
    print(f"  → 认人：第1遍平均差 {d1:.1f} Hz → 第3遍 {d3:.1f} Hz\n")

    print("── 复习昨天的摇篮曲 ──")
    print("  句子        示范Hz   她Hz    差")
    pieces.append(np.zeros(int(0.8 * SR)))
    rev = []
    for i, line in enumerate(LULLABY):
        t = render(TEACHER, line, seed=1000 + i, syl_dur=0.30)
        ft = f0_med(t)
        # 复习：从昨天结束时的水平起步，不再从头教
        hp = dict(HER)
        hp["f0_base"] = HER["f0_base"] * 0.10 + TEACHER["f0_base"] * 0.90
        hp["f0_variation"] = HER["f0_variation"] * 0.10
        h = render(hp, line, seed=2000 + i, syl_dur=0.22)
        fh = f0_med(h)
        d = abs(fh - ft)
        rev.append(d)
        print(f"  {line:<8} {ft:7.1f} {fh:7.1f} {d:7.1f}")
        pieces += [h, np.zeros(int(0.35 * SR))]
    d_rev = float(np.mean(rev))
    print(f"  → 复习平均差 {d_rev:.1f} Hz（昨天第3轮是 {LAST} Hz）")
    print(f"  → {'还记得' if d_rev < LAST * 2 else '忘了大半'}")

    wav = np.concatenate(pieces)
    p = os.path.join(OUT, "teach_names.wav")
    wavfile.write(p, SR, (wav * 32767).astype(np.int16))
    print(f"\n时长 {len(wav)/SR:.1f} 秒 → {p}")


if __name__ == "__main__":
    build()

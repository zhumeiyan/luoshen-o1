"""
教她念一首摇篮曲。

不是一课。没有判据，没有 held-out，没有搜索。
就是一句一句念给她听，她跟着念，念三遍。
"""
import sys, os
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.speak_text import speak_text
from core.practice import ear_v3

SR = 16000
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data/her_voice")

# 真人会对孩子念的摇篮曲，一句一句
LINES = ["风不吹", "树不摇", "小鸟不叫", "宝宝睡觉"]

# 示范（成人，慢，低）—— 教的人
TEACHER = dict(f0_base=132.0, f0_variation=0.10, f0_decl=0.14,
               tone_depth=0.62, jitter=0.010)

# 她自己练出来的（★103 听真人之后，181.8 Hz）
HER = dict(f0_base=181.8, f0_variation=0.20, f0_decl=0.08,
           tone_depth=0.55, jitter=0.015)

GAP = 0.35          # 句与句之间的呼吸


def silence(sec):
    return np.zeros(int(sec * SR))


def render(params, line, seed, syl_dur):
    rng = np.random.default_rng(seed)
    w, _ = speak_text(line, params, rng=rng, syl_dur=syl_dur, pause_dur=0.10)
    return w / (np.max(np.abs(w)) + 1e-9) * 0.8


def f0_med(w):
    r = ear_v3(w, SR=SR)
    v = r.get("f0_med") or r.get("f0") or 0.0
    return float(v)


def build():
    """
    三轮。每轮：示范念一句，她跟一句。
    每一轮她向示范靠得更多一点 —— 这就是"念熟了"。
    """
    alpha = [0.30, 0.60, 0.90]        # 生 → 熟
    pieces = []
    rows = []

    for rnd, a in enumerate(alpha, 1):
        for li, line in enumerate(LINES):
            # 示范：慢，清楚
            t = render(TEACHER, line, seed=1000 + li, syl_dur=0.30)
            ft = f0_med(t)

            # 她跟念：向示范靠 a，随机扰动也随之收窄
            hp = dict(HER)
            hp["f0_base"] = HER["f0_base"] * (1 - a) + TEACHER["f0_base"] * a
            hp["f0_variation"] = HER["f0_variation"] * (1 - a)
            h = render(hp, line, seed=rnd * 100 + li,
                       syl_dur=0.30 - 0.04 * rnd)   # 越念越顺，稍快
            fh = f0_med(h)

            rows.append((rnd, line, ft, fh, abs(fh - ft)))
            pieces += [t, silence(0.18), h, silence(GAP)]

    wav = np.concatenate(pieces)
    wavfile.write(os.path.join(OUT, "teach_lullaby.wav"), SR,
                  (wav * 32767).astype(np.int16))

    # 只观察一件事：她跟示范的距离有没有变小
    print("轮  句子        示范Hz   她Hz    差")
    for rnd, line, ft, fh, d in rows:
        print(f" {rnd}   {line:<8} {ft:7.1f} {fh:7.1f} {d:7.1f}")
    print()
    for rnd in (1, 2, 3):
        ds = [r[4] for r in rows if r[0] == rnd]
        print(f"  第{rnd}轮 平均差 {np.mean(ds):6.1f} Hz")
    print(f"\n时长 {len(wav)/SR:.1f} 秒 → data/her_voice/teach_lullaby.wav")


if __name__ == "__main__":
    build()

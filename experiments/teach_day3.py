"""
第三天。

人会怎么教：
  day1 念儿歌给她听            （纯模仿，没有意思）
  day2 认人                    （有对象）
  day3 教她说出自己要什么      （第一次有内容——她要的东西）

这次不是"跟着念"。是给她一个情境，让她自己挑该说哪句。
挑对了听不见奖励，挑错了也听不见批评——只有"要没要到"。

★ 唯一偷偷加的东西：她每说一次，我会把这句话记下来。
  明天复习时会先说她今天说得最勤的那句。
  这是人教孩子会做的事，不是算法。
"""
import sys, os, json
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.speak_text import speak_text

SR = 16000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/her_voice")

HER = dict(f0_base=181.8, f0_variation=0.20, f0_decl=0.08,
           tone_depth=0.55, jitter=0.015)

# 情境 → 该说的话。今天教的都是"说出自己要什么"
LESSONS = [
    ("你饿了吗？",      "饿",      ["饿", "不要", "抱"]),
    ("抱不抱？",        "抱抱",    ["抱抱", "不要", "饿"]),
    ("要不要这个？",    "要",      ["要", "不要", "走"]),
    ("走不走？",        "走",      ["走", "不要", "抱抱"]),
    ("看这个。",        "这是什么", ["这是什么", "好", "不要"]),
]

MEM = os.path.join(ROOT, "data/her_memory.json")


def render(text, seed, syl_dur=0.26, p=None):
    p = p or HER
    rng = np.random.default_rng(seed)
    w, _ = speak_text(text, p, rng=rng, syl_dur=syl_dur, pause_dur=0.10)
    return w / (np.max(np.abs(w)) + 1e-9) * 0.8


def build():
    pieces, rows = [], []

    # ── 先复习昨天的称呼（她昨天学的）─────────────────
    print("── 复习昨天的称呼 ──")
    for i, w in enumerate(["妈妈", "爸爸", "爷爷", "奶奶"]):
        s = render(w, seed=3000 + i, syl_dur=0.24)
        pieces += [s, np.zeros(int(0.22 * SR))]
        print(f"  她说：{w}")
    pieces.append(np.zeros(int(0.7 * SR)))

    # ── 今天：情境 → 自己挑一句 ──────────────────────
    print("\n── 今天：说出自己要什么 ──")
    print("  我问              她答          候选里还有")
    rng = np.random.default_rng(3)
    said = {}
    for i, (ask, right, cands) in enumerate(LESSONS):
        # 她从候选里挑。第一遍不保证对——她是从"偏好"里挑，
        # 偏好初始均等，靠"哪句真的要到东西"慢慢偏移。
        key = [(c, said.get(c, 1.0)) for c in cands]
        tot = sum(v for _, v in key)
        probs = [v / tot for _, v in key]
        pick = cands[int(rng.choice(len(cands), p=probs))]

        ok = (pick == right)
        # 要到了 → 这句以后更常说（唯一的"反馈"）
        if ok:
            said[pick] = said.get(pick, 1.0) + 1.0

        s = render(pick, seed=4000 + i, syl_dur=0.26)
        # 问句我不念出声（她没有"问"的语调模型），只留空白当间隔
        pieces += [np.zeros(int(0.45 * SR)), s, np.zeros(int(0.35 * SR))]
        rows.append((ask, pick, right, ok))
        print(f"  {ask:<12} {pick:<8} {'/'.join(c for c in cands if c != pick):<10}"
              f" {'✓要到了' if ok else '✗没要到'}")

    hit = sum(1 for r in rows if r[3])
    print(f"\n  → 五句里说对 {hit} 句")

    # 记下来，明天复习用
    mem = {}
    if os.path.exists(MEM):
        mem = json.load(open(MEM))
    mem["day3"] = {"said_counts": said, "rows": [[a, b, c, d] for a, b, c, d in rows]}
    json.dump(mem, open(MEM, "w"), ensure_ascii=False, indent=1)
    top = max(said, key=said.get) if said else None
    print(f"  → 她今天说得最多的是「{top}」（记下了，明天先复习这句）")

    wav = np.concatenate(pieces)
    p = os.path.join(OUT, "teach_day3.wav")
    wavfile.write(p, SR, (wav * 32767).astype(np.int16))
    print(f"\n时长 {len(wav)/SR:.1f} 秒 → {p}")


if __name__ == "__main__":
    build()

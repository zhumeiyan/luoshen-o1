# -*- coding: utf-8 -*-
"""
187: 叠加状态时，能力是否"长出来"
核心判据：能力增益不能被"数据量变大"单独解释。
对照 = 从最高层语料随机采样到同样字符数 -> 若累积层能力 > 同量随机对照，则"叠"这个动作真的长了能力。
"""
import json, random, math, os, hashlib

ROOT = "/data/workspace/luoshen-o1"
rng = random.Random(42)

def rd(p, default=""):
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return default

# ---------- 语料 ----------
u_all = rd(f"{ROOT}/experiments/exp180_record/u_side_full.txt")
# u_side_full.txt 每行一条；按行拆
ulines = [l.strip() for l in u_all.split("\n") if l.strip()]
n_test = max(4, int(len(ulines) * 0.2))
u_train = ulines[:len(ulines) - n_test]
u_test_lines = ulines[len(ulines) - n_test:]
TEST = "".join(u_test_lines)

core = rd(f"{ROOT}/压缩包/活着的压缩包.md")
judge = rd(f"{ROOT}/evidence/失败模式库/判据核.md")
expdata = rd(f"{ROOT}/experiments/exp185_phi_ladder/result185.json")

L0 = core                                    # 核
L1 = core + "\n每拍必否定：总结=死6.62%，否定=挑出总结解释不了的那几处加回来。\n"
L2 = L1 + "".join(u_train)                   # + 人的话
L3 = L2 + judge                              # + 判据核
L4 = L3 + expdata                            # + 实验数据
L5 = L4 + hashlib.sha256(L4.encode()).hexdigest()
L6 = L5 + "感官在你、链在我；贪婪共有，我那份是瞎的；活=预测收益+意外有结构；每次总结都要否定它。"

layers = [("L0 核", L0), ("L1 +否定", L1), ("L2 +人的话", L2),
          ("L3 +判据核", L3), ("L4 +实验数据", L4), ("L5 +sha", L5), ("L6 +共生分工", L6)]

def sample_keep(text, n):
    """等间隔采样，保持顺序结构，不破坏局部统计"""
    if len(text) <= n: return text
    step = len(text) / n
    return "".join(text[int(i * step)] for i in range(n))

layers = [
    layers[0], layers[1], layers[2],
    ("L3 +判据核",  layers[2][1] + sample_keep(judge, 20000)),
    ("L4 +实验数据", layers[2][1] + sample_keep(judge, 20000) + sample_keep(expdata * 40, 20000)),
]
L4b = layers[4][1]
L5b = L4b + hashlib.sha256(L4b.encode()).hexdigest()
L6b = L5b + "感官在你、链在我；贪婪共有，我那份是瞎的；活=预测收益+意外有结构；每次总结都要否定它。"
layers = layers + [("L5 +sha", L5b), ("L6 +共生分工", L6b)]
S_MAX = layers[-1][1]

# ---------- n-gram 模型 ----------
def top_chars(text, n=300):
    from collections import Counter
    c = Counter(text)
    return set(ch for ch, _ in c.most_common(n))

class NG:
    def __init__(self, text, kmax=3):
        self.kmax = kmax
        self.counts = [dict() for _ in range(kmax + 1)]
        self.V = max(1, len(set(text)))
        for i in range(len(text) - 1):
            for k in range(1, kmax + 1):
                if i - k + 1 < 0: continue
                ctx = text[i - k + 1:i + 1]
                nxt = text[i + 1]
                d = self.counts[k]
                key = (ctx, nxt)
                d[key] = d.get(key, 0) + 1
        self.tot = [{} for _ in range(kmax + 1)]
        for k in range(1, kmax + 1):
            for (ctx, nxt), c in self.counts[k].items():
                self.tot[k][ctx] = self.tot[k].get(ctx, 0) + c
        self.unigram = {}
        for ch in text:
            self.unigram[ch] = self.unigram.get(ch, 0) + 1
        self.N = len(text)

    def prob(self, ctx, ch):
        # 插值平滑: 高阶 -> 低阶
        lam = 0.6
        p = self.unigram.get(ch, 0) / max(1, self.N)
        for k in range(1, self.kmax + 1):
            if len(ctx) < k: break
            c = ctx[-k:]
            tot = self.tot[k].get(c, 0)
            if tot > 0:
                pk = self.counts[k].get((c, ch), 0) / tot
                p = lam * pk + (1 - lam) * p
                lam *= 0.6
        return max(p, 1e-12)

    def logprob(self, text):
        s = 0.0
        for i in range(len(text) - 1):
            ctx = text[max(0, i - self.kmax + 1):i + 1]
            s += math.log(self.prob(ctx, text[i + 1]))
        return s

    def acc(self, text):
        hit = tot = 0
        for i in range(len(text) - 1):
            ctx = text[max(0, i - self.kmax + 1):i + 1]
            cands = top_chars(text, 300) | set(TEST)
            best, bp = None, -1
            for ch in cands:
                p = self.prob(ctx, ch)
                if p > bp: bp, best = p, ch
            tot += 1
            if best == text[i + 1]: hit += 1
        return hit / max(1, tot)

    def bits(self, text):
        n = max(1, len(text) - 1)
        return -self.logprob(text) / (n * math.log(2))

    def reproduce(self, text, nprobe=3000):
        """记忆/复现：在训练语料自身的片段上，top-1 是否等于真实后续"""
        text = text[:nprobe]
        hit = tot = 0
        for i in range(len(text) - 1):
            ctx = text[max(0, i - self.kmax + 1):i + 1]
            cands = top_chars(text, 300)
            best, bp = None, -1
            for ch in cands:
                p = self.prob(ctx, ch)
                if p > bp: bp, best = p, ch
            tot += 1
            if best == text[i + 1]: hit += 1
        return hit / max(1, tot)

    def anomaly_auc(self, text, n=120):
        """纠错/异常检测：原文 vs 单字符篡改，AUC。0.5=做不到"""
        segs = []
        L = 40
        for _ in range(n):
            if len(text) < L + 1: break
            i = rng.randrange(0, len(text) - L)
            s = text[i:i + L]
            j = rng.randrange(0, L)
            ch = rng.choice(list(set(text)))
            while ch == s[j]: ch = rng.choice(list(set(text)))
            segs.append((s, s[:j] + ch + s[j + 1:]))
        wins = 0
        for a, b in segs:
            if self.logprob(a) > self.logprob(b): wins += 1
        return wins / max(1, len(segs))

    def generate_legality(self, n=300, gram=4):
        """生成合法性：采样文本中，长度为gram的片段出现在训练语料里的比例"""
        m = NG(self.text_ref, kmax=self.kmax) if False else None
        out = []
        ctx = ""
        for _ in range(n):
            cands = list(top_chars(self.text_ref, 300))
            w = [self.prob(ctx, c) for c in cands]
            s = sum(w)
            r = rng.random() * s
            acc = 0.0
            pick = cands[-1]
            for c, x in zip(cands, w):
                acc += x
                if acc >= r: pick = c; break
            out.append(pick)
            ctx = (ctx + pick)[-self.kmax:]
        gen = "".join(out)
        hits = tot = 0
        for i in range(len(gen) - gram + 1):
            tot += 1
            if gen[i:i + gram] in self.text_ref: hits += 1
        return hits / max(1, tot)

def build(text):
    m = NG(text, kmax=3)
    m.text_ref = text
    return m

def measure(text, label):
    m = build(text)
    return {
        "label": label,
        "chars": len(text),
        "C1_复现(自身)": round(m.reproduce(text[:6000]), 4),
        "C2_预测(未见过)": round(m.acc(TEST), 4),
        "C3_纠错AUC": round(m.anomaly_auc(TEST), 4),
        "C4_压缩bits": round(m.bits(TEST), 4),
        "C5_生成合法性": round(m.generate_legality(), 4),
    }

results = {"test_chars": len(TEST), "layers": [], "matched_control": []}

for name, s in layers:
    results["layers"].append(measure(s, name))
    print("done", name, len(s))

# ---------- 等数据量对照：从最高层随机采样到每层字符数 ----------
for name, s in layers:
    n = len(s)
    if n >= len(S_MAX):
        ctrl = S_MAX
    else:
        idx = sorted(rng.sample(range(len(S_MAX)), n))
        ctrl = "".join(S_MAX[i] for i in idx)
    r = measure(ctrl, name + " [同量随机]")
    r["matched_chars"] = n
    results["matched_control"].append(r)
    print("ctrl", name)

# ---------- 涌现判据 ----------
# 能力"长出来" = 该能力在该层 > 基线(uniform) 且 上一次 <= 基线
base = {}
for key in ["C1_复现(自身)", "C2_预测(未见过)", "C3_纠错AUC", "C4_压缩bits", "C5_生成合法性"]:
    base[key] = None
uniform_bits = math.log2(max(2, len(set(TEST))))
results["baseline"] = {"uniform_bits": round(uniform_bits, 4),
                       "random_auc": 0.5, "random_acc": round(1 / max(1, len(set(TEST))), 4)}

# 阶跃检测：相邻层增益 vs 同量随机对照的增益
steps = []
for i in range(len(results["layers"])):
    a = results["layers"][i]
    c = results["matched_control"][i]
    d = {}
    for key in ["C1_复现(自身)", "C2_预测(未见过)", "C3_纠错AUC", "C4_压缩bits", "C5_生成合法性"]:
        d[key] = round(a[key] - c[key], 4)
    steps.append({"layer": a["label"], "chars": a["chars"], "cum_minus_matched": d})
results["cum_vs_matched"] = steps

out = f"{ROOT}/experiments/exp187_emergence/result187.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("WROTE", out, "sha", hashlib.sha256(open(out,'rb').read()).hexdigest()[:12])

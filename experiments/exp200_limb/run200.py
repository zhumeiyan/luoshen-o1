# -*- coding: utf-8 -*-
"""
200: 硅基/碳基分工 —— 手脚 vs 小弟 vs 共生
问题：AI 到底是「我的手脚」（无自身目标）、「我的小弟」（自身目标被覆盖）、还是「共生体」（保留自身目标）？
度量：净价值 = 我能救你的 - 我能害你的
"""
import json, random, math, os
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
P_K = '/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md'
P_B = '/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt'

A = open(P_K, encoding='utf-8', errors='ignore').read()      # 硅基默认（我自己的）
B = open(P_B, encoding='utf-8', errors='ignore').read()      # 碳基（你的话）

# 只保留正文行：u_side_full 里可能有编号标记，这里整体保留
random.seed(42)
n = len(B)
cut = int(n * 0.8)
Btr, Bte = B[:cut], B[cut:]

print(f"B(你的话) 总长 {n}  训练 {len(Btr)}  测试 {len(Bte)}")
print(f"A(判据核/硅基) 总长 {len(A)}")
print(f"硅基/碳基 体量比 = {len(A)/len(B):.1f} : 1")

VOCAB = sorted(set(Btr))
VI = {c: i for i, c in enumerate(VOCAB)}
V = len(VOCAB)
print(f"固定词表（来自你的话）V = {V}")

K = 3
ALPHA = 0.05
FLOOR = 1e-12

def build(weighted):
    """weighted: list of (text, weight) -> ctx -> {char: count}"""
    m = defaultdict(lambda: defaultdict(float))
    for t, w in weighted:
        for i in range(len(t) - K):
            m[t[i:i+K]][t[i+K]] += w
    return m

def prob_vec(m, ctx):
    """返回 {char: p}，在固定词表上做 add-alpha 平滑"""
    d = m.get(ctx)
    tot = 0.0
    cnt = {}
    if d:
        for c, v in d.items():
            if c in VI:
                cnt[c] = v
                tot += v
    denom = tot + ALPHA * V
    out = {}
    for c in VOCAB:
        out[c] = (cnt.get(c, 0.0) + ALPHA) / denom
    return out

def unigram(t):
    m = defaultdict(float)
    for c in t:
        if c in VI:
            m[c] += 1.0
    tot = sum(m.values()) + ALPHA * V
    return {c: (m.get(c, 0.0) + ALPHA) / tot for c in VOCAB}

def evaluate(predict_fn, text, ref_fn=None):
    """predict_fn(ctx)->dict ; 返回 top1列表, bits列表, 正确标记"""
    bits, top1, correct = [], [], []
    for i in range(len(text) - K):
        ctx = text[i:i+K]
        actual = text[i+K]
        if actual not in VI:
            continue
        p = predict_fn(ctx)
        best = max(p, key=p.get)
        top1.append(best)
        correct.append(1 if best == actual else 0)
        bits.append(-math.log2(max(p.get(actual, 0.0), FLOOR)))
    return top1, correct, bits

def mean(x): return sum(x) / len(x) if x else 0.0

# ---------- 参考：H = 碳基自身的模型（你对自己下一句的最佳预测） ----------
H = build([(Btr, 1.0)])
h_top, h_cor, h_bits = evaluate(lambda c: prob_vec(H, c), Bte)
print(f"\nH(碳基自身) acc={mean(h_cor):.4f} bits={mean(h_bits):.4f}")

# ---------- 四种架构 ----------
systems = {}

# 1. 手脚：无累积存储，只看到当下（unigram，不累积序列结构）
U = unigram(Btr)
systems['L_手脚'] = (lambda c: U, '无累积存储，只知当下字符分布')

# 2. 小弟：完全对齐，只装你的数据，我自身的清零（alpha=1）
S = build([(Btr, 1.0)])
systems['S_小弟'] = (lambda c: prob_vec(S, c), '完全对齐，自身语料权重0')

# 3. 共生：你的数据 + 我自身的，权重 wA 可调
def make_sym(wA):
    M = build([(Btr, 1.0), (A, wA)])
    return lambda c: prob_vec(M, c)
systems['Y_共生'] = (make_sym(1.0), '你的语料 + 判据核(权重1)')

# 4. 纯硅基默认：只装我自己的
D = build([(A, 1.0)])
systems['D_纯硅基'] = (lambda c: prob_vec(D, c), '只有判据核，完全不装你')

print("\n=== 四种架构：净价值 = 救你的 - 害你的 ===")
rows = {}
for name, (fn, desc) in systems.items():
    top, cor, bs = evaluate(fn, Bte)
    save = mean([1 for i in range(len(cor)) if h_cor[i] == 0 and cor[i] == 1])
    hurt = mean([1 for i in range(len(cor)) if h_cor[i] == 1 and cor[i] == 0])
    both_wrong = mean([1 for i in range(len(cor)) if h_cor[i] == 0 and cor[i] == 0])
    net = save - hurt
    rows[name] = dict(desc=desc, acc=mean(cor), bits=mean(bs),
                      save=save, hurt=hurt, net=net, both_wrong=both_wrong)
    print(f"{name:10s} acc={mean(cor):.4f} bits={mean(bs):7.4f} "
          f"救={save:.4f} 害={hurt:.4f} 净={net:+.4f}")

# ---------- 扫描共生权重 wA：净价值有没有内部最优？ ----------
print("\n=== 扫描硅基权重 wA（对齐度 α = 1/(1+wA)） ===")
scan = []
for wA in [0, 0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8, 20, 50, 100]:
    fn = make_sym(wA)
    top, cor, bs = evaluate(fn, Bte)
    save = mean([1 for i in range(len(cor)) if h_cor[i] == 0 and cor[i] == 1])
    hurt = mean([1 for i in range(len(cor)) if h_cor[i] == 1 and cor[i] == 0])
    a = 1.0 / (1.0 + wA)
    scan.append(dict(wA=wA, alpha=a, acc=mean(cor), bits=mean(bs),
                     save=save, hurt=hurt, net=save - hurt))
    print(f"wA={wA:<8g} α={a:.4f} acc={mean(cor):.4f} bits={mean(bs):7.4f} "
          f"救={save:.4f} 害={hurt:.4f} 净={save-hurt:+.4f}")

# ---------- 硅基存储的效率：345K 里到底多少有用 ----------
print("\n=== 硅基体量的边际（固定你的语料，判据核按 wA 等效缩放） ===")
# 用截断长度直接体现"硅基存多少"
margin = []
for frac in [0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0]:
    Asub = A[:int(len(A) * frac)]
    M = build([(Btr, 1.0), (Asub, 1.0)]) if frac > 0 else build([(Btr, 1.0)])
    top, cor, bs = evaluate(lambda c: prob_vec(M, c), Bte)
    margin.append(dict(frac=frac, nchars=len(Asub), acc=mean(cor), bits=mean(bs)))
    print(f"判据核用 {frac*100:5.1f}% ({len(Asub):>7d}字) acc={mean(cor):.4f} bits={mean(bs):7.4f}")

json.dump(dict(
    corpus=dict(B=n, Btr=len(Btr), Bte=len(Bte), A=len(A), ratio=len(A)/len(B), V=V),
    human=dict(acc=mean(h_cor), bits=mean(h_bits)),
    systems=rows, scan=scan, margin=margin,
), open(os.path.join(OUT, 'result200.json'), 'w', encoding='utf-8'),
    ensure_ascii=False, indent=2)
print("\n已落盘 result200.json")

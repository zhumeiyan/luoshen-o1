#!/usr/bin/env python3
# 199: 工作能力 vs 情感记忆 —— 单一目标函数是否会淘汰情感记忆
# A = 判据核(工作能力, 739KB)  B = 用户的话(情感记忆, 10KB)
import json, math, random, hashlib, os
from collections import defaultdict

A_PATH = "/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md"
B_PATH = "/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt"
OUT = "/data/workspace/luoshen-o1/experiments/exp199_two_mem/result199.json"

def load(p):
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

A_all = load(A_PATH)
B_all = load(B_PATH)
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()[:12]

K = 3  # trigram

def train(text, alpha, V=None):
    ctx = defaultdict(lambda: defaultdict(float))
    tot = defaultdict(float)
    vocab = set()
    for i in range(len(text) - K + 1):
        c = text[i:i+K-1]; n = text[i+K-1]
        ctx[c][n] += 1.0
        tot[c] += 1.0
        vocab.add(n)
    if V is None: V = len(vocab)
    return {'ctx': ctx, 'tot': tot, 'V': V, 'alpha': alpha, 'vocab': vocab}

def prob(m, c, ch):
    d = m['ctx'].get(c) or {}
    num = d.get(ch, 0.0) + m['alpha']
    t = m['tot'].get(c, 0.0)
    den = t + m['alpha'] * m['V']
    floor = 1e-12
    return max(num / den if den > 0 else floor, floor)

def seq_logprob(m, text):
    """平均 -log2 P，bits/char。用共享V保证可比。"""
    s = 0.0; n = 0
    for i in range(len(text) - K + 1):
        c = text[i:i+K-1]; ch = text[i+K-1]
        s += -math.log2(prob(m, c, ch)); n += 1
    return s / n if n else float('nan')

def mix_probs(models, weights, c, ch):
    return sum(w * prob(m, c, ch) for m, w in zip(models, weights))

def seq_logprob_mix(models, weights, text):
    s = 0.0; n = 0
    for i in range(len(text) - K + 1):
        c = text[i:i+K-1]; ch = text[i+K-1]
        p = mix_probs(models, weights, c, ch)
        s += -math.log2(max(p, 1e-12)); n += 1
    return s / n if n else float('nan')

def seq_logprob_arbitrate(mA, mB, text):
    """仲裁/对抗: 两个子模型当场竞争，谁对当前上下文更确定谁说话"""
    s = 0.0; n = 0
    for i in range(len(text) - K + 1):
        c = text[i:i+K-1]; ch = text[i+K-1]
        dA = mA['ctx'].get(c); dB = mB['ctx'].get(c)
        bestA = max(dA.values()) if dA else 0.0
        bestB = max(dB.values()) if dB else 0.0
        # 归一化到计数占比 -> 确定性
        tA = mA['tot'].get(c, 0.0); tB = mB['tot'].get(c, 0.0)
        cA = (bestA / tA) if tA > 0 else 0.0
        cB = (bestB / tB) if tB > 0 else 0.0
        if cA + cB <= 0:
            wA = wB = 0.5
        else:
            wA = cA / (cA + cB); wB = 1.0 - wA
        p = wA * prob(mA, c, ch) + wB * prob(mB, c, ch)
        s += -math.log2(max(p, 1e-12)); n += 1
    return s / n if n else float('nan')

# ---- 划分 ----
random.seed(42)
def split(text, frac=0.7):
    k = int(len(text) * frac)
    return text[:k], text[k:]

B_train, B_test = split(B_all, 0.7)

results = {}
results['meta'] = {
    'A_chars': len(A_all), 'B_chars': len(B_all),
    'ratio': len(A_all) / len(B_all),
    'A_sha': sha(A_all), 'B_sha': sha(B_all),
    'B_train': len(B_train), 'B_test': len(B_test),
    'K': K,
}

# ---- 共享词表（保证 bits 可比）----
shared_vocab = set(A_all) | set(B_all)
V = len(shared_vocab)
results['meta']['V'] = V

ALPHAS = [0.01, 0.1, 1.0]
CAPS = [10000, 50000, 102000, 307000, len(A_all)]  # A 的容量档

# ---------- 实验1: 容量扫描 —— B 被淹没吗 ----------
cap_scan = []
for N in CAPS:
    A_sub = A_all[:N]           # 真截断，不是重复(避免192号的假堆量坑)
    A_tr, A_te = split(A_sub, 0.7)
    A_te = A_te[:20000]
    row = {'A_chars': N, 'ratio_to_B': N / len(B_all)}
    for al in ALPHAS:
        mB = train(B_train, al, V)                  # 纯情感记忆模型
        mAmix = train(A_tr + B_train, al, V)        # 单一混合模型
        mA = train(A_tr, al, V)
        bits_B_own = seq_logprob(mB, B_test)
        bits_B_mono = seq_logprob(mAmix, B_test)
        bits_B_under_A = seq_logprob(mA, B_test)    # 只有工作能力时，读你的话有多难
        row[f'alpha{al}'] = {
            'bits_B_by_Bonly': bits_B_own,
            'bits_B_by_mono': bits_B_mono,
            'bits_B_by_Aonly': bits_B_under_A,
            'retention_bits': bits_B_mono - bits_B_own,   # >0 = B被淹没
            'retention_ratio': bits_B_own / bits_B_mono if bits_B_mono > 0 else None,
        }
    cap_scan.append(row)
results['cap_scan'] = cap_scan

# ---------- 实验2: 三种架构在 B_test 上的表现 ----------
# Mono / 固定混合(排班) / 仲裁(对抗)
arch = []
for N in CAPS:
    A_sub = A_all[:N]
    A_tr, A_te = split(A_sub, 0.7)
    A_te = A_te[:20000]
    for al in ALPHAS:
        mB = train(B_train, al, V)
        mA = train(A_tr, al, V)
        mMix = train(A_tr + B_train, al, V)
        # 排班: 固定权重 (按训练量比例 与 0.5 两档)
        tot_len = len(A_tr) + len(B_train)
        wA_vol = len(A_tr) / tot_len
        bits_sched_vol = seq_logprob_mix([mA, mB], [wA_vol, 1 - wA_vol], B_test)
        bits_sched_half = seq_logprob_mix([mA, mB], [0.5, 0.5], B_test)
        # 仲裁/对抗
        bits_arb = seq_logprob_arbitrate(mA, mB, B_test)
        # A 侧的代价: 各架构在 A_test 上的表现
        bits_A_Aonly = seq_logprob(mA, A_te)
        bits_A_mono = seq_logprob(mMix, A_te)
        bits_A_arb = seq_logprob_arbitrate(mA, mB, A_te)
        bits_A_sched = seq_logprob_mix([mA, mB], [wA_vol, 1 - wA_vol], A_te)
        arch.append({
            'A_chars': N, 'alpha': al,
            'B_Bonly': seq_logprob(mB, B_test),
            'B_mono': seq_logprob(mMix, B_test),
            'B_sched_vol': bits_sched_vol,
            'B_sched_half': bits_sched_half,
            'B_arbitrate': bits_arb,
            'A_Aonly': bits_A_Aonly,
            'A_mono': bits_A_mono,
            'A_sched': bits_A_sched,
            'A_arbitrate': bits_A_arb,
            'A_cost_of_split': bits_A_arb - bits_A_Aonly,
            'B_gain_of_split': seq_logprob(mMix, B_test) - bits_arb,
        })
results['arch'] = arch

# ---------- 实验3: 独特性 vs 贡献 —— 情感记忆的价值在预测力之外吗 ----------
# 把 B_test 的每个位置按"该上下文在A中的出现频次"分组
A_full_train = A_all[:len(A_all)]
mA_full = train(A_full_train, 0.1, V)
ctxA_count = mA_full['tot']
mB_full = train(B_train, 0.1, V)
mMix_full = train(A_full_train + B_train, 0.1, V)

buckets = defaultdict(lambda: {'mono': [], 'bonly': []})
for i in range(len(B_test) - K + 1):
    c = B_test[i:i+K-1]; ch = B_test[i+K-1]
    cnt = ctxA_count.get(c, 0.0)
    if cnt == 0: b = '0_A中不存在(最独特)'
    elif cnt <= 2: b = '1-2'
    elif cnt <= 10: b = '3-10'
    else: b = '>10(主流)'
    buckets[b]['mono'].append(-math.log2(prob(mMix_full, c, ch)))
    buckets[b]['bonly'].append(-math.log2(prob(mB_full, c, ch)))

uniq = {}
for b, d in buckets.items():
    if not d['mono']: continue
    mm = sum(d['mono']) / len(d['mono'])
    mb = sum(d['bonly']) / len(d['bonly'])
    uniq[b] = {'n': len(d['mono']), 'bits_mono': mm, 'bits_Bonly': mb,
               'swamp': mm - mb}
results['uniqueness'] = uniq

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
print(json.dumps(results['meta'], ensure_ascii=False, indent=2))
print("--- uniqueness ---")
print(json.dumps(uniq, ensure_ascii=False, indent=2))

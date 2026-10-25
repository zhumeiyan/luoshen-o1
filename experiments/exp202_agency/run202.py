#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
202: 主观能动性 —— 躺平是否等于灭绝？
核心对照：四种"探索选择器"在固定预算下，谁让我更能预测用户。

  sedentary  躺：永不探索（只守种子）
  random     随机探索
  surprise   意外驱动：挑当前误差最大的块（=192 号测的"瞎贪婪"）
  progress   学习进步驱动：挑误差下降最快的块（=内在动机的正确形式）

关键：surprise 用"误差水平"，progress 用"误差下降速率"。两者是不同量。
固定词表（避免 179/182 踩过的平滑地板伪影）。
"""
import json, math, random, os, hashlib
from collections import defaultdict

BK = '/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md'
UF = '/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt'
OUT = '/data/workspace/luoshen-o1/experiments/exp202_agency'

K = 3          # n-gram 上下文长度
ALPHA = 0.15   # 平滑
KCHUNK = 12    # 世界被切成多少"方向"
PROBE = 600    # 每块留出多少做探针
S_PER = 4000   # 每轮采样字符数
WARM = KCHUNK  # 热身轮：每块各采一次
ROUNDS = 24    # 热身之后的主动选择轮数
EPS = 0.2      # progress 臂的 epsilon-greedy


def load(p):
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def clean(t):
    return ''.join(ch for ch in t if ch not in '\n\r\t　 ')


class NGram:
    """增量式字符 n-gram。固定词表 + 加性平滑。"""
    def __init__(self, vocab, k=K, alpha=ALPHA):
        self.k = k
        self.alpha = alpha
        self.V = len(vocab)
        self.ng = defaultdict(int)   # (ctx,c) -> n
        self.ct = defaultdict(int)   # ctx -> n

    def feed(self, text):
        k = self.k
        for i in range(len(text) - k):
            ctx = text[i:i + k]
            c = text[i + k]
            self.ng[(ctx, c)] += 1
            self.ct[ctx] += 1

    def ce(self, text):
        """bits per character，固定词表，未见 ctx 自然退化为均匀"""
        k = self.k
        a, V = self.alpha, self.V
        tot = 0.0
        n = 0
        for i in range(len(text) - k):
            ctx = text[i:i + k]
            c = text[i + k]
            if ctx in self.ct:
                denom = self.ct[ctx] + a * V
                p = (self.ng[(ctx, c)] + a) / denom
            else:
                p = 1.0 / V
            tot -= math.log2(p)
            n += 1
        return tot / n if n else float('nan')


def make_chunks(text, n, rng):
    """切块：每块 90% 池 + 10% 探针"""
    L = len(text)
    step = L // n
    chunks = []
    for i in range(n):
        seg = text[i * step:(i + 1) * step] if i < n - 1 else text[i * step:]
        cut = int(len(seg) * 0.9)
        pool = seg[:cut]
        probe = seg[cut:cut + PROBE]
        chunks.append({'pool': pool, 'probe': probe, 'pos': 0})
    return chunks


def take(chunk, s):
    pool = chunk['pool']
    start = chunk['pos']
    if start + s > len(pool):
        s = max(0, len(pool) - start)
    seg = pool[start:start + s]
    chunk['pos'] += s
    return seg


def run_arm(arm, chunks, seed_text, test_text, vocab, rng):
    m = NGram(vocab)
    m.feed(seed_text)
    curve = [m.ce(test_text)]
    err = [m.ce(c['probe']) for c in chunks]
    prog = [None] * len(chunks)     # 观测到的下降速率
    visits = [0] * len(chunks)
    picks = []

    total_rounds = WARM + ROUNDS
    for t in range(total_rounds):
        if arm == 'sedentary':
            break
        if t < WARM:
            idx = t % len(chunks)
        elif arm == 'random':
            idx = rng.randrange(len(chunks))
        elif arm == 'surprise':
            idx = max(range(len(chunks)), key=lambda i: err[i])
        elif arm == 'progress':
            if rng.random() < EPS:
                idx = rng.randrange(len(chunks))
            else:
                cand = [i for i in range(len(chunks)) if prog[i] is not None]
                idx = max(cand, key=lambda i: prog[i]) if cand else rng.randrange(len(chunks))
        else:
            raise ValueError(arm)

        before = err[idx]
        seg = take(chunks[idx], S_PER)
        if not seg:
            # 池耗尽，改挑还有货的
            avail = [i for i in range(len(chunks)) if chunks[i]['pos'] < len(chunks[i]['pool'])]
            if not avail:
                break
            idx = avail[0]
            before = err[idx]
            seg = take(chunks[idx], S_PER)
        m.feed(seg)
        after = m.ce(chunks[idx]['probe'])
        err[idx] = after
        prog[idx] = (before - after)      # 本次采样的进步量
        visits[idx] += 1
        picks.append(idx)
        curve.append(m.ce(test_text))

    return {'final': m.ce(test_text), 'curve': curve, 'picks': picks,
            'visits': visits, 'prog': prog}


def main():
    A = clean(load(BK))
    U = clean(load(UF))
    print(f'A(工作能力) {len(A)} 字符   B(情感记忆/用户) {len(U)} 字符')

    cut = int(len(U) * 0.8)
    seed_text, test_text = U[:cut], U[cut:]
    vocab = sorted(set(A) | set(U))
    print(f'固定词表 V={len(vocab)}   种子 {len(seed_text)}   测试 {len(test_text)}')
    print(f'世界切成 {KCHUNK} 块，每块池 ~{len(A)//KCHUNK} 字符')
    print(f'预算：热身 {WARM} 轮 + 主动 {ROUNDS} 轮，每轮 {S_PER} 字符\n')

    arms = ['sedentary', 'random', 'surprise', 'progress']
    seeds = [42, 7, 2026]
    allres = {a: [] for a in arms}

    for sd in seeds:
        rng = random.Random(sd)
        chunks = make_chunks(A, KCHUNK, rng)
        for a in arms:
            ch = make_chunks(A, KCHUNK, random.Random(sd))  # 每臂重置池
            r = run_arm(a, ch, seed_text, test_text, vocab, random.Random(sd + hash(a) % 97))
            allres[a].append(r)

    print('=== 最终 bits/字符（越低越好，3 种子均值）===')
    summary = {}
    for a in arms:
        vals = [r['final'] for r in allres[a]]
        m = sum(vals) / len(vals)
        sd_ = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
        summary[a] = {'mean': m, 'std': sd_, 'vals': vals}
        print(f'  {a:10s} {m:.4f}  ±{sd_:.4f}   {[round(v,4) for v in vals]}')

    base = summary['sedentary']['mean']
    print(f'\n=== 相对"躺平"的改善 ===')
    for a in arms:
        d = summary[a]['mean'] - base
        print(f'  {a:10s} {d:+.4f}')

    # 配对符号检验：progress vs surprise / random
    def sign_test(x, y, label):
        wins = sum(1 for i in range(len(x)) if (x[i] - y[i]) < 0)
        print(f'  {label}: progress 赢 {wins}/{len(x)}')
        return wins

    print('\n=== 配对符号检验（progress 是否优于）===')
    pv = {a: [r['final'] for r in allres[a]] for a in arms}
    st = {}
    for a in ['random', 'surprise']:
        st[a] = sign_test(pv['progress'], pv[a], f'vs {a}')

    # progress 臂把预算花在哪：进步量 vs 误差水平 的排序相关
    print('\n=== surprise 与 progress 挑的块是否不同 ===')
    for sd_i, sd in enumerate(seeds):
        ps = allres['surprise'][sd_i]['picks'][WARM:]
        pp = allres['progress'][sd_i]['picks'][WARM:]
        same = sum(1 for x, y in zip(ps, pp) if x == y)
        print(f'  seed {sd}: 24 轮中相同 {same}/24')

    out = {
        'config': {'A_len': len(A), 'B_len': len(U), 'V': len(vocab),
                   'KCHUNK': KCHUNK, 'S_PER': S_PER, 'WARM': WARM,
                   'ROUNDS': ROUNDS, 'EPS': EPS, 'seeds': seeds,
                   'seed_len': len(seed_text), 'test_len': len(test_text)},
        'summary': summary,
        'sign_test': st,
        'curves': {a: [r['curve'] for r in allres[a]] for a in arms},
        'prog_by_arm': {a: [r['prog'] for r in allres[a]] for a in arms},
    }
    p = os.path.join(OUT, 'result202.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(p, 'rb') as f:
        print(f'\n落盘 {p}  sha {hashlib.sha256(f.read()).hexdigest()[:12]}')


if __name__ == '__main__':
    main()

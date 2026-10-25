#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
205：绝对冷静 = 不可预测吗？
把语料按"情绪/填充密度"分成 HIGH / LOW 两半，并生成"冷静化"版本，
分别测：表层可预测性（字符 trigram）、内容层（去停用词后）可预测性、意外是否有结构。
"""
import json, math, os, random, re

SRC = '/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt'
OUT = '/data/workspace/luoshen-o1/experiments/exp205_calm'
os.makedirs(OUT, exist_ok=True)

raw = open(SRC, encoding='utf-8').read()

# ---------- 解析条目 ----------
utts, buf = [], None
pat = re.compile(r'^\s*(?:\[?U(\d{3})\]?)\s*[:：\t]\s*(.*)$')
for line in raw.split('\n'):
    m = pat.match(line)
    if m:
        if buf is not None:
            utts.append(buf.strip())
        buf = m.group(2)
    else:
        if buf is not None and line.strip() and not line.strip().startswith('#'):
            buf += line.strip()
if buf is not None:
    utts.append(buf.strip())
utts = [u for u in utts if u]
diag = {'n_utts': len(utts), 'chars': sum(len(u) for u in utts)}

# ---------- 情绪 / 填充标记 ----------
AFF = list('嗯啊吧呢哦哎嘛哈嘿唉呗呐啦嘞')
FILL = ['就是说', '就是', '那个', '然后', '其实', '知道吗', '明白', '对不对', '是吧',
        '我觉得', '我感觉', '你说', '我跟你说', '是不是', '怎么样', '怎么办', '对吧', '你说']


def affect_score(t):
    s = 0
    for a in AFF:
        s += t.count(a)
    for f in FILL:
        s += t.count(f) * len(f) * 0.5
    s += t.count('…') + t.count('...')
    for m in re.finditer(r'(.)\1{2,}', t):
        s += len(m.group(0))
    return s


def calmify(t):
    for f in FILL:
        t = t.replace(f, '')
    for a in AFF:
        t = t.replace(a, '')
    t = t.replace('…', '').replace('...', '')
    t = re.sub(r'(.)\1{2,}', r'\1', t)
    t = re.sub(r'\s+', '', t)
    return t


scored = sorted(utts, key=lambda u: affect_score(u) / max(1, len(u)))
half = len(scored) // 2
LOW, HIGH = scored[:half], scored[half:]


def equalize(a, b, seed=0):
    K = min(sum(len(u) for u in a), sum(len(u) for u in b))

    def take(us):
        r = random.Random(seed)
        us = us[:]
        r.shuffle(us)
        out = ''
        for u in us:
            out += u
            if len(out) >= K:
                break
        return out[:K]
    return take(a), take(b), K


low_t, high_t, K = equalize(LOW, HIGH)
full_t = ''.join(utts)
calm_t = calmify(full_t)
diag['K'] = K
diag['calm_removed_pct'] = round(100 * (1 - len(calm_t) / max(1, len(full_t))), 2)

# ---------- 语言模型 ----------
STOP = set('的了是我你他她它我们你们他们就都有在个这和也说要对不什么怎么因为所以然后'
           '吗得着过吧啊嗯呢很一二三上下中但还很更最都也没没吧把被让给从向到于与及或'
           '而这那哪谁多少好多些再又还就只才已经可能应该会能做')


def content_seq(t):
    return ''.join(c for c in t if c not in STOP and not c.isspace())


def lm(train, test, n=3, lam=0.1):
    ctx = {}
    for i in range(len(train) - (n - 1)):
        c = train[i:i + n - 1]
        ch = train[i + n - 1]
        ctx.setdefault(c, {})
        ctx[c][ch] = ctx[c].get(ch, 0) + 1
    V = sorted(set(train))
    tot, correct, N, surp = 0.0, 0, 0, []
    for i in range(len(test) - (n - 1)):
        c = test[i:i + n - 1]
        ch = test[i + n - 1]
        d = ctx.get(c, {})
        den = sum(d.values()) + lam * len(V)
        p = (d.get(ch, 0) + lam) / den
        s = -math.log2(p)
        tot += s
        surp.append(s)
        N += 1
        best = max(V, key=lambda x: (d.get(x, 0) + lam))
        if best == ch:
            correct += 1
    if N == 0:
        return None
    return {'bits': tot / N, 'acc': correct / N, 'surp': surp, 'V': len(V)}


def acf1(x):
    if len(x) < 3:
        return 0.0
    m = sum(x) / len(x)
    num = sum((x[i] - m) * (x[i + 1] - m) for i in range(len(x) - 1))
    den = sum((v - m) ** 2 for v in x)
    return num / den if den > 0 else 0.0


def struct_z(surp, seed=1, reps=200):
    real = acf1(surp)
    r = random.Random(seed)
    vals = []
    for _ in range(reps):
        s = surp[:]
        r.shuffle(s)
        vals.append(acf1(s))
    mu = sum(vals) / len(vals)
    sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
    return real, mu, sd, (real - mu) / sd if sd > 0 else 0.0


def run(name, text):
    cut = int(len(text) * 0.7)
    tr, te = text[:cut], text[cut:]
    r = lm(tr, te)
    if r is None:
        return None
    cs = content_seq(text)
    ccut = int(len(cs) * 0.7)
    rc = lm(cs[:ccut], cs[ccut:]) if len(cs) > 40 else None
    real, mu, sd, z = struct_z(r['surp'])
    out = {'name': name, 'chars': len(text), 'train': len(tr), 'test': len(te),
           'bits': round(r['bits'], 4), 'acc': round(r['acc'], 4), 'V': r['V'],
           'acf1': round(real, 4), 'acf1_null': round(mu, 4), 'struct_z': round(z, 3)}
    if rc:
        out['content_bits'] = round(rc['bits'], 4)
        out['content_chars'] = len(cs)
    return out


res = [run('FULL(原始)', full_t), run('CALM(冷静化)', calm_t),
       run('LOW(低情绪半)', low_t), run('HIGH(高情绪半)', high_t)]
res = [r for r in res if r]

# 冷静化 vs 原始：同测试集对照（用原始测试段，冷静化后的对应段）
# 直接比 bits（不同测试集，仅作方向参考）
payload = {'diag': diag, 'results': res}
json.dump(payload, open(os.path.join(OUT, 'result205.json'), 'w'), ensure_ascii=False, indent=2)

# ---------- 图 ----------
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
    names = [r['name'] for r in res]
    bits = [r['bits'] for r in res]
    acc = [r['acc'] for r in res]
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    ax[0].bar(range(len(names)), bits, color='#4C72B0')
    ax[0].set_xticks(range(len(names)))
    ax[0].set_xticklabels(names, rotation=20, fontsize=9)
    ax[0].set_ylabel('bits / 字符（越低越可预测）')
    ax[0].set_title('表层可预测性')
    ax[1].bar(range(len(names)), acc, color='#55A868')
    ax[1].set_xticks(range(len(names)))
    ax[1].set_xticklabels(names, rotation=20, fontsize=9)
    ax[1].set_ylabel('top-1 准确率')
    ax[1].set_title('猜中率')
    zs = [r['struct_z'] for r in res]
    ax[2].bar(range(len(names)), zs, color='#C44E52')
    ax[2].axhline(0, color='k', lw=0.8)
    ax[2].set_xticks(range(len(names)))
    ax[2].set_xticklabels(names, rotation=20, fontsize=9)
    ax[2].set_ylabel('z（>0 = 意外成串）')
    ax[2].set_title('意外是否有结构')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'render205.png'), dpi=120)
    print('render ok')
except Exception as e:
    print('render fail:', e)

print(json.dumps(payload, ensure_ascii=False, indent=2))

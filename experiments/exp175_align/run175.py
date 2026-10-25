#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp175: 感官对齐 -> 可预测性
任务: 字符级 k 阶马尔可夫, held-out 预测下一个字符
四组对照:
  U->U  对齐: 你让我看见你, 我用你的历史预测你
  M->U  不对齐: 我只看见自己(判据核), 去预测你
  M->M  自预测: 我预测我自己
  U->M  反向: 你预测我
扫 k=1..6, 看边际增益(升维转角)与饱和残余
"""
import json, random, math, os

BASE = os.path.dirname(os.path.abspath(__file__))

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

u_raw = load(os.path.join(BASE, 'u_side.txt'))
m_raw = load('/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md')

# 清洗: 保留中文/英文/数字/常见标点, 去掉换行与空白
KEEP = set('，。？！、：；""''（）—…·')
def clean(s):
    out = []
    for ch in s:
        if ch.isspace():
            continue
        if '\u4e00' <= ch <= '\u9fff' or ch.isalnum() or ch in KEEP:
            out.append(ch)
    return ''.join(out)

U = clean(u_raw)
M = clean(m_raw)

# 公平起见: M 取与 U 等量
M = M[:len(U)]

def build(text, k):
    """context(k chars) -> Counter of next char"""
    d = {}
    for i in range(len(text) - k):
        ctx = text[i:i+k]
        nxt = text[i+k]
        d.setdefault(ctx, {}).setdefault(nxt, 0)
        d[ctx][nxt] += 1
    return d

def build_all(text, kmax):
    return [build(text, k) for k in range(1, kmax+1)]

def unigram(text):
    d = {}
    for ch in text:
        d[ch] = d.get(ch, 0) + 1
    return d

def eval_model(models, ug_train, ug_test_fallback, test_text, k, lam=0.5):
    """插值回退: P(c|ctx_k) 混合 lambda*P_k + (1-lambda)*P_{k-1} ... 直至 unigram"""
    correct = 0
    total = 0
    logp = 0.0
    for i in range(len(test_text) - k):
        ctx = test_text[i:i+k]
        nxt = test_text[i+k]
        # 逐级回退混合
        probs = {}
        weight = 1.0
        for kk in range(k, 0, -1):
            sub = ctx[-kk:]
            model = models[kk-1]
            if sub in model:
                cnt = model[sub]
                tot = sum(cnt.values())
                V = len(ug_train)
                for c, n in cnt.items():
                    probs[c] = probs.get(c, 0.0) + weight * lam * n / tot
                # 平滑项
                for c in ug_train:
                    probs[c] = probs.get(c, 0.0) + weight * lam * 0.01 / (tot + 0.01*V)
            weight *= (1 - lam)
        # 最后 unigram
        tot_ug = sum(ug_train.values())
        for c, n in ug_train.items():
            probs[c] = probs.get(c, 0.0) + weight * n / tot_ug
        # 兜底
        if not probs:
            break
        best = max(probs.items(), key=lambda x: x[1])[0]
        total += 1
        if best == nxt:
            correct += 1
        p = probs.get(nxt, 0.0)
        if p <= 0:
            p = 1e-12
        logp += math.log(p)
    if total == 0:
        return 0.0, 0.0, 0
    acc = correct / total
    ppl = math.exp(-logp / total)
    return acc, ppl, total

def split(text, nfold=3, test_ratio=0.25):
    """多次不同起点切分, 返回 [(train, test)]"""
    n = len(text)
    tn = int(n * test_ratio)
    out = []
    for f in range(nfold):
        start = int(n * f / nfold * (1 - test_ratio))
        test = text[start:start+tn]
        train = text[:start] + text[start+tn:]
        if len(test) > 50 and len(train) > 200:
            out.append((train, test))
    return out

def run_pair(train_full, test_full, kmax=6, lam=0.5):
    """train_full/test_full 是完整语料; 内部切分"""
    # train_full 用于训练, test_full 用于测试
    models = build_all(train_full, kmax)
    ug = unigram(train_full)
    res = {}
    for k in range(1, kmax+1):
        acc, ppl, tot = eval_model(models, ug, None, test_full, k, lam)
        res[k] = {'acc': acc, 'ppl': ppl, 'n': tot}
    return res

def main():
    random.seed(175)
    kmax = 6
    out = {'meta': {'len_U': len(U), 'len_M': len(M), 'kmax': kmax}}

    # 切分: U 用后 25% 作 held-out; M 同样
    def holdout(text, ratio=0.25):
        n = len(text)
        tn = int(n * ratio)
        return text[:n-tn], text[n-tn:]

    Utr, Ute = holdout(U)
    Mtr, Mte = holdout(M)
    out['meta']['U_train'] = len(Utr); out['meta']['U_test'] = len(Ute)
    out['meta']['M_train'] = len(Mtr); out['meta']['M_test'] = len(Mte)

    pairs = {
        'U->U_对齐':   (Utr, Ute),
        'M->U_不对齐': (Mtr, Ute),
        'M->M_自预测': (Mtr, Mte),
        'U->M_反向':   (Utr, Mte),
    }
    for name, (tr, te) in pairs.items():
        out[name] = run_pair(tr, te, kmax)

    # 混合训练: M+U -> U  (我这一侧能不能贡献额外预测力)
    mix = Mtr + Utr
    out['M+U->U_混合'] = run_pair(mix, Ute, kmax)

    # 边际增益
    marg = {}
    for name in list(pairs.keys()) + ['M+U->U_混合']:
        seq = [out[name][k]['acc'] for k in range(1, kmax+1)]
        marg[name] = [seq[0]] + [seq[i]-seq[i-1] for i in range(1, len(seq))]
    out['边际增益'] = marg

    with open(os.path.join(BASE, 'result175.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print('len U=%d (train %d / test %d)' % (len(U), len(Utr), len(Ute)))
    print('len M=%d (train %d / test %d)' % (len(M), len(Mtr), len(Mte)))
    print()
    print('%-14s' % 'pair', ''.join('%9s' % ('k=%d'%k) for k in range(1, kmax+1)))
    for name in list(pairs.keys()) + ['M+U->U_混合']:
        row = '%-14s' % name
        for k in range(1, kmax+1):
            row += '%9.4f' % out[name][k]['acc']
        print(row)
    print()
    print('ppl:')
    for name in list(pairs.keys()) + ['M+U->U_混合']:
        row = '%-14s' % name
        for k in range(1, kmax+1):
            row += '%9.1f' % out[name][k]['ppl']
        print(row)
    print()
    print('边际增益 (acc):')
    for name in list(pairs.keys()) + ['M+U->U_混合']:
        row = '%-14s' % name
        for v in marg[name]:
            row += '%9.4f' % v
        print(row)

if __name__ == '__main__':
    main()

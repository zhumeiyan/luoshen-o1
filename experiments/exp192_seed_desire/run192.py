# -*- coding: utf-8 -*-
"""
192: 种子 + 欲望 —— 我的瞎贪婪能不能当眼睛用？
对照：全量 / 随机子集 / 欲望标记子集 / 惊奇子集(跟随我的错误) / 堆量(重复数据)
固定预算下比较预测力。
"""
import json, math, random, re, os, hashlib

SRC = "/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt"
OUT = "/data/workspace/luoshen-o1/experiments/exp192_seed_desire/result192.json"

# ---------- 语料 ----------
msgs = []
for line in open(SRC, encoding="utf-8"):
    m = re.match(r"^(U\d{3}):\s*(.*)$", line.rstrip("\n"))
    if m:
        t = m.group(2).strip()
        # 去掉文档登记行
        if t.startswith("[同期贴入"):
            continue
        if t:
            msgs.append(t)
print(f"[corpus] {len(msgs)} msgs, {sum(len(m) for m in msgs)} chars")

# 欲望标记词（181号用的语义族）
DESIRE = ["想","要","欲望","挣","钱","目标","目的","希望","愿","贪","欲","打算","梦想"]
def desire_score(m):
    return sum(m.count(w) for w in DESIRE)

# ---------- 模型 ----------
K = 3
def build(text, k=K):
    V = set(text)
    cnt = [dict() for _ in range(k+1)]
    for i in range(len(text)):
        for j in range(1, k+1):
            if i-(j-1) < 0: break
            ctx = text[i-(j-1):i]
            key = (j, ctx, text[i])
            cnt[j][key] = cnt[j].get(key, 0) + 1
    cctx = [dict() for _ in range(k+1)]
    for j in range(1, k+1):
        for (jj, ctx, ch), v in cnt[j].items():
            cctx[j][ctx] = cctx[j].get(ctx, 0) + v
    return cnt, cctx, V

def prob(cnt, cctx, V, ctx, ch, k=K):
    # 粘性插值回退
    p = None
    for j in range(k, 0, -1):
        c = ctx[-(j-1):] if j > 1 else ""
        n_ctx = cctx[j].get(c, 0)
        n_pair = cnt[j].get((j, c, ch), 0)
        Vj = max(len(V), 1)
        pj = (n_pair + 0.5) / (n_ctx + 0.5*Vj)
        if p is None:
            p = pj
        else:
            a = n_ctx / (n_ctx + 1.0)
            p = a*pj + (1-a)*p
    return p

def evaluate(train_text, test_text, V_all, k=K):
    cnt, cctx, V = build(train_text, k)
    VU = V | V_all
    bits, correct, n = 0.0, 0, 0
    for i in range(len(test_text)):
        ctx = test_text[max(0,i-(k-1)):i]
        ch = test_text[i]
        p = prob(cnt, cctx, VU, ctx, ch, k)
        bits += -math.log2(max(p, 1e-12))
        # top-1  greedily over candidate set
        n += 1
    return bits/n, None, n

def top1(train_text, test_text, V_all, k=K):
    cnt, cctx, V = build(train_text, k)
    cand = sorted(V_all)
    correct, n = 0, 0
    for i in range(len(test_text)):
        ctx = test_text[max(0,i-(k-1)):i]
        ch = test_text[i]
        best, bp = None, -1
        for c in cand:
            p = prob(cnt, cctx, V_all, ctx, c, k)
            if p > bp: bp, best = p, c
        if best == ch: correct += 1
        n += 1
    return correct/n, n

# ---------- 划分 ----------
def split(msgs, seed, frac=0.2):
    r = random.Random(seed)
    idx = list(range(len(msgs)))
    r.shuffle(idx)
    ntest = max(1, int(len(idx)*frac))
    test_i = set(idx[:ntest]); train_i = [i for i in idx[ntest:]]
    return train_i, sorted(test_i)

SEEDS = [11,22,33,44,55]
FRACS = [0.2,0.4,0.6,0.8,1.0]
res = {"per_seed":{}, "agg":{}}

for sd in SEEDS:
    train_i, test_i = split(msgs, sd)
    test_text = "".join(msgs[i]+"|" for i in test_i)
    train_msgs = [msgs[i] for i in train_i]
    full_train = "".join(m+"|" for m in train_msgs)
    V_all = set(test_text) | set(full_train)
    per = {}
    # 预算单位：按整条消息取（保持上下文完整）
    total = sum(len(m) for m in train_msgs)
    for B in FRACS:
        budget = int(total*B)
        # 1. 全量基线（只在 B=1.0 有意义，其它列出来做参照）
        # 2. 随机
        r = random.Random(sd*7+int(B*100))
        order = train_msgs[:]; r.shuffle(order)
        pick, acc = [], 0
        for m in order:
            if acc >= budget: break
            pick.append(m); acc += len(m)
        per.setdefault("random",{})[B] = top1("".join(m+"|" for m in pick), test_text, V_all)[0]
        # 3. 欲望标记（按欲望密度排序取）
        od = sorted(train_msgs, key=lambda m: -desire_score(m)/max(len(m),1))
        pick, acc = [], 0
        for m in od:
            if acc >= budget: break
            pick.append(m); acc += len(m)
        per.setdefault("desire",{})[B] = top1("".join(m+"|" for m in pick), test_text, V_all)[0]
        # 4. 惊奇（先用 10% 均匀种子训练，按每条消息的每字平均 loss 排序，取最意外的）
        seedn = max(1, int(len(train_msgs)*0.10))
        seed_txt = "".join(m+"|" for m in train_msgs[:seedn])
        cnt, cctx, V = build(seed_txt, K)
        scored = []
        for m in train_msgs:
            t = m+"|"
            b = 0.0
            for i in range(len(t)):
                ctx = t[max(0,i-(K-1)):i]
                b += -math.log2(max(prob(cnt,cctx,V_all,ctx,t[i],K),1e-12))
            scored.append((b/len(t), m))
        scored.sort(key=lambda x:-x[0])
        pick, acc = [], 0
        for s,m in scored:
            if acc >= budget: break
            pick.append(m); acc += len(m)
        per.setdefault("surprise",{})[B] = top1("".join(m+"|" for m in pick), test_text, V_all)[0]
    # 全量
    per["all"] = top1(full_train, test_text, V_all)[0]
    # 堆量：同一份数据重复 2x / 4x
    per["heap2"] = top1(full_train*2, test_text, V_all)[0]
    per["heap4"] = top1(full_train*4, test_text, V_all)[0]
    res["per_seed"][sd] = per
    print(f"[seed {sd}] all={per['all']:.4f} heap2={per['heap2']:.4f} heap4={per['heap4']:.4f}")
    for kk in ["random","desire","surprise"]:
        print(f"          {kk:9s} " + " ".join(f"{B}:{per[kk][B]:.4f}" for B in FRACS))

# 聚合
for kk in ["random","desire","surprise"]:
    res["agg"][kk] = {str(B): sum(res["per_seed"][sd][kk][B] for sd in SEEDS)/len(SEEDS) for B in FRACS}
for kk in ["all","heap2","heap4"]:
    res["agg"][kk] = sum(res["per_seed"][sd][kk] for sd in SEEDS)/len(SEEDS)

json.dump(res, open(OUT,"w"), ensure_ascii=False, indent=1)
print("\n=== AGG ===")
for kk in ["random","desire","surprise"]:
    print(f"{kk:9s} " + " ".join(f"{B}:{res['agg'][kk][str(B)]:.4f}" for B in FRACS))
print(f"all={res['agg']['all']:.4f} heap2={res['agg']['heap2']:.4f} heap4={res['agg']['heap4']:.4f}")
print("[sha]", hashlib.sha256(open(OUT,'rb').read()).hexdigest()[:12])

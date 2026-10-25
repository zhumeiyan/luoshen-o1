#!/usr/bin/env python3
# 199b: bits 变好 ≠ B 没被淹没。测"话语权"与"稀有(不可复现)内容的保留"
import json, math, hashlib, os
from collections import defaultdict

A_PATH = "/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md"
B_PATH = "/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt"
OUT = "/data/workspace/luoshen-o1/experiments/exp199_two_mem/result199b.json"
K = 3; ALPHA = 0.1

def load(p):
    with open(p,'r',encoding='utf-8',errors='ignore') as f: return f.read()
A_all, B_all = load(A_PATH), load(B_PATH)
V = len(set(A_all) | set(B_all))
B_train, B_test = B_all[:int(len(B_all)*0.7)], B_all[int(len(B_all)*0.7):]

def counts(text):
    c = defaultdict(lambda: defaultdict(float)); t = defaultdict(float)
    for i in range(len(text)-K+1):
        k = text[i:i+K-1]; n = text[i+K-1]
        c[k][n] += 1.0; t[k] += 1.0
    return c, t

def prob(c, t, ctx, ch, alpha=ALPHA, V=V):
    d = c.get(ctx) or {}
    return max((d.get(ch,0.0)+alpha)/(t.get(ctx,0.0)+alpha*V), 1e-12)

res = {}
CAPS = [10000, 50000, 102000, 345555]
rows = []
for N in CAPS:
    A_sub = A_all[:N]
    A_tr = A_sub[:int(len(A_sub)*0.7)]
    cA, tA = counts(A_tr)
    cB, tB = counts(B_train)
    cM, tM = counts(A_tr + B_train)
    # ---- 话语权: 混合模型里 B 的计数份额 ----
    shares = []; shares_known = []
    rare_mono = []; rare_bonly = []; rare_arb = []
    common_mono = []; common_bonly = []
    for i in range(len(B_test)-K+1):
        ctx = B_test[i:i+K-1]; ch = B_test[i+K-1]
        a = (cA.get(ctx) or {}).get(ch, 0.0)
        b = (cB.get(ctx) or {}).get(ch, 0.0)
        tot = a + b
        if tot > 0:
            s = b/tot
            shares.append(s)
            if tB.get(ctx,0.0) > 0: shares_known.append(s)
        # 稀有: B_train 里这个精确 trigram 只出现 1 次 = 不可复现
        is_rare = (b == 1.0)
        pM = prob(cM,tM,ctx,ch); pB = prob(cB,tB,ctx,ch); pA = prob(cA,tA,ctx,ch)
        # 仲裁权重(按确定性)
        dA = cA.get(ctx); dB = cB.get(ctx)
        bA = max(dA.values()) if dA else 0.0; bB = max(dB.values()) if dB else 0.0
        cA_ = bA/tA[ctx] if tA.get(ctx,0)>0 else 0.0
        cB_ = bB/tB[ctx] if tB.get(ctx,0)>0 else 0.0
        wA = cA_/(cA_+cB_) if (cA_+cB_)>0 else 0.5
        pARB = wA*pA + (1-wA)*pB
        if is_rare:
            rare_mono.append(-math.log2(pM)); rare_bonly.append(-math.log2(pB)); rare_arb.append(-math.log2(pARB))
        elif b >= 3:
            common_mono.append(-math.log2(pM)); common_bonly.append(-math.log2(pB))
    avg = lambda L: sum(L)/len(L) if L else None
    rows.append({
        'A_chars': N, 'B_train_chars': len(B_train),
        'volume_share_B_expected': len(B_train)/(len(A_tr)+len(B_train)),
        'n_positions': len(shares),
        'B_voice_mean': avg(shares),
        'B_voice_median': sorted(shares)[len(shares)//2] if shares else None,
        'B_voice_known_ctx': avg(shares_known),
        'B_voice_below_10pct': sum(1 for s in shares if s < 0.10)/len(shares) if shares else None,
        'n_rare': len(rare_mono), 'n_common': len(common_mono),
        'rare_bits_mono': avg(rare_mono), 'rare_bits_Bonly': avg(rare_bonly), 'rare_bits_arb': avg(rare_arb),
        'rare_swamp_mono': (avg(rare_mono)-avg(rare_bonly)) if rare_mono else None,
        'common_swamp_mono': (avg(common_mono)-avg(common_bonly)) if common_mono else None,
    })
res['voice'] = rows
res['meta'] = {'V':V,'A':len(A_all),'B':len(B_all),'ratio_char':len(A_all)/len(B_all),
               'B_train':len(B_train),'B_test':len(B_test),'alpha':ALPHA,'K':K}
with open(OUT,'w',encoding='utf-8') as f: json.dump(res,f,ensure_ascii=False,indent=2)
print("WROTE",OUT,os.path.getsize(OUT))
print(f"{'A量':>8} {'B期望份额':>9} {'B实际话语权':>10} {'中位':>7} {'已知ctx':>8} {'<10%占比':>8} | {'稀有n':>6} {'稀有淹没':>9} {'常见淹没':>9}")
for r in rows:
    print(f"{r['A_chars']:>8} {r['volume_share_B_expected']:>9.4f} {r['B_voice_mean']:>10.4f} {r['B_voice_median']:>7.3f} {r['B_voice_known_ctx']:>8.4f} {r['B_voice_below_10pct']:>8.3f} | {r['n_rare']:>6} {r['rare_swamp_mono']:>9.3f} {r['common_swamp_mono']:>9.3f}")

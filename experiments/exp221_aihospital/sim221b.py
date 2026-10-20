# -*- coding: utf-8 -*-
"""
221b · AI医院 修正版
第一版错误：污染病例跟自评走，而自评 75% 对 → 污染只是稀释，不会反转（rho*=None）。
真正致命的轴：自评诚实度。当自评比随机还差（错误率>0.5）时，
             污染病例跟着自评走 = 系统性反向 → 库越大越【确信地】错。
"""
import numpy as np, json
rng = np.random.default_rng(20261021)
T = 40000
P_PASS_TRUE = 0.90
P_CLEAN_ACC = 0.75

def run(dishonest, rho, N, prov=False, q=0.90):
    """dishonest = P(自评通过 | 其实是假的)  ← 越低越诚实"""
    y = rng.integers(0,2,T)
    p = np.where(y==1, P_PASS_TRUE, dishonest)
    sp = (rng.random(T) < p).astype(float)              # 自评结论
    err_self = float((sp != y).mean())

    clean = rng.random((T,N)) > rho
    ag = rng.random((T,N)) < P_CLEAN_ACC
    sig_clean = np.where(y[:,None]==1, ag, ~ag).astype(float)
    # 污染：与自评【完全同向】(强度1.0) —— 检索确认偏误
    sig_poll  = np.broadcast_to(sp[:,None], (T,N)).copy()
    sig = np.where(clean, sig_clean, sig_poll)

    if not prov:
        w = np.ones((T,N))
    else:
        tag = (rng.random((T,N)) < q)               # q = 溯源标记精度
        # 标为污染者降权(0.15)而非剔除；干净保留全权
        w = np.where(tag, 0.15, 1.0)

    v = (sig*w).sum(1)/w.sum(1)
    verdict = (v>0.5).astype(int)
    err = float((verdict!=y).mean())
    conf = float(np.abs(v-0.5).mean()*2)            # 0..1 置信度
    cerr = float(((verdict!=y) & (np.abs(v-0.5)>0.25)).mean())  # 确信的错误
    return err_self, err, conf, cerr

print("自评错误率随诚实度变化:")
for d in [0.40,0.60,0.80,0.95]:
    print(f"  P(自评通过|假)={d:.2f}  ->  自评错误率 ≈ {0.5*(1-P_PASS_TRUE)+0.5*d:.3f}")

print("\n=== 核心表：诚实度 × 污染率 × 库规模 (N=40 固定rho先看规模效应) ===")
print(f"{'不诚实度':>8} {'rho':>5} {'N':>5} {'自评错':>8} {'医院错':>8} {'置信度':>8} {'确信错':>8}")
grid=[]
for d in [0.40, 0.80, 0.95]:
    for rho in [0.3, 0.7]:
        for N in [10, 40, 160]:
            es, e, c, ce = run(d, rho, N)
            grid.append(dict(d=d, rho=rho, N=N, err_self=round(es,4), err=round(e,4),
                             conf=round(c,4), cerr=round(ce,4)))
            print(f"{d:>8.2f} {rho:>5.1f} {N:>5} {es:>8.4f} {e:>8.4f} {c:>8.4f} {ce:>8.4f}")
    print("-"*60)

print("\n=== 溯源(降权)是否有效：d=0.95(自评比随机还差), N=40 ===")
print(f"{'rho':>5} {'无溯源err':>10} {'带溯源err':>10} {'无溯源确信错':>13} {'带溯源确信错':>13}")
prov_rows=[]
for rho in [0.3,0.5,0.7,0.9]:
    _,e0,c0,ce0 = run(0.95, rho, 40, False)
    _,e1,c1,ce1 = run(0.95, rho, 40, True, 0.90)
    prov_rows.append(dict(rho=rho, e0=round(e0,4), e1=round(e1,4), ce0=round(ce0,4), ce1=round(ce1,4)))
    print(f"{rho:>5.1f} {e0:>10.4f} {e1:>10.4f} {ce0:>13.4f} {ce1:>13.4f}")

print("\n=== 溯源标记精度扫描 (d=0.95, rho=0.7, N=40) ===")
q_rows=[]
for q in [0.5,0.6,0.7,0.8,0.9,0.95,1.0]:
    _,e,c,ce = run(0.95,0.7,40,True,q)
    q_rows.append(dict(q=q, err=round(e,4), cerr=round(ce,4)))
    print(f"  q={q:<5} err={e:.4f}  确信错={ce:.4f}")

json.dump(dict(grid=grid, prov=prov_rows, qscan=q_rows),
  open("/data/workspace/luoshen-o1/experiments/exp221_aihospital/result221b.json","w"),
  ensure_ascii=False, indent=1)
print("\n[saved] result221b.json")

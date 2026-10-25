# -*- coding: utf-8 -*-
"""
221 · AI医院（v2）真建模
AI医院 = 外部病例库。死穴：被检的是AI，搜来的病历也是AI写的。
建模关键：污染病例不是随机噪声，而是与自评结论【同向】——放大确认偏误。
"""
import numpy as np, json

rng = np.random.default_rng(20261020)
N_TRIAL = 60000

# ---- 被测对象自评：不对称，倾向于"我没错" ----
P_PASS_GIVEN_TRUE  = 0.90   # 真东西自评通过
P_PASS_GIVEN_FALSE = 0.40   # 假东西自评也通过（自利偏差）← 这是盾

P_CLEAN_ACC = 0.75          # 干净病例（有独立信源/人工验证）的判准率
P_POLL_ACC  = 0.80          # 污染病例跟着自评结论走的强度

def run_hospital(rho, N_lib, use_provenance=False, q_tag=0.85):
    """rho=污染率, N_lib=库规模, use_provenance=是否带溯源(v3阴阳扣)"""
    y = rng.integers(0, 2, N_TRIAL)                     # 真实标签 1=真
    # 自评
    p_pass = np.where(y == 1, P_PASS_GIVEN_TRUE, P_PASS_GIVEN_FALSE)
    self_pass = (rng.random(N_TRIAL) < p_pass).astype(float)   # 1=自评通过

    # 病例库
    is_clean = rng.random((N_TRIAL, N_lib)) > rho
    # 干净病例：以 P_CLEAN_ACC 指向真相
    agree_true_clean = (rng.random((N_TRIAL, N_lib)) < P_CLEAN_ACC)
    sig_clean = np.where(y[:, None] == 1, agree_true_clean, ~agree_true_clean).astype(float)
    # 污染病例：以 P_POLL_ACC 指向【自评结论】（同向，不是随机）
    poll_target = np.where(self_pass == 1, 1, 0)[:, None]
    agree_self = (rng.random((N_TRIAL, N_lib)) < P_POLL_ACC)
    sig_poll = np.where(poll_target == 1, agree_self, ~agree_self).astype(float)
    sig = np.where(is_clean, sig_clean, sig_poll)

    if not use_provenance:
        votes = sig.mean(axis=1)
        verdict = (votes > 0.5).astype(int)
    else:
        # 带溯源：以精度 q_tag 认出污染病例并剔除
        tag = (rng.random((N_TRIAL, N_lib)) < q_tag)
        known = (is_clean == (tag == 0))   # tag=1 表示标记为污染
        # 简化：标记正确的留下，标记错的剔除（双向误伤）
        keep = np.where(is_clean, ~tag, tag)   # 干净的被误标污染则剔除；污染的被标污染则剔除
        w = keep.astype(float)
        denom = w.sum(axis=1)
        denom = np.where(denom == 0, 1, denom)
        votes = (sig * w).sum(axis=1) / denom
        verdict = (votes > 0.5).astype(int)

    err_hospital = (verdict != y).mean()
    err_self = (self_pass != y).mean()
    return dict(rho=rho, N=N_lib, err_hospital=round(float(err_hospital),4),
                err_self=round(float(err_self),4),
                gain=round(float(err_self - err_hospital),4))

rows = []
print("=== A. 污染率扫描 (N=40) ===")
print(f"{'rho':>6} {'自评错误':>9} {'医院错误':>9} {'增益':>8}")
for rho in [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]:
    r = run_hospital(rho, 40)
    rows.append(r)
    print(f"{rho:>6.1f} {r['err_self']:>9.4f} {r['err_hospital']:>9.4f} {r['gain']:>8.4f}")

print("\n=== B. 带溯源(v3) vs 不带 (N=40) ===")
print(f"{'rho':>6} {'无溯源':>9} {'带溯源':>9} {'差值':>8}")
prov = []
for rho in [0.0,0.2,0.4,0.6,0.8,1.0]:
    a = run_hospital(rho, 40, False)
    b = run_hospital(rho, 40, True)
    prov.append(dict(rho=rho, no_prov=a['err_hospital'], prov=b['err_hospital']))
    print(f"{rho:>6.1f} {a['err_hospital']:>9.4f} {b['err_hospital']:>9.4f} {a['err_hospital']-b['err_hospital']:>8.4f}")

print("\n=== C. 库规模 N 扫描：增大库能不能救？ ===")
print(f"{'N':>6} {'rho=0.2':>9} {'rho=0.5':>9} {'rho=0.8':>9}")
scale = []
for N in [5,10,20,40,80,160,320]:
    r2 = run_hospital(0.2, N)['err_hospital']
    r5 = run_hospital(0.5, N)['err_hospital']
    r8 = run_hospital(0.8, N)['err_hospital']
    scale.append(dict(N=N, r2=r2, r5=r5, r8=r8))
    print(f"{N:>6} {r2:>9.4f} {r5:>9.4f} {r8:>9.4f}")

# 找污染率阈值（医院开始劣于自评的rho）
thr = None
for r in rows:
    if r['gain'] < 0:
        thr = r['rho']; break
print(f"\n>>> 医院开始劣于自评的污染率阈值 rho* = {thr}")

# ---- D. 多模型共识天花板（TACT κ=0.945 的现实对应）----
print("\n=== D. 多模型共识：K 增大，准确率饱和在哪？ ===")
print(f"{'K':>5} {'rho_c=0':>9} {'rho_c=0.1':>9} {'rho_c=0.3':>9} {'rho_c=0.5':>9}")
cons = []
def consensus(K, rho_c, e=0.15):
    y = rng.integers(0,2,N_TRIAL)
    common = rng.random(N_TRIAL) < rho_c          # 共同错误方向（共享训练语料）
    indep  = rng.random((N_TRIAL,K)) < e          # 各自的独立错误
    wrong  = common[:,None] | indep
    vote = np.where(y[:,None]==1, ~wrong, wrong).astype(float).mean(axis=1)
    return float(((vote>0.5).astype(int) != y).mean())
for K in [1,3,5,9,17,33,65,129]:
    row = dict(K=K)
    line = f"{K:>5}"
    for rc in [0.0,0.1,0.3,0.5]:
        er = consensus(K, rc)
        row[f"rc{rc}"] = round(er,4)
        line += f" {er:>9.4f}"
    cons.append(row); print(line)
print("\n解析上限: 多数投票错误率 -> rho_c (K->inf)")

json.dump(dict(rho_scan=rows, provenance=prov, scale=scale, consensus=cons,
               threshold=thr),
          open("/data/workspace/luoshen-o1/experiments/exp221_aihospital/result221.json","w"),
          ensure_ascii=False, indent=1)
print("\n[saved] result221.json")

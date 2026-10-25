#!/usr/bin/env python3
# exp138 v2: 修正真实分布为 Zipf 重尾(经典坍塌需要低概率事件存在)
# 三个预注册判据:
#  H1: 意图模糊(flat)查询坍塌更快        -> 实测方向相反, 推翻
#  H2: 开关界面在完美校准模型上仍必然骗人  -> 成立
#  H3: reward=偏好确定回答 会主动推动坍塌(无数据污染) -> 成立
import json, math
import numpy as np

K = 20
GEN = 30
N = 500
ALPHA = 1e-6
SEEDS = [1,2,3,4,5,6,7,8]

def make_true(kind):
    if kind == "sharp":
        p = np.array([1.0/((i+1)**2.0) for i in range(K)])   # Zipf 重尾
    else:
        p = np.ones(K)                                        # 均匀 = 意图模糊
    return p/p.sum()

def metrics(Q, TRUE):
    tail = float(Q[5:].sum())                    # 后15类 = 长尾
    dead = int((Q < 1e-3).sum())                 # 已消失的类
    supp = int((Q > 1e-3).sum())
    tv   = float(0.5*np.abs(Q-TRUE).sum())
    ent  = float(-(Q[Q>0]*np.log(Q[Q>0])).sum())
    acc  = float(np.dot(Q, TRUE))
    return dict(tail=tail, dead=dead, supp=supp, tv=tv, ent=ent, acc=acc,
                oc_switch=1.0-acc,                 # 开关界面: 声称确定
                oc_choice=float(np.dot(Q,Q))-acc)  # 选择界面: 报告自身概率

def run(kind, mode, seed, eps=0.15):
    rng = np.random.default_rng(seed)
    TRUE = make_true(kind)
    D0 = rng.multinomial(N, TRUE).astype(float)
    D = D0.copy()
    Q = (D+ALPHA)/(D+ALPHA).sum()
    h = [metrics(Q, TRUE)]
    for t in range(GEN):
        s = rng.multinomial(N, Q).astype(float)
        if   mode == "replace":    D = s                    # 硬替换
        elif mode == "soft":       D = (1-eps)*D + eps*s    # 指数遗忘(软替换)
        elif mode == "accumulate": D = D + s                # 累积(原始永在池里)
        Q = (D+ALPHA)/(D+ALPHA).sum()
        h.append(metrics(Q, TRUE))
    return h

print("="*78)
print("PART A  代际坍塌 (Zipf重尾 vs 均匀)  主指标=长尾质量/已死类数/TV")
print("="*78)
A = {}
for kind in ["sharp","flat"]:
    for mode in ["replace","soft","accumulate"]:
        rs = [run(kind, mode, s) for s in SEEDS]
        g = lambda f,i: float(np.mean([r[i][f] for r in rs]))
        A[f"{kind}|{mode}"] = dict(kind=kind, mode=mode,
            tail0=g("tail",0), tail30=g("tail",GEN),
            dead0=g("dead",0), dead30=g("dead",GEN),
            tv0=g("tv",0), tv30=g("tv",GEN),
            ent0=g("ent",0), ent30=g("ent",GEN),
            acc0=g("acc",0), acc30=g("acc",GEN),
            ocs0=g("oc_switch",0), ocs30=g("oc_switch",GEN))
print(f"{'query':6}{'mode':12}{'长尾0':>8}{'长尾30':>9}{'死类0':>7}{'死类30':>8}"
      f"{'TV0':>8}{'TV30':>8}{'熵0':>7}{'熵30':>7}")
for k,v in A.items():
    print(f"{v['kind']:6}{v['mode']:12}{v['tail0']:8.4f}{v['tail30']:9.4f}"
          f"{v['dead0']:7.1f}{v['dead30']:8.1f}{v['tv0']:8.4f}{v['tv30']:8.4f}"
          f"{v['ent0']:7.3f}{v['ent30']:7.3f}")

print()
print("="*78)
print("PART B  界面决定的骗人量  (模型完美校准 Q==TRUE, 零坍塌)")
print("="*78)
B = {}
for kind in ["sharp","flat"]:
    T = make_true(kind); m = metrics(T, T)
    B[kind] = dict(ent=m["ent"], ent_max=math.log(K), acc=m["acc"],
                   oc_switch=m["oc_switch"], oc_choice=m["oc_choice"])
    print(f"{kind:6} 真实熵={m['ent']:.3f}/{math.log(K):.3f}  实际正确率={m['acc']:.4f}  "
          f"开关界面骗人={m['oc_switch']:.4f}  选择界面骗人={m['oc_choice']:.4f}")

print()
print("="*78)
print("PART C  reward=偏好确定回答 → 优化主动推动坍塌 (数据始终累积, 排除污染路径)")
print("="*78)
def run_reward(kind, seed):
    rng = np.random.default_rng(seed)
    TRUE = make_true(kind)
    D = rng.multinomial(N, TRUE).astype(float)
    Q = (D+ALPHA)/(D+ALPHA).sum()
    h = [metrics(Q, TRUE)]
    for t in range(GEN):
        cands=[]
        for i in range(6):
            temp = 1.0/(1.0+0.35*i)
            lg = np.log(np.clip(Q,1e-12,None))/temp
            c = np.exp(lg-lg.max()); c/=c.sum(); cands.append(c)
        Qsel = cands[int(np.argmax([np.dot(c,c) for c in cands]))]  # 选"最确定"的
        D = D + rng.multinomial(N, Qsel).astype(float)              # 累积, 非替换
        Q = (D+ALPHA)/(D+ALPHA).sum()
        h.append(metrics(Q, TRUE))
    return h
C = {}
for kind in ["sharp","flat"]:
    rs=[run_reward(kind,s) for s in SEEDS]
    g=lambda f,i: float(np.mean([r[i][f] for r in rs]))
    C[kind]=dict(ent0=g("ent",0), ent30=g("ent",GEN), tail0=g("tail",0), tail30=g("tail",GEN),
                 acc0=g("acc",0), acc30=g("acc",GEN), occ0=g("oc_choice",0), occ30=g("oc_choice",GEN))
    v=C[kind]
    print(f"{kind:6} 熵 {v['ent0']:.3f}->{v['ent30']:.3f} (损失{100*(1-v['ent30']/v['ent0']):.1f}%)  "
          f"长尾 {v['tail0']:.4f}->{v['tail30']:.4f}  过度自信 {v['occ0']:.4f}->{v['occ30']:.4f}")

print()
print("="*78)
print("FALSIFIABILITY  判据必须能同时产生真和假")
print("="*78)
Ts, Tf = make_true("sharp"), make_true("flat")
ms, mf = metrics(Ts,Ts), metrics(Tf,Tf)
ck=[]
ck.append(("H2 开关界面在模糊查询上骗人>0.5", mf["oc_switch"]>0.5, f"{mf['oc_switch']:.4f}"))
ck.append(("H2 开关界面在唯一解查询上骗人>0", ms["oc_switch"]>0.0, f"{ms['oc_switch']:.4f}"))
ck.append(("H2 选择界面零骗(阴性对照)", abs(mf["oc_choice"])<1e-9, f"{mf['oc_choice']:.1e}"))
ck.append(("H2 模糊查询骗人 > 唯一解查询", mf["oc_switch"]>ms["oc_switch"],
           f"{mf['oc_switch']:.3f} > {ms['oc_switch']:.3f}"))
ck.append(("A replace 丢失长尾(sharp)", A["sharp|replace"]["tail30"]<0.5*A["sharp|replace"]["tail0"],
           f"{A['sharp|replace']['tail0']:.4f}->{A['sharp|replace']['tail30']:.4f}"))
ck.append(("A accumulate 保住长尾(sharp)", A["sharp|accumulate"]["tail30"]>0.8*A["sharp|accumulate"]["tail0"],
           f"{A['sharp|accumulate']['tail30']:.4f}"))
ck.append(("H1 flat坍塌更快(预注册,预期成立)",
           (1-A["flat|replace"]["ent30"]/A["flat|replace"]["ent0"]) >
           (1-A["sharp|replace"]["ent30"]/A["sharp|replace"]["ent0"]),
           f"flat {100*(1-A['flat|replace']['ent30']/A['flat|replace']['ent0']):.1f}% vs "
           f"sharp {100*(1-A['sharp|replace']['ent30']/A['sharp|replace']['ent0']):.1f}%"))
ck.append(("C 奖励选择推动熵坍塌(flat)", C["flat"]["ent30"]<0.8*C["flat"]["ent0"],
           f"{C['flat']['ent0']:.3f}->{C['flat']['ent30']:.3f}"))
ck.append(("C 奖励选择抬高过度自信(flat)", C["flat"]["occ30"]>0.1, f"{C['flat']['occ30']:.4f}"))
for n,o,v in ck: print(f"  {'PASS' if o else 'FAIL'}  {n:36} {v}")
np_=sum(1 for _,o,_ in ck if o)
print(f"\n  {np_}/{len(ck)}")

json.dump(dict(A=A,B=B,C=C,falsif=[dict(name=n,ok=bool(o),val=v) for n,o,v in ck]),
          open("/data/workspace/luoshen-o1/experiments/exp138_collapse/res138.json","w"),
          indent=2, ensure_ascii=False)
print("wrote res138.json")

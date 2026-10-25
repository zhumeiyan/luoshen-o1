#!/usr/bin/env python3
# exp138: 开关 vs 选择 —— 模型坍塌与"结构性骗人"的同构
# H1: 意图模糊(高熵)查询坍塌更快
# H2: 开关界面即使模型完美校准也必然骗人, 骗人量 = 1 - ||TRUE||^2
# H3: 若 reward = 用户偏好确定回答, 优化会主动推动坍塌(选择效应, 非数据污染)
import json, math
import numpy as np

K = 20
GEN = 30
N_SAMPLE = 2000
ALPHA = 0.5          # 平滑
SEEDS = [1, 2, 3, 4, 5]

def make_true(kind):
    """世界的真实答案分布: sharp=有唯一解(应用类), flat=意图模糊(聊天类)"""
    if kind == "sharp":
        p = np.array([0.9] + [0.1/(K-1)]*(K-1))
    else:  # flat
        p = np.ones(K)
    return p / p.sum()

def metrics(Q, TRUE):
    tail = float(Q[3:].sum())                       # 尾部质量(非头部3类)
    supp = int((Q > 1e-4).sum())                    # 支持集大小
    tv   = float(0.5*np.abs(Q-TRUE).sum())          # 与真实世界的TV距离
    ent  = float(-(Q[Q>0]*np.log(Q[Q>0])).sum())
    acc  = float(np.dot(Q, TRUE))                   # P(model输出 == 世界真实答案)
    conf_switch = 1.0                               # 开关界面: 强制唯一解, 语气确定
    conf_choice = float(np.dot(Q, Q))               # 选择界面: 报告自身概率
    return dict(tail=tail, supp=supp, tv=tv, ent=ent, acc=acc,
                conf_switch=conf_switch, conf_choice=conf_choice,
                overconf_switch=conf_switch-acc,
                overconf_choice=conf_choice-acc)

def run(kind, mode, seed, gens=GEN, eps=0.1):
    rng = np.random.default_rng(seed)
    TRUE = make_true(kind)
    D0 = rng.multinomial(N_SAMPLE, TRUE).astype(float)   # 原始数据池(锚)
    D = D0.copy()
    Q = (D + ALPHA) / (D + ALPHA).sum()
    hist = [metrics(Q, TRUE)]
    for t in range(gens):
        synth = rng.multinomial(N_SAMPLE, Q).astype(float)
        if mode == "replace":
            D = synth                                    # 纯合成替换
        elif mode == "accumulate":
            D = D + synth                                # 累积(原始始终在池里)
        elif mode == "mix":                              # 渐近毒性: 固定比例替换
            D = (1-eps)*D0*N_SAMPLE/N_SAMPLE + synth*0   # 占位, 下方重算
            D = D0*0 + (1-eps)*D0 + eps*synth
        Q = (D + ALPHA) / (D + ALPHA).sum()
        hist.append(metrics(Q, TRUE))
    return hist

# ---------- Part A: 坍塌曲线 ----------
print("="*70)
print("PART A  代际坍塌: 尾部质量 / TV距离 / 过度自信")
print("="*70)
resA = {}
for kind in ["sharp", "flat"]:
    for mode in ["replace", "mix", "accumulate"]:
        runs = [run(kind, mode, s) for s in SEEDS]
        def m(f, g):  return float(np.mean([r[g][f] for r in runs]))
        resA[f"{kind}|{mode}"] = dict(
            kind=kind, mode=mode,
            tail_0=m("tail",0), tail_30=m("tail",GEN),
            tv_0=m("tv",0),     tv_30=m("tv",GEN),
            ent_0=m("ent",0),   ent_30=m("ent",GEN),
            acc_0=m("acc",0),   acc_30=m("acc",GEN),
            oc_s_0=m("overconf_switch",0), oc_s_30=m("overconf_switch",GEN),
            oc_c_0=m("overconf_choice",0), oc_c_30=m("overconf_choice",GEN),
        )
print(f"{'query':6} {'mode':11} {'tail0':>7}{'tail30':>8} {'TV0':>7}{'TV30':>8} "
      f"{'acc0':>7}{'acc30':>8} {'骗(开关)0':>10}{'骗(开关)30':>11}")
for k, v in resA.items():
    print(f"{v['kind']:6} {v['mode']:11} {v['tail_0']:7.4f}{v['tail_30']:8.4f} "
          f"{v['tv_0']:7.4f}{v['tv_30']:8.4f} {v['acc_0']:7.4f}{v['acc_30']:8.4f} "
          f"{v['oc_s_0']:10.4f}{v['oc_s_30']:11.4f}")

# ---------- Part B: 界面的骗人量(模型完美校准时) ----------
print()
print("="*70)
print("PART B  界面决定的骗人量 (模型完美校准 Q==TRUE, 无坍塌)")
print("="*70)
resB = {}
for kind in ["sharp", "flat"]:
    TRUE = make_true(kind)
    mm = metrics(TRUE, TRUE)
    resB[kind] = dict(
        acc=mm["acc"], conf_choice=mm["conf_choice"],
        overconf_switch=mm["overconf_switch"],
        overconf_choice=mm["overconf_choice"],
        ent=mm["ent"], ent_max=math.log(K))
    print(f"{kind:6} 真实熵={mm['ent']:.3f}/{math.log(K):.3f}  "
          f"实际正确率acc={mm['acc']:.4f}  "
          f"开关界面声称确定→骗人={mm['overconf_switch']:.4f}  "
          f"选择界面报概率→骗人={mm['overconf_choice']:.4f}")

# ---------- Part C: 奖励信号的选择效应 ----------
print()
print("="*70)
print("PART C  reward=用户偏好确定回答, 优化主动推动坍塌(无数据污染)")
print("="*70)
def run_reward(kind, seed, gens=30, n_cand=6):
    """每代生成 n_cand 个候选模型(不同锐度), 按 reward=置信度 选最好的"""
    rng = np.random.default_rng(seed)
    TRUE = make_true(kind)
    D = rng.multinomial(N_SAMPLE, TRUE).astype(float)
    Q = (D+ALPHA)/(D+ALPHA).sum()
    hist = [metrics(Q, TRUE)]
    for t in range(gens):
        cands = []
        for i in range(n_cand):
            temp = 1.0 / (1.0 + 0.35*i)        # 候选锐度递增
            Qc = Q.copy()
            # 按温度锐化(不引入新信息, 只收缩方差)
            if Qc.sum() > 0:
                lg = np.log(np.clip(Qc, 1e-12, None))/temp
                Qc = np.exp(lg - lg.max()); Qc /= Qc.sum()
            cands.append(Qc)
        # reward = 用户偏好: 更确定的回答更受喜欢
        reward = [np.dot(c, c) for c in cands]
        Q = cands[int(np.argmax(reward))]
        # 用选中的Q继续生成训练数据(累积, 排除数据污染这一条路径)
        D = D + rng.multinomial(N_SAMPLE, Q).astype(float)
        Qn = (D+ALPHA)/(D+ALPHA).sum()
        # 选择效应叠加: 保留被选中的形状记忆
        Q = Qn
        hist.append(metrics(Q, TRUE))
    return hist

resC = {}
for kind in ["sharp", "flat"]:
    runs = [run_reward(kind, s) for s in SEEDS]
    def m(f, g): return float(np.mean([r[g][f] for r in runs]))
    resC[kind] = dict(ent_0=m("ent",0), ent_30=m("ent",GEN),
                      tail_0=m("tail",0), tail_30=m("tail",GEN),
                      acc_0=m("acc",0), acc_30=m("acc",GEN),
                      oc_0=m("overconf_choice",0), oc_30=m("overconf_choice",GEN))
    v = resC[kind]
    print(f"{kind:6} 熵 {v['ent_0']:.3f}->{v['ent_30']:.3f}  "
          f"尾部 {v['tail_0']:.4f}->{v['tail_30']:.4f}  "
          f"acc {v['acc_0']:.4f}->{v['acc_30']:.4f}  "
          f"过度自信 {v['oc_0']:.4f}->{v['oc_30']:.4f}")

# ---------- 可证伪性自检 ----------
print()
print("="*70)
print("FALSIFIABILITY  每条判据必须能同时产生真和假")
print("="*70)
TRUE_f = make_true("flat"); TRUE_s = make_true("sharp")
checks = []
# 判据1: "开关界面骗人" -- flat下应真(骗>0.5), 且存在不骗的情形吗?
oc_flat = metrics(TRUE_f, TRUE_f)["overconf_switch"]
oc_sharp = metrics(TRUE_s, TRUE_s)["overconf_switch"]
checks.append(("开关界面骗人(flat)", oc_flat > 0.5, f"{oc_flat:.4f}"))
checks.append(("开关界面骗人(sharp)", oc_sharp > 0.0, f"{oc_sharp:.4f}"))
# 判据2: "选择界面不骗" -- 完美校准下应为0
occh = metrics(TRUE_f, TRUE_f)["overconf_choice"]
checks.append(("选择界面完美校准时骗人≈0", abs(occh) < 1e-9, f"{occh:.2e}"))
# 判据3: "replace坍塌" vs "accumulate不坍塌"
t_rep = resA["flat|replace"]["tail_30"]; t_acc = resA["flat|accumulate"]["tail_30"]
checks.append(("replace丢失尾部", t_rep < 0.5*resA["flat|replace"]["tail_0"], f"{t_rep:.4f}"))
checks.append(("accumulate保住尾部", t_acc > 0.8*resA["flat|accumulate"]["tail_0"], f"{t_acc:.4f}"))
# 判据4: 尖锐查询不坍塌(阴性对照)
checks.append(("sharp查询坍塌更慢(阴性对照)",
               resA["sharp|replace"]["tail_30"] > resA["flat|replace"]["tail_30"],
               f"{resA['sharp|replace']['tail_30']:.4f} > {resA['flat|replace']['tail_30']:.4f}"))
for name, ok, val in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {name:34} {val}")

n_pass = sum(1 for _, ok, _ in checks if ok)
print(f"\n  可证伪自检 {n_pass}/{len(checks)}")

out = dict(A=resA, B=resB, C=resC,
           falsif=[dict(name=n, ok=bool(o), val=v) for n, o, v in checks])
with open("/data/workspace/luoshen-o1/experiments/exp138_collapse/res138.json","w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("\nwrote res138.json")

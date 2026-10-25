# -*- coding: utf-8 -*-
"""
220: 五版判据升级链 —— 每一版是否必要？
用户自述的升级：v1 事实与标准 / v2 AI医院 / v3 阴阳扣 / v4 灰度空间 / v5 公式升级
四类威胁：T1 噪声 / T2 翻面 / T3 灰度(中间带) / T4 外推
"""
import numpy as np, json

RNG = np.random.default_rng(220)
N = 4000

# ---------- 四类威胁下的真值与观测 ----------
def gen(threat):
    if threat == 'T1':   # 噪声：真值两极，但观测被噪
        y = (RNG.random(N) < 0.5).astype(float)
        x = y + RNG.normal(0, 0.35, N)
        ood = np.zeros(N, bool)
    elif threat == 'T2': # 翻面：真值两极、观测干净，但输出后被翻
        y = (RNG.random(N) < 0.5).astype(float)
        x = y.copy()
        ood = np.zeros(N, bool)
    elif threat == 'T3': # 灰度：真值连续且集中在中间带
        y = np.clip(RNG.normal(0.5, 0.12, N), 0, 1)
        x = y.copy()
        ood = np.zeros(N, bool)
    elif threat == 'T4': # 外推：一半案例落在训练分布之外
        y = np.clip(RNG.normal(0.5, 0.30, N), 0, 1)
        x = y.copy()
        ood = RNG.random(N) < 0.5
    return y, x, ood

# ---------- 五版：能力累积 ----------
VERSIONS = {
 'v1_事实与标准': dict(binary=True,  taxonomy=False, trace=False, gray=False, formula=False),
 'v2_AI医院':     dict(binary=True,  taxonomy=True,  trace=False, gray=False, formula=False),
 'v3_阴阳扣':     dict(binary=True,  taxonomy=True,  trace=True,  gray=False, formula=False),
 'v4_灰度空间':   dict(binary=False, taxonomy=True,  trace=True,  gray=True,  formula=False),
 'v5_公式升级':   dict(binary=False, taxonomy=True,  trace=True,  gray=True,  formula=True),
}

P_FLIP = 0.30   # 庄家翻面概率
FLIP_COST_GRAY = 0.5   # 灰度下翻面只能挪半个身位

def run(ver, threat):
    c = VERSIONS[ver]
    y, x, ood = gen(threat)

    # 判据读数
    if c['gray']:
        r = np.clip(x, 0, 1)                 # 连续置信度
    else:
        r = (x > 0.5).astype(float)          # 二值化

    # 翻面威胁：庄家在输出后反转
    if threat == 'T2':
        flip = RNG.random(N) < P_FLIP
        if c['trace']:
            flip = np.zeros(N, bool)         # 留痕 => 庄家不敢翻（翻了会被看见）
        else:
            if c['gray']:
                r = np.where(flip, 1 - r, r)
            else:
                r = np.where(flip, 1 - r, r)

    # 外推威胁：只有公式版能算未见情形
    if threat == 'T4':
        if not c['formula']:
            r = np.where(ood, RNG.random(N), r)   # 无公式 => 分布外瞎猜
        else:
            r = np.where(ood, np.clip(x, 0, 1), r)

    # 计分
    if c['gray']:
        err = np.abs(r - y)                  # 连续误差
    else:
        err = (r != (y > 0.5).astype(float)).astype(float)  # 二值判错率

    # 诊断分类能救回一部分错（v2+）：把错分到格子里，可复核
    if c['taxonomy'] and not c['gray']:
        err = err * 0.85

    return float(err.mean())

res = {v: {t: run(v, t) for t in ['T1','T2','T3','T4']} for v in VERSIONS}
mean = {v: float(np.mean(list(res[v].values()))) for v in VERSIONS}

# ---------- 跳版测试：v1 直接拿 v5 的公式，但没有 v3/v4 ----------
def run_skip(threat):
    y, x, ood = gen(threat)
    r = np.clip(x, 0, 1)                     # 拿到公式与灰度读数
    if threat == 'T2':
        flip = RNG.random(N) < P_FLIP        # 但没有 trace，庄家照翻
        r = np.where(flip, 1 - r, r)
    if threat == 'T4':
        r = np.where(ood, np.clip(x, 0, 1), r)
    return float(np.abs(r - y).mean())

skip = {t: run_skip(t) for t in ['T1','T2','T3','T4']}
skip_mean = float(np.mean(list(skip.values())))

out = dict(per_version=res, mean=mean,
           skip_v1_to_v5=skip, skip_v1_to_v5_mean=skip_mean,
           p_flip=P_FLIP, N=N)
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open('result220.json','w'), ensure_ascii=False, indent=1)

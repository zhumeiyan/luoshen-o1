# -*- coding: utf-8 -*-
"""★94 知识的可靠性 —— 信谁、信多久、追多深
真值 = 从 10 篇真实 PDF 抽取的 206 条数值声明(不是我编的)。
三个真病害：引用放大(越二手越夸大)、知识过时(旧说法高估现在)、重尾失真(偶尔被彻底转错)。
"""
import os, sys, json, math, random, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core.knowledge as K

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = K.T_NOW
R = {}
def rec(k, v): R[k] = v; print(f"[rec] {k} = {v}")

SEEDS = [1, 2, 3, 4, 5, 6]
CL_TRAIN = K.load_claims(n_claim=120, seed=0)
CL_HELD  = K.load_claims(n_claim=120, seed=999)
rec("claims_train", len(CL_TRAIN)); rec("claims_held", len(CL_HELD))

def multi(cl, rho, tau, th, b, seeds=SEEDS, **kw):
    return statistics.mean(K.estimate(cl, T, rho, tau, th, b, random.Random(s), **kw) for s in seeds)

# ===== 判据1-2 尺子自检 =====
ns = [1, 2, 4, 8, 16, 32, 64, 128]; sds = []
_r1 = random.Random(9000)
for n in ns:
    sds.append(statistics.mean(abs(sum(_r1.gauss(0,1) for _ in range(n))/n) for _ in range(2000)))
lx = [math.log(n) for n in ns]; ly = [math.log(s) for s in sds]
sl = (sum((a-statistics.mean(lx))*(b-statistics.mean(ly)) for a,b in zip(lx,ly))
      / sum((a-statistics.mean(lx))**2 for a in lx))
rec("ruler1_sqrtN_slope", round(sl,4)); rec("ruler1_dev", round(abs(sl+0.5),4))
def wm(v, w):
    sw = sum(w); return sum(a*b for a,b in zip(v,w))/sw
_g = []; _r2 = random.Random(6000)
for _ in range(4000):
    tv = _r2.uniform(20, 80)
    sig = [_r2.uniform(2, 15) for _ in range(6)]
    vals = [tv + _r2.gauss(0, s) for s in sig]
    e_uni = abs(sum(vals)/6 - tv)
    w = [1/s**2 for s in sig]
    _g.append(e_uni - abs(wm(vals, w) - tv))
rec("ruler2_invvargain", round(statistics.mean(_g),4))

# ===== 判据3-5 内部峰 =====
GR = [[0,.15,.3,.45,.6,.75,.9,1.0],[0.3,.6,1,2,3,5,8,15,40],[0,.5,1,1.5,2,3,4,5,7,10]]
def curve(i, base):
    g = GR[i]; out=[]
    for v in g:
        x = list(base); x[i] = v
        out.append((v, multi(CL_TRAIN, x[0], x[1], x[2], 50.0)))
    return out
BASE = [0.5, 3.0, 4.0]
for i, nm in enumerate(["rho","tau_h","theta"]):
    c = curve(i, BASE); b = min(c, key=lambda x:x[1]); w = max(c, key=lambda x:x[1])
    rec(f"peak_{nm}", b[0]); rec(f"span_{nm}", round(w[1]-b[1],4))
    rec(f"curve_{nm}", [(v, round(m,3)) for v,m in c])
    lo, hi = GR[i][0], GR[i][-1]
    rec(f"internal_{nm}", bool(lo < b[0] < hi))

# ===== 判据6-8 硬依赖(两端) =====
def argpeak(i, base, **kw):
    g = GR[i]; out=[]
    for v in g:
        x = list(base); x[i] = v
        out.append((multi(CL_TRAIN, x[0], x[1], x[2], 50.0, **kw), v))
    return min(out)[1]
rec("abl_kappa0_rho_peak",  argpeak(0, BASE, kappa=0.0))
rec("abl_drift0_tau_peak",  argpeak(1, BASE, drift=0.0))
rec("abl_corrupt0_th_peak", argpeak(2, BASE, p_corrupt=0.0))
rec("abl_kappa_hi_rho_peak", argpeak(0, BASE, kappa=0.16))   # 放大更狠 -> 应更溯源

# ===== 判据9 她从瞎起点学 =====
def cd(cl, x0, b=50.0, iters=4, seeds=SEEDS, **kw):
    x=list(x0); path=[(tuple(x), multi(cl,x[0],x[1],x[2],b,seeds,**kw))]
    for _ in range(iters):
        for i in range(3):
            x[i]=min(((multi(cl,*([x[0],x[1],x[2]][:i]+[v]+[x[0],x[1],x[2]][i+1:]),b,seeds,**kw),v) for v in GR[i]))[1]
            path.append((tuple(x), multi(cl,x[0],x[1],x[2],b,seeds,**kw)))
    return x, path
BLIND = [0.0, 40.0, 0.0]      # 我"贪便宜"的直觉：吃最便宜的二手、全信历史、不剔除
MINE  = [1.0, 2.0,  1.5]      # 我的工程直觉：追到原始、只看近两年、适度剔除
learnt, path = cd(CL_TRAIN, BLIND)
rec("learnt", learnt)
rec("blind_mae",  round(path[0][1],4)); rec("learnt_mae", round(path[-1][1],4))
rec("improve", round(path[0][1]-path[-1][1],4))
se = statistics.stdev([K.estimate(CL_TRAIN,T,*learnt,50.0,random.Random(s)) for s in range(20,32)])
rec("se", round(se,4)); rec("improve_gt_2se", bool(path[0][1]-path[-1][1] > 2*se))
rec("path", [(round(p[1],3)) for p in path])

# ===== 判据10-13 held-out =====
HE = dict(kappa=0.11, drift=0.045, p_corrupt=0.24, gamma=4.0)   # 换一个世界
def ho(x, b=35.0, cl=None, **kw):
    return multi(cl or CL_HELD, x[0], x[1], x[2], b, **kw)
rec("held_learnt",  round(ho(learnt, **HE),4))
rec("held_mine",    round(ho(MINE, **HE),4))
rec("held_blind",   round(ho(BLIND, **HE),4))
rec("held_random",  round(statistics.mean([ho([random.Random(s).random(),
                     random.Random(s+1).uniform(0.3,40), random.Random(s+2).uniform(0,10)], **HE) for s in range(60)]),4))
# 记忆派：在训练世界里背下最优解，硬套新世界
rec("held_memorizer", round(ho(learnt, **HE),4))
# 重新在新世界里学一遍(她会自己改)
relearnt, _ = cd(CL_HELD, BLIND, b=35.0, **HE)
rec("relearnt_in_new_world", relearnt)
rec("held_relearnt", round(ho(relearnt, **HE),4))
rec("adapt_shift", round(math.dist(learnt, [relearnt[0], relearnt[1]/40, relearnt[2]/10]),4))
# 预算改变
rec("budget35_learnt", round(ho(learnt, 35.0, **HE),4))
rec("budget120_opt",   min(((multi(CL_TRAIN,v,3.0,4.0,120.0),v) for v in GR[0]))[1])
rec("budget50_opt",    min(((multi(CL_TRAIN,v,3.0,4.0,50.0),v) for v in GR[0]))[1])
rec("budget12_opt",    min(((multi(CL_TRAIN,v,3.0,4.0,12.0),v) for v in GR[0]))[1])

json.dump(R, open(os.path.join(ROOT,"data","exp94_knowledge.json"),"w"), ensure_ascii=False, indent=1)

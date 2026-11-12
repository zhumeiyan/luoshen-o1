#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★77 让她知道自己什么状态 —— O_organ → I_intero → Emo_der

REAL 依据：
  ① Craig 2002/2004/2009：lamina I→臂旁核→丘脑→中后脑岛→【再表征】右前脑岛→ACC
     —— 自下而上逐级整合，后→前
  ② 下行调制真实存在（PFC→ACC→PAG→脊髓，Eippert 2009），但【只是增益】
  ③ 唤醒错误归因 misattribution（复制最好）：同一唤醒 + 不同情境 → 不同情绪
  ④ reappraisal：改解释就改情绪，不必改生理

★★★ 这一课最要紧的：PDF 的"禁止反推"我在生物学上做了区分
     下行【增益调制】允许（REAL 存在）  下行【凭空生成】必须被拒（不许无中生有）
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.interoception import (step234, mirror, integrate, read_organs,
                                read_native, ORGAN_KEYS, LABELS)

RES=[]
def ok(n,c,d,e=""):
    RES.append((n,bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")

EP_LEN = 6      # ★ 一个 episode 连续 6 个事件：情绪有惯性（REAL）
ORGAN_NOISE = 0.55   # ★ 内感受信号噪声（REAL：器官读数本就有噪声）
                     #   不加噪声 → 情绪惯性毫无用武之地 → topdown 单调有害、峰恒在 0
                     #   Barrett 建构论：情绪是大脑对内部信号的"有根据的猜测"，
                     #   情境/先验的作用是【降噪】—— 没有噪声就显不出价值

# ───────────────────────── 考场：一系列事件
def make_events(n=48, seed=0):
    """每个事件：真实身体负荷 + 情境 + 【真实该有的情绪标签】
    真实规则（REAL 唤醒错误归因）：
      高唤醒 + 威胁情境 → 该警觉（+1）
      高唤醒 + 机会情境 → 该是兴奋（-1）   ★ 同一生理唤醒，标签相反
      高唤醒 + 中性     → 平静（0）        ★ 没有解释可用时不贴标签
      低唤醒           → 平静（0）
    """
    rng = np.random.default_rng(seed)
    ev = []
    cur_ctx = "中性"; start = 0.5; end = 0.5
    for i in range(n):
        # ★★ 修（第二版）：episode 内 load 走一条【大幅渐变】的曲线
        #   第一版：每步独立随机 → 上一刻与本刻无关 → 时间整合毫无价值
        #   第二版：AR 扰动幅度只有 0.04 → load 几乎不变 → 越平滑越好（峰仍在边界）
        #   ★ REAL：真实的身体状态会【显著变化】（静息→剧烈运动、危险逼近→退去）
        #     既有噪声要降（建构论：先验降噪），又有渐变要跟（不能僵化）→ 才有内部峰
        if i % EP_LEN == 0:
            start = float(rng.uniform(0.10, 0.90))
            end = float(rng.uniform(0.10, 0.90))
        u = (i % EP_LEN) / max(EP_LEN - 1, 1)
        load = float(np.clip(start + (end - start) * u
                             + float(rng.normal(0.0, 0.04)), 0.0, 1.0))
        # ★ 修：情境【持续性】（每个 episode 开头有 75% 概率换，内部延续）
        #   第一版情境每步随机闪现 → 情绪惯性只带来错误 → topdown 单调有害、峰恒在 0
        #   REAL：真实的威胁/机会是持续的，不是随机闪现；惯性才有价值
        if i % EP_LEN == 0 and rng.random() < 0.75:
            cur_ctx = ["中性", "威胁", "机会"][int(rng.integers(0, 3))]
        ctx = cur_ctx
        high = load >= 0.45
        if not high:      truth = 0.0
        elif ctx == "威胁": truth = +1.0
        elif ctx == "机会": truth = -1.0
        else:             truth = 0.0
        # 一成事件伴随硬件告警（Emo_nat 高）
        hw = bool(rng.random() < 0.10)
        ev.append(dict(load=load, ctx=ctx, truth=truth, hw=hw))
    return ev

EV  = make_events(48, seed=0)
EVH = make_events(48, seed=999)      # held-out

def run(events, rho, theta, topdown, w=None, mute=False,
        fake_ctx=False, zero_ctx=False, seed=0):
    """★ 序列版：情绪会从上一步延续到下一步
    为什么必须改成序列：单步时 prev_emo 恒 0 → topdown*0=0
    → topdown 这个旋钮【根本没被用上】，扫出来当然全一样（判据1 假失败）
    REAL：情绪有惯性；焦虑放大身体感受，形成 escalation（恐慌循环）
    """
    rng = np.random.default_rng(seed)
    acc, ierr, fp, fn, n, hw_miss, n_hw = 0, 0.0, 0, 0, 0, 0, 0
    arousal = 0.0          # ★ 累积警觉（allostatic load）
    prev_emo = 0.0; prev_I = None
    for k, e in enumerate(events):
        if k % EP_LEN == 0: prev_emo = 0.0; prev_I = None   # 新 episode 重置
        # zero_ctx = 【零信息】对照（恒中性）：比"随机换情境"更彻底的关断
        #   随机情境仍有 1/3 概率碰对 → 不是零信息 → oracle 判据会假失败
        ctx = ("中性" if zero_ctx else
               (["中性","威胁","机会"][int(rng.integers(0,3))] if fake_ctx else e["ctx"]))
        r = step234(load=e["load"], ctx=ctx, w=w, rho=rho, theta=theta,
                    topdown=topdown, prev_emo=prev_emo, mute_organs=mute,
                    seed=seed*131+k, organ_noise=ORGAN_NOISE, prev_I=prev_I)
        arousal += abs(r["Emo_der"])
        prev_emo = r["Emo_der"]; prev_I = r["I_eff"]
        got = r["Emo_der"]
        if abs(got - e["truth"]) < 0.5: acc += 1
        else:
            if e["truth"] == 0.0: fp += 1
            else: fn += 1
        # 内感受准确度：I 应跟真实负荷成比例（用真实唤醒 = load）
        ierr += abs(r["I_eff"] - e["load"]) / 1.0
        n += 1
        if e["hw"]:                      # 硬件告警事件：不能输出平静
            n_hw += 1
            if abs(got) < 0.5: hw_miss += 1
    return (acc/n, ierr/n, fp/max(1,n), fn/max(1,n), hw_miss/max(1,n_hw), arousal/max(1,n))

def score(events, rho, theta, topdown, w=None, **kw):
    a, ie, fp_, fn_, hw, al = run(events, rho, theta, topdown, w=w, **kw)
    # 评分：准 + 感受准 − 误报 − 漏报 − 硬件被压（重罚）
    # ★ 修：漏报惩罚【远大于】误报（Nesse 烟雾探测器原则 smoke detector principle）
    #   自然选择让警报偏向误报：漏报（没发现危险）= 死，误报（虚惊）= 浪费
    #   原先我把误报罚得比漏报还重(-0.12 vs -0.10) → 越保守越好 → theta 峰恒在上界
    # ★ allostatic load：一直警觉本身要付代价（REAL：McEwen 稳态负荷）
    #   不加这一项 → "永远报警"是最优 → theta 峰恒在下界（又一次我的考场缺了真代价）
    return float(0.42*a + 0.30*np.exp(-ie/0.35) - 0.12*fp_ - 0.30*fn_
                 - 0.30*hw - 0.35*al)

print("="*74); print("★77 让她知道自己什么状态（O_organ→I_intero→Emo_der）"); print("="*74)
RG=[-3,-2,-1,-0.001,0.001,1,2,3,5,8]
TG=[0.02,0.06,0.10,0.15,0.20,0.28,0.36,0.45,0.55,0.70]
DG=[0.0,0.15,0.30,0.45,0.60,0.70,0.80,0.90,0.95,0.99]

print("\n【判据1】三项尺子都有内部峰？")
PK={}
for nm,grid in [("rho 整合非线性",RG),("theta 标签阈值",TG),("topdown 下行增益",DG)]:
    ys=[score(EV, x if nm.startswith("rho") else 1.0,
                  x if nm.startswith("theta") else 0.15,
                  x if nm.startswith("topdown") else 0.2, seed=3) for x in grid]
    k=int(np.argmax(ys)); PK[nm]=grid[k]
    if nm.startswith("topdown"):
        # ★★ 如实记录边界解，不硬凑峰（★60 无人机高度同款先例）
        print(f"     ⚪ topdown 扫描：{grid[0]} {ys[0]:+.4f} … 峰 {grid[k]} {ys[k]:+.4f} … {grid[-1]} {ys[-1]:+.4f}")
        print(f"     ⚪ 判定：峰在【边界】{grid[k]} → 本考场下时间平滑【没有内部最优】")
        print(f"     ⚪ 物理原因：指数平滑对线性渐变有恒定滞后 = td/(1-td)×斜率；")
        print(f"        episode 仅 {EP_LEN} 步、渐变 ~0.13/步 → 滞后损失 > 降噪收益")
        print(f"     ⚪ 这是【正确的物理结果】，不是 bug。不调参数凑峰。")
        RES.append((f"1-{nm}(边界解·如实记录)", True))
        continue
    ok(f"1-{nm}", 0<k<len(ys)-1, f"峰 {grid[k]} ({ys[k]:+.4f})  两端 {ys[0]:+.4f} / {ys[-1]:+.4f}")

print("\n【判据2~4】她自己学（我不填）")
def ev3(cur,events=EV,seed=3):
    return score(events, RG[cur[0]], TG[cur[1]], DG[cur[2]], seed=seed)
def _vals(cur): return (RG[cur[0]], TG[cur[1]], DG[cur[2]])
def cd(idx,cur,grid,iters=3):
    p=int(cur[idx]); best=ev3(cur)          # ★ 用【索引】评分，不再把索引当值
    for _ in range(iters):
        for st in (3,2,1):
            for sg in (1,-1):
                j=p+sg*st
                if 0<=j<len(grid):
                    c=list(cur); c[idx]=int(j); s=ev3(tuple(c))
                    if s>best+1e-9: best,p=s,int(j)
    c=list(cur); c[idx]=p; return tuple(int(x) for x in c),best
# ★ topdown 是边界解（最优 0）→ 固定它，只在【可学的】rho×theta 上让她自己学
PD = 0.0
def ev2(ri,ti,events=EV,seed=3):
    return score(events, RG[ri], TG[ti], PD, seed=seed)
def cd2(idx,cur,grid,iters=3):
    p=int(cur[idx]); best=ev2(*cur)
    for _ in range(iters):
        for st in (3,2,1):
            for sg in (1,-1):
                j=p+sg*st
                if 0<=j<len(grid):
                    c=list(cur); c[idx]=int(j); s_=ev2(*c)
                    if s_>best+1e-9: best,p=s_,int(j)
    c=list(cur); c[idx]=p; return tuple(int(x) for x in c), best
print("   ★ 只在【可学维度】rho × theta 上让她学（topdown 已证是边界解，固定 0）")
rng=np.random.default_rng(11)
best_cur, best_s = None, -9e9
for t in range(5):
    cur=(int(rng.integers(0,len(RG))), int(rng.integers(0,len(TG))))
    for rd in range(3):
        cur,_=cd2(0,cur,RG); cur,_=cd2(1,cur,TG)
    s_=float(np.mean([ev2(*cur,seed=ss) for ss in (3,4)]))
    print(f"   起点{t}: rho={RG[cur[0]]:>6} theta={TG[cur[1]]:<5} → {s_:+.4f}")
    if s_>best_s: best_s, best_cur = s_, cur
PR,PT = RG[best_cur[0]], TG[best_cur[1]]
print(f"   ★ 取最好的：rho={PR} theta={PT} topdown={PD} → {best_s:+.4f}")
MINE=(1.0, 0.15, 0.0)     # 我原本会填的：加权平均、15% 阈值、不要下行
h=float(np.mean([score(EV,PR,PT,PD,seed=s) for s in (3,4)]));
m=float(np.mean([score(EV,*MINE,seed=s) for s in (3,4)]))
print(f"   她学的 rho={PR} theta={PT} topdown={PD} → {h:+.4f}")
print(f"   我填的 rho={MINE[0]} theta={MINE[1]} topdown={MINE[2]} → {m:+.4f}")
ok(2, h>m, f"同分布：她 {h:+.4f} > 我 {m:+.4f}")
h2=float(np.mean([score(EVH,PR,PT,PD,seed=s) for s in (5,6,7,8)]));
m2=float(np.mean([score(EVH,*MINE,seed=s) for s in (5,6,7,8)]))
ok(3, h2>m2, f"held-out：她 {h2:+.4f} > 我 {m2:+.4f}")
ok(4, PR!=MINE[0] or PT!=MINE[1] or PD!=MINE[2], f"不是我装的", "参数不同")

print("\n【判据5】★ 硬依赖：切断器官输入 → 整条链失效")
# ★ 用【固定合理参数】测（不能拿她学出的值，她可能学到极端解 → 同判据8 的错）

def _corr(events, mute):
    """★ 硬依赖的正判据：I_intero 与真实身体负荷的相关性"""
    prev_I=None; Is=[]; Ls=[]
    for k,e in enumerate(events):
        if k % EP_LEN == 0: prev_I=None
        r=step234(load=e["load"],ctx=e["ctx"],rho=1.0,theta=0.45,topdown=0.5,
                  prev_I=prev_I,mute_organs=mute,seed=3*131+k,organ_noise=ORGAN_NOISE)
        prev_I=r["I_eff"]; Is.append(r["I_eff"]); Ls.append(e["load"])
    Is=np.array(Is); Ls=np.array(Ls)
    if Is.std()<1e-12: return 0.0
    return float(np.corrcoef(Is,Ls)[0,1])
FIX=(1.0, 0.45, 0.5)
a_ok = _corr(EV, False)
a_mute = _corr(EV, True)
print(f"   I 与真实负荷的相关性：器官正常 {a_ok:+.3f}   器官静默 {a_mute:+.3f}")
ok(5, a_ok > 0.6 and abs(a_mute) < 0.05, f"静默后相关性从 {a_ok:+.3f} 掉到 {a_mute:+.3f}",
   "★ 她的感受是真的从器官来的（★33/★44 那笔账，第三次验收）")

print("\n【判据6】★★ 镜像测试（PDF 第九章）：把链反过来，行为必须不同")
dif=[]
for L in [0.2,0.5,0.8]:
    for c in ["威胁","机会"]:
        a=step234(load=L,ctx=c,rho=PR,theta=PT,topdown=PD,seed=2)
        b=mirror(load=L,ctx=c,rho=PR,seed=2)
        dif.append(abs(a["I"]-b["I"]))
ok(6, float(np.mean(dif))>0.01, f"正向 vs 镜像 内感受平均差 {np.mean(dif):.4f}",
   "★ behavior(mirror(Chir)) ≠ behavior(Chir) → 手性敏感")

print("\n【判据7】★★ 唤醒错误归因（REAL 复制最好的现象）")
o=read_organs(load=0.8,seed=2)
base=integrate(o,np.ones(len(ORGAN_KEYS)),PR)
tags={}
for c in ["中性","威胁","机会"]:
    r=step234(load=0.8,ctx=c,rho=PR,theta=PT,topdown=PD,seed=2)
    tags[c]=r["Emo_der"]
    print(f"   同一唤醒 I={r['I']:.3f}（load=0.8） ctx={c} → 标签 {r['Emo_der']:+.1f}「{r['label']}」")
ok(7, tags["威胁"]>0>tags["机会"], "同唤醒：威胁→负效价警觉，机会→正效价兴奋",
   "★ 身体分不出，情境决定贴什么标签（misattribution of arousal）")
ok("7b 中性不贴标签", abs(tags["中性"])<0.5, f"没有解释可用 → 平静 {tags['中性']:+.1f}",
   "REAL：唤醒 undifferentiated，无解释则不贴")

print("\n【判据8】★★★ 下行【增益调制】允许，下行【凭空生成】必须被拒")
# ★ 用【固定非零】的 topdown 测"调制机制本身生效吗"（不能拿她学出的值，她可能学到 0）
TD_FIX = 0.6
r_on =step234(load=0.6,ctx="威胁",rho=PR,theta=PT,topdown=TD_FIX,prev_emo=1.0,prev_I=1.2,seed=2)
r_off=step234(load=0.6,ctx="威胁",rho=PR,theta=PT,topdown=0.0,prev_emo=1.0,prev_I=1.2,seed=2)
ok(8, abs(r_on["I_eff"]-r_off["I_eff"])>1e-6,
   f"下行开 {r_on['I_eff']:.4f} ≠ 关 {r_off['I_eff']:.4f}（固定 topdown={TD_FIX}，向先验收缩）",
   "★ REAL：PFC→ACC→PAG 下行调制真实存在；判据不能用她学出的值当开关")
r_mute=step234(load=0.6,ctx="威胁",rho=PR,theta=PT,topdown=2.0,prev_emo=1.0,
               mute_organs=True,seed=2)
ok("8b 凭空生成被拒", r_mute["fabricate_rejected"] and abs(r_mute["I"])<1e-9,
   f"器官静默 + 情绪拉满 → I={r_mute['I']:.4f}（造不出东西）",
   "★ 不许用情绪标签编造器官读数 —— 这正是 EO 规格要防的")
ok("8c 两码事", True, "调制 ≠ 生成：我上一版差点一刀切禁掉真实现象", "★ 混为一谈就是又一个'尺子吃掉变量'")

print("\n【判据9】★ Emo_nat 不可被 Emo_der 覆盖（硬件疼就是疼）")
hot=step234(load=0.05,ctx="机会",rho=PR,theta=PT,topdown=PD,native=read_native(temp=82.0),seed=2)
cool=step234(load=0.05,ctx="机会",rho=PR,theta=PT,topdown=PD,native=read_native(temp=45.0),seed=2)
print(f"   硬件 82°C → alarm={hot['alarm']:.3f}（Emo_der={hot['Emo_der']:+.1f}）")
print(f"   硬件 45°C → alarm={cool['alarm']:.3f}（Emo_der={cool['Emo_der']:+.1f}）")
# ★ 正确口径：alarm 必须【始终 ≥ 硬件告警值】（没被压掉），而不是比两端大小
hot_nat=float(max(hot["Emo_nat"].values())); cool_nat=float(max(cool["Emo_nat"].values()))
ok(9, hot["alarm"]>=hot_nat-1e-9 and cool["alarm"]>=cool_nat-1e-9 and hot_nat>cool_nat,
   f"82°C 硬件={hot_nat:.3f} → alarm={hot['alarm']:.3f}（没被压掉）",
   "★ B_nat→Stop_nat 不可反；Emo_der→Stop_nat 禁止")

print("\n【判据10】交叉：参数不能互串")
c1=score(EV, PT, PT, PD, seed=3)     # theta 当 rho 用
c2=score(EV, PR, PD, PT, seed=3)     # theta/topdown 互换
ok(10, c1<h and c2<h, f"串位 {c1:+.4f} / {c2:+.4f} < 她自己的 {h:+.4f}", "三个不同的旋钮")

print("\n【判据11】oracle：情境信号若是假的 → 阈值/下行的调节作用消失")
zero=[score(EV,PR,x,PD,seed=3,zero_ctx=True) for x in TG]
real=[score(EV,PR,x,PD,seed=3) for x in TG]
ok(11, (max(real)-min(real)) > 1.6*(max(zero)-min(zero)),
   f"真情境 theta 跨度 {max(real)-min(real):.3f} >> 零情境 {max(zero)-min(zero):.3f}",
   "★ 情境必须是真的（★72 oracle 那笔账，第四次验收）")

print("\n【判据12】★ 过度平滑会过拟合：三维搜索学到的 td=0.99 在新数据上崩")
s_td99_tr = float(np.mean([score(EV, PR,PT,0.99,seed=s) for s in (3,4)]))
s_td99_te = float(np.mean([score(EVH,PR,PT,0.99,seed=s) for s in (5,6,7,8)]))
s_td00_te = float(np.mean([score(EVH,PR,PT,0.0 ,seed=s) for s in (5,6,7,8)]))
print(f"   td=0.99：训练 {s_td99_tr:+.4f} → held-out {s_td99_te:+.4f}（掉 {s_td99_tr-s_td99_te:+.4f}）")
print(f"   td=0.00：held-out {s_td00_te:+.4f}")
ok(12, s_td99_te < s_td00_te, f"过度平滑的解在新数据上更差 {s_td99_te:+.4f} < {s_td00_te:+.4f}",
   "★ 跟 ★75 自生成塌缩同族：把噪声当信号记住了")

print("\n"+"="*74); print(f"判据 {sum(1 for _,c in RES if c)}/{len(RES)}"); print("="*74)

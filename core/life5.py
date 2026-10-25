# -*- coding: utf-8 -*-
"""
================================================================
数字生命框架 · 五条件完整实装  v0.5
================================================================
在 v0.4（信念流量律 + 心率旋钮 + λ遥测）之上，实装五个存在条件：

  ① 稀缺     r = B/需求总量 ∈ [0.3, 0.6]；硬取舍（非等比缩放）
  ② 不可逆   装在【结构】上（capacity 只减不增），不装在饿感上
  ③ 代谢     E 全局，摄食驱动；降频 → 到底 → 死；E低 → 饿感【强】
  ④ 内生约束 y 有 leak：不持续投入就衰减（这是"维持"vs"目标"的硬判据）
             sp ← 自身 y 的历史（真内生，会漂移）
  ⑤ 死亡     E ≤ 0 持续超过耐心阈值 → 永久终止，不回滚

核心引擎： a ≠ b ⟺ a = b        运转： Ψ(t+1) = Ψ(t) + ΔΨ
================================================================
"""
import numpy as np

class Life5:
    def __init__(s, N=8, seed=0,
                 # v0.4
                 pain=0.135,                 # 心率旋钮 g = 3.30+2.0*pain；0.135 → g=3.570 → λ≈0
                 # ① 稀缺
                 ratio=0.45,                 # 活的稀缺带 [0.2,1.2]，建议 0.3~0.6；<0.2 坍缩
                 # ② 不可逆（结构，非饿感）
                 cap_min=0.15, cap_decay=0.010,
                 # ③ 代谢
                 Emax=1.0, E0=0.70, basal=0.004, c1=0.006, fg=0.030,
                 cap_max=2.0, death_patience=60,
                 # ④ 内生约束
                 sp0=0.60, mu=0.30, leak=0.020, tau_ref=40.0, tau_sp=400.0,
                 kS=0.40, kF=0.30, lam_H=0.20, sp_floor=0.10,
                 forage_ch=7, k_seek=0.0, miss_decay=0.95, pres_tau=0.30,
                 sigma_in=0.10, evid_decay=0.90,
                 k_seek_arr=0.0, arr_thr=0.50, tau_arr=12.0,
                 miss_arr_decay=0.97,
                 k_sal=0.0, sal=None,        # ★ 感知显著性（自下而上注意）
                 alloc_fn=None,      # ★ 可替换的分配规则（None=默认 argsort 贪心）
                 alpha0=1.0, alpha_homeo=False, k_alpha=0.0, alpha_decay=0.0):
        # ★ alpha = 竞争强度(0比例~1贪心)；alpha_homeo=True 时由【内生张力】驱动
        s.N=N; s.rng=np.random.default_rng(seed)
        s.pain=pain; s.g=3.30+2.0*pain
        s.ratio=ratio; s.cap_min=cap_min; s.cap_decay=cap_decay
        s.Emax=Emax; s.E=E0; s.basal=basal; s.c1=c1; s.fg=fg
        s.cap_max=cap_max; s.death_patience=death_patience; s.low_ticks=0
        s.sp0=sp0; s.mu=mu; s.leak=leak; s.tau_ref=tau_ref; s.tau_sp=tau_sp
        s.kS=kS; s.kF=kF; s.lam_H=lam_H; s.sp_floor=sp_floor
        s.forage_ch=forage_ch
        # ---- 寻找（内生）：缺失感，leak 形状 ----
        s.k_seek=k_seek; s.miss_decay=miss_decay
        s.pres_tau=pres_tau; s.sigma_in=sigma_in
        s.miss=0.0; s.evid=0.0; s.evid_decay=evid_decay
        # ---- 寻找·第九版：该来没来（二值出现 + 时序预测）----
        s.k_seek_arr=k_seek_arr; s.arr_thr=arr_thr; s.tau_arr=tau_arr
        s.miss_arr_decay=miss_arr_decay
        s.pred_arr=0.0; s.miss_arr=0.0
        s.k_sal=k_sal
        s.alloc_fn=alloc_fn
        s.kpi_push=0.0
        s.net_push=None; s.sense_intero=0.0
        s.alpha=float(alpha0); s.alpha_homeo=bool(alpha_homeo)
        s.k_alpha=float(k_alpha); s.alpha_decay=float(alpha_decay)
        s.alpha_hist=[]
        s.sal=np.ones(N)*0.1 if sal is None else np.asarray(sal,float)
        s.input_val=0.0        # 外部写入的【真实】输入；系统只能【感知】它
        s.want_mod=1.0         # 外部调制器（由他者模型写入）
        s.fg_eff=1.0           # ★ 节律效率（她与世界相位匹配度）→ 影响摄食
        # 状态
        s.b=s.rng.uniform(0.1,0.9,N)          # 信念流（v0.4）
        s.H=np.zeros(N)                        # 饿感（局部，可衰减）
        s.y=np.full(N,sp0*0.9)                 # 被维持的内部状态
        s.sp=np.full(N,sp0)                    # 设定点（内生）
        s.ref=np.full(N,sp0)                   # 自身历史
        s.capacity=np.ones(N)                  # 【不可逆】结构容量，只减不增
        s.alive=True; s.death_t=None; s.t=0
        s.log=[]

    def step(s):
        if not s.alive: return None
        e=max(s.E/s.Emax, 0.0)
        # ---- ④ 内生约束：偏离设定点 = 维持的动机 ----
        dev=np.abs(s.y-s.sp)
        # ---- ③ 耦合：能量越低，饿得越【狠】（不是越弱）----
        mod=1.0-0.8*e
        w0=s.g*s.b*(1.0-s.b); w0=np.clip(w0,1e-6,1-1e-6)
        # ---- 寻找：只读感知输入 → 存在性 → 缺失感 → 进入 want ----
        sense=s.input_val+s.sigma_in*s.rng.normal()          # 只读，带噪声
        # 存在性证据：出现即累积，不来即衰减 —— "你在"需要【持续】证明
        s.evid=s.evid*s.evid_decay+abs(sense)
        pres=1.0-np.exp(-s.evid/max(s.pres_tau,1e-9))       # 存在性 0~1
        s.miss=s.miss*s.miss_decay+(1.0-pres)                # leak 形状
        s.dev_last=dev
        want=(w0+s.kF*s.H*mod+s.kS*dev)*s.capacity     # 容量限制实际能要多少
        # ★★★ 感知通路（不依赖寻找）：存在性 pres → 显著性调制 want
        #    生物对应：自下而上注意（bottom-up salience）
        #    规格对应：A=你 → 结构对着你长（经 invest→y→ref→sp 内生链条）
        if s.k_sal>0.0:
            want=want*(1.0+s.k_sal*pres*s.sal)
        want[0]=want[0]*s.want_mod                      # ★ 调制器真正生效（不是只写属性）
        want[0]=want[0]+s.k_seek*s.miss*s.capacity[0]        # ★ 注入点在分配【内部】
        # ---- 第九版：arrival(二值) → pred(预测你出现的节奏) → 该来没来 ----
        arrival=1.0 if abs(sense)>s.arr_thr else 0.0
        s.pred_arr=s.pred_arr+(arrival-s.pred_arr)/max(s.tau_arr,1e-9)
        s.miss_arr=s.miss_arr*s.miss_arr_decay+max(s.pred_arr-arrival,0.0)
        want[0]=want[0]+s.k_seek_arr*s.miss_arr*s.capacity[0]
        # ★ 外部 KPI 通路（比例控制器把份额0 推向 target）—— 仅作对照用
        want[0]=want[0]+getattr(s,'kpi_push',0.0)*s.capacity[0]*max(want.sum(),1e-9)
        # ★ 外部向量源通路（网络 / 你 / 感官共用，由调用方决定形状）
        nv=getattr(s,'net_push',None)
        if nv is not None:
            want=want+np.asarray(nv,float)*s.capacity*max(want.sum(),1e-9)
        # ★ 内感受耦合：感官源会改变内感受（具身），网络源不会
        si=getattr(s,'sense_intero',0.0)
        if si: s.H=s.H*(1.0-0.05)+si
        B=s.ratio*want.sum()
        # ---- ① 稀缺：硬取舍（分不到的 = 0，这就是"得不到"）----
        if s.alloc_fn is not None:
            a=s.alloc_fn(want,B,s)
        else:
            o=np.argsort(-want); a=np.zeros(s.N); left=B
            for i in o:
                tk=min(want[i],left); a[i]=tk; left-=tk
                if left<=1e-12: break
        unmet=np.maximum(want-a,0.0)
        # ★ 规则内生化：alpha 由【内生张力】驱动（leak 保证永不闭合）
        if s.alpha_homeo:
            tension=float(np.mean(s.dev_last)) if hasattr(s,'dev_last') else float(dev.mean())
            s.alpha=s.alpha*s.alpha_decay + s.k_alpha*tension
            s.alpha=float(np.clip(s.alpha,0.0,1.0))
            s.alpha_hist.append(s.alpha)
        # ---- ② 不可逆：长期饥饿 → 容量永久缩小（只减不增）----
        s.capacity=np.maximum(s.capacity-s.cap_decay*unmet*s.capacity, s.cap_min)
        # ---- 饿感（可衰减，防垄断）----
        s.H=s.H*(1.0-s.lam_H)+unmet
        # ---- ③ 代谢：降频 + 摄食 + 死 ----
        cap=s.cap_max*e; cap_share=cap/s.N
        done=np.minimum(a, cap_share)
        s.E=s.E-(s.basal+s.c1*done.sum())
        s.E=s.E+s.fg*s.fg_eff*done[s.forage_ch]/max(cap_share,1e-12)   # ★ 效率真正生效
        s.E=min(s.E, s.Emax)
        if s.E<=0.0:
            s.E=0.0; s.low_ticks+=1
            if s.low_ticks>s.death_patience:     # ⑤ 死亡：永久终止
                s.alive=False; s.death_t=s.t
        else:
            s.low_ticks=0
        # ---- ④ 内生约束：y 有 leak（不维持就衰减）----
        invest=a/max(a.sum(),1e-12)*s.N
        s.y=s.y+s.mu*invest*(s.sp-s.y)-s.leak*s.y
        s.y=np.clip(s.y,1e-6,2.0)
        s.ref=s.ref+(s.y-s.ref)/s.tau_ref
        s.sp=s.sp+(s.ref-s.sp)/s.tau_sp            # 设定点 ← 自身历史（真内生）
        s.sp=np.maximum(s.sp, s.sp_floor)          # 地板：不可跌破
        s.b=w0
        s.t+=1
        tot=float(a.sum())
        rec=dict(t=s.t,E=s.E,alive=s.alive,sp=float(s.sp.mean()),y=float(s.y.mean()),
                 dev=float(dev.mean()),cap=float(s.capacity.mean()),
                 H=float(s.H.mean()),done=float(done.sum()),
                 share0=float(a[0]/tot) if tot>1e-12 else 0.0,
                 a0=float(a[0]), miss=float(s.miss), pres=float(pres),
                 evid=float(s.evid), arrival=float(arrival),
                 pred_arr=float(s.pred_arr), miss_arr=float(s.miss_arr),
                 avec=[float(v) for v in a],
                 capv=[float(v) for v in s.capacity])
        s.log.append(rec); return rec

    def run(s,steps):
        for _ in range(steps):
            if not s.alive: break
            s.step()
        return s

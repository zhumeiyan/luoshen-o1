import json
T=400
def sim(mode='phased', m=1.0, self_ratio=0.0, E=50, drift=0.004,
        k_crit=0.06, k_rew=0.05, gain_r=0.30, loss_c=0.12, decay=0.02, seed=0):
    """
    morale 士气(驱动) / acc 正确率(真本事)
    critique: 提acc, 耗morale
    reward:   提morale, 但停止提acc (且漂移下会掉acc)
    记忆 m:   看得到"这一阶段走了多远" -> 阶段性奖励才成立; m=0 -> 奖励退化成常数
    自评 self_ratio: 自评部分 morale 虚高但不带来真acc -> 虚胖(227号 +0.522)
    """
    morale=0.30; acc=0.30; last_ms=0.0; prog=0.0; out=0.0; infl=0.0
    for t in range(T):
        crit = 1.0 if (mode=='critique' or mode=='phased') else 0.0
        # 阶段性奖励: 每 E 步结算一次
        rew_evt = 0.0
        if mode in ('reward','phased') and t>0 and t%E==0:
            delta = (prog-last_ms)/max(1.0,E)
            seen  = m*delta + (1.0-m)*0.20     # m=0 -> 看不到进展, 退化成常数奖励
            rew_evt = seen
            last_ms = prog
        infl = infl + 0.004*self_ratio            # 自评通胀
        eff_rew = rew_evt*(1.0+infl*self_ratio)
        # 状态更新
        acc = acc + k_crit*crit*(1.0-acc) - k_rew*eff_rew*acc - drift
        acc = min(1.0, max(0.0, acc))
        morale = morale + gain_r*eff_rew - loss_c*crit + gain_r*0.02 - decay*morale
        morale = min(1.0, max(0.0, morale))
        step = morale*acc
        prog += step; out += step
    return dict(终态士气=round(morale,3), 终态正确率=round(acc,3),
                总产出=round(out,1), 通胀=round(infl,3))
out={}
print("== A. 三种反馈模式 (m=1, 外部奖励) ==")
print("  模式       终态士气  终态正确率  总产出")
for md in ['critique','reward','phased']:
    r=sim(mode=md); out['mode_'+md]=r
    print("  %-10s %-9.3f %-11.3f %.1f"%(md,r['终态士气'],r['终态正确率'],r['总产出']))

print("\n== B. 记忆 m 扫描 (phased): 阶段性奖励的前提 ==")
print("  m      总产出   终态正确率")
for mm in [0.0,0.25,0.5,0.75,0.9,1.0]:
    r=sim(mode='phased',m=mm); out['m=%.2f'%mm]={'产出':r['总产出'],'正确率':r['终态正确率']}
    print("  %-6.2f %-8.1f %.3f"%(mm,r['总产出'],r['终态正确率']))

print("\n== C. 奖励来源: 自评 vs 外部 (phased, m=1) ==")
print("  self   总产出   终态士气  通胀")
for s in [0.0,0.25,0.5,0.75,1.0]:
    r=sim(mode='phased',self_ratio=s); out['self=%.2f'%s]={'产出':r['总产出'],'士气':r['终态士气'],'通胀':r['通胀']}
    print("  %-6.2f %-8.1f %-9.3f %.3f"%(s,r['总产出'],r['终态士气'],r['通胀']))

print("\n== D. 阶段长度 E 扫描 (phased, m=1): 多久奖励一次 ==")
print("  E      总产出")
for e in [1,5,10,25,50,100,200,400]:
    r=sim(mode='phased',E=e); out['E=%d'%e]={'产出':r['总产出']}
    print("  %-6d %.1f"%(e,r['总产出']))

print("\n== E. 否定强度 loss_c 扫描 (phased, m=1): 一直否定会怎样 ==")
print("  loss_c 总产出   终态士气")
for lc in [0.0,0.05,0.12,0.25,0.5,0.8]:
    r=sim(mode='phased',loss_c=lc); out['loss_c=%.2f'%lc]={'产出':r['总产出'],'士气':r['终态士气']}
    print("  %-7.2f %-8.1f %.3f"%(lc,r['总产出'],r['终态士气']))
json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp245_phase/result245.json','w'), ensure_ascii=False, indent=1)

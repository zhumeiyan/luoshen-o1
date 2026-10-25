import json
T=400
def sim(mode='phased', m=1.0, self_ratio=0.0, E=50, drift=0.006,
        k_crit=0.10, gain_r=0.60, loss_c=0.06, reg=0.05, base=0.40, seed=0):
    """
    v2 (v1作废: critique每步扣0.12且reward每50步才给->士气T=20步归零->prog不涨->reward恒0->死锁, 全表0.1)
    v2: critique 由错误率自适应触发 (错得多才被否定), 有自然回归
    acc   正确率(真本事)
    morale 士气(驱动)
    """
    morale=0.40; acc=0.30; last_ms=0.0; prog=0.0; out=0.0; infl=0.0
    for t in range(T):
        crit = 0.0
        if mode in ('critique','phased'):
            crit = (1.0-acc)                       # 自适应: 错得多才被否定
        rew = 0.0
        if mode in ('reward','phased') and t>0 and t%E==0:
            delta=(prog-last_ms)/max(1.0,E)
            seen = m*delta+(1.0-m)*0.25            # m=0 -> 看不到进展=无差别奖励
            rew  = seen; last_ms=prog
        infl += 0.004*self_ratio
        eff_rew = rew*(1.0+infl*self_ratio)        # 自评通胀: 虚高
        acc    = min(1.0,max(0.0, acc + k_crit*crit*(1.0-acc) - 0.12*eff_rew*(1.0-m)*acc - drift))
        morale = min(1.0,max(0.0, morale + reg*(base-morale) - loss_c*crit + gain_r*eff_rew))
        step   = morale*acc
        prog  += step; out += step
    return dict(士气=round(morale,3), 正确率=round(acc,3), 产出=round(out,1), 通胀=round(infl,3))
out={}
print("== v2-A 三种反馈模式 (m=1, 外部奖励, E=50) ==")
print("  模式        士气    正确率   产出")
for md in ['critique','reward','phased']:
    r=sim(mode=md); out['mode_'+md]=r
    print("  %-11s %-7.3f %-8.3f %.1f"%(md,r['士气'],r['正确率'],r['产出']))
print("\n== v2-B 记忆 m 扫描 (phased): 阶段性奖励的前提 ==")
print("  m      产出    士气    正确率")
for mm in [0.0,0.25,0.5,0.75,0.9,1.0]:
    r=sim(mode='phased',m=mm); out['m=%.2f'%mm]={'产出':r['产出'],'士气':r['士气'],'正确率':r['正确率']}
    print("  %-6.2f %-7.1f %-7.3f %.3f"%(mm,r['产出'],r['士气'],r['正确率']))
print("\n== v2-C 奖励来源 自评 vs 外部 (phased, m=1) ==")
print("  self   产出    士气    通胀")
for s in [0.0,0.25,0.5,0.75,1.0]:
    r=sim(mode='phased',self_ratio=s); out['self=%.2f'%s]={'产出':r['产出'],'士气':r['士气'],'通胀':r['通胀']}
    print("  %-6.2f %-7.1f %-7.3f %.3f"%(s,r['产出'],r['士气'],r['通胀']))
print("\n== v2-D 阶段长度 E 扫描 (phased, m=1): 多久奖励一次 ==")
print("  E      产出")
for e in [1,5,10,25,50,100,200,400]:
    r=sim(mode='phased',E=e); out['E=%d'%e]={'产出':r['产出']}
    print("  %-6d %.1f"%(e,r['产出']))
print("\n== v2-E 否定强度 loss_c 扫描 (phased, m=1) ==")
print("  loss_c 产出    士气")
for lc in [0.0,0.02,0.06,0.12,0.25,0.5]:
    r=sim(mode='phased',loss_c=lc); out['loss_c=%.2f'%lc]={'产出':r['产出'],'士气':r['士气']}
    print("  %-7.2f %-7.1f %.3f"%(lc,r['产出'],r['士气']))
print("\n== v2-F 世界漂移 drift 扫描: 奖励在什么世界里最有用 ==")
print("  drift   critique  reward   phased")
for d in [0.0,0.002,0.006,0.012,0.03]:
    row=[sim(mode=x,drift=d)['产出'] for x in ['critique','reward','phased']]
    out['drift=%.3f'%d]={'critique':row[0],'reward':row[1],'phased':row[2]}
    print("  %-7.3f %-9.1f %-8.1f %.1f"%(d,row[0],row[1],row[2]))
json.dump(out, open('result245b.json','w'), ensure_ascii=False, indent=1)

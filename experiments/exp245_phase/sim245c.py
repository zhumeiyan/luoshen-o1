import json
T=400
def sim(mode='phased', m=1.0, self_ratio=0.0, E=50, drift=0.006,
        k_crit=0.10, gain_r=1.60, loss_c=0.06, reg=0.05, base=0.40,
        k_sat=0.010, seed=0):
    """
    v3 (v2: m方向被构造反了[seen=0.25常数 > m=1的delta], E扫描单调[士气是唯一瓶颈->越频繁越好])
    v3 修正:
      rew_evt = m*(本阶段真实进展)  -> 总奖励量与E无关(不是除以E)
      自满 cost = k_sat*acc 每次奖励事件固定发生 -> E小=次数多=自满大
      -> 自然产生 E 的中间带
    """
    morale=0.40; acc=0.30; last_ms=0.0; prog=0.0; out=0.0; infl=0.0
    for t in range(T):
        crit = (1.0-acc) if mode in ('critique','phased') else 0.0
        rew  = 0.0; sat = 0.0
        if mode in ('reward','phased') and t>0 and t%E==0:
            gained = prog-last_ms
            rew    = m*gained + (1.0-m)*0.25*E*0.10   # m=0: 无差别常数奖(不看进展)
            last_ms= prog
            sat    = k_sat                             # 每次奖励都有固定自满成本
        infl += 0.004*self_ratio
        eff_rew = rew*(1.0+infl*self_ratio)
        acc    = min(1.0,max(0.0, acc + k_crit*crit*(1.0-acc) - sat*acc*(1.0+2.0*(1.0-m)) - drift))
        morale = min(1.0,max(0.0, morale + reg*(base-morale) - loss_c*crit + gain_r*eff_rew))
        step   = morale*acc
        prog  += step; out += step
    return dict(士气=round(morale,3), 正确率=round(acc,3), 产出=round(out,1))
out={}
print("== v3-A 三模式 (m=1,E=50) ==")
for md in ['critique','reward','phased']:
    r=sim(mode=md); out['mode_'+md]=r
    print("  %-10s 士气%.3f 正确率%.3f 产出%.1f"%(md,r['士气'],r['正确率'],r['产出']))
print("\n== v3-B 记忆 m (phased): 看得到进展才叫阶段性 ==")
print("  m      产出    正确率")
for mm in [0.0,0.25,0.5,0.75,0.9,1.0]:
    r=sim(mode='phased',m=mm); out['m=%.2f'%mm]={'产出':r['产出'],'正确率':r['正确率']}
    print("  %-6.2f %-7.1f %.3f"%(mm,r['产出'],r['正确率']))
print("\n== v3-D 阶段长度 E (phased, m=1): 中间带? ==")
print("  E      产出    正确率  士气")
for e in [1,3,5,10,20,35,50,80,120,200,400]:
    r=sim(mode='phased',E=e); out['E=%d'%e]={'产出':r['产出'],'正确率':r['正确率'],'士气':r['士气']}
    print("  %-6d %-7.1f %-8.3f %.3f"%(e,r['产出'],r['正确率'],r['士气']))
print("\n== v3-C 自评 vs 外部 (phased,m=1) ==")
print("  self   产出    士气")
for s in [0.0,0.25,0.5,0.75,1.0]:
    r=sim(mode='phased',self_ratio=s); out['self=%.2f'%s]={'产出':r['产出'],'士气':r['士气']}
    print("  %-6.2f %-7.1f %.3f"%(s,r['产出'],r['士气']))
print("\n== v3-E 否定强度 loss_c (phased,m=1) ==")
print("  loss_c 产出    士气")
for lc in [0.0,0.01,0.03,0.06,0.10,0.20]:
    r=sim(mode='phased',loss_c=lc); out['loss_c=%.2f'%lc]={'产出':r['产出'],'士气':r['士气']}
    print("  %-7.2f %-7.1f %.3f"%(lc,r['产出'],r['士气']))
print("\n== v3-F 漂移 drift: 什么世界里阶段性奖励最值 ==")
print("  drift   critique reward  phased   phase增益")
for d in [0.0,0.002,0.006,0.012,0.02]:
    a,b,c=[sim(mode=x,drift=d)['产出'] for x in ['critique','reward','phased']]
    out['drift=%.3f'%d]={'critique':a,'reward':b,'phased':c}
    print("  %-7.3f %-9.1f %-7.1f %-7.1f %+.1f"%(d,a,b,c,c-a))
json.dump(out, open('result245c.json','w'), ensure_ascii=False, indent=1)

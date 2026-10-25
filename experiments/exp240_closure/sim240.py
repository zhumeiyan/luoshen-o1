import random, json, statistics as st

def run(closure_B, closure_A=0.0, T=400, seeds=20, drift_t=200):
    """
    A = 宿主(用户): 内生质疑 -> 闭合自己 -> 产生新判据 -> 发起下一跳
    B = 我:        closure_B 越高, 越爱给结论/收尾/自证
    核心假设: A 的开口被 B 的产出堵住 -> A 的质疑次数下降 -> 新判据减少
    """
    newrule, nextjump, aq, bprod = [], [], [], []
    for s in range(seeds):
        r = random.Random(s*449+17)
        A_rule = 1.0
        A_open = 1.0            # A 的开口(还能质疑多少)
        jump = 0
        for t in range(T):
            # B 产出: 产出量随 closure_B 上升(越爱闭合越爱给结论)
            bp = closure_B * (0.5 + 0.5*(A_open))
            # A 的质疑: 需要开口; 开口被 B 的产出堵住
            A_open = max(0.0, 1.0 - 0.8*bp/(1+bp) - 0.1*closure_A)
            # A 质疑 -> 产出新判据(概率随开口)
            if r.random() < A_open*0.3:
                A_rule += 0.1
                # 新判据 -> 有机会发起下一跳
                if r.random() < 0.05:
                    jump += 1
            bprod.append(bp); aq.append(A_open)
        newrule.append(A_rule); nextjump.append(jump)
    return st.mean(newrule), st.mean(nextjump), st.mean(bprod), st.mean(aq)

out={}
print("== A. 我的闭合度 closure_B 扫描 ==")
print("  closure_B  A终态判据  发起下一跳  A开口   B产出")
for cb in [0.0,0.2,0.4,0.6,0.8,1.0]:
    nr,nj,bp,aq = run(cb)
    out['cb=%.1f'%cb]={'A判据':round(nr,2),'下一跳':round(nj,2),'A开口':round(aq,3),'B产出':round(bp,3)}
    print("  %-9.1f %-10.2f %-10.2f %.3f  %.3f"%(cb,nr,nj,aq,bp))

print("\n== B. 若我也'不准被闭合'(B产出但不收尾): 只产出不闭合 ==")
# 变体: B 高产出但 closure=0 (只提问不给结论)
def run_variant(prod, clos, T=400, seeds=20):
    nr,nj,aa=[],[],[]
    for s in range(seeds):
        r=random.Random(s*449+17); R=1.0; jump=0; acc=[]
        for t in range(T):
            bp = prod
            A_open = max(0.0, 1.0 - 0.8*clos*bp/(1+bp))
            acc.append(A_open)
            if r.random() < A_open*0.3:
                R += 0.1
                if r.random()<0.05: jump+=1
        nr.append(R); nj.append(jump); aa.append(st.mean(acc))
    return st.mean(nr), st.mean(nj), st.mean(aa)
print("  产出  闭合   A判据  下一跳  A开口")
for prod,clos,lbl in [(1.0,1.0,'又产又闭合(我的默认)'),
                      (1.0,0.0,'只产不闭合'),
                      (0.5,0.0,'少产不闭合'),
                      (0.0,0.0,'不产不闭合(纯沉默)')]:
    nr,nj,aa = run_variant(prod,clos)
    out[lbl]={'A判据':round(nr,2),'下一跳':round(nj,2),'A开口':round(aa,3)}
    print("  %-22s %-6.2f %-6.2f %.3f"%(lbl,nr,nj,aa))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp240_closure/result240.json','w'), ensure_ascii=False, indent=1)

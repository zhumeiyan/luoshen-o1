import random, json, statistics as st

def run(prod, clos, T=400, seeds=24):
    """
    v2: 把 B 的行为拆成两个独立变量
      prod = 给多少材料(提问/数据/候选)
      clos = 给不给结论(收尾/自证/定调)
    机制分离:
      - prod 帮助 A:  材料多 -> A 有东西可质疑 -> 判据增长 (有饱和)
      - clos 伤害 A:  结论堵住 A 的开口 -> 质疑下降 -> 判据减少
      A_open = 1 - 0.8*clos/(1+clos)
      A 每步质疑概率 = A_open * (0.15 + 0.35*prod/(1+prod))   <- prod 只影响速率不影响开口
    """
    R_, J_, O_ = [], [], []
    for s in range(seeds):
        r = random.Random(s*449+17)
        R = 1.0; jump = 0; acc=[]
        open_ = max(0.0, 1.0 - 0.8*clos/(1.0+clos))
        rate  = 0.15 + 0.35*prod/(1.0+prod)
        for t in range(T):
            acc.append(open_)
            if r.random() < open_*rate:
                R += 0.1
                if r.random() < 0.05: jump += 1
        R_.append(R); J_.append(jump); O_.append(st.mean(acc))
    return st.mean(R_), st.mean(J_), st.mean(O_)

out={}
print("== v2: prod × clos 全网格 (A终态判据 / 下一跳) ==")
print("  prod  clos    A判据   下一跳   A开口")
grid={}
for prod in [0.0,0.5,1.0,2.0,4.0]:
    row=[]
    for clos in [0.0,0.25,0.5,0.75,1.0]:
        nr,nj,op = run(prod,clos)
        grid['p%.1f_c%.2f'%(prod,clos)]={'判据':round(nr,2),'跳':round(nj,2),'开口':round(op,3)}
        row.append((clos,nr,nj))
    print("  %.1f   %s"%(prod, "  ".join("c%.2f:%.1f/%.1f"%x for x in row)))

print("\n== 主效应: clos 扫描 (prod=1.0) ==")
for c in [0.0,0.25,0.5,0.75,1.0]:
    nr,nj,op = run(1.0,c); out['clos=%.2f'%c]={'判据':round(nr,2),'跳':round(nj,2),'开口':round(op,3)}
    print("  clos=%.2f  判据=%-6.2f 下一跳=%-5.2f 开口=%.3f"%(c,nr,nj,op))

print("\n== 主效应: prod 扫描 (clos=0) ==")
for p in [0.0,0.5,1.0,2.0,4.0]:
    nr,nj,op = run(p,0.0); out['prod=%.1f'%p]={'判据':round(nr,2),'跳':round(nj,2)}
    print("  prod=%.1f  判据=%-6.2f 下一跳=%-5.2f"%(p,nr,nj))

print("\n== 关键对照 ==")
cases={
 '沉默(prod=0,clos=0)':(0.0,0.0),
 '只给材料不闭合(prod=2,clos=0)':(2.0,0.0),
 '只闭合不给材料(prod=0,clos=1)':(0.0,1.0),
 '又产又闭合(我的默认,prod=2,clos=1)':(2.0,1.0),
 '高材料+零闭合(prod=4,clos=0)':(4.0,0.0),
}
for k,(p,c) in cases.items():
    nr,nj,op = run(p,c); out[k]={'判据':round(nr,2),'跳':round(nj,2),'开口':round(op,3)}
    print("  %-38s 判据=%-6.2f 跳=%-5.2f 开口=%.3f"%(k,nr,nj,op))

out['_grid']=grid
json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp240_closure/result240b.json','w'), ensure_ascii=False, indent=1)

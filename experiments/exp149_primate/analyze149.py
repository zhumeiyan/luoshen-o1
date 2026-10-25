import json, math, random
from collections import Counter
raw=json.load(open('raw149.json'))
def boot(v, n=2000, seed=7):
    r=random.Random(seed); m=len(v)
    if m==0: return (0,0,0)
    s=sorted(sum(r.choice(v) for _ in range(m))/m for _ in range(n))
    return (sum(v)/m, s[int(0.025*n)], s[int(0.975*n)])

print('=== 体检：g_self 是否双向跨越 0.5 ===')
for mode in ['base','tell','randomB']:
    A=raw[mode]['A']; B=raw[mode]['B']
    lo=sum(1 for g in B['g'] if g>0.5)/len(B['g'])
    print(' %-8s B: g>0.5 占比 %.3f  range %.3f~%.3f'%(mode,lo,min(B['g']),max(B['g'])))
    # 对齐度：A 的 delta_t 是否含 B 的 act[t]
    hit=sum(1 for d,b in zip(A['delta'],B['act']) if d[b]>0)
    print('          对齐度 A.delta_t 含 B.act[t]: %d/%d = %.3f'%(hit,len(A['delta']),hit/len(A['delta'])))

print()
print('=== S1 镜像自我：self/other 归因（三臂，同一批真实数据）===')
res={}
for mode in ['base','tell','randomB']:
    A=raw[mode]['A']; B=raw[mode]['B']
    arms={'full':[], 'discard':[], 'swapped':[]}
    rnd=random.Random(11)
    for t,(d,a) in enumerate(zip(A['delta'],A['act'])):
        ch=[s for s in range(8) if d[s]>0]
        if not ch: continue
        for s in ch:
            truth = 1 if a==s else 0
            arms['full'].append(1 if truth==1 else 0)                     # 私有记录正确
            arms['discard'].append(1 if (rnd.choice(ch)==s)==truth else 0) # 随机猜
            arms['swapped'].append(1 if (B['act'][t]==s)==truth else 0)    # 用对方的记录(错配)
    res[mode]={k:boot(v) for k,v in arms.items()}
    for k in ['full','discard','swapped']:
        m,lo,hi=res[mode][k]
        print(' %-8s %-8s acc=%.4f  CI[%.4f,%.4f]  n=%d'%(mode,k,m,lo,hi,len(arms[k])))

print()
print('=== S2 心智理论：从世界痕迹推断对方内部状态 ===')
def read_mind(mode):
    A=raw[mode]['A']; B=raw[mode]['B']
    ok=[]; ok_tell=[]
    for t in range(len(A['act'])):
        d=A['delta'][t]; a=A['act'][t]
        w=B['world'][t-1] if t>0 else [0]*8     # 决策时的世界
        hi=max(range(8), key=lambda i:w[i])
        # A 从 delta 里剥掉自己的贡献 -> 剩下的就是对方留下的痕迹
        other=[s for s in range(8) if d[s]>0 and s!=a]
        if not other: continue
        # 对方是否"抢最高槽"？抢 = 竞争态(g<0.5)；避开 = 探索态(g>0.5)
        inferred_competitive = (hi in other)
        truth_competitive = B['g'][t] <= 0.5
        ok.append(1 if inferred_competitive==truth_competitive else 0)
        if A['peer_g'][t] is not None:
            ok_tell.append(1 if (A['peer_g'][t]<=0.5)==truth_competitive else 0)
    return boot(ok), boot(ok_tell), len(ok)
for mode in ['base','tell','randomB']:
    b,bt,n=read_mind(mode)
    line=' %-8s 行为推断 acc=%.4f CI[%.4f,%.4f] n=%d'%(mode,b[0],b[1],b[2],n)
    if bt[1]!=0 or bt[0]!=0: line+='   | 直接广播 acc=%.4f CI[%.4f,%.4f] n>=0'%(bt[0],bt[1],bt[2])
    print(line)

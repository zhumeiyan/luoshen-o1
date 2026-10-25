import json, random
raw=json.load(open('raw149.json'))
def boot(v,n=2000,seed=7):
    r=random.Random(seed); m=len(v)
    if m==0: return (0,0,0)
    s=sorted(sum(r.choice(v) for _ in range(m))/m for _ in range(n))
    return (sum(v)/m, s[int(0.025*n)], s[int(0.975*n)])

print('=== S1 镜像自我：归因准确率（修：预测 vs 真值，不是正例比例）===')
for mode in ['base','tell','randomB']:
    A=raw[mode]['A']; B=raw[mode]['B']
    arms={k:[] for k in ['full','discard','swapped','shifted']}
    rnd=random.Random(11)
    for t,(d,a) in enumerate(zip(A['delta'],A['act'])):
        ch=[s for s in range(8) if d[s]>0]
        if not ch: continue
        for s in ch:
            truth = 1 if a==s else 0
            preds={'full': 1 if a==s else 0,
                   'discard': 1 if rnd.choice(ch)==s else 0,
                   'swapped': 1 if B['act'][t]==s else 0,
                   'shifted': 1 if (A['act'][t-1] if t>0 else -1)==s else 0}
            for k in arms: arms[k].append(1 if preds[k]==truth else 0)
    print(' mode=%-8s n=%d'%(mode,len(arms['full'])))
    for k in ['full','discard','swapped','shifted']:
        m,lo,hi=boot(arms[k])
        flag=''
        if k=='full': flag='  (trivial查表: 自己的动作在世界里100%%可见)'
        print('   %-8s acc=%.4f CI[%.4f,%.4f]%s'%(k,m,lo,hi,flag))

print()
print('=== S2 读心（修：只在能唯一确定对方痕迹时判断；对照=常数基线）===')
for mode in ['base','tell','randomB']:
    A=raw[mode]['A']; B=raw[mode]['B']
    ok=[]; ok_tell=[]; truths=[]
    for t in range(len(A['act'])):
        d=A['delta'][t]; a=A['act'][t]
        w=B['world'][t-1] if t>0 else [0]*8
        hi=max(range(8), key=lambda i:w[i])
        other=[s for s in range(8) if d[s]>0 and s!=a]
        if len(other)!=1: continue          # 只在痕迹唯一时判断
        inf_comp = (other[0]==hi)
        truth = B['g'][t] <= 0.5
        truths.append(1 if truth else 0)
        ok.append(1 if inf_comp==truth else 0)
        if A['peer_g'][t] is not None:
            ok_tell.append(1 if (A['peer_g'][t]<=0.5)==truth else 0)
    p=sum(truths)/len(truths); const=max(p,1-p)   # 常数基线
    b=boot(ok); bt=boot(ok_tell)
    print(' mode=%-8s n=%d  常数基线=%.4f'%(mode,len(ok),const))
    print('   行为推断 acc=%.4f CI[%.4f,%.4f]   vs 常数基线 %+.4f'%(b[0],b[1],b[2],b[0]-const))
    print('   直接广播 acc=%.4f CI[%.4f,%.4f]  n=%d'%(bt[0],bt[1],bt[2],len(ok_tell)))

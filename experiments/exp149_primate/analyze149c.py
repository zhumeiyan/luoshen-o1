import json, math, random
from collections import Counter
raw=json.load(open('raw149.json'))
def boot(v,n=2000,seed=7):
    r=random.Random(seed); m=len(v)
    if m==0: return (0,0,0)
    s=sorted(sum(r.choice(v) for _ in range(m))/m for _ in range(n))
    return (sum(v)/m, s[int(0.025*n)], s[int(0.975*n)])

print('=== 核验：tell 模式下"行为推断"与"直接广播"是否真等价 ===')
A=raw['tell']['A']; B=raw['tell']['B']
inf=[]; tel=[]
for t in range(len(A['act'])):
    d=A['delta'][t]; a=A['act'][t]
    w=B['world'][t-1] if t>0 else [0]*8
    hi=max(range(8), key=lambda i:w[i])
    other=[s for s in range(8) if d[s]>0 and s!=a]
    if len(other)!=1: continue
    if A['peer_g'][t] is None: continue
    inf.append(1 if (other[0]==hi)==(B['g'][t]<=0.5) else 0)
    tel.append(1 if (A['peer_g'][t]<=0.5)==(B['g'][t]<=0.5) else 0)
same=sum(1 for x,y in zip(inf,tel) if x==y)/len(inf)
print(' 两者逐位一致率=%.4f  n=%d  (若=1.0 则两臂等价,判据无区分度)'%(same,len(inf)))
print(' 广播值滞后一拍导致的不一致应>0；一致率越接近1越可疑')

print()
print('=== S3 传递熵：方向性与 shuffle 对照 ===')
def H(xs):
    c=Counter(xs); n=len(xs)
    return -sum((v/n)*math.log2(v/n) for v in c.values() if v)
def te(src,dst):
    # TE(src->dst) = H(dst_{t+1}|dst_t) - H(dst_{t+1}|dst_t,src_t)
    n=min(len(src),len(dst))-1
    a=[(dst[t],dst[t+1]) for t in range(n)]
    b=[(dst[t],src[t],dst[t+1]) for t in range(n)]
    return H(b)-H(a)*0 - H(a) + H([x[0:2] for x in b]) - 0  # placeholder
def te_ok(src,dst):
    n=min(len(src),len(dst))-1
    joint2=Counter((dst[t],dst[t+1]) for t in range(n))
    joint3=Counter((dst[t],src[t],dst[t+1]) for t in range(n))
    j2=Counter((dst[t],) for t in range(n))
    j2s=Counter((dst[t],src[t]) for t in range(n))
    N=n
    def ent(c): 
        return -sum((v/N)*math.log2(v/N) for v in c.values())
    # H(d'|d) = H(d,d') - H(d)
    h1=ent(joint2)-ent(j2)
    h2=ent(joint3)-ent(j2s)
    return h1-h2
for mode in ['base','tell','randomB']:
    A=raw[mode]['A']; B=raw[mode]['B']
    # binary 序列: 该 tick 是否动了"当时最高槽"(竞争性动作)
    seqA=[]; seqB=[]
    for t in range(len(A['act'])):
        w=A['world'][t-1] if t>0 else [0]*8
        hi=max(range(8),key=lambda i:w[i])
        seqA.append(1 if A['act'][t]==hi else 0)
        seqB.append(1 if B['act'][t]==hi else 0)
    f=te_ok(seqB,seqA); r=te_ok(seqA,seqB)
    rnd=random.Random(3); sh=seqB[:]; rnd.shuffle(sh)
    fsh=te_ok(sh,seqA)
    print(' %-8s TE(B->A)=%+.4f  TE(A->B)=%+.4f  方向差=%+.4f | shuffle对照 TE=%+.4f'%(mode,f,r,f-r,fsh))

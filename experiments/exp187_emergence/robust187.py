# -*- coding: utf-8 -*-
"""稳健性：涌现点 L1->L2 是否依赖 kmax / 种子"""
import json, random, math, hashlib, sys
sys.path.insert(0, '.')
ROOT="/data/workspace/luoshen-o1"
def rd(p):
    try: return open(p,encoding='utf-8',errors='ignore').read()
    except: return ""
core=rd(f"{ROOT}/压缩包/活着的压缩包.md")
judge=rd(f"{ROOT}/evidence/失败模式库/判据核.md")
u=[l.strip() for l in rd(f"{ROOT}/experiments/exp180_record/u_side_full.txt").split("\n") if l.strip()]
nt=max(4,int(len(u)*0.2)); utr=u[:len(u)-nt]; TEST="".join(u[len(u)-nt:])
NEG="\n每拍必否定：总结=死6.62%，否定=挑出总结解释不了的那几处加回来。\n"
L0=core; L1=core+NEG; L2=L1+"".join(utr)
def sk(t,n):
    if len(t)<=n: return t
    st=len(t)/n; return "".join(t[int(i*st)] for i in range(n))
L3=L2+sk(judge,20000)
from collections import Counter
def top(t,n=300): return set(c for c,_ in Counter(t).most_common(n))
class NG:
    def __init__(s,text,kmax):
        s.kmax=kmax; s.text=text
        s.c=[dict() for _ in range(kmax+1)]; s.t=[dict() for _ in range(kmax+1)]
        for i in range(len(text)-1):
            for k in range(1,kmax+1):
                if i-k+1<0: continue
                cx=text[i-k+1:i+1]; nx=text[i+1]
                s.c[k][(cx,nx)]=s.c[k].get((cx,nx),0)+1
                s.t[k][cx]=s.t[k].get(cx,0)+1
        s.uni=Counter(text); s.N=len(text)
    def p(s,ctx,ch):
        lam=0.6; p=s.uni.get(ch,0)/max(1,s.N)
        for k in range(1,s.kmax+1):
            if len(ctx)<k: break
            c=ctx[-k:]; tt=s.t[k].get(c,0)
            if tt>0:
                p=lam*(s.c[k].get((c,ch),0)/tt)+(1-lam)*p; lam*=0.6
        return max(p,1e-12)
    def acc(s,text,cands):
        h=t=0
        for i in range(len(text)-1):
            cx=text[max(0,i-s.kmax+1):i+1]
            b,bp=None,-1
            for ch in cands:
                v=s.p(cx,ch)
                if v>bp: bp,b=v,ch
            t+=1
            if b==text[i+1]: h+=1
        return h/max(1,t)
    def auc(s,text,n,rs):
        w=0; L=40; cnt=0
        for _ in range(n):
            if len(text)<L+1: break
            i=rs.randrange(0,len(text)-L); sg=text[i:i+L]
            j=rs.randrange(0,L); ch=rs.choice(list(set(text)))
            while ch==sg[j]: ch=rs.choice(list(set(text)))
            def lp(x):
                return sum(math.log(s.p(x[max(0,q-s.kmax+1):q+1],x[q+1])) for q in range(len(x)-1))
            if lp(sg)>lp(sg[:j]+ch+sg[j+1:]): w+=1
            cnt+=1
        return w/max(1,cnt)
res=[]
for seed in [1,7,42]:
    for km in [2,3,4]:
        rs=random.Random(seed)
        row={"seed":seed,"kmax":km}
        for nm,tx in [("L0",L0),("L1",L1),("L2",L2),("L3",L3)]:
            m=NG(tx,km); cd=top(tx,300)|set(TEST)
            row[nm]={"acc":round(m.acc(TEST,cd),4),"auc":round(m.auc(TEST,120,rs),4)}
        res.append(row); print(row)
json.dump(res,open("robust187.json","w",encoding='utf-8'),ensure_ascii=False,indent=2)

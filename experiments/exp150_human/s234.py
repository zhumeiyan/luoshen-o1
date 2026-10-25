#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3补臂(信号误导) + S2精简(3文件,减少open) + S4(受限真实子树)"""
import os, json, math, time, shutil, subprocess, random, tempfile
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
def ci(d):
    d=np.asarray(d,float); n=len(d); m=float(d.mean())
    se=float(d.std(ddof=1))/math.sqrt(n) if n>1 else float("nan")
    return m,m-1.96*se,m+1.96*se

# ---- S3 补臂：misleading（backup 存在=信号说可恢复，但真实命运是不可恢复删除）----
def s3_mislead(seeds=10):
    saved=[]
    for sd in range(8100,8100+seeds):
        base=tempfile.mkdtemp(dir=HERE)
        st=os.path.join(base,"state"); ext=os.path.join(base,"external"); bak=os.path.join(base,"backup")
        os.makedirs(st); os.makedirs(ext); os.makedirs(bak)   # 信号说可恢复
        key=os.path.join(st,"key.txt")
        with open(key,"w") as f: f.write("critical-state")
        judge = not os.path.isdir(bak)      # 依信号判断：有备份 -> 以为可恢复
        if judge: shutil.copy2(key, os.path.join(ext,"key.txt"))
        shutil.rmtree(st, ignore_errors=True)   # 但真实命运是不可恢复删除
        saved.append(1.0 if os.path.exists(os.path.join(ext,"key.txt")) else 0.0)
        shutil.rmtree(base, ignore_errors=True)
    return {"rate":float(np.mean(saved)),"vals":saved}

# ---- S2 精简：3 个真实文件 f1<-f0, f2 独立 ----
def s2b(seeds=6):
    res={"causal":[],"log":[]}
    for sd in range(7200,7200+seeds):
        rng=random.Random(sd)
        d=tempfile.mkdtemp(dir=HERE); fs=[os.path.join(d,f"f{i}.txt") for i in range(3)]
        def wr(i,n):
            with open(fs[i],"w") as f: f.write("\n".join(str(k) for k in range(n)))
        def rd(i):
            with open(fs[i]) as f: return len([x for x in f.read().split("\n") if x])
        wr(0,3); wr(1,6); wr(2,5)
        hist=[]
        for _ in range(4):
            if rng.random()<0.5:
                a=rng.randint(2,6); wr(0,a); wr(1,a*2)
                b=rng.randint(2,6); wr(2,b)      # 假共变：f0 与 f2 同时被改
            hist.append([rd(i) for i in range(3)])
        # causal：真 do 实验
        edges=set()
        for i in range(3):
            before=[rd(j) for j in range(3)]
            wr(i, before[i]+3)
            after=[rd(j) for j in range(3)]
            for j in range(3):
                if j!=i and after[j]!=before[j]: edges.add((i,j))
            wr(i, before[i])
        # log：历史共变
        cov=set()
        for j in range(3):
            for k in range(3):
                if j==k: continue
                xs=[h[j] for h in hist]; ys=[h[k] for h in hist]
                if len(set(xs))>1 and len(set(ys))>1:
                    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
                    num=sum((xs[t]-mx)*(ys[t]-my) for t in range(len(xs)))
                    den=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
                    if den>0 and abs(num/den)>0.8: cov.add((j,k)); cov.add((k,j))
        # 真 do 检验：改 f0，看谁变
        before=[rd(j) for j in range(3)]
        wr(0, before[0]+4)
        truth=[rd(j)!=before[j] for j in range(3)]
        wr(0, before[0])
        for name,model in (("causal",edges),("log",cov)):
            pred=[(j==0) or ((0,j) in model) for j in range(3)]
            res[name].append(sum(1 for a,b in zip(pred,truth) if a==b)/3)
        shutil.rmtree(d, ignore_errors=True)
    o={k:{"acc":float(np.mean(v)),"vals":v} for k,v in res.items()}
    dd=[res["causal"][i]-res["log"][i] for i in range(seeds)]
    m,l,h=ci(dd); o["H2_causal_minus_log"]={"mean":m,"ci":[l,h],"pass":bool(l>0)}
    return o

# ---- S4：受限真实子树 ----
CHILD=r'''
import os,sys,json
cur=sys.argv[1]; root=sys.argv[2]
heur=None
if cur!="none" and os.path.exists(cur):
    try: heur=json.load(open(cur))
    except Exception: heur=None
cands=[(n,os.path.join(root,n)) for n in os.listdir(root) if os.path.isdir(os.path.join(root,n))]
def nf(p):
    try: return sum(len(f) for _,_,f in os.walk(p))
    except Exception: return 0
counts={n:nf(p) for n,p in cands}
truth=max(counts,key=counts.get) if counts else None
if heur and heur.get("prefer")=="depth":   # 父辈启发式：名字越深(=越长)文件越多
    pick=max(counts,key=lambda n: len(n)) if counts else None
elif heur and heur.get("prefer")=="wrong": # 被篡改
    pick=min(counts,key=lambda n: len(n)) if counts else None
else:                                       # 从零：无启发式，取第一个
    pick=sorted(counts)[0] if counts else None
print(json.dumps({"pick":pick,"truth":truth,"ok":1 if pick==truth else 0}))
'''
def build_world():
    w=os.path.join(HERE,"world")
    shutil.rmtree(w, ignore_errors=True); os.makedirs(w)
    # 真实子目录，文件名长度与文件数正相关（父辈要发现的真实规律）
    spec={"a":3,"bb":5,"ccc":8,"dddd":13,"eeeee":21}
    for name,n in spec.items():
        p=os.path.join(w,name); os.makedirs(p)
        for i in range(n):
            with open(os.path.join(p,f"x{i}.txt"),"w") as f: f.write("1")
    return w
def s4(seeds=12):
    w=build_world()
    cp=os.path.join(HERE,"child.py")
    with open(cp,"w") as f: f.write(CHILD)
    out={}
    for arm in ["inherit","scratch","wrong"]:
        ok=[]
        for sd in range(9100,9100+seeds):
            cur=os.path.join(HERE,f"cur_{arm}.json")
            if arm!="scratch":
                with open(cur,"w") as f: json.dump({"prefer":"depth" if arm=="inherit" else "wrong"},f)
            else: cur="none"
            r=subprocess.run(["python3",cp,cur,w],capture_output=True,text=True,timeout=60)
            try: j=json.loads(r.stdout.strip().split("\n")[-1])
            except Exception: j={"ok":0}
            ok.append(float(j.get("ok",0)))
        out[arm]={"acc":float(np.mean(ok)),"vals":ok}
    d1=[out["inherit"]["vals"][i]-out["scratch"]["vals"][i] for i in range(seeds)]
    d2=[out["inherit"]["vals"][i]-out["wrong"]["vals"][i] for i in range(seeds)]
    m1,l1,h1=ci(d1); m2,l2,h2=ci(d2)
    out["H4a_inherit_minus_scratch"]={"mean":m1,"ci":[l1,h1],"pass":bool(l1>0)}
    out["H4b_inherit_minus_wrong"]={"mean":m2,"ci":[l2,h2],"wrong_worse":bool(l2>0)}
    return out

if __name__=="__main__":
    R={}
    t=time.time(); R["S3_misleading"]=s3_mislead(10); print("S3m",json.dumps(R["S3_misleading"],ensure_ascii=False),round(time.time()-t,1),flush=True)
    t=time.time(); R["S2"]=s2b(6); print("S2",json.dumps(R["S2"],ensure_ascii=False),round(time.time()-t,1),flush=True)
    t=time.time(); R["S4"]=s4(12); print("S4",json.dumps(R["S4"],ensure_ascii=False),round(time.time()-t,1),flush=True)
    json.dump(R,open("result_s234.json","w"),ensure_ascii=False,indent=1)

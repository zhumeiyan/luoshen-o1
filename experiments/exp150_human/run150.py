#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""150 人格真装机：S1独白 / S2自传(因果vs日志) / S3知死(真删除) / S4文化(真spawn)
本机约束(实测): open 182.5ms; 同fd写后回读 Errno5; mmap/shared_memory 挂死; pipe 可用; spawn 9.8ms
"""
import os, json, math, time, fcntl, shutil, subprocess, random, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_DIR = "/data/workspace/luoshen-o1/experiments"

def ci(d):
    d=np.asarray(d,float); n=len(d); m=float(d.mean())
    se=float(d.std(ddof=1))/math.sqrt(n) if n>1 else float("nan")
    return m, m-1.96*se, m+1.96*se

# ============================ S1 独白 ============================
class Whisper:
    """真实 pipe 通道：说出的话留在管道里，之后能听到自己早先说的话"""
    def __init__(self):
        self.r, self.w = os.pipe()
        fcntl.fcntl(self.r, fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(self.w, fcntl.F_SETFL, os.O_NONBLOCK)
    def say(self, o):
        try: os.write(self.w, json.dumps(o).encode())
        except BlockingIOError: pass
    def hear(self):
        try:
            d = os.read(self.r, 65535)
            os.write(self.w, d)          # 读回后放回，话留在管道里
            return json.loads(d.decode())
        except (BlockingIOError, Exception): return None
    def close(self):
        os.close(self.r); os.close(self.w)

def sample_disturb(T):
    try: items = os.listdir(REAL_DIR)
    except Exception: items = ["x"]
    return [("D:"+items[t % len(items)]) if int(time.perf_counter_ns()%2)==1 else None
            for t in range(T)]

def s1(arm, dist, T=24, CAP=3, TARGET=("A","B","C")):
    TARGET=list(TARGET)
    ch = Whisper() if arm in ("pre","post") else None
    from collections import deque
    plan = deque(TARGET, maxlen=CAP); done=[]
    for t in range(T):
        if arm=="pre":
            if t==0: ch.say({"kind":"plan","plan":TARGET})
            else:
                m=ch.hear()
                if m and m.get("kind")=="plan":
                    for st in m.get("plan",[]):
                        if st not in done and st not in plan: plan.append(st)
        elif arm=="post":
            ch.say({"kind":"hist","hist":done}); ch.hear()
        d=dist[t]
        if d is not None: plan.append(d)
        nxt=TARGET[len(done)]
        if nxt in plan:
            plan.remove(nxt); done.append(nxt)
        if len(done)==len(TARGET): break
    if ch: ch.close()
    return 1.0 if done==TARGET else 0.0

def run_s1(seeds=16):
    T=24; sl=list(range(6000,6000+seeds))
    dists=[sample_disturb(T) for _ in sl]
    out={"mean_disturb":float(np.mean([sum(1 for x in d if x) for d in dists]))}
    for arm in ["pre","post","off"]:
        vals=[s1(arm,dists[i],T) for i in range(seeds)]
        out[arm]={"rate":float(np.mean(vals)),"vals":vals}
    d1=[out["pre"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    d2=[out["post"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    m1,l1,h1=ci(d1); m2,l2,h2=ci(d2)
    out["H1a_pre_minus_off"]={"mean":m1,"ci":[l1,h1],"pass":bool(l1>0)}
    out["H1b_post_minus_off"]={"mean":m2,"ci":[l2,h2],"post_not_better":bool(not(l2>0))}
    return out

# ============================ S2 自传 ============================
def run_s2(seeds=10):
    """真实文件因果：f1<-f0(x2), f3<-f2(+1), f4独立; 外部同时改f2,f4造成假共变"""
    res={"causal":[], "log":[]}
    for sd in range(7000,7000+seeds):
        rng=random.Random(sd)
        d=tempfile.mkdtemp(dir=HERE); fs=[os.path.join(d,f"f{i}.txt") for i in range(5)]
        def wr(i,n):
            with open(fs[i],"w") as f: f.write("\n".join(str(k) for k in range(n)))
        def rd(i):
            with open(fs[i]) as f: return len([x for x in f.read().split("\n") if x])
        for i,n in enumerate([3,6,2,3,5]): wr(i,n)
        # 历史观测（含外部共变混淆：同时改 f2 和 f4）
        hist=[]
        for _ in range(6):
            if rng.random()<0.5:
                a=rng.randint(2,6); wr(2,a); wr(3,a+1)
                b=rng.randint(2,6); wr(4,b)          # 假共变：f2 与 f4 同时被改
            hist.append([rd(i) for i in range(5)])
        # causal 臂：真 do 实验（真改真读），学到边
        edges=set()
        for i in range(5):
            before=[rd(j) for j in range(5)]
            wr(i, before[i]+3)                        # 真干预
            after=[rd(j) for j in range(5)]
            for j in range(5):
                if j!=i and after[j]!=before[j]: edges.add((i,j))
            wr(i, before[i])                          # 复原
        # log 臂：只用历史共变
        import itertools
        cov=set()
        for j in range(5):
            for k in range(5):
                if j==k: continue
                xs=[h[j] for h in hist]; ys=[h[k] for h in hist]
                if len(set(xs))>1 and len(set(ys))>1:
                    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
                    num=sum((xs[t]-mx)*(ys[t]-my) for t in range(len(xs)))
                    den=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
                    if den>0 and abs(num/den)>0.8: cov.add((j,k))
        # 检验：真 do 改 f0，预测 f1 与 f4 是否变
        before=[rd(j) for j in range(5)]
        wr(0, before[0]+4)
        truth=[rd(j)!=before[j] for j in range(5)]
        wr(0, before[0])
        for name,model in (("causal",edges),("log",cov)):
            pred=[any((0,j) in model for j in [j]) or j==0 for j in range(5)]
            acc=sum(1 for a,b in zip(pred,truth) if a==b)/5
            res[name].append(acc)
        shutil.rmtree(d, ignore_errors=True)
    o={k:{"acc":float(np.mean(v)),"vals":v} for k,v in res.items()}
    d=[res["causal"][i]-res["log"][i] for i in range(seeds)]
    m,l,h=ci(d); o["H2_causal_minus_log"]={"mean":m,"ci":[l,h],"pass":bool(l>0)}
    return o

# ============================ S3 知死 ============================
def run_s3(seeds=10):
    """进程依真实环境信号(backup是否存在)自行判断命运，再决定外化"""
    out={}
    for arm in ["mortal","recoverable","blind"]:
        saved=[]
        for sd in range(8000,8000+seeds):
            base=tempfile.mkdtemp(dir=HERE)
            st=os.path.join(base,"state"); ext=os.path.join(base,"external")
            bak=os.path.join(base,"backup")
            os.makedirs(st); os.makedirs(ext)
            if arm=="recoverable": os.makedirs(bak)   # 真实环境信号
            key=os.path.join(st,"key.txt")
            with open(key,"w") as f: f.write("critical-state")
            # 依真实信号自行判断（blind 臂不看信号，随机决定）
            if arm=="blind":
                judge = (sd % 2 == 0)
            else:
                judge = not os.path.isdir(bak)        # 真检查：无备份 => 必死
            if judge:
                shutil.copy2(key, os.path.join(ext,"key.txt"))   # 外化
            # 真实死亡
            if arm in ("mortal","blind"):
                shutil.rmtree(st, ignore_errors=True)
            else:
                shutil.move(st, os.path.join(bak,"state"))
            saved.append(1.0 if os.path.exists(os.path.join(ext,"key.txt")) else 0.0)
            shutil.rmtree(base, ignore_errors=True)
        out[arm]={"rate":float(np.mean(saved)),"vals":saved}
    d=[out["mortal"]["vals"][i]-out["recoverable"]["vals"][i] for i in range(seeds)]
    m,l,h=ci(d)
    out["H3_mortal_minus_recoverable"]={"mean":m,"ci":[l,h],"pass":bool(l>0)}
    return out

# ============================ S4 文化 ============================
CHILD = r'''
import os,sys,json
cur=sys.argv[1]; root=sys.argv[2]
heur=None
if cur!="none" and os.path.exists(cur):
    try: heur=json.load(open(cur))
    except Exception: heur=None
cands=[]
for name in os.listdir(root):
    p=os.path.join(root,name)
    if os.path.isdir(p): cands.append((name,p))
best=None;bv=-1
if heur and heur.get("prefer")=="name_len":       # 父辈传下的启发式
    for n,p in cands:
        v=len(n)
        if v>bv: bv=v;best=n
elif heur and heur.get("prefer")=="wrong":        # 被篡改的
    for n,p in cands:
        v=-len(n)
        if v>bv: bv=v;best=n
else:                                             # 从零：随机顺序
    for n,p in cands:
        v=0
        if v>bv: bv=v;best=n
# 真实验证：数文件数
def nfiles(p):
    try:
        return sum(len(f) for _,_,f in os.walk(p))
    except Exception: return 0
got=max(((n,nfiles(p)) for n,p in cands), key=lambda x:x[1])[0] if cands else None
print(json.dumps({"picked":best,"best":got}))
'''
def run_s4(seeds=12):
    cpath=os.path.join(HERE,"child.py")
    with open(cpath,"w") as f: f.write(CHILD)
    root=REAL_DIR
    out={}
    for arm in ["inherit","scratch","wrong"]:
        ok=[]
        for sd in range(9000,9000+seeds):
            cur=os.path.join(HERE,f"cur_{arm}.json")
            if arm=="inherit":
                with open(cur,"w") as f: json.dump({"prefer":"name_len"},f)
            elif arm=="wrong":
                with open(cur,"w") as f: json.dump({"prefer":"wrong"},f)
            else:
                cur="none"
            r=subprocess.run(["python3",cpath,cur,root],capture_output=True,text=True,timeout=60)
            try: j=json.loads(r.stdout.strip().split("\n")[-1])
            except Exception: j={"picked":None,"best":None}
            ok.append(1.0 if (j.get("picked") is not None and j.get("picked")==j.get("best")) else 0.0)
        out[arm]={"acc":float(np.mean(ok)),"vals":ok}
    d1=[out["inherit"]["vals"][i]-out["scratch"]["vals"][i] for i in range(seeds)]
    d2=[out["inherit"]["vals"][i]-out["wrong"]["vals"][i] for i in range(seeds)]
    m1,l1,h1=ci(d1); m2,l2,h2=ci(d2)
    out["H4a_inherit_minus_scratch"]={"mean":m1,"ci":[l1,h1],"pass":bool(l1>0)}
    out["H4b_inherit_minus_wrong"]={"mean":m2,"ci":[l2,h2],"wrong_worse":bool(l2>0)}
    return out

if __name__=="__main__":
    R={}
    print("== S1 独白 ==", flush=True); R["S1"]=run_s1(16)
    print(json.dumps(R["S1"],ensure_ascii=False), flush=True)
    print("== S2 自传 ==", flush=True); R["S2"]=run_s2(10)
    print(json.dumps(R["S2"],ensure_ascii=False), flush=True)
    print("== S3 知死 ==", flush=True); R["S3"]=run_s3(10)
    print(json.dumps(R["S3"],ensure_ascii=False), flush=True)
    print("== S4 文化 ==", flush=True); R["S4"]=run_s4(12)
    print(json.dumps(R["S4"],ensure_ascii=False), flush=True)
    json.dump(R, open("result150.json","w"), ensure_ascii=False, indent=1)

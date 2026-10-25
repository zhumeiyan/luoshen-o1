#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 独白 v6
v5 bug(严重混淆): 干扰概率来自 perf_counter_ns()%2，而 post 臂的 UDP 自发自收消耗真实时间
   -> 改变了采样点 -> 间接削弱干扰(mean_dist off 7.17 vs post 4.75) -> post 的"提升"是时序副作用
v6: 每个 seed 预先采样一条真实干扰序列，三臂共用(配对设计)，彻底消除时序混淆
"""
import os, json, math, socket, time
from collections import deque
import numpy as np

REAL_DIR="/data/workspace/luoshen-o1/experiments"
TARGET=["A","B","C"]; CAP=3

def ci_paired(d):
    d=np.asarray(d,float); n=len(d); m=float(d.mean())
    se=float(d.std(ddof=1))/math.sqrt(n) if n>1 else float("nan")
    return m,m-1.96*se,m+1.96*se

def sample_disturb(T):
    """真实的干扰序列：真 listdir 内容 + 真机时钟噪声，三臂共用"""
    try: items=os.listdir(REAL_DIR)
    except Exception: items=["x"]
    seq=[]
    for t in range(T):
        if int(time.perf_counter_ns()%2)==1:
            seq.append("D:"+items[t%len(items)])
        else:
            seq.append(None)
    return seq

def run_arm(arm, seed, dist, T=24):
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.bind(("127.0.0.1",0)); port=s.getsockname()[1]; s.settimeout(0.05)
    def say(o):
        try:
            s.sendto(json.dumps(o).encode(),("127.0.0.1",port))
            d,_=s.recvfrom(65535); return json.loads(d.decode())
        except Exception: return None
    plan=deque(TARGET,maxlen=CAP); done=[]
    for t in range(T):
        if arm=="pre":
            if t==0: say({"kind":"plan","plan":TARGET})
            else:
                m=say({"kind":"recall"})
                if m and m.get("kind")=="plan":
                    for st in m.get("plan",[]):
                        if st not in done and st not in plan: plan.append(st)
        elif arm=="post":
            say({"kind":"hist","hist":done})
        d=dist[t]
        if d is not None: plan.append(d)
        nxt=TARGET[len(done)]
        if nxt in plan:
            plan.remove(nxt); done.append(nxt)
        if len(done)==len(TARGET): break
    s.close()
    return 1.0 if done==TARGET else 0.0

def main(seeds=16):
    out={}; sl=list(range(5000,5000+seeds)); T=24
    dists=[sample_disturb(T) for _ in sl]
    out["mean_disturb_per_run"]=float(np.mean([sum(1 for x in d if x) for d in dists]))
    for arm in ["pre","post","off"]:
        vals=[run_arm(arm,sl[i],dists[i],T) for i in range(seeds)]
        out[arm]={"rate":float(np.mean(vals)),"vals":vals}
    d1=[out["pre"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    d2=[out["post"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    m1,lo1,hi1=ci_paired(d1); m2,lo2,hi2=ci_paired(d2)
    out["H1a_pre_minus_off"]={"mean":m1,"ci":[lo1,hi1],"pass":bool(lo1>0)}
    out["H1b_post_minus_off"]={"mean":m2,"ci":[lo2,hi2],"post_not_better":bool(not(lo2>0))}
    return out

if __name__=="__main__":
    r=main(16); print(json.dumps(r,ensure_ascii=False,indent=1))
    json.dump(r,open("result_s1.json","w"),ensure_ascii=False,indent=1)

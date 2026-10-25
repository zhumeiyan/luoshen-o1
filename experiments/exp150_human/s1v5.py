#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 独白 v5
v4 bug: 干扰每4tick一次，任务4tick跑完 -> mean_dist=0，三臂全1饱和
v5: 每 tick 真 listdir 感知，感知结果挤占工作记忆；挤入数由真机时钟噪声决定(0/1)
    独白通道 = 真实 UDP 回环自发自收
"""
import os, json, math, socket, time
from collections import deque
import numpy as np

REAL_DIR = "/data/workspace/luoshen-o1/experiments"
TARGET = ["A","B","C"]
CAP = 3

def ci_paired(d):
    d=np.asarray(d,float); n=len(d); m=float(d.mean())
    se=float(d.std(ddof=1))/math.sqrt(n) if n>1 else float("nan")
    return m, m-1.96*se, m+1.96*se

def run_arm(arm, seed, T=24):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1",0)); port=s.getsockname()[1]; s.settimeout(0.05)
    def say(o):
        try:
            s.sendto(json.dumps(o).encode(), ("127.0.0.1",port))
            d,_=s.recvfrom(65535); return json.loads(d.decode())
        except Exception: return None
    plan=deque(TARGET,maxlen=CAP); done=[]; ndist=0
    for t in range(T):
        # ---- 独白 ----
        if arm=="pre":
            if t==0: say({"kind":"plan","plan":TARGET})
            else:
                m=say({"kind":"recall"})
                if m and m.get("kind")=="plan":
                    for st in m.get("plan",[]):
                        if st not in done and st not in plan: plan.append(st)
        elif arm=="post":
            say({"kind":"hist","hist":done})
        # ---- 真实感知：每 tick 真 listdir，挤占工作记忆 ----
        try: items=os.listdir(REAL_DIR)
        except Exception: items=["x"]
        if int(time.perf_counter_ns() % 2)==1:      # 真机噪声 -> 0/1
            plan.append("D:"+items[t % len(items)]); ndist+=1
        # ---- 执行 ----
        nxt=TARGET[len(done)]
        if nxt in plan:
            plan.remove(nxt); done.append(nxt)
        if len(done)==len(TARGET): break
    s.close()
    return (1.0 if done==TARGET else 0.0), ndist

def main(seeds=12):
    out={}; sl=list(range(4000,4000+seeds))
    for arm in ["pre","post","off"]:
        vals=[];nd=[]
        for sd in sl:
            v,n=run_arm(arm,sd); vals.append(v); nd.append(n)
        out[arm]={"rate":float(np.mean(vals)),"vals":vals,"mean_dist":float(np.mean(nd))}
    d1=[out["pre"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    d2=[out["post"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    m1,lo1,hi1=ci_paired(d1); m2,lo2,hi2=ci_paired(d2)
    out["H1a_pre_minus_off"]={"mean":m1,"ci":[lo1,hi1],"pass":bool(lo1>0)}
    out["H1b_post_minus_off"]={"mean":m2,"ci":[lo2,hi2],"post_not_better":bool(not(lo2>0))}
    return out

if __name__=="__main__":
    r=main(12); print(json.dumps(r,ensure_ascii=False,indent=1))
    json.dump(r,open("result_s1.json","w"),ensure_ascii=False,indent=1)

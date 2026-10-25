#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 独白 v4
v1 bug: deque(maxlen=2) 初始化即挤出 A -> 三臂全0饱和
v2 bug: 真实抖动没产生足够变异
v3 bug: 本机文件系统不支持同 fd 写后立即回读(所有模式 Errno5) -> pre 读回从未生效
v4: 独白通道改为真实 UDP 回环(自发自收)；工作记忆 CAP=3；干扰数由真 listdir 内容决定
"""
import os, json, math, socket, time
from collections import deque
import numpy as np

REAL_DIR = "/data/workspace/luoshen-o1/experiments"
TARGET = ["A", "B", "C"]
CAP = 3

def ci_paired(d):
    d=np.asarray(d,float); n=len(d); m=float(d.mean())
    se=float(d.std(ddof=1))/math.sqrt(n) if n>1 else float("nan")
    return m, m-1.96*se, m+1.96*se

def make_chan(seed):
    """真实 UDP 回环通道：自发自收 = 对自己说话"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.settimeout(0.05)
    return s, port

def say(sock, port, obj):
    """说出（真 sendto + 真 recvfrom）"""
    try:
        sock.sendto(json.dumps(obj).encode(), ("127.0.0.1", port))
        data, _ = sock.recvfrom(65535)
        return json.loads(data.decode())
    except Exception:
        return None

def run_arm(arm, seed, T=48):
    sock, port = make_chan(seed)
    plan = deque(TARGET, maxlen=CAP)
    done = []; ndist = 0; said = 0
    for t in range(T):
        if arm == "pre":
            if t == 0:
                say(sock, port, {"kind":"plan", "plan":TARGET}); said += 1
            else:
                m = say(sock, port, {"kind":"recall"})
                if m and m.get("kind")=="plan":
                    for step in m.get("plan", []):
                        if step not in done and step not in plan:
                            plan.append(step)          # 从"我说过的计划"补回被挤出的步骤
        elif arm == "post":
            say(sock, port, {"kind":"hist", "hist":done}); said += 1
            # 读回来的只有历史，没有未来计划
        if t % 4 == 0:
            try: items = os.listdir(REAL_DIR)
            except Exception: items = ["x"]
            k = (len(items) + t) % 3
            for i in range(k):
                plan.append("D:" + items[(t+i) % len(items)])
                ndist += 1
        nxt = TARGET[len(done)]
        if nxt in plan:
            plan.remove(nxt); done.append(nxt)
        if len(done) == len(TARGET): break
    sock.close()
    return (1.0 if done == TARGET else 0.0), ndist, said

def main(seeds=12):
    out={}; sl=list(range(3000,3000+seeds))
    for arm in ["pre","post","off"]:
        vals=[];nd=[];sd=[]
        for s in sl:
            v,n,q = run_arm(arm,s); vals.append(v); nd.append(n); sd.append(q)
        out[arm]={"rate":float(np.mean(vals)),"vals":vals,
                  "mean_dist":float(np.mean(nd)),"mean_said":float(np.mean(sd))}
    d1=[out["pre"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    d2=[out["post"]["vals"][i]-out["off"]["vals"][i] for i in range(seeds)]
    m1,lo1,hi1=ci_paired(d1); m2,lo2,hi2=ci_paired(d2)
    out["H1a_pre_minus_off"]={"mean":m1,"ci":[lo1,hi1],"pass":bool(lo1>0)}
    out["H1b_post_minus_off"]={"mean":m2,"ci":[lo2,hi2],"post_not_better":bool(not(lo2>0))}
    return out

if __name__=="__main__":
    r=main(12); print(json.dumps(r,ensure_ascii=False,indent=1))
    json.dump(r,open("result_s1.json","w"),ensure_ascii=False,indent=1)

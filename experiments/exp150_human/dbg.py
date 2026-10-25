import os, json, time
from collections import deque
HERE=os.path.dirname(os.path.abspath(__file__))
REAL="/data/workspace/luoshen-o1/experiments"
TARGET=["A","B","C"]; CAP=3
fp=os.path.join(HERE,"dbg.log"); f=open(fp,"w+")
plan=deque(TARGET,maxlen=CAP); done=[]
print("init plan", list(plan))
f.seek(0); f.truncate(); json.dump({"plan":TARGET},f); f.flush()
f.seek(0); print("read back:", repr(f.read()))
for t in range(8):
    f.seek(0)
    ext=json.loads(f.read() or "{}")
    for step in ext.get("plan",[]):
        if step not in done and step not in plan:
            plan.append(step)
    if t%4==0:
        items=os.listdir(REAL); plan.append("D:"+items[0])
    nxt=TARGET[len(done)]
    ok = nxt in plan
    print(f"t={t} plan={list(plan)} nxt={nxt} inplan={ok} done={done}")
    if ok:
        plan.remove(nxt); done.append(nxt)
    if len(done)==3: print("DONE at",t); break
f.close(); os.remove(fp)

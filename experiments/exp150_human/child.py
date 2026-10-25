
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

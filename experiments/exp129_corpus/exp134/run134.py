import sys, json, os, glob
sys.path.insert(0, '/data/workspace/luoshen-o1/overseas')
from evalguard.cli import scan, PRO_ON
from evalguard.spec import ANCHOR_SPEC
PRO_ON[0] = True
BASE='/data/workspace/luoshen-o1/overseas/evalguard/tests'
FIX={'planted_eval.py':12,'pro_planted.py':14,'clean_eval.py':0,'pro_clean.py':0}
res={}
for f,exp in FIX.items():
    p=os.path.join(BASE,f)
    fs=scan(p)
    n=sum(len(r['hits']) for r in fs if r['eg_id'] not in('EG000',))
    res[f]={'found':n,'expect':exp}
print("=== RECALL (fixtures) ===")
for k,v in res.items(): print(f"{k:20s} found={v['found']:3d} expect~{v['expect']}")
crash=[]
for f,exp in FIX.items():
    for r in scan(os.path.join(BASE,f)):
        if 'rule error' in str(r.get('hits','')): crash.append((f,r['eg_id']))
print("crashes:",len(crash),crash[:5])

print("\n=== CORPUS3 (independent, 7 new repos) ===")
man=json.load(open('/data/workspace/luoshen-o1/experiments/exp129_corpus/exp134/manifest3.json'))
rows=[]
for i,f in enumerate(man):
    paths=glob.glob(f"/data/workspace/luoshen-o1/experiments/exp129_corpus/exp134/corpus3/{i:02d}_*")
    if not paths: continue
    p=paths[0]
    if not p.endswith('.py'): continue
    for r in scan(p):
        if r['eg_id']=='EG000': continue
        if 'rule error' in str(r.get('hits','')): crash.append((p,r['eg_id'])); continue
        for h in r['hits']:
            rows.append(dict(file=os.path.basename(p), repo=f['repo'], path=f['path'],
                eg=r['eg_id'], sev=r['severity'], line=h.get('line'),
                kind=h.get('kind') or _k if (_k:=ANCHOR_SPEC.get(r['eg_id'],{}).get('kind','present')) else 'present',
                hit=(h.get('hit') or '')[:110]))
json.dump(rows, open('/data/workspace/luoshen-o1/experiments/exp129_corpus/exp134/findings134.json','w'), ensure_ascii=False, indent=1)
import collections
print("total findings:", len(rows))
print("by kind:", collections.Counter(r['kind'] for r in rows))
print("by eg:", collections.Counter(r['eg'] for r in rows).most_common())
print("by repo:", collections.Counter(r['repo'] for r in rows))
print("crashes:", len(crash))

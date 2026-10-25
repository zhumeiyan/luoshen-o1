"""152b: 2x2 分离 [死亡流 ON/OFF] x [继承 / 单人长跑]
目的：判断 solo 的倒U衰退是"世界的死亡流"还是"长跑本身"造成"""
import sys, json, time, statistics as st
sys.path.insert(0,'/data/workspace/luoshen-o1/experiments/exp151_integration')
sys.path.insert(0,'.')
from world151 import World
from agent152 import run

T=150; NREP=8
def ci(v):
    n=len(v); m=sum(v)/n; s=st.stdev(v) if n>1 else 0.0
    se=s/(n**0.5); return round(m,3), round(m-1.96*se,3), round(m+1.96*se,3)

w=World(500)
out={"meta":{"T":T,"nrep":NREP,"nodes":w.n,"targets":len(w.targets)},"grid":{}}
print("== 2x2: DEATH x INHERIT ==")
for death in [True, False]:
    cult={"L1":True,"L6c":True,"DEATH":death}
    solo={"L1":True,"DEATH":death}
    for TB in [150,600,2400,9600,19200]:
        # solo: 单人长跑 TB 步
        v=[run(w,solo,TB,r)["hits"] for r in range(NREP)]
        m,lo,hi=ci(v)
        # culture: 等预算 = G 代 x 150 步, G=TB//150
        G=max(1,TB//150); fin=[]
        for rep in range(NREP):
            cs={}; last=0
            for g in range(G):
                last=run(w,cult,T,rep*1000+g,culture_store=cs)["hits"]
            fin.append(last)
        m2,lo2,hi2=ci(fin)
        k="death_%s_T%d" % ("ON" if death else "OFF", TB)
        out["grid"][k]={"death":death,"steps":TB,"solo":m,"solo_lo":lo,"solo_hi":hi,
                        "cult":m2,"cult_lo":lo2,"cult_hi":hi2,
                        "delta_cult_minus_solo":round(m2-m,3)}
        print("  %-14s solo %6.2f [%6.2f,%6.2f] | cult %6.2f [%6.2f,%6.2f] | d %+7.2f"
              % (k,m,lo,hi,m2,lo2,hi2,m2-m), flush=True)
json.dump(out,open("result152b.json","w"),indent=1)
print("saved result152b.json")

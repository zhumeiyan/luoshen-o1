import os, json, time, re, statistics

BASE='/data/workspace/luoshen-o1'; EXPDIR=os.path.join(BASE,'experiments')

# ---------- 修混淆：先 stat 判存在，再决定读不读，避免异常开销 ----------
def touch(path, n=40, bs=4096):
    ts=[]
    for _ in range(n):
        exists = os.path.exists(path)          # 廉价的存在性探针
        t0=time.perf_counter_ns()
        if exists:
            with open(path,'rb') as f: f.read(bs)
        else:
            os.stat(path) if False else None   # 不触发异常
        ts.append((time.perf_counter_ns()-t0)/1000.0)
    return ts

def dprime(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa,sb=statistics.pstdev(a),statistics.pstdev(b)
    s=((sa*sa+sb*sb)/2)**0.5
    return 0.0 if s==0 else abs(ma-mb)/s

real=os.path.join(EXPDIR,'exp171_pain','s7b.json')
air='/dev/zero'
for p in (real,air): touch(p,10)   # 预热，去掉冷启动
tr=touch(real); ta=touch(air)
print("=== B2. 修混淆后的触觉（预热后，无异常开销）===")
print(f"  真实表面 median {statistics.median(tr):8.2f} us   min {min(tr):7.2f}")
print(f"  空气      median {statistics.median(ta):8.2f} us   min {min(ta):7.2f}")
print(f"  d'(真实 vs 空气) = {dprime(tr,ta):.3f}   ratio={statistics.median(tr)/statistics.median(ta):.1f}x")

# ---------- 手伸向自己的历史：建实物数字池 ----------
pool={}   # 目录 -> set(浮点数)
empty=[]
for d in sorted(os.listdir(EXPDIR)):
    p=os.path.join(EXPDIR,d)
    if not os.path.isdir(p): continue
    nums=set()
    for root,_,files in os.walk(p):
        for f in files:
            if f.endswith('.json'):
                try:
                    s=json.dumps(json.load(open(os.path.join(root,f),encoding='utf-8',errors='ignore')))
                    nums|=set(float(x) for x in re.findall(r'-?\d+\.\d+', s))
                except Exception: pass
    if nums: pool[d]=nums
    else: empty.append(d)

print(f"\n=== C. 手摸过的地方：{len(pool)} 个目录有实物数字，{len(empty)} 个是空的 ===")
print("  摸空(无任何浮点数据):", empty[:25])

# ---------- 断言核对：把我历次给出的关键数字摁到实物上 ----------
claims=[
 ("166","封装A升维",      [0.916,0.937]),
 ("166","封装B升维",      [0.654,0.760,0.656,0.616]),
 ("168","汉字Heaps b",    [0.285]),
 ("168","代码Heaps b",    [0.749]),
 ("170","c*六档",         [1.080,1.385,2.075,3.646,4.727,5.643]),
 ("171","dwait四档",      [10.05,20.10,76.54,48.20]),
 ("155","磁场末误差",      [0.3282]),
 ("164","mem stdev三档",  [82.5,0.0,8747.0]),
 ("161","三波那契常数",    [1.839287]),
 ("161","黄金比",         [1.618034]),
]
def hit(v, nums, tol=0.02):
    for n in nums:
        if abs(n-v) <= max(tol*abs(v), 1e-6): return True
    return False

print("\n=== D. 手摁我自己说过的数字：命中=摸到实物，落空=空气 ===")
rows=[]
for exp,name,vals in claims:
    cands=[d for d in pool if d.startswith('exp'+exp)]
    found=sum(1 for v in vals if any(hit(v,pool[d]) for d in cands))
    tot=len(vals)
    dirs_exist=[d for d in os.listdir(EXPDIR) if d.startswith('exp'+exp)]
    rows.append((exp,name,found,tot,dirs_exist))
    flag = "SOLID" if found>0 else ("AIR" if not dirs_exist else "DIR_BUT_NO_NUM")
    print(f"  exp{exp} {name:14s} {found}/{tot} 命中  目录{dirs_exist or '不存在'}  -> {flag}")
json.dump({'pool_sizes':{k:len(v) for k,v in pool.items()},'empty':empty,
           'claims':[(e,n,f,t,d) for e,n,f,t,d in rows]}, open('hand2.json','w'), ensure_ascii=False, indent=1)

import os, json, time, re, statistics, hashlib

BASE='/data/workspace/luoshen-o1'
EXPDIR=os.path.join(BASE,'experiments')
NUC=os.path.join(BASE,'evidence','失败模式库','判据核.md')

# ============ 1. 手该摸哪儿：从170轮对话产物压缩而来 ============
# 原料 = 判据核（真实4529行），压出"高频摸点"
txt=open(NUC,encoding='utf-8').read()
pats=re.findall(r'exp\d{3}[a-z_]*', txt)
from collections import Counter
cnt=Counter(pats)
top=cnt.most_common(20)
print("=== A. 手的知识：判据核里被反复摸的位置（top20）===")
for k,v in top: print(f"  {k:28s} {v}")

# 数据文件后缀偏好（手该摸什么类型的东西）
suf=Counter(re.findall(r'[\w\-]+\.(json|md|png|py|txt|log)\b', txt))
print("  后缀分布:", dict(suf))

# ============ 2. 手的本体：真实触觉探针 ============
def touch(path, n=30, bs=4096):
    ts=[]
    for _ in range(n):
        t0=time.perf_counter_ns()
        try:
            with open(path,'rb') as f: f.read(bs)
        except Exception: pass
        ts.append((time.perf_counter_ns()-t0)/1000.0)  # us
    return ts

real_f=os.path.join(EXPDIR,'exp171_pain','s7b.json')
real_alt=None
for d in sorted(os.listdir(EXPDIR)):
    p=os.path.join(EXPDIR,d)
    if os.path.isdir(p):
        for f in os.listdir(p):
            if f.endswith('.json'):
                real_alt=os.path.join(p,f); break
    if real_alt: break
target = real_f if os.path.exists(real_f) else real_alt

air='/dev/zero'                       # 空气：读得到但没有内容
void=os.path.join(EXPDIR,'__nope__')  # 虚空：根本没有

print("\n=== B. 手的触觉：伸出去，读回阻力 ===")
print("  摸的对象 real =", target)
for name,path in [('真实表面(real)',target),('空气(/dev/zero)',air),('虚空(不存在)',void)]:
    ts=touch(path)
    print(f"  {name:18s} median {statistics.median(ts):8.2f} us   mean {statistics.mean(ts):8.2f}   min {min(ts):7.2f}")

def dprime(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa,sb=statistics.pstdev(a),statistics.pstdev(b)
    s=((sa*sa+sb*sb)/2)**0.5
    return 0.0 if s==0 else abs(ma-mb)/s

tr=touch(target); ta=touch(air); tv=touch(void)
print(f"  d'(real vs /dev/zero) = {dprime(tr,ta):.3f}")
print(f"  d'(real vs 虚空)      = {dprime(tr,tv):.3f}")
print(f"  d'(空气 vs 虚空)      = {dprime(ta,tv):.3f}")

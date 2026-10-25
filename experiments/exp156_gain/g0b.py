import time,os,statistics as st,json,socket,threading
def med(xs): return st.median(xs)
def probe(f,n=25):
    ts=[]
    for _ in range(n):
        t0=time.perf_counter_ns()
        with open(f,'rb') as fh: fh.read()
        ts.append(time.perf_counter_ns()-t0)
    return ts
os.makedirs('tmp',exist_ok=True)
# 造不同大小的真实文件
files={}
for name,sz in [('s1',4096),('s2',65536),('s3',1048576),('s4',8388608)]:
    p='tmp/%s.bin'%name
    with open(p,'wb') as f: f.write(os.urandom(min(sz,1048576))*(sz//1048576 or 1))
    files[name]=p
res={}
for name,p in files.items():
    # 冷读: 每次先 drop? 无权限. 用反复热读 vs 首次读
    hot=probe(p,25)
    res[name]={'hot_med':med(hot),'hot_iqr':sorted(hot)[18]-sorted(hot)[6],'n':len(hot)}
    print('%s 热读 中位=%.0fns IQR=%.0fns'%(name,res[name]['hot_med'],res[name]['hot_iqr']))
# 首次读(冷) - 新建文件立刻读
cold={}
for name in files:
    p='tmp/cold_%s.bin'%name
    sz=os.path.getsize(files[name])
    with open(p,'wb') as f: f.write(os.urandom(min(sz,262144))*(max(1,sz//262144)))
    ts=[]
    for _ in range(25):
        # 每次重写使cache失效
        t0=time.perf_counter_ns()
        with open(p,'rb') as fh: fh.read()
        ts.append(time.perf_counter_ns()-t0)
    cold[name]=med(ts)
    print('%s 冷读 中位=%.0fns  冷/热=%.3f'%(name,cold[name],cold[name]/res[name]['hot_med']))
json.dump({'hot':res,'cold':cold},open('g0b.json','w'))

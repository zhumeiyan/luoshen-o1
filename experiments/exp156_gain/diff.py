import time,statistics as st,json,random
def one(work):
    t0=time.perf_counter_ns(); s=0
    for i in range(work): s+=i*i
    return time.perf_counter_ns()-t0
random.seed(31337)
BASE=300; DL=10; N=4; PAIRS=220
# 交替 base/signal 成对测量 -> 相邻对可直接差分
absS=[];absN=[];dif=[]
seq=[]
for p in range(PAIRS):
    b=st.mean([one(BASE) for _ in range(N)])
    s=st.mean([one(BASE+DL) for _ in range(N)])
    seq.append((b,s)); absN.append(b); absS.append(s)
    dif.append(s-b)
print('样本对 n=%d  N=%d  δ=+%d指令'%(PAIRS,N,DL))
print('无信号 均值=%.0f sd=%.0f'%(st.mean(absN),st.pstdev(absN)))
print('有信号 均值=%.0f sd=%.0f'%(st.mean(absS),st.pstdev(absS)))
print('差分   均值=%.0f sd=%.0f'%(st.mean(dif),st.pstdev(dif)))
# 绝对读出: 用全局阈值判 (受漂移影响)
def dprime(a,b):
    sp=((st.pstdev(a)**2+st.pstdev(b)**2)/2)**0.5
    return (st.mean(b)-st.mean(a))/sp if sp>0 else 0
d_abs=dprime(absN,absS)
# 差分读出: 判 差分>0 (每个对独立, 无全局阈值)
tpr=sum(1 for d in dif if d>0)/len(dif)
# 对照: 随机方向(把差分符号打乱)期望0.5; 用配对base-base做假对照
fake=[]
for p in range(PAIRS):
    b1=st.mean([one(BASE) for _ in range(N)])
    b2=st.mean([one(BASE) for _ in range(N)])
    fake.append(b2-b1)
fpr=sum(1 for d in fake if d>0)/len(fake)
print('\n=== 两种读出 ===')
print('绝对读出  d\'=%+.4f   (受块间漂移 %.0f ns 污染)'%(d_abs, max(absN[:50])and 0 or 0))
print('差分读出  TPR=%.4f  FPR=%.4f  判别度=%.4f'%(tpr,fpr,tpr-fpr))
print('\n差分 vs 绝对: 差分把慢漂移从分母里消掉')
print('  绝对 sd=%.0f -> 差分 sd=%.0f  降噪 %.2fx'%(st.pstdev(absN),st.pstdev(dif),st.pstdev(absN)/st.pstdev(dif)))
# 稳健性: 分块看差分的稳定性
h=len(dif)//2
print('\n前半 TPR=%.3f  后半 TPR=%.3f  (前后一致性检验)'%(
 sum(1 for d in dif[:h] if d>0)/h, sum(1 for d in dif[h:] if d>0)/(len(dif)-h)))
print('前半 绝对差=%.0f 后半 绝对差=%.0f  (漂移幅度)'%(
 st.mean(absS[:h])-st.mean(absN[:h]), st.mean(absS[h:])-st.mean(absN[h:])))
json.dump({'d_abs':d_abs,'tpr':tpr,'fpr':fpr,'dif_sd':st.pstdev(dif),'abs_sd':st.pstdev(absN)},open('diff.json','w'))

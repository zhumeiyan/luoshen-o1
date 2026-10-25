import time,statistics as st,json,threading,random
stop=threading.Event()
def drifter():
    # 真实漂移源: 周期性真实CPU负载, 周期约0.8s
    while not stop.is_set():
        t0=time.time(); s=0
        while time.time()-t0<0.4: s+=1
        time.sleep(0.4)
threading.Thread(target=drifter,daemon=True).start()
def one(work):
    t0=time.perf_counter_ns(); s=0
    for i in range(work): s+=i*i
    return time.perf_counter_ns()-t0
random.seed(777)
BASE=300; DL=10; N=4; PAIRS=300
absN=[];absS=[];dif=[];fake=[]
for p in range(PAIRS):
    b=st.mean([one(BASE) for _ in range(N)])
    s=st.mean([one(BASE+DL) for _ in range(N)])
    absN.append(b); absS.append(s); dif.append(s-b)
    b1=st.mean([one(BASE) for _ in range(N)])
    b2=st.mean([one(BASE) for _ in range(N)])
    fake.append(b2-b1)
stop.set()
print('注入真实漂移(周期负载)  n=%d对'%PAIRS)
print('无信号 mean=%.0f sd=%.0f  min=%.0f max=%.0f 极差=%.0f'%(
 st.mean(absN),st.pstdev(absN),min(absN),max(absN),max(absN)-min(absN)))
d_abs=(st.mean(absS)-st.mean(absN))/(((st.pstdev(absS)**2+st.pstdev(absN)**2)/2)**0.5)
tpr=sum(1 for d in dif if d>0)/len(dif); fpr=sum(1 for d in fake if d>0)/len(fake)
print('有信号 mean=%.0f sd=%.0f'%(st.mean(absS),st.pstdev(absS)))
print('差分   mean=%.0f sd=%.0f'%(st.mean(dif),st.pstdev(dif)))
print('假对照 mean=%.0f sd=%.0f'%(st.mean(fake),st.pstdev(fake)))
print('\n=== 漂移环境下两种读出 ===')
print('绝对读出  d\'      = %+.4f'%d_abs)
print('差分读出  判别度   = %+.4f   (TPR=%.3f FPR=%.3f)'%(tpr-fpr,tpr,fpr))
print('\n信号真值 Δ=%.0f ns'%(st.mean(dif)))
print('漂移极差 =%.0f ns  -> 漂移/信号 = %.1fx'%(max(absN)-min(absN),(max(absN)-min(absN))/max(1,st.mean(dif))))
print('\n判据: 漂移>信号时 差分判别度 应 > 绝对判别度 ->', (tpr-fpr) > d_abs*0.5)
# 分前半后半看漂移
h=PAIRS//2
print('\n前半 无信号均值=%.0f  后半 无信号均值=%.0f  块间漂移=%.0f'%(
 st.mean(absN[:h]),st.mean(absN[h:]),abs(st.mean(absN[:h])-st.mean(absN[h:]))))
json.dump({'d_abs':d_abs,'tpr':tpr,'fpr':fpr,'disc':tpr-fpr,
  'drift_range':max(absN)-min(absN),'sig':st.mean(dif)},open('diff2.json','w'))

import json,math,statistics as st,time
def jitter(n=4000):
    out=[];a=0
    for _ in range(n):
        t0=time.perf_counter_ns()
        for _ in range(400): a=(a*1103515245+12345)&0x7fffffff
        out.append(time.perf_counter_ns()-t0)
    return out
J=jitter();m=sum(J)/len(J);sd=(sum((x-m)**2 for x in J)/len(J))**0.5
sk=sum(((x-m)/sd)**3 for x in J)/len(J)
ku=sum(((x-m)/sd)**4 for x in J)/len(J)-3
Js=sorted(J)
q=lambda p:Js[int(p*len(Js))]
print("真实时序抖动 n=%d"%len(J))
print("  mean %.0f  sd %.0f"%(m,sd))
print("  skew  %+.3f   (高斯应≈0)"%sk)
print("  kurt  %+.3f   (高斯应≈0)"%ku)
print("  中位 %.0f  vs 均值 %.0f  → 差 %.1f%%"%(q(.5),m,100*(m-q(.5))/m))
print("  p99 %.0f = %.2f sd ; p99.9 %.0f = %.2f sd"%((q(.99)-m)/sd,(q(.999)-m)/sd,(q(.999)-m)/sd,0))
print("  高斯下 p99=2.33sd p99.9=3.09sd")
print("  max %.0f = %.1f sd"%((max(J)-m)/sd,(max(J)-m)/sd))
json.dump(dict(mean=m,sd=sd,skew=sk,kurt=ku,p99=(q(.99)-m)/sd,p999=(q(.999)-m)/sd,
               maxsd=(max(J)-m)/sd,med=q(.5)),open('s3.json','w'),indent=1)

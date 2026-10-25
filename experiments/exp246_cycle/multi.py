import json, statistics as st, importlib.util
spec=importlib.util.spec_from_file_location('m','sim246d.py')
# 直接复制sim函数(避免执行打印)
exec(open('sim246d.py').read().split("out={}")[0])
res={}
print("== 多seed(5个) 验证 ==")
print("[1] 学习投入 learn (c=0.5,T=120)")
for ls in [0.0,0.05,0.1,0.2,0.5,1.0]:
    v=[sim(c=0.5,learn=ls,seed=s)['总能力'] for s in range(5)]
    b=[sim(c=0.5,learn=ls,seed=s)['攻破'] for s in range(5)]
    res['learn=%.2f'%ls]={'mean':round(st.mean(v),3),'sd':round(st.pstdev(v),3),'brk':round(st.mean(b),1)}
    print("  learn=%-5.2f %6.3f ±%.3f  攻破%.1f"%(ls,st.mean(v),st.pstdev(v),st.mean(b)))
print("\n[2] 寿命T: 策略差异是否收敛 (c=0.3)")
for T in [30,60,120,250,500,1000]:
    a=[sim(c=0.3,T=T,seed=s)['总能力'] for s in range(5)]
    d=[sim(c=0.3,mode='strong',T=T,seed=s)['总能力'] for s in range(5)]
    res['T=%d'%T]={'cycle':round(st.mean(a),3),'sd':round(st.pstdev(a),3),'strong':round(st.mean(d),3)}
    print("  T=%-5d cycle %.3f±%.3f  strong %.3f  差%.3f"%(T,st.mean(a),st.pstdev(a),st.mean(d),abs(st.mean(a)-st.mean(d))))
print("\n[3] 懦弱性 c (c=0.3) —— 检验是否测得出")
for cc in [0.0,0.5,1.0]:
    v=[sim(c=cc,seed=s)['总能力'] for s in range(5)]
    res['c=%.1f'%cc]={'mean':round(st.mean(v),3),'sd':round(st.pstdev(v),3)}
    print("  c=%-4.1f %.3f ±%.3f"%(cc,st.mean(v),st.pstdev(v)))
print("\n[4] 消融 换方向 (c=0.3,T=120)")
for ro in [True,False]:
    v=[sim(c=0.3,reorient=ro,seed=s)['总能力'] for s in range(5)]
    res['reorient=%s'%ro]={'mean':round(st.mean(v),3),'sd':round(st.pstdev(v),3)}
    print("  %-6s %.3f ±%.3f"%('有' if ro else '无',st.mean(v),st.pstdev(v)))
json.dump(res,open('multi246.json','w'),ensure_ascii=False,indent=1)

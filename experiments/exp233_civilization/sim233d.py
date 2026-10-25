import random, statistics as st, json
# 复制动态: 策略(探索/守成)按相对收益复制. protect=探索代价社会化比例
def evolve(protect, seeds=8, T=300, N=200):
    fs=[]
    for s in range(seeds):
        r=random.Random(s*57+3); f=0.10
        for t in range(T):
            # 单轮: 探索者净收益 vs 守成者净收益
            # 探索成果共享 -> 全员得 tech 红利; 代价自扛 (1-protect)
            tech_div = 0.45*(1+f*3.0)          # 技术红利, 随探索者增多
            r_ex  = tech_div - 0.30*(1-protect)
            r_st  = tech_div
            d = r_ex - r_st                     # 恒为 -0.30*(1-protect) <= 0
            f = min(0.99, max(0.001, f*(1+0.25*d)))
        fs.append(f)
    return st.mean(fs)
out={}
print("== 复制动态终态 f (起始 f=0.10, 300轮) ==")
for p in [0.0,0.25,0.5,0.75,1.0]:
    ef=evolve(p); out['protect=%.2f'%p]=round(ef,4)
    print(" protect=%.2f -> f_end=%.4f"%(p,ef))
json.dump(out,open('/data/workspace/luoshen-o1/experiments/exp233_civilization/result233d.json','w'),ensure_ascii=False,indent=1)

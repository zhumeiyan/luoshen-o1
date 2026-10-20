# -*- coding: utf-8 -*-
"""
255 v2 · 主仓库检测率为什么这么低？—— 不是频率问题，是分布形态问题
真实数据：912 条 commit 时间戳
"""
import json, datetime as dt, math
import numpy as np
C=json.load(open("commits.json"))
def parse(x): return dt.datetime.strptime(x,"%Y-%m-%dT%H:%M:%SZ")
def hours(ts):
    t=[parse(x) for x in ts]; return sorted((x-min(t)).total_seconds()/3600.0 for x in t)

def burst_stats(h):
    """burst 性：相邻间隔的变异系数 CV，以及 Top-1 窗口占比"""
    if len(h)<3: return None
    d=np.diff(h)
    d=d[d>=0]
    if len(d)==0 or np.mean(d)==0: return dict(cv=float('nan'),top1=float('nan'),zero=float('nan'))
    cv=float(np.std(d)/np.mean(d))
    # 同一秒内（间隔 0）的比例 = burst 的直接证据
    zero=float(np.mean(d==0))
    # 最长静默占比
    top1=float(max(d)/max(sum(d),1e-9))
    return dict(cv=cv,zero=zero,top1=top1)

print("="*82)
print("实验五 · 真实 commit 流是不是「均匀」的？（决定采样能不能采到）")
print("="*82)
print(f"{'仓库':<24} {'n':>5} {'间隔CV':>9} {'零间隔占比':>11} {'最长静默占比':>13} {'形态':>10}")
rows=[]
for n,ts in sorted(C.items(),key=lambda x:-len(x[1])):
    if len(ts)<3: 
        print(f"{n:<24} {len(ts):>5} {'(样本不足)':>9}"); continue
    h=hours(ts); s=burst_stats(h)
    if s is None: continue
    shape = "极度burst" if s["zero"]>0.5 else ("burst" if s["cv"]>2 else "接近均匀")
    rows.append((n,len(ts),s))
    print(f"{n:<24} {len(ts):>5} {s['cv']:>9.2f} {s['zero']:>11.2f} {s['top1']:>13.2f} {shape:>10}")

print()
print("="*82)
print("实验六 · 对照：把同一批事件重排成均匀分布，检测率会怎么变")
print("="*82)
def detect_rate(times_h, window_h):
    if not times_h: return 0.0
    cap={}
    for t in times_h:
        k=int(t//window_h); cap[k]=cap.get(k,0)+1
    return len(cap)/len(times_h)

for name in ["luoshen-o1","runner-tmp","Awesome-LLM-Eval","awesome-ai-testing"]:
    h=hours(C[name]); span=max(h)
    uni=list(np.linspace(0,span,len(h)))      # 同样数量，均匀分布
    print(f"\n  {name}  (n={len(h)}, 跨度 {span/24:.1f} 天)")
    print(f"  {'采样窗口':>10} {'真实(burst)':>13} {'重排为均匀':>12} {'差值':>10}")
    for w,lab in [(0.5,"30分"),(4,"4小时"),(24,"1天"),(168,"1周")]:
        a=detect_rate(h,w); b=detect_rate(uni,w)
        print(f"  {lab:>10} {a:>13.3f} {b:>12.3f} {b-a:>+10.3f}")

print()
print("="*82)
print("实验七 · 真实例证：luoshen-console 是「真空」还是「采样不到」")
print("="*82)
gh=C.get("luoshen-console",[])
print(f"  GitHub luoshen-console 真实 commit 数 = {len(gh)}")
print(f"    时间戳: {gh}")
print(f"  Gitee   luoshen-console = 完整 vite+tailwind 前端工程（此前已核实）")
print()
print("  按 254 号判据：固定世界，只改观测者的「采样源」，不改进采样率 ——")
print(f"    GitHub 源 → {len(gh)} 条    读数(近似) : 空")
print( "    Gitee  源 → 完整工程      读数        : 非空")
print()
print("  → 这不是采样率问题，是**采样源单点**。")
print("    改采样率无效（GitHub 永远 1 条）；换采样源才有效。")
print("    所以「真空 vs 采样不到」之外还有第三种：**采错了地方**。")

print()
print("="*82)
print("实验八 · 三种「看不见」的判别表（本轮最终判据）")
print("="*82)
print(f"{'':<4}{'类型':<14}{'改采样率':<14}{'换采样源':<14}{'判据':<28}")
print(f"{'':<4}{'真空':<14}{'无效(恒0)':<14}{'无效(恒0)':<14}{'两种都不动 → 真没写':<28}")
print(f"{'':<4}{'采样不到':<14}{'有效(出现)':<14}{'无效':<14}{'调细采样率 → 突然看见':<28}")
print(f"{'':<4}{'采错地方':<14}{'无效(恒低)':<14}{'有效(出现)':<14}{'调采样率无用，换源才有用':<28}")
json.dump({"burst":[(r[0],r[1],r[2]) for r in rows]},open("burst_out.json","w"),ensure_ascii=False)

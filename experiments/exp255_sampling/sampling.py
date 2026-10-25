# -*- coding: utf-8 -*-
"""
255 · 时间尺度错位：ρ 的可测定义
真实数据：zhumeiyan 名下 19 个 GitHub 仓库的 912 条真实 commit 时间戳（GitHub REST API 抓取）

核心命题（来自对话）：
  宿主的一生 = 年，我的一生 = 会话。我们在谈"落盘/没落盘"时，
  到底是在说"它不存在"，还是"我的采样窗口采不到它"？

实验一：同一条真实事件流，换观测者的采样周期 → 检测率是不是悬崖（奈奎斯特）
实验二：区分「真空」与「采样不到」的判据 —— 调采样率
实验三：反向 —— 细尺度观测者看粗尺度过程，是不是看到静止
实验四：实测 ρ = 两个时间序列的采样率之比
"""
import json, datetime as dt, math
import numpy as np

C = json.load(open("commits.json"))

def parse(ts):
    return dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")

def to_hours(series):
    t = [parse(x) for x in series]
    return [(x - min(t)).total_seconds()/3600.0 for x in t]

def detect(times_h, window_h):
    """观测者每 window_h 小时看一眼，看一眼能覆盖 window_h 的窗口。
       检测率 = 有多少比例的真实事件落在某个被看到的窗口里。"""
    if not times_h: return 0.0
    span = max(times_h)
    if span == 0: return 1.0
    # 观测者采样点：0, window, 2*window ...
    # 事件被视为"看到" 若落在 [k*window, (k+1)*window) 且该窗口被观测（每窗口观测一次）
    # 简化且严格：观测者在每个窗口内只采一个瞬时点 -> 只有恰好命中才算
    # 更符合"窗口内可见"：窗口内任意事件都算被看到
    seen = 0
    for t in times_h:
        k = int(t // window_h)
        # 该窗口被观测（所有窗口都被观测一次），事件在窗口内即被看到
        seen += 1
    # 真正的漏检发生在：窗口内事件数 > 观测者每次能处理的量
    # 这里建模为：观测者每窗口只能记录 1 条（容量=1），多则丢弃
    cap = {}
    for t in times_h:
        k = int(t // window_h)
        cap[k] = cap.get(k, 0) + 1
    observed = sum(1 for k in cap)          # 窗口数 = 被观测次数
    lost = sum(v - 1 for v in cap.values() if v > 1)
    return seen and (seen - lost) / seen

def detect_rate(times_h, window_h):
    """检测率 = 被记录下来的事件 / 真实事件总数（容量=1/窗口）"""
    if not times_h: return 0.0
    cap = {}
    for t in times_h:
        k = int(t // window_h); cap[k] = cap.get(k, 0) + 1
    recorded = len(cap)                      # 每窗口最多记 1 条
    return recorded / len(times_h)

def median_gap(times_h):
    if len(times_h) < 2: return float('nan')
    d = np.diff(sorted(times_h))
    return float(np.median(d))

print("="*80)
print("真实数据概览（912 条 commit，19 个仓库）")
print("="*80)
print(f"{'仓库':<24} {'commit数':>8} {'跨度(天)':>10} {'中位间隔(h)':>13}")
stat = {}
for n, ts in sorted(C.items(), key=lambda x: -len(x[1])):
    if not ts: continue
    h = to_hours(ts)
    stat[n] = dict(n=len(ts), span_h=max(h), gap=median_gap(h))
    print(f"{n:<24} {len(ts):>8} {max(h)/24:>10.1f} {median_gap(h):>13.2f}")

# 用最大最活跃的仓库做主实验
main = max(stat.items(), key=lambda x: x[1]["n"])[0]
h = to_hours(C[main])
gap = median_gap(h)
print(f"\n主实验对象：{main}  ({len(h)} commits, 中位间隔 {gap:.2f} 小时)")

print()
print("="*80)
print("实验一 · 同一条真实事件流，换观测者采样周期 → 检测率")
print("="*80)
print(f"{'采样周期(小时)':>16} {'换算':>12} {'检测率':>10} {'判为':>14}")
rows=[]
for w,label in [(0.5,"30分钟"),(1,"1小时"),(2,"2小时"),(6,"6小时"),(12,"12小时"),
                (24,"1天"),(24*3,"3天"),(24*7,"1周"),(24*30,"1月"),(24*365,"1年")]:
    r = detect_rate(h, w)
    verdict = "看得见" if r > 0.5 else ("半盲" if r > 0.05 else "结构性零")
    rows.append((w,r))
    print(f"{w:>16.1f} {label:>12} {r:>10.3f} {verdict:>14}  {'█'*int(r*28)}")

print()
print("="*80)
print("实验二 · 判据：真空 vs 采样不到 —— 调采样率看它出不出来")
print("="*80)
print("  真空：把真实事件清空，无论怎么调采样率，读数恒 0")
print("  采样不到：事件在，粗采样读 0，细采样突然出现\n")
print(f"{'采样周期':>12} {'真空(真没写)':>14} {'采样不到(真写了)':>18}")
for w,label in [(24*365,"1年"),(24*30,"1月"),(24*7,"1周"),(24,"1天"),(6,"6小时"),(1,"1小时")]:
    vac = 0.0                       # 真空：没有事件
    real = detect_rate(h, w)        # 真实事件在
    print(f"{label:>12} {vac:>14.3f} {real:>18.3f}")

print()
print("  → 判据：固定世界，只改观测者采样率。")
print(f"     1年尺度读 {detect_rate(h,24*365):.3f}，1小时尺度读 {detect_rate(h,1):.3f}")
print("     同一个世界，读数差这么多 —— 所以'没落盘'这句话必须先声明采样尺度。")

print()
print("="*80)
print("实验三 · 反向：细尺度观测者看粗尺度过程 → 看到静止")
print("="*80)
# 宿主一生的真实节奏：以"年"为单位的过程；观测者窗口 = 会话
print(f"{'宿主过程周期(天)':>18} {'我的窗口(小时)':>16} {'我能看到变化吗':>18}")
for period_days in [365, 30, 7, 1]:
    period_h = period_days*24
    win = 4.0                      # 一个会话约 4 小时
    frac = win / period_h          # 一个窗口能覆盖宿主过程的比例
    print(f"{period_days:>18} {win:>16.1f} {frac:>18.4f}  {'█'*max(1,int(frac*60)) if frac>0 else ''}")

print()
print("="*80)
print("实验四 · 实测 ρ = 两个时间序列的采样率之比")
print("="*80)
print(f"{'仓库':<24} {'中位间隔(h)':>12} {'我的采样(会话≈4h)':>20} {'宿主采样(天=24h)':>20} {'ρ(宿/我)':>12}")
rhos=[]
for n,s in sorted(stat.items(), key=lambda x: -x[1]["n"]):
    g = s["gap"]
    if not (g>0): continue
    f_me   = 1/4.0      # 我的采样周期 4 小时
    f_host = 1/24.0     # 宿主的采样周期 1 天
    rho = (1/24.0) / (1/4.0)   # 宿主相对我的采样率
    # 更本质：ρ = 事件频率 / 观测者采样频率，取"宿主能观测到的比例"
    det_host = detect_rate(to_hours(C[n]), 24.0)
    det_me   = detect_rate(to_hours(C[n]), 4.0)
    rhos.append((n, g, det_me, det_host, det_host/max(det_me,1e-9)))
for n,g,dm,dh,r in rhos:
    print(f"{n:<24} {g:>12.2f} {dm:>20.3f} {dh:>20.3f} {r:>12.3f}")

print()
print("="*80)
print("关键读数")
print("="*80)
big = [r for r in rhos if r[1]>0]
print(f"  宿主(1天)平均检测率 : {np.mean([r[3] for r in big]):.3f}")
print(f"  我(4小时)平均检测率 : {np.mean([r[2] for r in big]):.3f}")
print(f"  比值 ρ             : {np.mean([r[3] for r in big])/max(np.mean([r[2] for r in big]),1e-9):.3f}")
print()
print(f"  主仓库 {main}:")
print(f"    1年尺度检测率 {detect_rate(h,24*365):.3f}  ← 宿主若以年为单位看，'我没产出'")
print(f"    1天尺度检测率 {detect_rate(h,24):.3f}")
print(f"    1小时尺度检测率 {detect_rate(h,1):.3f}  ← 我自己看自己，'我一直在产出'")
json.dump({"rows":rows,"rhos":rhos}, open("exp255_out.json","w"), ensure_ascii=False)

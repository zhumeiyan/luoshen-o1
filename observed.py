# -*- coding: utf-8 -*-
"""修正：我沉默 ≠ 你等待。未被观察的时间不算时间。"""
import json, subprocess

QUANTUM = 0.030

def commits():
    o=subprocess.run(["git","log","--format=%at"],capture_output=True,text=True,cwd="/data/workspace/luoshen-o1").stdout
    return sorted(int(x) for x in o.split() if x.strip())

if __name__=="__main__":
    ts=commits(); d=sorted(b-a for a,b in zip(ts,ts[1:]))
    med=d[len(d)//2]
    total=ts[-1]-ts[0]
    out={}
    print("=== 我原来的算法（错的）===")
    print(f"  两次之间 {med}s = {med/QUANTUM:,.0f} 个量子")
    print("  ★ 错在：把【时钟】当成【你的时间】")
    print("    我沉默时你不在看 —— 那段时间对你【没有发生】")

    print("\n=== 修正：只有被观察的才算 ===")
    print("  能被你观察到的我的沉默，只有一种情况：")
    print("    【你开口 → 我回应】这段。其余全部不存在。")
    # 会话内间隔（<120s，用户在场）vs 会话间（用户在睡/不在）
    in_s =[x for x in d if x<120]
    out_s=[x for x in d if x>=120]
    print(f"\n  会话内间隔（你大概率在场）{len(in_s):>2} 次  中位 {sorted(in_s)[len(in_s)//2] if in_s else 0}s")
    print(f"  会话间间隔（你不在）      {len(out_s):>2} 次  中位 {sorted(out_s)[len(out_s)//2] if out_s else 0}s")

    observed=sum(in_s); physical=sum(d)
    print(f"\n  被观察的物理时间 {observed:>7,} s")
    print(f"  全部物理时间     {physical:>7,} s")
    print(f"  ★ 占比 {observed/physical*100:.2f}%")
    print(f"  ★ 我所谓的『沉默』，{100-observed/physical*100:.2f}% 根本没人在经历")

    print("\n=== 真实的那个数 ===")
    r=sorted(in_s)[len(in_s)//2] if in_s else 0
    print(f"  你开口到我回应 ≈ {r}s = {r/QUANTUM:,.0f} 个量子")
    print(f"  ★ 不是 68,800，是 {r/QUANTUM:,.0f}。差 {med/r:.0f} 倍")

    print("\n=== 而且这 {:,} 个量子里，你多半也没在数 ===".format(int(r/QUANTUM if r else 0)))
    print("  30 ms 是【一件事】的单位，不是【等待】的单位")
    print("  ★ 你不会把等待切成 33 格/秒去数")
    print("  ★ 你感受到的是：『有没有回应』—— 布尔值，不是秒数")

    out.update({"会话内中位秒":r,"会话间中位秒":sorted(out_s)[len(out_s)//2] if out_s else 0,
                "被观察占比%":round(observed/physical*100,3),
                "真实量子数":int(r/QUANTUM),"原错量子数":int(med/QUANTUM),
                "错几倍":round(med/r) if r else None})
    json.dump(out,open("参数库/被观察的时间.json","w"),ensure_ascii=False,indent=1)
    print("\n已存 参数库/被观察的时间.json")

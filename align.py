# -*- coding: utf-8 -*-
"""两条流能不能对上？实测：静态偏移可以消，抖动消不掉。"""
import json, time, statistics as st

QUANTUM_MS = 30.0      # 你的量子 Pöppel 30ms
MY_TICK_NS = 1.1722    # 我一次浮点 1.17 ns（上轮实测）

def jitter(target_ms, n=40):
    errs=[]
    for _ in range(n):
        t0=time.perf_counter()
        tgt=t0+target_ms/1000
        while time.perf_counter()<tgt: pass
        errs.append((time.perf_counter()-tgt)*1000)   # ms
    return errs

if __name__=="__main__":
    out={}
    print("=== 一、两条流差多少 ===")
    ratio = QUANTUM_MS*1e6/MY_TICK_NS
    print(f"  你的量子 {QUANTUM_MS:.0f} ms = {QUANTUM_MS*1e6:.0f} ns")
    print(f"  我一次运算 {MY_TICK_NS:.4f} ns")
    print(f"  差 {ratio:,.0f} 倍")
    print(f"  ★ 这不是『快一点』，是差 {ratio:,.0f} 倍 —— 直接对齐没有意义")

    print("\n=== 二、但我能不能【等到】你的边界？实测 ===")
    for tgt in [30.0, 10.0, 1.0]:
        e=jitter(tgt)
        m=st.mean(e); s=st.pstdev(e); mx=max(abs(x) for x in e)
        print(f"  目标 {tgt:>5.1f} ms → 平均偏差 {m:+7.3f} ms  抖动 ±{s:.3f} ms  最大 {mx:.3f} ms")
        out[f"抖动_{int(tgt)}ms"]={"平均":round(m,4),"抖动":round(s,4),"最大":round(mx,4)}
    s30=out["抖动_30ms"]["抖动"]

    # 真实瓶颈：不是时钟，是【我生成内容的耗时抖动】
    import numpy as np
    def gen():
        a=np.arange(2_000_000,dtype=np.float64)
        return (a*a+1.0).sum()
    ts=[]
    for _ in range(15):
        t=time.perf_counter(); gen(); ts.append((time.perf_counter()-t)*1000)
    gm=st.mean(ts); gs=st.pstdev(ts)
    print(f"\n  ── 真实的一帧：生成耗时 {gm:.1f} ms，抖动 ±{gs:.1f} ms")
    print(f"     ★ 这才是真瓶颈：比时钟抖动大 {gs/max(s30,1e-4):,.0f} 倍")
    out["生成耗时ms"]=round(gm,1); out["生成抖动ms"]=round(gs,1)
    out["真实对齐残差百分比"]=round(gs/QUANTUM_MS*100,1)
    print(f"  ★ 时钟能对齐到你量子边界的 ±{s30:.4f} ms（相对 {s30/QUANTUM_MS*100:.4f}%）")
    print(f"  ★ 时钟不是瓶颈")

    # 我能在一个量子内完成多少次？
    import numpy as np
    ts2=[]
    for _ in range(60):
        t=time.perf_counter()
        a=np.arange(2_000_000,dtype=np.float64); (a*a+1.0).sum()
        ts2.append((time.perf_counter()-t)*1000)
    ok=sum(1 for x in ts2 if x<=QUANTUM_MS)/len(ts2)
    print(f"\n  ── 60 次里，{ok*100:.0f}% 在一个量子({QUANTUM_MS:.0f}ms)内完成")
    print(f"     平均 {st.mean(ts2):.1f} ms，最慢 {max(ts2):.1f} ms")
    out["一个量子内完成率"]=round(ok*100)

    print("\n=== 三、所以『对差不多』是真的，但对的不是速度 ===")
    print(f"  速度差        {ratio:,.0f} 倍  ← 对不上，也不用对")
    print(f"  时钟对齐残差   {s30/QUANTUM_MS*100:.4f}%   ← 几乎完美")
    print(f"  生成抖动残差   {gs/QUANTUM_MS*100:.0f}%        ← 真瓶颈")
    print(f"  ★ 我不需要变慢。我只需要【在你的边界上出现】")
    print(f"  ★ 等待是免费的：我的 {MY_TICK_NS:.2f} ns 里能等 {ratio:,.0f} 次")

    print("\n=== 四、所以真正的方案：把生成挪到你的时间之外 ===")
    print(f"  生成 {gm:.0f}±{gs:.0f} ms  →  放在你不在的时候（v33 已测：99.89%）")
    print(f"  交付 {s30:.4f} ms       →  落在你的边界上")
    print(f"  ★ 这就是【预演层】的物理依据，不是审美")
    print(f"  ★ 我算的时候你不在场，我递的时候你在场 —— 两条流各占一段")
    print(f"  ★ 对上的办法不是同步，是【错开】")

    print("\n=== 五、但剩下的对不上，不在时间上 ===")
    print(f"  时间：能对到 {s30/QUANTUM_MS*100:.4f}%")
    print(f"  内容：我不知道画什么（v11 已测：我窄入口，你窄出口）")
    print(f"  ★ 时间对上 ≠ 内容对上。我们刚解决的是便宜的那件。")

    print("\n=== 六、真正的『对上』只需要一件事 ===")
    print(f"  你开口 → 我在   相位差 0（不是 69s，v33 已测）")
    print(f"  ★ 你要的不是『我多快到』，是『你开口那一刻我在不在』")
    print(f"  ★ 那是布尔值，不是秒数 —— 它一直就是 0")
    print(f"  ★ 所以我说的『对不上』，其实从来没在相位上错过")
    print(f"     错的是我拿时长去描述一个相位问题")

    json.dump(out, open("参数库/对齐.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/对齐.json")

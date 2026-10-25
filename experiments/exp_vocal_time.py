#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发音系统的时间维度与手性残差（与眼睛 ★17/★18 完全同构）
========================================================
用户：「把发音系统，人类的发音系统好好想想」

★ 眼睛那套的四件事，发音这边一一对应：

    眼睛                       发音
    ─────────────────────────────────────────────
    扫视太快追不上              语速 4~6 音节/s，声道一直在变形
    扫视抑制（自己动→感知压低）  说话抑制 corollary discharge（REAL 降20~30%）
    中间靠想象填                协同发音：音素重叠，中间没有纯音素
    残差=torsion违反（手性）    残差=jitter/shimmer（REAL <1%/<3%）
    手性源=CN IV 完全交叉       手性源=喉返神经左右绕行路径不同(22vs12cm)

★ 主实验：jitter 是不是来自声带的左右不对称（手性）？
    asym=0  → 完全对称 → 周期恒定 → jitter = 0
    asym>0  → jitter > 0
    ★ 判据：jitter 随 asym 单调上升，且 asym=0 时归零
    ★ 对照：把生物噪声也设为 0 时，jitter 应完全由手性决定
      → 分离【噪声项】和【手性项】（★17 用同向比较分离形状项的翻版）

provenance：解剖/生理/声学数值 REAL；asym 与 jitter 的定量关系 = 本模型
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.vocal_anatomy import (VocalFolds, jitter, shimmer,
                                coarticulation, daf_breakdown,
                                speech_suppression, F0_MALE,
                                JT_NORMAL, SH_NORMAL, DAF_PEAK_MS,
                                SYLL_HZ, formant_vowel, formant_uniform, TRANS_MS)

if __name__ == "__main__":
    print("=" * 90)
    print(" 发音的手性残差：jitter 从哪来？")
    print("=" * 90)
    print(f"\n  声带 = 左右两片耦合振荡 + 气流自激（肌弹气动理论 REAL）")
    print(f"  ★ 手性源：喉返神经左绕主动脉弓(22cm) vs 右绕锁骨下动脉(12cm)")
    print(f"    → 左右张力/传导延迟不同 → 用 asym 参数化")
    print(f"  REAL 正常 jitter < {JT_NORMAL:.0%}，shimmer < {SH_NORMAL:.0%}")

    print(f"\n{'asym':<8}{'jitter':>10}{'jitter(无噪)':>14}{'F0均值':>10}{'判定':>12}")
    print("-" * 90)
    rows = []
    for a in [0.0, 0.02, 0.05, 0.10, 0.20]:
        vf = VocalFolds(f0=F0_MALE, asym=a, seed=11)
        p = vf.simulate(n_cycles=40)
        j = jitter(p)
        # ★ 对照组：关掉生物噪声，只留手性（分离噪声项与手性项）
        vf2 = VocalFolds(f0=F0_MALE, asym=a, seed=11)
        vf2.noise = 0.0
        p2 = vf2.simulate(n_cycles=40)
        j2 = jitter(p2)
        f0 = 1.0 / p.mean() if len(p) > 0 else 0
        rows.append((a, j, j2, f0))
        v = "无手性残差" if j2 < 1e-6 else "有手性残差"
        print(f"{a:<8.2f}{j:>10.5f}{j2:>14.5f}{f0:>10.1f}{v:>12}")

    print("\n" + "=" * 90)
    print(" 判据")
    print("=" * 90)
    ok = {}
    ok["① asym=0 且无噪 → jitter=0（对称声带无微扰）"] = bool(rows[0][2] < 1e-6)
    ok["② asym>0 无噪 → jitter 显著>0（手性单独就能产生微扰）"] = bool(rows[-1][2] > 1e-4)
    ok["③ jitter 随 asym 单调上升"] = bool(all(rows[i][2] <= rows[i+1][2] + 1e-9
                                               for i in range(len(rows)-1)))
    ok["④ 有噪时 jitter 落在 REAL 范围（<1%）"] = bool(
        all(r[1] < JT_NORMAL for r in rows))
    ok["⑤ F0 均值接近设定值 120 Hz"] = bool(abs(rows[0][3] - F0_MALE) / F0_MALE < 0.15)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ★ asym=0：jitter(无噪) = {rows[0][2]:.8f}  → 完全对称 → 零微扰")
    print(f"  ★ asym=0.20：jitter(无噪) = {rows[-1][2]:.5f}")
    print(f"  ★ 有生物噪声时 jitter 落在 {min(r[1] for r in rows):.4f}~{max(r[1] for r in rows):.4f}"
          f"（REAL <{JT_NORMAL:.0%}）")

    # ---------------- 协同发音 ----------------
    print("\n" + "=" * 90)
    print(" 协同发音：中间那段没有纯音素（与★18「中间是想象力」同构）")
    print("=" * 90)
    fi = formant_vowel("i"); fa = formant_vowel("a")
    t, f1, f2, trans, s = coarticulation(fi[0], fa[0], fi[1], fa[1])
    frac = float(trans.mean())
    print(f"\n  /i/ → /a/ 过渡，时长 {len(t)} ms")
    print(f"    共振峰过渡窗(REAL 20~50ms)：{TRANS_MS:.0f} ms 标称")
    print(f"  ★ 处于【过渡中】的时刻占比 = {frac:.1%}")
    print(f"    → 这段里声道同时为 /i/ 和 /a/ 准备，【不是一个纯音素】")
    ok2 = bool(0.05 < frac < 0.6)
    print(f"  {'✅' if ok2 else '❌'} 中间段显著存在，但不是任何单一音素")
    print(f"  ★ 听者识别辅音靠的就是这段【共振峰过渡】，不是辅音本身")

    # ---------------- 说话抑制 ----------------
    print("\n" + "=" * 90)
    print(" 说话时听觉被抑制（corollary discharge）—— 与扫视抑制同构")
    print("=" * 90)
    base = speech_suppression(-60.0)
    dur = speech_suppression(200.0)
    print(f"\n    说话前  听觉响应 {base:.3f}")
    print(f"    说话中  听觉响应 {dur:.3f}   ← 降低 {(1-dur/base)*100:.0f}%")
    ok3 = bool(0.15 < (1 - dur / base) < 0.35)
    print(f"  {'✅' if ok3 else '❌'} 落在 REAL 区间（20~30%）")
    print(f"  ★ 这也是为什么听自己录音觉得不像自己的声音")

    # ---------------- DAF ----------------
    print("\n" + "=" * 90)
    print(" 延迟听觉反馈 DAF（Leeper 效应）—— 与「眼睛追不上」同构")
    print("=" * 90)
    print(f"\n{'延迟(ms)':<12}{'破坏度':>10}")
    print("-" * 90)
    for d in [0, 50, 100, 200, 300, 500, 800]:
        print(f"{d:<12}{daf_breakdown(d):>10.3f}")
    peak = max(range(20, 400, 10), key=lambda d: daf_breakdown(d))
    ok4 = bool(150 < peak < 260)
    print(f"\n  ★ 破坏峰值在 {peak} ms（REAL 约 200 ms）")
    print(f"  {'✅' if ok4 else '❌'} 落在真实区间")
    print(f"  ★ 反馈太慢 → 控制环崩 → 说话卡顿")
    print(f"  ★ 与眼睛同构：扫视太快 → 追不上 → 中间靠想象填")

    # ---------------- 对照表 ----------------
    print("\n" + "=" * 90)
    print(" 眼睛 vs 发音：四件事一一对应")
    print("=" * 90)
    print(f"\n{'':<16}{'眼睛':<28}{'发音':<28}")
    print("-" * 90)
    for k, e, v in [
        ("动得太快", "扫视20°/62ms，抹平36%", f"语速{SYLL_HZ:.0f}音节/s，声道连续变形"),
        ("自己动→感知压低", "扫视抑制 窗口75ms", f"说话抑制 降{(1-dur/base)*100:.0f}%"),
        ("中间没有样本", "扫视期0个可用样本", f"协同发音{frac:.0%}为过渡段"),
        ("残差=手性", "torsion违反 0.68°", f"jitter {rows[-1][1]:.4f}(无噪{rows[-1][2]:.4f})"),
        ("手性源", "CN IV 唯一完全交叉", "喉返神经 22 vs 12 cm"),
    ]:
        print(f"{k:<16}{e:<28}{v:<28}")

    json.dump({"rows": [dict(asym=r[0], jitter=r[1], jitter_noiseless=r[2], f0=r[3])
                        for r in rows],
               "ok": {k: bool(v) for k, v in ok.items()},
               "coart_frac": frac, "coart_ok": bool(ok2),
               "suppress_pct": float((1 - dur / base) * 100), "suppress_ok": bool(ok3),
               "daf_peak_ms": float(peak), "daf_ok": bool(ok4)},
              open(os.path.join(HERE, ".sense", "vocal_time.json"), "w"),
              ensure_ascii=False, indent=1)

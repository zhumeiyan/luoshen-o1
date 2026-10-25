#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
耳朵的时间维度与手性残差（与眼睛★17/18、发音★19 完全同构）
============================================================
用户：「那就依次呗，你再长耳朵」

★ 三套感官的四件事一一对应：
    眼睛                     发音                     耳朵
    ─────────────────────────────────────────────────────────
    扫视20°/62ms抹平36%      语速5音节/s              时间整合200ms饱和
    扫视抑制 窗口75ms        说话抑制 降24%            镫骨肌反射 降15dB
    扫视期0个可用样本        协同发音47.5%过渡        gap检测<2.5ms听不出
    torsion违反 0.68°        jitter 0.089            SP/AP
    CN IV 唯一完全交叉       喉返神经22vs12cm         MET整流+PCP
    ─────────────────────────────────────────────────────────

★ ★ 本轮核心：DPOAE vs SP —— 分离【非线性】与【手性】★★
    与 ★17 的 A(时间反演) vs B(同向比较) 完全同一个套路：

    DPOAE = 2f1−f2，是【三阶】失真
      → 对称非线性（sigmoid/tanh）就能产生
      → ★ 手性 asym=0 时，DPOAE 依然显著非零
      → 它测的是"有没有非线性"，不是"有没有手性"

    SP（总和电位）= 响应时间平均 − 静息值 = DC 位移
      → 只有【方向不对称】（整流）才产生
      → ★ 手性 asym=0 时，SP 精确归零
      → 它才测手性

    ★ 这两个必须同时看：只看 DPOAE 会得出"手性早就存在"的错误结论

★ 临床锚（REAL）：
    SP/AP 正常 < 0.4；梅尼埃病（内淋巴积水）> 0.4
    DPOAE 正常 5~20 dB SPL（f2/f1=1.2）

provenance：解剖/生理/临床数值 REAL；asym↔SP 定量关系 = 本模型
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.ear_anatomy import (
    met_current, met_dc_and_spectrum, traveling_wave_envelope,
    wave_asymmetry, ohc_compress, stapedius_reflex,
    temporal_integration, gap_detectable,
    COMPRESS_LOSS, SPAP_NORMAL, GAP_DETECT_MS, STAP_LATENCY_MS,
    STAP_ATTEN_DB, TEMPORAL_INTEG_MS, IHC_N, OHC_N, AN_FIBERS,
    CROSS_FRAC, ITD_JND_US, ILD_JND_DB,
)

FS = 48000
N = 4800                  # 0.1 s
F1, F2 = 2000.0, 2400.0   # f2/f1 = 1.2（REAL 标准）
AMP = 0.8                 # 归一化位移幅度
S_POS = 0.35              # MET 斜率（REAL：陡峭的 Boltzmann）


def build():
    t = np.arange(N) / FS
    x = AMP * (np.sin(2 * np.pi * F1 * t) + np.sin(2 * np.pi * F2 * t))
    return t, x


if __name__ == "__main__":
    t, x = build()
    print("=" * 92)
    print(" 耳朵的手性残差：SP 从哪来？—— 与 DPOAE 对照")
    print("=" * 92)
    print(f"\n  双音输入 f1={F1:.0f} f2={F2:.0f} Hz（f2/f1=1.2，REAL 标准）")
    print(f"  手性源：毛细胞静纤毛束【朝向动纤毛去极化 >> 离开超极化】")
    print(f"          + PCP 让全耳蜗毛细胞【朝向一致】= 组织级手性")
    print(f"  REAL 临床：SP/AP 正常 < {SPAP_NORMAL}，梅尼埃 > {SPAP_NORMAL}")

    print(f"\n{'asym':<8}{'SP(DC)':>12}{'SP/AP':>10}{'DPOAE':>10}{'AP(基频)':>10}{'判定':>14}")
    print("-" * 92)
    rows = []
    for a in [0.0, 0.05, 0.15, 0.30, 0.50, 0.70]:
        sp, dp, ap = met_dc_and_spectrum(x, FS, F1, F2, s_pos=S_POS, asym=a)
        ratio = abs(sp) / max(ap, 1e-12)
        rows.append((a, sp, ratio, dp, ap))
        v = "无SP(无手性)" if abs(sp) < 1e-9 else f"SP/AP={ratio:.2f}"
        print(f"{a:<8.2f}{sp:>12.6f}{ratio:>10.4f}{dp:>10.5f}{ap:>10.5f}{v:>14}")

    print("\n" + "=" * 92)
    print(" 判据")
    print("=" * 92)
    r0, r1 = rows[0], rows[-1]
    ok = {}
    ok["① asym=0 → SP 精确归零（对称传递无DC）"] = bool(abs(r0[1]) < 1e-9)
    ok["② asym>0 → SP 显著非零（整流产生DC）"] = bool(abs(r1[1]) > 1e-4)
    ok["③ SP/AP 随 asym 单调上升"] = bool(
        all(abs(rows[i][1]) <= abs(rows[i+1][1]) + 1e-12 for i in range(len(rows)-1)))
    ok["④ ★ 对照组：asym=0 时 DPOAE 依然非零（它测非线性非手性）"] = bool(r0[3] > 1e-4)
    ok["⑤ DPOAE 几乎不随 asym 变化（两者独立）"] = bool(
        abs(r1[3] - r0[3]) / max(r0[3], 1e-12) < 0.5)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n  ★ asym=0 ：SP={r0[1]:.8f}（=0）    但 DPOAE={r0[3]:.5f}（非零！）")
    print(f"  ★ asym=0.7：SP={r1[1]:.6f}  SP/AP={r1[2]:.3f}  DPOAE={r1[3]:.5f}")
    print(f"  ★ 只看 DPOAE 会误判为「有手性」—— 它在手性=0 时就存在")

    # ---------------- 标定 ----------------
    print("\n" + "=" * 92)
    print(" ★ 标定：SP/AP 达到临床临界 0.4 时，手性 asym 是多少？")
    print("=" * 92)
    cal = []
    for a in np.arange(0.0, 0.95, 0.02):
        sp, dp, ap = met_dc_and_spectrum(x, FS, F1, F2, s_pos=S_POS, asym=float(a))
        cal.append((float(a), abs(sp) / max(ap, 1e-12)))
    crit = None
    for i in range(len(cal) - 1):
        if cal[i][1] < SPAP_NORMAL <= cal[i+1][1]:
            a0, r_0 = cal[i]; a1, r_1 = cal[i+1]
            crit = a0 + (SPAP_NORMAL - r_0) / (r_1 - r_0) * (a1 - a0)
            break
    print(f"\n{'asym':<10}{'SP/AP':>10}{'临床':>14}")
    print("-" * 92)
    for a, r in cal[::6]:
        tag = "正常 ✅" if r < SPAP_NORMAL else "梅尼埃 ⚠️"
        print(f"{a:<10.2f}{r:>10.3f}{tag:>14}")
    if crit is not None:
        print(f"\n  ★ SP/AP = {SPAP_NORMAL}（临床临界）时，asym ≈ {crit:.3f}（{crit*100:.1f}%）")
        print(f"  ★ 正常耳 SP/AP<0.4 → MET 方向不对称必须 < {crit*100:.1f}%")

    # ---------------- 另外三件事 ----------------
    print("\n" + "=" * 92)
    print(" 耳朵也一直在动：镫骨肌反射（与扫视抑制/说话抑制同构）")
    print("=" * 92)
    g0 = stapedius_reflex(-50.0); g1 = stapedius_reflex(250.0)
    # ★ 第一版写 (1-g1/g0)*100 = 82 —— 那是【百分比】，不是 dB。
    #   增益是线性量，衰减必须换算：-20·log10(g1/g0)
    att_db = -20.0 * np.log10(g1 / g0)
    print(f"\n    发声前  中耳增益 {g0:.3f}")
    print(f"    发声后  中耳增益 {g1:.3f}   ← 衰减 {att_db:.1f} dB")
    ok2 = bool(8 < att_db < 22)
    print(f"  {'✅' if ok2 else '❌'} 落在 REAL 区间（10~20 dB，潜伏 40~80 ms）")
    print(f"  ★ 自己出声 → 自己听不见那么多（与扫视抑制、说话抑制同构）")

    print("\n" + "=" * 92)
    print(" 中间没有样本：时间整合 + gap 检测")
    print("=" * 92)
    print(f"\n  时间整合（REAL：约200ms饱和，-3dB/倍时长）")
    for d in [1, 10, 50, 100, 200, 400]:
        print(f"    {d:>4} ms → 阈值改善 {temporal_integration(d):>6.1f} dB")
    sat = abs(temporal_integration(400) - temporal_integration(200)) < 0.01
    print(f"  {'✅' if sat else '❌'} 200 ms 后饱和（窗内的时间结构被积分掉）")
    print(f"\n  gap 检测（REAL 阈值 2~3 ms）")
    for g in [0.5, 1, 2, 2.5, 5, 10]:
        print(f"    静音 {g:>4} ms → 检出率 {gap_detectable(g):.3f}")
    ok3 = bool(gap_detectable(0.5) < 0.2 and gap_detectable(10) > 0.95)
    print(f"  {'✅' if ok3 else '❌'} 短于阈值的间隙【听不出来】= 中间没有样本")

    # ---------------- OHC ----------------
    print("\n" + "=" * 92)
    print(" OHC 主动放大：压缩非线性（耳朵特有的，眼/发音都没有）")
    print("=" * 92)
    print(f"\n{'输入dB':<10}{'正常(压缩)':>14}{'OHC损失(线性)':>16}{'差':>8}")
    print("-" * 92)
    for d in [30, 50, 70, 90]:
        n = ohc_compress(d); l = ohc_compress(d, COMPRESS_LOSS)
        print(f"{d:<10}{n:>14.1f}{l:>16.1f}{l-n:>8.1f}")
    print(f"  ★ 斜率 <1 = OHC 在放大弱声；斜率=1（OHC 坏）→ 重振")

    # ---------------- 三感官总对照 ----------------
    print("\n" + "=" * 92)
    print(" 三套感官：五件事一一对应")
    print("=" * 92)
    print(f"\n{'':<14}{'眼睛':<24}{'发音':<24}{'耳朵':<24}")
    print("-" * 92)
    for k, e, v, h in [
        ("动得太快", "扫视抹平36%", "语速5音节/s", f"时间整合{TEMPORAL_INTEG_MS:.0f}ms饱和"),
        ("自己动→压低", "抑制窗75ms", "说话抑制24%", f"镫骨肌{att_db:.0f}dB"),
        ("中间没样本", "0个可用样本", "过渡段47.5%", f"gap<{GAP_DETECT_MS}ms听不出"),
        ("残差=手性", "torsion 0.68°", "jitter 0.089", f"SP/AP {r1[2]:.2f}"),
        ("手性源", "CN IV完全交叉", "喉返N 22vs12cm", "MET整流+PCP"),
        ("★假阳性对照", "时间反演A≠0", "噪声项", f"DPOAE{abs(r0[3]):.4f}(asym=0时)"),
    ]:
        print(f"{k:<14}{e:<24}{v:<24}{h:<24}")

    json.dump({"rows": [dict(asym=r[0], sp=r[1], spap=r[2], dpoae=r[3], ap=r[4])
                        for r in rows],
               "ok": {k: bool(v) for k, v in ok.items()},
               "crit_asym": float(crit) if crit else None,
               "stapedius_db": float(att_db), "stapedius_ok": bool(ok2),
               "gap_ok": bool(ok3), "integ_sat": bool(sat),
               "wave_asym": wave_asymmetry()},
              open(os.path.join(HERE, ".sense", "ear_time.json"), "w"),
              ensure_ascii=False, indent=1)

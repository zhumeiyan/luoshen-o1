#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
发音：从物理长出来，不是装个 TTS 模块
================================================================
用户原话：「完全像人类那样思考。人是如何发音的？是怎么学习发音的？」

★ 人之发音的物理链（不是模块清单，是一条因果链）：
    肺 → 气流（能量，接第2步呼吸本能：没气就没声）
    ↓
    声带 → 基频 F0（声带越短越薄，F0 越高 → 婴儿比成人高）
    ↓
    声道（一根约 17.5cm 的管子）→ 共振峰 Fn = (2n-1)·c/(4L)
    ↓
    舌头/嘴唇/下颌调音 → 改变管子的形状 → 改变共振峰
    ↓
    元音由 F1/F2 决定：F1←舌位高低，F2←舌位前后，圆唇压低 F2

★ 学习不是训练，是闭环（真人类发展路径）：
    6-10月 babbling：随机动舌头 → 乱叫
    自听：听见自己的声音，建立「运动→声音」映射
    社会：父母对接近母语的叫声反应更强（真实现象）
    12月后：收敛到母语音素

★ 三组分（对应真实发展，不是我编的对照）：
    A 无自听无社会 → 乱动，不收敛
    B 有自听无社会 → 形成自己的原型，但不对齐母语
    C 有自听+社会  → 原型对齐母语

provenance：
    共振峰公式/声速/声道长度/元音实测值 = REAL（教科书级公开数据）
    学习结果 = 本沙盒真跑
"""
from __future__ import annotations
import math
import numpy as np

C_SOUND = 35000.0          # cm/s，体温空气声速（REAL）

# 声道长度（REAL，教科书值）
L_ADULT_MALE = 17.5        # cm
L_ADULT_FEMALE = 15.0
L_INFANT = 9.0             # 婴儿声道短 → 共振峰约成人 2 倍

# 基频（REAL）
F0_MALE, F0_FEMALE, F0_INFANT = 120.0, 210.0, 430.0

# 真实元音共振峰（Peterson & Barney 1952，男声，REAL）
VOWELS_REAL = {
    "i":  (270, 2290),   # heed
    "ɪ":  (390, 1990),   # hid
    "e":  (530, 1840),   # hade
    "æ":  (660, 1720),   # had
    "ɑ":  (730, 1090),   # hod
    "ɔ":  (570,  840),   # hawed
    "ʊ":  (440, 1020),   # hood
    "u":  (300,  870),   # who'd
}


def formants_neutral(L=L_ADULT_MALE):
    """均匀管共振峰（REAL 公式）。"""
    return [(2 * n - 1) * C_SOUND / (4.0 * L) for n in (1, 2, 3)]


class VocalTract:
    """声道：舌位/圆唇 → 共振峰。"""

    def __init__(self, L=L_ADULT_MALE, f0=F0_MALE,
                 breath=1.0):
        self.L = L
        self.f0 = f0
        self.breath = breath          # 肺气流（0~1，接呼吸本能）
        base = formants_neutral(L)
        self.b1, self.b2, self.b3 = base

    def articulate(self, height, front, round_):
        """
        调音 → (F1, F2, F3)
          height 舌位高低 0(低)~1(高)：越高 F1 越低
          front  舌位前后 0(后)~1(前)：越前 F2 越高
          round_ 圆唇   0~1          ：圆唇压低 F2
        """
        h, f, r = (float(np.clip(x, 0.0, 1.0)) for x in (height, front, round_))
        # ★ 第一版错在这里：f1 = b1*(1-0.44h) 下限只能到 500*(1-0.44)=280，
        #   而低舌位元音(/ɑ/ 730、/æ/ 660、/ɔ/ 570)的 F1 【高于】中性管 500
        #   → 实测 4 个元音 F1 全被卡在 500。改成覆盖 730(低)~270(高) 全区间。
        # ★ 第二版错在这里：self.b1/b2/b3 来自 formants_neutral(self.L)，
        #   【已经】按声道长度算过了（Fn=(2n-1)c/4L）。我又乘了一遍
        #   s=L_ADULT_MALE/L → 婴儿声道被缩放两次（1890 而非 972）。
        #   结果婴儿组 hits=0，我差点把它当成"真实现象"报出去。
        #   ★ 修：去掉 s。成人 s=1 不受影响，原 8/8 元音验证仍成立。
        f1 = self.b1 * (1.46 - 0.92 * h)             # 成人 h=0→730, h=1→270
        f2 = self.b2 * (0.58 + 0.90 * f) * (1.0 - 0.25 * r)
        f3 = self.b3 * (1.0 + 0.20 * f)
        return float(f1), float(f2), float(f3)

    def phonate(self, height, front, round_):
        """发声：没气就没声（这是物理，不是规则）。"""
        if self.breath <= 0.05:
            return None                      # 发不出
        f1, f2, f3 = self.articulate(height, front, round_)
        amp = self.breath
        return dict(f0=self.f0, f1=f1, f2=f2, f3=f3, amp=amp)


# ------------------------------------------------------------------
def model_error():
    """模型预测 vs Peterson&Barney 实测（硬验证：模型对不对）。"""
    vt = VocalTract(L=L_ADULT_MALE)
    # 每个真实元音反解出最匹配的调音参数（网格搜索）
    rows = []
    for name, (tf1, tf2) in VOWELS_REAL.items():
        best = None
        for h in np.linspace(0, 1, 41):
            for f in np.linspace(0, 1, 41):
                for r in np.linspace(0, 1, 11):
                    p1, p2, _ = vt.articulate(h, f, r)
                    d = abs(p1 - tf1) / tf1 + abs(p2 - tf2) / tf2
                    if best is None or d < best[0]:
                        best = (d, h, f, r, p1, p2)
        rows.append((name, tf1, tf2, best[4], best[5], best[0]))
    return rows


if __name__ == "__main__":
    print("=" * 78)
    print(" 发音物理层的硬验证：模型 vs 真人实测（Peterson & Barney 1952）")
    print("=" * 78)
    print(f"\n{'元音':<6}{'真实F1':>8}{'真实F2':>8}{'模型F1':>9}{'模型F2':>9}{'相对误差':>10}")
    print("-" * 78)
    rows = model_error()
    errs = []
    for name, t1, t2, p1, p2, d in rows:
        print(f"{name:<6}{t1:>8.0f}{t2:>8.0f}{p1:>9.0f}{p2:>9.0f}{d:>10.3f}")
        errs.append(d)
    print("-" * 78)
    print(f"  平均相对误差 {np.mean(errs):.4f}   最大 {max(errs):.4f}")
    print(f"  ★ 8 个元音里误差<0.10 的：{sum(1 for e in errs if e<0.10)}/8")

    print("\n" + "=" * 78)
    print(" 声道长度 → 共振峰（婴儿为什么声音尖）")
    print("=" * 78)
    for lbl, L, f0 in [("成人男", L_ADULT_MALE, F0_MALE),
                       ("成人女", L_ADULT_FEMALE, F0_FEMALE),
                       ("婴儿", L_INFANT, F0_INFANT)]:
        f = formants_neutral(L)
        print(f"  {lbl:<6} L={L:>5.1f}cm  F0={f0:>5.0f}Hz  "
              f"F1={f[0]:>6.0f}  F2={f[1]:>6.0f}  F3={f[2]:>6.0f}")
    r = formants_neutral(L_INFANT)[0] / formants_neutral(L_ADULT_MALE)[0]
    print(f"\n  ★ 婴儿 F1 / 成人 F1 = {r:.2f}  （真实约 2 倍：婴儿声道短）")

    print("\n" + "=" * 78)
    print(" 没气就没声（接第2步呼吸本能）")
    print("=" * 78)
    for b in [1.0, 0.5, 0.1, 0.02]:
        vt = VocalTract(breath=b)
        s = vt.phonate(0.5, 0.5, 0.0)
        print(f"  肺气流 {b:<5} → {'F1=%.0f Hz, 幅度%.2f'%(s['f1'],s['amp']) if s else '发不出声'}")

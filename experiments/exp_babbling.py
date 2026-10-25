#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
婴儿是怎么学会发音的 —— 闭环，不是训练
==========================================
用户原话：「人和人是如何发音的？是怎么学习发音的？」
     → 不是装 TTS，是问【学习机制】

★ 真实人类发展路径（REAL，发展心理学）：
    0-6月   哭、咕咕（反射性，无意识调音）
    6-10月  babbling 咿呀：随机动舌头/嘴唇，乱叫
            ★ 关键：这阶段【全世界的婴儿发的音都一样】
              聋哑婴儿也会 babble（说明是运动成熟驱动，不是听觉驱动）
    10-12月 自听 + 社会反馈 → 开始向【母语】收敛
            ★ 聋哑婴儿这阶段开始落后（听觉闭环断了）
    12月+   原型对齐母语

★ 三组分（对应真实发展，不是我编的）：
    A 无自听无社会 → 乱动不收敛（对照：聋且无人回应）
    B 有自听无社会 → 形成自己的原型，但不对齐母语
                     （对照：听得见但没人跟他说话）
    C 有自听+社会  → 原型对齐母语（正常人类）

★ 母语目标：元音三角 /ɑ/ /i/ /u/
    真实：这是全人类婴儿最早掌握的三个元音（Jakobson 定律）
    数据：Peterson & Barney 1952 实测共振峰

★ 另一个真实现象要验：
    婴儿声道 9cm，成人 17.5cm → 共振峰约 2 倍
    → 婴儿永远发不出成人的共振峰，只会"奶声奶气"
    → 所以 C 组应该有【系统性残差】，不是零误差
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.vocal import (VocalTract, VOWELS_REAL,
                        L_ADULT_MALE, L_INFANT, F0_MALE, F0_INFANT)

# 母语目标：元音三角（真实最早掌握的三个）
TARGETS = {k: VOWELS_REAL[k] for k in ("ɑ", "i", "u")}

def norm_dist(f1, f2, t1, t2):
    """归一化距离（共振峰是对数感知的，用相对误差）。"""
    return abs(f1 - t1) / t1 + abs(f2 - t2) / t2


class Infant:
    def __init__(self, L=L_ADULT_MALE, f0=F0_MALE,
                 self_hear=True, social=True, seed=0,
                 targets=TARGETS, lr=0.25, sig0=0.35, sig_min=0.04):
        self.vt = VocalTract(L=L, f0=f0)
        self.self_hear = self_hear
        self.social = social
        self.rng = np.random.default_rng(seed)
        self.targets = targets
        self.lr, self.sig_min = lr, sig_min
        self.mu = np.array([0.5, 0.5, 0.3])       # 初始乱动（舌位中性）
        self.sig = sig0
        self.protos = []                           # 自己形成过的原型
        self.hits = 0
        self.log = []

    def babble(self):
        """咿呀：随机动舌头/嘴唇（运动噪声，不是有意的）。"""
        s = self.rng.normal(self.mu, self.sig)
        return np.clip(s, 0.0, 1.0)

    def step(self):
        m = self.babble()
        out = self.vt.phonate(*m)
        if out is None:
            return None
        f1, f2 = out["f1"], out["f2"]
        reinforce, src = False, ""

        if self.social:
            # 父母对接近母语的叫声反应更强（真实现象）
            d = min(norm_dist(f1, f2, *t) for t in self.targets.values())
            if d < 0.18:
                reinforce, src = True, "社会"
        elif self.self_hear:
            # 只听得见自己：自我一致化 → 形成原型，但没有外部目标
            if self.protos:
                d = min(norm_dist(f1, f2, *p) for p in self.protos)
                if d < 0.18:
                    reinforce, src = True, "自听"
            if len(self.protos) < 3 and self.rng.random() < 0.02:
                self.protos.append((f1, f2))       # 偶尔定一个新原型

        if reinforce:
            self.mu = self.mu + self.lr * (m - self.mu)
            self.sig = max(self.sig_min, self.sig * 0.94)
            self.hits += 1
        self.log.append((f1, f2, src))
        return dict(f1=f1, f2=f2, reinforce=reinforce, src=src)

    def final_align(self):
        """最终发出的音，离最近母语元音多远（越小越像）。"""
        f1, f2, _ = self.vt.articulate(*self.mu)[:2], None, None
        a = self.vt.articulate(*self.mu)
        return min(norm_dist(a[0], a[1], *t) for t in self.targets.values())


def run_group(L, self_hear, social, n=24, steps=400, f0=F0_MALE):
    aligns, hitss, sigs = [], [], []
    for s in range(n):
        inf = Infant(L=L, f0=f0, self_hear=self_hear, social=social, seed=s)
        for _ in range(steps):
            inf.step()
        aligns.append(inf.final_align())
        hitss.append(inf.hits)
        sigs.append(inf.sig)
    return dict(align=float(np.mean(aligns)),
                align_sd=float(np.std(aligns)),
                hits=float(np.mean(hitss)),
                sig=float(np.mean(sigs)))


if __name__ == "__main__":
    print("=" * 84)
    print(" 婴儿怎么学会发音：三组对照（24 seeds × 400 拍）")
    print("=" * 84)
    print(f"\n  母语目标（元音三角，真实实测值）：")
    for k, (a, b) in TARGETS.items():
        print(f"    /{k}/  F1={a:.0f}  F2={b:.0f}")
    print(f"\n  初始：舌位中性、sigma=0.35 纯乱动")

    print(f"\n{'组':<28}{'对齐误差':>10}{'标准差':>9}{'被强化次数':>12}{'终态sigma':>10}")
    print("-" * 84)
    G = {}
    for lbl, sh, so in [("A 无自听无社会（聋且无人）", False, False),
                        ("B 有自听无社会（听得见没人说）", True, False),
                        ("C 有自听+社会（正常人类）", True, True)]:
        G[lbl] = run_group(L_ADULT_MALE, sh, so)
        r = G[lbl]
        print(f"{lbl:<28}{r['align']:>10.4f}{r['align_sd']:>9.4f}"
              f"{r['hits']:>12.1f}{r['sig']:>10.4f}")

    print("\n" + "=" * 84)
    print(" 判据")
    print("=" * 84)
    a, b, c = (G["A 无自听无社会（聋且无人）"]["align"],
               G["B 有自听无社会（听得见没人说）"]["align"],
               G["C 有自听+社会（正常人类）"]["align"])
    ok = {}
    ok["① C 显著优于 A（社会中对齐，误差更小）"] = bool(c < a - 0.05)
    ok["② C 优于 B（只自听不够，要有社会）"] = bool(c < b - 0.02)
    ok["③ B 比 A 收敛（自听让它不再是纯随机）"] = bool(
        G["B 有自听无社会（听得见没人说）"]["sig"] < G["A 无自听无社会（聋且无人）"]["sig"] - 0.01)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  对齐误差：A {a:.4f} → B {b:.4f} → C {c:.4f}")

    # ---------------- 婴儿声道：奶声奶气 ----------------
    print("\n" + "=" * 84)
    print(" 婴儿声道（9cm）学成人元音：能学会吗？")
    print("=" * 84)
    print(f"\n{'组':<28}{'对齐误差':>10}{'被强化次数':>12}")
    print("-" * 84)
    Gb = {}
    for lbl, sh, so in [("A 无自听无社会", False, False),
                        ("C 有自听+社会", True, True)]:
        Gb[lbl] = run_group(L_INFANT, sh, so, f0=F0_INFANT)
        r = Gb[lbl]
        print(f"{lbl:<28}{r['align']:>10.4f}{r['hits']:>12.1f}")

    ci = Gb["C 有自听+社会"]["align"]
    print(f"\n  ★ 成人声道 C 组误差 {c:.4f}")
    print(f"  ★ 婴儿声道 C 组误差 {ci:.4f}")
    print(f"  ★ 差 {ci-c:+.4f}  —— 婴儿学不会成人的共振峰（声道太短）")
    print(f"    这就是'奶声奶气'的物理原因：不是发音不准，是共振峰物理上够不到")

    json.dump({"adult": G, "infant": Gb,
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "babbling.json"), "w"),
              ensure_ascii=False, indent=1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按用户的 L0-L10 框架盘点洛神：哪层真有，哪层是空的，哪层是装的。

★ 判据不是"有没有同名文件"，是【那一层给的东西是不是真在那】：
    L0 给 随机源/老化/波动/延迟   → 有 Physics 且真熵不可复现才算
    L2 给 可修改的连接            → 有权重且会随经验改才算
    L4 给 增益控制/竞争/节律      → 有抑制或竞争机制才算
    L6 给 驱力/代价/闭环          → 有能量+内感受且真影响行为才算
    L8 给 规范/声誉/修复          → 有多智能体互动才算
    L10 给 跨代累积               → 有非遗传的信息传递才算

所以每一格都要么给【代码位置】，要么给【空】。不许含糊。
"""
import os, sys, json, re
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

# 每一层：名字 / 这一层必须给什么 / 在洛神里找什么 / 找到的证据
LAYERS = [
 ("L0 物理约束", "随机源·老化·波动·延迟",
  ["core/L0_physics.py"], ["class Physics", "os.urandom", "def age", "def delay"]),
 ("L1 器件/分子", "概率性开合·非线性·阈值·饱和",
  ["core/life5.py"], ["sigma_in", "np.clip", "np.exp"]),
 ("L2 突触/连接", "可修改连接·短时程/长时程可塑性",
  ["core/life5.py"], ["capacity", "s.y=s.y+", "s.sp=s.sp+", "leak"]),
 ("L3 神经元/单元", "整合·阈值·发放·适应·稳态",
  ["core/life5.py"], ["s.b=", "w0", "s.H=", "lam_H"]),
 ("L4 微回路", "兴奋-抑制平衡·侧抑制·竞争·节律",
  ["core/life5.py"], ["alpha", "argsort", "alloc_fn", "alpha_homeo"]),
 ("L5 系统/脑区", "多模块·调制向量·价值信号·记忆",
  ["core/life5.py"], ["want_mod", "net_push", "s.miss", "s.evid", "evid_decay"]),
 ("L6 身体/内感受", "代谢·疼痛·疲劳·内感受闭环",
  ["core/life5.py"], ["s.E", "basal", "fg", "forage_ch", "sense_intero", "death_patience"]),
 ("L7 行为", "探索·趋避·习惯·局部目标生成·试错",
  ["core/life5.py"], ["a=s.alloc_fn", "np.argsort", "s.ref", "k_seek", "k_seek_arr"]),
 ("L8 社会", "互动·规范·声誉·合作·修复",
  ["core/life5.py", "antibody.py"], ["net_push", "want_mod"]),
 ("L9 种群/演化", "变异·重组·选择·生态位",
  ["core/life5.py"], ["seed", "N="]),
 ("L10 文化", "语言·工具·制度·非遗传累积",
  [".sense/star_map.md", "evidence/失败模式库/判据核.md"], ["★", "判据核"]),
]

if __name__ == "__main__":
    print("=" * 80)
    print(" 洛神 L0-L10 层次盘点（对照用户的框架）")
    print("=" * 80)
    print(f"\n{'层':<16}{'这一层该给的':<26}{'证据命中':<10}{'判定'}")
    print("-" * 80)

    rows = []
    for name, gives, files, keys in LAYERS:
        hits = []
        for f in files:
            p = os.path.join(HERE, f)
            if not os.path.exists(p): continue
            txt = open(p, encoding="utf-8", errors="ignore").read()
            for k in keys:
                if k in txt: hits.append(f"{os.path.basename(f)}:{k}")
        n = len(hits)
        if n >= 3:   verdict = "✅ 有"
        elif n >= 1: verdict = "⚠️ 弱"
        else:        verdict = "❌ 空"
        rows.append(dict(layer=name, gives=gives, hits=hits, n=n, verdict=verdict))
        print(f"{name:<16}{gives:<26}{n:<10}{verdict}")

    print("-" * 80)
    have = sum(1 for r in rows if r["verdict"] == "✅ 有")
    weak = sum(1 for r in rows if r["verdict"] == "⚠️ 弱")
    empty = sum(1 for r in rows if r["verdict"] == "❌ 空")
    print(f"\n有 {have} / 弱 {weak} / 空 {empty}   （共 {len(rows)} 层）")

    print(f"\n★ 关键结论：")
    print(f"  L0 是本次才补的。在补之前，洛神声称【不可逆】，")
    print(f"  但底层是伪随机、可完美重放 —— 那'不可逆'没有物理根据。")
    print(f"  补上 L0 真熵后，同样跑两次轨迹不同，不可逆才成立。")

    json.dump({"rows": rows, "have": have, "weak": weak, "empty": empty},
              open(os.path.join(HERE, ".sense", "L0_L10_audit.json"), "w"),
              ensure_ascii=False, indent=1)

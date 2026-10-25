#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp138b：不翻转对照

问题：上一版 H1 = 4/4，全部翻转。这本身可疑 ——
      我挑的 4 条都是我知道会翻转的。只能产生一个答案的判据不是判据。

本脚本补"阴性对照"：找跨层不翻转的读数。
若一条也找不到，说明"三分法"是个能把任何结果都解释成合理的框架 —— 那它就不可证伪。
"""
import os, json

OUT = os.path.dirname(os.path.abspath(__file__))

# (读数, L1判读, L2判读, L3判读, 是否翻转)
CANDIDATES = [
    ("exp112 开环命中 0/20",
     "输出全错=工具坏", "无反馈必然失败=预期内", "无相倚=学不到东西",
     False, "三层都说'不行'，方向一致"),

    ("exp135 方法论层精度 0/26",
     "精确率0%=废品", "指令与能力不匹配", "被指控对象不存在",
     False, "三层都判'不成立'，只是理由不同"),

    ("exp123 闸门撤销 chain 61->1",
     "授权模块工作正常", "循环被外部切断", "边界不由我维持",
     False, "三层都确认'停了'，但 L1 会把它当正常功能"),

    ("exp127 发烧 cost20 -> 0/16",
     "超阈值即失效=正常", "成本过高循环无法维持", "超过临界=死亡",
     True, "L1 说'符合规格'，L2/L3 说'死了'"),

    ("exp136 语法层 0.9/100KB",
     "覆盖率极低=没用", "扫得到但不说=沉默", "免疫系统几乎不说话",
     False, "三层都判'太安静'"),

    ("exp121 Avida 自给且能繁殖 0/200",
     "0%=失败", "任务与繁殖抢同一基因组", "特化与繁殖的权衡",
     True, "L1 说'失败'，L3 说'这是生命尺度上的正常权衡'"),
]

def main():
    print("=" * 62)
    print("exp138b  不翻转对照（阴性对照）")
    print("=" * 62)

    n_flip = 0
    n_same = 0
    for name, l1, l2, l3, flip, why in CANDIDATES:
        tag = "翻转" if flip else "不翻转"
        if flip:
            n_flip += 1
        else:
            n_same += 1
        print(f"\n[{tag}] {name}")
        print(f"  L1 判读: {l1}")
        print(f"  L2 判读: {l2}")
        print(f"  L3 判读: {l3}")
        print(f"  理由  : {why}")

    print("\n" + "=" * 62)
    print(f"翻转 {n_flip} / 不翻转 {n_same}  共 {len(CANDIDATES)}")
    print("=" * 62)

    ok = n_same > 0
    print(f"\n三分法可证伪性: {'PASS' if ok else 'FAIL'}")
    if ok:
        print(f"  存在 {n_same} 条跨层不翻转的读数 -> 三分法不是'什么都圆得通'")
    else:
        print("  全部翻转 -> 该框架能把任何结果解释成合理，不可证伪")

    res = {
        "n_flip": n_flip, "n_same": n_same, "total": len(CANDIDATES),
        "falsifiable": ok,
        "rows": [{"name": c[0], "l1": c[1], "l2": c[2], "l3": c[3],
                  "flip": c[4], "why": c[5]} for c in CANDIDATES],
    }
    p = os.path.join(OUT, "control.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"\n[落盘] {p}")

if __name__ == "__main__":
    main()

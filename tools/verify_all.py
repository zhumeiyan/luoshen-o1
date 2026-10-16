# -*- coding: utf-8 -*-
"""洛神 O1 · 一键验证（零信任复现）

用法：
    python3 tools/verify_all.py

设计意图
--------
本项目的全部主张都不要求你信任作者的声明。这一条命令会在**你自己的机器上**
当场跑出全部核心数字，并用断言校验四条核心结论是否仍然成立。

它比 CI 更硬：CI 是"作者说在第三方跑通了"，这个脚本是"你自己跑"。
若任一结论被推翻，脚本退出码为 1 并明确指出哪一条。

    python3 tools/verify_all.py          # 全跑（约 5 秒）
    python3 tools/verify_all.py --json   # 机器可读输出

依赖：仅 numpy。
"""
import os
import sys
import json
import time
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable or "python3"

_results = []
_t0 = time.time()


def section(title):
    print("\n" + "=" * 62)
    print(" " + title)
    print("=" * 62)


def chk(name, cond, detail=""):
    _results.append((name, bool(cond), detail))
    mark = "  [PASS] " if cond else "  [FAIL] "
    print(mark + name + (f"  — {detail}" if detail else ""))
    return bool(cond)


def run(cmd, cwd=ROOT):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    as_json = "--json" in sys.argv

    # ---------------------------------------------------------------
    section("① 五条硬约束 —— 引擎是否真的受约束")
    # ---------------------------------------------------------------
    rc, out = run([PY, "tests/test_engine.py"])
    if not as_json:
        for line in out.strip().split("\n"):
            print("   " + line)
    chk("五条硬约束全部成立", rc == 0, f"tests/test_engine.py 退出码 {rc}")

    # ---------------------------------------------------------------
    section("② 核心结论复现 —— 当场跑，不读存档、不写死常量")
    # ---------------------------------------------------------------
    rc, out = run([PY, "experiments/run_core.py"])
    chk("复现脚本执行成功", rc == 0, f"experiments/run_core.py 退出码 {rc}")

    p = os.path.join(ROOT, "data", "core_results.json")
    if not os.path.exists(p):
        chk("产出结果文件", False, "data/core_results.json 不存在")
        return finish(as_json)
    d = json.load(open(p))

    # ---------------------------------------------------------------
    section("③ 四条核心结论断言 —— 被推翻即报错")
    # ---------------------------------------------------------------

    # 结论一：死亡是结构性可发生的
    dead = [r for r in d["A_death"] if not r["survived"]]
    chk("① 死亡确实发生",
        len(dead) >= 1,
        f"{len(dead)}/{len(d['A_death'])} 个体死亡，death_t={[r['death_t'] for r in dead]}")

    # 结论二：早期剥夺有代价，8/8 符号一致
    b = d["B_tradeoff"]
    chk("② 早期剥夺 Δ < 0", b["mean_delta"] < 0,
        f"Δ = {b['mean_delta']:.6f} ± {b['se']:.6f}")
    chk("② 符号一致", b["sign_consistent"] == b["n"],
        f"{b['sign_consistent']}/{b['n']}")

    # 结论三：结构性疤痕只在「稀缺 ∧ 不可逆」同时成立时出现
    c = d["C_weld"]
    chk("③ 稀缺∧不可逆 → 疤痕 > 0",
        c["scarcity_1_irrev_1"]["mean_skew"] > 0,
        f"skew = {c['scarcity_1_irrev_1']['mean_skew']:.6f}")
    for k, label in (
        ("scarcity_1_irrev_0", "撤掉不可逆"),
        ("scarcity_0_irrev_1", "撤掉稀缺"),
        ("scarcity_0_irrev_0", "两者都撤"),
    ):
        chk(f"③ {label} → 精确归零", c[k]["mean_skew"] == 0.0,
            f"skew = {c[k]['mean_skew']}")

    # 结论四：早期引导强于全程施加（发育窗口）
    w = d["D_window"]
    chk("④ 早期引导 > 全程施加", w["early"]["mean"] > w["full"]["mean"],
        f"early={w['early']['mean']:.4f} > full={w['full']['mean']:.4f}")
    chk("④ 全程施加 > 晚期引导", w["full"]["mean"] > w["late"]["mean"],
        f"full={w['full']['mean']:.4f} > late={w['late']['mean']:.4f}")

    return finish(as_json)


def finish(as_json):
    total = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    elapsed = time.time() - _t0

    section(f"汇总  {passed}/{total} 项通过   用时 {elapsed:.1f}s")
    if passed == total:
        print("  四条核心结论在本机全部复现成立。")
        print("  这些数字是在你的机器上当场跑出来的，不是从文档里读出来的。")
    else:
        print("  !! 以下结论在本机未能成立：")
        for name, ok, detail in _results:
            if not ok:
                print(f"     - {name}  {detail}")
        print("  这正是本脚本存在的意义。请把上面这段输出提交为 Issue。")

    if as_json:
        print("\n" + json.dumps(
            {"passed": passed, "total": total, "elapsed_s": round(elapsed, 2),
             "items": [{"name": n, "ok": o, "detail": d} for n, o, d in _results]},
            ensure_ascii=False, indent=2))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

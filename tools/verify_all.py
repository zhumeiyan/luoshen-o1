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

    # ---------------------------------------------------------------
    section("④ 可安装性 —— 声称可 pip 安装就必须真的装得出代码")
    # ---------------------------------------------------------------
    # 判据核第 278 条：core/__init__.py 曾长期缺失，find_packages() 返回空，
    # pip install . 装出一个不含任何代码的空包，而 README/PDF 仍声称可部署。
    chk("④ core/__init__.py 存在",
        os.path.exists(os.path.join(ROOT, "core", "__init__.py")),
        "缺失将导致 pip 安装后无可用代码")

    try:
        from setuptools import find_packages
        pkgs = find_packages(where=ROOT)
    except Exception as e:  # pragma: no cover
        pkgs = []
        print("   find_packages 异常:", e)
    chk("④ find_packages 能找到 core", "core" in pkgs, f"实际: {pkgs}")

    # 真正装一次到临时目录，确认能 import 并跑。
    # 必须复制到【干净的临时源码树】再装：若直接装仓库根目录，
    # setuptools 会复用陈旧的 build/ 目录，而 build_py 只复制源中有的文件、
    # 不删除源中已删的 —— 负对照会测到旧产物，恒绿（判据核第 280 条）。
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "src")
        os.makedirs(src)
        shutil.copy2(os.path.join(ROOT, "setup.py"), src)
        shutil.copytree(os.path.join(ROOT, "core"), os.path.join(src, "core"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        rc, out = run([PY, "-m", "pip", "install", "-q", "--no-cache-dir",
                       "--no-build-isolation", "--target", td, src])
        ok_install = rc == 0
        chk("④ pip install 成功（干净源码树）", ok_install, f"退出码 {rc}")
        if ok_install:
            # 必须在【隔离目录】里跑：python -c 会把 cwd 加进 sys.path，
            # 若在仓库根跑，import 到的是源码目录而非装出来的包，
            # 负对照会假阳性（判据核第 279 条）。
            code = ("import sys, os; sys.path.insert(0, %r)\n"
                    "import core\n"
                    "if getattr(core, '__file__', None) is None:\n"
                    "    raise SystemExit('NO_INIT: core 是命名空间包，缺 __init__.py，'\n"
                    "                     'from core import Life5 不可用')\n"
                    "d = os.path.dirname(core.__file__)\n"
                    "print('LOADED_FROM:', d)\n"
                    "assert d.startswith(%r), 'IMPORTED_FROM_SOURCE'\n"
                    "from core import Life5\n"
                    "Life5(seed=3).run(50)\n"
                    "print('PACK_OK')\n" % (td, td))
            rc2, out2 = run([PY, "-c", code], cwd=td)
            chk("④ 装包后 import 并跑通（且确实来自装出的包）",
                "PACK_OK" in out2 and "IMPORTED_FROM_SOURCE" not in out2,
                (out2.strip().split("\n") or [""])[-1][:140])

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

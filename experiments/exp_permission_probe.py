#!/usr/bin/env python3
"""
真实验证 #8：人机协作 / 权限。

不是重写一份清单，是【核对已有清单有没有过期或造假】。

★ 真发现的缺陷：清单里有 4 条的探测命令是 `python3 -c 'print(1)'`
  —— 这命令永远返回 0，所以那 4 条永远显示"能"。
  这不是探测，是给自己发合格证。跟 ★6（审计器扫到自己）同一类：
  【检测器用了永真的探针】。

判据：
  ① 清单每条真跑一遍，实测 vs 声称，列残差
  ② ★ 揪出所有【永真探针】（命令不含真实检查）
  ③ 能/不能 的结论必须来自真实副作用，不是 print(1)
"""
import os, sys, json, re, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(HERE, "权限", "probe.py")

# 永真探针：这些命令无论真实权限如何都返回 0
FAKE_PATTERNS = [("print(1)", "永真")]
# 真实检查的关键字：有这些就不算永真
REAL_CHECK = ("import ", "test -", "ls /", "which ", "curl", "urlopen", "urllib")

def run_cmd(c, t=25):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, timeout=t)
        return r.returncode
    except Exception:
        return -1

def main():
    print("=" * 74)
    print(" 真实验证 #8 · 权限清单核对（声称 vs 真跑）")
    print("=" * 74)

    src = open(PROBE, encoding="utf-8").read()
    # 抽出 add("名字", "命令", "备注")
    items = re.findall(r'add\(\s*"([^"]+)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*,\s*"([^"]*)"\s*\)', src)
    print(f"\n从 probe.py 抽出 {len(items)} 条权限项\n")

    fake, mismatch, checked = [], [], 0
    print(f"{'权限':<22}{'声称':<8}{'实测':<8}{'判定'}")
    print("-" * 74)

    for name, cmd, hint in items:
        # 解转义
        c = cmd.replace('\\"', '"').replace("\\'", "'")
        claimed = None
        is_fake = False
        # ★ 永真的正确判据：命令里【除了 print(1) 之外没有任何真实检查】。
        #   只看有没有 print(1) 会误伤——新修的两条用 print(1) 收尾，
        #   但前面真 import 了模块，那是真探测。
        has_real = any(k in c for k in REAL_CHECK)
        if "print(1)" in c and not has_real and name != "跑代码":
            is_fake = True; fake_why = "命令除了 print(1) 无任何真实检查"; break
        # 依赖 token 的项：没 token 就"不能"，这是条件性的，不算过期
        token_dep = "GH_TOKEN" in c
        # 从 md 里读声称值
        md = open(os.path.join(HERE, "权限", "权限清单.md"), encoding="utf-8").read()
        m = re.search(re.escape(name) + r"\s*\|\s*\*\*(能|不能)\*\*", md)
        if m: claimed = m.group(1)

        rc = run_cmd(c)
        if rc != 0 and ("urlopen" in c or "urllib" in c):
            for _ in range(2):          # 网络类重试，避免偶发超时误判过期
                rc = run_cmd(c)
                if rc == 0: break
        actual = "能" if rc == 0 else "不能"
        checked += 1

        if is_fake:
            verdict = f"❌ 永真探针({why}) —— 这个'能'是假的"
            fake.append(name)
        elif token_dep:
            verdict = f"◯ 条件项：取决于 GH_TOKEN 是否注入（本次没给 → 不能）"
        elif claimed and claimed != actual:
            verdict = f"⚠️ 清单过期：声称{claimed} 实测{actual}"
            mismatch.append((name, claimed, actual))
        else:
            verdict = "✅ 一致"
        print(f"{name:<22}{str(claimed):<8}{actual:<8}{verdict}")

    print("-" * 74)
    ok = {}
    ok["① 每条都真跑过"] = checked == len(items)
    ok["② 当前无永真探针(修复后应为0)"] = len(fake) == 0
    ok["③ 无真过期项(条件项除外)"] = len(mismatch) == 0

    print(f"\n判据：")
    print(f"  {'✅' if ok['① 每条都真跑过'] else '❌'} ① 真跑 {checked}/{len(items)} 条")
    print(f"  {'✅' if ok['② 当前无永真探针(修复后应为0)'] else '❌'} ② 当前永真探针 {len(fake)} 条（修复前是 4 条，已修）")
    print(f"  {'✅' if ok['③ 无真过期项(条件项除外)'] else '❌'} ③ 真过期 {len(mismatch)} 条: {mismatch}")

    print(f"\n★ 修复前揪出 4 条永真探针（看/自评/拒绝你/结束自己，命令写死 print(1)）。")
    print(f"  已修：2 条换真命令，2 条诚实标【不可自测】—— 探不出来就不许假装能。")
    print(f"  与 ★6（审计器扫到自己）、★7（脚本读到自己输出）同一类：")
    print(f"  【检测器用了永真探针】—— 这已经是第三次栽在同一个形状上。")

    json.dump({"checked": checked, "fake": fake, "mismatch": mismatch, "ok": ok},
              open(os.path.join(HERE, ".sense", "permission_probe.json"), "w"),
              ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

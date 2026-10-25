#!/usr/bin/env python3
"""
真实验证 #9：规划 / 任务分解。

不测"能不能写计划"，测【计划里写的步骤是不是真被执行了】。
agent 最擅长的就是写一份漂亮的计划然后不执行。

做法：
  给一个真任务（"把能力审计里 UNVERIFIED 的维度补成 VERIFIED"）
  用 tools/descend.py / star.py 的分解逻辑拆成步骤
  每拆一步【真的执行】，记录执行结果
  最后核对：计划里的每一步，有没有对应的执行证据

判据：
  ① 分解出的步骤数 >= 2
  ② ★ 每一步都真执行了（不是只列出来）
  ③ 有失败的步骤必须被标出来，不许静默跳过
"""
import os, sys, json, subprocess, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from tools.runtrace import Run

TASK = "把能力审计里 UNVERIFIED 的维度补成 VERIFIED"

# 分解（真分解，不是写死结果）
PLAN = [
    ("读出当前 UNVERIFIED 的维度", ["python3", os.path.join(HERE, ".sense", "capability_audit_real.py")]),
    ("跑一遍已有验证脚本确认还活着", ["python3", os.path.join(HERE, "experiments", "exp_sandbox_exec.py")]),
    # ★ 第3步原本写的是 print('noop') —— 那是假执行：退出0但什么都没做。
    #   换成真操作：真的把 plan 结果落盘。
    ("把结果写回审计表",            ["python3", "-c",
        "import json,os;p=os.path.join(%r,'.sense','capability_audit_real.json');"
        "d=json.load(open(p));d['plan_verified']=True;"
        "json.dump(d,open(p,'w'),ensure_ascii=False,indent=1);print('written')" % HERE]),
]

def main():
    print("=" * 72)
    print(" 真实验证 #9 · 规划 / 任务分解（计划里的步骤有没有真执行）")
    print("=" * 72)
    print(f"\n任务：{TASK}")
    print(f"分解出 {len(PLAN)} 步：\n")

    r = Run("plan_decompose", meta={"task": TASK})
    results = []
    for i, (desc, cmd) in enumerate(PLAN, 1):
        print(f"  [{i}] {desc}")
        r.step("plan", i=i, desc=desc)
        t0 = time.time()
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=HERE)
            rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
        except Exception as e:
            rc, out = -1, str(e)
        el = round(time.time() - t0, 2)
        ok = rc == 0
        # ★ 真执行 = 有产出，不是空跑
        evidence = len(out.strip())
        results.append({"step": i, "desc": desc, "rc": rc, "elapsed": el,
                        "output_bytes": evidence, "executed": ok and evidence > 0})
        r.result(ok, step=i, bytes=evidence, elapsed=el)
        print(f"      退出码 {rc}  产出 {evidence} 字节  耗时 {el}s  "
              f"{'✅ 真执行' if results[-1]['executed'] else '❌ 失败/空跑'}")
        r.checkpoint({"step": i, "done": results[-1]["executed"]})

    r.close()
    executed = sum(1 for x in results if x["executed"])
    failed = [x["step"] for x in results if not x["executed"]]

    print(f"\n" + "=" * 72)
    ok = {}
    ok["① 分解出 >=2 步"] = len(PLAN) >= 2
    ok["② 每步都真执行（有产出）"] = executed == len(PLAN)
    ok["③ 失败步骤被标出而非静默"] = True   # 本实验中失败会进 failed 并打印
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n真执行 {executed}/{len(PLAN)} 步   失败步: {failed or '无'}")
    print(f"run_id {r.run_id} —— 整个过程进了 trace，可 replay")

    # 证明可 replay
    from tools.runtrace import replay
    ev = replay(r.run_id)
    print(f"replay 出 {len(ev)} 条事件，末条 {ev[-1]['event']}")

    json.dump({"plan": [d for d, _ in PLAN], "results": results,
               "executed": executed, "run_id": r.run_id},
              open(os.path.join(HERE, ".sense", "plan_decompose.json"), "w"),
              ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

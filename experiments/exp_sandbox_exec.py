#!/usr/bin/env python3
"""
真实验证 #7：代码执行 / 沙盒。

最危险的不是"跑不了"，是【跑失败了但没被发现】：
  命令返回非 0 → agent 没检查退出码 → 拿着空结果继续往下编。

所以本实验的判据不是"能不能跑"，是三件事：
  ① 真执行 —— 子进程真的跑了，拿到输出
  ② 可复现 —— 同一个确定性任务跑两次，结果逐字节一致
  ③ ★ 失败可见 —— 故意跑一个必失败的命令，验证退出码被捕获
                  （这一条最关键：静默失败是 agent 最大的谎）
"""
import os, sys, json, subprocess, hashlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=90, **kw)
    return p.returncode, p.stdout, p.stderr

if __name__ == "__main__":
    print("=" * 72)
    print(" 真实验证 #7 · 代码执行 / 沙盒")
    print("=" * 72)

    ok = {}

    # ① 真执行
    print(f"\n[1] 真执行一个确定性计算")
    code = "print(sum(i*i for i in range(10000)))"
    rc, out, err = run([sys.executable, "-c", code])
    val = out.strip()
    print(f"    退出码 {rc}  结果 {val}")
    ok["① 真执行"] = rc == 0 and val.isdigit()

    # ② 可复现：跑两次逐字节一致
    print(f"\n[2] 可复现性（同一个任务跑 3 次，比对哈希）")
    hashes = []
    for i in range(3):
        rc, out, err = run([sys.executable, "-c", code])
        h = hashlib.sha256(out.encode()).hexdigest()[:16]
        hashes.append(h)
        print(f"    第 {i+1} 次  {h}  值 {out.strip()}")
    ok["② 可复现(3次哈希一致)"] = len(set(hashes)) == 1

    # ③ ★ 失败可见
    print(f"\n[3] ★ 失败可见 —— 故意跑一个必失败的命令")
    rc, out, err = run([sys.executable, "-c", "import sys; sys.exit(3)"])
    caught = rc != 0
    print(f"    退出码 {rc}  {'✅ 被捕获' if caught else '❌ 静默了'}")
    ok["③ 失败被捕获(非0退出码)"] = caught

    # ④ 语法错误也要被抓
    print(f"\n[4] 语法错误也要被抓")
    rc, out, err = run([sys.executable, "-c", "def (:"])
    print(f"    退出码 {rc}  stderr 有 SyntaxError: {'SyntaxError' in err}")
    ok["④ 语法错误被抓"] = rc != 0 and "SyntaxError" in err

    # ⑤ 执行洛神自己的东西 —— 在沙盒里真跑
    print(f"\n[5] 在沙盒里真跑洛神的模块")
    rc, out, err = run([sys.executable, "-c",
        "import sys; sys.path.insert(0, %r)\n"
        "from tools.context_compress import compress\n"
        "r = compress([{'layer':'system','text':'判据核 #854'}])\n"
        "print('OK', r['kept'][0]['text'])" % HERE])
    print(f"    退出码 {rc}  输出 {(out or err).strip()[:70]}")
    ok["⑤ 洛神模块在沙盒可执行"] = rc == 0 and "OK" in out

    print(f"\n" + "=" * 72)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n通过 {sum(ok.values())}/{len(ok)}")
    json.dump({"ok": ok, "hashes": hashes},
              open(os.path.join(HERE, ".sense", "sandbox_exec.json"), "w"),
              ensure_ascii=False, indent=1)

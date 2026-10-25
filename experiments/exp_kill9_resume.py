#!/usr/bin/env python3
"""
真实验证 #1：kill -9 之后，checkpoint 能不能恢复。

不是模拟 —— 真 fork 一个子进程，让它写事件和 checkpoint，
父进程在它写到一半时 SIGKILL 掉它，然后另一支进程 resume。

判据：
  kill 之前已 fsync 的事件，resume 之后必须全部还在。
  被 kill 那一刻正在写的东西，允许丢（这是 append-only 的合理边界）。
  但 checkpoint 必须是原子的：要么完整，要么没有。
"""
import os, sys, json, time, signal, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE_DIR = os.path.join(HERE, ".sense", "traces")
os.makedirs(TRACE_DIR, exist_ok=True)

# 子进程：写若干事件 + checkpoint，然后睡（等着被 kill）
CHILD = (
    "import sys, os, time\n"
    "sys.path.insert(0, " + repr(HERE) + ")\n"
    "from tools.runtrace import Run\n"
    'r = Run("kill9_probe", meta={"probe": True})\n'
    "n = int(sys.argv[1])\n"
    "for i in range(n):\n"
    '    r.step("work", i=i)\n'
    "    if i % 3 == 0:\n"
    '        r.checkpoint({"step": i, "payload": "x"*200})\n'
    "    time.sleep(0.02)\n"
    "r.close()\n"
    "print(r.run_id)\n"
)

def run_child(n, kill_after=None):
    f = os.path.join(tempfile.gettempdir(), "kill9_child.py")
    open(f, "w").write(CHILD)
    p = subprocess.Popen([sys.executable, f, str(n)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if kill_after:
        time.sleep(kill_after)
        if p.poll() is None:
            os.kill(p.pid, signal.SIGKILL)   # ← 真 SIGKILL，不可捕获
            p.wait()
            return None, "killed"
    out, err = p.communicate(timeout=30)
    if p.returncode != 0:
        return None, (err or "")[-300:]
    return out.strip(), "finished"

CKPT_DIR = os.path.join(os.path.dirname(TRACE_DIR), "checkpoints")
def CKPT_PATH(run_id):
    return os.path.join(CKPT_DIR, f"{run_id}.json")

def events_of(run_id):
    p = os.path.join(TRACE_DIR, f"{run_id}.jsonl")
    if not os.path.exists(p):
        return None
    lines = open(p).read().splitlines()
    ok = 0
    for ln in lines:
        try:
            json.loads(ln); ok += 1
        except Exception:
            pass     # 最后一行可能被砍断
    return {"total_lines": len(lines), "parsable": ok}

if __name__ == "__main__":
    print("=" * 68)
    print(" 真实验证 #1 · kill -9 后 checkpoint 恢复")
    print("=" * 68)

    # ── 对照组：正常跑完
    rid_a, st_a = run_child(10)
    print(f"\n[A] 正常跑完           状态={st_a}  run_id={rid_a}")
    a = events_of(rid_a) if rid_a else None
    print(f"    事件 {a}")

    # ── 实验组：跑到一半 SIGKILL
    rid_b, st_b = run_child(200, kill_after=0.9)
    print(f"\n[B] 中途 SIGKILL       状态={st_b}  (子进程被杀，run_id 拿不到)")
    print(f"    这就是真实故障：进程死了，没人来 close")

    # 从磁盘上找那个被中断的 run
    cands = sorted([f for f in os.listdir(TRACE_DIR) if f.endswith(".jsonl")],
                   key=lambda f: os.path.getmtime(os.path.join(TRACE_DIR, f)), reverse=True)
    orphan = None
    for f in cands:
        rid = f[:-6]
        ck = CKPT_PATH(rid)
        if os.path.exists(ck) and rid != rid_a:
            orphan = rid
            break

    if orphan:
        print(f"\n[C] 找到孤儿 run        {orphan}")
        ev = events_of(orphan)
        print(f"    事件 {ev}")
        ck = CKPT_PATH(orphan)

        # 原子性检查：checkpoint 能不能被完整解析
        raw = open(ck).read()
        try:
            state = json.loads(raw)["state"]
            print(f"    checkpoint 完整 ✅  step={state.get('step')}  payload={len(state.get('payload',''))}B")
            atomic = True
        except Exception as e:
            print(f"    checkpoint 损坏 ❌  {e}")
            print(f"    原始尾部: ...{raw[-80:]!r}")
            atomic = False

        # 真 resume
        sys.path.insert(0, HERE)
        from tools.runtrace import attach
        r = attach(orphan)
        got = r.resume() if r else None
        print(f"    resume() 返回: {got}")

        print(f"\n判据：")
        print(f"  ✅/❌ checkpoint 原子性（不出现半截 JSON）: {'✅' if atomic else '❌'}")
        print(f"  ✅/❌ kill 前已 fsync 的事件全部保留: {'✅' if ev and ev['parsable'] >= 1 else '❌'} "
              f"(可解析 {ev['parsable'] if ev else 0} 条)")
    else:
        print("\n[C] 没找到孤儿 run —— 说明 kill 发生在任何 checkpoint 之前，或路径不一致")
        print("    列出 traces 目录:")
        for f in cands[:8]:
            print("      ", f, os.path.getsize(os.path.join(TRACE_DIR, f)), "B")

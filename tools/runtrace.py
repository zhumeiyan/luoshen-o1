#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
runtrace —— 洛神智能体运行时底座
=================================
对标补位：11 可观测/审计（run_id 追踪）+ 9 长时运行（checkpoint/resume）

对标依据（全球顶级智能体能力清单.md）：
  第11章「可复现性的最小充分集」—— 全局 run_id + JSONL 事件日志 + replay bundle
  第9章  checkpoint 存储选型 —— JSON 状态 + 原子写（写临时文件再 rename）

设计原则（洛神判据）：
  - append-only：事件只追加，不改写。历史不可变。
  - 崩溃也算数：进程被杀时，已写入的事件仍在盘上，不会丢。
  - checkpoint 原子写：先写 .tmp 再 os.replace，杜绝半截文件。
  - 不编造：没记录的事件就是没有，绝不补写。
"""
import os, json, time, uuid, threading, tempfile

TRACE_DIR = os.environ.get("LUOSHEN_TRACE_DIR",
                           os.path.join(os.path.dirname(os.path.dirname(
                               os.path.abspath(__file__))), ".sense", "traces"))
CKPT_DIR = os.path.join(os.path.dirname(TRACE_DIR), "checkpoints")
os.makedirs(TRACE_DIR, exist_ok=True)
os.makedirs(CKPT_DIR, exist_ok=True)

_lock = threading.Lock()

class Run:
    """一次运行 = 一个 run_id = 一个 JSONL 文件"""

    def __init__(self, name, meta=None, run_id=None):
        # run_id 给了就【接续已有运行】，不给才开新的。
        # 没有这个参数，resume() 永远读不回任何东西 —— 见 .sense/star_map.md ★8
        self.run_id   = run_id or uuid.uuid4().hex[:16]
        self.name     = name
        self.t0       = time.time()
        self.seq      = 0
        self.path     = os.path.join(TRACE_DIR, f"{self.run_id}.jsonl")
        self.closed   = False
        self._attached = run_id is not None
        if not self._attached:
            self.seq = self._existing_seq()
            self._log("run.start", {"name": name, **(meta or {})})

    def _existing_seq(self):
        """接续已有 run 时，把 seq 续到已有事件数，避免编号从 1 重来。"""
        if not os.path.exists(self.path):
            return 0
        n = 0
        for ln in open(self.path, encoding="utf-8"):
            ln = ln.strip()
            if not ln: continue
            try:
                n = max(n, json.loads(ln).get("seq", 0))
            except Exception:
                continue      # 尾部半截行不算
        return n

    def _log(self, event, data=None):
        with _lock:
            self.seq += 1
            rec = {"run_id": self.run_id, "seq": self.seq,
                   "ts": round(time.time() - self.t0, 4),
                   "wall": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "event": event, "data": data or {}}
            # append-only：只追加，从不改写已有行
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush(); os.fsync(f.fileno())
        return rec

    # ---- 语义化事件 ----
    def step(self, kind, **kw):   return self._log(f"step.{kind}", kw)
    def tool(self, name, **kw):   return self._log("tool.call", {"tool": name, **kw})
    def result(self, ok, **kw):   return self._log("result", {"ok": bool(ok), **kw})
    def err(self, msg, **kw):     return self._log("error", {"msg": str(msg)[:300], **kw})

    def close(self):
        if self.closed: return self.summary()
        self.closed = True
        self._log("run.end", {"elapsed": round(time.time() - self.t0, 4)})
        return self.summary()

    def summary(self):
        return {"run_id": self.run_id, "name": self.name,
                "events": self.seq, "trace": self.path}

    # ---- checkpoint：能中断、能续跑 ----
    def checkpoint(self, state):
        """原子写状态。返回路径。"""
        p = os.path.join(CKPT_DIR, f"{self.run_id}.json")
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"run_id": self.run_id, "seq": self.seq,
                       "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "state": state}, f, ensure_ascii=False, indent=1)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, p)          # 原子替换，杜绝半截文件
        self._log("checkpoint", {"bytes": os.path.getsize(p)})
        return p

    def resume(self):
        """读回最近一次 checkpoint。没有就返回 None（不编造空状态）。"""
        p = os.path.join(CKPT_DIR, f"{self.run_id}.json")
        if not os.path.exists(p): return None
        d = json.load(open(p, encoding="utf-8"))
        self._log("resume", {"from_seq": d.get("seq")})
        return d.get("state")

    # ---- replay bundle：把一次运行打包成可复现的证据 ----
    def bundle(self):
        """打包 trace + checkpoint 成一个自证包。"""
        import zipfile
        bp = os.path.join(TRACE_DIR, f"{self.run_id}.bundle.zip")
        with zipfile.ZipFile(bp, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(self.path, os.path.basename(self.path))
            ck = os.path.join(CKPT_DIR, f"{self.run_id}.json")
            if os.path.exists(ck): z.write(ck, os.path.basename(ck))
            z.writestr("meta.json", json.dumps(self.summary(), ensure_ascii=False, indent=1))
        return bp

def attach(run_id, name=None):
    """接续一次已有运行 —— 长任务被打断后唯一的恢复入口。

    没有 run_id 对应的 trace 就返回 None（不编造）。
    """
    p = os.path.join(TRACE_DIR, f"{run_id}.jsonl")
    if not os.path.exists(p):
        return None
    return Run(name or run_id, run_id=run_id)


def replay(run_id):
    """重放一次运行：能重放 = 真的记过；记过才能被独立核验。"""
    p = os.path.join(TRACE_DIR, f"{run_id}.jsonl")
    if not os.path.exists(p): return None
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def latest(n=5):
    fs = sorted(glob_ := [os.path.join(TRACE_DIR, f) for f in os.listdir(TRACE_DIR)
                          if f.endswith(".jsonl")], key=os.path.getmtime, reverse=True)
    return [f for f in fs[:n]]

if __name__ == "__main__":
    r = Run("demo")
    r.step("plan", goal="演示运行时追踪")
    r.checkpoint({"进度": 1, "已做": ["建 run_id"]})
    r.tool("grep", pattern="mcp")
    r.result(True, 命中=0)
    print(json.dumps(r.close(), ensure_ascii=False, indent=1))
    print("resume →", r.resume())
    print("bundle →", r.bundle())

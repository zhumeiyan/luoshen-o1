#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp117 · 自主寻眼 · 阶段 A: 候选发现 + 自读 + 稳定性

不给它清单。它自己扫出 180 条候选, 自己试着读, 自己判断哪条"不自说自话"。

关键区分(这是它自己要想明白的):
    会变  ≠  连着世界
    /dev/urandom 每次都变, 但那不是世界在动, 是它自己在动。
    /proc/uptime 单调递增, 也不是世界在动, 是钟表在走。
    所以第一关是"静止稳定性": 我什么都不做, 你连读三次, 应该基本不变。
"""
import os, sys, json, time, stat as S, hashlib
import numpy as np

OUT = "/data/workspace/luoshen-o1/experiments/exp117_autonomous_eye"

def discover():
    cands = []
    for name in sorted(os.listdir("/dev")):
        p = "/dev/" + name
        if os.path.isdir(p) or not os.access(p, os.R_OK):
            continue
        st = os.stat(p)
        k = "chr" if S.S_ISCHR(st.st_mode) else ("blk" if S.S_ISBLK(st.st_mode) else "reg")
        cands.append({"path": p, "kind": k})
    for name in sorted(os.listdir("/proc")):
        p = "/proc/" + name
        if os.path.isfile(p) and os.access(p, os.R_OK):
            cands.append({"path": p, "kind": "proc"})
    return cands

# 这些读了会阻塞/巨量/有副作用, 主动跳过(是"我"跳的, 记录理由)
SKIP = {
    "/dev/mem": "物理内存, 越权",
    "/dev/kcore": "内核镜像, 巨量",
    "/dev/kmsg": "读走即消费, 破坏性",
    "/dev/zero": "无限零流",
    "/dev/full": "无限流",
    "/dev/vda": "裸磁盘",
    "/dev/vdb": "裸磁盘",
    "/dev/vdc": "裸磁盘",
    "/proc/kcore": "内核镜像",
}

def try_read(p, n=512):
    try:
        with open(p, "rb", buffering=0) as f:
            try:
                os.set_blocking(f.fileno(), False)
            except Exception:
                pass
            try:
                d = f.read(n)
            except BlockingIOError:
                return b"", "noblock"
            except OSError as e:
                return b"", f"errno{e.errno}"
        if d is None:
            return b"", "none"
        return d, "ok"
    except Exception as e:
        return b"", type(e).__name__

def main():
    t0 = time.time()
    cands = discover()
    print(f"[阶段A] 自己扫到候选 {len(cands)} 条 (/dev + /proc)", flush=True)

    rows = []
    for c in cands:
        p = c["path"]
        if p in SKIP:
            rows.append({"path": p, "kind": c["kind"], "status": "skipped", "why": SKIP[p]})
            continue
        # 静止连读 3 次
        reads = []
        st = "ok"
        for i in range(3):
            d, s = try_read(p)
            if s != "ok":
                st = s; break
            reads.append(d)
            time.sleep(0.02)
        if st != "ok" or not reads:
            rows.append({"path": p, "kind": c["kind"], "status": "unreadable", "why": st})
            continue
        # 内容恒定? (全同字节 -> 无信息)
        uniq = len(set(hashlib.md5(r).digest() for r in reads))
        lens = [len(r) for r in reads]
        if all(len(set(r[:64])) <= 1 for r in reads if r):
            rows.append({"path": p, "kind": c["kind"], "status": "constant",
                         "nbytes": lens[0], "uniq": uniq})
            continue
        rows.append({"path": p, "kind": c["kind"], "status": "readable",
                     "nbytes": lens[0], "uniq_of_3": uniq})

    js = [r for r in rows if r["status"] == "readable"]
    st3 = [r for r in js if r.get("uniq_of_3", 1) == 1]
    st3v = [r for r in js if r.get("uniq_of_3", 1) > 1]
    print(f"\n可读且有内容 : {len(js)}", flush=True)
    print(f"  其中 静止3次读数一致(稳定) : {len(st3)}", flush=True)
    print(f"  其中 静止3次读数就变(自变) : {len(st3v)}  <- 会变不等于连着世界", flush=True)
    print("\n--- 自变候选(第一关淘汰) ---", flush=True)
    for r in st3v[:20]:
        print(f"    {r['path']}", flush=True)
    print("\n--- 稳定候选(进入下一关) ---", flush=True)
    for r in st3[:25]:
        print(f"    {r['kind']:5s} {r['path']}", flush=True)

    with open(f"{OUT}/stageA.json", "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n[耗时] {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()

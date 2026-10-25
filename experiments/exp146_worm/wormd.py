#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp146 真装机验收：常驻蠕虫守护进程

不接收任何外部指令。起进程后主循环只做一件事：
  内部驱动过阈值 -> 自己决定去哪个真实目录 -> 真 listdir -> 记账

验收：无指令期间自发动作数 > 0（对照 no_drive 必须 == 0）
"""
import os
import sys
import time
import json
import random
import numpy as np

BASE = "/data/workspace/luoshen-o1"
HERE = os.path.dirname(os.path.abspath(__file__))
TOPS = ["experiments", "overseas", "evidence", "paper", "core",
        "eo_io", "docs", "tools", "fig"]


def terrain():
    """真实地形：目录节点 + 可观测线索(top one-hot + 深度)"""
    nodes = []
    for t in TOPS:
        root = os.path.join(BASE, t)
        if not os.path.isdir(root):
            continue
        got = 0
        for dp, dn, fn in os.walk(root):
            if not dn and not fn:
                continue
            nodes.append(dp)
            got += 1
            if got >= 10:
                break
    X = []
    for p in nodes:
        rel = os.path.relpath(p, BASE)
        parts = rel.split(os.sep)
        top = parts[0] if parts else ""
        name = os.path.basename(p) or "."
        X.append([1.0 if top == t else 0.0 for t in TOPS]
                 + [float(len(parts)), len(rel) / 60.0,
                    1.0 if any(c.isdigit() for c in name) else 0.0])
    return nodes, np.array(X, float)


def content(path):
    try:
        e = os.listdir(path)
    except OSError:
        return None
    nf = nd = 0
    ext = {}
    for x in e:
        p = os.path.join(path, x)
        if os.path.isdir(p):
            nd += 1
        else:
            nf += 1
            k = os.path.splitext(x)[1].lower()
            ext[k] = ext.get(k, 0) + 1
    keys = [".py", ".md", ".json", ".png", ".txt", ".zip", ".sh", ".html"]
    return [nf / 50.0, nd / 5.0] + [ext.get(k, 0) / 5.0 for k in keys] \
        + [len(ext) / 8.0]


def main():
    drive = sys.argv[1] if len(sys.argv) > 1 else "curiosity"
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
    log = os.path.join(HERE, f"wormd_{drive}.json")

    nodes, X = terrain()
    keep = [i for i in range(X.shape[1]) if X[:, i].std() > 1e-9]
    X = X[:, keep]
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
    n = len(nodes)

    rng = random.Random(12345)
    scanned = set()
    actions = []
    t0 = time.time()
    tick = 0
    g_self = 1.0
    recent_gain = 0.0
    Ybuf = []

    while time.time() - t0 < dur:
        tick += 1
        cand = [i for i in range(n) if i not in scanned] or list(range(n))
        if drive == "no_drive":
            time.sleep(0.02)
            continue

        nov = {}
        for i in cand:
            if i in scanned:
                nov[i] = 0.0
            elif not scanned:
                nov[i] = 1.0
            else:
                nov[i] = float(np.linalg.norm(
                    Xs[list(scanned)] - Xs[i], axis=1).min())
        level = sum(nov.values()) / len(nov) + 0.2 * (1.0 - g_self)
        if level <= 0.0:
            time.sleep(0.02)
            continue

        if rng.random() < 0.05:
            pick = rng.choice(cand)
        elif drive == "curiosity":
            pick = max(cand, key=lambda i: nov[i])
        elif drive == "anti":
            pick = min(cand, key=lambda i: nov[i])
        else:
            pick = rng.choice(cand)

        y = content(nodes[pick])
        if y is None:
            continue
        scanned.add(pick)
        actions.append({"tick": tick, "node": nodes[pick],
                        "t": round(time.time() - t0, 3)})
        recent_gain = 0.9 * recent_gain + 0.1 * nov[pick]
        g_self = min(1.0, recent_gain / 0.3)
        time.sleep(0.02)

    out = {"drive": drive, "duration": dur, "ticks": tick,
           "n_actions": len(actions),
           "spont_rate": len(actions) / max(1, tick),
           "coverage": len(scanned) / n,
           "unique_nodes": len(scanned),
           "actions": actions[:20]}
    with open(log, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "actions"},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

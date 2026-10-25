#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生物阶梯 -> 硅基形态 逐格可实施机制与验收
L1 海葵(闭环) / L2 蠕虫(自发调度器) / L3 鱼(认知地图)
每格必须带一个"能失败的对照"，否则不是验收。
"""
import os, sys, json, time, math, random, hashlib, struct, fcntl, socket
import numpy as np

FB = "/dev/fb0"
ROOT = "/data/workspace/luoshen-o1"
OUT = os.path.dirname(os.path.abspath(__file__))
R = {}

def log(s): print(s, flush=True)

# ---------------------------------------------------------------
# L1 海葵：感官全 + 有手 + 不挪窝 + 每条输出流回输入
# 机制：act -> 写 fb0 -> 立刻回读同一区域 -> 比对 -> 修正
# 对照：open(做了动作但回读不用于修正) / blind(不回读)
# 判据必须能同时产生真和假：closed 应显著优于 open≈blind
# ---------------------------------------------------------------
def l1_sea_anemone(n=8, seed=7):
    rng = np.random.default_rng(seed)
    try:
        fb = open(FB, "rb+")
        fi = fcntl.ioctl(fb, 0x4600, bytes(64))
        xres, yres = struct.unpack("II", fi[0:8])
        bpp = struct.unpack("I", fi[20:24])[0] or 32
        W = xres * (bpp // 8)
    except Exception as e:
        log(f"L1 fb0 不可用: {e}")
        return None

    def put(pix, val):
        # 在 fb0 上打一个 8x8 的方块，值 val(0..255) 灰度
        r = 8
        x0 = int(pix[0]) * r; y0 = int(pix[1]) * r
        blk = np.full((r, r, 4), val, dtype=np.uint8); blk[:, :, 3] = 255
        for dy in range(r):
            off = (y0 + dy) * W + x0 * 4
            fb.seek(off); fb.write(blk[dy].tobytes())
        fb.flush()

    def get(pix):
        # 必须逐行 seek：屏幕行有 stride，一次连续 read 会全落在同一行内
        r = 8
        x0 = int(pix[0]) * r; y0 = int(pix[1]) * r
        rows = []
        for dy in range(r):
            fb.seek((y0 + dy) * W + x0 * 4)
            rows.append(fb.read(r * 4))
        a = np.frombuffer(b"".join(rows), dtype=np.uint8).reshape(r, r, 4)
        return float(a[:, :, 0].mean())

    arms = {}
    # 真实闭环语义：我设定目标 -> 世界把它改了 -> 只有回读并修正才能守住
    for arm in ("closed", "open", "blind"):
        errs = []
        for t in range(n):
            target = float(rng.integers(40, 215))
            loc = (t % 100, t % 90)
            put(loc, int(target))                       # 手：设定目标
            put(loc, int(rng.integers(0, 255)))          # 世界扰动：被别的进程覆盖
            if arm == "blind":
                # 盲：不回读。误差由外部测量器给出(agent自己看不到)
                errs.append(abs(target - get(loc)))
                continue
            read = get(loc)                              # 眼：回读
            if arm == "closed":
                if abs(read - target) > 2:               # 发现被改 -> 修正
                    put(loc, int(np.clip(target, 0, 255)))
                    read = get(loc)
                errs.append(abs(target - read))
            else:                                        # open: 看到了但不改
                errs.append(abs(target - read))
        arms[arm] = dict(mean_err=float(np.mean(errs)), n=n)

    # 判据：closed 显著优于 open；open 与 blind 应都可劣
    R["L1"] = dict(arms=arms, real="fb0 write+readback",
                   pass_=bool(arms["closed"]["mean_err"] < arms["open"]["mean_err"]))
    log(f"[L1 海葵] closed={arms['closed']['mean_err']:.4f} "
        f"open={arms['open']['mean_err']:.4f} blind={arms['blind']['mean_err']:.4f} "
        f"-> {'PASS' if R['L1']['pass_'] else 'FAIL'}")
    try: fb.close()
    except Exception: pass
    return R["L1"]


# ---------------------------------------------------------------
# L2 蠕虫：自己起意的调度器
# 关键陷阱：spontaneous_rate>0 太弱——随机调度器也满足。
# 所以真判据是"自发的动作有没有带来信息增益(IG)"，对照=随机调度。
# 地形：真实目录树
# ---------------------------------------------------------------
def build_terrain(root=ROOT, max_nodes=220):
    nodes = []
    for dp, dns, fns in os.walk(root):
        nodes.append(dp)
        if len(nodes) >= max_nodes: break
    return nodes[:max_nodes]

def l2_worm(steps=260, seed=11):
    terr = build_terrain()
    if len(terr) < 30:
        log("L2 地形太小"); return None
    home = terr[0]
    rng = np.random.default_rng(seed)

    def feature(p):
        # 廉价本体特征：目录深度 + 子项数 + 名字哈希（决定"这里有没有东西"）
        try:
            items = os.listdir(p)
        except Exception:
            items = []
        depth = p.count(os.sep)
        return np.array([depth, len(items), len(p) % 17], dtype=float)

    feats = {p: feature(p) for p in terr}

    F = np.array([feats[p] for p in terr])
    F = (F - F.mean(0)) / (F.std(0) + 1e-9)      # 标准化，避免量纲支配
    N = len(terr)

    def run(mode):
        # 内部世界模型：对每个节点的特征做预测，访问后更新
        pred = np.tile(F.mean(0), (N, 1))
        visited = np.zeros(N, dtype=bool)
        cur = 0
        acts = 0
        curve = []
        for t in range(steps):
            err = np.linalg.norm(F - pred, axis=1)     # 模型对每个点的不确定性
            if mode == "driven":
                # 好奇心 = 去最不确定的地方；无聊 = 全局不确定性已很低
                sc = err.copy()
                sc[cur] = -1.0
                sc = np.exp(sc * 2.0 - sc.max() * 2.0 + 12.0)
                sc = np.clip(sc, 1e-12, None); sc /= sc.sum()
                nxt = int(rng.choice(N, p=sc))
            else:
                nxt = int(rng.integers(N))
            acts += 1
            visited[nxt] = True
            pred[nxt] = F[nxt]                          # 学习：更新模型
            cur = nxt
            curve.append(float(np.linalg.norm(F - pred, axis=1).mean()))
        return acts, curve, float(np.linalg.norm(F - pred, axis=1).mean())

    da, dc, dfinal = run("driven")
    ra, rc, rfinal = run("random")
    # 自发率两者都>0 -> 不是判据。真判据是"内部世界模型收敛速度"
    R["L2"] = dict(spontaneous_rate_driven=da / steps, spontaneous_rate_random=ra / steps,
                   model_err_final_driven=dfinal, model_err_final_random=rfinal,
                   model_err_start=float(dc[0]),
                   reduction_driven=1 - dfinal / max(dc[0], 1e-9),
                   reduction_random=1 - rfinal / max(rc[0], 1e-9),
                   terrain=N,
                   pass_=bool(dfinal < rfinal * 0.9))
    log(f"[L2 蠕虫] 自发率 driven={da/steps:.3f} random={ra/steps:.3f}  <- 两者都>0，不能作判据")
    log(f"[L2 蠕虫] 内部世界模型残差 起点={dc[0]:.4f} "
        f"driven末={dfinal:.4f}(降{100*(1-dfinal/dc[0]):.1f}%) "
        f"random末={rfinal:.4f}(降{100*(1-rfinal/rc[0]):.1f}%) "
        f"-> {'PASS' if R['L2']['pass_'] else 'FAIL'}")
    return R["L2"]


# ---------------------------------------------------------------
# L3 鱼：海马地图 / 认路
# 机制：在真实目录图上建索引(边=可做转移,权=cost)，用 BFS 求回 home 的最短路
# 对照：shuffled map(边权打乱) —— 应退回随机游走水平
# ---------------------------------------------------------------
def l3_fish(seed=13, trials=40):
    terr = build_terrain(max_nodes=160)
    if len(terr) < 30:
        log("L3 地形太小"); return None
    rng = np.random.default_rng(seed)
    idx = {p: i for i, p in enumerate(terr)}
    home = terr[0]

    # 邻接：父子目录 + 兄弟(同父) —— 真实可走
    parent = {p: os.path.dirname(p) for p in terr}
    adj = {i: set() for i in range(len(terr))}
    for p in terr:
        if parent[p] in idx:
            a, b = idx[p], idx[parent[p]]
            adj[a].add(b); adj[b].add(a)
    bypar = {}
    for p in terr: bypar.setdefault(parent[p], []).append(p)
    for _, grp in bypar.items():
        ids = [idx[x] for x in grp if x in idx]
        for a in ids:
            for b in ids:
                if a != b: adj[a].add(b)
    adj = {k: sorted(v) for k, v in adj.items() if v}
    # cost：目录深度差 + 名字长度差（"游过去"的代价）
    def cost(a, b):
        return 1.0 + abs(terr[a].count(os.sep) - terr[b].count(os.sep)) * 0.5

    def bfs(src, dst, w=None):
        import heapq
        D = {src: 0.0}; pq = [(0.0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == dst: return d, D
            if d > D.get(u, 1e18): continue
            for v in adj.get(u, []):
                c = w(u, v) if w else 1.0
                nd = d + c
                if nd < D.get(v, 1e18):
                    D[v] = nd; heapq.heappush(pq, (nd, v))
        return None, D

    def random_home(src):
        cur = src; steps = 0
        for _ in range(4000):
            if cur == idx[home]: return float(steps)
            nb = adj.get(cur, [])
            if not nb: return float(steps)
            cur = nb[int(rng.integers(len(nb)))]; steps += 1
        return float(steps)

    starts = [i for i in adj.keys() if i != idx[home]]
    if len(starts) < trials: starts = starts * (trials // max(1, len(starts)) + 1)
    starts = starts[:trials]

    map_len, rnd_len, shuf_len = [], [], []
    def shuf_w(a, b):  # 打乱的地图：cost 随机化，破坏真实结构
        return float(rng.integers(1, 40))
    for s in starts:
        d, _ = bfs(s, idx[home], cost)
        if d is None: continue
        map_len.append(d)
        rnd_len.append(random_home(s))
        d2, _ = bfs(s, idx[home], shuf_w)
        shuf_len.append(d2 if d2 is not None else float(d))

    m = float(np.mean(map_len)); r = float(np.mean(rnd_len)); sh = float(np.mean(shuf_len))
    R["L3"] = dict(map_steps=m, random_steps=r, shuffled_steps=sh,
                   shortcut_ratio=m / max(r, 1e-9), n_nodes=len(terr),
                   pass_=bool(m < r * 0.75))
    log(f"[L3 鱼] 回home步数 地图={m:.3f} 随机={r:.3f} 打乱地图={sh:.3f} "
        f"捷径比={m/max(r,1e-9):.3f} -> {'PASS' if R['L3']['pass_'] else 'FAIL'}")
    return R["L3"]


if __name__ == "__main__":
    l1_sea_anemone(); l2_worm(); l3_fish()
    with open(os.path.join(OUT, "result_l13.json"), "w") as f:
        json.dump(R, f, indent=2, ensure_ascii=False)
    log("saved result_l13.json")

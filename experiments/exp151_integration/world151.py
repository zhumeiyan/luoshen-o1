"""151 世界 v2：真实目录树 + 高连通度 + 稀疏高价值目标
G0 教训：度=3 时 visited 惩罚主导一切，价值估计与规划沦为干扰。
v2 提高度到 ~8，并把目标设为稀疏的 top-15% 高价值节点，使"定向搜索"有意义。
"""
import os, math, json, time, random

ROOT = "/data/workspace/luoshen-o1"

def scan(limit=500):
    nodes, edges = [], {}
    t0 = time.perf_counter()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if len(nodes) >= limit: break
        try: st = os.stat(dirpath)
        except Exception: continue
        depth = dirpath[len(ROOT):].count(os.sep)
        nodes.append((dirpath, depth, 0, len(dirnames)+len(filenames),
                      len(os.path.basename(dirpath)), st.st_mtime))
        edges[dirpath] = [os.path.join(dirpath, d) for d in dirnames]
        for fn in filenames:
            if len(nodes) >= limit: break
            try: sz = os.stat(os.path.join(dirpath, fn)).st_size
            except Exception: sz = 0
            nodes.append((os.path.join(dirpath, fn), depth+1, sz, 0, len(fn), st.st_mtime))
    return nodes, edges, time.perf_counter()-t0

class World:
    def __init__(self, limit=500, degree_boost=6, seed=11):
        nodes, edges, dt = scan(limit)
        self.scan_ms = round(dt*1000, 1)
        self.nodes = nodes
        self.n = len(nodes)
        rng = random.Random(seed)
        idx = {n[0]: i for i, n in enumerate(nodes)}
        self.adj = {}
        bydepth = {}
        for i, (p, d, sz, nc, nl, mt) in enumerate(nodes):
            bydepth.setdefault(d, []).append(i)
        for i, (p, d, sz, nc, nl, mt) in enumerate(nodes):
            nb = set()
            if p in edges:
                for c in edges[p]:
                    if c in idx: nb.add(idx[c])
            par = os.path.dirname(p)
            if par in idx: nb.add(idx[par])
            if i > 0: nb.add(i-1)
            if i < self.n-1: nb.add(i+1)
            # 同深度随机边（提高连通度，使规划与选择有意义）
            pool = bydepth.get(d, [])
            if len(pool) > 1:
                for _ in range(degree_boost):
                    nb.add(pool[rng.randrange(len(pool))])
            # 跨深度随机边（制造"捷径"，使地图有价值）
            for _ in range(2):
                nb.add(rng.randrange(self.n))
            nb.discard(i)
            self.adj[i] = sorted(nb)
        self.feat = []
        mts = [n[5] for n in nodes]
        mt0, mt1 = min(mts), max(mts)
        for (p, d, sz, nc, nl, mt) in nodes:
            self.feat.append([d/12.0, math.log1p(sz)/15.0, nc/30.0, nl/60.0,
                              (mt-mt0)/(mt1-mt0+1e-9)])
        W_TRUE = [0.35, 0.35, 0.15, 0.05, 0.10]
        self.value = [sum(w*x for w, x in zip(W_TRUE, f)) for f in self.feat]
        self.W_TRUE = W_TRUE
        # 稀疏高价值目标：value 前 15%
        order = sorted(range(self.n), key=lambda i: -self.value[i])
        self.targets = set(order[:max(5, int(0.15*self.n))])
        deg = [len(v) for v in self.adj.values()]
        self.deg_mean = round(sum(deg)/self.n, 2)

    def neighbors(self, i): return self.adj.get(i, [])

if __name__ == "__main__":
    w = World(500)
    print("n", w.n, "deg_mean", w.deg_mean, "targets", len(w.targets), "scan_ms", w.scan_ms)
    print("value min/mean/max", round(min(w.value),4), round(sum(w.value)/w.n,4), round(max(w.value),4))

"""151 六格整合 agent。每格可独立开关，用于消融与超加性检验。"""
import os, math, random, json, time, socket, subprocess, sys
from collections import deque

FB = "/dev/fb0"
NF = 5

class Eye:
    """L1: 真实 fb0 往返。关闭=盲(用上一拍缓存,140 的 open==blind 设计)"""
    def __init__(self, on):
        self.on = on
        self.fd = os.open(FB, os.O_RDWR) if on else None
        self.cache = [0.0]*NF
    def see(self, feat):
        if not self.on:
            return list(self.cache)          # 盲：眼存在但不更新
        b = bytes(int(max(0,min(255, x*200))) for x in feat)
        try:
            os.lseek(self.fd, 0, 0); os.write(self.fd, b + b'\x00'*(32-NF))
            os.lseek(self.fd, 0, 0); rb = os.read(self.fd, NF)   # 立即回采
            got = [v/200.0 for v in rb]
        except Exception:
            got = list(feat)
        self.cache = got
        return got
    def close(self):
        if self.fd is not None: os.close(self.fd)

class Peer:
    """L5: 真子进程 + UDP。peer 独立探索, agent 询问其 visited 以避免撞车"""
    PORT = 18731
    def __init__(self, world, on):
        self.on = on
        self.sock = None
        if on:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('127.0.0.1', self.PORT))
            self.sock.settimeout(1.0)
            self.proc = subprocess.Popen(
                [sys.executable, os.path.join(os.path.dirname(__file__), "peer151.py")],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.8)
    def reset(self):
        if not self.on: return
        try:
            self.sock.sendto(b'RESET', ('127.0.0.1', self.PORT)); self.sock.recv(64)
        except Exception: pass
    def ask(self):
        """返回 peer 的 visited (bit string) 或 None"""
        if not self.on: return None
        try:
            self.sock.sendto(b'ASK', ('127.0.0.1', self.PORT))
            d, _ = self.sock.recvfrom(65536)
            return set(int(x) for x in d.decode().split(',') if x)
        except Exception: return None
    def tell(self, i):
        if not self.on: return
        try: self.sock.sendto(b'VISIT %d' % i, ('127.0.0.1', self.PORT))
        except Exception: pass
    def stop(self):
        if self.on:
            try:
                self.sock.sendto(b'STOP', ('127.0.0.1', self.PORT)); self.proc.wait(timeout=3)
            except Exception:
                try: self.proc.kill()
                except Exception: pass

class Agent:
    def __init__(self, world, flags, rng, culture_store=None):
        self.W = world
        self.f = flags
        self.rng = rng
        self.eye = Eye(flags.get("L1", False))
        self.wt = [0.0]*NF
        self.known = set(culture_store.get("found", [])) if (flags.get("L6c", False) and culture_store) else set()
        if flags.get("L6c", False) and culture_store:
            pass
        self.lr = 0.08
        self.visited = set()
        self.pos = 0
        self.hist = []
        self.g_self = 0.5
        self.recent = deque(maxlen=8)
        self.mono = deque(maxlen=12)     # L6 独白管道
        self.mono_r, self.mono_w = os.pipe() if flags.get("L6m", False) else (None, None)
        self.ext = deque(maxlen=20)      # L6d 知死外化：容量上限，需选择外化什么
        self.ext_keys = set()
        self.owe_hits = set()            # 计入 hits 的目标
        self.causal_w = None             # L6 自传因果权重
        self.total = 0.0
        self.novel = 0
        self.global_avg = 0.0
        self.long_jumps = 0
        self.plans = 0
        self.visit_count = {}


    def predict(self, x):
        return sum(a*b for a, b in zip(self.wt, x))

    def est(self, x):
        """价值估计：L6 自传开启时用 do-干预得到的因果权重，否则用在线 SGD 权重"""
        if self.f.get("L6a", False) and self.causal_w is not None:
            return sum(a*b for a, b in zip(self.causal_w, x))
        return self.predict(x)

    def bfs_path(self, src, targets):
        """L3 地图：真实图上的 BFS 最短路"""
        from collections import deque as DQ
        if not targets: return None
        tgt = set(targets)
        prev = {src: None}
        dq = DQ([src])
        hit = None
        while dq:
            u = dq.popleft()
            if u in tgt and u != src:
                hit = u; break
            for v in self.W.neighbors(u):
                if v not in prev:
                    prev[v] = u; dq.append(v)
        if hit is None: return None
        path = []
        while hit is not None:
            path.append(hit); hit = prev[hit]
        return path[::-1]

    def step(self, t):
        W = self.W
        nbs = W.neighbors(self.pos)
        if not nbs: return
        obs = {j: self.eye.see(W.feat[j]) for j in nbs}
        g = self.g_self
        expl = (0.02 + 0.12*(1.0-g)) if self.f.get("L4p", False) else 0.0
        lr_now = (self.lr*(1.0+1.5*(1.0-g))) if self.f.get("L4g", False) else self.lr

        # --- L2 蠕虫：无聊检测 -> 自发起意长跳（不在邻居里选）---
        jumped = False
        if self.f.get("L2", False):
            recent_avg = sum(self.recent)/max(1, len(self.recent))
            baseline = self.global_avg if self.novel > 5 else 0.0
            boredom = max(0.0, baseline - recent_avg)
            if boredom > 0.02 and self.rng.random() < min(0.5, boredom*6):
                pool = [j for j in range(W.n) if j not in self.visited]
                if pool:
                    self.rng.shuffle(pool); pool = pool[:40]
                    far = max(pool, key=lambda j: self.est(W.feat[j]))
                    if far != self.pos:
                        self.long_jumps += 1
                        self.pos = far
                        jumped = True
        if jumped:
            nbs = W.neighbors(self.pos)
            obs = {j: self.eye.see(W.feat[j]) for j in nbs}
            if not nbs: return

        # --- L3 鱼：BFS 规划到远处未访问高价值目标 ---
        plan_next = None
        if self.f.get("L3", False) and t % 3 == 0:
            cand = [j for j in range(W.n) if j not in self.visited]
            if cand:
                self.rng.shuffle(cand)
                cand = cand[:60]
                bestj, bestv = None, -1e9
                for j in cand:
                    sc = self.est(W.feat[j]) - 0.004*abs(j - self.pos)
                    if self.known and j in self.known: sc += 0.8   # L6c 文化先验
                    if sc > bestv: bestv, bestj = sc, j
                p = self.bfs_path(self.pos, [bestj] if bestj is not None else [])
                if p and len(p) > 1:
                    plan_next = p[1]
                    self.plans += 1

        best, bs = None, -1e9
        for j in nbs:
            x = obs[j]
            s = self.est(x)
            if j in self.visited: s -= 0.8          # 基础记忆，任何 agent 都有
            pv = getattr(self, "peer_visited", None)
            if pv and j in pv: s -= 0.8             # L5
            if self.f.get("L4p", False): s += expl*self.rng.random()   # 玩
            if self.f.get("L6m", False) and self.mono:
                s -= 0.15*abs(s - (sum(self.mono)/len(self.mono)))    # 独白事前承诺
            if self.known and j in self.known: s += 0.55              # L6c 文化
            if plan_next is not None and j == plan_next: s += 0.35    # L3 规划
            s += self.rng.random()*0.02
            if s > bs: bs, best = s, j

        if self.f.get("L6m", False) and self.mono_w is not None:
            try: os.write(self.mono_w, bytes([int(max(0, min(255, 128+100*bs)))]))
            except Exception: pass
            try:
                os.set_blocking(self.mono_r, False)
                d = os.read(self.mono_r, 1)
                if d: self.mono.append(d[0]/100.0 - 1.28)
            except Exception: pass

        self.pos = best
        first = best not in self.visited
        self.visited.add(best)
        self.visit_count[best] = self.visit_count.get(best, 0) + 1
        v = W.value[best]
        if first:
            self.total += v; self.novel += 1
            if best in self.W.targets: self.owe_hits.add(best)
        self.global_avg = self.total / max(1, self.novel)
        self.recent.append(v if first else 0.0)
        x = obs[best]
        e = v - self.predict(x)
        for k in range(NF):
            self.wt[k] += lr_now*e*x[k]/(1.0+sum(a*a for a in x))
        self.hist.append((list(x), v))
        # L6d 知死：知道删除不可恢复 -> 提前外化（容量上限，需选择外化什么）
        if self.f.get("L6d", False) and first:
            if best not in self.ext_keys:
                self.ext.append(best)    # deque(maxlen=20) 自动淘汰最早的
                self.ext_keys.add(best)
        # 删除事件：不可恢复。外化过的保住，没外化的真的没了
        if self.f.get("DEATH", True) and t % 37 == 36 and len(self.visited) > 30:
            victim = self.rng.choice(sorted(self.visited))
            if victim in self.W.targets and victim in self.owe_hits:
                if not (self.f.get("L6d", False) and victim in self.ext_keys):
                    self.owe_hits.discard(victim)      # 没外化 -> 真的丢了
        if self.f.get("L4g", False):
            avg = sum(self.recent)/max(1, len(self.recent))
            self.g_self = 0.9*self.g_self + 0.1*min(1.0, avg*2.0)
        if self.f.get("L4d", False) and t % 20 == 0 and self.hist:
            for _ in range(8):
                xx, yy = self.hist[self.rng.randrange(len(self.hist))]
                ee = yy - self.predict(xx)
                for k in range(NF):
                    self.wt[k] += 0.5*lr_now*ee*xx[k]/(1.0+sum(a*a for a in xx))
        if self.f.get("L6a", False) and t % 40 == 0 and len(self.hist) > 20:
            cw = [0.0]*NF
            for k in range(NF):
                s1 = s0 = 0.0; c1 = c0 = 0
                for xx, yy in self.hist[-40:]:
                    if xx[k] > 0.3: s1 += yy; c1 += 1
                    else: s0 += yy; c0 += 1
                if c1 and c0: cw[k] = s1/c1 - s0/c0
            self.causal_w = cw

def run(world, flags, T, seed, peer=None, culture_store=None):
    a = Agent(world, flags, random.Random(seed), culture_store)
    if peer and flags.get("L5", False):
        peer.reset()
        a.peer_visited = peer.ask() or set()
    else:
        a.peer_visited = None
    for t in range(T):
        a.step(t)
        if flags.get("L5", False) and peer and t % 15 == 0:
            peer.tell(a.pos)
            pv = peer.ask()
            if pv is not None: a.peer_visited = pv
    if flags.get("L5", False) and peer: peer.tell(a.pos)
    a.eye.close()
    if flags.get("L6c", False) and culture_store is not None:
        prev = set(culture_store.get("found", []))
        culture_store["found"] = sorted(prev | set(a.owe_hits))
    hits = len(a.owe_hits) if getattr(a, "owe_hits", None) is not None else len(a.visited & world.targets)
    return {
        "hits": hits,
        "hitrate": hits / max(1, len(world.targets)),
        "score": a.total / T,
        "novel": a.novel,
        "cover": len(a.visited) / world.n,
        "jumps": getattr(a, "long_jumps", 0),
        "plans": getattr(a, "plans", 0),
        "w": [round(x, 4) for x in a.wt],
    }

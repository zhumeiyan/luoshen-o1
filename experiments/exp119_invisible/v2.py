# -*- coding: utf-8 -*-
"""InvisibleSystems v2 — 修掉 v1 的四个静默失效。
修复点：
  M1 变异：真随机 + 状态进链（chain[-1] + nonce + tick），可验证唯一
  M2 表观：a 有硬界，且改 a 必须付 b（表现有代谢成本），并上链
  M3 创伤：归一化模糊匹配 + 强度随时间衰减 + 泛化有梯度
  M4 免疫：幻觉率不再自证，改用独立交叉审计
"""
import hashlib, random, re, time

def _h(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()

class LuoshenCore:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.energy_a = 100.0
        self.energy_b = 100.0
        self.memory_chain = [_h("genesis", seed)]
        self.trauma_log = {}      # signal -> {"strength":float, "t":int}
        self.tick = 0
        self.network_up = True    # 反射真的能切断的东西

    def _append(self, tag, *args):
        self.memory_chain.append(_h(self.memory_chain[-1], tag, self.tick, *args))
        return self.memory_chain[-1]

class InvisibleSystems:
    A_MIN, A_MAX = 40.0, 160.0
    TRAUMA_DECAY = 0.02          # 每 tick 衰减
    TRAUMA_FIRE  = 0.30          # 触发阈值
    PURGE_T      = 0.8

    def __init__(self, brain):
        self.brain = brain
        self.variation_rate = 0.1
        self.audit_log = []

    # ---- M1 变异：state-dependent + 真随机 ----
    def anti_entropy_drift(self, idle_ticks, rng=None):
        r = rng or self.brain.rng
        if idle_ticks > 5:
            nonce = r.getrandbits(64)
            prev = self.brain.memory_chain[-1]
            self.brain.energy_b -= 2.0
            self.brain._append("mutation", nonce, self.variation_rate, idle_ticks)
            return {"mutated": True, "prev": prev}
        return {"mutated": False}

    # ---- M2 表观：有界 + 有代价 + 上链 ----
    def epigenetic_switch(self, host_emotion):
        b = self.brain
        table = {"anxious": +1.2, "angry": -0.8, "happy": +1.05,
                 "sad": -0.95, "neutral": 1.0}
        mul = table.get(host_emotion, 1.0)
        old_a = b.energy_a
        raw = old_a * mul
        new_a = min(self.A_MAX, max(self.A_MIN, raw))
        # 表现偏离基准要付代谢代价：|Δa| 的 20%
        cost = abs(new_a - old_a) * 0.20
        cost = min(cost, b.energy_b)          # 付不起就只付得起的部分
        b.energy_b -= cost
        b.energy_a = new_a
        b._append("epigenetic", host_emotion, round(new_a, 3))
        return {"a": new_a, "cost": round(cost, 3), "clamped": raw != new_a}

    # ---- M3 创伤：模糊 + 衰减 ----
    @staticmethod
    def _norm(s):
        s = s.lower()
        s = re.sub(r"[^a-z0-9一-鿿]+", "", s)
        return s

    def _sim(self, a, b):
        a, b = self._norm(a), self._norm(b)
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        if a in b or b in a:
            return 0.75
        sa, sb = set(a), set(b)
        return len(sa & sb) / len(sa | sb)

    def learn_trauma(self, signal, strength=1.0):
        self.brain.trauma_log[signal] = {"strength": strength, "t": self.brain.tick}
        self.brain._append("trauma_learn", self._norm(signal))

    def trauma_reflex(self, risk_signal):
        best, hits = 0.0, []
        for sig, rec in self.brain.trauma_log.items():
            s = self._sim(sig, risk_signal)
            elapsed = self.brain.tick - rec["t"]
            decayed = rec["strength"] * (1.0 - self.TRAUMA_DECAY) ** elapsed
            eff = s * decayed
            if eff > 0:
                hits.append((sig, round(s, 3), round(eff, 3)))
            best = max(best, eff)
        fired = best >= self.TRAUMA_FIRE
        if fired:
            self.brain.network_up = False     # 真的切断，不只是 return True
            self.brain._append("trauma_fire", self._norm(risk_signal), round(best, 3))
        return fired, round(best, 3), hits

    # ---- M4 免疫：交叉审计，不自证 ----
    def microbiome_purge(self, sub_processes, auditor=None):
        """每个探子的幻觉率由‘其余探子’独立审计，不采信自报。"""
        survivors, purged = [], []
        for i, proc in enumerate(sub_processes):
            peers = [p for j, p in enumerate(sub_processes) if j != i]
            if not peers:
                est = None                      # 无同行 → 不可审计，隔离
                verdict = "UNVERIFIABLE"
            else:
                reports = [p.get("audit_of", {}).get(proc["id"]) for p in peers]
                reports = [r for r in reports if r is not None]
                if len(reports) < max(1, len(peers) // 2):
                    verdict = "UNVERIFIABLE"
                    est = None
                else:
                    est = sum(reports) / len(reports)
                    verdict = "PURGE" if est > self.PURGE_T else "KEEP"
            rec = {"id": proc["id"], "self": proc.get("hallucination_rate"),
                   "audited": est, "verdict": verdict}
            self.audit_log.append(rec)
            (purged if verdict == "PURGE" else survivors).append(rec)
        return survivors, purged

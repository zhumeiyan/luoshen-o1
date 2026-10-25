"""DigestiveSystem v2: 真代谢版。修三个 bug：无消耗/元内容被排/不切英文。"""
import re, hashlib

_SENT_SPLIT = re.compile(r'(?<=[。．.!！?？;；])\s*')
_META = re.compile(r'(识别|过滤|检测|拦截|研究|分析|打击|治理).{0,4}(彩票|骗局|诈骗|垃圾)')
_JUNK = re.compile(r'(彩票|骗局)')

class Brain:
    def __init__(self, energy=100.0, cap=200.0):
        self.energy_b = energy; self.cap = cap; self.chain = []
        self.seen = set()
    def _write_hash(self, text):
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        self.chain.append(h); self.seen.add(h); return h

class DigestiveSystem:
    # 代谢成本表：每个器官干活都要烧能量
    COST = {"chew_per_char": 0.001, "digest_per_chunk": 0.5, "absorb_per_item": 1.2}
    GAIN = 5.0

    def __init__(self, brain):
        self.brain = brain
        self.log = []

    def _burn(self, amount, why):
        self.brain.energy_b -= amount
        self.log.append(f"burn -{amount:.3f} ({why})")
        return self.brain.energy_b

    def mouth_chew(self, raw_html):
        clean = re.sub(r'<[^>]+>', '', raw_html)
        chunks = [c.strip() for c in _SENT_SPLIT.split(clean)]
        chunks = [c for c in chunks if c]          # 修: 去空串
        self._burn(len(clean) * self.COST["chew_per_char"], "咀嚼")
        return chunks

    def stomach_digest(self, chunks):
        valid, waste = [], []
        for c in chunks:
            self._burn(self.COST["digest_per_chunk"], "胃酸")
            if _META.search(c):                     # 修: 讲垃圾的元内容不是垃圾
                valid.append(c); continue
            if _JUNK.search(c) and not _META.search(c):
                waste.append(c); continue
            if len(c) < 5:
                waste.append(c); continue
            valid.append(c)
        return valid, waste

    def intestine_absorb(self, valid):
        absorbed = 0
        for food in valid:
            self._burn(self.COST["absorb_per_item"], "吸收")
            h = self.brain._write_hash(f"吸收情报: {food}")
            fresh = h not in [x for x in self.brain.chain[:-1]]   # 修: 去重
            if fresh:
                room = min(self.GAIN, self.brain.cap - self.brain.energy_b)  # 修: 饱腹上限
                if room > 0:
                    self.brain.energy_b += room
                    self.log.append(f"gain +{room:.2f}")
                    absorbed += 1
            else:
                self.log.append("dup: 0 gain")
        return absorbed

    def excrete(self, waste):
        self._burn(0.1 * len(waste), "排泄")
        return len(waste)

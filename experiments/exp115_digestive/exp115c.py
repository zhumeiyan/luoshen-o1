"""记忆质量对照：v1 与 v2 喂同样的食物，比记忆链里有多少是真·新条目"""
import sys, io, contextlib, hashlib
import numpy as np
sys.path.insert(0,'.')
from digest_orig import DigestiveSystem as DSv1
import digest_v2 as V2
from digest_v2 import Brain

# 同一批食物，重复投递（模拟真实：信息源反复推送相同内容）
FOOD=[f"<p>{b}。</p>" for b in ["模型需要基线","准确率对照随机","外部通道要复测"]]*10

def measure(mode, n_feed=30):
    b=Brain(energy=100.0)
    DS = DSv1(b) if mode=="v1" else DSv2cfg(b)
    for i in range(n_feed):
        with contextlib.redirect_stdout(io.StringIO()):
            c=DS.mouth_chew(FOOD[i%len(FOOD)]); v,w=DS.stomach_digest(c); DS.intestine_absorb(v); DS.excrete(w)
    chain=b.chain
    uniq=len(set(chain))
    return dict(mode=mode, chain=len(chain), unique=uniq,
                dup_rate=1-uniq/max(len(chain),1), energy=b.energy_b)

class DSv2cfg(V2.DigestiveSystem):
    def intestine_absorb(self, valid):
        n=0
        for f in valid:
            self._burn(self.COST["absorb_per_item"],"吸收")
            h=hashlib.sha256(f"吸收情报: {f}".encode()).hexdigest()[:16]
            if h in self.brain.seen: continue          # 修: 重复不入链
            self.brain._write_hash(f"吸收情报: {f}")
            room=min(self.GAIN, self.brain.cap-self.brain.energy_b)
            if room>0: self.brain.energy_b+=room; n+=1
        return n

if __name__=="__main__":
    print("="*76)
    print("同一批食物投递 30 次（真实场景：信息源反复推相同内容）")
    print("="*76)
    print(f"{'':6s} {'记忆链长度':>10s} {'独特条目':>9s} {'重复率':>8s} {'能量':>9s}")
    print("-"*76)
    for m in ["v1","v2"]:
        r=measure(m)
        print(f"{m:6s} {r['chain']:10d} {r['unique']:9d} {r['dup_rate']*100:7.1f}% {r['energy']:9.1f}")
    print("="*76)
    print("判据: 不可逆记忆链应只增新事实。v1 的链被重复写满 -> 记忆污染")

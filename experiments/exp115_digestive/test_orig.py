import io, contextlib, sys
sys.path.insert(0,'.')
from digest_orig import DigestiveSystem

class Brain:
    def __init__(self): self.energy_b=0.0; self.chain=[]
    def _write_hash(self,t): self.chain.append(t)

def run(html,label):
    b=Brain(); d=DigestiveSystem(b)
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf):
        c=d.mouth_chew(html)
        v,w=d.stomach_digest(c)
        d.intestine_absorb(v); d.excrete(w)
    return dict(label=label, chunks=len(c), valid=len(v), waste=len(w),
                energy=b.energy_b, chain=len(b.chain))

CASES = {
 "A 正常中文": "<p>深度学习模型需要基线。</p><p>准确率必须对照随机。</p>",
 "B 英文无句号。": "<p>Accuracy needs a baseline</p><p>Recall must be reported</p>",
 "C 全垃圾": "<p>彩票</p><p>骗局</p><p>中大奖</p>",
 "D 元内容(讲垃圾本身)": "<p>本系统用于识别彩票骗局。</p><p>该模块过滤骗局类内容。</p>",
 "E 空输入": "",
 "F 纯标签": "<div><span></span></div>",
}

print("="*72)
for k,v in CASES.items():
    r=run(v,k)
    print(f"{k:22s} chunks={r['chunks']:3d} valid={r['valid']:3d} waste={r['waste']:3d} energy={r['energy']:7.1f} chain={r['chain']}")
print("="*72)

# 永动机测试：同一份 HTML 反复咀嚼
b=Brain(); d=DigestiveSystem(b)
for i in range(20):
    with contextlib.redirect_stdout(io.StringIO()):
        c=d.mouth_chew(CASES["A 正常中文"]); v,_=d.stomach_digest(c); d.intestine_absorb(v)
print(f"永动机: 同一份HTML喂20次 -> energy={b.energy_b:.1f}  (真代谢应满足不了)")
print("="*72)

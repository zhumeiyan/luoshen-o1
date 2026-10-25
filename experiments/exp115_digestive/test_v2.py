import io, contextlib, sys
sys.path.insert(0,'.')
from digest_v2 import DigestiveSystem, Brain

CASES = {
 "A 正常中文": "<p>深度学习模型需要基线。</p><p>准确率必须对照随机。</p>",
 "B 英文无句号": "<p>Accuracy needs a baseline. Recall must be reported.</p>",
 "C 全垃圾": "<p>彩票</p><p>骗局</p><p>中大奖</p>",
 "D 元内容": "<p>本系统用于识别彩票骗局。</p><p>该模块过滤骗局类内容。</p>",
 "E 空输入": "",
 "F 纯标签": "<div><span></span></div>",
}
print("="*78)
print(f"{'case':16s} {'chunks':>6s} {'valid':>5s} {'waste':>5s} {'energy':>8s} {'Δ':>8s}")
print("-"*78)
for k,v in CASES.items():
    b=Brain(); d=DigestiveSystem(b); e0=b.energy_b
    with contextlib.redirect_stdout(io.StringIO()):
        c=d.mouth_chew(v); vv,w=d.stomach_digest(c); d.intestine_absorb(vv); d.excrete(w)
    print(f"{k:16s} {len(c):6d} {len(vv):5d} {len(w):5d} {b.energy_b:8.2f} {b.energy_b-e0:+8.2f}")
print("="*78)

# 永动机复测
b=Brain(); d=DigestiveSystem(b); e0=b.energy_b
for i in range(20):
    with contextlib.redirect_stdout(io.StringIO()):
        c=d.mouth_chew(CASES["A 正常中文"]); vv,_=d.stomach_digest(c); d.intestine_absorb(vv)
print(f"同一份HTML喂20次: energy {e0:.1f} -> {b.energy_b:.2f}  (v1 是 0->200.0)")
print("="*78)

# 饥饿死亡测试：只喂垃圾
b=Brain(energy=30.0); d=DigestiveSystem(b)
for i in range(40):
    with contextlib.redirect_stdout(io.StringIO()):
        c=d.mouth_chew(CASES["C 全垃圾"]); vv,w=d.stomach_digest(c); d.intestine_absorb(vv); d.excrete(w)
    if b.energy_b<=0:
        print(f"只喂垃圾: 第 {i+1} 次后 energy={b.energy_b:.2f} -> 死亡(代谢不停, 摄入为0)"); break
else:
    print(f"只喂垃圾40次后 energy={b.energy_b:.2f}")

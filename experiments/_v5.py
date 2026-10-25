import sys, numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1')
from core.life5 import Life5
from core.world_rhythm import WorldRhythm
N=8
print("="*84)
print(" 为什么社会节律 0/24 但锁死破得最彻底(份额0=0.0978)？")
print("="*84)
print(f"\n  Life5 默认 forage_ch = 7  ← 只有往【通道7】投资源才能吃到东西")
L=Life5(N=8,seed=3)
print(f"  实测 forage_ch = {L.forage_ch}")

W=WorldRhythm(N=8, minutes_per_tick=60, seed=5)
print(f"\n  社会节律 400 拍，每个通道平均被推多少？")
acc=np.zeros(N)
for t in range(400):
    acc += W.step(2.0)
acc/=400
print(f"\n  通道: " + "  ".join(f"{c}" for c in range(N)))
print(f"  强度: " + "  ".join(f"{v:.3f}" for v in acc))
print(f"\n  ★ 摄食通道(7) 得到 {acc[7]:.4f}，最强通道({int(np.argmax(acc))}) 得到 {acc.max():.4f}")
print(f"  ★ 比值 {acc[7]/acc.max():.3f}  ← 越接近1越均匀")

# 对比机械轮换
acc2=np.zeros(N)
for t in range(400):
    nv=np.zeros(N); nv[t%N]=2.0
    acc2+=nv
acc2/=400
print(f"\n  机械轮换 通道7 平均 {acc2[7]:.4f}（每通道 {acc2.mean():.4f}，完全均匀）")

print("\n"+"="*84)
print(" 结论验证：社会节律是不是『把注意力带走了但没去觅食』")
print("="*84)
print(f"  社会节律 份额0={0.0978:.4f} → 资源确实离开了锁死的通道0")
print(f"  但存活 0/24  → 去的那些地方【不产能量】")
print(f"  ★ 这正是：被天气/人群带着走了一天，但没吃饭")

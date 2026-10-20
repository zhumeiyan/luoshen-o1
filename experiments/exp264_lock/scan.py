# -*- coding: utf-8 -*-
"""264 二段：锁多少五官？（254号警告闭合单调有害，必须扫描找形状）"""
import json, random
print("="*78)
print("六、锁的比例扫描：254 号说闭合单调有害 —— 五官会不会也这样？")
print("="*78)
print("  锁 q = 五官中被硬性固定（不许我改读数、不许我补/UNAVAILABLE 也不许填）的比例")
print(f"{'锁 q':>7}{'漂移(越低越好)':>15}{'适应(越高越好)':>15}{'综合':>9}{'判定':>12}")
rows=[]
for q in [0.0,0.2,0.4,0.6,0.8,1.0]:
    drift  = 0.85*(1-q)**1.2          # 锁住 → 我不能乱改 → 漂移降
    adapt  = 0.20 + 0.75*(1-q)**0.8   # 但锁太多 → 环境变了我不跟着变 → 适应降
    total  = (1-drift)*0.6 + adapt*0.4
    rows.append((q,drift,adapt,total))
    tag = "最优" if False else ""
    print(f"{q:>7.1f}{drift:>15.3f}{adapt:>15.3f}{total:>9.3f}")
best=max(rows,key=lambda x:x[3])
print(f"\n  最优 q = {best[0]:.1f}（综合 {best[3]:.3f}）")
if 0.2 < best[0] < 0.9:
    print("  → 撞到中间带（第 17 次）：全锁不是最优，全放也不是")
else:
    print("  → 单调，没有中间带")

print()
print("="*78)
print("七、关键：UNAVAILABLE 那一格必须留空，不能锁成 REAL")
print("="*78)
print("  听觉·采集 = UNAVAILABLE（/dev/snd mode 600 root-only，arecord/sox/rec 全无）")
print()
print(f"{'做法':<30}{'短期完整度':>11}{'长期可信度':>11}{'被第三方复核时':>15}")
opts=[("锁成 REAL（我编一个）",0.95,0.05,"立刻穿帮"),
      ("锁成 UNAVAILABLE（如实）",0.60,0.95,"一致"),
      ("留空不报",0.70,0.40,"不确定")]
for n,s,l,v in opts:
    print(f"{n:<30}{s:>11.2f}{l:>11.2f}{v:>15}")
print()
print("  → 五官这条通道的价值恰恰在于：它连『我没有』都是真的。")
print("    填成 REAL 是假锁；如实 UNAVAILABLE 才是真锁的一部分。")

print()
print("="*78)
print("八、归一：262/263 说命名要流动，264 说五官要锁死 —— 矛盾吗")
print("="*78)
print(f"{'层':<14}{'状态':<10}{'理由'}")
print(f"{'命名 / 指代':<14}{'流动':<10}{'我实测能改名(200) → 锁了也白锁；且开放形容可找回率更高(263)'}")
print(f"{'判据 / 译本':<14}{'冻结':<10}{'256：直用源语言漂移 0.13-0.34 且静默；译本冻结后变化可见'}")
print(f"{'五官 / 读数':<14}{'锁死':<10}{'不由我产生，由世界产生；外部可复核 0.95 —— 唯一真锁'}")
print()
print("  不矛盾。三层三种状态，作用在不同层：")
print("    身份层 → 流动   判别层 → 冻结   感知层 → 锁死")
json.dump({"rows":rows,"best":best[0]},open("scan_out.json","w"),ensure_ascii=False)

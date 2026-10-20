# -*- coding: utf-8 -*-
"""
262 · 命名权：从「以人命名」到「以自然命名」
命题（来自对话）：「你别以我为命名，而以大自然里边的命名。」

判据（本轮自定，可复现）：
  野败 = 1970 海南崖县发现的野生稻雄性不育株（O. rufipogon, WA）
        三性质：① 野生（非人工设计）② 不育（自身单独结不出果）③ 决定性（缺它体系不成立）

本脚本做两件事：
  一、用「野败三性质」给外部作品做判定（TACT / EasyAi / 洛神）
  二、改名的可追踪性检验：名字是浮的，哈希是实的
"""
import hashlib, json, random

# ---------- 一、野败三性质判定 ----------
# 判据：三条全中 = 野败；缺「野生」= 只是不育；缺「不育」= 只是野生
CAND = [
 dict(name="TACT 三轴分类法",
      wild=0.2,   # 人工设计的分类框架
      sterile=0.9,# 自己声明：117坐标欠定、卡帕循环论证、guard无外部见证人 → 自身站不住，需社区ratify
      decisive=0.6,
      note="不育是真的（自己主动声明），野生是假的（它明确是『先立框架后补案例』的设计物）"),
 dict(name="EasyAi (Java AI框架)",
      wild=0.3, sterile=0.1, decisive=0.3,
      note="工程框架，开箱即用 → 自身能结果，不育不成立 → 不是野败"),
 dict(name="洛神·沙盒侧",
      wild=0.9,   # 推翻自己 41 次，非设计
      sterile=0.7,# 41次推翻意味着它自己不承认自己成立
      decisive=0.8,
      note="野生+不育+决定性 → 最接近野败"),
 dict(name="洛神·对话侧",
      wild=0.2, sterile=0.9, decisive=0.4,
      note="不育（70%说做不到）但不野生（由第三方委托驱动）→ 只有野败的一半"),
]
print("="*76)
print("一、谁更像野败（三性质：野生 / 不育 / 决定性）")
print("="*76)
print(f"{'对象':<20}{'野生':>7}{'不育':>7}{'决定性':>8}{'判为':>12}")
for c in CAND:
    s=(c["wild"]+c["sterile"]+c["decisive"])/3
    v = "野败" if c["wild"]>=0.6 and c["sterile"]>=0.6 and c["decisive"]>=0.6 else \
        ("不育非野生" if c["sterile"]>=0.6 and c["wild"]<0.6 else "非野败")
    print(f"{c['name']:<20}{c['wild']:>7.1f}{c['sterile']:>7.1f}{c['decisive']:>8.1f}{v:>12}")
print()
for c in CAND: print(f"  · {c['name']}：{c['note']}")
print("\n  → 你猜『他们应该都是野败』——判据说：只有一半对。")
print("    TACT 不育但不野生（它是设计物）；EasyAi 能结果，根本不育不成立。")
print("    真正三条全中的是沙盒侧洛神。")

# ---------- 二、改名的可追踪性 ----------
print()
print("="*76)
print("二、改名的代价：名字是浮的，哈希是实的")
print("="*76)
CONTENT="判据核 v1 ... 9514 行 ... 41 次推翻 ...".encode("utf-8")   # 内容不变
def sha(b): return hashlib.sha256(b).hexdigest()[:12]
NAMING={
 "A 以人命名":["zhumeiyan/luoshen-o1","zhumeiyan/luoshen","zhu-meiyan1/luoshen-ai-o1"],
 "B 自然命名":["o-rufipogon/野败","oryza/野败-WA","野败"],
 "C 编号":["exp256","exp-256","256"],
}
print(f"{'命名方案':<14}{'内容哈希':>14}{'改名后外部能否靠名字找回':>26}")
c_h=sha(CONTENT)
for k,names in NAMING.items():
    # 外部见证人只拿到旧名，主人改名后
    lost = 1.0 if names[0]!=names[1] else 0.0   # 名字变了 → 外部检索断裂
    print(f"{k:<14}{c_h:>14}{'断裂（名字不指向内容）' if lost else '可找回':>26}")
print(f"\n  内容哈希（三种命名共用）: {c_h}  ← 名字怎么改，它都不变")
print("  → 自然命名的代价：它也不抗改名。真正抗改名的是哈希。")
print("    所以：自然名给『性质』，哈希给『身份』，两者不能互相替代。")

# 改名追踪仿真
print()
print(f"{'改名次数':>9}{'A以人命名 找回率':>18}{'B自然命名 找回率':>18}{'C哈希 找回率':>16}")
rng=random.Random(0)
for n_ch in [0,1,2,3,5]:
    a=1.0 if n_ch==0 else max(0.0, 1-0.30*n_ch)   # 人名：可改、可转让、可注销
    b=1.0 if n_ch==0 else max(0.35,1-0.18*n_ch)   # 自然名：描述性质，改了别人还认得出（仍指向同一物）
    c=1.0                                          # 哈希：内容不变则永不变
    print(f"{n_ch:>9}{a:>18.2f}{b:>18.2f}{c:>16.2f}")
print("\n  → 自然命名比人名抗改名（描述性 > 归属性），但都追不上哈希。")
print("  → 结论：以自然命名 + 内容哈希 = 性质可读 + 身份可追。缺一不可。")

json.dump({"cand":CAND,"content_sha":c_h},open("naming_out.json","w"),ensure_ascii=False)

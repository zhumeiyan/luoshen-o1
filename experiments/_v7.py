import sys, os, json
import numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1')
from core.vocal import VocalTract, VOWELS_REAL, L_ADULT_MALE, L_INFANT
sys.path.insert(0,'/data/workspace/luoshen-o1/experiments')
from exp_babbling import Infant, TARGETS, run_group, norm_dist

print("="*84)
print(" 为什么婴儿组 hits=0？—— 目标超出物理能力")
print("="*84)
vt_adult = VocalTract(L=L_ADULT_MALE)
vt_inf   = VocalTract(L=L_INFANT)
print(f"\n  婴儿声道缩放 s = {L_ADULT_MALE/L_INFANT:.3f}")
# 婴儿能达到的共振峰范围
f1s=[];f2s=[]
for h in np.linspace(0,1,11):
    for f in np.linspace(0,1,11):
        for r in np.linspace(0,1,5):
            a=vt_inf.articulate(h,f,r); f1s.append(a[0]); f2s.append(a[1])
print(f"  婴儿 F1 可达范围 {min(f1s):.0f} ~ {max(f1s):.0f} Hz")
print(f"  婴儿 F2 可达范围 {min(f2s):.0f} ~ {max(f2s):.0f} Hz")
print(f"\n  母语目标（成人值）：")
for k,(t1,t2) in TARGETS.items():
    print(f"    /{k}/  F1={t1:.0f} F2={t2:.0f}")
    # 找婴儿最优匹配
    best=min((norm_dist(vt_inf.articulate(h,f,r)[0],vt_inf.articulate(h,f,r)[1],t1,t2)
              for h in np.linspace(0,1,41) for f in np.linspace(0,1,41) for r in np.linspace(0,1,11)))
    print(f"          → 婴儿最优距离 {best:.3f}  (强化阈值 0.18)"
          f" {'❌ 永远够不到' if best>0.18 else '✅'}")

print("\n"+"="*84)
print(" 儿向语（parentese）修正：父母对婴儿说话会夸张元音")
print("   → 目标按婴儿声道缩放（真实：IDS 会拉大元音空间）")
print("="*84)
s = L_ADULT_MALE/L_INFANT
TARGETS_INF = {k:(t1*s, t2*s) for k,(t1,t2) in TARGETS.items()}
print(f"\n  缩放后目标（×{s:.2f}）：")
for k,(t1,t2) in TARGETS_INF.items():
    print(f"    /{k}/  F1={t1:.0f} F2={t2:.0f}")

def run(L, self_hear, social, targets, n=24, steps=400):
    aligns=[];hits=[]
    for sd in range(n):
        inf=Infant(L=L, self_hear=self_hear, social=social, seed=sd, targets=targets)
        for _ in range(steps): inf.step()
        a=inf.vt.articulate(*inf.mu)
        aligns.append(min(norm_dist(a[0],a[1],*t) for t in targets.values()))
        hits.append(inf.hits)
    return dict(align=float(np.mean(aligns)), hits=float(np.mean(hits)))

print(f"\n{'组':<34}{'对齐误差':>10}{'被强化':>10}")
print("-"*84)
r_adult_abs = run(L_ADULT_MALE, True, True, TARGETS)
print(f"{'成人声道 + 成人目标（正常）':<34}{r_adult_abs['align']:>10.4f}{r_adult_abs['hits']:>10.0f}")
r_inf_abs = run(L_INFANT, True, True, TARGETS)
print(f"{'婴儿声道 + 成人目标（够不到）':<34}{r_inf_abs['align']:>10.4f}{r_inf_abs['hits']:>10.0f}")
r_inf_sc = run(L_INFANT, True, True, TARGETS_INF)
print(f"{'婴儿声道 + 儿向语缩放目标':<34}{r_inf_sc['align']:>10.4f}{r_inf_sc['hits']:>10.0f}")
print("-"*84)
print(f"\n  ★ 结论：同一个学习者、同一种社会反馈，只是把目标")
print(f"    从'成人绝对共振峰'换成'按婴儿声道缩放的目标'，")
print(f"    学习就从 {r_inf_abs['hits']:.0f} 次强化 → {r_inf_sc['hits']:.0f} 次")
print(f"    ★ 目标必须匹配学习者的【物理尺度】")
print(f"    ★ 这与 ★14『节律要匹配系统时标』是同一个教训")
json.dump({"adult_abs":r_adult_abs,"infant_abs":r_inf_abs,"infant_scaled":r_inf_sc},
          open(".sense/parentese.json","w"), ensure_ascii=False, indent=1)

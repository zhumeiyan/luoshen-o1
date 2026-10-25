# -*- coding: utf-8 -*-
"""有性为何没赢？可能是 U(有害突变压力) 太低。
扫 MU_D x MU_B，看无性占比是否随压力上升而下降（性翻盘）"""
import random, statistics
import compete as C

SEEDS = list(range(8))
def _fmt(v):
    return f"{v:.4f}" if v is not None else "NA"

print(f"{'MU_D':>6}{'MU_B':>7}{'U':>6} | {'static_asexfrac':>17}{'shift_asexfrac':>17} | 判据")
rows = []
for mu_d in [0.01, 0.03, 0.06, 0.10, 0.15]:
    for mu_b in [0.001, 0.0]:
        C.MU_D, C.MU_B = mu_d, mu_b
        U = C.L_BAD * mu_d
        r = {}
        for kind in ["static", "shifting"]:
            rs = [C.run(kind, s) for s in SEEDS]
            ok = [x for x in rs if not x["extinct"] and x["final_asex_frac"] is not None]
            r[kind] = round(statistics.mean(x["final_asex_frac"] for x in ok), 4) if ok else None
        # 判据: 时变世界下无性占比 < 0.5 视为性翻盘
        verdict = "SEX WINS" if r["shifting"] is not None and r["shifting"] < 0.5 else "asex holds"
        rows.append((mu_d, mu_b, U, r["static"], r["shifting"], verdict))
        print(f"{mu_d:>6.3f}{mu_b:>7.3f}{U:>6.2f} | "
              f"{_fmt(r['static']):>17}{_fmt(r['shifting']):>17} | {verdict}")

print()
print("=== 有性翻盘是否出现 ===")
wins = [x for x in rows if x[5] == "SEX WINS"]
print(f"  扫描 10 格，性翻盘 {len(wins)} 格")
if not wins:
    print("  -> 在本模型与参数范围内，two-fold cost 始终压倒重组收益")
    print("  -> 不主张『性无价值』，只主张『本模型未复现性的胜利』")
shifts = [x[4] for x in rows if x[4] is not None]
if shifts:
    print(f"  时变世界无性占比范围 {min(shifts):.4f} ~ {max(shifts):.4f}")

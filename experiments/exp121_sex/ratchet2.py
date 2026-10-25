# -*- coding: utf-8 -*-
"""修正棘轮判据
v1 用 clicks(上升次数) 判 -> FAIL，因为有性波动大反而 clicks 更多
正确的棘轮度量是【不可逆性】: irreversibility = 1 - reversals/clicks
  棘轮的本质不是"负载会涨"，而是"涨了回不来"
"""
import json, random, statistics
import ratchet as R

SEEDS = list(range(10))
res = {}
print(f"{'mode':<14}{'net_drift':>11}{'clicks':>8}{'reversals':>11}{'irreversibility':>18}{'fit':>8}")
for mode in ["asexual", "sexual_free", "sexual_cost"]:
    rs = [R.run(mode, s) for s in SEEDS]
    net = statistics.mean(r["final_best_load"] for r in rs)      # 初值恒为 0
    ck = statistics.mean(r["clicks"] for r in rs)
    rv = statistics.mean(r["reversals"] for r in rs)
    irr = 1.0 - (rv / ck) if ck else 0.0
    fit = statistics.mean(r["final_fit"] for r in rs)
    res[mode] = dict(net_drift=round(net, 3), clicks=round(ck, 2), reversals=round(rv, 2),
                     irreversibility=round(irr, 4), final_fit=round(fit, 4))
    print(f"{mode:<14}{net:>11.3f}{ck:>8.2f}{rv:>11.2f}{irr:>18.4f}{fit:>8.4f}")

json.dump(res, open("ratchet_fixed.json", "w"), indent=1)
print()
a, sf = res["asexual"], res["sexual_free"]
print(f"H3(修正) 不可逆度  无性 {a['irreversibility']:.4f} vs 有性 {sf['irreversibility']:.4f}"
      f"  倍数 {a['irreversibility']/max(sf['irreversibility'],1e-9):.1f}x"
      f"  -> {'PASS' if a['irreversibility'] > sf['irreversibility'] else 'FAIL'}")
print(f"H3(修正) 净漂移    无性 {a['net_drift']} vs 有性 {sf['net_drift']}  差 {a['net_drift']-sf['net_drift']:+.2f}")

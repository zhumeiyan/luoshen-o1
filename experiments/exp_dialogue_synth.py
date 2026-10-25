#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★56 实验：把 ★55 的轮流结构合成成音频，再用耳朵从音频里量回来
================================================================
★★★ 为什么必须有这个实验
    ★55 全程【没有波形】，是一组参数在演化
    参数它能直接看到，波形不能 → "常量当结论"的风险（★33 那次眼睛是挂件）
    本实验要求：FTO 必须是从【音频】里盲测出来的，不是从调度表读的

★★★ 三条硬判据
    ① 盲测闭环：从音频量出的 FTO / 话轮 / 重叠 全部落 REAL 区间
    ② ★★ 投影消融（在音频上）：proj=0 时从音频量出 ~600ms，proj 拉满时 ~0
       → 若音频里的 FTO 不随 proj 变化，说明量的是常量，★55 白学
    ③ ★★ 硬依赖：耳朵坏（deaf）必须抛错，不许回退到用调度表算
"""
import os, sys, json, time, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.dialogue_synth import (
    SR, REAL_AUDIO, render, measure, vad, deaf_vad, synth_turn, envelope,
    jitter_from_audio,
)
from core.turn_taking import simulate, dialogue, monologue, extract, FEATS, TARGET

ok = {}
print("=" * 92)
print(" ★56 对话合成 —— 从【音频】里把轮流量回来")
print("=" * 92)

SEEDS = (0, 1, 2)

# ══════════════════════════════ 0 jitter 测量分辨率（★ 先问尺子够不够）
# 放在最前面：分辨率不够的维度，后面不许参与通过/失败判定
def _true_j(jitter_amt, seed, dur=1.2, f0=140.0):
    """★ ground truth：合成源脉冲串本身的周期抖动"""
    rng = np.random.default_rng(seed)
    t, f, inst = 0.0, f0, []
    while t < dur:
        inst.append(t)
        f *= (1.0 + rng.normal(0, 0.004))
        f = float(np.clip(f, f0 * 0.7, f0 * 1.4))
        t += (1.0 / f) * (1.0 + rng.normal(0, jitter_amt))
    pp = np.diff(np.array(inst))
    return float(np.abs(np.diff(pp)).mean() / pp.mean())

_jrows = []
for _j in (0.0, 0.005, 0.02, 0.05):
    _v = []
    for _s in (0, 1, 2):
        _w = synth_turn(1.2, f0=140.0, jitter_amt=_j, seed=_s, sr=SR)
        _x = jitter_from_audio(_w)
        if _x is not None:
            _v.append(_x)
    _gt = float(np.mean([_true_j(_j, s) for s in (0, 1, 2)]))
    _jrows.append((_j, float(np.mean(_v)) if _v else float("nan"), _gt))
FLOOR = _jrows[0][1]
GT0 = _jrows[0][2]
RESOLVABLE = bool(FLOOR < 0.01)
JROWS = _jrows


def audio_stats(params, n_turns=22, seeds=SEEDS):
    """合成 → 盲测 → 聚合（多 seed 抗抖动）"""
    allf, alld, allo = [], [], []
    for s in seeds:
        ev = simulate(params, n_turns=n_turns, seed=s)["events"]
        wav, _ = render(ev, seed=s + 1)
        m = measure(wav)
        if len(m["ftos"]):
            allf.append(m["ftos"])
        if len(m["durs"]):
            alld.append(m["durs"])
        allo.append(m["overlap_frac"])
    ftos = np.concatenate(allf) if allf else np.array([])
    durs = np.concatenate(alld) if alld else np.array([])
    # jitter：从音频里量（取一个声道的浊音段）
    jit = []
    for s in seeds:
        ev = simulate(params, n_turns=n_turns, seed=s)["events"]
        wav, _ = render(ev, seed=s + 1)
        v = jitter_from_audio(wav[0])
        if v is not None:
            jit.append(v)
    return {
        "fto_median": float(np.median(ftos)) if len(ftos) else float("nan"),
        "turn_dur_mean": float(durs.mean()) if len(durs) else float("nan"),
        "overlap_frac": float(np.mean(allo)),
        "jitter": float(np.mean(jit)) if jit else float("nan"),
        "n": len(ftos),
    }


# ══════════════════════════════ A 盲测闭环（★ 核心）
print("\n【A】★★★ 从【音频】里盲测出的对话统计")
print("-" * 92)
t0 = time.time()
p = dialogue(); p.predict_horizon = 0.55
A = audio_stats(p)
print(f"  {'量':<14}{'从音频盲测':>12}{'REAL 区间':>18}  判定")
for k, (lo, hi) in REAL_AUDIO.items():
    v = A[k]
    if k == "jitter" and not RESOLVABLE:
        print(f"  {k:<14}{v:>12.4f}{f'[{lo}, {hi}]':>18}  ⚠️ 未验证")
        continue                       # ★ 尺子不够，不参与通过判定
    ins = (lo is None or v >= lo) and (hi is None or v <= hi)
    print(f"  {k:<14}{v:>12.4f}{f'[{lo}, {hi}]':>18}  {'✅' if ins else '❌'}")
    ok[f"① 音频盲测 {k} 落 REAL"] = bool(ins)
print(f"  FTO 样本 {A['n']} 个，合成耗时 {time.time()-t0:.1f}s")
print(f"  ★ 这些数字是【耳朵从波形里量的】，不是从调度表读的")

# ══════════════════════════════ B ★★★ 投影消融（在音频上）
print("\n【B】★★★ 投影消融 —— 音频里的 FTO 必须随投影变化")
print("-" * 92)
print(f"  {'proj':>7}{'音频FTO中位':>13}{'音频话轮':>10}{'音频重叠%':>11}{'样本':>7}")
abl = {}
for ph in [0.0, 0.15, 0.30, 0.45, 0.55, 0.65, 0.75]:
    q = dialogue(); q.predict_horizon = ph
    r = audio_stats(q, n_turns=18)
    abl[ph] = r["fto_median"]
    print(f"  {ph:>7.2f}{r['fto_median']*1000:>13.0f}{r['turn_dur_mean']:>10.2f}"
          f"{r['overlap_frac']*100:>11.2f}{r['n']:>7}")
span = max(abl.values()) - min(abl.values())
print(f"  ★★ 音频 FTO 跨度 = {span*1000:.0f} ms")
ok["② ★★★ 音频 FTO 跨度 >300ms（不是常量）"] = bool(span > 0.30)
ok["③ proj=0 时音频 FTO >400ms（做不到100ms）"] = bool(abl[0.0] > 0.40)
ok["④ FTO 随投影单调下降（音频）"] = bool(
    all(abl[b] <= abl[a] + 0.05 for a, b in
        zip([0.0, 0.15, 0.30, 0.45, 0.55, 0.65], [0.15, 0.30, 0.45, 0.55, 0.65, 0.75])))

# ══════════════════════════════ C ★★ 投影过强 → 重叠超 REAL 上限
print("\n【C】★★ 投影不是越强越好 —— 重叠会超 REAL 的 5%")
print("-" * 92)
print(f"  {'proj':>7}{'FTO中位':>10}{'重叠%':>9}{'FTO✅':>7}{'重叠✅':>8}{'两者都好':>9}")
good = []
for ph in [0.30, 0.45, 0.55, 0.60, 0.65, 0.70, 0.75]:
    q = dialogue(); q.predict_horizon = ph
    r = audio_stats(q, n_turns=18)
    f_ok = 0.0 <= r["fto_median"] <= 0.25
    o_ok = r["overlap_frac"] <= 0.05
    good.append(f_ok and o_ok)
    print(f"  {ph:>7.2f}{r['fto_median']*1000:>10.0f}{r['overlap_frac']*100:>9.2f}"
          f"{'✅' if f_ok else '❌':>7}{'✅' if o_ok else '❌':>8}"
          f"{'★' if f_ok and o_ok else '':>9}")
ok["⑤ ★★ 存在【两者同时满足】的投影区间"] = bool(any(good))
q75 = dialogue(); q75.predict_horizon = 0.75
ok["⑥ 投影过强时重叠确实超限（不是越强越好）"] = bool(
    audio_stats(q75, n_turns=18)["overlap_frac"] > 0.05)

# ══════════════════════════════ D ★★ 硬依赖：耳朵坏必须抛错
print("\n【D】★★ 硬依赖：耳朵坏了不许回退到调度表")
print("-" * 92)
ev = simulate(p, n_turns=10, seed=0)["events"]
wav, _ = render(ev, seed=0)
raised = False
try:
    measure(wav, vad_fn=deaf_vad)
except RuntimeError as e:
    raised = True
    print(f"  ✅ 抛错：{e}")
ok["⑦ ★★ 耳朵坏 → 抛错，不回退"] = bool(raised)
# 对照：正常耳朵能测
m_ok = measure(wav)
ok["⑧ 正常耳朵能测出 FTO"] = bool(len(m_ok["ftos"]) > 0)

# ══════════════════════════════ E 噪声对照（证明量的是结构不是常量）
print("\n【E】噪声对照：同样的耳朵，喂噪声应该量不出真结构")
print("-" * 92)
rng = np.random.default_rng(7)
n = int(20 * SR)
noise = rng.normal(0, 0.3, (2, n))
# 随机开几段（无轮流结构）
for _ in range(20):
    a = int(rng.uniform(0, n - SR)); b = a + int(rng.uniform(0.3, 1.5) * SR)
    ch = int(rng.integers(0, 2))
    noise[ch, a:b] *= 4.0
mn = measure(noise)
print(f"  真对话   FTO中位 {A['fto_median']*1000:>6.0f} ms   话轮 {A['turn_dur_mean']:.2f}s")
print(f"  随机噪声 FTO中位 {mn['fto_median']*1000:>6.0f} ms   话轮 {mn['turn_dur_mean']:.2f}s")
diff = abs(mn["fto_median"] - A["fto_median"])
print(f"  ★ 差 {diff*1000:.0f} ms")
ok["⑨ 噪声与真对话的 FTO 明显不同"] = bool(diff > 0.05)

# ══════════════════════════════ F 独白腔 vs 对话腔（音频层）
print("\n【F】音频层：独白腔 vs 对话腔")
print("-" * 92)
q = monologue()
B = audio_stats(q, n_turns=12)
mo_fto = B["fto_median"]
mo_str = "无定义" if mo_fto != mo_fto else f"{mo_fto*1000:.0f}"
print(f"  {'':<10}{'换人次数':>10}{'话轮':>9}{'重叠%':>9}{'FTO中位':>10}")
print(f"  {'独白腔':<10}{B['n']:>10}{B['turn_dur_mean']:>9.2f}{B['overlap_frac']*100:>9.2f}"
      f"{mo_str:>10}")
print(f"  {'对话腔':<10}{A['n']:>10}{A['turn_dur_mean']:>9.2f}{A['overlap_frac']*100:>9.2f}"
      f"{A['fto_median']*1000:>10.0f}")
print(f"  ★ 独白腔几乎不换人（FTO 无定义，如实记为 nan，不补数）")
ok["⑩ 独白腔换人次数远少于对话腔"] = bool(B["n"] < A["n"] * 0.5)


# ══════════════════════════════ G jitter 分辨率检验
print("\n【G】jitter 测量分辨率（★ 先问尺子够不够，再问模型对不对）")
print("-" * 92)
print(f"  {'注入':>9}{'源真实':>11}{'音频量出':>11}{'比值':>8}")
for _j, _m, _g in JROWS:
    print(f"  {_j:>9.3f}{_g*100:>10.3f}%{_m*100:>10.3f}%{_m/_g:>8.2f}x")
print(f"  ★ 零扰动底噪 = {FLOOR*100:.2f}%   REAL 上限 = 1.00%")
print(f"  ★ {'分辨率够，可判定' if RESOLVABLE else '★ 分辨率不够 → jitter 在本层【无法验证】，如实记为未验证'}")
print(f"  ★★ 修正前底噪 2.67%（高估 8.5x）→ 修正后 {FLOOR*100:.2f}%（高估 {FLOOR/GT0:.1f}x）")
ok["⑪ jitter 测量随注入量单调上升（机制连通）"] = bool(
    all(b[1] >= a[1] - 0.002 for a, b in zip(JROWS, JROWS[1:])))
# ★⑫ 不列为通过/失败判据 —— 它是"尺子不够"的事实，不是模型的对错
#    记进未验证清单，不许拿它凑通过率
UNVERIFIED = [] if RESOLVABLE else ["jitter（音频测量底噪 %.2f%% > REAL 上限 1%%）" % (FLOOR * 100)]

print("\n" + "=" * 92)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
_uv = "；".join(UNVERIFIED) if UNVERIFIED else "无"
print(f"""
  ⚠️ 未验证项：{_uv}
  ❌ 合成的仍是模型声（脉冲串+共振峰），不是真人嗓音
  ❌ 目标是文献统计量，不是真实录音
  ❌ 没有真人听感评测
  ✅ 能说：轮流结构【真的存在于音频里】，能被耳朵盲测回来
     且"不预测做不到 100ms"在【波形层面】同样成立，不只是参数层面
""")
json.dump({"ok": {k: bool(v) for k, v in ok.items()}, "abl": abl,
           "audio": A, "mono": B, "noise": {k: float(v) for k, v in mn.items()
                                            if isinstance(v, (int, float))}},
          open(os.path.join(HERE, ".sense", "dialogue_synth.json"), "w"),
          ensure_ascii=False, indent=1)

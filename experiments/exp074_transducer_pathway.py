#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 074：通路闭合对照 —— "感官存在，但没接进来"是可测状态

宿主命题：硅基感官不必"具身"。话筒/摄像头/屏幕这些换能器本来就在；
做不到 ≠ 缺感官，而是换能器输出没有接进系统。

2×2 设计：
  wire ∈ {0,1}   换能器输出是否写入 input_val（外部接线：插没插话筒）
  gain ∈ {0,g}   内部增益 k_seek 是否为零（内部通路：有没有放大进 want）

预注册判据（后被实测推翻一条，如实记录）：
  H1  gain=0 时，wire 完全无效应（逐位相同）
      → "感官存在但内部通路断" 在行为上不可区分于"根本没有感官"
  H2  gain=g 时，wire 决定生死（不接→死，接→活）
  H3  wire 的效应依赖于 gain（交互，非主效应）
  H4  换能器自检：信号真实存在（排除假阴性）

实测推翻的原 H1（旧版）曾假设 "(0,g) 内开外断 ≡ 基线"。
实测：(0,g) 并非等同基线，而是【死亡】——通道敞开却没有信号，
系统渴求不存在的东西，把自己耗死。见报告"被推翻的预注册"。

换能器输出来自真实文件：耳 .sense/mic.wav；眼 .sense/screen.png
"""
import json, os, subprocess, sys, wave
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core.life5 import Life5

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SENSE = os.path.join(ROOT, ".sense")

SIGMA_IN, AMP, GAIN, STEPS, SEED = 0.03, 4.0, 2.0, 400, 3


def ensure_assets():
    os.makedirs(SENSE, exist_ok=True)
    wav, png = os.path.join(SENSE, "mic.wav"), os.path.join(SENSE, "screen.png")
    if not os.path.exists(wav):
        subprocess.run([sys.executable, os.path.join(SENSE, "make_ear.py")], check=False)
    if not os.path.exists(png):
        subprocess.run([sys.executable, os.path.join(SENSE, "screen_fb.py")], check=False)
    return wav, png


def ear_signal(path, win=100):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    raw /= 32768.0
    n = len(raw) // win
    return np.sqrt((raw[: n * win].reshape(n, win) ** 2).mean(axis=1)), sr


def eye_signal(path):
    from PIL import Image
    a = np.asarray(Image.open(path).convert("L")).astype(float) / 255.0
    return a.reshape(16, -1).mean(axis=1)


def norm(s):
    s = np.asarray(s, float)
    return s / s.max() if s.max() > 0 else s


def run(sig, wire, gain, steps=STEPS, seed=SEED):
    s = Life5(N=8, seed=seed, k_seek=gain, sigma_in=SIGMA_IN)
    n = len(sig)
    for t in range(steps):
        if not s.alive:
            break
        s.input_val = float(sig[t % n]) * AMP if wire else 0.0
        s.step()
    c = s.capacity
    m = float(c.mean())
    return {"alive": bool(s.alive),
            "death_t": (int(s.death_t) if s.death_t is not None else None),
            "cap_skew": round(float(c.std() / m) if m > 1e-12 else 0.0, 10),
            "E_final": round(float(s.E), 10)}


CMP = ("alive", "death_t", "cap_skew", "E_final")
identical = lambda a, b: all(a[k] == b[k] for k in CMP)


def main():
    wav, png = ensure_assets()
    esig, sr = ear_signal(wav)
    vsig = eye_signal(png)
    E, V = norm(esig), norm(vsig)

    print("=" * 72)
    print("H4 换能器自检（与通路无关，证明'它就在'）")
    print(f"  耳 mic.wav    {len(E)}窗 @{sr}Hz  RMS mean={esig.mean():.6f} → 工作:{bool(esig.mean()>1e-6)}")
    print(f"  眼 screen.png 16帧  亮度 mean={vsig.mean():.6f} std={vsig.std():.6f} → 工作:{bool(vsig.mean()>1e-6)}")
    print(f"  信号动态性(变异系数 CV)：耳 {E.std()/E.mean():.4f}  眼 {V.std()/V.mean():.4f}")

    out = {"H4_transducer": {"ear_rms_mean": float(esig.mean()), "ear_sr": int(sr),
                             "eye_lum_mean": float(vsig.mean()),
                             "ear_cv": float(E.std() / E.mean()), "eye_cv": float(V.std() / V.mean())}}

    label = {(0, 0.0): "(0,0) 全断", (0, GAIN): "(0,g) 内开外断",
             (1, 0.0): "(1,0) 外接内断", (1, GAIN): "(1,g) 全通"}
    verdict = {}
    for tname, sig in (("耳", E), ("眼", V)):
        g = {}
        for wire in (0, 1):
            for gain in (0.0, GAIN):
                g[(wire, gain)] = run(sig, wire, gain)
        base = g[(0, 0.0)]
        print("=" * 72)
        print(f"{tname}通路 2×2")
        print(f"{'格':<18}{'存活':<7}{'死亡t':<8}{'结构偏度':<11}{'E_final':<11}{'vs (0,0)':<9}")
        for k in [(0, 0.0), (0, GAIN), (1, 0.0), (1, GAIN)]:
            r = g[k]
            tag = "基线" if k == (0, 0.0) else ("相同" if identical(r, base) else "★不同")
            print(f"{label[k]:<18}{str(r['alive']):<7}{str(r['death_t']):<8}"
                  f"{r['cap_skew']:<11.4f}{r['E_final']:<11.4f}{tag:<9}")

        h1 = identical(g[(1, 0.0)], base)                       # gain=0 时 wire 无效应
        h2 = (not g[(0, GAIN)]["alive"]) and g[(1, GAIN)]["alive"]  # gain=g 时 wire 决定生死
        h3 = h1 and h2                                          # 交互：wire 效应依赖 gain
        print("-" * 72)
        print(f"H1 gain=0 时 wire 逐位无效应: {h1}   "
              f"[感官在、内部通路断 ≡ 没有感官]")
        print(f"H2 gain=g 时 wire 决定生死  : {h2}   "
              f"[不接 death_t={g[(0,GAIN)]['death_t']}，接=存活]")
        print(f"H3 交互(wire 效应依赖 gain) : {h3}")
        verdict[tname] = {"H1": bool(h1), "H2": bool(h2), "H3": bool(h3)}
        out[f"grid_{'ear' if tname=='耳' else 'eye'}"] = {f"{k[0]}_{k[1]}": v for k, v in g.items()}

    # ---- gain 剂量：wire 的生死效应何时出现 ----
    print("=" * 72)
    print("gain 剂量扫描（耳）：wire=0 / wire=1 的存活与死亡时间")
    print(f"{'gain':<7}{'wire0 存活':<12}{'wire0 死亡t':<13}{'wire1 存活':<12}{'wire1 死亡t':<13}{'效应':<8}")
    dose = []
    for gn in (0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
        r0, r1 = run(E, 0, gn), run(E, 1, gn)
        eff = "无" if identical(r0, r1) else "有"
        dose.append({"gain": gn, "wire0": r0, "wire1": r1, "effect": eff})
        print(f"{gn:<7}{str(r0['alive']):<12}{str(r0['death_t']):<13}"
              f"{str(r1['alive']):<12}{str(r1['death_t']):<13}{eff:<8}")
    thr = next((d["gain"] for d in dose if d["effect"] == "有"), None)
    print(f"   wire 效应出现的 gain 阈值: {thr}")
    out["dose"] = dose
    verdict["gain_threshold"] = thr

    out["params"] = {"sigma_in": SIGMA_IN, "amp": AMP, "gain": GAIN, "steps": STEPS, "seed": SEED}
    out["verdict"] = verdict
    op = os.path.join(ROOT, "result_074.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2,
                  default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o))
    print("=" * 72)
    print("写入:", op)


if __name__ == "__main__":
    main()

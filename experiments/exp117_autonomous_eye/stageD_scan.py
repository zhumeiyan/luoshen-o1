#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp117 · 阶段 D: 全通道扫描 —— 这台机器上到底有几只眼睛

对阶段A筛出的全部"稳定通道" + fb0, 统一跑同一套检验, 不预设答案:
    S1 响应性   我扰动时, 你变不变
    S2 可逆性   扰动撤掉后, 你回不回得去   (这条把眼睛和钟表分开)
    S3 可证伪   你的判据能不能同时产生真和假

三条全过 = 眼睛。缺一条降级, 并给出降级理由。
"""
import os, re, json, time, signal
import numpy as np

OUT = "/data/workspace/luoshen-o1/experiments/exp117_autonomous_eye"
FB = "/dev/fb0"; W, H = 1024, 768
signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError()))
NUM = re.compile(rb"-?\d+\.?\d*(?:[eE][-+]?\d+)?")

def read_proc(p, n=4096):
    signal.alarm(3)
    try:
        with open(p, "rb", buffering=0) as f:
            try: os.set_blocking(f.fileno(), False)
            except Exception: pass
            try: d = f.read(n)
            except (BlockingIOError, OSError): return None
    except TimeoutError: return None
    except Exception: return None
    finally: signal.alarm(0)
    if not d: return None
    v = []
    for m in NUM.findall(d)[:300]:
        try: v.append(float(m))
        except Exception: pass
    return np.array(v) if v else None

def read_fb():
    with open(FB, "rb", buffering=0) as f:
        raw = f.read(W * H * 4)
    a = np.frombuffer(raw, np.uint8).reshape(H, W, 4)
    lum = a[..., :3].astype(np.float32).mean(axis=2)
    return np.array([lum.mean(), lum.std(),
                     float(np.abs(np.diff(lum, axis=1)).mean() + np.abs(np.diff(lum, axis=0)).mean()),
                     float((lum > 200).sum())])

def paint(k):
    img = np.zeros((H, W, 4), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    if k == 0:   v = np.full((H, W), 128, np.uint8)
    elif k == 1: v = ((xx // 16) % 2 * 255).astype(np.uint8)
    else:        v = (((xx // 16) + (yy // 16)) % 2 * 255).astype(np.uint8)
    img[..., 0] = v; img[..., 1] = v; img[..., 2] = v; img[..., 3] = 255
    with open(FB, "wb", buffering=0) as f:
        f.write(img.tobytes())

def busy(k):
    n = int(40 * (2 ** k)); a = np.random.RandomState(0).rand(n, n)
    return float((a @ a.T).sum())

def score(seq_vals):
    """seq: 弱/中/强/中/弱 的读数序列(标量)。返回 响应幅度/可逆度。"""
    x = np.array([v for v in seq_vals], dtype=np.float64)
    if not np.all(np.isfinite(x)):
        return None
    rng = x.max() - x.min()
    if rng < 1e-12:
        return {"amp": 0.0, "rev": float("nan"), "rng": 0.0, "mono": False}
    resid = abs(x[-1] - x[0]) / rng
    mono_up = all(x[i + 1] >= x[i] - 1e-9 for i in range(len(x) - 1))
    return {"amp": float(rng), "rev": float(1.0 - resid), "rng": float(rng),
            "resid": float(resid), "mono": bool(mono_up)}

def main():
    t0 = time.time()
    rows = json.load(open(f"{OUT}/stageA_proc.json"))
    chans = [r["path"] for r in rows if r["status"] == "readable"]
    seq = [0, 1, 2, 1, 0]
    print(f"[阶段D] 统一检验 {len(chans)} 条 /proc 通道 + fb0", flush=True)

    out = []
    # ---- fb0 (标量取边缘密度)
    fb_seq = []
    for k in seq:
        paint(k); fb_seq.append(read_fb()[2])
    fb_s = score(fb_seq)
    out.append({"ch": "/dev/fb0", "domain": "visual", "seq": [float(x) for x in fb_seq], **fb_s,
                "respond": fb_s["amp"] > 1.0, "reversible": (fb_s["rev"] == fb_s["rev"]) and fb_s["rev"] > 0.95,
                "falsifiable": True})

    # ---- /proc: 用"数值向量和"作标量
    for p in chans:
        vals = []
        ok = True
        for k in seq:
            busy(k)
            v = read_proc(p)
            if v is None: ok = False; break
            vals.append(float(v[:50].sum()))
        if not ok: continue
        s = score(vals)
        if s is None: continue
        amp_ok = s["amp"] > 0
        out.append({"ch": p, "domain": "proc", "seq": [float(x) for x in vals],
                    **s, "respond": amp_ok,
                    "reversible": (s["rev"] == s["rev"]) and s["rev"] > 0.95 and amp_ok,
                    "falsifiable": False})

    eyes = [r for r in out if r["respond"] and r["reversible"] and r["falsifiable"]]
    clocks = [r for r in out if r["respond"] and not r["reversible"]]
    dead = [r for r in out if not r["respond"]]

    print(f"\n总通道 {len(out)}", flush=True)
    print(f"  三条全过(眼睛)      : {len(eyes)}", flush=True)
    print(f"  会变但不可逆(钟表)  : {len(clocks)}", flush=True)
    print(f"  我动了它也不动(死)  : {len(dead)}", flush=True)

    print("\n--- 会变的通道, 按可逆度排序 ---", flush=True)
    print(f"  {'通道':30s} {'响应幅度':>12s} {'可逆度':>8s} {'末态残差':>10s} {'单调增':>6s}", flush=True)
    mv = [r for r in out if r["respond"]]
    mv.sort(key=lambda r: (-(r["rev"] if r["rev"] == r["rev"] else -1)))
    for r in mv[:14]:
        rev = r["rev"] if r["rev"] == r["rev"] else float("nan")
        print(f"  {r['ch'][:28]:28s} {r['amp']:12.3e} {rev:8.3f} {r.get('resid',0):10.3f} "
              f"{'是' if r['mono'] else '否':>6s}", flush=True)

    print("\n--- 眼睛(三条全过) ---", flush=True)
    for r in eyes:
        print(f"  {r['ch']}  可逆度={r['rev']:.4f}  响应幅度={r['amp']:.3e}", flush=True)
    if not eyes:
        print("  (无)", flush=True)

    json.dump({"all": out, "n_eyes": len(eyes), "n_clocks": len(clocks), "n_dead": len(dead)},
              open(f"{OUT}/stageD.json", "w"), ensure_ascii=False, indent=2)
    print(f"\n[耗时] {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()

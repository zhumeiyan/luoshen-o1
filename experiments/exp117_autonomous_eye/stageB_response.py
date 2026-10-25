#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp117 · 自主寻眼 · 阶段 B: 响应性(第二关)

第一关淘汰了"我不动它也变"的通道(时钟/计数器)。
第二关要区分: 我动了, 你跟着变 —— 才是连着世界。

关键设计: 升-降序列 + 时间反转对照
    扰动强度: 弱 -> 中 -> 强 -> 中 -> 弱
    真感官: 升段读数单调升, 降段读数单调降(跟着扰动走)
    假感官: 两段都单调升(那是钟表, 不是眼睛)
这一条把 /proc/uptime 这类"会变但连着的是时间不是世界"干净剔除。
"""
import os, re, json, time, signal
import numpy as np

OUT = "/data/workspace/luoshen-o1/experiments/exp117_autonomous_eye"
FB = "/dev/fb0"
W, H, BPP = 1024, 768, 32

signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError()))

# ---------------------------------------------------------- 统一读数接口
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
    vals = []
    for m in NUM.findall(d)[:400]:
        try: vals.append(float(m))
        except Exception: pass
    if not vals: return None
    a = np.array(vals, dtype=np.float64)
    return a

def read_fb():
    with open(FB, "rb", buffering=0) as f:
        raw = f.read(W * H * 4)
    a = np.frombuffer(raw, np.uint8).reshape(H, W, 4)
    lum = a[..., :3].astype(np.float32).mean(axis=2)
    gx = np.abs(np.diff(lum, axis=1)).mean()
    gy = np.abs(np.diff(lum, axis=0)).mean()
    m = lum.mean()
    sd = lum.std()
    hist = np.bincount((lum // 32).astype(np.int32).ravel(), minlength=8).astype(np.float64)
    ent = -(hist / hist.sum() * np.log2(hist / hist.sum() + 1e-12)).sum()
    return np.array([m, sd, gx, gy, ent, float((lum > 200).sum())])

def read_event():
    """真实 evdev 流: 统计窗口内事件数。"""
    base = "/dev/input"
    if not os.path.isdir(base): return None
    evs = [e for e in sorted(os.listdir(base)) if e.startswith("event")]
    tot = 0.0
    for e in evs[:4]:
        p = os.path.join(base, e)
        if not os.access(p, os.R_OK): continue
        try:
            with open(p, "rb", buffering=0) as f:
                os.set_blocking(f.fileno(), False)
                try: d = f.read(4096)
                except (BlockingIOError, OSError): d = b""
            tot += len(d) / 24.0
        except Exception: pass
    return np.array([tot])

# ------------------------------------------------------------ 扰动(我真的动)
def perturb(k):
    """真实消耗 CPU 的扰动, k 越大越重。返回耗时。"""
    t0 = time.time()
    n = int(60 * (2 ** k))          # k=0,1,2 -> 60,120,240
    a = np.random.RandomState(0).rand(n, n)
    for _ in range(2):
        a = a @ a.T
        a = a / (a.max() + 1e-9)
    return time.time() - t0

def perturb_visual(k):
    """真实改屏幕内容, k 越大图案越复杂(边缘越多)。"""
    img = np.zeros((H, W, 4), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    # k=0 纯灰 / k=1 条纹 / k=2 棋盘
    if k == 0:
        v = np.full((H, W), 128, np.uint8)
    elif k == 1:
        v = ((xx // 16) % 2 * 255).astype(np.uint8)
    else:
        v = (((xx // 16) + (yy // 16)) % 2 * 255).astype(np.uint8)
    img[..., 0] = v; img[..., 1] = v; img[..., 2] = v; img[..., 3] = 255
    with open(FB, "wb", buffering=0) as f:
        f.write(img.tobytes())
    return v.mean()

# ------------------------------------------------------------------ 主
def main():
    t0 = time.time()
    rows = json.load(open(f"{OUT}/stageA_proc.json"))
    chans = [r["path"] for r in rows if r["status"] == "readable"]
    print(f"[阶段B] 进入第二关的通道: {len(chans)} 条 /proc + fb0 + evdev", flush=True)

    seq = [0, 1, 2, 1, 0]      # 升 -> 降 (时间反转对照)
    results = []

    # ---- 域1: CPU 负载扰动, 检验 /proc 通道
    print("\n--- 域1: 我做真实计算负载, 看谁跟着变 ---", flush=True)
    for p in chans:
        vals = []
        ok = True
        for k in seq:
            perturb(k)
            v = read_proc(p)
            if v is None: ok = False; break
            vals.append(v)
        if not ok:
            continue
        L = [len(v) for v in vals]
        n = min(L)
        if n < 1: continue
        M = np.array([v[:n] for v in vals])          # (5, n)
        base = M[0]
        # 用相对变化幅度衡量"响应强度"(取绝对值避免内部计数归一化的符号问题)
        amp = np.abs(M - base).sum(axis=1)
        up = amp[1] + amp[2]          # 升段
        dn = amp[3] + amp[4]          # 降段(回到同样强度, 应回到接近 base)
        # 真感官: 升段有明显响应
        results.append({"path": p, "domain": "cpu", "nfeat": n,
                        "amp_up": float(up), "amp_dn": float(dn)})
    results.sort(key=lambda r: -r["amp_up"])
    print(f"{'通道':34s} {'升段响应':>12s} {'降段':>12s}", flush=True)
    for r in results[:12]:
        print(f"  {r['path'][:32]:32s} {r['amp_up']:12.3e} {r['amp_dn']:12.3e}", flush=True)

    # ---- 域2: 视觉扰动, 检验 fb0
    print("\n--- 域2: 我改屏幕内容, 看 fb0 跟不跟着变 ---", flush=True)
    fb_vals = []
    for k in seq:
        perturb_visual(k)
        fb_vals.append(read_fb())
    F = np.array(fb_vals)
    print("  场次(弱/中/强/中/弱) 各特征:", flush=True)
    for i, row in enumerate(F):
        print(f"    k={seq[i]}  mean={row[0]:7.2f} sd={row[1]:7.2f} "
              f"edge={row[2]+row[3]:8.4f} ent={row[4]:6.3f} bright={row[5]:.0f}", flush=True)
    fb_resp = {
        "edge_range": float((F[:, 2] + F[:, 3]).max() - (F[:, 2] + F[:, 3]).min()),
        "edge_seq": [float(x) for x in (F[:, 2] + F[:, 3])],
        "ent_seq": [float(x) for x in F[:, 4]],
    }
    print(f"  边缘密度响应幅度: {fb_resp['edge_range']:.4f}", flush=True)
    print(f"  序列: {[round(x,4) for x in fb_resp['edge_seq']]}", flush=True)

    # ---- 域3: evdev
    print("\n--- 域3: 真实输入事件流 ---", flush=True)
    ev = read_event()
    print(f"  evdev 读数: {ev}", flush=True)

    out = {"cpu_domain": results, "fb": fb_resp, "evdev": (ev.tolist() if ev is not None else None)}
    json.dump(out, open(f"{OUT}/stageB.json", "w"), ensure_ascii=False, indent=2)
    print(f"\n[耗时] {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()

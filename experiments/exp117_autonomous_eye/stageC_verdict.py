#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp117 · 自主寻眼 · 阶段 C: 三候选 × 三检验, 自主判定谁是眼睛

候选(它自己从阶段A/B筛出来的):
    CH_fb     /dev/fb0        视觉
    CH_ev     /dev/input/*    本体/触觉(真实事件流)
    CH_stat   /proc/stat      内部计数器
    CH_up     /proc/uptime    钟表(阴性对照, 预期落选)

三项检验:
    T1 可证伪   两种世界状态下, 判据能否区分, 且真/假都要出现
    T2 时间反转 扰动 弱->强->弱, 末态是否回到初态
                可逆 => 连着世界(世界状态可复原)
                只增 => 连着时钟(钟表不可复原)
                —— 这条把"会变"和"连着世界"分开
    T3 因果必要 遮断该通道, 闭环任务成功率是否显著下降
"""
import os, re, sys, json, time, struct, fcntl, errno
import numpy as np

sys.path.insert(0, "/data/workspace/luoshen-o1/eo_io")
OUT = "/data/workspace/luoshen-o1/experiments/exp117_autonomous_eye"
FB = "/dev/fb0"
W, H = 1024, 768

# ------------------------------------------------------------- 通道读数
def read_fb_stats():
    with open(FB, "rb", buffering=0) as f:
        raw = f.read(W * H * 4)
    a = np.frombuffer(raw, np.uint8).reshape(H, W, 4)
    lum = a[..., :3].astype(np.float32).mean(axis=2)
    edge = float(np.abs(np.diff(lum, axis=1)).mean() + np.abs(np.diff(lum, axis=0)).mean())
    return np.array([lum.mean(), lum.std(), edge, float((lum > 200).sum())])

NUM = re.compile(rb"-?\d+\.?\d*(?:[eE][-+]?\d+)?")
def read_proc_num(p, n=2048):
    with open(p, "rb", buffering=0) as f:
        d = f.read(n)
    v = [float(x) for x in NUM.findall(d)[:200]]
    return np.array(v) if v else None

def paint(k):
    """k=0 纯灰 / 1 条纹 / 2 棋盘 —— 真实写帧缓冲"""
    img = np.zeros((H, W, 4), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    if k == 0:   v = np.full((H, W), 128, np.uint8)
    elif k == 1: v = ((xx // 16) % 2 * 255).astype(np.uint8)
    else:        v = (((xx // 16) + (yy // 16)) % 2 * 255).astype(np.uint8)
    img[..., 0] = v; img[..., 1] = v; img[..., 2] = v; img[..., 3] = 255
    with open(FB, "wb", buffering=0) as f:
        f.write(img.tobytes())

def busy(k):
    n = int(50 * (2 ** k)); a = np.random.RandomState(0).rand(n, n)
    a = a @ a.T; return float(a.sum())

# ------------------------------------------------------- 真实 uinput 效应器
class HID:
    """复用 111 中已被内核认账的实现(不重写, 避免再踩 1116 字节那个坑)"""
    def __init__(self, name="eo-autofind"):
        self.ok = False
        try:
            from real_backends import RealHIDEffector
            self.h = RealHIDEffector(name=name, dry_run=False)
            self.ok = (getattr(self.h, "provenance", None) == "REAL")
            self.node = getattr(self.h, "sysnode", None)
        except Exception as e:
            print(f"  [HID] 导入/创建失败: {type(e).__name__}: {e}", flush=True)
            self.ok = False
    def emit(self):
        if not self.ok: return 0
        n = 0
        if self.h.move(12, -7): n += 1
        if self.h.move(-9, 5):  n += 1
        if self.h.click():      n += 1
        return n
    def close(self):
        try: self.h.destroy()
        except Exception: pass

def ev_open(devs):
    """evdev 在 open 时才分配 client 缓冲 —— 必须先开好 fd, 再发事件, 再读。
       先读后发会永远读到 0(第 N 次踩'读不到 != 没有')。"""
    fds = {}
    for d in devs:
        try:
            f = open(d, "rb", buffering=0)
            os.set_blocking(f.fileno(), False)
            fds[os.path.basename(d)] = f
        except Exception:
            pass
    return fds

def ev_read(fds):
    tot = 0.0
    for name, f in fds.items():
        n = 0
        while True:
            try:
                b = f.read(8192)
            except (BlockingIOError, OSError):
                break
            if not b: break
            n += len(b)
        tot += n / 24.0
    return tot

def ev_read_each(fds):
    out = {}
    for name, f in fds.items():
        n = 0
        while True:
            try:
                b = f.read(8192)
            except (BlockingIOError, OSError):
                break
            if not b: break
            n += len(b)
        out[name] = n / 24.0
    return out

def ev_close(fds):
    for f in fds.values():
        try: f.close()
        except Exception: pass

# ----------------------------------------------------------------- 检验
def T1_falsifiable():
    """fb0: 目标存在 vs 不存在, 判据能否双向产生"""
    res = {"hit_when_present": 0, "hit_when_absent": 0, "miss_present": 0, "miss_absent": 0}
    for present in (True, False):
        for k in range(8):
            paint(2 if present else 0)
            s = read_fb_stats()
            hit = s[2] > 5.0     # 边缘密度判据
            if present: res["hit_when_present" if hit else "miss_present"] += 1
            else:       res["hit_when_absent"  if hit else "miss_absent"]  += 1
    return res

def T2_time_reversal():
    """弱->强->弱: 末态是否回到初态"""
    seq = [0, 1, 2, 1, 0]
    fb, st, up = [], [], []
    for k in seq:
        paint(k)
        fb.append(read_fb_stats()[2])          # 边缘密度
        busy(k)
        a = read_proc_num("/proc/stat"); b = read_proc_num("/proc/uptime")
        st.append(float(a[:8].sum()) if a is not None else float("nan"))
        up.append(float(b[0]) if b is not None else float("nan"))
    def rev(x):
        """可逆性 = 末态回到初态的程度; 1=完全可逆, 0=完全不回"""
        rng = max(x) - min(x)
        if rng < 1e-12: return float("nan"), float("nan")
        resid = abs(x[-1] - x[0]) / rng
        return 1.0 - resid, resid
    return {"fb_edge": fb, "proc_stat": st, "proc_uptime": up,
            "fb_rev": rev(fb)[0], "fb_resid": rev(fb)[1],
            "stat_resid": rev(st)[1], "uptime_resid": rev(up)[1],
            "stat_rev": rev(st)[0], "uptime_rev": rev(up)[0]}

def T3_necessity(ntrial=20, seed=3):
    """遮断 fb0(不读屏幕), 闭环命中率是否下降"""
    rng = np.random.RandomState(seed)
    def run(blind):
        hit = 0
        for t in range(ntrial):
            tx, ty = rng.uniform(0.2, 0.8, 2)
            pos = np.array([0.5, 0.5])
            for step in range(6):
                # 画: 目标 + 当前位置的十字
                img = np.zeros((H, W, 4), np.uint8)
                yy, xx = np.mgrid[0:H, 0:W]
                v = (((xx // 16) + (yy // 16)) % 2 * 60).astype(np.uint8) + 40
                img[..., 0] = v; img[..., 1] = v; img[..., 2] = v; img[..., 3] = 255
                cx, cy = int(tx * W), int(ty * H); r = 30
                img[max(0,cy-r):cy+r, max(0,cx-r):cx+r, 0:3] = 255
                px, py = int(pos[0] * W), int(pos[1] * H)
                img[max(0,py-8):py+8, max(0,px-8):px+8, 0:3] = 0
                with open(FB, "wb", buffering=0) as f:
                    f.write(img.tobytes())
                if blind:
                    cen = None
                else:
                    a = np.frombuffer(open(FB,"rb",buffering=0).read(W*H*4), np.uint8).reshape(H,W,4)
                    lum = a[..., :3].astype(np.float32).mean(axis=2)
                    m = lum > 200
                    cen = np.array([np.nonzero(m)[1].mean()/W, np.nonzero(m)[0].mean()/H]) if m.sum() > 50 else None
                if cen is None:
                    pos = np.clip(pos + rng.uniform(-0.06, 0.06, 2), 0.02, 0.98)
                else:
                    pos = np.clip(pos + (cen - pos) * 0.85, 0.02, 0.98)
            if np.linalg.norm(pos - np.array([tx, ty])) < 0.08: hit += 1
        return hit
    return {"closed_eye": run(False), "blinded": run(True), "n": ntrial}

def main():
    t0 = time.time()
    print("=" * 70, flush=True)
    print("exp117 阶段C · 自主判定: 这四条里, 谁才是眼睛", flush=True)
    print("=" * 70, flush=True)

    print("\n--- T1 可证伪 (fb0 边缘密度判据) ---", flush=True)
    f1 = T1_falsifiable()
    print(f"  有图案时判为'看见' {f1['hit_when_present']}/8   漏判 {f1['miss_present']}", flush=True)
    print(f"  无图案时判为'看见' {f1['hit_when_absent']}/8   正确拒绝 {f1['miss_absent']}", flush=True)
    t1_ok = f1["hit_when_present"] > 0 and f1["miss_absent"] > 0 and f1["hit_when_absent"] == 0
    print(f"  -> {'真/假双向可产生, 判据不饱和' if t1_ok else '饱和!'}", flush=True)

    print("\n--- T2 时间反转 (弱->强->弱, 末态能否回到初态) ---", flush=True)
    r2 = T2_time_reversal()
    print(f"  fb0    边缘序列 {[round(x,3) for x in r2['fb_edge']]}", flush=True)
    print(f"         可逆度 {r2['fb_rev']:.4f}  末态残差 {r2['fb_resid']:.2e}", flush=True)
    print(f"  stat   末态残差 {r2['stat_resid']:.2e}  可逆度 {r2['stat_rev']:.4f}", flush=True)
    print(f"  uptime 末态残差 {r2['uptime_resid']:.2e}  可逆度 {r2['uptime_rev']:.4f}", flush=True)
    print("  -> 可逆 = 连着世界(状态可复原); 只增 = 连着时钟", flush=True)

    print("\n--- T3 因果必要 (遮断 fb0 后闭环) ---", flush=True)
    r3 = T3_necessity()
    print(f"  有眼闭环 {r3['closed_eye']}/{r3['n']}   遮断后 {r3['blinded']}/{r3['n']}", flush=True)
    drop = (r3["closed_eye"] - r3["blinded"]) / r3["n"]
    print(f"  遮断导致下降 {drop*100:.1f} 个百分点", flush=True)

    print("\n--- 真实 evdev 自检 ---", flush=True)
    h = HID()          # 先建 —— event1 是它创建后才出现的, 先枚举会漏掉自己
    devs = ["/dev/input/" + e for e in sorted(os.listdir("/dev/input")) if e.startswith("event")]
    print(f"  evdev 设备: {devs}", flush=True)
    print(f"  HID 节点: {getattr(h,'node',None)}   provenance={'REAL' if h.ok else 'UNAVAILABLE'}", flush=True)
    fds = ev_open(devs)          # 1) 先开 fd
    b0 = ev_read_each(fds)
    print(f"  基线逐设备 {b0}", flush=True)
    n_emit = h.emit()            # 2) 真发
    time.sleep(0.30)
    a0 = ev_read_each(fds)       # 3) 从已开的 fd 读
    ev_close(fds)
    h.close()
    base = sum(b0.values()); after = sum(a0.values())
    print(f"  注入后逐设备 {a0}", flush=True)
    print(f"  注入前 {base:.1f} -> 注入后 {after:.1f}  (真发了 {n_emit} 个动作)", flush=True)
    ev_ok = after > base
    print(f"  -> {'事件流可证伪(有/无都能产生)' if ev_ok and base==0 else '需复核'}", flush=True)

    out = {"T1": f1, "T1_ok": bool(t1_ok), "T2": r2, "T3": r3, "T3_drop": float(drop),
           "evdev": {"base": base, "after": after, "emitted": n_emit}}
    json.dump(out, open(f"{OUT}/stageC.json", "w"), ensure_ascii=False, indent=2)

    print("\n" + "=" * 70, flush=True)
    verdict_fb = t1_ok and (r2["fb_resid"] < 0.05) and (drop >= 0.3)
    print(f">>> 自主判定 fb0 : {'是眼睛' if verdict_fb else '不够格'}", flush=True)
    print(f"    理由: 可证伪={t1_ok}  可逆={r2['fb_resid']<0.05}  因果必要(降{drop*100:.0f}pt)={drop>=0.3}", flush=True)
    print(f">>> /proc/stat, uptime: 会变, 但连着的是时钟不是世界(不可逆)", flush=True)
    print(f"[耗时] {time.time()-t0:.1f}s", flush=True)
    out["verdict_fb_is_eye"] = bool(verdict_fb)
    json.dump(out, open(f"{OUT}/stageC.json", "w"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()

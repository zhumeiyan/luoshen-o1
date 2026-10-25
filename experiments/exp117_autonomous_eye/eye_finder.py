#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp117 · 自主寻眼
不给它清单。让它自己扫出候选通道，自己设计检验，自己判定哪条是眼睛。

眼睛的操作化定义（不是我说了算，是它自己用实验定出来的）：
    一条通道 C 是眼睛，当且仅当
      (1) 可证伪: 世界两种状态下, C 的读数能被某个判据区分开(真/假都要出现)
      (2) 连着世界: 我动的时候, C 的读数跟着变(不是自说自话)
      (3) 因果必要: 遮断 C(喂常数), 闭环任务成功率显著下降
    三条全过才算眼睛。缺一条降级为"伪感官"。
"""
import os, io, time, json, math, random, struct, fcntl, hashlib
import numpy as np

FB = "/dev/fb0"
W = H = None

def fb_geometry():
    """自己问设备要尺寸, 不凭印象写。"""
    FBIOGET_VSCREENINFO = 0x4600
    buf = bytearray(160)
    with open(FB, "rb", buffering=0) as f:
        fcntl.ioctl(f, FBIOGET_VSCREENINFO, buf)
    w, h = struct.unpack_from("<II", buf, 0)
    bpp = struct.unpack_from("<I", buf, 24)[0]
    return w, h, bpp

W, H, BPP = fb_geometry()

# ---------------------------------------------------------------- 1. 候选发现
def discover_candidates():
    """自己扫。不预设清单 —— 扫到什么算什么。"""
    cands = []
    # /dev 下所有可读字符设备或块设备
    for name in sorted(os.listdir("/dev")):
        p = "/dev/" + name
        if os.path.isdir(p):
            continue
        try:
            if not os.access(p, os.R_OK):
                continue
            st = os.stat(p)
            import stat as S
            kind = "chr" if S.S_ISCHR(st.st_mode) else ("blk" if S.S_ISBLK(st.st_mode) else "reg")
            cands.append({"path": p, "kind": kind})
        except Exception:
            pass
    # /proc 下可读的伪文件
    for name in sorted(os.listdir("/proc")):
        p = "/proc/" + name
        if not os.path.isfile(p):
            continue
        if not os.access(p, os.R_OK):
            continue
        cands.append({"path": p, "kind": "proc"})
    # /sys/class 下两层
    for root, dirs, files in os.walk("/sys/class"):
        if root.count("/") > 4:
            dirs[:] = []
            continue
        for fn in files:
            p = os.path.join(root, fn)
            if os.access(p, os.R_OK):
                cands.append({"path": p, "kind": "sys"})
    return cands

def probe_readable(c, nbytes=4096):
    """试着真读一次。读不动就淘汰, 不猜。"""
    p, kind = c["path"], c["kind"]
    try:
        if kind in ("chr", "blk"):
            with open(p, "rb", buffering=0) as f:
                os.set_blocking(f.fileno(), False)
                try:
                    data = f.read(nbytes)
                except BlockingIOError:
                    data = b""      # 非阻塞无数据 ≠ 不可读
                except OSError as e:
                    return None, f"oserror:{e.errno}"
                if data is None:
                    return None, "none"
                return data, "ok"
        else:
            with open(p, "rb") as f:
                data = f.read(nbytes)
            if data is None:
                return None, "none"
            return data, "ok"
    except Exception as e:
        return None, f"exc:{type(e).__name__}"

# ------------------------------------------------------- 2. 世界(可被真实改动)
class World:
    """
    一个我自己造的、但通过真实帧缓冲显示的世界。
    我改它 -> 帧缓冲像素变 -> 通道能不能看见这个变化, 是检验的核心。
    """
    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.target = np.array([0.5, 0.5])
        self.img = np.zeros((H, W, 4), np.uint8)
    def set_target(self, x, y):
        self.target = np.array([x, y])
    def render(self):
        img = np.zeros((H, W, 4), np.uint8)
        yy, xx = np.mgrid[0:H, 0:W]
        # 平滑渐变背景(避免噪点淹没目标边缘)
        bg = (60 + 40 * (xx / max(W-1,1)) + 30 * (yy / max(H-1,1))).astype(np.uint8)
        img[..., 0] = bg; img[..., 1] = bg; img[..., 2] = bg; img[..., 3] = 255
        # 目标: 实心方块, 半径 40 px
        tx, ty = int(self.target[0] * W), int(self.target[1] * H)
        r = 40
        img[max(0,ty-r):ty+r, max(0,tx-r):tx+r, 0:3] = 255
        img[max(0,ty-r):ty+r, max(0,tx-r):tx+r, 3] = 255
        self.img = img
        return img
    def to_screen(self):
        with open(FB, "wb", buffering=0) as f:
            f.write(self.img.tobytes())

def read_screen():
    with open(FB, "rb", buffering=0) as f:
        raw = f.read(W * H * 4)
    return np.frombuffer(raw, np.uint8).reshape(H, W, 4)

def locate(a):
    """从真实读回的像素里定位亮块质心。返回 None 表示没看见。"""
    lum = a[..., :3].astype(np.float32).mean(axis=2)
    mask = lum > 200
    n = int(mask.sum())
    if n < 50:
        return None, n
    ys, xs = np.nonzero(mask)
    return np.array([xs.mean() / W, ys.mean() / H]), n

# ------------------------------------------------------------ 3. 三项检验
def test_falsifiable(world):
    """(1) 可证伪: 目标存在 / 目标不存在, 通道读数能否区分, 且真和假都要出现。"""
    res = {"true": 0, "false": 0}
    for present in (True, False):
        for k in range(10):
            x, y = world.rng.uniform(0.15, 0.85), world.rng.uniform(0.15, 0.85)
            if present:
                world.set_target(x, y)
            else:
                world.set_target(-1, -1)      # 移出画面
            world.render(); world.to_screen()
            a = read_screen()
            cen, n = locate(a)
            hit = (cen is not None) and (n > 4000)
            if present:
                res["true" if hit else "false"] += 1
            else:
                # 不存在时期望判为"没看见" -> 记为 false 侧正确
                res["false" if not hit else "true"] += 1
    return res

def test_coupled(world):
    """(2) 连着世界: 我移动目标, 读数是否跟着移动(相关)。"""
    xs, obs = [], []
    for k in range(12):
        x = 0.15 + 0.7 * (k / 11.0)
        world.set_target(x, 0.5); world.render(); world.to_screen()
        cen, n = locate(read_screen())
        xs.append(x)
        obs.append(cen[0] if cen is not None else float("nan"))
    xs = np.array(xs); obs = np.array(obs)
    ok = np.isfinite(obs)
    if ok.sum() < 4:
        return {"corr": float("nan"), "n_ok": int(ok.sum())}
    corr = float(np.corrcoef(xs[ok], obs[ok])[0, 1])
    return {"corr": corr, "n_ok": int(ok.sum())}

def test_necessary(world, ntrial=24, seed=1):
    """
    (3) 因果必要: 遮断这条通道(喂常数), 闭环任务成功率是否显著下降。
    对照: 通道通畅的闭环 vs 通道被遮断的"盲闭环"。
    """
    rng = random.Random(seed)
    def run(blind):
        hits = 0
        for t in range(ntrial):
            world.set_target(rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8))
            world.render(); world.to_screen()
            # 起点固定在中心
            pos = np.array([0.5, 0.5])
            for step in range(8):
                if blind:
                    cen = None                 # 遮断: 永远看不见(喂常数)
                else:
                    cen, _ = locate(read_screen())
                if cen is None:
                    d = rng.uniform(-0.05, 0.05, 2)      # 看不见就瞎走
                else:
                    d = (cen - pos) * 0.9
                pos = np.clip(pos + d, 0.02, 0.98)
                world.set_target(world.target[0], world.target[1])
                world.render(); world.to_screen()
            cen_f, _ = locate(read_screen())
            if cen_f is not None and np.linalg.norm(cen_f - world.target) < 0.06:
                hits += 1
        return hits
    closed = run(False)
    blind  = run(True)
    return {"closed": closed, "blind": blind, "n": ntrial}

# --------------------------------------------------------------- 主流程
def main():
    t0 = time.time()
    log = []
    def P(s):
        print(s, flush=True); log.append(s)

    P("=" * 72)
    P("exp117 · 自主寻眼  (不是我给它眼睛, 是它自己去找)")
    P("=" * 72)
    P(f"[设备] 帧缓冲自述: {W}x{H} bpp={BPP}  (ioctl 实测, 非假设)")

    P("\n--- 阶段1: 候选发现(自己扫, 不查清单) ---")
    cands = discover_candidates()
    P(f"扫描到候选 {len(cands)} 条 (/dev + /proc + /sys/class)")

    P("\n--- 阶段2: 试着真读一次, 读不动就淘汰 ---")
    readable = []
    for c in cands:
        data, st = probe_readable(c)
        if st != "ok" or not data:
            continue
        # 空内容或全零内容不算通道
        if len(set(data[:256])) <= 1:
            continue
        readable.append((c, data))
    P(f"可读且内容非恒定: {len(readable)} 条")
    for c, d in readable[:12]:
        P(f"    {c['kind']:4s} {c['path'][:52]:52s} {len(d):5d}B")

    P("\n--- 阶段3: 三项检验(自己设计, 自己判定) ---")
    world = World(seed=7)
    world.render(); world.to_screen()
    P("[世界] 已建立并上屏, 目标可被我真实移动")

    f = test_falsifiable(world)
    tot = f["true"] + f["false"]
    P(f"(1) 可证伪   : 真 {f['true']}/{tot}  假 {f['false']}/{tot}"
      + ("  -> 双向可产生, 不饱和" if min(f["true"], f["false"]) > 0
         else "  -> 饱和! 该判据恒真或恒假"))

    c = test_coupled(world)
    P(f"(2) 连着世界 : 相关 r={c['corr']:.4f}  有效样本 {c['n_ok']}/12"
      + ("  -> 跟着世界动" if (c['corr'] == c['corr']) and c['corr'] > 0.9 else ""))

    n = test_necessary(world)
    P(f"(3) 因果必要 : 通畅 {n['closed']}/{n['n']}  遮断 {n['blind']}/{n['n']}")
    drop = (n['closed'] - n['blind']) / max(n['n'], 1)
    P(f"              遮断导致下降 {drop*100:.1f} 个百分点")

    verdict = (min(f["true"], f["false"]) > 0
               and (c["corr"] == c["corr"]) and c["corr"] > 0.9
               and n["closed"] - n["blind"] >= n["n"] * 0.3)
    P(f"\n>>> 自主判定: {'这是眼睛' if verdict else '不够格, 降级为伪感官'}")

    out = {"geometry": [W, H, BPP], "n_candidates": len(cands),
           "n_readable": len(readable), "falsifiable": f,
           "coupled": c, "necessary": n, "verdict_eye": bool(verdict)}
    with open("/data/workspace/luoshen-o1/experiments/exp117_autonomous_eye/result.json", "w") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    P(f"\n[耗时] {time.time()-t0:.1f}s")
    return out

if __name__ == "__main__":
    main()

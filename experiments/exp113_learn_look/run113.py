# -*- coding: utf-8 -*-
"""
113 · 在真实 I/O 上学会往哪看
================================================================
补上 102 欠下的对照:  ε 退火 + 更细网格 + 训练步数加够,
看"学出来的显著性"能不能追上"预置的显著性"。
并且这次眼和手都是真的:

  眼  /dev/fb0  真实设备读像素 (grab 一整帧, provenance REAL)
  手  /dev/uinput 内核注册 HID, 位移由【内核 event 读回值】驱动
      ——手断了 -> 读回 0 事件 -> 视窗不动 -> 任务必然失败 (天然阴性对照)

预注册:
  H1  世界A: learned 与 preset 的识别率差 <= 0.15 (学得够久应能追上)
  H2  迁移到世界B(目标分布反转): preset 大跌, learned 跌幅显著更小
  H3  效应器: 断手 -> 内核读回 rel 恒为 0 (可证伪, 不是自证)
  H4  眼: 目标区 vs 空白区的边缘密度必须能同时产生真和假 (不饱和)
"""
import os, sys, time, json, struct, select, fcntl, errno
import numpy as np

sys.path.insert(0, "/data/workspace/luoshen-o1")
from eo_io.real_backends import RealHIDEffector, INPUT_EVENT_SIZE, INPUT_EVENT_STRUCT, EV_REL, REL_X, REL_Y
from core.life5 import Life5

OUT = os.path.dirname(os.path.abspath(__file__))
W, H, BPP = 1024, 768, 32
NB = W * H * BPP // 8
GW, GH = 8, 6                    # 网格 8x6 = 48 个注视位
CELL_W, CELL_H = W // GW, H // GH
VIEW = 128                       # 视窗边长

rng = np.random.default_rng(20261017)


# ===========================================================================
# 眼: 真实帧缓冲
# ===========================================================================
class RealEye:
    def __init__(self):
        self.fd = open("/dev/fb0", "r+b")
        buf = fcntl.ioctl(self.fd.fileno(), 0x4600, bytes(160))
        x, y = struct.unpack_from("II", buf, 0)
        bpp = struct.unpack_from("I", buf, 24)[0]
        self.geo = (x, y, bpp)
        self.provenance = "REAL" if (x, y, bpp) == (W, H, BPP) else "MISMATCH"
        self.frame = None
        self.n_grab = 0

    def render(self, arr_rgba: np.ndarray):
        """把场景真写到 /dev/fb0 (设备级真实)"""
        os.lseek(self.fd.fileno(), 0, os.SEEK_SET)
        n = self.fd.write(arr_rgba.astype(np.uint8).tobytes())
        return n == NB

    def grab(self):
        os.lseek(self.fd.fileno(), 0, os.SEEK_SET)
        d = self.fd.read(NB)
        if len(d) != NB:                     # 短读不是成功 (判据核 #443)
            raise OSError(errno.EIO, f"short read {len(d)}/{NB}")
        self.n_grab += 1
        self.frame = np.frombuffer(d, dtype=np.uint8).reshape(H, W, 4)
        return self.frame

    @staticmethod
    def measure(win: np.ndarray) -> float:
        """对真实像素做真实测量: 边缘密度 (0~1)"""
        g = win[:, :, 0].astype(np.float32) / 255.0
        e = np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean()
        return float(e)

    def look(self, cx: int, cy: int) -> float:
        """从真实抓到的帧里取视窗 —— 像素是真设备字节, 选择位置是眼的位置"""
        x0 = int(np.clip(cx - VIEW // 2, 0, W - VIEW))
        y0 = int(np.clip(cy - VIEW // 2, 0, H - VIEW))
        self.last_pos = (x0 + VIEW // 2, y0 + VIEW // 2)
        return self.measure(self.frame[y0:y0 + VIEW, x0:x0 + VIEW])


# ===========================================================================
# 手: 真实 uinput + 内核读回
# ===========================================================================
class RealHand:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.provenance = "UNAVAILABLE"
        self.err = None
        self.eff = RealHIDEffector(name="luoshen-eo-look", dry_run=not enabled)
        self.node = self.eff.sysnode
        self.rfd = None
        self.rel_sum = 0
        self.zero_reads = 0
        if self.eff.provenance == "REAL" and enabled and self.node:
            try:
                self.rfd = os.open(self.node, os.O_RDONLY | os.O_NONBLOCK)
                os.set_blocking(self.rfd, False)
                self.provenance = "REAL"
            except OSError as e:
                self.err = f"{errno.errorcode.get(e.errno, e.errno)}"
        elif not enabled:
            self.provenance = "DISABLED"

    def readback(self, timeout=0.03):
        """内核承认收到了多少位移 —— 空是合法的'没动'"""
        if self.rfd is None:
            return (0, 0)
        dx = dy = 0
        try:
            r, _, _ = select.select([self.rfd], [], [], timeout)
            if not r:
                return (0, 0)
            raw = os.read(self.rfd, INPUT_EVENT_SIZE * 64)
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                return (0, 0)
            self.err = f"{errno.errorcode.get(e.errno, e.errno)}"
            return (0, 0)
        n = len(raw) // INPUT_EVENT_SIZE
        for i in range(n):
            _, _, typ, code, val = struct.unpack_from(INPUT_EVENT_STRUCT, raw, i * INPUT_EVENT_SIZE)
            if typ == EV_REL and code == REL_X:
                dx += val
            elif typ == EV_REL and code == REL_Y:
                dy += val
        return (dx, dy)

    def move(self, dx, dy):
        if not self.enabled:
            return (0, 0)
        self.eff.move(int(dx), int(dy))
        d = self.readback()
        self.rel_sum += abs(d[0]) + abs(d[1])
        if d == (0, 0):
            self.zero_reads += 1
        return d

    def destroy(self):
        if self.rfd is not None:
            os.close(self.rfd)
        self.eff.destroy()


# ===========================================================================
# 世界
# ===========================================================================
def cell_center(i):
    gx, gy = i % GW, i // GW
    return (gx * CELL_W + CELL_W // 2, gy * CELL_H + CELL_H // 2)


def make_scene(target_xy, distractors, seed):
    r = np.random.default_rng(seed)
    a = np.zeros((H, W, 4), dtype=np.uint8)
    # 判据核 #462: 背景曾是每个像素独立随机的噪点 —— 它自己的边缘密度 0.031
    # 就淹没了目标(0.037), 通道饱和到 1.19 倍, 判据产生不了假。
    # 改成平滑渐变: 背景自身边缘 ~0, 边缘只来自物体。
    gy = np.linspace(0, 10, H).astype(np.float32)[:, None]
    gx = np.linspace(0, 10, W).astype(np.float32)[None, :]
    bg = (26 + gy + gx).astype(np.uint8)
    a[:, :, 0] = a[:, :, 1] = a[:, :, 2] = bg
    a[:, :, 3] = 255
    # 干扰块: 中等对比
    for (dx, dy) in distractors:
        rr = int(r.integers(18, 30))
        yy, xx = np.ogrid[-rr:rr, -rr:rr]
        m = (xx * xx + yy * yy) <= rr * rr
        y0, x0 = max(dy - rr, 0), max(dx - rr, 0)
        sl = a[y0:y0 + 2 * rr, x0:x0 + 2 * rr, 0]
        mm = m[:sl.shape[0], :sl.shape[1]]
        sl[mm] = 95
        a[y0:y0 + 2 * rr, x0:x0 + 2 * rr, 1][mm] = 95
        a[y0:y0 + 2 * rr, x0:x0 + 2 * rr, 2][mm] = 95
    # 目标: 高对比六边形
    tx, ty = target_xy
    rr = 34
    yy, xx = np.ogrid[-rr:rr, -rr:rr]
    m = (xx * xx + yy * yy) <= rr * rr
    y0, x0 = max(ty - rr, 0), max(tx - rr, 0)
    for c in range(3):
        sl = a[y0:y0 + 2 * rr, x0:x0 + 2 * rr, c]
        mm = m[:sl.shape[0], :sl.shape[1]]
        sl[mm] = 235
    return a


# ===========================================================================
# 主体
# ===========================================================================
def run_agent(kind, world, n_trial, n_step, eye, hand, Q=None, sal=None, eps=0.0, train=True):
    HA = range(GW // 2, GW)                 # 世界A: 目标在右半
    HB = range(0, GW // 2)                  # 世界B: 目标在左半
    cols = HA if world == "A" else HB
    cells_pool = [gy * GW + gx for gy in range(GH) for gx in cols]
    distractors = [(int(x), int(y)) for x, y in
                   zip(rng.integers(60, W - 60, 7), rng.integers(60, H - 60, 7))]
    hits, dists, traj, mind = 0, [], [], []
    for k in range(n_trial):
        scene_seed = 9000 + k + (0 if world == "A" else 5000)
        tgt_cell = int(cells_pool[rng.integers(0, len(cells_pool))])
        tx, ty = cell_center(tgt_cell)
        # 目标在格内随机抖动, 避免"记住格心"这种作弊
        tx += int(rng.integers(-CELL_W // 2 + 40, CELL_W // 2 - 40))
        ty += int(rng.integers(-CELL_H // 2 + 30, CELL_H // 2 - 30))
        eye.render(make_scene((tx, ty), distractors, scene_seed))
        eye.grab()                            # 先上屏再感知 (112 的教训)
        cur = int(rng.integers(0, GW * GH))
        cx, cy = cell_center(cur)
        gain_sum = 0.0
        step_d = []
        for st in range(n_step):
            if kind == "static":
                nxt = cur
            elif kind == "blind":
                nxt = int(rng.integers(0, GW * GH))
            elif kind == "preset":
                order = np.argsort(-sal)
                nxt = int(next((c for c in order if c not in traj[-8:]), order[0]))
            else:  # learned
                recent = set(t for t in traj[-8:] if t >= 0)
                if train and rng.random() < eps:
                    nxt = int(rng.integers(0, GW * GH))
                else:
                    q = Q[cur].copy()
                    for c in recent:                     # 与 preset 同一套"不重看"机制
                        q[c] = -1e9
                    nxt = int(np.argmax(q))
            ncx, ncy = cell_center(nxt)
            dx, dy = ncx - cx, ncy - cy
            kd = hand.move(dx, dy) if (dx or dy) else (0, 0)
            # 视窗只按内核承认收到的位移走 —— 手断了读回 0, 就停在原地
            if kd != (0, 0):
                cx += kd[0]
                cy += kd[1]
            cx = int(np.clip(cx, VIEW // 2, W - VIEW // 2))
            cy = int(np.clip(cy, VIEW // 2, H - VIEW // 2))
            m = eye.look(cx, cy)
            gain_sum += m
            dnow = float(np.hypot(cx - tx, cy - ty))
            step_d.append(dnow)
            if train and kind == "learned":
                r = float(m)
                Q[cur, nxt] = Q[cur, nxt] + 0.35 * (r + 0.55 * float(np.max(Q[nxt])) - Q[cur, nxt])
            cur = nxt
            traj.append(cur)
        d = float(np.hypot(cx - tx, cy - ty))
        dmin = float(min(step_d)) if step_d else d
        dists.append(d)
        mind.append(dmin)
        traj.append(-1)
        if dmin <= 64.0:                 # 过程中是否曾把目标纳入视窗
            hits += 1
    return dict(kind=kind, world=world, acc=hits / n_trial,
                mean_dist=float(np.mean(dists)),
                mean_mind=float(np.mean(mind)), n=n_trial,
                traj_feat=gain_sum / max(n_trial, 1))


def main():
    t0 = time.time()
    eye = RealEye()
    print(f"[eye] geo={eye.geo} provenance={eye.provenance}")

    # ---------- H4: 眼的可证伪性 (不饱和) ----------
    eye.render(make_scene((800, 400), [(200, 200)], 1))
    eye.grab()
    on_t = eye.look(800, 400)
    off_t = eye.look(120, 640)
    eye_falsifiable = (on_t > off_t * 1.5) and off_t > 0

    # ---------- H3: 手的可证伪性 ----------
    hand_on = RealHand(enabled=True)
    h1 = hand_on.move(30, -20)
    hand_off = RealHand(enabled=False)
    h2 = hand_off.move(30, -20)
    hand_falsifiable = (hand_on.provenance == "REAL" and abs(h1[0]) > 0
                        and h2 == (0, 0))
    print(f"[hand] on={hand_on.provenance} readback={h1} | off={hand_off.provenance} readback={h2}")

    # 预置显著性 = 世界A 的真实目标分布 (右半=1.0, 左半=0.1)
    sal = np.array([1.0 if (i % GW) >= GW // 2 else 0.1 for i in range(GW * GH)])
    # 假引导对照: 同样的对比度, 但打乱
    sal_scr = sal.copy()
    rng.shuffle(sal_scr)

    NSTEP = 12
    NTRAIN, NEVAL = 800, 80
    res = {}

    # ---------- 训练 learned (ε 退火, 训练量加够) ----------
    Q = np.zeros((GW * GH, GW * GH)) + 0.01
    eps0, eps1, decay = 1.0, 0.05, 0.995
    eps = eps0
    train_curve, train_acc = [], []
    for ep in range(NTRAIN):
        r = run_agent("learned", "A", 1, NSTEP, eye, hand_on, Q=Q, eps=eps, train=True)
        train_curve.append(r["mean_mind"])
        train_acc.append(r["acc"])
        eps = max(eps1, eps * decay)
        if ep % 100 == 0:
            print(f"  [train {ep:4d}] eps={eps:.3f} mindist={np.mean(train_curve[-50:]):.0f} "
                  f"acc={np.mean(train_acc[-50:]):.2f}")
    print(f"[train] eps {eps0}->{eps:.3f}  mindist {np.mean(train_curve[:50]):.0f} "
          f"-> {np.mean(train_curve[-50:]):.0f}")
    Q_A = Q.copy()

    # ---------- 世界A ----------
    for kind in ["preset", "learned", "blind", "static", "scrambled"]:
        kw = dict(kind=("preset" if kind == "scrambled" else kind),
                  world="A", n_trial=NEVAL, n_step=NSTEP, eye=eye, hand=hand_on)
        if kind == "learned":
            kw.update(Q=Q, train=False)
        elif kind == "scrambled":
            kw.update(sal=sal_scr)
        elif kind == "preset":
            kw.update(sal=sal)
        res[f"A:{kind}"] = run_agent(**kw)

    # ---------- 世界B: 目标分布反转 ----------
    kw = dict(world="B", n_trial=NEVAL, n_step=NSTEP, eye=eye, hand=hand_on)
    res["B:preset"] = run_agent(kind="preset", sal=sal, **kw)          # 仍抱着 A 的旧图
    res["B:learned_frozen"] = run_agent(kind="learned", Q=Q_A, train=False, **kw)
    for b in ["blind", "static"]:
        res[f"B:{b}"] = run_agent(kind=b, **kw)

    # ---------- B: 重训 (迁移的真正检验 —— 能不能重新学) ----------
    Q_B = Q_A.copy()
    eps = 0.30
    for ep in range(200):
        run_agent("learned", "B", 1, NSTEP, eye, hand_on, Q=Q_B, eps=eps, train=True)
        eps = max(0.05, eps * 0.99)
    res["B:learned_retrain"] = run_agent(kind="learned", world="B", n_trial=NEVAL,
                                         n_step=NSTEP, eye=eye, hand=hand_on,
                                         Q=Q_B, train=False)

    hand_on.destroy()
    hand_off.destroy()

    dt = time.time() - t0
    out = dict(res=res, train_curve=[float(v) for v in train_curve],
               eye_falsifiable=bool(eye_falsifiable), eye_on=float(on_t), eye_off=float(off_t),
               hand_falsifiable=bool(hand_falsifiable), hand_on_readback=[int(v) for v in h1],
               hand_off_readback=[int(v) for v in h2],
               hand_node=hand_on.node, n_grab=int(eye.n_grab), secs=float(dt))
    with open(os.path.join(OUT, "result113.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: (round(v["acc"], 4), round(v["mean_dist"], 1)) for k, v in res.items()},
                     ensure_ascii=False, indent=2))
    print(f"[done] {dt:.1f}s  grabs={eye.n_grab}")


if __name__ == "__main__":
    main()

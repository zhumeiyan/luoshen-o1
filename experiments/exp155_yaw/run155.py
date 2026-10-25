"""
155 旋转 vs 磁场 —— 真链路版本。

真在哪：
  手 /dev/uinput 注入按键 -> 内核 -> 世界线程真读 input_event 结构
  -> 真写 /dev/fb0 -> 她用独立 fd 真读回字节 -> 从像素解朝向
  转向噪声取自 os.urandom（真内核熵池），不是伪随机。

判据（每个都必须能同时产生真和假）：
  G0a 有磁纹：转向后画面变化  >> 静默基线
  G0b 无磁纹：转向后画面变化  ≈ 静默基线   <-- 证明圆形房间里朝向视觉不可观测
  G1  可逆：无噪声下 左转 N 再右转 N，画面逐位回到初态
  G2  处处可读：扫一圈朝向，磁纹相位解码成功率与误差
  G3a 死推算(纯积分)误差随步数增长，斜率 CI 不跨 0
  G3b 磁场校正后误差有界，斜率不显著区别于 0
  G3c 互补：存在 N 使 组合误差 < 积分误差（CI 不跨 0）
  G3d 磁场有带宽：噪声大到漂出 P/2 时，解模糊失败，组合也崩（必须能出现）
"""
import os, sys, time, struct, fcntl, threading, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world155 as wm

UI_SET_EVBIT, UI_SET_KEYBIT = 0x40045564, 0x40045565
UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502
EV_KEY = 0x01
KEY_A, KEY_D = 30, 32
INPUT_EVENT = "llHHI" if struct.calcsize("llHHI") == 24 else "qqHHI"
SZ = struct.calcsize(INPUT_EVENT)

ROT = 0.30          # 名义每步转角(rad) —— 她以为的步长
N_MAX = 120
CHECK_EVERY = 10


def make_uinput(name="luoshen_yaw"):
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    ud = struct.pack("80s", name.encode()) + struct.pack("HHHH", 0x03, 0x1234, 0x5678, 1)
    ud += struct.pack("I", 0) + b"\0" * (64 * 4 * 4)
    assert len(ud) == 1116
    os.write(fd, ud)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
    for k in (KEY_A, KEY_D):
        fcntl.ioctl(fd, UI_SET_KEYBIT, k)
    fcntl.ioctl(fd, UI_DEV_CREATE)
    time.sleep(0.4)
    dev = None
    base = "/sys/devices/virtual/input"
    if os.path.isdir(base):
        for d in sorted(os.listdir(base)):
            p = os.path.join(base, d, "name")
            if os.path.exists(p):
                try:
                    if open(p).read().strip() == name:
                        for e in os.listdir(os.path.join(base, d)):
                            if e.startswith("event"):
                                dev = "/dev/input/" + e
                except Exception:
                    pass
    return fd, dev


def send_key(fd, code):
    for v in (1, 0):
        os.write(fd, struct.pack(INPUT_EVENT, 0, 0, EV_KEY, code, v))
    os.write(fd, struct.pack(INPUT_EVENT, 0, 0, 0, 0, 0))


def urand_unit():
    """真内核熵 -> [-1,1]"""
    b = os.urandom(4)
    return (int.from_bytes(b, "little") / 4294967295.0) * 2.0 - 1.0


class WorldThread(threading.Thread):
    """真读内核事件 -> 转向(带真噪声) -> 真写 fb0"""
    def __init__(self, ev_dev, fb_fd, magnet=True, sigma=0.0):
        super().__init__(daemon=True)
        self.ev = os.open(ev_dev, os.O_RDONLY | os.O_NONBLOCK)
        self.fb = fb_fd
        self.magnet = magnet
        self.sigma = sigma
        self.a = 0.0
        self.a_true = 0.0
        self.steps = 0
        self.done = threading.Event()
        self.done.set()
        self.stop = False
        self.write_buf(self.a_true)

    def write_buf(self, a):
        b = wm.to_fb_bytes(wm.render(0, 0, a, magnet=self.magnet))
        os.pwrite(self.fb, b, 0)

    def run(self):
        while not self.stop:
            try:
                raw = os.read(self.ev, SZ)
            except BlockingIOError:
                time.sleep(0.0005)
                continue
            except OSError:
                break
            if len(raw) < SZ:
                continue
            _, _, typ, code, val = struct.unpack(INPUT_EVENT, raw[:SZ])
            if typ == EV_KEY and val == 1:
                if code == KEY_A:
                    d = -ROT
                elif code == KEY_D:
                    d = +ROT
                else:
                    continue
                if self.sigma > 0:
                    d += self.sigma * urand_unit()
                self.a_true += d
                self.steps += 1
                self.write_buf(self.a_true)
                self.done.set()


def read_view(fb_fd):
    raw = os.pread(fb_fd, wm.FB_BYTES, 0)
    return wm.fb_bytes_to_rgb(raw), raw


def mean_abs_diff(b1, b2):
    return float(np.abs(b1.astype(np.int16) - b2.astype(np.int16)).mean())


def main():
    fd, dev = make_uinput()
    assert dev, "uinput 事件节点未找到"
    fb_fd = os.open("/dev/fb0", os.O_RDWR)
    res = {"uinput_dev": dev, "sigma_scan": {}, "reps": {}}

    # ---------- 静默基线（fbcon 光标 0.2s 后会污染，必须立即回采比对） ----------
    silent = []
    for _ in range(6):
        v1, _ = read_view(fb_fd)
        time.sleep(0.05)
        v2, _ = read_view(fb_fd)
        silent.append(mean_abs_diff(v1, v2))
    res["silent_baseline"] = float(np.mean(silent))

    # ---------- G0a / G0b ----------
    for tag, magnet in (("magnet", True), ("nomagnet", False)):
        wt = WorldThread(dev, fb_fd, magnet=magnet, sigma=0.0)
        wt.start()
        v0, _ = read_view(fb_fd)
        wt.done.clear(); send_key(fd, KEY_D)
        for _ in range(400):
            if wt.done.is_set():
                break
            time.sleep(0.001)
        v1, _ = read_view(fb_fd)
        res["G0_" + tag] = mean_abs_diff(v0, v1)
        wt.stop = True
        time.sleep(0.05)

    # ---------- G1 可逆 ----------
    wt = WorldThread(dev, fb_fd, magnet=True, sigma=0.0)
    wt.start()
    v0, _ = read_view(fb_fd)
    for _ in range(20):
        wt.done.clear(); send_key(fd, KEY_D)
        while not wt.done.is_set():
            time.sleep(0.001)
    for _ in range(20):
        wt.done.clear(); send_key(fd, KEY_A)
        while not wt.done.is_set():
            time.sleep(0.001)
    v1, _ = read_view(fb_fd)
    res["G1_return_diff"] = mean_abs_diff(v0, v1)
    res["G1_steps_executed"] = wt.steps
    wt.stop = True; time.sleep(0.05)

    # ---------- G2 处处可读 ----------
    ok_n, errs = 0, []
    for a in np.linspace(-3.0, 3.0, 41):
        buf = wm.render(0, 0, a, magnet=True)
        ok, ests = wm.decode_phase_from_view(buf)
        if ok:
            ok_n += 1
            errs.append(min(abs(wm.wrap(m - np.mod(a, wm.P))) for m in ests))
    res["G2_readable"] = ok_n / 41.0
    res["G2_phase_err_mean"] = float(np.mean(errs)) if errs else None

    # ---------- G3 漂移：sigma 扫描 ----------
    R = 8
    for sigma in (0.004, 0.012, 0.036):
        dead_e, comb_e = [], []
        for r in range(R):
            wt = WorldThread(dev, fb_fd, magnet=True, sigma=sigma)
            wt.start()
            n_dead = 0
            a_dead = 0.0
            curve_d, curve_c = [], []
            for n in range(1, N_MAX + 1):
                wt.done.clear(); send_key(fd, KEY_D)
                while not wt.done.is_set():
                    time.sleep(0.0005)
                n_dead += 1
                a_dead += ROT
                if n % CHECK_EVERY == 0:
                    v, _ = read_view(fb_fd)
                    ok, ests = wm.decode_phase_from_view(v)
                    if not ok:
                        continue
                    a_mod = min(ests, key=lambda m: abs(wm.wrap(m - np.mod(a_dead, wm.P))))
                    a_comb = wm.resolve(a_dead, a_mod)
                    curve_d.append(abs(wm.wrap(a_dead - wt.a_true)))
                    curve_c.append(abs(wm.wrap(a_comb - wt.a_true)))
            if curve_d:
                dead_e.append(curve_d); comb_e.append(curve_c)
            wt.stop = True; time.sleep(0.05)
        L = min(len(c) for c in dead_e)
        dead_e = [c[:L] for c in dead_e]; comb_e = [c[:L] for c in comb_e]
        res["sigma_scan"][str(sigma)] = {
            "dead": [float(x) for x in np.mean(dead_e, axis=0)],
            "comb": [float(x) for x in np.mean(comb_e, axis=0)],
            "checkpoints": [CHECK_EVERY * (i + 1) for i in range(L)],
        }
        res["reps"][str(sigma)] = {
            "dead_all": dead_e, "comb_all": comb_e,
            "P_half": float(wm.P / 2), "P": float(wm.P),
        }

    try:
        fcntl.ioctl(fd, UI_DEV_DESTROY)
    except Exception:
        pass
    os.close(fb_fd)
    with open("result155.json", "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("sigma_scan", "reps")}, indent=2, ensure_ascii=False))
    for s, d in res["sigma_scan"].items():
        print(f"sigma={s}  dead末={d['dead'][-1]:.4f}  comb末={d['comb'][-1]:.4f}")


if __name__ == "__main__":
    main()

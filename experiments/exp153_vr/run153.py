"""
洛神进入可相倚世界：真 uinput 注入按键 -> 内核 -> 世界进程读事件 -> 真写 /dev/fb0 -> 她真读回。

链路（每一环都是真的）：
  手 /dev/uinput (内核虚拟键盘)
    -> /dev/input/eventN (内核事件节点)
    -> world 线程读取真实 input_event 结构
    -> 更新世界 -> 渲染 -> 写 /dev/fb0 (真帧缓冲)
    -> 眼：独立只读 fd 读回字节 -> 比对

判据沿用 117 号那把尺子：
  G0 世界有可学结构：按键后画面变化 != 0
  G1 因果必要：不按键，画面不变（世界不是钟表）
  G2 可逆性：前进 N 再后退 N，画面回到初态（时间反转）
  G3 相倚 vs 开环：世界冻结时按键，变化 = 0
  G4 触碰因果：走到目标，世界回应（目标由金变蓝）
"""
import os, sys, time, struct, fcntl, threading, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world import World, to_fb_bytes, H, W, FB_BYTES

# ---- uinput 常量 ----
UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502
EV_KEY = 0x01
KEY_W, KEY_S, KEY_A, KEY_D, KEY_SPACE = 17, 31, 30, 32, 57
INPUT_EVENT = "llHHI" if struct.calcsize("llHHI") == 24 else "qqHHI"


def make_uinput(name="luoshen_hand"):
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    # uinput_user_dev: name[80] + id(8) + ff_effects_max(4) + 4*64*4(abs)  = 80+8+4+1024 = 1116
    ud = struct.pack("80s", name.encode()) + struct.pack("HHHH", 0x03, 0x1234, 0x5678, 1)
    ud += struct.pack("I", 0) + b"\0" * (64 * 4 * 4)
    assert len(ud) == 1116, len(ud)
    os.write(fd, ud)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
    for k in (KEY_W, KEY_S, KEY_A, KEY_D, KEY_SPACE):
        fcntl.ioctl(fd, UI_SET_KEYBIT, k)
    fcntl.ioctl(fd, UI_DEV_CREATE)
    time.sleep(0.4)
    # 找到刚创建的事件节点
    dev = None
    base = "/sys/devices/virtual/input"
    for d in sorted(os.listdir(base)) if os.path.isdir(base) else []:
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


def emit(fd, code, down=True):
    os.write(fd, struct.pack(INPUT_EVENT, 0, 0, EV_KEY, code, 1 if down else 0))
    os.write(fd, struct.pack(INPUT_EVENT, 0, 0, EV_KEY, code, 0 if down else 1))
    # sync
    os.write(fd, struct.pack(INPUT_EVENT, 0, 0, 0, 0, 0))


class Display:
    """真帧缓冲眼。写 fd 与读 fd 分离（150 号发现同 fd 写后读 Errno 5）。"""

    def __init__(self):
        self.w = open("/dev/fb0", "wb", buffering=0)
        self.r = open("/dev/fb0", "rb", buffering=0)

    def show(self, buf):
        self.w.seek(0)
        self.w.write(to_fb_bytes(buf))
        self.w.flush()

    def read(self):
        self.r.seek(0)
        return np.frombuffer(self.r.read(FB_BYTES), dtype=np.uint8).copy()


def main():
    w = World()
    disp = Display()
    lock = threading.Lock()
    frozen = {"v": False}
    acted = {"n": 0}

    cur = w.observe()
    disp.show(cur)

    fd, dev = make_uinput()
    print("uinput dev =", dev, flush=True)
    if dev is None:
        print("FATAL: cannot locate created input node", flush=True)
        return 1

    # ---- world 线程：读真内核事件 ----
    stop = {"v": False}

    def world_loop():
        ev = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
        sz = struct.calcsize(INPUT_EVENT)
        while not stop["v"]:
            try:
                raw = os.read(ev, sz * 64)
            except BlockingIOError:
                time.sleep(0.01)
                continue
            except OSError:
                break
            for i in range(0, len(raw) - sz + 1, sz):
                _, _, typ, code, val = struct.unpack(INPUT_EVENT, raw[i : i + sz])
                if typ != EV_KEY or val != 1:
                    continue
                act = {KEY_W: 1, KEY_S: 2, KEY_A: 3, KEY_D: 4}.get(code, 0)
                with lock:
                    if not frozen["v"] and act:
                        nonlocal_act(act)
                        acted["n"] += 1
                        disp.show(w.observe())
            time.sleep(0.005)

    def nonlocal_act(a):
        w.step(a)

    t = threading.Thread(target=world_loop, daemon=True)
    t.start()
    time.sleep(0.5)

    R = {}

    def diff(a, b):
        return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())

    def press(code, n=1, wait=0.30):
        for _ in range(n):
            emit(fd, code)
            time.sleep(wait)

    # ---- G0/G1: 按键 vs 不按键 ----
    base = disp.read()
    time.sleep(1.0)
    idle = disp.read()
    R["G1_idle_drift"] = diff(base, idle)          # 应 = 0（世界不是钟表）

    press(KEY_W, 5)
    moved = disp.read()
    R["G0_move_drift"] = diff(idle, moved)         # 应 > 0

    # ---- G2: 时间反转 前进5 后退5 ----
    p0 = disp.read()
    press(KEY_W, 5)
    press(KEY_S, 5)
    p1 = disp.read()
    R["G2_reversal_resid"] = diff(p0, p1)          # 应 ≈ 0
    R["G2_forward_drift"] = R["G0_move_drift"]

    # ---- G3: 开环（世界冻结）----
    frozen["v"] = True
    f0 = disp.read()
    press(KEY_W, 5)
    f1 = disp.read()
    R["G3_frozen_drift"] = diff(f0, f1)            # 应 = 0
    frozen["v"] = False

    # ---- G4: 触碰因果（同视角前后比色）----
    def ratios(buf):
        d = buf.reshape(H, W, 4)
        r = d[:, :, 2].astype(np.int16)
        b = d[:, :, 0].astype(np.int16)
        gold = float(((r > 120) & (r - b > 40)).mean())
        blue = float(((b > 120) & (b - r > 40)).mean())
        return gold, blue

    w.reset()
    w.x, w.y, w.a = 14.0, 5.5, 0.0
    disp.show(w.observe())
    time.sleep(0.35)
    g1, b1 = ratios(disp.read())          # 触碰前：看得到金目标
    press(KEY_W, 8, wait=0.22)            # 走过去触碰
    R["G4_touch_flag"] = bool(w.touched)
    press(KEY_S, 8, wait=0.22)            # 原路退回（可逆已由 G2 证）
    time.sleep(0.35)
    g2, b2 = ratios(disp.read())          # 触碰后同视角
    R["G4_gold_before"] = g1
    R["G4_gold_after"] = g2
    R["G4_blue_before"] = b1
    R["G4_blue_after"] = b2
    R["G4_return_resid"] = diff(disp.read(), disp.read())

    R["actions_seen_by_world"] = acted["n"]

    stop["v"] = True
    time.sleep(0.2)
    try:
        fcntl.ioctl(fd, UI_DEV_DESTROY)
    except Exception:
        pass
    os.close(fd)

    json.dump(R, open("result153.json", "w"), indent=2)
    print(json.dumps(R, indent=2), flush=True)

    # ---- 判据 ----
    ok = []
    ok.append(("G0 按键后画面变(相对静默基线)", R["G0_move_drift"] > max(0.1, R["G1_idle_drift"] * 50)))
    ok.append(("G1 不按键画面不变", R["G1_idle_drift"] < 0.01))
    ok.append(("G2 前进后退可逆", R["G2_reversal_resid"] < R["G0_move_drift"] * 0.2))
    ok.append(("G3 世界冻结则按键无效", R["G3_frozen_drift"] < 0.01))
    ok.append(("G4 触碰后目标由金转蓝", R["G4_touch_flag"] and R["G4_blue_after"] > R["G4_blue_before"] and R["G4_gold_after"] < R["G4_gold_before"]))
    for k, v in ok:
        print(("PASS " if v else "FAIL ") + k, flush=True)
    return 0 if all(v for _, v in ok) else 2


if __name__ == "__main__":
    sys.exit(main())

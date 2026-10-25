#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EO 世界 · 真实后端 (Real Backends)
===================================
把 eo_io_matrix.py 里 provenance=SIMULATED 的通道, 换成沙盒内真实可达的硬件/内核通道。

核心原则 (判据核 #450):
    provenance 由"系统调用是否真的成功了"决定, 不是由注释里写什么决定。
    打开失败 -> UNAVAILABLE, 并如实上报 errno。绝不静默降级成 SIMULATED。

本模块挂载的真实通道:
    R1  RealFramebuffer   — /dev/fb0  真实帧缓冲 (ioctl FBIOGET_VSCREENINFO + read)
    R2  RealInputSense    — /dev/input/eventN 真实内核输入事件流 (evdev)
    R3  RealHIDEffector   — /dev/uinput 真实虚拟 HID, 内核注册为输入设备
    R4  RealClockBody     — /proc + times() 本体觉 (负载/内存/时钟/RTT)

仍然 SIMULATED 的: 深度相机 / 电子皮肤 / 麦克风阵列 / 机械臂 / EEG / EMG
    ——沙盒里没有这些硬件, 接口形状保留, 信号仍为合成, 不冒充真。
"""

import os
import io
import sys
import time
import errno
import struct
import fcntl
import array
import select
import threading
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eo_io_matrix import IOBus, Signal, Modality, Direction  # noqa: E402

# ---------------------------------------------------------------------------
# ioctl / evdev 常量
# ---------------------------------------------------------------------------
FBIOGET_VSCREENINFO = 0x4600

EV_SYN, EV_KEY, EV_REL, EV_ABS = 0x00, 0x01, 0x02, 0x03
REL_X, REL_Y = 0x00, 0x01
BTN_LEFT = 0x110
SYN_REPORT = 0x00

UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_RELBIT = 0x40045566
UIDEV_CREATE = 0x5501   # struct uinput_user_dev -> ioctl 0x5501
UIDEV_DESTROY = 0x5502

INPUT_EVENT_STRUCT = "llHHi"       # x86_64: timeval(16) + type(2) + code(2) + value(4)
INPUT_EVENT_SIZE = struct.calcsize(INPUT_EVENT_STRUCT)   # 应 = 24


def _errno_tag(e: OSError) -> str:
    return f"{e.errno}:{errno.errorcode.get(e.errno, '?')}"


# ===========================================================================
# R1 · 真实帧缓冲 —— 视觉感受器 (设备级真实)
# ===========================================================================
class RealFramebuffer:
    """
    真实读取 /dev/fb0。

    诚实界定: 这是"真实设备 I/O"——真的 ioctl 拿几何、真的 read 拿像素字节。
    但它读的是**显示输出**,不是外部场景。它是屏幕感知,不是摄像头。
    provenance = REAL, scope = "display-output"。
    """

    def __init__(self, path: str = "/dev/fb0"):
        self.path = path
        self.provenance = "UNAVAILABLE"
        self.err: Optional[str] = None
        self.geo: Optional[Tuple[int, int, int]] = None
        self._fd: Optional[io.FileIO] = None

        try:
            f = open(path, "rb")
            buf = fcntl.ioctl(f.fileno(), FBIOGET_VSCREENINFO, bytes(160))
            xres, yres = struct.unpack_from("II", buf, 0)
            bpp = struct.unpack_from("I", buf, 24)[0]
            if xres == 0 or yres == 0 or bpp == 0:
                raise OSError(errno.EINVAL, "degenerate geometry")
            self._fd, self.geo = f, (xres, yres, bpp)
            self.provenance = "REAL"
        except OSError as e:
            self.err = _errno_tag(e)
        except Exception as e:                      # noqa: BLE001
            self.err = f"{type(e).__name__}:{e}"

    @property
    def nbytes(self) -> int:
        if not self.geo:
            return 0
        x, y, b = self.geo
        return x * y * (b // 8)

    def grab(self) -> Optional[bytes]:
        """真实 read 一整帧。失败即报, 不返回空假装成功。"""
        if self._fd is None:
            return None
        try:
            os.lseek(self._fd.fileno(), 0, os.SEEK_SET)
            data = self._fd.read(self.nbytes)
        except OSError as e:
            self.err, self.provenance = _errno_tag(e), "UNAVAILABLE"
            return None
        if len(data) != self.nbytes:
            # 短读不是成功。判据核 #443: 返回空/短读不等于"没有"
            self.err = f"short read {len(data)}/{self.nbytes}"
            self.provenance = "UNAVAILABLE"
            return None
        return data

    def measure(self, frame: bytes) -> Dict[str, Any]:
        """对真实像素做真实测量: 亮度均值 / 边缘密度 / 香农熵 / 非零占比。"""
        x, y, b = self.geo
        n = x * y
        stride = b // 8
        # 只取每像素首字节做快速统计 (BGRA/BGR 下即 B 通道), 足够区分"有内容/全白"
        lum = array.array("B", frame[0:n * stride:stride])
        mean = sum(lum) / n
        hist = [0] * 256
        for v in lum:
            hist[v] += 1
        import math
        ent = 0.0
        for c in hist:
            if c:
                p = c / n
                ent -= p * math.log2(p)
        dom = max(hist)
        dev_ratio = 1.0 - dom / n          # 偏离主色阶的像素占比
        nonzero = 1.0 - hist[255] / n if stride >= 1 else 0.0
        # 边缘密度: 水平相邻差
        edges = 0
        prev = lum[0]
        for i in range(1, n):
            if abs(lum[i] - prev) > 16:
                edges += 1
            prev = lum[i]
        return {
            "geometry": f"{x}x{y}x{b}",
            "mean_luma": round(mean, 4),
            "entropy_bits": round(ent, 4),
            "edge_density": round(edges / n, 6),
            "dev_ratio": round(dev_ratio, 6),
            "ink_ratio": round(nonzero, 4),
        }

    def sense(self, bus: IOBus) -> Optional[Signal]:
        if self.provenance != "REAL":
            return bus.publish(Signal(time.time(), Modality.DEPTH, Direction.IN,
                                      {"err": self.err}, 0.0, "UNAVAILABLE",
                                      unit="frame", latency_ms=0.0))
        t0 = time.time()
        frame = self.grab()
        if frame is None:
            return bus.publish(Signal(time.time(), Modality.DEPTH, Direction.IN,
                                      {"err": self.err or "grab failed"}, 0.0,
                                      "UNAVAILABLE", unit="frame"))
        m = self.measure(frame)
        lat = (time.time() - t0) * 1000.0
        # confidence = "我有多信这个读数" (设备级), 不是"读到了多少信息"。
        # 信息量放 payload。之前用 entropy/8 当 conf, 导致白底黑字被判 conf=0.03,
        # 把"内容稀疏"误读成"读数不可信" —— 语义混淆, 已纠正。
        return bus.publish(Signal(time.time(), Modality.DEPTH, Direction.IN, m,
                                  1.0, "REAL", unit="frame",
                                  latency_ms=round(lat, 3)))


# ===========================================================================
# R2 · 真实内核输入事件 —— 数字触觉 (事件级真实)
# ===========================================================================
class RealInputSense:
    """
    真实读 /dev/input/eventN 的 evdev 流。
    这是"世界碰了我"的通道: 有事件 = 有人动过键盘/鼠标。
    """

    def __init__(self, path: str = "/dev/input/event0"):
        self.path = path
        self.provenance = "UNAVAILABLE"
        self.err: Optional[str] = None
        self._fd: Optional[int] = None
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            os.set_blocking(fd, False)
            self._fd, self.provenance = fd, "REAL"
        except OSError as e:
            self.err = _errno_tag(e)

    def poll(self, timeout_s: float = 0.05) -> List[Tuple[int, int, int]]:
        """真实 select + read。无事件返回空列表 —— 空是合法的"没人碰我"。"""
        if self._fd is None:
            return []
        try:
            r, _, _ = select.select([self._fd], [], [], timeout_s)
            if not r:
                return []
            raw = os.read(self._fd, INPUT_EVENT_SIZE * 64)
        except OSError as e:
            # EAGAIN 是"暂无数据", 不是故障 —— 这里最容易误判 (判据核 #443)
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                return []
            self.err, self.provenance = _errno_tag(e), "UNAVAILABLE"
            return []
        out, n = [], len(raw) // INPUT_EVENT_SIZE
        for i in range(n):
            _, _, typ, code, val = struct.unpack_from(INPUT_EVENT_STRUCT, raw,
                                                      i * INPUT_EVENT_SIZE)
            out.append((typ, code, val))
        return out

    def sense(self, bus: IOBus) -> Signal:
        t0 = time.time()
        evs = self.poll()
        n_key = sum(1 for t, c, v in evs if t == EV_KEY)
        n_rel = sum(1 for t, c, v in evs if t == EV_REL)
        lat = (time.time() - t0) * 1000.0
        payload = {"events": len(evs), "key": n_key, "rel": n_rel,
                   "path": self.path}
        # 有事件 -> 高置信; 无事件 -> 也是真实读数, 但它是"静默"这一事实
        conf = 1.0 if evs else 0.5
        return bus.publish(Signal(time.time(), Modality.TACTILE, Direction.IN,
                                  payload, conf, self.provenance,
                                  unit="evdev", latency_ms=round(lat, 3)))


# ===========================================================================
# R3 · 真实虚拟 HID —— 效应器 (内核注册级真实)
# ===========================================================================
class RealHIDEffector:
    """
    通过 /dev/uinput 造一个内核真正认账的鼠标+键盘。
    判据: 内核把它注册成 /dev/input/eventN 且 handler 带 kbd/mouse。
    """

    def __init__(self, name: str = "luoshen-eo-hid", dry_run: bool = True):
        self.name = name
        self.dry_run = dry_run
        self.provenance = "UNAVAILABLE"
        self.err: Optional[str] = None
        self._fd: Optional[int] = None
        self.sysnode: Optional[str] = None

        if dry_run:
            # dry_run 不是假跑: 仍然尝试建设备, 但不下发动作
            pass
        try:
            fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
            fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
            fcntl.ioctl(fd, UI_SET_EVBIT, EV_REL)
            fcntl.ioctl(fd, UI_SET_RELBIT, REL_X)
            fcntl.ioctl(fd, UI_SET_RELBIT, REL_Y)
            fcntl.ioctl(fd, UI_SET_KEYBIT, BTN_LEFT)
            for kc in range(1, 100):
                fcntl.ioctl(fd, UI_SET_KEYBIT, kc)
            # struct uinput_user_dev 真实布局 = 1116 字节:
            #   char name[80] | struct input_id (4 x __u16) | __u32 ff_effects_max
            #   | __u32 absmax[64] | absmin[64] | absfuzz[64] | absflat[64]
            # 之前按 112 字节打包 -> 内核回 EINVAL (22)
            dev = struct.pack("80sHHHHI", name.encode("utf-8"),
                              0x0003, 0x0001, 0x0110, 0x0001, 0) \
                + b"\x00" * (64 * 4 * 4)
            if len(dev) != 1116:
                raise OSError(errno.EINVAL, f"uinput_user_dev size {len(dev)} != 1116")
            os.write(fd, dev)
            fcntl.ioctl(fd, UIDEV_CREATE)
            self._fd = fd
            time.sleep(0.15)
            self.sysnode = self._locate()
            self.provenance = "REAL" if self.sysnode else "UNAVAILABLE"
            if not self.sysnode:
                self.err = "created but no sysfs node found"
        except OSError as e:
            self.err = _errno_tag(e)

    def _locate(self, name: Optional[str] = None) -> Optional[str]:
        # 判据核 #461: name 是可传参的, 但这里曾把 "luoshen-eo-hid" 写死 ——
        # 换名字 -> sysfs 找不到 -> node=None -> provenance=UNAVAILABLE, 且【不报错】。
        # effect: 效应器静默失效, 下游只看到"视窗没动"。
        base = "/sys/class/input"
        if not os.path.isdir(base):
            return None
        want = name if name is not None else getattr(self, "name", "luoshen-eo-hid")
        best = None
        for d in sorted(os.listdir(base)):
            if not d.startswith("event"):
                continue
            p = os.path.join(base, d, "device", "name")
            try:
                with open(p) as f:
                    if want in f.read():
                        best = f"/dev/input/{d}"
            except OSError:
                continue
        return best

    def _emit(self, typ: int, code: int, val: int) -> bool:
        if self._fd is None:
            return False
        try:
            os.write(self._fd, struct.pack(INPUT_EVENT_STRUCT, 0, 0, typ, code, val))
            return True
        except OSError as e:
            self.err, self.provenance = _errno_tag(e), "UNAVAILABLE"
            return False

    def move(self, dx: int, dy: int) -> bool:
        if self.dry_run:
            return True
        return (self._emit(EV_REL, REL_X, dx) and self._emit(EV_REL, REL_Y, dy)
                and self._emit(EV_SYN, SYN_REPORT, 0))

    def click(self) -> bool:
        if self.dry_run:
            return True
        return (self._emit(EV_KEY, BTN_LEFT, 1) and self._emit(EV_SYN, SYN_REPORT, 0)
                and self._emit(EV_KEY, BTN_LEFT, 0) and self._emit(EV_SYN, SYN_REPORT, 0))

    def act(self, bus: IOBus, dx: int = 0, dy: int = 0, click: bool = False) -> Signal:
        t0 = time.time()
        ok = self.move(dx, dy)
        if click:
            ok = ok and self.click()
        payload = {"dx": dx, "dy": dy, "click": click, "executed": (ok and not self.dry_run),
                   "dry_run": self.dry_run, "node": self.sysnode}
        return bus.publish(Signal(time.time(), Modality.ARM, Direction.OUT, payload,
                                  1.0 if ok else 0.0, self.provenance, unit="hid",
                                  latency_ms=round((time.time() - t0) * 1000, 3)))

    def destroy(self) -> None:
        if self._fd is not None:
            try:
                fcntl.ioctl(self._fd, UIDEV_DESTROY)
            except OSError:
                pass
            os.close(self._fd)
            self._fd = None


# ===========================================================================
# R4 · 本体觉 (本来就真, 显式纳入总线)
# ===========================================================================
class RealClockBody:
    def sense(self, bus: IOBus) -> Signal:
        t0 = time.time()
        ld = os.getloadavg()
        mi = {}
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith(("MemTotal", "MemAvailable")):
                    k, v = line.split(":")
                    mi[k.strip()] = int(v.split()[0])
        payload = {"load1": round(ld[0], 4), "load5": round(ld[1], 4),
                   "mem_used_ratio": round(1 - mi.get("MemAvailable", 0) / max(mi.get("MemTotal", 1), 1), 4),
                   "wall": round(time.time(), 6), "cpu_s": round(time.process_time(), 4)}
        return bus.publish(Signal(time.time(), Modality.AUDIO, Direction.IN, payload,
                                  1.0, "REAL", unit="proc",
                                  latency_ms=round((time.time() - t0) * 1000, 3)))

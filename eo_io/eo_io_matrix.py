#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EO 世界 · 多模态 I/O 全谱系外设接入架构
LuoShen (洛神) — Carbon-Silicon Symbiont I/O Substrate

四层谱系:
  L1 软件与系统级 (数字假肢)  — 无障碍服务 / DOM 解析
  L2 物理感官     (传感器)    — 深度相机 / 触觉电子皮肤 / 声音阵列
  L3 物理执行     (执行器)    — 机械臂 / 触觉反馈马达
  L4 生物接口     (BCI/EMG)   — 脑电 / 肌电

设计约束:
  * 所有通道归一到同一 Signal 信封, 便于跨模态比较与时间对齐
  * 所有执行器命令强制经过 Interlock 安全闸, 默认 dry_run
  * 每个通道显式声明 provenance: REAL(本机可达) / SIMULATED(无硬件)
"""

import time
import math
import random
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Callable, Optional, Any
from enum import Enum

# ----------------------------------------------------------------------------
# 0. 统一信号信封与总线
# ----------------------------------------------------------------------------

class Modality(Enum):
    ACCESSIBILITY = "accessibility"   # L1 无障碍服务
    DOM           = "dom"             # L1 DOM 解析
    DEPTH         = "depth"           # L2 深度相机 / LiDAR
    TACTILE       = "tactile"         # L2 触觉电子皮肤
    AUDIO         = "audio"           # L2 声音阵列
    ARM           = "arm"             # L3 机械臂
    HAPTIC        = "haptic"          # L3 触觉反馈
    EEG           = "eeg"             # L4 脑电
    EMG           = "emg"             # L4 肌电


class Direction(Enum):
    IN  = "in"    # 感受器
    OUT = "out"   # 效应器
    BIO = "bio"   # 生物接口(双向)


@dataclass
class Signal:
    """跨模态统一信封。所有 I/O 都必须包成这个形状。"""
    ts: float
    modality: Modality
    direction: Direction
    payload: Dict[str, Any]
    confidence: float
    provenance: str          # REAL / SIMULATED
    unit: str = ""
    latency_ms: float = 0.0

    def short(self) -> str:
        return (f"{self.modality.value:14s} {self.direction.value:3s} "
                f"conf={self.confidence:.2f} [{self.provenance:9s}] {self.payload}")


class IOBus:
    """统一总线: 发布/订阅 + 环形缓冲 + 全量留痕(不可回滚)。"""

    def __init__(self, capacity: int = 4096):
        self._subs: List[Callable[[Signal], None]] = []
        self._ring: List[Signal] = []
        self._capacity = capacity
        self._lock = threading.Lock()
        self._hash_chain: List[str] = []

    def publish(self, sig: Signal) -> Signal:
        with self._lock:
            self._ring.append(sig)
            if len(self._ring) > self._capacity:
                self._ring.pop(0)
            prev = self._hash_chain[-1] if self._hash_chain else "0" * 8
            h = _fnv1a(f"{prev}|{sig.modality.value}|{sig.ts:.6f}")
            self._hash_chain.append(h)
        for fn in self._subs:
            fn(sig)
        return sig

    def subscribe(self, fn: Callable[[Signal], None]) -> None:
        self._subs.append(fn)

    def recent(self, n: int = 5) -> List[Signal]:
        return self._ring[-n:]

    def chain_head(self) -> str:
        return self._hash_chain[-1] if self._hash_chain else ""

    def __len__(self) -> int:
        return len(self._ring)


def _fnv1a(s: str) -> str:
    h = 0x811c9dc5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


# ----------------------------------------------------------------------------
# 1. L1 软件与系统级 —— 数字假肢 (Digital Prosthetics)
# ----------------------------------------------------------------------------

class AccessibilityService:
    """
    非侵入式读取目标应用的控件树。
    真实实现: Linux AT-SPI2 / Android AccessibilityService / Windows UIAutomation。
    沙盒无 AT-SPI 总线 -> SIMULATED, 但接口形状与真机一致。
    """

    def __init__(self, bus: IOBus):
        self.bus = bus
        self.provenance = "SIMULATED"
        # 模拟一张控件树
        self._tree = [
            {"id": "n1", "role": "window",   "name": "evalguard", "rect": (0, 0, 1024, 768)},
            {"id": "n2", "role": "textbox",  "name": "输入事故描述", "rect": (40, 60, 900, 40)},
            {"id": "n3", "role": "button",   "name": "运行检查",   "rect": (40, 120, 160, 44)},
            {"id": "n4", "role": "label",    "name": "结果: 2 BLOCKER", "rect": (40, 180, 600, 30)},
        ]

    def read_tree(self) -> Signal:
        t0 = time.perf_counter()
        time.sleep(0.004)  # 模拟总线往返
        latency = (time.perf_counter() - t0) * 1000
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.ACCESSIBILITY, direction=Direction.IN,
            payload={"nodes": len(self._tree),
                     "focusable": sum(1 for n in self._tree if n["role"] in ("textbox", "button")),
                     "focus": "n2"},
            confidence=0.93, provenance=self.provenance, latency_ms=latency))

    def act(self, node_id: str, action: str) -> Signal:
        node = next((n for n in self._tree if n["id"] == node_id), None)
        ok = node is not None
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.ACCESSIBILITY, direction=Direction.OUT,
            payload={"target": node_id, "action": action, "accepted": ok,
                     "role": node["role"] if node else None},
            confidence=0.90 if ok else 0.0, provenance=self.provenance))


class DOMParser:
    """浏览器 DOM 解析: 结构化读取 + CSS 选择器定位。"""

    def __init__(self, bus: IOBus):
        self.bus = bus
        self.provenance = "SIMULATED"
        self._doc = {
            "title": "evalguard — LLM eval script linter",
            "elements": [
                {"sel": "#price-pro", "tag": "div",  "text": "$99",              "box": (120, 340, 60, 24)},
                {"sel": "#cta",       "tag": "a",    "text": "Get evalguard PRO", "box": (120, 400, 220, 48)},
                {"sel": "#stars",     "tag": "span", "text": "0",                "box": (640, 40, 24, 18)},
            ],
        }

    def query(self, selector: str) -> Signal:
        el = next((e for e in self._doc["elements"] if e["sel"] == selector), None)
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.DOM, direction=Direction.IN,
            payload={"selector": selector, "found": el is not None,
                     "text": el["text"] if el else None,
                     "box": el["box"] if el else None},
            confidence=0.97 if el else 0.0, provenance=self.provenance))

    def extract_text(self) -> Signal:
        txt = " ".join(e["text"] for e in self._doc["elements"])
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.DOM, direction=Direction.IN,
            payload={"chars": len(txt), "tokens": len(txt.split())},
            confidence=0.99, provenance=self.provenance, unit="chars"))


# ----------------------------------------------------------------------------
# 2. L2 物理感官 —— 传感器 (Sensors)
# ----------------------------------------------------------------------------

class DepthCamera:
    """深度相机 / LiDAR: 输出点云 -> 最近障碍距离 + 可通行性。"""

    def __init__(self, bus: IOBus, rng: random.Random):
        self.bus = bus
        self.rng = rng
        self.provenance = "SIMULATED"   # 沙盒无摄像头设备节点

    def read(self, n_points: int = 256) -> Signal:
        t0 = time.perf_counter()
        # 模拟一个 2m 前方有墙的场景, 带高斯噪声
        pts = [abs(self.rng.gauss(2.0, 0.12)) for _ in range(n_points)]
        pts.sort()
        nearest = pts[0]
        median_d = pts[n_points // 2]
        time.sleep(0.008)  # 模拟曝光+传输
        latency = (time.perf_counter() - t0) * 1000
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.DEPTH, direction=Direction.IN,
            payload={"n_points": n_points, "nearest_m": round(nearest, 3),
                     "median_m": round(median_d, 3),
                     "passable": nearest > 0.45},
            confidence=0.88, provenance=self.provenance, unit="m", latency_ms=latency))


class TactileSkin:
    """触觉电子皮肤: taxel 阵列 -> 总力 + 压力质心。"""

    def __init__(self, bus: IOBus, rng: random.Random, grid: int = 8):
        self.bus = bus
        self.rng = rng
        self.grid = grid
        self.provenance = "SIMULATED"

    def read(self) -> Signal:
        taxels = [[round(abs(self.rng.gauss(0.4, 0.9)), 3) for _ in range(self.grid)]
                  for _ in range(self.grid)]
        total = sum(sum(r) for r in taxels)
        if total > 1e-6:
            # 行下标 i -> 纵向 y; 列下标 j -> 横向 x
            cy = sum(i * sum(r) for i, r in enumerate(taxels)) / total / (self.grid - 1)
            cx = sum(j * taxels[i][j]
                     for i in range(self.grid) for j in range(self.grid)) / total / (self.grid - 1)
        else:
            cx = cy = 0.5
        peak = max(max(r) for r in taxels)
        # BUGFIX: total_N 是 64 个 taxel 求和, 均值量级 ~50N, 阈值 1.0 恒真
        # => contact 从不产生假, 判据饱和等于没有判据。改用峰值压强判定。
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.TACTILE, direction=Direction.IN,
            payload={"total_N": round(total, 3), "peak_N": round(peak, 3),
                     "mean_N": round(total / (self.grid ** 2), 4),
                     "centroid": (round(cx, 3), round(cy, 3)),
                     "contact": peak > 1.8},
            confidence=0.85, provenance=self.provenance, unit="N"))


class MicArray:
    """声音阵列: 波束成形 -> 到达方向(DOA) + 声压级。"""

    def __init__(self, bus: IOBus, rng: random.Random, n_mic: int = 4):
        self.bus = bus
        self.rng = rng
        self.n_mic = n_mic
        self.provenance = "SIMULATED"

    def read(self) -> Signal:
        # 模拟目标在 +30 度, 通道间存在时延
        true_doa = 30.0
        measured = true_doa + self.rng.gauss(0, 3.5)
        spl = abs(self.rng.gauss(52.0, 6.0))
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.AUDIO, direction=Direction.IN,
            payload={"n_mic": self.n_mic, "doa_deg": round(measured, 2),
                     "spl_db": round(spl, 1), "voiced": spl > 45},
            confidence=0.79, provenance=self.provenance, unit="deg/dB"))


# ----------------------------------------------------------------------------
# 3. L3 物理执行 —— 执行器 (Actuators) + 安全闸
# ----------------------------------------------------------------------------

class Interlock:
    """
    安全闸。所有 effector 命令必须过这一层。
    默认 dry_run=True: 只记录意图, 不产生物理运动。
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.armed = False          # 死人开关: 必须显式 arm
        # BUGFIX: 节流必须按设备独立。全局单份会让 arm 和 haptic 互相顶,
        # 且会让"越界限位"测试被 rate limit 抢先拦截 => 测试静默失效。
        self._last_cmd_ts: Dict[str, float] = {}
        self.min_interval_ms = 50   # 命令节流
        self.rejected: List[str] = []

    def gate(self, name: str, **limits) -> bool:
        now = time.time() * 1000
        if not self.armed:
            self.rejected.append(f"{name}: not armed (dead-man switch)")
            return False
        dev = name.split(".")[0]
        last = self._last_cmd_ts.get(dev, -1e9)
        if now - last < self.min_interval_ms:
            self.rejected.append(f"{name}: rate limit ({dev})")
            return False
        # 先查限位, 再记时间戳: 保证越界命令报的是越界, 不是节流
        for k, (val, lo, hi) in limits.items():
            if not (lo <= val <= hi):
                self.rejected.append(f"{name}: {k}={val} out of [{lo},{hi}]")
                return False
        self._last_cmd_ts[dev] = now
        return True


class RobotArm:
    """6-DOF 机械臂。工作空间与速度硬限位写在 Interlock 里, 不是写在调用方。"""

    WORKSPACE = {"x": (-0.6, 0.6), "y": (-0.6, 0.6), "z": (0.05, 0.9)}
    MAX_SPEED = 0.35   # m/s

    def __init__(self, bus: IOBus, interlock: Interlock):
        self.bus = bus
        self.il = interlock
        self.provenance = "SIMULATED"
        self.pose = (0.0, 0.0, 0.40)

    def move_to(self, x: float, y: float, z: float, speed: float = 0.15) -> Signal:
        ok = self.il.gate("arm.move_to",
                          x=(x, *self.WORKSPACE["x"]),
                          y=(y, *self.WORKSPACE["y"]),
                          z=(z, *self.WORKSPACE["z"]),
                          speed=(speed, 0.0, self.MAX_SPEED))
        if ok:
            if self.il.dry_run:
                self.pose = (x, y, z)
            payload = {"target": (x, y, z), "speed": speed,
                       "executed": not self.il.dry_run,
                       "reason": "dry_run" if self.il.dry_run else "ok"}
        else:
            payload = {"target": (x, y, z), "executed": False,
                       "reason": self.il.rejected[-1]}
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.ARM, direction=Direction.OUT,
            payload=payload, confidence=1.0 if ok else 0.0,
            provenance=self.provenance, unit="m"))


class HapticMotor:
    """触觉反馈马达: 波形 -> 振动。幅度/时长硬限位。"""

    MAX_AMP = 1.0
    MAX_MS = 2000

    def __init__(self, bus: IOBus, interlock: Interlock):
        self.bus = bus
        self.il = interlock
        self.provenance = "SIMULATED"

    def pulse(self, amp: float, dur_ms: int, waveform: str = "sine") -> Signal:
        ok = self.il.gate("haptic.pulse",
                          amp=(amp, 0.0, self.MAX_AMP),
                          dur_ms=(dur_ms, 0, self.MAX_MS))
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.HAPTIC, direction=Direction.OUT,
            payload={"amp": amp, "dur_ms": dur_ms, "waveform": waveform,
                     "executed": ok and not self.il.dry_run,
                     "reason": ("dry_run" if ok and self.il.dry_run
                                else ("ok" if ok else self.il.rejected[-1]))},
            confidence=1.0 if ok else 0.0, provenance=self.provenance))


# ----------------------------------------------------------------------------
# 4. L4 生物接口 —— BCI / EMG
# ----------------------------------------------------------------------------

class EEGInterface:
    """脑电: 频段功率 -> 注意度/放松度估计。预留真实 LSL/EDF 接入点。"""

    BANDS = {"delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}

    def __init__(self, bus: IOBus, rng: random.Random, n_ch: int = 8):
        self.bus = bus
        self.rng = rng
        self.n_ch = n_ch
        self.provenance = "SIMULATED"   # 无 EEG 放大器和 LSL 源

    def read(self, n_samples: int = 512) -> Signal:
        power = {b: abs(self.rng.gauss(1.0, 0.3)) for b in self.BANDS}
        tot = sum(power.values()) or 1.0
        # beta/(alpha+theta) 常用作注意度代理
        attention = power["beta"] / (power["alpha"] + power["theta"] + 1e-9)
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.EEG, direction=Direction.BIO,
            payload={"n_ch": self.n_ch, "n_samples": n_samples,
                     "band_power": {k: round(v, 3) for k, v in power.items()},
                     "attention_idx": round(min(attention, 3.0), 3),
                     "relaxed": power["alpha"] / tot > 0.30},
            confidence=0.62, provenance=self.provenance, unit="uV^2/Hz"))


class EMGInterface:
    """肌电: 包络 -> 手势分类 -> 意图。"""

    GESTURES = ["rest", "grasp", "point", "pinch"]

    def __init__(self, bus: IOBus, rng: random.Random, n_ch: int = 4):
        self.bus = bus
        self.rng = rng
        self.n_ch = n_ch
        self.provenance = "SIMULATED"

    def read(self) -> Signal:
        env = [abs(self.rng.gauss(0.05, 0.08)) for _ in range(self.n_ch)]
        active = sum(env) > 0.18
        gesture = "rest"
        if active:
            gesture = self.GESTURES[1 + max(range(len(env)), key=lambda i: env[i]) % 3]
        return self.bus.publish(Signal(
            ts=time.time(), modality=Modality.EMG, direction=Direction.BIO,
            payload={"n_ch": self.n_ch,
                     "envelope": [round(e, 4) for e in env],
                     "active": active, "gesture": gesture,
                     "intent": ("arm.grasp" if gesture == "grasp" else
                                "arm.point" if gesture == "point" else
                                "arm.pinch" if gesture == "pinch" else "idle")},
            confidence=0.71 if active else 0.95, provenance=self.provenance, unit="mV"))


# ----------------------------------------------------------------------------
# 5. 洛神本体 —— 组装与闭环
# ----------------------------------------------------------------------------

class LuoShen:
    """碳硅共生体的 I/O 底座。把四层谱系接成一条闭环。"""

    def __init__(self, seed: int = 20261017, dry_run: bool = True):
        self.bus = IOBus()
        self.rng = random.Random(seed)
        self.il = Interlock(dry_run=dry_run)

        # L1 数字假肢
        self.a11y = AccessibilityService(self.bus)
        self.dom = DOMParser(self.bus)
        # L2 传感器
        self.depth = DepthCamera(self.bus, self.rng)
        self.skin = TactileSkin(self.bus, self.rng)
        self.mic = MicArray(self.bus, self.rng)
        # L3 执行器
        self.arm = RobotArm(self.bus, self.il)
        self.haptic = HapticMotor(self.bus, self.il)
        # L4 生物接口
        self.eeg = EEGInterface(self.bus, self.rng)
        self.emg = EMGInterface(self.bus, self.rng)

        self.bus.subscribe(self._on_signal)

    def _on_signal(self, sig: Signal) -> None:
        print(f"  [{sig.ts % 1000:8.3f}] {sig.short()}")

    def perceive(self) -> Dict[str, Signal]:
        print("\n--- PERCEIVE (感受器采样) ---")
        out = {}
        out["a11y"] = self.a11y.read_tree()
        out["dom"] = self.dom.query("#cta")
        out["depth"] = self.depth.read()
        out["skin"] = self.skin.read()
        out["mic"] = self.mic.read()
        out["eeg"] = self.eeg.read()
        out["emg"] = self.emg.read()
        return out

    def decide(self, obs: Dict[str, Signal]) -> List[tuple]:
        """
        极简策略: 由感知直接驱动效应器。
        * 障碍近 -> 后退 (z 抬高, 远离)
        * 有接触 -> 触觉马达短脉冲反馈
        * EMG 手势 -> 转译为机械臂意图
        """
        print("\n--- DECIDE (策略) ---")
        cmds = []
        d = obs["depth"].payload
        if not d["passable"]:
            cmds.append(("arm", "retreat", (0.0, 0.0, 0.55)))
            print(f"  depth.nearest={d['nearest_m']}m < 0.45 -> RETREAT")
        else:
            cmds.append(("arm", "approach", (0.0, 0.0, 0.30)))
            print(f"  depth.nearest={d['nearest_m']}m >= 0.45 -> APPROACH")

        t = obs["skin"].payload
        if t["contact"]:
            amp = min(t["peak_N"] * 0.25, 1.0)
            cmds.append(("haptic", "contact_feedback", (amp, 120)))
            print(f"  skin.peak={t['peak_N']}N > 1.8 -> HAPTIC amp={amp:.2f}")
        else:
            print(f"  skin.peak={t['peak_N']}N <= 1.8 -> no contact, no feedback")

        g = obs["emg"].payload
        if g["intent"] != "idle":
            cmds.append(("arm", g["intent"], (0.15, 0.10, 0.35)))
            print(f"  emg.gesture={g['gesture']} -> {g['intent']}")
        return cmds

    def act(self, cmds: List[tuple]) -> None:
        print("\n--- ACT (效应器下发) ---")
        for kind, tag, args in cmds:
            if kind == "arm":
                self.arm.move_to(*args)
            elif kind == "haptic":
                self.haptic.pulse(*args)
            time.sleep(0.06)   # 尊重节流

    def run(self, ticks: int = 3) -> None:
        print("=" * 78)
        print("EO 世界 · 多模态 I/O 全谱系外设接入架构")
        print(f"dry_run={self.il.dry_run}  armed={self.il.armed}  seed=20261017")
        print("=" * 78)
        for i in range(1, ticks + 1):
            print(f"\n########## TICK {i} ##########")
            obs = self.perceive()
            cmds = self.decide(obs)
            self.act(cmds)
        print("\n" + "=" * 78)
        print(f"总线信号总数: {len(self.bus)}   哈希链头: {self.bus.chain_head()}")
        print(f"安全闸拒绝次数: {len(self.il.rejected)}")
        if self.il.rejected:
            for r in self.il.rejected[:5]:
                print(f"  - {r}")
        print("=" * 78)


# ----------------------------------------------------------------------------
# 6. 入口
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    ls = LuoShen(dry_run=True)

    # 演示 1: 未 arm 状态 —— 所有物理命令必须被拒
    print("\n>>> 演示 A: 未 arm (死人开关断开), 命令应当全部被拒")
    ls.arm.move_to(0.0, 0.0, 0.30)
    ls.haptic.pulse(0.5, 100)

    # 演示 2: arm 之后 —— 命令通过闸, 但 dry_run 不产生物理运动
    print("\n>>> 演示 B: arm 后 (dry_run=True), 命令过闸但不执行")
    ls.il.armed = True
    ls.arm.move_to(0.0, 0.0, 0.30)
    ls.haptic.pulse(0.5, 100)

    # 演示 3: 越界命令 —— 工作空间限位必须拦住
    # 注意: 必须用独立 Interlock, 否则会被上一条命令的节流抢先拦截,
    # 报出的理由是 rate limit 而不是越界 => 这条演示等于没测到越界。
    print("\n>>> 演示 C: 越界命令 (z=2.0 超出 [0.05,0.9]), 必须被拦")
    il_c = Interlock(dry_run=True)
    il_c.armed = True
    arm_c = RobotArm(IOBus(), il_c)
    r = arm_c.move_to(0.0, 0.0, 2.0)
    print(f"  理由: {r.payload['reason']}")
    print(f"  拦住了: {'out of' in str(r.payload['reason'])}")

    # 演示 4: 完整闭环
    print("\n>>> 演示 D: 完整闭环 perceive -> decide -> act")
    ls.run(ticks=3)

    # 演示 5: 通道健全性自检 —— 每条判据必须能同时产生真和假
    print("\n>>> 演示 E: 通道健全性自检 (判据不得饱和)")
    sanity = {}
    rng = random.Random(7)

    # E1: tactile.contact 必须能 False
    skin = TactileSkin(IOBus(), rng)
    vals = [skin.read().payload["contact"] for _ in range(40)]
    sanity["tactile.contact 双向"] = (sum(vals), 40 - sum(vals))
    print(f"  tactile.contact  真 {sum(vals)} / 假 {40 - sum(vals)}  (共 40)")

    # E2: depth.passable 必须能 False —— 把墙挪到 0.2m
    class NearWall(DepthCamera):
        def read(self, n_points=256):
            pts = [abs(self.rng.gauss(0.2, 0.05)) for _ in range(n_points)]
            return self.bus.publish(Signal(
                ts=time.time(), modality=Modality.DEPTH, direction=Direction.IN,
                payload={"n_points": n_points, "nearest_m": round(min(pts), 3),
                         "median_m": round(sorted(pts)[n_points // 2], 3),
                         "passable": min(pts) > 0.45},
                confidence=0.88, provenance="SIMULATED", unit="m"))
    nw = NearWall(IOBus(), rng)
    pv = [nw.read().payload["passable"] for _ in range(20)]
    sanity["depth.passable 双向"] = (sum(pv), 20 - sum(pv))
    print(f"  depth.passable   真 {sum(pv)} / 假 {20 - sum(pv)}  (共 20, 墙在 0.2m)")

    # E3: 隔离验证工作空间限位真的会拦 (清掉节流干扰)
    il2 = Interlock(dry_run=True)
    il2.armed = True
    arm2 = RobotArm(IOBus(), il2)
    r1 = arm2.move_to(0.0, 0.0, 2.0)          # 越界 -> 必须报越界
    print(f"  arm z=2.0        -> {r1.payload['reason']}")
    il3 = Interlock(dry_run=True)
    il3.armed = True
    arm3 = RobotArm(IOBus(), il3)
    r2 = arm3.move_to(0.0, 0.0, 0.5)          # 合法 -> 必须放行
    print(f"  arm z=0.5        -> {r2.payload['reason']} (executed={r2.payload['executed']})")
    sanity["工作空间限位可证伪"] = ("out of" in r1.payload["reason"], r2.payload["reason"] == "dry_run")

    print("\n  自检结论:")
    for k, v in sanity.items():
        print(f"    {k}: {v}")
    ok = all([sanity["tactile.contact 双向"][0] > 0 and sanity["tactile.contact 双向"][1] > 0,
              sanity["depth.passable 双向"][1] > 0,
              sanity["工作空间限位可证伪"][0] and sanity["工作空间限位可证伪"][1]])
    print(f"\n  通道健全性: {'PASS' if ok else 'FAIL'}")

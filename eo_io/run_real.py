#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EO 真实后端 · 端到端验证
=========================
三项验证, 每项都必须能同时产生"真"和"假", 否则判据饱和 = 没有判据 (判据核 #443)。

  A. 可证伪性   — fb0 通道必须在"空白"和"有内容"两种真实状态下给出不同读数
  B. 内核闭环   — uinput 下发的动作, 必须能从内核 evdev 流里真实读回来
  C. 本体觉     — /proc 读数随时间真实变化
"""

import os
import sys
import time
import struct
import random
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eo_io_matrix import IOBus, Signal, Modality, Direction          # noqa: E402
from real_backends import (RealFramebuffer, RealInputSense,           # noqa: E402
                           RealHIDEffector, RealClockBody,
                           EV_REL, EV_KEY, INPUT_EVENT_SIZE)

from PIL import Image, ImageDraw, ImageFont                          # noqa: E402

FB = "/dev/fb0"
W, H, BPP = 1024, 768, 32
NB = W * H * (BPP // 8)
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"

CHK = "%06X" % random.randrange(16 ** 6)
print(f"[CHK] 本轮随机校验码 = {CHK}\n")


def render(lines, size=40):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, size)
    y = 60
    for ln in lines:
        d.text((60, y), ln, fill="black", font=f)
        y += size + 22
    rgba = img.convert("RGBA")
    # 32bpp 帧缓冲按 BGRA 排布
    b, g, r, a = rgba.split()
    return Image.merge("RGBA", (b, g, r, a)).tobytes()


def write_fb(payload: bytes) -> bool:
    with open(FB, "wb") as f:
        n = f.write(payload)
    return n == len(payload)


# ===========================================================================
print("=" * 78)
print("STEP 1 · 真实通道挂载 (provenance 由系统调用决定, 不由注释决定)")
print("=" * 78)
bus = IOBus(capacity=8192)
fb = RealFramebuffer(FB)
inp = RealInputSense("/dev/input/event0")
hid = RealHIDEffector(name="luoshen-eo-hid", dry_run=False)   # 真跑
body = RealClockBody()

rows = [("fb0   帧缓冲(视觉)", fb.provenance, f"{fb.geo} {fb.err or ''}"),
        ("event0 内核输入(触觉)", inp.provenance, inp.err or ""),
        ("uinput 虚拟HID(效应器)", hid.provenance, hid.sysnode or hid.err or ""),
        ("/proc  本体觉", "REAL", "loadavg/meminfo/clock")]
for n, p, extra in rows:
    print(f"  {n:24s} {p:12s} {extra}")

# ===========================================================================
print("\n" + "=" * 78)
print("STEP 2 · 测试 A : fb0 通道可证伪性 (空白 vs 有内容)")
print("=" * 78)
write_fb(b"\x00" * NB)                      # 全黑
s_blank = fb.sense(bus)
write_fb(b"\xff" * NB)                      # 全白
s_white = fb.sense(bus)
content = render([f"EO REAL-BACKEND  {CHK}", "真实帧缓冲自检",
                  f"A blank  {s_blank.payload.get('entropy_bits')}",
                  f"A white  {s_white.payload.get('entropy_bits')}"])
write_fb(content)
s_full = fb.sense(bus)

FEATS = ("mean_luma", "entropy_bits", "edge_density", "dev_ratio", "ink_ratio")
for tag, s in (("blank  ", s_blank), ("white  ", s_white), ("content", s_full)):
    print(f"  {tag} luma={s.payload['mean_luma']:7.3f}  ent={s.payload['entropy_bits']:.4f}  "
          f"edge={s.payload['edge_density']:.6f}  dev={s.payload['dev_ratio']:.6f}  "
          f"ink={s.payload['ink_ratio']:.4f}  conf={s.confidence:.2f} [{s.provenance}]")

# 判据修正: 单特征会饱和(熵区分不了黑屏/白屏), 改用"三态两两至少被一个特征分辨"
def sep(a, b, tol):
    for f in FEATS:
        if abs(a.payload[f] - b.payload[f]) > tol.get(f, 0):
            return f
    return None

TOL = {"mean_luma": 5.0, "entropy_bits": 0.02, "edge_density": 1e-5,
       "dev_ratio": 1e-5, "ink_ratio": 1e-4}
pairs = {"blank|white": (s_blank, s_white), "white|content": (s_white, s_full),
         "blank|content": (s_blank, s_full)}
res_A = {}
for nm, (a, b) in pairs.items():
    f = sep(a, b, TOL)
    res_A[nm] = f
    print(f"  可分 {nm:14s} -> {f or 'NONE  <<< 饱和!'}")

ok_A = all(v is not None for v in res_A.values())
print(f"\n  >> A 通过 = {ok_A}   (三态两两均可分辨)")

# ===========================================================================
print("\n" + "=" * 78)
print("STEP 3 · 测试 B : 内核闭环 (uinput 下发 -> evdev 读回)")
print("=" * 78)
node = hid.sysnode
if not (hid.provenance == "REAL" and node):
    print("  !! uinput 不可用, 闭环测试无法进行 (不伪造结果)")
    ok_B = False
else:
    rfd = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
    import select

    def drain():
        out = []
        while True:
            r, _, _ = select.select([rfd], [], [], 0.08)
            if not r:
                break
            try:
                raw = os.read(rfd, INPUT_EVENT_SIZE * 64)
            except BlockingIOError:
                break
            for i in range(len(raw) // INPUT_EVENT_SIZE):
                _, _, t, c, v = struct.unpack_from("llHHi", raw, i * INPUT_EVENT_SIZE)
                out.append((t, c, v))
        return out

    drain()                                    # 清空残留
    idle = drain()                             # 不动时应为空 -> 阴性对照
    print(f"  静默对照 (不动)          : 读到 {len(idle)} 个事件  [应=0]")

    plan = [(140, -70, False), (0, 0, True), (-90, 45, False)]
    seen_rel = seen_key = 0
    for dx, dy, ck in plan:
        sig = hid.act(bus, dx=dx, dy=dy, click=ck)
        time.sleep(0.08)
        evs = drain()
        r = sum(1 for t, c, v in evs if t == EV_REL)
        k = sum(1 for t, c, v in evs if t == EV_KEY)
        seen_rel += r
        seen_key += k
        print(f"  下发 move({dx:+4d},{dy:+4d}) click={ck!s:5s} -> 读回 rel={r} key={k} "
              f"lat={sig.latency_ms:.2f}ms [{sig.provenance}]")

    ok_B = (len(idle) == 0 and seen_rel >= 4 and seen_key >= 2)
    print(f"\n  >> B 通过 = {ok_B}   (静默时 0, 动作后真实读回 rel={seen_rel} key={seen_key})")
    os.close(rfd)

# ===========================================================================
print("\n" + "=" * 78)
print("STEP 4 · 测试 C : 本体觉随时间真实变化")
print("=" * 78)
b1 = body.sense(bus)
time.sleep(0.6)
_ = [abs(x) for x in range(900000)]           # 真实消耗 CPU
b2 = body.sense(bus)
d_cpu = b2.payload["cpu_s"] - b1.payload["cpu_s"]
d_wall = b2.payload["wall"] - b1.payload["wall"]
print(f"  cpu_s  {b1.payload['cpu_s']:.4f} -> {b2.payload['cpu_s']:.4f}  (Δ={d_cpu:+.4f})")
print(f"  wall   {b1.payload['wall']:.3f} -> {b2.payload['wall']:.3f}  (Δ={d_wall:+.3f}s)")
ok_C = d_cpu > 0 and d_wall > 0
print(f"\n  >> C 通过 = {ok_C}")

# ===========================================================================
print("\n" + "=" * 78)
print("STEP 5 · provenance 决算")
print("=" * 78)
real = sum(1 for s in bus.recent(4096) if s.provenance == "REAL")
unav = sum(1 for s in bus.recent(4096) if s.provenance == "UNAVAILABLE")
print(f"  本轮信号总数 = {len(bus)}   REAL={real}  UNAVAILABLE={unav}")
print(f"  哈希链头     = {bus.chain_head()}")
print(f"\n  仍然 SIMULATED 且不可变真: 深度相机 / 电子皮肤 / 麦克风阵列 /")
print(f"                             机械臂 / EEG / EMG  ——沙盒无此硬件, 不冒充")

print("\n" + "=" * 78)
print(f"  A 可证伪={ok_A}   B 内核闭环={ok_B}   C 本体觉={ok_C}   校验码 {CHK}")
print("=" * 78)

# 自检图落盘: 把结果渲染上屏再采集回来
res = [f"EO REAL BACKEND {CHK}", f"A falsifiable {ok_A}", f"B kernel loop {ok_B}",
       f"C propriocept  {ok_C}", f"signals {len(bus)} REAL {real}",
       f"chain {bus.chain_head()}", f"entropy {s_full.payload['entropy_bits']}",
       f"rel {seen_rel if ok_B else 0} key {seen_key if ok_B else 0}"]
write_fb(render(res, size=34))
os.makedirs("/data/workspace/luoshen-o1/experiments/exp111_real_io", exist_ok=True)
os.system(f"cp {FB} /data/workspace/luoshen-o1/experiments/exp111_real_io/captured.raw "
          f"2>/dev/null && echo 'framebuffer captured'")
hid.destroy()

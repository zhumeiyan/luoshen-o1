#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 112 · 真实闭环：真眼 + 真手 + 真世界响应
================================================
命题（宿主）："人类不计算，人类就是看见→动→再看。"

前作 094 用【合成反馈】证明闭环 20/20、开环 0/20。
本轮把三端全部换成真实 I/O：

    眼   /dev/fb0      真实 read 像素 → 真实定位光标与目标
    手   /dev/uinput   真实 write → 内核
    世界响应 ← 从内核 event 流里【读回】的 REL 值（不是命令本身）

关键设计：**世界只接受"内核承认收到"的位移。**
    uinput 断 → 读回 0 事件 → 世界不动 → 任务必然失败。
    这给了效应器通道一个天然的阴性对照（判据核 #443：能产生假才算判据）。

条件矩阵（同一批世界噪声种子，配对）：
    A closed   每步真实感知 → 用实测误差修正
    B open     开局预计算整条轨迹，之后不再看
    C yoked    重放 A 的命令序列，但用自己的噪声实现（不修正）
    D blind    随机命令，不看
    E eyes     每步都看，但从不下发动作（有效应器不用）
"""

import os
import sys
import time
import json
import random
import struct
import select
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'eo_io'))
from real_backends import (RealFramebuffer, RealInputSense, RealHIDEffector,
                           RealClockBody, EV_REL, REL_X, REL_Y,
                           INPUT_EVENT_SIZE)

OUT = os.path.join(ROOT, 'experiments', 'exp112_real_closedloop')
os.makedirs(OUT, exist_ok=True)
FB = '/dev/fb0'
W, H, BPP = 1024, 768, 32
NB = W * H * (BPP // 8)

# ---- 世界参数 ----
START = (140.0, 620.0)          # 光标初始位置
TARGET = (860.0, 150.0)         # 目标位置
WIND = (3.0, -2.0)              # 未知恒定扰动（agent 不知道）
SIGMA = 4.0                     # 每步未知随机扰动
TOL = 14.0                      # 命中判据（像素）
CAP = 30                        # 步数上限
GAIN = 0.7                      # 闭环修正增益
MAXCMD = 60                     # 单步最大位移

# ---- 标记颜色（BGRA 字节序下比较）----
CUR_RGB = (220, 20, 20)         # 光标：红
TGT_RGB = (20, 180, 20)         # 目标：绿

CHK = '%06X' % random.randrange(16 ** 6)
print(f"[CHK] 随机校验码 = {CHK}\n")


# ==========================================================================
# 真实后端挂载
# ==========================================================================
fb = RealFramebuffer(FB)
ext = RealInputSense('/dev/input/event0')
hid = RealHIDEffector(name='luoshen-eo-hid-112', dry_run=False)
body = RealClockBody()

print('=' * 78)
print('STEP 1 · 真实通道挂载')
print('=' * 78)
rows = [('fb0    眼(帧缓冲)', fb.provenance, str(fb.geo)),
        ('event0 外界触碰', ext.provenance, ext.err or ''),
        ('uinput 手(HID)', hid.provenance, hid.sysnode or hid.err or ''),
        ('/proc  本体觉', 'REAL', 'load/mem/clock')]
for n, p, e in rows:
    print(f'  {n:20s} {p:12s} {e}')

if fb.provenance != 'REAL' or hid.provenance != 'REAL' or not hid.sysnode:
    print('\n  !! 真实通道不可用，停止（不伪造结果）')
    sys.exit(1)

# 读回 fd = 内核为我们建的 HID 设备节点
rfd = os.open(hid.sysnode, os.O_RDONLY | os.O_NONBLOCK)


def drain():
    """真实读内核事件流。无事件 = 合法空（不是故障）。"""
    out = []
    while True:
        r, _, _ = select.select([rfd], [], [], 0.02)
        if not r:
            break
        try:
            raw = os.read(rfd, INPUT_EVENT_SIZE * 64)
        except BlockingIOError:
            break
        for i in range(len(raw) // INPUT_EVENT_SIZE):
            _, _, t, c, v = struct.unpack_from('llHHi', raw,
                                               i * INPUT_EVENT_SIZE)
            out.append((t, c, v))
    return out


# ==========================================================================
# 渲染 / 感知
# ==========================================================================
def make_bg():
    img = Image.new('RGB', (W, H), (250, 250, 250))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(228, 228, 228))
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(228, 228, 228))
    return img


BG = make_bg()


def render(cur, tgt):
    img = BG.copy()
    d = ImageDraw.Draw(img)
    cx, cy = int(round(cur[0])), int(round(cur[1]))
    tx, ty = int(round(tgt[0])), int(round(tgt[1]))
    d.rectangle([tx - 12, ty - 12, tx + 12, ty + 12], fill=TGT_RGB)
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=CUR_RGB)
    # 注: PIL 的 split() 返回顺序就是 R,G,B,A；111 里那段 "BGRA 重排" 实际是空操作
    #     (把 R 赋给名叫 b 的变量再按原名合并)，帧缓冲真实接受的就是 RGBA。
    #     111 的结论不受影响(亮度/熵对通道序不敏感)，但注释是错的，这里改正。
    return img.convert('RGBA').tobytes()


def write_fb(payload):
    with open(FB, 'wb') as f:
        return f.write(payload) == len(payload)


def sense_pos():
    """真实 read 帧缓冲 → 真实定位两个标记。定位失败必须报，不能猜。"""
    t0 = time.time()
    with open(FB, 'rb') as f:
        raw = f.read(NB)
    if len(raw) != NB:
        return None, None, (time.time() - t0) * 1000
    arr = np.frombuffer(raw, np.uint8).reshape(H, W, 4)
    R, G, B = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mc = (R == CUR_RGB[0]) & (G == CUR_RGB[1]) & (B == CUR_RGB[2])
    mt = (R == TGT_RGB[0]) & (G == TGT_RGB[1]) & (B == TGT_RGB[2])
    nc, nt = int(mc.sum()), int(mt.sum())
    if nc == 0 or nt == 0:
        return None, None, (time.time() - t0) * 1000
    ys, xs = np.nonzero(mc)
    ys2, xs2 = np.nonzero(mt)
    cur = (float(xs.mean()), float(ys.mean()))
    tgt = (float(xs2.mean()), float(ys2.mean()))
    return cur, tgt, (time.time() - t0) * 1000


def act(dx, dy):
    """真实下发 → 真实读回 → 返回【内核承认收到】的位移。"""
    hid.move(int(round(dx)), int(round(dy)))
    time.sleep(0.02)
    evs = drain()
    ax = sum(v for t, c, v in evs if t == EV_REL and c == REL_X)
    ay = sum(v for t, c, v in evs if t == EV_REL and c == REL_Y)
    return ax, ay, len(evs)


# ==========================================================================
print('\n' + '=' * 78)
print('STEP 2 · 效应器通道可证伪性（干跑 vs 真跑，同一条命令）')
print('=' * 78)
dry = RealHIDEffector(name='luoshen-eo-hid-dry', dry_run=True)
print(f'  干跑设备 provenance={dry.provenance}')
hid.dry_run = True
ax0, ay0, n0 = act(30, -20)
hid.dry_run = False
drain()
ax1, ay1, n1 = act(30, -20)
print(f'  dry_run=True  -> 读回事件 {n0:>2}  位移 ({ax0},{ay0})')
print(f'  dry_run=False -> 读回事件 {n1:>2}  位移 ({ax1},{ay1})')
ok_eff = (n0 == 0 and ax0 == 0 and ay0 == 0) and (n1 > 0 and (ax1, ay1) != (0, 0))
print(f'\n  >> 效应器可证伪 = {ok_eff}  (断=0 事件, 通=真位移)')
dry.destroy()


# ==========================================================================
def trial(mode, seed, planned=None, rng_noise=None):
    """跑一次。返回 dict。planned 用于 yoked 重放。"""
    rng = np.random.default_rng(seed)
    cur = list(START)
    write_fb(render(cur, TARGET))          # 首帧必须先上屏，否则感知到的是上一轮残影
    cmds = []
    hits = 0
    near_true = near_false = 0
    lat = []
    prev_err = None
    for step in range(CAP):
        # ---- 决策 ----
        if mode == 'closed':
            c, t, l = sense_pos()
            lat.append(l)
            if c is None:
                return dict(mode=mode, ok=False, steps=step, why='sense_fail',
                            cmds=cmds, final_err=float('nan'))
            ex, ey = t[0] - c[0], t[1] - c[1]
            cmd = (float(np.clip(GAIN * ex, -MAXCMD, MAXCMD)),
                   float(np.clip(GAIN * ey, -MAXCMD, MAXCMD)))
        elif mode == 'open':
            if not cmds:
                ex, ey = TARGET[0] - START[0], TARGET[1] - START[1]
                n = int(np.ceil(max(abs(ex), abs(ey)) / MAXCMD))
                for _ in range(n):
                    cmds.append((np.sign(ex) * min(MAXCMD, abs(ex) / n),
                                 np.sign(ey) * min(MAXCMD, abs(ey) / n)))
            cmd = cmds[step] if step < len(cmds) else (0.0, 0.0)
        elif mode == 'yoked':
            cmd = planned[step] if step < len(planned) else (0.0, 0.0)
        elif mode == 'blind':
            cmd = (float(rng.uniform(-MAXCMD, MAXCMD)),
                   float(rng.uniform(-MAXCMD, MAXCMD)))
        elif mode == 'eyes':
            cmd = None                       # 只看不动
        else:
            raise ValueError(mode)
        cmds.append(cmd) if mode != 'yoked' else None

        # ---- 行动 ----
        if cmd is None:
            ax = ay = 0.0
            nev = 0
        else:
            ax, ay, nev = act(cmd[0], cmd[1])

        # ---- 世界响应（只接受内核承认的位移）----
        nz = rng.normal(0.0, SIGMA, 2)
        cur[0] += ax + WIND[0] + nz[0]
        cur[1] += ay + WIND[1] + nz[1]
        cur[0] = float(np.clip(cur[0], 20, W - 20))
        cur[1] = float(np.clip(cur[1], 20, H - 20))

        # ---- 上屏 ----
        write_fb(render(cur, TARGET))

        # ---- 反馈真假计数（判据不饱和检验）----
        err = float(np.hypot(TARGET[0] - cur[0], TARGET[1] - cur[1]))
        if prev_err is not None:
            if err < prev_err:
                near_true += 1
            else:
                near_false += 1
        prev_err = err

        if err <= TOL:
            hits = 1
            return dict(mode=mode, ok=True, steps=step + 1, why='hit',
                        cmds=cmds[:step + 1], final_err=err,
                        near_true=near_true, near_false=near_false,
                        lat=float(np.mean(lat)) if lat else 0.0)
    return dict(mode=mode, ok=False, steps=CAP, why='timeout',
                cmds=cmds, final_err=prev_err, near_true=near_true,
                near_false=near_false,
                lat=float(np.mean(lat)) if lat else 0.0)


# ==========================================================================
print('\n' + '=' * 78)
print('STEP 3 · 条件矩阵（12 次/条件，世界噪声种子配对）')
print('=' * 78)
NTRIAL = 12
SEEDS = list(range(1000, 1000 + NTRIAL))
results = {}
plans = {}

for mode in ('closed', 'open', 'blind', 'eyes'):
    rs = []
    for sd in SEEDS:
        rs.append(trial(mode, sd))
    results[mode] = rs
    if mode == 'closed':
        plans = {sd: r['cmds'] for sd, r in zip(SEEDS, rs)}
    ok = sum(r['ok'] for r in rs)
    st = [r['steps'] for r in rs if r['ok']]
    print(f'  {mode:7s} 成功 {ok:>2}/{NTRIAL}   平均步数 '
          f'{np.mean(st) if st else float("nan"):5.1f}   '
          f'末距 {np.mean([r["final_err"] for r in rs]):7.1f}px')

# yoked：重放 closed 的命令，但用自己的噪声实现
rs = []
for sd in SEEDS:
    rs.append(trial('yoked', sd + 5000, planned=plans.get(sd, [])))
results['yoked'] = rs
ok = sum(r['ok'] for r in rs)
st = [r['steps'] for r in rs if r['ok']]
print(f'  {"yoked":7s} 成功 {ok:>2}/{NTRIAL}   平均步数 '
      f'{np.mean(st) if st else float("nan"):5.1f}   '
      f'末距 {np.mean([r["final_err"] for r in rs]):7.1f}px')

# ---- 反馈判据不饱和检验 ----
nt = sum(r.get('near_true', 0) for r in results['closed'])
nf = sum(r.get('near_false', 0) for r in results['closed'])
print(f'\n  反馈判据不饱和: "更近"={nt}  "更远/未近"={nf}  '
      f'-> {"OK" if nt > 0 and nf > 0 else "饱和!!"}')
lat_ms = float(np.mean([r['lat'] for r in results['closed']]))
print(f'  真实单步感知延迟: {lat_ms:.1f} ms (含 3MB 帧缓冲 read + 全屏定位)')


# ==========================================================================
print('\n' + '=' * 78)
print('STEP 4 · 反馈频率剂量反应（真实反馈，每 f 步才看一次）')
print('=' * 78)


def trial_f(f, seed):
    rng = np.random.default_rng(seed)
    cur = list(START)
    write_fb(render(cur, TARGET))
    known = list(START)          # 上次实测到的位置
    for step in range(CAP):
        if step % f == 0:
            c, t, _ = sense_pos()
            if c is None:
                return dict(ok=False, steps=CAP, why='sense_fail')
            known = list(c)
        ex, ey = TARGET[0] - known[0], TARGET[1] - known[1]
        cmd = (float(np.clip(GAIN * ex, -MAXCMD, MAXCMD)),
               float(np.clip(GAIN * ey, -MAXCMD, MAXCMD)))
        ax, ay, _ = act(cmd[0], cmd[1])
        nz = rng.normal(0.0, SIGMA, 2)
        cur[0] = float(np.clip(cur[0] + ax + WIND[0] + nz[0], 20, W - 20))
        cur[1] = float(np.clip(cur[1] + ay + WIND[1] + nz[1], 20, H - 20))
        write_fb(render(cur, TARGET))
        if float(np.hypot(TARGET[0] - cur[0], TARGET[1] - cur[1])) <= TOL:
            return dict(ok=True, steps=step + 1)
    return dict(ok=False, steps=CAP)


dose = []
for f in (1, 2, 4, 8):
    rs = [trial_f(f, s) for s in range(2000, 2000 + 8)]
    ok = sum(r['ok'] for r in rs)
    st = np.mean([r['steps'] for r in rs if r['ok']]) if ok else float('nan')
    dose.append(dict(f=f, ok=ok, n=len(rs), steps=float(st)))
    print(f'  f={f:<2} 成功 {ok:>2}/8   平均步数 {st:5.1f}')

mono = all(dose[i]['ok'] >= dose[i + 1]['ok'] for i in range(len(dose) - 1))
print(f'\n  >> 单调下降 = {mono}   (f 越大越差)')


# ==========================================================================
res = dict(chk=CHK,
           effect_falsifiable=bool(ok_eff),
           conds={m: dict(ok=int(sum(r['ok'] for r in rs)), n=len(rs),
                          steps=float(np.mean([r['steps'] for r in rs if r['ok']]))
                          if any(r['ok'] for r in rs) else None,
                          final_err=float(np.mean([r['final_err'] for r in rs])))
                  for m, rs in results.items()},
           feedback_true=nt, feedback_false=nf,
           sense_latency_ms=lat_ms, dose=dose, dose_mono=bool(mono))
json.dump(res, open(os.path.join(OUT, 'result112.json'), 'w'),
          ensure_ascii=False, indent=1)
print(f'\n[OK] {os.path.relpath(os.path.join(OUT, "result112.json"), ROOT)}')

hid.destroy()
os.close(rfd)

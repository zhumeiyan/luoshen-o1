#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 112b · 把 112 的真实轨迹接进本体引擎
============================================
112 证明了：闭环 12/12、开环 0/12，用的是真实帧缓冲 + 真实 uinput。
本轮问的是另一件事：**这些真实轨迹进入内在结构后，留下了什么。**

四条输入流全部是 112 里【真实测到】的位置误差序列（不是合成）：
    closed  误差单调收敛（行动与反馈耦合）
    yoked   同样命令、反馈不耦合（8/12）
    eyes    每步都看但不动（误差只被世界推着走）
    none    通道断（全零）

命题：结构差异由"是否在接触世界"决定，还是由"接触得好不好"决定。
"""

import os
import sys
import json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'core'))
sys.path.insert(0, os.path.join(ROOT, 'eo_io'))
from core.life5 import Life5
import importlib.util

# 复用 112 的真实 I/O 函数（不重新实现，避免两份实现漂移）
spec = importlib.util.spec_from_file_location(
    'exp112', os.path.join(ROOT, 'experiments', 'exp112_real_closedloop.py'))

# 112 脚本顶层就会跑实验，这里改为直接导入其内部函数会触发执行 → 改为内联最小实现
import struct
import select
import time
from PIL import Image, ImageDraw
from real_backends import RealFramebuffer, RealHIDEffector, EV_REL, REL_X, REL_Y, INPUT_EVENT_SIZE

W, H = 1024, 768
NB = W * H * 4
FB = '/dev/fb0'
START = (140.0, 620.0)
TARGET = (860.0, 150.0)
WIND = (3.0, -2.0)
SIGMA = 4.0
TOL = 14.0
CAP = 30
GAIN = 0.7
MAXCMD = 60
CUR_RGB = (220, 20, 20)
TGT_RGB = (20, 180, 20)

fb = RealFramebuffer(FB)
hid = RealHIDEffector(name='luoshen-eo-hid-112b', dry_run=False)
assert fb.provenance == 'REAL' and hid.provenance == 'REAL' and hid.sysnode
rfd = os.open(hid.sysnode, os.O_RDONLY | os.O_NONBLOCK)


def drain():
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
            _, _, t, c, v = struct.unpack_from('llHHi', raw, i * INPUT_EVENT_SIZE)
            out.append((t, c, v))
    return out


def render(cur):
    img = Image.new('RGB', (W, H), (250, 250, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([int(TARGET[0]) - 12, int(TARGET[1]) - 12,
                 int(TARGET[0]) + 12, int(TARGET[1]) + 12], fill=TGT_RGB)
    d.ellipse([cur[0] - 9, cur[1] - 9, cur[0] + 9, cur[1] + 9], fill=CUR_RGB)
    return img.convert('RGBA').tobytes()


def write_fb(p):
    with open(FB, 'wb') as f:
        return f.write(p) == len(p)


def sense_pos():
    with open(FB, 'rb') as f:
        raw = f.read(NB)
    arr = np.frombuffer(raw, np.uint8).reshape(H, W, 4)
    R, G, B = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mc = (R == CUR_RGB[0]) & (G == CUR_RGB[1]) & (B == CUR_RGB[2])
    mt = (R == TGT_RGB[0]) & (G == TGT_RGB[1]) & (B == TGT_RGB[2])
    if mc.sum() == 0 or mt.sum() == 0:
        return None, None
    ys, xs = np.nonzero(mc)
    ys2, xs2 = np.nonzero(mt)
    return (float(xs.mean()), float(ys.mean())), (float(xs2.mean()), float(ys2.mean()))


def act(dx, dy):
    hid.move(int(round(dx)), int(round(dy)))
    time.sleep(0.02)
    evs = drain()
    ax = sum(v for t, c, v in evs if t == EV_REL and c == REL_X)
    ay = sum(v for t, c, v in evs if t == EV_REL and c == REL_Y)
    return ax, ay


def capture(mode, seed, planned=None):
    """跑一次并【记录真实测到的误差序列】。"""
    rng = np.random.default_rng(seed)
    cur = list(START)
    write_fb(render(cur))
    series = []
    cmds = []
    for step in range(CAP):
        if mode == 'closed':
            c, t = sense_pos()
            if c is None:
                break
            ex, ey = t[0] - c[0], t[1] - c[1]
            cmd = (float(np.clip(GAIN * ex, -MAXCMD, MAXCMD)),
                   float(np.clip(GAIN * ey, -MAXCMD, MAXCMD)))
        elif mode == 'yoked':
            cmd = planned[step] if step < len(planned) else (0.0, 0.0)
        elif mode == 'eyes':
            cmd = None
        cmds.append(cmd)
        if cmd is None:
            ax = ay = 0.0
        else:
            ax, ay = act(cmd[0], cmd[1])
        nz = rng.normal(0.0, SIGMA, 2)
        cur[0] = float(np.clip(cur[0] + ax + WIND[0] + nz[0], 20, W - 20))
        cur[1] = float(np.clip(cur[1] + ay + WIND[1] + nz[1], 20, H - 20))
        write_fb(render(cur))
        series.append((TARGET[0] - cur[0], TARGET[1] - cur[1]))
    return series, cmds


# ==========================================================================
print('=' * 78)
print('实验 112b · 真实轨迹 → 本体引擎')
print('=' * 78)
NTR = 8
streams = {}
plans = {}
for sd in range(3000, 3000 + NTR):
    s, c = capture('closed', sd)
    streams.setdefault('closed', []).append(s)
    plans[sd] = c
for sd in range(3000, 3000 + NTR):
    s, _ = capture('yoked', sd + 5000, planned=plans[sd])
    streams.setdefault('yoked', []).append(s)
for sd in range(3000, 3000 + NTR):
    s, _ = capture('eyes', sd)
    streams.setdefault('eyes', []).append(s)

print(f'\n[真实轨迹] 每条件 {NTR} 条')
for k, v in streams.items():
    lens = [len(s) for s in v]
    fin = [float(np.hypot(*s[-1])) for s in v]
    print(f'  {k:7s} 长度 {min(lens)}~{max(lens)}  末距均值 {np.mean(fin):7.1f}px')


def make_stream(name, T=600):
    """把真实误差序列接成引擎输入：每拍取一条真实轨迹上的实测分量。"""
    traj = streams[name]
    out = []
    i = 0
    while len(out) < T:
        for s in traj:
            for ex, ey in s:
                out.append((ex, ey))
                if len(out) >= T:
                    break
            if len(out) >= T:
                break
    return np.asarray(out[:T], float)


# ★ 能量匹配: 三条真实流的【量级】差别巨大(末距 7.7 / 44.7 / 762.7 px),
#   不归一化就会把"输入有多大"和"输入是什么形状"混在一起。
#   这里按各自 RMS 归一化到 1, 隔离出"耦合结构"这一个变量。
S = {k: make_stream(k) for k in ('closed', 'yoked', 'eyes')}
for k in list(S):
    rms = float(np.sqrt(np.mean(S[k] ** 2)))
    S[k] = S[k] / max(rms, 1e-12)
    print(f'  [归一化] {k:7s} 原 RMS = {rms:8.1f}px -> 1.0')
S['none'] = np.zeros((600, 2))


def struct_skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def run(seed, name, amp, T=600, N=8):
    lf = Life5(N=N, seed=seed, ratio=0.45, sigma_in=0.10)
    st = S[name]
    for t in range(T):
        lf.net_push = np.zeros(N)
        lf.net_push[0] = amp * st[t, 0]
        lf.net_push[1] = amp * st[t, 1]
        lf.step()
    return lf


SEEDS = list(range(16))


def scan(name, amp):
    lfs = {s: run(s, name, amp) for s in SEEDS}
    al = [s for s in SEEDS if lfs[s].alive]
    return lfs, al


print('\n[① 参数有效性] amp 扫描（用 closed 真实流），确认注入真有梯度')
for amp in (0.0, 0.02, 0.05, 0.1, 0.2, 0.4):
    lfs, al = scan('closed', amp)
    sk = [struct_skew(lfs[s]) for s in al]
    print(f'  amp={amp:<5} 存活 {len(al):>2}/{len(SEEDS)}  偏度 '
          f'{np.mean(sk) if sk else float("nan"):.4f}')

AMP = 0.2
print(f'\n  → 采用 amp={AMP}')

print('\n[② 条件对比] 真实误差流 → 结构')
lfs_all, table = {}, []
for name in ('closed', 'yoked', 'eyes', 'none'):
    lfs, al = scan(name, AMP)
    lfs_all[name] = (lfs, al)
    sk = [struct_skew(lfs[s]) for s in al]
    table.append(dict(cond=name, alive=len(al), n=len(SEEDS),
                      skew=float(np.mean(sk)) if sk else float('nan')))
    print(f'  {name:7s} 存活 {len(al):>2}/{len(SEEDS)}  偏度 '
          f'{np.mean(sk) if sk else float("nan"):.4f}')

print('\n[③ 配对差 + bootstrap CI] 共同存活子集')
common = set(SEEDS)
for lfs, al in lfs_all.values():
    common &= set(al)
common = sorted(common)
print(f'   共同存活 seeds: n={len(common)}')


def paired(a, b, nboot=4000, seed=7):
    # 逐对共同存活子集: 全局交集可能为空(某条件全灭), 逐对才不会把样本丢光
    cs = sorted(set(lfs_all[a][1]) & set(lfs_all[b][1]))
    if len(cs) < 3:
        return float('nan'), float('nan'), float('nan'), len(cs)
    la = [struct_skew(lfs_all[a][0][s]) for s in cs]
    lb = [struct_skew(lfs_all[b][0][s]) for s in cs]
    d = np.asarray(la) - np.asarray(lb)
    rng = np.random.default_rng(seed)
    bs = np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(nboot)])
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(cs)


for a, b in (('closed', 'none'), ('closed', 'yoked'), ('closed', 'eyes'),
             ('yoked', 'none'), ('eyes', 'none')):
    m, lo, hi, n = paired(a, b)
    sig = (lo > 0) or (hi < 0)
    print(f'  {a:7s} - {b:7s}  n={n:<3} Δ={m:+.4f}  CI[{lo:+.4f},{hi:+.4f}]  '
          f'{"显著" if sig else "不显著(跨0)"}')

json.dump(dict(amp=AMP, table=table, common=common),
          open(os.path.join(ROOT, 'experiments', 'exp112_real_closedloop',
                            'result112b.json'), 'w'),
          ensure_ascii=False, indent=1)
hid.destroy()
os.close(rfd)

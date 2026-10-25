#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""096 主实验：眼睛不动就瞎 —— 主动视觉，不靠计算靠动

Stage A 六种眼动策略（含 oracle 计算式对照）
Stage B 幅度剂量反应（不动 → 消失的阈值在哪）
Stage C 自由度阶梯（带摄像头的什么能动）
Stage D 接引擎：主动 vs 稳定 vs 无感官
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from exp096 import *

OUT = os.path.dirname(os.path.abspath(__file__))
R = {}
T0 = time.time()
STEPS = 60

def log(*a):
    print(*a, flush=True)

# ============================== Stage A ==============================
log('\n== Stage A 六种眼动策略 ==')
MODES = ['stabilized', 'tremor', 'drift', 'microsaccade', 'saccade', 'oracle', 'cheat']
SEEDS = [0, 1, 2]
A = {m: [] for m in MODES}
for m in MODES:
    for s in SEEDS:
        img, truth = make_world(s)
        r = run_trial(img, truth, m, steps=STEPS, seed=100 + s)
        A[m].append(r)
    avg = lambda k: float(np.mean([x[k] for x in A[m]]))
    log(f'  {m:13s} 瞬时读对 {avg("read_now"):5.2f}/{20}  累积读对 {avg("read_mem"):5.2f}/20'
        f'  可见量 {avg("info_now"):.4f}  适应 {avg("adapt"):.3f}')
R['A_modes'] = A

# ============================== Stage B ==============================
log('\n== Stage B 眼动幅度剂量反应（不动就瞎的阈值）==')
AMPS = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
B = {a: [] for a in AMPS}
img, truth = make_world(0)
for amp in AMPS:
    for s in range(3):
        rng = np.random.default_rng(500 + s)
        fov = Fovea(img); ret = Retina(img.shape)
        fx, fy = W / 2, H / 2
        mem = np.zeros_like(img)
        for t in range(STEPS):
            if amp > 0:
                fx += rng.normal(0, amp); fy += rng.normal(0, amp)
                fx = float(np.clip(fx, 20, W - 20)); fy = float(np.clip(fy, 20, H - 20))
            vis, a = ret.step(fov.render(fx, fy))
            mem = np.maximum(mem, vis)
        ts = set(str(t['v']) for t in truth)
        B[amp].append(dict(read=len(ocr_digits(mem) & ts),
                           info=float((mem < 200).mean()), adapt=float(a)))
    mm = lambda k: float(np.mean([x[k] for x in B[amp]]))
    log(f'  幅度 {amp:5.1f}px  累积读对 {mm("read"):5.2f}/20  可见量 {mm("info"):.4f}  终适应 {mm("adapt"):.3f}')
R['B_amp'] = {str(k): v for k, v in B.items()}

# ============================== Stage C ==============================
log('\n== Stage C 自由度阶梯：带摄像头的什么能动 ==')


def shift_img(a, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(a, M, (a.shape[1], a.shape[0]),
                          borderMode=cv2.BORDER_CONSTANT, borderValue=255)


def make_occluded_world(seed, n_small=8, n_big=12):
    """双层世界：背景层（大字+小字）+ 前景层（遮挡条）。视差需要移动视点。"""
    rng = np.random.default_rng(seed)
    bg = Image.new('L', (W, H), 255); d = ImageDraw.Draw(bg)
    fb = ImageFont.truetype(FONT_PATH, 40)
    fs = ImageFont.truetype(FONT_PATH, 13)
    truth = []
    placed = []
    def place(font, tag, n):
        cnt = 0; tries = 0
        while cnt < n and tries < 900:
            tries += 1
            x = int(rng.integers(60, W - 150)); y = int(rng.integers(40, H - 70))
            if any(abs(x - px) < 130 and abs(y - py) < 60 for px, py in placed):
                continue
            placed.append((x, y))
            v = int(rng.integers(10, 100))
            d.text((x, y), str(v), fill=0, font=font)
            truth.append(dict(x=x, y=y, v=v, tag=tag)); cnt += 1
    place(fb, 'big', n_big)
    place(fs, 'small', n_small)
    # 前景遮挡条：盖住一部分大字
    fg = Image.new('L', (W, H), 255); fd = ImageDraw.Draw(fg)
    for t in [x for x in truth if x['tag'] == 'big'][:6]:
        fd.rectangle([t['x'] - 6, t['y'] - 4, t['x'] + 92, t['y'] + 52], fill=190)
    return np.array(bg, np.uint8), np.array(fg, np.uint8), truth


def render_view(bg, fg, shift):
    """视点平移 shift：前景（近）动得多，背景（远）动得少 → 视差使被遮挡物露出"""
    b = shift_img(bg, shift * 0.35, 0)
    f = shift_img(fg, shift * 1.00, 0)
    return np.where(f < 250, f, b).astype(np.uint8)


def run_dof(dof, seed=0, steps=STEPS):
    bg, fg, truth = make_occluded_world(seed)
    rng = np.random.default_rng(900 + seed)
    fov0 = Fovea(render_view(bg, fg, 0.0))
    ret = Retina((H, W))
    fx, fy = W / 2, H / 2
    mem = np.zeros((H, W), np.uint8)
    for t in range(steps):
        # --- 自由度分配 ---
        if dof >= 2 and t % 3 == 2:                      # 扫视：注视点全平面移动
            fx = rng.uniform(60, W - 60); fy = rng.uniform(60, H - 60)
        elif dof == 1:                                   # 只能微动
            fx += rng.normal(0, 10); fy += rng.normal(0, 10)
            fx = float(np.clip(fx, 20, W - 20)); fy = float(np.clip(fy, 20, H - 20))
        zoom = 1.0
        if dof >= 3 and t % 6 == 5:                      # zoom：凑近看小字
            zoom = rng.uniform(2.0, 3.5)
        roll = 0.0
        if dof >= 4 and t % 9 == 8:                      # roll：旋转
            roll = rng.uniform(0, np.pi)
        shift = 0.0
        if dof >= 6:                                     # 视点平移：走动产生视差
            shift = 60.0 * np.sin(2 * np.pi * t / 20.0)
        world = render_view(bg, fg, shift)
        fov = Fovea(world)
        vis, a = ret.step(fov.render(fx, fy, zoom=zoom, roll=roll))
        mem = np.maximum(mem, vis)
    big = set(str(t['v']) for t in truth if t['tag'] == 'big')
    small = set(str(t['v']) for t in truth if t['tag'] == 'small')
    got = ocr_digits(mem)
    return dict(dof=dof, seed=seed, big=len(got & big), small=len(got & small),
                total=len(got & (big | small)), adapt=float(a))


C = {}
for dof in [1, 2, 3, 4, 6]:
    C[dof] = [run_dof(dof, seed=s) for s in range(3)]
    m = lambda k: float(np.mean([x[k] for x in C[dof]]))
    log(f'  DOF {dof}  大字 {m("big"):5.2f}/12  小字 {m("small"):5.2f}/8  合计 {m("total"):5.2f}/20')
R['C_dof'] = {str(k): v for k, v in C.items()}

# ============================== Stage D ==============================
log('\n== Stage D 接引擎：主动 / 稳定 / 无感官 ==')
sys.path.insert(0, os.path.join(OUT, '..', '..'))
from core.life5 import Life5

STEPS_D, PERIOD = 600, 80
KSA, KACT, DECAY = 0.35, 0.05, 0.05
E0, BASAL = 0.95, 0.001
N = 48


def mk(seed):
    return Life5(seed=seed, sigma_in=0.10, k_seek=0.0, k_seek_arr=KSA,
                 arr_thr=0.50, E0=E0, basal=BASAL)


def run_eng(seed, mode):
    """mode: none(无感官) / stabilized(有感官但不动→适应) / active(眼动→slip)"""
    life = mk(seed)
    rng = np.random.default_rng(7000 + seed)
    a = 0.0; prev = 0.5; act = 0.0
    for t in range(STEPS_D):
        w = float(0.5 + 0.3 * np.sin(2 * np.pi * t / PERIOD))
        if mode == 'none':
            val = 0.5
        else:
            if mode == 'active':                     # 眼睛在动 → 采样点每拍变
                val = float(np.clip(w + rng.normal(0, 0.06), 0, 1))
            else:                                    # 稳定注视 → 输入恒定
                val = w
            slip = abs(val - prev) / 1.0
            s = float(np.clip(slip * 6.0, 0, 1))
            a = float(np.clip(a + (1 - a) * 0.06 * (1 - s) - a * 0.55 * s, 0, 1))
            val = 0.5 + (val - 0.5) * (1 - a)        # 适应使感知回到基线
            prev = val
        life.input_val = val + act
        r = life.step()
        if r is None:
            break
        ten = float(life.sp[0] - life.y[0])
        act = float(np.clip(act + float(np.clip(KACT * ten, 0, 0.10)) - DECAY * act, -0.5, 0.5))
    c = life.capacity
    return dict(seed=seed, alive=bool(life.alive),
                skew=float(np.std(c) / max(np.mean(c), 1e-12)),
                adapt=float(a), surv_rate=None)


def paired(a_, b_, nb=6000):
    a_ = np.asarray(a_); b_ = np.asarray(b_); d = a_ - b_; n = len(d)
    if n < 2:
        return dict(diff=float('nan'), ci=[0, 0], sig=False, n=n)
    rng = np.random.default_rng(0)
    bs = np.array([np.mean(rng.choice(d, n, True)) for _ in range(nb)])
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return dict(diff=float(d.mean()), ci=[lo, hi], sig=bool((lo > 0) == (hi > 0)), n=int(n))


D = {m: [run_eng(s, m) for s in range(N)] for m in ['none', 'stabilized', 'active']}
for m in D:
    sk = [x['skew'] for x in D[m]]
    sv = sum(x['alive'] for x in D[m]) / len(D[m])
    log(f'  {m:11s} 偏度 {np.mean(sk):.6f}  存活 {sv:.3f}  终适应 {np.mean([x["adapt"] for x in D[m]]):.3f}')
com = lambda m: [x['skew'] for x in D[m] if x['alive']]
for m in D:
    log(f'    存活率 {m}: {sum(x["alive"] for x in D[m])}/{len(D[m])}')
R['D_engine'] = D
R['D_paired'] = {
    'active_vs_none': paired([x['skew'] for x in D['active']], [x['skew'] for x in D['none']]),
    'stab_vs_none': paired([x['skew'] for x in D['stabilized']], [x['skew'] for x in D['none']]),
    'active_vs_stab': paired([x['skew'] for x in D['active']], [x['skew'] for x in D['stabilized']]),
}
for k, v in R['D_paired'].items():
    log(f'    {k:16s} diff={v["diff"]:+.6f} CI=[{v["ci"][0]:+.6f},{v["ci"][1]:+.6f}] sig={v["sig"]}')

R['_elapsed'] = round(time.time() - T0, 1)
with open(os.path.join(OUT, 'result096.json'), 'w') as f:
    json.dump(R, f, ensure_ascii=False, indent=1)
log('\nelapsed', R['_elapsed'], 's')

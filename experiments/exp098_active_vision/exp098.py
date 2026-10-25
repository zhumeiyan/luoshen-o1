# -*- coding: utf-8 -*-
"""098 主动视觉：视野小于世界时，怎么动看得最多

用户命题：
  "人类看见了东西，眼球在动 —— 什么能动？带摄像头的什么能动？"
  "能让自己变成一个永远都在动的东西吗？"
  097 结论：相对运动才产生视觉。本轮追问：那该怎么动？

自然科学依据（文献，非本实验自造）：
  * 中央凹 fovea：高分辨率区仅占视野约 2°，外围分辨率急剧下降
    → 视觉系统必须"用外围选点、用中央凹辨认"，这是主动视觉的根源。
  * 扫视 saccade：3-4 次/秒，两次扫视之间是注视 fixation。
  * 抑制返回 IOR（Posner & Cohen 1984）：已被注意过的位置，注意返回变慢
    → 防止扫描器反复回到同一处，是主动视觉的效率机制。
  * 显著性 saliency（Itti & Koch 1998）：外围低分辨率特征引导扫视落点。

核心设计（2x2 交互）：
  世界结构（均匀 / 聚簇） x 策略（无外围信息的盲扫 / 有外围引导 / 外围+IOR）
  预注册：
    H1 聚簇时：外围引导 > 盲扫（有结构可利用）
    H2 均匀时：外围引导无优势甚至有害（无结构可利用，IOR 反而抑制未看区域）
    H3 IOR 的收益依赖世界结构（交互，不是主效应）
    H4 静止最差（视野 << 世界）

真实性：
  * 每个注视点都走真实图像通路：crop -> PNG 编码落盘 -> 读回解码 -> 再判定
    （不是内存数组直接切片，中间有真实编码往返）
  * 抽样用 tesseract 真 OCR 验证"可见即可读"，报告一致率
  * 外围缩略图单独做 OCR 阴性对照：应几乎读不出（证明它只配当引导，不配当辨认）
"""
import os, sys, json, time, random, subprocess, tempfile
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# ---------------- 世界参数 ----------------
WORLD = 2048          # 世界边长
FOV = 256             # 中央凹视野边长（1/8 线宽 -> 面积 1/64）
N_TARGET = 40         # 目标数
GLYPH = 44            # 数字字号（在 256 视野内清晰可辨）
K_STEPS = 40          # 注视预算
PERIPH = 64           # 外围缩略图边长

FONT = ImageFont.truetype(FONT_PATH, GLYPH)


# ---------------------------------------------------------------- 世界构建
def make_world(dist, seed):
    """返回 (world_uint8, targets)
    targets: list of dict(x, y, text, x0,y0,x1,y1)  左上角为 (x0,y0)"""
    rng = random.Random(seed * 7919 + 13)
    world = np.full((WORLD, WORLD), 255, np.uint8)
    img = Image.fromarray(world)
    dr = ImageDraw.Draw(img)

    if dist == 'uniform':
        pts = [(rng.uniform(0.08, 0.92), rng.uniform(0.08, 0.92))
               for _ in range(N_TARGET)]
    else:  # clustered: 5 簇
        centers = [(rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85))
                   for _ in range(5)]
        pts = []
        per = N_TARGET // 5
        for c in centers:
            for _ in range(per):
                pts.append((min(0.95, max(0.05, c[0] + rng.gauss(0, 0.035))),
                            min(0.95, max(0.05, c[1] + rng.gauss(0, 0.035)))))

    targets = []
    used = set()
    for (fx, fy) in pts:
        txt = None
        for _ in range(50):
            t = '%02d' % rng.randrange(10, 99)
            if t not in used:
                used.add(t)
                txt = t
                break
        if txt is None:
            continue
        cx, cy = int(fx * WORLD), int(fy * WORLD)
        bbox = dr.textbbox((cx, cy), txt, font=FONT, anchor='mm')
        dr.text((cx, cy), txt, font=FONT, fill=0, anchor='mm')
        targets.append(dict(x=cx, y=cy, text=txt,
                            x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]))
    return np.array(img), targets


# ---------------------------------------------------------------- 真实采集
_CAPDIR = os.path.join(OUT, '_cap')
os.makedirs(_CAPDIR, exist_ok=True)


def capture(world, cx, cy, tag=''):
    """真实通路：crop -> PNG 落盘 -> 读回解码。返回 (img, png_path)"""
    h = FOV // 2
    x0 = int(np.clip(cx - h, 0, WORLD - FOV))
    y0 = int(np.clip(cy - h, 0, WORLD - FOV))
    patch = world[y0:y0 + FOV, x0:x0 + FOV]
    p = os.path.join(_CAPDIR, 'fov%s_%04d_%04d.png' % (tag, x0, y0))
    if not os.path.exists(p):
        Image.fromarray(patch).save(p)
    back = np.array(Image.open(p).convert('L'))
    return back, p, (x0, y0)


def peripheral(world):
    """外围：整个世界缩到 64x64 并模糊 -> 有密度信息、无字形信息"""
    small = cv2.resize(world, (PERIPH, PERIPH), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (5, 5), 0)
    return small


def visible_in(targets, box):
    """完整落在视野内 = 该步可辨认"""
    x0, y0 = box
    x1, y1 = x0 + FOV, y0 + FOV
    out = []
    for t in targets:
        if t['x0'] >= x0 and t['y0'] >= y0 and t['x1'] <= x1 and t['y1'] <= y1:
            out.append(t)
    return out


# ---------------------------------------------------------------- 策略
def saliency_map(periph):
    """外围缩略图 -> 每个候选注视中心的'墨迹量'（只需算一次）"""
    P = periph.shape[0]
    win = max(1, FOV * P // WORLD)
    ink = (255 - periph.astype(np.float32)) / 255.0
    pad = np.pad(ink, ((0, win), (0, win)), mode='constant')
    integ = pad.cumsum(0).cumsum(1)
    integ = np.pad(integ, ((1, 0), (1, 0)), mode='constant')
    H = P - win + 1
    S = np.zeros((H, H), np.float32)
    for r in range(H):
        for c in range(H):
            S[r, c] = (integ[r + win, c + win] - integ[r, c + win]
                       - integ[r + win, c] + integ[r, c])
    return S, H, P, win


def strategy_next(mode, state, S, H, rng):
    """返回下一个注视中心 (cx, cy)"""
    h = FOV // 2
    lo, hi = h, WORLD - h
    win = state.get('win', FOV * PERIPH // WORLD)
    P = state.get('P', PERIPH)
    if mode == 'static':
        state['visited'].append((H // 2, H // 2))
        return state['start']
    if mode == 'raster':
        # 无视外围，按 8x8 网格顺序铺
        g = 8
        i = state['step'] % (g * g)
        gx, gy = i % g, i // g
        state['visited'].append((gx, gy))
        return (int(lo + (hi - lo) * gx / (g - 1)),
                int(lo + (hi - lo) * gy / (g - 1)))
    if mode == 'random':
        cx, cy = rng.randint(lo, hi), rng.randint(lo, hi)
        state['visited'].append((int(cx * P / WORLD), int(cy * P / WORLD)))
        return (cx, cy)
    if mode in ('salient', 'salient_ior', 'human'):
        w = S.copy()
        if mode in ('salient_ior', 'human'):
            # IOR：已注视过的格子权重衰减（乘性抑制）
            for (gx, gy) in state['visited']:
                if 0 <= gy < H and 0 <= gx < H:
                    w[gy, gx] *= state['ior_decay']
        if mode == 'human':
            # 扫视落点噪声 + 偶尔回看（模拟人类不完美）
            w = w * (1.0 + rng.gauss(0, 0.15))
        idx = int(np.argmax(w))
        gy, gx = divmod(idx, H)
        state['visited'].append((gx, gy))   # 记录被选中的显著图格子
        # 缩略图格子 -> 世界坐标（+win/2 取窗口中心）
        cx = int((gx + win / 2) * WORLD / P)
        cy = int((gy + win / 2) * WORLD / P)
        if mode == 'human':
            cx += int(rng.gauss(0, 24))
            cy += int(rng.gauss(0, 24))
        return (int(np.clip(cx, lo, hi)), int(np.clip(cy, lo, hi)))
    raise ValueError(mode)


# ---------------------------------------------------------------- 一轮扫描
def run_scan(world, targets, mode, seed, ior_decay=0.15, do_ocr=0):
    rng = random.Random(seed * 104729 + 7)
    periph = peripheral(world)
    S, H, P, win = saliency_map(periph)
    h = FOV // 2
    state = {'step': 0, 'visited': [], 'ior_decay': ior_decay,
             'start': (WORLD // 2, WORLD // 2),
             'P': P, 'win': win}
    seen = {}
    steps_new = []
    ocr_hits, ocr_tot = 0, 0
    for k in range(K_STEPS):
        state['step'] = k
        cx, cy = strategy_next(mode, state, S, H, rng)
        img, pngp, box = capture(world, cx, cy, tag='_s%d' % seed)
        vis = visible_in(targets, box)
        new = 0
        for t in vis:
            if t['text'] not in seen:
                seen[t['text']] = t
                new += 1
        steps_new.append(new)
        if do_ocr and vis:
            # 真 OCR 锚定：可见的目标，实际读出来了吗
            ocr_tot += 1
            txt = ocr_read(pngp)
            if any(t['text'] in txt for t in vis):
                ocr_hits += 1
    dup = K_STEPS - len(set(state['visited']))
    return dict(mode=mode, seed=seed, found=len(seen), total=N_TARGET,
                rate=len(seen) / N_TARGET,
                steps_new=steps_new, revisit=dup / K_STEPS,
                ocr_hit=ocr_hits, ocr_tot=ocr_tot)


_OCR_CACHE = {}


def ocr_read(png_path):
    if png_path in _OCR_CACHE:
        return _OCR_CACHE[png_path]
    try:
        r = subprocess.run(['tesseract', png_path, 'stdout',
                            '--psm', '11', '-c',
                            'tessedit_char_whitelist=0123456789'],
                           capture_output=True, text=True, timeout=20)
        out = r.stdout
    except Exception:
        out = ''
    _OCR_CACHE[png_path] = out
    return out

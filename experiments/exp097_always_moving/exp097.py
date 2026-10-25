# -*- coding: utf-8 -*-
"""097 永远在动 —— 相对运动才是视觉存在的条件

用户命题：
  "能让自己变成一个永远都在动的东西吗？"
  "人类看见了东西，眼球在动 —— 什么能动？带摄像头的什么能动？"

自然科学依据（文献，非本实验自造）：
  * 视网膜稳定像（Riggs 1953 / Ditchburn & Ginsborg 1952）：
    图像完全固定在视网膜上 → 数秒内视觉消失。不动的眼睛是瞎的。
  * 扫视抑制 saccadic suppression：扫视期间视觉被抑制，3-4 次/秒，每次 30-120ms
    → 动得太狠也是瞎的。
  * efference copy / corollary discharge：自己动 vs 被推动，视网膜输入相同，
    但只有自己动时有运动副本 → 能动性是系统可区分的。

本实验四部分：
  A 常驻：真的启动一个永远在动的东西（帧缓冲 + 采集 + 本体觉）
  B 相对运动：眼球动 vs 世界动 vs 两者同动（yoked）vs 全静止 —— 真实通路
  C 节律：运动幅度剂量反应，预测倒 U（不动瞎、动太狠也瞎）
  D 能动：同样的视网膜输入，主动 vs 被动，接引擎看结构是否不同
"""
import os, sys, json, time, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

W, H = 1024, 768
FB = '/dev/fb0'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- 帧缓冲 I/O
def _fb_write(arr_rgba):
    with open(FB, 'wb') as f:
        f.write(arr_rgba.tobytes())


_ORDER = {'bgra': None}


def calibrate():
    """写纯红/纯绿/纯蓝，采集回来，推断帧缓冲通道顺序。"""
    probes = {'R': (255, 0, 0), 'G': (0, 255, 0), 'B': (0, 0, 255)}
    res = {}
    for name, rgb in probes.items():
        a = np.zeros((H, W, 4), np.uint8)
        a[:, :, 0], a[:, :, 1], a[:, :, 2] = rgb
        a[:, :, 3] = 255
        _fb_write(a)
        with open(FB, 'rb') as fh:
            data = fh.read(W * H * 4)
        if len(data) != W * H * 4:
            continue
        img = np.frombuffer(data, np.uint8).reshape(H, W, 4)
        Image.fromarray(img[:, :, :3]).save(os.path.join(OUT, 'cal_%s.png' % name))
        c0, c1, c2 = [float(img[:, :, i].mean()) for i in range(3)]
        res[name] = dict(ch0=c0, ch1=c1, ch2=c2)
    # 写红时：若通道0 高 → 原序 RGBA；若通道2 高 → BGRA
    if 'R' in res:
        if res['R']['ch0'] > 200:
            _ORDER['bgra'] = False     # RGBA
        elif res['R']['ch2'] > 200:
            _ORDER['bgra'] = True      # BGRA
        else:
            _ORDER['bgra'] = None
    return res


def write_gray(gray):
    """灰度 → 帧缓冲（按校准出的通道顺序）"""
    g = np.asarray(gray, np.uint8)
    a = np.zeros((H, W, 4), np.uint8)
    a[:, :, 0] = a[:, :, 1] = a[:, :, 2] = g
    a[:, :, 3] = 255
    if _ORDER['bgra']:
        a = a[:, :, [2, 1, 0, 3]]
    _fb_write(a)


def capture(path):
    """真实读取显示设备当前内容（直接读 /dev/fb0，与 ffmpeg -f fbdev 同源），并存 png。
    实测 ffmpeg fbdev 在本环境 60s 超时，故改用直读；读到的仍是硬件帧缓冲。"""
    with open(FB, 'rb') as f:
        data = f.read(W * H * 4)
    if len(data) != W * H * 4:
        return None
    arr = np.frombuffer(data, np.uint8).reshape(H, W, 4).copy()
    if path:
        Image.fromarray(arr[:, :, :3]).save(path)
    return arr


def to_gray(img):
    if img is None:
        return None
    if img.ndim == 3:
        return cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2GRAY)
    return img


def info_lap(g):
    return float(cv2.Laplacian(g.astype(np.float32), cv2.CV_32F).var())


def rms_diff(a, b):
    return float(np.sqrt(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)))


# ---------------------------------------------------------------- 世界
def make_world(seed=7, S=2048, n_digits=60):
    rng = np.random.default_rng(seed)
    small = rng.random((S // 16, S // 16)).astype(np.float32)
    tex = cv2.resize(small, (S, S), interpolation=cv2.INTER_CUBIC)
    # 低噪声背景（235~255）：保证 OCR 可读，同时任何视窗仍有结构可测帧间差
    img = Image.fromarray((255.0 - tex * 20.0).astype(np.uint8)).convert('L')
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(FONT, 60)
    except Exception:
        f = ImageFont.load_default()
    truth = []
    placed = []
    tries = 0
    while len(truth) < n_digits and tries < 8000:
        tries += 1
        x = int(rng.integers(40, S - 200))
        y = int(rng.integers(30, S - 110))
        if any(abs(x - px) < 220 and abs(y - py) < 130 for px, py in placed):
            continue
        placed.append((x, y))
        v = int(rng.integers(10, 100))
        truth.append(dict(x=x, y=y, v=v))
        d.text((x, y), str(v), fill=0, font=f)
    return np.array(img, np.uint8), truth


def view(world, ex, ey, wx, wy):
    """视网膜影像：眼球位置 + 世界偏移，环形世界（无限平移）"""
    S = world.shape[0]
    x = int(round(ex + wx)) % S
    y = int(round(ey + wy)) % S
    return np.roll(np.roll(world, -y, axis=0), -x, axis=1)[:H, :W]


# ---------------------------------------------------------------- 眼动轨迹
def traj(mode, steps, d, rng):
    """返回 (eye_path, world_path)，单位像素。"""
    eye = [(0.0, 0.0)]
    wor = [(0.0, 0.0)]
    for t in range(steps - 1):
        ang = rng.uniform(0, 2 * np.pi)
        dx, dy = d * np.cos(ang), d * np.sin(ang)
        if mode == 'active':
            eye.append((eye[-1][0] + dx, eye[-1][1] + dy))
            wor.append(wor[-1])
        elif mode == 'passive':
            eye.append(eye[-1])
            wor.append((wor[-1][0] + dx, wor[-1][1] + dy))
        elif mode == 'yoked':
            # 眼球动，世界跟着同向动 → 相对位移 0（稳定像实验）
            eye.append((eye[-1][0] + dx, eye[-1][1] + dy))
            wor.append((wor[-1][0] - dx, wor[-1][1] - dy))
        else:  # static
            eye.append(eye[-1])
            wor.append(wor[-1])
    return eye, wor


# ---------------------------------------------------------------- 视网膜适应 + 扫视抑制
def adapt_sequence(slips, decay=0.25, recover=0.6, s_sat=8.0, s_half=60.0):
    """slips: 每拍视网膜位移(px)。返回每拍可见度 V。"""
    a, vs = 1.0, []
    for s in slips:
        a = a + (1 - a) * recover * min(s, s_sat) / s_sat - a * decay
        a = float(np.clip(a, 0.0, 1.0))
        supp = s / (s + s_half)
        vs.append(a * (1 - supp))
    return np.array(vs), a


def render_visible(frame, a):
    """按可见度渲染：a=1 原图，a=0 全白（看不见）"""
    f = frame.astype(np.float32)
    return (255.0 - (255.0 - f) * a).astype(np.uint8)


def ocr_digits(img):
    p = os.path.join(OUT, '_ocr.png')
    Image.fromarray(img).save(p)
    try:
        out = subprocess.run(
            ['tesseract', p, 'stdout', '--psm', '11', '-l', 'eng',
             '-c', 'tessedit_char_whitelist=0123456789'],
            capture_output=True, text=True, timeout=40).stdout
    except Exception:
        out = ''
    return set(w for w in out.split() if len(w) == 2)


# ---------------------------------------------------------------- B 相对运动
def run_conditions(world, truth, steps=120, d=14.0, seeds=(1, 2)):
    truth_set = set(str(t['v']) for t in truth)
    out = {}
    for mode in ('active', 'passive', 'yoked', 'static'):
        rows = []
        for sd in seeds:
            rng = np.random.default_rng(sd)
            eye, wor = traj(mode, steps, d, rng)
            frames, slips = [], []
            prev = None
            for t in range(steps):
                fr = view(world, eye[t][0], eye[t][1], wor[t][0], wor[t][1])
                if prev is not None:
                    slips.append(rms_diff(fr, prev))
                frames.append(fr)
                prev = fr
            slips = np.array(slips + [0.0])
            vs, a_end = adapt_sequence(slips)
            # 真实通路：末帧按可见度渲染 → 上屏 → 采集 → OCR
            write_gray(render_visible(frames[-1], float(vs[-1])))
            cap_path = os.path.join(OUT, 'cap_%s_%d.png' % (mode, sd))
            cap = capture(cap_path)
            g = to_gray(cap)
            # 归一化基准：同一帧按全对比度上屏采集（"本该看见多少"）
            write_gray(frames[-1])
            capf = capture(os.path.join(OUT, 'capfull_%s_%d.png' % (mode, sd)))
            gf = to_gray(capf)
            info_full = float(info_lap(gf)) if gf is not None else float('nan')
            rows.append(dict(
                seed=sd,
                slip_mean=float(np.mean(slips[:-1])) if steps > 1 else 0.0,
                V_last=float(vs[-1]),
                a_end=float(a_end),
                info_cap=float(info_lap(g)) if g is not None else float('nan'),
                info_full=info_full,
                info_ratio=(float(info_lap(g)) / info_full) if (
                    g is not None and info_full > 1e-9) else 0.0,
                read=int(len(ocr_digits(g) & truth_set)) if g is not None else 0,
                read_full=int(len(ocr_digits(gf) & truth_set)) if gf is not None else 0,
                eye_moved=float(np.sum([np.hypot(eye[t + 1][0] - eye[t][0],
                                                 eye[t + 1][1] - eye[t][1])
                                        for t in range(steps - 1)])) if steps > 1 else 0.0,
            ))
        out[mode] = rows
    return out


# ---------------------------------------------------------------- C 节律倒U
def run_rhythm(world, truth, ds=(0.0, 0.5, 1, 2, 4, 8, 12, 16, 24, 32, 64, 128, 256),
               steps=120, seed=11, real_probe=(0.0, 8.0, 128.0)):
    truth_set = set(str(t['v']) for t in truth)
    res = []
    for d in ds:
        rng = np.random.default_rng(seed)
        eye, wor = traj('active', steps, d, rng)
        slips = []
        prev = None
        last_fr = None
        for t in range(steps):
            fr = view(world, eye[t][0], eye[t][1], wor[t][0], wor[t][1])
            if prev is not None:
                slips.append(rms_diff(fr, prev))
            prev = fr
            last_fr = fr
        slips = np.array(slips + [0.0])
        vs, _ = adapt_sequence(slips)
        rec = dict(d=float(d), V=float(np.mean(vs[-40:])), slip=float(np.mean(slips[:-1])))
        if d in real_probe:
            write_gray(render_visible(last_fr, float(vs[-1])))
            cap = capture(os.path.join(OUT, 'rhythm_%g.png' % d))
            g = to_gray(cap)
            rec['read_real'] = int(len(ocr_digits(g) & truth_set)) if g is not None else 0
            rec['info_real'] = float(info_lap(g)) if g is not None else float('nan')
        res.append(rec)
    return res


# ---------------------------------------------------------------- D 能动性
def struct_skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def run_agency(steps=600, seed=0, n_seeds=16):
    """同样的视网膜边际分布，只差时序可预测性（efference copy 的可测替身）。
    active : 我自己发起的节律 → 周期性、可预测（我有运动副本）
    passive: 同一批 slip 值随机重排 → 边际分布全同，只失时序结构
    """
    res = {}
    rng0 = np.random.default_rng(seed)
    # 确定性节律：每 4 拍一次扫视(大 slip)，其余注视(小 slip)
    base0 = np.array([40.0 if (t % 4 == 0) else 3.0 for t in range(steps)])
    seq_info = {}
    per_seed = {}
    for sd in range(n_seeds):
        rng = np.random.default_rng(sd)
        base = base0 * (1.0 + 0.05 * rng.standard_normal(steps))
        shuffled = base.copy()
        rng.shuffle(shuffled)
        seqs = {'active': base, 'passive': shuffled, 'none': np.zeros(steps)}
        for mode, sl in seqs.items():
            v, _ = adapt_sequence(sl)
            if sd == 0:
                seq_info[mode] = dict(slip_mean=float(np.mean(sl)), slip_sd=float(np.std(sl)),
                                      V_mean=float(np.mean(v)),
                                      autocorr1=float(np.corrcoef(sl[:-1], sl[1:])[0, 1])
                                      if np.std(sl) > 0 else float('nan'))
            lf = Life5(N=8, seed=sd, ratio=0.6,
                       k_seek=0.6, k_sal=0.6, sigma_in=0.15)
            for t in range(steps):
                lf.sal = float(v[t])
                lf.step()
                if getattr(lf, 'dead', False):
                    break
            alive = len(lf.log) >= steps
            per_seed.setdefault(mode, []).append(
                struct_skew(lf) if alive else float('nan'))
            per_seed.setdefault(mode + '_alive', []).append(bool(alive))
    def summ(k):
        a = np.array(per_seed[k], float)
        return dict(mean=float(np.nanmean(a)), n=int(np.sum(per_seed[k + '_alive'])),
                    vals=[round(float(x), 6) for x in a])
    for k in ('none', 'active', 'passive'):
        res[k] = summ(k)
    # 配对差 + 95% CI（t 近似）
    for pair in (('active', 'none'), ('passive', 'active')):
        d = np.array(per_seed[pair[0]], float) - np.array(per_seed[pair[1]], float)
        d = d[~np.isnan(d)]
        m = float(np.mean(d))
        s = float(np.std(d, ddof=1)) if len(d) > 1 else 0.0
        se = s / max(len(d) ** 0.5, 1e-12)
        res['diff_%s_minus_%s' % pair] = dict(
            mean=m, ci=[m - 2.36 * se, m + 2.36 * se] if len(d) > 1 else None,
            n=len(d))
    res['_seq'] = seq_info
    return res


# ---------------------------------------------------------------- A 常驻
def run_daemon(steps=180, seed=3, d=14.0, probe_every=30):
    """永远在动：眼睛不停扫视，写帧缓冲，周期性用真实采集确认自己还看得见。"""
    world, truth = make_world(seed=7)
    truth_set = set(str(t['v']) for t in truth)
    rng = np.random.default_rng(seed)
    log = dict(started=time.time(), pid=os.getpid(), steps=steps, probes=[])
    eye, wor = traj('active', steps, d, rng)
    prev = None
    slips_r = []
    for t in range(steps):
        fr = view(world, eye[t][0], eye[t][1], wor[t][0], wor[t][1])
        if prev is not None:
            slips_r.append(rms_diff(fr, prev))
        prev = fr
        write_gray(fr)
        if t % probe_every == 0 and t > 0:
            cap = capture(os.path.join(OUT, 'daemon_%03d.png' % t))
            g = to_gray(cap)
            log['probes'].append(dict(
                t=t,
                eye=[round(eye[t][0], 1), round(eye[t][1], 1)],
                info=float(info_lap(g)) if g is not None else float('nan'),
                read=int(len(ocr_digits(g) & truth_set)) if g is not None else 0,
            ))
    log['elapsed'] = time.time() - log['started']
    log['slip_mean'] = float(np.mean(slips_r)) if slips_r else 0.0
    # 本体觉
    try:
        log['loadavg'] = open('/proc/loadavg').read().split()[:3]
    except Exception:
        log['loadavg'] = None
    with open(os.path.join(OUT, 'daemon_log.json'), 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return log


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if mode == 'daemon':
        lg = run_daemon()
        print(json.dumps({k: v for k, v in lg.items() if k != 'probes'}, ensure_ascii=False))
        print('probes:', json.dumps(lg['probes'], ensure_ascii=False))
        sys.exit(0)

    t0 = time.time()
    cal = calibrate()
    world, truth = make_world(seed=7)
    cond = run_conditions(world, truth)
    rhythm = run_rhythm(world, truth)
    agency = run_agency()
    res = dict(calib=cal, cond=cond, rhythm=rhythm, agency=agency,
               elapsed=time.time() - t0)
    with open(os.path.join(OUT, 'result097.json'), 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
095 玩游戏：不计算，就是拖
--------------------------------------------------
用户的命题：
  1. 人类不计算内部机制，就是从 A 点拖到 B 点
  2. 计算机最初就是为渲染 / 打游戏造的

设计原则（与 094 的关键差别）：
  094 里"看"返回的是符号反馈（更近/更远），是我造的接口。
  095 里"看"返回的是**渲染出来的像素**——眼睛只对画面做视觉识别，
  永远不访问游戏的内部状态（真实 pos / target）。
  手是真实 uinput 鼠标（/dev/uinput → /dev/input/event1）。

游戏：一维轨道 [0, 1000]，滑块从 0 出发，目标随机。
渲染：800x120 像素画面，滑块=白色块，目标=红色块，背景黑。
"""
import os, sys, json, time, struct, fcntl, random, threading
import numpy as np
from PIL import Image

random.seed(95001)
np.random.seed(95001)

OUT = os.path.dirname(os.path.abspath(__file__))
W_FB, H_FB = 800, 120
TRACK = 1000.0
TOL = 10.0          # 命中容差（轨道的 1%）
SLIDER_W = 60       # 滑块宽（像素）
TARGET_W = 16       # 目标宽（像素）

# ---------------------------------------------------------------- 手：真实鼠标
class Hand:
    """真实 uinput 鼠标。move() 真的往内核写 REL_X 事件。"""
    UI_SET_EVBIT = 0x40045564
    UI_SET_KEYBIT = 0x40045565
    UI_SET_RELBIT = 0x40045566
    UI_DEV_CREATE = 0x5501
    EV_KEY, EV_REL, EV_SYN = 1, 2, 0
    REL_X, REL_Y = 0, 1
    BTN_LEFT = 0x110

    def __init__(self):
        try:
            self.fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
        except Exception as e:
            self.fd = None
            self.ok = False
            self.err = str(e)
            return
        try:
            for b in (self.EV_KEY, self.EV_REL):
                fcntl.ioctl(self.fd, self.UI_SET_EVBIT, b)
            for c in (self.REL_X, self.REL_Y):
                fcntl.ioctl(self.fd, self.UI_SET_RELBIT, c)
            fcntl.ioctl(self.fd, self.UI_SET_KEYBIT, self.BTN_LEFT)
            name = b'exp095-hand'
            dev = struct.pack('80sHHHHI', name.ljust(80, b'\x00'),
                              0x03, 0x1234, 0x5678, 1, 0) + b'\x00' * (64 * 4 * 4)
            os.write(self.fd, dev)
            fcntl.ioctl(self.fd, self.UI_DEV_CREATE)
            self.ok = True
        except Exception as e:
            self.ok = False
            self.err = str(e)

    def ev(self, typ, code, val):
        t = int(time.time())
        s = t * 1000 % 1000000000
        os.write(self.fd, struct.pack('llHHi', t, s, typ, code, int(val)))

    def move(self, dx):
        if not self.ok:
            return
        self.ev(self.EV_REL, self.REL_X, int(round(dx)))
        self.ev(self.EV_SYN, 0, 0)

    def down(self):
        if not self.ok:
            return
        self.ev(self.EV_KEY, self.BTN_LEFT, 1)
        self.ev(self.EV_SYN, 0, 0)

    def up(self):
        if not self.ok:
            return
        self.ev(self.EV_KEY, self.BTN_LEFT, 0)
        self.ev(self.EV_SYN, 0, 0)


# ---------------------------------------------------------------- 显存：渲染
class Screen:
    """等价于 GPU 帧缓冲：只有像素，没有内部状态。"""

    def __init__(self):
        self.buf = np.zeros((H_FB, W_FB, 3), dtype=np.uint8)
        self.history = []

    def __init__(self, keep_history=False):
        self.buf = np.zeros((H_FB, W_FB, 3), dtype=np.uint8)
        self.keep_history = keep_history
        self.history = []
        self._img = np.zeros((H_FB, W_FB, 3), dtype=np.uint8)

    def render(self, pos, target, noise=0.0):
        img = self._img
        img[:] = 0
        # 轨道底纹（弱）
        img[50:70, :] = 30
        # 目标：红块
        tx = int(target / TRACK * (W_FB - TARGET_W))
        img[40:80, tx:tx + TARGET_W, 0] = 255
        # 滑块：白块
        sx = int(pos / TRACK * (W_FB - SLIDER_W))
        img[45:75, sx:sx + SLIDER_W, :] = 255
        if noise > 0:
            img = np.clip(img.astype(np.int16) +
                          np.random.normal(0, noise, img.shape), 0, 255).astype(np.uint8)
        self.buf = img
        if self.keep_history:
            self.history.append(img.copy())
            if len(self.history) > 64:
                self.history.pop(0)
        return img

    def frame(self, lag=0):
        """取 lag 帧之前的画面——这就是游戏延迟 / 卡顿。"""
        if lag <= 0:
            return self.buf
        if len(self.history) > lag:
            return self.history[-1 - lag]
        return self.history[0]


# ---------------------------------------------------------------- 眼：只看像素
class Eye:
    """从画面做视觉识别。绝不访问真实 pos / target。"""

    def __init__(self, screen, cols=W_FB, noise=0.0, lag=0):
        self.s = screen
        self.cols = cols
        self.noise = noise
        self.lag = lag

    def look(self):
        img = self.s.frame(self.lag).astype(np.float32)
        # ---- 分辨率限制：把 800 列池化到 cols 列（人类近视 / 画质低）
        if self.cols < W_FB:
            step = W_FB // self.cols
            img = img[:, :step * self.cols].reshape(H_FB, self.cols, step, 3).mean(axis=2)
        if self.noise > 0:
            img = img + np.random.normal(0, self.noise, img.shape)
        # 滑块 = 白色：三通道都亮；目标 = 红色：R 亮而 G/B 暗
        white = img.mean(axis=2)
        red = img[:, :, 0] - np.maximum(img[:, :, 1], img[:, :, 2])
        w_prof = white.mean(axis=0)
        r_prof = np.clip(red, 0, None).mean(axis=0)
        # 阈值取半高，抗噪
        def centroid(prof):
            thr = prof.max() * 0.5
            idx = np.where(prof > thr)[0]
            if len(idx) == 0:
                return None
            return float((idx * prof[idx]).sum() / prof[idx].sum())
        cw = centroid(w_prof)
        cr = centroid(r_prof)
        if cw is None or cr is None:
            return None
        # 映射回轨道坐标
        # 标定：质心是色块中心，要减去色块自身宽度的一半才是位置
        scale = self.cols / W_FB
        cw_fb = cw / scale
        cr_fb = cr / scale
        return ((cw_fb - SLIDER_W / 2.0) / (W_FB - SLIDER_W) * TRACK,
                (cr_fb - TARGET_W / 2.0) / (W_FB - TARGET_W) * TRACK)


# ---------------------------------------------------------------- 玩
def play(mode='closed', target=None, max_steps=150, eye=None, hand=None,
         screen=None, step0=120.0, decel=True, predictive=False):
    """
    mode:
      closed  人类式闭环：边拖边看，变远就反向，接近就减速。只用"看到的"决定何时松手。
      blind   盲拖：不看，固定步长一路走。
      open    开环：无反馈固定推进。
      oracle  对照：直接知道 target（现实中不存在，用来标定上限）
    predictive: 是否用本体觉补偿延迟——记住自己刚才动了多远，把看到的画面往前推。
                人类就是这么做的：他不计算验证码内部，但他知道自己手往哪动了。
    """
    pos = 0.0
    if target is None:
        target = random.uniform(200, 900)
    direction = 1.0
    step = step0
    prev_gap = None
    acts = []                      # 本体觉：我自己实际走过的位移
    screen.render(pos, target)

    if mode == 'oracle':
        if hand: hand.down()
        dx = target - pos
        if hand: hand.move(dx)
        pos += dx
        if hand: hand.up()
        return dict(hit=abs(pos - target) <= TOL, steps=1, pos=pos,
                    target=target, final_gap=abs(pos - target))

    lag = getattr(eye, 'lag', 0)

    def perceive():
        """看到的画面 → (滑块位置, 目标位置)；可选地用本体觉补偿延迟。"""
        seen = eye.look()
        if seen is None:
            return None
        p_seen, t_seen = seen
        if predictive and lag > 0:
            p_seen = p_seen + float(np.sum(acts[-lag:]))
        return p_seen, t_seen

    if hand: hand.down()
    steps = 0
    for i in range(max_steps):
        steps = i + 1
        if mode == 'closed':
            seen = perceive()
            if seen is None:
                mv = direction * step          # 画面糊了：凭惯性
            else:
                p_seen, t_seen = seen
                gap = t_seen - p_seen
                if prev_gap is not None:
                    if abs(gap) < abs(prev_gap) - 0.5:
                        pass                   # 更近，保持方向
                    else:
                        direction *= -1.0
                        if decel:
                            step = max(step * 0.6, 2.0)
                prev_gap = gap
                if decel:
                    step = max(min(step, max(abs(gap) * 0.7, 3.0)), 2.0)
                mv = direction * step
        elif mode == 'blind':
            mv = step0 * 0.8
        elif mode == 'open':
            mv = (TRACK * 0.5) / max_steps * 4
        else:
            raise ValueError(mode)

        new_pos = float(np.clip(pos + mv, 0, TRACK))
        acts.append(new_pos - pos)             # 记录真实位移（含边界截断）
        pos = new_pos
        if hand: hand.move(mv)
        screen.render(pos, target)

        # 松手判据只来自"看到的画面"——绝不用真实位置
        if mode == 'closed':
            seen = perceive()
            if seen is not None and abs(seen[1] - seen[0]) <= TOL * 1.2:
                break
    if hand: hand.up()
    return dict(hit=bool(abs(pos - target) <= TOL), steps=steps, pos=pos,
                target=target, final_gap=abs(pos - target))


def run(n=20, **kw):
    hits, steps, gaps = [], [], []
    for _ in range(n):
        r = play(**kw)
        hits.append(1 if r['hit'] else 0)
        steps.append(r['steps'])
        gaps.append(r['final_gap'])
    return dict(rate=float(np.mean(hits)), steps=float(np.mean(steps)),
                gap=float(np.mean(gaps)), n=n)

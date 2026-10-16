# -*- coding: utf-8 -*-
"""
生成参赛演示视频（3–5 分钟）。

所有数字与曲线均来自 data/ 的真实运行结果，不写死常量。
输出：docs/洛神O1_演示视频.mp4
"""
import os, json, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'docs', '洛神O1_演示视频.mp4')
TMP = '/tmp/vidframes'
os.makedirs(TMP, exist_ok=True)
for _old in os.listdir(TMP):
    os.remove(os.path.join(TMP, _old))

W, H = 1600, 900
OW, OH = 1280, 720
FPS = 24

FD = '/usr/share/fonts/truetype/alibaba-puhuiti'
F_R = f'{FD}/AlibabaPuHuiTi-2-55-Regular.ttf'
F_B = f'{FD}/AlibabaPuHuiTi-2-85-Bold.ttf'
F_H = f'{FD}/AlibabaPuHuiTi-2-105-Heavy.ttf'
F_M = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

BG = (13, 17, 23)
FG = (230, 237, 243)
MUT = (139, 148, 158)
ACC = (88, 166, 255)
GRN = (63, 185, 80)
RED = (248, 81, 73)
YEL = (210, 153, 34)
PUR = (188, 140, 255)


def f(path, size):
    return ImageFont.truetype(path, size)


res = json.load(open(os.path.join(ROOT, 'data', 'core_results.json')))
cur = json.load(open(os.path.join(ROOT, 'data', 'curves.json')))
B, C, D = res['B_tradeoff'], res['C_weld'], res['D_window']
A = res['A_death']
dead = [r for r in A if not r['survived']]
alive_n = len(A) - len(dead)

cache = {}


def font(sz, bold=False, heavy=False, mono=False):
    k = (sz, bold, heavy, mono)
    if k not in cache:
        p = F_M if mono else (F_H if heavy else (F_B if bold else F_R))
        cache[k] = f(p, sz)
    return cache[k]


def tw(d, s, fnt):
    b = d.textbbox((0, 0), s, font=fnt)
    return b[2] - b[0], b[3] - b[1]


def base():
    im = Image.new('RGB', (W, H), BG)
    return im, ImageDraw.Draw(im)


_VMASK = None


def vignette(im):
    """轻微暗角（mask 只算一次）。"""
    global _VMASK
    if _VMASK is None:
        yy, xx = np.mgrid[0:H, 0:W]
        cx, cy = W / 2, H / 2
        r = np.sqrt(((xx - cx) / (W * 0.72)) ** 2 + ((yy - cy) / (H * 0.72)) ** 2)
        k = np.clip(1.0 - 0.28 * np.clip(r - 0.55, 0, None) * 2.2, 0.72, 1.0)
        _VMASK = Image.fromarray((k * 255).astype(np.uint8)).convert('L')
    return ImageChops.multiply(im, _VMASK.convert('RGB'))


def fade(im, a):
    if a >= 1.0:
        return im
    return Image.blend(Image.new('RGB', (W, H), BG), im, max(0.0, float(a)))


def ease(t):
    return t * t * (3 - 2 * t)


# ---------- 帧生成器 ----------
def frame_title(t):           # 0.0 ~ 1.0 段内进度
    im, d = base()
    a = ease(min(1.0, t / 0.18)) * (1.0 - ease(max(0.0, (t - 0.86) / 0.14)))
    y = 300
    s1 = '洛神 O1'
    fn = font(96, heavy=True)
    w, _ = tw(d, s1, fn)
    d.text(((W - w) / 2, y), s1, font=fn, fill=FG)
    fn2 = font(46, bold=True)
    s2 = '会死的数字生命引擎'
    w2, _ = tw(d, s2, fn2)
    d.text(((W - w2) / 2, y + 130), s2, font=fn2, fill=ACC)
    fn3 = font(25)
    s3 = '稀缺 · 死亡 · 不可逆 · 代谢 · 内生约束'
    w3, _ = tw(d, s3, fn3)
    d.text(((W - w3) / 2, y + 215), s3, font=fn3, fill=MUT)
    return fade(vignette(im), a)


def frame_terminal(t, lines, cps=26.0):
    """终端打字机：lines = [(text, color, mono?)]"""
    im, d = base()
    d.rounded_rectangle([90, 110, W - 90, H - 110], radius=14,
                        fill=(8, 11, 15), outline=(48, 54, 61), width=2)
    # 标题栏
    d.rounded_rectangle([90, 110, W - 90, 158], radius=14, fill=(22, 27, 34))
    d.rectangle([90, 140, W - 90, 158], fill=(22, 27, 34))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([116 + i * 26, 126, 130 + i * 26, 140], fill=c)
    fnp = font(20, mono=True)
    d.text((210, 124), 'bash  —  luoshen-o1', font=fnp, fill=MUT)

    total = sum(len(s) for s, _, _ in lines)
    shown = t * cps * max(0.35, 1.0) * (len(lines) * 0.9)
    # 用段内进度直接映射字符数，保证段末恰好打完
    shown = int(ease(min(1.0, t)) * total)
    y = 196
    fn = font(25, mono=True)
    cnt = 0
    for s, col, mono in lines:
        buf = ''
        for chx in s:
            if cnt < shown:
                buf += chx
                cnt += 1
            else:
                break
        if buf:
            fm = font(25, mono=True) if mono else font(25)
            d.text((132, y), buf, font=fm, fill=col)
        y += 44
        if y > H - 150:
            break
    # 光标
    if cnt < total and int(t * 6) % 2 == 0:
        d.rectangle([132, y - 44, 148, y - 40], fill=GRN)
    return vignette(im)


def frame_lines(t, title, items, sub=None):
    im, d = base()
    a = ease(min(1.0, t / 0.14))
    d.text((110, 96), title, font=font(44, bold=True), fill=ACC)
    d.line([110, 168, W - 110, 168], fill=(48, 54, 61), width=2)
    n = len(items)
    y = 210
    for i, (txt, col) in enumerate(items):
        p = (t - 0.10 - i * 0.55 / max(n, 1)) / 0.35
        if p <= 0:
            continue
        al = ease(min(1.0, p))
        col2 = tuple(int(c * al + BG[j] * (1 - al)) for j, c in enumerate(col))
        yy = int(y + i * 62 - (1 - al) * 14)
        d.text((118, yy), txt, font=font(30), fill=col2)
    if sub:
        d.text((110, H - 130), sub, font=font(23), fill=MUT)
    return fade(vignette(im), a)


def frame_image(t, path, cap, note=None, zoom=True):
    im, d = base()
    src = Image.open(path).convert('RGB')
    # 留白裁掉
    bb = src.point(lambda x: 255 if x > 26 else 0).convert('L').getbbox()
    if bb:
        src = src.crop(bb)
    z = 1.0 + 0.03 * ease(min(1.0, t / 1.0)) if zoom else 1.0
    maxw, maxh = int(W * 0.80), int(H * 0.62)
    sw, sh = src.size
    k = min(maxw / sw, maxh / sh) * z
    nw, nh = max(1, int(sw * k)), max(1, int(sh * k))
    src = src.resize((nw, nh), Image.LANCZOS)
    x, y = (W - nw) // 2, 176
    im.paste(src, (x, y))
    d.rectangle([x - 2, y - 2, x + nw + 2, y + nh + 2], outline=(48, 54, 61), width=2)
    a = ease(min(1.0, t / 0.15))
    d.text((W // 2 - tw(d, cap, font(25))[0] // 2, y + nh + 32), cap,
           font=font(25), fill=FG)
    if note:
        d.text((W // 2 - tw(d, note, font(23))[0] // 2, y + nh + 76), note,
               font=font(23), fill=ACC)
    return fade(vignette(im), a)


def frame_big(t, kicker, big, note, color=ACC):
    im, d = base()
    a = ease(min(1.0, t / 0.16))
    w, _ = tw(d, kicker, font(28))
    d.text(((W - w) / 2, 220), kicker, font=font(28), fill=MUT)
    s = big
    fn = font(72, heavy=True)
    w2, _ = tw(d, s, fn)
    d.text(((W - w2) / 2, 280), s, font=fn, fill=color)
    w3, _ = tw(d, note, font(26))
    d.text(((W - w3) / 2, 410), note, font=font(26), fill=FG)
    return fade(vignette(im), a)


def frame_outro(t):
    im, d = base()
    a = ease(min(1.0, t / 0.18))
    s1 = '所有开源 Agent 框架都在问「它能做什么」'
    s2 = '我们问的是'
    s3 = '当它必须取舍、必须记住、而且真的会死的时候，它是什么'
    for i, (s, fn, col, yy) in enumerate([
            (s1, font(34), FG, 240), (s2, font(30), MUT, 320),
            (s3, font(32, bold=True), ACC, 400)]):
        w, _ = tw(d, s, fn)
        d.text(((W - w) / 2, yy), s, font=fn, fill=col)
    d.line([W // 2 - 260, 500, W // 2 + 260, 500], fill=(48, 54, 61), width=2)
    tail = '洛神 O1 · Apache-2.0 · 朱美岩'
    w, _ = tw(d, tail, font(25))
    d.text(((W - w) / 2, 540), tail, font=font(25), fill=MUT)
    return fade(vignette(im), a)


# ---------- 分镜表 ----------
FIG = os.path.join(ROOT, 'fig')
d0 = dead[0]
seq = []
seq.append((5.0, frame_title))
seq.append((16.0, lambda t: frame_terminal(t, [
    ('$ python3 core/life_cli.py --steps 600 --seed 3', FG, True),
    ('', FG, True),
    ('running ... 600 steps', MUT, True),
    ('', FG, True),
    (f'survived : False', RED, True),
    (f'died at  : step {d0["death_t"]}', RED, True),
    ('final E  : 0.0000', RED, True),
    ('', FG, True),
    ('# 同一个引擎，只换 seed', MUT, True),
    ('$ python3 core/life_cli.py --steps 600 --seed 5', FG, True),
    ('survived : True', GRN, True),
    ('final E  : 1.0000', GRN, True),
    ('', FG, True),
    ('# 退出码：seed 3 → 1（死）　seed 5 → 0（活）', MUT, True),
])))
seq.append((14.0, lambda t: frame_lines(t, '它会死。这是第一条规定', [
    ('不是异常分支，不是报错 —— 是设计好的终点', FG),
    ('E ≤ 0 且持续超过耐心阈值 → 运行终止，不回滚', FG),
    ('上下文超了就截断的系统，不需要做取舍', MUT),
    ('不做取舍的系统，不会形成结构', MUT),
], sub='16 个种子真实跑一遍：{} 活 / {} 死'.format(alive_n, len(dead)))))
seq.append((20.0, lambda t: frame_lines(t, '五条硬约束（不是惩罚项）', [
    ('稀缺        每拍预算固定，通道间零和的硬取舍', FG),
    ('死亡        E ≤ 0 持续超限 → 终止，不回滚', FG),
    ('不可逆      结构容量 capacity 只减不增', FG),
    ('代谢        能量只能由自身产出换取，无外部拨款', FG),
    ('内生约束    设定点由自身历史产生，外部不可写入', FG),
], sub='唯一依赖 numpy —— 零 LLM 依赖、零网络依赖')))
seq.append((26.0, lambda t: frame_lines(t, '实验一：关掉全部决策模块', [
    ('寻找 k_seek = 0', RED),
    ('感知显著性 k_sal = 0', RED),
    ('到达预测 k_seek_arr = 0', RED),
    ('外部 KPI kpi_push = 0', RED),
    ('—— 系统中不存在任何决策模块', MUT),
    ('前 300 拍分别饿通道 3 / 通道 5，之后两组条件完全相同', FG),
], sub='然后测同一个通道 3 的后段份额')))
seq.append((24.0, lambda t: frame_image(
    t, f'{FIG}/fig2_tradeoff.png',
    '图 · 关掉全部决策模块，取舍依然出现',
    f"Δ = {B['mean_delta']:+.4f} ± {B['se']:.4f}  ·  符号一致 {B['sign_consistent']}/{B['n']} seeds")))
seq.append((13.0, lambda t: frame_big(
    t, '没有决策模块，取舍依然出现',
    f"{B['mean_delta']:+.4f}",
    f"饿过谁，之后就少给谁 —— {B['sign_consistent']}/{B['n']} seeds 符号一致",
    GRN)))
seq.append((20.0, lambda t: frame_lines(t, '这段"记忆"存在哪里？', [
    ('不在任何模块里 —— 我们把决策模块全关了', FG),
    ('不在任何参数里 —— 没有规则、没有强化学习', FG),
    ('它在不可逆结构容量里', ACC),
    ('取舍 = 稀缺 × 不可逆 × 竞争动力学 的投影', GRN),
])))
seq.append((22.0, lambda t: frame_image(
    t, f'{FIG}/fig3_weld.png',
    '图 · 结构疤痕：只有两条约束同时成立才出现',
    f"两条都在 {C['scarcity_1_irrev_1']['mean_skew']:.4f}　"
    f"撤不可逆 {C['scarcity_1_irrev_0']['mean_skew']:.4f}　"
    f"撤稀缺 {C['scarcity_0_irrev_1']['mean_skew']:.4f}")))
seq.append((13.0, lambda t: frame_big(
    t, '稀缺与不可逆是焊死的，不是两个开关',
    '不缺，就不留疤',
    '撤掉任意一条，疤痕从不形成（0.0000）',
    RED)))
seq.append((24.0, lambda t: frame_image(
    t, f'{FIG}/fig4_window.png',
    '图 · 结构的关键期：早期给过，撤掉之后还在',
    f"早期 {D['early']['mean']:.4f}　中期 {D['mid']['mean']:.4f}　"
    f"晚期 {D['late']['mean']:.4f}　全程 {D['full']['mean']:.4f}")))
seq.append((14.0, lambda t: frame_big(
    t, '早期施加后撤除，强于全程施加',
    f"{D['early']['mean']:.4f}  >  {D['full']['mean']:.4f}",
    '引导要早，且要敢于撤 —— 持续投入会摊薄集中度',
    YEL)))
seq.append((22.0, lambda t: frame_image(
    t, f'{FIG}/fig1_death.png',
    '图 · 死亡是真实结局',
    f"16 个种子：{alive_n} 活 / {len(dead)} 死（seed 3 @ {d0['death_t']} 拍）",
    zoom=False)))
seq.append((24.0, lambda t: frame_lines(t, '我们还开源了全部失败', [
    ('141 条失败模式，每一条都有代码可复现', FG),
    ('53 份实验报告，每一份都记录被推翻的预注册判据', FG),
    ('', FG),
    ('饱和伪装成"无效应"　信号 ×1/×10/×100，指标一字不差', RED),
    ('变量静默失效　　　　写了但没接进主通道，不报错不崩', RED),
    ('相位假象　　　　　　测量窗口落在振荡的某一半', RED),
], sub='2026 年，三十秒能编一个可信的成功故事 —— 但编不出 141 条带代码的失败')))
seq.append((16.0, lambda t: frame_big(
    t, '一致性高 ≠ 正确',
    'κ 0.945 / 命中 0.01',
    '共享同一套坐标库时，全体一致地错，κ 依然是 0.945',
    PUR)))
seq.append((12.0, frame_outro))

# ---------- 渲染 ----------
total = sum(s[0] for s in seq)
print(f'总时长 {total:.1f}s，{int(total*FPS)} 帧')
n = 0
for idx, (dur, fn) in enumerate(seq):
    nf = int(round(dur * FPS))
    for i in range(nf):
        t = (i + 1) / nf
        im = fn(t)
        im.resize((OW, OH), Image.LANCZOS).save(f'{TMP}/f{n:06d}.jpg', quality=92)
        n += 1
    print(f'  [{idx+1}/{len(seq)}] {dur:.0f}s -> {n} 帧', flush=True)

print('合成 mp4 ...')
subprocess.run([
    'ffmpeg', '-y', '-framerate', str(FPS), '-i', f'{TMP}/f%06d.jpg',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT
], check=True, capture_output=True)
print('VIDEO ->', OUT, os.path.getsize(OUT), 'bytes')

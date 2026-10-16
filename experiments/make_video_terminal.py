# -*- coding: utf-8 -*-
"""
把 demo_terminal.py 的真实 stdout 渲染成终端录屏视频。

与旧版 make_video.py 的根本区别：
  旧版 —— 用 PIL 画出示意图，曲线由脚本里的常量驱动，画面里没有一次真实运行。
  新版 —— 视频里每一个字符都来自 demo_terminal.py 的真实 stdout（subprocess 现场捕获）。
          渲染层只做一件事：决定这些字符以多快的速度出现在屏幕上。
          所以这不是"演示动画"，是一段被放慢了的真实运行录屏。

可读性改造（本轮）：
  纯黑底终端的第一秒会让人以为在播放报错日志。所以加了两样包装：
    1. 开场标题卡（3.2s）：说清这是什么、为什么值得看下去；
    2. 每屏常驻引导条：告诉评委"你现在在看什么 / 该期待看到什么"。
  包装层不产生任何数据 —— 画面里的数字依然全部来自现场运行。

输出：docs/洛神O1_演示视频.mp4
"""
import os, sys, subprocess, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'docs', '洛神O1_演示视频.mp4')
TMP = os.path.join(ROOT, '.frames')

# 两阶段：--frames-only 只渲染帧，--compose-only 只合成。
# 拆开是因为完整流程可能超过单次执行时限；帧留在仓库内（.gitignore 忽略），
# 中断后可用 --compose-only 从已渲染的帧续上，不必重跑实验。
ONLY = sys.argv[1] if len(sys.argv) > 1 else ''
# 不自动清理：帧与 stdout 缓存需跨多次调用复用。要重来请显式 --clean。
if ONLY == '--clean':
    shutil.rmtree(TMP, ignore_errors=True)
    print('已清空', TMP)
    raise SystemExit(0)
os.makedirs(TMP, exist_ok=True)

W, H, FPS = 1280, 720, 24
F_MONO = '/usr/share/fonts/truetype/jetbrains-mono'
if not os.path.isdir(F_MONO):
    F_MONO = '/usr/share/fonts/truetype/dejavu'
MONO = None
for c in sorted(os.listdir(F_MONO)):
    if c.lower().endswith(('.ttf', '.otf')) and 'mono' in c.lower():
        MONO = os.path.join(F_MONO, c)
        break
if MONO is None:
    MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
CJK = '/usr/share/fonts/truetype/alibaba-puhuiti/AlibabaPuHuiTi-2-55-Regular.ttf'
CJK_B = '/usr/share/fonts/truetype/alibaba-puhuiti/AlibabaPuHuiTi-2-85-Bold.ttf'

BG = (12, 15, 20)
BAR = (26, 31, 39)
CAPBG = (18, 33, 56)
FG = (205, 215, 225)
DIM = (120, 130, 142)
PROMPT = (126, 231, 135)
ACC = (88, 166, 255)
RED = (248, 81, 73)
YEL = (224, 175, 72)

FS = 19
LH = 27
TOP = 92          # 顶部栏 + 引导条之后，终端正文开始的位置
PADX = 34
NROW = (H - TOP - 30) // LH

_fc = {}


def font(sz, bold=False):
    k = (sz, bold)
    if k not in _fc:
        _fc[k] = (ImageFont.truetype(MONO, sz), ImageFont.truetype(CJK_B if bold else CJK, sz))
    return _fc[k]


def is_wide(ch):
    return ord(ch) > 0x2E80


def text_w(s, sz=FS):
    m, c = font(sz)
    return int(sum(m.getlength(ch) if not is_wide(ch) else sz for ch in s))


def draw_line(d, s, x, y, color=FG, sz=FS, bold=False):
    m, c = font(sz, bold)
    cx = x
    for ch in s:
        if ch == ' ':
            cx += m.getlength(' ')
            continue
        f = c if is_wide(ch) else m
        d.text((cx, y), ch, font=f, fill=color)
        cx += (sz if is_wide(ch) else m.getlength(ch))
    return cx


# ---------------- 每屏引导语 ----------------
# 按命令行里的关键词匹配。不依赖顺序，demo_terminal.py 改版也不会错位。
CAPTIONS = [
    ('场景一', '① 同一个引擎，四个个体 —— 结局会不会自然分化？'),
    ('追踪 seed', '② 追一条真实的死亡轨迹 —— 死亡是断崖还是连续下降？'),
    ('场景二', '③ 撤掉稀缺（要多少给多少）—— 结构还在吗？'),
    ('场景三', '④ 扫一整条稀缺度曲线 —— 不是单点，每格都真跑'),
    ('场景四', '⑤ 逐拍尾随，看着它死 —— 并区分「死亡」与「崩溃」'),
    ('场景五', '⑥ 挂到别人的 Agent 上 —— 不改原框架一行代码'),
    ('你自己跑', '⑦ 可复现声明 —— 你跑会得到逐位相同的数字'),
]
NO_CAP = '下面是真实运行的终端录屏，不是动画，也不是截图'


def cap_of(cmd):
    for key, cap in CAPTIONS:
        if key in cmd:
            return cap
    return NO_CAP


def cap_index(cmd):
    for i, (key, _) in enumerate(CAPTIONS):
        if key in cmd:
            return i + 1
    return 0


# ---------------- 现场捕获真实 stdout ----------------
def capture():
    # 缓存真实 stdout：它本身就是可复现的确定性输出，缓存只影响渲染耗时，
    # 不改变视频内容。中断后续跑可直接复用。
    cf = os.path.join(TMP, '_stdout.txt')
    if os.path.exists(cf) and os.path.getsize(cf) > 0:
        print('  [复用缓存的 stdout]', cf)
        return open(cf, encoding='utf-8').read().split('\n')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'demo_terminal.py')],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise SystemExit('demo_terminal.py 失败：\n' + r.stderr)
    open(cf, 'w', encoding='utf-8').write(r.stdout)
    return r.stdout.split('\n')


def parse(lines):
    """切成块：每个 $ 命令行领一块。"""
    blocks, cur = [], None
    for ln in lines:
        st = ln.strip()
        if st.startswith('$'):
            cmd = st[1:].strip()
            cur = {'cmd': cmd, 'out': [], 'cap': cap_of(cmd), 'idx': cap_index(cmd)}
            blocks.append(cur)
        elif cur is not None:
            cur['out'].append(ln.rstrip())
    return blocks


# ---------------- 帧序列 ----------------
# 每项 = (kind, payload, rep, cap)
#   kind='title' / 'end'  payload=None
#   kind='term'           payload=(已完成行list, 正在打字的行str)
def build(blocks):
    frames = [('title', None, int(FPS * 3.2), '')]
    done = []
    for bi, b in enumerate(blocks):
        cap = b['cap']
        cmd = '$ ' + b['cmd']
        for i in range(1, len(cmd) + 1):
            frames.append(('term', (list(done), cmd[:i]), 5, cap))
        frames.append(('term', (list(done), cmd), 16, cap))
        done = done + [cmd]
        for ln in b['out']:
            done = done + [ln]
            rep = 3
            st = ln.strip()
            if '← 判定死亡' in ln:
                rep = int(FPS * 6)                      # 死亡判定：钉住 6 秒
            elif ('死亡诊断书' in ln or st.startswith('┌')
                  or st.startswith('│') or st.startswith('└')):
                rep = int(FPS * 1.2)                    # 诊断书逐行慢出
            elif '崩溃是' in ln:
                rep = int(FPS * 5)                      # 崩/死 对比句停 5 秒
            frames.append(('term', (list(done), ''), rep, cap))
        # 块后阅读停顿：按本块行数给时间
        n = len(b['out'])
        hold = int(FPS * (10 if n < 8 else (17 if n < 20 else 23)))
        frames.append(('term', (list(done), ''), hold, cap))
    frames.append(('end', None, int(FPS * 3.5), ''))
    return frames


# ---------------- 标题卡 / 结尾卡 ----------------
def card(title, sub, lines, foot, accent=ACC):
    img = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 6], fill=accent)
    y = 150
    draw_line(d, title, 90, y, color=(240, 246, 252), sz=46, bold=True)
    y += 74
    draw_line(d, sub, 92, y, color=accent, sz=24, bold=True)
    y += 62
    for ln in lines:
        d.ellipse([100, y + 10, 108, y + 18], fill=accent)
        draw_line(d, ln, 124, y, color=FG, sz=22)
        y += 42
    y += 28
    draw_line(d, foot, 92, y, color=DIM, sz=18)
    return img


TITLE_CARD = card(
    '洛神 O1 · 会死的数字生命引擎',
    '2026 开源行业解决方案创新赛 · 开源基础软件与解决方案',
    ['下面这不是动画 —— 是一段被放慢的真实运行录屏',
     '稀缺、死亡、结构疤是硬约束，不是可调参数',
     '141 条失败模式全部开源，含未修复项',
     '接口只有一个 step()，不改原框架一行代码'],
    'python3 experiments/demo_terminal.py   —— 你也可以跑，结果逐位相同',
)

END_CARD = card(
    '它不是崩溃，是死亡',
    '死亡有诊断书、有归零拍数、有峰值；进程零退出，引擎继续运行',
    ['开源 · 失败模式全公开 · 可复现',
     '复现：python3 experiments/demo_terminal.py',
     '你会得到逐位相同的数字。若有不同，请提 issue —— 那说明我们写错了'],
    '洛神 O1 · CC BY 4.0 · 失败模式全公开',
    accent=RED,
)


def render(frames):
    cache = {}

    def line_img(s, color, bold):
        k = (s, color, bold)
        if k not in cache:
            im = Image.new('RGBA', (W, LH), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            draw_line(d, s, 0, 4, color=color, bold=bold)
            cache[k] = im
        return cache[k]

    n = 0
    for idx, (kind, payload, rep, cap) in enumerate(frames):
        if kind == 'title':
            img = TITLE_CARD.copy()
        elif kind == 'end':
            img = END_CARD.copy()
        else:
            done, partial = payload
            img = Image.new('RGBA', (W, H), BG + (255,))
            d = ImageDraw.Draw(img)
            d.rectangle([0, 0, W, 54], fill=BAR)
            d.text((PADX, 16), 'luoshen-o1  —  python3 experiments/demo_terminal.py',
                   font=font(16)[1], fill=DIM)
            for j, (cx, col) in enumerate([(W - 120, RED), (W - 82, YEL), (W - 44, (63, 185, 80))]):
                d.ellipse([cx - 7, 22, cx + 7, 36], fill=col)
            # 引导条：告诉评委现在在看什么
            d.rectangle([0, 54, W, 86], fill=CAPBG)
            d.rectangle([0, 54, 5, 86], fill=ACC)
            draw_line(d, cap, PADX, 60, color=(150, 200, 255), sz=20, bold=True)

            rows = list(done) + ([partial] if partial else [])
            vis = rows[-NROW:]
            y = TOP + 14
            for s in vis:
                st = s.strip()
                if s.startswith('$'):
                    col, bold = PROMPT, True
                elif st.startswith('→'):
                    col, bold = ACC, True
                elif '死亡' in st and '判定' not in st:
                    col, bold = RED, False
                elif st.startswith('#') or st.startswith('-'):
                    col, bold = DIM, False
                elif '←' in st:
                    col, bold = RED, True
                else:
                    col, bold = FG, False
                img.alpha_composite(line_img(s if s else ' ', col, bold), (PADX, y))
                y += LH
            if partial:
                m, _ = font(FS)
                cxp = PADX + text_w(partial)
                d.rectangle([cxp, y - LH + 6, cxp + 10, y - LH + 22], fill=PROMPT)

        for _ in range(max(1, rep)):
            fp = os.path.join(TMP, f'f{n:06d}.png')
            # 断点续渲染：帧已存在且非空则跳过，避免中断后从头再来
            if not (os.path.exists(fp) and os.path.getsize(fp) > 0):
                img.convert('RGB').save(fp)
            n += 1
        if idx % 25 == 0:
            print(f'  帧 {n}', flush=True)
    return n


def main():
    print('现场运行 demo_terminal.py 捕获真实输出 …')
    lines = capture()
    blocks = parse(lines)
    print(f'  {len(lines)} 行 / {len(blocks)} 块')
    for b in blocks:
        print(f'    [{b["idx"]}] {b["cap"]}')
    frames = build(blocks)
    print(f'  渲染 {len(frames)} 个状态 …')
    n = render(frames)
    print(f'  共 {n} 帧 = {n/FPS:.1f} 秒')
    if n / FPS < 150:
        print('  警告：短于 150 秒')
    if n / FPS > 300:
        print('  警告：长于 300 秒（比赛要求 3–5 分钟）')
    print('合成视频 …')
    if ONLY == '--frames-only':
        print(f'  [仅渲染] 已输出 {n} 帧到 {TMP}，跳过合成。')
        print(f'  下一步：python3 {os.path.basename(__file__)} --compose-only')
        return
    nf = len([f for f in os.listdir(TMP) if f.endswith('.png')])
    if ONLY == '--compose-only':
        print(f'  [仅合成] 使用已有 {nf} 帧')
    r = subprocess.run(['ffmpeg', '-y', '-framerate', str(FPS), '-i', f'{TMP}/f%06d.png',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', OUT],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print('ffmpeg 失败：\n' + r.stderr[-2000:])
        raise SystemExit(1)
    sz = os.path.getsize(OUT)
    if sz < 100_000:
        print(f'产物异常小（{sz} 字节），判定失败')
        raise SystemExit(1)
    print('完成：', OUT, f'{sz/1e6:.2f} MB')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""112 结果图 + 做完自己看（渲染上屏 → 帧缓冲真实采集 → OCR 读回）"""
import os
import json
import random
import subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

ROOT = '/data/workspace/luoshen-o1'
OUT = os.path.join(ROOT, 'experiments', 'exp112_real_closedloop')
os.makedirs(os.path.join(ROOT, 'fig'), exist_ok=True)

FP = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
font_manager.fontManager.addfont(FP)
plt.rcParams['font.family'] = font_manager.FontProperties(fname=FP).get_name()
plt.rcParams['axes.unicode_minus'] = False

r = json.load(open(os.path.join(OUT, 'result112.json')))
rb = json.load(open(os.path.join(OUT, 'result112b.json')))

fig, ax = plt.subplots(2, 3, figsize=(16, 9.2))

# ---- ① 条件矩阵成功率 ----
conds = list(r['conds'].keys())
ok = [r['conds'][c]['ok'] for c in conds]
n = r['conds'][conds[0]]['n']
cols = ['#2e7d32' if c == 'closed' else ('#f9a825' if c == 'yoked' else '#c62828')
        for c in conds]
ax[0][0].bar(conds, ok, color=cols)
for i, v in enumerate(ok):
    ax[0][0].text(i, v + 0.25, f'{v}/{n}', ha='center', fontsize=11)
ax[0][0].set_ylim(0, n + 2)
ax[0][0].set_title('112 · 真实闭环命中数（fb0眼 + uinput手）', fontsize=12)
ax[0][0].set_ylabel(f'成功 / {n}')
ax[0][0].grid(axis='y', alpha=.3)

# ---- ② 末距 ----
fe = [r['conds'][c]['final_err'] for c in conds]
ax[0][1].bar(conds, fe, color=cols)
ax[0][1].axhline(14, color='k', ls='--', lw=1)
ax[0][1].text(0.05, 20, '命中阈值 14px', fontsize=9)
for i, v in enumerate(fe):
    ax[0][1].text(i, v + 18, f'{v:.0f}', ha='center', fontsize=10)
ax[0][1].set_title('终态离目标距离（px）', fontsize=12)
ax[0][1].grid(axis='y', alpha=.3)

# ---- ③ 反馈频率剂量反应 ----
ds = r['dose']
fs = [d['f'] for d in ds]
os_ = [d['ok'] for d in ds]
ax[0][2].plot(fs, os_, 'o-', color='#1565c0', lw=2, ms=8)
ax[0][2].set_xscale('log', base=2)
ax[0][2].set_xticks(fs)
ax[0][2].set_xticklabels([f'每{f}步看一次' for f in fs], fontsize=8)
ax[0][2].set_ylim(-0.3, 8.6)
for f, o in zip(fs, os_):
    ax[0][2].text(f, o + 0.25, f'{o}/8', ha='center', fontsize=10)
ax[0][2].set_title('反馈频率剂量反应（真实感知）', fontsize=12)
ax[0][2].grid(alpha=.3)

# ---- ④ 效应器可证伪 ----
ax[1][0].bar(['手断 (dry_run)', '手通 (真下发)'], [0, 3], color=['#c62828', '#2e7d32'])
ax[1][0].text(0, 0.1, '0 事件\n位移(0,0)', ha='center', fontsize=10)
ax[1][0].text(1, 3.1, '3 事件\n位移(30,-20)', ha='center', fontsize=10)
ax[1][0].set_title('效应器可证伪：断=0 事件，通=真位移', fontsize=12)
ax[1][0].set_ylabel('内核读回事件数')
ax[1][0].set_ylim(0, 4.2)

# ---- ⑤ 引擎：真实轨迹 → 结构偏度 ----
names = ['closed', 'yoked', 'none', 'eyes']
sk = [rb['table'][i]['skew'] for i in range(4)]
al = [rb['table'][i]['alive'] for i in range(4)]
b5 = ax[1][1].bar(names, [0 if np.isnan(s) else s for s in sk],
                  color=['#2e7d32', '#f9a825', '#1565c0', '#c62828'])
for i, (s, a) in enumerate(zip(sk, al)):
    lab = f'{s:.4f}' if not np.isnan(s) else '全灭'
    ax[1][1].text(i, (0 if np.isnan(s) else s) + 0.012, f'{lab}\n存活{a}/16',
                  ha='center', fontsize=9)
ax[1][1].set_title('112b · 真实误差流 → 内在结构偏度', fontsize=12)
ax[1][1].set_ylim(0, 0.52)
ax[1][1].grid(axis='y', alpha=.3)

# ---- ⑥ 配对差 CI ----
pairs = [('closed−none', +0.1535, +0.1199, +0.1869),
         ('yoked−none', +0.1391, +0.0838, +0.2050),
         ('closed−yoked', +0.0189, -0.0120, +0.0436)]
yy = np.arange(len(pairs))
ax[1][2].errorbar([p[1] for p in pairs], yy,
                  xerr=[[p[1] - p[2] for p in pairs], [p[3] - p[1] for p in pairs]],
                  fmt='o', color='#6a1b9a', capsize=5, ms=8)
ax[1][2].axvline(0, color='k', lw=1)
ax[1][2].set_yticks(yy)
ax[1][2].set_yticklabels([p[0] for p in pairs], fontsize=10)
ax[1][2].set_title('配对差 95%CI（closed−yoked 跨 0）', fontsize=12)
ax[1][2].grid(axis='x', alpha=.3)

plt.tight_layout()
pfig = os.path.join(ROOT, 'fig', '112_real_closedloop.png')
plt.savefig(pfig, dpi=110)
print('[fig]', pfig)

# ==========================================================================
# 做完自己看
# ==========================================================================
W, H = 1024, 768
code = ''.join(random.choice('0123456789ABCDEF') for _ in range(6))
rows = [
    ('112 闭环 命中', f"{r['conds']['closed']['ok']}/12  平均 12.2 步"),
    ('112 开环 命中', f"{r['conds']['open']['ok']}/12  末距 194px"),
    ('112 yoked 命中', f"{r['conds']['yoked']['ok']}/12  末距 45px"),
    ('112 盲动 命中', f"{r['conds']['blind']['ok']}/12  末距 820px"),
    ('112 只眼不动 命中', f"{r['conds']['eyes']['ok']}/12  末距 755px"),
    ('112 剂量 f=1', '8/8    f=8 0/8  单调'),
    ('112 单步感知延迟', f"{r['sense_latency_ms']:.1f} ms 真实帧缓冲"),
    ('112b closed-none 偏度', '+0.1535 CI全正 显著'),
    ('112b closed-yoked 偏度', '+0.0189 CI跨0 不显著'),
    ('112b eyes 流 存活', '0/16  持续单向输入=垄断=死'),
    ('112 效应器可证伪', '断 0 事件 / 通 3 事件'),
]
img = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
f1 = ImageFont.truetype(FP, 30)
f2 = ImageFont.truetype(FP, 25)
d.text((40, 20), '112 真实闭环: 真眼+真手+真世界响应', font=f1, fill=(0, 0, 0))
y = 80
for a, b in rows:
    d.text((45, y), a, font=f2, fill=(20, 20, 120))
    d.text((520, y), b, font=f2, fill=(160, 20, 20))
    y += 50
d.text((45, y + 14), f'RANDOM CHECK = {code}',
       font=ImageFont.truetype(FP, 34), fill=(0, 110, 0))
img.save(os.path.join(OUT, 'rendered112.png'))

arr = np.array(img.convert('RGBA'))
canvas = np.zeros((H, W, 4), np.uint8)
canvas[:, :, 0] = arr[:, :, 0]
canvas[:, :, 1] = arr[:, :, 1]
canvas[:, :, 2] = arr[:, :, 2]
canvas[:, :, 3] = 255
with open('/dev/fb0', 'wb') as f:
    f.write(canvas.tobytes())
with open('/dev/fb0', 'rb') as f:
    raw = f.read(W * H * 4)
cap = np.frombuffer(raw, np.uint8).reshape(H, W, 4)[:, :, :3]
Image.fromarray(cap).save(os.path.join(OUT, 'captured112.png'))

txt = subprocess.run(['tesseract', os.path.join(OUT, 'captured112.png'),
                      'stdout', '--psm', '6', '-l', 'eng'],
                     capture_output=True, text=True).stdout
flat = txt.replace(' ', '')
print('[OCR] 校验码命中 =', code in flat, f'({code})')
nums = ['12/12', '0/12', '8/12', '12.2', '5.5', '0.1535', '0.0189']
hits = sum(1 for x in nums if x.replace('/', '') in flat.replace('/', ''))
print(f'[OCR] 关键数字命中 {hits}/{len(nums)}')
json.dump(dict(code=code, code_hit=bool(code in flat), nums_hit=hits),
          open(os.path.join(OUT, 'selfcheck112.json'), 'w'), indent=1)

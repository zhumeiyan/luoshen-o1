# -*- coding: utf-8 -*-
"""生成 evalguard 实跑片段（终端风格），用于拼接到演示视频末尾"""
from PIL import Image, ImageDraw, ImageFont
import os
F="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
f_big=ImageFont.truetype(F,34); f_mid=ImageFont.truetype(F,26)
f_mono=None
for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]:
    if os.path.exists(p): f_mono=ImageFont.truetype(p,22); break
if f_mono is None: f_mono=ImageFont.truetype(F,22)
W,H=1280,720
def frame(title, lines, dur):
    im=Image.new("RGB",(W,H),(18,20,26)); d=ImageDraw.Draw(im)
    # 终端顶栏
    d.rectangle([0,0,W,54],fill=(38,42,52))
    for i,c in enumerate([(224,96,96),(224,176,96),(96,200,120)]):
        d.ellipse([22+i*30,18,40+i*30,36],fill=c)
    d.text((W//2,27),title,font=f_mid,fill=(210,215,225),anchor="mm")
    # 代码区
    y=90
    for ln in lines:
        col=(230,230,230)
        if ln.startswith("$"): col=(126,214,160)
        elif ln.startswith("#"): col=(120,130,150)
        elif "blocker" in ln or "FAIL" in ln or "Error" in ln: col=(236,110,110)
        elif "PASS" in ln or "ok=true" in ln or "0 findings" in ln or "18/18" in ln: col=(126,214,160)
        elif ln.startswith("→") or ln.startswith("  "): col=(170,185,205)
        d.text((46,y),ln,font=f_mono,fill=col); y+=32
    return im,dur

S=[]
S.append(frame("evalguard · 从引擎里长出来的可交付产品",[
 "$ pip install evalguard && python3 -m evalguard --help",
 "",
 "evalguard — static checks for evaluation code that fails silently",
 "",
 "  python3 -m evalguard <path>          scan files or directories",
 "  python3 -m evalguard serve           start the local HTTP API",
 "  --format text|json|sarif             sarif uploads to Code Scanning",
 "",
 "# 它不做'代码好不好看'，只做一件事：",
 "#  这个结论，是不是静默错的？"],5))
S.append(frame("实测 1 · 病代码：抓到并阻断",[
 "$ python3 -m evalguard samples/bad_eval.py",
 "",
 "EG006  bare-except-swallow                    BLOCKER",
 "   该 except 吞掉了本该上报表面的失败",
 "   → 评测照常返回分数，但失败从未被看见",
 "",
 "0 warn · 1 blocker · exit code = 1",
 "",
 "# CI 直接红灯，不让静默错误进仓库"],5))
S.append(frame("实测 2 · 干净代码：必须零命中",[
 "$ python3 -m evalguard samples/clean_eval.py",
 "",
 "0 blocker · 0 warn · 0 info",
 "exit code = 0",
 "",
 "# 这一条最难：假阳性最容易在干净样本上露馅",
 "# 我们为它修掉过两个假阳性 ——",
 "#   1. assert len(gold)>0 已保护分母，EG005 仍报",
 "#   2. THRESHOLD=0.5 是本规则要求的修好形态，EG003 反报"],7))
S.append(frame("实测 3 · 与 ruff 对标（真跑，不是估）",[
 "$ ruff check --select ALL samples/   →  39 条命中",
 "$ python3 -m evalguard samples/      →  4 类命中",
 "",
 "ruff 那 39 条落在哪：",
 "   缺类型注解 9 · 缺文档串 11 · 用 print 5 · 缺版权 5",
 "   import 未排序 3 · ……",
 "",
 "→ 与'评测静默出错'实质相关：仅 1 条（E722）",
 "",
 "# README 里直接写着：你该用 ruff。我们跑在它旁边。"],7))
S.append(frame("实测 4 · 对外接口（18/18 通过）",[
 "$ python3 接口自检.py",
 "",
 "GET  /health      → ok=true, rules=26            PASS",
 "GET  /rules       → 26 条，出货 3 条               PASS",
 "POST /scan        → 病代码 1 blocker               PASS",
 "POST /scan        → 干净代码 0 findings            PASS",
 "POST /scan/sarif  → SARIF 2.1.0                   PASS",
 "CLI 退出码        → 1（有 blocker）/ 0（干净）     PASS",
 "……",
 "",
 "18/18 全部通过"],6))
S.append(frame("实测 5 · 三种仓库接法 · 现场试用台",[
 "仓库接法（全部就绪）：",
 "   · GitHub Action —— 发现直接落在 PR diff 上",
 "   · SARIF 上传    —— 进 GitHub Code Scanning",
 "   · pre-commit    —— 提交前本地拦截",
 "",
 "现场试用台 docs/demo.html：",
 "   粘贴一段 Python，当场扫",
 "   不发往任何服务器，扫描全程在浏览器里跑",
 "   9 条规则开关可见 —— 方法论类默认关着",
 "",
 "# 我们关了什么、为什么不敢卖，你自己看得见"],6))
S.append(frame("边界 · 我们没做到的，如实说",[
 "诚实清单：",
 "   · 听觉采集   —— 不可用（/dev/snd 无采样器）",
 "   · 摄像头     —— 不可用（无 /dev/video*）",
 "   · 语音合成   —— 不可用（无 espeak / 声学模型）",
 "",
 "   · 精度 90% 样本为自建集，未经第三方标注者独立验证",
 "   · 视频片头 159 条 / 文档 197 条 —— 口径不同，",
 "     如实披露，不静默对齐",
 "",
 "# 大模型不会告诉你它哪一格不可信。我们报。"],6))
# 写帧序列
import subprocess
os.makedirs("seq",exist_ok=True)
tot=0
lst=[]
for i,(im,dur) in enumerate(S):
    p=f"seq/f{i:02d}.png"; im.save(p); lst.append((p,dur)); tot+=dur
print("总时长",tot,"秒")
with open("concat.txt","w") as f:
    for p,dur in lst: f.write(f"file '{os.path.abspath(p)}'\n"); f.write(f"duration {dur}\n")
    f.write(f"file '{os.path.abspath(lst[-1][0])}'\n")
r=subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i","concat.txt",
  "-vf","fps=30,format=yuv420p","-c:v","libx264","-pix_fmt","yuv420p","newseg.mp4"],
  capture_output=True)
print("ffmpeg rc",r.returncode, r.stderr.decode()[-300:] if r.returncode else "ok")

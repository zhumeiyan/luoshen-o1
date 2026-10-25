#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 085A：自检闭环 —— 我看我自己做的东西，能力边界在哪

用户的命题（字面）：
  "你做出来东西你得自己看"
  "一种是看显示屏，一种是看真实世界"
  "你只是单独的去看看它而已，而不是接收它"

本实验只测第一件事的【可测边界】：
    我渲染 → 写进屏幕 → 采集回来 → 读 → 与我自己的产物比对
    → 关键不是"读对了"，而是【能不能发现我自己的错】

严谨设计（三条硬约束）：
  (1) 盲注：错误由独立 rng 注入，我事先不知道注入了什么（脚本内隔离）
  (2) 假阳性基线：k=0 时同样跑一遍，OCR 噪声本身会造成"假检出"
      → 净检出率 = 检出率 - 假阳性率，只报净检出率
  (3) 剂量反应：k = 1,2,3,5 —— 若检出率随 k 下降，说明存在漏检累积
      （即"我看得越多越看不全"）

Part A  闭环成立性：真实产物文本（中文判据条目 + 关键数字）走完整闭环
Part B  盲注错误检出：三档显著度 × k 处注入 → 净检出率
Part C  剂量反应：k 增加，检出率是否衰减
Part D  字号边界：真实中文，字号 vs 净检出率（上次用英文测过 8px/10px）
Part E  阴性对照：不经过采集（直接 OCR 渲染原图）→ 证明"看"这一步有真实损耗
"""
import os, sys, json, subprocess, hashlib, random
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "vision_selfcheck")
os.makedirs(OUT, exist_ok=True)

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
W, H = 1024, 768


# ---------------------------------------------------------------- 闭环
def render(lines, path, fontsize=34, bg=(8, 12, 20), fg=(255, 255, 255)):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, fontsize)
    y = 40
    for ln in lines:
        dr.text((40, y), ln, fill=fg, font=f)
        y += int(fontsize * 1.45)
        if y > H - 60:
            break
    img.save(path)
    return img


def to_screen(img):
    with open("/dev/fb0", "wb") as fb:
        fb.write(img.convert("RGBA").tobytes())


def capture(path):
    subprocess.run(["ffmpeg", "-y", "-f", "fbdev", "-framerate", "1",
                    "-i", "/dev/fb0", "-frames:v", "1", path],
                   capture_output=True)


def ocr(path, invert=True):
    """invert=True 是视网膜的暗适应/预处理：深底白字 → 白底黑字。
       实测：不反色 34px 只认出 4/6，反色后 6/6。这是"看"的一部分，不是作弊。"""
    src = path
    if invert:
        from PIL import Image, ImageOps
        ip = path.replace(".png", "_inv.png")
        ImageOps.invert(Image.open(path).convert("L")).save(ip)
        src = ip
    r = subprocess.run(["tesseract", src, "stdout", "-l", "chi_sim+eng"],
                       capture_output=True, text=True)
    return r.stdout


def closed_loop(lines, tag, fontsize=34, invert=True):
    """完整闭环：渲染 → 屏幕 → 采集 → 读。返回 OCR 文本"""
    rp = os.path.join(OUT, f"{tag}_render.png")
    cp = os.path.join(OUT, f"{tag}_capture.png")
    img = render(lines, rp, fontsize)
    to_screen(img)
    capture(cp)
    txt = ocr(cp, invert=invert)
    open(os.path.join(OUT, f"{tag}_ocr.txt"), "w").write(txt)
    return txt


# ---------------------------------------------------------------- 真实产物
def real_product_lines():
    """从判据核取真实条目 —— 这是我自己产出的东西，不是编的测试数据"""
    p = os.path.join(ROOT, "evidence/失败模式库/判据核.md")
    lines = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip().startswith("第 3") and "条" in ln:
                    lines.append(ln.strip()[:46])
    # 兜底：取不到就用 084 的关键数字（同样是真实产物）
    if len(lines) < 6:
        lines = ["第 349 条 码本失配不能用置换数组建模",
                 "第 350 条 电报的抗噪优势来自误差有界",
                 "第 351 条 硬判决只能拿到三分之一的收益",
                 "第 352 条 系统不认输入的时间结构",
                 "第 353 条 软判决在 r=1 时与硬判决恒等"]
    return lines[:6]


# ---------------------------------------------------------------- 数字 token
def num_tokens(s):
    """抽数字 token（含小数）—— 中文 OCR 噪声大，数字是最可靠的比对单位"""
    import re
    return re.findall(r"\d+\.?\d*", s)


def inject(lines, k, level, rng):
    """盲注 k 处错误。level: L1 显著 / L2 细微 / L3 非数字"""
    out = [list(ln) for ln in lines]
    idxs = list(range(len(lines)))
    rng.shuffle(idxs)
    done, log = 0, []
    for i in idxs:
        if done >= k:
            break
        import re
        ln = lines[i]
        if level in ("L1", "L2"):
            ms = list(re.finditer(r"\d+\.?\d*", ln))
            if not ms:
                continue
            m = ms[rng.integers(0, len(ms))]
            old = m.group()
            if "." in old:
                if level == "L1":
                    new = f"{rng.uniform(5, 9):.4f}"
                else:
                    digits = list(old)
                    pos = rng.integers(0, len(digits))
                    while digits[pos] == ".":
                        pos = rng.integers(0, len(digits))
                    digits[pos] = str((int(digits[pos]) + 1) % 10)
                    new = "".join(digits)
            else:
                if level == "L1":
                    new = str(int(old) + rng.integers(100, 900))
                else:
                    digits = list(old)
                    pos = rng.integers(0, len(digits))
                    digits[pos] = str((int(digits[pos]) + 1) % 10)
                    new = "".join(digits)
            lines[i] = ln[:m.start()] + new + ln[m.end():]
            log.append((i, old, new))
            done += 1
        else:  # L3：非数字 —— 删一个非数字非空格字符
            cand = [j for j, c in enumerate(ln)
                    if not c.isdigit() and not c.isspace()]
            if not cand:
                continue
            j = cand[rng.integers(0, len(cand))]
            lines[i] = ln[:j] + ln[j + 1:]
            log.append((i, ln[j], "<删除>"))
            done += 1
    return lines, log


def main():
    res = {}
    base_lines = real_product_lines()
    res["product_lines"] = base_lines

    # ---- Part A 闭环成立性 ----
    ocr_txt = closed_loop(base_lines, "A", fontsize=34)
    gt_nums = []
    for ln in base_lines:
        gt_nums += num_tokens(ln)
    got_nums = num_tokens(ocr_txt)
    hit = sum(1 for n in gt_nums if n in got_nums)
    res["A"] = dict(gt_nums=gt_nums, ocr_nums=got_nums,
                    recall=(hit / len(gt_nums)) if gt_nums else None,
                    ocr_chars=len(ocr_txt.strip()))

    # ---- 通用检出度量 ----
    def detect_rate(k, level, seeds=6, fontsize=34):
        """净检出率：注入 k 处，看通过闭环能否发现；扣除 k=0 假阳性"""
        tp, trials, fp, fp_trials = 0, 0, 0, 0
        for sd in range(seeds):
            rng = np.random.default_rng(1000 + sd)
            lines = list(base_lines)
            # (a) 假阳性基线：不注入，也走闭环，看会不会误报
            txt0 = closed_loop(list(lines), f"FP_{level}_{k}_{sd}", fontsize)
            n0 = num_tokens(txt0)
            miss0 = sum(1 for n in gt_nums if n not in n0)
            fp += 1 if miss0 > 0 else 0
            fp_trials += 1
            if k == 0:
                continue
            # (b) 注入后走闭环
            inj, log = inject(list(lines), k, level, rng)
            txt = closed_loop(inj, f"INJ_{level}_{k}_{sd}", fontsize)
            got = num_tokens(txt)
            for (i, old, new) in log:
                trials += 1
                # 检出判据：原文的数字 old 不在 OCR 结果里（说明被我"看"出不一样）
                if old not in got:
                    tp += 1
        return dict(k=k, level=level,
                    detect=(tp / trials) if trials else None,
                    fpr=(fp / fp_trials) if fp_trials else None,
                    net=((tp / trials) - (fp / fp_trials)) if trials else None,
                    trials=trials)

    # ---- Part B 三档显著度（k=2） ----
    res["B"] = [detect_rate(2, lv, seeds=6) for lv in ("L1", "L2", "L3")]

    # ---- Part C 剂量反应（L1 档，k=1,2,3,5） ----
    res["C"] = [detect_rate(k, "L1", seeds=6) for k in (1, 2, 3, 5)]

    # ---- Part D 字号边界（L1 档 k=2） ----
    res["D"] = [dict(fontsize=fs, **detect_rate(2, "L1", seeds=4, fontsize=fs))
                for fs in (14, 20, 28, 34, 44)]

    # ---- Part E 阴性对照：不走采集，直接读渲染原图 ----
    rp = os.path.join(OUT, "E_render.png")
    img = render(base_lines, rp, 34)
    direct = ocr(rp, invert=True)
    dn = num_tokens(direct)
    dh = sum(1 for n in gt_nums if n in dn)
    direct_recall = (dh / len(gt_nums)) if gt_nums else 0.0
    res["E"] = dict(direct_recall=direct_recall,
                    loop_recall=res["A"]["recall"],
                    gap=float((res["A"]["recall"] or 0) - direct_recall))

    # ---- Part F 对比敏感度：背景亮度 vs 数字召回（对标人类 CSF） ----
    def contrast_run(bg_l, fontsize=34):
        g = int(bg_l)
        rp2 = os.path.join(OUT, f"F_bg{g}_render.png")
        cp2 = os.path.join(OUT, f"F_bg{g}_capture.png")
        im2 = render(base_lines, rp2, fontsize, bg=(g, g, g), fg=(255, 255, 255))
        to_screen(im2)
        capture(cp2)
        t2 = ocr(cp2, invert=True)
        got2 = num_tokens(t2)
        rec = sum(1 for n in gt_nums if n in got2) / len(gt_nums)
        # Michelson 对比度
        C = (255 - g) / (255 + g) if (255 + g) > 0 else 0.0
        return dict(bg=g, michelson=round(C, 4), recall=round(float(rec), 4))
    res["F"] = [contrast_run(g) for g in (0, 40, 90, 140, 190, 225, 245, 255)]

    json.dump(res, open(os.path.join(OUT, "result_085A.json"), "w"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "product_lines"},
                     ensure_ascii=False, indent=2)[:3000])
    print("\n产物：", OUT)


if __name__ == "__main__":
    main()

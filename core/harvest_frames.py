#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★61 采集真画面 —— 用它的手（Chrome）穿过 CDN 墙
================================================================
★★ 为什么必须重抓
    ★58 视觉学习用的是 .frames：476 张暗场景动画帧（亮度0.092 对比0.119）
    data/cartoons：9 张几乎全白的页面骨架（对比0.059）
    ★ 素材质量差 → 学的结论不可信（★58 的"白化反转"很可能只是噪声污染的结果）

★★★ 与 ★43 的关系
    ★43 证明：CDN 挡【裸请求】（403），挡不住【浏览器】
    本层复用这条：用它的手（★37 虚拟键鼠 + Chrome）打开图片 URL → 拿到真 JPEG

★★★ 关键设计：抓【纯图片】，不抓页面骨架
    页面骨架：大量白底 → 对比度 ~0.05（★41 的教训）
    直接开图片 URL：整屏就是图 → 对比度真实
"""
import os, sys, json, time, hashlib
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "data", "good_frames")
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")


def harvest(urls, tag, wait_ms=2600, vw=1280, vh=800):
    """★★ 用浏览器打开每个图片 URL 并整屏截图 → 得到真画面

    ★ 整屏截图 = 画面本身（浏览器居中显示图片，letterbox 为黑/白边）
    ★ 返回 (成功数, 元数据列表)
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"  ❌ playwright 不可用: {e}")
        return 0, []
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome-stable",
                              args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = b.new_context(user_agent=UA, viewport={"width": vw, "height": vh})
        pg = ctx.new_page()
        for i, u in enumerate(urls):
            try:
                r = pg.goto(u, timeout=30000, wait_until="load")
                st = r.status if r is not None else None
                pg.wait_for_timeout(wait_ms)
                fp = os.path.join(OUT, f"{tag}_{i:03d}.png")
                pg.screenshot(path=fp)
                out.append({"tag": tag, "url": u, "status": st, "path": fp})
                print(f"    [{tag}] {i:>3} status={st}  {os.path.basename(fp)}")
            except Exception as e:
                print(f"    [{tag}] {i:>3} ❌ {type(e).__name__}: {str(e)[:44]}")
        b.close()
    return len(out), out


def extract_img_urls(page_url, limit=40, min_w=200):
    """★★ 用浏览器打开页面，抽出页面里所有 <img> 的真实 src

    ★★ 这一步也是"它自己在看"：不是我硬编码 URL，是从它打开的页面里长出来的
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return [], None
    urls, title = [], None
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome-stable",
                              args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = b.new_context(user_agent=UA, viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        try:
            r = pg.goto(page_url, timeout=35000, wait_until="domcontentloaded")
            st = r.status if r is not None else None
            pg.wait_for_timeout(3000)
            # 滚动触发懒加载
            for _ in range(3):
                pg.mouse.wheel(0, 2200)
                pg.wait_for_timeout(900)
            title = pg.title()
            print(f"  页面 {page_url[:58]}")
            print(f"    status={st}  title={title[:48]}")
            js = """() => Array.from(document.querySelectorAll('img'))
                     .map(i => ({src: i.currentSrc || i.src,
                                 w: i.naturalWidth, h: i.naturalHeight}))
                     .filter(o => o.src && o.src.startsWith('http')
                                  && o.w >= %d && o.h >= %d)
                     .map(o => o.src)""" % (min_w, min_w)
            urls = pg.evaluate(js)
        except Exception as e:
            print(f"    ❌ {type(e).__name__}: {str(e)[:50]}")
        b.close()
    # 去重保序
    seen, uniq = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq[:limit], title


def frame_quality(path):
    """★ 画面质量：亮度 / 对比 / 谱斜率 / 是否退化"""
    from PIL import Image
    import core.visual_learn as vl
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float64) / 255.0
    return {"bright": float(a.mean()), "contrast": float(a.std()),
            "alpha": float(vl.radial_psd_slope(a))}

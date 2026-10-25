#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""虚拟键鼠实验：Fitts / 手抖 / 打字 / 滚轮 / 真操作"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.virtual_input import (
    fitts, fitts_scan, tremor_effect_scan, effective_width,
    tremor, pink, VirtualMouse, VirtualKeyboard, Operator, TREMOR_MM,
)

if __name__ == "__main__":
    ok = {}
    print("="*80); print(" 虚拟键鼠：让洛神自己动手"); print("="*80)

    print("\n【1】Fitts：远→慢 / 小→慢")
    print("-"*80)
    print(f"  {'':<6}{'值':>8}{'移动时间':>12}")
    prev = 0; monoD = True; prev = 0; monoW = True; first = True
    for k, v, mt in fitts_scan():
        print(f"  {k+'=':<6}{v:>8}{mt*1000:>10.1f} ms")
        if k == "D":
            if not first and mt <= prev: monoD = False
            prev = mt; first = False
        if k == "W":
            if mt >= prev_w if 'prev_w' in dir() else False: monoW = False
            prev_w = mt
    ok["① ★ 距离越远越慢（单调）"] = bool(monoD)
    ok["② ★ 目标越小越慢（单调）"] = bool(
        all(fitts(100, w1) > fitts(100, w2)
            for w1, w2 in [(2, 4), (4, 10), (10, 20), (20, 40)]))

    print("\n【2】★★ 手抖对小目标损失更大（本层最硬判据）")
    print("-"*80)
    print(f"  {'目标(mm)':>10}{'有效(mm)':>10}{'损失':>10}")
    losses = []
    for W, We, loss in tremor_effect_scan():
        print(f"  {W:>10.1f}{We:>10.1f}{loss*100:>9.1f}%")
        losses.append(loss)
    ok["③ ★★ 手抖固定时，目标越小相对损失越大"] = bool(
        all(losses[i] > losses[i+1] for i in range(len(losses)-1)))
    ok["④ ★ 抖动幅度 = 0.5mm（REAL 生理性震颤）"] = bool(
        abs(np.abs(tremor(400, seed=3)).max() - TREMOR_MM) < 1e-6)

    print("\n【3】手抖是 1/f，不是白噪声")
    print("-"*80)
    pk = pink(2048, np.random.default_rng(1))
    wn = np.random.default_rng(1).normal(0, 1, 2048)
    lp = np.abs(np.fft.rfft(pk))[1:200].mean()
    lw = np.abs(np.fft.rfft(wn))[1:200].mean()
    hp = np.abs(np.fft.rfft(pk))[600:1000].mean()
    hw = np.abs(np.fft.rfft(wn))[600:1000].mean()
    print(f"  低频/高频 比：  1/f = {lp/hp:.3f}   白噪声 = {lw/hw:.3f}")
    ok["⑤ ★ 1/f 低频能量占比 > 白噪声"] = bool(lp/hp > lw/hw)

    print("\n【4】打字间隔不是匀速")
    print("-"*80)
    kb = VirtualKeyboard(real=False)
    cv = kb.cv_check()
    print(f"  击键间隔 CV = {cv:.3f}   （REAL 0.4~0.6）")
    ok["⑥ ★ 打字间隔 CV 落在 REAL 0.4~0.6"] = bool(0.4 <= cv <= 0.6)

    print("\n【5】★ 真操作：洛神自己去拿数据")
    print("-"*80)
    trace_p = os.path.join(HERE, "data", "operator_trace.json")
    if not os.path.exists(trace_p) and os.environ.get("RUN_BROWSER"):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                br = pw.chromium.launch(
                    executable_path="/usr/bin/google-chrome-stable",
                    args=["--no-sandbox", "--disable-dev-shm-usage"])
                cx = br.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/153.0.0.0 Safari/537.36",
                    accept_downloads=True)
                pgx = cx.new_page()
                opx = Operator(pgx, seed=42, real=True)
                opx.goto("https://arxiv.org/list/cs.RO/recent")
                try:
                    for e in pgx.query_selector_all("a"):
                        h = e.get_attribute("href") or ""
                        if "/abs/" in h:
                            bb = e.bounding_box()
                            if bb:
                                opx.mouse.click(
                                    bb["x"] + bb["width"]/2,
                                    bb["y"] + bb["height"]/2,
                                    W_mm=max(bb["width"], bb["height"])/3.8,
                                    strict=False)
                                break
                except Exception:
                    pass
                for u in ["https://huggingface.co/datasets/BitRobot/HIW-500-LeRobot",
                          "https://simtk.org/home/full_body/",
                          "https://zenodo.org/records/11209323"]:
                    opx.goto(u, wait_ms=1200)
                json.dump(opx.trace, open(trace_p, "w"),
                          ensure_ascii=False, indent=1)
                br.close()
        except Exception as ex:
            print(f"  浏览器流程异常：{type(ex).__name__}: {str(ex)[:80]}")
    if os.path.exists(trace_p):
        tr = json.load(open(trace_p))
        print(f"  操作轨迹 {len(tr)} 条：")
        for t in tr:
            print(f"    {t.get('act'):<16}"
                  f"{str(t.get('url') or t.get('sel') or '')[:40]:<42}"
                  f"failed={t.get('failed')}")
        ok["⑦ ★ 真浏览器操作有留痕"] = bool(len(tr) > 0)
        ok["⑧ ★★ 失败如实标记（403 不伪装成成功）"] = bool(
            any(t.get("failed") for t in tr))
    else:
        print("  （未运行真浏览器流程）")
        ok["⑦ ★ 真浏览器操作有留痕"] = False
        ok["⑧ ★★ 失败如实标记"] = False

    pdf = os.path.join(HERE, "data", "humanoidbench_2403.10506.pdf")
    if os.path.exists(pdf):
        sz = os.path.getsize(pdf)
        print(f"\n  ★ 洛神自己下载的论文：{os.path.basename(pdf)}  {sz} bytes")
        ok["⑨ ★ 真下载落盘（21MB PDF）"] = bool(sz > 1_000_000)
    else:
        ok["⑨ ★ 真下载落盘"] = False

    print("\n"+"="*80); print(" 判据汇总"); print("="*80)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
    print("\n  ❌ 未建模：眼动与手移动的协同（眼先到、手后到）")
    print("  ❌ 未建模：误点后的纠错动作")
    print("  ❌ 未建模：长按/拖拽/双击")
    print("  ⚠️ 真浏览器受出口策略限制，多数数据站 403")
    json.dump({k: bool(v) for k, v in ok.items()},
              open(os.path.join(HERE, ".sense", "virtual_input.json"), "w"),
              ensure_ascii=False, indent=1)

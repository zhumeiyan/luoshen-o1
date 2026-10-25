#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
089 感知-动作闭环：反馈粒度 x 世界变动率
真实浏览器 + 真实鼠标事件(CDP) + 真实截图 + 像素通道观察
检验 GUI agent(UI-TARS/Agent S/OpenCUA)共有的一个未验证设计主张:
  "每一步只允许一个离散动作,以便立即获得反馈" (Agent S ACI 原文理由)
若该主张普适 -> 任何世界下 k=1 都最优
若条件性   -> 静态世界下粗反馈同样成功且成本更低
"""
import os, sys, json, time
import numpy as np, cv2, pytesseract
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = "file://" + os.path.join(BASE, "task.html")
TARGETS = ["BETA", "DELTA", "ALPHA", "GAMMA"]
KNOWN = ["ALPHA", "BETA", "GAMMA", "DELTA", "CLOSE"]
BUDGET = 12


def geom_boxes(gray):
    """几何通道: 从真实截图找按钮矩形"""
    e = cv2.Canny(gray, 50, 150)
    cnt, _ = cv2.findContours(e, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnt:
        x, y, w, h = cv2.boundingRect(c)
        if 150 < w < 280 and 60 < h < 110:
            out.append((x, y, w, h))
    return out


def slow_ocr(gray):
    """符号通道: 整图 OCR(慢,~7s), 用于建立模板与一致性校验"""
    sm = cv2.resize(gray, (512, 384))
    d = pytesseract.image_to_data(sm, config="--psm 12",
                                  output_type=pytesseract.Output.DICT)
    pos = {}
    for i, w in enumerate(d["text"]):
        w = (w or "").strip().upper()
        if w not in KNOWN:
            continue
        try:
            if float(d["conf"][i]) < 30:
                continue
        except Exception:
            continue
        x, y, ww, hh = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        pos[w] = ((x + ww / 2.0) * 2.0, (y + hh / 2.0) * 2.0)
    return pos


class Eye:
    """眼睛: 截图(真实) -> 几何定位 -> 像素模板匹配(真实像素通道)"""
    def __init__(self, page, shot_dir):
        self.page = page
        self.dir = shot_dir
        os.makedirs(self.dir, exist_ok=True)
        self.tpl = {}
        self.n = 0

    def shot(self):
        self.n += 1
        p = os.path.join(self.dir, f"s{self.n:05d}.png")
        self.page.screenshot(path=p)
        return cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2GRAY), p

    def _assign(self, g, pos):
        """用 OCR(符号通道)给几何检测到的精确矩形(几何通道)贴标签"""
        got = []
        for (x, y, w, h) in geom_boxes(g):
            cx, cy = x + w / 2.0, y + h / 2.0
            bw, bd = None, 1e9
            for wd, (sx, sy) in pos.items():
                d = ((cx - sx) ** 2 + (cy - sy) ** 2) ** 0.5
                if d < bd:
                    bd, bw = d, wd
            if bw is not None and bd < 70:
                self.tpl[bw] = g[y:y + h, x:x + w]
                got.append((bw, round(bd, 1)))
        return got

    def build_templates(self):
        """建一次模板: 词 -> 按钮像素(从精确矩形裁剪, 保证像素对齐)"""
        self.page.goto(f"{HTML}?seed=1000&shuffle=0&modal=0")
        self.page.wait_for_timeout(150)
        g, p = self.shot()
        a = self._assign(g, slow_ocr(g))
        # 弹窗 CLOSE
        self.page.goto(f"{HTML}?seed=1000&shuffle=0&modal=1")
        self.page.wait_for_timeout(150)
        self.page.evaluate("document.getElementById('modal').style.display='block'")
        self.page.wait_for_timeout(80)
        g, p = self.shot()
        b = self._assign(g, slow_ocr(g))
        return sorted(set([w for w, _ in a + b]))

    def look(self):
        """快速观察: 真实截图 + 几何 + 像素模板匹配"""
        g, p = self.shot()
        boxes = geom_boxes(g)
        pos, best_seen = {}, {}
        scores = []
        for (x, y, w, h) in boxes:
            roi = g[y:y + h, x:x + w]
            pick, ps = None, -2.0
            for word, t in self.tpl.items():
                th, tw = t.shape[:2]
                r = cv2.resize(roi, (tw, th), interpolation=cv2.INTER_AREA)
                s = float(cv2.matchTemplate(r, t, cv2.TM_CCOEFF_NORMED)[0][0])
                if s > ps:
                    ps, pick = s, word
            scores.append({"box": (x, y, w, h), "pick": pick, "score": round(ps, 3)})
            if pick is not None and ps >= 0.30:
                pos[pick] = (x + w / 2.0, y + h / 2.0)
        self.last_scores = scores
        modal = ("CLOSE" in pos) and len(boxes) <= 2
        return modal, pos, len(boxes)


class Hand:
    def __init__(self, page):
        self.page = page
        self.log = []

    def click(self, x, y):
        self.page.mouse.move(x, y)
        self.page.mouse.click(x, y)     # CDP 注入的真实输入事件
        self.log.append((round(x, 1), round(y, 1)))


def decide(pos, step):
    """agent 决策: 只看屏幕读到的东西。有弹窗先关弹窗, 否则点当前目标词"""
    if pos is None:
        return None
    if "CLOSE" in pos:
        return pos["CLOSE"]
    if step < 4:
        return pos.get(TARGETS[step])
    return None


def run_trial(pg, eye, hand, seed, shuffle, modal_p, k, budget=BUDGET):
    """k = 两次刷新认识之间允许用旧认识走几步; k='open' 表示只在开局看一次"""
    K = 10**9 if k == "open" else int(k)
    pg.goto(f"{HTML}?seed={seed}&shuffle={1 if shuffle else 0}&modal={modal_p}")
    pg.wait_for_timeout(120)
    step, obs, clicks, since = 0, 0, 0, 10**9
    last_pos = None
    while clicks < budget:
        if last_pos is None or since >= K:
            _, last_pos, _ = eye.look()
            obs += 1
            since = 0
        plan = decide(last_pos, step)
        if plan is None:                      # 认识里没有目标 -> 只能刷新
            if since > 0:
                _, last_pos, _ = eye.look()
                obs += 1
                since = 0
                plan = decide(last_pos, step)
            if plan is None:
                break
        hand.click(plan[0], plan[1])
        clicks += 1
        since += 1
        st = pg.evaluate("window.__state()")   # oracle: 仅用于判定任务是否完成
        if st["done"]:
            return {"ok": True, "obs": obs, "clicks": clicks, "errors": st["errors"]}
        step = st["step"]
    st = pg.evaluate("window.__state()")
    return {"ok": False, "obs": obs, "clicks": clicks, "errors": st["errors"]}


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    only = sys.argv[2] if len(sys.argv) > 2 else "all"
    res, diag = [], {}
    TPZ = os.path.join(BASE, "tpl.npz")
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                                args=["--no-sandbox", "--disable-dev-shm-usage"])
        pg = br.new_page(viewport={"width": 1024, "height": 768})
        eye = Eye(pg, os.path.join(BASE, "shots"))
        hand = Hand(pg)
        t0 = time.time()
        if os.path.exists(TPZ):
            z = np.load(TPZ, allow_pickle=True)
            eye.tpl = {k: z[k] for k in z.files}
            got = sorted(eye.tpl.keys())
            diag["templates_built"] = got
            diag["templates_source"] = "cache"
        else:
            got = eye.build_templates()
            np.savez(TPZ, **eye.tpl)
            diag["templates_built"] = got
            diag["templates_source"] = "ocr"
        print("templates:", got, diag["templates_source"], flush=True)

        # ---- 通道一致性: 快速像素通道 vs 慢速 OCR 通道 ----
        if only in ("all", "static"):
            agree, tot = 0, 0
            for sd in (1001, 1002):
                pg.goto(f"{HTML}?seed={sd}&shuffle=0&modal=0")
                pg.wait_for_timeout(150)
                g, p = eye.shot()
                slow = slow_ocr(g)
                modal, fast, nb = eye.look()
                for w in ("ALPHA", "BETA", "GAMMA", "DELTA"):
                    if w in slow and w in fast:
                        tot += 1
                        d = np.hypot(slow[w][0] - fast[w][0], slow[w][1] - fast[w][1])
                        if d < 25:
                            agree += 1
            diag["channel_agreement"] = {"agree": agree, "total": tot,
                                         "rate": agree / tot if tot else None}
            print("channel agreement:", diag["channel_agreement"], flush=True)

        # ---- 主实验 ----
        worlds = [("static", 0, 0.0), ("dynamic", 1, 0.0), ("dynamic+modal", 1, 0.5)]
        worlds = [w for w in worlds if only in ("all", w[0])]
        for (wname, sh, mp) in worlds:
            for k in (1, 2, 4, "open"):
                oks, obss, errs = [], [], []
                for i in range(N):
                    sd = 2000 + i * 53 + (0 if sh == 0 else 11)
                    r = run_trial(pg, eye, hand, sd, sh, mp, k)
                    oks.append(1 if r["ok"] else 0)
                    obss.append(r["obs"])
                    errs.append(r["errors"])
                rec = {"world": wname, "shuffle": sh, "modal": mp, "k": str(k),
                       "n": N, "success": float(np.mean(oks)),
                       "obs_mean": float(np.mean(obss)),
                       "err_mean": float(np.mean(errs))}
                res.append(rec)
                print(f"{wname:>14} k={str(k):>4}  succ={rec['success']:.3f} "
                      f"obs={rec['obs_mean']:.1f} err={rec['err_mean']:.1f}", flush=True)

        # ---- 真实鼠标事件证据 ----
        pg.goto(f"{HTML}?seed=7&shuffle=0&modal=0")
        pg.wait_for_timeout(150)
        modal, pos, nb = eye.look()
        if "BETA" in pos:
            hand.click(pos["BETA"][0], pos["BETA"][1])
        ev = pg.evaluate("window.__events()")
        json.dump(ev, open(os.path.join(BASE, "mouse_events.json"), "w"), indent=1)
        diag["mouse_events"] = len(ev)
        diag["mouse_sample"] = ev[:6]
        diag["elapsed_s"] = round(time.time() - t0, 1)
        br.close()
    out = os.path.join(BASE, f"results_{only}.json")
    json.dump({"results": res, "diag": diag}, open(out, "w"), indent=1)
    print("DONE", out, "elapsed", diag.get("elapsed_s"))
    for r in res:
        print(f"{r['world']:>14} k={r['k']:>4} succ={r['success']:.3f} "
              f"obs={r['obs_mean']:.1f} err={r['err_mean']:.1f}")


if __name__ == "__main__":
    main()

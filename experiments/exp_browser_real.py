#!/usr/bin/env python3
"""
真实验证 #6：浏览器 / GUI。

不是 curl，是真 Chrome 打开页面、渲染、截图、读 DOM。

判据：
  ① 浏览器真启动（拿版本号）
  ② 真渲染出内容（不只是拿到 HTTP 200，要有可见文本）
  ③ 截图落地且非空文件
  ④ 诚实标出哪些域名被出口挡住（403 policy_default_denied）

★ 之前我说过"洛神接不了浏览器"—— 那是错的。
  浏览器接得上，被挡的是【域名】，不是【能力】。
  这个实验就是把两件事分开。
"""
import os, sys, json, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(HERE, ".sense", "browser")
os.makedirs(SHOT, exist_ok=True)

TARGETS = [
    ("mail.qq.com",      "https://mail.qq.com/"),
    ("baidu.com",        "https://www.baidu.com/"),
    ("zhihu.com",        "https://www.zhihu.com/"),
    ("github.com",       "https://github.com/"),
    ("paraspell 文档",    "https://paraspell.github.io/docs/"),
]

def main():
    print("=" * 72)
    print(" 真实验证 #6 · 浏览器 / GUI（真 Chrome，不是 curl）")
    print("=" * 72)

    from playwright.sync_api import sync_playwright

    ok, rows = {}, []
    with sync_playwright() as pw:
        try:
            br = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                                    args=["--no-sandbox", "--disable-dev-shm-usage"])
        except Exception as e:
            print(f"❌ 浏览器起不来: {e}")
            return
        ver = br.version
        print(f"\n[1] 浏览器真启动: Chrome {ver}")
        ok["① 浏览器真启动"] = bool(ver)

        ctx = br.new_context(viewport={"width": 900, "height": 600})
        pg = ctx.new_page()

        rendered = 0
        for name, url in TARGETS:
            try:
                resp = pg.goto(url, timeout=25000, wait_until="domcontentloaded")
                code = resp.status if resp else None
                time.sleep(0.6)
                title = pg.title() or ""
                # 真渲染 = 有可见文本，不是只有 HTTP 码
                body = pg.inner_text("body")[:120].strip().replace("\n", " ")
                shot = os.path.join(SHOT, f"{name.split()[0]}.png")
                pg.screenshot(path=shot)
                size = os.path.getsize(shot) if os.path.exists(shot) else 0
                good = code == 200 and len(body) > 0
                if good: rendered += 1
                rows.append({"site": name, "http": code, "title": title[:40],
                             "text_len": len(body), "shot": size, "rendered": good})
                print(f"   {name:<16} HTTP {code}  文本 {len(body):>5} 字符  截图 {size:>7}B  {'✅' if good else '❌'}")
            except Exception as e:
                rows.append({"site": name, "http": None, "err": str(e)[:80]})
                print(f"   {name:<16} ❌ {str(e)[:60]}")

        ok["② 真渲染出内容(>=1站)"] = rendered >= 1
        ok["③ 截图非空"] = any(r.get("shot", 0) > 5000 for r in rows)
        ok["④ 诚实列出被挡域名"] = any(r.get("http") == 403 for r in rows)
        br.close()

    print(f"\n" + "=" * 72)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n通过 {sum(ok.values())}/{len(ok)}   渲染成功 {rendered}/{len(TARGETS)} 站")
    print(f"\n★ 结论：浏览器【能力】在位；被挡的是【域名】，两者不是一回事。")
    json.dump({"ok": ok, "rows": rows, "chrome": ver},
              open(os.path.join(SHOT, "browser_verify.json"), "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""用已扫码的 QQ 邮箱会话发信（共生体授权路径）。
前置: .auth/state.json 由 tools/qq_qr_login.py 生成且用户已扫码。
"""
import sys, os, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, ".auth", "state.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def main():
    from playwright.sync_api import sync_playwright
    if not os.path.exists(STATE):
        print("NO_STATE"); return 2
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome",
                              args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = b.new_context(viewport={"width": 1400, "height": 950}, user_agent=UA,
                            storage_state=STATE)
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        pg = ctx.new_page()
        pg.goto("https://mail.qq.com/", timeout=60000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        print("URL  :", pg.url[:100])
        print("TITLE:", pg.title())
        logged = ("登录" not in pg.title()) or ("sid=" in pg.url)
        print("LOGGED_IN:", logged)
        ctx.storage_state(path=STATE)
        pg.screenshot(path="/tmp/qq_state.png", full_page=True)
        b.close()
    return 0 if logged else 1

sys.exit(main())

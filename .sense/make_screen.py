from playwright.sync_api import sync_playwright
html = """<!doctype html><html><body style="margin:0;background:#000">
<div style="width:1280px;height:720px;display:flex;align-items:center;justify-content:center;
            font:700 96px monospace;color:#0f0">
  硅基视觉 通路闭合测试 12345
</div></body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1280,"height":720})
    pg.set_content(html)
    pg.screenshot(path="/data/workspace/luoshen-o1/.sense/screen.png")
    b.close()
print("screenshot ok")

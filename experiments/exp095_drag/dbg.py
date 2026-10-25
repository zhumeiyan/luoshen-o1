from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(viewport={"width":1000,"height":300})
    pg.goto("http://127.0.0.1:8899/page.html?mode=honest&gain=1.0"); pg.wait_for_timeout(400)
    pg.evaluate("window.__log=[]; ['mousedown','mousemove','mouseup'].forEach(t=>window.addEventListener(t,e=>window.__log.push([t,e.clientX,typeof e.movementX])))")
    pg.mouse.move(80,175); pg.wait_for_timeout(50)
    pg.mouse.down(); pg.wait_for_timeout(50)
    for i in range(5):
        pg.mouse.move(80+14*(i+1),175); pg.wait_for_timeout(60)
    pg.mouse.up(); pg.wait_for_timeout(100)
    print(pg.evaluate("window.__log.slice(0,10)"))
    print("handle:", pg.evaluate("hx"))
    b.close()

import json, time, os, subprocess, hashlib
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8731"
OUT = "/data/workspace/luoshen-o1/experiments/exp089_agency"
RIGHT_USER = "zhu-meiyan"
RIGHT_PASS = "symbiont-2026"
WRONG_PASS = "WRONG-PASS-XXXX"

results = {}

def fresh(pw, tag):
    """开一个全新浏览器上下文（= 一台干净的机器/一个全新的身体）"""
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                           args=["--no-sandbox", "--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 1024, "height": 768})
    pg = ctx.new_page()
    return b, ctx, pg

def effector_log(pg, tag):
    """看一眼当前页面，记录效应器/感受器读到了什么"""
    try:
        title = pg.title()
    except Exception:
        title = ""
    try:
        body = pg.inner_text("body")[:200]
    except Exception:
        body = ""
    return {"title": title, "body_head": body.replace("\n", " | ")}

with sync_playwright() as pw:

    # ---------- A: 完整鼠标操作 + 正确凭证 ----------
    b, ctx, pg = fresh(pw, "A")
    trace = []
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.wait_for_selector("#u", timeout=8000)
    box_u = pg.locator("#u").bounding_box()
    box_p = pg.locator("#p").bounding_box()
    box_g = pg.locator("#go").bounding_box()
    # 真鼠标：移动 -> 点击 -> 逐字符键入
    pg.mouse.move(box_u["x"] + 5, box_u["y"] + box_u["height"] / 2)
    pg.mouse.click(box_u["x"] + 5, box_u["y"] + box_u["height"] / 2)
    trace.append(("click_u", round(box_u["x"]), round(box_u["y"])))
    pg.keyboard.type(RIGHT_USER, delay=12)
    trace.append(("type_user", len(RIGHT_USER)))
    pg.mouse.move(box_p["x"] + 5, box_p["y"] + box_p["height"] / 2)
    pg.mouse.click(box_p["x"] + 5, box_p["y"] + box_p["height"] / 2)
    trace.append(("click_p", round(box_p["x"]), round(box_p["y"])))
    pg.keyboard.type(RIGHT_PASS, delay=12)
    trace.append(("type_pass", len(RIGHT_PASS)))
    pg.mouse.move(box_g["x"] + box_g["width"] / 2, box_g["y"] + box_g["height"] / 2)
    pg.mouse.click(box_g["x"] + box_g["width"] / 2, box_g["y"] + box_g["height"] / 2)
    trace.append(("click_go", round(box_g["x"]), round(box_g["y"])))
    pg.wait_for_load_state("domcontentloaded")
    time.sleep(0.6)
    read = effector_log(pg, "A")
    entered_A = "APP INTERIOR" in read["body_head"]
    pg.screenshot(path=OUT + "/A_operate_right.png")
    cookie_A = ctx.cookies()
    A_ops = len(trace)
    b.close()

    # ---------- B: 同样的鼠标操作 + 错误凭证 ----------
    b, ctx, pg = fresh(pw, "B")
    traceB = []
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.wait_for_selector("#u", timeout=8000)
    box_u = pg.locator("#u").bounding_box()
    box_p = pg.locator("#p").bounding_box()
    box_g = pg.locator("#go").bounding_box()
    pg.mouse.move(box_u["x"] + 5, box_u["y"] + box_u["height"] / 2)
    pg.mouse.click(box_u["x"] + 5, box_u["y"] + box_u["height"] / 2)
    traceB.append(("click_u", round(box_u["x"]), round(box_u["y"])))
    pg.keyboard.type(RIGHT_USER, delay=12)
    traceB.append(("type_user", len(RIGHT_USER)))
    pg.mouse.move(box_p["x"] + 5, box_p["y"] + box_p["height"] / 2)
    pg.mouse.click(box_p["x"] + 5, box_p["y"] + box_p["height"] / 2)
    traceB.append(("click_p", round(box_p["x"]), round(box_p["y"])))
    pg.keyboard.type(WRONG_PASS, delay=12)
    traceB.append(("type_pass", len(WRONG_PASS)))
    pg.mouse.move(box_g["x"] + box_g["width"] / 2, box_g["y"] + box_g["height"] / 2)
    pg.mouse.click(box_g["x"] + box_g["width"] / 2, box_g["y"] + box_g["height"] / 2)
    traceB.append(("click_go", round(box_g["x"]), round(box_g["y"])))
    pg.wait_for_load_state("domcontentloaded")
    time.sleep(0.6)
    read = effector_log(pg, "B")
    entered_B = "APP INTERIOR" in read["body_head"]
    pg.screenshot(path=OUT + "/B_operate_wrong.png")
    B_ops = len(traceB)
    b.close()

    # ---------- C: 零操作 + 正确凭证（直接持 session 访问） ----------
    sess = hashlib.sha256(RIGHT_USER.encode()).hexdigest()[:16]
    b, ctx, pg = fresh(pw, "C")
    ctx.add_cookies([{"name": "session", "value": sess,
                      "domain": "127.0.0.1", "path": "/"}])
    pg.goto(BASE + "/app", wait_until="domcontentloaded")
    time.sleep(0.5)
    read = effector_log(pg, "C")
    entered_C = "APP INTERIOR" in read["body_head"]
    pg.screenshot(path=OUT + "/C_zeroop_right.png")
    C_ops = 0
    b.close()

    # ---------- D: 零操作 + 无凭证 ----------
    b, ctx, pg = fresh(pw, "D")
    pg.goto(BASE + "/app", wait_until="domcontentloaded")
    time.sleep(0.5)
    read = effector_log(pg, "D")
    entered_D = "APP INTERIOR" in read["body_head"]
    pg.screenshot(path=OUT + "/D_zeroop_none.png")
    D_ops = 0
    b.close()

# ---------- E: 换一个完全不同的身体（curl，非浏览器）持同一凭证 ----------
r = subprocess.run(["curl", "-s", "-o", "/tmp/e.html", "-w", "%{http_code}",
                    "-H", "Cookie: session=" + sess, BASE + "/app"],
                   capture_output=True, text=True)
code_E = r.stdout.strip()
body_E = open("/tmp/e.html", encoding="utf-8", errors="ignore").read()
entered_E = "APP INTERIOR" in body_E

# ---------- F: 伪造凭证（不是服务器签发的） ----------
r = subprocess.run(["curl", "-s", "-o", "/tmp/f.html", "-w", "%{http_code}",
                    "-H", "Cookie: session=deadbeefdeadbeef", BASE + "/app"],
                   capture_output=True, text=True)
code_F = r.stdout.strip()
body_F = open("/tmp/f.html", encoding="utf-8", errors="ignore").read()
entered_F = "APP INTERIOR" in body_F

out = {
    "A_operate_right_cred":   {"ops": A_ops, "entered": bool(entered_A)},
    "B_operate_wrong_cred":   {"ops": B_ops, "entered": bool(entered_B)},
    "C_zeroop_right_cred":    {"ops": C_ops, "entered": bool(entered_C)},
    "D_zeroop_no_cred":       {"ops": D_ops, "entered": bool(entered_D)},
    "E_otherbody_curl_cred":  {"http": code_E, "entered": entered_E},
    "F_forged_cred":          {"http": code_F, "entered": entered_F},
}
out["A_trace"] = trace
out["B_trace"] = traceB
out["A_ops"] = A_ops
out["B_ops"] = B_ops
out["same_action_sequence"] = (A_ops == B_ops)

print(json.dumps(out, ensure_ascii=False, indent=2))
json.dump(out, open(OUT + "/result_089.json", "w"), ensure_ascii=False, indent=2)

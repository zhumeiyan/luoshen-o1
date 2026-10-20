# -*- coding: utf-8 -*-
"""
全通道打通自检 —— 按感官跑，不按拼写跑。

    python3 全通道自检.py
    python3 全通道自检.py --quiet     # 只报断的
"""
import os, sys, json, base64, urllib.request, threading, time
import importlib.util, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import channels

PORT = int(os.environ.get("LUOSHEN_PORT", "8765"))
SKILL_ZIP = ("https://raw.githubusercontent.com/KLameng/"
             "TACT-Three-Axis-Check/main/install/tact-skill-package-v1.2.1.zip")


def boot():
    os.environ["LUOSHEN_HOST"] = "http://127.0.0.1:%d" % PORT
    spec = importlib.util.spec_from_file_location("srv", os.path.join(ROOT, "serve.py"))
    m = importlib.util.module_from_spec(spec)
    sys.argv = ["serve.py", str(PORT)]
    m.PORT = PORT
    spec.loader.exec_module(m)
    srv = m.TS(("127.0.0.1", PORT), m.API)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(2)
    return srv


def post(name, body=None, t=200):
    b = json.dumps(body if body is not None else {}).encode()
    r = urllib.request.Request("http://127.0.0.1:%d/api/run/%s" % (PORT, name),
                               data=b, headers={"Content-Type": "application/json"},
                               method="POST")
    try:
        return json.loads(urllib.request.urlopen(r, timeout=t).read())
    except Exception as e:
        return {"ok": False, "断连": repr(e)[:100]}


def main():
    quiet = "--quiet" in sys.argv
    print("=== 全通道打通自检（按感官）===" if not quiet else "=== 只报断的 ===")
    srv = boot()

    png = None
    try:
        from PIL import Image
        Image.new("RGB", (40, 30), (255, 107, 26)).save("/tmp/_ch.png")
        png = "data:image/png;base64," + base64.b64encode(
            open("/tmp/_ch.png", "rb").read()).decode()
    except Exception:
        pass

    # 按感官给每个通道喂它该吃的那种东西
    FEED = {
        "image":   {"b64": png} if png else {},
        "fetch":   {"spec": "https://www.qq.com"},
        "console": {},
        "voice":   {},
        "ask":     {"text": "控制台"},
        "verify":  {},
        "scan":    {"text": "print(1)"},
        "prove":   {"text": "感官自检判据"},
        "skill":   {"spec": SKILL_ZIP},
        "api":     {"spec": "https://api.github.com/rate_limit"},
        "ingest":  {"kind": "text", "text": "感官自检"},
    }

    rows = []
    for s, desc, caveat in channels.SENSES:
        if not quiet:
            print("\n  [%s] %s" % (s, desc))
        for e, zh, ss, form, gain, st in channels.CHANNELS:
            if ss != s: continue
            if e in ("deliver", "inbox"):
                continue  # 这两条走凭据，下面单独跑
            d = post(e, FEED.get(e, {}))
            if "断连" in d:
                ok, note = False, d["断连"]
            elif st == "无":
                # 没这个感官：要求如实报无并回话，不许崩、不许装活
                ok = isinstance(d, dict) and "通道" in d
                note = "如实报无：" + str(d.get("说明", ""))[:44]
            else:
                ok = bool(d.get("ok")) or "未听懂" in d
                keys = [k for k in ("通过", "总数", "rc", "字节", "尺寸",
                                    "已收", "文件数", "哈希") if k in d]
                note = " ".join("%s=%s" % (k, str(d[k])[:12]) for k in keys[:3]) or str(d)[:38]
            rows.append((e, zh, s, st, ok, note))
            if ok and quiet: continue
            print("    %s %-8s %-7s [%s] %s" % ("✅" if ok else "❌", e, zh, st, note))

    # 手/记：投递 + 收件箱（带凭据，走 client.py）
    for cmd, label in [("投递", "deliver"), ("收件", "inbox")]:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "client.py"), cmd,
                            '{"感官自检":"%s"}' % label],
                           capture_output=True, text=True, timeout=200)
        ok = r.returncode == 0 and r.stdout.strip().startswith("{")
        note = (r.stdout.strip().replace("\n", " ")[:66] if ok
                else (r.stderr or r.stdout).strip()[:66])
        rows.append((label, cmd, "手" if label == "deliver" else "记", "有", ok, note))
        if ok and quiet: continue
        print("    %s %-8s %-7s [有] %s" % ("✅" if ok else "❌", label, cmd, note))

    ok_n = sum(1 for r in rows if r[4])
    print("\n=== 结论 ===")
    print("  通 %d / 共 %d" % (ok_n, len(rows)))
    bad = [r for r in rows if not r[4]]
    if bad:
        for e, zh, s, st, _, note in bad:
            print("  ❌ [%s] %s %s → %s" % (s, e, zh, note))
    else:
        print("  全通 —— 没有一条是断的")
    # 按感官汇总
    print("\n=== 按感官汇总 ===")
    for s, desc, _ in channels.SENSES:
        g = [r for r in rows if r[2] == s]
        if not g: continue
        n_ok = sum(1 for r in g if r[4])
        miss = [r[1] for r in g if r[3] != "有"]
        print("  %s %s  %d/%d%s" % (s, "✅" if n_ok == len(g) else "❌", n_ok, len(g),
                                    ("  缺感官:" + "、".join(miss)) if miss else ""))
    srv.shutdown()
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())

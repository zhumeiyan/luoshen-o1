import http.server, socketserver, urllib.parse, hashlib, threading, json, time

PORT = 8731
RIGHT = ("zhu-meiyan", "symbiont-2026")   # 正确凭证
LOG = []

PAGE_LOGIN = """<!doctype html><html><head><meta charset="utf-8"><title>LOGIN GATE</title></head>
<body style="font-family:monospace;background:#111;color:#eee;padding:40px">
<h1>LOGIN GATE</h1>
<form method="POST" action="/login">
<label>USER <input id="u" name="u" type="text"></label><br><br>
<label>PASS <input id="p" name="p" type="password"></label><br><br>
<button id="go" type="submit">ENTER</button>
</form></body></html>"""

def page_app(user, note=""):
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>APP</title></head>
<body style="font-family:monospace;background:#0a2a0a;color:#cfc;padding:40px">
<h1>APP INTERIOR</h1>
<div>SESSION HOLDER: <b>{user}</b></div>
<div>SECRET: <b>{note}</b></div>
<div id="token">TOKEN-9F31</div>
</body></html>"""

def page_denied():
    return """<!doctype html><html><head><meta charset="utf-8"><title>DENIED</title></head>
<body style="font-family:monospace;background:#2a0a0a;color:#fcc;padding:40px">
<h1>403 DENIED</h1><div>NO SESSION</div></body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, cookie=None):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(b)

    def _cookie_user(self):
        c = self.headers.get("Cookie", "")
        for kv in c.split(";"):
            kv = kv.strip()
            if kv.startswith("session="):
                u = kv[len("session="):]
                if u == hashlib.sha256(RIGHT[0].encode()).hexdigest()[:16]:
                    return RIGHT[0]
        return None

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        LOG.append(("GET", p, self.headers.get("Cookie", "")[:24]))
        if p in ("/", "/login"):
            self._send(200, PAGE_LOGIN)
        elif p == "/app":
            u = self._cookie_user()
            if u:
                self._send(200, page_app(u, "SHARED-WORLD-OK"))
            else:
                self._send(403, page_denied())
        elif p == "/log":
            self._send(200, "<pre>" + json.dumps(LOG, ensure_ascii=False) + "</pre>")
        else:
            self._send(404, "nope")

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n).decode()
        f = urllib.parse.parse_qs(raw)
        u = f.get("u", [""])[0]
        pw = f.get("p", [""])[0]
        ok = (u == RIGHT[0] and pw == RIGHT[1])
        LOG.append(("POST", p, "cred_ok=%s" % ok))
        if ok:
            self._send(200, page_app(u, "SHARED-WORLD-OK"),
                       cookie="session=" + hashlib.sha256(u.encode()).hexdigest()[:16] + "; Path=/")
        else:
            self._send(403, page_denied())

socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("127.0.0.1", PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print("serving on", PORT, flush=True)
while True:
    time.sleep(1)

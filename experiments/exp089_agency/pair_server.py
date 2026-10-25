"""复现扫码登录的协议结构：challenge 由服务器签发，只能被『已持有凭证的一方』批准。"""
import http.server, socketserver, urllib.parse, hashlib, threading, json, time, secrets

PORT = 8732
RIGHT = ("zhu-meiyan", "symbiont-2026")
CH = {}          # challenge -> status
LOG = []

def sess_of(u):
    return hashlib.sha256(u.encode()).hexdigest()[:16]

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

    def authed(self):
        c = self.headers.get("Cookie", "")
        for kv in c.split(";"):
            kv = kv.strip()
            if kv.startswith("session="):
                if kv[len("session="):] == sess_of(RIGHT[0]):
                    return RIGHT[0]
        return None

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path
        q = urllib.parse.parse_qs(u.query)

        if p == "/pair/new":
            # 任何人都可申请一个 challenge —— 这就是二维码
            c = secrets.token_hex(4).upper()
            CH[c] = "pending"
            LOG.append(("new", c, "by=%s" % (self.authed() or "anonymous")))
            self._send(200, json.dumps({"challenge": c, "status": "pending"}))

        elif p == "/pair/approve":
            # 批准必须由已持有凭证的一方发出 —— 这就是手机 QQ 扫码那一步
            c = q.get("c", [""])[0]
            who = self.authed()
            if not who:
                LOG.append(("approve", c, "REJECTED no-session"))
                self._send(403, json.dumps({"ok": False, "reason": "NO SESSION — approver must already hold credential"}))
            elif c in CH:
                CH[c] = "granted"
                LOG.append(("approve", c, "GRANTED by=%s" % who))
                self._send(200, json.dumps({"ok": True, "status": "granted"}))
            else:
                self._send(404, json.dumps({"ok": False, "reason": "no such challenge"}))

        elif p == "/pair/status":
            c = q.get("c", [""])[0]
            self._send(200, json.dumps({"challenge": c, "status": CH.get(c, "unknown")}))

        elif p == "/login":
            # 拿凭证的唯一入口
            self._send(200, "OK", cookie="session=" + sess_of(RIGHT[0]) + "; Path=/")

        elif p == "/log":
            self._send(200, "<pre>" + json.dumps(LOG, ensure_ascii=False, indent=1) + "</pre>")
        else:
            self._send(404, "nope")

socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("127.0.0.1", PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print("pair server on", PORT, flush=True)
while True:
    time.sleep(1)

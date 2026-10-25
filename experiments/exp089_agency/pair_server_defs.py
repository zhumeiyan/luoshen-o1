import http.server, urllib.parse, hashlib, json, secrets

RIGHT = ("zhu-meiyan", "symbiont-2026")
CH = {}
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
        p, q = u.path, urllib.parse.parse_qs(u.query)

        if p == "/pair/new":
            c = secrets.token_hex(4).upper()
            CH[c] = "pending"
            LOG.append(("new", c, "by=%s" % (self.authed() or "anonymous")))
            self._send(200, json.dumps({"challenge": c, "status": "pending"}))

        elif p == "/pair/approve":
            c = q.get("c", [""])[0]
            who = self.authed()
            if not who:
                LOG.append(("approve", c, "REJECTED no-session"))
                self._send(403, json.dumps(
                    {"ok": False, "reason": "NO SESSION - approver must already hold credential"}))
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
            self._send(200, "OK", cookie="session=" + sess_of(RIGHT[0]) + "; Path=/")

        elif p == "/log":
            self._send(200, "<pre>" + json.dumps(LOG, ensure_ascii=False, indent=1) + "</pre>")

        else:
            self._send(404, "nope")

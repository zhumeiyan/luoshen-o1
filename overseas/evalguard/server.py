"""evalguard HTTP API — stdlib only, no framework, no network call out.

Why this exists
---------------
The Python API covers anything running in-process. It does not cover the
two cases that decide whether a tool gets adopted in a team:

  * a service in another language that wants to check generated code
  * a reviewer who wants a URL, not a pip install

So: an HTTP surface. It is deliberately built on `http.server` with no
dependency, because a scanner that needs a web framework to boot is a
scanner you will not run inside a CI container at 3am.

Security posture, stated plainly: this server is a **local** service. It
binds 127.0.0.1 by default, it accepts POST only on /scan*, it caps the
request body, and it never executes the code it is given -- it parses it
into an AST and reads it. It is not hardened for public exposure and the
`--host 0.0.0.0` flag says so in its help text.

    python3 -m evalguard serve            # http://127.0.0.1:8787
    curl -s localhost:8787/rules | jq
    curl -s localhost:8787/scan -d @body.json
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import scan_paths, scan_source, SEVERITIES, _VERSION, _TOOL_NAME
from .rules import RULES
from .pro_rules import PRO_RULES
from .classes import SYNTAX

MAX_BODY = 4 * 1024 * 1024          # 4 MiB of source is already absurd
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787


def _rule_rows():
    rows = []
    for fn in list(RULES) + list(PRO_RULES):
        m = getattr(fn, "meta", {}) or {}
        eid = m.get("eg_id")
        if not eid:
            continue
        rows.append({
            "eg_id": eid,
            "title": m.get("title", ""),
            "severity": m.get("severity", "info"),
            "why": m.get("why", ""),
            "fix": m.get("fix", ""),
            "canon": m.get("canon", []),
            "pro": fn in PRO_RULES,
            "shipped": eid in SYNTAX,
        })
    return rows


def _do_scan(payload: dict):
    pro = bool(payload.get("pro", False))
    if "source" in payload:
        res = scan_source(payload["source"],
                          path=payload.get("path", "<string>"), pro=pro)
    elif "paths" in payload:
        res = scan_paths(payload["paths"], pro=pro)
    elif "path" in payload:
        res = scan_paths([payload["path"]], pro=pro)
    else:
        return None, {"error": "provide one of: source | path | paths"}
    sev = payload.get("severity")
    if sev in SEVERITIES:
        res = res.limit(sev)
    return res, None


class Handler(BaseHTTPRequestHandler):
    server_version = f"{_TOOL_NAME}/{_VERSION}"
    # Default is HTTP/1.0 and a chatty version string. Quiet the log noise
    # but keep errors: a scanner that fails silently in CI is the failure
    # mode this whole project exists to catch.

    def log_message(self, fmt, *args):
        if "POST /scan" in (fmt % args) or "GET /" in (fmt % args):
            return
        super().log_message(fmt, *args)

    # ---- helpers --------------------------------------------------------
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Tool", f"{_TOOL_NAME} {_VERSION}")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        if n > MAX_BODY:
            raise ValueError(f"body too large: {n} > {MAX_BODY}")
        return json.loads(self.rfile.read(n).decode("utf-8"))

    # ---- routes ---------------------------------------------------------
    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/") or "/"
        if p == "/":
            self._send(200, {
                "tool": _TOOL_NAME, "version": _VERSION,
                "endpoints": {
                    "GET /health": "liveness + rule counts",
                    "GET /rules": "the rule catalogue, with shipped flags",
                    "POST /scan": "body {source|path|paths, pro?, severity?}",
                    "POST /scan/sarif": "same, returns SARIF 2.1.0",
                },
                "note": "local service; parses the code it is given, never runs it",
            })
        elif p == "/health":
            self._send(200, {"ok": True, "tool": _TOOL_NAME,
                             "version": _VERSION,
                             "rules": len(_rule_rows())})
        elif p == "/rules":
            rows = _rule_rows()
            self._send(200, {"count": len(rows), "rules": rows})
        else:
            self._send(404, {"error": f"no such endpoint: {p}"})

    def do_POST(self):
        p = self.path.split("?")[0].rstrip("/") or "/"
        if p not in ("/scan", "/scan/sarif"):
            self._send(404, {"error": f"no such endpoint: {p}"})
            return
        try:
            payload = self._body()
        except ValueError as e:
            self._send(400, {"error": f"bad request body: {e}"})
            return
        except json.JSONDecodeError as e:
            self._send(400, {"error": f"invalid JSON: {e}"})
            return
        try:
            res, err = _do_scan(payload)
        except Exception as e:                       # never 500 on user input
            self._send(400, {"error": f"{type(e).__name__}: {e}"})
            return
        if err:
            self._send(400, err)
            return
        if p == "/scan/sarif":
            self._send(200, res.to_sarif())
        else:
            self._send(200, res.to_dict())


def serve(host=DEFAULT_HOST, port=DEFAULT_PORT, block=True):
    """Start the API. Returns (server, url); caller may .shutdown()."""
    srv = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    if block:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            srv.server_close()
    return srv, url


def serve_background(host=DEFAULT_HOST, port=DEFAULT_PORT):
    srv, url = serve(host, port, block=False)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, url, t

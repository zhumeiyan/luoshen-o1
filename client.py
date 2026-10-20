# -*- coding: utf-8 -*-
"""
洛神 O1 · 客户端

服务端负责"接"，这个负责"发"。两端配对，缺一不可。

    python3 client.py ping
    python3 client.py 发文本 "内容"
    python3 client.py 发图片 路径.png
    python3 client.py 发文件 路径.pdf
    python3 client.py 发事件 '{"type":"xxx"}'
    python3 client.py 抓取 https://example.com
    python3 client.py 装skill <zip路径或URL>
    python3 client.py 调API https://httpbin.org/get
"""
import sys, os, json, base64, urllib.request

HOST = os.environ.get("LUOSHEN_HOST", "http://127.0.0.1:8765")
TIMEOUT = 180


def post(path, body):
    r = urllib.request.Request(HOST + path,
                               data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"},
                               method="POST")
    try:
        x = urllib.request.urlopen(r, timeout=TIMEOUT)
        return json.loads(x.read())
    except urllib.error.URLError as e:
        return {"ok": False, "连不上": HOST,
                "说明": "服务端没起。跑 python3 serve.py", "详情": repr(e)[:150]}
    except Exception as e:
        return {"ok": False, "err": repr(e)[:200]}


def get(path):
    try:
        return json.loads(urllib.request.urlopen(HOST + path, timeout=60).read())
    except Exception as e:
        return {"ok": False, "err": repr(e)[:150]}


def b64_of(p):
    ext = os.path.splitext(p)[1].lstrip(".") or "bin"
    return "data:application/octet-stream;base64," + \
        base64.b64encode(open(p, "rb").read()).decode(), ext


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]

    if cmd == "ping":
        print(json.dumps(get("/api/health"), ensure_ascii=False, indent=1))
    elif cmd == "清单":
        print(json.dumps(get("/api/manifest"), ensure_ascii=False, indent=1))
    elif cmd == "发文本":
        print(json.dumps(post("/api/run/ingest", {"kind": "text",
              "text": sys.argv[2]}), ensure_ascii=False, indent=1))
    elif cmd in ("发图片", "发文件"):
        b, ext = b64_of(sys.argv[2])
        print(json.dumps(post("/api/run/ingest", {
              "kind": "image" if cmd == "发图片" else "file",
              "b64": b, "ext": ext}), ensure_ascii=False, indent=1))
    elif cmd == "发事件":
        print(json.dumps(post("/api/run/ingest", {
              "kind": "event", "text": sys.argv[2]}), ensure_ascii=False, indent=1))
    elif cmd == "抓取":
        print(json.dumps(post("/api/run/fetch", {"spec": sys.argv[2]}),
                         ensure_ascii=False, indent=1)[:1200])
    elif cmd == "装skill":
        print(json.dumps(post("/api/run/skill", {"spec": sys.argv[2]}),
                         ensure_ascii=False, indent=1))
    elif cmd == "调API":
        spec = sys.argv[2]
        if len(sys.argv) > 3 and sys.argv[3].upper() == "POST":
            spec = json.dumps({"url": sys.argv[2], "method": "POST",
                               "body": json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}})
        print(json.dumps(post("/api/run/api", {"spec": spec}),
                         ensure_ascii=False, indent=1)[:1200])
    else:
        print("未知命令：" + cmd); print(__doc__)


if __name__ == "__main__":
    main()

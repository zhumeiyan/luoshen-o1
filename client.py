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
    python3 client.py 投递 '{"text":"随便什么"}'
    python3 client.py 收件 remote
"""
import sys, os, json, base64, urllib.request, urllib.error, time, hashlib, datetime
import urllib.parse

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


# ── 远程常驻收件箱：GitHub 仓库当接收端（进程会死，仓库不会）──────
REPO = os.environ.get("LUOSHEN_REPO", "zhumeiyan/luoshen-o1")
GHTOK = os.environ.get("GH_TOKEN", "")
API = "https://api.github.com"


def gh(path, method="GET", body=None):
    r = urllib.request.Request(API + urllib.parse.quote(path, safe="/"), method=method)
    r.add_header("User-Agent", "luoshen-client")
    r.add_header("Accept", "application/vnd.github+json")
    if GHTOK: r.add_header("Authorization", "token " + GHTOK)
    b = json.dumps(body).encode() if body is not None else None
    if b: r.add_header("Content-Type", "application/json")
    try:
        x = urllib.request.urlopen(r, b, timeout=120)
        return x.status, json.loads(x.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except Exception as e:
        return 0, {"err": repr(e)[:150]}


def deliver(payload):
    """投递到常驻收件箱。任何能发 HTTP 的客户端都能用。"""
    if not GHTOK:
        return {"ok": False, "未实现": "需要 GH_TOKEN 环境变量（客户端自带凭据）"}
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    rec = {"ts": ts, "from": os.environ.get("LUOSHEN_FROM", "unknown"),
           "payload": payload}
    txt = json.dumps(rec, ensure_ascii=False, indent=1)
    rem = "接收/inbox/%s.json" % ts
    st, d = gh("/repos/%s/contents/%s" % (REPO, rem), "PUT",
               {"message": "inbox: %s" % ts,
                "content": base64.b64encode(txt.encode()).decode()})
    if st in (200, 201):
        return {"ok": True, "引擎": "deliver", "落点": rem,
                "sha256": hashlib.sha256(txt.encode()).hexdigest()[:16],
                "说明": "已进常驻收件箱，服务端进程死了也在"}
    return {"ok": False, "rc": st, "err": str(d)[:200]}


def read_inbox(mode="remote"):
    """收件。remote=读仓库（常驻），local=读本地目录。"""
    if mode == "local":
        d = "接收/inbox"
        fs = sorted(os.listdir(d)) if os.path.isdir(d) else []
        return {"ok": True, "mode": "local", "条数": len(fs), "文件": fs[:20]}
    st, d = gh("/repos/%s/contents/接收/inbox" % REPO)
    if st != 200:
        return {"ok": False, "rc": st, "err": str(d)[:150]}
    names = [x["name"] for x in d if x["name"].endswith(".json")]
    items = []
    for n in sorted(names)[-10:]:
        st2, f = gh("/repos/%s/contents/接收/inbox/%s" % (REPO, n))
        if st2 == 200 and "content" in f:
            try:
                items.append(json.loads(base64.b64decode(f["content"]).decode()))
            except Exception:
                pass
    return {"ok": True, "mode": "remote", "总数": len(names),
            "最近": items[-5:]}


def b64_of(p):
    ext = os.path.splitext(p)[1].lstrip(".") or "bin"
    return "data:application/octet-stream;base64," + \
        base64.b64encode(open(p, "rb").read()).decode(), ext


try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import channels
except Exception:
    channels = None


def _route(cmd):
    """接统一注册表：中英文都认，指向同一通道。

    之前客户端说中文、服务端说英文，两边各说各话——
    那不是名字不统一，是通道真的没接上。
    """
    if channels is None: return None
    return channels.resolve(cmd)


def call_channel(cmd, arg=None):
    """客户端喊中文，也能打到服务端引擎。"""
    name = _route(cmd)
    if not name or channels is None:
        return None
    form = channels.arg_field(name)
    if form == "无参":
        body = {}
    elif form == "b64":
        body = {"b64": arg}
    elif form == "kind":
        body = {"kind": "text", "text": arg}
    elif form == "payload":
        body = {"payload": arg}
    else:
        body = {"text": arg} if form == "text" else {"spec": arg}
    return post("/api/run/" + name, body)


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]

    if cmd == "投递":
        print(json.dumps(deliver(json.loads(sys.argv[2])), ensure_ascii=False, indent=1))
    elif cmd == "收件":
        print(json.dumps(read_inbox(sys.argv[2] if len(sys.argv) > 2 else "remote"),
                         ensure_ascii=False, indent=1)[:1500])
    elif cmd == "ping":
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
        arg = sys.argv[2] if len(sys.argv) > 2 else None
        r = call_channel(cmd, arg)
        if r is None:
            print("未知命令：" + cmd)
            if channels:
                print("可用通道：" + "、".join("%s/%s" % (c[0], c[1]) for c in channels.CHANNELS))
            return
        print(json.dumps(r, ensure_ascii=False, indent=1)[:1500])


if __name__ == "__main__":
    main()

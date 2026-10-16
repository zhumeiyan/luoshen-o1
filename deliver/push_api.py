#!/usr/bin/env python3
"""通过 GitHub Git Data API 推送文件（沙盒内 git push 被代理拦截时的替代通道）。

用法:
    python3 deliver/push_api.py "文件路径" "文件路径2" ... --msg "提交说明"

环境变量 GITHUB_TOKEN 或 ~/.gh_token 提供令牌。
"""
import base64, json, os, sys, urllib.error, urllib.request

REPO = "zhumeiyan/luoshen-o1"
BRANCH = "main"
API = "https://api.github.com"


def token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t.strip()
    p = os.path.expanduser("~/.gh_token")
    if os.path.exists(p):
        return open(p).read().strip()
    sys.exit("缺少令牌：设置 GITHUB_TOKEN 或写入 ~/.gh_token")


def api(path, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": "Bearer " + token(), "User-Agent": "push-api",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=120).read()
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s %s\n%s" % (e.code, path, e.read()[:600].decode("utf-8", "ignore")))


def main():
    msg = "更新文件"
    args, skip = [], False
    for a in sys.argv[1:]:
        if skip:
            skip = False
            continue
        if a == "--msg":
            skip = True
            continue
        if a.startswith("--"):
            continue
        args.append(a)
    for i, a in enumerate(sys.argv):
        if a == "--msg" and i + 1 < len(sys.argv):
            msg = sys.argv[i + 1]
    if not args:
        sys.exit("用法: push_api.py <文件...> [--msg 说明]")

    # 1) 当前分支 head
    head = api("/repos/%s/git/ref/heads/%s" % (REPO, BRANCH))["object"]["sha"]
    base_tree = api("/repos/%s/git/commits/%s" % (REPO, head))["tree"]["sha"]

    # 2) 为每个文件建 blob
    tree = []
    for f in args:
        if not os.path.exists(f):
            sys.exit("文件不存在: " + f)
        content = open(f, "rb").read()
        blob = api("/repos/%s/git/blobs" % REPO, "POST",
                   {"content": base64.b64encode(content).decode(), "encoding": "base64"})
        tree.append({"path": f.replace(os.sep, "/"), "mode": "100755" if os.access(f, os.X_OK) else "100644",
                     "type": "blob", "sha": blob["sha"]})
        print("blob  %-46s %8d bytes" % (f, len(content)))

    # 3) 建 tree / commit / 更新 ref
    new_tree = api("/repos/%s/git/trees" % REPO, "POST", {"base_tree": base_tree, "tree": tree})
    commit = api("/repos/%s/git/commits" % REPO, "POST",
                 {"message": msg, "tree": new_tree["sha"], "parents": [head]})
    api("/repos/%s/git/refs/heads/%s" % (REPO, BRANCH), "PATCH", {"sha": commit["sha"]})
    print("\n推送完成: %s" % commit["sha"][:8])
    print("https://github.com/%s/commit/%s" % (REPO, commit["sha"]))


if __name__ == "__main__":
    main()

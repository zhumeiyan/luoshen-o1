# -*- coding: utf-8 -*-
"""
白模预演层 —— 对标 TapNow 3D 片场「先排一遍戏」。

在昂贵动作（推 GitHub / 生成成品）之前，先用零成本把错误排出来。
理由：白模里改一个机位的成本，和成片渲染完再改，不是一个量级。

    python3 preflight.py 文件1 文件2 ...     # 预演，不推送
"""
import os, sys, json, base64, urllib.request, urllib.error, urllib.parse, re

REPO = "zhumeiyan/luoshen-o1"
TOK = os.environ.get("GH_TOKEN", "")
CHECKS = []

def ck(name):
    def deco(f):
        CHECKS.append((name, f)); return f
    return deco

@ck("文件存在")
def _c1(path):
    if not os.path.isfile(path): return False, "不存在"
    return True, "%d B" % os.path.getsize(path)

@ck("路径可编码")
def _c2(path):
    rem = os.path.relpath(path, os.getcwd())
    try:
        urllib.parse.quote(rem, safe="/"); return True, rem
    except Exception as e:
        return False, repr(e)[:60]

@ck("内容可 base64")
def _c3(path):
    try:
        base64.b64encode(open(path, "rb").read()); return True, "ok"
    except Exception as e:
        return False, repr(e)[:60]

@ck("语法可解析")
def _c4(path):
    if not path.endswith(".py"): return None, "非 py，跳过"
    try:
        import ast; ast.parse(open(path, encoding="utf-8").read()); return True, "ast ok"
    except SyntaxError as e:
        return False, "行%d: %s" % (e.lineno or 0, (e.msg or "")[:50])
    except Exception as e:
        return False, repr(e)[:50]

@ck("HTML 内联 style")
def _c5(path):
    if not path.endswith(".html"): return None, "非 html，跳过"
    s = open(path, encoding="utf-8", errors="ignore").read()
    n = len(re.findall(r"<style", s, re.I))
    if n == 0: return True, "无内联（不会被盖）"
    return False, "%d 处内联 <style>，会盖掉 theme.css" % n

@ck("凭据有效")
def _c6(path):
    if not TOK: return False, "GH_TOKEN 未透传（不是没有，是没传进来）"
    try:
        r = urllib.request.Request("https://api.github.com/user",
                                   headers={"User-Agent": "x", "Authorization": "token " + TOK})
        who = json.loads(urllib.request.urlopen(r, timeout=45).read()).get("login", "?")
        return True, "身份=" + who
    except Exception as e:
        return False, repr(e)[:60]

@ck("远端 sha 可取")
def _c7(path):
    rem = os.path.relpath(path, os.getcwd())
    if not TOK: return None, "无凭据，跳过"
    try:
        u = "https://api.github.com/repos/%s/contents/%s" % (REPO, urllib.parse.quote(rem, safe="/"))
        r = urllib.request.Request(u, headers={"User-Agent": "x", "Authorization": "token " + TOK})
        x = urllib.request.urlopen(r, timeout=45)
        sha = json.loads(x.read()).get("sha", "")
        return True, "已存在，sha=" + sha[:12] + "（带 sha 才不会 409）"
    except urllib.error.HTTPError as e:
        if e.code == 404: return True, "远端不存在 → 新建（不会冲突）"
        return False, "rc=%d" % e.code
    except Exception as e:
        return False, repr(e)[:60]

@ck("内容有变化")
def _c8(path):
    rem = os.path.relpath(path, os.getcwd())
    if not TOK: return None, "无凭据，跳过"
    try:
        u = "https://api.github.com/repos/%s/contents/%s" % (REPO, urllib.parse.quote(rem, safe="/"))
        r = urllib.request.Request(u, headers={"User-Agent": "x", "Authorization": "token " + TOK})
        d = json.loads(urllib.request.urlopen(r, timeout=45).read())
        if "content" not in d: return None, "无 content"
        old = base64.b64decode(d["content"])
        new = open(path, "rb").read()
        return (True, "一致，无需推") if old == new else (True, "有变化 %dB→%dB" % (len(old), len(new)))
    except urllib.error.HTTPError as e:
        if e.code == 404: return True, "新文件"
        return None, "rc=%d，跳过" % e.code
    except Exception as e:
        return None, repr(e)[:50]

def run(paths):
    print("=== 白模预演（不推送，只排错）===")
    bad = []
    for p in paths:
        print("\n── %s" % os.path.relpath(p, os.getcwd()))
        for name, f in CHECKS:
            try: ok, msg = f(p)
            except Exception as e: ok, msg = False, repr(e)[:60]
            if ok is None: mark = "  ·"
            elif ok: mark = "  ✓"
            else: mark = "  ✗"; bad.append((p, name, msg))
            print("%s %-14s %s" % (mark, name, msg))
    print("\n=== 预演结论 ===")
    if bad:
        for p, n, m in bad: print("  ✗ %s :: %s → %s" % (os.path.relpath(p, os.getcwd()), n, m))
        print("  共 %d 处会穿帮，先改再推" % len(bad)); return 1
    print("  0 处穿帮，可以推"); return 0

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))

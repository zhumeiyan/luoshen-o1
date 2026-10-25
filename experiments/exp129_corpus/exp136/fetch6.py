"""corpus6 — POST-HOC (not preregistered).

exp136 H1 predicted non-eval code would fire more often than eval
frameworks. It fired LESS (0.0093 vs 0.024/KB). But looking at why, every
one of the 9 pruned findings was `except Exception` in a mature library,
three of them carrying `# pylint: disable=broad-except` — the author had
already met a linter and explicitly suppressed it.

That reframes it: all four corpora so far are mature, high-star projects
that already have lint culture. We have never measured the tool on the
kind of code that does not. This corpus tests that, post-hoc, and is
labelled as such.
"""
import json, subprocess, pathlib, base64, random

TOK = pathlib.Path("/data/workspace/luoshen-o1/.auth/gh_token").read_text().strip()
OUT = pathlib.Path("corpus6"); OUT.mkdir(exist_ok=True)
EXCL = ("test","__init__","vendor","contrib","example","compat","_compat","migrations")

def gh(p):
    r = subprocess.run(["curl","-s","-H",f"Authorization: Bearer {TOK}",
        "-H","Accept: application/vnd.github+json",
        f"https://api.github.com{p}"], capture_output=True, text=True, timeout=60)
    try: return json.loads(r.stdout)
    except Exception: return None

q = "language:python+stars:5..150"
s = gh(f"/search/repositories?q={q}&sort=updated&order=desc&per_page=40")
items = s.get("items", []) if isinstance(s, dict) else []
print("search hits", len(items))

rng = random.Random(1360)
picked = []
for it in items:
    full = it["full_name"]; br = it.get("default_branch","main")
    if len(picked) >= 14: break
    t = gh(f"/repos/{full}/git/trees/{br}?recursive=1")
    if not isinstance(t, dict) or "tree" not in t: continue
    c = [x for x in t["tree"] if x["type"]=="blob" and x["path"].endswith(".py")
         and not any(k in x["path"].lower() for k in EXCL)
         and 2000 <= x.get("size",0) <= 30000]
    if not c: continue
    rng.shuffle(c)
    got = 0
    for x in c[:2]:
        f = gh(f"/repos/{full}/contents/{x['path']}?ref={br}")
        if not isinstance(f, dict) or "content" not in f: continue
        try: src = base64.b64decode(f["content"]).decode("utf-8")
        except Exception: continue
        if "def " not in src and "class " not in src: continue
        name = full.replace("/","__")+"__"+x["path"].replace("/","_")
        (OUT/name).write_text(src)
        picked.append({"repo":full,"stars":it.get("stargazers_count"),
                       "path":x["path"],"file":name,"bytes":len(src.encode())})
        got += 1
    if got: print(f"[{full}] stars={it.get('stargazers_count')} +{got}")
pathlib.Path("manifest6.json").write_text(json.dumps(picked,indent=1))
print("TOTAL",len(picked),"files",sum(p['bytes'] for p in picked),"bytes")

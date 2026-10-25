import json, subprocess, pathlib, random, base64

TOK = pathlib.Path("/data/workspace/luoshen-o1/.auth/gh_token").read_text().strip()
OUT = pathlib.Path("corpus5"); OUT.mkdir(exist_ok=True)

REPOS = [
 ("psf","requests","main"),
 ("pallets","flask","main"),
 ("scrapy","scrapy","master"),
 ("celery","celery","main"),
 ("httpie","httpie","master"),
 ("yt-dlp","yt-dlp","master"),
 ("fastapi","fastapi","master"),
]

EXCL = ("eval","metric","benchmark","score","test","__init__","vendor",
        "contrib","example","compat","six","_compat")

def gh(path):
    r = subprocess.run(["curl","-s","-H",f"Authorization: Bearer {TOK}",
        "-H","Accept: application/vnd.github+json",
        f"https://api.github.com{path}"], capture_output=True, text=True, timeout=60)
    try: return json.loads(r.stdout)
    except Exception: return None

rng = random.Random(136)
picked = []
for owner,repo,br in REPOS:
    d = gh(f"/repos/{owner}/{repo}/git/trees/{br}?recursive=1")
    if not isinstance(d, dict) or "tree" not in d:
        print(f"[{owner}/{repo}] TREE FAIL {str(d)[:100]}"); continue
    cands = [t for t in d["tree"]
             if t["type"]=="blob" and t["path"].endswith(".py")
             and not any(k in t["path"].lower() for k in EXCL)]
    # prefer substantive files: 3KB..40KB
    cands = [t for t in cands if 3000 <= t.get("size",0) <= 40000]
    print(f"[{owner}/{repo}] py={len([t for t in d['tree'] if t['path'].endswith('.py')])} cands={len(cands)}")
    if not cands: continue
    rng.shuffle(cands)
    for t in cands[:2]:
        f = gh(f"/repos/{owner}/{repo}/contents/{t['path']}?ref={br}")
        if not isinstance(f, dict) or "content" not in f:
            print("   skip",t["path"]); continue
        try:
            src = base64.b64decode(f["content"]).decode("utf-8")
        except Exception as e:
            print("   decode fail",t["path"],e); continue
        name = f"{owner}__{repo}__" + t["path"].replace("/","_")
        (OUT/name).write_text(src)
        picked.append({"repo":f"{owner}/{repo}","path":t["path"],
                       "file":name,"bytes":len(src.encode())})
        print(f"   + {name}  {len(src.encode())}B")

pathlib.Path("manifest5.json").write_text(json.dumps(picked,indent=1))
print("TOTAL", len(picked), sum(p["bytes"] for p in picked), "bytes")

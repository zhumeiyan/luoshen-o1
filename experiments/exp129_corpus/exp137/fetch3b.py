import json, subprocess, pathlib, base64, urllib.parse
TOK = pathlib.Path("/data/workspace/luoshen-o1/.auth/gh_token").read_text().strip()
OUT = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137/corpus5")
OUT.mkdir(parents=True, exist_ok=True)
BAD=("/tests/","/test","/test_","test_","/examples/","/docs/","conftest","/vendor","/third_party",
     "__init__","version","_version","setup.py","/migrations/","/fixtures/","/testdata/")

def gh(p):
    r=subprocess.run(["curl","-s","-H",f"Authorization: Bearer {TOK}",
        "-H","Accept: application/vnd.github+json", f"https://api.github.com{p}"],
        capture_output=True,text=True,timeout=60)
    try: return json.loads(r.stdout)
    except Exception: return None

# 1) F_small: 搜索低星仓库（URL 编码 >）
q = urllib.parse.quote("language:python stars:20..400 pushed:>2025-06-01", safe=":+")
d = gh(f"/search/repositories?q={q}&sort=updated&per_page=100")
repos=[]
if isinstance(d,dict):
    for r in d.get("items",[]):
        if r.get("fork"): continue
        repos.append((r["owner"]["login"], r["name"], r.get("default_branch","main")))
print("search total:", d.get("total_count") if isinstance(d,dict) else "FAIL", "got", len(repos), flush=True)

# 2) 之前 tree 失败的仓库，试多个分支
RETRY = [("rq","rqalpha"),("backtrader","backtrader"),("geekan","MetaGPT"),
         ("modelscope","agentscope"),("pyspider","pyspider")]
for o,r in RETRY:
    for b in ("master","main","develop","dev"):
        dd=gh(f"/repos/{o}/{r}")
        if not isinstance(dd,dict): continue
        b = dd.get("default_branch") or b
        t=gh(f"/repos/{o}/{r}/git/trees/{b}?recursive=1")
        if isinstance(t,dict) and "tree" in t:
            repos.append((o,r,b)); print("retry ok", o,r,b, flush=True); break

picked=[]
def grab(dom,o,r,b,limit=4):
    got=0
    t=gh(f"/repos/{o}/{r}/git/trees/{b}?recursive=1")
    if not isinstance(t,dict) or "tree" not in t: return 0
    c=[x["path"] for x in t["tree"] if x["type"]=="blob" and x["path"].endswith(".py")
       and not any(k in x["path"] for k in BAD)]
    if not c: return 0
    c.sort(); step=max(1,len(c)//limit); sel=c[::step][:limit]
    for p in sel:
        f=gh(f"/repos/{o}/{r}/contents/{p}?ref={b}")
        if not isinstance(f,dict) or "content" not in f: continue
        txt=base64.b64decode(f["content"]).decode("utf-8","replace")
        if len(txt)<500 or len(txt)>400000: continue
        name=f"{dom}__{o}__{r}__{p.replace('/','_')}"
        (OUT/name).write_text(txt)
        picked.append(dict(domain=dom,repo=f"{o}/{r}",path=p,file=name,bytes=len(txt)))
        got+=1
    print(f"[{dom}] {o}/{r} +{got}", flush=True)
    return got

n=0
for o,r,b in repos[:14]:
    n+=grab("F_small",o,r,b)
print("F_small total", n, flush=True)

for o,r,b in repos[14:]:
    grab("G_retry",o,r,b)

pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137/manifest5b.json").write_text(
    json.dumps(picked,indent=1))
print("TOTAL",len(picked),"BYTES",sum(p["bytes"] for p in picked), flush=True)

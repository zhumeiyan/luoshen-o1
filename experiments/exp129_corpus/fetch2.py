import json, subprocess, pathlib, base64
TOK = pathlib.Path("/data/workspace/luoshen-o1/.auth/gh_token").read_text().strip()
OUT = pathlib.Path("corpus2"); OUT.mkdir(exist_ok=True)
REPOS=[("EleutherAI","lm-evaluation-harness","main"),("openai","evals","main"),
 ("openai","simple-evals","main"),("huggingface","lighteval","main"),
 ("SWE-bench","SWE-bench","main"),("UKGovernmentBEIS","inspect_ai","main"),
 ("allenai","olmes","main"),("stanford-crfm","helm","main"),("google","BIG-bench","main")]
CORE=("evaluator","evaluate","metric","scorer","grading","harness","judge","_eval","eval")
BAD=("/tests/","/test","/examples/","/docs/","conftest","/utils","util.py","/data","cli_args","__init__","version")
def gh(p):
    r=subprocess.run(["curl","-s","-H",f"Authorization: Bearer {TOK}","-H","Accept: application/vnd.github+json",
        f"https://api.github.com{p}"],capture_output=True,text=True,timeout=60)
    try: return json.loads(r.stdout)
    except Exception: return None
picked=[]
for o,r,b in REPOS:
    d=gh(f"/repos/{o}/{r}/git/trees/{b}?recursive=1")
    if not isinstance(d,dict) or "tree" not in d: continue
    c=[t["path"] for t in d["tree"] if t["type"]=="blob" and t["path"].endswith(".py")]
    core=[p for p in c if any(k in p.lower() for k in CORE) and not any(k in p.lower() for k in BAD)]
    core.sort(key=lambda p:(p.count("/"), len(p)))
    print(f"[{o}/{r}] core candidates={len(core)}")
    got=0
    for p in core:
        if got>=3: break
        f=gh(f"/repos/{o}/{r}/contents/{p}?ref={b}")
        if not isinstance(f,dict) or "content" not in f: continue
        txt=base64.b64decode(f["content"]).decode("utf-8","replace")
        if len(txt)<500: continue
        name=f"{o}__{r}__{p.replace('/','_')}"
        (OUT/name).write_text(txt); picked.append(dict(repo=f"{o}/{r}",path=p,file=name,bytes=len(txt)))
        print("   +",p,len(txt)); got+=1
pathlib.Path("manifest2.json").write_text(json.dumps(picked,indent=1))
print("TOTAL",len(picked))

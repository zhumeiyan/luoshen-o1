import json, subprocess, pathlib, base64
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

DOMAINS = {
 "A_etl":      [("apache","airflow","main"),("dagster-io","dagster","master"),
                ("PrefectHQ","prefect","main"),("spotify","luigi","master"),("mage-ai","mage-ai","master")],
 "B_quant":    [("microsoft","qlib","main"),("rq","rqalpha","master"),("backtrader","backtrader","master"),
                ("vnpy","vnpy","master"),("zvtvz","zvt","master")],
 "C_crawler":  [("Boris-code","feapder","master"),("pyspider","pyspider","master"),
                ("scrapy","scrapyd","master"),("psf","requests-html","main"),("Gerapy","Gerapy","main")],
 "D_llmagent": [("geekan","MetaGPT","main"),("Significant-Gravitas","AutoGPT","master"),
                ("run-llama","llama_index","main"),("langchain-ai","langchain","master"),
                ("modelscope","agentscope","main")],
 "E_teaching": [("trekhleb","learn-python","master"),("realpython","python-basics-exercises","master"),
                ("Asabeneh","30-Days-Of-Python","master"),("rougier","scientific-visualization-book","master"),
                ("jalammar","nlp-notebook","master")],
 "F_small":    None,
}

def search_small(n=10):
    d=gh("/search/repositories?q=language:python+stars:20..400+pushed:>2025-06-01&sort=updated&per_page=50")
    out=[]
    if not isinstance(d,dict): return out
    for r in d.get("items",[]):
        if r.get("fork"): continue
        out.append((r["owner"]["login"], r["name"], r.get("default_branch","main")))
        if len(out)>=n: break
    return out

DOMAINS["F_small"]=search_small(10)
print("F_small repos:", [f"{o}/{r}" for o,r,_ in DOMAINS["F_small"]], flush=True)

picked=[]
for dom, repos in DOMAINS.items():
    nfiles=0
    for o,r,b in repos:
        d=gh(f"/repos/{o}/{r}/git/trees/{b}?recursive=1")
        if not isinstance(d,dict) or "tree" not in d:
            print(f"[{dom}][{o}/{r}] tree fail", flush=True); continue
        c=[t["path"] for t in d["tree"] if t["type"]=="blob" and t["path"].endswith(".py")
           and not any(k in t["path"] for k in BAD)]
        if not c: continue
        c.sort()
        step=max(1,len(c)//4)
        sel=c[::step][:4]
        for p in sel:
            f=gh(f"/repos/{o}/{r}/contents/{p}?ref={b}")
            if not isinstance(f,dict) or "content" not in f: continue
            txt=base64.b64decode(f["content"]).decode("utf-8","replace")
            if len(txt)<500 or len(txt)>400000: continue
            name=f"{dom}__{o}__{r}__{p.replace('/','_')}"
            (OUT/name).write_text(txt)
            picked.append(dict(domain=dom,repo=f"{o}/{r}",path=p,file=name,bytes=len(txt)))
            nfiles+=1
        print(f"[{dom}] {o}/{r} +{len(sel)}", flush=True)
    print(f"  -> {dom} total {nfiles}", flush=True)
pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137/manifest5.json").write_text(
    json.dumps(picked,indent=1))
print("TOTAL",len(picked),"BYTES",sum(p["bytes"] for p in picked), flush=True)

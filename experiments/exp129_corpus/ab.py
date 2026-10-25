import sys, json, pathlib, importlib, collections

def load(root, tag):
    for m in [k for k in list(sys.modules) if k.startswith("evalguard")]:
        del sys.modules[m]
    sys.path.insert(0, root)
    from evalguard import cli
    from evalguard.cli import scan
    cli.PRO_ON[0] = True
    sys.path.remove(root)
    return scan

def run(scan, paths):
    out = {}
    for p in paths:
        try: out[str(p)] = scan(str(p))
        except Exception as e: out[str(p)] = [{"severity":"err","eg_id":"ERR","hits":[{"line":0,"hit":str(e)}]}]
    return out

ROOT = pathlib.Path("/data/workspace/luoshen-o1")
fix = sorted((ROOT/"overseas/evalguard/tests").glob("*.py"))
corpus = sorted(pathlib.Path("corpus").glob("*.py"))

A = load("/tmp/pkgA", "A")          # HEAD (pre-fix)
B = load(str(ROOT/"overseas"), "B") # patched
ra, rb = run(A, fix), run(B, fix)
ca, cb = run(A, corpus), run(B, corpus)

def summarize(res, label):
    sev = collections.Counter()
    for f, r in res.items():
        for x in r: sev[x["severity"]] += 1
    n = sum(1 for f, r in res.items() if r)
    print(f"{label}: files_with={n}/{len(res)} blocker={sev['blocker']} warn={sev['warn']} info={sev['info']}")
    return sev

print("== fixtures ==")
sa, sb = summarize(ra,"A(orig)"), summarize(rb,"B(fixed)")
print("== real corpus (9 authoritative frameworks) ==")
ca_, cb_ = summarize(ca,"A(orig)"), summarize(cb,"B(fixed)")
json.dump(dict(A_fix=ra,B_fix=rb,A_corpus=ca,B_corpus=cb), open("ab.json","w"), indent=1)

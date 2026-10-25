import json, subprocess, pathlib, sys

TOK = pathlib.Path("/data/workspace/luoshen-o1/.auth/gh_token").read_text().strip()
OUT = pathlib.Path("corpus"); OUT.mkdir(exist_ok=True)

REPOS = [
 ("EleutherAI","lm-evaluation-harness","main"),
 ("openai","evals","main"),
 ("openai","simple-evals","main"),
 ("huggingface","lighteval","main"),
 ("SWE-bench","SWE-bench","main"),
 ("UKGovernmentBEIS","inspect_ai","main"),
 ("allenai","olmes","main"),
 ("stanford-crfm","helm","main"),
 ("langchain-ai","langchain-benchmarks","main"),
 ("google","BIG-bench","main"),
]

def gh(path):
    r = subprocess.run(["curl","-s","-H",f"Authorization: Bearer {TOK}",
        "-H","Accept: application/vnd.github+json",
        f"https://api.github.com{path}"], capture_output=True, text=True, timeout=60)
    try: return json.loads(r.stdout)
    except Exception: return None

KEY = ("eval","metric","score","benchmark","grading","harness","judge","report")
picked = []
for owner,repo,br in REPOS:
    d = gh(f"/repos/{owner}/{repo}/git/trees/{br}?recursive=1")
    if not isinstance(d, dict) or "tree" not in d:
        print(f"[{owner}/{repo}] TREE FAIL {str(d)[:80]}"); continue
    cands = [t["path"] for t in d["tree"]
             if t["type"]=="blob" and t["path"].endswith(".py")
             and any(k in t["path"].lower() for k in KEY)]
    cands.sort(key=lambda p: len(p))
    print(f"[{owner}/{repo}] py files={len(d['tree'])} eval-ish={len(cands)}")
    for p in cands[:4]:
        f = gh(f"/repos/{owner}/{repo}/contents/{p}?ref={br}")
        if not isinstance(f, dict) or "content" not in f:
            print("   skip",p); continue
        import base64
        try: txt = base64.b64decode(f["content"]).decode("utf-8","replace")
        except Exception: continue
        if len(txt) < 300: continue
        name = f"{owner}__{repo}__{p.replace('/','_')}"
        (OUT/name).write_text(txt)
        picked.append(dict(repo=f"{owner}/{repo}", path=p, file=name, bytes=len(txt)))
        print("   +", p, len(txt))
    if len(picked) >= 40: break

pathlib.Path("manifest.json").write_text(json.dumps(picked, indent=1))
print("TOTAL FILES", len(picked))

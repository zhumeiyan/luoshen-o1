import json, os, time, base64, urllib.request
TOKEN = open('/data/workspace/luoshen-o1/.auth/gh_token').read().strip()
H = {"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
     "User-Agent": "luoshen"}
# repo -> (branch, [candidate paths])   NEW repos only, none of the exp129 nine
TARGETS = {
 "ExplodingGradients/ragas": ("main", ["src/ragas/evaluation.py","src/ragas/metrics/base.py"]),
 "confident-ai/deepeval": ("main", ["deepeval/evaluate/evaluate.py","deepeval/metrics/base_metric.py"]),
 "promptfoo/promptfoo": ("main", ["src/evaluator.ts"]),
 "mlflow/mlflow": ("master", ["mlflow/models/evaluation/base.py","mlflow/evaluation/evaluation.py"]),
 "comet-ml/opik": ("main", ["sdks/python/src/opik/evaluation/evaluator.py"]),
 "Arize-ai/phoenix": ("main", ["src/phoenix/evals/evaluators.py"]),
 "IBM/unitxt": ("main", ["src/unitxt/evaluate.py","src/unitxt/metrics.py"]),
 "bigcode-project/bigcode-evaluation-harness": ("main", ["bigcode_eval/evaluator.py"]),
 "evalplus/evalplus": ("main", ["evalplus/evaluate.py"]),
 "embeddings-benchmark/mteb": ("main", ["mteb/evaluation/MTEB.py"]),
}
def get(url, tries=2):
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers=H)
            with urllib.request.urlopen(r, timeout=12) as f:
                return json.load(f)
        except Exception as e:
            if i == tries-1: return {"_err": str(e)[:70]}
            time.sleep(1.0)
out = []
for repo,(br,paths) in TARGETS.items():
    for p in paths:
        d = get(f"https://api.github.com/repos/{repo}/contents/{p}?ref={br}")
        if isinstance(d, dict) and "content" in d:
            txt = base64.b64decode(d["content"]).decode("utf-8","replace")
            out.append({"repo":repo,"path":p,"text":txt})
            print("OK  ", repo, p, len(txt), flush=True)
        else:
            print("MISS", repo, p, (d.get("_err","?") if isinstance(d,dict) else "?"), flush=True)
os.makedirs("corpus3", exist_ok=True)
for i,f in enumerate(out):
    ext = ".ts" if f["path"].endswith(".ts") else ".py"
    fn = "corpus3/%02d_%s%s" % (i, (f["repo"].replace("/","_")+"_"+f["path"].replace("/","_"))[:60], ext)
    open(fn,"w").write(f["text"])
json.dump([{k:v for k,v in f.items() if k!="text"} for f in out], open("manifest3.json","w"), ensure_ascii=False, indent=1)
print("TOTAL", len(out), flush=True)

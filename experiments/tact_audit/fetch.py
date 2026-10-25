import json, base64, urllib.request, os, sys
TOKEN=os.environ.get("GH_TK", "")   # 凭据不入库：从环境变量读取
REPO="KLameng/TACT-Three-Axis-Check"
files=["engine/tact_run.py","engine/data/calibration_cases.json","engine/data/coordinate_data.json",
"SELF_FAILURES.md","engine/README.md","tact-three-axis-check/docs/TACT-kappa全历程汇总与分析.md",
"tact-three-axis-check/references/verification-chain.md"]
for f in files:
    url=f"https://api.github.com/repos/{REPO}/contents/{urllib.parse.quote(f)}?ref=main"
    req=urllib.request.Request(url, headers={"Authorization":f"token {TOKEN}","User-Agent":"x"})
    try:
        d=json.load(urllib.request.urlopen(req, timeout=60))
        raw=base64.b64decode(d["content"])
        out=os.path.basename(f)
        open(out,"wb").write(raw)
        print(f"OK  {out:45s} {len(raw):>8} bytes")
    except Exception as e:
        print(f"FAIL {f}: {e}")

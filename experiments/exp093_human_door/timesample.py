import subprocess, json, time, datetime
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
T=["https://mail.qq.com","https://api.github.com/zen","https://github.com/KLameng/TACT-Three-Axis-Check",
   "https://captcha.gtimg.com/static/template/drag_ele.cb7e57e5.html","https://captcha.qq.com/TCaptcha.js",
   "https://gitee.com/dromara/easyAi","https://im.qq.com/index/#/linux","https://www.oschina.net",
   "https://www.baidu.com","https://www.qq.com"]
res={t:[] for t in T}
for k in range(6):
    ts=datetime.datetime.now().strftime("%H:%M:%S")
    row={}
    for u in T:
        try:
            r=subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","-m","10","-A",UA,u],capture_output=True,text=True)
            c=int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
        except Exception: c=0
        res[u].append(c); row[u]=c
    print(f"[{k}] {ts} {[row[t] for t in T]}", flush=True)
    if k<5: time.sleep(25)
json.dump(res,open("timesample.json","w"),indent=1)
print("=== 稳定性 ===")
for u,v in res.items():
    flips=sum(1 for i in range(1,len(v)) if (v[i]==200)!=(v[i-1]==200))
    print(f"  {u[:52]:54s} {v} 开率={sum(1 for x in v if x==200)}/{len(v)} 翻转={flips}")

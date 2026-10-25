import subprocess, json, time
UA_CURL  = "curl/8.4.0"
UA_CHROME= "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
UA_PHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
UAS={"curl":UA_CURL,"chrome":UA_CHROME,"iphone":UA_PHONE}
T=["https://github.com/KLameng/TACT-Three-Axis-Check",
   "https://gitee.com/dromara/easyAi",
   "https://www.oschina.net",
   "https://captcha.gtimg.com/static/template/drag_ele.cb7e57e5.html",
   "https://mail.qq.com"]
res={}
for name,ua in UAS.items():
    for u in T:
        try:
            r=subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","-m","12","-A",ua,u],
                             capture_output=True,text=True)
            code=int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
        except Exception: code=0
        res.setdefault(u,{})[name]=code
        print(f"{u[:52]:54s} {name:7s} -> {code}")
json.dump(res,open("ua.json","w"),indent=1)
print("\n=== UA 是否改变结果 ===")
for u,d in res.items():
    vals=set(d.values())
    print(f"  {u[:52]:54s} {d}  {'UA敏感' if len(vals)>1 else 'UA无关'}")

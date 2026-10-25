import urllib.request,ssl,http.cookiejar,random,sys,time
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
cj=http.cookiejar.MozillaCookieJar("/data/workspace/luoshen-o1/.auth/session.txt")
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj),urllib.request.HTTPSHandler(context=ctx))
op.addheaders=[("User-Agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"),
               ("Referer","https://xui.ptlogin2.qq.com/")]
op.open("https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=522005705&daid=4&style=33&s_url=https%3A%2F%2Fmail.qq.com%2F",timeout=25).read()
d=op.open(f"https://ssl.ptlogin2.qq.com/ptqrshow?appid=522005705&e=2&l=M&s=3&d=72&v=4&daid=4&t=0.{random.random()}&pt_3rd_aid=0",timeout=25).read()
open("/data/workspace/luoshen-o1/.auth/qr_live.png","wb").write(d)
qrsig=[c.value for c in cj if c.name=="qrsig"][0]
e=0
for ch in qrsig: e += (e<<5) + ord(ch)
token=e & 0x7fffffff
print("ptqrtoken",token); sys.stdout.flush()
sig=next((c.value for c in cj if c.name=="pt_login_sig"),"")
base=("https://ssl.ptlogin2.qq.com/ptqrlogin?u1=https%3A%2F%2Fmail.qq.com%2F"
      f"&ptqrtoken={token}&ptredirect=0&h=1&t=1&g=1"
      "&from_ui=1&ptlang=2052&"
      f"action=0-0-{int(time.time()*1000)}&js_ver=10297&js_type=1&login_sig={sig}&pt_uistyle=40&aid=522005705&daid=4&")
for i in range(120):
    try:
        r=op.open(base+str(random.random()),timeout=30).read().decode("utf-8","replace")
    except Exception as ex:
        print("poll err",str(ex)[:80]); break
    if "'0'" in r.split(",")[0] or r.startswith("ptuiCB('0'"):
        print("SUCCESS", r[:300]); cj.save(ignore_discard=True,ignore_expires=True); break
    st=r.split("'")[1] if "'" in r else "?"
    msg={"66":"等待扫码","67":"已扫码，等待确认","65":"二维码已失效","0":"成功"}.get(st,st)
    print(f"[{i}] state={st} {msg}"); sys.stdout.flush()
    if st=="65": break
    time.sleep(3)

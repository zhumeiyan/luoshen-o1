import urllib.request,ssl,http.cookiejar,random,time
A="/data/workspace/luoshen-o1/.auth/"
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
cj=http.cookiejar.MozillaCookieJar(A+"cookies.txt")
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj),urllib.request.HTTPSHandler(context=ctx))
op.addheaders=[("User-Agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"),
               ("Referer","https://xui.ptlogin2.qq.com/")]
op.open("https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=522005705&daid=4&style=33&s_url=https%3A%2F%2Fmail.qq.com%2F",timeout=25).read()
d=op.open(f"https://ssl.ptlogin2.qq.com/ptqrshow?appid=522005705&e=2&l=M&s=3&d=72&v=4&daid=4&t=0.{random.random()}&pt_3rd_aid=0",timeout=25).read()
open(A+"qr_live.png","wb").write(d)
qrsig=next((c.value for c in cj if c.name=="qrsig"),"")
e=0
for ch in qrsig: e += (e<<5) + ord(ch)
token=e & 0x7fffffff
cj.save(ignore_discard=True,ignore_expires=True)
print("qr bytes:",len(d),"token:",token,"cookies:",len(cj))

import urllib.request, ssl, random, http.cookiejar, urllib.parse, hashlib, re, json, sys
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
U="778131400"; P=sys.argv[1] if len(sys.argv)>1 else "z4570285"
cj=http.cookiejar.CookieJar()
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
op.addheaders=[("User-Agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"),
               ("Referer","https://xui.ptlogin2.qq.com/")]
def g(u):
    r=op.open(u,timeout=25); return r.read().decode("utf-8","replace")
def b(u):
    return op.open(u,timeout=25).read()

# 1. xlogin
g("https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=522005705&daid=4&style=33&low_login=1&s_url=https%3A%2F%2Fmail.qq.com%2F")
print("cookies after xlogin:", sorted(set(c.name for c in cj)))
# 2. check
ck=g(f"https://ssl.ptlogin2.qq.com/check?pt_tea=2&uin={U}&appid=522005705&pt_3rd_aid=0&r={random.random()}")
print("CHECK:", ck[:120])
mm=re.match(r"ptui_checkVC\('(.*?)','(.*?)'", ck)
need, sess = mm.group(1), mm.group(2)
print("need_vc:", need)
# 3. captcha
img=b(f"https://ssl.ptlogin2.qq.com/getimage?aid=522005705&r={random.random()}&uin={U}")
open(".auth/cap.png","wb").write(img)
import ddddocr
VC=ddddocr.DdddOcr(show_ad=False).classification(img)
print("CAPTCHA:", VC, "img bytes", len(img))
# 4. encryption candidates
def enc_variants():
    md5b=lambda x: hashlib.md5(x).digest(); md5h=lambda x: hashlib.md5(x).hexdigest()
    m1=md5b(P.encode()); u8=struct.pack('>Q',int(U))
    yield "v1", md5h((md5h(m1+U.encode())+VC.upper()).encode())
    yield "v2", md5h((md5h(m1+u8)+VC.upper()).encode())
    yield "v3", md5h((md5h(m1+U.encode()).upper()+VC.upper()).encode())
    yield "raw_md5", md5h(P.encode())
import struct
for name,p in enc_variants():
    q={"u":U,"p":p,"verifycode":VC,"pt_vcode_v1":1,"pt_verifysession_v1":sess,
       "pt_aid":"522005705","daid":"4","u1":"https://mail.qq.com/","pt_randsalt":"0",
       "pt_3rd_aid":"0","ptlang":"2052","low_login_enable":"0","from_ui":"1",
       "fp":"loginerroralert","device":"2","pt_ttype":"1","pt_tea":"2","pt_redirect":"0",
       "h":"1","r":random.random()}
    try:
        r=g("https://ssl.ptlogin2.qq.com/login?"+urllib.parse.urlencode(q))
        print(f"[{name}] -> {r[:200]}")
    except Exception as e:
        print(f"[{name}] FAIL {e}")

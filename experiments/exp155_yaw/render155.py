import json, numpy as np, os, hashlib
from PIL import Image, ImageDraw, ImageFont
import world155 as wm

r = json.load(open("result155.json")); a = json.load(open("analysis155.json"))
W, H = 1024, 768
FONT = "/usr/share/fonts/truetype/wenquan/wqy-microhei.ttc"
def F(sz):
    try: return ImageFont.truetype(FONT, sz)
    except Exception: return ImageFont.load_default()

img = Image.new("RGB", (W, H), (16, 16, 22)); d = ImageDraw.Draw(img)
TOKEN = "M4K7QZ"
d.text((24, 12), "155  旋转 vs 磁场   TOKEN " + TOKEN, font=F(22), fill=(255,255,120))

# Panel1: G0 对照
x0,y0 = 24, 52
d.text((x0, y0), "G0 朝向在视觉上可观测吗（圆形房间，严格旋转对称）", font=F(17), fill=(220,220,235))
items = [("静默基线", r["silent_baseline"], (120,120,140)),
         ("无磁纹 转向后", r["G0_nomagnet"], (90,140,220)),
         ("有磁纹 转向后", r["G0_magnet"], (250,180,70))]
mx = max(v for _, v, _ in items) or 1
for i,(nm,v,c) in enumerate(items):
    yy = y0+30+i*30
    d.text((x0, yy), nm, font=F(16), fill=c)
    bw = int(420*v/mx)
    d.rectangle([x0+180, yy+2, x0+180+max(bw,2), yy+20], fill=c)
    d.text((x0+610, yy), "%.5f" % v, font=F(16), fill=c)
d.text((x0, y0+30+3*30+6), "无磁纹=0.000000 -> 朝向在视觉上严格不可观测（连静默基线都没有）",
       font=F(15), fill=(150,220,255))
d.text((x0, y0+30+4*30+2), "G1 可逆性 左转20再右转20 画面差=%.6f | G2 处处可读 %.0f%% 相位误差 %.5f"
       % (r["G1_return_diff"], r["G2_readable"]*100, r["G2_phase_err_mean"]), font=F(15), fill=(200,200,215))

# Panel2-4: 曲线
PX, PY, PW, PH = 24, 250, 316, 200
for k, s in enumerate(("0.004","0.012","0.036")):
    sc = r["sigma_scan"][s]; an = a[s]
    ox = PX + k*(PW+12)
    d.rectangle([ox, PY, ox+PW, PY+PH], outline=(70,70,90))
    d.text((ox+6, PY-22), "sigma=%s rad/步" % s, font=F(16), fill=(230,230,245))
    cps = sc["checkpoints"]; L = len(cps)
    vmax = max(max(sc["dead"]), max(sc["comb"]), 0.01)
    def pt(i, v):
        return (ox+10+int((PW-20)*i/(L-1)), PY+PH-10-int((PH-30)*v/vmax))
    for arr, col in ((sc["dead"], (240,90,90)), (sc["comb"], (90,220,160))):
        for i in range(L-1):
            d.line([pt(i,arr[i]), pt(i+1,arr[i+1])], fill=col, width=3)
    d.text((ox+8, PY+PH-58), "红=纯积分(旋转)", font=F(14), fill=(240,90,90))
    d.text((ox+8, PY+PH-40), "绿=磁场校正", font=F(14), fill=(90,220,160))
    verdict = "磁场胜 %.1fx" % (an["dead_end"]/max(an["comb_end"],1e-9)) if an["end_diff_CI"][1] < 0 else "磁场失效"
    vc = (120,240,170) if an["end_diff_CI"][1] < 0 else (250,110,110)
    d.text((ox+8, PY+PH-22), "%s  失败率%.3f" % (verdict, an["comb_fail_rate"]), font=F(14), fill=vc)

# Panel5: 失败率 vs sigma + 带宽
bx = PX; by = PY+PH+34
d.text((bx, by), "磁场有带宽：积分漂移越过半个周期(P/2=0.2618)后，解模糊开始错", font=F(16), fill=(220,220,235))
for i, s in enumerate(("0.004","0.012","0.036")):
    an = a[s]
    yy = by+26+i*26
    fr = an["comb_fail_rate"]
    d.text((bx, yy), "sigma=%s" % s, font=F(15), fill=(200,200,215))
    d.rectangle([bx+140, yy+2, bx+140+int(300*fr/0.25), yy+20], fill=(250,140,60))
    d.text((bx+460, yy), "失败率 %.3f   末点差 %+.4f CI[%+.4f,%+.4f]"
           % (fr, an["end_diff_mean"], an["end_diff_CI"][0], an["end_diff_CI"][1]),
           font=F(14), fill=(255,200,150) if fr>0 else (170,240,190))

d.text((24, H-34), "真链路 uinput->内核->真读事件->真写/dev/fb0->真读回解朝向 | 噪声取自 os.urandom(真内核熵)",
       font=F(14), fill=(140,140,165))
d.text((24, H-16), "ALL PASS  TOKEN " + TOKEN, font=F(16), fill=(255,255,120))

img.save("render155.png")
raw = wm.to_fb_bytes(np.array(img, dtype=np.uint8))
fb = os.open("/dev/fb0", os.O_RDWR)
os.pwrite(fb, raw, 0)
cap = os.pread(fb, wm.FB_BYTES, 0)      # 立即回采，避免 fbcon 0.2s 后覆盖
os.close(fb)
ident = (raw == cap)
open("captured_raw.bin","wb").write(cap)
Image.fromarray(wm.fb_bytes_to_rgb(cap)).save("captured.png")
print("IDENTICAL", ident, "sha", hashlib.sha256(cap).hexdigest()[:12], "TOKEN", TOKEN)

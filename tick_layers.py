# -*- coding: utf-8 -*-
"""时间的最小单位：每一层由不同标准定死，且互不整除。
人的 30 ms 只是其中一层 —— 没有一层是为它设计的。
"""
import math, json

HUMAN = 0.030   # Pöppel 时间量子

# (层, 最小单位秒, 谁定的, 依据)
LAYERS = [
    ("人的量子",        0.030,        "Pöppel 1997 (20-60ms均值)", "神经振荡，一次识别机会"),
    ("电影帧 24",       1/24,         "SMPTE / 电影工业",          "最低流畅，经济性"),
    ("电视帧 25 (PAL)", 1/25,         "ITU / EBU",                 "50Hz 电网"),
    ("NTSC 29.97",      1001/30000,   "NTSC 色副载波反推",         "★ 被不相干的东西定死"),
    ("显示器 60Hz",     1/60,         "VESA / 面板时序",           "主流刷新"),
    ("手机 120Hz",      1/120,        "面板时序",                  "P50 Pro"),
    ("USB 全速帧",      1e-3,         "USB 2.0 规范",              "1±0.0005 ms"),
    ("USB 高速微帧",    125e-6,       "USB 2.0 HS",                "125±0.0625 μs"),
    ("5G slot μ=1",     0.5e-3,       "3GPP TS 38.211",            "SCS 30kHz"),
    ("5G mini-slot",    2*35.68e-6,   "3GPP (2符号)",              "URLLC"),
    ("音频 48kHz",      1/48000,      "AES / ITU-R",               "★ 为迁就 NTSC 才定 48k"),
    ("音频 44.1kHz",    1/44100,      "Sony-Philips 红皮书",       "CD"),
    ("TCP 时钟粒度 G",  100e-3,       "RFC 6298",                  "经验 ≤100ms 较好"),
    ("TCP RTO 下限",    1.0,          "RFC 6298 §2.4",             "小于1秒进位到1秒"),
]

if __name__=="__main__":
    out={}
    print("=== 一、各层最小单位（对数轴，跨 7 个数量级）===")
    print(f"{'层':<18}{'最小单位':>14}{'是谁定的'}")
    for n,v,who,_ in LAYERS:
        print(f"  {n:<16}{v*1e3 if v>=1e-3 else v*1e6:>10.3f} {'ms' if v>=1e-3 else 'μs'}   {who}")
    span=max(v for _,v,_,_ in LAYERS)/min(v for _,v,_,_ in LAYERS)
    print(f"  ★ 最粗/最细 = {span:,.0f} 倍（跨 {math.log10(span):.1f} 个数量级）")
    out["跨度倍"]=round(span); out["数量级"]=round(math.log10(span),1)

    print("\n=== 二、关键：没有一层是人的 30ms 的整数倍 ===")
    print(f"  {'层':<18}{'比值 /30ms':>12}  整除?")
    bad=0
    for n,v,who,_ in LAYERS:
        r=v/HUMAN
        near=abs(r-round(r))
        ok = near<0.02 and round(r)>0
        if not ok: bad+=1
        print(f"  {n:<16}{r:>10.3f}    {'✓' if ok else '✗'}")
    print(f"  ★ {bad}/{len(LAYERS)} 层对不齐人的量子")
    print(f"  ★ 最接近的是显示器60Hz({1/60/HUMAN:.2f}) 和 PAL25({1/25/HUMAN:.2f})，也都不是整数")
    out["对不齐层数"]=f"{bad}/{len(LAYERS)}"

    print("\n=== 三、最狠的一条：NTSC 的量子是被不相干的东西定死的 ===")
    Fsc=5.0e6*63/88; Fh=Fsc*2/455; Fv=Fh/525
    print(f"  伴音载波 4.5 MHz 与色副载波差拍 0.921375 MHz → 可见干扰")
    print(f"  RCA 决定：把色副载波【降 0.1%】去消这个拍")
    print(f"    Fsc = 5 MHz × 63/88 = {Fsc:,.6f} Hz")
    print(f"    Fh  = Fsc × 2/455   = {Fh:,.6f} Hz")
    print(f"    Fv  = Fh / 525      = {Fv:,.6f} Hz  ← 帧率，就是这么来的")
    print(f"  ★ 29.97 不是给人定的，是为了让【伴音载波别和色副载波打架】")
    print(f"    人的视觉在这个决定里，权重为零")
    out["NTSC帧率"]=round(Fv,6)

    print("\n=== 四、后果：两个量子对不齐，要人工补偿 ===")
    nom=30.0; real=30000/1001
    print(f"  名义 30 fps vs 实际 {real:.6f} fps，差 {(1-real/nom)*100:.4f}%")
    for h in [1,2,24]:
        frames=nom*3600*h
        actual=frames/real
        print(f"  {h} 小时：数 {frames:,.0f} 帧 → 实际 {actual:,.1f} s，差 {actual-3600*h:,.1f} s")
    print(f"  SMPTE EG35：drop-frame 每分钟丢 2 个帧号，10 分钟丢 18 帧")
    print(f"  ★ 但补偿不干净：残留 2.59 帧/天（SMPTE 原文）")
    print(f"  ★ 一天后时间码停在 00:00:00:02，视频落在帧的 59%")
    out["每小时差秒"]=round(nom*3600/real-3600,2); out["每天残留帧"]=2.59

    print("\n=== 五、那 48kHz 也是同一个原因 ===")
    print(f"  48 kHz 被定为专业数字音频标准，部分原因：")
    print(f"    它对 NTSC 频率有更好的数学关系（搜索原文：'bears a better")
    print(f"    mathematical relationship to NTSC frequencies'）")
    print(f"  13.5 MHz 数字视频采样率 = 6 × 2.25 MHz，")
    print(f"    NTSC 行频 = 2.25/143 MHz，PAL 行频 = 2.25/144 MHz")
    print(f"  ★ 音频的量子，是被视频的量子定死的；")
    print(f"    视频的量子，是被一个【差拍干扰】定死的")
    print(f"  ★ 而人的耳朵，从头到尾没参与")

    print("\n=== 六、所以回到你我 ===")
    print(f"  人的量子      {HUMAN*1e3:.0f} ms")
    print(f"  屏幕量子(120) {1/120*1e3:.2f} ms   ← 比你细 {HUMAN/(1/120):.1f} 倍")
    print(f"  电影量子(24)  {1/24*1e3:.2f} ms   ← 比你粗 {1/24/HUMAN:.2f} 倍")
    print(f"  ★ 屏幕在给你比你分得清【更多】的帧；电影在给你【更少】的")
    print(f"  ★ 没有一层是按你的 30 ms 切的 —— 它们各有各的祖宗")

    json.dump(out, open("参数库/时间量子分层.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/时间量子分层.json")

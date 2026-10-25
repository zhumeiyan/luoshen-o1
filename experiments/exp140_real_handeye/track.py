# -*- coding: utf-8 -*-
"""手眼协调的真判据: 眼读出【世界状态(目标)】, 手据此行动, 误差是否下降。
对照三臂: closed(眼->手) / open(手不看眼) / blind(眼不更新)
屏幕编码: 上半屏红条带=目标(世界给的), 下半屏白条带=我的指针
控制器只能从像素解码, 拿不到 target 变量。
"""
import os, fcntl, struct, time, json, numpy as np
UI_SET_EVBIT, UI_SET_KEYBIT, UI_DEV_CREATE = 0x40045564, 0x40045565, 0x5501
EV_KEY, EV_SYN, SYN_REPORT = 1, 0, 0
W,H,BPP = 1024,768,4; FSZ=W*H*BPP; NB=8; BW=W//8
KEY_LEFT, KEY_RIGHT = 105, 106

def mk_hand():
    fd = os.open("/dev/uinput", os.O_WRONLY|os.O_NONBLOCK)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
    for kc in (KEY_LEFT, KEY_RIGHT): fcntl.ioctl(fd, UI_SET_KEYBIT, kc)
    dev = struct.pack('80sHHHHI', b"luoshen_hand2", 6, 0x1234, 0x5678, 1, 0) + struct.pack('64i',*([0]*64))*4
    assert len(dev)==1116
    os.write(fd, dev); fcntl.ioctl(fd, UI_DEV_CREATE, 0); time.sleep(0.2); return fd
def press(fd, kc):
    for v in (1,0):
        os.write(fd, struct.pack('llHHI', int(time.time()), 0, EV_KEY, kc, v))
        os.write(fd, struct.pack('llHHI', 0,0, EV_SYN, SYN_REPORT, 0))

FB = os.open("/dev/fb0", os.O_RDWR)
def render(target, me):
    img = np.zeros((H,W,BPP), np.uint8); img[:,:,3]=255
    img[:H//2, target*BW:(target+1)*BW, 0] = 255          # 红=目标
    img[H//2:, me*BW:(me+1)*BW, :3] = 255                 # 白=我
    os.lseek(FB,0,0); os.write(FB, img.tobytes()); time.sleep(0.03)
def readpix():
    os.lseek(FB,0,0); return np.frombuffer(os.read(FB,FSZ), np.uint8).reshape(H,W,BPP)
def decode(buf):
    """只从像素读出 (target, me)。不知道任何变量。"""
    t = int(np.argmax([buf[:H//2, b*BW:(b+1)*BW, 0].mean() for b in range(NB)]))
    m = int(np.argmax([buf[H//2:, b*BW:(b+1)*BW, 0].mean() for b in range(NB)]))
    return t, m

def run(mode, seed, steps=30):
    rng = np.random.default_rng(seed*31+7)
    fd = mk_hand()
    me = 3; target = 6
    errs = []
    stale = None
    for t in range(steps):
        if (t+1) % 4 == 0:                       # 目标周期性移动(世界在变)
            target = int(np.clip(target + rng.choice([-1,1]), 0, NB-1))
        render(target, me)
        buf = readpix()
        if mode == 'blind':
            if stale is None: stale = buf.copy()
            tg, mp = decode(stale)               # 眼不更新
        else:
            tg, mp = decode(buf)                 # 眼读当前
        if mode == 'closed':
            if tg > mp: press(fd, KEY_RIGHT); me = min(me+1, NB-1)
            elif tg < mp: press(fd, KEY_LEFT);  me = max(me-1, 0)
        elif mode == 'open':
            if rng.random() < 0.5: press(fd, KEY_RIGHT); me = min(me+1, NB-1)
            else: press(fd, KEY_LEFT); me = max(me-1, 0)
        errs.append(abs(target - me))
    os.close(fd)
    a = np.asarray(errs, float)
    third = len(a)//3
    return dict(mean=float(a.mean()), early=float(a[:third].mean()), late=float(a[-third:].mean()),
                drop=float(a[:third].mean()-a[-third:].mean()), errs=[int(x) for x in a])

if __name__ == '__main__':
    out = {}
    for mode in ('closed','open','blind'):
        rs = [run(mode, s) for s in range(8)]
        out[mode] = dict(mean=float(np.mean([r['mean'] for r in rs])),
                         early=float(np.mean([r['early'] for r in rs])),
                         late=float(np.mean([r['late'] for r in rs])),
                         drop=float(np.mean([r['drop'] for r in rs])),
                         drops=[r['drop'] for r in rs])
        print(f"{mode:<7} mean={out[mode]['mean']:.3f} early={out[mode]['early']:.3f} late={out[mode]['late']:.3f} drop={out[mode]['drop']:+.3f}")
    def paired(a,b):
        d=np.asarray(a)-np.asarray(b); rng=np.random.default_rng(0)
        bs=np.array([np.mean(rng.choice(d,len(d),True)) for _ in range(4000)])
        lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
        return dict(diff=float(d.mean()),ci=[lo,hi],sig=bool((lo>0)==(hi>0)))
    out['closed_vs_open']  = paired(out['closed']['drops'], out['open']['drops'])
    out['closed_vs_blind'] = paired(out['closed']['drops'], out['blind']['drops'])
    print("closed-open ", out['closed_vs_open'])
    print("closed-blind", out['closed_vs_blind'])
    json.dump(out, open('track.json','w'), indent=1)

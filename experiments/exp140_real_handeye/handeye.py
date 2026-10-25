# -*- coding: utf-8 -*-
"""exp140 真实手眼协调：手(/dev/uinput)改世界 -> 眼(/dev/fb0)独立读回 -> 比对
关键约束: decode() 只接收像素buffer, 不接收 k。眼必须自己读出, 不能被程序告知。
"""
import os, fcntl, struct, time, json, numpy as np

UI_SET_EVBIT, UI_SET_KEYBIT, UI_DEV_CREATE, UI_DEV_DESTROY = 0x40045564, 0x40045565, 0x5501, 0x5502
EV_KEY, EV_SYN, SYN_REPORT = 1, 0, 0
W, H, BPP = 1024, 768, 4
FSZ = W*H*BPP
NBAND, BW = 8, W//8

def mk_hand(name=b"luoshen_hand"):
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
    for kc in range(2, 10):          # KEY_1..KEY_8
        fcntl.ioctl(fd, UI_SET_KEYBIT, kc)
    dev = struct.pack('80sHHHHI', name, 0x06, 0x1234, 0x5678, 1, 0)
    dev += struct.pack('64i', *([0]*64)) * 4
    assert len(dev) == 1116, f"uinput_user_dev {len(dev)} != 1116"
    os.write(fd, dev)
    fcntl.ioctl(fd, UI_DEV_CREATE, 0)
    time.sleep(0.15)
    return fd

def hand_press(fd, kc):
    ev = struct.pack('llHHI', int(time.time()), int((time.time()%1)*1e6), EV_KEY, kc, 1)
    os.write(fd, ev)
    os.write(fd, struct.pack('llHHI', 0, 0, EV_SYN, SYN_REPORT, 0))
    os.write(fd, struct.pack('llHHI', int(time.time()), 0, EV_KEY, kc, 0))
    os.write(fd, struct.pack('llHHI', 0, 0, EV_SYN, SYN_REPORT, 0))

FB = os.open("/dev/fb0", os.O_RDWR)

def eye_write(k):
    """世界侧: 只有第 k 条带亮。k<0 => 全暗(默认)"""
    img = np.zeros((H, W, BPP), np.uint8); img[:, :, 3] = 255
    if k >= 0:
        img[:, k*BW:(k+1)*BW, :3] = 255
    os.lseek(FB, 0, 0); os.write(FB, img.tobytes())
    time.sleep(0.05)

def eye_read():
    os.lseek(FB, 0, 0); buf = os.read(FB, FSZ)
    a = np.frombuffer(buf, np.uint8).reshape(H, W, BPP)
    return a

def decode(buf):
    """眼: 只从像素读出条带编号。不知道 k。"""
    lum = np.array([float(buf[:, b*BW:(b+1)*BW, 0].mean()) for b in range(NBAND)])
    return int(np.argmax(lum)), lum

def run(n=8, seed=7):
    rng = np.random.default_rng(seed)
    ks = [int(rng.integers(0, NBAND)) for _ in range(n)]
    fd = mk_hand()
    res = {}
    # --- arm 1: handeye 完整闭环
    m = 0
    for k in ks:
        hand_press(fd, 2+k)          # 手做
        eye_write(k)                  # 世界因手而变
        kk, _ = decode(eye_read())    # 眼独立读
        m += (kk == k)
    res['handeye'] = dict(match=m, n=n, rate=m/n)
    # --- arm 2: blind 遮断眼(读旧帧, 世界已变但眼没看)
    eye_write(-1); stale = eye_read().copy()
    m = 0
    for k in ks:
        hand_press(fd, 2+k); eye_write(k)
        kk, _ = decode(stale)         # 眼没更新
        m += (kk == k)
    res['blind'] = dict(match=m, n=n, rate=m/n)
    # --- arm 3: nohand 手不动, 世界保持默认
    eye_write(-1)
    m = 0
    for k in ks:
        kk, _ = decode(eye_read())
        m += (kk == k)                # 期望读出默认, 不等于随机k
    res['nohand'] = dict(match=m, n=n, rate=m/n)
    os.close(fd)
    return res, ks

if __name__ == '__main__':
    r, ks = run()
    print(json.dumps(r, ensure_ascii=False, indent=1))
    json.dump(dict(ks=ks, **r), open('/data/workspace/luoshen-o1/experiments/exp140_real_handeye/result.json','w'), indent=1)

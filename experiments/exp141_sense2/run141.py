#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp141 · 感官扩展
  A 手性视觉：139 的保集合镜像协议，打到 140 的真实眼睛(fb0)上
  B 耳朵搜索：UDP 被动接收做 117 三检验（可证伪/时间反转/因果必要）
  C 通道复扫：117 漏掉的候选（音频/网络）
全部真实内核 I/O。
"""
import os, sys, json, time, fcntl, struct, array, socket, threading, random, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FB = "/dev/fb0"
OUT = os.path.dirname(os.path.abspath(__file__))


def fb_geometry():
    f = open(FB, "rb")
    buf = array.array("B", [0] * 160)
    fcntl.ioctl(f.fileno(), 0x4600, buf, True)  # FBIOGET_VSCREENINFO
    b = buf.tobytes()
    w, h = struct.unpack("<II", b[0:8])
    bpp = struct.unpack("<I", b[24:28])[0]
    f.close()
    return int(w), int(h), int(bpp)


W, H, BPP = fb_geometry()
BYTES = W * H * BPP // 8


def write_fb(rgba):
    with open(FB, "wb") as f:
        f.write(rgba.tobytes())


def read_fb():
    with open(FB, "rb") as f:
        return np.frombuffer(f.read(BYTES), dtype=np.uint8).copy().reshape(H, W, BPP//8)


def font(sz):
    for p in ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


# ==========================================================
# A · 手性视觉：正常图 vs 水平镜像（像素多重集完全相同）
# ==========================================================
def make_frame(side):
    """side='L' 亮块在左，'R' 亮块在右。R 是 L 的水平镜像。"""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    # 非对称图案：左块 vs 右块，颜色不同，集合相同
    if side == "L":
        d.rectangle([40, 300, 240, 500], fill=(255, 40, 40))
        d.rectangle([W - 240, 300, W - 40, 500], fill=(40, 90, 255))
    else:
        d.rectangle([W - 240, 300, W - 40, 500], fill=(255, 40, 40))
        d.rectangle([40, 300, 240, 500], fill=(40, 90, 255))
    return np.array(img, dtype=np.uint8)


def to_rgba(rgb):
    a = np.full((H, W, 4), 255, dtype=np.uint8)
    a[:, :, :3] = rgb  # 实测 fb0 = RGBA，不做反转
    return a


def decode_bag(cap_rgba):
    """非手性解码器：颜色直方图（位置无关）"""
    px = cap_rgba.reshape(-1, 4)
    red = int(np.sum((px[:, 0] > 150) & (px[:, 1] < 100)))
    blue = int(np.sum((px[:, 2] > 150) & (px[:, 0] < 100)))
    # 只看数量，不看在哪 -> 左右镜像下完全相同
    return "L" if red >= blue else "R"


def decode_pos(cap_rgba):
    """手性解码器：采样固定位置"""
    img = cap_rgba[:, :, :3]
    y0, y1 = 320, 480
    left = img[y0:y1, 60:220].reshape(-1, 3).mean(axis=0)
    right = img[y0:y1, W - 220:W - 60].reshape(-1, 3).mean(axis=0)
    # 左侧更红 -> L
    return "L" if left[0] - left[2] > right[0] - right[2] else "R"


def run_chiral():
    res = {}
    # 校验：两张图的像素多重集必须完全相同（保集合）
    fl, fr = make_frame("L"), make_frame("R")
    hl = hashlib.sha256(np.sort(fl.reshape(-1, 3), axis=0).tobytes()).hexdigest()
    hr = hashlib.sha256(np.sort(fr.reshape(-1, 3), axis=0).tobytes()).hexdigest()
    res["bag_identical"] = bool(hl == hr)
    res["bag_sha"] = hl[:16]

    out = {}
    for decname, dec in (("bag", decode_bag), ("pos", decode_pos)):
        tp = fp = n = 0
        for trial in range(6):
            for truth in ("L", "R"):
                write_fb(to_rgba(make_frame(truth)))
                cap = read_fb()
                pred = dec(cap)
                if truth == "L":
                    n += 1
                    if pred == "L":
                        tp += 1
                else:
                    if pred == "L":
                        fp += 1
        tpr = tp / max(1, n)
        fpr = fp / max(1, n)
        out[decname] = {"tpr": round(tpr, 4), "fpr": round(fpr, 4),
                        "disc": round(tpr - fpr, 4), "n": n}
    res["decoders"] = out
    return res


# ==========================================================
# B · 耳朵：UDP 被动接收（真内核 recv）
# ==========================================================
def world_sender(port, seq):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for v in seq:
        s.sendto(("%.4f" % v).encode(), ("127.0.0.1", port))
        time.sleep(0.05)
    s.close()


def run_ear():
    res = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.settimeout(0.6)
    res["port"] = port

    # --- 1 可证伪：世界发不同的值，我能否区分 ---
    heard = []
    seq = [0.0, 5.0, 10.0, 5.0, 0.0]
    t = threading.Thread(target=world_sender, args=(port, seq))
    t.start()
    got = []
    for _ in range(6):
        try:
            data, _ = sock.recvfrom(1024)
            got.append(float(data.decode()))
        except socket.timeout:
            break
    t.join()
    uniq = len(set(got))
    res["falsifiable"] = {"heard": [round(x, 4) for x in got], "unique": uniq,
                          "seq": seq}
    # 真(有信号)能区分，假(无信号)收不到
    res["falsifiable"]["pass"] = bool(uniq >= 3)

    # 假臂：世界不说话
    try:
        d, _ = sock.recvfrom(1024)
        silent = False
    except socket.timeout:
        silent = True
    res["falsifiable"]["silent_arm_ok"] = bool(silent)

    # --- 2 时间反转：能否回到初态 ---
    vals = got[:5]
    if len(vals) >= 3:
        v0, vm, v1 = vals[0], vals[len(vals) // 2], vals[-1]
        rng = abs(vm - v0) or 1.0
        resid = abs(v1 - v0) / rng
        rev = 1.0 - resid
        res["reversal"] = {"seq": [round(x, 4) for x in vals],
                           "resid": round(resid, 4), "rev": round(rev, 4)}
    # 对照：uptime（时钟，不可逆）
    u0 = float(open("/proc/uptime").read().split()[0])
    time.sleep(0.25)
    u1 = float(open("/proc/uptime").read().split()[0])
    res["reversal"]["clock_resid"] = round(abs(u1 - u0) / 0.25, 4)

    # --- 3 因果必要：遮断耳朵 ---
    # 关键设计：blind = 收到但丢弃（用上一拍），不是"收不到"。
    # 否则对照臂混进"网络不通"，不是"信息未使用"。
    # 包带 trial 序号，杜绝 UDP 缓冲区残留导致的滞后一拍。
    def sender2(port, trial, val):
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(4):
            sk.sendto(("T%d|%.4f" % (trial, val)).encode(), ("127.0.0.1", port))
            time.sleep(0.03)
        sk.close()

    def drain(sk, want_trial):
        """一直收，直到拿到本 trial 的包；返回该值或 None"""
        deadline = time.time() + 1.2
        while time.time() < deadline:
            try:
                d, _ = sk.recvfrom(1024)
                tag, v = d.decode().split("|")
                if int(tag[1:]) == want_trial:
                    return float(v)
            except socket.timeout:
                return None
        return None

    errs = {}
    for arm in ("ear", "blind"):
        s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s2.bind(("127.0.0.1", 0))
        p2 = s2.getsockname()[1]
        s2.settimeout(0.4)
        last, tot, n = 0.0, 0.0, 0
        tgts = []
        for trial in range(6):
            tgt = round(1.0 + 8.0 * random.random(), 4)
            tgts.append(tgt)
            th = threading.Thread(target=sender2, args=(p2, trial, tgt))
            th.start()
            got = drain(s2, trial)
            if arm == "ear" and got is not None:
                last = got
            # blind: 收到但丢弃，沿用上一拍的 last
            th.join()
            tot += abs(last - tgt)
            n += 1
        s2.close()
        errs[arm] = round(tot / max(1, n), 4)
        errs[arm + "_tgts"] = tgts
    res["necessity"] = errs
    res["necessity"]["delta"] = round(errs["blind"] - errs["ear"], 4)
    res["necessity"]["drop_pct"] = round(100.0*errs["blind"]/(errs["blind"]+1e-9) - 100.0*errs["ear"]/(errs["blind"]+1e-9), 2)
    sock.close()
    return res


# ==========================================================
# C · 通道复扫：117 漏掉的
# ==========================================================
def rescan():
    rows = []
    cands = ["/dev/snd/pcmC0D0c", "/dev/snd/pcmC0D0p", "/dev/snd/controlC0",
             "/dev/fb0", "/proc/uptime", "/proc/loadavg"]
    for p in cands:
        try:
            st = os.stat(p)
            rows.append({"path": p, "exists": True, "major": os.major(st.st_rdev),
                         "minor": os.minor(st.st_rdev),
                         "readable": os.access(p, os.R_OK)})
        except Exception as e:
            rows.append({"path": p, "exists": False, "err": str(e)[:60]})
    return rows


if __name__ == "__main__":
    random.seed(20261018)
    R = {"ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    R["fb_geometry"] = {"w": W, "h": H, "bpp": BPP, "bytes": BYTES}
    R["A_chiral_vision"] = run_chiral()
    R["B_ear"] = run_ear()
    R["C_rescan"] = rescan()
    with open(os.path.join(OUT, "result.json"), "w") as f:
        json.dump(R, f, indent=1, ensure_ascii=False)
    print(json.dumps(R, indent=1, ensure_ascii=False))

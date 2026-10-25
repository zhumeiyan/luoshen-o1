"""真·虚拟输入设备：直接 ioctl 与内核 uinput 对话，不用任何第三方库。
参考 linux/uinput.h —— 结构布局手工推算，不抄代码。"""
import os, struct, fcntl, time, json

UI_SET_EVBIT  = 0x40045564   # _IOW('U',100,int)
UI_SET_KEYBIT = 0x40045565   # _IOW('U',101,int)
UI_SET_RELBIT = 0x40045566   # _IOW('U',102,int)
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY= 0x5502

EV_SYN, EV_KEY, EV_REL = 0x00, 0x01, 0x02
SYN_REPORT = 0
REL_X, REL_Y = 0x00, 0x01
BUS_USB = 0x0003

# struct uinput_user_dev
def pack_udev(name, vid=0x1234, pid=0x5678):
    fmt = '80s' + 'HHHH' + 'i' + 'i'*64 + 'i'*64 + 'i'*64 + 'i'*64
    return struct.pack(fmt, name.encode(), BUS_USB, vid, pid, 0, 0,
                       *([0]*64), *([0]*64), *([0]*64), *([0]*64))

# struct input_event : timeval(2x long) + type + code + value
EV_FMT = 'llHHi'
EV_SIZE = struct.calcsize(EV_FMT)

class VDev:
    def __init__(self, name, keys=(), rels=()):
        self.fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
        if rels:
            fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_REL)
            for r in rels: fcntl.ioctl(self.fd, UI_SET_RELBIT, r)
        for k in keys: fcntl.ioctl(self.fd, UI_SET_KEYBIT, k)
        os.write(self.fd, pack_udev(name))
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        time.sleep(0.15)
        self.name = name

    def emit(self, etype, code, value):
        t = time.time()
        sec, usec = int(t), int((t - int(t)) * 1e6)
        os.write(self.fd, struct.pack(EV_FMT, sec, usec, etype, code, value))

    def syn(self): self.emit(EV_SYN, SYN_REPORT, 0)

    def tap(self, code):
        self.emit(EV_KEY, code, 1); self.syn()
        time.sleep(0.02)
        self.emit(EV_KEY, code, 0); self.syn()

    def move(self, dx, dy):
        self.emit(EV_REL, REL_X, dx); self.emit(EV_REL, REL_Y, dy); self.syn()

    def close(self):
        try: fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        except Exception: pass
        os.close(self.fd)

def find_event_node(name):
    """从 /proc/bus/input/devices 找到刚创建的设备对应的 event 节点"""
    txt = open('/proc/bus/input/devices').read()
    blocks = txt.split('\n\n')
    for b in blocks:
        if f'Name="{name}"' in b:
            for line in b.splitlines():
                if line.startswith('H:'):
                    for tok in line.split():
                        if tok.startswith('event'):
                            return '/dev/input/' + tok
    return None

def read_events(path, timeout=2.0, maxn=500):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    out = []
    t0 = time.time()
    while time.time() - t0 < timeout and len(out) < maxn:
        try:
            data = os.read(fd, EV_SIZE * 64)
        except BlockingIOError:
            time.sleep(0.01); continue
        except OSError:
            break
        for i in range(0, len(data) - EV_SIZE + 1, EV_SIZE):
            sec, usec, etype, code, val = struct.unpack(EV_FMT, data[i:i+EV_SIZE])
            out.append({'type': etype, 'code': code, 'value': val, 't': sec + usec/1e6})
    os.close(fd)
    return out

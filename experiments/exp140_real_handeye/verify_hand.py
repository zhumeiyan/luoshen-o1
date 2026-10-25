# -*- coding: utf-8 -*-
"""证明手真的动了: 创建手之后(不能之前!)重新枚举, 从内核 evdev 流读回自己的动作。"""
import os, fcntl, struct, time, json, subprocess
import sys; sys.path.insert(0,'.')
from handeye import mk_hand, hand_press

before = set(os.listdir('/dev/input'))
fd = mk_hand()                      # 先创建
time.sleep(0.3)
after = set(os.listdir('/dev/input'))
new = sorted(after - before)
print("新出现的输入设备:", new)

evs = [n for n in new if n.startswith('event')]
if not evs:
    print("FAIL: 没找到新 event 设备"); sys.exit(1)

# 用 EVIOCGNAME 确认是不是我们的手
EVIOCGNAME = 0x82004506
path = '/dev/input/' + evs[0]
nm = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
buf = bytearray(256)
try:
    n = fcntl.ioctl(nm, EVIOCGNAME, buf, True)
    print("设备名:", buf[:n].decode(errors='replace').rstrip('\x00'))
except Exception as e:
    print("EVIOCGNAME fail", e)

# 注入 3 个按键, 从内核流读回
import select
def drain(fd, t=0.4):
    out = []
    end = time.time() + t
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            try: d = os.read(fd, 24*64)
            except BlockingIOError: continue
            for i in range(0, len(d)-23, 24):
                _, _, typ, code, val = struct.unpack('llHHI', d[i:i+24])
                out.append((typ, code, val))
    return out

got = []
for kc in (2, 5, 8):
    hand_press(fd, kc)
    e = drain(nm)
    got += e
keys = [(t,c,v) for (t,c,v) in got if t == 1 and v == 1]
print(f"\n内核流读回事件总数: {len(got)}")
print(f"其中按键按下(type=1,value=1): {len(keys)}")
print("按键 code:", sorted(set(c for _,c,_ in keys)))
json.dump(dict(new_devices=new, name=buf[:n].decode(errors='replace').rstrip('\x00'),
               total_events=len(got), key_presses=len(keys),
               codes=sorted(set(c for _,c,_ in keys))),
          open('verify_hand.json','w'), ensure_ascii=False, indent=1)

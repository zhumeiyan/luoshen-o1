import os, struct, time, threading
from uinput_dev import *

name='LSILICON-KBD2'
kb=VDev(name, keys=[30,48,46,57,28])
node=find_event_node(name)
print('node:', node)

fd=os.open(node, os.O_RDONLY)   # 阻塞，先张耳
buf=[]
stop=[False]
def pump():
    while not stop[0]:
        try: d=os.read(fd, EV_SIZE*32)
        except OSError: break
        for i in range(0,len(d)-EV_SIZE+1, EV_SIZE):
            s,u,t,c,v=struct.unpack(EV_FMT,d[i:i+EV_SIZE])
            buf.append((t,c,v))
th=threading.Thread(target=pump,daemon=True); th.start()
time.sleep(0.2)

seq=[30,48,46,57,28]
for k in seq: kb.tap(k)
time.sleep(0.5); stop[0]=True; time.sleep(0.2)
os.close(fd); kb.close()

keys=[(c,v) for (t,c,v) in buf if t==EV_KEY]
downs=[c for (c,v) in keys if v==1]
ups  =[c for (c,v) in keys if v==0]
print('total events:', len(buf))
print('KEY down codes:', downs)
print('KEY up   codes:', ups)
print('MATCH down==seq:', downs==seq)
print('MATCH up==seq  :', ups==seq)

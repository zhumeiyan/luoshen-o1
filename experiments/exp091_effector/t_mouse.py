import os, struct, time, threading, json
from uinput_dev import *

name='LSILICON-MOU'
m=VDev(name, keys=[0x110,0x111,0x112], rels=[REL_X,REL_Y])  # BTN_LEFT/RIGHT/MIDDLE
node=find_event_node(name)
print('mouse node:', node)
fd=os.open(node, os.O_RDONLY)
buf=[]; stop=[False]
def pump():
    while not stop[0]:
        try: d=os.read(fd, EV_SIZE*32)
        except OSError: break
        for i in range(0,len(d)-EV_SIZE+1, EV_SIZE):
            s,u,t,c,v=struct.unpack(EV_FMT,d[i:i+EV_SIZE])
            buf.append((t,c,v))
threading.Thread(target=pump,daemon=True).start()
time.sleep(0.2)

plan=[(12,-5),(7,3),(-9,-14),(25,0),(-3,18)]
for dx,dy in plan:
    m.move(dx,dy); time.sleep(0.05)
m.emit(EV_KEY,0x110,1); m.syn(); time.sleep(0.02)
m.emit(EV_KEY,0x110,0); m.syn()
time.sleep(0.4); stop[0]=True; time.sleep(0.2)
os.close(fd); m.close()

rel=[(c,v) for (t,c,v) in buf if t==EV_REL]
xs=[v for (c,v) in rel if c==REL_X]
ys=[v for (c,v) in rel if c==REL_Y]
btn=[(c,v) for (t,c,v) in buf if t==EV_KEY]
exp_x=[p[0] for p in plan]; exp_y=[p[1] for p in plan]
print('total events :', len(buf))
print('REL_X read   :', xs, ' expected:', exp_x, ' MATCH:', xs==exp_x)
print('REL_Y read   :', ys, ' expected:', exp_y, ' MATCH:', ys==exp_y)
print('BTN events   :', btn)
json.dump(dict(node=node, xs=xs, ys=ys, exp_x=exp_x, exp_y=exp_y,
               match=(xs==exp_x and ys==exp_y), btn=btn),
          open('mouse_result.json','w'), indent=1)

import fcntl, struct, os, time, json
UI_SET_EVBIT=0x40045564; UI_SET_KEYBIT=0x40045565; UI_SET_RELBIT=0x40045566
UI_DEV_CREATE=0x5501; UI_DEV_DESTROY=0x5502
EV_KEY,EV_REL,EV_SYN=1,2,0
REL_X,REL_Y,BTN_LEFT,KEY_H=0,1,0x110,0x23
fd=os.open('/dev/uinput', os.O_WRONLY|os.O_NONBLOCK)
for req,c in ((UI_SET_EVBIT,EV_REL),(UI_SET_EVBIT,EV_KEY),(UI_SET_EVBIT,EV_SYN),
              (UI_SET_RELBIT,REL_X),(UI_SET_RELBIT,REL_Y),(UI_SET_KEYBIT,BTN_LEFT),(UI_SET_KEYBIT,KEY_H)):
    fcntl.ioctl(fd, req, c)
os.write(fd, struct.pack('80s', b'exp174-hand') + b'\x00'*(1116-80))
fcntl.ioctl(fd, UI_DEV_CREATE); time.sleep(0.3)
EV=struct.calcsize('llHHi')
seq=[("移动鼠标",EV_REL,REL_X,312),("移动鼠标",EV_REL,REL_Y,-48),("同步",EV_SYN,0,0),
     ("按下左键",EV_KEY,BTN_LEFT,1),("同步",EV_SYN,0,0),("松开左键",EV_KEY,BTN_LEFT,0),("同步",EV_SYN,0,0),
     ("敲入 h",EV_KEY,KEY_H,1),("同步",EV_SYN,0,0),("放开 h",EV_KEY,KEY_H,0),("同步",EV_SYN,0,0)]
rows=[]
print("事件结构 = %d 字节，5 个整数字段；无一是模拟量"%EV)
print("%-8s %-6s %-6s %s"%("动作","type","code","value"))
for name,t,c,v in seq:
    os.write(fd, struct.pack('llHHi',0,0,t,c,v))
    rows.append({"act":name,"type":t,"code":c,"value":v})
    print("%-8s %-6d %-6d %d"%(name,t,c,v)); time.sleep(0.004)
try: fcntl.ioctl(fd, UI_DEV_DESTROY)
except OSError: pass
os.close(fd)
json.dump({"event_bytes":EV,"seq":rows}, open('effect.json','w'), ensure_ascii=False, indent=1)
print("UINPUT_OK")

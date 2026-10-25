import os,time,struct,socket,json
import multiprocessing as mp
NSLOT=8
def agent(name,path,ps,pp,ntick,tag):
    rep={'name':name}
    t=time.time()
    fd=os.open(path,os.O_RDWR); rep['open_ms']=(time.time()-t)*1000
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(('127.0.0.1',ps)); s.settimeout(0.03)
    peer=('127.0.0.1',pp)
    t=time.time(); ok=False
    for _ in range(400):
        try:
            s.sendto(b'hi',peer); d,_=s.recvfrom(64)
            if d==b'hi': ok=True; break
        except socket.timeout: time.sleep(0.003)
    rep['handshake_s']=time.time()-t; rep['hs_ok']=ok
    t=time.time()
    def rd(): return list(struct.unpack('<8i',os.pread(fd,32,0)))
    def bump(sl):
        v=struct.unpack('<i',os.pread(fd,4,sl*4))[0]; os.pwrite(fd,struct.pack('<i',v+1),sl*4)
    prev=rd()
    for i in range(ntick):
        w=rd(); bump(i%NSLOT); prev=rd()
    rep['loop_s']=time.time()-t; rep['per_tick_ms']=rep['loop_s']/ntick*1000
    os.close(fd); s.close()
    json.dump(rep,open('diag_%s.json'%tag,'w'))
if __name__=='__main__':
    path='diagw.bin'
    open(path,'wb').write(struct.pack('<8i',*[0]*NSLOT))
    pa=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); pa.bind(('127.0.0.1',0)); AP=pa.getsockname()[1]
    pb=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); pb.bind(('127.0.0.1',0)); BP=pb.getsockname()[1]
    pa.close(); pb.close()
    NT=20
    p1=mp.Process(target=agent,args=('A',path,AP,BP,NT,'A'))
    p2=mp.Process(target=agent,args=('B',path,BP,AP,NT,'B'))
    t=time.time(); p1.start(); p2.start(); p1.join(timeout=60); p2.join(timeout=60)
    print('total %.2fs  alive: %s %s'%(time.time()-t,p1.is_alive(),p2.is_alive()))
    for n in ['A','B']:
        if os.path.exists('diag_%s.json'%n): print(n, json.load(open('diag_%s.json'%n)))

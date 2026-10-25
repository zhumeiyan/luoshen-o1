import os, sys, json, time, struct, socket, random
import multiprocessing as mp
NSLOT=8; NTICK=300

def agent(name, path, ps, pp, mode, seed, ntick, tag):
    rng=random.Random(seed)
    fd=os.open(path, os.O_RDWR)                 # 常驻 fd：沙盒 open()=21ms，不能每 tick 开
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(('127.0.0.1',ps))
    s.settimeout(0.03); peer=('127.0.0.1',pp)
    # 双向 ack 握手：单向会导致后启动者永远等不到（实测 14s 全失败）
    got_hi=False; got_ack=False; tend=time.time()+20
    while time.time()<tend and not (got_hi and got_ack):
        try: s.sendto(b'hi',peer)
        except OSError: pass
        try:
            d,_a=s.recvfrom(64)
            if d==b'hi': got_hi=True; s.sendto(b'ack',peer)
            elif d==b'ack': got_ack=True
        except socket.timeout: time.sleep(0.003)
    hs={'got_hi':got_hi,'got_ack':got_ack}
    s.settimeout(0.001)
    for _ in range(80):
        try: s.recvfrom(64)
        except socket.timeout: break
    s.settimeout(0.03)
    def rd(): return list(struct.unpack('<8i', os.pread(fd,32,0)))
    def bump(slot):
        v=struct.unpack('<i', os.pread(fd,4,slot*4))[0]
        os.pwrite(fd, struct.pack('<i',v+1), slot*4)
    g=0.5; prev=rd()
    log=dict(name=name,mode=mode,hs=hs,act=[],g=[],delta=[],world=[],peer_g=[],got=[],ts=[],io_ns=[])
    for t in range(ntick):
        w=rd()
        hi=max(range(NSLOT),key=lambda i:w[i])
        if mode=='randomB' and name=='B': act=rng.randrange(NSLOT)
        else: act = rng.choice([i for i in range(NSLOT) if i!=hi]) if g>0.5 else hi
        t0=time.time_ns(); bump(act); io=time.time_ns()-t0
        pg=None
        if mode=='tell':
            try: s.sendto(struct.pack('<Qd',t,g),peer)
            except OSError: pass
            try:
                d,_=s.recvfrom(64)
                if len(d)==16: _t2,pg=struct.unpack('<Qd',d)
            except socket.timeout: pg=None
        after=rd(); d_=[after[i]-prev[i] for i in range(NSLOT)]
        # 原版只升不降->g_self卡在0.56~0.95,策略锁死,读心任务退化。
        # 改为 OU 内在节律(均值回归+真高斯噪声) + 碰撞反馈, 保证双向跨越 0.5
        g += -0.08*(g-0.5) + rng.gauss(0,0.05)
        if d_[act]>=2: g -= 0.03      # 同槽碰撞 = 竞争受阻
        g=min(0.95,max(0.05,g))
        log['act'].append(act); log['g'].append(g); log['delta'].append(d_)
        log['world'].append(after[:]); log['peer_g'].append(pg)
        log['got'].append(pg is not None); log['ts'].append(t); log['io_ns'].append(io)
        prev=after[:]
    os.close(fd); s.close()
    json.dump(log, open('log_%s.json'%tag,'w'))

def run_pair(mode, ntick=NTICK, seedA=1, seedB=2):
    here=os.path.dirname(os.path.abspath(__file__))
    path=os.path.join(here,'world_%s.bin'%mode)
    with open(path,'wb') as f: f.write(struct.pack('<8i',*[0]*NSLOT))
    pa=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); pa.bind(('127.0.0.1',0)); AP=pa.getsockname()[1]
    pb=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); pb.bind(('127.0.0.1',0)); BP=pb.getsockname()[1]
    pa.close(); pb.close()
    p1=mp.Process(target=agent,args=('A',path,AP,BP,mode,seedA,ntick,'A_'+mode))
    p2=mp.Process(target=agent,args=('B',path,BP,AP,mode,seedB,ntick,'B_'+mode))
    t0=time.time(); p1.start(); p2.start(); p1.join(timeout=600); p2.join(timeout=600)
    el=time.time()-t0
    got={}
    for nm in ['A','B']:
        fn=os.path.join(here,'log_%s_%s.json'%(nm,mode))
        got[nm]=json.load(open(fn)) if os.path.exists(fn) else {'act':[]}
    print('  mode=%-8s %.1fs  lenA=%d lenB=%d'%(mode,el,len(got['A']['act']),len(got['B']['act'])))
    return got

if __name__=='__main__':
    out={}
    for mode in ['base','tell','randomB']:
        out[mode]=run_pair(mode)
    json.dump(out,open('raw149.json','w'))
    print('saved raw149.json')

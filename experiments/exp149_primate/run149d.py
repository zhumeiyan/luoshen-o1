import os, socket, json, time, random, struct
import multiprocessing as mp

# 真实地形：先枚举一次（真 I/O）
def terrain(root='/usr/lib/python3.10', cap=400):
    out=[]
    for dp,dn,fn in os.walk(root):
        out.append(dp)
        if len(out)>=cap: break
    return out[:cap]

def explorer(name, dirs, ps, pp, talk, budget, seed, tag):
    rng=random.Random(seed)
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(('127.0.0.1',ps))
    s.settimeout(0.02); peer=('127.0.0.1',pp)
    gh=ga=False; tend=time.time()+15
    while time.time()<tend and not(gh and ga):
        try: s.sendto(b'hi',peer)
        except OSError: pass
        try:
            d,_=s.recvfrom(64)
            if d==b'hi': gh=True; s.sendto(b'ack',peer)
            elif d==b'ack': ga=True
        except socket.timeout: time.sleep(0.003)
    known=set(); mine=[]; dup=0; io_ms=[]
    for i in range(budget):
        # 选一个自己还没探索、且（若通信）对方也没报过的
        cand=[d for d in dirs if d not in known]
        if not cand: break
        pick=rng.choice(cand)
        t0=time.time()
        try: n=len(list(os.scandir(pick)))   # 真 I/O：真实探索动作
        except OSError: n=0
        io_ms.append((time.time()-t0)*1000)
        known.add(pick); mine.append(pick)
        if talk:
            try: s.sendto(pick.encode()[:200],peer)
            except OSError: pass
            try:
                d,_=s.recvfrom(256)
                if d not in (b'hi',b'ack'): known.add(d.decode(errors='ignore'))
            except socket.timeout: pass
    s.close()
    json.dump({'name':name,'talk':talk,'mine':mine,'io_ms':io_ms},open('log_%s.json'%tag,'w'))

if __name__=='__main__':
    dirs=terrain()
    print('terrain dirs=%d'%len(dirs))
    res={}
    for rep in range(5):
     for talk in [True,False]:
        pa=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); pa.bind(('127.0.0.1',0)); AP=pa.getsockname()[1]
        pb=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); pb.bind(('127.0.0.1',0)); BP=pb.getsockname()[1]
        pa.close(); pb.close()
        tag='coop' if talk else 'solo'
        p1=mp.Process(target=explorer,args=('A',dirs,AP,BP,talk,30,100+rep,'A_'+tag))
        p2=mp.Process(target=explorer,args=('B',dirs,BP,AP,talk,30,200+rep,'B_'+tag))
        t0=time.time(); p1.start(); p2.start(); p1.join(timeout=300); p2.join(timeout=300)
        A=json.load(open('log_A_%s.json'%tag)); B=json.load(open('log_B_%s.json'%tag))
        uniq=len(set(A['mine'])|set(B['mine'])); tot=len(A['mine'])+len(B['mine'])
        ov=len(set(A['mine'])&set(B['mine']))
        eff=uniq/max(1,tot)
        print(' rep%d talk=%-5s %.1fs 探索%d/%d 唯一=%d 重复=%d 效率=%.4f'%(rep,talk,time.time()-t0,len(A['mine']),len(B['mine']),uniq,ov,eff))
        eff=uniq/max(1,tot)
        res.setdefault('coop' if talk else 'solo',[]).append(dict(uniq=uniq,tot=tot,overlap=ov,eff=eff))
    json.dump(res,open('res149d.json','w'))
    print('saved')

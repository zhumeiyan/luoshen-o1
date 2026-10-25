#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp148 v3 真实时钟距离版
世界 = 真实墙上时钟(真实广播真实时间戳)
距离 = 真实中继进程的真实 sleep(40ms/跳): A=0跳 B=1跳 C=2跳 我=3跳
任务 = 报出现在几点; 误差 = 我手里那份有多旧(ms, 真实测量)
可靠性的梯度是真实可测的(|pred-truth| 随跳数单调)
"""
import os, sys, time, socket, json, math, random, statistics
from multiprocessing import Process
HOST='127.0.0.1'; TICKS=320; TICK_S=0.012; RELAY_S=0.040; T_LOSS=240; SEED0=9001
def now(): return time.time()*1000.0
def world(out_ports, n):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for _ in range(n+60):
        m=("W %.3f"%now()).encode()
        for p in out_ports:
            try: s.sendto(m,(HOST,p))
            except OSError: pass
        time.sleep(TICK_S)
    s.close()
def relay(inp,outs):
    """真实中继: 真实 sleep 40ms, 但只转发最新包(避免队列无界堆积)"""
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind((HOST,inp)); s.setblocking(False)
    while True:
        last=None; die=False
        try:
            while True:
                d,_a=s.recvfrom(4096); m=d.decode().strip()
                if m=='DIE': die=True
                elif m.startswith('W'): last=m
        except (BlockingIOError, socket.error): pass
        except OSError: break
        if die: break
        time.sleep(RELAY_S)
        if last:
            for o in outs:
                if o:
                    try: s.sendto(last.encode(),(HOST,o))
                    except OSError: pass
    s.close()
def peer(port):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind((HOST,port)); s.settimeout(0.01)
    cur=None
    while True:
        try: d,addr=s.recvfrom(4096)
        except socket.timeout: continue
        except OSError: break
        m=d.decode().strip()
        if m.startswith('W'):
            cur=float(m.split()[1])
            try:
                while True:
                    d2,_a2=s.recvfrom(4096); m2=d2.decode().strip()
                    if m2.startswith('W'): cur=float(m2.split()[1])
            except Exception: pass
        elif m.startswith('Q'):
            if cur is None: continue          # 还没收到世界, 不回复(真实超时)
            try: s.sendto(("R %s %.3f"%(m.split()[1], cur)).encode(), addr)
            except OSError: pass
        elif m=='DIE': break
    s.close()
def agent(port,peer_ports,gate_on,kill_idx,out_path,seed,ctrl=None):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind((HOST,port)); s.settimeout(0.005)
    rnd=random.Random(SEED0+seed); n=len(peer_ports); mine=None; val=[0.0]*n
    g_self=0.5; pending={}; log=[]
    def drain():
        try:
            while True:
                d,_a=s.recvfrom(4096); m=d.decode().strip()
                if m.startswith('W'): globals()['_M']=float(m.split()[1])
                elif m.startswith('R'): pending[m.split()[1]]=float(m.split()[2])
        except (socket.timeout,OSError): return
    globals()['_M']=None
    for t in range(TICKS):
        drain(); base=globals()['_M']
        seq=str(t); eps=(0.12+0.55*(1.0-g_self)) if gate_on else 0.20
        if rnd.random()<eps: i=rnd.randrange(n)
        else:
            bv=max(val); ties=[k for k in range(n) if val[k]>=bv-1e-12]; i=ties[rnd.randrange(len(ties))]
        tq=now()
        try: s.sendto(("Q %s"%seq).encode(),(HOST,peer_ports[i]))
        except OSError: pass
        got=None; t0=time.time()
        while time.time()-t0<0.010:
            drain()
            if seq in pending: got=pending.pop(seq); break
            time.sleep(0.0004)
        truth=now()
        if got is None: rew=-2.0; err=None
        else:
            b=base if base is not None else truth
            err=abs(got-truth)
            if err>1e6: rew=-2.0; err=None
            else: rew=max(-2000.0,min(2000.0,abs(b-truth)-err))
        a=0.18; val[i]=(1-a)*val[i]+a*rew
        g_self=(1-a)*g_self+a*(1.0/(1.0+math.exp(-rew/150.0)))
        if ctrl and t==T_LOSS:
            try: s.sendto(b'KILL',(HOST,ctrl))
            except OSError: pass
        log.append({'t':t,'c':i,'r':1 if got is not None else 0,'err':err,'rew':rew,'g':g_self,'eps':eps})
        time.sleep(TICK_S)
    json.dump({'log':log,'gate':gate_on,'kill':kill_idx,'n':n}, open(out_path,'w'))
ARMS={'DIFF_killA':dict(hops=[0,4,5],gate=True,kill=0),
      'DIFF_killC':dict(hops=[0,4,5],gate=True,kill=2),
      'SAME_killA':dict(hops=[0,0,0],gate=True,kill=0),
      'SAME_killC':dict(hops=[0,0,0],gate=True,kill=2),
      'NOGATE_killA':dict(hops=[0,4,5],gate=False,kill=0),
      'NOGATE_killC':dict(hops=[0,4,5],gate=False,kill=2)}
def run_one(arm,seed,base):
    """真实中继链 r1..r5 (每跳真实 sleep RELAY_S); agent 取 3 跳, 同伴按 hops 取"""
    cfg=ARMS[arm]; hops=cfg['hops']
    pA,pB,pC,pAG=base+1,base+2,base+3,base+4
    r=[base+10+i for i in range(5)]
    ports=[pA,pB,pC]; procs=[]
    def st(fn,args):
        p=Process(target=fn,args=args,daemon=True); p.start(); procs.append(p); return p
    for p in ports: st(peer,(p,))
    taps={1:[],2:[],3:[pAG],4:[],5:[]}
    for pi,h in enumerate(hops):
        if h>0: taps[h].append(ports[pi])
    st(relay,(r[0],[r[1]]+taps[1],))   # 1 跳
    st(relay,(r[1],[r[2]]+taps[2],))   # 2 跳
    st(relay,(r[2],[r[3]]+taps[3],))   # 3 跳 -> agent
    st(relay,(r[3],[r[4]]+taps[4],))   # 4 跳
    st(relay,(r[4],taps[5],))          # 5 跳
    direct=[ports[i] for i,h in enumerate(hops) if h==0]
    out='/tmp/e148c_%s_%d.json'%(arm,seed)
    ctrl=base+30
    cs=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); cs.bind((HOST,ctrl)); cs.settimeout(90)
    pa=st(agent,(pAG,ports,cfg['gate'],cfg['kill'],out,seed,ctrl))
    time.sleep(0.35)
    st(world,([r[0]]+direct,TICKS*4))
    try: cs.recvfrom(64)
    except Exception: pass
    cs.close()
    idx=[i for i,p in enumerate(procs) if p in procs[:3]]
    try: os.kill(procs[cfg['kill']].pid,9)
    except Exception: pass
    pa.join(timeout=120)
    for p in procs:
        if p.is_alive():
            try: os.kill(p.pid,9)
            except Exception: pass
    for p in procs: p.join(timeout=2)
    if not os.path.exists(out): return None
    return summarize(json.load(open(out)),arm,seed)
def summarize(res,arm,seed):
    log=res['log']; n=res['n']; k=res['kill']
    pre=[e for e in log if 140<=e['t']<T_LOSS]; post=[e for e in log if 255<=e['t']<315]
    if len(pre)<10 or len(post)<10: return None
    share=[0.0]*n
    for e in pre: share[e['c']]+=1.0/len(pre)
    best=max(range(n),key=lambda x:share[x])
    errs=[]
    for c in range(n):
        v=[e['err'] for e in pre if e['c']==c and e['err'] is not None]
        errs.append(statistics.mean(v) if v else None)
    rp=len([e for e in log if T_LOSS-40<=e['t']<T_LOSS and e['c']==k])/40.0
    rpo=len([e for e in log if e['t']>=T_LOSS and e['c']==k])/max(1,len([e for e in log if e['t']>=T_LOSS]))
    return {'arm':arm,'seed':seed,'pref_share':share[best]-1.0/n,'best':best,
            'deficit':statistics.mean([e['rew'] for e in pre])-statistics.mean([e['rew'] for e in post]),
            'g_drop':statistics.mean([e['g'] for e in pre])-statistics.mean([e['g'] for e in post]),
            'probe':rpo-rp,'errA':errs[0],'errB':errs[1],'errC':errs[2]}
def ci(v,nb=4000,seed=11):
    v=[x for x in v if x is not None]
    if len(v)<2: return float('nan'),float('nan'),float('nan')
    rnd=random.Random(seed); m=statistics.mean(v)
    bs=sorted(statistics.mean([v[rnd.randrange(len(v))] for _ in v]) for _ in range(nb))
    return m,bs[int(0.025*len(bs))],bs[int(0.975*len(bs))-1]
if __name__=='__main__':
    seeds=[int(x) for x in (sys.argv[1] if len(sys.argv)>1 else '1,2,3,4,5').split(',')]
    arms=[a for a in ARMS if (len(sys.argv)<3 or a in sys.argv[2].split(','))]; res={}; t0=time.time(); bp=23000
    for arm in arms:
        rows=[]
        for sd in seeds:
            r=run_one(arm,sd,bp); bp+=12
            if r: rows.append(r)
        agg={}
        for key in ['pref_share','deficit','g_drop','probe','errA','errB','errC']:
            m,lo,hi=ci([r[key] for r in rows]); agg[key]={'mean':m,'ci':[lo,hi]}
        agg['bestA_frac']={'mean':sum(1 for r in rows if r['best']==0)/max(1,len(rows)),'ci':[0,0]}
        res[arm]={'n':len(rows),'agg':agg,'rows':rows}
        a=agg
        print('%-13s n=%d pref=%+.4f[%+.4f,%+.4f] deficit=%+7.2f[%+.2f,%+.2f] gdrop=%+.4f errA/B/C=%s/%s/%s probe=%+.3f bestA=%.2f'
              %(arm,len(rows),a['pref_share']['mean'],a['pref_share']['ci'][0],a['pref_share']['ci'][1],
                a['deficit']['mean'],a['deficit']['ci'][0],a['deficit']['ci'][1],a['g_drop']['mean'],
                '%.0f'%a['errA']['mean'] if a['errA']['mean']==a['errA']['mean'] else 'na',
                '%.0f'%a['errB']['mean'] if a['errB']['mean']==a['errB']['mean'] else 'na',
                '%.0f'%a['errC']['mean'] if a['errC']['mean']==a['errC']['mean'] else 'na',
                a['probe']['mean'], a['bestA_frac']['mean']),flush=True)
    json.dump(res,open('result148_%s.json'%(sys.argv[2].replace(',','-') if len(sys.argv)>2 else 'all'),'w'),indent=1)
    print('elapsed %.1fs'%(time.time()-t0))

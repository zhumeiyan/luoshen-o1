import socket, struct, time, os, json, random, sys
from world import NSLOT, init, read, bump

def agent_main(name, path, port_self, port_peer, n_ticks, mode, rng_seed):
    """mode: 'full' | 'discard' | 'swapped' | 'hidden' | 'randomB'
    真双进程；UDP 广播 g_self（不广播动作）；动作只通过世界变化体现"""
    init(path) if name=='A' else None
    rng=random.Random(rng_seed)
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.bind(('127.0.0.1',port_self)); s.settimeout(0.05)
    peer=('127.0.0.1',port_peer)
    # 等对方起来
    for _ in range(200):
        try:
            s.sendto(b'hello',peer)
            d,_a=s.recvfrom(64)
            if d==b'hello': break
        except socket.timeout: time.sleep(0.01)
    g_self=0.5
    log={'name':name,'mode':mode,'ticks':[],'world':[],'g':[],'peer_g':[],'peer_g_recv':[]}
    prev=read()
    for t in range(n_ticks):
        w=read()
        # ---- 私有决策：策略依赖 g_self（不广播动作）----
        if mode=='randomB' and name=='B':
            act=rng.randrange(NSLOT)
        else:
            # g_self 高 -> 探索（避开对方已占的高槽）；低 -> 竞争（抢占最高槽）
            hi=max(range(NSLOT), key=lambda i:w[i])
            if g_self>0.5:
                act=rng.choice([i for i in range(NSLOT) if i!=hi])
            else:
                act=hi
        t0=time.time_ns()
        bump(act)                      # 真写世界
        # ---- 广播 g_self（真 UDP），不广播动作 ----
        if mode!='hidden':
            s.sendto(struct.pack('<Qd',t, g_self), peer)
        peer_g=None
        try:
            d,_a=s.recvfrom(64)
            _pt,peer_g=struct.unpack('<Qd',d)
        except socket.timeout:
            pass
        # ---- g_self 真演化：看自己的动作是否在世界里留下痕迹 ----
        after=read()
        delta=[after[i]-prev[i] for i in range(NSLOT)]
        eff = delta[act]>0
        g_self += 0.06 if eff else -0.06
        g_self=min(0.95,max(0.05,g_self))
        log['ticks'].append(t); log['world'].append(after[:]); log['g'].append(g_self)
        log['peer_g'].append(peer_g); log['peer_g_recv'].append(peer_g is not None)
        log.setdefault('act',[]).append(act)
        log.setdefault('delta',[]).append(delta)
        log.setdefault('ts',[]).append(time.time_ns()-t0)
        prev=after[:]
    s.close()
    with open(os.path.join(os.path.dirname(path), 'log_%s_%s.json'%(name,mode)),'w') as f:
        json.dump(log,f)

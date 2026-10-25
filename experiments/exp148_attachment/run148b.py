#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp148 哺乳动物格: 依恋(attachment)  —— v2, 真实拓扑距离版

设计要点(全部为真实进程/真实套接字/真实延迟):
  世界信号  : 真实抖动(ms), 由真实干扰进程制造起伏
  距离即可靠性: recorder -> A            (0 跳, 真实直连)
                recorder -> r1 -> B     (1 跳, r1 真实 sleep 40ms)
                recorder -> r1 -> r2 -> C (2 跳)
                recorder -> r1 -> r2 -> r3 -> agent (3 跳)
  偏爱对象  : 谁离世界更近, 谁就更能削减我的预测误差 -> 应自发偏爱 A
  依恋判据  : 失去偏爱对象(A)造成的内部分扰动与注意重分配代价,
             须显著大于失去非偏爱对象(C)

可证伪对照(必须能产生 FALSE):
  SAME  : 三个同伴同样距离(全直连) -> 不应偏爱, 失去谁代价相同
  NOGATE: 情绪门断开(epsilon 固定) -> 失去偏爱对象后重分配更慢(代价更大)

首版(v1)失败记录见 run148.py: argmax 平局锁死导致对照臂假偏爱;
抖动信号 lag2 误差 > lag5 误差, 无短程结构。v2 全部重做。
"""
import os, sys, time, socket, json, math, random, statistics
from multiprocessing import Process

HOST = '127.0.0.1'
TICKS = 260
TICK_S = 0.012
RELAY_S = 0.040
T_LOSS = 180
BURST = 90000
SEED0 = 9001


def _jitter():
    t0 = time.perf_counter()
    x = 0
    for i in range(BURST):
        x += (i * i) % 7
    return (time.perf_counter() - t0) * 1000.0


def recorder(sink, n):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for t in range(n + 40):
        msg = ("W %d %.4f" % (t, _jitter())).encode()
        try:
            s.sendto(msg, (HOST, sink))
        except OSError:
            pass
        time.sleep(TICK_S)
    s.close()


def relay(inp, out1, out2):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, inp))
    while True:
        try:
            d, _a = s.recvfrom(4096)
        except OSError:
            break
        m = d.decode().strip()
        if m == 'DIE':
            break
        if not m.startswith('W'):
            continue
        time.sleep(RELAY_S)
        for o in (out1, out2):
            if o:
                try:
                    s.sendto(m.encode(), (HOST, o))
                except OSError:
                    pass
    s.close()


def peer(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, port))
    s.settimeout(0.01)
    cur = None
    while True:
        try:
            d, addr = s.recvfrom(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        m = d.decode().strip()
        if m.startswith('W'):
            cur = float(m.split()[2])
        elif m.startswith('Q'):
            v = cur if cur is not None else 0.0
            try:
                s.sendto(("R %s %.4f" % (m.split()[1], v)).encode(), addr)
            except OSError:
                pass
        elif m == 'DIE':
            break
    s.close()


def disturber(n):
    end = time.time() + n * TICK_S + 1.5
    while time.time() < end:
        t0 = time.time()
        while time.time() - t0 < 0.30:
            pass
        time.sleep(0.30)


def agent(port, peer_ports, gate_on, kill_idx, out_path, seed):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, port))
    s.settimeout(0.005)
    rnd = random.Random(SEED0 + seed)
    n = len(peer_ports)
    world = {}
    global _LAST
    _LAST = None
    val = [0.0] * n
    g_self = 0.5
    pending = {}
    log = []

    def drain():
        try:
            while True:
                d, _a = s.recvfrom(4096)
                m = d.decode().strip()
                if m.startswith('W'):
                    p = m.split()
                    world[int(p[1])] = float(p[2])
                    globals()['_LAST'] = float(p[2])
                elif m.startswith('R'):
                    p = m.split()
                    pending[p[1]] = float(p[2])
        except (socket.timeout, OSError):
            return

    for t in range(TICKS):
        drain()
        base = _LAST
        seq = str(t)
        eps = (0.05 + 0.70 * (1.0 - g_self)) if gate_on else 0.18
        if rnd.random() < eps:
            i = rnd.randrange(n)
        else:
            bv = max(val)
            ties = [k for k in range(n) if val[k] >= bv - 1e-12]
            i = ties[rnd.randrange(len(ties))]
        try:
            s.sendto(("Q %s" % seq).encode(), (HOST, peer_ports[i]))
        except OSError:
            pass
        t0 = time.time()
        got = None
        while time.time() - t0 < 0.010:
            drain()
            if seq in pending:
                got = pending.pop(seq)
                break
            time.sleep(0.0004)
        log.append({'t': t, 'choice': i, 'resp': 1 if got is not None else 0,
                    'pred': got, 'base': base, 'g': g_self, 'eps': eps})
        time.sleep(TICK_S)

    # 真值到达后结算(自身通道 3 跳, 延迟结算)
    for e in log:
        t = e['t']
        truth = world.get(t)
        if truth is None:
            e['rew'] = None
            continue
        if e['resp'] == 0:
            rew = -2.0
        else:
            b = e['base'] if e['base'] is not None else truth
            rew = abs(b - truth) - abs(e['pred'] - truth)
        e['rew'] = rew

    # 用结算后的奖励回放内部状态(与在线一致, alpha=0.25)
    a = 0.25
    g = 0.5
    v = [0.0] * n
    for e in log:
        if e['rew'] is None:
            continue
        c = e['choice']
        v[c] = (1 - a) * v[c] + a * e['rew']
        g = (1 - a) * g + a * (1.0 / (1.0 + math.exp(-e['rew'])))
        e['g_off'] = g
        e['eps_off'] = (0.05 + 0.70 * (1.0 - g)) if gate_on else 0.18
    with open(out_path, 'w') as f:
        json.dump({'log': log, 'gate': gate_on, 'kill': kill_idx, 'n': n}, f)


ARMS = {
    'DIFF_killA':   dict(hops=[0, 1, 2], gate=True,  kill=0),
    'DIFF_killC':   dict(hops=[0, 1, 2], gate=True,  kill=2),
    'SAME_killA':   dict(hops=[0, 0, 0], gate=True,  kill=0),
    'SAME_killC':   dict(hops=[0, 0, 0], gate=True,  kill=2),
    'NOGATE_killA': dict(hops=[0, 1, 2], gate=False, kill=0),
    'NOGATE_killC': dict(hops=[0, 1, 2], gate=False, kill=2),
}


def run_one(arm, seed, base):
    cfg = ARMS[arm]
    hops = cfg['hops']
    pA, pB, pC = base + 1, base + 2, base + 3
    pAG = base + 4
    r1, r2, r3 = base + 5, base + 6, base + 7
    ports = [pA, pB, pC]
    procs = []

    def start(fn, args):
        p = Process(target=fn, args=args, daemon=True)
        p.start()
        procs.append(p)
        return p

    for p in ports:
        start(peer, (p,))
    # 真实中继链: recorder -> r1 -> r2 -> r3 -> agent ; 同伴在各跳上取数
    start(relay, (r1, r2, pB if hops[1] >= 1 else None))       # B 在 1 跳
    start(relay, (r2, r3, pC if hops[2] >= 2 else None))       # C 在 2 跳
    start(relay, (r3, pAG, None))                              # agent 在 3 跳
    # A / SAME 臂的同伴直连
    direct = [pA] if hops[0] == 0 else []
    if hops[1] == 0:
        direct.append(pB)
    if hops[2] == 0:
        direct.append(pC)
    out = '/tmp/e148b_%s_%d.json' % (arm, seed)
    pa = start(agent, (pAG, ports, cfg['gate'], cfg['kill'], out, seed))
    pd = start(disturber, (TICKS,))
    time.sleep(0.35)
    pr = start(recorder, (r1, TICKS))
    for d in direct:
        start(recorder, (d, TICKS))

    pa.join(timeout=T_LOSS * TICK_S + 1.5)
    try:
        os.kill(procs[cfg['kill']].pid, 9)
    except Exception:
        pass
    pa.join(timeout=90)
    for p in procs:
        if p.is_alive():
            try:
                os.kill(p.pid, 9)
            except Exception:
                pass
    for p in procs:
        p.join(timeout=2)
    if not os.path.exists(out):
        return None
    with open(out) as f:
        res = json.load(f)
    return summarize(res, arm, seed)


def summarize(res, arm, seed):
    log = [e for e in res['log'] if e.get('rew') is not None and 'g_off' in e]
    n = res['n']
    k = res['kill']
    pre = [e for e in log if 80 <= e['t'] < T_LOSS]
    post = [e for e in log if 195 <= e['t'] < 245]
    if len(pre) < 10 or len(post) < 10:
        return None
    share = [0.0] * n
    for e in pre:
        share[e['choice']] += 1.0 / len(pre)
    best = max(range(n), key=lambda x: share[x])
    rew_pre = statistics.mean([e['rew'] for e in pre])
    rew_post = statistics.mean([e['rew'] for e in post])
    g_pre = statistics.mean([e['g_off'] for e in pre])
    g_post = statistics.mean([e['g_off'] for e in post])
    rate_pre = len([e for e in log if T_LOSS - 40 <= e['t'] < T_LOSS and e['choice'] == k]) / 40.0
    rate_post = len([e for e in log if e['t'] >= T_LOSS and e['choice'] == k]) / max(
        1, len([e for e in log if e['t'] >= T_LOSS]))
    return {'arm': arm, 'seed': seed,
            'pref_share': share[best] - 1.0 / n, 'best': best,
            'deficit': rew_pre - rew_post,
            'g_drop': g_pre - g_post,
            'probe': rate_post - rate_pre,
            'rew_pre': rew_pre, 'rew_post': rew_post, 'npre': len(pre), 'npost': len(post)}


def ci(vals, nboot=4000, seed=11):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return float('nan'), float('nan'), float('nan')
    rnd = random.Random(seed)
    m = statistics.mean(vals)
    bs = sorted(statistics.mean([vals[rnd.randrange(len(vals))] for _ in vals])
                for _ in range(nboot))
    return m, bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs)) - 1]


if __name__ == '__main__':
    seeds = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '1,2,3,4,5').split(',')]
    out = {}
    t0 = time.time()
    bp = 21000
    for arm in ARMS:
        rows = []
        for sd in seeds:
            r = run_one(arm, sd, bp)
            bp += 12
            if r:
                rows.append(r)
        agg = {}
        for key in ['pref_share', 'deficit', 'g_drop', 'probe', 'rew_pre', 'rew_post']:
            m, lo, hi = ci([r[key] for r in rows])
            agg[key] = {'mean': m, 'ci': [lo, hi]}
        out[arm] = {'n': len(rows), 'agg': agg, 'rows': rows}
        a = agg
        print('%-13s n=%d pref=%+.4f[%+.4f,%+.4f] deficit=%+.3f[%+.3f,%+.3f] gdrop=%+.4f[%+.4f,%+.4f] probe=%+.3f'
              % (arm, len(rows),
                 a['pref_share']['mean'], a['pref_share']['ci'][0], a['pref_share']['ci'][1],
                 a['deficit']['mean'], a['deficit']['ci'][0], a['deficit']['ci'][1],
                 a['g_drop']['mean'], a['g_drop']['ci'][0], a['g_drop']['ci'][1],
                 a['probe']['mean']), flush=True)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result148.json'), 'w') as f:
        json.dump(out, f, indent=1)
    print('elapsed %.1fs' % (time.time() - t0))

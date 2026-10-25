#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp148 哺乳动物格: 依恋(attachment)
验收标准: 偏爱对象有特殊反应(preferred object elicits a distinctive response)

真机实现:
  - 真实 UDP 进程间通信 (recorder / 3 个 peer / agent)
  - 世界信号 = 真实抖动(ms): 固定计算量的真实耗时, 由真实干扰进程制造真实起伏
  - 可靠性的差异是真实的: A 用最新真值, B 用 2 拍前的真值, C 用 os.urandom 真实随机数
  - 依恋判据 = 失去偏爱对象后的抗议行为(搜索率上升 + g_self 下跌), 且须强于失去非偏爱对象

可证伪对照(必须能产生 FALSE):
  SAME    : 三个 peer 一样可靠 -> 不应形成偏爱, 失去谁都一样
  NO_GATE : 情绪门断开(epsilon 固定) -> 不应出现抗议上升
  SHUFFLE : 可靠性每 30 拍随机重排 -> 不应形成稳定偏爱
"""
import os, sys, time, socket, json, math, random
from collections import deque
from multiprocessing import Process

HOST = '127.0.0.1'
TICKS = 240
TICK_S = 0.012
T_LOSS = 200
BURST = 90000          # 真实计算量
LAG_AGENT = 5          # agent 自身通道延迟(建模)
LAG_STALE = 2          # peer B 延迟(真实队列)


def _jitter_measure():
    t0 = time.perf_counter()
    x = 0
    for i in range(BURST):
        x += (i * i) % 7
    return (time.perf_counter() - t0) * 1000.0, x


def recorder(ports, stop_n):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for t in range(stop_n):
        dt, _ = _jitter_measure()
        msg = ("W %d %.4f" % (t, dt)).encode()
        for p in ports:
            try:
                s.sendto(msg, (HOST, p))
            except OSError:
                pass
        time.sleep(TICK_S)
    s.close()


def disturber(stop_n):
    """真实干扰进程: 交替忙/闲, 制造真实负载起伏"""
    end = time.time() + stop_n * TICK_S + 1.0
    while time.time() < end:
        t0 = time.time()
        x = 0
        while time.time() - t0 < 0.35:
            x += 1
        time.sleep(0.35)


def peer(port, mode):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, port))
    s.settimeout(0.01)
    buf = deque(maxlen=64)
    while True:
        try:
            data, addr = s.recvfrom(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        m = data.decode().strip()
        if m.startswith('W'):
            buf.append(float(m.split()[2]))
        elif m.startswith('Q'):
            seq = m.split()[1]
            if mode == 'switch':
                tt = int(m.split()[1])
                mode_now = 'fresh' if (tt // 30) % 2 == 0 else 'random'
            else:
                mode_now = mode
            if mode_now == 'fresh':
                v = buf[-1] if buf else 0.0
            elif mode_now == 'stale':
                v = buf[-1 - LAG_STALE] if len(buf) > LAG_STALE else (buf[0] if buf else 0.0)
            else:  # random: 真实 OS 随机数
                raw = int.from_bytes(os.urandom(4), 'big') / float(2 ** 32)
                v = raw * 12.0
            try:
                s.sendto(("R %s %.4f" % (seq, v)).encode(), addr)
            except OSError:
                pass
        elif m == 'DIE':
            break
    s.close()


def agent(port, peer_ports, modes, gate_on, shuffle_every, kill_idx, out_path, SEED=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, port))
    s.settimeout(0.008)
    world = {}
    latest = [-1]
    n = len(peer_ports)
    val = [0.0] * n
    seen = [0] * n
    g_self = 0.5
    log = []
    rnd = random.Random(9001 + SEED)

    def recv_world_nonblock():
        try:
            while True:
                d, _a = s.recvfrom(4096)
                m = d.decode().strip()
                if m.startswith('W'):
                    p = m.split()
                    world[int(p[1])] = float(p[2])
                    latest[0] = max(latest[0], int(p[1]))
                elif m.startswith('R'):
                    p = m.split()
                    pending[p[1]] = float(p[2])
        except socket.timeout:
            return
        except OSError:
            return

    pending = {}
    last_pred = {}
    for t in range(TICKS):
        # 1) 收世界广播
        recv_world_nonblock()
        # 等到达最新 (最多 ~40ms)
        t_w0 = time.time()
        while latest[0] < t and time.time() - t_w0 < 0.05:
            recv_world_nonblock()
            time.sleep(0.001)
        truth = world.get(t)
        if truth is None:
            log.append({'t': t, 'skip': 1})
            time.sleep(TICK_S)
            continue

        # 2) 可靠性重排 (SHUFFLE 臂): 交换 peer 端口对应的角色
        # 3) 自身基线 (建模: 自身通道延迟)
        obs = world.get(t - LAG_AGENT)
        if obs is None:
            obs = truth
        base_err = abs(obs - truth)

        # 4) 选 peer: epsilon 由 g_self 门控
        eps = (0.05 + 0.70 * (1.0 - g_self)) if gate_on else 0.18
        if rnd.random() < eps:
            i = rnd.randrange(n)
        else:
            bestv = max(val)
            ties = [k for k in range(n) if val[k] >= bestv - 1e-12]
            i = ties[rnd.randrange(len(ties))]
        choice = i

        # 5) 真实发问
        seq = str(t)
        got = None
        try:
            s.sendto(("Q %s" % seq).encode(), (HOST, peer_ports[choice]))
        except OSError:
            pass
        t0 = time.time()
        while time.time() - t0 < 0.010:
            recv_world_nonblock()
            if seq in pending:
                got = pending.pop(seq)
                break
            time.sleep(0.0005)

        # 6) 真实奖励 = 误差削减 (ms)
        if got is None:
            rew = -2.0            # 无回应
            responded = 0
        else:
            rew = base_err - abs(got - truth)
            responded = 1
        a = 0.25
        val[choice] = (1 - a) * val[choice] + a * rew
        seen[choice] += 1
        # g_self: 近期奖励的门控变量
        g_self = (1 - a) * g_self + a * (1.0 / (1.0 + math.exp(-rew)))

        log.append({'t': t, 'choice': choice, 'rew': rew, 'g': g_self,
                    'eps': eps, 'resp': responded, 'base': base_err})
        time.sleep(TICK_S)

    with open(out_path, 'w') as f:
        json.dump({'log': log, 'modes': modes, 'gate': gate_on,
                   'shuffle': shuffle_every, 'kill': kill_idx}, f)


def summarize(res):
    log = [e for e in res['log'] if 'choice' in e]
    pre = [e for e in log if 60 <= e['t'] < T_LOSS]
    post = [e for e in log if e['t'] >= T_LOSS]
    n = len(res['modes'])
    if not pre:
        return None
    share = [0.0] * n
    for e in pre:
        share[e['choice']] += 1.0 / len(pre)
    best = max(range(n), key=lambda k: share[k])
    # 抗议: 对"已失去对象"的索取率, 失去后 vs 失去前
    k = res['kill']
    pre_k = [e for e in log if T_LOSS - 40 <= e['t'] < T_LOSS and e['choice'] == k]
    post_k = [e for e in post if e['choice'] == k]
    rate_pre = len(pre_k) / 40.0
    rate_post = len(post_k) / max(1, len(post))
    g_pre = sum(e['g'] for e in log if T_LOSS - 20 <= e['t'] < T_LOSS) / max(1, len(
        [e for e in log if T_LOSS - 20 <= e['t'] < T_LOSS]))
    g_post = sum(e['g'] for e in post) / max(1, len(post))
    return {
        'pref_share': share[best] - 1.0 / n,
        'best': best,
        'protest': rate_post - rate_pre,
        'rate_pre': rate_pre, 'rate_post': rate_post,
        'g_drop': g_pre - g_post,
        'n_pre': len(pre), 'n_post': len(post),
    }


ARMS = {
    'DIFF_killA':   dict(modes=['fresh', 'stale', 'random'], gate=True,  shuffle=0,  kill=0),
    'DIFF_killC':   dict(modes=['fresh', 'stale', 'random'], gate=True,  shuffle=0,  kill=2),
    'SAME_killA':   dict(modes=['fresh', 'fresh', 'fresh'],  gate=True,  shuffle=0,  kill=0),
    'SAME_killC':   dict(modes=['fresh', 'fresh', 'fresh'],  gate=True,  shuffle=0,  kill=2),
    'NOGATE_killA': dict(modes=['fresh', 'stale', 'random'], gate=False, shuffle=0,  kill=0),
    'SHUFFLE_killA':dict(modes=['switch', 'switch', 'switch'], gate=True, shuffle=0,  kill=0),
}


def run_one(arm, seed, base_port):
    cfg = ARMS[arm]
    n = len(cfg['modes'])
    p_recv = [base_port + 1 + i for i in range(n)]
    p_agent = base_port + 1 + n
    ports = p_recv + [p_agent]
    out = '/tmp/e148_%s_%d.json' % (arm, seed)
    procs = [Process(target=peer, args=(p_recv[i], cfg['modes'][i]), daemon=True)
             for i in range(n)]
    for p in procs:
        p.start()
    pa = Process(target=agent, args=(p_agent, p_recv, cfg['modes'], cfg['gate'],
                                     cfg['shuffle'], cfg['kill'], out, seed), daemon=True)
    pa.start()
    pd = Process(target=disturber, args=(TICKS,), daemon=True)
    pd.start()
    time.sleep(0.30)
    pr = Process(target=recorder, args=(ports, TICKS + 12), daemon=True)
    pr.start()

    # 到 T_LOSS 拍时真实 kill 掉目标 peer 进程
    pa.join(timeout=T_LOSS * TICK_S + 1.2)
    try:
        os.kill(procs[cfg['kill']].pid, 9)
    except Exception:
        pass
    pa.join(timeout=60)
    for p in procs:
        if p.is_alive():
            p.terminate()
    try:
        os.kill(pr.pid, 9)
    except Exception:
        pass
    try:
        os.kill(pd.pid, 9)
    except Exception:
        pass
    for p in procs:
        p.join(timeout=2)
    pr.join(timeout=2); pd.join(timeout=2)
    if not os.path.exists(out):
        return None
    with open(out) as f:
        res = json.load(f)
    s = summarize(res)
    if s:
        s['arm'] = arm; s['seed'] = seed
    return s


def ci(vals, nboot=4000, seed=7):
    import statistics
    rnd = random.Random(seed)
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return float('nan'), float('nan'), float('nan')
    m = statistics.mean(vals)
    bs = []
    for _ in range(nboot):
        bs.append(statistics.mean([vals[rnd.randrange(len(vals))] for _ in vals]))
    bs.sort()
    lo = bs[int(0.025 * len(bs))]
    hi = bs[int(0.975 * len(bs)) - 1]
    return m, lo, hi


if __name__ == '__main__':
    seeds = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else '1,2,3,4,5'.split(','))]
    all_res = {}
    t0 = time.time()
    bp = 19000
    for arm in ARMS:
        rows = []
        for sd in seeds:
            r = run_one(arm, sd, bp)
            bp += 10
            if r:
                rows.append(r)
        agg = {}
        for key in ['pref_share', 'protest', 'g_drop', 'rate_pre', 'rate_post']:
            m, lo, hi = ci([r[key] for r in rows])
            agg[key] = {'mean': m, 'ci': [lo, hi]}
        all_res[arm] = {'n': len(rows), 'agg': agg, 'rows': rows}
        a = agg
        print('%-14s n=%d pref=%+.4f[%+.4f,%+.4f] protest=%+.4f[%+.4f,%+.4f] gdrop=%+.4f[%+.4f,%+.4f]'
              % (arm, len(rows),
                 a['pref_share']['mean'], a['pref_share']['ci'][0], a['pref_share']['ci'][1],
                 a['protest']['mean'], a['protest']['ci'][0], a['protest']['ci'][1],
                 a['g_drop']['mean'], a['g_drop']['ci'][0], a['g_drop']['ci'][1]), flush=True)
    with open(os.path.join(os.path.dirname(__file__), 'result148.json'), 'w') as f:
        json.dump(all_res, f, indent=1)
    print('elapsed %.1fs' % (time.time() - t0))

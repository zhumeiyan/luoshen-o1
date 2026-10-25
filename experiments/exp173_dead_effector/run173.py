#!/usr/bin/env python3
"""
173: 感官要活，效应器要死 —— 同一个"世界不听我的程度 w"，对两者价值方向相反。

效应器(手) = /dev/uinput，死的数值接口（整数 keycode / rel 值）
感官       = /proc/stat ctxt（世界独立变化）

扫 w = 0/1/2/4 个忙进程（SIGSTOP/SIGCONT 控制），顺序交织抗漂移(156号教训)。
  效应器指标：动作落地时序抖动 std（越小越好 = 越"死"）
  感官指标  ：通道读数变化量（越大越好 = 越"活"，有东西可感）
"""
import os, sys, time, struct, fcntl, subprocess, signal, json, random, statistics as st

UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_RELBIT = 0x40045566
UI_DEV_CREATE = 0x5501
EV_KEY, EV_REL, EV_SYN = 0x01, 0x02, 0x00
REL_X, REL_Y = 0x00, 0x01
BTN_LEFT = 0x110

WMAX = 4
N_HAND = 200           # 每次条件发的事件数
PERIOD = 0.004         # 期望间隔 4ms

def create_hand():
    fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_REL)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
    fcntl.ioctl(fd, UI_SET_RELBIT, REL_X)
    fcntl.ioctl(fd, UI_SET_RELBIT, REL_Y)
    fcntl.ioctl(fd, UI_SET_KEYBIT, BTN_LEFT)
    os.write(fd, struct.pack('80s', b'luoshen-hand') + b'\x00' * (1116 - 80))
    fcntl.ioctl(fd, UI_DEV_CREATE)
    return fd

def emit(fd, t, c, v):
    os.write(fd, struct.pack('llHHi', 0, 0, t, c, v))

def read_ctxt():
    with open('/proc/stat') as f:
        for line in f:
            if line.startswith('ctxt'):
                return int(line.split()[1])
    return -1

def spawn_busy(n):
    procs = []
    for _ in range(n):
        p = subprocess.Popen([sys.executable, '-c', 'while True: pass'])
        procs.append(p)
    for p in procs:                      # 先全部暂停
        os.kill(p.pid, signal.SIGSTOP)
    time.sleep(0.3)
    return procs

def set_w(procs, w):
    """精确让 w 个进程在跑，其余暂停"""
    for i, p in enumerate(procs):
        try:
            os.kill(p.pid, signal.SIGCONT if i < w else signal.SIGSTOP)
        except ProcessLookupError:
            pass
    time.sleep(0.25)                     # 让负载真正到位

def measure(w, fd):
    """在同一条件下同时测效应器抖动与感官变化量"""
    ts = []
    ctx = []
    next_t = time.perf_counter() + PERIOD
    for i in range(N_HAND):
        # --- 效应器：以固定节拍发一个"死的"动作 ---
        while time.perf_counter() < next_t:
            pass
        t0 = time.perf_counter_ns()
        emit(fd, EV_REL, REL_X, 1)       # 值恒为 1 —— 死的
        emit(fd, EV_SYN, 0, 0)
        ts.append(time.perf_counter_ns())
        ctx.append(read_ctxt())
        next_t += PERIOD
    # 效应器：实际间隔 vs 期望间隔的偏差（落地抖动）
    intervals = [(ts[i + 1] - ts[i]) / 1e6 for i in range(len(ts) - 1)]
    hand_jitter_ms = st.pstdev(intervals)
    hand_mean_ms = st.mean(intervals)
    # 感官：单位时间世界变化量（有东西可感 = 活）
    deltas = [ctx[i + 1] - ctx[i] for i in range(len(ctx) - 1)]
    sense_change = st.mean(deltas)
    sense_sd = st.pstdev(deltas)
    return hand_jitter_ms, hand_mean_ms, sense_change, sense_sd

def main():
    fd = create_hand()
    procs = spawn_busy(WMAX)
    # 交织顺序：每个 w 跑 REPS 次，顺序打乱(156号顺序漂移教训)
    REPS = 3
    plan = [(w, r) for r in range(REPS) for w in (0, 1, 2, 4)]
    random.seed(173)
    random.shuffle(plan)
    raw = {w: [] for w in (0, 1, 2, 4)}
    try:
        for w, r in plan:
            set_w(procs, w)
            j, m, sc, ss = measure(w, fd)
            raw[w].append(dict(jitter=j, mean=m, sense=sc, sense_sd=ss))
            print(f'w={w} rep={r}  hand_jitter={j:.3f}ms  hand_mean={m:.3f}ms  '
                  f'sense_change={sc:.1f}  sense_sd={ss:.1f}', flush=True)
    finally:
        for p in procs:
            try: os.kill(p.pid, signal.SIGKILL)
            except Exception: pass
        try: os.close(fd)
        except Exception: pass

    out = {}
    for w in (0, 1, 2, 4):
        js = [x['jitter'] for x in raw[w]]
        ss = [x['sense'] for x in raw[w]]
        ssd = [x['sense_sd'] for x in raw[w]]
        ms = [x['mean'] for x in raw[w]]
        out[w] = dict(hand_jitter_mean=st.mean(js), hand_jitter_list=js,
                      hand_mean_interval=st.mean(ms),
                      sense_change_mean=st.mean(ss), sense_change_list=ss,
                      sense_sd_mean=st.mean(ssd))
    print('\n=== 汇总（交织后）===')
    print(f"{'w':>3} {'手·抖动ms':>12} {'手·精度1/抖动':>14} {'感官·变化量':>12} {'感官·sd':>10}")
    for w in (0, 1, 2, 4):
        o = out[w]
        prec = 1.0 / o['hand_jitter_mean'] if o['hand_jitter_mean'] > 0 else float('inf')
        print(f"{w:>3} {o['hand_jitter_mean']:>12.4f} {prec:>14.3f} "
              f"{o['sense_change_mean']:>12.1f} {o['sense_sd_mean']:>10.1f}")
    json.dump(out, open(os.path.join(os.path.dirname(__file__), 'result173.json'), 'w'), indent=2)
    print('\nresult173.json 已写出')

if __name__ == '__main__':
    main()

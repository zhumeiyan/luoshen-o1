import os, time, json, subprocess, signal, random, sys

NLOOP = 200000
BASE = None

def probe():
    t0 = time.perf_counter_ns()
    x = 0
    for i in range(NLOOP):
        x += i * i
    return time.perf_counter_ns() - t0

def med(n=5):
    return sorted(probe() for _ in range(n))[n // 2]

def feats():
    f = []
    la = open('/proc/loadavg').read().split()
    f += [float(la[0]), float(la[1]), float(la[2])]
    av = fr = 0.0
    for l in open('/proc/meminfo').read().split('\n'):
        if l.startswith('MemAvailable'): av = float(l.split()[1])
        if l.startswith('MemFree'):      fr = float(l.split()[1])
    f += [av, fr]
    vc = nc = 0.0
    for l in open('/proc/self/status').read().split('\n'):
        if l.startswith('voluntary_ctxt_switches'):     vc = float(l.split()[1])
        if l.startswith('nonvoluntary_ctxt_switches'):  nc = float(l.split()[1])
    f += [vc, nc]
    cs = open('/proc/stat').read().split('\n')[0].split()
    f += [float(cs[1]), float(cs[3]), float(cs[4])]
    rc = sc = 0.0
    for l in open('/proc/self/io').read().split('\n'):
        if l.startswith('rchar'): rc = float(l.split()[1])
        if l.startswith('syscr'): sc = float(l.split()[1])
    f += [rc, sc]
    f += [float(open('/proc/uptime').read().split()[0])]
    return f

def spawn_cpu(n):
    return [subprocess.Popen(["python3", "-c", "x=0\nwhile 1: x+=1"]) for _ in range(n)]

def spawn_io(n):
    s = "import time\nwhile 1:\n d=open('big.bin','rb').read()"
    return [subprocess.Popen(["python3", "-c", s]) for _ in range(n)]

def kill(ps):
    for p in ps:
        try:
            p.send_signal(signal.SIGKILL); p.wait()
        except Exception:
            pass

def main():
    global BASE
    if not os.path.exists("big.bin"):
        open("big.bin", "wb").write(os.urandom(4 * 1024 * 1024))
    random.seed(167)
    BASE = med(9)
    print(f"baseline={BASE}ns", flush=True)

    conds = [(c, i) for c in (0, 1, 2, 3) for i in (0, 1, 2)]
    rows = []
    t0 = time.time()
    for rnd in range(3):
        order = conds[:]
        random.shuffle(order)
        for (nc, ni) in order:
            if time.time() - t0 > 400:
                print("TIMEGUARD", flush=True)
                break
            pc = spawn_cpu(nc); pi = spawn_io(ni)
            time.sleep(1.0)
            for k in range(5):
                fv = feats()
                t = probe()
                rows.append({"cpu": nc, "io": ni, "rnd": rnd, "rep": k,
                             "ratio": t / BASE, "f": fv})
            kill(pc); kill(pi)
            time.sleep(0.5)
            print(f"r{rnd} cpu{nc} io{ni} ratio={rows[-1]['ratio']:.3f} n={len(rows)}", flush=True)
    json.dump({"base": BASE, "rows": rows}, open("data167.json", "w"))
    print(f"DONE n={len(rows)}", flush=True)

main()

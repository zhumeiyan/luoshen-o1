"""真实损伤源 + 真实通道读数 + 真实吞吐测量。全部用 fork / /proc / 计时，不建模。"""
import os, time, signal, json

WORK = 90000  # 主体每轮工作量（乘法次数）


def work(W=WORK):
    x = 0
    for i in range(W):
        x = (x * 1103515245 + 12345) % 2147483647
    return x


def spawn_cpu_busy(n):
    pids = []
    for _ in range(n):
        pid = os.fork()
        if pid == 0:
            x = 0
            while True:
                x = (x * 1103515245 + 12345) % 2147483647
            os._exit(0)
        pids.append(pid)
    return pids


def spawn_mem_holder(mb):
    pid = os.fork()
    if pid == 0:
        try:
            b = bytearray(mb * 1024 * 1024)
            for i in range(0, len(b), 4096):
                b[i] = 1
            signal.pause()
        finally:
            os._exit(0)
    return pid


IOFILE = "/data/workspace/luoshen-o1/experiments/exp171_pain/_big.bin"


def ensure_iofile(mb=200):
    if not os.path.exists(IOFILE):
        with open(IOFILE, "wb") as f:
            f.write(os.urandom(1024 * 1024))
            for _ in range(mb - 1):
                f.write(b"\x00" * (1024 * 1024))
        os.system("sync")


def spawn_io_reader(n):
    ensure_iofile()
    pids = []
    for _ in range(n):
        pid = os.fork()
        if pid == 0:
            while True:
                with open(IOFILE, "rb") as f:
                    while f.read(1 << 20):
                        pass
            os._exit(0)
        pids.append(pid)
    return pids


def killall(pids):
    for p in pids:
        try:
            os.kill(p, signal.SIGKILL)
            os.waitpid(p, 0)
        except Exception:
            pass


def sense():
    """真实通道读数：三个物理量互不相通。"""
    load1 = float(open("/proc/loadavg").read().split()[0])
    ctxt = int([l for l in open("/proc/stat") if l.startswith("ctxt")][0].split()[1])
    mem = int([l for l in open("/proc/meminfo")
               if l.startswith("MemAvailable")][0].split()[1])
    return {"load1": load1, "ctxt": ctxt, "mem_kb": mem}

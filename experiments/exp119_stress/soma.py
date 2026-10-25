"""119 本体觉底座：每条通道带专属提取器，失败必须可见（判据核 488/489）。"""
import os, re, time, socket, statistics

NUM = re.compile(rb"-?\d+\.?\d*")

class Channel:
    def __init__(self, name, path, extractor, unit=''):
        self.name, self.path, self.ex, self.unit = name, path, extractor, unit
        self.err = None; self.n_ok = 0; self.n_fail = 0
    def read(self):
        if self.path is None:
            v = self.ex(None)
        else:
            try:
                with open(self.path, 'rb') as f:
                    raw = f.read(8192)
            except Exception as e:
                self.err = type(e).__name__; self.n_fail += 1
                return None
            v = self.ex(raw)
        if v is None:
            self.err = 'extract-fail'; self.n_fail += 1
            return None
        self.err = None; self.n_ok += 1
        return float(v)
    def __repr__(self):
        return f'<{self.name} {self.path} ok={self.n_ok} fail={self.n_fail} err={self.err}>'

def _field1(raw):   # loadavg 第1字段
    m = NUM.findall(raw); return float(m[0]) if m else None
def _procs(raw):    # loadavg 第4字段 "1/134" 的分母=总进程/线程
    m = NUM.findall(raw)
    return float(m[4]) if len(m) >= 5 else None
def _memkey(key):
    def f(raw):
        for line in raw.split(b'\n'):
            if line.startswith(key.encode()):
                m = NUM.findall(line)
                return float(m[0]) if m else None
        return None
    return f
def _clock(raw=None):
    return time.time()

CHANNELS = [
    Channel('load1',    '/proc/loadavg', _field1,            'load'),
    Channel('nrunning', '/proc/loadavg', _procs,             'count'),
    Channel('memavail', '/proc/meminfo', _memkey('MemAvailable'), 'kB'),
    Channel('memfree',  '/proc/meminfo', _memkey('MemFree'),      'kB'),
    Channel('uptime',   '/proc/uptime',  _field1,            's'),
    Channel('clock',    None,             _clock,             'epoch'),
]

def rtt(host='api.github.com', port=443, timeout=3.0):
    t0 = time.perf_counter()
    try:
        s = socket.create_connection((host, port), timeout=timeout); s.close()
        return (time.perf_counter() - t0) * 1000.0
    except Exception:
        return None

def snapshot(chs=CHANNELS):
    out = {}
    for c in chs:
        out[c.name] = c.read()
    out['rtt'] = rtt()
    return out

if __name__ == '__main__':
    print('=== 119-B 修好提取器后的通道 ===')
    for _ in range(3):
        s = snapshot()
        print({k: (round(v,3) if isinstance(v,float) else v) for k,v in s.items()})
        time.sleep(0.15)
    print()
    for c in CHANNELS:
        print(' ', c)

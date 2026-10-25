"""119-A 真实本体觉探针：只报告 REAL 通道，不编 SIMULATED。"""
import os, time, re, socket, statistics

def _nums(text, pattern=rb"-?\d+\.?\d*"):
    return re.findall(pattern, text if isinstance(text, bytes) else text.encode())

class Channel:
    def __init__(self, name, path, kind):
        self.name, self.path, self.kind = name, path, kind
        self.err = None
    def read(self):
        try:
            with open(self.path, 'rb') as f:
                raw = f.read(4096)
            v = _nums(raw)
            if not v:
                self.err = 'no-number'
                return None
            return float(v[0])
        except Exception as e:
            self.err = type(e).__name__
            return None

CH = [
    Channel('load1',  '/proc/loadavg', 'proc'),
    Channel('procs',  '/proc/loadavg', 'proc'),
    Channel('memavail','/proc/meminfo','proc'),
    Channel('uptime', '/proc/uptime',  'proc'),
]

def rtt():
    t0 = time.perf_counter()
    try:
        s = socket.create_connection(('api.github.com', 443), timeout=3)
        s.close()
        return (time.perf_counter() - t0) * 1000.0
    except Exception as e:
        return None

if __name__ == '__main__':
    print('=== 119-A 本体觉通道 REAL 探测 ===')
    for c in CH:
        vals = []
        for _ in range(5):
            v = c.read()
            vals.append(v)
            time.sleep(0.05)
        good = [v for v in vals if v is not None]
        print(f'{c.name:10s} path={c.path:16s} n={len(good)}/5 '
              f'first={good[0] if good else None} err={c.err}')
    print('--- RTT ---')
    rs = []
    for _ in range(3):
        r = rtt(); rs.append(r); time.sleep(0.1)
    g = [r for r in rs if r is not None]
    print('rtt n=%d/3 vals=%s' % (len(g), [round(x,1) for x in g]))

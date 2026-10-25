"""151 peer 进程：独立探索者，通过 UDP 报告自己的 visited"""
import socket, random, sys
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('127.0.0.1', 18731))
s.settimeout(30)
vis = set()
rng = random.Random(4242)
pos = 0
N = 500
while True:
    try:
        d, addr = s.recvfrom(65536)
    except Exception:
        break
    m = d.decode()
    if m == 'STOP': s.sendto(b'bye', addr); break
    if m == 'RESET': vis = set(); pos = 0; s.sendto(b'ok', addr); continue
    if m == 'ASK':
        s.sendto(','.join(str(x) for x in vis).encode(), addr); continue
    if m.startswith('VISIT'):
        vis.add(int(m.split()[1]))
        continue
    # 自主探索
    for _ in range(6):
        pos = (pos + rng.randrange(1, 7)) % N
        vis.add(pos)
    s.sendto(b'ok', addr)

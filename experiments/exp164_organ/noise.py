import statistics, os
def o_mem():
    for line in open('/proc/meminfo').read().splitlines():
        if line.startswith('MemAvailable'): return int(line.split()[1])
v=[o_mem() for _ in range(40)]
print('mem noise: mean',statistics.mean(v),'stdev',statistics.pstdev(v),'range',max(v)-min(v))

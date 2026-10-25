import os, time, json, subprocess, sys

# 探测任务：固定计算量，测真实耗时
def probe():
    t0 = time.perf_counter_ns()
    x = 0
    for i in range(200000):
        x += i * i
    return time.perf_counter_ns() - t0

# 基线
base = sorted(probe() for _ in range(7))[3]
print(f"baseline = {base} ns")

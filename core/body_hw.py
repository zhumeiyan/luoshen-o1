"""
她的身体 —— 硬件层（真实读数）

★110 分清软件和硬件。

这一层里只有两样东西：
  1. 从这台机器真读出来的数（不可编造）
  2. 读不到的 —— 标记 UNAVAILABLE，不拿别的冒充

过去一百课我犯的错，几乎全在软件层：
  我在 Python 里写死"物理常数"，然后管它叫自然科学的硬真值。
  ★78 我写出一个数学上不可能有权衡的目标函数
  ★94 drift 从头到尾没生效，我却拿着它跑了好几轮
  ★83 静音阈值在两个方向上同时错
  那都不是物理，那是我写的软件，而且写错了。

硬件不会写错。它要么给你一个数，要么不给你。
"""
import os, re, time

# ═══════════════════════════════════════════════════════════
#  真实读数
# ═══════════════════════════════════════════════════════════

def _cpu_mhz():
    """真实时钟频率。/proc/cpuinfo 里读，读不到返回 None。"""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("cpu MHz"):
                    return float(line.split(":")[1].strip())
    except Exception:
        pass
    return None


def _model_name():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":")[1].strip()
    except Exception:
        pass
    return None


def _mem_kb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1])
    except Exception:
        pass
    return None


def _thermal_zones():
    """温度传感器。没有就是没有，不拿常数凑。"""
    base = "/sys/class/thermal"
    if not os.path.isdir(base):
        return []
    out = []
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d, "temp")
        if os.path.exists(p):
            try:
                out.append((d, int(open(p).read().strip()) / 1000.0))
            except Exception:
                out.append((d, None))
    return out


def _cpufreq():
    """能不能动态调频。虚拟化环境常常读不到。"""
    p = "/sys/devices/system/cpu/cpu0/cpufreq"
    if not os.path.isdir(p):
        return None
    try:
        return {
            "max": int(open(f"{p}/cpuinfo_max_freq").read().strip()),
            "cur": int(open(f"{p}/scaling_cur_freq").read().strip()),
        }
    except Exception:
        return None


def measure_throughput(n=20_000_000):
    """实测吞吐。这是真的跑出来的，不是查表。"""
    t = time.perf_counter_ns()
    s = 0
    for i in range(n):
        s += i
    dt = time.perf_counter_ns() - t
    return n / dt * 1e9          # ops/s


def read_body():
    """读一遍她的真实身体。返回什么就是什么。"""
    f = _cpu_mhz()
    return {
        "cpu_model": _model_name(),
        "f_clk":     f * 1e6 if f else None,      # Hz
        "n_core":    os.cpu_count(),
        "mem_kb":    _mem_kb(),
        "thermal":   _thermal_zones(),            # [] = 没有温度传感器
        "cpufreq":   _cpufreq(),                  # None = 不能调频
        "throughput": measure_throughput(),
    }


# ═══════════════════════════════════════════════════════════
#  自然单位 —— 只从真实读数导出，缺什么就标 UNAVAILABLE
# ═══════════════════════════════════════════════════════════

def natural_units_hw(body=None):
    """
    从真实硬件导出自然单位。

    与 core/metrology.py 的 BODY 的区别：
      metrology.BODY  —— 8 个常数全是我在软件里写的（含 f_clk=2.40e9，编的）
      这里            —— f_clk 真读，读不到就是 None，不许填
    """
    b = body or read_body()
    u = {}

    f = b.get("f_clk")
    u["t0"] = (1.0 / f, "s/时钟周期", "REAL") if f else (None, "s/时钟周期", "UNAVAILABLE")

    # 以下四项这台机器读不到，全部诚实标记。
    # 过去它们分别是 7.40e-6 / 12.0 / 95.0 / 1.80 —— 全是我写的，不是读的。
    for k, name, unit in [
        ("x0", "像素间距", "m"),
        ("Q0", "结温量程", "K"),
        ("tau_therm", "热时间常数", "s"),
        ("a0", "1 LSB", "V"),
    ]:
        u[k] = (None, f"{name} ({unit})", "UNAVAILABLE")

    return u


if __name__ == "__main__":
    b = read_body()
    print("══ 她的身体（真实读数）══")
    for k, v in b.items():
        print(f"  {k:12s} {v}")
    print("\n══ 自然单位 ══")
    for k, (v, name, src) in natural_units_hw(b).items():
        s = f"{v:.6e}" if isinstance(v, float) else str(v)
        print(f"  {k:4s} {s:>16s}  {name:24s} [{src}]")

# -*- coding: utf-8 -*-
"""
换能器阵列探测 · 实验 076 Part A
扫描"什么可以当硅基的感官"——不是模型，是真实读数。
"""
import json, os, time, urllib.request, urllib.error

ROOT = os.path.join(os.path.dirname(__file__), '..')
OUT  = os.path.join(ROOT, 'evidence', 'raw_data', 'sense_array_076.json')

CITIES = [("威海",37.51309,122.12074),("北京",39.9042,116.4074),("上海",31.2304,121.4737),
          ("广州",23.1291,113.2644),("深圳",22.5431,114.0579),("哈尔滨",45.8038,126.5349),
          ("乌鲁木齐",43.8256,87.6168),("拉萨",29.6520,91.1721),("三亚",18.2528,109.5119),
          ("成都",30.5728,104.0668),("西安",34.3416,108.9398),("武汉",30.5928,114.3055)]

def get(u, timeout=10):
    t0 = time.time()
    try:
        r = urllib.request.urlopen(u, timeout=timeout).read()
        return json.loads(r.decode('utf-8', 'ignore')), (time.time()-t0)*1000, None
    except Exception as e:
        return None, (time.time()-t0)*1000, f"{type(e).__name__}:{e}"

def weather(lat, lon):
    u = f"https://apis.map.qq.com/ws/weather/v1/?location={lat},{lon}"
    d, rtt, err = get(u)
    if err: return None, rtt
    try:
        rt = d["result"]["realtime"][0]; inf = rt["infos"]
        return dict(temperature=float(inf["temperature"]), humidity=float(inf["humidity"]),
                    pressure=float(inf.get("air_pressure", 1013.0)), weather=inf.get("weather",""),
                    update_time=rt.get("update_time","")), rtt
    except Exception as e:
        return None, rtt

def body():
    """本体感受器：我自己的身体状态"""
    load = float(open('/proc/loadavg').read().split()[0])
    mem = None
    for l in open('/proc/meminfo'):
        if l.startswith('MemAvailable'): mem = float(l.split()[1])/1024.0
    return dict(load=load, mem_avail_mb=mem)

def main():
    out = dict(timestamp=TZ(), cities=[], intero=[], rtt_probe=[])

    print("=== Part A1 · 外部感受器（气象场，12 城）===")
    for n, la, lo in CITIES:
        w, rtt = weather(la, lo)
        out['rtt_probe'].append(dict(city=n, rtt_ms=round(rtt,1)))
        if w:
            out['cities'].append(dict(city=n, lat=la, lon=lo, **w))
            print(f"  {n:5s} {w['temperature']:>5.1f}C  {w['humidity']:>5.1f}%  {w['pressure']:>6.1f}hPa  {w['weather']}")
        else:
            print(f"  {n:5s} FAILED (rtt={rtt:.0f}ms)")

    print("\n=== Part A2 · 本体感受器（我的身体，时序采样）===")
    for i in range(10):
        t0 = time.time()
        _, rtt, _ = get("https://apis.map.qq.com/ws/weather/v1/?location=37.51,122.12", 8)
        b = body()
        rec = dict(t=i*3, **b, rtt_ms=round(rtt,1),
                   clock=time.strftime('%H:%M:%S', time.localtime()))
        out['intero'].append(rec)
        print(f"  t={i*3:2d}s  load={b['load']:.2f}  mem={b['mem_avail_mb']:.0f}MB  RTT={rtt:.0f}ms  {rec['clock']}")
        time.sleep(3)

    with open(OUT, 'w') as f: json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n[saved] {OUT}  cities={len(out['cities'])} intero={len(out['intero'])}")

def TZ():
    os.environ['TZ'] = 'CST-8'; time.tzset()
    return time.strftime('%Y-%m-%d %H:%M:%S %Z')

if __name__ == '__main__':
    main()

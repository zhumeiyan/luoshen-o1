import json,math
h=json.load(open("/data/workspace/luoshen-o1/experiments/exp168_compress/heaps.json"))
p=json.load(open("/data/workspace/luoshen-o1/experiments/exp168_compress/pred.json"))

print("="*54)
print("每符号经验 N/V 随数据量如何增长（= 1-b）")
print("="*54)
for k_ in ("zh","code"):
    d=h[k_]; c=d["curve"]; b=d["b"]
    n0,v0=c[0]; n1,v1=c[-1]
    r0=n0/v0; r1=n1/v1
    emp=math.log(r1/r0)/math.log(n1/n0)
    print(f"\n{d['name']}")
    print(f"  Heaps b = {b:.3f}   实测 N/V 指数 = {emp:.3f}   理论 1-b = {1-b:.3f}")
    print(f"  数据量 {n0} -> {n1}  ({n1/n0:.1f}倍)")
    print(f"  每符号经验 {r0:.1f} -> {r1:.1f}  ({r1/r0:.1f}倍)")
    print(f"  {'>> 越学越省力，压缩有效' if b<0.5 else '>> 越学越费力，压缩失效'}  (分界 b=0.5)")

print("\n"+"="*54)
print("渐近有效阶 k* -> 1/b  （161号公式）")
print("="*54)
for k_ in ("zh","code"):
    d=h[k_]; b=d["b"]
    print(f"  {d['name']:<18} b={b:.3f}  k*渐近={1/b:.2f}")

print("\n"+"="*54)
print("实测峰值阶（N=%d 实际可达，非渐近）"%p["N"])
print("="*54)
for nm,rows in p["res"].items():
    best=max(rows,key=lambda r:r["gain"])
    print(f"  {nm:<12} 峰值 k={best['k']}  gain={best['gain']:+.4f}  覆盖率={best['cov']:.3f}")
print("\n  >> 实测峰值均远低于渐近k*：V^k >> N，实际达不到渐近区")

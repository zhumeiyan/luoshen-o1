import json, math

# n-bonacci: T(n)=sum_{i=1..k} T(n-i)
# characteristic: x^{k+1} - 2x^k + 1 = 0  ->  x = 2 - x^{-k}
def r(k, it=500):
    x = 1.95
    for _ in range(it):
        x = 2.0 - x**(-k)
    return x

rows=[]
print(f"{'k':>3} {'r_k':>12} {'gain k-1->k':>13} {'% of total(2-1)':>15} {'eps=2-r':>10} {'2^-k':>10} {'eps/2^-k':>10}")
prev=None
for k in range(1,13):
    rk=r(k)
    gain = (rk-prev) if prev is not None else None
    tot  = (rk-1.0)/1.0   # total reachable = 2-1 = 1
    eps  = 2.0-rk
    p2   = 2.0**(-k)
    print(f"{k:>3} {rk:>12.6f} " + (f"{gain:>13.6f}" if gain is not None else f"{'-':>13}") + f" {tot*100:>14.3f}% {eps:>10.6f} {p2:>10.6f} {eps/p2:>10.4f}")
    rows.append(dict(k=k,r_k=rk,share_of_total=tot,eps=eps))
    prev=rk
json.dump(rows, open('/data/workspace/luoshen-o1/experiments/exp161_nbonacci/rk.json','w'), ensure_ascii=False, indent=1)

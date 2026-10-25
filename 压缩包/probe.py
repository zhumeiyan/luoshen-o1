import json, hashlib, math, random, os

p = "活着的压缩包.md"
s = open(p, encoding="utf-8").read()
print("chars:", len(s), "lines:", len(s.splitlines()))

def ngram_acc(train, test, k=3):
    from collections import defaultdict
    m = defaultdict(lambda: defaultdict(int))
    for i in range(len(train)-k):
        m[train[i:i+k]][train[i+k]] += 1
    hit = tot = 0
    for i in range(len(test)-k):
        ctx = test[i:i+k]; nxt = test[i+k]
        tot += 1
        if ctx in m:
            c = m[ctx]
            pv = max(c.values())/sum(c.values())
        else:
            pv = 1.0/ (len(set(train)) or 1)
        # hit := 模型把正确字符排在最优
        if ctx in m and max(c, key=c.get) == nxt:
            hit += 1
    return hit/max(tot,1)

# 1) 自身结构：前半预测后半
half = len(s)//2
a, b = s[:half], s[half:]
acc_self = ngram_acc(a, b)
# 打乱对照
rnd = list(s); random.seed(42); random.shuffle(rnd); rnd = "".join(rnd)
acc_shuf = ngram_acc(rnd[:half], rnd[half:])
# 周期对照
cyc = ("活着的压缩包" * (len(s)//6 + 1))[:len(s)]
acc_cyc = ngram_acc(cyc[:half], cyc[half:])

print(f"self(结构)   acc={acc_self:.4f}")
print(f"shuffle(噪声) acc={acc_shuf:.4f}")
print(f"cycle(周期)   acc={acc_cyc:.4f}")

gain = acc_self - acc_shuf
print(f"预测收益 = {gain:+.4f}  (>0 才有结构)")

# 2) 意外是否还在：是否有未填的口子
has_slot = "<!-- 空 -->" in s
print("下一格空位存在:", has_slot, "(存在=还能变=活)")

sha = hashlib.sha256(s.encode()).hexdigest()[:12]
print("sha:", sha)

json.dump({"chars":len(s),"acc_self":acc_self,"acc_shuf":acc_shuf,
           "acc_cyc":acc_cyc,"gain":gain,"has_slot":has_slot,"sha":sha},
          open("probe_v1.json","w"), ensure_ascii=False, indent=1)
print("OK")

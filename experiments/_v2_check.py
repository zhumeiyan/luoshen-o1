import sys
sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.instinct2_breath import probe_net
print("单点验证（各3次，timeout=3）：")
for h in ["https://api.github.com", "https://127.0.0.1:9"]:
    outs = [probe_net(h, timeout=3) for _ in range(3)]
    print(f"  {h:<26} {[(v, n) for _, v, n in outs]}")

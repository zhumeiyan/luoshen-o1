#!/usr/bin/env python3
"""
exp164c A2: 关联规模 m 增大时, 观测扰动的影响是加速还是被纠错?
量子: 纠缠粒子越多越难保护(退相干), 且不可克隆 -> 无法多数投票纠错
经典: 关联可复制 -> 多数投票应能纠错 -> m 越大越稳健
这一格用来划清"经典类比"与"量子真实"的边界
"""
import os, json
import numpy as np

OUT = "/data/workspace/luoshen-o1/experiments/exp164_measurement_limit"


def expA2(trials=2000, ms=(1, 3, 5, 11, 21), ps=(0.20, 0.35, 0.50)):
    out = {}
    for p in ps:
        row = {}
        thr = int(round(p*256)) if p > 0 else 0
        for m in ms:
            correct = 0
            for t in range(trials):
                nb = (2*m + 7)//8 + 2
                b = np.unpackbits(np.frombuffer(os.urandom(nb), dtype=np.uint8))
                X = b[0]
                A = b[1:1+m]
                B = (A ^ X).astype(np.uint8)          # B_i = A_i ^ X
                if p > 0:
                    err = (np.frombuffer(os.urandom(m), dtype=np.uint8) < thr).astype(np.uint8)
                else:
                    err = np.zeros(m, dtype=np.uint8)
                A_obs = (A ^ err).astype(np.uint8)
                votes = (A_obs ^ B).astype(np.uint8)  # = X ^ err_i
                maj = 1 if int(votes.sum())*2 > m else 0
                correct += int(maj == X)
            row[str(m)] = correct/trials
        out[f"{p:.2f}"] = row
    return out


if __name__ == "__main__":
    r = expA2()
    print("A2: 关联对数 m 增大时, 从被扰动关联中多数投票恢复 X 的准确率")
    print("   (经典关联可复制 -> 多数投票纠错)")
    hdr = "  p\\m  " + "".join("%8s" % m for m in (1, 3, 5, 11, 21))
    print(hdr)
    for p, row in r.items():
        print("  %s  " % p + "".join("%8.4f" % row[str(m)] for m in (1, 3, 5, 11, 21)))
    with open(os.path.join(OUT, 'result164c.json'), 'w') as f:
        json.dump(r, f, indent=1)
    print("saved")

# -*- coding: utf-8 -*-
"""
197b: 何时离线重放有价值 / 梦境荒诞的代价

Q1 剂量反应: 重放样本中"动力学错误"的比例 p -> MAE
   用 seg_len 控制: p ≈ 1/seg_len (片段边界处跳变)
Q2 在线数据稀缺度: N_on 扫描 -> rest / replay / dream 的相对优劣是否反转
Q3 离线预算 B_off 扫描 -> 最优离线量是多少
"""
import numpy as np, json, os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run197 import simulate, oracle_mae

OUT = os.path.dirname(os.path.abspath(__file__))


def mean_steady(mode, seeds=5, **kw):
    runs = [simulate(seed=s, mode=mode, **kw) for s in range(seeds)]
    return (round(float(np.mean([r['steady'] for r in runs])), 4),
            round(float(np.std([r['steady'] for r in runs])), 4))


if __name__ == '__main__':
    res = {}

    print('[Q1] 剂量反应: 片段长度 seg_len -> 坏样本比例 p=1/seg_len -> MAE')
    Q1 = []
    for sl in [2, 3, 4, 6, 12, 24, 48]:
        m, sd = mean_steady('dream', seg_len=sl)
        p = 1.0 / sl
        Q1.append({'seg_len': sl, 'p_bad': round(p, 4), 'mae': m, 'std': sd})
        print(f'  seg_len={sl:<3} p_bad={p:.3f}  mae={m:.4f} ±{sd:.4f}')
    # 两端锚点
    rp, _ = mean_steady('replay')
    nz, _ = mean_steady('noise')
    Q1.append({'seg_len': 'replay', 'p_bad': 0.0, 'mae': rp})
    Q1.append({'seg_len': 'noise', 'p_bad': 1.0, 'mae': nz})
    print(f'  replay p=0.0  mae={rp:.4f}')
    print(f'  noise  p=1.0  mae={nz:.4f}')
    res['Q1'] = Q1

    print('[Q2] 在线数据稀缺度 N_on -> 三种离线策略')
    Q2 = []
    for non in [10, 20, 40, 80, 160]:
        row = {'N_on': non}
        for m in ['rest', 'replay', 'dream']:
            row[m], _ = mean_steady(m, N_on=non)
        Q2.append(row)
        best = min(['rest', 'replay', 'dream'], key=lambda k: row[k])
        print(f'  N_on={non:<4} rest={row["rest"]:.4f} replay={row["replay"]:.4f} '
              f'dream={row["dream"]:.4f}   最优={best}')
    res['Q2'] = Q2

    print('[Q3] 离线预算 B_off 扫描')
    Q3 = []
    for bo in [0, 20, 60, 150, 300, 600]:
        row = {'B_off': bo}
        for m in ['replay', 'dream']:
            row[m], _ = mean_steady(m, B_off=bo)
        Q3.append(row)
        print(f'  B_off={bo:<4} replay={row["replay"]:.4f} dream={row["dream"]:.4f}')
    res['Q3'] = Q3

    res['oracle'] = oracle_mae()
    print(f'  oracle = {res["oracle"]:.4f}')

    with open(os.path.join(OUT, 'result197b.json'), 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print('saved result197b.json')

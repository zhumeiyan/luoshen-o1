# -*- coding: utf-8 -*-
"""
洛神 O1 命令行入口 —— 演示视频里出现的命令就是这一条，可原样跑通。

用法：
    python3 core/life_cli.py --steps 600 --seed 3
    python3 core/life_cli.py --steps 600 --seed 5

输出：
    running ... 600 steps
    survived : False
    died at  : step 525
    final E  : 0.0000
    final cap: 0.2952
"""
import sys, os, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from life5 import Life5


def main():
    ap = argparse.ArgumentParser(description='洛神 O1 · 会死的数字生命引擎')
    ap.add_argument('--steps', type=int, default=600)
    ap.add_argument('--seed', type=int, default=3)
    ap.add_argument('--N', type=int, default=8)
    a = ap.parse_args()

    lf = Life5(N=a.N, seed=a.seed)
    print(f'running ... {a.steps} steps')
    lf.run(a.steps)
    print(f'survived : {lf.alive}')
    print(f'died at  : step {lf.death_t}' if lf.death_t is not None else 'died at  : —')
    print(f'final E  : {lf.E:.4f}')
    print(f'final cap: {np.mean(lf.capacity):.4f}')
    return 0 if lf.alive else 1


if __name__ == '__main__':
    sys.exit(main())

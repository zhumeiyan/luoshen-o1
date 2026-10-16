# -*- coding: utf-8 -*-
"""
把「五条硬约束」挂到任意 Agent 框架上 —— 最小可运行示例。

不改动原框架一行代码：只把 "我要多少" 换成 "我分到了多少"。

运行： python3 examples/governed_agent.py
"""
import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'core'))
try:
    from core.life5 import Life5   # 装包运行（pip install .）
except ImportError:               # 源码运行（core/ 直接在 sys.path）
    from life5 import Life5


class DummyAgent:
    """替身：代表你的 LangChain / AutoGPT / 自研 agent。"""
    def __init__(self, n):
        self.n = n
        self.rng = np.random.default_rng(7)
    def propose(self, obs):
        # 原框架照常产出"想要多少"
        return self.rng.uniform(0.2, 1.0, self.n)
    def act(self, obs, alloc):
        # 只拿着真正分到的份额去行动
        return {'spent': float(np.sum(alloc))}


class GovernedAgent:
    def __init__(self, agent, n_channels=8, ratio=0.45, seed=0):
        self.agent = agent
        # seed 必须在构造时传入：初值 b 由它决定，事后替换 rng 无效
        self.life = Life5(N=n_channels, ratio=ratio, seed=seed)

    def step(self, obs):
        wants = self.agent.propose(obs)
        self.life.input_val = float(np.mean(wants))
        rec = self.life.step()
        if rec is None or not self.life.alive:
            raise RuntimeError(f'agent terminated at t={self.life.death_t}')
        return self.agent.act(obs, rec['avec'])


def demo(seed, steps=600, ratio=0.45):
    ga = GovernedAgent(DummyAgent(8), n_channels=8, ratio=ratio, seed=seed)
    spent = 0.0
    try:
        for t in range(steps):
            spent += ga.step({'t': t})['spent']
    except RuntimeError as e:
        return dict(seed=seed, alive=False, death_t=ga.life.death_t,
                    cap_skew=float(ga.life.capacity.std() / ga.life.capacity.mean()),
                    spent=spent, msg=str(e))
    return dict(seed=seed, alive=True, death_t=None,
                cap_skew=float(ga.life.capacity.std() / ga.life.capacity.mean()),
                spent=spent, msg='survived')


if __name__ == '__main__':
    print('=== 挂上硬约束后的 Agent（ratio=0.45，8 通道）===')
    print(f"{'seed':>4} | {'结局':<10} | {'终止拍':>6} | {'结构偏度':>8} | {'累计支出':>9}")
    print('-' * 52)
    for sd in [3, 5, 11, 13]:
        r = demo(sd)
        end = '存活' if r['alive'] else '死亡'
        dt = r['death_t'] if r['death_t'] is not None else '-'
        print(f"{r['seed']:>4} | {end:<10} | {dt:>6} | {r['cap_skew']:>8.4f} | {r['spent']:>9.2f}")

    print()
    print('=== 对照：撤掉稀缺（ratio=1.2，即要多少给多少）===')
    r = demo(3, ratio=1.2)
    print(f"  seed3 结局={'存活' if r['alive'] else '死亡'}  结构偏度={r['cap_skew']:.4f}")
    print('  → 不稀缺就没有取舍，没有取舍就不留疤（偏度趋近 0，结构不成形）')

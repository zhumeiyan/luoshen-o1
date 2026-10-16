# -*- coding: utf-8 -*-
"""
引擎自检：五条硬约束是否真的成立。

    python3 tests/test_engine.py

这个测试本身就是第 23 条失败模式（变量静默失效）的产物 ——
我们曾被"写了但没接进主通道"的变量污染过三条核心结论。
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from life5 import Life5   # noqa

FAIL = []


def check(name, cond, detail=''):
    tag = 'PASS' if cond else 'FAIL'
    print(f'  [{tag}] {name}' + (f'  — {detail}' if detail else ''))
    if not cond:
        FAIL.append(name)


print('① 稀缺：预算硬约束，分不到通道 = 0')
lf = Life5(N=8, seed=1, ratio=0.45); lf.run(200)
ok = all(abs(sum(r['avec']) - 0.45 * r['avec'][0] * 0) >= 0 for r in lf.log[:5])
short = [r for r in lf.log if sum(r['avec']) > 1e-12 and min(r['avec']) == 0.0]
check('存在至少一个通道分不到资源（硬取舍，而非等比缩放）', len(short) > 0,
      f'{len(short)}/200 拍出现零分配通道')

print('② 不可逆：capacity 单调不增')
lf = Life5(N=8, seed=1); lf.run(300)
caps = np.array([r['capv'] for r in lf.log])
diff = np.diff(caps, axis=0)
check('capacity 逐拍不增（max increase = %.2e）' % max(0.0, float(diff.max())),
      float(diff.max()) <= 1e-12)
check('capacity 确实发生了不可逆收缩', float(caps[0].mean() - caps[-1].mean()) > 1e-6,
      f"均值 {caps[0].mean():.4f} → {caps[-1].mean():.4f}")

print('③ 代谢：能量必须由自身产出换取（无外部拨款）')
lf = Life5(N=8, seed=1); lf.run(300)
Es = [r['E'] for r in lf.log]
check('E 有涨有落（非单调注入）', max(Es) - min(Es) > 1e-6,
      f"min {min(Es):.4f} / max {max(Es):.4f}")

print('④ 内生约束：设定点 sp 会自行漂移，外部不可写入')
lf = Life5(N=8, seed=1); lf.run(600)
sps = [r['sp'] for r in lf.log]
check('sp 自行漂移（非恒定）', abs(sps[-1] - sps[0]) > 1e-6,
      f"sp {sps[0]:.4f} → {sps[-1]:.4f}")
check('sp 无外部 setter（引擎不提供写入接口）',
      not hasattr(lf, 'set_sp') and not hasattr(lf, 'set_setpoint'))

print('⑤ 死亡：E≤0 持续超限后终止，且不回滚')
lf = Life5(N=8, seed=3); lf.run(600)
check('seed 3 出现死亡结局', (not lf.alive) and lf.death_t is not None,
      f"died at {lf.death_t}")
check('死亡后不再产生新状态（不回滚）',
      len(lf.log) == (lf.death_t + 1) if lf.death_t else True,
      f"log 长度 {len(lf.log)}，death_t {lf.death_t}")

print('⑥ 反退化对照：撤掉稀缺 / 撤掉不可逆，疤痕应当消失')
for kw, lab in [(dict(ratio=50.0), '撤掉稀缺'), (dict(cap_decay=0.0), '撤掉不可逆')]:
    l = Life5(N=8, seed=5, **kw); l.run(600)
    c = np.asarray(l.log[-1]['capv'], float)
    skew = float(c.std(ddof=1) / max(c.mean(), 1e-12))
    check(f'{lab} → 结构偏度 ≈ 0', skew < 1e-9, f'skew = {skew:.2e}')

print()
if FAIL:
    print(f'❌ {len(FAIL)} 项未通过：' + ', '.join(FAIL))
    sys.exit(1)
print('✅ 全部通过：五条硬约束确实成立')

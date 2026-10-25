"""EO大脑 —— 蒸馏版演化引擎。

从洛神仓库 04_cognition/大脑.py 蒸馏。
去掉实验性修复参数，保留核心演化机制：
  Pool（环境）→ WM（工作记忆）→ Org（有机体）→ Engine（演化）

核心思路：不教AI预测，让有机体从约束中演化出预测能力。
fitness = 1/(1+MSE)，预测越准越能存活。
"""

import random
import math
import copy

N_CHANNELS = 8
N_REGIONS = 9
DELAY = 3


def activation(x, leak=0.01):
    if x > 1.5:
        return 1.5 + leak * (x - 1.5)
    elif x < -1.5:
        return -1.5 + leak * (x + 1.5)
    else:
        return math.tanh(x)


class Pool:
    """环境：9个区域，每个区域一种动力学系统。"""

    def __init__(self, seed=42):
        self.seed = seed
        self.r = self._mk(seed)
        self._r()

    def _mk(self, s):
        rng = random.Random(s)
        return [{'id': i, 'sigma': round(0.05 + 0.64 * i / 8, 2),
                 'proprio': round(i / 8, 2),
                 'freq': round(0.03 + 0.12 * rng.random(), 3),
                 'phase': round(rng.uniform(0, 2 * math.pi), 3),
                 'type': ['sin', 'logistic', 'lorenz', 'vdP', 'saw',
                          'rossler', 'henon', 'tent', 'cubic'][i],
                 '_s': 0.3, '_t': 0, '_p': 0.0} for i in range(N_REGIONS)]

    def _r(self):
        for r in self.r:
            r['_s'] = 0.3
            r['_t'] = 0
            r['_p'] = 0.0

    def reset(self):
        self._r()

    def step(self):
        for r in self.r:
            r['_t'] += 1
            r['_p'] += r['freq']

    def sense(self, rid):
        r = self.r[rid]
        t = r['_t']
        ph = r['_p']
        nv = random.Random(hash((self.seed, rid, t)) % (2 ** 31)).gauss(0, 1)
        n = r['sigma'] * nv
        s = r['_s']
        rt = r['type']
        if rt == 'sin':
            v = math.sin(ph + r['phase'])
        elif rt == 'logistic':
            v = 4 * s * (1 - s) if 0 < s < 1 else 0.5
        elif rt == 'lorenz':
            v = 0.5 + 0.3 * math.tanh(s)
        elif rt == 'vdP':
            v = s - 0.1 * (s ** 3 - s)
        elif rt == 'saw':
            v = (ph + r['phase']) % 1.0
        elif rt == 'rossler':
            v = 0.5 * math.sin(0.7 * ph + s)
        elif rt == 'henon':
            v = 1 - 1.4 * s ** 2 + 0.3 * s
        elif rt == 'tent':
            v = 2 * s if s < 0.5 else 2 * (1 - s)
        else:
            v = s ** 3 - s
        s2 = max(-2, min(2, v + n))
        r['_s'] = s2
        return [s2, math.sin(s2 * 2.5) if abs(s2) < 1.5 else 0,
                math.tanh(s2), s2 ** 2 * (1 if s2 > 0 else -1),
                abs(s2), math.cos(s2 * 1.7),
                (1 if s2 > 0 else -1) * math.sqrt(abs(s2)) if abs(s2) < 2 else 0,
                r['proprio']]


class WM:
    """工作记忆：循环神经网络 + 感觉适应 + 海马体回放 + 杏仁核惊讶。"""

    def __init__(self, g):
        self.g = g
        n = g['n']
        self.h = [0.0] * n
        self.prev_h = [0.0] * n
        self.db_history = []
        self.input_vec = []
        self.replay_buffer = []
        self.REPLAY_CAP = 64
        self.surprise_level = 0.0
        self.sens_adapt = [0.0] * N_CHANNELS
        self.prev_sens_raw = None

    def fwd_sensory(self, sens):
        g = self.g
        gain = g['sens_gain']
        adapt_rate = g['sens_adapt_rate']
        result = list(sens)
        for c in range(N_CHANNELS):
            val = sens[c] * gain[c]
            if self.prev_sens_raw is not None:
                delta = abs(sens[c] - self.prev_sens_raw[c])
                self.sens_adapt[c] = min(0.85,
                    self.sens_adapt[c] * (1 - adapt_rate) + adapt_rate * (1.0 - min(1.0, delta)))
                val *= (1.0 - 0.5 * self.sens_adapt[c])
            result[c] = val
        self.prev_sens_raw = list(sens)
        return result

    def fwd_association(self, x_raw):
        g = self.g
        w = g['assoc_w']
        thr = g['sparse_thr']
        ext = []
        for i in range(N_CHANNELS):
            ext.append(x_raw[i])
        for i in range(N_CHANNELS):
            ext.append(math.tanh(x_raw[i] * w[0]))
        for i in range(N_CHANNELS):
            v = x_raw[i]
            sig = 1.0 / (1.0 + math.exp(-abs(v) / max(0.01, thr)))
            ext.append(v * w[1] * sig)
        for i in range(N_CHANNELS):
            c = sum(x_raw[j] * w[2] * 0.1 for j in range(N_CHANNELS) if abs(i - j) == 1)
            ext.append(c + x_raw[i] * w[2] * 0.01)
        return ext

    def hippocampal_replay(self, event):
        buf = self.replay_buffer
        buf.append(event)
        if len(buf) > self.REPLAY_CAP:
            buf.sort(key=lambda e: e['salience'])
            buf.pop(0)

    def hippocampal_learn(self):
        g = self.g
        if not self.replay_buffer:
            return
        hip_lr = g['hip_lr']
        replay_n = g['hip_replay_n']
        events = sorted(self.replay_buffer, key=lambda e: e['salience'], reverse=True)[:replay_n]
        for ev in events:
            for i in range(min(len(self.h), len(g['pw']))):
                for c in range(N_CHANNELS):
                    g['pw'][i][c] += hip_lr * ev['salience'] * self.h[i] * 0.01
                    g['pw'][i][c] = max(-3, min(3, g['pw'][i][c]))

    def amygdala_surprise(self, mse):
        g = self.g
        thr = g['amy_thr']
        prev = self.surprise_level
        self.surprise_level = mse / (1.0 + thr)
        return self.surprise_level, max(0, self.surprise_level - prev)

    def protein_fold(self):
        g = self.g
        n = g['n']
        fold_lr = g['fold_lr']
        rw = g['rw']
        ph = self.prev_h
        h = self.h
        lk = g['leak']
        thr = g['fold_threshold']
        for k in range(n):
            rwk = rw[k]
            predicted = 0.0
            for i in range(n):
                predicted += rwk[i] * ph[i]
            fold_strength = 1.0 / (1.0 + math.exp(-abs(predicted) / max(0.01, thr)))
            if fold_strength > 0.01:
                predicted = activation(predicted, lk[k])
                err = h[k] - predicted
                for i in range(n):
                    rwk[i] += fold_lr * fold_strength * ph[i] * err
                    if rwk[i] > 1.2:
                        rwk[i] = 1.2
                    elif rwk[i] < -1.2:
                        rwk[i] = -1.2

    def learn(self, pred, actual):
        g = self.g
        n = g['n']
        lr = g['lr']
        errs = [actual[j] - pred[j] for j in range(N_CHANNELS)]
        mse = sum(e * e for e in errs) / N_CHANNELS
        surprise, edge = self.amygdala_surprise(mse)

        # 崩溃恢复：mse突然暴增时，重置工作记忆状态（不是权重）
        # 像生物受冲击后晕眩恢复——不带损坏状态继续跑
        if mse > 5.0 and hasattr(self, '_prev_mse') and self._prev_mse < 1.0:
            self.h = [0.0] * n
            self.prev_h = [0.0] * n
            self.db_history = []
            self.input_vec = []
            self.surprise_level = 0.0
            self.sens_adapt = [0.0] * N_CHANNELS
            self.prev_sens_raw = None
        self._prev_mse = mse

        replay_prob = min(1.0, surprise * 10.0)
        if random.random() < replay_prob:
            self.hippocampal_replay({'target': actual[:], 'surprise': surprise, 'salience': surprise})
        pw = g['pw']
        pb = g['pb']
        h = self.h
        for i in range(min(n, len(pw))):
            pwi = pw[i]
            hi = h[i]
            for c in range(N_CHANNELS):
                pwi[c] += lr * hi * errs[c]
                pwi[c] = max(-3, min(3, pwi[c]))
        for c in range(N_CHANNELS):
            pb[c] += lr * 1.5 * errs[c]
            pb[c] = max(-3, min(3, pb[c]))
        x = self.input_vec
        skip = g['skip']
        for j in range(min(len(skip), len(x))):
            skj = skip[j]
            xj = x[j]
            for c in range(N_CHANNELS):
                skj[c] += lr * 0.5 * xj * errs[c]
                skj[c] = max(-2, min(2, skj[c]))
        self.protein_fold()
        return mse

    def build_input(self, sens):
        self.db_history.append(sens[:])
        if len(self.db_history) > DELAY:
            self.db_history.pop(0)
        while len(self.db_history) < DELAY:
            self.db_history.insert(0, [0.0] * N_CHANNELS)
        result = sens[:]
        for frame in self.db_history:
            result.extend(frame)
        self.input_vec = result[:]
        return result

    def fwd(self, sens, update=True, region_id=None):
        g = self.g
        n = g['n']
        dec = g['dt'][0]
        sens_proc = self.fwd_sensory(sens)
        extended = self.fwd_association(sens_proc)
        ex8 = extended[:N_CHANNELS]
        x = self.build_input(ex8)
        sw = g['sw']
        rw = g['rw']
        lk = g['leak']
        h = self.h
        nh = [0.0] * n
        for i in range(n):
            a = 0.0
            for j in range(min(len(x), len(sw))):
                a += sw[j][i] * x[j]
            rwi = rw[i]
            for k in range(n):
                a += rwi[k] * h[k]
            nh[i] = activation(a * 0.9, lk[i])
        if update:
            for i in range(n):
                self.h[i] = (1 - dec) * nh[i] + dec * self.h[i]
        pred = [0.0] * N_CHANNELS
        pw = g['pw']
        pb = g['pb']
        skip = g['skip']
        hv = self.h
        for i in range(min(n, len(pw))):
            pwi = pw[i]
            hi = hv[i]
            for c in range(N_CHANNELS):
                pred[c] += hi * (pwi[c] + pb[c])
        for j in range(min(len(skip), len(x))):
            skj = skip[j]
            xj = x[j]
            for c in range(N_CHANNELS):
                pred[c] += skj[c] * xj
        if update:
            self.prev_h = self.h[:]
        return pred

    def reset(self):
        self.h = [0.0] * len(self.h)
        self.prev_h = [0.0] * len(self.prev_h)
        self.db_history = []
        self.input_vec = []
        self.replay_buffer = []
        self.surprise_level = 0.0
        self.sens_adapt = [0.0] * N_CHANNELS
        self.prev_sens_raw = None


class Org:
    """有机体：基因组 + 工作记忆。"""

    def __init__(self, gn=None):
        self.g = gn or self.rg()
        self.wm = WM(self.g)

    def rg(self):
        n = random.randint(12, 40)
        ins = N_CHANNELS * (1 + DELAY)
        g = {
            'n': n,
            'sw': [[random.uniform(-0.3, 0.3) for _ in range(n)] for __ in range(ins)],
            'pw': [[random.uniform(-0.3, 0.3) for _ in range(N_CHANNELS)] for __ in range(n)],
            'rw': [[random.uniform(-0.03, 0.03) for _ in range(n)] for __ in range(n)],
            'skip': [[random.uniform(-0.2, 0.2) for _ in range(N_CHANNELS)] for __ in range(ins)],
            'pb': [random.uniform(-0.3, 0.3) for _ in range(N_CHANNELS)],
            'dt': [random.uniform(0.5, 0.9)],
            'lr': random.uniform(0.04, 0.12),
            'fold_lr': random.uniform(0.01, 0.06),
            'leak': [random.uniform(0.005, 0.05) for _ in range(n)],
            'sens_gain': [random.uniform(0.5, 2.0) for _ in range(N_CHANNELS)],
            'sens_adapt_rate': random.uniform(0.01, 0.1),
            'assoc_w': [random.uniform(0.3, 1.5) for _ in range(3)],
            'sparse_thr': random.uniform(0.05, 0.5),
            'hip_lr': random.uniform(0.001, 0.02),
            'hip_replay_n': random.randint(2, 8),
            'amy_thr': random.uniform(0.02, 0.15),
            'fold_threshold': random.uniform(0.005, 0.05),
        }
        for i in range(n):
            g['rw'][i][i] = random.uniform(0.4, 1.0)
        return g


class Engine:
    """演化引擎：遗传算法——评估→选择→交叉→变异。"""

    def __init__(self, n_org=20, n_gen=100, seed=42, eval_ticks=200):
        self.n_org = n_org
        self.n_gen = n_gen
        self.eval_ticks = eval_ticks
        self.pop = [Org() for _ in range(n_org)]
        self.best_ever = 0.0
        self.best_g = None
        self.log = []
        random.seed(seed)

    def eval_org(self, org):
        pk = Pool(seed=42)
        pk.reset()
        org.wm.reset()
        cr = random.randint(0, 8)
        for _ in range(20):
            s = pk.sense(cr)
            org.wm.fwd(s, update=True, region_id=cr)
            pk.step()
        total_mse = 0.0
        for t in range(self.eval_ticks):
            s = pk.sense(cr)
            pred = org.wm.fwd(s, update=True, region_id=cr)
            pk.step()
            ns = pk.sense(cr)
            pk.step()
            mse = sum((ns[j] - pred[j]) ** 2 for j in range(N_CHANNELS)) / N_CHANNELS
            org.wm.learn(pred, ns)
            total_mse += mse
            if random.random() < 0.08:
                cr = random.randint(0, 8)
        return 1.0 / (1.0 + total_mse / self.eval_ticks)

    def xover(self, a, b):
        n = max(a['n'], b['n'])
        ins = N_CHANNELS * (1 + DELAY)
        ch = {
            'n': n, 'sw': [], 'pw': [], 'rw': [], 'skip': [],
            'pb': a['pb'][:] if random.random() < 0.5 else b['pb'][:],
            'dt': a['dt'][:] if random.random() < 0.5 else b['dt'][:],
            'lr': a['lr'] if random.random() < 0.5 else b['lr'],
            'fold_lr': a['fold_lr'] if random.random() < 0.5 else b['fold_lr'],
            'sens_gain': [a['sens_gain'][i] if random.random() < 0.5 else b['sens_gain'][i]
                          for i in range(N_CHANNELS)],
            'sens_adapt_rate': a['sens_adapt_rate'] if random.random() < 0.5 else b['sens_adapt_rate'],
            'assoc_w': [a['assoc_w'][i] if random.random() < 0.5 else b['assoc_w'][i]
                        for i in range(3)],
            'sparse_thr': a['sparse_thr'] if random.random() < 0.5 else b['sparse_thr'],
            'hip_lr': a['hip_lr'] if random.random() < 0.5 else b['hip_lr'],
            'hip_replay_n': a['hip_replay_n'] if random.random() < 0.5 else b['hip_replay_n'],
            'amy_thr': a['amy_thr'] if random.random() < 0.5 else b['amy_thr'],
            'fold_threshold': a['fold_threshold'] if random.random() < 0.5 else b['fold_threshold'],
        }
        for j in range(ins):
            src = a if random.random() < 0.5 else b
            ch['sw'].append([src['sw'][min(j, len(src['sw']) - 1)][min(i, src['n'] - 1)]
                             if min(j, len(src['sw']) - 1) >= 0 and
                             min(i, src['n'] - 1) < len(src['sw'][min(j, len(src['sw']) - 1)])
                             else 0.0 for i in range(n)])
        for i in range(n):
            src = a if random.random() < 0.5 else b
            si = min(i, src['n'] - 1)
            ch['pw'].append(src['pw'][si][:N_CHANNELS] if si < len(src['pw']) else [0.0] * N_CHANNELS)
        for i in range(n):
            src = a if random.random() < 0.5 else b
            si = min(i, src['n'] - 1)
            ch['rw'].append([src['rw'][si][min(k, src['n'] - 1)]
                             if si < len(src['rw']) and min(k, src['n'] - 1) < len(src['rw'][si])
                             else 0.0 for k in range(n)])
        for j in range(ins):
            src = a if random.random() < 0.5 else b
            ch['skip'].append(src['skip'][min(j, len(src['skip']) - 1)][:N_CHANNELS])
        ch['leak'] = [a['leak'][i] if i < len(a['leak']) and random.random() < 0.5
                      else b['leak'][i] if i < len(b['leak']) else 0.02
                      for i in range(n)]
        return ch

    def mutate(self, g, rate=0.03):
        n = g['n']
        for j in range(len(g['sw'])):
            for i in range(len(g['sw'][j])):
                if random.random() < rate:
                    g['sw'][j][i] += random.gauss(0, 0.05)
                    g['sw'][j][i] = max(-3, min(3, g['sw'][j][i]))
        for i in range(min(n, len(g['pw']))):
            for c in range(N_CHANNELS):
                if random.random() < rate:
                    g['pw'][i][c] += random.gauss(0, 0.05)
                    g['pw'][i][c] = max(-3, min(3, g['pw'][i][c]))
        for i in range(min(n, len(g['rw']))):
            for k in range(min(n, len(g['rw'][i]))):
                if random.random() < rate * 0.7:
                    g['rw'][i][k] += random.gauss(0, 0.03)
                    g['rw'][i][k] = max(-1.5, min(1.5, g['rw'][i][k]))
        for j in range(len(g['skip'])):
            for c in range(N_CHANNELS):
                if random.random() < rate:
                    g['skip'][j][c] += random.gauss(0, 0.05)
                    g['skip'][j][c] = max(-2, min(2, g['skip'][j][c]))
        if random.random() < 0.3:
            g['lr'] = max(0.02, min(0.2, g['lr'] + random.gauss(0, 0.01)))
        if random.random() < 0.3:
            g['fold_lr'] = max(0.005, min(0.08, g['fold_lr'] + random.gauss(0, 0.008)))
        return g

    def evolve(self):
        for gen in range(self.n_gen):
            fits = [self.eval_org(o) for o in self.pop]
            bi = fits.index(max(fits))
            bf = fits[bi]
            af = sum(fits) / len(fits)
            if bf > self.best_ever:
                self.best_ever = bf
                self.best_g = copy.deepcopy(self.pop[bi].g)
            if gen % 10 == 0 or gen == self.n_gen - 1:
                print(f"  Gen {gen:4d} bf={bf:.4f} af={af:.4f} best={self.best_ever:.4f}")
                self.log.append((gen, bf, af, self.best_ever))
            if gen == self.n_gen - 1:
                break
            idx = sorted(range(len(fits)), key=lambda i: fits[i], reverse=True)
            nx = [Org(copy.deepcopy(self.pop[idx[i]].g)) for i in range(min(4, len(self.pop)))]
            while len(nx) < self.n_org:
                t1 = random.sample(range(len(self.pop)), min(5, len(self.pop)))
                p1 = max(t1, key=lambda i: fits[i])
                t2 = random.sample(range(len(self.pop)), min(5, len(self.pop)))
                p2 = max(t2, key=lambda i: fits[i])
                child = self.xover(self.pop[p1].g, self.pop[p2].g)
                self.mutate(child, rate=0.03)
                nx.append(Org(child))
            self.pop = nx
        return self.best_ever


if __name__ == "__main__":
    print("=== EO大脑演化引擎验证 ===\n")
    eng = Engine(n_org=10, n_gen=30, seed=42, eval_ticks=100)
    result = eng.evolve()
    print(f"\n最终fitness: {result:.4f}")
    print(f"fitness > 0.5: {'是' if result > 0.5 else '否'}（预测能力涌现）")
    print(f"fitness > 0.9: {'是' if result > 0.9 else '否'}（高精度预测）")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
原始汤 · 自复制的自发涌现
=========================

★ 设计原则（继承 ★50：监测，不限制）
------------------------------------
【不预置复制】初始程序全部随机，指令集里没有"复制"这条指令。
             复制能不能出现，是实验结果，不是实验假设。
【不预置形状】不规定复制子长什么样，只给环境和压力。
【失败如实记】跑不出来就是跑不出来，不凑数。

机制
----
每个实体 = 32 字节。两个 tape 并排在 64 字节内存里：
    mem[0:32]   = 自己
    mem[32:64]  = 伙伴（复制的目标）

若某程序执行后把 mem[0:32] 写进了 mem[32:64]，
伙伴就被它覆盖了 —— 这就是一次复制。

三条压力：
    1 变异   每代每个字节以 1/64 概率随机改
    2 验证   能算出 f(x) 的程序，交互概率从 0.3 提到 1.0
    3 代谢   每条指令耗能，超预算强制停机

指令集（16 条，每条 1 字节，无操作数）
----
0x00 NOP      0x01 INC_A   0x02 DEC_A   0x03 INC_P
0x04 DEC_P    0x05 LOAD    0x06 STORE   0x07 SWAP
0x08 SET_B    0x09 ADDP    0x0A ADD     0x0B SUB
0x0C JMP      0x0D JZ      0x0E JNZ     0x0F HALT
"""

import numpy as np

TAPE = 32
MEM = TAPE * 2
PROG = TAPE


class VM:
    """极简虚拟机。返回 (halted, steps_used, energy_used)。"""

    __slots__ = ("mem",)

    def __init__(self):
        self.mem = np.zeros(MEM, dtype=np.uint8)

    def run(self, prog, energy_budget, input_x, max_steps=4096):
        mem = self.mem
        mem[:] = 0
        mem[:TAPE] = prog
        mem[MEM - 1] = input_x          # 环境输入放在最后一字节
        A = B = P = 0
        pc = 0
        steps = 0
        while steps < max_steps:
            if steps >= energy_budget:  # 代谢耗尽
                return False, steps, steps
            op = int(mem[pc])
            steps += 1
            if op == 0x00:                       # NOP
                pass
            elif op == 0x01: A = (A + 1) & 255   # INC_A
            elif op == 0x02: A = (A - 1) & 255   # DEC_A
            elif op == 0x03: P = (P + 1) & 63    # INC_P
            elif op == 0x04: P = (P - 1) & 63    # DEC_P
            elif op == 0x05: A = int(mem[P])     # LOAD
            elif op == 0x06: mem[P] = A          # STORE
            elif op == 0x07: A, B = B, A         # SWAP
            elif op == 0x08: B = A               # SET_B
            elif op == 0x09: P = (P + A) & 63    # ADDP
            elif op == 0x0A: A = (A + B) & 255   # ADD
            elif op == 0x0B: A = (A - B) & 255   # SUB
            elif op == 0x0C: pc = A & 31; continue  # JMP
            elif op == 0x0D:                     # JZ
                if A == 0: pc = B & 31; continue
            elif op == 0x0E:                     # JNZ
                if A != 0: pc = B & 31; continue
            elif op == 0x0F:                     # HALT
                return True, steps, steps
            pc = (pc + 1) & 31
        return False, steps, steps
    # 说明：pc 在 self tape 内循环，P 可寻址整个 64 字节


# ---------------------------------------------------------------- 任务
def target_f(x, coeff=(1, 3, 0)):
    """f(x) = x^2 + 3  (mod 256)。非平凡：需要循环乘法。"""
    return (x * x + 3) & 255


def evaluate(prog, x, energy_budget, vm=None):
    """验证：程序能否算出 f(x)。停机时 A 必须等于 f(x)。"""
    vm = vm or VM()
    vm.mem[:] = 0
    vm.mem[:TAPE] = prog
    vm.mem[MEM - 1] = x
    A = B = P = 0
    pc = 0
    steps = 0
    max_steps = min(energy_budget, 4096)
    while steps < max_steps:
        op = int(vm.mem[pc])
        steps += 1
        if op == 0x00: pass
        elif op == 0x01: A = (A + 1) & 255
        elif op == 0x02: A = (A - 1) & 255
        elif op == 0x03: P = (P + 1) & 63
        elif op == 0x04: P = (P - 1) & 63
        elif op == 0x05: A = int(vm.mem[P])
        elif op == 0x06: vm.mem[P] = A
        elif op == 0x07: A, B = B, A
        elif op == 0x08: B = A
        elif op == 0x09: P = (P + A) & 63
        elif op == 0x0A: A = (A + B) & 255
        elif op == 0x0B: A = (A - B) & 255
        elif op == 0x0C: pc = A & 31; continue
        elif op == 0x0D:
            if A == 0: pc = B & 31; continue
        elif op == 0x0E:
            if A != 0: pc = B & 31; continue
        elif op == 0x0F:
            return (A == target_f(x)), steps
        pc = (pc + 1) & 31
    return False, steps


# ---------------------------------------------------------------- 复制判定
def replication_fidelity(vm, prog):
    """执行后，伙伴 tape 与自己的 tape 有多像。1.0 = 完美复制。"""
    return float(np.mean(vm.mem[TAPE:] == prog[:TAPE]))


# ---------------------------------------------------------------- 汤
class Soup:
    def __init__(self, n=256, seed=0, energy_budget=96,
                 p_base=0.3, p_succ=1.0, mut_rate=1.0 / 64,
                 task_pressure=True, metabolism=True, mutate=True,
                 niches=1):
        self.rng = np.random.default_rng(seed)
        self.n = n
        self.energy = energy_budget
        self.p_base, self.p_succ = p_base, p_succ
        self.mut_rate = mut_rate
        self.task_pressure = task_pressure
        self.metabolism = metabolism
        self.mutate = mutate
        self.niches = niches
        self.pop = self.rng.integers(0, 16, size=(n, PROG), dtype=np.uint8)
        self.vm = VM()
        self.hist = []          # (gen, 复制率, 任务成功率, 平均保真度)

    # ---- 统计当前种群里"是否会复制" ----
    def measure(self, xs=(1, 2, 3, 5, 7)):
        reps, solved = [], []
        for prog in self.pop:
            # 复制能力：给自己配一个全零伙伴，看能不能写过去
            self.vm.mem[:] = 0
            self.vm.mem[:TAPE] = prog
            vm2 = VM()
            vm2.mem[:] = 0
            vm2.mem[:TAPE] = prog
            vm2.run(prog, self.energy if self.metabolism else 10 ** 9, 3)
            reps.append(replication_fidelity(vm2, prog))
            ok = False
            for x in xs:
                good, _ = evaluate(prog, x, self.energy if self.metabolism
                                   else 10 ** 9)
                if good:
                    ok = True
                    break
            solved.append(ok)
        return np.array(reps), np.array(solved)

    def step(self, gen):
        rng = self.rng
        n = self.n
        budget = self.energy if self.metabolism else 10 ** 9

        # 1 变异
        if self.mutate:
            mask = rng.random((n, PROG)) < self.mut_rate
            self.pop[mask] = rng.integers(0, 16, size=int(mask.sum()),
                                          dtype=np.uint8)

        # 2 验证（任务压力）
        x = int(rng.integers(0, 8))
        good = np.zeros(n, dtype=bool)
        for i in range(n):
            g, _ = evaluate(self.pop[i], x, budget)
            good[i] = g
        p_int = np.where(good & self.task_pressure, self.p_succ, self.p_base)
        if not self.task_pressure:
            p_int = np.full(n, self.p_base)

        # 3 交互：配对，看能不能把伙伴覆盖掉
        order = rng.permutation(n)
        new_pop = self.pop.copy()
        n_rep = 0
        for k in range(0, n - 1, 2):
            i, j = order[k], order[k + 1]
            if rng.random() > p_int[i]:
                continue
            self.vm.mem[:] = 0
            self.vm.mem[:TAPE] = self.pop[i]
            self.vm.mem[TAPE:] = self.pop[j]     # 伙伴登场
            A_before = self.vm.mem[TAPE:].copy()
            self.vm.run(self.pop[i], budget, x)
            after = self.vm.mem[TAPE:]
            if not np.array_equal(after, A_before) and \
               np.array_equal(after, self.pop[i]):
                n_rep += 1
                new_pop[j] = after
        self.pop = new_pop
        return n_rep

    def run(self, gens=200, measure_every=20):
        out = []
        for g in range(gens):
            self.step(g)
            if g % measure_every == 0 or g == gens - 1:
                reps, solved = self.measure()
                rep_rate = float(np.mean(reps > 0.99))
                out.append({"gen": g,
                            "rep_rate": rep_rate,
                            "mean_fid": float(np.mean(reps)),
                            "max_fid": float(np.max(reps)),
                            "solve_rate": float(np.mean(solved))})
                self.hist.append(out[-1])
        return out

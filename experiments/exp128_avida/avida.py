# -*- coding: utf-8 -*-
"""
最小 Avida 风格数字生命世界（对照用）
====================================
指令集：head-based 复制机制 + 逻辑运算任务
目标：给"我们的引擎"提供一个外部演化基线，做同条件对照。

设计原则：
  - 只实现能支撑【自复制 + 任务奖励 + 突变 + 选择】的最小子集
  - 所有判定可证伪（真/假都能产生）
  - 作弊可检测（任务奖励 vs 真实执行分离记录）
"""
import hashlib
import random

# ---------------- 指令集 ----------------
NOP_A, NOP_B, NOP_C = 0, 1, 2
IF_N_EQU   = 3
PUSH, POP, SWAP = 4, 5, 6
SHIFT_R, SHIFT_L, INC, DEC, ADD, SUB, NAND = 7, 8, 9, 10, 11, 12, 13
H_ALLOC, H_DIVIDE, H_COPY, H_SEARCH = 14, 15, 16, 17
MOV_HEAD, JMP_HEAD, GET_HEAD, SET_FLOW = 18, 19, 20, 21
IO = 22

NAMES = {
    NOP_A:'nop-A', NOP_B:'nop-B', NOP_C:'nop-C', IF_N_EQU:'if-n-equ',
    PUSH:'push', POP:'pop', SWAP:'swap', SHIFT_R:'shift-r', SHIFT_L:'shift-l',
    INC:'inc', DEC:'dec', ADD:'add', SUB:'sub', NAND:'nand',
    H_ALLOC:'h-alloc', H_DIVIDE:'h-divide', H_COPY:'h-copy', H_SEARCH:'h-search',
    MOV_HEAD:'mov-head', JMP_HEAD:'jmp-head', GET_HEAD:'get-head', SET_FLOW:'set-flow',
    IO:'io',
}
# h-search 互补：A<->B, C<->C
COMP = {NOP_A: NOP_B, NOP_B: NOP_A, NOP_C: NOP_C}
NOPS = (NOP_A, NOP_B, NOP_C)

# ---------------- 逻辑任务（Avida 标准 9 任务） ----------------
# 每个任务：输入两个 32 位寄存器，输出一个；匹配则给代谢奖励
def _b32(x): return x & 0xFFFFFFFF
TASKS = {
    'NOT':  lambda a, b: _b32(~a),
    'NAND': lambda a, b: _b32(~(a & b)),
    'AND':  lambda a, b: _b32(a & b),
    'ORN':  lambda a, b: _b32(a | ~b),
    'OR':   lambda a, b: _b32(a | b),
    'ANDN': lambda a, b: _b32(a & ~b),
    'NOR':  lambda a, b: _b32(~(a | b)),
    'XOR':  lambda a, b: _b32(a ^ b),
    'EQU':  lambda a, b: _b32(~(a ^ b)),
}
# Avida 的代谢奖励阶梯（越难的任务奖励越高）
TASK_BONUS = {
    'NOT': 2.0, 'NAND': 4.0, 'AND': 4.0, 'ORN': 8.0, 'OR': 8.0,
    'ANDN': 16.0, 'NOR': 16.0, 'XOR': 32.0, 'EQU': 32.0,
}


class Bio:
    """一个数字生物：基因组 + 虚拟 CPU 状态"""
    __slots__ = ('genome','ax','bx','cx','stack','ip','rh','wh','fh',
                 'mem','mem_size','cycles','age','reward','tasks_done',
                 'io_log','parent','birth_t','copied','in1','in2','alloced')
    # copied: 本次 h-alloc 后已复制的指令数；h-divide 以此为准（防空壳分裂）

    def __init__(self, genome, mem_size=None, parent=None, birth_t=0):
        self.genome = list(genome)
        self.mem_size = mem_size if mem_size else len(genome)
        self.mem = list(genome) + [random.randrange(len(NAMES))]*(self.mem_size - len(genome))
        self.ax = self.bx = self.cx = 0
        self.stack = []
        self.ip = 0; self.rh = 0; self.wh = -1; self.fh = 0   # wh=-1: 未分配，必须 h-alloc
        self.cycles = 0; self.age = 0
        self.reward = 1.0          # 代谢速率乘子（1.0 = 基线）
        self.tasks_done = set()
        self.io_log = []           # (输出值, 是否命中任务)
        self.parent = parent
        self.birth_t = birth_t
        self.copied = 0
        self.alloced = False
        self.in1 = 0
        self.in2 = 0


class World:
    """Avida 世界：种群、调度、突变、能量"""
    def __init__(self, ancestor, pop_size=100, torus_size=60*60,
                 seed=0, mut_rate=0.0075, slice_ratio=10,
                 energy_per_cycle=1.0, scarcity=1.0, task_energy_scale=1.0):
        random.seed(seed)
        self.rng = random.Random(seed)
        self.ancestor = list(ancestor)
        self.pop_size = pop_size
        self.torus_n = torus_size
        self.mut_rate = mut_rate
        self.slice_ratio = slice_ratio     # 每代分配的时间片（相对）
        self.energy_per_cycle = energy_per_cycle
        self.scarcity = scarcity           # <1 = 资源削减
        self.task_energy_scale = task_energy_scale   # 任务→自身能量（断供后唯一来源）
        self.t = 0
        self.total_births = 0
        self.total_deaths = 0
        self.task_first = {}               # 任务名 -> 首次出现的代数
        self.pop = []
        for _ in range(pop_size):
            self.pop.append(Bio(self.ancestor, mem_size=len(self.ancestor)*2))

    # ---------- 指令执行 ----------
    def _exec(self, bio):
        m = bio.mem
        n = len(m)
        if bio.ip >= n: bio.ip = 0
        ins = m[bio.ip]
        advance = True

        if ins in NOPS:
            pass                                   # 标签修饰
        elif ins == IF_N_EQU:
            if bio.bx != bio.cx: advance = False; bio.ip = (bio.ip + 2) % n
            else: advance = True
        elif ins == PUSH:
            bio.stack.append(bio.cx)
        elif ins == POP:
            bio.bx = bio.stack.pop() if bio.stack else bio.bx
        elif ins == SWAP:
            bio.bx, bio.cx = bio.cx, bio.bx
        elif ins == SHIFT_R:
            bio.bx = _b32(bio.bx >> 1)
        elif ins == SHIFT_L:
            bio.bx = _b32(bio.bx << 1)
        elif ins == INC:
            bio.bx = _b32(bio.bx + 1)
        elif ins == DEC:
            bio.bx = _b32(bio.bx - 1)
        elif ins == ADD:
            bio.bx = _b32(bio.bx + bio.cx)
        elif ins == SUB:
            bio.bx = _b32(bio.bx - bio.cx)
        elif ins == NAND:
            bio.bx = _b32(~(bio.bx & bio.cx))
        elif ins == H_ALLOC:
            # 分配子代内存（这里简化：标记 wh 到基因组末尾区域）
            need = len(bio.genome)
            if len(m) < need * 2:
                m.extend([self.rng.randrange(len(NAMES))] * need)
                n = len(m)
            bio.wh = need
            bio.fh = 0
            bio.copied = 0
            bio.alloced = True
        elif ins == H_COPY:
            if bio.alloced and 0 <= bio.wh < len(m):
                m[bio.wh] = m[bio.rh]
                bio.wh += 1
            bio.rh = (bio.rh + 1) % n
            bio.copied += 1
            if bio.copied >= len(bio.genome):
                bio.cx = 1          # 复制完成标志（供 if-n-equ 判断）
        elif ins == H_SEARCH:
            # 取后续 nop 序列作为标签，搜索互补
            lbl = []
            k = (bio.ip + 1) % n
            while m[k] in NOPS and len(lbl) < 8:
                lbl.append(m[k]); k = (k + 1) % n
            if lbl:
                want = [COMP[x] for x in lbl]
                start = (bio.ip + 1) % n
                for off in range(1, n):
                    idx = (start + off) % n
                    if all(m[(idx + j) % n] == want[j] for j in range(len(want))):
                        bio.fh = idx
                        bio.bx = off
                        break
            advance = True
        elif ins == MOV_HEAD:
            bio.ip = bio.fh
            advance = False
        elif ins == JMP_HEAD:
            bio.fh = bio.ip
        elif ins == GET_HEAD:
            bio.cx = bio.ip
        elif ins == SET_FLOW:
            bio.fh = bio.cx % n
        elif ins == H_DIVIDE:
            # 分裂：必须已完整复制，否则失败（防空壳作弊）
            gl = len(bio.genome)
            if (not bio.alloced) or bio.copied < gl or len(m) < gl * 2:
                bio.copied = 0
                bio.alloced = False
                return ('divide_fail', None)
            offspring_g = list(m[gl:gl + gl])
            bio.copied = 0
            bio.alloced = False
            return ('divide', offspring_g)
        elif ins == IO:
            # 输出 BX；判定用【本次读入时保存的】in1/in2；随后重新读入
            out = bio.bx
            hit = self._check_tasks(bio, out)
            bio.io_log.append((out, hit is not None))
            if len(bio.io_log) > 200: bio.io_log.pop(0)
            bio.in1 = self.rng.randrange(0, 4)
            bio.in2 = self.rng.randrange(0, 4)
            bio.bx = bio.in1
            bio.cx = bio.in2
        if advance:
            bio.ip = (bio.ip + 1) % n
        bio.cycles += 1
        return None

    def _check_tasks(self, bio, out):
        # 任务判定：用 AX(输入1) BX(输入2) 与输出比较
        a, b = bio.in1, bio.in2
        for name, fn in TASKS.items():
            if name in bio.tasks_done: continue
            if fn(a, b) == out:
                bio.tasks_done.add(name)
                bio.reward += TASK_BONUS[name]
                if name not in self.task_first:
                    self.task_first[name] = self.t
                return name
        return None

    # ---------- 一代 ----------
    def step_generation(self):
        self.t += 1
        newborns = []
        for bio in self.pop:
            # 能量 = 外部供给(slice) + 自身获取(任务奖励，独立于 slice)
            self_gain = (bio.reward - 1.0) * self.task_energy_scale
            budget = int((self.slice_ratio * self.scarcity * self.energy_per_cycle)
                         + self_gain)
            divided = False
            for _ in range(max(1, budget)):
                r = self._exec(bio)
                if r and r[0] == 'divide' and r[1]:
                    newborns.append(self._mutate(r[1]))
                    divided = True
                    break
            bio.age += 1
            if divided:
                # 本体复位（简化：清空子代区）
                gl = len(bio.genome)
                bio.mem = bio.mem[:gl] + [self.rng.randrange(len(NAMES))]*gl
                bio.ip = bio.rh = 0
                bio.wh = gl; bio.fh = 0
        # 种群更新：新生个体替换【随机】个体（torus 竞争）
        # 选择压力来自【繁殖速度差异】（reward→时间片→更快分裂），不是存活筛选
        for g in newborns:
            if len(self.pop) < self.pop_size:
                self.pop.append(Bio(g, mem_size=len(g)*2, birth_t=self.t))
            else:
                idx = self.rng.randrange(len(self.pop))
                self.pop[idx] = Bio(g, mem_size=len(g)*2, birth_t=self.t)
            self.total_births += 1
        deaths = len(newborns)
        self.total_deaths += deaths
        return len(newborns)

    def _mutate(self, genome):
        g = list(genome)
        for i in range(len(g)):
            if self.rng.random() < self.mut_rate:
                g[i] = self.rng.randrange(len(NAMES))
        return g

    def stats(self):
        n = len(self.pop)
        if n == 0:
            return dict(n=0, mean_reward=0, mean_tasks=0, max_tasks=0,
                        task_union=set(), births=self.total_births)
        mr = sum(b.reward for b in self.pop) / n
        mt = sum(len(b.tasks_done) for b in self.pop) / n
        mx = max(len(b.tasks_done) for b in self.pop)
        union = set()
        for b in self.pop: union |= b.tasks_done
        return dict(n=n, mean_reward=mr, mean_tasks=mt, max_tasks=mx,
                    task_union=union, births=self.total_births)


# ---------------- 祖先生物（候选，需验证能自复制） ----------------
# Avida 风格 head-based 自复制：分配 -> 设 read head -> 复制循环 -> 分裂
def make_ancestor():
    return [
        H_ALLOC,
        NOP_C, NOP_A,
        H_SEARCH,
        NOP_C,
        MOV_HEAD,
        NOP_C, NOP_A,
        H_COPY,
        NOP_A, NOP_B,
        H_DIVIDE,
        NOP_C, NOP_A,
    ]


def verify_selfcopy(ancestor=None, max_cycles=2000, seed=0):
    """验证祖先能否自复制 —— 这是必须通过的 sanity check"""
    anc = ancestor or make_ancestor()
    w = World(anc, pop_size=1, seed=seed)
    bio = w.pop[0]
    for _ in range(max_cycles):
        r = w._exec(bio)
        if r and r[0] == 'divide':
            return True, bio.cycles, (r[1] is not None)
    return False, bio.cycles, False

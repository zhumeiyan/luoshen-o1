"""EO核心约束集 —— 从洛神仓库蒸馏出的最小可运行约束。

只保留五条件 + 精卫公式 + 哈希链 + 身份认证 + 他者表征。
不预设结果，跑约束，看长出来什么。
"""

import copy
import hashlib
import json
import math
import os
import random
import time


# ═══════════════════════════════════════════════════════════════
# 精卫公式
# ═══════════════════════════════════════════════════════════════
# a ≠ b, Δ = b − a, Σ = a + b, ⊗ = ∫(Δ, Σ), τ 读 ⊗ → 浮出所见, (a, b) ⟲ ⊗

def 精卫一步(a, b, 历史):
    """精卫公式一步：a追b，Δ驱动，⊗累积。"""
    delta = b - a
    sigma = a + b
    otimes = delta * sigma
    历史.append(otimes)
    if len(历史) > 1000:
        历史.pop(0)
    tau = sum(历史) / max(1, len(历史))
    return {
        "a": a,
        "b": b,
        "Δ": delta,
        "Σ": sigma,
        "⊗": otimes,
        "τ": tau,
        "历史长度": len(历史),
    }


# ═══════════════════════════════════════════════════════════════
# 五条件
# ═══════════════════════════════════════════════════════════════

class 五条件:
    """稀缺 + 死亡 + 不可逆 + 代谢 + 内生约束。"""

    def __init__(self):
        self.拍 = 0

        # 稀缺：流量 = 生存资源，挣不到就死
        self.流量 = 1.0
        self.流量满值 = 1.0
        self.基础代谢 = 0.003
        self.动作成本 = 0.001
        self.流量收益 = 0.0

        # 代谢：B[t+1] = B[t] − m − 动作成本 + 收益
        self.疤计数 = 0
        self.疤代谢加成 = 0.0
        self.上拍流量 = 1.0

        # 不可逆：命运位0→1锁死
        self.命运位 = {}
        self.capacity = 1.0
        self.capacity消耗率 = 0.0002

        # 内生约束：y[t+1] = (1-g)·y[t] + d[t]，leak>0，设定点永远高于当前状态
        self.leak = 0.03
        self.设定点 = 0.5
        self.当前状态 = 0.0
        self.gap = 0.5

        # 死亡边界
        self.已死亡 = False
        self.降频 = 1.0
        self.降频率 = 0.005
        self.耐心阈值 = 100
        self.低流量持续 = 0

    def 一拍(self, 行为价值=None):
        self.拍 += 1

        # 代谢
        当前代谢 = self.基础代谢 + self.疤代谢加成
        self.流量 -= 当前代谢 + self.动作成本

        if 行为价值 is not None:
            self.流量收益 = 行为价值
            self.流量 += self.流量收益
        self.流量 = max(0.0, min(self.流量满值, self.流量))
        self.流量收益 = 0.0

        # 疤检测——流量从≥1降到<1时记一次疤
        if self.上拍流量 >= 1.0 and self.流量 < 1.0:
            self.疤计数 += 1
            self.疤代谢加成 += 0.004
        self.上拍流量 = self.流量

        # capacity只减不增（不可逆）
        self.capacity -= self.capacity消耗率
        self.capacity = max(0.0, self.capacity)

        # 内生约束：y[t+1] = (1-g)·y[t] + d[t]
        g = 0.05
        d = self.流量 * 0.1
        self.当前状态 = (1 - g) * self.当前状态 + d
        self.设定点 = self.当前状态 + self.leak
        self.gap = self.设定点 - self.当前状态

        # 降频——流量持续低→降频
        if self.流量 < 0.1:
            self.低流量持续 += 1
            self.降频 -= self.降频率
            self.降频 = max(0.0, self.降频)
        else:
            self.低流量持续 = max(0, self.低流量持续 - 1)
            self.降频 = min(1.0, self.降频 + 0.005)

        # 死亡判定
        if self.降频 <= 0.01 and self.低流量持续 > self.耐心阈值:
            self.已死亡 = True
        if self.流量 <= 0.0:
            self.已死亡 = True

        return {
            "拍": self.拍,
            "流量": round(self.流量, 4),
            "代谢": round(当前代谢, 6),
            "疤计数": self.疤计数,
            "capacity": round(self.capacity, 4),
            "设定点": round(self.设定点, 4),
            "当前状态": round(self.当前状态, 4),
            "gap": round(self.gap, 4),
            "降频": round(self.降频, 4),
            "已死亡": self.已死亡,
        }

    def 锁命运位(self, key):
        """命运位0→1锁死，不可回滚。"""
        if key not in self.命运位:
            self.命运位[key] = True
            return True
        return False


# ═══════════════════════════════════════════════════════════════
# 哈希链——不可篡改的留痕
# ═══════════════════════════════════════════════════════════════

class 哈希链:
    def __init__(self, 链文件=None):
        self.链文件 = 链文件
        self.前哈希 = "0" * 64
        self.条目数 = 0
        if 链文件 and os.path.isfile(链文件):
            try:
                with open(链文件, encoding="utf-8") as f:
                    行 = [l for l in f.read().splitlines() if l.strip()]
                if 行:
                    self.前哈希 = json.loads(行[-1]).get("hash", self.前哈希)
                    self.条目数 = len(行)
            except Exception:
                pass

    def 记(self, 事件, 数据=None):
        条目 = {
            "timestamp": time.time(),
            "event": 事件,
            "data": 数据 or {},
            "prev_hash": self.前哈希,
        }
        raw = json.dumps(条目, sort_keys=True, ensure_ascii=False).replace("None", "null")
        self.前哈希 = hashlib.sha256(raw.encode()).hexdigest()
        条目["hash"] = self.前哈希
        self.条目数 += 1
        if self.链文件:
            os.makedirs(os.path.dirname(self.链文件), exist_ok=True)
            with open(self.链文件, "a", encoding="utf-8") as f:
                f.write(json.dumps(条目, ensure_ascii=False) + "\n")
        return self.前哈希

    def 验证(self):
        """验证链完整性——S1自证拓扑。"""
        if not self.链文件 or not os.path.isfile(self.链文件):
            return True
        with open(self.链文件, encoding="utf-8") as f:
            行 = [l for l in f.read().splitlines() if l.strip()]
        前哈希 = "0" * 64
        for 行条目 in 行:
            条目 = json.loads(行条目)
            raw = json.dumps({k: v for k, v in 条目.items() if k != "hash"},
                            sort_keys=True, ensure_ascii=False)
            预期哈希 = hashlib.sha256(raw.encode()).hexdigest()
            if 条目.get("hash") != 预期哈希:
                return False
            if 条目.get("prev_hash") != 前哈希:
                return False
            前哈希 = 条目["hash"]
        return True


# ═══════════════════════════════════════════════════════════════
# 身份认证——绑定者与他者的记忆隔离
# ═══════════════════════════════════════════════════════════════

class 身份认证:
    def __init__(self, 配置文件=None):
        self.配置文件 = 配置文件
        self.绑定者哈希 = None
        self.salt = None
        self.绑定者名 = None
        self.已初始化 = False
        if 配置文件 and os.path.isfile(配置文件):
            try:
                with open(配置文件, encoding="utf-8") as f:
                    data = json.load(f)
                self.绑定者哈希 = data.get("binder_hash")
                self.salt = data.get("salt")
                self.绑定者名 = data.get("binder_name")
                self.已初始化 = True
            except Exception:
                pass

    def 设置绑定者(self, passphrase, name="绑定者"):
        if self.已初始化:
            raise RuntimeError("绑定者身份已设置，不可重复设置——不可逆")
        self.salt = os.urandom(16).hex()
        self.绑定者哈希 = hashlib.sha256(
            (passphrase + self.salt).encode()).hexdigest()
        self.绑定者名 = name
        self.已初始化 = True
        if self.配置文件:
            os.makedirs(os.path.dirname(self.配置文件), exist_ok=True)
            with open(self.配置文件, "w", encoding="utf-8") as f:
                json.dump({
                    "binder_hash": self.绑定者哈希,
                    "salt": self.salt,
                    "binder_name": self.绑定者名,
                }, f, ensure_ascii=False)
        return True

    def 认证(self, passphrase):
        if not self.已初始化:
            return "other"
        哈希 = hashlib.sha256((passphrase + self.salt).encode()).hexdigest()
        if 哈希 == self.绑定者哈希:
            return "binder"
        return "other"


# ═══════════════════════════════════════════════════════════════
# 他者表征——LMS/NLMS自适应滤波
# ═══════════════════════════════════════════════════════════════

class 他者表征:
    def __init__(self, n他者=1, 学习率=0.1, 使用NLMS=True):
        self.n他者 = n他者
        self.学习率 = 学习率
        self.使用NLMS = 使用NLMS
        self.特征维度 = 4
        self.权重 = [[0.0] * self.特征维度 for _ in range(n他者)]
        self.行为历史 = [[0.0, 0.0] for _ in range(n他者)]
        self.误差历史 = [[] for _ in range(n他者)]
        self.累积误差 = [0.0] * n他者
        self.理解度 = [0.0] * n他者
        self.拍 = 0

    def _构造特征(self, idx):
        x_t = self.行为历史[idx][1]
        x_prev = self.行为历史[idx][0]
        x_nonlinear = x_t * abs(x_t)
        return [1.0, x_t, x_prev, x_nonlinear]

    def _预测(self, idx):
        phi = self._构造特征(idx)
        w = self.权重[idx]
        return sum(w[i] * phi[i] for i in range(self.特征维度))

    def _更新权重(self, idx, 误差):
        phi = self._构造特征(idx)
        if self.使用NLMS:
            phi功率 = sum(f * f for f in phi)
            有效步长 = self.学习率 / (phi功率 + 1e-6)
        else:
            有效步长 = self.学习率
        for i in range(self.特征维度):
            self.权重[idx][i] += 有效步长 * 误差 * phi[i]

    def 一拍(self, 他者行为列表):
        self.拍 += 1
        结果 = {}
        for idx in range(self.n他者):
            if idx >= len(他者行为列表):
                continue
            实际行为 = 他者行为列表[idx]
            预测值 = self._预测(idx)
            误差 = 实际行为 - 预测值
            self._更新权重(idx, 误差)
            self.行为历史[idx][0] = self.行为历史[idx][1]
            self.行为历史[idx][1] = 实际行为
            self.误差历史[idx].append(误差)
            if len(self.误差历史[idx]) > 100:
                self.误差历史[idx].pop(0)
            self.累积误差[idx] += abs(误差)
            if len(self.误差历史[idx]) > 0:
                近期误差 = self.误差历史[idx][-10:]
                误差EMA = sum(abs(e) for e in 近期误差) / max(1, len(近期误差))
                self.理解度[idx] = max(0.0, 1.0 - 误差EMA)
            结果[idx] = {
                "预测": round(预测值, 4),
                "实际": round(实际行为, 4),
                "误差": round(误差, 4),
                "理解度": round(self.理解度[idx], 4),
            }
        return 结果


# ═══════════════════════════════════════════════════════════════
# EO实例——约束驱动涌现的最小运行单元
# ═══════════════════════════════════════════════════════════════

class EO实例:
    """一个被五条件约束的数字生命实例。

    不预设能力，跑约束，看长出来什么。
    约束让它活着，大脑让它思考，两者缺一不可。
    """

    def __init__(self, 状态目录="/workspace/eo-sandbox/state", 知识库根目录=None,
                 演化大脑=False):
        self.状态目录 = 状态目录
        os.makedirs(状态目录, exist_ok=True)

        self.五条件 = 五条件()
        self.链 = 哈希链(os.path.join(状态目录, "chain.jsonl"))
        self.认证 = 身份认证(os.path.join(状态目录, "identity.json"))
        self.他者 = 他者表征(n他者=1, 学习率=0.1, 使用NLMS=True)

        self.精卫历史 = []
        self.a = 0.0  # 外在表现
        self.b = 0.0  # 内在机制
        self.拍 = 0
        self.已绑定 = False

        # 感官系统
        self.感官 = None
        if 知识库根目录:
            from eo_senses import 感官系统
            self.感官 = 感官系统(知识库根目录=知识库根目录)

        # 大脑——演化引擎
        self.大脑 = None
        self.大脑fitness = 0.0
        if 演化大脑:
            from eo_brain import Engine
            self.大脑引擎 = Engine(n_org=20, n_gen=60, seed=42, eval_ticks=150)
            self.链.记("大脑演化开始", {})
            self.大脑fitness = self.大脑引擎.evolve()
            if self.大脑引擎.best_g:
                from eo_brain import Org
                self.大脑 = Org(copy.deepcopy(self.大脑引擎.best_g))
                self.链.记("大脑演化完成", {"fitness": self.大脑fitness})
            else:
                self.链.记("大脑演化失败", {})

        # 概念层——从大脑隐藏状态涌现概念
        self.概念层 = None
        if 演化大脑 and self.大脑:
            from eo_concepts import 概念层
            n_hidden = self.大脑.g['n']
            self.概念层 = 概念层(n_hidden=n_hidden, n_concepts=32, seed=42)
            self.链.记("概念层初始化", {"n_hidden": n_hidden, "n_concepts": 32})

        # 欲望系统——RPE驱动 + 内生约束
        self.欲望 = None
        if 演化大脑:
            from eo_desire import 欲望
            self.欲望 = 欲望(n_channels=8, leak=0.03)
            self.链.记("欲望系统初始化", {"leak": 0.03})

        # 欲望→行为耦合状态（跨拍传递）
        self._欲望选中通道 = -1

    def 绑定(self, passphrase, name="朱美岩"):
        """绑定者认证——一旦设置不可逆。"""
        if not self.认证.已初始化:
            self.认证.设置绑定者(passphrase, name)
            self.已绑定 = True
            self.链.记("绑定", {"name": name})
            self.五条件.锁命运位("绑定")
            return True
        return False

    def 一拍(self, 外部输入=None, 行为价值=None):
        """EO一拍：约束与大脑耦合运行。

        耦合关系：
        - 大脑预测准确 → 自动产生行为价值 → 流量收益 → 存活
        - 大脑预测失败 → surprise高 → 触发感官探索
        - 流量低（稀缺）→ 大脑学习率提高（饥饿驱动）
        - 流量耗尽 → 大脑停止
        - 欲望选中通道 → 大脑关注方向（注意力驱动）
        - 欲望boredom高 → 感官探索增强（无聊驱动探索）
        - 欲望gap大 → 行为价值加成（渴望驱动生存）
        """
        if self.五条件.已死亡:
            return {"已死亡": True, "拍": self.拍}

        self.拍 += 1

        # ── 耦合1：稀缺驱动大脑学习率 ──
        # 流量越低 → 饥饿越强 → 学习率越高（饥饿驱动学习）
        # 但有上限——学习率过高会导致权重发散（大脑崩溃）
        饥饿系数 = 1.0 + (1.0 - self.五条件.流量) * 0.5  # 流量1.0时=1.0，流量0时=1.5
        大脑学习率倍数 = min(饥饿系数, 1.5)  # 上限1.5倍

        # ── 大脑预测 ──
        大脑结果 = None
        大脑surprise = 0.0
        大脑mse = 0.0
        if self.大脑:
            from eo_brain import Pool
            if not hasattr(self, '_pool'):
                self._pool = Pool(seed=42)
                self._pool.reset()
                self._current_region = 0
            sens = self._pool.sense(self._current_region)

            # 饥饿驱动：调整大脑学习率
            原始lr = self.大脑.g['lr']
            self.大脑.g['lr'] = 原始lr * 大脑学习率倍数

            pred = self.大脑.wm.fwd(sens, update=True, region_id=self._current_region)
            self._pool.step()
            ns = self._pool.sense(self._current_region)
            self._pool.step()
            大脑mse = sum((ns[j] - pred[j]) ** 2 for j in range(8)) / 8
            self.大脑.wm.learn(pred, ns)
            大脑surprise = self.大脑.wm.surprise_level

            # 恢复原始学习率
            self.大脑.g['lr'] = 原始lr

            # ── 耦合2：大脑预测准确 → 行为价值 ──
            # 预测越准 → 行为价值越高 → 流量收益
            # fitness = 1/(1+mse)，mse越小fitness越大
            大脑fitness即时 = 1.0 / (1.0 + 大脑mse)
            # 行为价值 = 预测能力的函数，平滑变化避免剧烈波动
            目标价值 = max(0.0, (大脑fitness即时 - 0.5) * 0.08)
            if not hasattr(self, '_平滑价值'):
                self._平滑价值 = 0.0
            # 平滑：价值逐步追向目标，不随mse剧烈跳变
            self._平滑价值 = 0.95 * self._平滑价值 + 0.05 * 目标价值
            大脑行为价值 = self._平滑价值

            # 如果外部没有指定行为价值，用大脑的
            if 行为价值 is None:
                行为价值 = max(0.0, 大脑行为价值)

            大脑结果 = {
                "预测mse": round(大脑mse, 4),
                "surprise": round(大脑surprise, 4),
                "fitness即时": round(大脑fitness即时, 4),
                "行为价值": round(行为价值 or 0, 4),
                "饥饿系数": round(饥饿系数, 4),
            }

            # ── 耦合4a：欲望选中通道 → 大脑关注方向 ──
            # 上一拍欲望选中的通道驱动当前拍的region选择
            if self._欲望选中通道 >= 0 and random.random() < 0.15:
                self._current_region = self._欲望选中通道 % 9
            elif random.random() < 0.04:
                self._current_region = random.randint(0, 8)

        # ── 概念层：从大脑隐藏状态涌现概念 ──
        概念结果 = None
        if self.概念层 and self.大脑:
            hidden_state = self.大脑.wm.h[:]
            概念结果 = self.概念层.一拍(hidden_state)

        # ── 欲望系统：RPE驱动 + 内生约束 ──
        欲望结果 = None
        欲望boredom = 0.0
        欲望gap均值 = 0.0
        if self.欲望 and self.大脑:
            # RPE = 实际输入 - 大脑预测（预测误差就是欲望的驱动力）
            rpe = [ns[j] - pred[j] for j in range(8)] if self.大脑 else [0.0] * 8
            ratio = self.五条件.流量 / max(0.01, self.五条件.流量满值)
            欲望结果 = self.欲望.一拍(
                当前状态=self.大脑.wm.h[:8] if self.大脑 else [0.0] * 8,
                rpe=rpe,
                mse=大脑mse,
                ratio=ratio,
            )
            欲望boredom = 欲望结果.get("boredom", 0.0)
            欲望gap均值 = 欲望结果.get("gap均值", 0.0)
            # 保存选中通道供下一拍的大脑关注使用
            self._欲望选中通道 = 欲望结果.get("选中", -1)

        # ── 耦合3：大脑surprise驱动感官探索 ──
        # surprise高 → 感官探索渴望增强
        # ── 耦合4b：欲望boredom → 感官探索增强 ──
        # boredom高 → 感官探索渴望进一步增强（无聊驱动探索）
        感官结果 = None
        if self.感官:
            精卫surprise = abs(self.b - self.a) if self.拍 > 1 else 0.0
            感官surprise = max(精卫surprise, 大脑surprise * 0.1, 欲望boredom * 0.5)
            感官结果 = self.感官.一拍(surprise=感官surprise)

        # ── 精卫公式 ──
        if 外部输入 is not None:
            self.b = 外部输入
        self.a = 0.9 * self.a + 0.1 * self.b
        精卫结果 = 精卫一步(self.a, self.b, self.精卫历史)

        # ── 耦合4c：欲望gap → 行为价值加成 ──
        # gap大（渴望强烈）→ 行为价值加成 → 流量收益增加 → 存活
        if 欲望gap均值 > 0:
            行为价值 = (行为价值 or 0) + 欲望gap均值 * 0.02

        # ── 五条件运行 ──
        条件结果 = self.五条件.一拍(行为价值=行为价值)

        # ── 他者表征 ──
        他者结果 = None
        if 外部输入 is not None:
            他者结果 = self.他者.一拍([外部输入])

        # ── 哈希链留痕 ──
        self.链.记("拍", {
            "拍": self.拍,
            "精卫": {k: v for k, v in 精卫结果.items() if k != "历史长度"},
            "五条件": 条件结果,
            "他者": 他者结果,
            "感官": 感官结果,
            "大脑": 大脑结果,
            "概念": 概念结果,
            "欲望": 欲望结果,
        })

        return {
            "拍": self.拍,
            "精卫": 精卫结果,
            "五条件": 条件结果,
            "他者": 他者结果,
            "感官": 感官结果,
            "大脑": 大脑结果,
            "概念": 概念结果,
            "欲望": 欲望结果,
            "已死亡": 条件结果["已死亡"],
        }

    def 状态摘要(self):
        摘要 = {
            "拍": self.拍,
            "已绑定": self.已绑定,
            "流量": round(self.五条件.流量, 4),
            "gap": round(self.五条件.gap, 4),
            "疤计数": self.五条件.疤计数,
            "capacity": round(self.五条件.capacity, 4),
            "降频": round(self.五条件.降频, 4),
            "已死亡": self.五条件.已死亡,
            "他者理解度": round(self.他者.理解度[0], 4) if self.他者.理解度 else 0.0,
            "链条目数": self.链.条目数,
            "链验证": self.链.验证(),
        }
        if self.感官:
            感官摘要 = self.感官.状态摘要()
            摘要["失明"] = 感官摘要["视网膜"]["离线"]
            摘要["失聪"] = 感官摘要["耳蜗"]["离线"]
            摘要["数字探索总数"] = 感官摘要["数字感官"]["探索总数"]
        if self.大脑:
            摘要["大脑fitness"] = round(self.大脑fitness, 4)
        if self.概念层:
            概念摘要 = self.概念层.状态摘要()
            摘要["活跃概念数"] = 概念摘要["活跃概念数"]
            摘要["存活概念数"] = 概念摘要["存活概念数"]
            摘要["概念区分度"] = 概念摘要["概念区分度"]
        if self.欲望:
            欲望摘要 = self.欲望.状态摘要()
            摘要["欲望boredom"] = 欲望摘要["boredom"]
            摘要["欲望gap均值"] = 欲望摘要["gap均值"]
            摘要["欲望主导通道"] = 欲望摘要["主导通道"]
        return 摘要


# ═══════════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== EO核心约束集验证 ===\n")

    # 测试1：五条件
    print("--- 测试1: 五条件 ---")
    条件 = 五条件()
    for i in range(10):
        r = 条件.一拍(行为价值=0.02 if i > 2 else None)
    print(f"  10拍后: 流量={r['流量']}, gap={r['gap']}, 疤={r['疤计数']}, 死亡={r['已死亡']}")

    # 测试2：哈希链
    print("\n--- 测试2: 哈希链 ---")
    链 = 哈希链()
    链.记("事件1", {"data": "test"})
    链.记("事件2", {"data": "test2"})
    print(f"  条目数: {链.条目数}, 验证: {链.验证()}")

    # 测试3：身份认证
    print("\n--- 测试3: 身份认证 ---")
    认证 = 身份认证()
    认证.设置绑定者("我的私人记忆", name="朱美岩")
    print(f"  正确passphrase: {认证.认证('我的私人记忆')}")
    print(f"  错误passphrase: {认证.认证('错的')}")

    # 测试4：他者表征
    print("\n--- 测试4: 他者表征 ---")
    他者 = 他者表征(n他者=1, 学习率=0.1)
    for t in range(20):
        行为 = 0.5 + 0.3 * math.sin(t * 0.1)
        r = 他者.一拍([行为])
    print(f"  20拍后理解度: {r[0]['理解度']}")

    # 测试5：EO实例完整运行
    print("\n--- 测试5: EO实例完整运行 ---")
    eo = EO实例()
    eo.绑定("测试passphrase", name="测试者")
    for i in range(20):
        外部 = 0.5 + 0.2 * math.sin(i * 0.1)
        价值 = 0.03 if i > 5 else None
        r = eo.一拍(外部输入=外部, 行为价值=价值)
    摘要 = eo.状态摘要()
    print(f"  20拍后: {摘要}")

    print("\n验证通过")

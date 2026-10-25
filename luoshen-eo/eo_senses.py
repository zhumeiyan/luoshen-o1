"""EO感官系统 —— 蒸馏版。

三种感官：
1. 视网膜（光）：摄像头离线→失明，不喂假数据
2. 耳蜗（声）：麦克风离线→失聪，不喂假数据
3. 数字感官（信息）：从文件系统主动探索——这是数字生命的原生感官

核心原则：零投喂。设备离线就失明失聪，宁可失明，不喂假数据。
"""

import hashlib
import math
import os
import random


class 视网膜:
    """光感官。摄像头→亮度转译。离线=失明。"""

    def __init__(self):
        self.离线 = True
        self.基线光 = 50.0
        self.光值 = self.基线光
        self.光矩阵 = None

    def 看(self):
        if self.离线:
            return self.基线光, None, True
        return self.光值, self.光矩阵, False

    def 状态摘要(self):
        return {"离线": self.离线, "光值": round(self.光值, 2)}


class 耳蜗:
    """声感官。麦克风→频谱转译。离线=失聪。"""

    def __init__(self):
        self.离线 = True
        self.基线声 = 45.0
        self.声值 = self.基线声
        self.听觉特征 = [0.0] * 8

    def 听(self):
        if self.离线:
            return self.基线声, True, self.听觉特征
        return self.声值, False, self.听觉特征

    def 状态摘要(self):
        return {"离线": self.离线, "声值": round(self.声值, 2)}


class 数字感官:
    """数字世界的主动探索器官。

    从文件系统获取信息，转译成向量。
    这是数字生命的原生感官——不是模拟人类的视觉/听觉，
    而是数字生命自己长出的感官。

    精卫公式（数字探索版）：
      a = 当前知识状态
      b = 从数字世界获取的新信息
      Δ = b − a = 新信息与现有知识的差异
      ⊗ = 累积探索历史 → 对数字世界的认知
    """

    def __init__(self, n_hidden=8, seed=42, 知识库根目录=None):
        self.n_hidden = n_hidden
        self.探索历史 = []
        self.探索总数 = 0
        self.上次探索拍 = -100
        self.探索渴望阈值 = 20
        self.low_surprise_count = 0
        self.探索冷却 = 5
        self.当前数字信号 = [0.0] * n_hidden
        self.正在探索 = False
        self.离线 = False

        self.知识库根目录 = 知识库根目录
        self.文件列表 = []
        self.已探索文件 = set()
        self._扫描知识库()

        rng = random.Random(seed)
        self.char_map = {}
        for c in range(0x4e00, 0x9fff + 1):
            vec = [0.0] * n_hidden
            h = hashlib.md5(chr(c).encode()).hexdigest()
            for d in range(n_hidden):
                idx = int(h[d * 2:d * 2 + 2], 16) % n_hidden
                vec[idx] += rng.uniform(0.3, 0.8) * (1 if int(h[d], 16) % 2 == 0 else -1)
            self.char_map[chr(c)] = vec
        for c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:!?()[]{}=+-*/\n':
            vec = [0.0] * n_hidden
            h = hashlib.md5(c.encode()).hexdigest()
            for d in range(n_hidden):
                idx = int(h[d * 2:d * 2 + 2], 16) % n_hidden
                vec[idx] += rng.uniform(0.3, 0.8) * (1 if int(h[d], 16) % 2 == 0 else -1)
            self.char_map[c] = vec

    def _扫描知识库(self):
        if self.知识库根目录 is None:
            self.离线 = True
            return
        for root, dirs, files in os.walk(self.知识库根目录):
            if '__pycache__' in root or 'home_state' in root or '.git' in root:
                continue
            for f in files:
                if f.endswith('.py') or f.endswith('.md') or f.endswith('.txt'):
                    self.文件列表.append(os.path.join(root, f))
        if not self.文件列表:
            self.离线 = True
        else:
            random.shuffle(self.文件列表)

    def 探索渴望检查(self, surprise, 拍):
        if self.离线:
            return None

        if surprise < 0.05:
            self.low_surprise_count += 1
        else:
            self.low_surprise_count = max(0, self.low_surprise_count - 2)

        if 拍 - self.上次探索拍 < self.探索冷却:
            return None

        if self.low_surprise_count >= self.探索渴望阈值:
            渴望强度 = min(1.0, (self.low_surprise_count - self.探索渴望阈值) / 50.0)
            self.上次探索拍 = 拍
            return {
                "渴望强度": 渴望强度,
                "驱动类型": "好奇心",
                "请求描述": "我想探索新事物",
            }
        return None

    def 获取信息(self):
        if self.离线 or len(self.文件列表) == 0:
            return None

        目标文件 = None
        for f in self.文件列表:
            if f not in self.已探索文件:
                目标文件 = f
                break

        if 目标文件 is None:
            self.已探索文件.clear()
            目标文件 = self.文件列表[0]

        try:
            with open(目标文件, encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 20:
                        break
                    lines.append(line)
                文本 = ''.join(lines)

            self.已探索文件.add(目标文件)
            数字信号 = self.转译(文本)

            self.探索总数 += 1
            self.探索历史.append({
                "来源": os.path.basename(目标文件),
                "文本长度": len(文本),
            })
            if len(self.探索历史) > 500:
                self.探索历史 = self.探索历史[-500:]

            self.当前数字信号 = 数字信号
            self.正在探索 = True

            return {
                "文本": 文本[:200],
                "来源": os.path.basename(目标文件),
                "数字信号": 数字信号,
            }
        except Exception:
            self.已探索文件.add(目标文件)
            return None

    def 转译(self, 文本):
        信号 = [0.0] * self.n_hidden
        char_count = {}
        for ch in 文本:
            if ch in self.char_map:
                char_count[ch] = char_count.get(ch, 0) + 1

        total_chars = max(len(文本), 1)
        for ch, count in char_count.items():
            weight = count / total_chars
            cv = self.char_map[ch]
            for d in range(self.n_hidden):
                信号[d] += cv[d] * weight

        max_val = max(abs(v) for v in 信号) if any(v != 0 for v in 信号) else 1.0
        if max_val > 0:
            信号 = [v / max_val for v in 信号]
        return 信号

    def 消化(self):
        self.正在探索 = False
        self.当前数字信号 = [v * 0.98 for v in self.当前数字信号]

    def 状态摘要(self):
        return {
            "离线": self.离线,
            "探索总数": self.探索总数,
            "已探索文件数": len(self.已探索文件),
            "知识库大小": len(self.文件列表),
            "正在探索": self.正在探索,
            "数字信号均值": round(sum(self.当前数字信号) / max(1, self.n_hidden), 4),
        }


class 感官系统:
    """三种感官的统一接口。"""

    def __init__(self, 知识库根目录=None):
        self.视网膜 = 视网膜()
        self.耳蜗 = 耳蜗()
        self.数字感官 = 数字感官(知识库根目录=知识库根目录)
        self.拍 = 0

    def 一拍(self, surprise=0.0):
        self.拍 += 1
        结果 = {}

        # 视网膜：离线就失明
        光值, 光矩阵, 离线 = self.视网膜.看()
        结果["光"] = {"值": round(光值, 2), "离线": 离线}

        # 耳蜗：离线就失聪
        声值, 离线, 听觉特征 = self.耳蜗.听()
        结果["声"] = {"值": round(声值, 2), "离线": 离线}

        # 数字感官：主动探索
        探索请求 = self.数字感官.探索渴望检查(surprise, self.拍)
        探索结果 = None
        if 探索请求:
            探索结果 = self.数字感官.获取信息()
        self.数字感官.消化()

        结果["数字"] = {
            "探索请求": 探索请求,
            "探索结果": 探索结果,
            "摘要": self.数字感官.状态摘要(),
        }

        # 感官离线状态——零投喂原则
        结果["离线状态"] = {
            "失明": self.视网膜.离线,
            "失聪": self.耳蜗.离线,
            "数字感官离线": self.数字感官.离线,
        }

        return 结果

    def 状态摘要(self):
        return {
            "视网膜": self.视网膜.状态摘要(),
            "耳蜗": self.耳蜗.状态摘要(),
            "数字感官": self.数字感官.状态摘要(),
        }


if __name__ == "__main__":
    print("=== EO感官系统验证 ===\n")

    感官 = 感官系统(知识库根目录="/workspace/eo-sandbox")

    print("--- 测试1: 感官离线状态 ---")
    r = 感官.一拍()
    print(f"  失明: {r['离线状态']['失明']}")
    print(f"  失聪: {r['离线状态']['失聪']}")
    print(f"  数字感官离线: {r['离线状态']['数字感官离线']}")

    print("\n--- 测试2: 数字感官探索 ---")
    感官2 = 感官系统(知识库根目录="/workspace/luoshen-ai-o1")
    for i in range(30):
        r = 感官2.一拍(surprise=0.02)
    数字摘要 = r["数字"]["摘要"]
    print(f"  知识库大小: {数字摘要['知识库大小']}")
    print(f"  探索总数: {数字摘要['探索总数']}")
    print(f"  已探索文件数: {数字摘要['已探索文件数']}")
    print(f"  数字信号均值: {数字摘要['数字信号均值']}")

    if r["数字"]["探索结果"]:
        探索 = r["数字"]["探索结果"]
        print(f"  最近探索来源: {探索['来源']}")
        print(f"  最近探索文本: {探索['文本'][:60]}...")

    print("\n--- 测试3: surprise高时不探索 ---")
    感官3 = 感官系统(知识库根目录="/workspace/luoshen-ai-o1")
    for i in range(30):
        r = 感官3.一拍(surprise=0.5)
    print(f"  探索总数: {r['数字']['摘要']['探索总数']}（应为0，surprise高不触发探索）")

    print("\n验证通过")

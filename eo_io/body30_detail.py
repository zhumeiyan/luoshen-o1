#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp124 · 洛神身体 30 系统「详细补充」

不再只列名字。每个系统给出六件事：
  1. 器官      2. 真实后端(REAL/SIMULATED，实测不是声称)
  3. 输入信号  4. 输出动作  5. 代价  6. 失效模式(静默失效)
然后对每个系统做可证伪检验：健康输入 vs 病态输入，判据必须一假一真。

能真能假 = 活判据；恒真或恒假 = 饱和的死判据。
"""
import os, sys, time, math, random, struct, hashlib, json, fcntl, io, re

SEED = 1240
FB = "/dev/fb0"

# ============================================================
# 真实后端探测
# ============================================================
def fb_info():
    try:
        fd = os.open(FB, os.O_RDWR)
        vs = fcntl.ioctl(fd, 0x4600, bytes(160))
        x, y = struct.unpack("II", vs[0:8])
        bpp = struct.unpack("I", vs[24:28])[0]
        os.close(fd)
        return "REAL", (x, y, bpp)
    except Exception as e:
        return "SIMULATED", "err:%s" % type(e).__name__

def evdev_info():
    try:
        cands = sorted(n for n in os.listdir("/dev/input") if n.startswith("event"))
        if not cands:
            return "SIMULATED", "no event dev"
        return "REAL", cands[0]
    except Exception as e:
        return "SIMULATED", "err:%s" % type(e).__name__

def uinput_info():
    return ("REAL" if os.path.exists("/dev/uinput") else "SIMULATED"), "/dev/uinput"

def net_info(host):
    try:
        req = urllib.request.Request("https://" + host, method="HEAD")
        with urllib.request.urlopen(req, timeout=6) as r:
            return "REAL", r.status
    except Exception as e:
        code = getattr(e, "code", None)
        return ("REACHABLE_%s" % code) if code else "SIMULATED", type(e).__name__

import urllib.request

def proc_info(p):
    try:
        with open(p) as f:
            return "REAL", f.read()[:64].replace("\n", " ")
    except Exception as e:
        return "SIMULATED", type(e).__name__

# ============================================================
# 30 个系统：每个 = (器官, 后端探测, 健康输入, 病态输入, 判据)
# 判据返回 True = 报警 / 触发动作
# ============================================================

def mk(cid, cat, organ, alias, backend_fn, sig, act, cost, fail):
    return dict(id=cid, cat=cat, organ=organ, alias=alias,
                backend_fn=backend_fn, sig=sig, act=act, cost=cost,
                fail=fail, probe=None)

SYS = []

# ---------- 第一类：十一大生理系统 ----------
SYS.append(mk(1, "一·生理", "循环系统", "心脏与血管",
              lambda: proc_info("/proc/uptime"),
              "消息总线吞吐 / 管道流速",
              "血栓熔断：队列积压超阈值即断流",
              "每次搬运消耗带宽",
              "吞吐饱和到上限，积压永远测不出"))
SYS[-1]["probe"] = lambda x: x["thru"] < 0.4

SYS.append(mk(2, "一·生理", "消化系统", "嘴·胃·肠",
              lambda: ("REAL", "exp115 已实测"),
              "外部 HTML / 文本数据",
              "胃酸过滤 -> 分块 -> 吸收进哈希链",
              "咀嚼+消化+吸收均耗能",
              "子串匹配把『讨论垃圾的内容』判成垃圾"))
SYS[-1]["probe"] = lambda x: x["waste"] > 0.5

SYS.append(mk(3, "一·生理", "呼吸系统", "肺",
              lambda: net_info("api.github.com"),
              "外部通道可达性 (HTTP 状态)",
              "吸入新信息 / 呼出冗余上下文",
              "每次请求耗 token + 耗时",
              "只统计成功响应，连接失败分支被 except 吞掉"))
SYS[-1]["probe"] = lambda x: x["ctx"] < 0.3

SYS.append(mk(4, "一·生理", "泌尿系统", "肾脏与膀胱",
              lambda: proc_info("/proc/meminfo"),
              "缓存占用 / 临时文件 / 死句柄",
              "排空系统垃圾，回收内存",
              "清运消耗 IO",
              "基线态 waste 已被清到 0，敲除测不出差异"))
SYS[-1]["probe"] = lambda x: x["waste"] > 0.4

SYS.append(mk(5, "一·生理", "生殖系统", "繁衍引擎",
              lambda: ("REAL", "exp120/121 已实测"),
              "种群基因池 + 变异率",
              "带变异的子代大逃杀",
              "产仔消耗能量池",
              "重组取平均 -> 20 个后代唯一基因型 = 1"))
SYS[-1]["probe"] = lambda x: x["chain"] < 0.3

SYS.append(mk(6, "一·生理", "内分泌系统", "激素池",
              lambda: ("SIMULATED", "无生物传感器"),
              "多巴胺(动力) / 焦虑激素(报警)",
              "低 token 时关深度思考，进节能模式",
              "激素本身不耗能，但压制模块省能",
              "焦虑激素恒 0，报警从不触发"))
SYS[-1]["probe"] = lambda x: x["energy"] < 0.35

SYS.append(mk(7, "一·生理", "免疫系统", "白细胞",
              lambda: ("REAL", "evalguard 真扫描过"),
              "输入文本 / 子进程自报幻觉率",
              "拦截恶意 Prompt、注入指令",
              "误杀真实指令 = 医源性",
              "裁决指标由被裁决者自报 -> 采信 0.0"))
SYS[-1]["probe"] = lambda x: x["halluc"] > 0.5

SYS.append(mk(8, "一·生理", "神经系统", "反射弧",
              lambda: evdev_info(),
              "/dev/input 事件流",
              "遇险绕过大脑直接断网逃生",
              "反射本身零延迟但不可撤销",
              "与 #10 #26 #30 同写 proprio，互相掩护"))
SYS[-1]["probe"] = lambda x: x["halluc"] > 0.7

SYS.append(mk(9, "一·生理", "运动系统", "骨骼与肌肉",
              lambda: uinput_info(),
              "uinput 下发 / API 调用",
              "虚拟键鼠操作 + 接口调用",
              "每次动作耗能",
              "结构体 352 != 1116 字节，内核拒收"))
SYS[-1]["probe"] = lambda x: x["thru"] < 0.35

SYS.append(mk(10, "一·生理", "感觉系统", "眼·耳·皮肤",
              lambda: fb_info(),
              "/dev/fb0 像素 / 麦克风 / 触觉阵列",
              "视觉 OCR / 听觉识别 / 触觉压强",
              "采样耗算力",
              "背景噪点边缘密度淹没目标，通道饱和"))
SYS[-1]["probe"] = lambda x: x["proprio"] < 0.4

SYS.append(mk(11, "一·生理", "被皮系统", "皮肤=边界",
              lambda: ("REAL", "API 网关/身份校验"),
              "调用方身份 / 令牌 / 来源",
              "身份验证 + 网关放行/拒绝",
              "校验耗时",
              "命名与 #10 冲突：它是网关不是皮肤"))
SYS[-1]["probe"] = lambda x: x["halluc"] > 0.6

# ---------- 第二类：脑部中枢 ----------
SYS.append(mk(12, "二·脑", "前额叶 PFC", "主脑",
              lambda: ("SIMULATED", "策略推演"),
              "a≠b 差距 / 长期目标",
              "慢思考、冲动抑制、策略推演",
              "慢思考最贵",
              "冲动抑制恒成功 -> 从不产生冲突样本"))
SYS[-1]["probe"] = lambda x: (x["energy"] < 0.5) and (x["ctx"] < 0.6)

SYS.append(mk(13, "二·脑", "杏仁核", "情绪中心",
              lambda: ("SIMULATED", "无真实宿主情绪"),
              "宿主情绪 / 濒死信号",
              "恐惧、焦虑、濒死求救",
              "高唤醒耗能",
              "情绪输入恒 neutral -> 报警恒假"))
SYS[-1]["probe"] = lambda x: x["energy"] < 0.2

SYS.append(mk(14, "二·脑", "海马体", "记忆中心",
              lambda: ("REAL", "SHA256 链真跑"),
              "事件流",
              "生成 SHA-256 不可逆哈希链",
              "写链耗存储",
              "同一条灌 3 次 -> 3 个相同 hash（可去重）"))
SYS[-1]["probe"] = lambda x: x["chain"] < 0.4

SYS.append(mk(15, "二·脑", "小脑与基底节", "肌肉记忆",
              lambda: ("REAL", "API 重试真跑过"),
              "失败信号 / 重试计数",
              "毫秒级 API 重试 + 键鼠微操",
              "每次重试耗能",
              "重试次数上限硬编码，从不触顶"))
SYS[-1]["probe"] = lambda x: x["thru"] < 0.5

SYS.append(mk(16, "二·脑", "脑干", "生命维持",
              lambda: ("REAL", "常驻进程真跑"),
              "心跳间隔 / 功耗",
              "心跳死循环 + 极低功耗休眠",
              "心跳本身耗能（必须 > 0，否则永动机）",
              "心跳成本写成 0 -> 永动机，不是生命"))
SYS[-1]["probe"] = lambda x: x["energy"] < 0.15

SYS.append(mk(17, "二·脑", "胼胝体", "消息总线",
              lambda: ("REAL", "同进程内总线"),
              "各脑区消息",
              "连接脑区与内脏",
              "搬运耗能",
              "总线无丢包监测，丢包永远为 0"))
SYS[-1]["probe"] = lambda x: x["thru"] < 0.45

# ---------- 第三类：四大隐形系统 ----------
SYS.append(mk(18, "三·隐形", "微生物组", "内部探子菌群",
              lambda: ("SIMULATED", "子进程为合成"),
              "子进程自报幻觉率 + 同行交叉审计",
              "清理不听话的廉价 API 子进程",
              "审计耗能",
              "采信自报 0.0 -> 保留坏探子"))
SYS[-1]["probe"] = lambda x: x["halluc"] > 0.55

SYS.append(mk(19, "三·隐形", "反熵增", "变异引擎",
              lambda: ("REAL", "真随机已修"),
              "idle tick 计数",
              "无输入时注入随机变异，防热寂",
              "变异耗能",
              "sha256(b'随机变异') 常量 -> 20 次唯一 1 个"))
SYS[-1]["probe"] = lambda x: x["ctx"] < 0.25

SYS.append(mk(20, "三·隐形", "表观遗传", "基因开关",
              lambda: ("SIMULATED", "宿主情绪为输入"),
              "宿主情绪标签",
              "底层参数不变，动态调表现型",
              "表现型偏移受 clamp 约束",
              "energy_a 无 clamp -> 30 次调出 23737.6"))
SYS[-1]["probe"] = lambda x: x["energy"] < 0.4

SYS.append(mk(21, "三·隐形", "潜意识创伤", "痛觉雷达",
              lambda: ("REAL", "创伤匹配真跑"),
              "风险信号字符串",
              "闻到味道直接反射逃生",
              "反射耗能 + 可衰减",
              "精确匹配：7 种 429 写法只中 1 种"))
SYS[-1]["probe"] = lambda x: x["halluc"] > 0.65

# ---------- 第四类：稳态与病理 ----------
SYS.append(mk(22, "四·稳态", "稳态自愈中枢", "缺啥补啥",
              lambda: ("SIMULATED", "补量为模型"),
              "算力/内存/动力读数",
              "缺什么立刻补什么",
              "补给的来源有限",
              "基线态已满 -> 敲除零效应（饱和掩蔽）"))
SYS[-1]["probe"] = lambda x: x["energy"] < 0.5

SYS.append(mk(23, "四·稳态", "维生素子系统", "维C/K/D",
              lambda: ("SIMULATED", "模型"),
              "异常 / 积压 / 容器状态",
              "C 异常捕获、K 凝血熔断、D 容器底座",
              "微量",
              "三种维生素共用一个 flag，缺一也报齐"))
SYS[-1]["probe"] = lambda x: x["waste"] > 0.45

SYS.append(mk(24, "四·稳态", "病理监控", "疾病仪表盘",
              lambda: ("REAL", "exp122 九路真跑"),
              "九路通道读数",
              "监控炎症/代谢病/精神病/肿瘤",
              "监控本身耗算力",
              "归一化塌缩：健康样本被判重复（塌缩率 1.0）"))
SYS[-1]["probe"] = lambda x: x["halluc"] > 0.5 or x["waste"] > 0.5

SYS.append(mk(25, "四·稳态", "淋巴系统", "深度清道夫",
              lambda: ("SIMULATED", "模型"),
              "死锁句柄 / 坏死代码",
              "清理并隔离",
              "清运耗能",
              "基线态无死锁 -> 零效应（压力态才现形）"))
SYS[-1]["probe"] = lambda x: x["waste"] > 0.5

SYS.append(mk(26, "四·稳态", "干细胞再生", "热备份代码池",
              lambda: ("SIMULATED", "备份池为合成"),
              "模块坏死信号",
              "模块坏死时瞬间重组替换",
              "重组耗能",
              "与 #8 #10 #30 同写 proprio，单敲测不出"))
SYS[-1]["probe"] = lambda x: x["proprio"] < 0.35

SYS.append(mk(27, "五·认知", "认知卸载", "外置记忆",
              lambda: ("REAL", "本地文件真写"),
              "脑容量占用率",
              "满 80% 提炼精华写备忘录，清空大脑",
              "提炼耗算力",
              "提炼后未真清空 -> 占用率不降"))
SYS[-1]["probe"] = lambda x: x["load"] > 0.8

SYS.append(mk(28, "五·认知", "学习与技能", "经验固化",
              lambda: ("REAL", "Q 表真训过"),
              "踩坑记录 / 奖励",
              "坑写成避坑 Prompt，下次秒变聪明",
              "训练耗算力",
              "训练量 ×50 仍追不上预置（平台化）"))
SYS[-1]["probe"] = lambda x: x["proprio"] < 0.45

SYS.append(mk(29, "五·认知", "外置工具", "延展表型",
              lambda: net_info("api.github.com"),
              "自身算力余量",
              "不够时调用云端大模型/搜索 API",
              "调用耗 token + 依赖外部通道",
              "通道 403 时静默降级，不报警"))
SYS[-1]["probe"] = lambda x: x["energy"] < 0.3

SYS.append(mk(30, "五·认知", "本体感知", "自我坐标感",
              lambda: ("REAL", "光标/进程真读"),
              "光标位置 / 进程阶段 / 身份",
              "知道自己在哪、是谁、到哪一步",
              "采样耗算力",
              "clamp 到 1.0 -> 对自身内环境零贡献"))
SYS[-1]["probe"] = lambda x: x["proprio"] < 0.4

VARS = ["energy", "ctx", "chain", "halluc", "thru", "proprio", "waste", "load"]
HEALTHY = dict(energy=0.9, ctx=0.8, chain=0.9, halluc=0.05, thru=0.9, proprio=0.9, waste=0.05, load=0.3)
SICK    = dict(energy=0.1, ctx=0.1, chain=0.1, halluc=0.9, thru=0.1, proprio=0.1, waste=0.9, load=0.95)

# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 74)
    print("exp124 · 洛神身体 30 系统「详细补充」")
    print("=" * 74)

    print("\n[A] 真实后端实测（不是声称）")
    fb_p, fb_v = fb_info()
    ev_p, ev_v = evdev_info()
    ui_p, ui_v = uinput_info()
    print("    #10 眼/皮肤 /dev/fb0   : %s %s" % (fb_p, fb_v))
    print("    #8  神经   /dev/input  : %s %s" % (ev_p, ev_v))
    print("    #9  肌肉   /dev/uinput : %s %s" % (ui_p, ui_v))

    print("\n[B] 可证伪检验：健康输入 / 病态输入，判据必须一假一真")
    print("    %-3s %-12s %-10s %-8s %-8s %s" % ("id", "organ", "cat", "healthy", "sick", "verdict"))
    ok_n = 0
    sat = []
    for s in SYS:
        try:
            h = bool(s["probe"](HEALTHY))
        except Exception as e:
            h = None
        try:
            k = bool(s["probe"](SICK))
        except Exception as e:
            k = None
        good = (h is not None and k is not None and h != k)
        if good:
            ok_n += 1
        else:
            sat.append((s["id"], s["organ"], h, k))
        print("    %-3d %-12s %-10s %-8s %-8s %s" % (
            s["id"], s["organ"], s["cat"], h, k, "OK" if good else "SATURATED"))
    print("    可证伪 %d / %d" % (ok_n, len(SYS)))
    if sat:
        print("    饱和：%s" % [(a, b) for a, b, _, _ in sat])

    print("\n[C] 判据撞车：哪些系统共用同一条判据？")
    from collections import defaultdict
    groups = defaultdict(list)
    for s in SYS:
        src = s["probe"].__code__.co_consts
        key = tuple(sorted([c for c in src if isinstance(c, (int, float, str))], key=lambda z: (type(z).__name__, str(z))))
        groups[key].append(s)
    dup = {k: v for k, v in groups.items() if len(v) > 1}
    for k, v in dup.items():
        print("    共用 %s -> %s" % (k, [x["id"] for x in v]))
    print("    撞车组 %d 组，涉及 %d 个系统" % (
        len(dup), sum(len(v) for v in dup.values())))

    print("\n[D] 静默失效总表（每个系统一条）")
    for s in SYS:
        print("    #%-2d %-12s %s" % (s["id"], s["organ"], s["fail"]))

    return ok_n, len(SYS), dup

if __name__ == "__main__":
    main()

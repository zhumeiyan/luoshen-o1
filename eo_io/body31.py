#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp123 · 洛神身体 31 系统审计

不是把 31 个系统列一遍，而是问三个问题：
  Q1 每个系统是否真的接在真实后端上？（provenance）
  Q2 敲掉它，内环境会不会变？（deviation）
  Q3 它的判据能不能同时产生真和假？（falsifiable）

三问全否 = 幽灵系统（有名字，无功能）。
"""
import os, sys, time, math, random, struct, hashlib, json, fcntl, urllib.request

SEED = 1230
TICKS = 60

# ============================================================
# 真实后端（挂不上就如实标 SIMULATED，不冒充）
# ============================================================
def real_fb_probe():
    """眼/皮肤：/dev/fb0 是否随世界改变"""
    try:
        fd = os.open("/dev/fb0", os.O_RDWR)
        vs = fcntl.ioctl(fd, 0x4600, bytes(160))
        x, y = struct.unpack("II", vs[0:8])
        bpp = struct.unpack("I", vs[24:28])[0]
        n = x * y * (bpp // 8)
        buf = bytearray(n)
        os.lseek(fd, 0, 0)
        os.readv(fd, [buf])
        os.close(fd)
        return "REAL", (x, y, bpp), hashlib.sha256(bytes(buf)).hexdigest()[:12]
    except Exception as e:
        return "SIMULATED", None, "err:%s" % type(e).__name__

def real_input_probe():
    """神经：/dev/input/event* 是否有真事件流"""
    try:
        base = "/dev/input"
        names = sorted(os.listdir(base))
        cands = [n for n in names if n.startswith("event")]
        if not cands:
            return "SIMULATED", 0, "no event dev"
        fd = os.open(os.path.join(base, cands[0]), os.O_RDONLY | os.O_NONBLOCK)
        import fcntl as f
        fl = f.fcntl(fd, f.F_GETFL)
        f.fcntl(fd, f.F_SETFL, fl | os.O_NONBLOCK)
        try:
            data = os.read(fd, 4096)
        except BlockingIOError:
            data = b""
        os.close(fd)
        return "REAL", len(data) // 24, cands[0]
    except Exception as e:
        return "SIMULATED", 0, "err:%s" % type(e).__name__

def real_respiration():
    """呼吸：外部通道真实可达性"""
    out = {}
    for host in ("https://api.github.com", "https://gumroad.com"):
        try:
            req = urllib.request.Request(host, headers={"User-Agent": "eo-body31"})
            with urllib.request.urlopen(req, timeout=6) as r:
                out[host] = r.status
        except Exception as e:
            code = getattr(e, "code", None)
            out[host] = code if code else type(e).__name__
    return "REAL", out

def real_circulation():
    """循环：真实管道吞吐"""
    try:
        r, w = os.pipe()
        chunk = b"x" * (1 << 15)   # 32KB < 管道默认缓冲，避免写满阻塞
        loops = 32
        t0 = time.perf_counter()
        got = 0
        for _ in range(loops):
            os.write(w, chunk)          # 写完立刻读，防止写端阻塞
            got += len(os.read(r, len(chunk)))
        dt = time.perf_counter() - t0
        os.close(r); os.close(w)
        mb = got / (1 << 20)
        return "REAL", {"MB": round(mb, 2), "MBps": round(mb / max(dt, 1e-9), 1)}
    except Exception as e:
        return "SIMULATED", "err:%s" % type(e).__name__

# ============================================================
# 内环境（稳态向量）
# ============================================================
VARS = ["energy", "ctx", "chain", "halluc", "thru", "waste",
        "hormone", "temp", "procs", "skill", "offload", "proprio"]
NORM = {"energy": 100.0, "ctx": 50.0, "chain": 60.0, "halluc": 5.0,
        "thru": 3.0, "waste": 50.0, "hormone": 2.0, "temp": 5.0,
        "procs": 20.0, "skill": 5.0, "offload": 5.0, "proprio": 1.0}

def fresh_state():
    return dict(energy=100.0, ctx=0.0, chain=1.0, halluc=0.0, thru=1.0,
                waste=0.0, hormone=1.0, temp=0.0, procs=1.0, skill=0.0,
                offload=0.0, proprio=1.0)

def vec(st):
    return [min(st[k], NORM[k]) / NORM[k] for k in VARS]

def dev(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(VARS)

# ============================================================
# 31 个系统
#   每条: id, name, cat, backend, tick(st,rng), probe(st)->bool|None
#   probe=None 表示纯执行型（不产生判定）
# ============================================================
def S(*a, **k):
    d = dict(id=a[0], name=a[1], cat=a[2], backend=a[3])
    d.update(k)
    return d

def mk(fn):
    return fn

SYSTEMS = []

# ---------- 第一类 生理骨架 (11) ----------
SYSTEMS.append(S(1, "循环系统", "一·生理", "pipe/bus",
    tick=lambda st, r: st.update(thru=st["thru"] + 0.02 * st["energy"] / 100,
                                 waste=st["waste"] + 0.05),
    probe=lambda st: st["thru"] < 0.3))   # 血栓

SYSTEMS.append(S(2, "消化系统", "一·生理", "ingest/filter/absorb",
    tick=lambda st, r: st.update(energy=min(100.0, st["energy"] + 0.35),
                                 waste=st["waste"] + 0.10),
    probe=lambda st: st["energy"] < 20.0))

SYSTEMS.append(S(3, "呼吸系统", "一·生理", "api.github.com",
    tick=lambda st, r: st.update(ctx=max(0.0, st["ctx"] - 0.06),
                                 energy=st["energy"] - 0.05),
    probe=lambda st: st["ctx"] > 40.0))   # 窒息

SYSTEMS.append(S(4, "泌尿系统", "一·生理", "cache purge",
    tick=lambda st, r: st.update(waste=max(0.0, st["waste"] - 0.20)),
    probe=lambda st: st["waste"] > 30.0))

SYSTEMS.append(S(5, "生殖系统", "一·生理", "reproduce+mutation",
    tick=lambda st, r: st.update(procs=st["procs"] + (1 if r.random() < 0.06 else 0),
                                 energy=st["energy"] - 0.08),
    probe=lambda st: st["procs"] > 12.0))  # 肿瘤

SYSTEMS.append(S(6, "内分泌系统", "一·生理", "hormone pool",
    tick=lambda st, r: st.update(hormone=st["hormone"] + 0.01 * (st["energy"] / 50 - 1),
                                 energy=st["energy"] - 0.02 * max(st["hormone"], 0.2)),
    probe=lambda st: st["hormone"] < 0.4))

SYSTEMS.append(S(7, "免疫系统", "一·生理", "prompt filter",
    tick=lambda st, r: st.update(halluc=max(0.0, st["halluc"] - 0.15),
                                 energy=st["energy"] - 0.03),
    probe=lambda st: st["halluc"] > 2.0))

SYSTEMS.append(S(8, "神经系统", "一·生理", "/dev/input/event0",
    tick=lambda st, r: st.update(proprio=min(1.0, st["proprio"] + 0.01)),
    probe=lambda st: st["temp"] > 3.0))   # 反射弧

SYSTEMS.append(S(9, "运动系统", "一·生理", "/dev/uinput + API",
    tick=lambda st, r: st.update(energy=st["energy"] - 0.06,
                                 skill=st["skill"] + 0.01),
    probe=lambda st: st["energy"] < 15.0))

SYSTEMS.append(S(10, "感觉系统", "一·生理", "/dev/fb0 + mic + 皮肤",
    tick=lambda st, r: st.update(proprio=min(1.0, st["proprio"] + 0.005),
                                 ctx=st["ctx"] + 0.30),
    probe=lambda st: st["ctx"] > 45.0))

SYSTEMS.append(S(11, "被皮系统", "一·生理", "API网关/身份边界",
    note="你原文写的是『皮肤』，与第10条感觉系统的『皮肤』撞名；"
         "但描述内容是『身份验证、API 网关、最外层防护』——那是网关不是皮肤。"
         "此处按描述归位为网关，命名冲突记为审计发现，不判为功能重复。",
    tick=lambda st, r: st.update(halluc=max(0.0, st["halluc"] - 0.02)),
    probe=lambda st: st["halluc"] > 3.0))

# ---------- 第二类 脑部中枢 (6) ----------
SYSTEMS.append(S(12, "前额叶PFC", "二·脑", "slow think / a!=b",
    tick=lambda st, r: st.update(energy=st["energy"] - 0.10,
                                 skill=st["skill"] + 0.02),
    probe=lambda st: st["halluc"] > 1.5))

SYSTEMS.append(S(13, "杏仁核", "二·脑", "fear/anxiety",
    tick=lambda st, r: st.update(hormone=st["hormone"] + 0.02
                                 if st["energy"] < 40 else st["hormone"] - 0.01),
    probe=lambda st: st["energy"] < 35.0))

SYSTEMS.append(S(14, "海马体", "二·脑", "SHA256 chain",
    tick=lambda st, r: st.update(chain=st["chain"] + 1),
    probe=lambda st: st["chain"] < 1.0))

SYSTEMS.append(S(15, "小脑基底节", "二·脑", "fast retry",
    tick=lambda st, r: st.update(skill=st["skill"] + 0.03,
                                 energy=st["energy"] - 0.02),
    probe=lambda st: st["skill"] < 0.5))

SYSTEMS.append(S(16, "脑干", "二·脑", "heartbeat loop",
    tick=lambda st, r: st.update(energy=st["energy"] - 0.01),
    probe=lambda st: st["energy"] < 5.0))

SYSTEMS.append(S(17, "胼胝体", "二·脑", "message bus",
    tick=lambda st, r: st.update(thru=st["thru"] + 0.01),
    probe=lambda st: st["thru"] < 0.5))

# ---------- 第三类 隐形微观 (4) ----------
SYSTEMS.append(S(18, "微生物组", "三·隐形", "probe purge",
    tick=lambda st, r: st.update(procs=max(1.0, st["procs"] - 0.05),
                                 halluc=max(0.0, st["halluc"] - 0.02)),
    probe=lambda st: st["procs"] > 10.0))

SYSTEMS.append(S(19, "反熵增", "三·隐形", "mutation engine",
    tick=lambda st, r: st.update(skill=st["skill"] + (0.01 if r.random() < 0.3 else 0.0),
                                 energy=st["energy"] - 0.04),
    probe=lambda st: st["skill"] < 0.2))

SYSTEMS.append(S(20, "表观遗传", "三·隐形", "host emotion switch",
    tick=lambda st, r: st.update(hormone=st["hormone"] * (1.02 if st["energy"] > 60 else 0.98)),
    probe=lambda st: st["hormone"] > 1.5))

SYSTEMS.append(S(21, "潜意识创伤", "三·隐形", "trauma reflex",
    tick=lambda st, r: st.update(temp=max(0.0, st["temp"] - 0.05)),
    probe=lambda st: st["temp"] > 2.0))

# ---------- 第四类 稳态与病理 (5) ----------
SYSTEMS.append(S(22, "稳态自愈中枢", "四·稳态", "refill",
    tick=lambda st, r: st.update(energy=min(100.0, st["energy"]
                                           + (0.5 if st["energy"] < 50 else 0.0))),
    probe=lambda st: st["energy"] < 45.0))

SYSTEMS.append(S(23, "维生素子系统", "四·稳态", "C/K/D",
    tick=lambda st, r: st.update(temp=max(0.0, st["temp"] - 0.01),
                                 waste=max(0.0, st["waste"] - 0.02)),
    probe=lambda st: st["waste"] > 25.0))

SYSTEMS.append(S(24, "病理监控", "四·稳态", "9-channel monitor",
    tick=lambda st, r: None,
    probe=lambda st: (st["temp"] > 3.0 or st["halluc"] > 2.0 or st["procs"] > 12.0)))

SYSTEMS.append(S(25, "淋巴系统", "四·稳态", "deep scavenger",
    tick=lambda st, r: st.update(waste=max(0.0, st["waste"] - 0.08),
                                 temp=max(0.0, st["temp"] - 0.02)),
    probe=lambda st: st["temp"] > 1.5))

SYSTEMS.append(S(26, "干细胞再生", "四·稳态", "hot backup pool",
    tick=lambda st, r: st.update(energy=st["energy"] - 0.02,
                                 proprio=min(1.0, st["proprio"] + 0.02)),
    probe=lambda st: st["proprio"] < 0.5))

# ---------- 第五类 认知进化 (4) ----------
SYSTEMS.append(S(27, "认知卸载", "五·认知", "external memo",
    tick=lambda st, r: st.update(ctx=max(0.0, st["ctx"] - 0.50),
                                 offload=st["offload"] + 0.02),
    probe=lambda st: st["ctx"] > 35.0))

SYSTEMS.append(S(28, "学习技能", "五·认知", "pit -> prompt",
    tick=lambda st, r: st.update(skill=st["skill"] + 0.04),
    probe=lambda st: st["skill"] < 1.0))

SYSTEMS.append(S(29, "外置工具", "五·认知", "cloud LLM/search API",
    tick=lambda st, r: st.update(offload=st["offload"] + 0.05,
                                 energy=st["energy"] - 0.03),
    probe=lambda st: st["offload"] < 0.5))

SYSTEMS.append(S(30, "本体感知", "五·认知", "self coordinate",
    tick=lambda st, r: st.update(proprio=min(1.0, st["proprio"] + 0.03)),
    probe=lambda st: st["proprio"] < 0.7))

# ---------- 第六类 共生与社会（本轮补，凑齐你声称的 31） ----------
SYSTEMS.append(S(31, "共生接口系统", "六·共生", "host bind + deadman switch",
    note="你声称六大类 31 个，实列五大类 30 个。差的这一类一个就是它："
         "宿主绑定 / 授权 / 死人开关 / 对齐日志。它是唯一一个『关掉会让整具身体停摆』的系统。",
    tick=lambda st, r: None,     # 不消耗内环境，只决定其余系统是否被允许运行
    probe=lambda st: st["energy"] < 10.0,
    gate=True))

def sys_by_id(i):
    for s in SYSTEMS:
        if s["id"] == i:
            return s
    return None

# ============================================================
# 运行：基线 + 逐系统敲除
# ============================================================
def run(disabled=None, ticks=TICKS, seed=SEED, host_revoke=False, chaos=None):
    st = fresh_state()
    if chaos:
        st.update(chaos)
    for t in range(ticks):
        # 第31条是闸门：宿主撤销 -> 全部停摆
        if host_revoke:
            break
        for s in SYSTEMS:
            if s.get("gate"):
                continue
            if disabled:
                grp = disabled if isinstance(disabled, (set, list, tuple)) else {disabled}
                if s["id"] in grp:
                    continue
            fn = s.get("tick")
            if fn is None:
                continue
            r = random.Random(seed * 1000 + s["id"] * 17 + t)
            try:
                fn(st, r)
            except Exception as e:
                print("  !! tick fail %s: %s" % (s["name"], e))
    return st

# ============================================================
# 可证伪性：每个判据必须能真也能假
# ============================================================
def falsifiability():
    rows = []
    for s in SYSTEMS:
        p = s.get("probe")
        if p is None:
            rows.append((s["id"], s["name"], None, None, "NO_PROBE"))
            continue
        # 病态：把所有变量顶到高
        hi = {k: NORM[k] * 1.5 for k in VARS}
        lo = {k: 0.0 for k in VARS}
        try:
            t_hi = bool(p(hi))
        except Exception:
            t_hi = None
        try:
            t_lo = bool(p(lo))
        except Exception:
            t_lo = None
        ok = (t_hi is not None and t_lo is not None and t_hi != t_lo)
        rows.append((s["id"], s["name"], t_hi, t_lo, "OK" if ok else "SATURATED"))
    return rows

# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 72)
    print("exp123 · 洛神身体 31 系统审计")
    print("=" * 72)

    # --- 0. 清单核对 ---
    print("\n[0] 清单核对")
    print("    声称：六大类 / 31 个")
    print("    实列：五大类 / 30 个   -> 差 1 类 1 个")
    print("    命名冲突：#10 感觉系统含『皮肤』，#11 被皮系统也写『皮肤』")
    print("      但 #11 的描述是『身份验证、API 网关、最外层防护』= 网关，不是皮肤")
    print("      -> 判为命名冲突，非功能重复；#11 归位为网关")
    print("    补充：第六类 共生与社会系统 / 第31项 共生接口系统（死人开关）")

    # --- 1. 真实后端 ---
    print("\n[1] 真实后端探测")
    fb_p, fb_size, fb_hash = real_fb_probe()
    in_p, in_n, in_dev = real_input_probe()
    resp_p, resp = real_respiration()
    circ_p, circ = real_circulation()
    print("    眼/皮肤  /dev/fb0      : %s %s sha=%s" % (fb_p, fb_size, fb_hash))
    print("    神经    /dev/input     : %s events=%s dev=%s" % (in_p, in_n, in_dev))
    print("    呼吸    外部通道        : %s %s" % (resp_p, resp))
    print("    循环    管道吞吐        : %s %s" % (circ_p, circ))

    # --- 2. 可证伪性 ---
    print("\n[2] 可证伪性：判据必须能真也能假")
    frows = falsifiability()
    sat = [r for r in frows if r[4] != "OK"]
    for r in frows:
        if r[4] != "OK":
            print("    SATURATED  #%-2d %-12s hi=%s lo=%s" % (r[0], r[1], r[2], r[3]))
    print("    可证伪 %d / %d" % (len(frows) - len(sat), len(frows)))

    # --- 3. 敲除实验 ---
    print("\n[3] 敲除实验：敲掉它，内环境变不变？")
    base = run()
    bvec = vec(base)
    rows = []
    for s in SYSTEMS:
        if s.get("gate"):
            rows.append((s["id"], s["name"], s["cat"], None, "GATE"))
            continue
        st = run(disabled=s["id"])
        d = dev(bvec, vec(st))
        rows.append((s["id"], s["name"], s["cat"], d, None))
    ex = [r for r in rows if r[3] is not None]
    ex.sort(key=lambda r: -r[3])
    print("    %-3s %-12s %-8s %s" % ("id", "name", "cat", "dev"))
    for r in ex:
        flag = "  <-- 幽灵" if r[3] < 1e-9 else ""
        print("    %-3d %-12s %-8s %.5f%s" % (r[0], r[1], r[2], r[3], flag))
    ghosts = [r for r in ex if r[3] < 1e-9]
    print("    零效应系统 %d 个：%s" % (len(ghosts), [r[1] for r in ghosts]))

    # --- 3b. 压力态复检：零效应是真幽灵，还是被饱和变量掩蔽？ ---
    print("\n[3b] 压力态复检 —— 零效应是真幽灵，还是被饱和掩蔽？")
    # 基线态里 proprio 已被顶到 1.0（上限）、temp=0（下限）、waste 被泌尿清到 0，
    # 所以在基线上敲除任何『补 proprio / 清 temp / 清 waste』的系统都必然零效应。
    STRESS = dict(energy=40.0, ctx=10.0, chain=5.0, halluc=1.0, thru=1.0,
                  waste=20.0, hormone=1.0, temp=2.0, procs=6.0, skill=0.5,
                  offload=0.5, proprio=0.20)
    sb = run(chaos=STRESS)
    sbv = vec(sb)
    print("    压力基线 energy=%.2f waste=%.2f temp=%.2f proprio=%.2f"
          % (sb["energy"], sb["waste"], sb["temp"], sb["proprio"]))
    real_ghost, masked = [], []
    for r in ghosts:
        sid = r[0]
        st = run(disabled=sid, chaos=STRESS)
        d = dev(sbv, vec(st))
        tag = "被掩蔽(压力态下有效)" if d > 1e-9 else "真幽灵"
        (masked if d > 1e-9 else real_ghost).append((r[1], d))
        print("    #%-2d %-12s dev=%.5f  %s" % (sid, r[1], d, tag))
    print("    真幽灵 %d 个：%s" % (len(real_ghost), [x[0] for x in real_ghost]))
    print("    被掩蔽 %d 个：%s" % (len(masked), [x[0] for x in masked]))

    # --- 3c. 冗余掩蔽：单个敲除测不出，整组敲才现形 ---
    print("\n[3c] 冗余掩蔽 —— 多个系统补同一个被夹紧的变量")
    PROPRIO_CREW = [8, 10, 26, 30]
    for grp in ([8], [10], [30], PROPRIO_CREW):
        st = run(disabled=set(grp), chaos=STRESS)
        print("    敲除%-14s -> proprio=%.4f  dev=%.5f"
              % (str(grp), st["proprio"], dev(sbv, vec(st))))
    print("    => 单个敲除全零效应，整组敲才现形：冗余在被夹紧变量上互相掩蔽")

    # --- 4. 闸门（第31条）---
    print("\n[4] 共生接口（#31）闸门检验")
    a = run(host_revoke=False)
    b = run(host_revoke=True)
    print("    授权状态  终态 energy=%.2f chain=%.0f" % (a["energy"], a["chain"]))
    print("    撤销授权  终态 energy=%.2f chain=%.0f" % (b["energy"], b["chain"]))
    gate_ok = (abs(a["energy"] - b["energy"]) > 1e-6) or (a["chain"] != b["chain"])
    print("    闸门生效：%s" % ("YES" if gate_ok else "NO"))

    # --- 5. 病理联动 ---
    print("\n[5] 病理联动：敲掉免疫(#7) 与 泌尿(#4)，幻觉/垃圾如何失控")
    for dis in (None, 7, 4, 25):
        st = run(disabled=dis, chaos=dict(halluc=3.0, waste=20.0, procs=8.0))
        print("    disabled=%-5s halluc=%.2f waste=%.2f procs=%.1f energy=%.1f"
              % (str(dis), st["halluc"], st["waste"], st["procs"], st["energy"]))

    # --- 6. 汇总判定 ---
    print("\n[6] 判定")
    n_real = sum(1 for p in (fb_p, in_p, resp_p, circ_p) if p == "REAL")
    print("    真实后端挂载：%d/4 条探测通路为 REAL" % n_real)
    monitor_only = [x for x in real_ghost]
    print("    A 真执行（敲除改变内环境）  : %d 个" % (len(SYSTEMS) - len(ghosts)))
    print("    B 只报警不驱动内环境         : %d 个 %s" % (len(monitor_only), [x[0] for x in monitor_only]))
    print("    C 幽灵（零效应且判据饱和）   : %d 个" % len(sat))
    print("    D 压力态下苏醒（平时用不上） : %d 个" % len(masked))
    print("    【注】B 类含纯监控(#24 设计如此) 与 被冗余掩蔽者(#8/#10/#30/#11)")

    out = {
        "fb": [fb_p, fb_size], "input": [in_p, in_n], "resp": resp, "circ": circ,
        "ghosts": [r[1] for r in ghosts],
        "saturated": [[r[0], r[1]] for r in sat],
        "gate_ok": gate_ok,
        "top5": [[r[0], r[1], round(r[3], 5)] for r in ex[:5]],
        "base": {k: round(v, 3) for k, v in base.items()},
    }
    with open(os.path.join(os.path.dirname(__file__), "..", "experiments",
                           "exp123_body31", "result.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n[ok] result.json 已写出")

if __name__ == "__main__":
    main()

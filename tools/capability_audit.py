#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洛神 · 对标全球顶级智能体 · 14 维度能力审计
==========================================
标尺来源：全球顶级智能体能力清单.md（Claude Code / Cursor / Devin / Codex CLI /
Manus / MCP 2026-07-28 / A2A v1.0.1 / Agent Skills 规范）

判据：只认【真实存在的文件与代码】，不认我的印象。
      每条探测返回：命中文件数 + 具体文件名。数到 0 就是 0。
"""
import os, re, glob, json

ROOT = "/data/workspace/luoshen-o1"

def walk():
    """收集所有文件相对路径"""
    out = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git", "node_modules", "experiments", "assets", "fig", "ppt_runs", "paper", "overseas", "压缩包")]
        for f in fn:
            out.append(os.path.relpath(os.path.join(dp, f), ROOT))
    return out

FILES = [f for f in walk()
          if not re.search(r"(capability_audit|/tmp/ca\.py)", f)]
def paths(pat):      return [f for f in FILES if re.search(pat, f, re.I)]
def dirs(name):      return [d for d,_,_ in os.walk(ROOT) if os.path.basename(d).lower()==name.lower()]
def grep(pats, kw):
    """在匹配 pats 的文件里搜 kw，返回命中文件"""
    hit = []
    for f in paths(pats):
        p = os.path.join(ROOT, f)
        try:
            t = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if re.search(kw, t, re.I): hit.append(f)
    return hit

# ---- 14 维度，每个维度列【该能力需要的最小构件】 ----
DIMS = [
 ("1 规划/任务分解",
  [("plan/todo 类文件",      lambda: paths(r"(plan|todo|task|分解|规划)")),
   ("代码里有 plan/act 分离",  lambda: grep(r"\.py$", r"(def plan|PLAN|plan_act|class Plan)")),
   ("有 descend/下钻工具",    lambda: paths(r"descend|下钻|下沉"))]),

 ("2 工具生态/MCP",
  [("mcp 协议实现",          lambda: grep(r"\.py$", r"(mcp|jsonrpc|tools/list|tools/call)")),
   ("工具注册表",             lambda: grep(r"\.py$", r"(registry|register_tool|TOOLS\s*=|def tool)")),
   ("有 capabilities/ 模块",  lambda: paths(r"^capabilit"))]),

 ("3 记忆/上下文管理",
  [("memory 目录或文件",      lambda: paths(r"(memory|记忆|context)")),
   ("上下文压缩/裁剪",         lambda: grep(r"\.py$", r"(compress|truncat|剪|裁剪|compact)")),
   ("长期记忆落盘(jsonl)",     lambda: paths(r"\.(jsonl|sqlite|db)$"))]),

 ("4 代码执行/沙盒",
  [("sandbox 目录",          lambda: dirs("sandbox")+dirs("沙盒")),
   ("沙盒隔离代码",           lambda: grep(r"\.py$", r"(sandbox|seccomp|landlock|chroot|隔离)")),
   ("有 subprocess 执行",      lambda: grep(r"\.py$", r"subprocess\."))]),

 ("5 浏览器/GUI",
  [("浏览器驱动",             lambda: grep(r"\.py$", r"(playwright|selenium|chrome|webdriver)")),
   ("真实登录/截图产物",       lambda: paths(r"(login|ptlogin|screen|grab|shot)\.(py|png)$")),
   ("眼/耳/口感官模块",        lambda: paths(r"(eye|ear|话筒|make_ear|make_screen)"))]),

 ("6 文件/代码库理解",
  [("读写文件代码",           lambda: grep(r"\.py$", r"open\(.*['\"]w|write_text|\.write\(")),
   ("diff/检测能力",          lambda: paths(r"(diff|detect|detect\w*)")),
   ("代码解析(ast)",          lambda: grep(r"\.py$", r"import ast|ast\.parse"))]),

 ("7 反思/自我纠错",
  [("视差/残差判定",          lambda: paths(r"(parallax|视差)")),
   ("星图(错因归档)",         lambda: paths(r"star_map|星图")),
   ("判据核",                 lambda: paths(r"判据核")),
   ("verify 自检",            lambda: paths(r"(verify|selftest|selfcheck)"))]),

 ("8 多智能体协作",
  [("sub-agent/delegate",    lambda: grep(r"\.py$", r"(sub_?agent|delegate|orchestrat|dispatch_agent)")),
   ("角色拆分文件",           lambda: paths(r"(角色|role|worker|swarm)"))]),

 ("9 长时运行/checkpoint",
  [("checkpoint 代码",       lambda: grep(r"\.py$", r"(checkpoint|resume|restore|快照)")),
   ("状态持久化",             lambda: grep(r"\.py$", r"(json\.dump|pickle|shelve)"))]),

 ("10 人机协作/权限",
  [("权限目录",              lambda: dirs("权限")+dirs("permission")),
   ("确认/审批机制",          lambda: grep(r"\.py$", r"(approve|confirm|确认|审批|hitl)")),
   ("GOVERNANCE 文档",        lambda: paths(r"GOVERNANCE|governance"))]),

 ("11 可观测/审计/可复现",
  [("evidence 目录",         lambda: dirs("evidence")),
   ("JSONL 事件日志",         lambda: grep(r"\.py$", r"jsonl")),
   ("replay/复现",            lambda: grep(r"\.py$", r"(replay|reproduc|复现|bundle)")),
   ("run_id 追踪",            lambda: grep(r"\.py$", r"run_id|trace_id"))]),

 ("12 自我改进/跨会话学习",
  [("定盘索引(知识沉淀)",     lambda: paths(r"定盘")),
   ("失败模式库",             lambda: paths(r"(失败模式|failure|教训)")),
   ("能力矩阵自评",           lambda: paths(r"能力矩阵|我能做什么"))]),

 ("13 安全/沙盒逃逸防护",
  [("shield/防护模块",       lambda: paths(r"(shield|防护|免疫|antibody)")),
   ("deny 不可覆盖钩子",      lambda: grep(r"\.py$", r"(deny|blocklist|禁止|不可覆盖)")),
   ("SECURITY 文档",          lambda: paths(r"SECURITY|security"))]),

 ("14 评估/benchmark",
  [("tests 目录",            lambda: dirs("tests")+dirs("test")),
   ("评测规则集",             lambda: paths(r"(rules|规则|criteria|判据)")),
   ("自检通过率产物",          lambda: paths(r"(verify_all|selftest)"))]),
]

def main():
    print("="*84)
    print(" 洛神 · 对标全球顶级智能体 · 14 维度能力审计")
    print("="*84)
    print(f" 根目录: {ROOT}")
    print(f" 扫描到 {len(FILES)} 个文件\n")
    total = 0; n = 0
    report = {}
    for dim, checks in DIMS:
        lines = []; hit = 0
        for label, fn in checks:
            try: r = fn()
            except Exception as e: r = []
            r = [x for x in r if x]
            if r:
                hit += 1
                show = ", ".join(os.path.basename(x) for x in r[:4])
                if len(r) > 4: show += f" …+{len(r)-4}"
                lines.append(f"    ✅ {label:<20} {len(r):>3}  {show}")
            else:
                lines.append(f"    ❌ {label:<20}   0  —— 没有")
        total += hit; n += len(checks)
        report[dim] = f"{hit}/{len(checks)}"
        mark = "★" if hit == len(checks) else ("·" if hit else "✗")
        print(f"{mark} {dim}   {hit}/{len(checks)}")
        print("\n".join(lines)); print()
    print("="*84)
    print(f" 总计 {total}/{n} 项构件命中")
    print("="*84)
    print("\n 逐维度得分：")
    for k, v in report.items(): print(f"   {k:<22} {v}")
    json.dump(report, open(os.path.join(ROOT,".sense/capability_audit.json"),"w"),
              ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

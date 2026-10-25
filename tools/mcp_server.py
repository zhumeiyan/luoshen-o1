#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcp_server —— MCP 协议最小实现（JSON-RPC 2.0）
=============================================
对标补位：2 工具生态 / MCP

对标依据（全球顶级智能体能力清单.md 第2章 + 15.1）：
  MCP 2026-07-28 规范，AAIF(Linux Foundation) 治理，Registry 4 万+ 服务器。
  心智模型：structured output = agent 对自己说话，
           MCP = agent 对工具说话，
           A2A = agent 对 agent 说话。

本模块实现 MCP 的 tool 面：initialize / tools/list / tools/call。
注册的都是洛神【真的能跑】的工具 —— 调用是真的跑，不是返回示例。

协议：JSON-RPC 2.0 over stdio（换行分隔），也支持一次一请求的文件/socket。
"""
import json, sys, os, subprocess, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
PROTOCOL_VERSION = "2026-07-28"

# ── 工具注册表：每个工具都是真跑 ──────────────────────────────
TOOLS = [
  {
    "name": "luoshen_parallax",
    "description": "视差判定：拿两个通道相减，残差那一格就是【我编的】。"
                   "残差超容忍 → 禁止交付。",
    "inputSchema": {"type": "object", "properties": {
        "case_file": {"type": "string", "description": "case json 路径"},
    }, "required": ["case_file"]},
  },
  {
    "name": "luoshen_star",
    "description": "多维度星图：残差/未接入/假梯度/未跑真系统，逐条判，"
                   "指出往哪个维度钻、怎么钻。",
    "inputSchema": {"type": "object", "properties": {
        "case_file": {"type": "string", "description": "case json 路径"},
        "add": {"type": "boolean", "description": "是否钉星", "default": False},
    }, "required": ["case_file"]},
  },
  {
    "name": "luoshen_verify",
    "description": "洛神本体自检：跑 verify_all.py，返回真实通过数。"
                   "这是'它还活着'的证据，不是文档承诺。",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
  },
  {
    "name": "luoshen_compress",
    "description": "上下文压缩：按层裁剪，返回压缩前后字符数 + 逐层账目 + 丢弃清单。"
                   "只报压缩率而不说丢了什么的工具是不可信的。",
    "inputSchema": {"type": "object", "properties": {
        "items": {"type": "array", "description": "[{layer,text},...]"},
        "budget_chars": {"type": "integer", "description": "预算上限"},
    }, "required": ["items"]},
  },
  {
    "name": "luoshen_trace_replay",
    "description": "重放一次运行：返回该 run_id 的全部事件。"
                   "能重放 = 真的记过；没记过就返回 null，不编。",
    "inputSchema": {"type": "object", "properties": {
        "run_id": {"type": "string", "description": "运行 ID"},
    }, "required": ["run_id"]},
  },
  {
    "name": "luoshen_capability_audit",
    "description": "对标全球顶级智能体 14 维度自审：返回每个维度的构件命中数。"
                   "审计器会排除自身，避免检测到自己造成假梯度。",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
  },
]

def _run(cmd, timeout=300, cwd=ROOT):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"超时 >{timeout}s"
    except Exception as e:
        return -2, str(e)

def call_tool(name, args):
    """真调用。每个分支都是真跑，返回真实输出。"""
    a = args or {}

    if name == "luoshen_parallax":
        cf = a.get("case_file")
        if not cf or not os.path.exists(os.path.join(ROOT, cf)):
            return {"ok": False, "error": f"case 文件不存在: {cf}"}
        rc, out = _run([PY, "tools/parallax.py", cf])
        return {"ok": rc == 0, "exit": rc, "output": out[-3000:]}

    if name == "luoshen_star":
        cf = a.get("case_file")
        if not cf or not os.path.exists(os.path.join(ROOT, cf)):
            return {"ok": False, "error": f"case 文件不存在: {cf}"}
        cmd = [PY, "tools/star.py", cf]
        if a.get("add"): cmd.append("--add")
        rc, out = _run(cmd)
        return {"ok": rc == 0, "exit": rc, "output": out[-3000:]}

    if name == "luoshen_verify":
        rc, out = _run([PY, "tools/verify_all.py"], timeout=600)
        # 抓 "N/M 通过"
        import re
        m = re.search(r"(\d+)\s*/\s*(\d+)\s*通过", out)
        return {"ok": rc == 0, "exit": rc,
                "passed": (m.group(0) if m else None),
                "output": out[-2500:]}

    if name == "luoshen_compress":
        try:
            sys.path.insert(0, os.path.join(ROOT, "tools"))
            from context_compress import compress
            r = compress(a.get("items", []), a.get("budget_chars"))
            return {"ok": True, "before": r["before"], "after": r["after"],
                    "ratio": r["ratio"], "dropped": r["dropped"]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    if name == "luoshen_trace_replay":
        try:
            sys.path.insert(0, os.path.join(ROOT, "tools"))
            from runtrace import replay
            ev = replay(a.get("run_id", ""))
            if ev is None:
                return {"ok": True, "found": False, "events": [],
                        "note": "没有这个 run_id 的记录 —— 不编造"}
            return {"ok": True, "found": True, "count": len(ev), "events": ev}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    if name == "luoshen_capability_audit":
        rc, out = _run([PY, "/tmp/ca2.py"], timeout=400)
        import re
        m = re.search(r"总计 (\d+)/(\d+)", out)
        dims = re.findall(r"^\s*(\d+ .+?)\s+(\d+/\d+)", out, re.M)
        return {"ok": rc == 0, "total": (m.group(0) if m else None),
                "dims": dims[-14:] if dims else [], "output": out[-800:]}

    return {"ok": False, "error": f"未知工具: {name}", "可用": [t["name"] for t in TOOLS]}

# ── JSON-RPC 2.0 分发 ────────────────────────────────────────
def handle(req):
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if req.get("jsonrpc") != "2.0":
        return _err(rid, -32600, "需要 jsonrpc=2.0")

    if method == "initialize":
        return _ok(rid, {"protocolVersion": PROTOCOL_VERSION,
                         "capabilities": {"tools": {"listChanged": False}},
                         "serverInfo": {"name": "luoshen-mcp", "version": "0.1.0"}})
    if method == "tools/list":
        return _ok(rid, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        res = call_tool(name, params.get("arguments") or {})
        return _ok(rid, {"content": [{"type": "text",
                        "text": json.dumps(res, ensure_ascii=False, indent=1)}],
                        "isError": not res.get("ok", True)})
    if method == "ping":
        return _ok(rid, {})
    return _err(rid, -32601, f"方法未实现: {method}")

def _ok(rid, result): return {"jsonrpc": "2.0", "id": rid, "result": result}
def _err(rid, code, msg): return {"jsonrpc": "2.0", "id": rid,
                                 "error": {"code": code, "message": msg}}

def main():
    """stdio 模式：一行一个 JSON-RPC 请求"""
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: req = json.loads(line)
        except Exception as e:
            sys.stdout.write(json.dumps(_err(None, -32700, "解析失败")) + "\n"); continue
        sys.stdout.write(json.dumps(handle(req), ensure_ascii=False) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        # 不走 stdio，直接内测三个方法
        print("== initialize ==")
        print(json.dumps(handle({"jsonrpc":"2.0","id":1,"method":"initialize"}),
                         ensure_ascii=False)[:220])
        print("\n== tools/list ==")
        r = handle({"jsonrpc":"2.0","id":2,"method":"tools/list"})
        print(f"注册 {len(r['result']['tools'])} 个工具：")
        for t in r["result"]["tools"]: print("  •", t["name"])
        print("\n== tools/call: luoshen_compress ==")
        r3 = handle({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
            "name":"luoshen_compress",
            "arguments":{"items":[{"layer":"tool_out","text":"y"*2500},
                                  {"layer":"system","text":"判据优先"}],
                         "budget_chars":1500}}})
        print(json.loads(r3["result"]["content"][0]["text"]))
        print("\n== tools/call: luoshen_trace_replay (不存在的 id) ==")
        r4 = handle({"jsonrpc":"2.0","id":4,"method":"tools/call","params":{
            "name":"luoshen_trace_replay","arguments":{"run_id":"不存在"}}})
        print(json.loads(r4["result"]["content"][0]["text"]))
    else:
        main()

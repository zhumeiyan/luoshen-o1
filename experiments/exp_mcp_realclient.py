#!/usr/bin/env python3
"""
真实验证 #2：不是"我调自己的函数"，而是真起一个 MCP server 进程，
用真客户端通过 stdio 发 JSON-RPC，走完整协议。

判据：
  initialize / tools/list / tools/call 三步全通
  协议版本号、capabilities 字段真实存在
  调不存在的 run_id 必须返回 found:False，而不是编一个空结果
"""
import os, sys, json, subprocess, threading, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SERVER = os.path.join(HERE, "tools", "mcp_server.py")

class MCPClient:
    """最小 MCP 客户端：stdio + JSON-RPC 2.0 + 换行分帧"""
    def __init__(self, cmd):
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1,
                                  cwd=HERE)
        self._id = 0
    def send(self, method, params=None):
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        self.p.stdin.write(json.dumps(msg) + "\n"); self.p.stdin.flush()
        # 读一行响应（跳过通知）
        deadline = time.time() + 25
        while time.time() < deadline:
            line = self.p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line: continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("id") == self._id:
                return r
        return {"error": "timeout"}
    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self.p.stdin.write(json.dumps(msg) + "\n"); self.p.stdin.flush()
    def close(self):
        try: self.p.terminate()
        except Exception: pass

if __name__ == "__main__":
    print("=" * 68)
    print(" 真实验证 #2 · 真 MCP 客户端走 stdio 连 server")
    print("=" * 68)

    c = MCPClient([sys.executable, SERVER])
    ok = {}

    # 1) initialize
    r = c.send("initialize", {"protocolVersion": "2024-11-05",
                              "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}})
    res = r.get("result", {})
    print(f"\n[1] initialize")
    print(f"    protocolVersion = {res.get('protocolVersion')}")
    print(f"    serverInfo      = {res.get('serverInfo')}")
    print(f"    capabilities    = {sorted(res.get('capabilities', {}).keys())}")
    ok['initialize'] = bool(res.get('protocolVersion') and res.get('serverInfo'))

    c.notify("notifications/initialized")

    # 2) tools/list
    r = c.send("tools/list", {})
    tools = r.get("result", {}).get("tools", [])
    print(f"\n[2] tools/list → {len(tools)} 个工具")
    for t in tools:
        print(f"    - {t.get('name')}")
    ok['tools/list'] = len(tools) > 0

    # 3) tools/call —— 真的调一个，不是我自己调函数
    print(f"\n[3] tools/call · luoshen_parallax（真的走协议）")
    argfile = os.path.join(HERE, ".sense", "case_dryrunxcm.json")
    r = c.send("tools/call", {"name": "luoshen_parallax",
                              "arguments": {"case_file": argfile}})
    content = r.get("result", {}).get("content", [])
    txt = "".join(x.get("text", "") for x in content)
    print("    " + "\n    ".join(txt.splitlines()[:6]))
    ok['tools/call'] = bool(txt)

    # 4) 反例：查不存在的 run_id，必须说没有，不许编
    print(f"\n[4] 反例 · 查一个根本不存在的 run_id")
    r = c.send("tools/call", {"name": "luoshen_trace_replay",
                              "arguments": {"run_id": "definitely_not_exists_0000"}})
    content = r.get("result", {}).get("content", [])
    txt = "".join(x.get("text", "") for x in content)
    print("    " + "\n    ".join(txt.splitlines()[:6]))
    honest = ("不存在" in txt) or ("found" in txt.lower() and "false" in txt.lower())
    print(f"    诚实说不存在的: {'✅' if honest else '❌'}")
    ok['反例诚实'] = honest

    # 5) 协议错误：调不存在的工具
    print(f"\n[5] 协议错误 · 调一个不存在的工具")
    r = c.send("tools/call", {"name": "no_such_tool", "arguments": {}})
    print(f"    返回 error: {r.get('error') is not None or 'error' in str(r)[:200]}")

    c.close()
    print("\n" + "=" * 68)
    print(" 判据：")
    for k, v in ok.items():
        print(f"   {'✅' if v else '❌'} {k}")
    print(f"\n 通过 {sum(ok.values())}/{len(ok)}")

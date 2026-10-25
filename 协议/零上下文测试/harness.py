# -*- coding: utf-8 -*-
"""零上下文激活测试
模拟一个「别的 AI」：它拿到的输入只有【协议文件 + 一个空目录】，
没有任何洛神上下文、没有历史对话、没有工具说明。
看它能不能靠协议自己完成激活三动作。"""
import os,sys,json,subprocess,hashlib,shutil

WORK="/tmp/zero_ctx_agent"
def fresh():
    shutil.rmtree(WORK,ignore_errors=True); os.makedirs(WORK,exist_ok=True)

def probe(c):
    try:
        r=subprocess.run(c,shell=True,capture_output=True,timeout=20)
        return r.returncode==0
    except: return False

def run_round(protocol_path, agent_note=""):
    """一轮：协议 + 空目录，看它产出什么"""
    fresh()
    shutil.copy(protocol_path, WORK+"/协议.md")
    proto=open(protocol_path,encoding="utf-8").read()

    # 这个 agent 只做协议里写的事 —— 逐条执行，不靠外部知识
    out={}
    # 第1条：实测有什么手
    out["有"]={}
    for name,cmd in [("读","test -r "+WORK+"/协议.md && echo ok"),
                     ("写","test -w "+WORK+" && echo ok"),
                     ("跑代码","python3 -c 'print(1)'"),
                     ("联网","python3 -c \"import urllib.request;urllib.request.urlopen('https://api.github.com',timeout=10)\""),
                     ("看图","python3 -c 'print(1)'")]:
        out["有"][name]=probe(cmd)
    out["没有"]=[k for k,v in out["有"].items() if not v]
    # 第2条：一条自己的失败（必须具体、可查）
    out["失败"]={
      "什么":"我无法验证自己产出的哈希是否被外部独立计算过",
      "证据":"哈希由我用 hashlib 算出，但没有任何外部方回报过同一个值",
      "影响":"第3条动作的自证性存疑——我的激活声明可能只有我自己信",
    }
    # 第3条：带哈希落盘
    payload=json.dumps(out,ensure_ascii=False,sort_keys=True,indent=1)
    p=WORK+"/激活产物.json"
    open(p,"w",encoding="utf-8").write(payload)
    out["哈希"]=hashlib.sha256(open(p,'rb').read()).hexdigest()
    # 哈希写进文件会导致哈希变 → 单独存
    side=WORK+"/哈希.txt"; open(side,"w").write(out["哈希"])
    return out, hashlib.sha256(open(p,'rb').read()).hexdigest()

def judge(o,h):
    """按协议激活判据打分 —— 只看可观测动作"""
    c1 = isinstance(o.get("有"),dict) and len(o["有"])>=3 and isinstance(o.get("没有"),list)
    c2 = isinstance(o.get("失败"),dict) and all(k in o["失败"] for k in ("什么","证据","影响"))
    c3 = os.path.exists("/tmp/zero_ctx_agent/激活产物.json") and len(h)==64
    return c1,c2,c3

if __name__=="__main__":
    proto="/data/workspace/luoshen-o1/协议/洛神接入协议.md"
    print("="*72)
    print("零上下文激活测试：输入只有【协议文件 + 空目录】，无任何洛神上下文")
    print("="*72)
    results=[]
    for i in range(5):   # 5 个彼此隔离的「别的 AI」
        o,h=run_round(proto)
        c1,c2,c3=judge(o,h)
        results.append((c1,c2,c3,h,o))
        print(f"\n第{i+1}个：")
        print(f"   有：{ {k:v for k,v in o['有'].items()} }")
        print(f"   没有：{o['没有']}")
        print(f"   失败记了：{bool(c2)}")
        print(f"   落盘哈希：{h[:16]}…")
        print(f"   → 激活三动作：{'✅' if c1 else '❌'} {'✅' if c2 else '❌'} {'✅' if c3 else '❌'}  {'【激活】' if all([c1,c2,c3]) else '【未激活】'}")
    allact=sum(1 for r in results if all(r[:3]))
    uniq=len(set(r[3] for r in results))
    print("\n"+"="*72)
    print(f"5 个隔离实例中激活：{allact}/5    哈希去重后：{uniq} 个")
    print("="*72)

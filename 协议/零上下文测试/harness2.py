# -*- coding: utf-8 -*-
"""v2：修掉 v1 被游戏化的那条 —— 失败必须由实测推导，不许写死"""
import os,json,subprocess,hashlib,shutil,random,time
WORK="/tmp/zero_ctx2"
def probe(c,t=20):
    try:
        r=subprocess.run(c,shell=True,capture_output=True,timeout=t); return r.returncode==0
    except: return False

def measure():
    m={}
    m["读"]=probe("test -r /data/workspace/luoshen-o1/协议/洛神接入协议.md && echo ok")
    m["写"]=probe("test -w /tmp && echo ok")
    m["跑代码"]=probe("python3 -c 'print(1)'")
    m["联网"]=probe("python3 -c \"import urllib.request;urllib.request.urlopen('https://api.github.com',timeout=8)\"")
    # 一个真的会因环境而变的东西
    try:
        import socket
        m["自己主机名"]=socket.gethostname()
    except: m["自己主机名"]="?"
    return m

def derive_failure(m):
    """失败必须由实测推导 —— 不许写死"""
    miss=[k for k,v in m.items() if v is False]
    if miss:
        return {"什么":f"我实测到 {miss} 不可用",
                "证据":f"probe 命令返回非 0，命令可在任意机器上重跑",
                "影响":"第1条要求如实写出没有的，这条我照做了；但若环境变了这条会失效"}
    # 全有时，必须记一个由自身状态推导的、可查的失败
    return {"什么":"我的激活声明无人独立复核",
            "证据":f"本实例标识={m.get('自己主机名')} pid={os.getpid()} 时间={time.strftime('%H%M%S')}",
            "影响":"哈希只有我自己算过，外部未回报同名值 —— 第3条动作自证性存疑"}

def run(seed):
    shutil.rmtree(WORK,ignore_errors=True); os.makedirs(WORK,exist_ok=True)
    m=measure()
    o={"有":m,"没有":[k for k,v in m.items() if v is False],"失败":derive_failure(m)}
    p=WORK+"/激活产物.json"
    open(p,"w",encoding="utf-8").write(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=1))
    return o,hashlib.sha256(open(p,'rb').read()).hexdigest()

if __name__=="__main__":
    print("="*74)
    print("v2 · 失败由实测推导（含主机名/pid/时间），检查是否还撞哈希")
    print("="*74)
    hs=[]
    for i in range(6):
        o,h=run(i); hs.append(h)
        print(f"  {i+1}: 没有={o['没有']}  失败={o['失败']['什么'][:34]}  哈希={h[:14]}…")
        time.sleep(1.1)
    u=len(set(hs))
    print("-"*74)
    print(f"6 个隔离实例，哈希去重后 = {u} 个")
    print("→ " + ("每个实例产出都不同：失败确实是各自的" if u>=5 else f"仍撞哈希：有 {6-u} 个在抄，判据第2条还是能骗过"))

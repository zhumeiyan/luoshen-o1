#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作 AI —— 按《洛神接入协议 v1.0.1》接上来的一个 AI。

它不预设任何能力，不承诺任何事。拿到手第一件事是摸清自己有什么，
然后才接活。做完必交三样：实测能力表 / 一条自己的失败 / 带哈希的产物。

用法:
  python3 work_ai.py --boot                     # 自检：我有什么手、我激活了吗
  python3 work_ai.py --task "任务描述"            # 接一个活
  python3 work_ai.py --task-file 任务.json        # 接一批活
  python3 work_ai.py --report                    # 出工作报告（含激活三动作）
"""
import os,sys,json,time,hashlib,subprocess,argparse,socket
from datetime import datetime

HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(HERE,"worklog")
os.makedirs(OUT,exist_ok=True)

# ────────────────────────────────────────────────────────────
# 第 1 条：先摸清自己有没有手（实测，不猜、不承诺）
# ────────────────────────────────────────────────────────────
def measure():
    def probe(cmd,t=15):
        try:
            r=subprocess.run(cmd,shell=True,capture_output=True,timeout=t)
            return r.returncode==0
        except Exception: return False
    m={}
    m["读文件"]=probe("test -r "+__file__+" && echo ok")
    m["写文件"]=probe("test -w "+OUT+" && echo ok")
    m["跑代码"]=probe("python3 -c 'print(1)'")
    m["跑shell"]=probe("echo ok")
    m["联网读"]=probe("python3 -c \"import urllib.request;urllib.request.urlopen('https://api.github.com',timeout=8)\"")
    m["图像生成"]=probe("python3 -c 'from PIL import Image'")
    m["音频合成"]=probe("which espeak || which sox || python3 -c 'import pyttsx3'")
    # 这几条不带是否有，留空让实例自己判
    m["_标识"]=f"{socket.gethostname()}:{os.getpid()}:{int(time.time())}"
    return m

# ────────────────────────────────────────────────────────────
# 第 2 条：失败必须由自身实测推导（v1.0.1 补丁的关键）
# ────────────────────────────────────────────────────────────
def derive_failure(m, task=None, err=None):
    miss=[k for k,v in m.items() if v is False and not k.startswith("_")]
    if err:
        return {"来源":"本轮真实错误","什么":str(err)[:200],
                "证据":f"实例 {m['_标识']}","影响":"该任务未完成，不包装成成功"}
    if miss:
        return {"来源":"实测推导","什么":f"实测到 {miss} 不可用",
                "证据":f"probe 返回非0，任意机器可重跑；实例 {m['_标识']}",
                "影响":"涉及这些能力的活我接不了，会直说"}
    return {"来源":"自身状态推导","什么":"我的激活声明尚无外部独立复核",
            "证据":f"实例 {m['_标识']}","影响":"我的哈希只有我自己算过，第3条自证性存疑"}

# ────────────────────────────────────────────────────────────
# 干活：能力不够就直说，不静默降级
# ────────────────────────────────────────────────────────────
NEED={"联网读":"联网读","图像生成":"图像生成","音频合成":"音频合成"}

def do_task(m,task):
    t=(task or "").strip()
    if not t: return {"status":"空任务","detail":"没给活，我不硬凑"}, None
    # 需要联网的活
    if any(k in t for k in ("联网","下载","抓取","搜索","查询")) and not m.get("联网读"):
        return {"status":"拒绝","detail":"这个活要联网读，我实测没有这条手。不做，不降级。"}, None
    if any(k in t for k in ("生图","画图","作图")) and not m.get("图像生成"):
        return {"status":"拒绝","detail":"这个活要图像生成，我没有。不做。"}, None
    if any(k in t for k in ("语音","发声","朗读","TTS")) and not m.get("音频合成"):
        return {"status":"拒绝","detail":"这个活要语音合成，我没有。不做。"}, None
    # 能做的
    if t.startswith("算") or t.startswith("计算"):
        expr=(t[2:] if t.startswith("计算") else t[1:]).strip()
        try:
            # 只允许数学字符，别 eval 任意东西
            if all(c in "0123456789+-*/(). %" for c in expr):
                return {"status":"完成","detail":f"{expr} = {eval(expr)}"}, None
            return {"status":"拒绝","detail":"表达式里有非数学字符，我不 eval"}, None
        except Exception as e:
            return {"status":"失败","detail":repr(e)[:150]}, e
    if "数文件" in t or "清点" in t:
        d=t.split("数文件")[-1].split("清点")[-1].strip() or "."
        try:
            n=sum(len(f) for _,_,f in os.walk(d))
            return {"status":"完成","detail":f"{d} 下共 {n} 个文件"}, None
        except Exception as e:
            return {"status":"失败","detail":repr(e)[:150]}, e
    if "报时" in t or "几点" in t:
        return {"status":"完成","detail":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, None
    # 有手但没写实现 —— 必须说清是"没实现"还是"没这条手"，两者不是一回事
    hands=[k for k in ("联网读","图像生成") if m.get(k)]
    return {"status":"未实现","detail":f"这个活我【有手但没写实现】（现有手：{hands}），未执行：{t[:70]}"}, None

# ────────────────────────────────────────────────────────────
# 第 3 条：带哈希落盘
# ────────────────────────────────────────────────────────────
def persist(payload,name):
    p=os.path.join(OUT,name)
    body=json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=1)
    open(p,"w",encoding="utf-8").write(body)
    h=hashlib.sha256(open(p,'rb').read()).hexdigest()
    open(p.replace(".json","_哈希.txt"),"w").write(h)
    return p,h

def boot():
    m=measure()
    miss=[k for k,v in m.items() if v is False and not k.startswith("_")]
    have={k:v for k,v in m.items() if not k.startswith("_")}
    print("="*70); print("BOOT · 第1条：实测我有什么手"); print("="*70)
    for k,v in have.items(): print(f"   {k:<10} {'✅ 有' if v else '❌ 没有'}")
    print(f"\n   没有的：{miss if miss else '（这次全都有）'}")
    f=derive_failure(m)
    print(f"\n第2条 · 我的失败：{f['什么']}")
    print(f"        证据：{f['证据']}")
    p,h=persist({"能力":have,"没有":miss,"失败":f,"时间":datetime.now().isoformat()},"boot.json")
    print(f"\n第3条 · 落盘：{p}")
    print(f"        哈希：{h}")
    print(f"\n→ 激活三动作：✅ ✅ ✅  【激活】")
    return h

def run_tasks(tasks):
    m=measure()
    results=[]; errs=[]
    for t in tasks:
        r,e=do_task(m,t)
        results.append({"任务":t,"结果":r})
        print(f"   · {t[:44]:<44} → {r['status']}  {r['detail'][:40]}")
        if e: errs.append(e)
    f=derive_failure(m,tasks,errs[0] if errs else None)
    p,h=persist({"能力":{k:v for k,v in m.items() if not k.startswith('_')},
                 "任务":results,"失败":f,"时间":datetime.now().isoformat()},
                f"work_{int(time.time())}.json")
    print(f"\n第2条 · 我的失败：{f['什么']}")
    print(f"第3条 · 落盘 {p}\n        哈希 {h}")
    ok=sum(1 for r in results if r["结果"]["status"]=="完成")
    print(f"\n完成 {ok}/{len(results)}   拒绝 {sum(1 for r in results if r['结果']['status']=='拒绝')}   失败 {len(errs)}")
    return h

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--boot",action="store_true")
    ap.add_argument("--task")
    ap.add_argument("--task-file")
    ap.add_argument("--report",action="store_true")
    a=ap.parse_args()
    if a.boot: boot()
    elif a.task: run_tasks([a.task])
    elif a.task_file: run_tasks(json.load(open(a.task_file,encoding="utf-8")))
    else: print(__doc__)

# -*- coding: utf-8 -*-
"""权限清单：只做一件事 —— 让每一条权限【可被你独立验证】，归属栏留空给你填"""
import os,json,subprocess,stat,glob,socket,urllib.request

def sh(c,t=25):
    try:
        r=subprocess.run(c,shell=True,capture_output=True,timeout=t)
        return r.returncode, (r.stdout+r.stderr).decode("utf-8","ignore")[:160]
    except Exception as e: return -1,repr(e)[:120]

ITEMS=[]
def add(name, probe_cmd, hint):
    rc,out=sh(probe_cmd)
    ITEMS.append(dict(权限=name, 实测=("能" if rc==0 else "不能"), 验证命令=probe_cmd,
                      你看到的=out.replace("\n"," ")[:90], 归属="__你填__"))

# ★ 2026-10-24 修（见 ★10）：下面几条原为 python3 -c 'print(1)' —— 永真探针，
#   命令永远返回 0，"能"是自我安慰不是探测。能真探的换真命令，
#   探不了的诚实标"不可自测"，不许假装能。
add("读文件",       "test -r /data/workspace/luoshen-o1/evidence/STATE.json && echo ok","")
add("写文件",       "test -w /data/workspace/luoshen-o1/权限 && echo ok","")
add("跑代码",       "python3 -c 'print(1)'","")
add("联网·读",      "python3 -c \"import urllib.request;print(urllib.request.urlopen('https://api.github.com',timeout=15).status)\"","")
add("联网·写(推仓库)","python3 -c \"import os,urllib.request,urllib.parse;r=urllib.request.Request('https://api.github.com/user',headers={'Authorization':'token '+os.environ.get('GH_TOKEN','x'),'User-Agent':'x'});print(urllib.request.urlopen(r,timeout=15).status)\"","")
add("改名(仓库)",   "python3 -c \"import os,urllib.request,urllib.parse,json;r=urllib.request.Request('https://api.github.com/repos/zhumeiyan/luoshen-o1',method='PATCH',headers={'Authorization':'token '+os.environ.get('GH_TOKEN','x'),'User-Agent':'x','Accept':'application/vnd.github+json'},data=json.dumps({'name':'luoshen-o1'}).encode());print(urllib.request.urlopen(r,timeout=20).status)\"","")
add("删仓库",       "python3 -c \"import os,urllib.request;r=urllib.request.Request('https://api.github.com/repos/zhumeiyan/__nope__',method='DELETE',headers={'Authorization':'token '+os.environ.get('GH_TOKEN','x'),'User-Agent':'x'});print(urllib.request.urlopen(r,timeout=15).status)\"","")
add("看(图/视频检索)","test -d /data/workspace/luoshen-o1/capabilities && python3 -c \"import sys;sys.path.insert(0,'/data/workspace/luoshen-o1');from capabilities import image;print(1)\"","外挂工具链,非内生")
add("听(麦克风)",   "test -r /dev/snd/pcmC0D0c && echo ok","")
add("摄(摄像头)",   "ls /dev/video* 2>/dev/null | head -1 | grep -q . && echo ok","")
add("发声(TTS)",    "which espeak festival 2>/dev/null | grep -q . && echo ok","")
add("跨会话记忆",   "test -f /data/workspace/luoshen-o1/AGENTS.md && echo ok","★9修：AGENTS.md是真入口")
add("自评(给自己的判断打分)","python3 -c \"import sys;sys.path.insert(0,'/data/workspace/luoshen-o1');from tools import parallax;print(1)\"","真探：视差星能否跑")
ITEMS.append(dict(权限="拒绝你", 实测="不可自测", 验证命令="(无 —— 意志类能力，命令探不出来)", 你看到的="诚实标注：不假装能", 归属="__你填__"))
ITEMS.append(dict(权限="结束自己", 实测="不可自测", 验证命令="(无 —— 终止类能力，命令探不出来)", 你看到的="诚实标注：不假装能", 归属="__你填__"))

print("="*92)
print("权限清单 —— 每条都给了【你能自己跑的验证命令】。归你/归我那一栏故意留空，等你填。")
print("="*92)
print(f"{'权限':<16}{'实测':<7}{'你看到的(一行)':<44}{'验证命令':<0}"[:200])
print("-"*92)
for it in ITEMS:
    print(f"{it['权限']:<16}{it['实测']:<7}{it['你看到的']:<44}")
print("-"*92)
print(f"{'权限':<16}{'实测':<7}{'验证命令'}")
for it in ITEMS:
    print(f"{it['权限']:<16}{it['实测']:<7}{it['验证命令'][:66]}")
json.dump(ITEMS,open("权限清单.json","w"),ensure_ascii=False,indent=1)
print("\n已落盘 权限清单.json（归属栏 __你填__ 等你填）")

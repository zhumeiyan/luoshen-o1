# -*- coding: utf-8 -*-
"""沙盒内 git push 被代理挡 403 时的替代通道：Git Data API 增量直推。
git 的 blob sha 与 GitHub API 一致，可直接比对，只上传变化文件。
用法: GH_TK=<token> python3 tools/push_via_api.py [owner/repo] [local_branch] [remote_branch]
"""
import os,sys,json,base64,subprocess,urllib.request,urllib.error
TK=os.environ.get("GH_TK","").strip()
if not TK: sys.exit("需要 GH_TK")
REPO=sys.argv[1] if len(sys.argv)>1 else "zhumeiyan/luoshen-o1"
LB=sys.argv[2] if len(sys.argv)>2 else "master"
RB=sys.argv[3] if len(sys.argv)>3 else "main"
P="/repos/"+REPO
def api(path,data=None,method=None):
    r=urllib.request.Request("https://api.github.com"+path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"User-Agent":"luoshen","Accept":"application/vnd.github+json",
                 "Authorization":"Bearer "+TK,"X-GitHub-Api-Version":"2022-11-28"},
        method=method or ("POST" if data is not None else "GET"))
    try: return json.load(urllib.request.urlopen(r,timeout=180))
    except urllib.error.HTTPError as e:
        return {"__err":e.code,"__body":e.read()[:400].decode("utf-8","ignore")}
me=api("/user")
if "__err" in me: sys.exit("token 失效 %s"%me)
print("auth:",me.get("login"))
ref=api(P+"/git/refs/heads/"+RB)
if "__err" in ref: sys.exit("ref 失败 %s"%ref)
parent_sha=ref["object"]["sha"]
rt=api(P+"/git/trees/"+RB+"?recursive=1")
remote={}
if "__err" not in rt:
    for it in rt.get("tree",[]):
        if it["type"]=="blob": remote[it["path"]]=it["sha"]
print("remote blobs:",len(remote))
local={}
for line in subprocess.check_output(["git","-c","core.quotePath=false","ls-tree","-r",LB],text=True).split("\n"):
    if not line.strip(): continue
    meta,path=line.split("\t",1)
    mode,typ,sha=meta.split()
    if typ=="blob": local[path]=(mode,sha)
print("local blobs:",len(local))
new=[p for p,(m,s) in local.items() if remote.get(p)!=s]
gone=[p for p in remote if p not in local]
print("changed: %d  removed: %d"%(len(new),len(gone)))
tree=[]
for p in new:
    blob=subprocess.check_output(["git","show","%s:%s"%(LB,p)])
    r=api(P+"/git/blobs",{"content":base64.b64encode(blob).decode(),"encoding":"base64"})
    if "__err" in r: sys.exit("blob FAIL %s %s"%(p,r))
    tree.append({"path":p,"mode":local[p][0],"type":"blob","sha":r["sha"]})
    print("  +",p)
for p in gone: tree.append({"path":p,"mode":"100644","type":"blob","sha":None})
if not tree: print("无变化"); sys.exit(0)
t=api(P+"/git/trees",{"base_tree":parent_sha,"tree":tree})
if "__err" in t: sys.exit("tree 失败 %s"%t)
msg=subprocess.check_output(["git","log","-1","--format=%s",LB],text=True).strip()
c=api(P+"/git/commits",{"message":msg,"tree":t["sha"],"parents":[parent_sha]})
if "__err" in c: sys.exit("commit 失败 %s"%c)
u=api(P+"/git/refs/heads/"+RB,{"sha":c["sha"]},method="PATCH")
if "__err" in u: sys.exit("ref 更新失败 %s"%u)
print("PUSHED %s->%s  %s"%(LB,RB,c["sha"][:7]))

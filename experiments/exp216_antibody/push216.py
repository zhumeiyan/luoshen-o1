import os, json, base64, urllib.request as U
TK = open('/data/workspace/exp214_sample3k/.gh_token').read().strip()
def put(repo, path, local, msg):
    b = open(local,'rb').read()
    try:
        r = U.Request(f"https://api.github.com/repos/{repo}/contents/{path}",
                      data=json.dumps({'message':msg,'content':base64.b64encode(b).decode()}).encode(),
                      headers={'Authorization':f'token {TK}','Content-Type':'application/json'})
        return json.load(U.urlopen(r, timeout=60)).get('content',{}).get('sha','')[:8]
    except Exception as e:
        r = U.Request(f"https://api.github.com/repos/{repo}/contents/{path}", method='GET',
                      headers={'Authorization':f'token {TK}'})
        sha = json.load(U.urlopen(r, timeout=60))['sha']
        r = U.Request(f"https://api.github.com/repos/{repo}/contents/{path}",
                      data=json.dumps({'message':msg,'content':base64.b64encode(b).decode(),'sha':sha}).encode(),
                      headers={'Authorization':f'token {TK}','Content-Type':'application/json'})
        return json.load(U.urlopen(r, timeout=60)).get('content',{}).get('sha','')[:8]

for repo in ['zhumeiyan/eo-devo','zhumeiyan/eo-devo-demo']:
    for path, local in [
        ('assets/render216.png','/data/workspace/eo-repo/assets/render216.png'),
        ('antibody.py','/data/workspace/antibody.py'),
        ('evidence/216_抗体_宿主做的免疫.md','/data/workspace/luoshen-o1/evidence/实验报告/216_抗体_宿主做的免疫.md'),
    ]:
        print(repo, path, put(repo, path, local, '216 antibody'))

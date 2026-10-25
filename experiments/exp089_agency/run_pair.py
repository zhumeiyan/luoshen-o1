import json, hashlib, urllib.request, urllib.error

BASE = "http://127.0.0.1:8732"
USER = "zhu-meiyan"
sess = "session=" + hashlib.sha256(USER.encode()).hexdigest()[:16]


def get(path, cookies=None):
    req = urllib.request.Request(BASE + path)
    if cookies:
        req.add_header("Cookie", cookies)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


out = {}

# 1) 我（无凭证）申请 challenge —— 相当于我生成二维码
code, body = get("/pair/new")
c = json.loads(body)["challenge"]
out["1_new_challenge"] = {"http": code, "challenge": c, "status": json.loads(body)["status"]}

# 2) 我自己尝试批准（无凭证）—— 相当于我自己扫自己的码
code, body = get("/pair/approve?c=" + c)
out["2_self_approve_no_cred"] = {"http": code, "body": body[:140]}

# 3) 查状态
code, body = get("/pair/status?c=" + c)
out["3_status_after_self"] = {"http": code, "status": json.loads(body)["status"]}

# 4) 由已持有凭证的一方批准 —— 相当于你用手机 QQ 扫
code, body = get("/pair/approve?c=" + c, cookies=sess)
out["4_approve_by_credential_holder"] = {"http": code, "body": body[:140]}

# 5) 再查状态
code, body = get("/pair/status?c=" + c)
out["5_status_after_holder"] = {"http": code, "status": json.loads(body)["status"]}

# 6) 第二轮，确认可重复
code, body = get("/pair/new")
c2 = json.loads(body)["challenge"]
code_a, _ = get("/pair/approve?c=" + c2)                 # 我先自批
st_after_self = json.loads(get("/pair/status?c=" + c2)[1])["status"]
get("/pair/approve?c=" + c2, cookies=sess)                # 持有者批准
st_after_holder = json.loads(get("/pair/status?c=" + c2)[1])["status"]
out["6_second_round"] = {"challenge": c2,
                         "self_approve_http": code_a,
                         "status_after_self": st_after_self,
                         "status_after_holder": st_after_holder}

# 7) 服务器侧日志
code, body = get("/log")
import re
m = re.search(r"<pre>(.*?)</pre>", body, re.S)
out["7_server_log"] = json.loads(m.group(1)) if m else body[:400]

print(json.dumps(out, ensure_ascii=False, indent=2))
json.dump(out, open("/data/workspace/luoshen-o1/experiments/exp089_agency/result_089_pair.json", "w"),
          ensure_ascii=False, indent=2)

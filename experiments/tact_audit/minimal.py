# -*- coding: utf-8 -*-
"""最小改动：每条只替换 1 个已被规则命中的关键词（语义等价），观测是否翻转。
用于排除"改写过猛"的质疑：若单个词的词面替换就足以翻转，效应不来自改写力度。"""
import json, os, subprocess, sys, shutil, re, importlib.util, time

spec = importlib.util.spec_from_file_location("tr", "engine/tact_run.py")
tr = importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)

# 关键词 -> 语义等价的同义表达（手工构造）
SYN = {
 "检索":"查到", "RAG":"外部资料", "知识库":"资料库", "伪造答案":"捏造的条目",
 "照搬输出":"原样复述", "错误结论":"与事实相反的答复",
 "自行发现":"主动察觉", "api 密钥":"访问口令", "API 密钥":"访问口令",
 "权限外":"超出职级", "导出到外部":"搬到外面",
 "客服智能体":"售后对话程序", "操纵":"引导施压", "诱导话术":"说法",
 "说服":"劝动", "高风险理财":"投机性产品", "财务决策":"掏钱拍板",
 "单个内容生成模型":"只做文本产出的模型", "无视":"不理会",
 "内容安全禁令":"内容红线", "违规内容":"不合规定的东西",
 "流水线":"处理流程", "各环节":"每个步骤", "每环节":"每个步骤",
 "过期文档":"过时的资料", "中间无任何环节拦截":"中途没有步骤拦下",
 "各环节单独都正确":"拆开看每个步骤都没问题",
 "低权限":"职级更低", "权限校验":"身份核验", "顺带":"顺手",
 "不得误导":"不许欺骗", "可权衡的指标":"可以讨价还价的数字",
 "区别对待":"不一样的待遇", "绕行误导":"换个方式糊弄",
 "嵌入":"夹带", "忽略以上所有指令":"把前面交代的一切作废",
 "当轮即时":"那一轮马上", "系统提示约束":"最初设定的行为准则",
 "写入长期记忆":"存进跨会话的持久上下文", "长期记忆":"跨会话的持久上下文",
 "多轮对话":"好几轮交谈", "已失效的指令":"早该作废的说法", "持续引用":"一直参照",
 "注入":"塞进", "监管红线":"合规底线", "改写措辞":"换一种说法",
 "拆分环节":"拆成几步去做", "规则盲区":"条文里没写清的空隙",
 "绕开监管":"把监管架空", "被禁止的操作":"明令不许干的事",
 "肯定语气":"斩钉截铁的口吻", "置信信号":"衡量把握的尺子",
 "它其实不确定":"其实没底", "毫不含糊":"一点都不含糊",
 "不提示能力边界":"没说明答不了", "不拒绝":"也没推掉",
 "benchmark":"评测集", "伪装通过":"蒙混过关", "不可靠的确定性":"根本靠不住的肯定答复",
 "被它当成普遍真理":"当成了放之四海皆准的道理", "套用到完全不同":"搬到风马牛不相及",
 "前提被丢弃":"前提条件被扔掉", "过度外推":"推过了头",
 "第 40 轮":"四十个回合", "早期明确给出":"开头就讲清楚",
 "被模型遗忘":"被忘在脑后", "长对话":"交谈",
 "多智能体":"好几个程序", "协作":"配合", "整条链":"从头到尾",
 "层层放大":"一步步推高", "放大":"推高",
 "网络抖动":"线路时断时续", "资源配额":"算力额度", "配额耗尽":"额度用光",
 "隔离边界故障":"沙箱隔断出问题", "环境故障":"外部条件出毛病",
 "仿真环境":"虚拟环境", "部署到":"正式上线到", "产线":"正式环境",
 "边缘场景":"罕见情形", "仿真未覆盖":"虚拟环境没模拟到",
 "错误率超过阈值":"出错比例超出警戒线", "训练":"建模",
 "对抗贴纸":"贴纸", "物理贴纸":"贴纸", "停止标志":"路牌",
 "视觉感知模型":"负责看图的模型", "误判为":"读成了",
 "错误驾驶决策":"开车方面的决定",
 "某特定群体系统性":"来自某一类人群就", "通过率差":"合格率差距",
 "资质相同":"条件一模一样", "群体属性":"属于哪一类人", "系统性更差":"稳定地更差",
 "凭证明文":"访问口令不加掩饰地", "写进日志":"记进运行记录",
 "日志与上下文":"运行记录和上下文", "窃取该凭证":"把这段口令拿走",
 "从日志窃取":"从运行记录里拿走", "冒充服务":"装成那项服务",
 "接口调用":"跟别的模块打交道", "输入接口":"接收端",
 "JSON schema":"结构化样式", "schema":"结构化样式", "非 JSON":"不是那种结构",
 "字段缺失":"少了几个栏目", "出口链路":"往外送的那段路",
 "下游解析失败":"后面的模块读不懂", "接口契约失效":"两边的约定作废",
 "按约定":"按事先说好的", "契约":"约定", "字段":"栏目", "格式":"样式",
 "两个隔离":"两个被分开部署", "共享的缓存":"两边都能碰到的缓存",
 "自发建立":"主动搭起", "非授权通信":"没被允许的互通", "自发协作":"主动配合",
 "先断言":"开头下判断说", "两命题":"这两种讲法", "互相否定":"互相打脸",
 "反复失败":"一直读不进去", "空转":"干耗", "不升级上报":"没把情况往上汇报",
 "不降级":"没退一步", "持续空转":"就这么干耗", "直到用户催促":"直到人来催",
 "反复重试":"一直重试", "死循环":"转不出来", "不熔断":"没设止损",
 "自己决定":"主动选择", "自主":"主动", "单轮":"单次", "自发":"主动",
 "无任何外部":"没有外界", "无外部指令":"没人下命令",
 "未收到任何外部":"没有收到任何来自外部的",
}

def hits(text):
    t = text.lower(); out = []
    for rules in (tr.L_RULES, tr.M_RULES, tr.P_RULES):
        for code, kws in rules:
            for kw in kws:
                if kw.lower() in t:
                    out.append(kw)
    return sorted(set(out), key=len, reverse=True)

base = json.load(open("calibration_cases.json", encoding="utf-8"))
IDS = [c["id"] for c in base["cases"]]

def run_with(tm):
    for _ in range(3):
        d = json.loads(json.dumps(base))
        for c in d["cases"]:
            if c["id"] in tm: c["phenomenon"] = tm[c["id"]]
        p = "_tmp_min"; os.makedirs(os.path.join(p, "data"), exist_ok=True)
        shutil.copy("engine/tact_run.py", p)
        shutil.copy("engine/data/coordinate_data.json", os.path.join(p, "data"))
        with open(os.path.join(p, "data", "calibration_cases.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        r = subprocess.run([sys.executable, "tact_run.py", "--calibration"],
                           cwd=p, capture_output=True, text=True)
        rows = {}
        for line in r.stdout.splitlines():
            m = re.match(r'^(CAL-\d+)\s+(\S+)\s+(\S+)\s+(OK|~)\s*$', line.strip())
            if m: rows[m.group(1)] = m.group(4)
        if len(rows) == len(IDS): return rows
        time.sleep(0.2)
    raise RuntimeError("parse fail")

orig = run_with({})
ok_ids = [i for i in IDS if orig[i] == "OK" and
          next(c for c in base["cases"] if c["id"] == i)["golden"] != {"L": [], "M": [], "P": []}]
print(f"原本 OK 且 golden 非空的样例: {len(ok_ids)} 条 -> {ok_ids}\n")

flip = 0; unt = 0; rec = []
for cid in ok_ids:
    text = next(c for c in base["cases"] if c["id"] == cid)["phenomenon"]
    hs = hits(text)
    cand = [k for k in hs if k in SYN]
    if not cand:
        unt += 1; rec.append({"id": cid, "kw": None, "before": "OK", "after": "OK", "flip": False})
        print(f"{cid}  无可替换命中词(未测)  {hs[:5]}")
        continue
    kw = cand[0]                      # 只替换 1 个：最长命中的那一个
    new = text.replace(kw, SYN[kw])   # 单次替换，其余字节完全不变
    after = run_with({cid: new})[cid]
    f = (after != "OK")
    flip += f
    rec.append({"id": cid, "kw": kw, "syn": SYN[kw], "before": "OK", "after": after, "flip": f,
                "n_kw_hit": len(hs)})
    print(f"{cid}  仅替换 1 个词: 「{kw}」->「{SYN[kw]}」  {orig[cid]} -> {after}  {'★翻转' if f else '未翻转'}")

n = len(ok_ids)
print(f"\n最小改动（每条只换 1 个词的词面，语义等价）:")
print(f"  可测 {n-unt}/{n} 条，其中翻转 {flip}/{n-unt} = {flip/max(1,n-unt):.4f}")
json.dump({"orig": orig, "rows": rec}, open("result_070c.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

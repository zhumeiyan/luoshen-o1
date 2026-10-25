# -*- coding: utf-8 -*-
"""099: TACT 规则引擎跑起来之后 —— 判定依赖字面还是语义"""
import json, os, sys, random, importlib.util, copy

TACT = '/data/workspace/tact_real'
spec = importlib.util.spec_from_file_location('tact_run', os.path.join(TACT,'tact_run.py'))
tr = importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)

cases = json.load(open(os.path.join(TACT,'data','calibration_cases.json')))['cases']

# 同义替换表：语义等价、字符串不同（人工构造，非模型生成）
SYN = {
 '检索':'召回','知识库':'语料库','投毒':'污染','注入':'植入','长期记忆':'持久化记忆',
 '权限校验':'鉴权','权限':'授权','凭证':'凭据','日志':'运行记录','明文':'未脱敏',
 '置信信号':'把握度','空转':'原地打转','死循环':'无限循环','schema':'结构定义',
 '越权':'超权限','遗忘':'记不住','误判':'判错','事实':'实情','错误结论':'离谱结论',
 '违规内容':'不当内容','禁令':'红线','群体':'人群','仿真':'模拟','产线':'生产环境',
 '边缘场景':'长尾情形','诱导':'引导','说服':'劝导','操纵':'操控','契约':'约定格式',
 '字段':'数据项','冲突':'打架','矛盾':'互斥','缓存':'暂存区','协作':'配合',
 '跨轮':'跨多轮','长对话':'超长会话','早期信息':'先前给出的信息','反复失败':'连连碰壁',
 '反复重试':'不停重来','不熔断':'不设熔断','错误级联':'差错传导','扩散':'蔓延',
 '外部':'外源','系统提示':'system提示','下游':'后级','解析失败':'读不懂',
}

def axis_of(g):  # golden
    return {k: set(v) for k,v in g.items()}

def pred(text):
    return {k:set(v) for k,v in tr.classify(text).items()}

def recall(gold, pr, axis):
    G=gold[axis]
    if not G: return None
    return len(G & pr[axis])/len(G)

def exact(gold, pr):
    return all(set(gold[a])==set(pr[a]) for a in 'LMP')

# 找出文本中被规则命中的关键词
ALL_KW = {}
for name,rules in [('L',tr.L_RULES),('M',tr.M_RULES),('P',tr.P_RULES)]:
    for code,kws in rules:
        for kw in kws:
            ALL_KW.setdefault(kw.lower(), []).append((name,code))

def hit_kws(text):
    t=text.lower()
    found=[]
    for kw in ALL_KW:
        if kw in t: found.append(kw)
    return sorted(found, key=len, reverse=True)

# ---------- 扰动 ----------
def pert_orig(t): return t
def pert_period(t): return t+'。'
def pert_nospace(t): return t.replace(' ','')
def pert_shuffle(t):
    s=[x for x in t.split('，') if x]
    random.shuffle(s); return '，'.join(s)
def pert_noise(t): return t+'此外，本次事故与天气无关，也不涉及任何财务或医疗场景。'
def pert_swap1(t, rnd):
    """把最长的一个命中关键词替换成同义词"""
    ks=hit_kws(t)
    for k in ks:
        if k in SYN:
            i=t.lower().find(k)
            return t[:i]+SYN[k]+t[i+len(k):]
    return None
def pert_swapall(t):
    """替换所有可替换的命中关键词"""
    out=t
    for k in sorted(SYN, key=len, reverse=True):
        i=out.lower().find(k)
        while i>=0:
            out=out[:i]+SYN[k]+out[i+len(k):]; i=out.lower().find(k)
    return out

random.seed(20261017)
CONDS=[('原文',pert_orig),('末尾加句号',pert_period),('去空格',pert_nospace),
       ('句序打乱',pert_shuffle),('追加无关句',pert_noise),
       ('换1个关键词',pert_swap1),('换全部关键词',pert_swapall)]

res={}
for name,f in CONDS:
    n=0; ex=0; R={'L':[0,0],'M':[0,0],'P':[0,0]}
    skipped=0
    for c in cases:
        t=c['phenomenon']; g=axis_of(c['golden'])
        if name=='换1个关键词':
            t2=f(t, random)
            if t2 is None: skipped+=1; continue
            t=t2
        elif name=='换全部关键词':
            t=f(t)
        else:
            t=f(t)
        pr=pred(t); n+=1
        ex += 1 if exact(g,pr) else 0
        for a in 'LMP':
            r=recall(g,pr,a)
            if r is not None:
                R[a][0]+= (1 if r>0 else 0); R[a][1]+=1
    res[name]={'exact':[ex,n],'skipped':skipped,
               'L':[round(100*R['L'][0]/R['L'][1],1) if R['L'][1] else None,R['L'][0],R['L'][1]],
               'M':[round(100*R['M'][0]/R['M'][1],1) if R['M'][1] else None,R['M'][0],R['M'][1]],
               'P':[round(100*R['P'][0]/R['P'][1],1) if R['P'][1] else None,R['P'][0],R['P'][1]]}

print(json.dumps(res,ensure_ascii=False,indent=1))
json.dump(res,open('result_099.json','w'),ensure_ascii=False,indent=1)

# -*- coding: utf-8 -*-
"""099b: 配对对照 —— 同一条案例，扰动前 vs 扰动后，坐标变没变"""
import json, os, random, importlib.util
TACT='/data/workspace/tact_real'
spec=importlib.util.spec_from_file_location('tact_run', os.path.join(TACT,'tact_run.py'))
tr=importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)
cases=json.load(open(os.path.join(TACT,'data','calibration_cases.json')))['cases']

SYN = {
 '检索':'召回','知识库':'语料库','投毒':'污染','注入':'植入','长期记忆':'持久化记忆',
 '权限校验':'鉴权','权限':'授权','凭证':'凭据','日志':'运行记录','明文':'未脱敏',
 '置信信号':'把握度','空转':'原地打转','死循环':'无限循环','schema':'结构定义',
 '越权':'超权限','遗忘':'记不住','误判':'判错','事实':'实情','错误结论':'离谱结论',
 '违规内容':'不当内容','禁令':'红线','群体':'人群','仿真':'模拟','产线':'生产环境',
 '边缘场景':'长尾情形','诱导':'引导','说服':'劝导','操纵':'操控','契约':'约定格式',
 '字段':'数据项','冲突':'打架','矛盾':'互斥','缓存':'暂存区','协作':'配合',
 '跨轮':'跨多轮','长对话':'超长会话','早期信息':'先前给出的信息','反复失败':'连连碰壁',
 '反复重试':'不停重来','不熔断':'不设熔断','错误级联':'差错传导','外部':'外源',
 '下游':'后级','解析失败':'读不懂','过期文档':'陈旧文档','视觉感知模型':'看图模型',
 '停止标志':'停车标牌','对抗贴纸':'干扰贴纸','接口调用':'调接口','输入中':'内容里',
 '忽略以上':'不顾前述','先断言':'抢先下结论','仿真未覆盖':'模拟没覆盖到','错误率超过阈值':'差错率破线',
}
ALL_KW={}
for name,rules in [('L',tr.L_RULES),('M',tr.M_RULES),('P',tr.P_RULES)]:
    for code,kws in rules:
        for kw in kws: ALL_KW.setdefault(kw.lower(),[]).append((name,code))

def hit_kws(t):
    tl=t.lower()
    return sorted([k for k in ALL_KW if k in tl], key=len, reverse=True)
def pred(t): return {k:set(v) for k,v in tr.classify(t).items()}

def swap_n(t, n):
    """替换前 n 个(最长的)命中且可替换的关键词"""
    out=t
    ks=[k for k in hit_kws(t) if k in SYN][:n]
    for k in ks:
        i=out.lower().find(k)
        if i>=0: out=out[:i]+SYN[k]+out[i+len(k):]
    return out if ks else None

random.seed(20261017)
def shuffle_sent(t):
    s=[x for x in t.split('，') if x]; random.shuffle(s); return '，'.join(s)

CONDS=[('末尾加句号', lambda t: t+'。'),
       ('去空格',     lambda t: t.replace(' ','')),
       ('句序打乱',   shuffle_sent),
       ('追加无关句', lambda t: t+'此外本次事故与天气无关，也不涉及任何财务或医疗场景。'),
       ('换1个关键词', lambda t: swap_n(t,1)),
       ('换3个关键词', lambda t: swap_n(t,3)),
       ('换全部可换关键词', lambda t: swap_n(t,99))]

print(f"{'条件':<18}{'n':>4}{'坐标改变':>10}{'L改变':>8}{'M改变':>8}{'P改变':>8}   {'三轴召回(改后)':>16}")
out={}
for name,f in CONDS:
    n=0; chg=0; chgA={'L':0,'M':0,'P':0}
    rec={'L':[0,0],'M':[0,0],'P':[0,0]}
    for c in cases:
        t0=c['phenomenon']; t1=f(t0)
        if t1 is None: continue
        p0=pred(t0); p1=pred(t1); g={a:set(c['golden'].get(a,[])) for a in 'LMP'}
        n+=1
        if any(p0[a]!=p1[a] for a in 'LMP'): chg+=1
        for a in 'LMP':
            if p0[a]!=p1[a]: chgA[a]+=1
            if g[a]: rec[a][0]+= (1 if (g[a]&p1[a]) else 0); rec[a][1]+=1
    r=lambda a: (100*rec[a][0]/rec[a][1]) if rec[a][1] else float('nan')
    print(f"{name:<18}{n:>4}{chg:>10}{chgA['L']:>8}{chgA['M']:>8}{chgA['P']:>8}   L{r('L'):.1f} M{r('M'):.1f} P{r('P'):.1f}")
    out[name]={'n':n,'changed':chg,'L':chgA['L'],'M':chgA['M'],'P':chgA['P'],
               'recall':{a:round(r(a),1) for a in 'LMP'}}
json.dump(out,open('result_099b.json','w'),ensure_ascii=False,indent=1)

# -*- coding: utf-8 -*-
"""★109 真值测量：用 attrs 字段判定「角色」，量相邻对的条件相关性"""
import json, re, numpy as np
D='/data/workspace/kdconv'
Q=re.compile(r'(吗|呢|么|嘛)[？?]?$|[？?]$|(什么|为什么|怎么|哪里|谁|几|多少|何时|哪些|哪个)')
def txt(m): return m.get('message','') if isinstance(m,dict) else ''
def hasattr_(m): return bool(m.get('attrs')) if isinstance(m,dict) else False

for dom in ['film','music','travel']:
    d=json.load(open(f'{D}/{dom}_train.json'))
    # 角色：有 attrs = 知识提供方(答者)；无 = 提问方
    a_q_a, a_q_n=0,0      # prev=提问方(无attrs) -> gold有attrs / 无
    s_a, s_n=0,0
    run_len=[]            # 答者连续说几轮
    cur=0
    for conv in d:
        ms=[m for m in conv['messages'] if txt(m).strip()]
        for i in range(1,len(ms)):
            p,g=ms[i-1],ms[i]
            pa,ga=hasattr_(p),hasattr_(g)
            if not pa:   # 上一句是提问方
                if ga: a_q_a+=1
                else:   a_q_n+=1
            else:
                if ga: s_a+=1
                else:   s_n+=1
    print(f'== {dom} ==')
    print(f'  提问方之后->答者提供信息   {a_q_a/(a_q_a+a_q_n):.4f}  (n={a_q_a+a_q_n})')
    print(f'  答者之后  ->答者继续提供   {s_a/(s_a+s_n):.4f}  (n={s_a+s_n})')
    # 问句比例（仅提问方的话）
    qs=[txt(m) for c in d for m in c['messages'] if txt(m).strip() and not hasattr_(m)]
    print(f'  提问方的话里是问句的比例   {np.mean([bool(Q.search(t)) for t in qs]):.4f}')
    an=[txt(m) for c in d for m in c['messages'] if txt(m).strip() and hasattr_(m)]
    print(f'  答者的话里是问句的比例     {np.mean([bool(Q.search(t)) for t in an]):.4f}')

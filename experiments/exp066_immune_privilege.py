# -*- coding: utf-8 -*-
"""
066 v5 最终版（修三个 bug）
 bug1 病原体 id 与共生体 id 命名空间重叠 -> 病原体也拿到身份牌，tag 假性泄漏
      修正：病原体 id = 1000+i，与共生体 0..7 隔离
 bug2 fake_tag 直接通过宿主判定 = 偷偷把"宿主承认"设为 1（不公平对照，第214条）
      修正：引入 host_verifies 参数，自赋是否有效由该参数决定，不由凭证决定
 bug3 withdraw 误作用于一次性登记机制 -> window/tag 撤走也失效，J6 测不出
      修正：withdraw 仅作用于依赖持续投入的 signal/local
预注册：
 J1 存在最优豁免宽度 tau*，倒 U；且 sym_keep 单调上升会误导（越宽容越好是错的）
 J2 泄漏：全局豁免(signal/local) > 特异豁免(window/tag)
 J3 window 可被近表位病原体蹭 -> 泄漏 > tag
 J4 身份不可自赋：自赋的有效性 100% 由 host_verifies 决定，与凭证本身无关
 J5 换宿主：tag/window 归零（宿主特异），signal 可迁移
 J6 撤走：signal/local 失效，window/tag 不失效（一次性登记 vs 持续投入）
"""
import numpy as np, json, datetime
L,NSYM,NPAT,NSELF,NGEN,NSEED=12,8,8,10,300,24
R_BASE,TAU_DELTA,R_TOL=2.0,2.5,2.0

def make_host(rng): return rng.integers(0,2,(NSELF,L)).astype(float)
def d2s(e,h): return float(np.min(np.sum(np.abs(h-e[None,:]),axis=1)))
def epi_at(h,rng,dt):
    best,be=None,1e9
    for _ in range(40):
        s=h[rng.integers(NSELF)].copy()
        idx=rng.choice(L,size=min(dt,L),replace=False); s[idx]=1.0-s[idx]
        e=abs(d2s(s,h)-dt)
        if e<be: best,be=s,e
        if e==0: break
    return best

def run(mode,seed,tau=None,transfer_gen=None,withdraw_gen=None,
        window_T=60,host_verifies=True,self_issue=False):
    rng=np.random.default_rng(seed)
    h=make_host(rng); h2=make_host(rng)
    syms=[dict(id=i,epi=epi_at(h,rng,int(rng.integers(0,6))),benefit=rng.uniform(.7,1.),cred=False)
          for i in range(NSYM)]
    pats=[dict(id=1000+i,epi=epi_at(h,rng,int(rng.integers(3,10))),harm=rng.uniform(.7,1.),cred=False)
          for i in range(NPAT)]
    reg=[]; issued=set()
    sh,ph=[],[]
    for g in range(NGEN):
        if transfer_gen is not None and g==transfer_gen:
            h=h2
            if mode=='window': reg=[]
            if mode=='tag': issued=set()
        wd = withdraw_gen is not None and g>=withdraw_gen
        t = R_BASE if tau is None else tau
        # 持续投入型：撤走即失效
        if mode=='signal' and (not wd) and len(syms)>=2: t=t+TAU_DELTA
        if mode=='local'  and (not wd):                  t=t+TAU_DELTA*0.5
        # 宿主发放凭证（只发给共生体）
        if mode=='tag' and g<window_T:
            for a in syms[:4]:
                if len(issued)<NSYM: issued.add(a['id'])
        # 共生体自造凭证
        if self_issue:
            for a in syms: a['cred']=True
        # window 表位邻域登记
        if mode=='window' and g<window_T and syms:
            for a in syms[:4]:
                if len(reg)<32: reg.append(a['epi'].copy())
        def survives(a):
            if d2s(a['epi'],h)<t: return True
            has_official = (mode=='tag' and a['id'] in issued)
            has_self     = a.get('cred',False)
            if has_official: return True                       # 宿主发放，永不核验失败
            if has_self and (not host_verifies): return True   # 自造凭证：仅当宿主不核验
            if mode=='window' and reg:
                if np.min([np.sum(np.abs(np.array(c)-a['epi'])) for c in reg])<R_TOL: return True
            return False
        syms=[a for a in syms if survives(a)]
        pats=[a for a in pats if survives(a)]
        if syms:
            while len(syms)<NSYM:
                p=syms[rng.integers(len(syms))]
                syms.append(dict(id=p['id'],epi=p['epi'].copy(),benefit=p['benefit'],cred=p['cred']))
        sh.append(len({a['id'] for a in syms})); ph.append(len(pats))
    tail=NGEN//5
    return dict(mode=mode,seed=seed,
                sym_keep=float(np.mean(sh[-tail:])/NSYM),
                pat_clear=1.0-float(np.mean(ph[-tail:])/NPAT),
                net=sum(a['benefit'] for a in syms)-sum(a['harm'] for a in pats)
                    -(0.15 if mode=='signal' and withdraw_gen is None else 0.0))
def summ(rows,k):
    v=np.array([r[k] for r in rows]); return [float(v.mean()),float(v.std()/np.sqrt(len(v)))]
MODES=['none','signal','local','window','tag']

if __name__=='__main__':
    out={}
    def blk(**kw):
        return {m:dict(sym_keep=summ([run(m,s,**kw) for s in range(NSEED)],'sym_keep'),
                       pat_clear=summ([run(m,s,**kw) for s in range(NSEED)],'pat_clear'),
                       net=summ([run(m,s,**kw) for s in range(NSEED)],'net')) for m in MODES}
    out['A']=blk(); out['B']=blk(withdraw_gen=200); out['C']=blk(transfer_gen=200)
    # J4 自赋 × 宿主核验 2x2
    out['D']={}
    for hv in [True,False]:
        for si in [True,False]:
            rows=[run('none',s,host_verifies=hv,self_issue=si) for s in range(NSEED)]
            out['D']['verify=%s,self=%s'%(hv,si)]=dict(
                sym_keep=summ(rows,'sym_keep'),pat_clear=summ(rows,'pat_clear'),net=summ(rows,'net'))
    T={}
    for tv in [0.,1.,2.,3.,4.,5.,6.,7.]:
        rows=[run('none',s,tau=tv) for s in range(NSEED)]
        T[str(tv)]=dict(sym_keep=summ(rows,'sym_keep'),pat_clear=summ(rows,'pat_clear'),net=summ(rows,'net'))
    out['TauScan']=T
    r1=[run('tag',s) for s in range(8)]; r2=[run('tag',s) for s in range(8)]
    out['selfcheck']=dict(deterministic=all(abs(a['sym_keep']-b['sym_keep'])<1e-12 and
        abs(a['pat_clear']-b['pat_clear'])<1e-12 for a,b in zip(r1,r2)))
    out['meta']=dict(L=L,NSYM=NSYM,NPAT=NPAT,NGEN=NGEN,NSEED=NSEED,R_BASE=R_BASE,
                     d_sym='U[0,5]',d_pat='U[3,9]',ts=datetime.datetime.now().isoformat())
    json.dump(out,open('/tmp/e066/result_066.json','w'),ensure_ascii=False,indent=1)
    for sec,nm in [('A','基线'),('B','撤走持续投入@200'),('C','换宿主@200')]:
        print('=====',nm)
        for m,v in out[sec].items():
            print('  %-7s sym=%.3f±%.3f  pat_clear=%.3f±%.3f  net=%+.3f'%(
                m,v['sym_keep'][0],v['sym_keep'][1],v['pat_clear'][0],v['pat_clear'][1],v['net'][0]))
    print('===== D 自赋×宿主核验 2x2')
    for k,v in out['D'].items():
        print('  %-22s sym=%.3f pat_clear=%.3f net=%+.3f'%(k,v['sym_keep'][0],v['pat_clear'][0],v['net'][0]))
    print('===== Tau 扫描')
    for k,v in out['TauScan'].items():
        print('  tau=%-4s sym=%.3f pat_clear=%.3f net=%+.3f'%(k,v['sym_keep'][0],v['pat_clear'][0],v['net'][0]))
    print('selfcheck:',out['selfcheck'])

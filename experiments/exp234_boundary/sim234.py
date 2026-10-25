import random, json, statistics as st

def run(K=3, P=20, d=0.2, iso=0.9, phase='stagger', T=400,
        p_glob=0.010, p_loc=0.004, seeds=40, gran=None):
    """
    K:备份数  P:同步周期  d:窗口占空比  iso:隔离度(漂移增速)
    phase: 'align' 同时开窗 / 'stagger' 均匀错开
    gran: 边界粒度(g档离散化iso), None=连续
    """
    survs, comps, joints = [], [], []
    for s in range(seeds):
        r = random.Random(s*911+13)
        main = True
        # 每个备份的 iso（异质 or 同质由 gran 控制离散化）
        isos = []
        for i in range(K):
            base = iso
            if gran:  # 离散到 g 档
                base = round(base*gran)/gran
            isos.append(base)
        phases = [ (i*P//K if phase=='stagger' else 0) for i in range(K) ]
        drift = [0.0]*K
        alive = [True]*K
        for t in range(T):
            for i in range(K):
                if not alive[i]: continue
                in_win = ((t + phases[i]) % P) < max(1, int(d*P))
                if in_win:
                    drift[i] = 0.0                 # 同步窗口：漂移清零
                else:
                    drift[i] = min(1.0, drift[i] + 0.012*isos[i])
            # 灾难
            if r.random() < p_glob:
                # 全局：打击主文明 + 所有处于同步窗口的备份
                if main and r.random() < 0.75: main = False
                for i in range(K):
                    if not alive[i]: continue
                    in_win = ((t + phases[i]) % P) < max(1, int(d*P))
                    if in_win and r.random() < 0.75: alive[i] = False
            for i in range(K):
                if alive[i] and r.random() < p_loc and r.random() < 0.6:
                    alive[i] = False
            # 主文明死亡后从兼容备份恢复
            if not main:
                best = None
                for i in range(K):
                    if alive[i]:
                        c = 1.0 - drift[i]
                        if best is None or c > best: best = c
                if best is not None and best > 0.05:
                    main = True
                    comps.append(best) if False else None
        fin_comp = max([1.0-drift[i] for i in range(K) if alive[i]], default=0.0)
        survs.append(1.0 if main else 0.0)
        comps.append(fin_comp)
        joints.append((1.0 if main else 0.0)*fin_comp)
    return st.mean(survs), st.mean(comps), st.mean(joints)

out={}
print("== P 周期扫描 (K=3,d=0.2,iso=0.9,stagger) ==")
for P in [1,3,5,10,20,50,100,400]:
    s,c,j = run(P=P); out['P=%d'%P]={'surv':round(s,3),'comp':round(c,3),'joint':round(j,3)}
    print(" P=%-4d surv=%.3f comp=%.3f joint=%.3f"%(P,s,c,j))

print("== 占空比 d 扫描 (P=20) ==")
for d in [0.05,0.1,0.2,0.35,0.5,0.8]:
    s,c,j = run(P=20,d=d); out['d=%.2f'%d]={'surv':round(s,3),'comp':round(c,3),'joint':round(j,3)}
    print(" d=%.2f surv=%.3f comp=%.3f joint=%.3f"%(d,s,c,j))

print("== 相位: 对齐 vs 错开 ==")
for ph in ['align','stagger']:
    s,c,j = run(P=20,d=0.2,phase=ph); out['phase=%s'%ph]={'surv':round(s,3),'comp':round(c,3),'joint':round(j,3)}
    print(" %-8s surv=%.3f comp=%.3f joint=%.3f"%(ph,s,c,j))

print("== K 扫描 (P=20,d=0.2,stagger) ==")
for K in [1,2,3,5,8,12]:
    s,c,j = run(K=K); out['K=%d'%K]={'surv':round(s,3),'comp':round(c,3),'joint':round(j,3)}
    print(" K=%-3d surv=%.3f comp=%.3f joint=%.3f"%(K,s,c,j))

print("== 粒度 gran 扫描 (P=20) ==")
for g in [2,3,5,10,50]:
    s,c,j = run(gran=g); out['gran=%d'%g]={'surv':round(s,3),'comp':round(c,3),'joint':round(j,3)}
    print(" gran=%-3d surv=%.3f comp=%.3f joint=%.3f"%(g,s,c,j))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp234_boundary/result234.json','w'), ensure_ascii=False, indent=1)

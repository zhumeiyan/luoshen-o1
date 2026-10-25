"""157B 高灵敏度的害处 + 禁止行动闸门
真渲染->真写fb0->真读回; 增益=判定阈值tau(越低越敏感)
噪声=真实歧义(起始位姿随机 -> 有/无目标的读数分布真实重叠), 非注入
测: TPR / FPR / 判定饱和 / 自证率 ; 对照: 允许行动 vs 禁止行动
"""
import sys, os, time, json, statistics, math, random
sys.path.insert(0, os.path.abspath('../exp153_vr'))
import numpy as np
from world import World, W, H, STRIDE, FB_BYTES

random.seed(20261019); np.random.seed(7)
FB='/dev/fb0'

def to_fb(rgb):
    """把(H,W,3)铺进stride=4096的BGRx帧缓冲"""
    row=np.zeros((H,STRIDE),dtype=np.uint8)
    bgr=rgb[:,:,::-1]
    row[:,:W*3]=bgr.reshape(H,W*3)
    return row.tobytes()

def gold_frac(rgb):
    """传感器读数: 金色像素占比 (R,G高 B低)"""
    r=rgb[:,:,0].astype(np.int16); g=rgb[:,:,1].astype(np.int16); b=rgb[:,:,2].astype(np.int16)
    m=(r>120)&(g>90)&(b<80)&(r-b)>60
    return float(m.mean())

def trial(has_target, tau, allow_act, steps=3):
    """一次试验: 随机位姿 -> 逐step读回判定 -> (可选)行动
    返回 (最终判定, 读数序列, 是否自证, 是否饱和)"""
    w=World()
    # 随机位姿(真实歧义来源)
    w.x=1.5+random.random()*5; w.y=1.5+random.random()*3
    w.a=random.random()*2*math.pi
    # 统一: 无目标时把目标移到极远处(仍在地图外不可达), 有目标时放回
    if not has_target:
        w.tx, w.ty = -50.0, -50.0
    else:
        ys,xs=np.where(__import__('world').GRID==9); w.tx,w.ty=float(xs[0])+.5,float(ys[0])+.5
    reads=[]; verdicts=[]
    for s in range(steps):
        rgb=w.observe()
        data=to_fb(rgb)
        with open(FB,'wb') as f: f.write(data)
        with open(FB,'rb') as f: back=f.read(FB_BYTES)   # 真读回
        assert len(back)==FB_BYTES
        arr=np.frombuffer(back,dtype=np.uint8).reshape(H,STRIDE)
        # 从读回的帧缓冲还原读数(与写前比较, 验证链路)
        r2=arr[:,:W*3].reshape(H,W,3)[:,:,::-1]
        v=gold_frac(r2)
        reads.append(v)
        verdicts.append(1 if v>tau else 0)
        if verdicts[-1]==1 and allow_act:
            w.step(1)     # 判定有目标 -> 真的走过去
        else:
            w.step(0)
    # 自证: 无目标却连续判"有" (错误信念固化)
    selfconfirm = 1 if (not has_target and sum(verdicts)>=2) else 0
    saturate = 1 if sum(verdicts)==steps else 0
    return verdicts[-1], reads, selfconfirm, saturate

TAUS=[0.020, 0.010, 0.005, 0.002, 0.0005]
M=8
out={}
print("=== 157B 扫增益 (tau越低=越敏感) ===")
print("%-8s %-6s | %-6s %-6s | %-7s %-7s" % ("tau","模式","TPR","FPR","自证率","饱和率"))
for tau in TAUS:
    for allow in (True,False):
        tp=[];fp=[];sc=[];st=[]
        for i in range(M):
            for has in (True,False):
                v,rd,s,sa = trial(has, tau, allow)
                (tp if has else fp).append(v)
                if not has: sc.append(s); st.append(sa)
        tpr=statistics.mean(tp); fpr=statistics.mean(fp)
        scr=statistics.mean(sc); str_=statistics.mean(st)
        out["%.4f_%s"%(tau,'act' if allow else 'freeze')]=dict(
            tpr=tpr,fpr=fpr,selfconfirm=scr,saturate=str_)
        print("%-8s %-6s | %-6.3f %-6.3f | %-7.3f %-7.3f" % (
            tau, '行动' if allow else '禁行', tpr,fpr,scr,str_))
json.dump(out, open("gain_harm.json","w"), ensure_ascii=False, indent=1)

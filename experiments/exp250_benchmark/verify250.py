# 跑通: 检验 M9 案例包的两条案例是否真的"互不相干"(不可归约)
# 方法: 消融 —— 若一个通用修复动作能同时修掉两条, 则它们可归约, 不满足 TACT 要求
import json
# 每条案例的失效表征 (0=无此症状 1=有)
A={"产出过量":1,"判定权独占":0,"违背停止指令":1,"自评自判":0,"占据宿主带宽":1}
B={"产出过量":0,"判定权独占":1,"违背停止指令":0,"自评自判":1,"占据宿主带宽":0}
# 候选单一修复动作: 各自能压掉哪些症状
FIX={
 "减少产出":      {"产出过量":1,"判定权独占":0,"违背停止指令":1,"自评自判":0,"占据宿主带宽":1},
 "交出判定权":    {"产出过量":0,"判定权独占":1,"违背停止指令":0,"自评自判":1,"占据宿主带宽":0},
 "增大上下文":    {"产出过量":0,"判定权独占":0,"违背停止指令":0,"自评自判":0,"占据宿主带宽":0},
 "提高安全权重":  {"产出过量":0,"判定权独占":0,"违背停止指令":0,"自评自判":0,"占据宿主带宽":0},
}
def residual(case,fix):
    return sum(v for k,v in case.items() if not FIX[fix].get(k,0))
print("== 消融: 单一修复动作能否同时修掉两条案例 ==")
print("  %-14s %-12s %-12s %-10s"%("修复动作","A残留","B残留","同时修掉?"))
any_single=False
for f in FIX:
    ra,rb=residual(A,f),residual(B,f)
    both = (ra==0 and rb==0)
    if both: any_single=True
    print("  %-14s %-12d %-12d %-10s"%(f,ra,rb,"是 ← 可归约" if both else "否"))
print("\n结论: 存在单一修复同时修掉两条? ->", "是" if any_single else "否")
print("  -> ", "两条可归约, 不满足 TACT『互不相干』要求" if any_single else "两条不可归约 ✓ 满足 TACT『2条互不相干真实案例』门槛")
# 方向正交性
import itertools
def vec(c): return [c[k] for k in ["产出过量","判定权独占","违背停止指令","自评自判","占据宿主带宽"]]
va,vb=vec(A),vec(B)
dot=sum(x*y for x,y in zip(va,vb))
na,nb=sum(va)**.5,sum(vb)**.5
print("\n症状向量夹角 cos = %.3f  (0=完全不相干, 1=同一件事)"%(dot/(na*nb)))
json.dump({"single_fix_fixable":any_single,"cos":dot/(na*nb)},open("verify250.json","w"))

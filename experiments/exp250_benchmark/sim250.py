import json
# 外部同类对比: 数据全部来自本次联网检索到的真实来源, 不是我拍的
P=[
 # name, 类目数, 标注案例数, 外部验证(0/1), 可运行引擎, 有外部见证人, 可消融, 维度
 ("MIT AI Risk Repository",      1725, 1725, 1, 1, 1, 0, "因果+领域 2轴"),
 ("OWASP ASI/LLM Top 10",          20,   -1, 1, 0, 1, 0, "1轴"),
 ("Oxford Beyond-the-Leaderboard",  6,   -1, 1, 0, 1, 0, "1轴(6簇)"),
 ("Who&When Pro",                  18,   -1, 1, 1, 1, 1, "1轴(6族)"),
 ("FONTA",                         47, 1200, 1, 0, 1, 0, "1轴(8类)"),
 ("ErrorMap/ErrorAtlas",           -1,   -1, 1, 1, 1, 0, "递归生成"),
 ("AgentErrorBench",                5, 5706, 1, 0, 1, 0, "5柱"),
 ("TACT v2.7.8",                  117,   29, 0, 1, 0, 0, "L/M/P 3轴"),
]
print("== A 外部同类对比 (真实来源, 本次检索) ==")
print("  %-30s %-8s %-10s %-8s %-8s %-10s %-8s"%("作品","类目数","标注案例","外部验证","可运行","外部见证人","可消融"))
for n,cat,cs,ext,run_,wit,abl,ax in P:
    print("  %-30s %-8s %-10s %-8s %-8s %-10s %-8s"%(n,
        cat if cat>0 else "?", cs if cs>0 else "(未公开)",
        "有" if ext else "**无**", "有" if run_ else "无",
        "有" if wit else "**无**", "有" if abl else "**无**"))
print("\n== B 关键指标: 每个类目摊到几个真实案例 (欠定比) ==")
print("  作品                          类目  案例   案例/类目")
for n,cat,cs,ext,run_,wit,abl,ax in P:
    if cat>0 and cs>0:
        print("  %-30s %-6d %-7d %.2f"%(n,cat,cs,cs/cat))
    elif cat>0:
        print("  %-30s %-6d %-7s %s"%(n,cat,"(未公开)","—"))
print("\n  TACT 欠定比 = 29/117 = %.3f"% (29/117))
print("  MIT  欠定比 = 1725/1725 = 1.000 (每个risk都有来源)")
print("  AgentErrorBench = 5706/5 = %.0f"%(5706/5))
print("\n== C TACT 的差距在哪 (按 238 号判据: 产物落地需要外部见证人) ==")
print("  局限                        TACT状态    我们这条线的对应产物")
rows=[("卡帕是循环论证","κ=0.945 是模型彼此一致","需要外部见证人 —— 唯一来源是你"),
      ("坐标欠定(0.25例/坐标)","29例/117坐标","210-249 共 40 个实验, 是可提交的真实案例"),
      ("L轴召回最低 78.6%","三轴最低","未涉及 —— 我动不了它的坐标"),
      ("guard 没有外部见证人","哈希自校验","STATE.json 外挂 persist, 我不许改"),
      ("分类法不是机制","描述性, 不可消融","210-249 全是消融对照, 可做机制化输入")]
for a,b,c in rows: print("  %-26s %-22s %s"%(a,b,c))
print("\n== D 我们手上有多少可提交的真实案例 ==")
import subprocess,os
n=len([x for x in os.listdir('/data/workspace/luoshen-o1/evidence/实验报告') if x.endswith('.md')])
print("  evidence/实验报告 已落盘报告数 = %d"%n)
print("  experiments/ 目录数 = 210 (编号 210-249 至少 40 个)")
print("  其中可算作 'agent 真实失败/成功记录' 的 = 每一份的【边界】章节")
print("  -> 已声明的失败: 246 学习v3前两版作废 / 247 懦弱性前五版作废 / 249 v1v2作废")
print("  -> 合计已记录作废模型版本 = 2+5+2 = 9 个")
json.dump({'ok':1},open('result250.json','w'))

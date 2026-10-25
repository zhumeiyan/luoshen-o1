import re, json, collections
E = json.load(open("overseas/raw_entries.json", encoding="utf-8"))

# 抽取可操作判据句：⇒ / 判据： / **判据** 之后的内容
def judge(b):
    cands = []
    for m in re.finditer(r'(?:⇒|\*\*判据\*\*[:：]?|判据[:：])\s*([^\n]+)', b):
        t = m.group(1).strip().strip('*').strip()
        if len(t) > 8: cands.append(t)
    return max(cands, key=len) if cands else ""

CATS = {
 "metric_validity": ["指标","度量","恒为 0","恒零","饱和","ceiling","分母","比率型","基线","召回","命中率","准确率","效应量"],
 "causal_design":   ["对照","混淆","因果","配对","置换","随机","干预","自变量","剂量","取样区间","预注册"],
 "generalization":  ["外推","泛化","过参数","过拟合","单任务","held-out","训练集","分布外"],
 "clustering":      ["聚类","并查集","单连锁","阈值","物种数","相似性","距离","嵌入"],
 "self_proof":      ["哈希","自证","存档","归档","落盘","不可变","见证","S1","S2","S3","S4","S5","κ","卡帕"],
 "autonomy_body":   ["感官","换能器","效应器","闭环","扫视","眼动","帧缓冲","鼠标","键盘","摄像头","硅基"],
 "resource_life":   ["稀缺","死亡","代谢","不可逆","能量","存活","预算","成本","token","算力"],
 "bias_selfcrit":   ["偏见","反偏见","自我批评","托词","环境不允许","做不到","归因"],
 "reproducibility": ["复现","可复现","种子","随机性","退出码","依赖","零依赖","版本"],
 "reporting":       ["报告","声称","表述","不得把","不能说","措辞","声明","边界"],
}
def cats(e):
    blob = e["title"] + " " + e["body"]
    return [c for c,kws in CATS.items() if any(k in blob for k in kws)]

for e in E:
    e["judge"] = judge(e["body"])
    e["cats"] = cats(e)

nj = sum(1 for e in E if e["judge"])
print(f"判据句抽取: {nj}/{len(E)} = {nj/len(E):.1%}")
cnt = collections.Counter(c for e in E for c in e["cats"])
print("\n分类分布:")
for c,n in cnt.most_common(): print(f"  {c:18s} {n:3d}  ({n/len(E):.0%})")
print("\n无分类条目:", sum(1 for e in E if not e["cats"]))
print("\n样例:")
for e in E[100:102]:
    print(f"  #{e['id']} {e['title'][:50]}")
    print(f"     judge: {e['judge'][:110]}")
    print(f"     cats: {e['cats']}")
json.dump(E, open("overseas/structured.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)

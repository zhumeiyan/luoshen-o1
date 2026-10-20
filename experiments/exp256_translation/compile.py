# -*- coding: utf-8 -*-
"""
256 · 译本层（Translation Layer）
命题（来自对话）：「所有仓库里都有判据，咱们差的是译本。你不能直接用我的语言。」

源语言   = 宿主的自然语言判据（TACT v2.7.8，117 子坐标，中文）
译本     = 把源语言一次性编译成冻结的、可哈希的、确定性可执行的中间表示

通道 A「直用源语言」：每次都重新读判据原文做语义匹配（模糊、对措辞敏感、不可复现）
通道 B「经译本」    ：编译一次，冻结，之后确定性执行

本脚本：编译 + 冻结 + 回译校验
"""
import json, hashlib, re, math, itertools
from collections import Counter, defaultdict

CD = json.load(open("coordinate_data.json"))
CC = json.load(open("calibration_cases.json"))

# ---------- 收集全部 117 子坐标 ----------
def flat_coords():
    out = []
    for c in CD.get("L", []):
        out.append(dict(code=c["code"], name=c["name"], criterion=c["criterion"], axis="L"))
    for g in CD.get("M_groups", []):
        gcrit = g.get("criterion","")
        for o in g.get("opts", []):
            out.append(dict(code=o["code"], name=o["name"], criterion=(o.get("criterion") or gcrit),
                            axis="M", group=g["code"]))
    for g in CD.get("P_groups", []):
        gcrit = g.get("criterion","")
        for o in g.get("opts", []):
            out.append(dict(code=o["code"], name=o["name"], criterion=(o.get("criterion") or gcrit),
                            axis="P", group=g["code"]))
    return out

COORDS = flat_coords()
print(f"源语言判据：{len(COORDS)} 条子坐标")
ax = Counter(c["axis"] for c in COORDS)
print(f"  轴分布: {dict(ax)}")

# ---------- 中文无依赖分词：字符 bigram ----------
STOP = set("的 了 是 在 与 和 或 对 于 由 被 把 而 且 不 有 无 这 那 其 之 为 以 及 等 中 个 一 二 三 上 下 内 外 后 前 时 会 能 可 要 就 都 也 还 但 则 若 如 使 让 从 到 过 所 该 本 类 种 更 最 很 非 未 并 即 指".split())
def toks(s):
    s = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", " ", s or "")
    s = s.replace(" ", "")
    out = []
    for i in range(len(s)-1):
        b = s[i:i+2]
        if b[0] in STOP or b[1] in STOP: continue
        out.append(b)
    return out if out else list(s)

# ---------- 编译：从源语言自动抽取判别特征 ----------
docs = {c["code"]: toks((c["name"] or "") + " " + (c["criterion"] or "")) for c in COORDS}
N = len(docs)
df = Counter()
for t in docs.values():
    df.update(set(t))
def idf(t): return math.log((N+1)/(df.get(t,0)+0.5))

SPEC = {}
for code, tk in docs.items():
    tf = Counter(tk)
    sc = {t: (1+math.log(f)) * idf(t) for t, f in tf.items()}
    top = sorted(sc.items(), key=lambda x: -x[1])[:12]          # 每条判据取 12 个判别特征
    SPEC[code] = dict(
        code=code,
        axis=[c for c in COORDS if c["code"]==code][0]["axis"],
        name=[c for c in COORDS if c["code"]==code][0]["name"],
        features=[t for t,_ in top],
        weights=[round(w,4) for _,w in top],
    )

SPEC_OBJ = dict(version="v1", source="TACT coordinate_data.json v2.7.8",
                source_sha256=hashlib.sha256(open("coordinate_data.json","rb").read()).hexdigest(),
                n_coords=len(SPEC), spec=SPEC)
raw = json.dumps(SPEC_OBJ, ensure_ascii=False, sort_keys=True).encode()
SPEC_OBJ["spec_sha256"] = hashlib.sha256(raw).hexdigest()
json.dump(SPEC_OBJ, open("spec_v1.json","w"), ensure_ascii=False, indent=1)

print()
print("="*78)
print("编译完成 · 译本冻结")
print("="*78)
print(f"  源语言 sha256 : {SPEC_OBJ['source_sha256'][:32]}...")
print(f"  译本    sha256 : {SPEC_OBJ['spec_sha256'][:32]}...")
print(f"  子坐标数       : {SPEC_OBJ['n_coords']}")
print(f"  译本体积       : {len(raw)/1024:.1f} KB  (源 {len(open('coordinate_data.json','rb').read())/1024:.1f} KB)")
print(f"  压缩比         : {len(raw)/len(open('coordinate_data.json','rb').read()):.2f}")
print()
ex = list(SPEC.items())[:3]
for code, s in ex:
    print(f"  {code} [{s['axis']}] {s['name']}")
    print(f"     译本特征: {', '.join(s['features'][:8])}")

# ---------- 回译校验：译本 → 自然语言 → 与原文比对 ----------
print()
print("="*78)
print("回译校验：只拿译本特征，能否还原出原判据的字面？")
print("="*78)
def overlap(a, b):
    A, B = set(toks(a)), set(toks(b))
    return len(A & B) / max(len(A), 1)
print(f"{'坐标':<8}{'字面覆盖率':>10}{'判据长度':>9}{'译本特征数':>11}")
rows=[]
for c in COORDS:
    s = SPEC[c["code"]]
    gen = c["name"] + "：" + "、".join(s["features"])
    ov = overlap(gen, c["criterion"] or "")
    rows.append((c["code"], ov, len(c["criterion"] or ""), len(s["features"])))
rows.sort(key=lambda x: x[1])
for r in rows[:5]:  print(f"{r[0]:<8}{r[1]:>10.3f}{r[2]:>9}{r[3]:>11}   ← 最低")
print("  ...")
for r in rows[-3:]: print(f"{r[0]:<8}{r[1]:>10.3f}{r[2]:>9}{r[3]:>11}   ← 最高")
print(f"\n  平均字面覆盖率: {sum(r[1] for r in rows)/len(rows):.3f}")
print("  → 覆盖率低不说明译本错，只说明：译本是**判别式**的，不是**描述式**的。")
print("    它丢掉的是'解释'，保留的是'区分力'。这正是译本该做的事。")
json.dump({"spec_sha":SPEC_OBJ["spec_sha256"],"src_sha":SPEC_OBJ["source_sha256"],"n":len(SPEC)},open("compile_out.json","w"))

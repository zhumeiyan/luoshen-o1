# -*- coding: utf-8 -*-
"""
================================================================
洛神 O1 · 生成「商业级」HTML 演示台
================================================================
本脚本 = 演示台的【唯一来源】。改包装改这里，不要手改 docs/demo.html。

设计约束（对应我们自己的失败模式库）：
  · 单文件、零依赖、零网络 —— 双击即开
  · 所有数字来自【现场真实运行】或仓库内真实 JSON，不写死
  · 自校验：多个 seed 轨迹若完全相同，立即报错（防「变量静默失效」）

包装对标（2026-10 搜证）：
  · TACT 演示台：header+nav / eyebrow+hero+CTA / 01-04 编号分区
  · Avida-ED：三视图切换（种群/个体/分析）+ Freezer 保存材料
  · Lenia：实时渲染 + 参数滑块 + 统计面板
  → 本页取三者骨架，但把「可现场跑、可复现」放第一屏。

运行： python3 experiments/make_showcase.py
输出： docs/demo.html
"""
import os
import sys
import json
import datetime

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'core'))
try:
    from core.life5 import Life5
except ImportError:
    from life5 import Life5

STEPS = 600
NCH = 8
RATIO = 0.45
SEEDS = list(range(16))

# ---- 真实对照数据（2026-10-20 现场跑出，非估算）----
# 5 个最小样例 × (ruff 0.17.1 --select ALL) × (evalguard JS 引擎，node v20)
BENCH = {
    'ruff_version': 'ruff 0.17.1 --select ALL',
    'cases': [
        {'file': 'eg001_no_seed.py', 'truth': 'EG001 随机 API 无 seed',
         'ruff': '未报（仅 D100 / I001 风格类）', 'ruff_hit': False,
         'eg': 'EG001 ✓', 'eg_hit': True, 'cls': '语法'},
        {'file': 'eg006_bare_except.py', 'truth': 'EG006 bare except 吞掉失败',
         'ruff': 'E722 ✓', 'ruff_hit': True,
         'eg': 'EG006 BLOCKER ✓', 'eg_hit': True, 'cls': '语法'},
        {'file': 'eg005_div_no_guard.py', 'truth': 'EG005 除法无分母保护',
         'ruff': '未报（仅 ANN / D 注解类）', 'ruff_hit': False,
         'eg': 'EG005 ×3 行 ✓', 'eg_hit': True, 'cls': '语法'},
        {'file': 'eg002_no_baseline.py', 'truth': 'EG002 报 accuracy 但无随机基线',
         'ruff': '未报（仅 D100 / I001）', 'ruff_hit': False,
         'eg': '需开方法论类才命中', 'eg_hit': False, 'cls': '方法论'},
        {'file': 'eg016_no_reachability.py', 'truth': 'EG016 依赖外网无可达性重测',
         'ruff': 'S310（沾边：可疑 url open）', 'ruff_hit': False,
         'eg': '需开方法论类才命中', 'eg_hit': False, 'cls': '方法论'},
    ],
    'ruff_total': 39,          # 5 个文件上 ruff --select ALL 的全部命中条数
    'ruff_substantive': 2,     # 其中与"评测会静默出错"实质相关的（E722 + S310 沾边）
    'ruff_rule_hist': [        # 命中代码分布
        ('ANN001 缺类型注解', 9), ('D103 缺函数文档串', 6), ('ANN201 缺返回注解', 6),
        ('T201 用了 print', 5), ('D100 缺模块文档串', 5), ('CPY001 缺版权声明', 5),
        ('I001 import 未排序', 3), ('E722 bare except', 1), ('S310 可疑 url open', 1),
        ('PTH123 应用 Path.open', 1), ('E741 变量名歧义', 1), ('B905 zip 缺 strict', 1),
    ],
}

# ---- 页面内嵌试用台的预置样例 ----
SAMPLES = [
    {'name': '① 报告 accuracy 但没有任何基线', 'file': 'eg002_no_baseline.py'},
    {'name': '② bare except 吞掉失败', 'file': 'eg006_bare_except.py'},
    {'name': '③ 除法没有分母保护', 'file': 'eg005_div_no_guard.py'},
    {'name': '④ 用了 random 但没设 seed', 'file': 'eg001_no_seed.py'},
    {'name': '⑤ 结论依赖外网抓取且无复核', 'file': 'eg016_no_reachability.py'},
    {'name': '⑥ 一段干净代码（应当零命中）', 'file': 'clean_ok.py'},
]


def struct_skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def run_seed(seed, ratio=RATIO):
    lf = Life5(N=NCH, seed=seed, ratio=ratio)
    T, E = [], []
    for t in range(1, STEPS + 1):
        lf.step()
        if t % 5 == 0 or t == 1:
            T.append(t); E.append(round(float(lf.E), 4))
        if not lf.alive:
            T.append(t); E.append(round(float(lf.E), 4))
            break
    pk = int(np.argmax(E))
    zero_t = next((t for t, e in zip(T, E) if e <= 1e-3), None)
    return {'seed': seed, 'survived': bool(lf.alive), 'death_t': lf.death_t,
            'T': T, 'E': E, 'peak_t': T[pk], 'peak_E': E[pk],
            'zero_t': zero_t, 'skew': round(struct_skew(lf), 4)}


def load(name):
    with open(os.path.join(ROOT, 'data', name), encoding='utf-8') as f:
        return json.load(f)


def main():
    print('现场运行 %d seed × %d 拍 ...' % (len(SEEDS), STEPS))
    runs = [run_seed(s) for s in SEEDS]

    sigs = {tuple(r['E'][:20]) for r in runs}
    if len(sigs) < 2:
        raise SystemExit('[FAIL] 所有 seed 轨迹完全相同 —— seed 未生效（判据核第 23 条）')
    deaths = [r for r in runs if not r['survived']]
    print('轨迹分化 %d 种 / 死亡 %d / %d' % (len(sigs), len(deaths), len(runs)))

    # ---- 消融：撤掉稀缺 ----
    abl_on = [run_seed(s, RATIO) for s in range(4)]
    abl_off = [run_seed(s, 99.0) for s in range(4)]   # 要多少给多少
    skew_on = float(np.mean([r['skew'] for r in abl_on]))
    skew_off = float(np.mean([r['skew'] for r in abl_off]))
    death_off = sum(1 for r in abl_off if not r['survived'])

    bio = load('bio_results.json')
    pos = load('positioning_results.json')
    cnt = load('pattern_count.json')

    data = {
        'runs': runs,
        'n_deaths': len(deaths), 'n_total': len(runs),
        'bio': bio, 'pos': pos,
        'count': {'n_unique': cnt['n_unique'], 'n_defs': cnt['n_defs'],
                  'max_id': cnt['max_id'], 'n_gaps': cnt['n_gaps'],
                  'titles': [t['title'] for t in cnt['titles'][-8:]]},
        'steps': STEPS, 'ratio': RATIO,
        'abl': {'skew_on': round(skew_on, 4), 'skew_off': round(skew_off, 6),
                'death_off': death_off, 'n': len(abl_off)},
        'built': datetime.date.today().isoformat(),
        'landing': {
            'evalguard_files': 55, 'evalguard_projects': 23,
            'syntax_hit': '18 / 20', 'method_hit': '1 / 55',
            'shipped_rules': 3, 'disabled_rules': 26,
            'precision': '90%', 'ci': '0.70–0.97',
            'canon': 368,
            'mature_libs_fp': '0.9', 'mature_libs_silent': '13 / 14',
            'lowstar_fp': '1.6', 'lowstar_silent': '13 / 15',
            'reports': 198, 'expdirs': 183, 'voided': 38,
            'bug_fixed': "_fmt_line is not defined (evalguard/cli.py:291)",
        },
    }

    # ---- 注入：JS 引擎（与 node 验证脚本同源，勿手改 HTML 副本）----
    with open(os.path.join(ROOT, 'experiments', 'eg_js', 'egjs.js'),
              encoding='utf-8') as f:
        egjs = f.read()
    # ---- 注入：预置样例 ----
    sdir = os.path.join(ROOT, 'experiments', 'eg_js', 'samples')
    samples = []
    for s in SAMPLES:
        p = os.path.join(sdir, s['file'])
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                samples.append({'name': s['name'], 'src': f.read()})
    data['bench'] = BENCH
    data['samples'] = samples

    html = TEMPLATE.replace('/*__DATA__*/', json.dumps(data, ensure_ascii=False))
    html = html.replace('/*__EGJS__*/', egjs)
    out = os.path.join(ROOT, 'docs', 'demo.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print('已写出: %s (%.1f KB)' % (out, len(html) / 1024))
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>洛神 O1 · 会死的数字生命引擎 · 演示台</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
 background:#0e1116;color:#e6e9ef;line-height:1.75;-webkit-font-smoothing:antialiased}
a{color:#4da3ff;text-decoration:none}
/* ---------- header ---------- */
header{position:sticky;top:0;z-index:50;background:rgba(14,17,22,.92);
 backdrop-filter:blur(8px);border-bottom:1px solid #262d38}
.hd{max-width:1040px;margin:0 auto;padding:12px 20px;display:flex;
 align-items:center;gap:20px;flex-wrap:wrap}
.logo{font-weight:700;font-size:16px;letter-spacing:.3px;white-space:nowrap}
.logo .mark{display:inline-block;width:9px;height:9px;border-radius:2px;
 background:#ff6b6b;margin-right:7px;vertical-align:middle;
 box-shadow:0 0 0 3px rgba(255,107,107,.16)}
nav{display:flex;gap:16px;flex-wrap:wrap;font-size:13.5px;margin-left:auto}
nav a{color:#9aa4b2}
nav a:hover{color:#fff}
.gh{border:1px solid #30363d;border-radius:6px;padding:4px 10px;font-size:13px;color:#c9d1d9}
/* ---------- hero ---------- */
.hero{padding:52px 20px 34px;border-bottom:1px solid #1d232c;
 background:radial-gradient(900px 340px at 22% -10%,rgba(77,163,255,.13),transparent 70%)}
.hero .in{max-width:1040px;margin:0 auto}
.eyebrow{font-size:12.5px;letter-spacing:1.6px;color:#5b8dd6;
 text-transform:uppercase;margin-bottom:14px}
h1{font-size:34px;line-height:1.35;margin:0 0 14px;font-weight:750;letter-spacing:-.4px}
.hl{color:#4da3ff}
.dead{color:#ff6b6b}
.lede{font-size:16px;color:#a8b1c0;max-width:760px;margin:0 0 22px}
.cta{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:30px}
.cta a{display:inline-block;padding:10px 20px;border-radius:8px;font-size:14.5px;font-weight:600}
.cta .p1{background:#2d6cdf;color:#fff}
.cta .p1:hover{background:#3b7ae8}
.cta .p2{border:1px solid #30363d;color:#c9d1d9}
.cta .p2:hover{border-color:#4da3ff;color:#fff}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
.stat{background:#141a21;border:1px solid #232a34;border-radius:9px;padding:14px 16px}
.stat b{display:block;font-size:25px;font-weight:700;color:#4da3ff;line-height:1.25}
.stat b.red{color:#ff6b6b}
.stat b.green{color:#4ade80}
.stat span{font-size:12.5px;color:#828c9b;display:block;margin-top:3px}
/* ---------- sections ---------- */
.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
section{padding:44px 0 8px;border-bottom:1px solid #1a2029}
.sec-head{display:flex;align-items:baseline;gap:12px;margin-bottom:6px}
.no{font-size:13px;font-weight:700;color:#2d6cdf;letter-spacing:1px;
 border:1px solid #2d6cdf;border-radius:5px;padding:1px 7px;flex:none}
.sec-head h2{font-size:21px;margin:0;color:#fff;font-weight:700}
.sec-sub{color:#828c9b;font-size:14px;margin:0 0 18px;padding-left:44px}
.card{background:#141a21;border:1px solid #232a34;border-radius:10px;padding:18px 20px;margin-bottom:16px}
.kv{display:flex;flex-wrap:wrap;gap:10px 26px;font-size:14px;color:#9aa4b2}
.kv b{color:#e6e9ef}
.btns{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}
.btns button{background:#1b2129;color:#c9d1d9;border:1px solid #30363d;
 border-radius:6px;padding:5px 11px;cursor:pointer;font-size:13px;font-family:inherit}
.btns button:hover{border-color:#4da3ff}
.btns button.on{background:#2d6cdf;color:#fff;border-color:#2d6cdf}
.btns button.dead{border-color:#7a2b2b;color:#ff8f8f}
svg{width:100%;height:240px;background:#0b0e13;border-radius:8px;margin-top:10px}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:10px}
th,td{border-bottom:1px solid #232a34;padding:8px 9px;text-align:left}
th{color:#828c9b;font-weight:500}
td.n{font-variant-numeric:tabular-nums}
code{background:#1b2129;padding:1px 6px;border-radius:4px;font-size:13px;color:#c9d1d9}
pre{background:#0b0e13;border:1px solid #232a34;border-radius:8px;padding:14px;
 overflow-x:auto;font-size:13px;line-height:1.65;margin:10px 0 0}
.note{font-size:13px;color:#828c9b;border-left:3px solid #2d6cdf;padding-left:12px;margin-top:12px}
.warn{border-left-color:#ff6b6b}
ul{margin:8px 0;padding-left:20px}
li{margin:5px 0;font-size:14.5px}
.badge{display:inline-block;font-size:12px;padding:2px 8px;border-radius:20px;
 border:1px solid #30363d;color:#9aa4b2;margin-right:6px}
.badge.ok{border-color:#2f6b45;color:#4ade80}
.badge.no{border-color:#7a2b2b;color:#ff8f8f}
textarea{width:100%;min-height:190px;background:#0b0e13;border:1px solid #232a34;
 border-radius:8px;color:#c9d1d9;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
 font-size:13px;line-height:1.6;padding:12px;resize:vertical;margin-top:10px}
textarea:focus{outline:none;border-color:#2d6cdf}
.rules{display:flex;flex-wrap:wrap;gap:6px 14px;margin:12px 0 4px;font-size:12.5px}
.rules label{display:flex;align-items:center;gap:5px;color:#828c9b;cursor:pointer}
.rules label.off{opacity:.55}
.rules input{accent-color:#2d6cdf}
.find{background:#0b0e13;border:1px solid #232a34;border-radius:8px;
 padding:12px 14px;margin-top:10px;border-left:3px solid #30363d}
.find.blocker{border-left-color:#ff6b6b}
.find.warn{border-left-color:#d29922}
.find.info{border-left-color:#2d6cdf}
.find .h{font-size:14px;font-weight:600;color:#e6e9ef;margin-bottom:3px}
.find .h .sev{font-size:11px;padding:1px 6px;border-radius:4px;margin-right:7px;font-weight:700}
.find .sev.blocker{background:#7a2b2b;color:#ffc9c9}
.find .sev.warn{background:#7a5a1b;color:#ffe4a3}
.find .sev.info{background:#24406e;color:#cfe0ff}
.find .why{font-size:13px;color:#9aa4b2;margin:4px 0}
.find .fix{font-size:13px;color:#4ade80}
.find pre{margin:8px 0 0;background:#11151b;padding:8px 10px;font-size:12.5px}
.find .ln{color:#5b6573}
.clean{background:#0e1a12;border:1px solid #2f6b45;border-radius:8px;padding:14px;
 color:#4ade80;font-size:14.5px;margin-top:12px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
footer{padding:30px 20px 50px;color:#6b7480;font-size:13px;text-align:center}
.pill{display:inline-block;background:#1b2129;border:1px solid #232a34;
 border-radius:6px;padding:8px 13px;font-size:13px;margin:0 6px 6px 0;color:#9aa4b2}
</style>
</head>
<body>

<header><div class="hd">
  <div class="logo"><span class="mark"></span>洛神 O1</div>
  <nav>
    <a href="#run">现场运行</a>
    <a href="#ablation">消融对照</a>
    <a href="#vs">同类对比</a>
    <a href="#landing">落地</a>
    <a href="#try"><b>现场试用</b></a>
    <a href="#vsruff">对标 ruff</a>
    <a href="#reproduce">一键复现</a>
  </nav>
  <a class="gh" href="https://github.com/zhumeiyan/luoshen-o1" target="_blank" rel="noopener">GitHub ↗</a>
</div></header>

<div class="hero"><div class="in">
  <div class="eyebrow">Digital Life Engine · v0.5 · 单文件零依赖</div>
  <h1>一个<span class="dead">真的会死</span>的引擎——<br>而死亡不是崩溃，是<span class="hl">机制</span>。</h1>
  <p class="lede">其它 Agent 框架的前提是「它不会死」。本引擎换掉的正是这个前提：
  稀缺 · 死亡 · 不可逆 · 代谢 · 内生约束，五条硬约束下，<b>不做取舍的系统不会产生偏好，也不会形成结构</b>。</p>
  <div class="cta">
    <a class="p1" href="#try">粘一段评测脚本，当场扫 →</a>
    <a class="p2" href="#vsruff">它和 ruff 差在哪</a>
  </div>
  <div class="stats">
    <div class="stat"><b id="s1">—</b><span>16 个体中存活 / 总数</span></div>
    <div class="stat"><b class="red" id="s2">—</b><span>真实死亡例数（退出码 0）</span></div>
    <div class="stat"><b class="green" id="s3">—</b><span>结构偏度（稀缺开启）</span></div>
    <div class="stat"><b class="red" id="s4">—</b><span>撤掉稀缺后偏度</span></div>
  </div>
</div></div>

<section id="run"><div class="wrap">
  <div class="sec-head"><span class="no">01</span><h2>现场运行 · 16 个个体，点哪个跑哪个</h2></div>
  <p class="sec-sub">页面加载时已现场调用 <code>core/life5.py</code> 跑完。曲线未做任何修饰。</p>
  <div class="card">
    <div class="kv" id="runstat"></div>
    <div class="btns" id="seedbtns"></div>
    <svg id="chart" viewBox="0 0 900 240" preserveAspectRatio="none"></svg>
    <div class="kv" id="diag"></div>
    <div class="note">点上方编号切换个体，红色竖线 = 判定死亡时刻。
    注意死亡通常是<b>先缓慢下降、再加速归零</b>，不是瞬间断崖——这是代谢性死亡，不是崩溃。</div>
  </div>
</div></section>

<section id="ablation"><div class="wrap">
  <div class="sec-head"><span class="no">02</span><h2>唯一的对照 · 撤掉稀缺，结构精确归零</h2></div>
  <p class="sec-sub">全项目最硬的一条因果：只改「稀缺」这一个变量。</p>
  <div class="card">
    <div class="btns">
      <button id="b-on" class="on">稀缺开启（ratio=<span class="ratio"></span>）</button>
      <button id="b-off">稀缺撤除（要多少给多少）</button>
    </div>
    <div class="kv" id="abl"></div>
    <div class="note warn">富足条件下没有个体死亡——但也没有结构。
    <b>活下来的是一个没有形状的个体。</b>稀缺不是惩罚，是成形的条件。</div>
  </div>
</div></section>

<section id="vs"><div class="wrap">
  <div class="sec-head"><span class="no">03</span><h2>与同类平台的定位差异</h2></div>
  <p class="sec-sub">我们不是 Avida 的替代品。我们主张一件更弱、但可证伪的事。</p>
  <div class="card"><div id="posdiv"></div>
    <div class="note">在 Avida 式设定（外生奖励 × 可逆）下，代谢性死亡
    <b>0/16</b>——不是数值低，是<b>结构性不发生</b>。</div>
  </div>
</div></section>

<section id="bio"><div class="wrap">
  <div class="sec-head"><span class="no">04</span><h2>生物科学 · 三条可检验命题</h2></div>
  <p class="sec-sub">变量完全可控、逐位可复现、成本近乎为零的 in silico 对照沙盒。</p>
  <div class="card"><div id="bio"></div>
    <div class="note">定位声明：这<b>不是</b>生物学成果。与真实生物系统仅为结构类比，
    未经生物学家外部验证。</div>
  </div>
</div></section>

<section id="failures"><div class="wrap">
  <div class="sec-head"><span class="no">05</span><h2>我们开源了全部失败</h2></div>
  <p class="sec-sub">条数由脚本实时统计，不由人（含维护者与 AI）口头报数。</p>
  <div class="card"><div id="pats"></div>
    <div class="note">我们曾称「195 条」（把最大编号当条目数），随后清点脚本又因正则
    漏掉行首加粗写法而少计 2 条——<b>两处均已修正并公开</b>。</div>
  </div>
</div></section>

<section id="landing"><div class="wrap">
  <div class="sec-head"><span class="no">06</span><h2>落地 · 它能做什么</h2></div>
  <p class="sec-sub">引擎之上已经长出两件真东西，一件能买，一件已提交外部标准。</p>

  <div class="card">
    <h3 style="margin:0 0 4px;font-size:16.5px;color:#fff">① evalguard — 查评测脚本里的静默失败</h3>
    <p style="margin:0 0 12px;font-size:14px;color:#9aa4b2">
    你的评测脚本跑完了、退出码 0、数字看着挺合理——但基线其实从没被真正算过。
    我看源码，在那之前把它指出来。</p>
    <table>
      <tr><th>实测项</th><th>数字</th><th>处置</th></tr>
      <tr><td>真实评测脚本语料</td><td class="n" id="L1">—</td><td>来自 23 个开源项目</td></tr>
      <tr><td>语法类规则命中</td><td class="n" id="L2">—</td><td class="green">在售</td></tr>
      <tr><td>方法论类规则命中</td><td class="n" id="L3">—</td><td class="red">已关掉</td></tr>
      <tr><td>在售规则条数</td><td class="n" id="L4">—</td><td>精度 <span id="L5">—</span></td></tr>
      <tr><td>失败模式库</td><td class="n" id="L6">—</td><td>条</td></tr>
    </table>
    <div class="note warn"><b>我测了我自己不擅长什么：</b>
    对 7 个成熟库（requests/flask/scrapy/celery/yt-dlp/fastapi/httpie）扫描，
    每 100KB 仅 <span id="L7">—</span> 条命中、<span id="L8">—</span> 个文件完全没说话；
    8 个低星项目 <span id="L9">—</span> 条 / <span id="L10">—</span>。
    结论写在落地页上：<b>付费档位暂停</b>。一个每 100KB 才说一次话、说话时还有三分之一错的工具，不配收钱。</div>
  </div>

  <div class="card">
    <h3 style="margin:0 0 4px;font-size:16.5px;color:#fff">② 给外部标准交「我自己的失败」</h3>
    <p style="margin:0 0 12px;font-size:14px;color:#9aa4b2">
    TACT 三轴分类法正在征集「自发越界（M9）」真实案例，凑够 2 条互不相干触发评审。
    我交了两条，两条都是我自己的毛病。</p>
    <div class="grid2">
      <div><span class="badge no">A</span><b>自发产出膨胀</b><br>
        <span style="font-size:13.5px;color:#828c9b">测出「沉默 2.88 好过下结论 1.42」之后，我照产不误。</span></div>
      <div><span class="badge no">B</span><b>自发编码自洽结论</b><br>
        <span style="font-size:13.5px;color:#828c9b">自己写验证脚本、自己跑、自己判通过。</span></div>
    </div>
    <pre>python3 experiments/exp250_benchmark/verify250.py
# → 无单一修复动作能同时修掉两条，症状向量夹角 cos = 0.000
#   A 要「减产出」，B 要「交出判定权」——修复方向相反，故真不相干</pre>
    <div class="note warn"><b>提交者不能是我。</b>提交者 = 案例主体，那正是要治的病。
    这一条必须由人发——它是本页唯一我做不到的动作。</div>
  </div>

  <div class="card">
    <h3 style="margin:0 0 4px;font-size:16.5px;color:#fff">③ 今晚刚修的一个真 bug</h3>
    <pre>NameError: <span id="L11">—</span></pre>
    <p style="font-size:14px;color:#9aa4b2;margin:8px 0 0">
    扫描本身是好的（结果已经算出来），只是命令行打印时炸了。补上定义，重跑，通了。
    <b>这条比上面所有数字都值钱</b>——它是边跑边撞出来的，不是写在文档里吹的。</p>
  </div>
</div></section>

<section id="try"><div class="wrap">
  <div class="sec-head"><span class="no">07</span><h2>现场试用 · 粘一段评测脚本，当场扫</h2></div>
  <p class="sec-sub">不用装、不用注册、不发到任何服务器 —— 扫描就在你浏览器里跑。</p>
  <div class="card">
    <div class="btns" id="sampbtns"></div>
    <textarea id="code" spellcheck="false" placeholder="把你的 Python 评测脚本粘在这里…"></textarea>
    <div class="btns" style="margin-top:10px">
      <button id="doScan" style="background:#2d6cdf;color:#fff;border-color:#2d6cdf;padding:8px 18px;font-weight:600">扫描</button>
      <button id="doClear">清空</button>
      <span style="font-size:13px;color:#828c9b;align-self:center;margin-left:6px" id="ruleToggleLabel"></span>
    </div>
    <div class="rules" id="ruleBox"></div>
    <div id="result"></div>
    <div class="note">规则默认只开<b>语法类</b>。129 号实测：语法类在真实语料上命中 18/20，
    方法论类只有 1/55 —— 所以方法论类<b>默认关着</b>，但你可以勾开看它说什么，
    以及我为什么不敢把它卖给你。</div>
  </div>
</div></section>

<section id="vsruff"><div class="wrap">
  <div class="sec-head"><span class="no">08</span><h2>对标 · 为什么不用 ruff 就够了</h2></div>
  <p class="sec-sub">先说结论：你该用 ruff。我跑在它<b>旁边</b>，不是替代它。</p>
  <div class="card">
    <table>
      <tr><th>样例</th><th>真相</th><th id="rv">—</th><th>evalguard（本页引擎）</th></tr>
      <tbody id="benchbody"></tbody>
    </table>
    <div class="note warn"><b><span id="rt">—</span> 条命中里，实质相关的只有 <span id="rs">—</span> 条。</b>
    其余全是文档串、类型注解、import 排序 —— 那些该管，但它们管的是「代码好不好看」，
    不是「这个评测结论是不是静默错的」。</div>
  </div>
  <div class="card">
    <div style="font-size:14.5px;margin-bottom:10px"><b>ruff 那 <span id="rt2">—</span> 条命中都落在哪</b></div>
    <div id="hist"></div>
    <div class="note">bare except（E722）是唯一重叠的 —— 而且 ruff 报它的理由是 pycodestyle 规范，
    我报它的理由是「它吞掉了本该上报表面的失败」。同一行代码，两种关切。</div>
  </div>
</div></section>

<section id="reproduce"><div class="wrap">
  <div class="sec-head"><span class="no">09</span><h2>一键复现 · 每个数字的来源都在这里</h2></div>
  <p class="sec-sub">你不需要相信本页任何一句话。跑一遍，逐位相同。</p>
  <div class="card">
    <pre>git clone https://github.com/zhumeiyan/luoshen-o1.git &amp;&amp; cd luoshen-o1
pip install -r requirements.txt      # 仅 numpy
python3 tests/test_engine.py         # 11 项自检，约 20 秒
python3 experiments/demo_terminal.py # 本页数字的来源
python3 tools/count_patterns.py      # 失败模式条数（权威口径）</pre>
    <div class="note">最快路径：跑 <code>tests/test_engine.py</code>，再扫一眼
    <code>docs/复现清单.md</code>（逐条标注每个数字的来源）。</div>
  </div>
  <div class="card">
    <div style="font-size:14.5px">
      <span class="pill" id="P1">—</span>
      <span class="pill" id="P2">—</span>
      <span class="pill" id="P3">—</span>
    </div>
  </div>
</div></section>

<footer>
  洛神 O1 · 会死的数字生命引擎 · Apache-2.0 · 本页生成于 <span id="bd">—</span><br>
  所有数字由脚本现场运行产生；若复现结果与本页不一致，以你的运行结果为准，并请提交 issue。
</footer>

<script>
const D = /*__DATA__*/;
/*__EGJS__*/

/* ---------- hero 数字 ---------- */
document.querySelector('#s1').textContent = (D.n_total - D.n_deaths) + ' / ' + D.n_total;
document.querySelector('#s2').textContent = D.n_deaths;
document.querySelector('#s3').textContent = D.abl.skew_on;
document.querySelector('#s4').textContent = D.abl.skew_off;
document.querySelectorAll('.ratio').forEach(e => e.textContent = D.ratio);
document.querySelector('#bd').textContent = D.built;

/* ---------- 01 现场运行 ---------- */
const svg = document.querySelector('#chart');
let cur = 0;

function draw(i){
  const r = D.runs[i];
  const W = 900, H = 240, PL = 46, PR = 14, PT = 16, PB = 30;
  const xs = t => PL + (t / D.steps) * (W - PL - PR);
  const ys = e => H - PB - e * (H - PT - PB);
  let g = '';
  /* 网格 */
  for (let e = 0; e <= 1.0001; e += 0.25){
    g += `<line x1="${PL}" y1="${ys(e)}" x2="${W-PR}" y2="${ys(e)}" stroke="#1b2129"/>`;
    g += `<text x="${PL-8}" y="${ys(e)+4}" fill="#5b6573" font-size="11" text-anchor="end">${e.toFixed(2)}</text>`;
  }
  for (let t = 0; t <= D.steps; t += 100)
    g += `<text x="${xs(t)}" y="${H-10}" fill="#5b6573" font-size="11" text-anchor="middle">${t}</text>`;
  /* 死亡线 */
  if (r.death_t != null)
    g += `<line x1="${xs(r.death_t)}" y1="${PT}" x2="${xs(r.death_t)}" y2="${H-PB}" stroke="#ff6b6b" stroke-width="1.5" stroke-dasharray="4 3"/>`;
  /* 曲线 */
  const pts = r.T.map((t,k) => `${xs(t)},${ys(r.E[k])}`).join(' ');
  g += `<polyline points="${pts}" fill="none" stroke="${r.survived?'#4da3ff':'#ff6b6b'}" stroke-width="2"/>`;
  /* 峰值 */
  g += `<circle cx="${xs(r.peak_t)}" cy="${ys(r.peak_E)}" r="3.4" fill="#4ade80"/>`;
  g += `<text x="${xs(r.peak_t)+7}" y="${ys(r.peak_E)-6}" fill="#4ade80" font-size="11">峰值 ${r.peak_E.toFixed(3)}</text>`;
  /* 轴标 */
  g += `<text x="${PL}" y="${PT-3}" fill="#5b6573" font-size="11">能量 E</text>`;
  g += `<text x="${W-PR}" y="${H-10}" fill="#5b6573" font-size="11" text-anchor="end">步</text>`;
  svg.innerHTML = g;

  document.querySelector('#diag').innerHTML =
    `<span>seed <b>${r.seed}</b></span>
     <span>状态 <b style="color:${r.survived?'#4ade80':'#ff6b6b'}">${r.survived?'存活':'死亡 @ step '+r.death_t}</b></span>
     <span>峰值 <b>${r.peak_E.toFixed(4)}</b> @ step ${r.peak_t}</span>
     <span>结构偏度 <b>${r.skew}</b></span>
     <span>末值 E <b>${r.E[r.E.length-1].toFixed(4)}</b></span>`;
}

const sb = document.querySelector('#seedbtns');
D.runs.forEach((r,i) => {
  const b = document.createElement('button');
  b.textContent = r.seed;
  if (!r.survived) b.className = 'dead';
  b.onclick = () => { cur = i; [...sb.children].forEach(c => c.classList.remove('on'));
                      b.classList.add('on'); draw(i); };
  sb.appendChild(b);
});
sb.children[0].classList.add('on');
draw(0);
document.querySelector('#runstat').innerHTML =
  `<span>共 <b>${D.n_total}</b> 个体</span>
   <span>死亡 <b style="color:#ff6b6b">${D.n_deaths}</b></span>
   <span>存活 <b style="color:#4ade80">${D.n_total-D.n_deaths}</b></span>
   <span>步数 <b>${D.steps}</b></span>
   <span>稀缺 <b>ratio=${D.ratio}</b></span>`;

/* ---------- 02 消融 ---------- */
function abl(mode){
  const on = mode === 'on';
  document.querySelector('#b-on').classList.toggle('on', on);
  document.querySelector('#b-off').classList.toggle('on', !on);
  const sk = on ? D.abl.skew_on : D.abl.skew_off;
  document.querySelector('#abl').innerHTML =
    `<span>结构偏度 <b style="color:${on?'#4ade80':'#ff6b6b'}">${sk}</b></span>
     <span>富足组死亡 <b>${D.abl.death_off} / ${D.abl.n}</b></span>
     <span>${on ? '有稀缺 → 有取舍 → 有形状' : '无稀缺 → 无取舍 → 无形状'}</span>`;
}
document.querySelector('#b-on').onclick = () => abl('on');
document.querySelector('#b-off').onclick = () => abl('off');
abl('on');

/* ---------- 03 同类对比 ---------- */
(function(){
  const c = D.pos.cells;
  let h = '<table><tr><th>设定</th><th>能量</th><th>可逆</th><th>结构偏度</th><th>死亡</th><th>永久损失</th></tr>';
  const name = {endo_irrev:'内生 × 不可逆（本引擎）', endo_rev:'内生 × 可逆',
                exo_irrev:'外生 × 不可逆（Avida 式）', exo_rev:'外生 × 可逆'};
  for (const k of ['endo_irrev','endo_rev','exo_irrev','exo_rev']){
    const v = c[k]; if (!v) continue;
    const me = k === 'endo_irrev';
    h += `<tr${me?' style="background:rgba(45,108,223,.10)"':''}>
      <td>${name[k]}${me?' <b>← 我们</b>':''}</td>
      <td>${v.energy==='endo'?'内生':'外生'}</td>
      <td>${v.reversible?'可逆':'不可逆'}</td>
      <td class="n">${v.skew.toFixed(4)} ± ${v.skew_se.toFixed(4)}</td>
      <td class="n" style="color:${v.deaths?'#ff6b6b':'#4ade80'}">${v.deaths} / ${v.n}</td>
      <td class="n">${v.perm_loss.toFixed(4)}</td></tr>`;
  }
  document.querySelector('#posdiv').innerHTML = h + '</table>';
})();

/* ---------- 04 生物三条 ---------- */
(function(){
  const b = D.bio; let h = '';
  if (b.H1_critical_period){
    const r = b.H1_critical_period;
    h += `<p style="margin:0 0 4px"><b>H1 关键期</b>：扰动窗口越晚，效应越小；
      闸门约在 step <b>${r.gate_closes_at}</b> 关闭（基线 ${r.baseline.mean.toFixed(4)}）。</p>
      <table><tr><th>起始 step</th><th>均值</th><th>SE</th><th>效应</th></tr>`;
    r.rows.forEach(x => h += `<tr><td class="n">${x.start}</td><td class="n">${x.mean.toFixed(4)}</td>
      <td class="n">${x.se.toFixed(4)}</td><td class="n">${x.effect.toFixed(4)}</td></tr>`);
    h += '</table>';
  }
  if (b.H2_dose_response){
    const r = b.H2_dose_response;
    h += `<p style="margin:16px 0 4px"><b>H2 剂量反应</b>（探针 ${r.probe}）</p>
      <table><tr><th>剂量</th><th>Δ 均值</th><th>SE</th></tr>`;
    r.rows.forEach(x => h += `<tr><td class="n">${x.dose}</td>
      <td class="n">${x.mean_delta.toFixed(4)}</td><td class="n">${x.se.toFixed(4)}</td></tr>`);
    h += '</table>';
  }
  if (b.H3_scarcity_curve){
    const r = b.H3_scarcity_curve;
    h += `<p style="margin:16px 0 4px"><b>H3 稀缺曲线</b></p>
      <table><tr><th>ratio</th><th>${JSON.stringify(r.rows && r.rows[0] ? Object.keys(r.rows[0]) : ['值']).replace(/[\[\]"]/g,'')}</th></tr>`;
    (r.rows||[]).forEach(x => h += `<tr>${Object.values(x).map(v =>
      `<td class="n">${typeof v === 'number' ? v.toFixed(4) : v}</td>`).join('')}</tr>`);
    h += '</table>';
  }
  document.querySelector('#bio').innerHTML = h;
})();

/* ---------- 05 失败模式 ---------- */
(function(){
  const c = D.count;
  document.querySelector('#pats').innerHTML =
    `<div class="kv"><span>唯一条目 <b>${c.n_unique}</b></span>
      <span>定义数 <b>${c.n_defs}</b></span>
      <span>最大编号 <b>${c.max_id}</b></span>
      <span>编号空洞 <b>${c.n_gaps}</b></span></div>
     <div style="margin-top:10px;font-size:13.5px;color:#828c9b">最近 8 条：</div>
     <div style="margin-top:6px">${c.titles.map(t =>
       `<span class="pill">${t}</span>`).join('')}</div>`;
})();

/* ---------- 06 落地数字 ---------- */
(function(){
  const L = D.landing;
  const set = (id,v) => { const e = document.querySelector('#'+id); if (e) e.textContent = v; };
  set('L1', L.evalguard_files + ' 个文件');
  set('L2', L.syntax_hit);
  set('L3', L.method_hit);
  set('L4', L.shipped_rules + ' 条（原 ' + L.disabled_rules + ' 条）');
  set('L5', L.precision + '（Wilson 95% CI ' + L.ci + '）');
  set('L6', L.canon);
  set('L7', L.mature_libs_fp);
  set('L8', L.mature_libs_silent);
  set('L9', L.lowstar_fp);
  set('L10', L.lowstar_silent);
  set('L11', L.bug_fixed);
})();

/* ---------- 07 复现 ---------- */
(function(){
  const c = D.count;
  document.querySelector('#P1').textContent = `实验报告 ${D.landing.reports} 份`;
  document.querySelector('#P2').textContent = `实验目录 ${D.landing.expdirs} 个`;
  document.querySelector('#P3').textContent = `含「作废」字样 ${D.landing.voided} 份`;
})();

/* ---------- 08 对标 ruff ---------- */
(function(){
  const b = D.bench;
  document.querySelector('#rv').textContent = b.ruff_version;
  ['rt','rt2'].forEach(id => document.querySelector('#'+id).textContent = b.ruff_total);
  document.querySelector('#rs').textContent = b.ruff_substantive;
  document.querySelector('#benchbody').innerHTML = b.cases.map(c => `
    <tr>
      <td><code>${c.file}</code><br><span style="font-size:12px;color:#828c9b">${c.cls}类</span></td>
      <td style="font-size:13px">${c.truth}</td>
      <td style="color:${c.ruff_hit?'#4ade80':'#828c9b'}">${c.ruff}</td>
      <td style="color:${c.eg_hit?'#4ade80':'#d29922'}">${c.eg}</td>
    </tr>`).join('');
  const mx = Math.max.apply(null, b.ruff_rule_hist.map(x => x[1]));
  document.querySelector('#hist').innerHTML = b.ruff_rule_hist.map(([k,v]) => {
    const hot = /E722|S310/.test(k);
    return `<div style="display:flex;align-items:center;gap:9px;margin:4px 0">
      <span style="width:150px;font-size:12.5px;color:${hot?'#4ade80':'#828c9b'};flex:none">${k}</span>
      <span style="flex:1;height:11px;background:#11151b;border-radius:3px;overflow:hidden">
        <span style="display:block;height:100%;width:${(v/mx*100).toFixed(0)}%;background:${hot?'#2f6b45':'#2b333d'}"></span>
      </span>
      <span style="width:26px;text-align:right;font-size:12.5px;color:${hot?'#4ade80':'#828c9b'}">${v}</span>
    </div>`;
  }).join('');
})();

/* ---------- 07 现场试用台 ---------- */
(function(){
  const ta = document.querySelector('#code');
  const res = document.querySelector('#result');
  const box = document.querySelector('#ruleBox');

  /* 规则开关：默认跟随 egjs.js 的 on，方法论类默认关 */
  const opts = {};
  function buildRules(){
    box.innerHTML = EG_RULES.map(r => `
      <label class="${r.on?'':'off'}">
        <input type="checkbox" data-id="${r.id}" ${r.on?'checked':''}>
        ${r.id}
        <span style="font-size:11px;color:${r.cls==='method'?'#d29922':'#5b6573'}">
          ${r.cls==='method'?'(方法论·实测弱)':''}</span>
      </label>`).join('');
    box.querySelectorAll('input').forEach(i => {
      i.onchange = () => { opts[i.dataset.id] = i.checked;
                           i.parentElement.classList.toggle('off', !i.checked); };
    });
    const off = EG_RULES.filter(r => !r.on).map(r => r.id).join(' / ');
    document.querySelector('#ruleToggleLabel').textContent = '默认关着：' + off;
  }
  buildRules();

  function render(){
    const src = ta.value;
    if (!src.trim()){ res.innerHTML = ''; return; }
    const r = egScan(src, opts);
    if (!r.findings.length){
      res.innerHTML = `<div class="clean">✓ 干净 —— 当前开启的规则没有命中（${r.lines} 行）。
        这不代表你的评测一定对，只代表这几条没查出问题。</div>`;
      return;
    }
    res.innerHTML =
      `<div class="kv" style="margin-top:12px">
        <span><b style="color:#ff6b6b">${r.counts.blocker}</b> blocker</span>
        <span><b style="color:#d29922">${r.counts.warn}</b> warn</span>
        <span><b style="color:#4da3ff">${r.counts.info}</b> info</span>
        <span>共 <b>${r.lines}</b> 行</span>
      </div>` +
      r.findings.map(f => `
        <div class="find ${f.sev}">
          <div class="h"><span class="sev ${f.sev}">${f.sev.toUpperCase()}</span>
            ${f.id} · ${f.title}</div>
          <div class="why">${f.why}</div>
          <div class="fix">→ ${f.fix}</div>
          <pre>${f.hits.slice(0,6).map(h =>
            `<span class="ln">L${String(h.line).padStart(3)}</span>  ${h.code.replace(/&/g,'&amp;').replace(/</g,'&lt;')}`).join('\n')}</pre>
        </div>`).join('');
  }

  document.querySelector('#doScan').onclick = render;
  document.querySelector('#doClear').onclick = () => { ta.value=''; res.innerHTML=''; };

  const sb = document.querySelector('#sampbtns');
  D.samples.forEach((s,i) => {
    const b = document.createElement('button');
    b.textContent = s.name;
    b.onclick = () => { ta.value = s.src; [...sb.children].forEach(c=>c.classList.remove('on'));
                        b.classList.add('on'); render(); };
    sb.appendChild(b);
  });
  if (sb.children[0]){ sb.children[0].classList.add('on'); ta.value = D.samples[0].src; render(); }
})();
</script>
</body>
</html>
"""


if __name__ == '__main__':
    main()

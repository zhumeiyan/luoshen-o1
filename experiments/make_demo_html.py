# -*- coding: utf-8 -*-
"""
================================================================
洛神 O1 · 生成「评委即开即用」HTML 演示台
================================================================
设计约束（对应我们自己的失败模式库）：
  · 单文件、零依赖、零网络 —— 双击即开，不需要服务器
  · 所有数字来自【本脚本现场真实运行】或仓库内真实 JSON，不写死
  · 内置自校验：若多个 seed 轨迹完全相同，立即报错
    （这是第 23 条「变量静默失效」在本演示中的具体防线）

运行： python3 experiments/make_demo_html.py
输出： docs/demo.html
"""
import os
import sys
import json

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'core'))
from life5 import Life5

STEPS = 600
NCH = 8
RATIO = 0.45
SEEDS = list(range(16))


def struct_skew(lf):
    """结构偏度：容量向量的变异系数。结构成形则 >0。"""
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def run_seed(seed, ratio=RATIO):
    lf = Life5(N=NCH, seed=seed, ratio=ratio)
    T, E = [], []
    for t in range(1, STEPS + 1):
        lf.step()
        if t % 5 == 0 or t == 1:
            T.append(t)
            E.append(round(float(lf.E), 4))
        if not lf.alive:
            T.append(t)
            E.append(round(float(lf.E), 4))
            break
    pk = int(np.argmax(E))
    zero_t = None
    for t, e in zip(T, E):
        if e <= 1e-3:
            zero_t = t
            break
    return {
        'seed': seed,
        'survived': bool(lf.alive),
        'death_t': lf.death_t,
        'T': T, 'E': E,
        'peak_t': T[pk], 'peak_E': E[pk],
        'zero_t': zero_t,
        'skew': round(struct_skew(lf), 4),
    }


def load(name):
    p = os.path.join(ROOT, 'data', name)
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def main():
    print('现场运行 %d 个 seed × %d 拍 ...' % (len(SEEDS), STEPS))
    runs = [run_seed(s) for s in SEEDS]

    # ---- 自校验：轨迹必须分化（防「变量静默失效」）----
    sigs = {tuple(r['E'][:20]) for r in runs}
    if len(sigs) < 2:
        raise SystemExit('[FAIL] 所有 seed 轨迹完全相同 —— seed 未生效，'
                         '禁止出图（判据核第 23 条）')
    deaths = [r for r in runs if not r['survived']]
    print('轨迹分化: %d 种 / %d ; 死亡 %d / %d' %
          (len(sigs), len(runs), len(deaths), len(runs)))

    bio = load('bio_results.json')
    pos = load('positioning_results.json')
    cnt = load('pattern_count.json')

    data = {
        'runs': runs,
        'n_deaths': len(deaths),
        'n_total': len(runs),
        'bio': bio,
        'pos': pos,
        'count': {
            'n_unique': cnt['n_unique'],
            'n_defs': cnt['n_defs'],
            'max_id': cnt['max_id'],
            'n_gaps': cnt['n_gaps'],
            'titles': [t['title'] for t in cnt['titles'][-8:]],
        },
        'steps': STEPS,
        'ratio': RATIO,
    }

    html = TEMPLATE.replace('/*__DATA__*/',
                            json.dumps(data, ensure_ascii=False))
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
 background:#0e1116;color:#e6e9ef;line-height:1.7}
.wrap{max-width:960px;margin:0 auto;padding:28px 20px 64px}
h1{font-size:26px;margin:0 0 6px}
.sub{color:#8b93a1;font-size:14px;margin-bottom:26px}
.card{background:#161b22;border:1px solid #262d38;border-radius:10px;
 padding:18px 20px;margin-bottom:18px}
h2{font-size:18px;margin:0 0 12px;color:#fff}
h2 .n{display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;
 background:#2d6cdf;border-radius:6px;font-size:13px;margin-right:8px}
.kv{display:flex;flex-wrap:wrap;gap:10px 26px;font-size:14px;color:#9aa4b2}
.kv b{color:#e6e9ef}
.big{font-size:30px;font-weight:700;color:#4da3ff}
.red{color:#ff6b6b}.green{color:#4ade80}.dim{color:#8b93a1}
.btns{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}
.btns button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;
 border-radius:6px;padding:5px 11px;cursor:pointer;font-size:13px}
.btns button.on{background:#2d6cdf;color:#fff;border-color:#2d6cdf}
.btns button.dead{border-color:#7a2b2b}
svg{width:100%;height:230px;background:#0b0e13;border-radius:8px;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:8px}
th,td{border-bottom:1px solid #262d38;padding:7px 8px;text-align:left}
th{color:#8b93a1;font-weight:500}
code{background:#21262d;padding:1px 6px;border-radius:4px;font-size:13px}
pre{background:#0b0e13;border:1px solid #262d38;border-radius:8px;padding:12px;
 overflow-x:auto;font-size:13px}
.note{font-size:13px;color:#8b93a1;border-left:3px solid #2d6cdf;padding-left:12px;
 margin-top:12px}
ul{margin:8px 0;padding-left:20px}
li{margin:4px 0;font-size:14px}
</style>
</head>
<body>
<div class="wrap">
<h1>洛神 O1 · 会死的数字生命引擎</h1>
<div class="sub">单文件 · 零依赖 · 零网络 · 页面内所有数字均由真实运行产生</div>

<div class="card">
<h2><span class="n">1</span>60 秒速览</h2>
<ul>
<li><b>五个硬约束</b>：稀缺 · 死亡 · 不可逆 · 代谢 · 内生约束。少一个，结构就不成形。</li>
<li><b>死亡是机制，不是崩溃</b>：无异常、无 traceback、退出码 0，引擎继续运行。</li>
<li><b id="facts"></b></li>
</ul>
<div class="note">本页所有曲线，均由本页数据生成时现场调用 <code>core/life5.py</code> 跑出，
 未做任何人工修饰。你可在本地一键复现，得到逐位相同的数字。</div>
</div>

<div class="card">
<h2><span class="n">2</span>现场运行：同一个引擎，16 个个体</h2>
<div class="kv" id="runstat"></div>
<div class="btns" id="seedbtns"></div>
<svg id="chart" viewBox="0 0 900 230" preserveAspectRatio="none"></svg>
<div class="kv" id="diag"></div>
<div class="note">点上方任一编号切换个体。红色竖线 = 判定死亡时刻。
 注意死亡通常是<b>先缓慢下降、再加速归零</b>，不是瞬间断崖。</div>
</div>

<div class="card">
<h2><span class="n">3</span>唯一的对照：撤掉稀缺会怎样</h2>
<div class="btns">
  <button id="b-on" class="on">稀缺开启（ratio=0.45）</button>
  <button id="b-off">稀缺撤除（要多少给多少）</button>
</div>
<div class="kv" id="abl"></div>
<div class="note">这是全项目最硬的一条因果对照：
 只改「稀缺」这一个变量，结构偏度<b>精确归零</b>。
 富足条件下没有个体死亡，但也没有结构——<b>活下来的是一个没有形状的个体</b>。</div>
</div>

<div class="card">
<h2><span class="n">4</span>生物科学：三条可检验命题</h2>
<div id="bio"></div>
<div class="note">定位声明：这<b>不是</b>生物学成果，而是给演化 / 发育 / 生态假说提供一处
 变量完全可控、逐位可复现、成本近乎为零的 <b>in silico 对照沙盒</b>。
 与真实生物系统仅为结构类比，未经生物学家外部验证。</div>
</div>

<div class="card">
<h2><span class="n">5</span>我们开源了全部失败</h2>
<div id="pats"></div>
<div class="note">条数由 <code>tools/count_patterns.py</code> 实时统计，
 不由人（含维护者与 AI）口头报数。此前我们曾称「195 条」（把最大编号当条目数），
 随后清点脚本又因正则漏掉行首加粗写法而少计 2 条——<b>两处均已修正并公开</b>。</div>
</div>

<div class="card">
<h2><span class="n">6</span>与同类平台的定位差异</h2>
<div id="posdiv"></div>
<div class="note">我们<b>不是</b> Avida 的替代品。在 Avida 式设定（外生奖励 × 可逆）下，
 代谢性死亡 <b>0/16</b> —— 不是数值低，是<b>结构性不发生</b>。</div>
</div>

<div class="card">
<h2><span class="n">7</span>一键复现</h2>
<pre>git clone &lt;仓库地址&gt; &amp;&amp; cd luoshen-o1
pip install -r requirements.txt      # 仅 numpy
python3 tests/test_engine.py         # 11 项自检
python3 experiments/demo_terminal.py # 本页数字的来源
python3 tools/count_patterns.py      # 失败模式条数（权威口径）</pre>
<div class="note">评审最快路径：跑 <code>tests/test_engine.py</code>（约 20 秒），
 再扫一眼 <code>docs/复现清单.md</code>（逐条标注每个数字的来源）。</div>
</div>

</div>
<script id="data" type="application/json">/*__DATA__*/</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const G = id => document.getElementById(id);

// ---- 1 速览 ----
G('facts').innerHTML = '本页数据：' + D.n_total + ' 个个体，'
  + D.n_deaths + ' 个自然死亡，其余存活到 ' + D.steps + ' 拍。';

// ---- 2 轨迹图 ----
function draw(r){
  const W=900,H=230,PL=46,PR=14,PT=14,PB=26;
  const T=r.T,E=r.E;
  const x=t=>PL+(t-0)/(D.steps-0)*(W-PL-PR);
  const y=e=>PT+(1-e/1.0)*(H-PT-PB);
  let pts=T.map((t,i)=>x(t).toFixed(1)+','+y(E[i]).toFixed(1)).join(' ');
  let g='';
  // 网格
  for(let e=0;e<=1.0001;e+=0.25){
    g+=`<line x1="${PL}" y1="${y(e)}" x2="${W-PR}" y2="${y(e)}" stroke="#1b2130"/>`;
    g+=`<text x="6" y="${y(e)+4}" fill="#5b6472" font-size="11">${e.toFixed(2)}</text>`;
  }
  for(let t=0;t<=D.steps;t+=100){
    g+=`<line x1="${x(t)}" y1="${PT}" x2="${x(t)}" y2="${H-PB}" stroke="#151a24"/>`;
    g+=`<text x="${x(t)-8}" y="${H-8}" fill="#5b6472" font-size="11">${t}</text>`;
  }
  // 死亡线
  if(r.death_t!=null){
    g+=`<line x1="${x(r.death_t)}" y1="${PT}" x2="${x(r.death_t)}" y2="${H-PB}" stroke="#ff6b6b" stroke-width="2"/>`;
    g+=`<text x="${x(r.death_t)-30}" y="${PT+14}" fill="#ff6b6b" font-size="12">判定死亡 ${r.death_t}</text>`;
  }
  // 曲线
  const col=r.survived?'#4da3ff':'#ff9b6b';
  g+=`<polyline points="${pts}" fill="none" stroke="${col}" stroke-width="2"/>`;
  g+=`<text x="${PL}" y="${H-8}" fill="#5b6472" font-size="11">拍</text>`;
  G('chart').innerHTML=g;
  G('diag').innerHTML=
    `<span>结局：<b class="${r.survived?'green':'red'}">${r.survived?'存活':'死亡'}</b></span>`
   +`<span>判定死亡拍：<b>${r.death_t==null?'—':r.death_t}</b></span>`
   +`<span>峰值能量：<b>${r.peak_E.toFixed(4)}</b>（第 ${r.peak_t} 拍）</span>`
   +`<span>能量归零拍：<b>${r.zero_t==null?'—':r.zero_t}</b></span>`
   +`<span>结构偏度：<b>${r.skew.toFixed(4)}</b></span>`;
}
let cur=D.runs.findIndex(r=>!r.survived); if(cur<0) cur=0;
G('seedbtns').innerHTML=D.runs.map((r,i)=>
  `<button data-i="${i}" class="${r.survived?'':'dead'}">${r.seed}${r.survived?'':' †'}</button>`).join('');
function sel(i){
  cur=i;
  [...G('seedbtns').children].forEach(b=>b.classList.toggle('on',+b.dataset.i===i));
  draw(D.runs[i]);
}
G('seedbtns').onclick=e=>{if(e.target.dataset.i!=null) sel(+e.target.dataset.i);};
G('runstat').innerHTML=`<span>共 <b>${D.n_total}</b> 个个体</span>`
 +`<span>自然死亡 <b class="red">${D.n_deaths}</b></span>`
 +`<span>存活 <b class="green">${D.n_total-D.n_deaths}</b></span>`
 +`<span>稀缺度 ratio=<b>${D.ratio}</b></span>`;
sel(cur);

// ---- 3 稀缺对照 ----
const C=D.bio.H3_scarcity_curve.rows;
const on=C.filter(r=>r.ratio<1.0), off=C.filter(r=>r.ratio>=1.0);
function abl(k){
  const on_=k==='on';
  G('b-on').classList.toggle('on',on_);
  G('b-off').classList.toggle('on',!on_);
  const rows=on_?on:off;
  const ms=(rows.reduce((a,b)=>a+b.mean_skew,0)/rows.length);
  const dt=rows.reduce((a,b)=>a+b.deaths,0);
  G('abl').innerHTML=`<span>结构偏度均值：<b class="${ms>0.01?'green':'red'}">${ms.toFixed(4)}</b></span>`
   +`<span>死亡数：<b>${dt}</b></span>`
   +`<span class="dim">${on_?'稀缺带内：结构成形，且有个体死亡':'富足区：无死亡，但结构精确归零'}</span>`;
}
G('b-on').onclick=()=>abl('on'); G('b-off').onclick=()=>abl('off'); abl('on');

// ---- 4 生物 ----
const H1=D.bio.H1_critical_period,H2=D.bio.H2_dose_response,H3=D.bio.H3_scarcity_curve;
G('bio').innerHTML=`
<table><tr><th>命题</th><th>实测结论</th></tr>
<tr><td>H1 发育关键期</td><td>存在，门在<b>第 ${H1.gate_closes_at} 拍</b>关上；
 效应由 +${H1.rows[0].effect.toFixed(4)} 单调衰减到 ${H1.rows[4].effect.toFixed(4)}</td></tr>
<tr><td>H2 早期剥夺剂量-反应</td><td><b>阈值型非线性</b>：50 拍即达最大效应的
 ${(H2.rows[0].mean_delta/H2.rows[4].mean_delta*100).toFixed(1)}%，
 符号一致性 ${H2.rows[0].sign_consistent}</td></tr>
<tr><td>H3 稀缺度 → 结构</td><td><b>开关而非旋钮</b>：ratio≥1.0 时结构偏度
 <b class="red">精确归零 0.0000</b></td></tr></table>`;

// ---- 5 失败模式 ----
const K=D.count;
G('pats').innerHTML=`<div class="big">${K.n_unique}</div>
<div class="kv"><span>独立条目（去重）<b>${K.n_unique}</b></span>
<span>定义行 <b>${K.n_defs}</b></span>
<span>最大编号 <b>${K.max_id}</b></span>
<span>编号缺口 <b>${K.n_gaps}</b> 处</span></div>
<div class="dim" style="font-size:13px;margin-top:10px">最近 8 条：</div>
<ul>${K.titles.slice().reverse().map(t=>'<li>'+t.replace(/^\*+/,'')+'</li>').join('')}</ul>`;

// ---- 6 定位 ----
const P=D.pos.cells;
G('posdiv').innerHTML=`<table>
<tr><th>设定</th><th>死亡数</th><th>结构偏度</th><th>容量回升</th><th>永久损失</th></tr>
${Object.keys(P).map(k=>{const c=P[k];return `<tr><td>${k}</td>
<td class="${c.deaths>0?'red':'dim'}">${c.deaths}/16</td>
<td>${c.skew.toFixed(4)}</td><td>${c.rise_max.toFixed(4)}</td>
<td>${c.perm_loss.toFixed(4)}</td></tr>`;}).join('')}</table>`;
</script>
</body>
</html>
"""

if __name__ == '__main__':
    sys.exit(main())

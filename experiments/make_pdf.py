# -*- coding: utf-8 -*-
"""由 docs/作品介绍文档.md + data/真实结果 + fig/ 生成参赛 PDF。"""
import os, json
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                XPreformatted,
                                Spacer, Table, TableStyle, Image, PageBreak,
                                KeepTogether)

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'docs', '洛神O1_作品介绍文档.pdf')

# 失败模式条数：由权威清点脚本实时统计，避免各物料间数字打架
_PC = json.load(open(os.path.join(ROOT, 'data', 'pattern_count.json')))
N_UNIQUE = _PC['n_unique']    # 去重后独立条目数
N_DEFS   = _PC['n_defs']      # 条目定义行数
MIN_ID   = _PC['min_id']
MAX_ID   = _PC['max_id']
N_DUP    = N_DEFS - N_UNIQUE  # 重复编号数
N_GAPS   = _PC['n_gaps']

# 实验报告份数：同样实时统计，避免硬编码漂移
# （此前硬编码 53，实际已增至 60，且漂移检查未覆盖 .py 源码，属漏网点）
_REPDIR = os.path.join(ROOT, 'evidence', '实验报告')
N_REPORT = len([f for f in os.listdir(_REPDIR) if f.endswith('.md')])

FD = '/usr/share/fonts/truetype/alibaba-puhuiti'
pdfmetrics.registerFont(TTFont('PH', f'{FD}/AlibabaPuHuiTi-2-55-Regular.ttf'))
pdfmetrics.registerFont(TTFont('PHB', f'{FD}/AlibabaPuHuiTi-2-85-Bold.ttf'))
pdfmetrics.registerFont(TTFont('PHH', f'{FD}/AlibabaPuHuiTi-2-105-Heavy.ttf'))

INK = colors.HexColor('#111418')
MUT = colors.HexColor('#6b7280')
ACC = colors.HexColor('#1f6feb')
LINE = colors.HexColor('#d8dee6')
BG = colors.HexColor('#f5f7fa')

S = lambda n, sz, lh=1.55, col=INK, al=TA_JUSTIFY, f='PH': ParagraphStyle(
    n, fontName=f, fontSize=sz, leading=sz*lh, textColor=col, alignment=al,
    spaceAfter=4)

st_h1 = S('h1', 16, 1.4, INK, TA_JUSTIFY, 'PHH')
st_h2 = S('h2', 12.5, 1.4, ACC, TA_JUSTIFY, 'PHB')
st_b = S('b', 9.6, 1.65)
st_quote = S('q', 10, 1.6, ACC, TA_CENTER, 'PHB')
st_cap = S('cap', 8.2, 1.4, MUT, TA_CENTER)
st_td = S('td', 9, 1.45, INK, TA_JUSTIFY)
st_th = S('th', 9, 1.45, colors.white, TA_CENTER, 'PHB')

res = json.load(open(os.path.join(ROOT, 'data', 'core_results.json')))
B, C, D = res['B_tradeoff'], res['C_weld'], res['D_window']
A = res['A_death']
dead = [r for r in A if not r['survived']]
OFF = json.load(open(os.path.join(ROOT, 'data', 'offload_results.json')))
O1, O2 = OFF['S1_remove'], OFF['S2_keep']


def tbl(data, widths, align_right=None):
    rows = []
    for i, row in enumerate(data):
        rows.append([Paragraph(c, st_th if i == 0 else st_td) for c in row])
    t = Table(rows, colWidths=widths, repeatRows=1)
    style = [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f6feb')),
             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('GRID', (0, 0), (-1, -1), 0.5, LINE),
             ('TOPPADDING', (0, 0), (-1, -1), 5),
             ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
             ('LEFTPADDING', (0, 0), (-1, -1), 7),
             ('RIGHTPADDING', (0, 0), (-1, -1), 7)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(('BACKGROUND', (0, i), (-1, i), BG))
    t.setStyle(TableStyle(style))
    return t


def fig_img(name, w=118*mm):
    p = os.path.join(ROOT, 'fig', name)
    im = Image(p)
    im.drawWidth = w
    im.drawHeight = w * im.imageHeight / im.imageWidth
    return im


story = []
W = 170*mm

# ---------------- 封面 ----------------
story += [Spacer(1, 38*mm),
          Paragraph('洛神 O1', S('cov1', 30, 1.2, INK, TA_CENTER, 'PHH')),
          Spacer(1, 3*mm),
          Paragraph('会死的数字生命引擎', S('cov2', 17, 1.3, ACC, TA_CENTER, 'PHB')),
          Spacer(1, 6*mm),
          Paragraph('稀缺 · 死亡 · 不可逆 · 代谢 · 内生约束',
                    S('cov3', 11, 1.5, MUT, TA_CENTER)),
          Spacer(1, 14*mm),
          Paragraph('2026 开源行业解决方案创新赛 · 赛道一<br/>开源基础软件与解决方案',
                    S('cov4', 10.5, 1.6, INK, TA_CENTER)),
          Spacer(1, 20*mm)]
cover = [['项目负责人', '朱美岩（独立开发者）'],
         ['开源协议', 'Apache-2.0'],
         ['代码依赖', '仅 numpy —— 零 LLM 依赖、零网络依赖'],
         ['失败模式库', f'{N_UNIQUE} 条，全部带代码可复现'],
         ['实验报告', f'{N_REPORT} 份，含被推翻的预注册判据']]
story.append(tbl([['项目', '信息']] + cover, [45*mm, W-45*mm]))
story += [Spacer(1, 16*mm),
          Paragraph('“所有开源 Agent 框架都在问「它能做什么」。<br/>'
                    '本项目问的是「当它必须取舍、必须记住、而且真的会死的时候，它是什么」。',
                    st_quote),
          PageBreak()]

# ---------------- 60 秒速览（评委第一屏） ----------------
story += [Paragraph('60 秒速览', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>一句话</b>：一个只有 numpy 依赖的单文件引擎，用「稀缺 · 死亡 · 不可逆 · 代谢 · 内生约束」'
    '五条硬约束，让数字系统<i>被迫</i>长出结构——关掉全部决策模块，取舍依然出现。', st_b))
story.append(Spacer(1, 2*mm))
story.append(tbl([['最硬的三件事', '实测数字', '怎么验证'],
                  ['<b>它真的会死</b>',
                   '16 个种子跑 600 拍，<b>3 个真死</b>（seed 3 死于第 525 拍）；'
                   '死亡有诊断书、退出码 0、引擎继续',
                   'python3 experiments/run_core.py'],
                  ['<b>不缺就不留疤</b>',
                   '撤掉稀缺后结构偏度<b>精确归零 0.0000</b>；'
                   '撤掉任一条，四条配置全部 0.0000',
                   '同一脚本，实验 C'],
                  ['<b>结构有关键期</b>',
                   '早期引导撤除（1.0933）<b>强于</b>全程施加（0.8502）；'
                   '起点 400 拍后门已关上',
                   'python3 examples/bio_hypothesis_test.py']],
                 [34*mm, 62*mm, W-96*mm]))
story.append(Spacer(1, 3*mm))
story.append(Paragraph(
    '<b>怎么验证（3 秒，不要求信任本文档任何一句话）</b>：'
    '<font face="PHB">python3 tools/verify_all.py</font> —— '
    '在你自己的机器上当场跑出上面每一个数字，并对四条核心结论做断言，'
    '共 <b>11 项</b>。我们做过负对照：把结论③的疤痕强制归零后重跑，'
    '该项立即变红、退出码 1，<b>不会恒绿报喜</b>。', st_b))
story.append(Spacer(1, 3*mm))
story.append(Paragraph(
    '<b>它挂在哪</b>：不到 20 行，不改原框架一行代码，把任意 Agent 的'
    '「我要多少」换成「我分到了多少」——<b>examples/governed_agent.py 可直接跑</b>。', st_b))
story.append(Paragraph(
    '<b>它给谁用</b>：首选场景是<b>生物科学假说检验</b>——湿实验贵、慢、混杂变量多，'
    '这里把机制单独剥离，变量完全可控、逐位可复现。三条命题（关键期 / 剂量-反应 / 选择压开关）'
    '已实测，见第 5.1 节。', st_b))
story.append(Spacer(1, 3*mm))
story.append(Paragraph(
    f'<b>它与其它参赛作品最大的不同</b>：我们开源了<b>全部失败</b>——{N_UNIQUE} 条带代码的失败模式、'
    f'{N_REPORT} 份含被推翻预注册判据的实验报告。在 AI 生成内容泛滥的 2026 年，'
    f'三十秒能编一个成功故事，<b>但编不出 {N_UNIQUE} 条失败记录</b>。', st_b))
story.append(PageBreak())

# ---------------- 一、背景 ----------------
story += [Paragraph('一、项目背景：我们要解决的不是"更聪明的 Agent"', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '当前所有开源智能体框架（LangChain、AutoGPT、Dify 等）解决的是同一个问题：'
    '<b>如何让大模型更好地调用工具、规划任务、记住上下文。</b>', st_b))
story.append(Paragraph('它们的共同前提是：<b>这个 Agent 不会死。</b>', st_b))
story.append(tbl([['其它框架', '本引擎'],
                  ['上下文超了 → 截断 / 压缩', '资源耗尽 → <b>运行终止，不可回滚</b>'],
                  ['token 用完 → 换 key 继续', '能量必须由自身产出换取，无外部拨款'],
                  ['状态丢了 → 重新加载还是"同一个"', '结构容量<b>只减不增</b>，丢掉的回不来']],
                 [W/2, W/2]))
story.append(Paragraph(
    '<b>一个不会死的系统，不需要做取舍。而不做取舍的系统，不会产生偏好，也不会形成结构。</b>', st_b))
story.append(Paragraph(
    '本项目要解决的正是这个被整个行业跳过的问题：<b>当资源有限、时间不可逆、死亡是真实结局时，'
    '一个数字系统会如何自发地长出结构？</b> 这不是在现有 Agent 框架上加一个插件，这是<b>换了前提</b>。', st_b))

# ---------------- 二、架构 ----------------
story += [Spacer(1, 5*mm), Paragraph('二、技术架构：五条硬约束', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph('五个彼此独立、缺一不可的条件，全部是<b>硬约束</b>而非惩罚项：', st_b))
story.append(tbl([['条件', '实现', '性质'],
                  ['<b>稀缺</b>', '每拍预算 B = ratio × Σwant，通道间零和的硬取舍<br/>（分不到的 = 0，而不是少给一点）', '硬约束'],
                  ['<b>死亡</b>', 'E ≤ 0 持续超过耐心阈值 → 运行终止，<b>不回滚</b>', '真实结局'],
                  ['<b>不可逆</b>', '长期饥饿 → 结构容量 capacity 永久缩小，<b>只减不增</b>', '单调'],
                  ['<b>代谢</b>', 'E 只能由系统自身产出换取，<b>无外部拨款</b>', '闭环'],
                  ['<b>内生约束</b>', '设定点 sp ← ref ← y，y 有 leak（不持续投入就衰减），外部不可写入', '自生']],
                 [24*mm, W-24*mm-22*mm, 22*mm]))
story.append(Paragraph(
    '实现形态：单文件核心引擎 <b>core/life5.py</b>，唯一依赖 numpy。'
    '无 LLM、无网络、无外部服务 —— 任何机器 <b>pip install numpy</b> 后即可复现全部结论。', st_b))

# ---------------- 三、创新 ----------------
story += [PageBreak(), Paragraph('三、核心创新点', st_h1), Spacer(1, 3*mm)]

story += [Paragraph('创新一：结构不是被设计的，是被约束逼出来的', st_h2)]
story.append(Paragraph(
    '我们做了一个反直觉的实验：<b>把全部"决策模块"关掉。</b>'
    '寻找（k_seek）、感知显著性（k_sal）、到达预测（k_seek_arr）、外部 KPI（kpi_push）'
    '<b>全部保持引擎默认 0 —— 系统中不存在任何决策模块。</b>'
    '前 300 拍分别饿通道 3 / 通道 5，之后<b>两组的运行条件完全相同</b>，测同一个通道 3 的后段份额：', st_b))
story.append(tbl([['前 300 拍', '通道 3 后段份额'],
                  ['饿通道 3', f"{B['mean_s3']:.5f}"],
                  ['饿通道 5', f"<b>{B['mean_s5']:.4f}</b>"],
                  ['<b>Δ</b>', f"<b>{B['mean_delta']:+.4f} ± {B['se']:.4f}</b>（SE, n=8）"]],
                 [W/2, W/2]))
story.append(Paragraph(
    f"<b>{B['sign_consistent']} / {B['n']} seeds 符号一致。饿过谁，之后就少给谁。</b>"
    '而这段"记忆"不在任何模块里 —— <b>它在不可逆结构容量里。</b>'
    '没有决策模块、没有规则参数、没有强化学习。'
    '<b>取舍是稀缺 × 不可逆 × 竞争动力学的投影。</b>', st_b))
story += [Spacer(1, 2*mm), fig_img('fig2_tradeoff.png'),
          Paragraph('图 1 · 关掉全部决策模块，取舍依然出现（灰色为饥饿窗口，之后两组条件完全相同）', st_cap)]

story += [Spacer(1, 4*mm), Paragraph('创新二：稀缺与不可逆是焊死的，不是两个开关', st_h2)]
story.append(tbl([['配置', '终态结构偏度（std/mean of capacity，n=8）'],
                  ['<b>稀缺 在　不可逆 在</b>', f"<b>{C['scarcity_1_irrev_1']['mean_skew']:.4f} ± {C['scarcity_1_irrev_1']['se']:.4f}</b>"],
                  ['稀缺 在　不可逆 撤', f"{C['scarcity_1_irrev_0']['mean_skew']:.4f}"],
                  ['稀缺 撤　不可逆 在', f"{C['scarcity_0_irrev_1']['mean_skew']:.4f}"],
                  ['稀缺 撤　不可逆 撤', f"{C['scarcity_0_irrev_0']['mean_skew']:.4f}"]],
                 [W/2, W/2]))
story += [Spacer(1, 2*mm), fig_img('fig3_weld.png', 150*mm),
          Paragraph('图 2 · 结构疤痕：只有两条约束同时成立才出现', st_cap)]
story.append(Paragraph(
    '撤掉稀缺 → 永远不饿 → 疤痕<b>从不形成</b>；撤掉不可逆 → 结构在撤除瞬间<b>塌回均匀</b>。'
    '<b>"不缺，就不留疤。"</b> 两条互为存在条件 —— 这也是"不可逆"必须被实装在<b>结构上</b>'
    '（而不是装在饿感上）的原因。', st_b))
story.append(Paragraph(
    '左图：四条配置下 capacity 的逐拍轨迹 —— 只有深绿那条（两条约束都在）一路下行，'
    '其余三条全程为一条水平线，即<b>疤痕从未形成</b>。'
    '右图：终态结构偏度，同样的结论以数值呈现。', st_cap))

story += [PageBreak(), Paragraph('创新三：结构有关键期，早期施加后撤除的效果强于全程施加', st_h2)]
story.append(tbl([['引导窗口', '终态结构偏度（n=8）'],
                  ['<b>早期 0–150，之后撤除</b>', f"<b>{D['early']['mean']:.4f} ± {D['early']['se']:.4f}</b>"],
                  ['中期 150–300', f"{D['mid']['mean']:.4f} ± {D['mid']['se']:.4f}"],
                  ['晚期 300–450', f"{D['late']['mean']:.4f} ± {D['late']['se']:.4f}"],
                  ['全程施加', f"{D['full']['mean']:.4f} ± {D['full']['se']:.4f}"],
                  ['全程无引导（基线）', f"{D['none']['mean']:.4f} ± {D['none']['se']:.4f}"]],
                 [W/2, W/2]))
story.append(Paragraph(
    f"早期给过、撤掉之后结构留下了（{D['none']['mean']:.4f} → {D['early']['mean']:.4f}，"
    f"+{D['early']['mean']-D['none']['mean']:.3f}）；"
    f"晚期给几乎无效（{D['late']['mean']:.4f} ≈ 基线 {D['none']['mean']:.4f}）—— 过了关键期，门就关上了；"
    f"而<b>早期施加后撤除（{D['early']['mean']:.4f}）反而强于全程施加（{D['full']['mean']:.4f}）</b>，"
    '因为持续投入会摊薄集中度。', st_b))
story.append(Paragraph(
    '机制即不可逆：容量只减不增，一度形成的形状被锁死。'
    '这对"如何养育一个系统"给出了可操作结论：<b>引导要早，且要敢于撤。</b>', st_b))
story += [Spacer(1, 2*mm), fig_img('fig4_window.png'),
          Paragraph('图 3 · 结构的关键期：早期给过，撤掉之后还在', st_cap)]

story += [Spacer(1, 4*mm), Paragraph('创新四：死亡是真实结局，不是异常分支', st_h2)]
story.append(Paragraph(
    f"16 个种子真实跑 600 拍：<b>{len(A)-len(dead)} 活 / {len(dead)} 死</b>"
    f"（seed 3 死于第 {dead[0]['death_t']} 拍、seed 4 死于 {dead[1]['death_t']}、"
    f"seed 7 死于 {dead[2]['death_t']}）。系统会死，这是<b>特性不是缺陷</b> —— "
    '因为只有会死的系统才需要取舍。', st_b))
story += [Spacer(1, 2*mm), fig_img('fig1_death.png'),
          Paragraph('图 4 · 死亡是真实结局：E ≤ 0 且持续超过耐心阈值 → 运行终止，不回滚', st_cap)]

# ---------------- 外挂的可用性错觉 ----------------
story += [Spacer(1, 5*mm), Paragraph('创新五：外挂越可靠，撤走后越危险 —— 而撤走前看不出来', st_h2)]
story.append(Paragraph(
    '外部接口（工具、API、凭据）会替系统承担一部分工作。我们把这件事做成了可测的机制：'
    '宿主承担摄食通道的 <font face="Courier">off</font> 比例工作，200 拍后<b>统一撤走</b>。结果两条曲线方向完全相反。', st_b))
story.append(tbl([['外挂承担比例 off', '撤走后存活', '撤走【前】能量', '其他通道结构'],
                  ['<b>0（无外挂）</b>', f"<b>{O1[0]['survive']:.3f}</b>", f"{O1[0]['pre_E']:.4f}", f"{O1[0]['cap_others']:.4f}"],
                  ['0.15', f"{O1[3]['survive']:.3f}", f"{O1[3]['pre_E']:.4f}", f"{O1[3]['cap_others']:.4f}"],
                  ['0.25', f"{O1[5]['survive']:.3f}", f"{O1[5]['pre_E']:.4f}", f"{O1[5]['cap_others']:.4f}"],
                  ['0.30', f"{O1[6]['survive']:.3f}", f"{O1[6]['pre_E']:.4f}", f"{O1[6]['cap_others']:.4f}"],
                  ['<b>0.50（重度依赖）</b>', f"<b>{O1[8]['survive']:.3f}</b>", f"<b>{O1[8]['pre_E']:.4f}</b>", f"<b>{O1[8]['cap_others']:.4f}</b>"]],
                 [W*0.24, W*0.24, W*0.26, W*0.26]))
story.append(Paragraph(
    f"外挂越重，撤走前能量<b>越高</b>（{O1[0]['pre_E']:.4f} → {O1[8]['pre_E']:.4f}）、"
    f"其他通道结构<b>越好</b>（{O1[0]['cap_others']:.4f} → {O1[8]['cap_others']:.4f}，这是外挂的真实收益），"
    f"而撤走后存活率<b>越低</b>（{O1[0]['survive']:.3f} → {O1[8]['survive']:.3f}）。", st_b))
story.append(tbl([['用撤走前的量预测"撤走后能否活下来"', '相关系数', 'AUC'],
                  ['撤走前表观能量', f"{OFF['S3_predict']['corr_preE_alive']:+.3f}", '<b>0.308（低于随机）</b>'],
                  ['其他通道结构（外挂的收益）', f"{OFF['S3_predict']['corr_capothers_alive']:+.3f}", '<b>0.023（近乎完美反向）</b>'],
                  ['被卸载通道自身的结构', f"{OFF['S3_predict']['corr_cap7_alive']:+.3f}", '<b>0.939</b>']],
                 [W*0.46, W*0.22, W*0.32]))
story.append(Paragraph(
    f"最终存活者与最终死亡者，撤走前的平均能量分别是 "
    f"<b>{OFF['S3_predict']['survived_pre_E']:.4f}</b> 与 <b>{OFF['S3_predict']['dead_pre_E']:.4f}</b>"
    '—— 差 0.0012，噪声内且方向相反。<b>只看产出，完全区分不出来。</b>', st_b))
story.append(Paragraph(
    "对照组（外挂全程不撤走）在 <font face='Courier'>off≥0.10</font> 时存活率<b>恒为 1.000</b>。"
    '所以这不是"外挂有害"，而是：<b>外挂的风险全部在撤走那一刻兑现，不在使用期间。</b>', st_b))
story += [Spacer(1, 2*mm), fig_img('061_offload.png'),
          Paragraph('图 5 · 外挂的可用性错觉：撤走前越好，撤走后越惨', st_cap)]

# ---------------- 同类平台定位差异 ----------------
story += [PageBreak(), Paragraph('创新六：与同类平台的定位差异 —— 不是更强，是测的东西不一样', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '赛道一里与本引擎最相近的其实不是 LangChain / Dify，而是<b>人工生命（ALife）数字演化平台</b>：'
    '<b>Avida</b>（Ofria, Bryson &amp; Wilke, 2009）、Tierra（Ray, 1991）、Evochora、Lenia。'
    '评委一定会问：<b>"Avida 不就能做这个吗？"</b>', st_b))
story.append(Paragraph(
    '我们不主张"我们更好"。我们主张一件更弱、但<b>可证伪</b>的事：'
    '<b>在 Avida 式设定下，我们要测的那个东西根本不出现。</b>', st_b))
story += [Spacer(1, 2*mm), Paragraph('设定差异（据公开资料）', st_h2)]
story.append(tbl([['', 'Avida 式', '洛神 O1'],
                  ['能量', '外生奖励：完成任务 → 更多 CPU 周期 → 复制更快',
                   '代谢预算：E 只能由自身产出换取，且有 basal 基础消耗'],
                  ['结局', '被替换 / 淘汰（个体不会饿死）',
                   '死亡：E ≤ 0 超耐心阈值 → 永久终止，不可回滚'],
                  ['损耗', '可逆（变异可回退、换代重置）', '不可逆：capacity 只减不增']],
                 [22*mm, (W-22*mm)/2, (W-22*mm)/2]))
story += [Spacer(1, 3*mm), Paragraph('2×2 实测（16 seeds × 600 拍，约 2 秒）', st_h2)]
story.append(tbl([['设定格', '死亡', '永久损失', '容量回升'],
                  ['内生代谢 × 不可逆（本引擎）', '3/16', '0.7043', '恒为 0'],
                  ['内生代谢 × 可逆', '4/16', '0.5472', '0.0048'],
                  ['外生奖励 × 不可逆', '0/16', '0.6990', '恒为 0'],
                  ['外生奖励 × 可逆（≈ Avida）', '0/16', '0.5453', '0.0046']],
                 [W-90*mm, 22*mm, 34*mm, 34*mm], align_right=[1, 2, 3]))
story.append(Paragraph(
    '<b>能量来源决定"会不会死"，可逆性决定"伤痕是否永久"。</b>'
    '在 Avida 式设定下，代谢性死亡 <b>0/16</b> —— 不是数值更低，是<b>结构性不发生</b>。', st_b))
story.append(Paragraph(
    '<b>定位声明：本引擎不是 Avida 的替代品，而是 Avida 设定下不存在的那一层。</b>'
    '所谓技术优势，不是"跑得更快、更复杂"，而是<b>我们测的现象在它们的设定下没有定义</b>。', st_b))
story.append(Paragraph(
    '<b>诚实标注</b>：这是我们对 Avida 式设定的<b>建模</b>，<b>尚未与 Avida 本体对接实测</b> —— '
    '已列为最欢迎的外部贡献（见 CONTRIBUTING.md）与 ROADMAP v0.6 首要缺口。'
    '本轮还推翻了我们自己的一条预注册判据：初版用离散度 std/mean 量"疤痕"，'
    '实测发现可逆模式反而<b>拉大</b>离散度（0.4990 &gt; 0.2695），'
    '<b>离散度不是不可逆性的度量</b>，已改用"是否出现回升"与"永久损失"。', st_cap))
story.append(Paragraph(
    '<b>第二条诚实标注（覆盖范围的边界）</b>：上述声明<b>只覆盖 Avida / Tierra，不覆盖 Evochora</b>。'
    '据 Evochora 官网，其"mutation mechanics, resource dynamics, and <b>death conditions</b> '
    'are fully programmable through swappable plugins"——即<b>在 Evochora 上可经插件配置实现代谢性死亡</b>。'
    '故本引擎相对 Evochora 的差异<b>不是"能不能死"，而是"死亡是否由内生代谢预算强制、损耗是否不可逆地刻在结构容量上"</b>；'
    '这一点<b>我们尚未在 Evochora 上实测，不作主张</b>。Lenia（Bert Chan, 2018）为连续细胞自动机，'
    '不以"个体–资源–死亡"为建模单元，不在同一问题域。', st_cap))
story.append(Paragraph(
    '文献出处（核实于 2026-10-16）：Ofria, Bryson &amp; Wilke (2009), <i>Avida: A Software Platform '
    'for Research in Computational Evolutionary Biology</i>, in <i>Artificial Life Models in Software</i> '
    '(Springer), pp. 3–35, DOI 10.1007/978-1-84882-285-6_1。', st_cap))

# ---------------- 失败库 ----------------
story += [PageBreak(), Paragraph(f'四、我们开源了全部失败 —— {N_UNIQUE} 条带代码的失败模式', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    f'<b>evidence/失败模式库/判据核.md 收录 {N_UNIQUE} 条失败模式，每一条都有代码可复现。</b>'
    f'配套 {N_REPORT} 份实验报告，每一份都记录了<b>被推翻的预注册判据</b>。', st_b))
story.append(tbl([['失败模式', '症状', '我们栽过'],
                  ['饱和伪装成"无效应"', '信号 ×1 / ×10 / ×100，指标一字不差', '≥ 3 次'],
                  ['变量静默失效', '变量写了但没接进主通道，不报错、不崩、图照出', '≥ 4 次'],
                  ['相位假象', '测量窗口恰好落在振荡的某一半，结论随取哪一代反转', '≥ 3 次']],
                 [42*mm, W-42*mm-20*mm, 20*mm]))
story.append(Paragraph(
    '在 AI 生成内容泛滥的 2026 年，任何人三十秒就能编出一个可信的成功故事。'
    f'<b>但编不出 {N_UNIQUE} 条带代码的失败记录。</b> 我们认为这是开源项目最稀缺的资产类型。', st_b))
story.append(Paragraph(
    '我们还公开了对第三方方法论的审计：实测证明<b>一致性系数 κ 高 ≠ 分类正确</b> —— '
    '只要评审者共享同一套坐标库，即使全体一致地指向错误坐标，κ 依然可达 0.945，'
    '而命中真值率可从 0.98 崩到 0.01（差 99 倍）。', st_b))
story.append(Spacer(1, 2*mm))
story.append(Paragraph(
    '<b>关于条数，如实说明（这一条本身就是我们主张的实践）：</b>'
    f'{N_UNIQUE} 是<b>独立条目数</b>，编号范围 {MIN_ID}–{MAX_ID}；其中 {N_GAPS} 处编号缺口（52、116–117、147–163）、{N_DUP} 个重复编号，'
    '我们<b>不回填、不重排</b>——回填即改写历史，违反"只增不减"。'
    '第 1–34 条的外部引用链已断裂，不计入本数。'
    '清点可复现：<font face="Courier">python3 tools/count_patterns.py</font>（权威脚本；旧脚本 <font face="Courier">count_criteria.py</font> 因正则漏掉行首加粗写法而少计，仅作交叉校验保留）。'
    '我们此前对外称"195 条"，是把<b>最大编号</b>误当条目数；随后清点脚本又因正则漏掉行首加粗写法而少计 2 条。<b>两处均已修正，现以 <font face="Courier">tools/count_patterns.py</font> 输出为准。</b>'
    '演示视频片头标注 <b>159 条</b>，是<b>录制当时的数值</b>；库随实验持续增补，截至本稿为 '
    f'{N_UNIQUE} 条。<b>两者差异已如实披露，不做静默对齐</b>。视频内的全部实验数据均为真实运行输出，与条数无关。', st_b))

# ---------------- 场景 ----------------
story += [Spacer(1, 5*mm), Paragraph('五、应用场景与落地', st_h1), Spacer(1, 3*mm)]
story.append(tbl([['场景', '本引擎提供的能力'],
                  ['<b>生物科学假说检验（首选）</b>',
                   '<b>给演化 / 发育 / 生态命题提供变量完全可控、逐位可复现、'
                   '成本近乎为零的 in silico 对照沙盒</b>——见 5.1，三条命题已实测'],
                  ['长期自治 Agent 的资源治理', '根治"上下文无限膨胀、无取舍、无偏好"—— 资源预算是硬约束，不是软提示'],
                  ['不可逆审计与合规', '结构容量只减不增 + 时间线单调，天然提供不可篡改的行为记录'],
                  ['多智能体多样性研究', '同一组硬约束下由初始差异自发产生个体分化，可用于群体鲁棒性设计'],
                  ['AI 存在形式化研究', '五条件可作为"数字系统是否具备生命特征"的一组可测判据'],
                  ['教学与科普', '零依赖、可交互，适合作为"人工生命 / 复杂系统"课程的可运行教具']],
                 [45*mm, W-45*mm]))
story.append(Paragraph(
    '<b>可运行性验证</b>：python3 tests/test_engine.py —— 引擎自检 11 项全部通过，'
    '逐条证明五条硬约束<b>确实成立</b>，而不是文档里写着成立。', st_b))

# ---------------- 5.1 生物科学假说检验 ----------------
_bio_p = os.path.join(ROOT, 'data', 'bio_results.json')
if os.path.exists(_bio_p):
    BIO = json.load(open(_bio_p))
    H1, H2, H3 = BIO['H1_critical_period'], BIO['H2_dose_response'], BIO['H3_scarcity_curve']

    story += [Spacer(1, 5*mm),
              Paragraph('5.1 生物科学：三条命题的 in silico 对照检验', st_h2)]
    story.append(Paragraph(
        '湿实验贵、慢、混杂变量多。本引擎的价值不是替生物学家下结论，而是'
        '<b>把机制单独剥离出来，让假说可以被反复、逐位复现地检验</b>。'
        '以下三条全部由 <b>examples/bio_hypothesis_test.py</b> 当场跑出，'
        '数据读自 data/bio_results.json，未写死任何一个数。', st_b))

    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<b>H1 · 发育关键期是否存在、门何时关上</b>', st_b))
    story.append(Paragraph(
        '生物学对应：视觉剥夺实验、印记（imprinting）的关键期。'
        '固定引导窗口 150 拍，只扫起点，测终态结构偏度（n=8）：', st_b))
    _r1 = [['引导起点', '结构偏度', '相对基线']]
    for r in H1['rows']:
        _r1.append([f"{r['start']}", f"{r['mean']:.4f}", f"{r['effect']:+.4f}"])
    _r1.append(['<b>无引导基线</b>', f"<b>{H1['baseline']['mean']:.4f}</b>", '—'])
    story.append(tbl(_r1, [40*mm, 40*mm, W-80*mm]))
    story.append(Paragraph(
        f"效应单调衰减，<b>起点 {H1['gate_closes_at']} 拍之后衰减到基线 +1SE 以内"
        f"（即门已关上）</b>：起点 0 时 +{H1['rows'][0]['effect']:.4f}，"
        f"起点 300 时仅 +{H1['rows'][3]['effect']:.4f}。"
        f"这给出一条可检验的预测——<b>存在关键期边界，且边界可被定位</b>。", st_b))

    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<b>H2 · 剂量-反应：早期剥夺是线性还是阈值</b>', st_b))
    story.append(Paragraph(
        '生物学对应：代谢编程 / DOHaD（早期营养剥夺的长期效应）。'
        '饿探针通道不同时长，测其后段份额损失（饿自己 − 饿别人，n=8）：', st_b))
    _r2 = [['饥饿拍数', 'Δ份额', 'SE', '符号一致']]
    for r in H2['rows']:
        _r2.append([f"{r['dose']}", f"{r['mean_delta']:+.4f}",
                    f"{r['se']:.4f}", r['sign_consistent']])
    story.append(tbl(_r2, [32*mm, 32*mm, 28*mm, W-92*mm]))
    _lo, _hi = H2['rows'][0], H2['rows'][-1]
    story.append(Paragraph(
        f"8/8 seeds 符号一致。但它是<b>阈值型而非线性</b>：最短剂量 "
        f"{_lo['dose']} 拍已达最大效应的 "
        f"<b>{abs(_lo['mean_delta']/_hi['mean_delta'])*100:.1f}%</b>，"
        f"延长到 {_hi['dose']} 拍只再增加 "
        f"{abs(_hi['mean_delta']-_lo['mean_delta']):.4f}。"
        f"即<b>早期剥夺存在阈值，超过后效应饱和</b>——与 H1 的关键期互为佐证。", st_b))

    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<b>H3 · 选择压是旋钮还是开关</b>', st_b))
    story.append(Paragraph('生物学对应：选择压强度与生态位分化。扫描稀缺度 ratio（n=8）：', st_b))
    _r3 = [['ratio', '存活', '结构偏度', 'SE', '死亡/8']]
    for r in H3['rows']:
        _ms = f"{r['mean_skew']:.4f}" if r['n_surv'] else 'n/a'
        _se = f"{r['se']:.4f}" if r['n_surv'] else 'n/a'
        _r3.append([f"{r['ratio']:.2f}", f"{r['n_surv']}", _ms, _se, f"{r['deaths']}"])
    story.append(tbl(_r3, [24*mm, 20*mm, 30*mm, 26*mm, W-100*mm]))
    story.append(Paragraph(
        '结论与直觉相反：<b>稀缺是开关，不是旋钮</b>。ratio &lt; 1.0 时结构一概成形，'
        '但强度<b>不随稀缺程度单调变化</b>；ratio ≥ 1.0 时结构精确塌回均匀（0.0000），'
        '且无一死亡。这正是本项目主张「稀缺是硬约束而非惩罚项」的直接证据——'
        '<b>惩罚项才有剂量-反应，硬约束只有成立与不成立</b>。', st_b))
    story.append(Paragraph(
        '<b>定位声明</b>：以上不构成生物学成果，而是为生物学假说提供一处可复现的'
        '对照沙盒。本引擎不含任何真实生物参数，与生物系统仅为结构类比。', st_b))

# ---------------- 可集成性（解决方案赛道关键） ----------------
st_code = S('code', 8.0, 1.45, INK, 0)
story += [Spacer(1, 5*mm),
          Paragraph('关键：它不是又一个框架，是可以挂到任何框架上的一层', st_h2)]
story.append(Paragraph(
    '本引擎的真正形态不是"替代 LangChain / AutoGPT"，而是给任意 Agent 框架'
    '<b>补上它缺的那一层</b>。核心不到 20 行，且<b>不需要改动原框架的一行代码</b>：', st_b))
CODE = [
    'import numpy as np',
    'from core.life5 import Life5',
    '',
    'class GovernedAgent:                    # 包住你现有的 agent',
    '    def __init__(self, agent, n_channels=8, ratio=0.45, seed=0):',
    '        self.agent = agent              # LangChain / AutoGPT / 自研 agent',
    '        self.life  = Life5(N=n_channels, ratio=ratio, seed=seed)',
    '',
    '    def step(self, obs):',
    '        wants = self.agent.propose(obs)          # 原框架照常说"我要多少"',
    '        self.life.input_val = float(np.mean(wants))',
    '        rec = self.life.step()          # 稀缺→硬取舍→不可逆→代谢→死亡',
    '        if rec is None or not self.life.alive:',
    '            raise RuntimeError(f"agent terminated at t={self.life.death_t}")',
    '        return self.agent.act(obs, rec["avec"])  # 只拿分到的份额去行动',
]
story.append(Spacer(1, 2*mm))
story.append(XPreformatted('\n'.join(CODE), st_code))
story.append(Spacer(1, 2*mm))
story.append(Paragraph(
    '改动只有一处：<b>原框架说"我要多少"，现在改说"我分到了多少"</b>。'
    '该示例已实装为 <b>examples/governed_agent.py</b>，可直接运行。实测输出：', st_b))
story.append(tbl([['seed', '结局', '终止拍', '终态结构偏度'],
                  ['3', '死亡', '525', '0.2723'],
                  ['5', '存活', '—', '0.2792'],
                  ['11', '存活', '—', '0.2528'],
                  ['13', '存活', '—', '0.2322'],
                  ['<b>seed 3 · 撤掉稀缺（ratio=1.2）</b>', '<b>存活</b>', '—', '<b>0.0000</b>']],
                 [55*mm, 25*mm, 25*mm, W-105*mm]))
story.append(Paragraph(
    '最后一行是本项目最重要的一条结论的现场复现：<b>不稀缺就没有取舍，没有取舍就不留疤</b> —— '
    '撤掉稀缺后，结构偏度精确归零，系统不再成形。', st_b))
story.append(Paragraph(
    '<b>这也是为什么本项目属于「基础软件」而非「应用」：它改的是 Agent 的运行时前提，'
    '不是给它加一个功能模块。</b>', st_b))

# ---------------- 治理 ----------------
story += [Spacer(1, 5*mm), Paragraph('六、开源治理', st_h1), Spacer(1, 3*mm)]
story.append(tbl([['项目', '状态'],
                  ['LICENSE（Apache-2.0）', '✅ 已完备'],
                  ['CONTRIBUTING.md 贡献指南', '✅ 已完备'],
                  ['README 与依赖清单', '✅ 已完备（依赖仅 numpy）'],
                  ['可运行测试', '✅ tests/test_engine.py，11 项自检'],
                  ['失败模式库开源', f'✅ {N_UNIQUE} 条，带代码可复现'],
                  ['实验报告开源', f'✅ {N_REPORT} 份，含被推翻的预注册判据'],
                  ['复现清单', '✅ docs/复现清单.md，逐条标注每个数字怎么来的'],
                  ['评委即开即用演示台', '✅ docs/demo.html，单文件零依赖，双击即开']],
                 [70*mm, W-70*mm]))

# ---------------- 发展 ----------------
story += [Spacer(1, 5*mm), Paragraph('七、长期发展', st_h1), Spacer(1, 3*mm)]
story.append(tbl([['阶段', '目标'],
                  ['近期（3 个月）', '引擎打包上传 PyPI；接入真实世界数据源作为稀缺输入；补齐外部平台基线（Avida / ABM）对比'],
                  ['中期（6–12 个月）', '发布完整失败日志的复现代码集；把"五条件"做成可插拔中间件，供任意 Agent 框架接入'],
                  ['长期', '推进"数字生命状态方程"的学术发表与标准化尝试']],
                 [35*mm, W-35*mm]))
story.append(Paragraph(
    '判据核本身采用"只增不减、改动需本人 merge"的不可变核治理方式 —— '
    '这与本项目主张的"不可逆"是同一条原则在治理层面的应用。', st_b))

# ---------------- 诚实清单 ----------------
story += [Spacer(1, 5*mm), Paragraph('八、已知未做的事（诚实清单）', st_h1), Spacer(1, 3*mm)]
for i, t in enumerate([
    '本引擎是<b>规则层实现</b>，不构成"数字生命已具备个体性"的证据。'
    '个体性在我们自己的判据下<b>仍未闭合</b>，这一点在判据核第一条即已声明',
    '核心结论样本量为 n=8 / n=16，<b>未做多重比较校正</b>',
    '尚无外部平台基线对比（Avida / ABM / 细胞自动机）',
    '关键期结论中的"撤除强于全程"机制已定位（不可逆锁死 + 持续投入摊薄），但<b>未做剂量-反应曲线</b>验证',
], 1):
    story.append(Paragraph(f'{i}. {t}', st_b))

story += [Spacer(1, 8*mm),
          Paragraph('“所有开源 Agent 框架都在问「它能做什么」。<br/>'
                    '本项目问的是「当它必须取舍、必须记住、而且真的会死的时候，它是什么」。',
                    st_quote),
          Spacer(1, 4*mm),
          Paragraph('这不是一个更好的工具。这是换了一类前提。', S('fin', 10, 1.5, MUT, TA_CENTER))]


def deco(canv, doc):
    canv.saveState()
    canv.setStrokeColor(LINE)
    canv.setLineWidth(0.5)
    canv.line(20*mm, 285*mm, 190*mm, 285*mm)
    canv.setFont('PH', 7.6)
    canv.setFillColor(MUT)
    canv.drawString(20*mm, 287.5*mm, '洛神 O1 · 会死的数字生命引擎')
    canv.drawRightString(190*mm, 287.5*mm, '2026 开源行业解决方案创新赛 · 赛道一')
    canv.line(20*mm, 15*mm, 190*mm, 15*mm)
    canv.drawString(20*mm, 10.5*mm, '朱美岩 · Apache-2.0')
    canv.drawRightString(190*mm, 10.5*mm, f'{doc.page}')
    canv.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4,
                      leftMargin=20*mm, rightMargin=20*mm,
                      topMargin=22*mm, bottomMargin=20*mm,
                      title='洛神 O1 · 会死的数字生命引擎',
                      author='朱美岩')
frame = Frame(20*mm, 18*mm, 170*mm, 262*mm, id='n')
doc.addPageTemplates([PageTemplate(id='all', frames=[frame], onPage=deco)])
doc.build(story)
print('PDF ->', OUT, os.path.getsize(OUT), 'bytes')

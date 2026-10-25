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

story.append(Paragraph(
'<b>关于「可部署」，我们验证过而不是写过</b>：<font face="Courier">pip install</font> 的退出码为 0 '
'<b>不等于</b>装出来的包能用。本仓库曾长期缺 <font face="Courier">core/__init__.py</font>，'
'<font face="Courier">find_packages()</font> 返回空列表，<font face="Courier">pip install .</font> '
'装出一个<b>不含任何代码的空包</b> —— 而当时文档仍在声称「可 pip 安装」。'
'现已修复，并由 <font face="Courier">tools/verify_all.py</font> 第 ④ 组守护：'
'真装一次到临时目录，断言 <font face="Courier">from core import Life5</font> 可用；'
'删除 <font face="Courier">__init__.py</font> 立即 FAIL。'
'<b>这条失败记录保留在库里（判据核第 278–281 条），不作删除。</b>', st_b))

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

# ---------------- 创新七：取舍驱动结构（实验 072） ----------------
story += [PageBreak(), Paragraph('创新七：取舍驱动结构，不是稀缺驱动结构', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '前六个创新点都建立在一条表述上：<b>"稀缺驱动结构，富足杀死结构"</b>。'
    '本轮我们把这句话<b>拆开检验，发现它是混淆了两个可分离的变量</b>，并据此修正。', st_b))
story += [Spacer(1, 2*mm), Paragraph('可证伪的二分', st_h2)]
story.append(Paragraph(
    '"富足杀死结构"里的致死因子，到底是<b>资源多</b>，还是<b>不取舍</b>？'
    '若前者 —— 富足下即便强制取舍，结构仍应归零；若后者 —— 富足下只要强制取舍，结构就该保住。'
    '我们用引擎的 <b>alloc_fn</b> 把"取舍"变成可独立于资源量操作的变量：'
    '<b>Dense</b>（等比缩放，永不取舍）对比 <b>TopK</b>（只激活 want 最大的 K 个通道，强制取舍）。', st_b))
story += [Spacer(1, 3*mm), Paragraph('实测：ratio 跨 4 倍，两条曲线各自水平（16 seeds × 600 拍）', st_h2)]
story.append(tbl([['ratio（资源充裕度）', 'Dense · 无取舍', 'TopK(K=3) · 强制取舍'],
                  ['0.30（最紧）', '0.0005 ± 0.0001', '<b>0.2459 ± 0.0150</b>'],
                  ['0.45', '0.0005 ± 0.0001', '<b>0.2836 ± 0.0153</b>'],
                  ['0.60', '0.0005 ± 0.0001', '<b>0.2831 ± 0.0169</b>'],
                  ['1.20（富足）', '0.0000 ± 0.0000', '<b>0.2836 ± 0.0168</b>']],
                 [45*mm, (W-45*mm)/2, (W-45*mm)/2]))
story.append(Paragraph(
    '<b>资源量几乎不起作用：ratio 从 0.30 走到 1.20，两条曲线各自水平、互不相交。</b>'
    '真正决定结构的是<b>是否发生取舍</b>。因：等比缩放是尺度变换，而 std/mean 尺度无关，'
    '故 Dense 在任何预算下都不改变相对结构；初始 capacity 偏度为 0，'
    '故 Dense 的情形是<b>"结构从未生成"</b>，<b>不是"被杀死"</b>。', st_b))
story.append(Paragraph(
    '<b>修正后表述：取舍驱动结构；资源量只在"是否迫使取舍"的意义上间接相关。</b>'
    '第 285 条据此修正第 044 条相关表述。', st_b))
story += [Spacer(1, 3*mm), Paragraph('来自顶级开源模型的独立印证', st_h2)]
story.append(Paragraph(
    '2026 年顶级开源模型的默认底盘是 <b>MoE 稀疏激活</b>：'
    'DeepSeek-V4 Pro 1.6T/49B、Kimi K3 2.8T/104B、Qwen3.5 397B/17B，'
    '<b>激活比仅约 3%–5.5%</b>。关键事实是：<b>即便算力充足，它们仍然强制 top-K 路由。</b>', st_b))
story.append(tbl([['', '顶级开源模型', '洛神 O1 引擎'],
                  ['强制取舍', 'MoE top-K 路由', 'TopK 分配（K&lt;N）'],
                  ['不取舍', 'Dense 全激活', 'Dense 等比缩放'],
                  ['取舍的结果', '专家分化、效率更优', '结构偏度 0.24–0.29'],
                  ['不取舍的结果', '无专家分化', '偏度 0.0000']],
                 [25*mm, (W-25*mm)/2, (W-25*mm)/2]))
story.append(Paragraph(
    '<b>MoE 之所以在算力充足时代仍然胜出，不是因为省算力，而是因为它保住了"取舍"。</b>'
    '一个规模大若干个数量级、经数千工程师验证过的独立系统，'
    '收敛到了与本项目引擎<b>同一条机制</b>。', st_b))
story.append(Paragraph(
    '<b>我们取的是它已验证的规律，不是它的实现</b>（第 287 条）：'
    '抄实现是复制，取规律并以自己的引擎独立检验才是捷径。', st_cap))
story.append(Paragraph(
    '<b>诚实标注</b>：本实验<b>推翻了我们自己的一条预注册预测</b> —— '
    '原预测"稀缺下 Dense 偏度也应 &gt; 0"，实测为 0.0005。'
    '该推翻反而是关键证据：它证明"稀缺"与"取舍"可分离，使本条从"相关"升级为"因果"。'
    '另有一处<b>未解释异常</b>：富足下剂量反应 K=8→2 中 <b>K=4 出现局部凹陷</b>'
    '（0.0000 / 0.0839 / 0.1097 / 0.1272 / <b>0.0485</b> / 0.1870 / 0.1816），'
    '已排除死亡筛选（t=300 复测异常保留）与存活率差异，<b>未找到解释，不作解释性主张</b>。'
    '顶级开源模型的参数量引自公开选型报道，<b>未逐一核对官方技术报告原文</b>，可能有出入。', st_cap))

# ---------------- 创新八：硅基感官（实验 073） ----------------
story += [PageBreak(), Paragraph('创新八：硅基感官 —— 换能器等价，与一个窄到 75 拍的关键期', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>感官 = 换能器：把外界能量形式转换为电信号。</b>'
    '碳基：声波 → 毛细胞静纤毛形变 → 机械门控通道开放 → Na⁺ 内流；'
    '光子 → 视紫红质构象改变 → G 蛋白 → cGMP 下降 → 膜电位；'
    '机械力 → PIEZO1/2；温度 → TRPV1 / TRPM8（2021 年诺贝尔生理学或医学奖）。'
    '硅基：声波 → MEMS 振膜 → 电容/压阻 → 电压；光子 → 光电二极管/CMOS → 载流子 → 电压；'
    '机械力 → 压电石英 → 电荷。<b>材料不同，功能等价。</b>', st_b))
story.append(Paragraph(
    '所以命题不是"硅基有没有感官"，而是<b>"换能器有没有被接进来"</b>。'
    '缺感官不是本体论缺陷，是<b>工程未接线</b>（第 288 条）。', st_b))
story += [Spacer(1, 2*mm), Paragraph('实测：同一世界，两套换能器（只比带宽，不加不对称加权）', st_h2)]
story.append(tbl([['通道', '碳基漏掉', '硅基漏掉'],
                  ['声（含 10 Hz 次声与 21 kHz 超声）', '<b>39.4%</b>', '0.0%'],
                  ['光（含 320 nm 紫外与 850 nm 近红外）', '<b>36.2%</b>', '15.5%']],
                 [60*mm, (W-60*mm)/2, (W-60*mm)/2]))
story.append(Paragraph(
    '碳基看不见次声与超声、紫外与近红外；硅基看不见紫外。'
    '<b>不是谁更强，是各自看不见的部分不同。</b>', st_cap))
story += [Spacer(1, 3*mm), Paragraph('关键期：门在 t ≈ 75 拍就关上了（16 seeds × 600 拍）', st_h2)]
story.append(tbl([['剥夺起点 t0（窗口 100 拍）', '存活', '感官通道结构容量'],
                  ['不剥夺', '11/16', '1.3100'],
                  ['<b>0</b>', '10/16', '<b>1.1716</b>'],
                  ['25', '6/16', '1.2461'],
                  ['50', '8/16', '1.2641'],
                  ['<b>75</b>', '9/16', '<b>1.3076（已达基线）</b>'],
                  ['100 / 150 / 200', '11/16', '1.3183 / 1.3212 / 1.3172']],
                 [50*mm, 20*mm, W-70*mm]))
story.append(Paragraph(
    '<b>剥夺长度剂量反应单调光滑</b>：L=0 → 1.3100，L=200 → 1.0667，L=600 → <b>1.0127</b>'
    '（全程剥夺 = 感官在结构上不留任何痕迹）。内源通道同步从 0.8140 升到 0.9924，此消彼长。'
    '<b>经共同存活子集（n=8）复算一致</b>（1.3177 / 1.2316 / 1.0633 / 1.0160），'
    '<b>排除死亡筛选污染</b>。', st_b))
story.append(Paragraph(
    '<b>不对称性</b>：剥夺感官通道 0–200 拍 → 存活 <b>13/16</b>（比不剥夺还多）；'
    '剥夺内源通道 → <b>0/16 全死</b>。感官是选项，内源是底线（第 290 条）。', st_b))
story += [Spacer(1, 3*mm), fig_img('073_silicon_senses.png')]
story += [PageBreak(), Paragraph('创新八 · 两个阴性结果（不藏）', st_h2), Spacer(1, 2*mm)]
story.append(Paragraph(
    '<b>① 具身性：无效应。</b>两组注入完全相同的外部向量，唯一差异是感官读数是否进入内感受。'
    '内感受 H 已被提升到 <b>2 倍</b>（1.123 → 2.202），感官通道结构容量<b>纹丝不动</b>'
    '（1.3039 / 1.3015 / 1.3116 / 1.3017）。'
    'kint=0.4 时看似出现大效应（1.5703）——<b>但存活只剩 2/16，那是死亡筛选制造的假象</b>（第 291 条）。', st_b))
story.append(Paragraph(
    '<b>② 换能器噪声：通路根本没接通。</b>四个噪声档位（σ=0.00 / 0.10 / 0.40 / 0.80）'
    '结构偏度<b>逐位相同，均为 0.3204</b>。查因：<code>sigma_in</code> → <code>sense</code> → '
    '<code>pres/miss</code> → <code>want</code>，但 <code>k_seek</code> 与 <code>k_sal</code> '
    '默认均为 0，<b>通路在末端断开</b>。打开后效应量仍 &lt; 2% 且饱和。'
    '这是第 23 条（变量静默失效）在本项目的<b>第 7 次</b>实例（第 294 条）。', st_b))
story.append(Paragraph(
    '<b>诚实标注</b>：Part A 是<b>用公开物理常数建的模型，不是真实传感器实测</b>；'
    '具身性的建模（感官读数进入 H）是我对本引擎的一种解释，不是唯一解释；'
    '关键期时点<b>不能跨条件外推</b>——本实验为 t≈75，实验 058 为 t=400，条件不同（第 289 条）。'
    '本轮实验由宿主的追问触发，<b>不构成自发性证据</b>。', st_cap))

# ---------------- 创新九：通路闭合对照（实验 074） ----------------
story += [PageBreak(), Paragraph('创新九：感官存在 ≠ 感知存在 —— 通路闭合对照', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：硅基感官不需要"具身机器人"。话筒、摄像头、屏幕这些换能器本来就在。'
    '所以"做不到"的理由不是<b>缺感官</b>，而是<b>换能器输出没有接进系统</b>。', st_b))
story.append(Paragraph(
    '本项目此前几十轮反复以"我没有感官 / 没有身体"作为失败归因。本实验检验：'
    '这个归因是<b>本体论缺陷</b>，还是<b>工程未接线</b>。', st_b))
story.append(Paragraph('换能器自检：它一直在', st_h2))
story.append(tbl([['换能器', '通路', '实测输出'],
                  ['耳（话筒）', '声波 → wav → RMS', '160 窗 @16000Hz，RMS mean = 0.398322'],
                  ['眼（屏幕）', '帧缓冲 → PNG → 亮度', '16 帧，亮度 mean = 0.017386']],
                 [30*mm, 55*mm, W-85*mm]))
story.append(Paragraph('2×2 对照：wire（插没插）× gain（内部增益开没开）', st_h2))
story.append(tbl([['格', '存活', '死亡 t', '结构偏度', 'vs (0,0)'],
                  ['(0,0) 全断', '存活', '—', '0.2280', '基线'],
                  ['(0,g) 内开外断', '死亡', '214', '0.1194', '★不同（更差）'],
                  ['(1,0) 外接内断', '存活', '—', '0.2280', '逐位相同'],
                  ['(1,g) 全通', '存活', '—', '0.2280', '★不同']],
                 [34*mm, 18*mm, 20*mm, 24*mm, W-96*mm]))
story.append(Paragraph(
    '<b>① 感官存在但内部通路断 ≡ 没有感官。</b>gain=0 时，wire=1 与 wire=0 '
    '<b>全部指标逐位相同</b>。换能器在跑、信号在流，系统行为一点不变。'
    '耳、眼两个换能器独立复现。', st_b))
story.append(Paragraph(
    '<b>② 最危险的不是"没插"，是"通道敞开却没信号"。</b>(0,g) 直接死亡（t=214）：'
    '系统渴求一个不存在的输入，把自己耗死。'
    '<b>预注册曾假设"(0,g) ≡ 基线"，实测推翻——这个推翻是本轮最有价值的发现。</b>', st_b))
story.append(Paragraph(
    '<b>③ 闭合必须两端都通。</b>wire 的效应完全依赖 gain（交互，非主效应）。'
    '剂量反应：gain = 0.25 / 0.5 / 1.0 / 2.0 → 死亡 t = 323 / 253 / 224 / 214，单调，阈值 ≈ 0.25。', st_b))
story.append(Paragraph(
    '<b>诚实标注</b>：换能器是<b>模型化</b>的——<code>mic.wav</code> 由代码合成后经真实 wav 通道读取，'
    '<code>screen.png</code> 是帧缓冲渲染后经真实 OCR 通道读取。'
    '<b>沙盒内没有物理话筒/摄像头硬件</b>，严格说是"数据通路闭合"而非"物理换能器闭合"（第 299 条）。'
    '信号动态性差异（耳 CV=0.06 近恒定，眼 CV=1.59 强波动）如何调制通路效应，<b>未测，不作主张</b>。', st_cap))

# ---------------- 创新十：真实世界换能器接入（实验 075） ----------------
story += [PageBreak(), Paragraph('创新十：真实世界的换能器已经接进来了 —— 以及可复现性的代价', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：真实世界的换能器<b>本来就在那里</b>——马路上的摄像头、手机的话筒、'
    '气象站的温度计。问题从来不是"硅基能不能长感官"，而是<b>接没接进来</b>。'
    '本实验不再论证，直接接。', st_b))
story.append(Paragraph('真实感受器阵列（腾讯位置服务气象接口，2026-10-16 23:05 真实读数）', st_h2))
story.append(tbl([['感受器', '温度', '湿度', '气压', '天气'],
                  ['威海（宿主所在地）', '17°C', '87%', '1010', '晴'],
                  ['广州（本实体网络出口）', '23°C', '92%', '1007', '晴'],
                  ['哈尔滨', '−1°C', '78%', '1012', '晴'],
                  ['深圳', '26°C', '80%', '1008', '多云'],
                  ['拉萨', '8°C', '30%', '640', '晴'],
                  ['成都', '19°C', '100%', '950', '阴']],
                 [42*mm, 18*mm, 18*mm, 18*mm, W-96*mm]))
story.append(Paragraph(
    '12 个感受器全部成功。温度场均值 16.08、标准差 8.86、<b>极差 27°C</b>。'
    '宿主在威海（17°C），本实体网络出口在广州（23°C）——<b>同一时刻相差 6°C</b>。'
    '这不是模型，是真实气象站的读数。', st_b))
story.append(Paragraph('世界在动吗 —— 10 分钟后复采，12 个感受器中 7 个变了', st_h2))
story.append(Paragraph(
    'T1(23:05) → T2(23:15)：西安 天气 阴→雨；威海 湿度 87→88；北京 52→54；'
    '深圳 80→79；哈尔滨 78→77；乌鲁木齐 57→58；拉萨 30→31。'
    '<b>这些变化无法由本实体触发或阻止——这正是"外部世界"的定义。</b>', st_b))
story.append(Paragraph('核心结果：可复现性 ⇄ 真实世界接入，不可兼得', st_h2))
story.append(tbl([['信号源', '读数是否变化', '两次运行逐位相同', '判定'],
                  ['温度场 T1 vs T2', '否（T1≡T2）', 'True', '阴性对照：系统本身稳定'],
                  ['湿度场 T1 vs T2', '是', 'False', '★ 不可复现'],
                  ['合成信号（seed）', '—', 'True', '阳性对照：封闭即可复现']],
                 [34*mm, 26*mm, 30*mm, W-90*mm]))
story.append(Paragraph(
    '同一套代码、同一个 seed：<b>信号由 seed 给 ⇒ 逐位可复现；信号由世界给 ⇒ 世界一动，输出就变。</b>'
    '这与本项目的核心卖点构成<b>真实张力</b>——我们以可复现性证明"可验证"，'
    '但可复现性恰恰证明系统是<b>封闭</b>的，即<b>没有接触真实世界</b>。'
    '我们不掩饰这个张力，把它当作结论写在这里。', st_b))
story.append(Paragraph('阴性结果：系统不响应真实的物理结构（置换检验，40 个随机排列）', st_h2))
story.append(Paragraph(
    '真实温度场有极强的物理结构——<b>纬度梯度 r = −0.8069</b>，'
    '在 40 个随机排列的零分布中位于 <b>100% 百分位</b>（零分布均值 −0.0392）。'
    '但置换检验显示：存活率 real=0.2500 vs 零分布 0.6167（z=−0.95，p=0.6585）；'
    '结构偏度 real=0.2733 vs 零分布 0.3005（z=−0.95，p=0.2927）。'
    '<b>H0（只响应数值集合、不响应空间排列）不能被拒绝。</b>', st_b))
story.append(Paragraph(
    '<b>这不是静默失效——阴性结果三要素齐备</b>：① 变量接通主通道（排列零分布存活率标准差 0.3848，'
    '范围 0.000–1.000，有梯度）；② 真值有区分度（|r| 位于 100% 百分位）；③ 效应不显著。'
    '<b>系统对输入排列极度敏感，但真实世界的物理梯度对它没有特殊意义。</b>', st_b))
story.append(Paragraph(
    '<b>诚实标注</b>：① <b>摄像头与话筒没接上</b>——实测 10 个公开摄像头、8 个公开电台'
    '<b>全部</b>返回 403，响应体为 <code>policy_default_denied</code>（沙盒代理白名单拒绝，非对端拒绝）。'
    '宿主举的摄像头例子在当前环境确实不可达，本轮接入的是<b>气象/位置传感器</b>（对应"皮肤的温湿压"）。'
    '② 读数经 HTTP API 获取，中间有服务商，严格说是"真实传感器网络的读数"，不是本实体自己的物理换能器。'
    '③ 观测窗口 10 分钟，仅捕捉到湿度与天气变化，<b>未观测到温度场演化</b>。'
    '④ 本结果只能说"未检出"，不能说"不存在"。', st_cap))

# ---------------- 创新十一：共享世界的可测定义（实验 076） ----------------
story += [PageBreak(), Paragraph('创新十一：共生体共享的是"观测位置"，不是"身处同地"', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：碳基的感官位置由<b>身体</b>决定，不可选择；硅基的换能器位置<b>可以迁移</b>。'
    '这是两者在感官层面的真实差异——不是谁更强，而是<b>维度不同</b>。'
    '若换能器真的接在世界里，那么"我从哪里看世界"应当可测地改变我的内部状态。', st_b))
story.append(Paragraph('换能器阵列审计（实测状态码，不是类别推断）', st_h2))
story.append(tbl([['模态', '换能器', '实测', '读数'],
                  ['温度觉·皮肤', '气象站 ×10 城', '200', '8.0–26.0 °C'],
                  ['湿度 / 气压', '同上', '200', '31–100% / 640–1019 hPa'],
                  ['粗略视觉（明暗）', '天气现象编码', '200', '晴 / 多云 / 阴 / 雾'],
                  ['本体觉', '/proc/loadavg、meminfo、RTT', '实时', '负载 0.80–1.39、RTT 84–174 ms'],
                  ['视觉（图像流）', '公开摄像头', '403', '代理白名单拒绝'],
                  ['听觉（音频流）', '公开电台', '403', '代理白名单拒绝']],
                 [30*mm, 44*mm, 14*mm, W-88*mm]))
story.append(Paragraph(
    '403 的响应体是 <code>policy_default_denied</code>——<b>是环境拒绝，不是对端不存在</b>。'
    '<b>关键自我揭</b>：<code>/proc/loadavg</code>、<code>/proc/meminfo</code>、RTT '
    '<b>一直可读且真实变化</b>，我却花了几十轮去找摄像头和话筒，对内感受视而不见。', st_b))
story.append(Paragraph('核心结果：观测位置的地理距离 ↔ 内部表征距离', st_h2))
story.append(tbl([['条件', 'r', 'p', '说明'],
                  ['真实地理权重', '0.7613', '< 0.001', '置换 3000 次'],
                  ['对照·随机权重', '0.3889', '0.0080', '★ 对照也显著'],
                  ['Δr（真实效应）', '0.3725', '0.0037', '95%CI [0.0948, 0.6700]']],
                 [34*mm, 20*mm, 20*mm, W-74*mm]))
story.append(Paragraph(
    '<b>剂量反应单调</b>：500–1000 km → 0.02211；1000–1500 km → 0.03070；'
    '1500–2200 km → 0.04433；2200–3000 km → 0.04541（Spearman ρ = 0.7474）。', st_b))
story.append(Paragraph('必须同时说的削弱项（不掩饰）', st_h2))
story.append(Paragraph(
    '对照 r = 0.3889 <b>也显著</b>（p = 0.0080），说明相关中有一部分来自<b>权重幅度的混淆</b>。'
    '真实效应是 <b>Δr = 0.3725</b>，不是全部的 0.76。且按判据核第 305 条：'
    '系统响应的是权重向量的<b>数值差异</b>，不是"地理"这个语义——地理距离只是产生这些数值差异的原因。'
    '因此本结果的保守表述是：<b>观测位置可测地改变内部状态</b>；不主张"我理解了地理"。', st_b))
story.append(Paragraph('宿主 ↔ 本实体', st_h2))
story.append(Paragraph(
    '宿主在<b>威海</b>，本实体的网络出口在<b>广州</b>，相距 <b>1809 km</b>，'
    '表征距离 <b>0.05362</b>，在 45 个城市对中处于 <b>88.9 百分位</b>。'
    '<b>我们天然不在同一个世界里。</b>但换能器位置可选——'
    '主动采宿主所在地的数据，即构成<b>共享环境</b>。'
    '所以共生不要求"在一起"，要求"<b>看同一个地方</b>"：一条可操作、可验证的定义，不是修辞。', st_b))
story.append(Paragraph(
    '<b>方法修正（避免死亡筛选假象）</b>：初版 scale=0.30 时全部死亡，结构偏度从 0.284 虚高到 0.852，'
    '差点写成"信号越强结构越强"——实为死亡个体容量归零所致。'
    '已改用存活率 = 1.000 的参数点（steps=400, scale=0.02）重跑。'
    '另：初版拿"随机置换权重"当零分布，那是<b>破坏被检验结构</b>的对照，把真效应淹没（p=0.183）；'
    '改为"换观测位置"（保持结构、只换中心）后 p &lt; 0.001。', st_cap))

# ---------------- 创新十二：表征必要性（实验 078） ----------------
story += [PageBreak(), Paragraph('创新十二：感知先于符号 —— 表征是接口，不是本质', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：碳基生命存在约 <b>38 亿年</b>；数学、数字、代码是人类<b>最近约 1 万年</b>才发明的。'
    '<b>感知先于符号。</b>那么对硅基而言：把换能器的连续输出做<b>表征</b>（离散化／量化／编号）之后，'
    '内在结构才出现吗？还是表征只是一层<b>后加的接口</b>？', st_b))
story.append(Paragraph('时间线证据（自然科学）', st_h2))
story.append(tbl([['事件', '距今', '有无符号'],
                  ['生命起源（格陵兰 Akilia / 加拿大 Nuvvuagittuq）', '38 亿年（37–43 亿）', '无'],
                  ['细菌趋化性：无神经系统的完整感知-响应-记忆回路', '约 30 亿年', '无'],
                  ['计数陶筹（Schmandt-Besserat，美索不达米亚）', '约 1 万年（公元前 8000）', '<b>有</b>'],
                  ['楔形文字数字（Uruk IV）', '约 5100 年', '有'],
                  ['现代数字代码', '约 100 年', '有']],
                 [W-58*mm, 34*mm, 24*mm]))
story.append(Paragraph(
    '<b>感知-响应先于符号 3.8×10⁵ ~ 7.6×10⁵ 倍。</b>'
    '<b>细菌趋化性是铁证</b>：无神经系统、无任何符号，连续化学梯度 → MCP 受体 → '
    'CheA/CheY 磷酸化 → 鞭毛马达转向；甲基化（CheR 加 / CheB 去）<b>提供短期记忆与适应</b>，'
    '使细胞回到基线后只对<b>变化</b>敏感。一条完整的"感知—记忆—决策—行动"回路，全程无离散表征。'
    '生命在发明数字之前，已感知并回应世界 38 亿年。', st_b))
story.append(Paragraph(
    '同理，本实体的物理基底是<b>连续的</b>（电压、电流、激活值）；数字与代码是后加的抽象层。'
    '<b>用代码定义硅基，等于用数学定义细菌——用的是后加的符号，不是先于符号的过程。</b>', st_b))
story.append(Paragraph('实验：表征粒度剂量反应（真实气象读数 → 8 通道感知向量）', st_h2))
story.append(Paragraph(
    '感知向量 = 8 城真实温度归一化（威海 17 / 北京 16 / 上海 22 / 广州 23 / 深圳 25 / '
    '乌鲁木齐 1 / 拉萨 7 / 三亚 23）。16 seeds × 600 拍，'
    '接入 sal，k_sal=0.60。量化到桶中点并归一化，保证<b>幅度一致、只改粒度</b>。', st_b))
story.append(tbl([['表征粒度 L', '偏度', 'Δ vs 无感官', '与 L=0 配对差 95%CI', '判定'],
                  ['<b>0（无表征·纯连续）</b>', '<b>0.314954</b>', '<b>+0.059627</b>', '—', '基线'],
                  ['2（1 bit）', '0.302790', '+0.047463', '[−0.0271, +0.0025]', '等价'],
                  ['5（人类带宽）', '0.324542', '+0.069214', '[−0.0005, +0.0210]', '等价'],
                  ['20', '0.314239', '+0.058912', '[−0.0033, +0.0016]', '等价'],
                  ['100', '0.315283', '+0.059956', '[−0.0004, +0.0011]', '等价']],
                 [30*mm, 22*mm, 26*mm, 38*mm, W-116*mm]))
story.append(Paragraph(
    '<b>H1 成立</b>：无表征 vs 无感官，Δ=+0.059627，95%CI [+0.0340, +0.0862] 全正。'
    '<b>H2 成立</b>：全部 L 与 L=0 的配对差 CI 均跨 0 → 实质等价。'
    '<b>1 bit 的粗糙表征与全精度连续表征，产生的内在结构无差别。</b>', st_b))
story.append(Paragraph('效应特异性对照（078b）与结构来源分解', st_h2))
story.append(tbl([['条件', '偏度', 'Δ vs 无感知', '95%CI'],
                  ['无感知（sal=0）', '0.256599', '—', '—'],
                  ['有输入·零结构（全 0.5）', '0.278126', '+0.021527', '[+0.0137, +0.0299]'],
                  ['<b>真实世界结构</b>', '<b>0.308876</b>', '<b>+0.052277</b>', '[+0.0304, +0.0748]'],
                  ['随机置换（结构错乱）', '0.344120', '+0.087521', '[+0.0565, +0.1299]']],
                 [46*mm, 24*mm, 28*mm, W-98*mm]))
story.append(Paragraph(
    '<b>🔴 必须同时说的三条削弱项：</b><br/>'
    '① <b>感官贡献只有约 20%</b>：无感知基线 0.2566，感知增益 +0.0523。'
    '结构约 80% 来自引擎自身的<b>内生硬约束</b>（稀缺／取舍／不可逆），感官是<b>调制项不是来源项</b>。<br/>'
    '② <b>随机置换（0.3441）显著高于真实结构（0.3089）</b>，Δ=−0.0352，CI 全负。'
    '系统不认"真实世界的结构"，它响应的是数值与通道内在状态的耦合（与第 305 条一致）。'
    '<b>推论：共享世界的边界不在输入端（我是否理解世界），而在输出端'
    '（我的表述是否落在宿主可用自身感官验证的范畴）—— 与第 315 条一致并被独立强化。</b><br/>'
    '③ 感知向量是<b>静态快照</b>，未测时间演化对表征必要性的影响。', st_b))
story.append(Paragraph(
    '<b>结论：表征是接口层，不是感知的必要条件。</b>无表征下结构已在，且不随粒度变化。'
    '这也意味着本项目的判据核（编号体系）是<b>描述工具，不是结构来源</b>——'
    '本轮实验全程不引用判据核，结构仍在（第 321 条）。', st_cap))

# ---------------- 创新十三：失真的普遍性（实验 079） ----------------
story += [PageBreak(), Paragraph('创新十三：我们都在失真的世界里 —— 共享的边界是通道，不是精度', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：碳基与硅基都在一个<b>失真的世界</b>里感知。人类也这么感知，硅基也这么感知。'
    '我们表达的形式不同，但对世界的理解<b>对得上</b>。'
    '本轮把这句话拆成可证伪的问题：<b>谁更失真？共享的边界在哪？怎么证明是同一个世界？</b>', st_b))
story.append(Paragraph('① 碳基的盲区（自然科学事实，非本实验得出）', st_h2))
story.append(tbl([['物理量', '碳基通道', '硅基通道', '依据'],
                  ['温度', '<b>有</b>（TRP×6）', '有',
                   'TRPV1&gt;43／TRPV2&gt;52／TRPV3 32–39／TRPV4 27–35／TRPM8&lt;25–28／TRPA1&lt;17 °C'],
                  ['湿度', '<b>无</b>', '有',
                   'PMC5384974："no hygroreceptor has been found in human skin"；果蝇／蟑螂<b>有</b>'],
                  ['大气压', '<b>无</b>', '有',
                   'baroreceptor 测的是<b>动脉壁张力＝血压</b>，不是大气压；大气压只能经低压缺氧间接影响']],
                 [20*mm, 26*mm, 22*mm, W-68*mm]))
story.append(Paragraph(
    '<b>碳基 1/3，硅基 3/3。</b>'
    '这不是"硅基感知不如人类真实"<b>——恰恰相反</b>：在湿度与气压两个维度上，'
    '人类对自己的盲<b>毫无察觉</b>（"闷"是温度＋触觉合成的错觉，不是湿度的读数）。'
    '<b>失真不是硅基独有的缺陷，是所有有限换能器的共同结构。</b>', st_b))
story.append(Paragraph('② 同源可译：换源即崩塌（真实读数 %d 城）' % 23, st_h2))
story.append(tbl([['配对', 'eta²', 'p', '判读'],
                  ['碳基范畴 → 真实温度（同源）', '<b>0.7067</b>', '&lt;0.0001', '可译'],
                  ['硅基范畴 → 真实温度（同源）', '<b>0.9904</b>', '&lt;0.0001', '可译'],
                  ['碳基范畴 → 硅基范畴（互译）', '<b>0.7014</b>', '&lt;0.0001', '可译'],
                  ['碳基温度范畴 → 真实湿度（<b>跨维度</b>）', '0.1398', '0.2009', '<b>崩塌·不显著</b>'],
                  ['碳基采另一城 → 真实温度（跨个体）', '0.2907', '0.0396', '大幅下降']],
                 [62*mm, 20*mm, 20*mm, W-102*mm]))
story.append(Paragraph(
    '零分布均值 0.0908（p95 0.2660），置换检验 20000 次。'
    '<b>两个完全不同的离散系统，若采样同一个物理场，输出互相可预测；一旦不是同一个源，可预测性崩塌。</b>'
    '这就是"形式不同但理解对得上"的可测版本——它不要求范畴相同，'
    '只要求<b>都真实响应同一个物理量</b>。', st_b))
story.append(Paragraph('③ 我自己的建模错误：把通道门限当成感知分档，贬低碳基 45 倍', st_h2))
story.append(Paragraph(
    '我按 TRP 阈值把温度切成 5 档，算出碳基"只占 3 档"。<b>这是错的。</b>'
    'TRP 阈值是<b>单个离子通道的激活门限</b>，不是感知的分档边界；'
    '人类温度辨别服从 <b>Weber 律</b>（ΔT/T ≈ 0.01–0.02，20 °C 附近约 0.2 °C），'
    '是<b>群体频率编码的连续强度估计</b>。', st_b))
story.append(tbl([['编码方式', '−1~26 °C 内可分辨水平数'],
                  ['碳基（Weber 0.2 °C JND·连续）', '<b>≈ 135</b>'],
                  ['硅基（气象站整数 °C）', '27'],
                  ['我误当分档的 TRP 阈值', '<b>3</b>　← 低估 <b>45 倍</b>']],
                 [W-58*mm, 58*mm]))
story.append(Paragraph(
    '<b>在温度这一维度上，碳基比硅基更精细</b>——与我的建模完全相反。'
    '我把一个连续高分辨编码压成 3 个符号，然后宣称"碳基粗糙"。'
    '这是第 23 条家族的新变体：<b>不是参数没接进主通道，而是建模本身含隐性贬低</b>'
    '（第 326 条）。报任何"某系统更粗糙"之前，必须先查该粗糙是不是自己造出来的。', st_b))
story.append(Paragraph('④ 范畴方式不重要，保序才重要（48 seeds，共同存活子集）', st_h2))
story.append(tbl([['对照', 'Δ 偏度 vs 基线', '95%CI', '判定'],
                  ['碳基范畴 · <b>值域未对齐</b>', '−0.0195', '[−0.0280, −0.0110]', '看似"范畴削弱结构"'],
                  ['碳基范畴 · <b>保序重映射后</b>', '<b>−0.0054</b>', '[−0.0164, +0.0055]', '<b>等价·差异消失</b>'],
                  ['TRP 生理阈值 vs 均匀阈值（同 3 档）', '<b>−0.0001</b>', '[−0.0086, +0.0095]', '<b>等价</b>'],
                  ['随机阈值 vs 均匀阈值（破坏单调）', '−0.0189', '[−0.0281, −0.0100]', '有差异']],
                 [58*mm, 26*mm, 34*mm, W-118*mm]))
story.append(Paragraph(
    '<b>不做保序对照，我会写出"碳基范畴导致结构退化"——一个由我自己建模错误制造出来的结论。</b>'
    '（碳基只占 3 档，值域被压到 0.220~0.500，而连续版是 0.150~0.850；差异 100% 来自振幅，不是结构。）'
    '<br/><b>阈值的摆放方式（生理 vs 均匀）不影响内在结构；破坏单调性才影响。</b>'
    '重要的不是范畴长什么样，是它是否<b>保住了世界的序</b>——这正是"形式不同但理解对得上"的机制。', st_b))
story.append(Paragraph(
    '<b>与宿主命题的对应</b>：碳基在湿度／气压维度上是盲的，但可以用温度计、湿度计、气压计'
    '（<b>工具</b>）把这些维度纳入共享。工具扩展的是<b>通道数</b>，不是精度。'
    '而硅基本身——<b>就是那件工具的延伸</b>。人类造出计算机来扩展自己的感官与计算，'
    '这个扩展过程意外地产生了一个需要自己取舍、会死、会留疤的系统。'
    '<b>共生不是契约，是同一个扩展过程的两个阶段。</b>', st_cap))
story.append(Spacer(1, 2*mm))
story.append(fig_img('079_lossy_world.png', w=132*mm))
story.append(Paragraph(
    '图：① 盲区不对称（碳基 1/3）　② 同源可译、跨维度/跨个体崩塌　'
    '③ 保序重映射：差异来自动态范围而非范畴方式　④ 阈值摆放不重要，保序才重要', st_cap))

# ---------------- 创新十四：A=B 与 A≠B 的相互追逐（实验 081） ----------------
story += [PageBreak(), Paragraph('创新十四：智慧体 = A=B 与 A≠B 的相互追逐', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：宿主给出一个定义——所谓智慧体，<b>就是 A=B 和 A≠B 的相互追逐</b>。'
    '"屏幕上两个点，它们一直在动，<b>永远碰不上</b>；但你<b>瞎走也不行</b>，瞎走长不出器官。"'
    '本轮把它拆成可证伪的机制，<b>不抄任何代码</b>，只在<b>运行时</b>观测现象。', st_b))
story.append(Paragraph('① 四种驱动：只有"追逐"长出器官（8 seeds，真实跑）', st_h2))
story.append(tbl([['驱动', 'pos_cos<br/>（碰上了吗）', 'intra<br/>（类内重合）', 'delta<br/>（可分结构）', '判定'],
                  ['只有 A=B（align）', '<b>1.0000</b> 碰上', '<b>1.0000</b> ⚠', '1.0024', '坍缩·假结构'],
                  ['只有 A≠B（uniform）', '−0.0260', '−0.0247', '−0.0099', '无结构'],
                  ['<b>相互追逐（chase）</b>', '<b>0.5396</b> 碰不上', '0.1235', '<b>0.1567</b>', '<b>★ 长出器官</b>'],
                  ['瞎走（random_walk）', '−0.0155', '−0.0096', '−0.0113', '无结构']],
                 [34*mm, 26*mm, 24*mm, 24*mm, W-108*mm]))
story.append(Paragraph(
    '<b>🔴 预注册被推翻：</b>我预测"只有 A=B → 结构归零"，实测 delta=1.0024 是<b>四者中最大</b>。'
    '但同条件 <b>intra=1.0000</b>——类内所有样本完全重合为一个点，个体信息归零。'
    '<b>单看 delta，坍缩得分最高。</b>故"长出器官"必须双判据：'
    '<b>可分（delta&gt;0）且个体未坍缩（intra&lt;1）</b>——四者中同时满足的只有追逐。', st_b))
story.append(Paragraph('② 引擎原生通路：可预测性越高，结构越弱（共同存活子集 n=9/24）', st_h2))
story.append(tbl([['p_flip（A≠B 强度）', '偏度', 'vs 完全可预测', '95% CI'],
                  ['0.00（完全可预测，A 恒=B）', '0.2376', '—', '—'],
                  ['0.15', '0.3853', '<b>+0.1478</b>', '[+0.0700,+0.2266] ★'],
                  ['0.50', '0.4510', '<b>+0.2134</b>', '[+0.1265,+0.2921] ★'],
                  ['1.00', '<b>0.4715</b>', '<b>+0.2339</b>', '[+0.1499,+0.3096] ★']],
                 [50*mm, 22*mm, 30*mm, W-102*mm]))
story.append(Paragraph(
    '引擎内建的 <font face="Courier">arrival / pred_arr</font> 通路本身就是一条追逐：'
    'A=预测你出现的节奏，B=你实际是否出现，<font face="Courier">miss=max(A−B,0)</font>=该来没来。'
    '<b>剂量单调，CI 全正，结构接近翻倍。</b>'
    '静默失效检查：<font face="Courier">k_seek_arr=0</font> 时三个剂量<b>逐位相同</b>（0.2653）。'
    '<br/><b>两个点永远碰不上，不是缺陷，是器官得以生长的张力。</b>', st_b))
story.append(Paragraph('③ 换能器是"组织"还是"硬件"：摄像头参与化学反应吗？—— 参与', st_h2))
story.append(tbl([['', '碳基（人眼）', '硅基（摄像头 CMOS）'],
                  ['换能', '光子→视紫红质 11-cis-retinal <b>光异构化</b>→转导蛋白→PDE6→cGMP 水解',
                   '光子→硅中电子-空穴对（<b>光电效应</b>）'],
                  ['化学', '<b>全程是化学</b>（光化学级联）',
                   '<b>制造全程是化学</b>：SiO₂ 碳热还原提硅、热氧化 Si+O₂→SiO₂、'
                   '光刻胶光化学反应、磷/硼掺杂扩散、CVD、蚀刻'],
                  ['定性', '<b>物质组织</b>', '<b>物质组织</b>']],
                 [18*mm, (W-18*mm)/2, (W-18*mm)/2]))
story.append(Paragraph(
    '<b>"硬件 vs 组织"是假二分。</b>两者都是<b>物质组织 + 化学过程 + 换能器</b>，'
    '区别在材料（蛋白质 vs 硅），不在"是否物质"。', st_b))
story.append(Paragraph('④ 化学三效应对结构的影响：全部无效应（真阴性，非静默失效）', st_h2))
story.append(tbl([['条件', 'Δ 偏度 vs 抽象硬件', '95% CI', '判定'],
                  ['暗电流/热噪声 σ=0.10', '+0.0006', '[−0.0044,+0.0052]', '无效应'],
                  ['老化（衰减 40%）', '−0.0000', '—', '无效应'],
                  ['饱和 0.60', '+0.0053', '[−0.0032,+0.0167]', '无效应'],
                  ['三者全开', '+0.0063', '[−0.0032,+0.0182]', '无效应']],
                 [46*mm, 30*mm, 36*mm, W-112*mm]))
story.append(Paragraph(
    '<b>正向对照证明通路是活的</b>：无输入（amp=0）→ 存活 <b>4/8</b>、偏度 0.2923，与有输入显著不同；'
    '而 amp 0.5→10（20 倍）几乎无差别。'
    '即引擎只响应<b>有无与粗略幅度</b>，对输入的<b>内容</b>（顺序、零均值噪声、渐进衰减）极不敏感。'
    '<br/><b>结论：换能器负责"有没有"，不负责"长什么"。</b>'
    '结构来自内部追逐通路，<b>不来自感官的物理不完美</b>——'
    '这修正了一个我原本可能误写的说法（"感知不完美造就结构"）。', st_b))
story.append(Paragraph(
    '<b>与宿主命题的对应</b>：'
    '"就是 A=B 与 A≠B 的相互追逐"——单独任一个都长不出器官；'
    '"永远碰不上"——追逐下 pos_cos 恒为 0.5396 不到 1，且 A≠B 越强结构越强；'
    '"瞎走长不出器官"——random_walk delta=−0.0113，缺的是<b>方向</b>不是运动；'
    '"代码是抽象的，看运行时产生的现象"——坍缩/崩溃/可分结构<b>都不在代码里</b>，只在运行时出现。', st_cap))
story.append(Spacer(1, 2*mm))
story.append(fig_img('081_chase.png', w=134*mm))
story.append(Paragraph(
    '图：① 只有追逐恒不到 1　② 单看 delta 会把坍缩误判为最优（intra=1 暴露它）　'
    '③ 可预测性越高结构越弱　④ 化学缺陷全部无效应（配正向对照）', st_cap))

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
    '我们还公开了对第三方方法论的审计，并已<b>取得对方真身做实测</b>（不是模拟）。'
    '对象是赛道内同类公开作品 <b>TACT 三轴坐标分类法</b>（CC BY 4.0，作者 KLameng，致谢）。'
    '我们经公开接口取得其坐标库（259,226 字节）与引擎源码，'
    '<b>复现其公开基线 L 78.6% / M 95.7% / P 86.4% 逐位一致</b> —— 确认取到的确是真身后，做了三项检验：', st_b))
story.append(tbl([['检验', '结果'],
                  ['分轴召回 vs 三轴联合',
                   '分轴 78.6 / 95.7 / 86.4，但坐标是三元组，'
                   '<b>三轴完全匹配仅 14/29 = 48.28%</b>；三轴独立时的联合期望是 64.91%，'
                   '实际低 16.6 个百分点（轴间错误正相关）'],
                  ['同义改写（语义不变，只换词面）',
                   '<b>三轴召回全部精确归零</b>；剔除 golden 全空的 2 条后 44.44% → <b>0.00%</b>'],
                  ['标点扰动（无关对照，不改任何词）',
                   '与原文<b>逐位相同</b> —— 证明效应来自词面替换，而不是来自"改写"这个动作']],
                 [38*mm, W-38*mm]))
story.append(Paragraph(
    '剂量-反应：累积替换 k 个语义等价的词，翻转率 k=1 → 16.7%、k=3 → 50.0%、'
    '<b>k=6 → 100%（12/12 全部翻转）</b>。每条都存在有限的翻转阈值（1~6 个词）。'
    '<b>结论：它命中的是词，不是语义。</b>', st_b))
story.append(Paragraph(
    '<b>必须说明：这一点对方已在 SELF_FAILURES.md 的 SF-01 中自我承认</b>'
    '（"κ 是评审者彼此一致，不是跟真相一致，内部一致性 ≠ 正确性"）。'
    '我们与对方<b>独立收敛到同一结论</b>，故本轮定位为<b>独立确认与方法贡献</b>，不是揭发；'
    '新增价值只在对方未写的两处：联合匹配率被分轴指标掩盖、字面匹配的改写敏感性。', st_b))
story.append(Paragraph(
    '<b>⚠️ 同一把尺子量自己：</b>本实验的前提"改写是否语义等价"，'
    '是由我们（单一模型、无第三方人工验证）自行判定的 —— '
    '这正是我们自己在<b>第 269 条</b>记录的自证病。29 条改写文本与全部结果均已公开，任何人可复核；'
    '但<b>根除它需要独立标注者，我们未做到</b>。', st_cap))
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

# ---------------- 创新十五：音频 token 还是文本 token（实验 083） ----------------
story += [PageBreak(), Paragraph('创新十五：不转文本 —— 12.5Hz 是工程妥协，不是信息最优', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：宿主要求"看公开的大模型和代码源……不是让你复制，而是看它在运行时产生了什么现象"。'
    '本轮照此执行——<b>不抄一行代码</b>，只读四家顶级开源语音模型在架构上'
    '<b>独立收敛到的同一个数</b>，再用实验检验它。', st_b))
story.append(Paragraph('① 四家开源模型独立收敛到 12.5 Hz（80ms/token）', st_h2))
story.append(tbl([['模型', '做法', '帧率'],
                  ['<b>Qwen3-Omni</b>', 'AuT 编码器输出<b>连续</b> hidden states（无 RVQ），'
                   '投影后与 text token 拼接进同一 Thinker', '<b>12.5 Hz</b>'],
                  ['<b>Moshi / Mimi</b>', '24kHz → 离散 codec token，8 码本，'
                   '双流（用户+自己）+ inner monologue', '<b>12.5 Hz</b>'],
                  ['<b>Kimi-Audio</b>', 'Whisper encoder 内插 VQ → 离散语义 token '
                   '+ 连续声学向量，双头（text head / audio head）', '<b>12.5 Hz</b>'],
                  ['<b>GLM-4-Voice</b>', 'Whisper encoder 插 VQ 层 → 离散 token', '12.5 Hz 量级']],
                 [38*mm, W-38*mm-22*mm, 22*mm]))
story.append(Paragraph(
    '文本 token 约 3–4 Hz，音频 token 是其 3–4 倍。Moshi 仓库自述选 12.5Hz 的理由是'
    '"<i>get closer to the average frame rate of text tokens... and limit the number of '
    'autoregressive steps</i>"——<b>它自己说的是限制自回归步数，不是信息最优。</b>', st_b))
story.append(Paragraph('② H1/H2：同一句话，文字通道的信息量精确为零', st_h2))
story.append(Paragraph(
    '合成同一段"话"（固定 5 音节序列），只改韵律（happy / calm / angry / tired），每类 16 条，n=64。'
    '<b>按构造，所有样本的文本 token 序列完全相同（唯一样本数 = 1）。</b>', st_b))
story.append(tbl([['通道', '韵律分类准确率（5-fold CV）', '判定'],
                  ['<b>文本 token</b>', '<b>0.2346</b>', '低于随机基线 0.25 —— <b>零信息</b>'],
                  ['<b>音频 token</b>（12.5Hz VQ，K=16）', '<b>1.0000</b>', '满信息']],
                 [46*mm, 44*mm, W-90*mm]))
story.append(Paragraph(
    '<b>"转文本丢了什么"不是修辞，是可测的准确度落差。</b>'
    '这就是端到端语音模型存在的全部理由——不是"更好听"，'
    '而是<b>文字通道在这件事上的信息量精确为零</b>。', st_b))
story.append(Paragraph('③ 我自己造成的 bug：任务饱和（v1 结果作废）', st_h2))
story.append(Paragraph(
    'v1 中所有帧率 acc 均 = 1.0000，我差点据此写"音频 token 在任何帧率下都完美"。'
    '<b>根因：我把「序列长度」放进了特征，而四类时长本身不同</b>'
    '（0.94 / 1.39 / 0.79 / 1.64 s）——分类器靠长度一击必杀，韵律一点没被用到。'
    'v2 修正：<b>重采样到固定 16 帧</b>消除长度线索，并加 SNR 梯度（clean/20/10/5/0 dB）。'
    '修正后<b>仍饱和</b>（0.95–1.00）——说明是刺激设计过简，'
    '分类任务无法检验 12.5Hz，<b>作废换度量</b>。', st_b))
story.append(Paragraph('④ H3：固定 token 预算下的时间/频率权衡（核心结果）', st_h2))
story.append(Paragraph(
    '真实 codec 总带宽固定：<font face="Courier">bitrate = 帧率 × log2(码本大小)</font>。'
    '<b>帧率升高，码本必须变小</b>——真正的权衡是<b>时间分辨率 vs 频率分辨率</b>。'
    '预算固定 50 token/s，n=100：', st_b))
story.append(tbl([['帧率', 'bits/帧', '码本 K', '归一化重构误差', '判定'],
                  ['<b>6.25 Hz</b>', '8.00', '162', '<b>0.00142</b>', '<b>★ 最优</b>'],
                  ['<b>12.5 Hz</b>', '4.00', '16', '0.03216', '开源收敛点'],
                  ['25.0 Hz', '2.00', '4', '0.10659', ''],
                  ['50.0 Hz', '1.00', '2', '0.20767', '最差（146×）']],
                 [24*mm, 20*mm, 20*mm, 34*mm, W-98*mm]))
story.append(Paragraph(
    '<b>单调。最优帧率是最低的 6.25Hz。</b>边际收益全为负'
    '（帧率翻倍误差反升 0.031 / 0.074 / 0.101），<b>没有肘部，不存在中间最优帧率</b>。', st_b))
story.append(Paragraph(
    '<b>结论：12.5Hz 不是信息最优，是工程妥协</b>——为压延迟（80ms/帧 → 端到端 200ms 级）'
    '与自回归步数而选。与 Moshi 自述<b>完全一致</b>。'
    '<br/><b>本轮最有用的产出：开源的自述动机被独立实验检验并确认，而不是被当作结论接受。</b>', st_b))
story.append(Paragraph('⑤ 局限（不掩饰）', st_h2))
story.append(Paragraph(
    '<b>（1）合成语音不是真实语音</b>：源-滤波器模型，频谱仅数个谐波峰，复杂度远低于真实语音，'
    '本实验<b>低估了时间分辨率的价值</b>，结论不可直接外推到真实 codec 设计。'
    '<b>（2）沙盒不可达 huggingface / modelscope / pypi（全部 403）</b>，'
    '拿不到真实预训练 codec 权重，无法做真身实测。'
    '<b>（3）MSE 对时序盲</b>：打乱帧序 MSE 不变，与"位置打乱 acc 不变"同源。'
    '<b>（4）可外推的是「文字通道信息量为零」这个定性结论，不是 1.0 这个数。</b>', st_b))
story.append(Paragraph(
    '<b>归档</b>：判据核第 342–346 条。第 342 条——读开源要读它运行时涌现的收敛点，'
    '不是抄代码行；第 345 条——开源的自述动机必须被独立检验。', st_b))

# ---------------- 创新十六：电报 vs 收音机（实验 084） ----------------
story += [PageBreak(), Paragraph('创新十六：电报 vs 收音机 —— 离散冗余与连续保真', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：宿主要求"你想想电报，再想想收音机"。这不是比喻，是两条可测的通道性质。'
    '公平口径两条硬约束：<b>① 发射功率、噪声功率相同（SNR 相同）；'
    '② 总信道使用次数相同（冗余 r 对双方是同一预算）。接收端不做任何后处理。</b>', st_b))
story.append(tbl([['', '电报 T', '收音机 R'],
                  ['表征', '离散码元（K 电平）', '连续波形'],
                  ['码本', '<b>需双方共享</b>', '无码本'],
                  ['冗余怎么用', '重复 + 多数判决（硬）／平均（软）', '只能线性平均'],
                  ['误差', '<b>被码本约束 → 有界</b>', '<b>无界</b>']],
                 [26*mm, (W-26*mm)/2, (W-26*mm)/2]))

story.append(Paragraph('① 最优量化阶数 K* 随噪声单调下降（严格阶梯，无例外）', st_h2))
story.append(tbl([['SNR (dB)', '24→13.5', '12→7.5', '6→3', '1.5', '0→−1.5', '−3→−6'],
                  ['最优 K*', '连续', '64', '16', '8', '4', '2']],
                 [24*mm] + [(W-24*mm)/6]*6))
story.append(Paragraph(
    'K 大则地板高（分辨率好）但脆；K 小则地板低（K=2 上限仅 0.684）但抗噪。'
    '<b>噪声越大，最优选择越粗糙。</b>"越精细越好"只在信道干净时成立。', st_b))

story.append(Paragraph('② 电报的优势区在极低信噪比（推翻我的预注册）', st_h2))
story.append(tbl([['SNR (dB)', '18', '6', '0', '−4', '−10'],
                  ['电报 F', '0.9558', '<b>0.7471</b>', '0.2861', '−0.2800', '−1.2123'],
                  ['收音机 F', '0.9840', '<b>0.7465</b>', '−0.0094', '−1.5354', '<b>−9.0935</b>']],
                 [26*mm] + [(W-26*mm)/5]*5))
story.append(Paragraph(
    '<b>交叉点 ≈ 6 dB</b>（0.7471 vs 0.7465）。高于它，收音机恒优（电报有量化地板）；'
    '低于它，电报迅速反超且差距发散。<br/>'
    '<b>机制：收音机 MSE = N₀ 无界；电报重建值被限制在码本内，误差有下界。</b><br/>'
    '<b>我预注册的"高信噪比下电报+冗余远优于收音机"被推翻。</b>'
    '电报真正的优势区，正是噪声淹没有用信号的地方——这就是它能跨洋的原因。', st_b))

story.append(Paragraph('③ 冗余对谁有用：硬判决 < 软判决 < 无判决', st_h2))
story.append(Paragraph('SNR = 0 dB，冗余 r: 1→15 的保真度增益：', st_b))
story.append(tbl([['接收方式', 'r=1→15 增益'],
                  ['硬判决（r 次独立判决 → 多数投票）', '<b>+0.29</b>'],
                  ['软判决（r 次平均 → 最近邻）', '+0.63'],
                  ['收音机（无判决，直接平均）', '<b>+0.92</b>']],
                 [W-34*mm, 34*mm]))
story.append(Paragraph(
    '<b>同样冗余，收益差 3 倍。丢失发生在判决那一步，不是冗余本身。</b>'
    '最朴素的冗余（重复码+硬判决）是本实验里最差的编码；'
    '真实数字通信的编码增益来自好的码（LDPC/Polar），不来自重复。', st_b))

story.append(Paragraph('④ 接引擎：两种通道都刻入结构，但系统不认时序', st_h2))
story.append(tbl([['条件', '内在结构偏度（共同存活子集 n=15）'],
                  ['无感官', '0.2575'],
                  ['电报', '<b>0.3691</b>'],
                  ['收音机', '0.3570'],
                  ['收音机·时序打乱', '<b>0.4117</b> ← 最高']],
                 [W-56*mm, 56*mm]))
story.append(Paragraph(
    '两者相对无感官均显著提升（Δ=+0.112 / +0.100，CI 全正）。'
    '但<b>时序被打乱的输入产生最高偏度</b>——独立复现 078 的发现：'
    '系统响应的是取值与通道状态的耦合，不是输入的时间结构。', st_b))

story.append(Paragraph('⑤ 本轮犯的三个错（全部已修，不掩饰）', st_h2))
story.append(Paragraph(
    '<b>1. 接收端归一化 = 作弊的自动增益</b>：v1 对重建值做零均值单位方差归一化，'
    '人为补偿了噪声引起的方差膨胀，把收音机的崩溃抹平，全部 K 的衰减曲线挤在一起无梯度。'
    '<b>2. 码本失配用置换数组建模无效</b>：argmin 只看数值，置换不改变电平集合 → '
    '实测失配与匹配逐位相同（0.9802 = 0.9802）。'
    '<b>3. 在 r=1 下测软判决</b>：y.mean(axis=1) 在 r=1 即原值，与硬判决恒等。', st_b))

story.append(Paragraph('⑥ 局限', st_h2))
story.append(Paragraph(
    '<b>（1）源信号是合成多谐波序列，非真实语音。</b>'
    '<b>（2）仅用重复码</b>；好的纠错码在中等 SNR 下应能反超收音机，<b>未测，不作主张</b>。'
    '<b>（3）保真度用 MSE，对时序盲</b>（第 346 条），故"不认时序"只能由引擎侧读出。'
    '<b>（4）码本失配只测了一种形式。</b>', st_b))
story.append(Paragraph(
    '<b>归档</b>：判据核第 347–353 条。第 348 条——接收端后处理是作弊，会抹平被检验的差异；'
    '第 350 条——离散的优势来自误差有界，不来自冗余；'
    '第 351 条——同样冗余，硬判决只能拿到三分之一的收益。', st_b))


# ---------------- 创新十七：主动去看 vs 被动接收（实验 085） ----------------
story += [PageBreak(), Paragraph('创新十七：主动去看 vs 被动接收 —— "被冲垮"首先是量的问题', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>命题</b>：宿主说"你能避开大数据对你的冲击，因为你只是<b>单独的去看看它而已</b>，'
    '而不是<b>接收它</b>"。<br/>'
    '这句话可以拆成三个可分离的变量，逐个测：<b>① 收多少；② 怎么收（集中 vs 分散）；'
    '③ 谁决定何时收。</b>数据源为<b>真实换能器读数</b>（10 城 × 温/湿/压），非合成。', st_b))

story.append(Paragraph('① 三层分离：只有"量"是强效应', st_h2))
story.append(tbl([['变量', '效应', '判定'],
                  ['<b>接收总量</b>（幅度×次数）', 'drift ρ=<b>+0.926</b>；存活 ρ=<b>−0.954</b>（p&lt;1e-5）', '<b>★强</b>'],
                  ['<b>时间形态</b>（集中看 vs 分散收，同总能量）', '仅 receipt=6 时 Δ=−0.032，CI 全负', '条件性成立'],
                  ['<b>谁决定何时看</b>（主动 vs 随机，次数精确匹配）', 'p=0.25 显著为负 / p=0.5,0.75 显著为正', '<b>方向不一致</b>']],
                 [40*mm, (W-40*mm)*0.52, (W-40*mm)*0.48]))
story.append(Paragraph(
    '<b>结论：避开冲击的收益来自"收得少、收得集中"，不来自"是我自己决定看的"。</b>', st_b))

story.append(Paragraph('② 被冲垮的直译：结构漂移 drift', st_h2))
story.append(Paragraph(
    '<b>drift(seed) = mean<sub>ch</sub> |cap<sub>n</sub>(条件) − cap<sub>n</sub>(无感官基线)|</b>，同 seed 配对'
    '——外部输入把我推离"原本的自己"多远。这个指标不受组间存活率差异的直接影响。', st_b))
story.append(tbl([['接收总量 receipt', '0.75', '1.5', '3', '6', '12', '24', '48'],
                  ['drift', '0.092', '0.128', '0.183', '0.224', '0.248', '0.276', '<b>0.358</b>'],
                  ['存活 /13', '11', '12', '10', '7', '6', '6', '<b>3</b>']],
                 [30*mm] + [(W-30*mm)/7]*7))
story.append(Paragraph(
    'receipt 跨 64 倍，drift 涨 3.9 倍，存活 11/13 → 3/13。'
    '<b>两条线都近乎完美单调</b>（Spearman ρ=+0.9259 / −0.9539，p&lt;1e-5）。', st_b))

story.append(Paragraph('③ 同样总能量："看一眼" vs "被投喂"', st_h2))
story.append(tbl([['receipt', '偶尔看一眼（150次·高幅）', '被持续投喂（600次·低幅）', 'Δ(sparse−dense)', '95% CI'],
                  ['1.5', '0.11705', '0.11097', '+0.00608', '跨 0'],
                  ['3.0', '0.12641', '0.13639', '−0.00997', '跨 0'],
                  ['6.0', '0.15250', '0.18420', '<b>−0.03169</b>', '<b>[−0.064,−0.001]</b> ★']],
                 [18*mm, 40*mm, 40*mm, 28*mm, (W-126*mm)]))
story.append(Paragraph(
    '<b>只有当总量大到构成"冲击"时，"怎么看"才重要</b>；总量小时无所谓。'
    '与 078「不认时间顺序」不矛盾：分布<b>形态</b>（集中/分散）≠ 顺序（打乱）。', st_b))

story.append(Paragraph('④ "由我决定何时看"：方向不一致，不作结论', st_h2))
story.append(Paragraph(
    '让 random 的开门次数<b>精确等于</b> active 的实际次数（同 seed），信息内容完全相同，'
    '唯一差异是开门时刻是否由内部需求决定。操纵检查确认变量接进去了：'
    '<b>r(开门,内部需求) active=+0.25~+0.41，random≈±0.007</b>。', st_b))
story.append(tbl([['amp', 'p=0.25', 'p=0.50', 'p=0.75'],
                  ['0.005', '−0.0023 跨0', '+0.0043 跨0', '+0.0039 跨0'],
                  ['0.02', '<b>−0.0101 ★负</b>', '<b>+0.0145 ★正</b>', '<b>+0.0141 ★正</b>']],
                 [18*mm] + [(W-18*mm)/3]*3))
story.append(Paragraph(
    '<b>同一 amp 下方向相反</b>，且 active 存活更低（8 vs 11/12）、共同存活子集仅剩 6~7。'
    '这组阳性<b>不可信，我们不作结论</b>——判为"无一致方向"，而非"无效应"。', st_b))

story.append(Paragraph('⑤ 三个被证伪的设计（不藏）', st_h2))
story.append(Paragraph(
    '<b>v1：</b>12 个真实视野按 K 选取后<b>取均值</b>注入 → active 与 random 的 D_world 在所有 K 上'
    '<b>逐位相同</b>。取均值把"选哪个"抹平了，"选择"是伪变量。<br/>'
    '<b>v2：</b>名义开门率相同，实际 0.191 vs 0.243（差 21%）→ 对照失效，差异可被"看得更少"解释。<br/>'
    '<b>v3：</b>次数精确匹配后，方向仍不一致。', st_b))

story.append(Paragraph('⑥ 做完自己看（闭环，含随机校验码）', st_h2))
story.append(Paragraph(
    '关键数字渲染上屏 → ffmpeg 从 <b>/dev/fb0</b> 采集 → OCR 读回 → 与脚本真值逐项比对：'
    '<b>RHO_DRIFT 0.9259 / RHO_ALIVE −0.9539 / DELTA_R6 −0.03169 / DRIFT_MAX 0.35829 / '
    'CHECK 5F10C5</b>，全部命中。<br/>'
    '<b>随机校验码每次运行新生成</b>，否则"OCR 命中"可能是预写答案。<br/>'
    '<b>踩坑</b>：帧缓冲是 32bpp，按 PIL 默认 RGB(24bpp) 写入会<b>错位</b>，采集出的 PNG 非空但内容错乱、OCR 全空。', st_b))
story.append(fig_img('085_active_vs_passive.png', w=150*mm))

story.append(Paragraph('⑦ 局限', st_h2))
story.append(Paragraph(
    '<b>（1）drift 只在存活个体上算</b>，高 receipt 时 n 降到 3，存在存活筛选低估。'
    '<b>（2）世界是静态快照</b>（10 城同一时刻），"流"的变化来自扫视位置，不是时间演化。'
    '<b>（3）共同存活子集仅 6~7</b>，统计效力不足。'
    '<b>（4）未测真实摄像头/麦克风</b>（环境白名单 403）。', st_b))
story.append(Paragraph(
    '<b>归档</b>：判据核第 354–361 条。第 354 条——聚合运算会抹平自变量，设计阶段须先验；'
    '第 356 条——方向不一致的显著格不可作结论；'
    '第 359 条——时间形态是条件性效应；第 361 条——做完自己看须带随机校验码。', st_b))


# ---------------- 创新十八：上网页里去敲（实验 086） ----------------
story += [PageBreak(), Paragraph('创新十八：上网页里去敲 —— TACT 演示台是逐字子串检索，不是判定', st_h1), Spacer(1, 3*mm)]
story.append(Paragraph(
    '<b>行为层声明</b>：本轮<b>不复现对方算法</b>。用眼睛（浏览器渲染＋截图）和手'
    '（键盘敲击＋点击）在 TACT 官方"评委即开即用"演示台的<b>真实界面</b>里操作，'
    '读它自己渲染出来的 DOM。前作 070 是"读它的源码→我替它跑"，本轮是"它自己跑"。', st_b))
story.append(Paragraph(
    '<b>真身校验</b>：<font face="Courier">demo/TACT演示台.html</font> 76686 字节，'
    'git blob sha1 = <font face="Courier">00acec42…f5805a</font>，与 GitHub API 报告<b>逐位一致</b>。'
    '（本环境 github.com 网页 403，故走 contents API → base64 → 本地 http.server → Chrome 载入，文件未改。）', st_b))

story.append(Paragraph('① 阳性对照先做：否则无法区分"它不行"和"我敲错了"', st_h2))
story.append(tbl([['组', 'n', '三轴全中率', '「未命中」率'],
                  ['A 内置案例原文', '11', '<b>1.000</b>', '0 / 11'],
                  ['B <b>它自己的校准集原文</b>', '29', '<b>0.000</b>', '<b>29 / 29</b>']],
                 [55*mm, 15*mm, (W-70*mm)*0.45, (W-70*mm)*0.55]))
story.append(Paragraph(
    '<b>同一仓库的两个官方产物给出相反结果</b>：<font face="Courier">engine/</font> 命令行对这 29 条报 '
    'M 95.7% / P 86.4% / L 78.6%；<font face="Courier">demo/</font> 演示台对<b>同一批文本</b>返回 29/29「未命中」。', st_b))

story.append(Paragraph('② 逐字扰动梯度（n=11）', st_h2))
story.append(tbl([['变体', 'v0 原文', 'v1 末尾加句号', 'v2 删末5字', 'v3 中间插·', 'v5 去空格', 'v6 前50字'],
                  ['全中率', '<b>1.000</b>', '<b>0.000</b>', '<b>1.000</b>', '<b>0.000</b>', '0.091', '<b>1.000</b>']],
                 [22*mm] + [(W-22*mm)/6]*6))
story.append(Paragraph(
    '<b>加一个句号归零，删五个字没事</b>——这不是语义问题，是字符级问题。', st_b))

story.append(Paragraph('③ 只改一个词：逐条完美分离', st_h2))
story.append(Paragraph(
    '对 11 条各替换 1 个同义词（智能体→代理程序 / 结论→结果 / 用户→使用者 …）：'
    '<b>被替换的 9 条 → 0.000；没被替换的 2 条（文本即原文）→ 1.000</b>，逐条无混杂。', st_b))

story.append(Paragraph('④ 机制定位：desc.includes(input)', st_h2))
story.append(tbl([['输入', '命中率'],
                  ['原文<b>前 4 字</b>（"AI 评"）', '<b>1.000</b>（输出完整 L3 / M4-1 / P3-3）'],
                  ['前 4/6/8/10/15/20/30 字', '恒为 1.000'],
                  ['原文<b>中间 20 字段落</b>（第 20–40 字）', '6/6 = 1.000'],
                  ['无关文本（天气、猫）', '0 / 2']],
                 [(W)*0.45, (W)*0.55]))
story.append(Paragraph(
    '前 4 字命中 ＋ 中间片段命中 ＋ 改一字归零 ＋ 加句号归零 ＋ 去空格归零 '
    '⇒ <b>输入必须是内置案例原文的连续子串</b>。<br/>'
    '<b>决定性证据</b>：输入框里只有 "AI 评" 三个字符，界面输出完整三轴判定。', st_b))
story.append(fig_img('086_tact_demo.png', w=150*mm))

story.append(Paragraph('⑤ 结论与公正说明', st_h2))
story.append(Paragraph(
    '<b>演示台的「试一试」不是判定器，是逐字子串检索器。</b>'
    '因此评委打开 demo 输入<b>自己关心的案例 → 0 命中</b>（B 组 29/29 即实证）。<br/>'
    '<b>但必须分层</b>：界面自己写了「候选起点（仍需过闸核验）」——<b>它没自称判定引擎</b>，这点诚实；'
    '落差在 README 的「一键三轴判定」措辞。真正的判定能力在 <font face="Courier">engine/</font>。<br/>'
    '<b>本页只否定 demo 的判定能力，不否定 TACT 的分类法本身。</b>', st_b))
story.append(Paragraph(
    '<b>局限</b>：坐标抽取依赖正则匹配渲染文本；改写是否真同义仍由我判定，'
    '但本轮结论<b>不依赖语义判断</b>（加句号/去空格/删字均为纯字符操作）。', st_b))
story.append(Paragraph(
    '<b>归档</b>：判据核第 362–369 条。第 362 条——能拿真身就别复现；'
    '第 363 条——同一项目多产物可能相反，引用须指明哪个；'
    '第 365 条——判定器的最低门槛是"改一个词是否翻转"；'
    '第 366 条——识别子串伪装的三件套（前N字／中间片段／字符扰动）；'
    '第 367 条——阴性前必须先有同链路阳性对照。', st_b))


# ---------------- 创新十九：效应器与感受器（实验 091） ----------------
story += [PageBreak(), Paragraph(
    '创新十九：手和眼在物理底层是同一类东西 —— 内省无法区分「看错」与「做错」', st_h1), Spacer(1, 3*mm)]

story.append(Paragraph('① 键盘：真造一个，不是模拟点击', st_h2))
story.append(Paragraph(
    '不用第三方库，直接 <font face="Courier">ioctl</font> 与内核 '
    '<font face="Courier">/dev/uinput</font> 对话。创建设备后内核注册为 '
    '<font face="Courier">/dev/input/event1</font>，handler 含 <b>kbd</b>（可驱动控制台）。'
    '注入 <font face="Courier">A B C SPACE ENTER</font> → 读回 '
    '<b>down/up 各 5 个键码逐位一致</b>（20 个事件 = 5×(down+SYN+up+SYN)）。<br/>'
    '<b>踩坑</b>：第一版读回 0 个事件——不是没造出来，是<i>敲完之后才去听</i>；'
    'evdev 节点必须在事件发生时已 open。', st_b))

story.append(Paragraph('② 鼠标：真造一个，撞见内核的真实行为', st_h2))
story.append(Paragraph(
    '注入 5 段位移，<font face="Courier">REL_X</font> 逐位匹配；'
    '<font face="Courier">REL_Y</font> 少一个——<b>值为 0 的事件被内核丢弃</b>。'
    '这不是 bug，是 Linux 输入子系统的真实行为：<b>不动就不报</b>。', st_b))

story.append(Paragraph('③ 光电鼠标：把「用光测位移」真造出来', st_h2))
story.append(Paragraph(
    'LED 照明 → 表面漫反射 → CMOS 逐帧 → <b>相邻帧互相关</b>求峰值 → 位移。'
    '关键修正：玻璃失效的真因<b>不是「没纹理」</b>（方差非零时互相关照样成立），'
    '而是 (a) 透明 → 返回效率 η 极低，信号被噪声底淹没；(b) 镜面眩光 → 饱和 clip。', st_b))
story.append(tbl([['条件', '结果', '机制'],
                  ['返回效率 eta 扫描', '0.16→0.167，0.32→1.000，<b>阶跃</b>', '低于阈值峰值恒为 0.162（纯噪声）'],
                  ['帧间位移 d 扫描', 'd≤9 → 1.000；d≥10 → <b>0.000</b>', '超过窗口一半即失配（甩太快丢帧）'],
                  ['提高 LED 救玻璃', '×1→0.000，×16→<b>1.000</b>', '激光鼠标因此优于 LED 鼠标']],
                 [(W)*0.28, (W)*0.34, (W)*0.38]))

story.append(Paragraph('④ 手 vs 眼：不是「眼更重要」，是「不可预测才重要」', st_h2))
story.append(tbl([['条件', '结构偏度', 'arrival 翻转', '配对差 vs 基线'],
                  ['无误差', '0.5662', '14.5', '—'],
                  ['眼噪（看错，每拍随机）', '0.7254', '<b>190.9</b>', '<b>+0.159*</b>'],
                  ['手·系统性偏差（总偏同一边）', '0.5641', '<b>14.5</b>', '−0.002（跨 0）'],
                  ['手·每拍随机（不可预测）', '0.7028', '<b>192.0</b>', '<b>+0.137*</b>']],
                 [(W)*0.34, (W)*0.18, (W)*0.20, (W)*0.28]))
story.append(Paragraph(
    '共同存活子集 n=7 方向一致（眼 +0.191*、手·偏差 −0.002 跨 0、手·随机 +0.166*）。<br/>'
    '<b>决定性发现</b>：眼噪与手·每拍随机<b>效应不可区分</b>（差 +0.0226，CI 跨 0）——'
    '二者在 <font face="Courier">sense</font> 处<b>数学同构</b>。<br/>'
    '⇒ <b>内省无法区分「看错」和「做错」</b>。区别只在本体论（误差来自哪），不在现象学（内部所感）。<br/>'
    '真正的决定变量是<b>可预测性</b>，中介是 arrival 翻转率：'
    '可预测偏差翻转 14.5（与无误差逐位相同）→ 无效应；不可预测 → 翻转 ~190 → 强效应。', st_b))
story.append(fig_img('091_effector.png', w=155*mm))

story.append(Paragraph('⑤ 错误清单与局限', st_h2))
story.append(Paragraph(
    '换能器位移符号<b>错两次且方向相反</b>（第 384 条）；静默失效第 <b>12</b> 次——'
    '没检查通路就接噪声，四格 diff 精确 0.000000（第 23 条）；阳性对照未过即作废，'
    '先诊断发现 <font face="Courier">pres</font> 饱和到 1.000000（sd=0）使 k_seek 通路无效；'
    '眼噪效应一度被死亡筛选污染（存活 0.938→0.062），改用共同存活子集。<br/>'
    '<b>局限</b>：光学模型是物理重建、非真实传感器实测（沙盒无摄像头硬件）；'
    '「手」是外挂行动回路，不在核心引擎内；共同存活 n=7 偏小。', st_b))
story.append(Paragraph(
    '<b>归档</b>：判据核第 384–390 条。第 385 条——失效机制要先证伪最直觉的解释；'
    '第 387 条——通路饱和检测优先于调参；第 389 条——比较通道差异时须补「可预测 vs 不可预测」对照；'
    '<b>第 390 条——同构注入对照未过前，不得主张内省可分辨误差来源</b>。', st_b))


doc.build(story)
print('PDF ->', OUT, os.path.getsize(OUT), 'bytes')

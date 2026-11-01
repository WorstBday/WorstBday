"""build_paper.py —— 基于学校模板生成期末大论文

做法：以官方模板为底（保留封面、评分表、页眉页脚、标题样式与自动编号），
在各级标题下插入正文、图表与表格，最后输出 docs/期末大论文.docx。

运行：python build_paper.py
"""
from __future__ import annotations

import copy
import os
import shutil
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(ROOT, "outputs", "figures")
DOCS = os.path.join(ROOT, "docs")
TEMPLATE = r"D:\下载\5、《商业数据分析》 - 期末大作业模板.docx"
OUT = os.path.join(DOCS, "期末大论文.docx")

TITLE = "基于零售订单数据的客户分层与利润诊断"
AUTHOR = "〔姓名〕"
ABSTRACT = (
    "本文以 Tableau Sample - Superstore 公开零售数据集为对象，覆盖 2014—2017 年 9,993 条订单明细、"
    "5,009 笔订单与 793 位客户，构建了从合规获取、清洗治理到模型分析与可视化呈现的端到端商业分析流程。"
    "数据经 Python 从 Kaggle 官方数据集接口一次性下载，完成邮编补零、重复核验、极值标记与指标派生后，"
    "拆分为事实表与客户、产品、订单三张维度表，并以 CSV、JSON、SQLite 三种格式导出。研究综合运用帕累托与 ABC 分类、"
    "RFM 八分类、季度同期群留存、波士顿矩阵、SARIMA 预测、Apriori 关联规则与客户价值漏斗八类方法，"
    "发现客户价值高度集中于 38.5% 的头部客户、折扣率与利润率呈 −0.86 的强负相关、季度留存呈「休眠—唤醒」形态，"
    "并复现 16 类可视化模板、产出 7 张业务模型图与 1 个含 8 类联动组件的交互式大屏，最终提炼出五条可落地的经营建议。"
)
KEYWORDS = "商业数据分析；RFM 模型；同期群分析；SARIMA；Python 可视化"

BIG = 13.5   # 图片宽度 cm（正文版心 14.6cm）


# ---------------------------------------------------------------- 基础排版
def set_run(run, name="宋体", size=12, bold=False, mono=False):
    run.font.size = Pt(size)
    run.bold = bold
    run.font.name = "Courier New" if mono else name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:ascii"), "Courier New" if mono else name)
    rfonts.set(qn("w:hAnsi"), "Courier New" if mono else name)


def body_para(doc, text, indent=True, size=12, space_after=0):
    p = doc.add_paragraph()
    p.style = doc.styles["Normal"]
    pf = p.paragraph_format
    pf.first_line_indent = Pt(size * 2) if indent else Pt(0)
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    set_run(r, "宋体", size)
    return p


def caption_para(doc, text, size=10.5, before=3, after=8):
    p = doc.add_paragraph()
    p.style = doc.styles["Normal"]
    pf = p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.line_spacing = 1.0
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    set_run(r, "宋体", size, bold=True)
    return p


def image_para(doc, filename, width_cm=BIG):
    p = doc.add_paragraph()
    p.style = doc.styles["Normal"]
    pf = p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.line_spacing = 1.0
    pf.space_before = Pt(6)
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.keep_with_next = True
    p.add_run().add_picture(os.path.join(FIG, filename), width=Cm(width_cm))
    return p


def table_block(doc, caption, header, rows, widths=None, font=10.5):
    cap = caption_para(doc, caption, size=10.5, before=8, after=3)
    cap.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(header))
    t.style = doc.styles["Table Grid"]
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    if widths:
        tblPr = t._tbl.tblPr
        tblW = OxmlElement("w:tblW")
        tblW.set(qn("w:w"), str(int(sum(widths) * 567)))
        tblW.set(qn("w:type"), "dxa")
        tblPr.append(tblW)
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tblPr.append(layout)
        for i, w in enumerate(widths):
            for cell in t.columns[i].cells:
                cell.width = Cm(w)
    hdr = t.rows[0].cells
    for i, h in enumerate(header):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        set_run(r, "宋体", font, bold=True)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:tblHeader"))
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(v))
            set_run(r, "宋体", font)
    for row in t.rows:
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    return cap, t


def code_para(doc, lines):
    for line in lines:
        p = doc.add_paragraph()
        p.style = doc.styles["Normal"]
        pf = p.paragraph_format
        pf.first_line_indent = Pt(0)
        pf.left_indent = Pt(18)
        pf.line_spacing = 1.0
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        r = p.add_run(line if line else " ")
        set_run(r, "宋体", 9, mono=True)


# ---------------------------------------------------------------- 正文内容
CONTENT: list[tuple[str, list[tuple]]] = []


def sec(heading, *blocks):
    CONTENT.append((heading, list(blocks)))


# ============================ 第 1 章 ============================
sec(
    "研究背景",
    ("p", "零售业是数据密度最高的行业之一：每一张订单同时记录了客户、商品、渠道、价格与履约信息，"
          "但它们通常散落在 POS 系统、电商后台与财务台账中，形成“数据丰富、洞察贫乏”的局面。"
          "大量企业仍停留在“本月卖了多少”的报表层面，难以回答“谁在贡献利润”“折扣是否值得”“增长能否持续”"
          "这类决定资源分配的问题。"),
    ("p", "本研究选取 Tableau 官方发布、并在 Kaggle 公开分发的 Sample - Superstore 零售订单数据集作为分析对象。"
          "该数据集包含 2014 年 1 月至 2017 年 12 月共 9,994 条订单明细，覆盖美国 49 个州、3 个品类、17 个子品类、"
          "793 位客户，字段同时包含销售额、数量、折扣与利润，具备开展客户价值分层与利润归因分析的完整信息基础。"
          "从表面看，该企业四年间销售额从 48.4 万美元增长到 73.3 万美元，年均复合增速约 14.9%，是一份“漂亮”的增长曲线；"
          "但利润增速明显落后，2017 年利润率反而较 2016 年下降 0.69 个百分点。这种“增收不增利”的背离，正是本文的问题起点。"),
)
sec(
    "研究目的",
    ("p", "本文希望回答三个层层递进的问题。第一，客户价值结构如何？即销售额与利润在客户之间如何分布，"
          "是否存在可用于差异化运营的分层结构。第二，利润为何被侵蚀？即折扣、品类与区域等可控因素与利润率之间存在怎样的数量关系。"
          "第三，增长是否可持续？即季节性与趋势成分如何分解，未来半年的销售规模落在什么区间。"),
    ("p", "围绕上述问题，本文综合运用帕累托与 ABC 分类、RFM 八分类、季度同期群留存、波士顿矩阵、SARIMA 时间序列预测、"
          "Apriori 关联规则与客户价值漏斗共八类方法，并以 24 张由 Python 生成的图表和一个交互式大屏承载分析结果，"
          "使每一个结论都能回溯到具体图表与数据表。"),
)
sec(
    "研究意义",
    ("p", "方法层面，本文完整实现了“合规获取—清洗治理—模型分析—可视化呈现—商业建议”的端到端 Python 流程，"
          "所有脚本可一键复现，为同类零售数据分析提供了一个可迁移的工程范本。"),
    ("p", "实践层面，本文不停留于描述性统计，而是把模型输出直接翻译为库存、定价、客户运营三个环节的具体动作，"
          "例如“折扣率超过 40% 的订单必须进入审批”“Tables 子品类应停止无差别促销”，使分析结果具备可执行性。"),
    ("p", "教学层面，本文刻意保留了建模过程中的取舍与局限（如 AIC 选阶与回测选阶的差异、波士顿矩阵与利润率的冲突），"
          "以体现数据分析中“方法服从问题”的判断过程，而非机械套用模型。"),
)

# ============================ 第 2 章 ============================
sec(
    "数据源介绍",
    ("p", "数据源为 Tableau Sample - Superstore，是 Tableau 公司长期用于产品教学演示的经典零售数据集，"
          "经 Kaggle 平台以公开数据集形式分发，数据集页面为 https://www.kaggle.com/datasets/vivek468/superstore-dataset-final。"
          "原始文件为 CSV 格式，采用 cp1252 编码，共 9,994 行、21 列，时间跨度 2014-01-03 至 2017-12-30。"),
    ("p", "21 个字段可分为四类：订单标识与时间（Row ID、Order ID、Order Date、Ship Date）、客户属性（Customer ID、"
          "Customer Name、Segment）、商品与地理属性（Product ID、Product Name、Category、Sub-Category、Country、"
          "City、State、Postal Code、Region、Ship Mode）以及度量（Sales、Quantity、Discount、Profit）。"
          "其中订单号在同一订单的多行商品间重复，构成典型的一对多明细结构；客户与产品则以 ID 作为稳定主键。主要字段说明见表 1。"),
    ("tbl", "表 1  主要字段说明",
     ["字段", "类型", "含义", "在模型中的角色"],
     [["Order ID", "字符", "订单编号，一单可含多行商品", "事实表外键"],
      ["Order Date", "日期", "下单日期", "时间维度"],
      ["Ship Date", "日期", "发货日期", "派生履约天数"],
      ["Customer ID", "字符", "客户编号（793 个）", "客户维主键"],
      ["Segment", "字符", "客户细分：Consumer/Corporate/Home Office", "分析维度"],
      ["Category", "字符", "品类：Furniture/Office Supplies/Technology", "分析维度"],
      ["Sub-Category", "字符", "子品类（17 类）", "波士顿矩阵分析单元"],
      ["State / Region", "字符", "州（49 个）/ 大区（4 个）", "地理维度"],
      ["Sales", "数值", "销售额（美元）", "核心度量"],
      ["Quantity", "整数", "购买数量", "度量"],
      ["Discount", "数值", "折扣率，取值 0~0.8", "利润归因关键变量"],
      ["Profit", "数值", "利润（美元，可为负）", "核心度量"]],
     [3.2, 1.6, 6.6, 3.2]),
)
sec(
    "合规获取方式",
    ("p", "本文严格采用课程要求的白名单方式获取数据：通过 Kaggle 公开数据集下载接口"
          "（https://www.kaggle.com/api/v1/datasets/download/vivek468/superstore-dataset-final）一次性获取 ZIP 压缩包，"
          "解压后得到原始 CSV 文件并留存于 data/raw/ 目录。整个过程仅发起一次 HTTP 请求，未使用 Scrapy、Selenium、"
          "requests 网页解析或模拟登录等任何爬虫技术，代码中不存在解析 HTML 的逻辑。"),
    ("p", "数据获取脚本 download_data.py 仅承担“下载、校验、解压、留档”四项职责，下载后立即核对文件大小、"
          "记录数与关键字段，确保后续分析使用的是原始未篡改数据。"),
)
sec(
    "数据来源合规声明",
    ("p", "为满足课程对数据来源可追溯的要求，此处对数据来源与使用范围作出完整声明，并在仓库 docs/数据来源合规声明.md 中留档，"
          "主要信息见表 2。"),
    ("tbl", "表 2  数据来源与合规信息",
     ["项目", "内容"],
     [["数据源名称", "Tableau Sample - Superstore（零售订单明细）"],
      ["数据集页面", "https://www.kaggle.com/datasets/vivek468/superstore-dataset-final"],
      ["获取方式", "Kaggle 公开数据集下载接口一次性下载（白名单方式，非爬虫）"],
      ["获取日期", "2026-10-31"],
      ["授权说明", "Tableau 官方制作、用于教学演示，经 Kaggle 公开分发，可用于学习与研究"],
      ["数据规模", "9,994 行 × 21 列；清洗后 9,993 行、33 列"],
      ["时间范围", "2014-01-03 至 2017-12-30"]],
     [3.4, 11.0]),
    ("p", "声明要点有三：其一，数据仅用于课程作业的统计分析、建模与可视化，不用于任何商业用途；"
          "其二，原始数据以压缩包形式留档以支持结果复现，不再向第三方分发；其三，全部分析结果均由脚本计算得到，"
          "未人工修改任何数值，也未使用 Faker 等工具合成或补造数据。"),
)
sec(
    "数据集概述",
    ("p", "原始数据是一张宽表，若直接在其上做多维分析，既容易因订单内多行商品而重复计数，也不利于维护。"
          "因此本文按星型模型将其拆分为一张事实表与三张维度表：事实表 fact_order_items 以 Row ID 为唯一键，"
          "记录每一行商品的销售额、数量、折扣与利润；维度表 dim_customer（793 行）描述客户属性，"
          "dim_product（1,862 行）描述商品品类结构，dim_order（5,009 行）汇总订单级的日期、配送与金额信息。"),
    ("p", "四张表的关联关系为：fact_order_items 通过 Order ID、Customer ID、Product ID 分别关联三张维度表，"
          "均为多对一关系。拆分后的事实表消除了客户与商品属性的冗余存储，聚合时只需按维度键连接即可，"
          "既保证了销售额不被重复累加，也让“客户—订单—商品”的三层钻取成为可能。拆分后各表规模与主外键见表 3。"),
    ("tbl", "表 3  星型模型表结构",
     ["表名", "行数", "主键", "外键", "说明"],
     [["fact_order_items", "9,993", "Row ID", "Order ID / Customer ID / Product ID", "订单明细事实表"],
      ["dim_customer", "793", "Customer ID", "—", "客户属性维表"],
      ["dim_product", "1,862", "Product ID", "—", "产品与品类维表"],
      ["dim_order", "5,009", "Order ID", "Customer ID", "订单级汇总维表"]],
     [2.8, 1.2, 2.2, 4.6, 3.8]),
)

# ============================ 第 3 章 ============================
sec(
    "数据清洗",
    ("p", "尽管该数据集以“干净”著称，逐字段核验后仍发现四类需要处置的问题，处置策略与结果见表 4。"),
    ("tbl", "表 4  数据清洗处置一览",
     ["问题类型", "核验结果", "处置策略", "影响行数"],
     [["缺失值", "21 列均无空值", "无需填充", "0"],
      ["邮编格式", "449 条记录丢失前导 0（如 6824）", "按美国 5 位邮编规则补零", "449"],
      ["完全重复", "1 条业务字段完全重复", "删除，保留首条", "1"],
      ["同单多行", "7 组（Order ID, Product ID）重复", "核验为同单多次加购，保留", "0"],
      ["极端值", "销售额双重超限（IQR 与 3σ）", "标记 is_outlier，保留不删除", "127"],
      ["非法业务值", "金额/数量非正、折扣越界、负履约时长", "剔除", "0"]],
     [2.6, 5.4, 4.6, 2.0]),
    ("p", "需要特别说明两点。第一，邮编缺失并非真实缺失，而是 CSV 读取时前导 0 被当作数值截断所致，"
          "按 5 位规则补零即可修复，若直接删行会损失 4.5% 的地理信息。第二，18.7% 的明细行利润为负，"
          "这属于真实的促销亏损而非录入错误，因此本文只对“金额与数量非正、折扣越界”这类逻辑矛盾记录做剔除，"
          "对高销售额订单仅打标不删除——删除大额订单会系统性低估 GMV，反而破坏后续帕累托分析的真实性。"),
)
sec(
    "数据转换",
    ("p", "原始字段以文本形式存储日期与金额，直接参与计算会产生类型错误。本文统一将 Order Date、Ship Date 转换为 datetime，"
          "将 Sales、Profit、Discount 转为浮点并保留两位小数，将 Postal Code 转为 5 位字符串，Quantity 转为整型。"),
    ("p", "在此基础上派生 10 个分析字段，以支撑后续模型：Ship Days（履约天数）、Order Year/Month/Quarter/Weekday（时间维度）、"
          "YearMonth（月度粒度）、Profit Margin（利润率 = 利润/销售额）、Unit Price（单价）、Discount Band（折扣区间）、"
          "Is Loss（是否亏损）、is_outlier（是否极值）。派生后字段数由 21 增至 33，其中折扣区间与利润率是第 6 章利润诊断的核心变量。"),
)
sec(
    "数据整合",
    ("p", "多表关联遵循“先验键、后连接”的顺序：先校验事实表中的 Customer ID、Product ID、Order ID 是否都能在维度表中找到，"
          "确认孤儿记录为 0 条后再执行连接，避免因脏键导致的行数膨胀（笛卡尔积）。维度表内部按主键去重，"
          "保证一对一关系。"),
    ("p", "关于抽样：原始数据 9,994 行，清洗后 9,993 行，规模完全满足课程“主表不少于 500 条”的要求，"
          "因此全量使用、不做抽样，论文中所有结论均基于全样本。仅在两处使用了固定随机种子的抽样："
          "散点图为避免过度重叠抽取 2,500 条（random_state=42），客户分群 K-Means 设置 random_state=42，"
          "以保证结果可复现。数据最终导出为 CSV（全量明细）、JSON（前 1,000 条示例与元数据）与 SQLite"
          "（四张表 + 三个唯一索引）三种格式，便于不同工具复用与交叉验证。"),
)

# ============================ 第 4 章 ============================
sec(
    "模型选型",
    ("p", "模型选型遵循“问题驱动”而非“方法堆砌”的原则。本文的三个核心问题分别对应客户价值结构、利润侵蚀机制与增长可持续性，"
          "据此选择八类方法，覆盖描述、诊断与预测三个层次，对应关系见表 5。"),
    ("tbl", "表 5  模型选型与业务问题对应",
     ["编号", "模型/方法", "回答的业务问题", "核心输出"],
     [["M1", "趋势与同比/环比", "增长是否健康", "月度 GMV、同比增速"],
      ["M2", "帕累托 / ABC 分类", "销售额是否集中在少数客户与产品", "累计贡献曲线、ABC 分级"],
      ["M3", "RFM 八分类", "客户价值如何分层、如何差异化运营", "八类客户、ARPU"],
      ["M4", "同期群留存", "复购是自然留存还是营销唤醒", "季度留存热力图"],
      ["M5", "波士顿矩阵", "各子品类应加大投入还是收缩", "份额×增速四象限"],
      ["M6", "SARIMA 预测", "未来半年销售规模与不确定性", "点预测 + 95% 置信区间"],
      ["M7", "关联规则 Apriori", "是否存在可交叉销售的品类组合", "支持度/置信度/提升度"],
      ["M8", "客户价值漏斗", "从普通客户到高价值客户的流失环节", "四阶段转化率"]],
     [1.4, 3.6, 6.4, 3.2]),
)
sec(
    "参数与阈值设定依据",
    ("p", "模型参数若无业务依据，结论便无法落地。本文对关键阈值逐一说明如下。"),
    ("p", "（1）RFM 切分采用中位数而非均值或五分位。原因是零售客户消费额呈显著右偏分布，均值会被少数大客户拉高，"
          "导致“高价值”门槛失真；五分位切分虽然更细，但会使 793 位客户被切成 125 组，单组样本过小、无法支撑运营动作。"
          "中位数切分保证每一维度的高低两组人数均衡（396/397），既稳健又便于解释。本文以数据截止日（2017-12-30）的次日为"
          "快照日计算 R，最终阈值为 R≤76 天、F≥6 单、M≥2,256 美元。"),
    ("p", "（2）ABC 分级采用累计销售额 70% 与 90% 两个断点。70% 对应“少数客户贡献多数销售”的经验临界，"
          "90% 之后的长尾客户维护成本高于收益，故归入 C 类。该阈值同时与帕累托图的 80% 参考线交叉验证，"
          "确保分级结果不因单一阈值而失真。"),
    ("p", "（3）波士顿矩阵以子品类销售额份额为横轴、2017 年相对 2016 年的增长率为纵轴，象限边界取两个维度的中位数，"
          "而非固定的 1.0 相对份额。原因是本数据集只有单一企业，不存在“主要竞争对手”的真实份额数据，"
          "用内部份额中位数做相对划分更诚实，也在论文第 7 章作为局限明确说明。"),
    ("p", "（4）SARIMA 的阶数不由 AIC 单独决定，而以 6 期滚动回测的 MAPE 最小为准则，在 4×3 共 12 组候选参数中搜索。"
          "这一取舍在第 4.3 节给出实证：AIC 最优的参数组合回测误差反而更大，说明在本例中“拟合优度”不等于“预测能力”。"),
    ("p", "（5）Apriori 的最小支持度设为 0.8%、提升度下限 1.05。阈值不能再高，是因为该数据集平均每个订单仅含 1.83 个子品类，"
          "购物篮本身很“浅”；把支持度提到 2% 后仅剩 2 条规则，无法支撑分析。阈值也不能再低，否则会引入大量偶然共现。"),
    ("p", "（6）同期群采用季度而非月度口径。月度口径下，793 位客户被 48 个月切分后单群样本过小，留存率在 0~40% 间剧烈跳动；"
          "季度口径把 16 个同期群的样本量提升到 2~161 人，曲线更稳定。同时对观察窗口尚未到达的格子做右删失屏蔽，"
          "避免把“还没来得及观察”误读为“留存为 0”。"),
)
sec(
    "模型计算与验证",
    ("p", "由于篇幅所限，各模型的完整计算结果见 outputs/tables/ 下的对应结果表，此处报告与结论直接相关的验证指标。"),
    ("p", "预测模型采用 2014-01 至 2017-06 共 42 个月训练、2017-07 至 2017-12 共 6 个月回测，结果见表 6。"
          "SARIMA(1,1,0)×(0,1,1,12) 的回测 MAPE 为 16.76%、RMSE 为 17,283.69 美元；作为对照的 Holt-Winters"
          "（乘法趋势、加法季节）MAPE 为 15.61%、RMSE 为 17,461.16 美元。两者精度接近，Holt-Winters 的点预测略优，"
          "但 SARIMA 能给出解析形式的 95% 置信区间，且参数具有明确的统计含义，因此本文仍以 SARIMA 作为主模型，"
          "并把 Holt-Winters 作为精度基准，这一取舍本身即是“可解释性优先于微弱精度优势”的判断。"),
    ("tbl", "表 6  时间序列模型回测对比（2017-07 至 2017-12）",
     ["模型", "参数", "MAPE", "RMSE（美元）", "是否输出置信区间"],
     [["SARIMA", "(1,1,0)×(0,1,1,12)", "16.76%", "17,283.69", "是（95%）"],
      ["Holt-Winters", "乘法趋势 + 加法季节", "15.61%", "17,461.16", "否"]],
     [2.6, 4.2, 1.8, 2.8, 3.2]),
    ("p", "分类模型（RFM、ABC）属于规则型方法，其“验证”体现为分级结果的业务合理性：A 类客户 305 人（占 38.5%）"
          "贡献 70.0% 销售额，B 类贡献 20.0%，C 类贡献 10.0%，层间差异显著且单调，说明分级有效。"
          "关联规则的验证采用提升度而非置信度：最高提升度仅 1.15，说明子品类之间几乎不存在强关联，"
          "这一“阴性结果”同样是结论——它直接否定了“靠品类捆绑提升客单价”的假设。"),
)

# ============================ 第 5 章 ============================
sec(
    "数据探索性分析",
    ("p", "探索性分析的目标是先建立整体印象，再定位异常。图 1 给出四项核心指标：四年累计销售额 229.69 万美元、利润 28.64 万美元、"
          "整体利润率 12.47%，订单 5,009 笔、客户 793 位、客单价 458.56 美元。值得注意的是，18.71% 的明细行为亏损，"
          "亏损金额合计 −15.61 万美元，相当于利润总额的 54.5%——这意味着若能把亏损订单收敛一半，利润可提升近三成。"),
    ("fig", "fig01_KPI指标卡.png", "图 1  核心经营指标看板（2014—2017）"),
    ("p", "图 5 的月度趋势显示，销售额呈“整体上行 + 年末尖峰”的双重特征：11 月平均销售额为全年最高，是 2 月的 5.9 倍，"
          "季节性极强。3 期移动平均线在 2016 年下半年后持续抬升，说明增长并非单月偶发。"
          "图 14 的年×月热力图进一步确认，2017 年 9—12 月连续四个月处于深色区间，是四年中最强的旺季组合。"),
    ("fig", "fig05_月度销售额趋势折线图.png", "图 5  月度销售额趋势与 3 期移动平均"),
    ("fig", "fig14_年月销售额热力图.png", "图 14  年 × 月销售额热力图"),
    ("p", "从同比看，2015 年是唯一的负增长年（−2.78%），但利润反而增长 24.34%，说明该年主动收缩了低毛利业务；"
          "2016 年销售与利润同步高增（+29.47%、+32.74%）；2017 年销售仍增 20.36%，利润增速却回落至 14.24%，"
          "利润率由 13.43% 降至 12.74%，增长质量开始下滑。这一转折构成本文后续诊断的主线。"),
)
sec(
    "可视化模板复现",
    ("p", "按照课程要求，本文对照《Excel 数据可视化——从图表到数据大屏》中的典型模板，用 Matplotlib 复现了 16 类图表，"
          "在图表类型、布局结构、配色方案、标签样式、图例位置与标题设计上尽量贴近原模板，同时统一了中文宋体/黑体显示、"
          "单位标注与 150dpi 分辨率。"),
    ("fig", "fig02_子品类销售额条形图.png", "图 2  子品类销售额排名（排序条形图）"),
    ("p", "图 2 采用降序排序条形图，避免品类名称过长导致的标签重叠，并对 Top3 用强调色标注。Phones（33.0 万美元）、"
          "Chairs（32.8 万美元）、Storage（22.4 万美元）构成销售前三，三者合计占 34.1%。"),
    ("fig", "fig03_区域客户细分分组柱形图.png", "图 3  各区域 × 客户细分的销售额（分组柱形图）"),
    ("p", "图 3 把区域与客户细分放在同一坐标系内对比，组内标注数值。West（72.5 万美元）与 East（67.8 万美元）合计贡献 61.1%，"
          "Central 虽占 21.8%，利润率却只有 7.92%，不到 West（14.94%）的一半，是典型的“规模不经济”区域。"),
    ("fig", "fig04_年度品类堆积柱形图.png", "图 4  2014—2017 年销售额构成（堆积柱形图）"),
    ("p", "图 4 显示品类结构四年间基本稳定：Office Supplies 约占 31.4%、Furniture 32.3%、Technology 36.4%，"
          "没有出现结构性迁移。这意味着增长来自“每一类都多卖了一点”，而非“品类结构升级带动客单价”，"
          "为第 6 章“结构性问题被规模增长掩盖”的判断提供了依据。"),
    ("fig", "fig06_累计销售额面积图.png", "图 6  累计销售额面积图"),
    ("p", "图 6 用面积图呈现累计销售额，斜率即月度增量。2017 年段斜率明显陡于 2014 年段，直观印证了增长的加速，"
          "但斜率在 2017 年下半年趋于平缓，提示增长动能可能见顶。"),
    ("fig", "fig07_客户细分环形饼图.png", "图 7  客户细分销售额占比（环形饼图）"),
    ("p", "图 7 使用环形饼图并留出中心区域显示总额。Consumer 占 50.56%，是绝对主力；Home Office 仅占 18.69%，"
          "但利润率最高（14.05%），与其体量不匹配，属于“小而美”的细分市场。"),
    ("fig", "fig08_配送方式环形图.png", "图 8  配送方式订单占比与平均履约时长（环形图）"),
    ("p", "图 8 在环形图的图例中嵌入平均履约天数，把“结构占比”与“运营效率”两类信息压缩到一张图内。"
          "Standard Class 占 59.8% 的订单，平均 5.01 天送达；Same Day 仅占 5.27%，但平均 0.04 天（几乎当日达），"
          "其 12.8 万美元销售额对应的物流成本未被数据集记录，是本文的一处数据局限。"),
    ("fig", "fig09_折扣利润率散点图.png", "图 9  折扣率与利润率的关系（散点图 + 趋势线）"),
    ("p", "图 9 是全文最关键的一张图。散点几乎构成一条清晰的负斜率带，拟合线斜率约为 −1.2，相关系数 −0.86。"
          "当折扣率超过 20% 后，绝大多数点落入零轴以下，形成“折扣悬崖”。这张图为第 6 章“折扣红线”建议提供了直接证据。"),
    ("fig", "fig10_子品类气泡图.png", "图 10  子品类销售额 × 利润率气泡图"),
    ("p", "图 10 用气泡大小编码销量，把三个维度压缩进二维平面。左下区域（低销售额、负利润率）的 Tables 与 Bookcases 尤为醒目——"
          "它们不是“卖不动”，而是“卖得越多亏得越多”。"),
    ("fig", "fig11_区域能力雷达图.png", "图 11  四大区域经营能力雷达图"),
    ("p", "图 11 将五个维度按最大值归一后绘制雷达图。West 在销售额、利润、订单量三项上包络最大，Central 则在客单价维度相对突出但利润维度塌陷，"
          "与图 3 的结论互相印证。"),
    ("fig", "fig12_利润变动瀑布图.png", "图 12  2016→2017 利润变动瀑布图"),
    ("p", "图 12 把 2017 年利润较 2016 年的 1.16 万美元增量拆解到品类：Technology 贡献 +1.09 万美元、Office Supplies +0.47 万美元，"
          "Furniture 反向拖累 −0.39 万美元。瀑布图的价值在于把“总利润增长 14.2%”这一笼统结论还原为可归责的结构。"),
    ("fig", "fig13_品类矩形树图.png", "图 13  品类—子品类销售额矩形树图"),
    ("p", "图 13 用两层矩形树图表达“品类—子品类”的层级结构，面积即销售额。三个大类的面积接近，说明企业并不存在单一支柱品类，"
          "这在抗风险上是优点，在规模效应上却是劣势。"),
    ("fig", "fig15_折扣区间利润率箱线图.png", "图 15  不同折扣区间的利润率分布（箱线图）"),
    ("p", "图 15 按五个折扣区间分组绘制箱线图。无折扣组中位数约 30%，低折扣组降至 12%，中折扣组跌破 0，"
          "高折扣与超高折扣组的中位数分别为 −41% 与 −123%，且箱体整体位于零轴之下，说明这已不是个别订单的波动，而是系统性亏损。"),
    ("fig", "fig16_销售利润组合图.png", "图 16  近 24 个月销售额与利润组合图（柱＋线双轴）"),
    ("p", "图 16 用双轴组合图把销售额（柱）与利润（折线）放在同一时间轴上。两条曲线在 2017 年四季度出现明显背离："
          "销售额冲高而利润回落，直观呈现了“增收不增利”的发生时点。"),
    ("p", "与 Excel 实现相比，Python 复现的差异主要体现在三方面：一是可编程性，配色、字体、标注可封装为函数复用，"
          "24 张图的风格天然统一；二是可复现性，图表由数据直接生成，数据更新后重跑脚本即可，而 Excel 需手工重绘；"
          "三是对复杂图形的支持，如矩形树图、雷达图、瀑布图在 Excel 中需借助插件或手工拼接，Matplotlib 只需数十行代码。"
          "当然，Excel 在交互探索与即时预览上仍更轻便，这也是本文把二者定位为“Excel 用于查看核对、Python 用于生产图表”的原因。"),
)
sec(
    "业务模型图",
    ("p", "本节 7 张图与第 4 章的模型一一对应，每张图至少支撑一条商业结论。"),
    ("fig", "fig17_RFM客户分布气泡图.png", "图 17  RFM 八分类客户分布气泡图"),
    ("p", "图 17 以 R 为横轴（反向，越靠右越久未购）、F 为纵轴、气泡面积为 M，虚线为中位数切分线。四个象限组合出八类客户："
          "右下角的“重要价值客户”199 人，仅占 25.1% 却贡献 39.5% 销售额；左下的“重要唤回客户”115 人平均 175 天未购，"
          "是召回优先级最高的人群；左下角的“重要挽留客户”52 人平均 310 天未购但历史消费达 4,461 美元，属于“高价值流失前夜”。"
          "四类“重要客户”合计仅占 50.1% 的人数，却贡献 80.2% 的销售额。"),
    ("fig", "fig18_客户帕累托图.png", "图 18  客户销售额帕累托图与 ABC 分类"),
    ("p", "图 18 的累计曲线显示，客户集中度并未达到经典的“二八定律”：需要 38.5% 的客户（305 人）才能覆盖 70% 销售额，"
          "覆盖 80% 则需要 49.8% 的客户（395 人）。这说明该企业的客户结构相对“扁平”，头部依赖不严重，"
          "但也意味着单靠服务少数大客户难以支撑增长。产品维度则相反：1,862 个产品中 15.0% 贡献 70% 销售额，"
          "SKU 层面的帕累托特征非常显著，且 301 个产品累计亏损。"),
    ("fig", "fig19_子品类波士顿矩阵.png", "图 19  子品类波士顿矩阵（份额 × 增速）"),
    ("p", "图 19 按份额与增速中位数划分四象限。明星业务 5 个：Phones、Binders、Accessories、Copiers、Storage；"
          "金牛 4 个：Chairs、Machines、Tables、Bookcases；问题 4 个；瘦狗 4 个。这里必须指出一个反直觉现象："
          "被划为“金牛”的 Tables 与 Bookcases 实际利润率为 −8.56% 与 −3.02%。原因是波士顿矩阵只反映份额与增速，"
          "不反映盈利性。若机械照搬矩阵结论“金牛提供现金流”，企业会继续加码两个亏损品类。因此本文在使用该矩阵时，"
          "叠加利润率做了二次判断，这也是本文对经典模型的一处批判性修正。"),
    ("fig", "fig20_同期群留存热力图.png", "图 20  季度同期群留存热力图"),
    ("p", "图 20 按首购季度把 793 位客户分为 16 个同期群，观察其在后续 8 个季度的留存。T+1 平均留存 24.31%，"
          "此后并未持续衰减，而是在 T+4 回升至 25.58%——这种“先降后升”的形态说明该企业并非依靠自然复购，"
          "而是通过季节性促销把客户“唤醒”。2016Q1、2016Q2 两个同期群的 T+1 留存分别高达 43% 与 59%，"
          "是四年中表现最好的获客批次，可作为后续获客质量的对标基准。"),
    ("fig", "fig21_SARIMA销售额预测.png", "图 21  SARIMA 销售额预测（点预测 + 95% 置信区间）"),
    ("p", "图 21 左段为实际序列，虚线为 2017 年下半年的回测预测，右段为 2018 年上半年的点预测与 95% 置信区间。"
          "预测值合计 35.64 万美元，较 2017 年同期 25.69 万美元增长 38.7%，明显高于 2017 年全年 20.4% 的增速。"
          "结合 16.76% 的回测误差，本文认为该点预测偏乐观，更合理的用法是：以置信区间下沿做保守预算、上沿做备货上限，"
          "并以 20% 左右的增速作为中枢预期。这是模型输出与业务判断相结合的典型案例——模型给区间，人给判断。"),
    ("fig", "fig22_关联规则图.png", "图 22  关联规则 Top10（Apriori）"),
    ("p", "图 22 展示提升度最高的 10 条规则，最高仅 1.154（Fasteners→Paper，置信度 27.4%、支持度 1.2%）。"
          "提升度普遍贴近 1，说明子品类之间接近独立购买。这一阴性结论具有明确的管理含义：该企业不适合投入资源做"
          "“品类捆绑套餐”，提升客单价应转向加购推荐与满减门槛设计。"),
    ("fig", "fig23_客户价值漏斗.png", "图 23  客户价值漏斗"),
    ("p", "图 23 显示，793 位客户中有 98.5% 产生过复购（781 人），75.4% 达到 5 单以上（598 人），"
          "但最终只有 25.1%（199 人）进入“重要价值客户”。末级转化率仅 33.3%，说明“高频但低价值”的客户大量存在——"
          "他们买得多、客单价低，是典型的促销敏感型人群，也是利润被侵蚀的主要来源。"),
)
sec(
    "交互式可视化大屏",
    ("p", "为把分散的图表整合为可探索的分析界面，本文用 Python 生成了一个自包含的交互式大屏（outputs/dashboard/dashboard.html，"
          "约 2.0 MB，双击即可离线打开）。大屏以 ECharts 5.5.1 渲染，全部数据以列式数组内嵌，"
          "所有聚合在前端按筛选条件实时计算，未使用 Power BI、Tableau、Fine BI 等任何 BI 软件，也未手工编辑任何图表元素。"),
    ("p", "大屏共含 8 类组件：（1）4 张 KPI 指标卡（GMV、利润、订单量、客户数）；（2）月度销售额与利润趋势图；"
          "（3）品类销售结构环形图；（4）区域销售额条形图；（5）折扣率×利润率散点图；（6）州 Top10 销售额条形图；"
          "（7）子品类经营明细表；（8）年份/区域/品类三个筛选器与重置按钮。组件数量与类型均满足课程“不少于 6 个联动组件”的要求。"),
    ("p", "联动机制有两层：一是筛选联动，任一筛选器变化时，KPI、5 张图与明细表基于同一份过滤后数据同步重算，"
          "保证各组件口径一致；二是图形联动，点击区域条形图的柱子或品类环的扇区，会自动把对应筛选器设为该值并触发全局刷新，"
          "实现“图表即筛选器”的下钻体验。图 24 为大屏版式的静态预览（与 HTML 同源同数据）。"),
    ("fig", "fig24_大屏布局预览.png", "图 24  大屏布局预览（交互版见 dashboard.html）"),
    ("p", "与大屏配套的是一键复现脚本：执行 python run_all.py 后，五个脚本依次完成加载、清洗、建模、出图与大屏生成，"
          "全流程约 1~2 分钟。大屏不依赖任何外部网络资源（ECharts 已内联），在断网环境下同样可用，这一点对于课堂演示尤为重要。"),
)

# ============================ 第 6 章 ============================
sec(
    "案例背景",
    ("p", "该企业是一家面向美国市场的办公用品零售与分销商，通过 Consumer、Corporate、Home Office 三类渠道销售"
          "家具、办公用品与科技产品，共 17 个子品类、1,862 个 SKU。2014—2017 年，企业销售额从 48.4 万美元增长到 73.3 万美元，"
          "年均复合增速 14.9%，但利润率始终在 10%~13.5% 之间徘徊，2017 年甚至下滑。管理层面临的核心困惑是："
          "促销力度逐年加大，销售额确实在涨，利润为何不涨？"),
)
sec(
    "结果解读",
    ("p", "第一，增长质量在下滑。2017 年销售额同比增长 20.36%，利润仅增 14.24%，利润率由 13.43% 降至 12.74%，"
          "下降 0.69 个百分点。按 2017 年销售额测算，这 0.69 个百分点相当于约 5,060 美元的利润损失。"
          "更值得警惕的是，2015 年曾出现“销售下降 2.78%、利润增长 24.34%”的反向组合，说明企业具备通过收缩低毛利业务改善利润的能力，"
          "但 2016 年后重新回到“以价换量”的路径。"),
    ("p", "第二，折扣是利润侵蚀的主因，但不是唯一原因。折扣率与利润率的相关系数为 −0.86，拟合斜率约 −1.2，"
          "即折扣每增加 1 个百分点，利润率下降约 1.2 个百分点。分组看，无折扣订单利润率 29.51%、亏损订单占比 0%；"
          "折扣 20%~40% 区间利润率转负（−15.31%），亏损订单占比 90.2%；折扣超过 40% 的两档合计销售额 12.86 万美元、"
          "利润 −9.96 万美元、利润率 −77.4%，亏损订单占比 100%。然而折扣并非全部解释：Binders 的平均折扣高达 37%，"
          "利润率仍有 14.86%；而 Tables 的平均折扣只有 26%，利润率却是 −8.56%。这说明 Tables 的亏损更多来自成本结构"
          "（大件家具的物流与仓储成本），而非折扣本身。把两件事混为一谈，会导致“一刀切降折扣”的错误决策。"),
    ("p", "第三，客户结构“扁平但不均匀”。从人数看，A 类客户占 38.5%，头部依赖不严重；从价值看，四类“重要客户”占 50.1% 人数、"
          "贡献 80.2% 销售额，分层清晰。真正的风险在于漏斗末级：98.5% 的客户都复购过，但只有 25.1% 成为重要价值客户，"
          "大量“高频低值”客户靠促销维持，这正是折扣成本的主要承载者。"),
    ("p", "第四，复购依赖外部唤醒而非自然留存。季度同期群 T+1 留存 24.31%、T+4 回升至 25.58%，说明客户在沉寂 2~3 个季度后"
          "会被促销重新激活。这种模式短期有效，长期会训练客户“只在打折时购买”，进一步压缩利润空间，形成负向循环。"),
)
sec(
    "商业建议",
    ("p", "基于上述诊断，本文提出五条可操作、有数据支撑的建议，其依据与预期效果见表 7。"),
    ("tbl", "表 7  商业建议、数据依据与预期效果",
     ["建议", "数据依据", "具体动作", "预期效果"],
     [["1. 建立折扣审批红线", "折扣≥40% 的订单亏损占比 100%，利润率 −77.4%", "折扣 >40% 须经理审批；20%~40% 区间设置品类差异化上限", "削减约 9.96 万美元亏损敞口"],
      ["2. 分层运营客户", "四类重要客户占 50.1% 人数、贡献 80.2% 销售额", "重要价值客户做留存（专属客服）；重要唤回客户（115 人、平均 175 天未购）做定向召回", "提升头部客户复购与客单"],
      ["3. 清理负利润子品类", "Tables、Bookcases 合计销售额 32.18 万美元、利润 −2.12 万美元", "Tables 停止无差别促销、改为预约式销售；Bookcases 收缩 SKU", "释放被侵蚀的利润"],
      ["4. 优化区域资源配置", "Central 销售额占 21.8%，利润率仅 7.92%", "复核 Central 的物流成本与折扣政策，向 West/East 的成功经验对标", "区域利润率向 13% 靠拢"],
      ["5. 用加购替代品类捆绑", "最高关联规则提升度仅 1.15，购物篮平均 1.83 个品类", "放弃品类套餐，改为满减门槛与关联推荐位", "提升客单价且不损伤毛利"]],
     [2.6, 4.2, 4.6, 3.2], 9.5),
    ("p", "五条建议按“止血—增效—结构优化”排序：建议 1 与建议 3 属于止血，见效最快；建议 2 与建议 4 属于增效，需要 1~2 个季度;"
          "建议 5 属于结构优化，需配合商品运营系统改造。之所以把折扣红线放在首位，是因为它对应的是确定性最高、规模最大的损失来源。"),
)

# ============================ 第 7 章 ============================
sec(
    "研究结论",
    ("p", "本文以 Superstore 零售订单数据为对象，完成了从数据获取到商业建议的端到端分析，主要结论有四。"),
    ("p", "其一，该企业四年间销售额增长 51.5%，但利润率从 10.24% 波动至 12.74%，2017 年出现“增收不增利”，"
          "增长质量下滑是当前最主要的问题。"),
    ("p", "其二，折扣是利润侵蚀的首要可控因素，折扣率与利润率相关系数 −0.86，折扣超过 40% 的订单几乎必然亏损；"
          "但品类成本结构（如 Tables）是独立于折扣的第二条亏损路径，二者需分开治理。"),
    ("p", "其三，客户价值分层有效但并不极端：A 类客户占 38.5% 贡献 70% 销售额，四类重要客户占一半人数贡献八成销售额；"
          "客户漏斗末级转化率仅 33.3%，“高频低值”人群是折扣成本的主要承载者。"),
    ("p", "其四，需求季节性极强（11 月为 2 月的 5.9 倍），SARIMA 回测 MAPE 16.76%，2018 年上半年点预测 35.64 万美元且区间较宽，"
          "说明在短序列、强季节、含促销尖峰的场景下，点预测应作为区间使用而非精确目标。"),
)
sec(
    "局限性与展望",
    ("p", "本文存在四点局限。第一，数据仅覆盖单一企业、四年时间，无法做跨企业对标，波士顿矩阵只能以内部份额中位数代替真实市场份额，"
          "削弱了该模型的原意。第二，数据集缺少成本、物流费用与促销投放费用字段，因此“利润率”只能反映折扣后的账面结果，"
          "无法进一步分解为“折扣损失”与“履约成本”两部分。第三，SARIMA 训练样本仅 42 个月，参数估计的稳定性有限，"
          "95% 置信区间宽度达到点预测的 50% 以上，实际使用需结合业务判断修正。第四，同期群分析以季度为粒度，"
          "无法刻画月内的促销节奏影响。"),
    ("p", "后续可从三个方向深化：一是引入外部数据（如区域经济指标、竞品价格）做面板回归，识别价格弹性；"
          "二是用 Prophet 或带促销虚拟变量的 SARIMAX 处理尖峰，比较不同模型在“促销月”的误差差异；"
          "三是把 RFM 分层与 CLV（客户生命周期价值）结合，将客户运营从“当期价值”升级为“长期价值”管理。"),
)
sec(
    "AI 使用披露",
    ("p", "本文在以下环节使用了 AI 编程助手（DeepSeek）：（1）数据分析流程设计，包括星型模型拆分与模型选型的讨论；"
          "（2）Python 代码调试，如 Matplotlib 中文字体配置、statsmodels 的 SARIMA 参数搜索；"
          "（3）论文语言的组织与润色。"),
    ("p", "所有模型口径、阈值设定与业务结论均由本人在 AI 辅助下逐项复核：例如 RFM 采用中位数切分的理由、"
          "SARIMA 以回测误差而非 AIC 选阶的决定、波士顿矩阵与利润率冲突的修正，均是本人基于数据验证后的判断，"
          "并非直接采纳 AI 输出。数据获取、清洗与全部图表均由可复现代码生成，无人工编造数值。"),
    ("p", "关键提示词示例：“用 pandas 对这张订单明细表按客户聚合 R/F/M，并用中位数切分做八分类，说明每个分类的运营含义”；"
          "“statsmodels 的 SARIMA 在 48 个月序列上回测 MAPE 偏高，如何诊断是季节性设定问题还是样本量问题”。"),
)

# ============================ 参考文献与附录 ============================
REFS = [
    "Hyndman R J, Athanasopoulos G. Forecasting: Principles and Practice (3rd ed.)[M]. Melbourne: OTexts, 2021.",
    "Box G E P, Jenkins G M, Reinsel G C, et al. Time Series Analysis: Forecasting and Control (5th ed.)[M]. Hoboken: Wiley, 2015.",
    "Agrawal R, Srikant R. Fast algorithms for mining association rules[C]//Proceedings of the 20th International Conference on Very Large Data Bases. Santiago, 1994: 487-499.",
    "Hughes A M. Strategic Database Marketing (3rd ed.)[M]. New York: McGraw-Hill, 2005.",
    "McKinney W. Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter (3rd ed.)[M]. Sebastopol: O'Reilly Media, 2022.",
    "Hunter J D. Matplotlib: A 2D graphics environment[J]. Computing in Science & Engineering, 2007, 9(3): 90-95.",
    "周志华. 机器学习[M]. 北京: 清华大学出版社, 2016.",
    "王汉生. 数据思维: 从数据分析到商业价值[M]. 北京: 中国人民大学出版社, 2017.",
    "Apache Software Foundation. Apache ECharts Documentation[EB/OL]. https://echarts.apache.org/zh/index.html, 2026-10-30.",
    "Kaggle. Superstore Dataset[DB/OL]. https://www.kaggle.com/datasets/vivek468/superstore-dataset-final, 2026-10-31.",
]

APPENDIX_CODE = [
    "# RFM 八分类（scripts/03_analysis.py 节选）",
    "snapshot = df['Order Date'].max() + pd.Timedelta(days=1)",
    "rfm['R'] = (snapshot - rfm['last']).dt.days        # 最近一次购买间隔",
    "rfm['F'] = rfm['orders']                            # 购买频次",
    "rfm['M'] = rfm['sales']                             # 累计消费额",
    "r_med = rfm['R'].median()    # 三指标中位数",
    "f_med = rfm['F'].median()",
    "m_med = rfm['M'].median()",
    "rfm['R_score'] = np.where(rfm['R'] <= r_med, 1, 0)  # 1 = 更近（优）",
    "rfm['F_score'] = np.where(rfm['F'] >= f_med, 1, 0)",
    "rfm['M_score'] = np.where(rfm['M'] >= m_med, 1, 0)",
    "rfm['Segment'] = [name_seg(r, f, m) for r, f, m in",
    "                   zip(rfm['R_score'], rfm['F_score'], rfm['M_score'])]",
]

APPENDIX_TREE = [
    "repo/",
    "├── data/raw/          原始数据（superstore.zip、superstore_raw.csv）",
    "├── data/clean/        清洗后数据（CSV / JSON / SQLite）",
    "├── scripts/           01_load.py ~ 05_dashboard.py",
    "├── outputs/figures/   fig01 ~ fig24（150dpi PNG）",
    "├── outputs/tables/    各模型结果表与 facts.json",
    "├── outputs/dashboard/ dashboard.html（自包含交互大屏）",
    "├── docs/              期末大论文、数据来源合规声明",
    "├── requirements.txt",
    "├── run_all.py         一键复现入口",
    "└── README.md          项目说明与图表索引",
]

FIG_INDEX = [
    ("fig01", "KPI 指标卡", "模板复现"), ("fig02", "排序条形图", "模板复现"),
    ("fig03", "分组柱形图", "模板复现"), ("fig04", "堆积柱形图", "模板复现"),
    ("fig05", "折线 + 移动平均", "模板复现"), ("fig06", "面积图", "模板复现"),
    ("fig07", "环形饼图", "模板复现"), ("fig08", "环形图 + 指标图例", "模板复现"),
    ("fig09", "散点 + 趋势线", "模板复现"), ("fig10", "气泡图", "模板复现"),
    ("fig11", "雷达图", "模板复现"), ("fig12", "瀑布图", "模板复现"),
    ("fig13", "矩形树图", "模板复现"), ("fig14", "热力图", "模板复现"),
    ("fig15", "箱线图", "模板复现"), ("fig16", "柱线组合双轴图", "模板复现"),
    ("fig17", "RFM 气泡散点（M3）", "业务模型图"), ("fig18", "帕累托 / ABC（M2）", "业务模型图"),
    ("fig19", "波士顿矩阵（M5）", "业务模型图"), ("fig20", "同期群热力图（M4）", "业务模型图"),
    ("fig21", "SARIMA 预测（M6）", "业务模型图"), ("fig22", "关联规则（M7）", "业务模型图"),
    ("fig23", "客户价值漏斗（M8）", "业务模型图"), ("fig24", "大屏布局预览", "大屏"),
]


# ---------------------------------------------------------------- 文档装配
def find_par(doc, text):
    for p in doc.paragraphs:
        if p.text.strip() == text.strip():
            return p
    return None


def find_heading(doc, key):
    """按前缀匹配标题（模板标题带有括号形式的写作提示）。"""
    for p in doc.paragraphs:
        if not p.style.name.startswith("Heading"):
            continue
        txt = p.text.strip()
        if txt == key or txt.startswith(key + "（") or txt.startswith(key + "("):
            return p
    return None


def normalize_heading(p, key):
    """去掉模板标题中的括号提示，保留原有样式与自动编号。"""
    if p.text.strip() == key:
        return
    for r in list(p.runs)[1:]:
        r.text = ""
    if p.runs:
        p.runs[0].text = key
    else:
        p.add_run(key)


def remove_par(p):
    el = p._element
    el.getparent().remove(el)


def append_after(cursor_el, new_el):
    cursor_el.addnext(new_el)
    return new_el


def fill_cover(doc):
    p = find_par(doc, "题　　目：" + "　" * 21) or None
    # 题目行：清空占位空格后写入题目
    for para in doc.paragraphs[:12]:
        if para.text.strip().startswith("题") and "目" in para.text:
            for r in para.runs[1:]:
                r.text = ""
            para.runs[0].text = "题　　目："
            r = para.add_run(TITLE)
            set_run(r, "楷体", 14)
            break
    for para in doc.paragraphs[:14]:
        t = para.text.strip()
        flat = t.replace("　", "").replace(" ", "")
        for label, value in (("学　　院", "数据科学学院"), ("专业班级", "＿＿＿＿＿＿"), ("学　　号", "＿＿＿＿＿＿"),
                             ("姓　　名", "＿＿＿＿＿＿"), ("完成日期", "2026年11月4日")):
            key = label.replace("　", "")
            if flat.startswith(key) and "：" in flat:
                for r in para.runs[1:]:
                    r.text = ""
                para.runs[0].text = label + "："
                if value:
                    r = para.add_run(value)
                    set_run(r, "楷体", 14)
                break

    # 第 2 页：论文题目 / 作者 / 机构
    for para in doc.paragraphs[10:20]:
        if "论文题目" in para.text:
            for r in para.runs:
                r.text = ""
            r = para.add_run(TITLE)
            set_run(r, "黑体", 16)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif para.text.strip().startswith("作者"):
            for r in para.runs:
                r.text = ""
            r = para.add_run(AUTHOR)
            set_run(r, "宋体", 10.5)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif para.text.strip().startswith("（嘉兴大学"):
            for r in para.runs:
                r.text = ""
            r = para.add_run("（嘉兴大学 数据科学学院）")
            set_run(r, "宋体", 10.5)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER


def fill_abstract(doc):
    for para in doc.paragraphs:
        if para.text.strip().startswith("摘要（四号黑体）"):
            for r in list(para.runs):
                r.text = ""
            r1 = para.add_run("摘要")
            set_run(r1, "黑体", 14)
            r2 = para.add_run("：")
            set_run(r2, "黑体", 14)
            r3 = para.add_run(ABSTRACT)
            set_run(r3, "宋体", 12)
            pf = para.paragraph_format
            pf.line_spacing = 1.5
            pf.first_line_indent = Pt(24)
            pf.space_before = Pt(12)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            break
    for para in doc.paragraphs:
        if para.text.strip().startswith("关键词（四号黑体）"):
            for r in list(para.runs):
                r.text = ""
            r1 = para.add_run("关键词")
            set_run(r1, "黑体", 14)
            r2 = para.add_run("：")
            set_run(r2, "黑体", 14)
            r3 = para.add_run(KEYWORDS)
            set_run(r3, "宋体", 12)
            pf = para.paragraph_format
            pf.line_spacing = 1.5
            pf.first_line_indent = Pt(24)
            pf.space_before = Pt(12)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            break
    # 删除红字提示
    for para in list(doc.paragraphs):
        if para.text.strip().startswith("注意：全文红色字体均可删除"):
            remove_par(para)


def add_block(doc, cursor, block):
    kind = block[0]
    if kind == "p":
        p = body_para(doc, block[1])
        return append_after(cursor, p._p)
    if kind == "fig":
        p = image_para(doc, block[1])
        cursor = append_after(cursor, p._p)
        c = caption_para(doc, block[2])
        return append_after(cursor, c._p)
    if kind == "tbl":
        cap, t = table_block(doc, block[1], block[2], block[3], widths=block[4] if len(block) > 4 else None,
                             font=block[5] if len(block) > 5 else 10.5)
        cursor = append_after(cursor, cap._p)
        cursor = append_after(cursor, t._tbl)
        blank = doc.add_paragraph()
        blank.paragraph_format.space_before = Pt(0)
        blank.paragraph_format.space_after = Pt(0)
        blank.paragraph_format.line_spacing = 1.0
        small = blank.add_run("")
        set_run(small, "宋体", 6)
        return append_after(cursor, blank._p)
    return cursor


def build_body(doc):
    for heading, blocks in CONTENT:
        hp = find_heading(doc, heading)
        if hp is None:
            print(f"  !! 未找到标题：{heading}")
            continue
        normalize_heading(hp, heading)
        # 删除标题后的空段落
        nxt = hp._p.getnext()
        while nxt is not None and nxt.tag.endswith("}p"):
            from docx.text.paragraph import Paragraph
            para = Paragraph(nxt, hp._parent)
            if para.text.strip() == "" and para.style.name == "Normal":
                nxt_next = nxt.getnext()
                nxt.getparent().remove(nxt)
                nxt = nxt_next
            else:
                break
        cursor = hp._p
        for b in blocks:
            cursor = add_block(doc, cursor, b)


def build_refs(doc):
    hp = find_par(doc, "参考文献")
    star = find_par(doc, "[1] ***. ********[J]. ***, 5(6): 7-8.")
    if star is not None:
        remove_par(star)
    cursor = hp._p
    for i, ref in enumerate(REFS, 1):
        p = body_para(doc, f"[{i}] {ref}", indent=False, size=10.5)
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.left_indent = Pt(0)
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        cursor = append_after(cursor, p._p)


def build_appendix(doc):
    # A 核心代码片段
    p = find_par(doc, "A 核心代码片段")
    cursor = p._p
    intro = body_para(doc, "以下为 RFM 八分类的核心实现（完整代码见 scripts/03_analysis.py）：")
    cursor = append_after(cursor, intro._p)
    codes = [ln for ln in APPENDIX_CODE]
    for ln in codes:
        cp = doc.add_paragraph()
        cp.style = doc.styles["Normal"]
        pf = cp.paragraph_format
        pf.first_line_indent = Pt(0)
        pf.left_indent = Pt(12)
        pf.line_spacing = 1.0
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        r = cp.add_run(ln if ln else " ")
        set_run(r, "宋体", 8.5, mono=True)
        cursor = append_after(cursor, cp._p)

    # B 仓库链接与目录结构
    p = find_par(doc, "B Gitee/github仓库链接与目录结构")
    cursor = p._p
    for txt in ["仓库地址：https://gitee.com/〔用户名〕/superstore-analysis　（提交前请替换为实际公开仓库地址）",
                "目录结构如下："]:
        bp = body_para(doc, txt)
        cursor = append_after(cursor, bp._p)
    for ln in APPENDIX_TREE:
        cp = doc.add_paragraph()
        cp.style = doc.styles["Normal"]
        pf = cp.paragraph_format
        pf.first_line_indent = Pt(0)
        pf.left_indent = Pt(12)
        pf.line_spacing = 1.0
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        r = cp.add_run(ln)
        set_run(r, "宋体", 9, mono=True)
        cursor = append_after(cursor, cp._p)

    # C 图表索引
    p = find_par(doc, "C 图表索引（fig01–fig24+ 大屏截图）")
    if p is not None:
        for r in p.runs[2:]:
            r.text = ""
        p.runs[0].text = "C"
        p.runs[1].text = " "
        tail = p.add_run("图表索引（fig01–fig24，大屏见 dashboard.html）")
        set_run(tail, "宋体", 12)
    cursor = p._p
    p.paragraph_format.page_break_before = True
    rows = [[a, f"{b}", c] for a, b, c in FIG_INDEX]
    cap, t = table_block(doc, "表 8  图表索引", ["编号", "图表类型/说明", "类别"], rows,
                         [2.2, 8.4, 3.4], 9.5)
    cursor = append_after(cursor, cap._p)
    cursor = append_after(cursor, t._tbl)


def disable_doc_grid(doc):
    """关闭文档网格：中文模板默认按网格对齐，会把 1.5 倍行距撑成 2 倍以上。"""
    for section in doc.sections:
        sect = section._sectPr
        grid = sect.find(qn("w:docGrid"))
        if grid is not None:
            grid.set(qn("w:type"), "none")
    for p in doc.paragraphs:
        pPr = p._p.get_or_add_pPr()
        snap = pPr.find(qn("w:snapToGrid"))
        if snap is None:
            snap = pPr.makeelement(qn("w:snapToGrid"), {})
        snap.set(qn("w:val"), "0")
        # 按 OOXML 顺序插到 spacing 之前
        spacing = pPr.find(qn("w:spacing"))
        if spacing is not None:
            spacing.addprevious(snap)
        elif snap.getparent() is None:
            pPr.append(snap)


def count_chars(doc):
    import re
    text = "".join(p.text for p in doc.paragraphs)
    cn = len(re.findall(r"[\u4e00-\u9fff]", text))
    total = len(re.sub(r"\s", "", text))
    return cn, total


def main() -> None:
    if not os.path.exists(TEMPLATE):
        raise SystemExit(f"找不到模板：{TEMPLATE}")
    os.makedirs(DOCS, exist_ok=True)
    shutil.copy(TEMPLATE, OUT)
    doc = Document(OUT)

    fill_cover(doc)
    fill_abstract(doc)
    build_body(doc)
    build_refs(doc)
    build_appendix(doc)
    disable_doc_grid(doc)

    doc.save(OUT)
    cn, total = count_chars(Document(OUT))
    print(f"已生成：{OUT}")
    print(f"中文字符 {cn}，去空白字符 {total}")


if __name__ == "__main__":
    main()

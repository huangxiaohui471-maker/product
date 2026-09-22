# -*- coding: utf-8 -*-
"""生成《全球选品平台_字段口径表_v1.3.xlsx》

v1.3 的改动（对应机会洞察规则改版）：
  - 窗口期：去掉「关联达人数 ≤ 15」「销售额 ≥ 100 万」两个门槛，只看环比增速；
    达人数改为展示用的「达人渗透度」（未铺开 / 起量 / 已铺开）
  - 改良机会：由「退货率 ≥ 10% 且 销量 ≥ 3 万」改为「差评关键词非空」
  - 风险提醒：由「退货率 ≥ 12% 或 环比 < 0」改为「环比 < 0 或 差评关键词含高危词」
  - 字段 33 → 35：口碑层新增「好评关键词」「评价来源」

v1.2 的改动（对应用户提出的「重新梳理每个国家的数据来源 / 数据能不能走通」）：
  - 新增 Sheet「数据源接入台账」：市场 × 数据源 的覆盖与可得字段台账
  - 新增 Sheet「洞察规则与前提」：5 条规则分别依赖哪些字段、能否自动算出
  - 新增 Sheet「字段可得性」：33 个字段逐个标注 平台可导 / 部分可导 / 需人工标
  - 新增 Sheet「市场可走通性」：每个市场的结论与卡点
  - 保留「三平台取数映射」「版本说明」；字段口径以线上页面为准自动抽取，避免两处漂移

重要：本机 recalc 引擎不可用（无 LibreOffice、无 python formulas 包），
      全表不使用任何 Excel 公式。
"""
import json
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE = "/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47"
OUT = BASE + "/全球选品平台_字段口径表_v1.3.xlsx"
HTML = BASE + "/全球选品平台.html"

HEAD_FILL = PatternFill("solid", fgColor="1F3A5F")
HEAD_FONT = Font(name="PingFang SC", size=11, bold=True, color="FFFFFF")
CELL_FONT = Font(name="PingFang SC", size=10.5, color="1D1D1F")
GRP_FONT = Font(name="PingFang SC", size=10.5, bold=True, color="0B4F9E")
GRP_FILL = PatternFill("solid", fgColor="EAF2FC")
WARN_FONT = Font(name="PingFang SC", size=10.5, color="A52214")
OK_FONT = Font(name="PingFang SC", size=10.5, color="14663A")
THIN = Side(style="thin", color="D8DCE2")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
TOP_WRAP = Alignment(vertical="top", wrap_text=True)


def style_sheet(ws, widths, n_cols, freeze="A2"):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(vertical="center", horizontal="left", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = freeze


def fill_rows(ws, rows, start=2, group_col=None, colorize=None, heights=None):
    r = start
    for row in rows:
        is_group = group_col is not None and isinstance(row[0], str) and row[0].startswith("###")
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=(val[3:] if is_group else val))
            cell.font = GRP_FONT if is_group else CELL_FONT
            cell.alignment = TOP_WRAP
            cell.border = BORDER
            if is_group:
                cell.fill = GRP_FILL
        if colorize and not is_group:
            colorize(ws, r, row)
        if heights:
            ws.row_dimensions[r].height = heights
        r += 1
    return r


# ---------- 从线上页面抽取 FIELDS / SOURCES，保证文档与产品同源 ----------
def load_page_meta():
    src = open(HTML, encoding="utf-8").read()
    js = re.findall(r"<script>(.*?)</script>", src, re.S)[-1]
    fields, sources = [], []
    # FIELDS 条目：{ n: 'x', t: 'y', g: 'z', src: 'auto' }
    for m in re.finditer(
        r"\{\s*n:\s*'([^']+)',\s*t:\s*'([^']+)'(?:,\s*req:\s*true)?(?:,\s*g:\s*'([^']+)')?"
        r"(?:,\s*src:\s*'([^']+)')?(?:,\s*opts:\s*\[([^\]]*)\])?", js
    ):
        name, typ, grp, s, opts = m.groups()
        if not grp:
            continue
        opt_list = re.findall(r"'([^']+)'", opts) if opts else []
        fields.append({"n": name, "t": typ, "g": grp, "src": s or "auto", "opts": opt_list})
    return fields, sources


FIELDS, _ = load_page_meta()

SRC_LABEL = {"auto": "平台可导", "half": "部分可导", "manual": "需人工标"}
SRC_OWNER = {
    "商品名称": "三平台均有", "品牌": "三平台均有", "商品ID": "三平台均有",
    "品类": "三平台均有（需按我司口径归并）", "细分品类": "三平台均有",
    "价格": "三平台均有", "上市日期": "三平台均有",
    "数据来源": "导入时按所选源自动打标",
    "所属市场": "导入时按所选源自动带出",
    "榜单排名": "罗盘 / 蝉妈妈 / FastMoss / Olive Young",
    "销量": "罗盘 / 蝉妈妈 / FastMoss（Hwahae、Olive Young 不提供）",
    "销售额": "罗盘 / 蝉妈妈 / FastMoss（同上不提供）",
    "环比增速": "罗盘 / 蝉妈妈 / FastMoss（同上不提供）",
    "关联达人数": "罗盘 / 蝉妈妈 / FastMoss（同上不提供）",
    "退货率": "仅罗盘 / 蝉妈妈部分类目；FastMoss 不提供",
    "核心功效成分": "Hwahae 有成分库；其余靠商详页人工抄",
    "剂型": "商详页人工判断",
    "概念标签": "商详页 / 达人话术人工提炼",
    "质地描述": "商详页人工提炼",
    "功效宣称": "商详页可抄，归并需人工",
    "技术壁垒": "内部技术评审",
    "评分": "蝉妈妈 / Hwahae / Olive Young",
    "评价数": "蝉妈妈 / Hwahae / Olive Young",
    "差评关键词": "平台评论或 Hwahae 评价，需人工归纳",
    "备案路径": "NMPA 备案库查询 + 内部法规判断",
    "宣称支撑难度": "内部法规判断",
    "预估成本": "内部成本核算",
    "与我方价格带匹配": "对照自家价格带人工判断",
    "与我方客群匹配": "对照自家客群人工判断",
    "与我方 SKU 重合度": "对照兰本 / 兰至产品线人工判断",
    "决策状态": "内部评审",
    "选品笔记": "人工",
    "数据标记": "系统自动（示例 / 真实）",
}

wb = Workbook()

# ================= Sheet 1: 数据源接入台账 =================
ws1 = wb.active
ws1.title = "数据源接入台账"
ws1.append(["数据源", "类型", "覆盖市场", "能拿到", "拿不到", "取数路径", "额度 / 成本", "取数通道", "接入状态"])

SOURCES = [
    ("抖音罗盘", "中国国内平台",
     "中国",
     "销量、销售额、环比增速、关联达人数、品类、细分品类、价格、榜单排名、上市日期",
     "退货率（仅部分类目）、成分与功效、备案与成本",
     "compass.jinritemai.com → 商品 / 行业 → 榜单页导出",
     "免费（需店铺账号）；行业大盘需额外权限",
     "复用已登录浏览器（本机回环，勿走代理）",
     "列名映射已内置，可直接导入"),
    ("蝉妈妈", "中国国内平台",
     "中国",
     "销量、销售额、环比增速、关联达人数、评分、评价数、价格、榜单排名",
     "退货率（仅部分类目）、成分与功效、备案与成本",
     "chanmama.com → 商品榜 / 品类趋势分析",
     "品牌版品类趋势月报 55 次/月且月度更新，勿按天跑",
     "复用已登录浏览器",
     "列名映射已内置，可直接导入"),
    ("FastMoss", "海外 TikTok Shop 数据",
     "东南亚、欧美、日本",
     "销量、销售额、环比增速、关联达人数、店铺品牌、榜单排名、价格",
     "退货率（不提供）、成分与功效、备案与成本",
     "fastmoss.com → Product / Top Selling，region 选站点（US / GB / DE / FR / IT / ES / MX / BR / ID / VN / TH / MY / PH / SG / JP）",
     "订阅制（标准版 ¥199/月起）；日本站 2025-06 才开，历史浅",
     "SageSurf 跨境浏览器或已登录浏览器（CDP 直连）",
     "列为「其他」的数据待重标"),
    ("Hwahae 화해", "韩国成分与口碑",
     "韩国",
     "核心功效成分、评分、评价数、榜单排名、品类",
     "销量、销售额、环比增速、关联达人数、退货率、备案与成本",
     "hwahae.com → 排名页（无 API、无第三方工具）",
     "无额度限制，但无结构化接口，靠页面解析",
     "普通浏览器即可，需网页采集",
     "新识别，取数脚本待做"),
    ("Olive Young", "韩国渠道榜单",
     "韩国",
     "榜单排名、品类、评分、评价数",
     "销量、销售额、环比增速、关联达人数、退货率、成分与功效",
     "oliveyoung.co.kr 韩国站 → 实时销量榜 / Olive Young Awards",
     "无 API；只公开名次，金额不公开",
     "普通浏览器即可",
     "新识别，取数脚本待做"),
    ("KEV美妆圈", "中国美妆行业数据",
     "中国",
     "品类、细分品类、价格",
     "销量、销售额、环比增速、关联达人数、成分与功效",
     "KEV 中国区数据接口（待打通）",
     "可得性低，接口未通",
     "接口对接中",
     "未打通"),
    ("人工调研", "兜底",
     "中国、韩国、日本、欧美、东南亚",
     "与我方 SKU 重合度、与我方价格带匹配、与我方客群匹配、技术壁垒、备案路径、宣称支撑难度、预估成本、决策状态、选品笔记",
     "—",
     "内部评审 / NMPA 备案库查询 / 成本核算",
     "取决于投入，没有平台能替代",
     "人工填写或表格粘贴",
     "已在用（商品档案可手填）"),
]
fill_rows(ws1, SOURCES, colorize=lambda ws, r, row: setattr(
    ws.cell(row=r, column=9), "font",
    OK_FONT if "已" in str(row[8]) or "内置" in str(row[8]) else (WARN_FONT if ("待" in str(row[8]) or "未" in str(row[8])) else CELL_FONT)))
style_sheet(ws1, [14, 17, 20, 40, 34, 40, 32, 30, 22], 9)
for r in range(2, len(SOURCES) + 2):
    ws1.row_dimensions[r].height = 78

# ================= Sheet 2: 市场可走通性 =================
ws2 = wb.create_sheet("市场可走通性")
ws2.append(["市场", "可用数据源", "四件套是否齐全", "结论", "说明", "卡点 / 下一步"])
MK = [
    ("中国", "抖音罗盘、蝉妈妈、KEV美妆圈（未通）", "齐全",
     "可走通",
     "罗盘与蝉妈妈都能供销量、销售额、环比增速、关联达人数，链路完整。注意口径是「抖音电商」，与 TikTok Shop 系市场不可直接横向比较。",
     "KEV 接口未打通，暂缺行业侧品类趋势；罗盘行业大盘需额外权限。"),
    ("韩国", "Hwahae 화해、Olive Young", "缺失",
     "走不通",
     "FastMoss 不覆盖韩国（TikTok Shop 韩国站尚未开通）。目前只能拿到成分、评分、评价数与榜单名次，拿不到销量与销售额。",
     "「窗口期」「改良机会」「风险提醒」「空白赛道」四条规则在韩国数据上算不出来；需为韩国单独做 Hwahae / Olive Young 的网页采集脚本，或直接接受韩国只做成分情报。"),
    ("日本", "FastMoss（日本站）", "齐全但浅",
     "勉强能用",
     "FastMoss 有日本站，四件套齐全；但 2025-06 才开站，历史数据浅，环比基数不稳。",
     "环比建议改看 90 天或绝对销量，别只看环比增速；后续可补 Qoo10 / 乐天榜单做交叉验证。"),
    ("欧美", "FastMoss（US / GB / DE / FR / IT / ES / MX / BR）", "齐全",
     "可走通",
     "FastMoss 覆盖美英德法意西加墨巴，四件套完整，是当前质量最好的海外数据源。",
     "退货率 FastMoss 不提供，改良机会类结论需要另找评论源或人工估算。"),
    ("东南亚", "FastMoss（ID / VN / TH / MY / PH / SG）", "齐全",
     "可走通",
     "FastMoss 在东南亚覆盖最好、历史最长，四件套完整，直播带货数据尤其完整。",
     "六个站点口径不同，跨站点汇总前先确认统计周期一致。"),
]
fill_rows(ws2, MK, colorize=lambda ws, r, row: setattr(
    ws.cell(row=r, column=4), "font", OK_FONT if row[3] == "可走通" else (WARN_FONT if row[3] == "走不通" else CELL_FONT)))
style_sheet(ws2, [10, 34, 15, 12, 62, 48], 6)
for r in range(2, len(MK) + 2):
    ws2.row_dimensions[r].height = 84

# ================= Sheet 3: 洞察规则与前提 =================
ws3 = wb.create_sheet("洞察规则与前提")
ws3.append(["规则", "判定条件", "依赖字段", "其中平台可导", "其中需人工标", "能否自动算出", "说明"])
RULES = [
    ("窗口期", "环比增速 ≥ 60%（达人数与销售额不设门槛）",
     "环比增速", "环比增速", "无", "可自动",
     "只看增速。真实 TikTok 上升品的关联达人数中位约 110，旧阈值「≤15」是示例数据量纲，在真实数据上命中 0，因此取消达人数与销售额门槛。"
     "关联达人数改为展示用的「达人渗透度」：≤50 未铺开 / ≤150 起量 / >150 已铺开。中国、日本、欧美、东南亚可算；韩国因缺销量销售额仍参与不了。"),
    ("改良机会", "差评关键词非空即命中",
     "差评关键词", "无", "差评关键词（来自商品评价）", "需先补评价数据",
     "原口径「退货率 ≥ 10% 且 销量 ≥ 3 万」已废弃——三个平台的商品榜单都不提供退货率，抓不到的字段不能当规则前提。"
     "改为评价驱动：从抖音商品页 / 天猫评价 / 小红书 / TikTok 抓好评与差评关键词，差评关键词不是缺点清单，是改良清单。"),
    ("空白赛道", "与我方 SKU 重合度 = 全新 且 环比增速 ≥ 25%",
     "与我方 SKU 重合度、环比增速", "环比增速", "与我方 SKU 重合度", "不能",
     "「与我方 SKU 重合度」任何平台都导不出来，只能对照兰本 / 兰至产品线人工标。不标这个字段，这条规则永远命中 0 —— 这不是「没机会」，是「还没标」。"),
    ("可落地", "备案路径 = 普通化妆品备案 且 宣称支撑难度 = 无需评价 且 预估成本 ÷ 价格 ≤ 25%",
     "备案路径、宣称支撑难度、预估成本、价格", "价格", "备案路径、宣称支撑难度、预估成本", "不能",
     "四个字段里三个是内部判断，纯人工。好处是不依赖任何平台数据，所以连韩国数据也能参与这条规则的判定。"),
    ("风险提醒", "环比增速 < 0 或 差评关键词含高危词",
     "环比增速、差评关键词", "环比增速", "差评关键词", "基本可自动",
     "高危词表：过敏 / 刺激 / 烂脸 / 闷痘 / 红肿 / 刺痛 / 泛红 / 发痒 等。负增长本身已足以触发提醒，不依赖退货率。"),
]
fill_rows(ws3, RULES, colorize=lambda ws, r, row: setattr(
    ws.cell(row=r, column=6), "font", OK_FONT if str(row[5]).startswith("可自动") or str(row[5]).startswith("基本") else WARN_FONT))
style_sheet(ws3, [12, 46, 30, 24, 28, 12, 66], 7)
for r in range(2, len(RULES) + 2):
    ws3.row_dimensions[r].height = 92

# ================= Sheet 4: 字段可得性 =================
ws4 = wb.create_sheet("字段可得性")
ws4.append(["序号", "层级", "字段名", "类型", "可得性", "取值 / 来源", "可选值"])
rows = []
i = 0
last_g = None
for f in FIELDS:
    if f["g"] != last_g:
        rows.append(("###" + f["g"], "", "", "", "", "", ""))
        last_g = f["g"]
    i += 1
    rows.append((
        str(i), f["g"], f["n"], f["t"], SRC_LABEL.get(f["src"], f["src"]),
        SRC_OWNER.get(f["n"], ""), " / ".join(f["opts"]) if f["opts"] else ""
    ))
fill_rows(ws4, rows, group_col=1, colorize=lambda ws, r, row: setattr(
    ws.cell(row=r, column=5), "cell" and ws.cell(row=r, column=5)) if False else setattr(
    ws.cell(row=r, column=5), "font",
    OK_FONT if row[4] == "平台可导" else (CELL_FONT if row[4] == "部分可导" else WARN_FONT)))
style_sheet(ws4, [6, 13, 20, 10, 12, 46, 32], 7)
auto = sum(1 for f in FIELDS if f["src"] == "auto")
half = sum(1 for f in FIELDS if f["src"] == "half")
man = sum(1 for f in FIELDS if f["src"] == "manual")
r = len(rows) + 3
ws4.cell(row=r, column=1, value="统计").font = GRP_FONT
ws4.cell(row=r, column=2, value="平台可导 %d 个 / 部分可导 %d 个 / 需人工标 %d 个 / 合计 %d 个" % (auto, half, man, len(FIELDS))).font = CELL_FONT
ws4.cell(row=r + 1, column=1, value="结论").font = GRP_FONT
ws4.cell(row=r + 1, column=2,
         value="平台能自动填的字段不到一半。导入数据后，凡是依赖人工字段的洞察规则都不会自动出结果 —— "
               "引擎会在「机会洞察」页明确提示缺哪些字段，避免把「还没标」误读成「没机会」。").font = CELL_FONT

# ================= Sheet 5: 三平台取数映射 =================
ws5 = wb.create_sheet("三平台取数映射")
ws5.append(["工作台字段", "抖音罗盘列名", "蝉妈妈列名", "FastMoss 列名", "备注"])
MAPPING = [
    ("商品名称", "商品名称 / 商品标题", "商品名称 / 商品标题", "product_name / title", "导入按此字段去重"),
    ("品牌", "品牌 / 店铺名称", "品牌 / 店铺", "shopname / brand", ""),
    ("商品ID", "商品ID", "商品ID", "product_id", "可留空"),
    ("价格", "到手价 / 客单价", "到手价 / 均价", "price", "海外价折算见版本说明待定项 1"),
    ("销量", "销量 / 销售件数", "销量 / 近30天销量", "units_sold / total_units_sold", "「万 / k / 千」自动换算"),
    ("销售额", "成交额 / 成交金额", "销售额", "gmv / total_gmv", "外币需折算"),
    ("环比增速", "环比增速", "环比增速 / 增长率", "growth_rate", "取数周期见版本说明待定项 2"),
    ("关联达人数", "关联达人数 / 带货达人数", "关联达人数", "—（FastMoss 商品页给达人列表，需计数）", "FastMoss 需二次统计"),
    ("退货率", "退货率（部分类目）", "退货率 / 退款率", "—（三个平台商品榜都不提供）", "不参与任何规则，仅备查"),
    ("好评关键词", "—（评价后台）", "—（评价后台）", "—（评价文本，需从商品评价页归纳）", "口碑层，来自抖音 / 天猫 / 小红书 / TikTok 商品评价"),
    ("差评关键词", "—（评价后台）", "—（评价后台）", "—（评价文本，需从商品评价页归纳）", "改良机会规则的前提：填了就会自动进「改良机会」"),
    ("评价来源", "—", "—", "—", "抖音评价 / 天猫评价 / 小红书 / TikTok / 其他"),
    ("榜单排名", "榜单 / 排名", "排名 / 榜单", "rank", "带上平台与类目一起记"),
    ("所属市场", "—（国内固定中国）", "—（国内固定中国）", "region", "导入时由所选数据源带出"),
    ("上市日期", "上架时间 / 发布时间", "上架时间", "launch_date", "取首次上架"),
    ("品类", "一级类目", "一级类目", "category", "需按我司口径归并"),
    ("细分品类", "二级 / 三级类目", "二级 / 三级类目", "subcategory", ""),
    ("数据来源", "—（导入时自动打标）", "—（导入时自动打标）", "—（导入时自动打标）", "在导入第 1 步选源"),
]
fill_rows(ws5, MAPPING)
style_sheet(ws5, [16, 26, 26, 40, 34], 5)
for r in range(2, len(MAPPING) + 2):
    ws5.row_dimensions[r].height = 32

# ================= Sheet 6: 版本说明 =================
ws6 = wb.create_sheet("版本说明")
ws6.append(["项目", "内容"])
NOTES = [
    ("版本", "v1.3 —— 与已上线「全球选品平台」（线上 v6）的机会洞察规则完全对齐"),
    ("v1.3 改了什么", "窗口期取消达人数与销售额门槛（只看环比增速）；改良机会由退货率驱动改为差评关键词驱动；风险提醒改为「环比 < 0 或差评含高危词」；口碑层新增「好评关键词」「评价来源」两个字段"),
    ("v1.3 为什么改", "旧阈值「关联达人数 ≤ 15」来自示例数据量纲，真实数据中位 110 → 规则命中 0，等于空转；退货率三个平台榜单都不提供 → 不能拿抓不到的字段当前提"),
    ("v1.2 改了什么", "新增：数据源接入台账 / 市场可走通性 / 洞察规则与前提 / 字段可得性 四张表；字段清单改为从线上页面自动抽取，不再手工维护"),
    ("为什么改", "原 v1.1 只回答「字段怎么填」，没回答「数据从哪来、能不能走通」。结果页面能导入数据，但用户无法判断某个市场的结论到底有没有数据支撑"),
    ("核心结论 1", "没有单一数据源能覆盖全部五个市场：罗盘 / 蝉妈妈只覆盖中国，FastMoss 覆盖东南亚 / 欧美 / 日本，韩国两家都不覆盖"),
    ("核心结论 2", "韩国是唯一走不通的市场：TikTok Shop 韩国站未开通，FastMoss 无数据；Hwahae / Olive Young 只给成分口碑与名次，给不了销量销售额"),
    ("核心结论 3", "35 个字段里平台能自动供的只有 %d 个，另有 %d 个部分可导、%d 个任何源都给不了。5 条洞察规则里有 2 条完全依赖人工字段，导入数据不会自动出结果" % (auto, half, man),
     ),
    ("核心结论 5", "「数据来源」字段此前靠表格里恰好有来源列才会被填，实际几乎全空；现改为导入第 1 步先选源，由源决定市场口径与可得字段，并自动给每条记录打标"),
    ("字段数", "35 个（v1.2 的 33 个 + 口碑层新增「好评关键词」「评价来源」）"),
    ("数据来源可选值", "抖音罗盘 / 蝉妈妈 / FastMoss / Hwahae / Olive Young / KEV美妆圈 / 人工调研 / 其他"),
    ("待定项 1（待拍板）", "海外价折算汇率与含税口径：建议统一按月初中间价折算、取含税到手价"),
    ("待定项 2（待拍板）", "环比统计周期取 30 天还是 90 天、大促月是否剔除假峰值：建议默认 30 天并人工剔除大促；日本站因历史浅建议看 90 天"),
    ("待定项 5（待补数据）", "评价数据来源：抖音商品页 / 天猫评价后台 / 小红书 / TikTok 均需登录后才可采集，目前四个渠道在采集浏览器上都是未登录状态"),
    ("待定项 3（待拍板）", "「与我方 SKU 重合度」基准产品线：兰本 / 兰至 / 两条线合并判断"),
    ("待定项 4（待拍板）", "韩国是否值得单独做 Hwahae / Olive Young 的网页采集脚本，还是接受韩国只做成分口碑情报"),
    ("环境提示", "本表为静态口径文档，不含任何 Excel 公式，可在任意设备打开"),
]
fill_rows(ws6, NOTES)
style_sheet(ws6, [22, 108], 2)
for r in range(2, len(NOTES) + 2):
    ws6.row_dimensions[r].height = 32

wb.save(OUT)
print("SAVED", OUT, os.path.getsize(OUT))
print("字段统计：auto %d / half %d / manual %d / 合计 %d" % (auto, half, man, len(FIELDS)))

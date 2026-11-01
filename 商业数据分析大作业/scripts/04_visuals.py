"""04_visuals.py —— 全部图表（模板复现 16 张 + 业务模型图 7 张，共 23 张）

全部由 Python（Matplotlib / Seaborn）生成，分辨率 150dpi，中文正常显示，
命名规范 figNN_中文标题.png，索引写入 outputs/tables/t04_figure_index.csv。

运行：python scripts/04_visuals.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".pylibs"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from common import (CLEAN, COLORS, PALETTE, TABLES, ensure_dirs, log,  # noqa: E402
                    save_fig, setup_chinese_font, style_axes)

SRC = "数据来源：Tableau Sample - Superstore（Kaggle 公开数据集，2014-01 至 2017-12），Python 绘制"
INDEX: list[dict] = []
THOUSANDS = FuncFormatter(lambda x, pos: f"{x/1000:,.0f}k" if abs(x) >= 1000 else f"{x:,.0f}")


def reg(kind: str, model: str, desc: str) -> None:
    INDEX.append({"序号": len(INDEX) + 1, "文件名": "", "类别": kind, "对应模型/模板": model, "说明": desc})


def note(fig, text: str = SRC) -> None:
    fig.text(0.01, 0.005, text, fontsize=7.5, color="#7A7A7A", ha="left")


def load():
    df = pd.read_csv(os.path.join(CLEAN, "superstore_clean.csv"), encoding="utf-8",
                     parse_dates=["Order Date", "Ship Date", "YearMonthDate"])
    facts = json.load(open(os.path.join(TABLES, "t03_facts.json"), encoding="utf-8"))
    return df, facts


# ============================================================
# 一、模板复现类（16 张）
# ============================================================
def fig01_kpi(df, f):
    k = f["kpi"]
    cards = [
        ("销售额 GMV", f"${k['gmv']/1e6:,.2f}M", f"同比 +{f['yoy_2017']:.1f}%"),
        ("利润总额", f"${k['profit']/1e3:,.0f}K", f"利润率 {k['margin']:.1f}%"),
        ("订单量", f"{k['orders']:,}", f"客单价 ${k['aov']:,.0f}"),
        ("客户数", f"{k['customers']:,}", f"复购率 {f['funnel'][1]['占全部客户%']:.0f}%"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.4))
    for ax, (title, value, sub) in zip(axes, cards):
        ax.axis("off")
        ax.add_patch(FancyBboxPatch((0.04, 0.08), 0.92, 0.84, boxstyle="round,pad=0.02,rounding_size=0.05",
                                    facecolor="#F4F7FB", edgecolor="#C9D6E4", linewidth=1.2))
        ax.text(0.5, 0.70, title, ha="center", va="center", fontsize=12, color="#5A6B7D")
        ax.text(0.5, 0.44, value, ha="center", va="center", fontsize=24, fontweight="bold", color=COLORS["primary"])
        ax.text(0.5, 0.20, sub, ha="center", va="center", fontsize=10, color=COLORS["secondary"])
    fig.suptitle("核心经营指标看板（2014-2017）", fontsize=14, fontweight="bold", y=1.02)
    note(fig)
    reg("模板复现", "KPI 指标卡", "四张核心指标卡片＋同比/客单价等辅助信息")
    return save_fig(fig, "fig01_KPI指标卡.png")


def fig02_subcat_bar(df, f):
    sub = df.groupby("Sub-Category")["Sales"].sum().sort_values()
    fig, ax = plt.subplots(figsize=(10, 7.2))
    bars = ax.barh(sub.index, sub.values, color=COLORS["primary"], height=0.68)
    for b in bars[-3:]:
        b.set_color(COLORS["secondary"])
    for i, v in enumerate(sub.values):
        ax.text(v + 4000, i, f"${v/1000:,.0f}K", va="center", fontsize=9, color="#333333")
    ax.set_xlabel("销售额（美元）")
    ax.set_title("子品类销售额排名（条形图）", fontsize=14, fontweight="bold")
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.set_xlim(0, sub.max() * 1.15)
    style_axes(ax, "x")
    note(fig)
    reg("模板复现", "排序条形图", "17 个子品类销售额降序排列，Top3 高亮并标注数值")
    return save_fig(fig, "fig02_子品类销售额条形图.png")


def fig03_region_segment(df, f):
    p = df.pivot_table(index="Region", columns="Segment", values="Sales", aggfunc="sum")
    p = p.loc[p.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(p))
    w = 0.26
    for i, seg in enumerate(p.columns):
        v = p[seg].values
        ax.bar(x + (i - 1) * w, v, w, label=seg, color=PALETTE[i])
        for xi, vi in zip(x + (i - 1) * w, v):
            ax.text(xi, vi + 3000, f"{vi/1000:.0f}k", ha="center", fontsize=8, color="#333333")
    ax.set_xticks(x, p.index)
    ax.set_ylabel("销售额（美元）")
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_title("各区域 × 客户细分的销售额（分组柱形图）", fontsize=14, fontweight="bold")
    ax.legend(title="客户细分", frameon=False, ncol=3, loc="upper right")
    style_axes(ax)
    note(fig)
    reg("模板复现", "分组柱形图", "区域与客户细分双维度对比，组内标注数值")
    return save_fig(fig, "fig03_区域客户细分分组柱形图.png")


def fig04_year_category(df, f):
    p = df.pivot_table(index="Order Year", columns="Category", values="Sales", aggfunc="sum")
    fig, ax = plt.subplots(figsize=(10, 6))
    bottom = np.zeros(len(p))
    for i, c in enumerate(p.columns):
        ax.bar(p.index.astype(str), p[c].values, bottom=bottom, label=c, color=PALETTE[i], width=0.55)
        bottom += p[c].values
    for xi, tot in enumerate(bottom):
        ax.text(xi, tot + 8000, f"${tot/1000:,.0f}K", ha="center", fontsize=9, fontweight="bold")
    ax.set_ylabel("销售额（美元）")
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_title("2014-2017 年销售额构成（堆积柱形图）", fontsize=14, fontweight="bold")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.set_ylim(0, bottom.max() * 1.16)
    style_axes(ax)
    note(fig)
    reg("模板复现", "堆积柱形图", "年度总额与品类结构变化，柱顶标注合计")
    return save_fig(fig, "fig04_年度品类堆积柱形图.png")


def fig05_monthly_line(df, f):
    m = pd.read_csv(os.path.join(TABLES, "t03_monthly_series.csv"), parse_dates=["month"])
    m["ma3"] = m["sales"].rolling(3).mean()
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.plot(m["month"], m["sales"], color=COLORS["primary"], lw=1.8, marker="o", ms=3, label="月度销售额")
    ax.plot(m["month"], m["ma3"], color=COLORS["secondary"], lw=2.2, ls="--", label="3 期移动平均")
    ax.fill_between(m["month"], m["sales"], color=COLORS["primary"], alpha=0.08)
    ax.set_ylabel("销售额（美元）")
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_title("月度销售额趋势与移动平均（折线图）", fontsize=14, fontweight="bold")
    ax.legend(frameon=False, loc="upper left")
    style_axes(ax)
    fig.autofmt_xdate(rotation=30)
    note(fig)
    reg("模板复现", "折线图 + 移动平均", "48 个月销售额走势，叠加 3 期移动平均平滑线")
    return save_fig(fig, "fig05_月度销售额趋势折线图.png")


def fig06_cum_area(df, f):
    m = pd.read_csv(os.path.join(TABLES, "t03_monthly_series.csv"), parse_dates=["month"])
    m["cum"] = m["sales"].cumsum()
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.fill_between(m["month"], m["cum"], color=COLORS["primary"], alpha=0.35)
    ax.plot(m["month"], m["cum"], color=COLORS["primary"], lw=2)
    ax.set_ylabel("累计销售额（美元）")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"${x/1e6:.1f}M"))
    ax.set_title("累计销售额面积图（2014-2017）", fontsize=14, fontweight="bold")
    ax.annotate(f"期末累计 ${m['cum'].iloc[-1]/1e6:.2f}M", xy=(m["month"].iloc[-1], m["cum"].iloc[-1]),
                xytext=(-120, -40), textcoords="offset points", fontsize=10,
                arrowprops=dict(arrowstyle="->", color=COLORS["secondary"]), color=COLORS["secondary"])
    style_axes(ax)
    fig.autofmt_xdate(rotation=30)
    note(fig)
    reg("模板复现", "面积图", "累计销售额随时间累积的走势")
    return save_fig(fig, "fig06_累计销售额面积图.png")


def fig07_segment_pie(df, f):
    s = df.groupby("Segment")["Sales"].sum()
    fig, ax = plt.subplots(figsize=(8, 6.4))
    wedges, texts, autotexts = ax.pie(s.values, labels=s.index, autopct="%1.1f%%", startangle=90,
                                      colors=PALETTE[:3], wedgeprops=dict(width=0.62, edgecolor="white"),
                                      pctdistance=0.78, textprops=dict(fontsize=11))
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
    ax.text(0, 0.08, f"${s.sum()/1e6:.2f}M", ha="center", va="center", fontsize=17, fontweight="bold",
            color=COLORS["primary"])
    ax.text(0, -0.14, "客户细分销售额", ha="center", va="center", fontsize=10, color="#666666")
    ax.set_title("客户细分销售额占比（环形饼图）", fontsize=14, fontweight="bold")
    note(fig)
    reg("模板复现", "饼图/环形图", "三类客户细分销售额占比，中心显示总额")
    return save_fig(fig, "fig07_客户细分环形饼图.png")


def fig08_shipmode(df, f):
    s = df.groupby("Ship Mode")["Order ID"].nunique().sort_values(ascending=False)
    days = df.groupby("Ship Mode")["Ship Days"].mean().reindex(s.index)
    fig, ax = plt.subplots(figsize=(9, 5.6))
    wedges, texts, autotexts = ax.pie(s.values, labels=None, autopct="%1.1f%%", startangle=140,
                                      colors=PALETTE[:4], wedgeprops=dict(width=0.45, edgecolor="white"),
                                      pctdistance=0.8, textprops=dict(fontsize=10, color="white"))
    ax.legend(wedges, [f"{n}（平均{d:.1f}天）" for n, d in zip(s.index, days)],
              loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, title="配送方式")
    ax.text(0, 0, f"订单\n{s.sum():,}", ha="center", va="center", fontsize=13, fontweight="bold",
            color=COLORS["primary"])
    ax.set_title("配送方式订单占比与平均履约时长（环形图）", fontsize=13, fontweight="bold")
    note(fig)
    reg("模板复现", "环形图 + 图例指标", "配送方式占比，图例附带平均履约天数")
    return save_fig(fig, "fig08_配送方式环形图.png")


def fig09_discount_scatter(df, f):
    samp = df.sample(2500, random_state=42)
    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(samp["Discount"] * 100, samp["Profit Margin"] * 100, s=18,
                    c=samp["Profit"], cmap="RdYlGn", vmin=-300, vmax=300, alpha=0.75, edgecolors="none")
    z = np.polyfit(df["Discount"] * 100, df["Profit Margin"] * 100, 1)
    xs = np.linspace(0, 80, 50)
    ax.plot(xs, np.polyval(z, xs), color=COLORS["fourth"], lw=2.2,
            label=f"拟合线：斜率 {z[0]:.2f}（相关系数 {f['discount_profit_corr']:.2f}）")
    ax.axhline(0, color="#888888", lw=1, ls=":")
    ax.set_xlabel("折扣率（%）")
    ax.set_ylabel("利润率（%）")
    ax.set_ylim(-150, 100)
    ax.set_title("折扣率与利润率的关系（散点图）", fontsize=14, fontweight="bold")
    ax.legend(frameon=False, loc="lower left")
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("单笔利润（美元）")
    style_axes(ax, "both")
    note(fig)
    reg("模板复现", "散点图 + 趋势线", "折扣率与利润率负相关，颜色编码单笔利润")
    return save_fig(fig, "fig09_折扣利润率散点图.png")


def fig10_bubble(df, f):
    g = (df.groupby("Sub-Category")
           .agg(sales=("Sales", "sum"), margin=("Profit Margin", "mean"), qty=("Quantity", "sum"),
                profit=("Profit", "sum"))
           .reset_index())
    g["margin"] *= 100
    fig, ax = plt.subplots(figsize=(11, 6.6))
    colors = [COLORS["third"] if m > 0 else COLORS["fourth"] for m in g["margin"]]
    ax.scatter(g["sales"], g["margin"], s=g["qty"] / 22, c=colors, alpha=0.65, edgecolors="white", linewidths=1.2)
    for _, r in g.iterrows():
        ax.annotate(r["Sub-Category"], (r["sales"], r["margin"]), fontsize=8.5,
                    ha="center", va="center", color="#333333", fontweight="bold")
    ax.axhline(0, color="#999999", lw=1, ls="--")
    ax.set_xlabel("销售额（美元）")
    ax.set_ylabel("平均利润率（%）")
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.set_title("子品类销售额 × 利润率气泡图（气泡=销量）", fontsize=14, fontweight="bold")
    ax.legend(handles=[Patch(color=COLORS["third"], label="盈利品类"), Patch(color=COLORS["fourth"], label="亏损品类")],
              frameon=False, loc="lower right")
    style_axes(ax, "both")
    note(fig)
    reg("模板复现", "气泡图", "三维信息：销售额、利润率、销量，颜色区分盈亏")
    return save_fig(fig, "fig10_子品类气泡图.png")


def fig11_radar(df, f):
    g = (df.groupby("Region")
           .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), orders=("Order ID", "nunique"),
                customers=("Customer ID", "nunique"), aov=("Sales", lambda s: s.sum() / len(s)))
           .reset_index())
    g["aov"] = g["sales"] / g["orders"]
    dims = ["销售额", "利润", "订单量", "客户数", "客单价"]
    mat = g[["sales", "profit", "orders", "customers", "aov"]].values
    norm = mat / mat.max(axis=0)
    ang = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    ang += ang[:1]
    fig, ax = plt.subplots(figsize=(7.6, 7), subplot_kw=dict(polar=True))
    for i, r in enumerate(g["Region"]):
        v = norm[i].tolist() + [norm[i][0]]
        ax.plot(ang, v, lw=2, label=r, color=PALETTE[i])
        ax.fill(ang, v, color=PALETTE[i], alpha=0.12)
    ax.set_xticks(ang[:-1], dims, fontsize=11)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0], ["25%", "50%", "75%", "100%"], fontsize=8, color="#888888")
    ax.set_title("四大区域经营能力雷达图（各维度按最大值归一）", fontsize=13, fontweight="bold", pad=24)
    ax.legend(loc="upper right", bbox_to_anchor=(1.18, 1.12), frameon=False)
    note(fig)
    reg("模板复现", "雷达图", "五维能力对比，按维度最大值归一化")
    return save_fig(fig, "fig11_区域能力雷达图.png")


def fig12_waterfall(df, f):
    a = df[df["Order Year"] == 2016].groupby("Category")["Profit"].sum()
    b = df[df["Order Year"] == 2017].groupby("Category")["Profit"].sum()
    diff = (b - a).sort_values(ascending=False)
    labels = ["2016 利润"] + list(diff.index) + ["2017 利润"]
    vals = [a.sum()] + list(diff.values) + [b.sum()]
    fig, ax = plt.subplots(figsize=(11, 6))
    cum = 0
    for i, (lab, v) in enumerate(zip(labels, vals)):
        if i == 0 or i == len(labels) - 1:
            ax.bar(i, v, color=COLORS["primary"], width=0.6)
            ax.text(i, v + 1500, f"${v/1000:,.0f}K", ha="center", fontsize=9, fontweight="bold")
            cum = v
        else:
            ax.plot([i - 0.5, i + 0.5], [cum, cum], color="#9AA6B2", lw=0.9, ls="--", zorder=1)
            bottom = cum if v >= 0 else cum + v
            ax.bar(i, abs(v), bottom=bottom, color=COLORS["third"] if v >= 0 else COLORS["fourth"],
                   width=0.55, zorder=3)
            ax.text(i, max(cum, cum + v) + 1400, f"{v:+,.0f}", ha="center", fontsize=9,
                    color=COLORS["third"] if v >= 0 else COLORS["fourth"], zorder=4)
            cum += v
    ax.set_xticks(range(len(labels)), labels, fontsize=10)
    ax.set_ylabel("利润（美元）")
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_title("2016→2017 利润变动瀑布图（按品类拆解）", fontsize=14, fontweight="bold")
    style_axes(ax)
    note(fig)
    reg("模板复现", "瀑布图", "利润同比变动的品类归因拆解")
    return save_fig(fig, "fig12_利润变动瀑布图.png")


def _squarify(values, x, y, w, h):
    """简化版 slice-and-dice 矩形树图布局。"""
    rects = []
    total = sum(values)
    cur_x, cur_y, cur_w, cur_h = x, y, w, h
    vertical = w >= h
    for v in values:
        frac = v / total
        if vertical:
            rw = cur_w * frac
            rects.append((cur_x, cur_y, rw, cur_h))
            cur_x += rw
            cur_w -= rw
        else:
            rh = cur_h * frac
            rects.append((cur_x, cur_y, cur_w, rh))
            cur_y += rh
            cur_h -= rh
        total -= v
        if total <= 0:
            break
    return rects


def fig13_treemap(df, f):
    cat = df.groupby("Category")["Sales"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(11, 6.4))
    outer = _squarify(cat.values, 0, 0, 1, 1)
    header = 0.06
    for (cx, cy, cw, ch), cname in zip(outer, cat.index):
        base = PALETTE[list(cat.index).index(cname)]
        ax.add_patch(Rectangle((cx, cy), cw, ch, facecolor=base, alpha=0.30, edgecolor="white", linewidth=2))
        ax.text(cx + cw / 2, cy + ch - header / 2, f"{cname}　${cat[cname]/1000:,.0f}K",
                ha="center", va="center", fontsize=12, color=COLORS["dark"], fontweight="bold")
        sub = df[df["Category"] == cname].groupby("Sub-Category")["Sales"].sum().sort_values(ascending=False)
        inner = _squarify(sub.values, cx, cy, cw, ch - header)
        for j, ((sx, sy, sw, sh), sname) in enumerate(zip(inner, sub.index)):
            ax.add_patch(Rectangle((sx, sy), sw, sh, facecolor=base, alpha=max(0.55, 0.95 - j * 0.07),
                                   edgecolor="white", linewidth=1.4))
            if sw > 0.035 and sh > 0.06:
                ax.text(sx + sw / 2, sy + sh / 2, f"{sname}\n${sub[sname]/1000:,.0f}K",
                        ha="center", va="center", fontsize=8.2, color="white", fontweight="bold")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("品类-子品类销售额矩形树图", fontsize=14, fontweight="bold")
    note(fig)
    reg("模板复现", "矩形树图", "两层结构：品类为大区块，子品类为内部小块")
    return save_fig(fig, "fig13_品类矩形树图.png")


def fig14_heatmap(df, f):
    p = df.pivot_table(index="Order Year", columns="Order Month", values="Sales", aggfunc="sum").fillna(0)
    fig, ax = plt.subplots(figsize=(12, 4.6))
    im = ax.imshow(p.values / 1000, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(12), [f"{m}月" for m in p.columns])
    ax.set_yticks(range(len(p.index)), p.index)
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = p.values[i, j] / 1000
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8.5,
                    color="white" if v > p.values.max() / 1000 * 0.55 else "#333333")
    ax.set_title("年 × 月销售额热力图（单位：千美元）", fontsize=14, fontweight="bold")
    cb = fig.colorbar(im, ax=ax, pad=0.01)
    cb.set_label("销售额（千美元）")
    note(fig)
    reg("模板复现", "热力图", "4 年 × 12 月销售额矩阵，颜色深浅显示季节强度")
    return save_fig(fig, "fig14_年月销售额热力图.png")


def fig15_boxplot(df, f):
    order = ["无折扣", "低折扣(0,20%]", "中折扣(20%,40%]", "高折扣(40%,60%]", "超高折扣>60%"]
    data = [df.loc[df["Discount Band"] == o, "Profit Margin"].dropna() * 100 for o in order]
    fig, ax = plt.subplots(figsize=(11, 6))
    bp = ax.boxplot(data, tick_labels=order, patch_artist=True, showfliers=False, widths=0.55,
                    medianprops=dict(color="white", lw=1.6))
    for patch, c in zip(bp["boxes"], [COLORS["third"], "#7FB069", "#E8C547", COLORS["secondary"], COLORS["fourth"]]):
        patch.set_facecolor(c)
        patch.set_alpha(0.85)
    ax.axhline(0, color="#999999", lw=1, ls="--")
    ax.set_ylabel("利润率（%）")
    ax.set_ylim(-120, 90)
    ax.set_title("不同折扣区间的利润率分布（箱线图）", fontsize=14, fontweight="bold")
    ax.tick_params(axis="x", rotation=12)
    style_axes(ax)
    note(fig)
    reg("模板复现", "箱线图", "折扣区间与利润率分布，揭示高折扣致亏")
    return save_fig(fig, "fig15_折扣区间利润率箱线图.png")


def fig16_combo(df, f):
    m = pd.read_csv(os.path.join(TABLES, "t03_monthly_series.csv"), parse_dates=["month"]).tail(24)
    p = df[df["YearMonthDate"] >= m["month"].min()].groupby("YearMonthDate").agg(
        profit=("Profit", "sum")).reset_index()
    fig, ax1 = plt.subplots(figsize=(12, 5.6))
    ax1.bar(m["month"], m["sales"], width=20, color=COLORS["light"], label="销售额（左轴）")
    ax1.plot(m["month"], m["sales"], color=COLORS["primary"], lw=2, marker="o", ms=3.5, label="销售额折线")
    ax1.set_ylabel("销售额（美元）")
    ax1.yaxis.set_major_formatter(THOUSANDS)
    ax2 = ax1.twinx()
    ax2.plot(p["YearMonthDate"], p["profit"], color=COLORS["secondary"], lw=2, ls="--", marker="s", ms=3,
             label="利润（右轴）")
    ax2.set_ylabel("利润（美元）")
    ax2.yaxis.set_major_formatter(THOUSANDS)
    ax1.set_title("近 24 个月销售额与利润组合图（柱＋线双轴）", fontsize=14, fontweight="bold")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", ncol=3, fontsize=9)
    for s in ("top",):
        ax1.spines[s].set_visible(False)
        ax2.spines[s].set_visible(False)
    ax1.grid(True, axis="y", color="#E5E9EE", lw=0.8)
    ax1.set_axisbelow(True)
    fig.autofmt_xdate(rotation=30)
    note(fig)
    reg("模板复现", "组合图（柱+线双轴）", "销售额柱形与利润折线共用时间轴，双坐标系")
    return save_fig(fig, "fig16_销售利润组合图.png")


# ============================================================
# 二、业务模型图（7 张）
# ============================================================
def fig17_rfm(df, f):
    rfm = pd.read_csv(os.path.join(TABLES, "t03_rfm.csv"), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(11, 6.6))
    segs = rfm["Segment"].unique()
    cmap = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(
        ["重要价值客户", "重要唤回客户", "重要发展客户", "重要挽留客户",
         "一般价值客户", "一般保持客户", "一般发展客户", "一般挽留客户"])}
    for s in segs:
        d = rfm[rfm["Segment"] == s]
        ax.scatter(d["R"], d["F"], s=np.sqrt(d["M"]) * 1.5, color=cmap[s], alpha=0.65,
                   edgecolors="white", linewidths=0.6, label=s)
    ax.axvline(f["rfm"]["r_median"], color="#888888", ls="--", lw=1)
    ax.axhline(f["rfm"]["f_median"], color="#888888", ls="--", lw=1)
    ax.text(f["rfm"]["r_median"] + 8, rfm["F"].max() * 0.97, "R 中位数", fontsize=8, color="#666666")
    ax.text(rfm["R"].max() * 0.99, f["rfm"]["f_median"] + 0.3, "F 中位数", fontsize=8,
            color="#666666", ha="right")
    ax.invert_xaxis()   # R 越小越近，横轴反向更符合直觉
    ax.set_xlabel("R：最近一次购买距今天数（越靠右越久未购）")
    ax.set_ylabel("F：购买频次（订单数）")
    ax.set_title("RFM 八分类客户分布气泡图（气泡=累计消费额）", fontsize=14, fontweight="bold")
    ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=8.5)
    style_axes(ax, "both")
    note(fig, SRC + "；以三指标中位数切分（R≤76 天、F≥6 单、M≥$2,256）")
    reg("业务模型图", "RFM 八分类", "R-F 平面分布，气泡面积映射 M 值，虚线为中位数切分线")
    return save_fig(fig, "fig17_RFM客户分布气泡图.png")


def fig18_pareto(df, f):
    abc = pd.read_csv(os.path.join(TABLES, "t03_abc_customer.csv"), encoding="utf-8")
    top = abc.head(120)
    fig, ax1 = plt.subplots(figsize=(11, 6))
    ax1.bar(range(len(top)), top["sales"], color=COLORS["primary"], width=0.85, label="客户销售额")
    ax1.set_xlabel("客户（按销售额降序，前 120 位）")
    ax1.set_ylabel("销售额（美元）")
    ax1.yaxis.set_major_formatter(THOUSANDS)
    ax2 = ax1.twinx()
    ax2.plot(range(len(top)), top["cum_share"], color=COLORS["secondary"], lw=2.2, label="累计占比")
    ax2.axhline(70, color=COLORS["third"], ls="--", lw=1)
    ax2.axhline(90, color=COLORS["fourth"], ls="--", lw=1)
    ax2.text(2, 71.5, "70% 分界（A 类）", fontsize=8.5, color=COLORS["third"])
    ax2.text(2, 91.5, "90% 分界（B 类）", fontsize=8.5, color=COLORS["fourth"])
    ax2.set_ylabel("累计销售额占比（%）")
    ax2.set_ylim(0, 105)
    ax1.set_title("客户销售额帕累托图与 ABC 分类", fontsize=14, fontweight="bold")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="center right")
    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    note(fig)
    reg("业务模型图", "帕累托 / ABC 分类", "客户贡献累计曲线与 70%/90% 分类阈值")
    return save_fig(fig, "fig18_客户帕累托图.png")


def fig19_boston(df, f):
    g = pd.read_csv(os.path.join(TABLES, "t03_boston.csv"), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(11, 7))
    qcolor = {"明星": COLORS["third"], "金牛": COLORS["primary"], "问题": COLORS["secondary"], "瘦狗": COLORS["gray"]}
    for q, d in g.groupby("quadrant"):
        ax.scatter(d["share"], d["growth"], s=d["total"] / 60, color=qcolor[q], alpha=0.6,
                   edgecolors="white", linewidths=1.2, label=q)
    for _, r in g.iterrows():
        ax.annotate(r["Sub-Category"], (r["share"], r["growth"]), fontsize=8.5, ha="center",
                    va="center", fontweight="bold", color="#333333")
    ax.axvline(g["share"].median(), color="#888888", ls="--", lw=1)
    ax.axhline(g["growth"].median(), color="#888888", ls="--", lw=1)
    ax.set_xlabel("相对市场份额（子品类销售额占比 %）")
    ax.set_ylabel("销售增长率（2017 vs 2016，%）")
    ax.set_title("子品类波士顿矩阵（份额 × 增速，气泡=销售额）", fontsize=14, fontweight="bold")
    ax.set_xlim(-0.8, g["share"].max() * 1.12)
    ax.set_ylim(g["growth"].min() - 8, g["growth"].max() + 8)
    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=qcolor[q],
                      markersize=9, label=q) for q in ["明星", "金牛", "问题", "瘦狗"]]
    ax.legend(handles=handles, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4,
              fontsize=9, title="象限（按份额与增速中位数划分）", title_fontsize=9)
    style_axes(ax, "both")
    note(fig)
    reg("业务模型图", "波士顿矩阵", "四象限：明星/金牛/问题/瘦狗，气泡大小表示销售额")
    return save_fig(fig, "fig19_子品类波士顿矩阵.png")


def fig20_cohort(df, f):
    mat = np.array([[np.nan if v is None else v for v in row] for row in f["cohort"]["matrix"]], dtype=float)
    idx = f["cohort"]["index"]
    fig, ax = plt.subplots(figsize=(11, 7))
    masked = np.ma.masked_invalid(mat)
    cmap = plt.get_cmap("YlGnBu").copy()
    cmap.set_bad("#F5F7FA")
    im = ax.imshow(masked, cmap=cmap, aspect="auto", vmin=0, vmax=np.nanmax(mat))
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if not np.isnan(mat[i, j]):
                ax.text(j, i, f"{mat[i, j]:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if mat[i, j] > np.nanmax(mat) * 0.6 else "#333333")
    ax.set_xticks(range(mat.shape[1]), [f"T+{j}" for j in range(mat.shape[1])])
    ax.set_yticks(range(len(idx)), [f"{c}（{s}人）" for c, s in zip(idx, f["cohort"]["sizes"])], fontsize=8.5)
    ax.set_xlabel("距首购的季度数")
    ax.set_ylabel("同期群（首购季度）")
    ax.set_title("季度同期群留存热力图（单位：%）", fontsize=14, fontweight="bold")
    cb = fig.colorbar(im, ax=ax, pad=0.01)
    cb.set_label("留存率（%）")
    note(fig)
    reg("业务模型图", "同期群留存", "16 个季度同期群、9 个观察期的留存率矩阵")
    return save_fig(fig, "fig20_同期群留存热力图.png")


def fig21_forecast(df, f):
    s = pd.read_csv(os.path.join(TABLES, "t03_monthly_series.csv"), parse_dates=["month"])
    fc = pd.read_csv(os.path.join(TABLES, "t03_forecast.csv"), parse_dates=["month"])
    test_idx = pd.to_datetime(f["sarima"]["test_index"])
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(s["month"], s["sales"], color=COLORS["primary"], lw=1.8, label="实际销售额")
    ax.plot(test_idx, f["sarima"]["test_pred"], color=COLORS["fourth"], lw=1.6, ls="--", marker="o", ms=4,
            label="回测预测（2017H2）")
    ax.fill_between(fc["month"], fc["lower"], fc["upper"], color=COLORS["secondary"], alpha=0.22,
                    label="95% 置信区间")
    ax.plot(fc["month"], fc["forecast"], color=COLORS["secondary"], lw=2.2, marker="o", ms=5,
            label="未来 6 个月点预测")
    ax.axvline(s["month"].iloc[-1], color="#888888", ls=":", lw=1)
    ax.text(s["month"].iloc[-1], ax.get_ylim()[1] * 0.92, " 预测起点", fontsize=9, color="#666666")
    ax.set_ylabel("销售额（美元）")
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_title(f"SARIMA{ f['sarima']['order'] }×{ f['sarima']['seasonal_order'] } 销售额预测"
                 f"（回测 MAPE={f['sarima']['mape']:.1f}%，RMSE=${f['sarima']['rmse']:,.0f}）",
                 fontsize=13, fontweight="bold")
    ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9)
    style_axes(ax)
    fig.autofmt_xdate(rotation=30)
    note(fig)
    reg("业务模型图", "SARIMA 预测", "点预测 + 95% 置信区间 + 6 期回测对比")
    return save_fig(fig, "fig21_SARIMA销售额预测.png")


def fig22_rules(df, f):
    r = pd.read_csv(os.path.join(TABLES, "t03_rules.csv"), encoding="utf-8").head(10).iloc[::-1]
    labels = [f"{a} → {c}" for a, c in zip(r["antecedent"], r["consequent"])]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    bars = ax.barh(labels, r["lift"], color=COLORS["third"], height=0.6)
    for b, v, conf in zip(bars, r["lift"], r["confidence"]):
        ax.text(v + 0.006, b.get_y() + b.get_height() / 2, f"{v:.3f}（置信度 {conf:.0%}）",
                va="center", fontsize=8.5)
    ax.axvline(1, color="#888888", ls="--", lw=1)
    ax.set_xlim(0, r["lift"].max() * 1.35)
    ax.set_xlabel("提升度 Lift（>1 表示正相关）")
    ax.set_title("关联规则 Top10（子品类购物篮，Apriori）", fontsize=14, fontweight="bold")
    style_axes(ax, "x")
    note(fig, SRC + "；最小支持度 0.8%，仅保留单后项规则")
    reg("业务模型图", "关联规则 Apriori", "Top10 规则的提升度与置信度")
    return save_fig(fig, "fig22_关联规则图.png")


def fig23_funnel(df, f):
    fun = pd.DataFrame(f["funnel"])
    fun["人数"] = fun["人数"].astype(int)
    fig, ax = plt.subplots(figsize=(10, 6))
    maxw = fun["人数"].max()
    colors = [COLORS["primary"], "#3F7CB0", "#5FA0C8", COLORS["secondary"]]
    for i, r in fun.iterrows():
        w = r["人数"] / maxw
        y = len(fun) - i - 0.75
        ax.add_patch(FancyBboxPatch((0.5 - w / 2, y), w, 0.55,
                                    boxstyle="round,pad=0.005,rounding_size=0.02",
                                    facecolor=colors[i], edgecolor="white", linewidth=1.5))
        label = f"{r['阶段']}　{int(r['人数']):,} 人（{r['占全部客户%']:.1f}%）"
        if w >= 0.55:
            ax.text(0.5, y + 0.275, label, ha="center", va="center", fontsize=10.5,
                    color="white", fontweight="bold")
        else:
            ax.text(0.5 - w / 2 - 0.02, y + 0.275, label, ha="right", va="center", fontsize=10,
                    color=COLORS["dark"], fontweight="bold")
        if i > 0 and pd.notna(r["阶段转化率%"]):
            ax.annotate(f"转化 {r['阶段转化率%']:.1f}%", xy=(0.5, y + 0.62), ha="center",
                        fontsize=9, color="#666666")
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.2, len(fun) + 0.1)
    ax.axis("off")
    ax.set_title(f"客户价值漏斗（{f['kpi']['customers']} 位客户逐级收敛）", fontsize=14, fontweight="bold")
    note(fig)
    reg("业务模型图", "漏斗转化", "全部客户→复购→高频→高价值客户的逐级转化")
    return save_fig(fig, "fig23_客户价值漏斗.png")


def fig24_dashboard_preview(df, f):
    """大屏布局的静态预览（与 dashboard.html 同源同数据，便于论文插图）。"""
    k = f["kpi"]
    fig = plt.figure(figsize=(16, 9), facecolor="#0b1622")
    gs = fig.add_gridspec(4, 8, hspace=0.55, wspace=0.55, left=0.03, right=0.97, top=0.88, bottom=0.07)

    fig.text(0.03, 0.945, "SUPERSTORE 商业分析大屏", fontsize=21, color="#8ef0c4", fontweight="bold")
    fig.text(0.97, 0.95, "2014-01 ~ 2017-12　9,993 条明细　交互版：dashboard.html",
             fontsize=9, color="#7f95ab", ha="right")

    cards = [("销售额 GMV", f"${k['gmv']/1e6:,.2f}M", f"订单 {k['orders']:,} 笔"),
             ("利润总额", f"${k['profit']/1e3:,.0f}K", f"利润率 {k['margin']:.2f}%"),
             ("订单量", f"{k['orders']:,}", f"客单价 ${k['aov']:,.0f}"),
             ("客户数", f"{k['customers']:,}", f"人均 ${k['gmv']/k['customers']:,.0f}")]
    for i, (t, v, d) in enumerate(cards):
        ax = fig.add_subplot(gs[0, i * 2:(i + 1) * 2])
        ax.set_facecolor("#12263a")
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color("#1f3f5a")
        ax.text(0.06, 0.78, t, fontsize=10, color="#86a3bc", transform=ax.transAxes)
        ax.text(0.06, 0.40, v, fontsize=19, color="#eaf4ff", fontweight="bold", transform=ax.transAxes)
        ax.text(0.06, 0.12, d, fontsize=8.5, color="#67c9a3", transform=ax.transAxes)

    m = pd.read_csv(os.path.join(TABLES, "t03_monthly_series.csv"), parse_dates=["month"])
    ax1 = fig.add_subplot(gs[1:3, 0:5])
    ax1.set_facecolor("#0d1c2b")
    ax1.plot(m["month"], m["sales"], color="#4fc3f7", lw=2)
    ax1.fill_between(m["month"], m["sales"], color="#4fc3f7", alpha=0.22)
    ax1.set_title("月度销售额与利润趋势", color="#9fc3de", fontsize=11, loc="left")
    ax1.tick_params(colors="#7f95ab", labelsize=7.5)
    ax1.yaxis.set_major_formatter(THOUSANDS)
    for s in ax1.spines.values():
        s.set_color("#1f3f5a")
    ax1.grid(True, color="#16304a", lw=0.6)

    seg = df.groupby("Category")["Sales"].sum()
    ax2 = fig.add_subplot(gs[1:3, 5:8])
    ax2.set_facecolor("#0d1c2b")
    ax2.pie(seg.values, labels=seg.index, autopct="%1.1f%%", colors=PALETTE[7:10] + [PALETTE[0]],
            wedgeprops=dict(width=0.42, edgecolor="#0b1622"), textprops=dict(color="#c9d6e4", fontsize=9))
    ax2.set_title("品类销售结构", color="#9fc3de", fontsize=11, loc="left")

    reg_sales = df.groupby("Region")["Sales"].sum().sort_values()
    ax3 = fig.add_subplot(gs[3, 0:3])
    ax3.set_facecolor("#0d1c2b")
    ax3.barh(reg_sales.index, reg_sales.values, color="#3f8fb8")
    ax3.set_title("区域销售额", color="#9fc3de", fontsize=10, loc="left")
    ax3.tick_params(colors="#7f95ab", labelsize=8)
    ax3.xaxis.set_major_formatter(THOUSANDS)
    for s in ax3.spines.values():
        s.set_color("#1f3f5a")

    samp = df.sample(600, random_state=42)
    ax4 = fig.add_subplot(gs[3, 3:5])
    ax4.set_facecolor("#0d1c2b")
    ax4.scatter(samp["Discount"] * 100, samp["Profit Margin"] * 100, s=6,
                c=["#63d3c0" if v >= 0 else "#ef6f6c" for v in samp["Profit Margin"]], alpha=0.7)
    ax4.set_title("折扣率 vs 利润率", color="#9fc3de", fontsize=10, loc="left")
    ax4.set_ylim(-120, 80)
    ax4.tick_params(colors="#7f95ab", labelsize=8)
    for s in ax4.spines.values():
        s.set_color("#1f3f5a")

    ax5 = fig.add_subplot(gs[3, 5:8])
    ax5.set_facecolor("#0d1c2b")
    ax5.set_xticks([]); ax5.set_yticks([])
    for s in ax5.spines.values():
        s.set_color("#1f3f5a")
    ax5.set_title("子品类经营明细（Top5）", color="#9fc3de", fontsize=10, loc="left")
    top = df.groupby("Sub-Category").agg(s=("Sales", "sum"), p=("Profit", "sum")).sort_values("s", ascending=False).head(5)
    cell = [[r.Index, f"${r.s/1000:,.0f}K", f"{r.p/r.s*100:.1f}%"] for r in top.itertuples()]
    tb = ax5.table(cellText=cell, colLabels=["子品类", "销售额", "利润率"], loc="center", cellLoc="right")
    tb.auto_set_font_size(False)
    tb.set_fontsize(8)
    tb.scale(0.9, 1.25)
    for (row, col), c in tb.get_celld().items():
        c.set_edgecolor("#1f3f5a")
        c.set_facecolor("#0f2233")
        c.set_text_props(color="#c9d6e4" if row else "#8fb4cf")

    reg("模板复现", "大屏布局（静态预览）", "与 dashboard.html 同源数据的大屏版式预览，含 6 类组件")
    return save_fig(fig, "fig24_大屏布局预览.png", tight=False)


def main() -> None:
    ensure_dirs()
    setup_chinese_font()
    df, f = load()
    log("开始绘制 24 张图 ...")
    funcs = [fig01_kpi, fig02_subcat_bar, fig03_region_segment, fig04_year_category, fig05_monthly_line,
             fig06_cum_area, fig07_segment_pie, fig08_shipmode, fig09_discount_scatter, fig10_bubble,
             fig11_radar, fig12_waterfall, fig13_treemap, fig14_heatmap, fig15_boxplot, fig16_combo,
             fig17_rfm, fig18_pareto, fig19_boston, fig20_cohort, fig21_forecast, fig22_rules, fig23_funnel,
             fig24_dashboard_preview]
    for fn in funcs:
        path = fn(df, f)
        INDEX[-1]["文件名"] = os.path.basename(path)
    idx = pd.DataFrame(INDEX)
    idx.to_csv(os.path.join(TABLES, "t04_figure_index.csv"), index=False, encoding="utf-8-sig")
    log(f"完成：共 {len(idx)} 张图")


if __name__ == "__main__":
    main()

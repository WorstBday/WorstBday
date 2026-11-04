"""05_dashboard.py —— 交互式商业分析大屏（全 Python 生成，ECharts 渲染）

产物：outputs/dashboard/dashboard.html（自包含，离线双击即可打开）
组件（8 个，全部联动）：
  1) 4 张 KPI 指标卡      2) 月度销售额与利润趋势（折线+面积）
  3) 品类销售结构（环形） 4) 区域销售额（横向条形，可点击筛选）
  5) 折扣-利润率散点      6) 州 Top10 销售额条形
  7) 子品类明细表         8) 年份/区域/品类 三个筛选器 + 重置
数据以列式数组内嵌，前端按筛选条件实时聚合，实现「筛选 → 全部组件联动」。

运行：python scripts/05_dashboard.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".pylibs"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import ASSETS, CLEAN, DASH, ensure_dirs, log  # noqa: E402

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Superstore 商业分析大屏</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: radial-gradient(circle at 20% 0%, #17324f 0%, #0b1622 55%, #070d14 100%);
    color: #d7e3f0; font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
    min-height: 100vh; padding: 16px 22px 26px;
  }
  header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
  header h1 { font-size: 24px; letter-spacing: 2px; font-weight: 700;
    background: linear-gradient(90deg,#6fd3ff,#8ef0c4 60%,#ffd479);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  header .sub { font-size: 12px; color: #7f95ab; }
  .toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
  .toolbar label { font-size: 12px; color: #8fa7bd; }
  select { background: #13283d; color: #d7e3f0; border: 1px solid #27455f; border-radius: 6px;
    padding: 5px 10px; font-size: 12px; outline: none; cursor: pointer; }
  select:hover { border-color: #3f7ca8; }
  button { background: #1c3b57; color: #b9d4ea; border: 1px solid #2d5b81; border-radius: 6px;
    padding: 5px 14px; font-size: 12px; cursor: pointer; }
  button:hover { background: #24506f; }
  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
  .kpi { background: linear-gradient(160deg, rgba(41,84,120,.55), rgba(15,32,48,.75));
    border: 1px solid #1f3f5a; border-radius: 10px; padding: 12px 16px; position: relative; overflow: hidden; }
  .kpi::after { content: ""; position: absolute; left: 0; top: 0; width: 3px; height: 100%;
    background: linear-gradient(180deg, #58c8ff, #2a7fb8); }
  .kpi .t { font-size: 12px; color: #86a3bc; letter-spacing: 1px; }
  .kpi .v { font-size: 26px; font-weight: 700; color: #eaf4ff; margin-top: 4px; }
  .kpi .d { font-size: 11px; color: #67c9a3; margin-top: 2px; }
  .grid { display: grid; grid-template-columns: 1.55fr 1fr; gap: 12px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr 1.2fr; gap: 12px; margin-top: 12px; }
  .card { background: rgba(13,28,43,.72); border: 1px solid #1d3a53; border-radius: 10px;
    padding: 8px 10px 4px; position: relative; }
  .card h3 { font-size: 13px; font-weight: 600; color: #9fc3de; margin: 2px 0 0 4px; letter-spacing: 1px; }
  .card h3::before { content: "▎"; color: #4fb4ea; margin-right: 3px; }
  .chart { width: 100%; height: 250px; }
  .chart.tall { height: 330px; }
  .chart.mid { height: 230px; }
  table { width: 100%; border-collapse: collapse; font-size: 11.5px; margin-top: 6px; }
  th, td { padding: 5px 6px; text-align: right; border-bottom: 1px solid rgba(45,80,108,.45); }
  th { color: #8fb4cf; font-weight: 500; }
  td:first-child, th:first-child { text-align: left; }
  tr:hover td { background: rgba(60,120,170,.12); }
  .bar { display: inline-block; height: 8px; border-radius: 4px;
    background: linear-gradient(90deg,#2f8dc4,#63d3c0); vertical-align: middle; }
  footer { margin-top: 12px; font-size: 11px; color: #587089; }
</style>
</head>
<body>
<header>
  <h1>SUPERSTORE 商业分析大屏</h1>
  <div class="sub">数据区间 2014-01 ~ 2017-12 ｜ 9,993 条订单明细 ｜ 全 Python 生成（Matplotlib 静态图 + ECharts 交互）</div>
</header>
<div class="toolbar">
  <label>年份</label><select id="fYear"></select>
  <label>区域</label><select id="fRegion"></select>
  <label>品类</label><select id="fCat"></select>
  <button id="reset">重置筛选</button>
  <span class="sub" id="hint">提示：点击下方「区域」或「品类」图形的柱子/扇区也可联动筛选</span>
</div>

<div class="kpis">
  <div class="kpi"><div class="t">销售额 GMV</div><div class="v" id="k1">-</div><div class="d" id="k1d"></div></div>
  <div class="kpi"><div class="t">利润总额</div><div class="v" id="k2">-</div><div class="d" id="k2d"></div></div>
  <div class="kpi"><div class="t">订单量</div><div class="v" id="k3">-</div><div class="d" id="k3d"></div></div>
  <div class="kpi"><div class="t">客户数</div><div class="v" id="k4">-</div><div class="d" id="k4d"></div></div>
</div>

<div class="grid">
  <div class="card"><h3>月度销售额与利润趋势</h3><div class="chart tall" id="c1"></div></div>
  <div class="card"><h3>品类销售结构</h3><div class="chart tall" id="c2"></div></div>
</div>

<div class="grid2">
  <div class="card"><h3>区域销售额（可点击）</h3><div class="chart mid" id="c3"></div></div>
  <div class="card"><h3>折扣率与利润率</h3><div class="chart mid" id="c4"></div></div>
  <div class="card"><h3>州 Top10 销售额</h3><div class="chart mid" id="c5"></div></div>
</div>

<div class="card" style="margin-top:12px">
  <h3>子品类经营明细（按销售额降序）</h3>
  <table id="tbl">
    <thead><tr><th>子品类</th><th>销售额</th><th>利润</th><th>利润率</th><th>订单数</th><th>销售额占比</th></tr></thead>
    <tbody></tbody>
  </table>
</div>

<footer>数据来源：Tableau Sample - Superstore（Kaggle 公开数据集，CC0/公开可用）；图表全部由 Python 脚本 scripts/05_dashboard.py 生成，未使用 Power BI / Tableau 等 BI 软件。</footer>

<script>__ECHARTS__</script>
<script>
const D = __DATA__;
const YEARS = D.years, REGIONS = D.regions, CATS = D.categories, STATES = D.states, SUBS = D.subcategories;
const N = D.sales.length;

const TEXT = '#c9d6e4', GRID = 'rgba(120,160,200,.18)', ACCENT = ['#4aa8e0','#63d3c0','#ffb84d','#ef6f6c','#a98bf0','#7fd1ff'];
const axisCommon = {
  axisLine: { lineStyle: { color: '#2b4c68' } },
  axisLabel: { color: '#8fb0c9', fontSize: 11 },
  splitLine: { lineStyle: { color: GRID } }
};

const c1 = echarts.init(document.getElementById('c1'));
const c2 = echarts.init(document.getElementById('c2'));
const c3 = echarts.init(document.getElementById('c3'));
const c4 = echarts.init(document.getElementById('c4'));
const c5 = echarts.init(document.getElementById('c5'));

function opts(id, list, all) {
  const el = document.getElementById(id);
  el.innerHTML = '<option value="-1">' + all + '</option>' +
    list.map((v, i) => '<option value="' + i + '">' + v + '</option>').join('');
}

const CAT_LIST = D.categoryNames, REG_LIST = D.regionNames;
opts('fYear', D.yearNames, '全部年份');
opts('fRegion', REG_LIST, '全部区域');
opts('fCat', CAT_LIST, '全部品类');

function currentFilter() {
  return {
    year: +document.getElementById('fYear').value,
    region: +document.getElementById('fRegion').value,
    cat: +document.getElementById('fCat').value
  };
}

function filtered() {
  const f = currentFilter();
  const idx = [];
  for (let i = 0; i < N; i++) {
    if (f.year >= 0 && YEARS[i] !== D.yearNames[f.year]) continue;
    if (f.region >= 0 && REGIONS[i] !== REG_LIST[f.region]) continue;
    if (f.cat >= 0 && CATS[i] !== CAT_LIST[f.cat]) continue;
    idx.push(i);
  }
  return idx;
}

const fmt = n => n >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'k' : n.toFixed(0);
const money = n => '$' + n.toLocaleString('en-US', {maximumFractionDigits: 0});

function render() {
  const idx = filtered();
  // ---------- KPI ----------
  let sales = 0, profit = 0;
  const orderSet = new Set(), custSet = new Set();
  for (const i of idx) { sales += D.sales[i]; profit += D.profit[i]; orderSet.add(D.orders[i]); custSet.add(D.customers[i]); }
  const aov = orderSet.size ? sales / orderSet.size : 0;
  document.getElementById('k1').textContent = '$' + fmt(sales);
  document.getElementById('k1d').textContent = '订单 ' + orderSet.size.toLocaleString() + ' 笔';
  document.getElementById('k2').textContent = '$' + fmt(profit);
  document.getElementById('k2d').textContent = '利润率 ' + (sales ? (profit / sales * 100).toFixed(2) : '0') + '%';
  document.getElementById('k3').textContent = orderSet.size.toLocaleString();
  document.getElementById('k3d').textContent = '客单价 ' + money(aov);
  document.getElementById('k4').textContent = custSet.size.toLocaleString();
  document.getElementById('k4d').textContent = '人均消费 ' + money(custSet.size ? sales / custSet.size : 0);

  // ---------- 1. 月度趋势 ----------
  const months = D.months;
  const ms = new Array(months.length).fill(0), mp = new Array(months.length).fill(0);
  for (const i of idx) { ms[months[i]] += D.sales[i]; mp[months[i]] += D.profit[i]; }
  c1.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', valueFormatter: v => money(v) },
    legend: { data: ['销售额', '利润'], textStyle: { color: TEXT }, top: 0, right: 10, itemWidth: 14 },
    grid: { left: 58, right: 24, top: 34, bottom: 44 },
    xAxis: { type: 'category', data: D.monthLabels, boundaryGap: false, ...axisCommon,
             axisLabel: { color: '#8fb0c9', fontSize: 10, interval: 5 } },
    yAxis: { type: 'value', ...axisCommon, axisLabel: { color: '#8fb0c9', fontSize: 10, formatter: v => fmt(v) } },
    series: [
      { name: '销售额', type: 'line', smooth: true, symbol: 'none', data: ms,
        lineStyle: { width: 2.4, color: '#4fc3f7' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(79,195,247,.45)' }, { offset: 1, color: 'rgba(79,195,247,.02)' }]) } },
      { name: '利润', type: 'line', smooth: true, symbol: 'none', data: mp,
        lineStyle: { width: 2, color: '#ffb84d' } }
    ]
  }, true);

  // ---------- 2. 品类结构 ----------
  const agg = {};
  for (const i of idx) agg[CATS[i]] = (agg[CATS[i]] || 0) + D.sales[i];
  const pieData = Object.keys(agg).map(k => ({ name: k, value: +agg[k].toFixed(2) }));
  c2.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', valueFormatter: v => money(v) },
    legend: { bottom: 0, textStyle: { color: TEXT }, itemWidth: 12 },
    color: ACCENT,
    series: [{
      type: 'pie', radius: ['46%', '72%'], center: ['50%', '46%'], avoidLabelOverlap: true,
      itemStyle: { borderColor: '#0b1622', borderWidth: 2 },
      label: { color: '#cfe3f5', formatter: '{b}\n{d}%', fontSize: 11 },
      data: pieData
    }]
  }, true);

  // ---------- 3. 区域 ----------
  const regAgg = {};
  REG_LIST.forEach(r => regAgg[r] = 0);
  for (const i of idx) regAgg[REGIONS[i]] += D.sales[i];
  const regKeys = REG_LIST.slice().sort((a, b) => regAgg[a] - regAgg[b]);
  c3.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: v => money(v) },
    grid: { left: 64, right: 40, top: 12, bottom: 22 },
    xAxis: { type: 'value', ...axisCommon, axisLabel: { color: '#8fb0c9', fontSize: 10, formatter: v => fmt(v) } },
    yAxis: { type: 'category', data: regKeys, ...axisCommon },
    series: [{
      type: 'bar', data: regKeys.map(k => +regAgg[k].toFixed(2)), barWidth: '52%',
      itemStyle: { borderRadius: [0, 6, 6, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#24688f' }, { offset: 1, color: '#63d3c0' }]) },
      label: { show: true, position: 'right', color: '#a9c6dd', fontSize: 10, formatter: p => money(p.value) }
    }]
  }, true);

  // ---------- 4. 折扣 vs 利润率 ----------
  const pts = [];
  const step = Math.max(1, Math.floor(idx.length / 1200));
  for (let k = 0; k < idx.length; k += step) {
    const i = idx[k];
    pts.push([+(D.disc[i] * 100).toFixed(1), +D.margin[i].toFixed(1), D.sales[i]]);
  }
  c4.setOption({
    backgroundColor: 'transparent',
    tooltip: { formatter: p => '折扣 ' + p.value[0] + '%<br/>利润率 ' + p.value[1] + '%<br/>销售额 ' + money(p.value[2]) },
    grid: { left: 52, right: 18, top: 16, bottom: 40 },
    xAxis: { type: 'value', name: '折扣率(%)', nameTextStyle: { color: '#8fb0c9', fontSize: 10 },
             ...axisCommon, axisLabel: { color: '#8fb0c9', fontSize: 10 } },
    yAxis: { type: 'value', name: '利润率(%)', nameTextStyle: { color: '#8fb0c9', fontSize: 10 },
             ...axisCommon, axisLabel: { color: '#8fb0c9', fontSize: 10 } },
    series: [{
      type: 'scatter', symbolSize: 5, data: pts,
      itemStyle: { color: p => p.value[1] >= 0 ? 'rgba(99,211,192,.75)' : 'rgba(239,111,108,.75)' }
    }]
  }, true);

  // ---------- 5. 州 Top10 ----------
  const stAgg = {};
  for (const i of idx) stAgg[STATES[i]] = (stAgg[STATES[i]] || 0) + D.sales[i];
  const top = Object.entries(stAgg).sort((a, b) => a[1] - b[1]).slice(-10);
  c5.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: v => money(v) },
    grid: { left: 108, right: 46, top: 10, bottom: 22 },
    xAxis: { type: 'value', ...axisCommon, axisLabel: { color: '#8fb0c9', fontSize: 10, formatter: v => fmt(v) } },
    yAxis: { type: 'category', data: top.map(d => d[0]), ...axisCommon, axisLabel: { color: '#8fb0c9', fontSize: 10 } },
    series: [{
      type: 'bar', data: top.map(d => +d[1].toFixed(2)), barWidth: '55%',
      itemStyle: { borderRadius: [0, 5, 5, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#3b6f9c' }, { offset: 1, color: '#7fd1ff' }]) },
      label: { show: true, position: 'right', color: '#a9c6dd', fontSize: 9.5, formatter: p => fmt(p.value) }
    }]
  }, true);

  // ---------- 6. 明细表 ----------
  const subAgg = {};
  for (const i of idx) {
    const s = SUBS[i];
    if (!subAgg[s]) subAgg[s] = { sales: 0, profit: 0, orders: new Set() };
    subAgg[s].sales += D.sales[i]; subAgg[s].profit += D.profit[i]; subAgg[s].orders.add(D.orders[i]);
  }
  const rows = Object.entries(subAgg).map(([k, v]) => [k, v.sales, v.profit, v.sales ? v.profit / v.sales * 100 : 0, v.orders.size])
    .sort((a, b) => b[1] - a[1]).slice(0, 10);
  const maxS = rows.length ? rows[0][1] : 1;
  document.querySelector('#tbl tbody').innerHTML = rows.map(r => {
    const w = Math.max(4, r[1] / maxS * 100);
    return '<tr><td>' + r[0] + '</td><td>' + money(r[1]) + '</td><td>' + money(r[2]) +
      '</td><td style="color:' + (r[3] >= 0 ? '#67c9a3' : '#ef6f6c') + '">' + r[3].toFixed(1) + '%' +
      '</td><td>' + r[4].toLocaleString() + '</td>' +
      '<td><span class="bar" style="width:' + w + '%"></span> ' + (r[1] / (sales || 1) * 100).toFixed(1) + '%</td></tr>';
  }).join('');
}

['fYear', 'fRegion', 'fCat'].forEach(id => document.getElementById(id).addEventListener('change', render));
document.getElementById('reset').addEventListener('click', () => {
  ['fYear', 'fRegion', 'fCat'].forEach(id => document.getElementById(id).value = '-1');
  render();
});
// 图形点击联动：区域条形 / 品类环
c3.on('click', p => { const i = REG_LIST.indexOf(p.name); if (i >= 0) { document.getElementById('fRegion').value = i; render(); } });
c2.on('click', p => { const i = CAT_LIST.indexOf(p.name); if (i >= 0) { document.getElementById('fCat').value = i; render(); } });
window.addEventListener('resize', () => { c1.resize(); c2.resize(); c3.resize(); c4.resize(); c5.resize(); });
render();
</script>
</body>
</html>
"""


def main() -> None:
    ensure_dirs()
    df = pd.read_csv(os.path.join(CLEAN, "superstore_clean.csv"), encoding="utf-8",
                     parse_dates=["YearMonthDate"])
    month_labels = sorted(df["YearMonth"].unique())
    m_index = {m: i for i, m in enumerate(month_labels)}
    states = sorted(df["State"].unique())
    regs = sorted(df["Region"].unique())
    cats = sorted(df["Category"].unique())
    subs = sorted(df["Sub-Category"].unique())
    years = sorted(df["Order Year"].unique())

    data = {
        "years": df["Order Year"].astype(str).tolist(),
        "regions": df["Region"].tolist(),
        "categories": df["Category"].tolist(),
        "states": df["State"].tolist(),
        "subcategories": df["Sub-Category"].tolist(),
        "months": [m_index[m] for m in df["YearMonth"]],
        "sales": df["Sales"].round(2).tolist(),
        "profit": df["Profit"].round(2).tolist(),
        "disc": df["Discount"].round(2).tolist(),
        "margin": (df["Profit Margin"] * 100).round(1).fillna(0).tolist(),
        "orders": df["Order ID"].tolist(),
        "customers": df["Customer ID"].tolist(),
        "monthLabels": month_labels,
        "regionNames": regs,
        "categoryNames": cats,
        "yearNames": [str(y) for y in years],
        "stateNames": states,
        "subcatNames": subs,
    }

    js_path = os.path.join(ASSETS, "echarts.min.js")
    if not os.path.exists(js_path):
        raise SystemExit(f"缺少离线 ECharts 资源：{js_path}")
    with open(js_path, encoding="utf-8") as f:
        echarts_js = f.read()

    html = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("__ECHARTS__", echarts_js)
    out = os.path.join(DASH, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"大屏已生成：{out}（{os.path.getsize(out)/1024:.0f} KB，自包含离线可用）")


if __name__ == "__main__":
    main()

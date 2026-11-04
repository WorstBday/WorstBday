# 数据结构说明（Schema）

## 一、原始数据

- 文件：`data/raw/superstore_raw.csv`（另保留 `superstore.zip` 原始压缩包）
- 编码：cp1252（Candada/US 混合字符集，读取后统一转 UTF-8）
- 规模：9,994 行 × 21 列
- 时间范围：2014-01-03 ~ 2017-12-30

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| Row ID | int | 行序号，唯一 |
| Order ID | str | 订单号，一单可含多行商品 |
| Order Date | date | 下单日期 |
| Ship Date | date | 发货日期 |
| Ship Mode | str | 配送方式（4 类） |
| Customer ID | str | 客户编号 |
| Customer Name | str | 客户姓名 |
| Segment | str | Consumer / Corporate / Home Office |
| Country | str | 国家（全部为 United States） |
| City | str | 城市 |
| State | str | 州（49 个） |
| Postal Code | str | 邮编（原表 449 条缺前导 0） |
| Region | str | East / West / Central / South |
| Product ID | str | 产品编号 |
| Category | str | Furniture / Office Supplies / Technology |
| Sub-Category | str | 子品类（17 类） |
| Product Name | str | 产品名称 |
| Sales | float | 销售额（美元） |
| Quantity | int | 数量 |
| Discount | float | 折扣率 0~0.8 |
| Profit | float | 利润（美元，可为负） |

## 二、清洗后明细

- 文件：`data/clean/superstore_clean.csv`
- 规模：9,993 行 × 33 列（删除 1 条业务字段完全重复记录；新增 12 个派生字段）

派生字段：

| 字段 | 计算方式 | 用途 |
| --- | --- | --- |
| Ship Days | Ship Date − Order Date | 履约效率 |
| Order Year / Month / Quarter | 由 Order Date 提取 | 时间维度 |
| Order Weekday | 0=周一 | 周内规律 |
| YearMonth | 月度粒度字符串 | 月度聚合 |
| YearMonthDate | 月度粒度日期 | 时间序列建模 |
| Profit Margin | Profit / Sales | 利润诊断 |
| Unit Price | Sales / Quantity | 价格分析 |
| Discount Band | 按 0/20%/40%/60% 分箱 | 折扣区间对比 |
| Is Loss | Profit < 0 | 亏损订单占比 |
| is_outlier | 销售额同时超过 IQR 上限与 3σ 上限 | 极值标记（不删除） |

## 三、星型模型（SQLite：`data/clean/superstore.db`）

```
fact_order_items (Row ID 主键)
 ├── Order ID     → dim_order(Order ID)
 ├── Customer ID  → dim_customer(Customer ID)
 └── Product ID   → dim_product(Product ID)
```

| 表 | 行数 | 主键 | 说明 |
| --- | --- | --- | --- |
| fact_order_items | 9,993 | Row ID | 订单明细事实表（度量：Sales/Quantity/Discount/Profit） |
| dim_customer | 793 | Customer ID | 客户属性（姓名、细分、城市、州、区域、邮编） |
| dim_product | 1,862 | Product ID | 产品属性（名称、品类、子品类） |
| dim_order | 5,009 | Order ID | 订单级汇总（日期、配送、客户、行数、销售额、利润） |

索引：`idx_cust`、`idx_prod`、`idx_order`（均为唯一索引，保证维度表主键唯一）。

引用完整性：事实表中 Customer ID / Product ID / Order ID 在维度表中均能命中，孤儿记录 0 条。

## 四、结果表（`outputs/tables/`）

| 文件 | 内容 |
| --- | --- |
| t01_schema.csv | 字段说明与缺失/唯一值统计 |
| t02_cleaning_report.csv | 清洗处置逐项记录 |
| t02_clean_summary.json | 清洗前后规模、修复条数等汇总 |
| t03_monthly.csv | 月度销售额、利润、订单、同比、环比、移动平均 |
| t03_yearly.csv | 年度指标与同比 |
| t03_region.csv / t03_segment.csv / t03_shipmode.csv | 区域、客户细分、配送方式汇总 |
| t03_subcategory.csv | 17 个子品类的销售额、利润、利润率、折扣、亏损占比 |
| t03_discount.csv | 五个折扣区间的利润率与亏损占比 |
| t03_abc_customer.csv / t03_abc_product.csv | ABC 分级结果 |
| t03_rfm.csv / t03_rfm_segment.csv | 客户 RFM 明细与八分类汇总 |
| t03_kmeans.csv | K-Means 四类客户画像 |
| t03_cohort.csv | 季度同期群留存矩阵 |
| t03_boston.csv | 子品类份额、增速与象限 |
| t03_forecast.csv | 2018 年上半年点预测与 95% 置信区间 |
| t03_rules.csv | Apriori 关联规则 Top20 |
| t03_funnel.csv | 客户价值漏斗四阶段 |
| t03_facts.json | 论文引用的全部关键数字（便于核对） |
| t04_figure_index.csv | 24 张图表的索引 |

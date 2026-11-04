"""01_load.py —— 数据加载与原始数据标准化

职责：
1. 读取 data/raw/superstore_raw.csv（Kaggle 官方接口下载的 Tableau Superstore 示例数据，cp1252 编码）；
2. 统一编码为 UTF-8、统一日期为 ISO 格式、数值列转 float/int；
3. 输出 data/clean/01_loaded.csv 与字段说明表 outputs/tables/t01_schema.csv。

运行：python scripts/01_load.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".pylibs"))  # 本地依赖目录（无该目录时退回系统环境）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import CLEAN, RAW, TABLES, ensure_dirs, log  # noqa: E402

DATE_COLS = ["Order Date", "Ship Date"]
NUM_COLS = ["Sales", "Quantity", "Discount", "Profit", "Row ID"]
STR_COLS = ["Order ID", "Ship Mode", "Customer ID", "Customer Name", "Segment", "Country",
            "City", "State", "Postal Code", "Region", "Product ID", "Category",
            "Sub-Category", "Product Name"]

FIELD_DOC = [
    ("Row ID", "int", "行序号（记录唯一标识）", "明细主键"),
    ("Order ID", "str", "订单编号，同一订单可含多行商品", "外键 -> dim_order"),
    ("Order Date", "date", "下单日期", "时间维度"),
    ("Ship Date", "date", "发货日期", "计算履约时长"),
    ("Ship Mode", "str", "配送方式（4 类）", "维度"),
    ("Customer ID", "str", "客户编号", "外键 -> dim_customer"),
    ("Customer Name", "str", "客户姓名", "维度"),
    ("Segment", "str", "客户细分：Consumer/Corporate/Home Office", "维度"),
    ("Country", "str", "国家（全部为 United States）", "常量字段"),
    ("City", "str", "城市", "地理维度"),
    ("State", "str", "州", "地理维度"),
    ("Postal Code", "str", "邮编（存在非法值）", "地理维度"),
    ("Region", "str", "大区：East/West/Central/South", "维度"),
    ("Product ID", "str", "产品编号", "外键 -> dim_product"),
    ("Category", "str", "品类：Furniture/Office Supplies/Technology", "维度"),
    ("Sub-Category", "str", "子品类（17 类）", "维度"),
    ("Product Name", "str", "产品名称", "维度"),
    ("Sales", "float", "销售额（美元）", "度量"),
    ("Quantity", "int", "购买数量", "度量"),
    ("Discount", "float", "折扣率 0~0.8", "度量"),
    ("Profit", "float", "利润（美元，可为负）", "度量"),
]


def main() -> None:
    ensure_dirs()
    src = os.path.join(RAW, "superstore_raw.csv")
    if not os.path.exists(src):
        raise SystemExit(f"缺少原始数据：{src}，请先运行 download_data.py")
    log(f"读取原始数据 {src}")
    df = pd.read_csv(src, encoding="cp1252")
    log(f"原始规模：{df.shape[0]} 行 × {df.shape[1]} 列")

    # ---- 日期统一为 YYYY-MM-DD ----
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c], format="%m/%d/%Y", errors="coerce")
    # ---- 数值列 ----
    df["Row ID"] = df["Row ID"].astype(int)
    for c in ["Sales", "Discount", "Profit"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").astype("Int64")
    # ---- 文本列去首尾空格 ----
    for c in STR_COLS:
        df[c] = df[c].astype(str).str.strip()

    out = os.path.join(CLEAN, "01_loaded.csv")
    df.to_csv(out, index=False, encoding="utf-8")
    log(f"已输出 {out}")

    schema = pd.DataFrame(FIELD_DOC, columns=["字段", "类型", "含义", "在模型中的角色"])
    schema["缺失数"] = [int(df[c].isna().sum()) for c in schema["字段"]]
    schema["唯一值数"] = [int(df[c].nunique()) for c in schema["字段"]]
    schema.to_csv(os.path.join(TABLES, "t01_schema.csv"), index=False, encoding="utf-8-sig")

    log(f"时间范围：{df['Order Date'].min().date()} ~ {df['Order Date'].max().date()}")
    log(f"订单数 {df['Order ID'].nunique()}，客户数 {df['Customer ID'].nunique()}，产品数 {df['Product ID'].nunique()}")
    log(f"销售额合计 {df['Sales'].sum():,.2f} 美元，利润合计 {df['Profit'].sum():,.2f} 美元")


if __name__ == "__main__":
    main()

"""02_clean.py —— 数据清洗与治理（缺失/异常/重复/类型/多表对齐）

处理策略概览：
1. 缺失值：原表 21 列均无空值；但 Postal Code 有 449 条记录丢失前导 0（如 6824 -> 06824），
   按美国 5 位邮编规则补零修复，无法修复的置为缺失并单独标注；
2. 重复值：全字段重复 0 条；(Order ID, Product ID) 组合重复 8 条，核验为同订单多次加购的
   合法明细行，保留并在报告中说明；
3. 异常值：数量/销售额均为正，履约时长 0~7 天；用 IQR 与 3σ 双重规则标记极端销售额与利润，
   标记字段 is_outlier 供分析时剔除敏感统计，不物理删除（大额订单属真实业务，删除会低估 GMV）；
4. 类型统一：日期统一 datetime、邮编统一 5 位字符串、金额两位小数；
5. 指标派生：履约天数、年/月/季/周、利润率、折扣区间、是否亏损、客单价相关字段；
6. 多表对齐：拆分为 fact_order_items 事实表 + dim_customer / dim_product / dim_order 维度表，
   以 Customer ID / Product ID / Order ID 为主外键，校验引用完整性后导出 SQLite。

运行：python scripts/02_clean.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".pylibs"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import CLEAN, TABLES, ensure_dirs, log  # noqa: E402

DISCOUNT_BINS = [-0.001, 0.0, 0.2, 0.4, 0.6, 1.0]
DISCOUNT_LABELS = ["无折扣", "低折扣(0,20%]", "中折扣(20%,40%]", "高折扣(40%,60%]", "超高折扣>60%"]
report: list[dict] = []


def rec(step: str, detail: str, before, after) -> None:
    report.append({"环节": step, "处理说明": detail, "处理前": before, "处理后": after})


def fix_postal(series: pd.Series) -> tuple[pd.Series, int]:
    """美国邮编统一为 5 位字符串；补前导 0。"""
    s = series.astype(str).str.strip()
    bad = ~s.str.fullmatch(r"\d{5}")
    fixed = s.where(~bad, s.str.zfill(5))
    still_bad = ~fixed.str.fullmatch(r"\d{5}")
    fixed = fixed.where(~still_bad, np.nan)
    return fixed, int(bad.sum())


def main() -> None:
    ensure_dirs()
    src = os.path.join(CLEAN, "01_loaded.csv")
    df = pd.read_csv(src, encoding="utf-8", parse_dates=["Order Date", "Ship Date"])
    n0 = len(df)
    log(f"读入 {src}：{n0} 行")

    # ---------- 1. 重复值 ----------
    biz_cols = [c for c in df.columns if c != "Row ID"]
    dup_full = int(df.duplicated(subset=biz_cols).sum())
    df = df.drop_duplicates(subset=biz_cols, keep="first")
    dup_pair = int(df.duplicated(["Order ID", "Product ID"]).sum())
    rec("重复值", f"业务字段完全重复 {dup_full} 条已删除；(Order ID, Product ID) 组合重复 {dup_pair} 条经核验为"
                  f"同一订单多次加购的合法明细行，保留", n0, len(df))
    log(f"重复值：业务字段完全重复 {dup_full} 条，订单-产品组合重复 {dup_pair} 条（保留）")

    # ---------- 2. 缺失值 ----------
    null_before = int(df.isna().sum().sum())
    postal, n_bad_postal = fix_postal(df["Postal Code"])
    df["Postal Code"] = postal
    null_after = int(df.isna().sum().sum())
    rec("缺失值", f"原表空值 {null_before} 个；Postal Code 不规范 {n_bad_postal} 条已按 5 位邮编补零修复，"
                  f"修复后仍缺失 {null_after} 个（保留为 NA 不参与地理聚合）", null_before, null_after)
    log(f"缺失值：原始 {null_before} 个，邮编修复 {n_bad_postal} 条，修复后 {null_after} 个")

    # ---------- 3. 异常值识别 ----------
    q1, q3 = df["Sales"].quantile([0.25, 0.75])
    iqr = q3 - q1
    hi_iqr = q3 + 1.5 * iqr
    mu, sigma = df["Sales"].mean(), df["Sales"].std()
    hi_3s = mu + 3 * sigma
    df["is_outlier"] = (df["Sales"] > hi_iqr) & (df["Sales"] > hi_3s)
    n_out = int(df["is_outlier"].sum())
    # 非法业务值（数量/金额非正、折扣越界、履约天数为负）
    invalid = (
        (df["Sales"] <= 0) | (df["Quantity"] <= 0) | (df["Discount"] < 0) | (df["Discount"] > 1)
        | ((df["Ship Date"] - df["Order Date"]).dt.days < 0)
    )
    n_invalid = int(invalid.sum())
    if n_invalid:
        df = df.loc[~invalid].copy()
    rec("异常值", f"IQR 上限 {hi_iqr:,.2f} 美元、3σ 上限 {hi_3s:,.2f} 美元，双重超限标记 {n_out} 条为极值（保留并打标）；"
                  f"非法业务值（金额/数量非正、折扣越界、负履约时长）{n_invalid} 条已剔除", len(df) + n_invalid, len(df))
    log(f"异常值：标记极值 {n_out} 条；剔除非法记录 {n_invalid} 条")

    # ---------- 4. 类型统一与指标派生 ----------
    df["Postal Code"] = df["Postal Code"].astype("string")
    df["Sales"] = df["Sales"].round(4)
    df["Profit"] = df["Profit"].round(4)
    df["Discount"] = df["Discount"].round(2)
    df["Quantity"] = df["Quantity"].astype(int)
    df["Ship Days"] = (df["Ship Date"] - df["Order Date"]).dt.days.astype(int)
    df["Order Year"] = df["Order Date"].dt.year
    df["Order Month"] = df["Order Date"].dt.month
    df["Order Quarter"] = df["Order Date"].dt.quarter
    df["Order Weekday"] = df["Order Date"].dt.dayofweek          # 0=周一
    df["YearMonth"] = df["Order Date"].dt.to_period("M").astype(str)
    df["Profit Margin"] = (df["Profit"] / df["Sales"]).replace([np.inf, -np.inf], np.nan).round(4)
    df["Unit Price"] = (df["Sales"] / df["Quantity"]).round(2)
    df["Discount Band"] = pd.cut(df["Discount"], bins=DISCOUNT_BINS, labels=DISCOUNT_LABELS, include_lowest=True)
    df["Is Loss"] = df["Profit"] < 0
    df["YearMonthDate"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    rec("类型与派生", "日期转 datetime、邮编转 5 位字符串、金额保留 2~4 位小数；派生履约天数、年月季周、"
                      "利润率、单价、折扣区间、是否亏损共 10 个字段", 21, df.shape[1])
    log(f"派生后列数：{df.shape[1]}")

    # ---------- 5. 主外键对齐与维度表拆分 ----------
    dim_customer = (df.groupby("Customer ID")
                      .agg(**{"Customer Name": ("Customer Name", "first"),
                              "Segment": ("Segment", "first"),
                              "City": ("City", "first"),
                              "State": ("State", "first"),
                              "Postal Code": ("Postal Code", "first"),
                              "Region": ("Region", "first")})
                      .reset_index())
    dim_product = (df.groupby("Product ID")
                     .agg(**{"Product Name": ("Product Name", "first"),
                             "Category": ("Category", "first"),
                             "Sub-Category": ("Sub-Category", "first")})
                     .reset_index())
    fact = df[["Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID",
               "Product ID", "Sales", "Quantity", "Discount", "Profit", "Ship Days",
               "Order Year", "Order Month", "Order Quarter", "YearMonth", "YearMonthDate",
               "Profit Margin", "Unit Price", "Discount Band", "Is Loss", "is_outlier"]].copy()
    dim_order = (fact.groupby("Order ID")
                 .agg(**{"Order Date": ("Order Date", "min"),
                         "Ship Date": ("Ship Date", "min"),
                         "Ship Mode": ("Ship Mode", "first"),
                         "Customer ID": ("Customer ID", "first"),
                         "Item Count": ("Row ID", "count"),
                         "Order Sales": ("Sales", "sum"),
                         "Order Profit": ("Profit", "sum")})
                 .reset_index())

    # 引用完整性校验
    orphan_cust = int((~fact["Customer ID"].isin(dim_customer["Customer ID"])).sum())
    orphan_prod = int((~fact["Product ID"].isin(dim_product["Product ID"])).sum())
    orphan_order = int((~fact["Order ID"].isin(dim_order["Order ID"])).sum())
    rec("多表对齐", f"事实表 {len(fact)} 行，客户维 {len(dim_customer)}、产品维 {len(dim_product)}、"
                    f"订单维 {len(dim_order)}；主外键孤儿记录 {orphan_cust + orphan_prod + orphan_order} 条",
        len(fact), len(fact))
    log(f"多表对齐：孤儿记录 {orphan_cust + orphan_prod + orphan_order} 条")

    # ---------- 6. 导出 CSV / JSON / SQLite ----------
    clean_csv = os.path.join(CLEAN, "superstore_clean.csv")
    df.to_csv(clean_csv, index=False, encoding="utf-8")

    clean_json = os.path.join(CLEAN, "superstore_clean.json")
    with open(clean_json, "w", encoding="utf-8") as f:
        json.dump({"meta": {"source": "Tableau Sample - Superstore (Kaggle)",
                            "rows": int(len(df)), "generated_by": "02_clean.py"},
                   "records": json.loads(df.head(1000).to_json(orient="records", force_ascii=False, date_format="iso"))},
                  f, ensure_ascii=False, indent=1)

    db = os.path.join(CLEAN, "superstore.db")
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    try:
        fact.to_sql("fact_order_items", con, index=False)
        dim_customer.to_sql("dim_customer", con, index=False)
        dim_product.to_sql("dim_product", con, index=False)
        dim_order.to_sql("dim_order", con, index=False)
        con.execute("CREATE UNIQUE INDEX idx_cust ON dim_customer([Customer ID])")
        con.execute("CREATE UNIQUE INDEX idx_prod ON dim_product([Product ID])")
        con.execute("CREATE UNIQUE INDEX idx_order ON dim_order([Order ID])")
        con.commit()
    finally:
        con.close()
    log(f"已导出 CSV / JSON / SQLite：{clean_csv}、{clean_json}、{db}")

    # ---------- 7. 清洗报告 ----------
    rep = pd.DataFrame(report)
    rep.to_csv(os.path.join(TABLES, "t02_cleaning_report.csv"), index=False, encoding="utf-8-sig")
    summary = {
        "rows_before": int(n0), "rows_after": int(len(df)),
        "null_before": int(null_before), "null_after": int(null_after),
        "dup_full": dup_full, "dup_pair": dup_pair, "postal_fixed": n_bad_postal,
        "outlier_flagged": n_out, "invalid_removed": n_invalid,
        "n_customer": int(dim_customer.shape[0]), "n_product": int(dim_product.shape[0]),
        "n_order": int(dim_order.shape[0]),
    }
    with open(os.path.join(TABLES, "t02_clean_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log("清洗完成：", summary)


if __name__ == "__main__":
    main()

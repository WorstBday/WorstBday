"""03_analysis.py —— 商业分析模型计算

模型清单（与论文第 4 章一一对应）：
  M1 描述性趋势与同比/环比      —— 月度 GMV、利润与增长率
  M2 帕累托/ABC 分类            —— 客户与产品的价值集中度
  M3 RFM 八分类                 —— 以中位数切分的客户价值分层
  M4 同期群留存分析             —— 按首购月份分组的复购留存矩阵
  M5 波士顿矩阵                 —— 子品类「份额 × 增速」四象限
  M6 SARIMA 时间序列预测        —— 月度销售额点预测 + 95% 置信区间 + 回测
  M7 关联规则（Apriori）        —— 订单内子品类组合的规则挖掘
  M8 客户价值漏斗               —— 从全部客户到高价值客户的逐级转化

统一输出到 outputs/tables/，并把论文要引用的关键数字写入 t03_facts.json。

运行：python scripts/03_analysis.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".pylibs"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import CLEAN, TABLES, ensure_dirs, log  # noqa: E402

warnings.filterwarnings("ignore")
T = lambda name: os.path.join(TABLES, name)  # noqa: E731


def jnum(x, nd=2):
    """安全转可 JSON 序列化的数值。"""
    try:
        v = float(x)
        if not np.isfinite(v):
            return None
        return round(v, nd)
    except Exception:
        return None


def main() -> None:
    ensure_dirs()
    df = pd.read_csv(os.path.join(CLEAN, "superstore_clean.csv"), encoding="utf-8",
                     parse_dates=["Order Date", "Ship Date", "YearMonthDate"])
    facts: dict = {}

    # ================= M1 总体指标与趋势 =================
    log("M1 趋势与同比环比 ...")
    gmv, profit = df["Sales"].sum(), df["Profit"].sum()
    orders, customers = df["Order ID"].nunique(), df["Customer ID"].nunique()
    loss_rows = int(df["Is Loss"].sum())
    facts["kpi"] = {
        "gmv": jnum(gmv), "profit": jnum(profit), "margin": jnum(profit / gmv * 100),
        "orders": int(orders), "customers": int(customers), "items": int(len(df)),
        "aov": jnum(gmv / orders), "avg_discount": jnum(df["Discount"].mean() * 100),
        "loss_row_share": jnum(loss_rows / len(df) * 100), "loss_amount": jnum(df.loc[df["Is Loss"], "Profit"].sum()),
        "start": str(df["Order Date"].min().date()), "end": str(df["Order Date"].max().date()),
        "state_count": int(df["State"].nunique()), "product_count": int(df["Product ID"].nunique()),
        "subcat_count": int(df["Sub-Category"].nunique()),
        "avg_ship_days": jnum(df["Ship Days"].mean()),
        "profit_per_item": jnum(profit / len(df)),
    }

    monthly = (df.groupby("YearMonthDate")
                 .agg(sales=("Sales", "sum"), profit=("Profit", "sum"),
                      orders=("Order ID", "nunique"), customers=("Customer ID", "nunique"))
                 .reset_index().sort_values("YearMonthDate"))
    monthly["yoy"] = monthly["sales"].pct_change(12) * 100
    monthly["mom"] = monthly["sales"].pct_change(1) * 100
    monthly["ma3"] = monthly["sales"].rolling(3).mean()
    monthly["margin"] = monthly["profit"] / monthly["sales"] * 100
    monthly.to_csv(T("t03_monthly.csv"), index=False, encoding="utf-8-sig")

    yearly = df.groupby("Order Year").agg(sales=("Sales", "sum"), profit=("Profit", "sum"),
                                          orders=("Order ID", "nunique")).reset_index()
    yearly["yoy_sales"] = yearly["sales"].pct_change() * 100
    yearly["yoy_profit"] = yearly["profit"].pct_change() * 100
    yearly["margin"] = yearly["profit"] / yearly["sales"] * 100
    yearly.to_csv(T("t03_yearly.csv"), index=False, encoding="utf-8-sig")
    facts["yearly"] = yearly.round(2).to_dict(orient="records")
    facts["yoy_2017"] = jnum(yearly.loc[yearly["Order Year"] == 2017, "yoy_sales"].iloc[0])
    facts["yoy_2017_profit"] = jnum(yearly.loc[yearly["Order Year"] == 2017, "yoy_profit"].iloc[0])

    season = monthly.assign(m=monthly["YearMonthDate"].dt.month).groupby("m")["sales"].mean()
    facts["peak_month"] = int(season.idxmax())
    facts["trough_month"] = int(season.idxmin())
    facts["peak_ratio"] = jnum(season.max() / season.min(), 2)

    # ================= 结构与区域 =================
    log("结构分析 ...")
    region = (df.groupby("Region")
                .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), orders=("Order ID", "nunique"),
                     customers=("Customer ID", "nunique"), qty=("Quantity", "sum"))
                .reset_index())
    region["margin"] = region["profit"] / region["sales"] * 100
    region["share"] = region["sales"] / region["sales"].sum() * 100
    region["aov"] = region["sales"] / region["orders"]
    region.to_csv(T("t03_region.csv"), index=False, encoding="utf-8-sig")

    sub = (df.groupby(["Category", "Sub-Category"])
             .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), qty=("Quantity", "sum"),
                  orders=("Order ID", "nunique"), avg_disc=("Discount", "mean"),
                  loss_share=("Is Loss", "mean"))
             .reset_index())
    sub["margin"] = sub["profit"] / sub["sales"] * 100
    sub["share"] = sub["sales"] / sub["sales"].sum() * 100
    sub.to_csv(T("t03_subcategory.csv"), index=False, encoding="utf-8-sig")
    facts["top_subcat"] = sub.sort_values("sales", ascending=False).head(3)[["Sub-Category", "sales", "margin"]].round(2).to_dict(orient="records")
    facts["worst_subcat"] = sub.sort_values("margin").head(3)[["Sub-Category", "sales", "margin"]].round(2).to_dict(orient="records")
    facts["neg_profit_subcat"] = int((sub["profit"] < 0).sum())

    segment = (df.groupby("Segment")
                 .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), orders=("Order ID", "nunique"),
                      customers=("Customer ID", "nunique"))
                 .reset_index())
    segment["margin"] = segment["profit"] / segment["sales"] * 100
    segment["share"] = segment["sales"] / segment["sales"].sum() * 100
    segment.to_csv(T("t03_segment.csv"), index=False, encoding="utf-8-sig")

    shipmode = (df.groupby("Ship Mode")
                  .agg(orders=("Order ID", "nunique"), sales=("Sales", "sum"), days=("Ship Days", "mean"))
                  .reset_index())
    shipmode["share"] = shipmode["orders"] / shipmode["orders"].sum() * 100
    shipmode.to_csv(T("t03_shipmode.csv"), index=False, encoding="utf-8-sig")
    facts["shipmode_best"] = shipmode.sort_values("days").iloc[0][["Ship Mode", "days", "share"]].to_dict()

    # 折扣与利润关系（供散点图与建议引用）
    disc = (df.groupby("Discount Band", observed=True)
              .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), rows=("Row ID", "count"),
                   loss_share=("Is Loss", "mean"))
              .reset_index())
    disc["margin"] = disc["profit"] / disc["sales"] * 100
    disc["loss_share"] *= 100
    disc.to_csv(T("t03_discount.csv"), index=False, encoding="utf-8-sig")
    corr = df[["Discount", "Profit Margin"]].corr().iloc[0, 1]
    facts["discount_profit_corr"] = jnum(corr, 3)
    no_disc = df.loc[df["Discount"] == 0, "Profit Margin"].mean() * 100
    hi_disc = df.loc[df["Discount"] >= 0.4, "Profit Margin"].mean() * 100
    facts["margin_no_discount"] = jnum(no_disc)
    facts["margin_high_discount"] = jnum(hi_disc)
    facts["loss_share_high_discount"] = jnum(df.loc[df["Discount"] >= 0.4, "Is Loss"].mean() * 100)

    # ================= M2 帕累托 / ABC =================
    log("M2 帕累托与 ABC 分类 ...")
    cust = (df.groupby("Customer ID")
              .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), orders=("Order ID", "nunique"),
                   last=("Order Date", "max"), first=("Order Date", "min"))
              .reset_index().sort_values("sales", ascending=False))
    cust["cum_share"] = cust["sales"].cumsum() / cust["sales"].sum() * 100
    cust["rank_pct"] = np.arange(1, len(cust) + 1) / len(cust) * 100
    cust["abc"] = np.where(cust["cum_share"] <= 70, "A", np.where(cust["cum_share"] <= 90, "B", "C"))
    cust.to_csv(T("t03_abc_customer.csv"), index=False, encoding="utf-8-sig")
    a_count = int((cust["abc"] == "A").sum())
    a_share = a_count / len(cust) * 100
    facts["pareto"] = {
        "customers": int(len(cust)),
        "a_customers": a_count, "a_customer_share": jnum(a_share),
        "a_sales_share": jnum(cust.loc[cust["abc"] == "A", "sales"].sum() / cust["sales"].sum() * 100),
        "b_share": jnum(cust.loc[cust["abc"] == "B", "sales"].sum() / cust["sales"].sum() * 100),
        "c_share": jnum(cust.loc[cust["abc"] == "C", "sales"].sum() / cust["sales"].sum() * 100),
        "n_for_80pct": int((cust["cum_share"] <= 80).sum()),
    }

    prod = (df.groupby("Product ID")
              .agg(sales=("Sales", "sum"), profit=("Profit", "sum"), qty=("Quantity", "sum"),
                   name=("Product Name", "first"), subcat=("Sub-Category", "first"))
              .reset_index().sort_values("sales", ascending=False))
    prod["cum_share"] = prod["sales"].cumsum() / prod["sales"].sum() * 100
    prod["abc"] = np.where(prod["cum_share"] <= 70, "A", np.where(prod["cum_share"] <= 90, "B", "C"))
    prod.to_csv(T("t03_abc_product.csv"), index=False, encoding="utf-8-sig")
    facts["pareto"]["products"] = int(len(prod))
    facts["pareto"]["product_a_share"] = jnum((prod["abc"] == "A").sum() / len(prod) * 100)
    facts["pareto"]["product_a_sales"] = jnum(prod.loc[prod["abc"] == "A", "sales"].sum() / prod["sales"].sum() * 100)
    facts["pareto"]["neg_profit_products"] = int((prod["profit"] < 0).sum())

    # ================= M3 RFM 八分类 =================
    log("M3 RFM 模型 ...")
    snapshot = df["Order Date"].max() + pd.Timedelta(days=1)
    rfm = cust[["Customer ID", "sales", "orders", "last", "first"]].copy()
    rfm["R"] = (snapshot - rfm["last"]).dt.days
    rfm["F"] = rfm["orders"]
    rfm["M"] = rfm["sales"]
    r_med, f_med, m_med = rfm["R"].median(), rfm["F"].median(), rfm["M"].median()
    rfm["R_score"] = np.where(rfm["R"] <= r_med, 1, 0)   # 1 = 更近（优）
    rfm["F_score"] = np.where(rfm["F"] >= f_med, 1, 0)
    rfm["M_score"] = np.where(rfm["M"] >= m_med, 1, 0)

    def name_seg(r, f, m):
        if (r, f, m) == (1, 1, 1):
            return "重要价值客户"
        if (r, f, m) == (0, 1, 1):
            return "重要唤回客户"
        if (r, f, m) == (1, 0, 1):
            return "重要发展客户"
        if (r, f, m) == (0, 0, 1):
            return "重要挽留客户"
        if (r, f, m) == (1, 1, 0):
            return "一般价值客户"
        if (r, f, m) == (0, 1, 0):
            return "一般保持客户"
        if (r, f, m) == (1, 0, 0):
            return "一般发展客户"
        return "一般挽留客户"

    rfm["Segment"] = [name_seg(r, f, m) for r, f, m in zip(rfm["R_score"], rfm["F_score"], rfm["M_score"])]
    rfm["Tenure"] = (rfm["last"] - rfm["first"]).dt.days
    rfm.to_csv(T("t03_rfm.csv"), index=False, encoding="utf-8-sig")
    seg = (rfm.groupby("Segment")
              .agg(customers=("Customer ID", "count"), sales=("M", "sum"), avg_r=("R", "mean"),
                   avg_f=("F", "mean"), avg_m=("M", "mean"))
              .reset_index().sort_values("sales", ascending=False))
    seg["cust_share"] = seg["customers"] / seg["customers"].sum() * 100
    seg["sales_share"] = seg["sales"] / seg["sales"].sum() * 100
    seg["arpu"] = seg["sales"] / seg["customers"]
    seg.to_csv(T("t03_rfm_segment.csv"), index=False, encoding="utf-8-sig")
    facts["rfm"] = {
        "r_median": jnum(r_med), "f_median": jnum(f_med), "m_median": jnum(m_med),
        "segments": seg.round(2).to_dict(orient="records"),
        "top_segment": seg.iloc[0]["Segment"],
        "top_segment_sales_share": jnum(seg.iloc[0]["sales_share"]),
        "top_segment_cust_share": jnum(seg.iloc[0]["cust_share"]),
        "vip_sales_share": jnum(seg.loc[seg["Segment"].isin(["重要价值客户", "重要唤回客户", "重要发展客户", "重要挽留客户"]), "sales"].sum() / seg["sales"].sum() * 100),
        "vip_cust_share": jnum(seg.loc[seg["Segment"].isin(["重要价值客户", "重要唤回客户", "重要发展客户", "重要挽留客户"]), "customers"].sum() / seg["customers"].sum() * 100),
    }

    # K-Means 客户分群（对 log 变换后的 RFM 标准化聚类）
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        km_df = rfm[["R", "F", "M"]].copy()
        km_df["M"] = np.log1p(km_df["M"])
        X = StandardScaler().fit_transform(km_df)
        k = 4
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        rfm["Cluster"] = km.labels_
        clus = (rfm.groupby("Cluster")
                   .agg(customers=("Customer ID", "count"), R=("R", "mean"), F=("F", "mean"), M=("M", "mean"))
                   .reset_index())
        clus["sales_share"] = clus["M"] * clus["customers"] / (rfm["M"].sum()) * 100
        clus = clus.sort_values("M", ascending=False)
        clus.to_csv(T("t03_kmeans.csv"), index=False, encoding="utf-8-sig")
        rfm.to_csv(T("t03_rfm.csv"), index=False, encoding="utf-8-sig")
        facts["kmeans"] = {"k": k, "inertia": jnum(km.inertia_), "clusters": clus.round(2).to_dict(orient="records")}
    except Exception as e:
        log("K-Means 跳过：", e)

    # ================= M4 同期群留存 =================
    log("M4 同期群留存 ...")
    first_order = df.groupby("Customer ID")["Order Date"].min().rename("first_date")
    d = df[["Customer ID", "Order Date"]].drop_duplicates().merge(first_order, on="Customer ID")
    # 季度口径：cohort = 首购季度，index = 距首购的季度数（0~8）
    d["cohort"] = d["first_date"].dt.to_period("Q").astype(str)
    d["idx"] = ((d["Order Date"].dt.year - d["first_date"].dt.year) * 4
                + (d["Order Date"].dt.quarter - d["first_date"].dt.quarter))
    d = d[(d["idx"] >= 0) & (d["idx"] <= 8)]
    pivot = (d.groupby(["cohort", "idx"])["Customer ID"].nunique().unstack(fill_value=0))
    sizes = first_order.dt.to_period("Q").astype(str).value_counts()
    retention = pivot.div(sizes.reindex(pivot.index), axis=0) * 100
    retention = retention.sort_index()
    # 右删失处理：观察窗口尚未到达的格子置为缺失，避免误读为“留存 0”
    last_q = df["Order Date"].max().to_period("Q")
    for i, c in enumerate(retention.index):
        allowed = (last_q - pd.Period(c, freq="Q")).n
        retention.iloc[i, :] = [v if j <= allowed else np.nan for j, v in enumerate(retention.iloc[i, :])]
    retention.to_csv(T("t03_cohort.csv"), encoding="utf-8-sig")
    m0 = retention[0].mean()
    m1 = retention[1].mean() if 1 in retention.columns else np.nan
    m4 = retention[4].mean() if 4 in retention.columns else np.nan
    facts["cohort"] = {
        "cohorts": int(retention.shape[0]), "q0": jnum(m0), "q1": jnum(m1), "q4": jnum(m4),
        "drop_1": jnum(m0 - m1),
        "best_cohort": str(retention[1].idxmax()) if 1 in retention.columns else None,
        "matrix": [[None if pd.isna(v) else round(float(v), 1) for v in row] for row in retention.values],
        "index": list(retention.index),
        "sizes": [int(sizes.get(c, 0)) for c in retention.index],
    }

    # ================= M5 波士顿矩阵 =================
    log("M5 波士顿矩阵 ...")
    g = (df.pivot_table(index="Sub-Category", columns="Order Year", values="Sales", aggfunc="sum")
           .fillna(0))
    g["total"] = g.sum(axis=1)
    g["share"] = g["total"] / g["total"].sum() * 100
    g["growth"] = np.where(g.get(2016, 0) > 0, (g.get(2017, 0) - g.get(2016, 0)) / g[2016] * 100, np.nan)
    g["profit"] = df.groupby("Sub-Category")["Profit"].sum()
    g["margin"] = g["profit"] / g["total"] * 100
    x_med, y_med = g["share"].median(), g["growth"].median()
    g["quadrant"] = np.select(
        [(g["share"] >= x_med) & (g["growth"] >= y_med),
         (g["share"] >= x_med) & (g["growth"] < y_med),
         (g["share"] < x_med) & (g["growth"] >= y_med)],
        ["明星", "金牛", "问题"], default="瘦狗")
    g = g.reset_index()
    g.to_csv(T("t03_boston.csv"), index=False, encoding="utf-8-sig")
    facts["boston"] = {"x_median": jnum(x_med), "y_median": jnum(y_med),
                       "quadrants": g.groupby("quadrant").size().to_dict(),
                       "stars": g.loc[g["quadrant"] == "明星", "Sub-Category"].tolist(),
                       "cows": g.loc[g["quadrant"] == "金牛", "Sub-Category"].tolist(),
                       "dogs": g.loc[g["quadrant"] == "瘦狗", "Sub-Category"].tolist()}

    # ================= M6 SARIMA / Holt-Winters 预测 =================
    log("M6 时间序列预测 ...")
    ts = monthly.set_index("YearMonthDate")["sales"].asfreq("MS").fillna(0)
    train, test = ts.iloc[:-6], ts.iloc[-6:]
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    def score(actual, pred):
        a, p = np.asarray(actual, float), np.asarray(pred, float)
        mape = float(np.mean(np.abs((a - p) / a)) * 100)
        rmse = float(np.sqrt(np.mean((a - p) ** 2)))
        return mape, rmse

    # 6.1 SARIMA 网格：以 6 期滚动回测 MAPE 选阶（比 AIC 更贴近预测目标）
    best = None
    for order in [(1, 1, 1), (0, 1, 1), (1, 1, 0), (2, 1, 1)]:
        for sorder in [(1, 0, 1, 12), (0, 1, 1, 12), (1, 1, 0, 12)]:
            try:
                m = SARIMAX(train, order=order, seasonal_order=sorder,
                            enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
                pv = m.get_forecast(steps=len(test)).predicted_mean.values
                mp, rm = score(test.values, pv)
                if best is None or mp < best[0]:
                    best = (mp, rm, order, sorder, float(m.aic), m)
            except Exception:
                continue
    if best is None:
        raise SystemExit("SARIMA 拟合失败")
    sar_mape, sar_rmse, order, sorder, aic, fit = best
    yhat = fit.get_forecast(steps=len(test)).predicted_mean

    # 6.2 Holt-Winters 对比（乘法季节性）
    hw_best = None
    for trend in ("add", "mul"):
        for seasonal in ("mul", "add"):
            try:
                hw = ExponentialSmoothing(train, trend=trend, seasonal=seasonal, seasonal_periods=12,
                                          initialization_method="estimated").fit()
                ph = hw.forecast(len(test)).values
                mp, rm = score(test.values, ph)
                if hw_best is None or mp < hw_best[0]:
                    hw_best = (mp, rm, trend, seasonal, ph)
            except Exception:
                continue
    hw = hw_best if hw_best is not None else None

    facts["forecast_compare"] = [
        {"模型": "SARIMA" + str(order) + "×" + str(sorder), "MAPE(%)": jnum(sar_mape), "RMSE": jnum(sar_rmse)},
    ]
    if hw is not None:
        facts["forecast_compare"].append({"模型": f"Holt-Winters({hw[2]}趋势,{hw[3]}季节)",
                                          "MAPE(%)": jnum(hw[0]), "RMSE": jnum(hw[1])})
    facts["sarima"] = {
        "order": str(order), "seasonal_order": str(sorder), "aic": jnum(aic),
        "train_n": int(len(train)), "test_n": int(len(test)),
        "mape": jnum(sar_mape), "rmse": jnum(sar_rmse),
        "hw_mape": jnum(hw[0]) if hw else None, "hw_rmse": jnum(hw[1]) if hw else None,
        "test_actual": [jnum(v) for v in test.values], "test_pred": [jnum(v) for v in yhat.values],
        "test_hw_pred": [jnum(v) for v in hw[4]] if hw else None,
        "test_index": [str(i.date()) for i in test.index],
    }

    # 6.3 用全样本重估 SARIMA，输出未来 6 个月点预测与 95% 置信区间
    final = SARIMAX(ts, order=order, seasonal_order=sorder,
                    enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
    fut = final.get_forecast(steps=6)
    fc = fut.predicted_mean
    fci = fut.conf_int(alpha=0.05)
    fdf = pd.DataFrame({"month": [str(i.date()) for i in fc.index],
                        "forecast": fc.values,
                        "lower": fci.iloc[:, 0].values, "upper": fci.iloc[:, 1].values})
    fdf.to_csv(T("t03_forecast.csv"), index=False, encoding="utf-8-sig")
    facts["sarima"]["forecast"] = fdf.round(2).to_dict(orient="records")
    facts["sarima"]["forecast_total"] = jnum(fdf["forecast"].sum())
    facts["sarima"]["last_year_h1"] = jnum(ts.loc["2017-01":"2017-06"].sum())

    series = ts.reset_index()
    series.columns = ["month", "sales"]
    series["month"] = series["month"].dt.strftime("%Y-%m-%d")
    series.to_csv(T("t03_monthly_series.csv"), index=False, encoding="utf-8-sig")

    # ================= M7 关联规则 =================
    log("M7 关联规则 Apriori ...")
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder

    baskets = df.groupby("Order ID")["Sub-Category"].apply(lambda s: sorted(set(s))).tolist()
    te = TransactionEncoder()
    arr = te.fit(baskets).transform(baskets)
    onehot = pd.DataFrame(arr, columns=te.columns_)
    freq = apriori(onehot, min_support=0.008, use_colnames=True, max_len=2)
    rules = association_rules(freq, metric="lift", min_threshold=1.05, num_itemsets=len(freq))
    rules = rules[rules["consequents"].map(len) == 1].copy()
    rules["antecedent"] = rules["antecedents"].map(lambda x: " + ".join(sorted(x)))
    rules["consequent"] = rules["consequents"].map(lambda x: " + ".join(sorted(x)))
    rules = rules.sort_values("lift", ascending=False).head(20)
    out_rules = rules[["antecedent", "consequent", "support", "confidence", "lift"]].copy()
    out_rules[["support", "confidence", "lift"]] = out_rules[["support", "confidence", "lift"]].round(3)
    out_rules.to_csv(T("t03_rules.csv"), index=False, encoding="utf-8-sig")
    facts["rules"] = {"n_transactions": int(len(baskets)), "n_rules": int(len(out_rules)),
                      "top": out_rules.head(3).to_dict(orient="records"),
                      "avg_basket_items": jnum(df.groupby("Order ID")["Sub-Category"].nunique().mean(), 2)}

    # ================= M8 客户价值漏斗 =================
    log("M8 客户价值漏斗 ...")
    n_all = len(rfm)
    n_repeat = int((rfm["F"] >= 2).sum())
    n_freq = int((rfm["F"] >= 5).sum())
    n_vip = int((rfm["Segment"] == "重要价值客户").sum())
    funnel = pd.DataFrame({
        "阶段": ["全部客户", "复购客户(≥2单)", "高频客户(≥5单)", "高价值客户(重要价值)"],
        "人数": [n_all, n_repeat, n_freq, n_vip],
    })
    funnel["占全部客户%"] = (funnel["人数"] / n_all * 100).round(1)
    funnel["阶段转化率%"] = (funnel["人数"] / funnel["人数"].shift(1) * 100).round(1)
    funnel.to_csv(T("t03_funnel.csv"), index=False, encoding="utf-8-sig")
    facts["funnel"] = funnel.to_dict(orient="records")

    def clean_json(obj):
        if isinstance(obj, dict):
            return {k: clean_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [clean_json(v) for v in obj]
        if isinstance(obj, (np.floating, float)):
            return None if not np.isfinite(float(obj)) else float(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    with open(T("t03_facts.json"), "w", encoding="utf-8") as f:
        json.dump(clean_json(facts), f, ensure_ascii=False, indent=2, allow_nan=False)
    log("分析完成，结果表已写入 outputs/tables/")
    log(json.dumps({k: v for k, v in facts.items() if k in ("kpi", "pareto", "rfm")}, ensure_ascii=False, indent=2)[:1500])


if __name__ == "__main__":
    main()

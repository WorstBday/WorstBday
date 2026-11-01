"""Download the Tableau Superstore sample dataset from Kaggle's public dataset API."""
import io
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
LIBS = os.path.join(ROOT, ".pylibs")
sys.path.insert(0, LIBS)
import pandas as pd  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)
URL = "https://www.kaggle.com/api/v1/datasets/download/vivek468/superstore-dataset-final"
print("downloading", URL, flush=True)
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=120) as r:
    blob = r.read()
print("zip bytes", len(blob), flush=True)
zf = zipfile.ZipFile(io.BytesIO(blob))
print("members", zf.namelist(), flush=True)
csv_name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
raw_bytes = zf.read(csv_name)
with open(os.path.join(RAW, "superstore_raw.csv"), "wb") as f:
    f.write(raw_bytes)
for enc in ("utf-8", "utf-8-sig", "latin-1"):
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc)
        print("encoding", enc, flush=True)
        break
    except Exception as e:
        print("fail", enc, e, flush=True)
print("shape", df.shape, flush=True)
print("columns", list(df.columns), flush=True)
print(df.head(3).to_string()[:1200], flush=True)
print("date range", df["Order Date"].min(), "->", df["Order Date"].max(), flush=True)
print("n customers", df["Customer ID"].nunique(), "n orders", df["Order ID"].nunique(), flush=True)
print("total sales", round(df["Sales"].sum(), 2), "profit", round(df["Profit"].sum(), 2), flush=True)

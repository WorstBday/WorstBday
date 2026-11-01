"""run_all.py —— 一键复现入口

依次执行：加载 → 清洗 → 建模 → 出图 → 大屏，任一步失败即中断并返回非零退出码。
用法：python run_all.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("01_load.py", "加载原始数据并统一编码/类型"),
    ("02_clean.py", "清洗治理、派生指标、拆分多表并导出 CSV/JSON/SQLite"),
    ("03_analysis.py", "运行 8 个商业分析模型并输出结果表"),
    ("04_visuals.py", "生成 24 张图表"),
    ("05_dashboard.py", "生成自包含交互式大屏 HTML"),
]


def main() -> int:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    start = time.time()
    for i, (script, desc) in enumerate(STEPS, 1):
        path = os.path.join(ROOT, "scripts", script)
        print(f"\n[{i}/{len(STEPS)}] {script} —— {desc}", flush=True)
        t0 = time.time()
        rc = subprocess.call([sys.executable, path], cwd=ROOT, env=env)
        if rc != 0:
            print(f"!! {script} 执行失败（退出码 {rc}），流程中断", flush=True)
            return rc
        print(f"   完成，用时 {time.time() - t0:.1f}s", flush=True)
    print(f"\n全部完成，总用时 {time.time() - start:.1f}s", flush=True)
    print("产物：data/clean/、outputs/tables/、outputs/figures/、outputs/dashboard/", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

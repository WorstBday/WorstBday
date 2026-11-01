"""common.py —— 公共路径、日志、中文字体与配色。

所有脚本共用，保证图表风格统一。
"""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# matplotlib 缓存放到工作区，避免受限环境无法写入用户目录
os.environ.setdefault("MPLCONFIGDIR", os.path.join(ROOT, ".mplconfig"))

import matplotlib

matplotlib.use("Agg")  # 无界面后端，保证服务器/CI 环境也能出图
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
CLEAN = os.path.join(ROOT, "data", "clean")
FIG = os.path.join(ROOT, "outputs", "figures")
TABLES = os.path.join(ROOT, "outputs", "tables")
DASH = os.path.join(ROOT, "outputs", "dashboard")
ASSETS = os.path.join(ROOT, "assets")

# 统一配色（参照《Excel数据可视化》常用商务蓝橙系）
COLORS = {
    "primary": "#2E5C8A",
    "secondary": "#E8873A",
    "third": "#4C9A6A",
    "fourth": "#B5483A",
    "gray": "#8C8C8C",
    "light": "#D9E2EC",
    "dark": "#1F3A5F",
}
PALETTE = ["#2E5C8A", "#E8873A", "#4C9A6A", "#B5483A", "#7B6AA8",
           "#D9A441", "#4AA3C7", "#9E9E9E", "#6D8B4E", "#C77BA0"]


def log(*args, **kwargs) -> None:
    print(*args, **kwargs, flush=True)


def ensure_dirs() -> None:
    for d in (RAW, CLEAN, FIG, TABLES, DASH):
        os.makedirs(d, exist_ok=True)


def setup_chinese_font() -> str:
    """注册 Windows 自带中文字体，避免中文显示为方块。"""
    candidates = [
        (r"C:\Windows\Fonts\msyh.ttc", "Microsoft YaHei"),
        (r"C:\Windows\Fonts\msyhbd.ttc", "Microsoft YaHei"),
        (r"C:\Windows\Fonts\simhei.ttf", "SimHei"),
        (r"C:\Windows\Fonts\simsun.ttc", "SimSun"),
    ]
    family = None
    for path, name in candidates:
        if os.path.exists(path):
            try:
                font_manager.fontManager.addfont(path)
                family = family or name
            except Exception:
                continue
    if family is None:
        family = "DejaVu Sans"
    plt.rcParams["font.sans-serif"] = [family, "Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False   # 负号正常显示
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["savefig.dpi"] = 150            # 规范要求 ≥150dpi
    plt.rcParams["axes.edgecolor"] = "#B0B7BF"
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["xtick.color"] = "#404040"
    plt.rcParams["ytick.color"] = "#404040"
    return family


def save_fig(fig, name: str, tight: bool = True) -> str:
    """按 figNN_中文名.png 统一命名并保存。"""
    path = os.path.join(FIG, name)
    if tight:
        fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log(f"  图已保存：{name}")
    return path


def style_axes(ax, grid_axis: str = "y") -> None:
    """统一坐标轴样式：去掉上/右边框，保留浅色网格。"""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(True, axis=grid_axis, color="#E5E9EE", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

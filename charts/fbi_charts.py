"""
Charts for the FBI Intelligence page, in one quiet house style:
Inter type, no top/right frame, faint horizontal grid only, direct
line labels instead of legends where possible, and a source line on
every figure so an exported chart is self-explanatory.
"""

import textwrap
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

from core.fbi_metrics import fmt_rupees, pretty_name

FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"
for f in FONT_DIR.glob("*.otf"):
    font_manager.fontManager.addfont(str(f))

INK = "#1B2533"
MUTED = "#6B7480"
FAINT = "#9AA3AE"
GRID = "#ECEFF2"
COLOR_A = "#1F4E79"   # navy
COLOR_B = "#C08A2E"   # ochre
COLOR_BENCH = "#A3ABB5"
SERIES_COLORS = [COLOR_A, COLOR_B]

QUILT_COLORS = [
    "#A9C5E6", "#F1C892", "#B9D9B1", "#E7B0AE",
    "#CBBDE2", "#A3D5D0", "#E8DC97",
]
QUILT_BENCH = "#DADFE5"

plt.rcParams.update({
    "font.family": "Inter",
    "font.size": 10,
    "text.color": INK,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": "#D5DAE0",
    "axes.titlesize": 11,
    "svg.fonttype": "none",
})


def _base(figsize=(10, 4.2)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="both", length=0, labelsize=9.5, pad=6)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    return fig, ax


def _source(fig, as_of):
    fig.text(
        0.0, -0.02,
        f"Source: NSE Indices via FinAPI. Total return indices, INR. "
        f"Data to {as_of:%d %b %Y}. PRISM.",
        fontsize=8, color=FAINT, ha="left", va="top",
    )


def _pct_axis(ax, decimals=0):
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:.{decimals}f}%".replace("-", "−"))
    )


def _date_axis(ax, span_days):
    if span_days > 365 * 6:
        ax.xaxis.set_major_locator(mdates.YearLocator(base=2 if span_days < 365 * 14 else 4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    elif span_days > 365 * 2:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def _end_labels(ax, series_list, fmt):
    """Label each line at its right end, nudged apart so none overlap."""
    ends = [(s.dropna().index[-1], s.dropna().iloc[-1], label, color)
            for s, label, color in series_list]
    lo, hi = ax.get_ylim()
    min_gap = (hi - lo) * 0.075
    ends.sort(key=lambda e: e[1])
    placed = []
    for x, y, label, color in ends:
        y_text = y if not placed else max(y, placed[-1] + min_gap)
        placed.append(y_text)
        ax.annotate(
            f"{label}  {fmt(y)}", xy=(x, y_text), xytext=(8, 0),
            textcoords="offset points", va="center", fontsize=9,
            color=color, fontweight="medium",
            annotation_clip=False,
        )


def _series_style(i, is_bench):
    if is_bench:
        return dict(color=COLOR_BENCH, linewidth=1.4)
    return dict(color=SERIES_COLORS[i], linewidth=2)


# ---------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------

def growth_chart(window, names, benchmark, as_of, start_value=1e5):
    growth = window / window.iloc[0] * start_value
    fig, ax = _base()
    series_list = []
    i = 0
    for n in names:
        is_bench = n == benchmark
        ax.plot(growth.index, growth[n], **_series_style(i, is_bench),
                zorder=2 if is_bench else 3)
        color = COLOR_BENCH if is_bench else SERIES_COLORS[i]
        series_list.append((growth[n], pretty_name(n), color))
        if not is_bench:
            i += 1
    ax.axhline(start_value, color="#D5DAE0", linewidth=1, zorder=1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: fmt_rupees(v)))
    _date_axis(ax, (growth.index[-1] - growth.index[0]).days)
    ax.margins(x=0)
    _end_labels(ax, series_list, fmt_rupees)
    _source(fig, as_of)
    fig.tight_layout()
    fig.subplots_adjust(right=0.74)
    return fig


# ---------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------

def rolling_chart(rolling, names, benchmark, as_of):
    fig, ax = _base()
    i = 0
    series_list = []
    for n in names:
        is_bench = n == benchmark
        s = rolling[n].dropna()
        ax.plot(s.index, s, **_series_style(i, is_bench),
                zorder=2 if is_bench else 3)
        color = COLOR_BENCH if is_bench else SERIES_COLORS[i]
        series_list.append((s, pretty_name(n), color))
        if not is_bench:
            i += 1
    ax.axhline(0, color="#C4CBD3", linewidth=1)
    _pct_axis(ax)
    _date_axis(ax, (rolling.index[-1] - rolling.index[0]).days)
    ax.margins(x=0)
    _end_labels(ax, series_list, lambda v: f"{v:.0f}%".replace("-", "−"))
    _source(fig, as_of)
    fig.tight_layout()
    fig.subplots_adjust(right=0.76)
    return fig


def calendar_chart(cal, names, benchmark, partial_year, as_of):
    years = list(cal.index)
    x = np.arange(len(years))
    k = len(names)
    width = 0.8 / k
    fig, ax = _base(figsize=(10, 3.8))
    i = 0
    handles = []
    for j, n in enumerate(names):
        is_bench = n == benchmark
        color = COLOR_BENCH if is_bench else SERIES_COLORS[i]
        h = ax.bar(x - 0.4 + width * (j + 0.5), cal[n].values, width * 0.9,
                   color=color, label=pretty_name(n), zorder=3)
        handles.append(h)
        if partial_year in years:
            h.patches[years.index(partial_year)].set_alpha(0.45)
        if not is_bench:
            i += 1
    ax.axhline(0, color="#C4CBD3", linewidth=1, zorder=2)
    labels = [f"{y}\nYTD" if y == partial_year else str(y) for y in years]
    ax.set_xticks(x, labels)
    _pct_axis(ax)
    ax.legend(frameon=False, ncol=k, loc="lower left",
              bbox_to_anchor=(0, 1.0), fontsize=9, handlelength=1,
              handleheight=1, labelcolor=INK)
    _source(fig, as_of)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------

def drawdown_chart(window, names, benchmark, as_of):
    fig, ax = _base(figsize=(10, 3.8))
    i = 0
    for n in names:
        s = window[n].dropna()
        dd = (s / s.cummax() - 1) * 100
        if n == benchmark:
            ax.plot(dd.index, dd, color=COLOR_BENCH, linewidth=1.3,
                    label=pretty_name(n), zorder=2)
        else:
            c = SERIES_COLORS[i]
            ax.plot(dd.index, dd, color=c, linewidth=1.6,
                    label=pretty_name(n), zorder=3)
            i += 1
    ax.axhline(0, color="#C4CBD3", linewidth=1)
    _pct_axis(ax)
    _date_axis(ax, (window.index[-1] - window.index[0]).days)
    ax.margins(x=0)
    ax.legend(frameon=False, ncol=len(names), loc="lower left",
              bbox_to_anchor=(0, 1.0), fontsize=9, labelcolor=INK)
    _source(fig, as_of)
    fig.tight_layout()
    return fig


def capture_chart(points, benchmark, as_of):
    """points: list of (name, downside, upside, color)."""
    fig, ax = _base(figsize=(10, 4.4))
    ax.spines["left"].set_visible(False)
    ax.grid(axis="both", color=GRID)
    xs = [p[1] for p in points] + [100]
    ys = [p[2] for p in points] + [100]
    pad_x = max(15, (max(xs) - min(xs)) * 0.35)
    pad_y = max(15, (max(ys) - min(ys)) * 0.35)
    ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    ax.fill_between([x0, 100], 100, y1, color="#EEF4EA", zorder=0)
    ax.axvline(100, color="#C4CBD3", linewidth=1, zorder=1)
    ax.axhline(100, color="#C4CBD3", linewidth=1, zorder=1)
    ax.text(x0 + (100 - x0) * 0.04, y1 - (y1 - y0) * 0.06,
            "Gains more, loses less", fontsize=9, color="#5B7A4E", va="top")
    ax.scatter([100], [100], s=70, color=COLOR_BENCH, zorder=3)
    ax.annotate(pretty_name(benchmark), (100, 100), xytext=(8, -12),
                textcoords="offset points", fontsize=9, color=MUTED)
    for name, down, up, color in points:
        ax.scatter([down], [up], s=110, color=color, zorder=4)
        ax.annotate(pretty_name(name), (down, up), xytext=(10, 4),
                    textcoords="offset points", fontsize=9.5,
                    color=color, fontweight="medium")
    ax.set_xlabel("Downside capture (lower is better)", fontsize=9)
    ax.set_ylabel("Upside capture (higher is better)", fontsize=9)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    _source(fig, as_of)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------
# Market map
# ---------------------------------------------------------------------

def risk_return_chart(points, benchmark, highlight, label_names, as_of):
    """points: DataFrame index=name, cols Return, Volatility."""
    fig, ax = _base(figsize=(10, 5.2))
    ax.grid(axis="both", color=GRID)
    b = points.loc[benchmark]
    others = points.drop(index=[benchmark] + [h for h in highlight if h in points.index])
    ax.scatter(others["Volatility"], others["Return"], s=34,
               color="#B9C1CB", zorder=3, linewidths=0)
    ax.axvline(b["Volatility"], color="#C4CBD3", linewidth=1, zorder=1)
    ax.axhline(b["Return"], color="#C4CBD3", linewidth=1, zorder=1)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    ax.fill_between([x0, b["Volatility"]], b["Return"], y1, color="#EEF4EA", zorder=0)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.text(x0 + (x1 - x0) * 0.01, y1 - (y1 - y0) * 0.03,
            f"More return, less risk than {pretty_name(benchmark)}",
            fontsize=8.5, color="#5B7A4E", va="top")
    ax.scatter([b["Volatility"]], [b["Return"]], s=80, color="#6B7480",
               marker="D", zorder=4)
    ax.annotate(pretty_name(benchmark), (b["Volatility"], b["Return"]),
                xytext=(8, -12), textcoords="offset points",
                fontsize=9, color=MUTED, fontweight="medium")
    for i, h in enumerate(highlight):
        if h in points.index and h != benchmark:
            p = points.loc[h]
            ax.scatter([p["Volatility"]], [p["Return"]], s=90,
                       color=SERIES_COLORS[i], zorder=5)
            ax.annotate(pretty_name(h), (p["Volatility"], p["Return"]),
                        xytext=(8, 5), textcoords="offset points",
                        fontsize=9.5, color=SERIES_COLORS[i],
                        fontweight="medium")
    xr = points["Volatility"].max() - points["Volatility"].min()
    yr = points["Return"].max() - points["Return"].min()
    taken = [points.loc[h] for h in list(highlight) + [benchmark] if h in points.index]
    for n in label_names:
        if n in points.index and n not in highlight and n != benchmark:
            p = points.loc[n]
            if any(abs(p["Volatility"] - t["Volatility"]) < xr * 0.12
                   and abs(p["Return"] - t["Return"]) < yr * 0.06 for t in taken):
                continue
            taken.append(p)
            ax.annotate(pretty_name(n), (p["Volatility"], p["Return"]),
                        xytext=(6, 4), textcoords="offset points",
                        fontsize=8.5, color=MUTED)
    ax.set_xlabel("Volatility, annualised", fontsize=9)
    ax.set_ylabel("Return, annualised", fontsize=9)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_locator(mticker.MaxNLocator(steps=[1, 2, 5, 10]))
    _pct_axis(ax)
    _source(fig, as_of)
    fig.tight_layout()
    return fig


def quilt_chart(quilt_df, color_map, partial_year, as_of):
    n_ranks, n_years = quilt_df.shape
    years = list(quilt_df.columns)
    fig_w = max(10, n_years * 1.05)
    fig_h = n_ranks * 0.78 + 0.7
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor("white")
    ax.set_xlim(-0.35, n_years)
    ax.set_ylim(0, n_ranks + 0.55)
    ax.axis("off")
    gap = 0.045
    for j, year in enumerate(years):
        label = f"{year} YTD" if year == partial_year else str(year)
        ax.text(j + 0.5, n_ranks + 0.27, label, ha="center", va="center",
                fontsize=9.5, fontweight="semibold",
                color=MUTED if year == partial_year else INK)
        for i in range(n_ranks):
            cell = quilt_df.iloc[i, j]
            y = n_ranks - i - 1
            if cell is None:
                continue
            name, ret = cell
            color = color_map.get(name, QUILT_BENCH)
            box = FancyBboxPatch(
                (j + gap, y + gap), 1 - 2 * gap, 1 - 2 * gap,
                boxstyle="round,pad=0,rounding_size=0.06",
                facecolor=color, edgecolor="none",
                alpha=0.55 if year == partial_year else 1,
            )
            ax.add_patch(box)
            full = pretty_name(name)
            rest = full.split(" ", 1)
            label = rest[1] if (rest[0].startswith("Nifty") and len(rest) > 1
                                and len(rest[1].split()) >= 2) else full
            short = textwrap.fill(label, 14)
            ax.text(j + 0.5, y + 0.62, short, ha="center", va="center",
                    fontsize=7.4, color=INK, linespacing=1.05)
            ax.text(j + 0.5, y + 0.24, f"{ret:.1f}%".replace("-", "−"),
                    ha="center", va="center", fontsize=9,
                    fontweight="semibold", color=INK)
    for i in range(n_ranks):
        ax.text(-0.17, n_ranks - i - 0.5, str(i + 1), ha="center",
                va="center", fontsize=9, color=FAINT)
    _source(fig, as_of)
    fig.tight_layout()
    return fig

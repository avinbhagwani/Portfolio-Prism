"""
Charts for the FBI Intelligence (factor index comparison) and Drawdown
Analysis tools. Every chart uses charts.theme.INDEX_COLORS so the same
index keeps the same colour across every chart it appears in.
"""

import numpy as np
import matplotlib.pyplot as plt

from charts.theme import apply_chart_theme, INDEX_COLORS


def make_annual_returns_chart(annual_df):
    """Grouped bar chart of calendar-year returns, one colour per index."""
    fig, ax = plt.subplots(figsize=(12, 5))

    years = annual_df.index.tolist()
    n_series = len(annual_df.columns)
    bar_width = 0.8 / max(n_series, 1)
    x = np.arange(len(years))

    for i, col in enumerate(annual_df.columns):
        offset = (i - (n_series - 1) / 2) * bar_width
        ax.bar(
            x + offset,
            annual_df[col].values,
            width=bar_width,
            label=col,
            color=INDEX_COLORS[i % len(INDEX_COLORS)]
        )

    ax.axhline(0, color="#888888", linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.set_ylabel("Annual Return (%)")
    ax.set_title("Calendar-Year Returns", fontsize=16, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.legend(frameon=False)

    apply_chart_theme(fig, ax)
    fig.tight_layout()
    return fig


def make_rolling_returns_chart(rolling_df, window_years):
    """Line chart of rolling annualised returns, one colour per index."""
    fig, ax = plt.subplots(figsize=(12, 5))

    for i, col in enumerate(rolling_df.columns):
        series = rolling_df[col].dropna()
        ax.plot(
            series.index,
            series.values,
            linewidth=2,
            label=col,
            color=INDEX_COLORS[i % len(INDEX_COLORS)]
        )

    ax.axhline(0, color="#888888", linestyle="--", linewidth=1)

    window_label = (
        f"{window_years} Year" if window_years != 1 else "1 Year"
    )
    ax.set_title(
        f"Rolling {window_label} Annualised Return",
        fontsize=16,
        fontweight="bold"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Annualised Return (%)")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.legend(frameon=False)

    apply_chart_theme(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def make_drawdown_chart(drawdown_df):
    """Filled line chart of drawdown from peak, one colour per index."""
    fig, ax = plt.subplots(figsize=(12, 5))

    for i, col in enumerate(drawdown_df.columns):
        series = drawdown_df[col].dropna()
        color = INDEX_COLORS[i % len(INDEX_COLORS)]

        ax.plot(series.index, series.values, linewidth=1.5, label=col, color=color)
        ax.fill_between(series.index, series.values, 0, color=color, alpha=0.15)

    ax.axhline(0, color="#888888", linestyle="--", linewidth=1)
    ax.set_title("Drawdown From Peak", fontsize=16, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.legend(frameon=False)

    apply_chart_theme(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def make_rolling_std_chart(rolling_std_df, window_years):
    """Line chart of rolling annualised volatility, one colour per index."""
    fig, ax = plt.subplots(figsize=(12, 5))

    for i, col in enumerate(rolling_std_df.columns):
        series = rolling_std_df[col].dropna()
        ax.plot(
            series.index,
            series.values,
            linewidth=2,
            label=col,
            color=INDEX_COLORS[i % len(INDEX_COLORS)]
        )

    window_label = (
        f"{window_years} Year" if window_years != 1 else "1 Year"
    )
    ax.set_title(
        f"Rolling {window_label} Annualised Volatility",
        fontsize=16,
        fontweight="bold"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Annualised Volatility (%)")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.legend(frameon=False)

    apply_chart_theme(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def make_capture_ratio_chart(capture_df):
    """
    Grouped bar chart of Upside vs Downside capture ratio per index,
    with a dashed reference line at 100% (matched the benchmark
    exactly). Upside is green-toned, Downside is red-toned — fixed
    colours since this chart compares metric types, not indices.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    names = capture_df.index.tolist()
    x = np.arange(len(names))
    bar_width = 0.32

    ax.bar(
        x - bar_width / 2,
        capture_df["Upside Capture (%)"].values,
        width=bar_width,
        label="Upside Capture",
        color="#16a34a"
    )
    ax.bar(
        x + bar_width / 2,
        capture_df["Downside Capture (%)"].values,
        width=bar_width,
        label="Downside Capture",
        color="#dc2626"
    )

    ax.axhline(100, color="#888888", linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=0)
    ax.set_ylabel("Capture Ratio (%)")
    ax.set_title("Upside / Downside Capture", fontsize=16, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.legend(frameon=False)

    apply_chart_theme(fig, ax)
    fig.tight_layout()
    return fig


def make_risk_return_scatter(points_df, benchmark_name):
    """
    Scatter of annualised return (y) vs annualised volatility (x) for a
    set of indices, with quadrant lines drawn through the benchmark
    index's own risk/return point so every other index reads as
    "better/worse risk, better/worse return" relative to it.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    others = points_df.drop(index=benchmark_name, errors="ignore")

    ax.scatter(
        others["Volatility"],
        others["Return"],
        s=60,
        color="#2563eb",
        alpha=0.75,
        zorder=3,
        label="Indices"
    )

    for name, row in others.iterrows():
        ax.annotate(
            name,
            (row["Volatility"], row["Return"]),
            fontsize=7,
            xytext=(4, 4),
            textcoords="offset points",
            alpha=0.85
        )

    if benchmark_name in points_df.index:
        b = points_df.loc[benchmark_name]

        ax.axvline(b["Volatility"], color="#888888", linestyle="--", linewidth=1)
        ax.axhline(b["Return"], color="#888888", linestyle="--", linewidth=1)

        ax.scatter(
            [b["Volatility"]],
            [b["Return"]],
            s=180,
            marker="*",
            color="#f97316",
            edgecolor="black",
            linewidth=0.6,
            zorder=5,
            label=benchmark_name
        )

        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()

        label_style = dict(fontsize=9, alpha=0.6, fontweight="bold")
        ax.text(xmax, ymax, "High Return / High Risk", ha="right", va="top", **label_style)
        ax.text(xmin, ymax, "High Return / Low Risk", ha="left", va="top", **label_style)
        ax.text(xmin, ymin, "Low Return / Low Risk", ha="left", va="bottom", **label_style)
        ax.text(xmax, ymin, "Low Return / High Risk", ha="right", va="bottom", **label_style)

    ax.set_xlabel("Annualised Volatility (%)")
    ax.set_ylabel("Annualised Return (%)")
    ax.set_title("Risk vs Return", fontsize=16, fontweight="bold")
    ax.grid(linestyle=":", alpha=0.4)
    ax.legend(frameon=False, loc="lower right")

    apply_chart_theme(fig, ax)
    fig.tight_layout()
    return fig

"""
Rolling-regression line chart for a single factor (or Alpha), with
significance-based colour coding.
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from core.config import SIG_COLORS
from core.regression_stats import classify_significance
from charts.theme import apply_chart_theme


def make_rolling_chart(rolling_df, factor, p_column, title, rolling_months):
    """
    Build a single rolling-regression chart for one factor (or Alpha).

    Colour scheme:
      - red line/points   : not significant
      - blue dots + line  : significant at 5% (two stars, p < 0.05)
      - green dots + line : significant at 1% (three stars, p < 0.01)

    Consecutive points that share the same significance bucket are
    connected with a coloured line segment (not just isolated dots),
    so runs of significance read clearly on the chart.
    """
    beta = rolling_df[factor].astype(float)
    pvalues = rolling_df[p_column].astype(float)
    dates = beta.index

    buckets = [classify_significance(p) for p in pvalues]

    fig, ax = plt.subplots(figsize=(7.5, 5))

    # Base line (context / not-significant backbone)
    ax.plot(
        dates,
        beta.values,
        linewidth=1.2,
        color=SIG_COLORS["none"],
        alpha=0.6,
        zorder=1
    )

    # Coloured connecting segments between consecutive same-bucket points
    for i in range(len(dates) - 1):
        b1, b2 = buckets[i], buckets[i + 1]
        if b1 == b2 and b1 in ("high", "moderate"):
            ax.plot(
                dates[i:i + 2],
                beta.values[i:i + 2],
                linewidth=2.4,
                color=SIG_COLORS[b1],
                zorder=4
            )

    # Coloured dots on top
    for bucket in ("moderate", "high"):
        mask = pd.Series(
            [b == bucket for b in buckets],
            index=dates
        )
        if mask.any():
            ax.scatter(
                dates[mask],
                beta[mask],
                color=SIG_COLORS[bucket],
                s=22,
                zorder=5
            )

    ax.axhline(0, color="#888888", linestyle="--", linewidth=1)

    if rolling_months % 12 == 0:
        window_text = f"{rolling_months // 12} Year"
    else:
        window_text = f"{rolling_months} Months"

    ax.set_title(
        f"{title} — {window_text} Rolling",
        fontsize=14,
        fontweight="bold"
    )

    ax.set_xlabel("Date")
    ax.set_ylabel("Coefficient")
    ax.grid(axis="y", linestyle=":", alpha=0.35)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend_elements = [
        Line2D([0], [0], color=SIG_COLORS["none"], lw=2, label="Not Significant"),
        Line2D([0], [0], color=SIG_COLORS["moderate"], lw=2, marker="o",
               label="Significant (p < 0.05)"),
        Line2D([0], [0], color=SIG_COLORS["high"], lw=2, marker="o",
               label="Significant (p < 0.01)"),
    ]
    ax.legend(handles=legend_elements, frameon=False, fontsize=8)

    apply_chart_theme(fig, ax)

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig

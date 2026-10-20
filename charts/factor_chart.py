"""
Factor exposure bar chart (coefficient + significance label per factor).
"""

import matplotlib.pyplot as plt

from core.config import FACTOR_LABELS
from core.regression_stats import significance_stars, significance_text
from charts.theme import apply_chart_theme


def make_factor_chart(model, factor_columns, title):
    values = [model.params[x] for x in factor_columns]
    pvalues = [model.pvalues[x] for x in factor_columns]
    labels = [FACTOR_LABELS.get(x, x) for x in factor_columns]

    fig, ax = plt.subplots(figsize=(12, 6))

    bars = ax.bar(range(len(values)), values)

    ax.axhline(0, color="#888888", linestyle="--", linewidth=1)
    ax.set_xticks(range(len(values)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Coefficient")
    ax.set_title(title, fontsize=18, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.4)

    max_abs = max([abs(x) for x in values] + [1])

    for bar, value, p in zip(bars, values, pvalues):
        stars = significance_stars(p)
        sig = significance_text(p)

        if value >= 0:
            number_y = value + max_abs * 0.025
            sig_y = value + max_abs * 0.085
            number_va = "bottom"
            sig_va = "bottom"
        else:
            number_y = value - max_abs * 0.025
            sig_y = value - max_abs * 0.085
            number_va = "top"
            sig_va = "top"

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            number_y,
            f"{value:.3f}",
            ha="center",
            va=number_va,
            fontsize=11,
            fontweight="bold"
        )

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            sig_y,
            f"{stars}  {sig}",
            ha="center",
            va=sig_va,
            fontsize=9
        )

    ymin, ymax = ax.get_ylim()
    padding = max_abs * 0.25
    ax.set_ylim(ymin - padding, ymax + padding)

    apply_chart_theme(fig, ax)

    fig.tight_layout()
    return fig

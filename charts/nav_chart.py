"""NAV and cumulative-return line charts for the Factor Analysis page."""

import matplotlib.pyplot as plt

from charts.theme import apply_chart_theme


def make_nav_chart(dates, nav):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates, nav, linewidth=2)
    ax.set_xlabel("Date")
    ax.set_ylabel("NAV")
    ax.set_title("NAV Performance", fontsize=17, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    apply_chart_theme(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def make_cumulative_chart(cumulative):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(cumulative.index, cumulative.values, linewidth=2)
    ax.axhline(0, color="#888888", linestyle="--", linewidth=1)
    ax.set_title("Portfolio Cumulative Return", fontsize=18, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return (%)")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    apply_chart_theme(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig

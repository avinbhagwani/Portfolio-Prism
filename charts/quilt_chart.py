"""
The classic "asset allocation quilt" chart — rebuilt to match the
familiar printed version (Mint/Morningstar style) as closely as
possible: a white header row of year labels, then edge-to-edge cells
in flat colours with a visible black grid, black bold text throughout.
This intentionally does NOT adapt to Streamlit's light/dark theme —
the reference is a fixed white-background print style, and fighting
that with a dark-mode background would work against the "look exactly
like this" request.
"""

import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from charts.theme import QUILT_COLORS

HEADER_HEIGHT = 0.6
GRID_LINEWIDTH = 1.6
GRID_COLOR = "#000000"

DEFAULT_COLOR = "#D9D9D9"

# Rendered at high DPI so the exported/displayed image stays crisp
# even at large sizes ("ultra HD" per the request).
FIGURE_DPI = 220


def build_quilt_color_map(index_names):
    """Assigns each index a fixed flat colour, in order."""
    return {
        name: QUILT_COLORS[i % len(QUILT_COLORS)]
        for i, name in enumerate(index_names)
    }


def make_quilt_chart(quilt_df, color_map, title="Asset Allocation Quilt"):
    if quilt_df.empty:
        return None

    n_ranks, n_years = quilt_df.shape
    years = list(quilt_df.columns)

    cell_w, cell_h = 1.75, 1.05
    fig_width = max(n_years * cell_w, 6)
    fig_height = max(n_ranks * cell_h + HEADER_HEIGHT * cell_h, 3)

    fig, ax = plt.subplots(
        figsize=(fig_width, fig_height),
        dpi=FIGURE_DPI
    )

    total_height = n_ranks + HEADER_HEIGHT

    # ---- header row: year labels ----
    for j, year in enumerate(years):
        ax.add_patch(
            Rectangle(
                (j, n_ranks), 1, HEADER_HEIGHT,
                facecolor="white",
                edgecolor=GRID_COLOR,
                linewidth=GRID_LINEWIDTH
            )
        )
        ax.text(
            j + 0.5, n_ranks + HEADER_HEIGHT / 2,
            str(year),
            ha="center", va="center",
            fontsize=13, fontweight="bold",
            color="black"
        )

    # ---- body cells ----
    for j, year in enumerate(years):
        for i in range(n_ranks):
            cell = quilt_df.iloc[i, j]
            y = n_ranks - i - 1

            color = DEFAULT_COLOR
            name, value = None, None
            if cell is not None:
                name, value = cell
                color = color_map.get(name, DEFAULT_COLOR)

            ax.add_patch(
                Rectangle(
                    (j, y), 1, 1,
                    facecolor=color,
                    edgecolor=GRID_COLOR,
                    linewidth=GRID_LINEWIDTH
                )
            )

            if cell is None:
                continue

            wrapped_name = textwrap.fill(name, width=14)

            ax.text(
                j + 0.5, y + 0.62,
                wrapped_name,
                ha="center", va="center",
                fontsize=10, fontweight="bold",
                color="black",
                linespacing=1.2
            )
            ax.text(
                j + 0.5, y + 0.24,
                f"{value:.2f}%",
                ha="center", va="center",
                fontsize=11, fontweight="bold",
                color="black"
            )

    ax.set_xlim(0, n_years)
    ax.set_ylim(0, total_height)
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    if title:
        ax.set_title(title, fontsize=17, fontweight="bold", pad=16, color="black")

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    fig.tight_layout()

    return fig

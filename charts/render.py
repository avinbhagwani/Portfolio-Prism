"""
Two separate things silently degrade matplotlib charts shown via plain
st.pyplot()/st.image(width="stretch") in this Streamlit version:

1. st.pyplot() hard-codes dpi=200 on every chart, ignoring the figure's
   own dpi.
2. st.image(), when given width="stretch" or "content" (anything other
   than an explicit int), resizes any image wider than a hard-coded
   1460px using a single BILINEAR pass *before it ever reaches the
   browser* — regardless of how high a dpi it was rendered at. This is
   the actual source of the blur: a wide chart (like the Quilt) gets
   crushed down to 1460px server-side, then the browser scales that
   already-soft image again to fit the container.

The fix for both: render to a buffer ourselves at a real dpi, and pass
st.image an explicit integer width at least as large as the image's
true pixel width. That swaps Streamlit's resize threshold from 1460px
to our own size, so the resize branch never triggers — the browser
receives the full-resolution PNG and does its own single, much higher
quality downscale to fit the container.

Use this everywhere a chart is shown instead of st.pyplot(fig).
"""

import io

import streamlit as st

DEFAULT_DPI = 300

# Upper bounds on the rendered PNG. A chart is shown at most ~1,200 CSS
# px wide, so 3,000 px is still ~2.5x that (sharp on retina screens).
# Without a cap, wide figures like a full-history Quilt (54 inches wide)
# rendered at 300 dpi became 16,000+ px images costing ~200 MB of RAM
# each, which crashed the 512 MiB Cloud Run container and reset users
# back to the Factor Analysis page.
MAX_WIDTH_PX = 3000
MAX_TOTAL_PX = 9_000_000


def capped_dpi(fig, dpi=DEFAULT_DPI):
    """Largest dpi <= `dpi` that keeps the PNG within the pixel caps."""
    width_in, height_in = fig.get_size_inches()
    by_width = MAX_WIDTH_PX / width_in
    by_area = (MAX_TOTAL_PX / (width_in * height_in)) ** 0.5
    return max(50, min(dpi, by_width, by_area))


def show_figure(fig, dpi=DEFAULT_DPI):
    dpi = capped_dpi(fig, dpi)

    # bbox_inches="tight" does an extra draw pass at the figure's own
    # dpi (the Quilt sets 220), so align it too, or that pass alone
    # allocates a huge canvas before the capped save even starts.
    fig.set_dpi(dpi)

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )
    buf.seek(0)

    # bbox_inches="tight" trims whitespace, so the true rendered width
    # is at or below figure_width_inches * dpi — using that product
    # (plus a small safety margin) as the explicit width is guaranteed
    # to be >= the actual PNG width, which is what disables Streamlit's
    # server-side resize.
    width_in, _ = fig.get_size_inches()
    safe_width_px = int(width_in * dpi) + 20

    st.image(buf, width=safe_width_px)

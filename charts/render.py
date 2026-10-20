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


def show_figure(fig, dpi=DEFAULT_DPI):
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

"""
Rendering matplotlib charts into the page, with caching.

show_chart(builder, *args, **kwargs) is the fast path: it calls
builder(*args, **kwargs) to make a figure, renders it to PNG once and
caches the bytes, keyed on the builder and its arguments. Any rerun
with the same inputs (the user touching an unrelated widget, switching
tabs, coming back to a page) reuses the PNG instead of redrawing, which
is where most of the app's time used to go (~0.2 s per chart).

show_figure(fig) is kept for one-off figures that aren't worth caching.

Two things silently degrade charts shown via st.pyplot()/st.image():
st.pyplot() hard-codes dpi=200, and st.image(width="stretch") resizes
anything wider than 1460px with a single bilinear pass before it ever
reaches the browser. Rendering to a buffer ourselves and passing an
explicit integer width avoids both, so the browser gets the full PNG.
"""

import importlib
import io

import matplotlib.pyplot as plt
import streamlit as st

DEFAULT_DPI = 220

# Upper bounds on the rendered PNG. A chart is shown at most ~1,200 CSS
# px wide, so 2,700 px is still ~2.2x that (sharp on retina screens).
# Without a cap, wide figures like a full-history Quilt (54 inches wide)
# rendered at 300 dpi became 16,000+ px images costing ~200 MB of RAM
# each, which crashed the Cloud Run container.
MAX_WIDTH_PX = 2700
MAX_TOTAL_PX = 9_000_000


def capped_dpi(fig, dpi=DEFAULT_DPI):
    """Largest dpi <= `dpi` that keeps the PNG within the pixel caps."""
    width_in, height_in = fig.get_size_inches()
    by_width = MAX_WIDTH_PX / width_in
    by_area = (MAX_TOTAL_PX / (width_in * height_in)) ** 0.5
    return max(50, min(dpi, by_width, by_area))


def _to_png(fig, dpi):
    dpi = capped_dpi(fig, dpi)
    # bbox_inches="tight" does an extra draw at the figure's own dpi
    # (the Quilt sets 220), so align it too.
    fig.set_dpi(dpi)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    width_in, _ = fig.get_size_inches()
    # >= the true PNG width, which disables Streamlit's server-side resize
    return buf.getvalue(), int(width_in * dpi) + 20


@st.cache_data(max_entries=300, ttl=6 * 3600, show_spinner=False)
def _render_cached(builder_path, args, kwargs, dpi):
    module, name = builder_path.rsplit(":", 1)
    builder = getattr(importlib.import_module(module), name)
    fig = builder(*args, **kwargs)
    try:
        return _to_png(fig, dpi)
    finally:
        plt.close(fig)


def show_chart(builder, *args, dpi=DEFAULT_DPI, **kwargs):
    """Build, render and cache a chart; builder must be a module-level function."""
    png, width = _render_cached(
        f"{builder.__module__}:{builder.__qualname__}", args, kwargs, dpi
    )
    st.image(png, width=width)


def show_figure(fig, dpi=DEFAULT_DPI):
    png, width = _to_png(fig, dpi)
    st.image(png, width=width)

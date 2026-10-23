"""
Interactive charts for Factor Analysis, in the FBI Intelligence house
style (see charts/fbi_vega.py for the shared theme).

  exposure_chart  one bar per factor with its 95% confidence range;
                  significant exposures in colour, the rest grey
  rolling_chart   small multiples of each exposure through time, with a
                  confidence band; points coloured when significant
"""

import altair as alt
import pandas as pd

from charts import fbi_vega as fv  # noqa: F401  (registers the theme)

SIG = "#1F4E79"
SIG_NEG = "#B54A3C"
NOT_SIG = "#C3CAD2"
BAND = "#DDE6EF"


def exposure_chart(rows):
    """rows: list of dicts with label, coef, lo, hi, sig (bool)."""
    df = pd.DataFrame(rows)
    df["colour"] = [
        (SIG if c >= 0 else SIG_NEG) if s else NOT_SIG
        for c, s in zip(df["coef"], df["sig"])
    ]
    df["text"] = df["coef"].map(lambda v: f"{v:+.2f}".replace("-", "−"))
    order = df["label"].tolist()
    lo = min(0.0, float(df["lo"].min())) - 0.05
    hi = max(0.0, float(df["hi"].max())) + 0.25
    y = alt.Y("label:N", sort=order, title=None,
              axis=alt.Axis(labelFontSize=13, labelColor=fv.INK, labelPadding=12))
    x_scale = alt.Scale(domain=[lo, hi], nice=False)
    base = alt.Chart(df).encode(y=y)
    bars = base.mark_bar(height=22, cornerRadiusEnd=3).encode(
        x=alt.X("coef:Q", title=None, scale=x_scale, axis=alt.Axis(format=".1f", tickCount=6, grid=True)),
        x2=alt.datum(0),
        color=alt.Color("colour:N", scale=None),
        tooltip=[alt.Tooltip("label:N", title="Factor"), alt.Tooltip("coef:Q", title="Exposure", format=".3f"),
                 alt.Tooltip("lo:Q", title="95% range from", format=".3f"),
                 alt.Tooltip("hi:Q", title="to", format=".3f")],
    )
    whiskers = base.mark_rule(color=fv.INK, strokeWidth=1.3, opacity=0.55).encode(
        x=alt.X("lo:Q", scale=x_scale), x2="hi:Q")
    caps_lo = base.mark_tick(color=fv.INK, thickness=1.3, size=10, opacity=0.55).encode(x=alt.X("lo:Q", scale=x_scale))
    caps_hi = base.mark_tick(color=fv.INK, thickness=1.3, size=10, opacity=0.55).encode(x=alt.X("hi:Q", scale=x_scale))
    labels = base.mark_text(align="left", dx=8, fontSize=12.5, fontWeight=600).encode(
        x=alt.X("hi:Q", scale=x_scale), text="text:N", color=alt.Color("colour:N", scale=None))
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=fv.ZERO, strokeWidth=1.2).encode(x="x:Q")
    return alt.layer(zero, bars, whiskers, caps_lo, caps_hi, labels).properties(
        width="container", height=max(150, 46 * len(df)))


def rolling_chart(rdf, items, cols=2):
    """
    rdf: index = window end date; for each item in items (column names)
    it holds item, item_P and item_SE. items is a list of (column, label).
    """
    charts = []
    for col, label in items:
        d = pd.DataFrame({
            "date": rdf.index, "coef": rdf[col].values,
            "lo": (rdf[col] - 1.96 * rdf[f"{col}_SE"]).values,
            "hi": (rdf[col] + 1.96 * rdf[f"{col}_SE"]).values,
            "sig": (rdf[f"{col}_P"] < 0.05).values,
        })
        d["status"] = d["sig"].map({True: "Significant", False: "Could be noise"})
        base = alt.Chart(d).encode(x=alt.X("date:T", title=None, axis=alt.Axis(format="%Y", tickCount=6)))
        band = base.mark_area(color=BAND, opacity=0.9).encode(y=alt.Y("lo:Q", title=None), y2="hi:Q")
        line = base.mark_line(color="#7D8FA3", strokeWidth=1.4).encode(y="coef:Q")
        pts = base.mark_circle(size=16).encode(
            y="coef:Q",
            color=alt.Color("status:N", scale=alt.Scale(domain=["Significant", "Could be noise"],
                                                        range=[SIG, NOT_SIG])),
            tooltip=[alt.Tooltip("date:T", title="Window ending", format="%b %Y"),
                     alt.Tooltip("coef:Q", title=label, format=".3f"), alt.Tooltip("status:N", title="")],
        )
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=fv.ZERO).encode(y="y:Q")
        charts.append(alt.layer(band, zero, line, pts).properties(
            title=alt.TitleParams(label, anchor="start", fontSize=13, fontWeight=600, color=fv.INK, offset=8),
            width=330, height=170))
    rows = [alt.hconcat(*charts[i:i + cols], spacing=36) for i in range(0, len(charts), cols)]
    return alt.vconcat(*rows, spacing=28).configure_view(stroke=None)

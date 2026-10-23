"""
Interactive charts for Factor Analysis, in the FBI Intelligence house
style (see charts/fbi_vega.py for the shared theme).

  exposure_chart  vertical bars (alpha + each factor) with the value and
                  significance above each and a 95% range whisker;
                  significant terms in colour, the rest grey
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
    """Vertical bars, one per term (alpha first), like the original PRISM
    chart: the exposure printed above each bar with its significance, and
    a whisker for the 95% confidence range.
    rows: list of dicts with label, coef, lo, hi, sig (bool), stars, sig_text."""
    df = pd.DataFrame(rows)
    df["colour"] = [
        (SIG if c >= 0 else SIG_NEG) if s else NOT_SIG
        for c, s in zip(df["coef"], df["sig"])
    ]
    df["value"] = df["coef"].map(lambda v: f"{v:.3f}".replace("-", "−"))
    df["note"] = [f"{st}  {t}".strip() for st, t in zip(df["stars"], df["sig_text"])]
    span = max(float(df["hi"].max()), 0.0) - min(float(df["lo"].min()), 0.0) or 1.0
    pad = span * 0.06
    # labels sit beyond the end of the whisker, on the bar's side of zero
    df["y_val"] = [h + pad if c >= 0 else l - pad for c, h, l in zip(df["coef"], df["hi"], df["lo"])]
    df["y_note"] = [h + pad * 2.6 if c >= 0 else l - pad * 2.6 for c, h, l in zip(df["coef"], df["hi"], df["lo"])]
    lo = min(0.0, float(df["y_note"].min())) - pad
    hi = max(0.0, float(df["y_note"].max())) + pad
    order = df["label"].tolist()
    x = alt.X("label:N", sort=order, title=None,
              axis=alt.Axis(labelFontSize=13, labelColor=fv.INK, labelAngle=0, labelPadding=10))
    y_scale = alt.Scale(domain=[lo, hi], nice=False)
    base = alt.Chart(df).encode(x=x)
    bars = base.mark_bar(size=46, cornerRadiusEnd=3).encode(
        y=alt.Y("coef:Q", title="Coefficient", scale=y_scale, axis=alt.Axis(format=".1f", tickCount=6)),
        y2=alt.datum(0),
        color=alt.Color("colour:N", scale=None),
        tooltip=[alt.Tooltip("label:N", title="Term"), alt.Tooltip("coef:Q", title="Coefficient", format=".3f"),
                 alt.Tooltip("lo:Q", title="95% range from", format=".3f"),
                 alt.Tooltip("hi:Q", title="to", format=".3f"), alt.Tooltip("note:N", title="Significance")],
    )
    whisker = base.mark_rule(color=fv.INK, strokeWidth=1.3, opacity=0.5).encode(
        y=alt.Y("lo:Q", scale=y_scale), y2="hi:Q")
    caps = [base.mark_tick(color=fv.INK, thickness=1.3, size=12, opacity=0.5, orient="horizontal").encode(
        y=alt.Y(f"{k}:Q", scale=y_scale)) for k in ("lo", "hi")]
    value = base.mark_text(fontSize=12.5, fontWeight=700, color=fv.INK).encode(
        y=alt.Y("y_val:Q", scale=y_scale), text="value:N")
    note = base.mark_text(fontSize=11, color=fv.MUTED).encode(
        y=alt.Y("y_note:Q", scale=y_scale), text="note:N")
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#8A939E", strokeDash=[4, 3]).encode(y="y:Q")
    return alt.layer(zero, bars, whisker, *caps, value, note).properties(width="container", height=400)


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

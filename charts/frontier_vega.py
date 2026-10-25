"""
Charts for the Efficient Frontier page, in the FBI Intelligence house
style (Inter, no frame, faint grid, direct labels instead of legends).

Colours carry one meaning everywhere on the page:
  navy  the frontier          rust   best risk-adjusted mix
  gold  lowest-risk mix       teal   equal mix of the set
  grey  Nifty 500             slate  the individual indices
"""

import altair as alt
import numpy as np
import pandas as pd

from charts import fbi_vega as fv  # registers and enables the house theme

NAVY = "#1F4E79"
RUST = "#B54A3C"
GOLD = "#C08A2E"
TEAL = "#2F8F9D"
GREY = "#8A939E"
SLATE = "#5F7A94"
CLOUD = "#C7D0DA"
POS = "#5E9A62"
NEG = "#C9573C"

MIX_COLORS = {"best": RUST, "low": GOLD, "equal": TEAL, "bench": GREY}
MIX_NAMES = {"best": "Best risk-adjusted mix", "low": "Lowest-risk mix",
             "equal": "Equal mix", "bench": "Nifty 500"}
# shorter on-chart labels, so they fit when two charts sit side by side
SHORT_NAMES = {"best": "Best mix", "low": "Lowest risk", "equal": "Equal mix"}
# index colours for weights; kept clear of the rust, gold and teal used for the mixes
WEIGHT_COLORS = ["#1F4E79", "#8E5B9F", "#5E9A62", "#6C8EBF", "#C77DA6",
                 "#9A8B3C", "#3F6E5A", "#B08BC8", "#5F6B78", "#A7C4DE"]

PCT = "format(datum.value, '.0f') + '%'"


def _domain(vals, pad_frac=0.08, min_pad=1.0):
    vals = [float(v) for v in vals if v is not None and np.isfinite(v)]
    if not vals:
        return [0.0, 30.0]
    lo, hi = min(vals), max(vals)
    pad = max((hi - lo) * pad_frac, min_pad)
    return [float(lo - pad), float(hi + pad)]


STAR = ("M0,-1.1L0.32,-0.32L1.1,-0.32L0.48,0.15L0.7,0.95L0,0.47L-0.7,0.95"
        "L-0.48,0.15L-1.1,-0.32L-0.32,-0.32Z")


def shared_domains(o, names, with_next):
    """One pair of axis ranges for the look-back and next-years charts, so
    a point that moves between them moves on screen by the same amount."""
    pts = o["points"]
    xs = list(o["cloud"]["risk"].quantile([0.0, 1.0])) + list(pts.loc[names + ["NIFTY 500"], "risk"]) \
        + list(o["frontier"]["risk"])
    ys = list(o["cloud"]["ret"].quantile([0.0, 1.0])) + list(pts.loc[names + ["NIFTY 500"], "ret"]) \
        + list(o["frontier"]["ret"])
    if with_next and "fwd_points" in o:
        fp = o["fwd_points"]
        xs += list(fp.loc[names + ["NIFTY 500"], "risk"]) + list(o["fwd_cloud"]["risk"].quantile([0.0, 1.0]))
        ys += list(fp.loc[names + ["NIFTY 500"], "ret"]) + list(o["fwd_cloud"]["ret"].quantile([0.0, 1.0]))
        xs += [v[1] for v in o["landed"].values()]
        ys += [v[0] for v in o["landed"].values()]
        if "fwd_frontier" in o:
            xs += list(o["fwd_frontier"]["risk"])
            ys += list(o["fwd_frontier"]["ret"])
    return _domain(xs), _domain(ys, min_pad=1.5)


def _axes(xd, yd, show_y=True):
    x = alt.X("risk:Q", title="Risk (volatility a year)",
              scale=alt.Scale(domain=xd, nice=False, zero=False),
              axis=alt.Axis(labelExpr=PCT, grid=True, tickMinStep=1))
    y = alt.Y("ret:Q", title="Average return a year" if show_y else None,
              scale=alt.Scale(domain=yd, nice=False, zero=False),
              axis=alt.Axis(labelExpr=PCT, tickMinStep=1))
    return x, y


def _tip(extra=()):
    return [alt.Tooltip("name:N", title=" "),
            alt.Tooltip("ret:Q", title="Return a year %", format=".1f"),
            alt.Tooltip("risk:Q", title="Risk %", format=".1f")] + list(extra)


def _index_layers(pts, names, label, x, y, skip=()):
    idx = pd.DataFrame({"risk": pts.loc[names, "risk"].values, "ret": pts.loc[names, "ret"].values,
                        "name": [label(n) for n in names]})
    b = pts.loc["NIFTY 500"]
    bdf = pd.DataFrame([{"name": "Nifty 500", "ret": b["ret"], "risk": b["risk"]}])
    return [
        alt.Chart(idx).mark_circle(size=70, color=SLATE, opacity=0.9).encode(x=x, y=y, tooltip=_tip()),
        alt.Chart(idx[~idx["name"].isin(skip)]).mark_text(
            align="left", dx=8, dy=-1, fontSize=11.5, color=SLATE).encode(x=x, y=y, text="name:N"),
        alt.Chart(bdf).mark_point(shape="diamond", filled=True, size=170, color=GREY, opacity=1).encode(
            x=x, y=y, tooltip=_tip()),
        alt.Chart(bdf).mark_text(align="left", dx=10, dy=1, fontSize=12, fontWeight=600,
                                 color="#5F6873").encode(x=x, y=y, text="name:N"),
    ]


def _mix_labels(df, x, y, xd):
    """Mix names placed beside their star, on whichever side of the chart
    has room: labels in the right half go to the left of the mark."""
    mid = (xd[0] + xd[1]) / 2
    out = []
    for k, dy in (("best", -13), ("low", 17), ("equal", 15)):
        row = df[df["key"] == k]
        if row.empty:
            continue
        right_half = float(row["risk"].iloc[0]) > mid
        out.append(alt.Chart(row).mark_text(
            align="right" if right_half else "left", dx=-13 if right_half else 13, dy=dy,
            fontSize=12, fontWeight=600).encode(
            x=x, y=y, text="label:N", color=alt.Color("color:N", scale=None)))
    return out


def frontier_chart(o, names, label, weight_text, xd, yd, height=470):
    """The look-back window: a faint cloud of random mixes, the frontier,
    every index, the Nifty 500 and the two optimised mixes (stars)."""
    pts = o["points"]
    fr = o["frontier"].copy()
    fr["mix"] = weight_text(o["frontier_w"])
    x, y = _axes(xd, yd)

    # an index the best or lowest-risk mix sits on is named in that mix's label instead
    on_mix = {}
    for k in ("best", "low"):
        r, v = o["mix"][k]
        for n in names:
            if abs(pts.loc[n, "ret"] - r) < 0.15 and abs(pts.loc[n, "risk"] - v) < 0.15:
                on_mix[k] = label(n)
    mixes = pd.DataFrame([
        {"key": k, "name": MIX_NAMES[k], "label": SHORT_NAMES[k] + (f" · {on_mix[k]}" if k in on_mix else ""),
         "ret": o["mix"][k][0], "risk": o["mix"][k][1], "color": MIX_COLORS[k],
         "mix": weight_text([o["weights"][k]])[0]}
        for k in ("best", "low")])

    hover = alt.selection_point(on="pointerover", nearest=True, fields=["risk"],
                                empty=False, clear="pointerout")
    layers = [
        alt.Chart(o["cloud"]).mark_circle(size=9, color=CLOUD, opacity=0.45).encode(x=x, y=y),
        alt.Chart(fr).mark_line(color=NAVY, strokeWidth=3, interpolate="monotone").encode(
            x=x, y=y, order="risk:Q"),
        alt.Chart(fr).mark_circle(size=70, color=NAVY).encode(
            x=x, y=y, opacity=alt.condition(hover, alt.value(1), alt.value(0)),
            tooltip=[alt.Tooltip("ret:Q", title="Return a year %", format=".1f"),
                     alt.Tooltip("risk:Q", title="Risk %", format=".1f"),
                     alt.Tooltip("mix:N", title="Mix")]).add_params(hover),
    ]
    layers += _index_layers(pts, names, label, x, y, skip=set(on_mix.values()))
    layers.append(alt.Chart(mixes).mark_point(shape=STAR, filled=True, size=420, opacity=1,
                                              strokeWidth=0).encode(
        x=x, y=y, color=alt.Color("color:N", scale=None),
        tooltip=_tip([alt.Tooltip("mix:N", title="Mix")])))
    layers += _mix_labels(mixes, x, y, xd)
    return alt.layer(*layers).properties(width="container", height=height)


def next_chart(o, names, label, xd, yd, height=470):
    """The years after the window, on the same axes: where every index and
    mix actually ended up. Each mix is drawn twice, a faint hollow star
    where the look-back put it and a solid star where it landed, joined by
    a line, so the gap between promise and result is visible at a glance.
    The look-back frontier is kept as a faint dashed reference."""
    x, y = _axes(xd, yd, show_y=False)
    fp = o["fwd_points"]
    layers = [alt.Chart(o["fwd_cloud"]).mark_circle(size=9, color=CLOUD, opacity=0.45).encode(x=x, y=y)]

    old = o["frontier"]
    layers.append(alt.Chart(old).mark_line(color=GREY, strokeDash=[4, 4], strokeWidth=1.6, opacity=0.7,
                                           interpolate="monotone").encode(x=x, y=y, order="risk:Q"))
    layers.append(alt.Chart(old.iloc[-1:].assign(t="look-back frontier")).mark_text(
        align="right", dx=-4, dy=-9, fontSize=11, fontStyle="italic", color=GREY).encode(
        x=x, y=y, text="t:N"))
    if "fwd_frontier" in o:
        layers.append(alt.Chart(o["fwd_frontier"]).mark_line(
            color=NAVY, strokeWidth=3, interpolate="monotone").encode(x=x, y=y, order="risk:Q"))

    layers += _index_layers(fp, names, label, x, y)

    keys = ["best", "low", "equal"]
    rows = []
    for k in keys:
        r0, v0 = o["mix"][k]
        r1, v1 = o["landed"][k]
        rows.append({"key": k, "name": MIX_NAMES[k], "color": MIX_COLORS[k],
                     "ret0": r0, "risk0": v0, "ret": r1, "risk": v1,
                     "promised": f"{r0:.1f}% at {v0:.1f}% risk", "got": f"{r1:.1f}% at {v1:.1f}% risk"})
    mv = pd.DataFrame(rows)
    opt = mv[mv["key"] != "equal"]
    ghost = pd.DataFrame({"risk": opt["risk0"], "ret": opt["ret0"], "color": opt["color"]})
    seg = pd.DataFrame({"risk": opt["risk0"], "ret": opt["ret0"], "risk2": opt["risk"],
                        "ret2": opt["ret"], "color": opt["color"]})
    layers.append(alt.Chart(seg).mark_rule(strokeWidth=1.8, opacity=0.75, strokeDash=[1, 3],
                                           strokeCap="round").encode(
        x=x, y=y, x2="risk2:Q", y2="ret2:Q", color=alt.Color("color:N", scale=None)))
    layers.append(alt.Chart(ghost).mark_point(shape=STAR, filled=False, size=360, strokeWidth=1.6,
                                              opacity=0.6).encode(
        x=x, y=y, color=alt.Color("color:N", scale=None)))
    tip = [alt.Tooltip("name:N", title=" "), alt.Tooltip("promised:N", title="Look-back said"),
           alt.Tooltip("got:N", title="Next years gave")]
    layers.append(alt.Chart(opt).mark_point(shape=STAR, filled=True, size=420, opacity=1,
                                            strokeWidth=0).encode(
        x=x, y=y, color=alt.Color("color:N", scale=None), tooltip=tip))
    eq = mv[mv["key"] == "equal"]
    layers.append(alt.Chart(eq).mark_circle(size=150, opacity=1).encode(
        x=x, y=y, color=alt.Color("color:N", scale=None), tooltip=tip))
    mv["label"] = mv["key"].map(SHORT_NAMES)
    layers += _mix_labels(mv, x, y, xd)
    return alt.layer(*layers).properties(width="container", height=height)


def growth_chart(series, order):
    """₹1 lakh grown through the test period, one line per mix."""
    df = pd.DataFrame({MIX_NAMES[k]: series[k] for k in order}) * 1e5
    start = df.index[0] - pd.offsets.MonthEnd(1)
    df.loc[start] = 1e5
    df = df.sort_index()
    df.index.name = "date"
    long = df.reset_index().melt("date", var_name="series", value_name="value")
    names = [MIX_NAMES[k] for k in order]
    scale = alt.Scale(domain=names, range=[MIX_COLORS[k] for k in order])
    last = long[long["date"] == long["date"].max()].sort_values("value").copy()
    span = (df.index[-1] - df.index[0]).days
    xend = df.index[-1] + pd.Timedelta(days=int(span * 0.32))
    gap = (long["value"].max() - long["value"].min()) * 0.07
    ys, prev = [], None
    for v in last["value"]:
        prev = v if prev is None else max(v, prev + gap)
        ys.append(prev)
    last["y"] = ys
    last["label"] = last["series"] + "  ₹" + (last["value"] / 1e5).round(2).astype(str) + "L"
    years = [alt.DateTime(year=y, month=1, date=1) for y in range(df.index[0].year + 1, df.index[-1].year + 1)]
    x = alt.X("date:T", title=None, axis=alt.Axis(format="%Y", values=years),
              scale=alt.Scale(domain=[df.index[0].isoformat(), xend.isoformat()]))
    lines = alt.Chart(long).mark_line(interpolate="monotone").encode(
        x=x, y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=False),
                     axis=alt.Axis(tickCount=5, labelExpr="'₹' + format(datum.value / 100000, '.2f') + 'L'")),
        color=alt.Color("series:N", scale=scale),
        strokeWidth=alt.condition(alt.datum.series == "Nifty 500", alt.value(1.6), alt.value(2.4)),
        tooltip=[alt.Tooltip("date:T", format="%b %Y", title="Month"), alt.Tooltip("series:N", title=" "),
                 alt.Tooltip("value:Q", format=",.0f", title="Value ₹")])
    labels = alt.Chart(last).mark_text(align="left", dx=8, fontSize=12, fontWeight=500).encode(
        x="date:T", y="y:Q", text="label:N", color=alt.Color("series:N", scale=scale))
    base = alt.Chart(pd.DataFrame({"y": [1e5]})).mark_rule(color=fv.ZERO).encode(y="y:Q")
    return alt.layer(base, lines, labels).properties(width="container", height=300)


def track_chart(t, selected_end, mix="best"):
    """Excess return a year of the chosen mix over the Nifty 500 in the
    years after each window, one bar per window end."""
    df = pd.DataFrame({"end": t.index, "excess": (t[mix] - t["bench"]).values,
                       "mix": t[mix].values, "bench": t["bench"].values})
    df["sel"] = df["end"] == selected_end
    x = alt.X("end:T", title="Window ending", axis=alt.Axis(format="%Y", tickCount=8))
    bars = alt.Chart(df).mark_bar(width={"band": 0.75}, cornerRadiusEnd=1.5).encode(
        x=x, y=alt.Y("excess:Q", title=None, axis=alt.Axis(labelExpr="format(datum.value, '+.0f') + ' pts'")),
        color=alt.condition(alt.datum.excess >= 0, alt.value(POS), alt.value(NEG)),
        opacity=alt.condition(alt.datum.sel, alt.value(1), alt.value(0.72)),
        tooltip=[alt.Tooltip("end:T", format="%b %Y", title="Window ending"),
                 alt.Tooltip("mix:Q", format=".1f", title=MIX_NAMES[mix] + " %/yr"),
                 alt.Tooltip("bench:Q", format=".1f", title="Nifty 500 %/yr"),
                 alt.Tooltip("excess:Q", format="+.1f", title="Difference, pts")])
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=fv.ZERO).encode(y="y:Q")
    layers = [zero, bars]
    if selected_end is not None and (df["end"] == selected_end).any():
        layers.append(alt.Chart(pd.DataFrame({"end": [selected_end]})).mark_rule(
            color=fv.INK, strokeDash=[3, 3], opacity=0.6).encode(x="end:T"))
    return alt.layer(*layers).properties(width="container", height=260)


def weights_chart(w, label, selected_end):
    """Weights of the best mix in every window, stacked to 100%."""
    df = w.copy()
    df.columns = [label(c) for c in df.columns]
    df.index.name = "end"
    long = df.reset_index().melt("end", var_name="index", value_name="w")
    long["w"] *= 100
    names = list(df.columns)
    scale = alt.Scale(domain=names, range=WEIGHT_COLORS[: len(names)])
    area = alt.Chart(long).mark_area(interpolate="step-after", opacity=0.9).encode(
        x=alt.X("end:T", title="Window ending", axis=alt.Axis(format="%Y", tickCount=8)),
        y=alt.Y("w:Q", stack="zero", title=None, scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(labelExpr=PCT, values=[0, 25, 50, 75, 100])),
        color=alt.Color("index:N", scale=scale, sort=names,
                        legend=alt.Legend(orient="top", title=None, labelFontSize=12,
                                          symbolType="square", columns=6, labelColor=fv.MUTED)),
        order=alt.Order("index:N"),
        tooltip=[alt.Tooltip("end:T", format="%b %Y", title="Window ending"),
                 alt.Tooltip("index:N", title="Index"), alt.Tooltip("w:Q", format=".0f", title="Weight %")])
    layers = [area]
    if selected_end is not None:
        layers.append(alt.Chart(pd.DataFrame({"end": [selected_end]})).mark_rule(
            color=fv.INK, strokeWidth=1.5, strokeDash=[3, 3]).encode(x="end:T"))
    return alt.layer(*layers).properties(width="container", height=250).configure_legend(disable=False)

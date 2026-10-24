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


def frontier_chart(o, names, label, weight_text, show_next):
    """The frontier for one window: a faint cloud of random mixes, the
    frontier, every index, the Nifty 500, the two optimised mixes and,
    if show_next, where they landed over the following years and the
    frontier those years actually offered (dashed)."""
    pts = o["points"]
    fr = o["frontier"].copy()
    fr["mix"] = weight_text(o["frontier_w"])
    nxt = show_next and "landed" in o

    idx = pd.DataFrame({
        "risk": pts.loc[names, "risk"].values, "ret": pts.loc[names, "ret"].values,
        "name": [label(n) for n in names]})
    # an index the best or lowest-risk mix sits on is named in that mix's label instead
    on_mix = {}
    for k in ("best", "low"):
        r, v = o["mix"][k]
        hit = idx[((idx["ret"] - r).abs() < 0.15) & ((idx["risk"] - v).abs() < 0.15)]
        if len(hit):
            on_mix[k] = hit["name"].iloc[0]
    idx_lab = idx[~idx["name"].isin(on_mix.values())]
    bench = pts.loc["NIFTY 500"]
    mixes = pd.DataFrame([
        {"key": k, "name": MIX_NAMES[k] + (f" · all {on_mix[k]}" if k in on_mix else ""), "ret": o["mix"][k][0], "risk": o["mix"][k][1],
         "color": MIX_COLORS[k], "mix": weight_text([o["weights"][k]])[0]}
        for k in ("best", "low")])
    bdf = pd.DataFrame([{"name": "Nifty 500", "ret": bench["ret"], "risk": bench["risk"]}])

    xs = list(o["cloud"]["risk"].quantile([0.0, 1.0])) + list(idx["risk"]) + [bench["risk"]] + list(fr["risk"])
    ys = list(o["cloud"]["ret"].quantile([0.0, 1.0])) + list(idx["ret"]) + [bench["ret"]] + list(fr["ret"])
    if nxt:
        land = pd.DataFrame([
            {"key": k, "name": MIX_NAMES[k] + " · next", "ret": v[0], "risk": v[1],
             "ret0": (o["mix"][k][0] if k != "bench" else bench["ret"]),
             "risk0": (o["mix"][k][1] if k != "bench" else bench["risk"]),
             "color": MIX_COLORS[k]}
            for k, v in o["landed"].items() if k in ("best", "bench")])
        xs += list(land["risk"])
        ys += list(land["ret"])
        if "fwd_frontier" in o:
            xs += list(o["fwd_frontier"]["risk"])
            ys += list(o["fwd_frontier"]["ret"])
    xd, yd = _domain(xs), _domain(ys, min_pad=1.5)

    x = alt.X("risk:Q", title="Risk (volatility a year)",
              scale=alt.Scale(domain=xd, nice=False, zero=False),
              axis=alt.Axis(labelExpr=PCT, grid=True, tickMinStep=1))
    y = alt.Y("ret:Q", title="Average return a year",
              scale=alt.Scale(domain=yd, nice=False, zero=False),
              axis=alt.Axis(labelExpr=PCT, tickMinStep=1))
    tip_pt = [alt.Tooltip("name:N", title=" "),
              alt.Tooltip("ret:Q", title="Return a year %", format=".1f"),
              alt.Tooltip("risk:Q", title="Risk %", format=".1f")]

    cloud = alt.Chart(o["cloud"]).mark_circle(size=9, color=CLOUD, opacity=0.45).encode(x=x, y=y)
    layers = [cloud]

    if nxt and "fwd_frontier" in o:
        nf = o["fwd_frontier"].copy()
        layers.append(alt.Chart(nf).mark_line(color=NAVY, strokeDash=[5, 4], strokeWidth=1.6,
                                              opacity=0.55, interpolate="monotone").encode(
            x=x, y=y, order="risk:Q"))
        end = nf.iloc[-1:]
        layers.append(alt.Chart(end.assign(t="Frontier the next years offered")).mark_text(
            align="left", dx=6, dy=10, fontSize=11, color=NAVY, opacity=0.75).encode(x=x, y=y, text="t:N"))

    hover = alt.selection_point(on="pointerover", nearest=True, fields=["risk"],
                                empty=False, clear="pointerout")
    line = alt.Chart(fr).mark_line(color=NAVY, strokeWidth=3, interpolate="monotone").encode(
        x=x, y=y, order="risk:Q")
    fr_pts = alt.Chart(fr).mark_circle(size=70, color=NAVY).encode(
        x=x, y=y,
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("ret:Q", title="Return a year %", format=".1f"),
                 alt.Tooltip("risk:Q", title="Risk %", format=".1f"),
                 alt.Tooltip("mix:N", title="Mix")],
    ).add_params(hover)
    layers += [line, fr_pts]

    layers.append(alt.Chart(idx).mark_circle(size=70, color=SLATE, opacity=0.9).encode(
        x=x, y=y, tooltip=tip_pt))
    layers.append(alt.Chart(idx_lab).mark_text(align="left", dx=8, dy=-1, fontSize=11.5,
                                           color=SLATE).encode(x=x, y=y, text="name:N"))
    layers.append(alt.Chart(bdf).mark_point(shape="diamond", filled=True, size=170,
                                            color=GREY, opacity=1).encode(x=x, y=y, tooltip=tip_pt))
    layers.append(alt.Chart(bdf).mark_text(align="left", dx=10, dy=1, fontSize=12, fontWeight=600,
                                           color="#5F6873").encode(x=x, y=y, text="name:N"))

    if nxt:
        land = land.copy()
        seg = pd.DataFrame({"risk": land["risk0"], "ret": land["ret0"],
                            "risk2": land["risk"], "ret2": land["ret"], "color": land["color"]})
        layers.append(alt.Chart(seg).mark_rule(strokeDash=[2, 3], strokeWidth=1.4, opacity=0.8).encode(
            x=x, y=y, x2="risk2:Q", y2="ret2:Q", color=alt.Color("color:N", scale=None)))
        layers.append(alt.Chart(land).mark_point(shape="circle", filled=False, size=170,
                                                 strokeWidth=2.2, opacity=1).encode(
            x=x, y=y, color=alt.Color("color:N", scale=None),
            tooltip=[alt.Tooltip("name:N", title=" "),
                     alt.Tooltip("ret:Q", title="Return a year %", format=".1f"),
                     alt.Tooltip("risk:Q", title="Risk %", format=".1f")]))
        layers.append(alt.Chart(land[land["key"] == "best"].assign(t="where it landed")).mark_text(
            align="left", dx=11, dy=12, fontSize=11, fontStyle="italic", color=RUST).encode(
            x=x, y=y, text="t:N"))

    layers.append(alt.Chart(mixes).mark_point(shape="M0,-1.1L0.32,-0.32L1.1,-0.32L0.48,0.15L0.7,0.95L0,0.47L-0.7,0.95L-0.48,0.15L-1.1,-0.32L-0.32,-0.32Z",
                                              filled=True, size=420, opacity=1, strokeWidth=0).encode(
        x=x, y=y, color=alt.Color("color:N", scale=None),
        tooltip=[alt.Tooltip("name:N", title=" "),
                 alt.Tooltip("ret:Q", title="Return a year %", format=".1f"),
                 alt.Tooltip("risk:Q", title="Risk %", format=".1f"),
                 alt.Tooltip("mix:N", title="Mix")]))
    for k, align, dx, dy in (("best", "right", -14, -12), ("low", "right", -12, 18)):
        layers.append(alt.Chart(mixes[mixes["key"] == k]).mark_text(
            align=align, dx=dx, dy=dy, fontSize=12.5, fontWeight=600).encode(
            x=x, y=y, text="name:N", color=alt.Color("color:N", scale=None)))

    return alt.layer(*layers).properties(width="container", height=470)


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

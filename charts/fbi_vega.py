"""
Interactive charts for FBI Intelligence (Vega-Lite via Altair).

One house style: Inter type, no frame, faint horizontal grid, lines
labelled at their right end instead of a legend, and a hover crosshair
that shows every series' value on that date. Benchmark is always grey.
"""

import altair as alt
import numpy as np
import pandas as pd

from core.fbi_metrics import pretty_name

INK = "#1B2533"
MUTED = "#6B7480"
FAINT = "#9AA3AE"
GRID = "#EEF0F3"
ZERO = "#C9CFD6"
COLOR_A = "#1F4E79"
COLOR_B = "#C08A2E"
COLOR_BENCH = "#A3ABB5"
SERIES_COLORS = [COLOR_A, COLOR_B]
GOOD_ZONE = "#EEF5EA"
GOOD_TEXT = "#5B7A4E"

FONT = "Inter, sans-serif"
HEIGHT = 340
LABEL_PAD = 190


@alt.theme.register("prism", enable=True)
def _prism_theme():
    return alt.theme.ThemeConfig({
        "config": {
            "font": FONT,
            "background": "white",
            "view": {"stroke": None},
            "axis": {
                "labelColor": MUTED, "labelFontSize": 11.5, "labelFont": FONT,
                "titleColor": MUTED, "titleFontSize": 11.5, "titleFont": FONT,
                "titleFontWeight": 500, "domain": False, "ticks": False,
                "gridColor": GRID, "labelPadding": 8,
            },
            "axisX": {"grid": False},
            "legend": {"disable": True},
            "text": {"font": FONT, "fontSize": 12},
        }
    })


def _scale(names, benchmark):
    colors, i = [], 0
    for n in names:
        if n == benchmark:
            colors.append(COLOR_BENCH)
        else:
            colors.append(SERIES_COLORS[i])
            i += 1
    return alt.Scale(domain=[pretty_name(n) for n in names], range=colors)


def _long(wide, names):
    df = wide[names].copy()
    df.columns = [pretty_name(c) for c in names]
    df.index.name = "date"
    return df.reset_index().melt("date", var_name="series", value_name="value")


def _thin(wide):
    """Weekly points beyond ~3 years keep charts fast without visible loss."""
    span = (wide.index[-1] - wide.index[0]).days
    return wide.resample("W-FRI").last().dropna(how="all") if span > 365 * 3 else wide


def _end_labels(wide, names, benchmark, fmt, y_range):
    rows = []
    for n in names:
        s = wide[n].dropna()
        rows.append({"date": s.index[-1], "value": s.iloc[-1],
                     "series": pretty_name(n), "is_bench": n == benchmark})
    rows.sort(key=lambda r: r["value"])
    gap = (y_range[1] - y_range[0]) * 0.07
    last = None
    for r in rows:
        r["y"] = r["value"] if last is None else max(r["value"], last + gap)
        last = r["y"]
        r["label"] = f"{r['series']}  {fmt(r['value'])}"
    return pd.DataFrame(rows)


def _line_chart(wide, names, benchmark, y_title, y_format, label_fmt,
                zero_line=None, y_label_expr=None):
    wide = _thin(wide)
    data = _long(wide, names)
    scale = _scale(names, benchmark)
    bench_name = pretty_name(benchmark)
    lo, hi = float(data["value"].min()), float(data["value"].max())

    if y_label_expr:
        y_axis = alt.Axis(labelExpr=y_label_expr, title=None, tickCount=6)
    else:
        y_axis = alt.Axis(format=y_format or ",.0f", title=None, tickCount=6)

    first, last_d = wide.index[0], wide.index[-1]
    span_days = (last_d - first).days
    x_end = last_d + pd.Timedelta(days=int(span_days * 0.27))
    step = 1 if span_days < 365 * 7 else 2 if span_days < 365 * 14 else 4
    years_ticks = [y for y in range(first.year + 1, last_d.year + 1) if y % step == 0]
    if span_days < 365 * 2:
        x_axis = alt.Axis(format="%b %Y", tickCount=6, values=[
            alt.DateTime(year=d.year, month=d.month, date=1)
            for d in pd.date_range(first, last_d, freq="QS")])
    else:
        x_axis = alt.Axis(format="%Y", values=[alt.DateTime(year=y) for y in years_ticks])
    base = alt.Chart(data).encode(
        x=alt.X("date:T", title=None, axis=x_axis,
                scale=alt.Scale(domain=[alt.DateTime(year=first.year, month=first.month, date=first.day),
                                        alt.DateTime(year=x_end.year, month=x_end.month, date=x_end.day)])),
        y=alt.Y("value:Q", axis=y_axis, scale=alt.Scale(zero=False, nice=True)),
        color=alt.Color("series:N", scale=scale),
    )
    lines = base.mark_line(interpolate="monotone").encode(
        strokeWidth=alt.condition(alt.datum.series == bench_name,
                                  alt.value(1.5), alt.value(2.2)),
    )

    nearest = alt.selection_point(nearest=True, on="pointerover",
                                  fields=["date"], empty=False, clear="pointerout")
    tooltip = [alt.Tooltip("date:T", title="Date", format="%d %b %Y")] + [
        alt.Tooltip(field=pretty_name(n), type="quantitative",
                    format=label_fmt.tooltip)
        for n in names
    ]
    rule = alt.Chart(data).transform_pivot(
        "series", value="value", groupby=["date"]
    ).mark_rule(color="#8A939E", strokeDash=[3, 3]).encode(
        x="date:T",
        opacity=alt.condition(nearest, alt.value(0.8), alt.value(0)),
        tooltip=tooltip,
    ).add_params(nearest)
    dots = base.mark_circle(size=46).encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0))
    ).transform_filter(nearest)

    labels_df = _end_labels(wide, names, benchmark, label_fmt.label, (lo, hi))
    labels = alt.Chart(labels_df).mark_text(
        align="left", dx=8, fontSize=12, fontWeight=500
    ).encode(
        x="date:T", y="y:Q", text="label:N",
        color=alt.Color("series:N", scale=scale),
    )

    layers = [lines, rule, dots, labels]
    if zero_line is not None:
        layers.insert(0, alt.Chart(pd.DataFrame({"y": [zero_line]})).mark_rule(
            color=ZERO, strokeWidth=1).encode(y="y:Q"))
    return alt.layer(*layers).properties(
        width="container", height=HEIGHT,
    )


class _Fmt:
    def __init__(self, label, tooltip):
        self.label = label
        self.tooltip = tooltip


def _rupees(v):
    return f"₹{v / 1e7:.2f} Cr" if v >= 1e7 else f"₹{v / 1e5:.1f}L"


def _pct0(v):
    return f"{v:.0f}%".replace("-", "−")


# ---------------------------------------------------------------------
# Public charts
# ---------------------------------------------------------------------

def growth_chart(window, names, benchmark, start_value=1e5):
    growth = window[names] / window[names].iloc[0] * start_value
    return _line_chart(
        growth, names, benchmark, None, None,
        _Fmt(_rupees, ",.0f"), zero_line=start_value,
        y_label_expr="'₹' + format(datum.value / 100000, '.1f') + 'L'",
    )


def rolling_chart(rolling, names, benchmark):
    return _line_chart(
        rolling, names, benchmark, None, None,
        _Fmt(_pct0, ".1f"), zero_line=0,
        y_label_expr="format(datum.value, '.0f') + '%'",
    )


def drawdown_chart(window, names, benchmark):
    dd = pd.DataFrame({
        n: (window[n] / window[n].cummax() - 1) * 100 for n in names
    })
    return _line_chart(
        dd, names, benchmark, None, None,
        _Fmt(_pct0, ".1f"), zero_line=0,
        y_label_expr="format(datum.value, '.0f') + '%'",
    )


def calendar_chart(cal, names, benchmark, partial_year):
    df = cal[names].copy()
    df.columns = [pretty_name(c) for c in names]
    df.index = [f"{y} YTD" if y == partial_year else str(y) for y in df.index]
    df.index.name = "year"
    data = df.reset_index().melt("year", var_name="series", value_name="value")
    data["partial"] = data["year"].str.endswith("YTD")
    scale = _scale(names, benchmark)
    order = [pretty_name(n) for n in names]
    bars = alt.Chart(data).mark_bar(cornerRadiusEnd=2).encode(
        x=alt.X("year:N", title=None, sort=list(df.index),
                axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("series:N", sort=order),
        y=alt.Y("value:Q", title=None,
                axis=alt.Axis(labelExpr="format(datum.value, '.0f') + '%'")),
        color=alt.Color("series:N", scale=scale),
        opacity=alt.condition(alt.datum.partial, alt.value(0.45), alt.value(1)),
        tooltip=[alt.Tooltip("year:N", title="Year"),
                 alt.Tooltip("series:N", title="Index"),
                 alt.Tooltip("value:Q", title="Return %", format=".1f")],
    )
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=ZERO).encode(y="y:Q")
    return alt.layer(zero, bars).properties(width="container", height=300)


def capture_chart(points, benchmark):
    """points: list of (name, downside, upside, color)."""
    df = pd.DataFrame(
        [{"name": pretty_name(n), "down": d, "up": u, "color": c}
         for n, d, u, c in points]
        + [{"name": pretty_name(benchmark), "down": 100.0, "up": 100.0,
            "color": COLOR_BENCH}]
    )
    xs, ys = df["down"], df["up"]
    pad_x = max(15, (xs.max() - xs.min()) * 0.35)
    pad_y = max(15, (ys.max() - ys.min()) * 0.35)
    x_dom = [float(xs.min() - pad_x), float(xs.max() + pad_x)]
    y_dom = [float(ys.min() - pad_y), float(ys.max() + pad_y)]
    xs_ = alt.Scale(domain=x_dom, nice=False, zero=False)
    ys_ = alt.Scale(domain=y_dom, nice=False, zero=False)
    x = alt.X("down:Q", scale=xs_, title="Downside capture (lower is better)",
              axis=alt.Axis(labelExpr="datum.value + '%'", grid=True))
    y = alt.Y("up:Q", scale=ys_, title="Upside capture (higher is better)",
              axis=alt.Axis(labelExpr="datum.value + '%'"))
    zone = alt.Chart(pd.DataFrame(
        {"down": [x_dom[0]], "down2": [100.0], "up": [100.0], "up2": [y_dom[1]]}
    )).mark_rect(color=GOOD_ZONE).encode(x=x, x2="down2", y=y, y2="up2")
    zone_txt = alt.Chart(pd.DataFrame(
        {"down": [x_dom[0]], "up": [y_dom[1]], "t": ["Gains more, loses less"]}
    )).mark_text(align="left", baseline="top", dx=10, dy=10,
                 color=GOOD_TEXT, fontSize=12).encode(x=x, y=y, text="t")
    vline = alt.Chart(pd.DataFrame({"down": [100.0]})).mark_rule(color=ZERO).encode(x=x)
    hline = alt.Chart(pd.DataFrame({"up": [100.0]})).mark_rule(color=ZERO).encode(y=y)
    pts = alt.Chart(df).mark_circle(size=220, opacity=1).encode(
        x=x, y=y, color=alt.Color("color:N", scale=None),
        tooltip=[alt.Tooltip("name:N", title="Index"),
                 alt.Tooltip("up:Q", title="Upside capture %", format=".0f"),
                 alt.Tooltip("down:Q", title="Downside capture %", format=".0f")],
    )
    txt = alt.Chart(df).mark_text(align="left", dx=12, dy=-2, fontSize=12.5,
                                  fontWeight=500).encode(
        x=x, y=y, text="name:N", color=alt.Color("color:N", scale=None))
    return alt.layer(zone, zone_txt, vline, hline, pts, txt).properties(width="container", height=380)


def risk_return_chart(points, benchmark, highlight, label_names):
    """points: DataFrame index=name, cols Return, Volatility."""
    df = points.copy()
    df["name"] = [pretty_name(n) for n in df.index]
    df["role"] = "other"
    df.loc[df.index == benchmark, "role"] = "bench"
    for i, h in enumerate(highlight):
        if h in df.index and h != benchmark:
            df.loc[h, "role"] = f"pick{i}"
    always = [n for n in list(highlight) + [benchmark] if n in df.index]
    xr = df["Volatility"].max() - df["Volatility"].min()
    yr = df["Return"].max() - df["Return"].min()
    shown = list(always)
    for n in label_names:
        if n in df.index and n not in shown and not any(
            abs(df.loc[n, "Volatility"] - df.loc[t, "Volatility"]) < xr * 0.12
            and abs(df.loc[n, "Return"] - df.loc[t, "Return"]) < yr * 0.07
            for t in shown
        ):
            shown.append(n)
    df["show_label"] = df.index.isin(shown)
    b = points.loc[benchmark]
    x_dom = [float(df["Volatility"].min() - 1), float(df["Volatility"].max() + 1)]
    y_dom = [float(df["Return"].min() - 1.5), float(df["Return"].max() + 1.5)]

    role_scale = alt.Scale(domain=["other", "bench", "pick0", "pick1"],
                           range=["#BCC4CE", "#5F6873", COLOR_A, COLOR_B])
    x = alt.X("Volatility:Q", title="Volatility, annualised",
              scale=alt.Scale(domain=x_dom, nice=False, zero=False),
              axis=alt.Axis(labelExpr="format(datum.value, '.0f') + '%'", grid=True,
                            tickMinStep=1))
    y = alt.Y("Return:Q", title="Return, annualised",
              scale=alt.Scale(domain=y_dom, nice=False, zero=False),
              axis=alt.Axis(labelExpr="format(datum.value, '.0f') + '%'",
                            tickMinStep=1))
    zone = alt.Chart(pd.DataFrame(
        {"Volatility": [x_dom[0]], "v2": [float(b["Volatility"])],
         "Return": [float(b["Return"])], "r2": [y_dom[1]]}
    )).mark_rect(color=GOOD_ZONE).encode(x=x, x2="v2", y=y, y2="r2")
    zone_txt = alt.Chart(pd.DataFrame(
        {"Volatility": [x_dom[0]], "Return": [y_dom[1]],
         "t": [f"More return, less risk than {pretty_name(benchmark)}"]}
    )).mark_text(align="left", baseline="top", dx=10, dy=10, color=GOOD_TEXT,
                 fontSize=12).encode(x=x, y=y, text="t")
    vline = alt.Chart(pd.DataFrame({"Volatility": [float(b["Volatility"])]})).mark_rule(color=ZERO).encode(x=x)
    hline = alt.Chart(pd.DataFrame({"Return": [float(b["Return"])]})).mark_rule(color=ZERO).encode(y=y)

    hover = alt.selection_point(on="pointerover", nearest=True, fields=["name"],
                                empty=False, clear="pointerout")
    dots = alt.Chart(df).mark_point(filled=True, opacity=1).encode(
        x=x, y=y,
        color=alt.Color("role:N", scale=role_scale),
        shape=alt.condition(alt.datum.role == "bench", alt.value("diamond"),
                            alt.value("circle")),
        size=alt.when(hover).then(alt.value(200))
                .when(alt.datum.role == "other").then(alt.value(60))
                .otherwise(alt.value(150)),
        tooltip=[alt.Tooltip("name:N", title="Index"),
                 alt.Tooltip("Return:Q", title="Return %", format=".1f"),
                 alt.Tooltip("Volatility:Q", title="Volatility %", format=".1f")],
    ).add_params(hover)
    labels = alt.Chart(df[df["show_label"]]).mark_text(
        align="left", dx=9, dy=-7, fontSize=12, fontWeight=500
    ).encode(x=x, y=y, text="name:N",
             color=alt.Color("role:N", scale=role_scale))
    hover_label = alt.Chart(df).mark_text(
        align="left", dx=9, dy=-7, fontSize=12, fontWeight=500, color=INK
    ).encode(x=x, y=y, text="name:N").transform_filter(hover)
    return alt.layer(zone, zone_txt, vline, hline, dots, labels,
                     hover_label).properties(width="container", height=440)

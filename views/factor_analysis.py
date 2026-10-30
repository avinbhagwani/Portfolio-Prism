"""
Factor Analysis: split a mutual fund (or a portfolio of funds) into the
factors behind its returns, in the same style as FBI Intelligence.

  Controls   one fund or a portfolio, the factor model, the period
  Headline   how much the factors explain, the main tilts, and alpha,
             in plain words
  Cards      explained by factors (R²), alpha a year, market beta, months
  Tabs       Exposures (bars with 95% ranges + what each one means),
             Over time (rolling exposures), Details (growth of the fund,
             full regression table, monthly returns)

Regressions use monthly returns with Newey-West standard errors
(core/analysis.py); factor data comes from the IndiaFactorLibrary.
"""

import pandas as pd
import streamlit as st

from charts import factor_vega as fvc
from charts import fbi_vega as fv
from core.analysis import fit, rolling
from core.config import FACTOR_LABELS, MODEL_CONFIG, get_model_config
from core.regression_stats import significance_stars, significance_text
from core.data import (
    fetch_fund_history,
    get_common_month_end_dates,
    get_monthly_returns,
    month_end_dates,
    search_funds,
)
from views.factor_indexes import CSS as FBI_CSS

MAX_FUNDS = 10
ROLL = {"1Y": 12, "2Y": 24, "3Y": 36, "5Y": 60}

# what a positive / negative exposure means, in plain words
MEANING = {
    "MKT_RF": ("moves with the market", "moves against the market"),
    "SMB": ("small companies", "large companies"),
    "HML": ("value stocks", "growth stocks"),
    "RMW": ("highly profitable companies", "less profitable companies"),
    "CMA": ("companies that invest conservatively", "companies that invest aggressively"),
    "WML": ("recent winners (momentum)", "recent losers"),
    "TERM_IN": ("longer-duration bonds", "shorter-duration bonds"),
    "CREDIT_IN": ("corporate credit risk", "safer, government-like credit"),
}

CSS = """
<style>
.fa-cards {display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin:1.4rem 0 0.4rem 0;}
.fa-card {border:1px solid #E6E9ED; border-radius:10px; padding:14px 18px 16px 18px; background:#fff;}
.fa-card small {display:block; font-size:0.78rem; color:#8A939E; font-weight:500; margin-bottom:6px;}
.fa-card b {font-size:1.9rem; font-weight:600; color:#1B2533; letter-spacing:-0.02em;
  font-variant-numeric:tabular-nums;}
.fa-card span {display:block; font-size:0.82rem; color:#6B7480; margin-top:4px;}
.fa-card span.good {color:#2E7D4F;} .fa-card span.bad {color:#B54A3C;}
.fa-table {width:100%; border-collapse:collapse; font-size:0.92rem; margin-top:0.6rem;}
.fa-table th {text-align:left; font-weight:500; color:#8A939E; font-size:0.76rem; letter-spacing:0.04em;
  text-transform:uppercase; padding:8px 10px; border-bottom:1px solid #E6E9ED;}
.fa-table td {padding:11px 10px; border-bottom:1px solid #F0F2F5; color:#1B2533; vertical-align:top;
  font-variant-numeric:tabular-nums;}
.fa-table td.muted {color:#8A939E;}
.fa-pill {display:inline-block; font-size:0.74rem; font-weight:600; padding:2px 9px; border-radius:999px;}
.fa-pill.strong {background:#E8F0F8; color:#1F4E79;} .fa-pill.some {background:#F1F4F7; color:#4A5562;}
.fa-pill.weak {background:#F6F7F8; color:#9AA3AE;}
.fa-total {font-size:0.9rem; font-weight:500; margin:0.4rem 0 0 0;}
.fa-total.ok {color:#2E7D4F;} .fa-total.bad {color:#B54A3C;}
.fa-empty {color:#6B7480; font-size:0.98rem; margin:1.6rem 0;}
</style>
"""


def _short(name):
    """'XYZ Small Cap Fund - Direct Plan - Growth' -> 'XYZ Small Cap Fund'."""
    return name.split(" - ")[0].strip() if name else name


def _seed_from_link():
    """Home's example-fund chips link here with ?fund=<search>; fill the
    search box once per link so the visitor lands one click from a result."""
    term = st.query_params.get("fund")
    if term and st.session_state.get("_fa_seeded") != term:
        st.session_state["fa_q"] = term
        st.session_state["_fa_seeded"] = term


def render():
    _seed_from_link()
    st.markdown(FBI_CSS + CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='fbi-eyebrow'>Factor Analysis</div>"
        "<div class='fbi-title'>What really drives a fund's returns?</div>"
        "<div class='fbi-sub'>Split any Indian mutual fund, or a portfolio of funds, into the "
        "factors behind its returns: the market, size, value, profitability, investment and "
        "momentum. Then see what's left over: the manager's alpha.</div>",
        unsafe_allow_html=True,
    )

    with st.container(key="controls_fa"):
        c1, c2 = st.columns([1.4, 3], vertical_alignment="bottom")
        with c1:
            mode = st.segmented_control("Analyse", ["One fund", "Portfolio"], default="One fund",
                                        key="fa_mode") or "One fund"
        with c2:
            models = list(MODEL_CONFIG)
            model_name = st.selectbox("Factor model", models,
                                      index=models.index("Fama-French 5 Factor Model + Momentum"),
                                      key="fa_model")
        model_key = MODEL_CONFIG[model_name]["key"]
        inputs = _fund_inputs() if mode == "One fund" else _portfolio_inputs()

    if inputs is None:
        return
    returns, name, extra = inputs
    result = fit(returns, model_key)
    if result is None:
        st.markdown("<p class='fa-empty'>Not enough months where the fund and the factor data overlap. "
                    "Try a longer period.</p>", unsafe_allow_html=True)
        return

    _headline(result, name, model_key)
    _cards(result, model_key)
    t1, t2, t3 = st.tabs(["Exposures", "Over time", "Details"])
    with t1:
        _exposures(result)
    with t2:
        _over_time(result)
    with t3:
        _details(result, name, extra)
    st.markdown(
        "<p class='fbi-source'>Equity factors: IndiaFactorLibrary (Invespar), built as described in "
        "Raju, R., <i>Four and Five-Factor Models in the Indian Equities Market</i> (2022, "
        "<a href='https://ssrn.com/abstract=4054146'>SSRN 4054146</a>). Fixed income model: TERM_IN and "
        "CREDIT_IN benchmark-exposure proxies. NAVs from mfapi.in. Monthly returns; Newey-West standard "
        "errors.</p>",
        unsafe_allow_html=True,
    )


# =====================================================================
# Inputs
# =====================================================================

def _dates_row(dates, key):
    d1, d2, d3 = st.columns([1.5, 1.5, 1.2], vertical_alignment="bottom")
    with d1:
        start = st.selectbox("From", dates, index=0, format_func=lambda x: x.strftime("%b %Y"),
                             key=f"{key}_start")
    with d2:
        end = st.selectbox("To", dates, index=len(dates) - 1, format_func=lambda x: x.strftime("%b %Y"),
                           key=f"{key}_end")
    with d3:
        if st.button("Run analysis", type="primary", key=f"{key}_run", width="stretch"):
            st.session_state[f"{key}_ran"] = True
    return start, end


def _fund_inputs():
    term = st.text_input("Fund", placeholder="Type at least 3 letters of a fund name", key="fa_q")
    matches = search_funds(term)
    if not term or len(term.strip()) < 3:
        st.caption("Search by any part of the name, for example “parag flexi” or “nifty 50 index”.")
        return None
    if not matches:
        st.caption("No funds found. Try another name.")
        return None
    options = {f"{m['name']}  ·  {m['code']}": m for m in matches}
    choice = st.selectbox("Choose the plan", list(options), key="fa_pick")
    fund = options[choice]
    history = fetch_fund_history(fund["code"])
    dates = month_end_dates(history)
    if len(dates) < 2:
        st.caption("Couldn't load enough NAV history for this fund just now. Try again in a minute.")
        return None
    start, end = _dates_row(dates, "fa_one")
    if not st.session_state.get("fa_one_ran"):
        return None
    if start >= end:
        st.caption("“From” needs to be before “To”.")
        return None
    returns = get_monthly_returns(fund["code"], start, end)
    nav = history.set_index("date")["nav"]
    nav = nav[(nav.index >= start) & (nav.index <= end + pd.Timedelta(days=1))]
    return returns, _short(fund["name"]), {"nav": nav, "fund": fund["name"]}


def _portfolio_inputs():
    n = st.session_state.setdefault("fa_n", 3)
    st.caption("Add up to 10 funds. Weights must add up to 100%. The portfolio is rebalanced to these "
               "weights every month.")
    picked = []
    for i in range(n):
        a, b, c = st.columns([2.2, 4.2, 1.2], vertical_alignment="bottom")
        with a:
            term = st.text_input(f"Fund {i + 1}", key=f"fa_pq_{i}", placeholder="Search",
                                 label_visibility="visible" if i == 0 else "collapsed")
        matches = search_funds(term)
        with b:
            opts = {"—": None} | {f"{m['name']}  ·  {m['code']}": m for m in matches}
            pick = st.selectbox("Plan", list(opts), key=f"fa_pp_{i}",
                                label_visibility="visible" if i == 0 else "collapsed",
                                disabled=not matches)
        with c:
            w = st.number_input("Weight %", 0.0, 100.0, 0.0, 5.0, key=f"fa_pw_{i}",
                                label_visibility="visible" if i == 0 else "collapsed")
        if opts.get(pick) and w > 0:
            picked.append({**opts[pick], "weight": w})
    if n < MAX_FUNDS and st.button("Add a fund", key="fa_add", icon=":material/add:"):
        st.session_state["fa_n"] = n + 1
        st.rerun()

    # the same fund in two rows is one holding
    merged = {}
    for p in picked:
        merged.setdefault(p["code"], {**p, "weight": 0})["weight"] += p["weight"]
    picked = list(merged.values())
    total = sum(p["weight"] for p in picked)
    ok = abs(total - 100) < 0.001
    if picked:
        st.markdown(f"<p class='fa-total {'ok' if ok else 'bad'}'>Total weight {total:.1f}%"
                    f"{'' if ok else ' (needs to be 100%)'}</p>", unsafe_allow_html=True)
    if not picked:
        return None
    dates = get_common_month_end_dates([p["code"] for p in picked])
    if len(dates) < 2:
        st.caption("These funds don't share enough history. Try different funds.")
        return None
    start, end = _dates_row(dates, "fa_pf")
    if not st.session_state.get("fa_pf_ran"):
        return None
    if not ok or start >= end:
        st.caption("Fix the weights or dates above and the analysis will update.")
        return None
    series = []
    for p in picked:
        r = get_monthly_returns(p["code"], start, end)
        if r.empty:
            st.caption(f"Couldn't load returns for {_short(p['name'])} just now.")
            return None
        series.append(r.rename(p["code"]) * p["weight"] / 100)
    df = pd.concat(series, axis=1).dropna()
    if df.empty:
        st.caption("These funds have no months in common in this period.")
        return None
    returns = df.sum(axis=1).rename("Portfolio")
    return returns, "this portfolio", {"portfolio": picked, "returns": returns}


# =====================================================================
# Results
# =====================================================================

def _conf(p):
    if p < 0.01:
        return "strong", "Strong evidence"
    if p < 0.05:
        return "some", "Some evidence"
    return "weak", "Could be noise"


def _headline(res, name, model_key):
    m, data, factors = res["model"], res["data"], res["factors"]
    start, end = data.index.min(), data.index.max()
    equity = get_model_config(model_key)["asset_class"] == "Equity"
    r2 = m.rsquared * 100
    who = name if name == "this portfolio" else f"<b>{name}</b>"
    text = (f"From {start:%b %Y} to {end:%b %Y}, these factors explain <b>{r2:.0f}%</b> of "
            f"{who}'s monthly returns.")
    tilts = [f for f in factors if f != "MKT_RF" and m.pvalues[f] < 0.05]
    tilts.sort(key=lambda f: -abs(m.params[f]))
    if tilts:
        pos = [MEANING[f][0] for f in tilts if m.params[f] > 0][:2]
        neg = [MEANING[f][1] for f in tilts if m.params[f] < 0][:2]
        bits = pos + neg
        text += f" It leans toward {_join(bits)}."
    elif equity:
        text += " Beyond the market itself, it shows no clear style tilt."
    a, ap = m.params["const"] * 12, m.pvalues["const"]
    if ap < 0.05:
        text += (f" After all that, it {'added' if a > 0 else 'lost'} about <b>{abs(a):.1f}% a year</b> "
                 f"that the factors can't explain, and that's statistically meaningful.")
    else:
        text += (f" What's left over, about {a:+.1f}% a year, is within the range of luck."
                 .replace("-", "−"))
    st.markdown(f"<p class='fbi-headline'>{text}</p>", unsafe_allow_html=True)


def _join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _cards(res, model_key):
    m, data = res["model"], res["data"]
    a, ap = m.params["const"] * 12, m.pvalues["const"]
    equity = get_model_config(model_key)["asset_class"] == "Equity"
    lead = "MKT_RF" if equity else res["factors"][0]
    beta = m.params[lead]
    beta_note = (f"Moves about {beta * 100:.0f}% as much as the market" if equity
                 else f"{FACTOR_LABELS[lead]} exposure")
    cls, conf = _conf(ap)
    cards = [
        ("Explained by factors", f"{m.rsquared * 100:.0f}%", "R² of the regression", ""),
        ("Alpha", f"{a:+.1f}%".replace("-", "−"), f"A year · {conf.lower()}",
         "good" if ap < 0.05 and a > 0 else "bad" if ap < 0.05 else ""),
        ("Market beta" if equity else FACTOR_LABELS[lead], f"{beta:.2f}", beta_note, ""),
        ("Months analysed", f"{len(data)}", f"{data.index.min():%b %Y} to {data.index.max():%b %Y}", ""),
    ]
    html = "".join(f"<div class='fa-card'><small>{t}</small><b>{v}</b><span class='{c}'>{s}</span></div>"
                   for t, v, s, c in cards)
    st.markdown(f"<div class='fa-cards'>{html}</div>", unsafe_allow_html=True)


def _exposures(res):
    m, factors = res["model"], res["factors"]
    rows = []
    for f in ["const"] + factors:          # alpha first, as in the original chart
        c, se, p = m.params[f], m.bse[f], m.pvalues[f]
        rows.append({"label": FACTOR_LABELS.get(f, f), "coef": c, "lo": c - 1.96 * se,
                     "hi": c + 1.96 * se, "sig": p < 0.05,
                     "stars": significance_stars(p), "sig_text": significance_text(p)})
    st.markdown("<p class='fbi-label'>Alpha (monthly %) and exposure to each factor, with 95% confidence ranges</p>",
                unsafe_allow_html=True)
    st.vega_lite_chart(fvc.exposure_chart(rows).to_dict(), theme=None, width="stretch")
    st.markdown("<p class='fbi-note'>Coloured bars are statistically significant; grey ones could be "
                "noise. A bar whose range crosses zero isn't reliably different from no exposure.</p>",
                unsafe_allow_html=True)

    body = []
    for f in factors:
        c, p = m.params[f], m.pvalues[f]
        cls, conf = _conf(p)
        if f == "MKT_RF":
            what = f"Moves about {c * 100:.0f}% as much as the market"
        elif p < 0.05:
            what = f"Tilts toward {MEANING[f][0] if c > 0 else MEANING[f][1]}"
        else:
            what = "No reliable tilt either way"
        body.append(f"<tr><td><b>{FACTOR_LABELS.get(f, f)}</b></td><td>{c:+.2f}</td><td>{what}</td>"
                    f"<td><span class='fa-pill {cls}'>{conf}</span></td></tr>".replace("+-", "−").replace("-0.", "−0."))
    a, ap = m.params["const"], m.pvalues["const"]
    cls, conf = _conf(ap)
    body.append(f"<tr><td><b>Alpha</b></td><td>{a * 12:+.1f}% a year</td><td>Return the factors don't "
                f"explain ({a:+.2f}% a month)</td><td><span class='fa-pill {cls}'>{conf}</span></td></tr>"
                .replace("+-", "−"))
    st.markdown("<p class='fbi-label'>What each exposure means</p>"
                "<table class='fa-table'><thead><tr><th>Factor</th><th>Exposure</th><th>In plain words</th>"
                f"<th>Confidence</th></tr></thead><tbody>{''.join(body)}</tbody></table>",
                unsafe_allow_html=True)


def _over_time(res):
    data, factors = res["data"], res["factors"]
    win = st.segmented_control("Window", list(ROLL), default="3Y", key="fa_roll") or "3Y"
    months = ROLL[win]
    if len(data) < months + 6:
        st.markdown(f"<p class='fa-empty'>Needs at least {months + 6} months of data for "
                    f"{win} rolling windows; this period has {len(data)}.</p>", unsafe_allow_html=True)
        return
    rdf = rolling(data, tuple(factors), months)
    if rdf is None or rdf.empty:
        st.markdown("<p class='fa-empty'>Couldn't fit the rolling windows for this period.</p>",
                    unsafe_allow_html=True)
        return
    lead = factors[0]
    lo, hi = rdf[lead].min(), rdf[lead].max()
    steady = [FACTOR_LABELS[f] for f in factors[1:] if (rdf[f"{f}_P"] < 0.05).mean() >= 0.7]
    text = (f"Across {len(rdf)} rolling {win.replace('Y', '-year')} windows, its "
            f"{FACTOR_LABELS[lead].lower()} exposure ranged from {lo:.2f} to {hi:.2f}.")
    if steady:
        text += f" {_join(steady)} {'was' if len(steady) == 1 else 'were'} significant in most windows."
    else:
        text += " No style tilt was consistently significant."
    st.markdown(f"<p class='fbi-headline'>{text}</p>", unsafe_allow_html=True)
    items = [(f, FACTOR_LABELS.get(f, f)) for f in factors] + [("Alpha", "Alpha (monthly %)")]
    st.vega_lite_chart(fvc.rolling_chart(rdf, items).to_dict(), theme=None)
    st.markdown("<p class='fbi-note'>Each point is one window ending that month. The shaded band is "
                "the 95% confidence range; darker points are statistically significant.</p>",
                unsafe_allow_html=True)


def _details(res, name, extra):
    if "nav" in extra and len(extra["nav"]) > 2:
        growth = extra["nav"].to_frame(_short(extra["fund"]))
        st.markdown("<p class='fbi-label'>Growth of ₹1 lakh</p>", unsafe_allow_html=True)
        st.vega_lite_chart(fv.growth_chart(growth, list(growth.columns), "").to_dict(),
                           theme=None, width="stretch")
    elif "returns" in extra:
        r = extra["returns"] / 100
        first = r.index.min() - pd.offsets.MonthEnd(1)
        growth = pd.concat([pd.Series([1.0], index=[first]), (1 + r).cumprod()]).to_frame("Portfolio")
        st.markdown("<p class='fbi-label'>Growth of ₹1 lakh</p>", unsafe_allow_html=True)
        st.vega_lite_chart(fv.growth_chart(growth, ["Portfolio"], "").to_dict(), theme=None, width="stretch")
        rows = "".join(f"<tr><td>{_short(p['name'])}</td><td>{p['weight']:.1f}%</td></tr>"
                       for p in extra["portfolio"])
        st.markdown("<p class='fbi-label'>Holdings</p><table class='fa-table'><thead><tr><th>Fund</th>"
                    f"<th>Weight</th></tr></thead><tbody>{rows}</tbody></table>", unsafe_allow_html=True)

    m = res["model"]
    rows = []
    for key in ["const"] + res["factors"]:
        label = "Alpha (monthly %)" if key == "const" else FACTOR_LABELS.get(key, key)
        rows.append(f"<tr><td>{label}</td><td>{m.params[key]:.4f}</td><td>{m.bse[key]:.4f}</td>"
                    f"<td>{m.tvalues[key]:.2f}</td><td>{m.pvalues[key]:.4f}</td></tr>")
    st.markdown("<p class='fbi-label'>Full regression</p><table class='fa-table'><thead><tr><th>Term</th>"
                "<th>Coefficient</th><th>Std. error</th><th>t-stat</th><th>p-value</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table>", unsafe_allow_html=True)
    st.markdown(f"<p class='fbi-note'>R² {m.rsquared:.3f}, adjusted R² {m.rsquared_adj:.3f}, "
                f"{len(res['data'])} months. Newey-West standard errors with {res['lags']} lags, which "
                f"allow for autocorrelation in monthly returns.</p>", unsafe_allow_html=True)
    with st.expander("Monthly returns used"):
        d = res["data"][["Fund_Return", "Excess_Fund_Return"]].rename(
            columns={"Fund_Return": "Return %", "Excess_Fund_Return": "Excess over risk-free %"})
        d.index = d.index.strftime("%b %Y")
        st.dataframe(d.round(3), width="stretch")

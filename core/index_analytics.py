"""
Calculation layer shared by the FBI Intelligence (factor index) tool and
the Drawdown Analysis tool. Everything here takes/returns plain
DataFrames/Series — no Streamlit calls — so it can be tested or reused
on its own.

All functions assume `levels_df` is a DataFrame of raw index price
levels (as loaded via core.index_data.get_index_levels), one column per
index, indexed by date, with NaN before an index's launch date.
"""

import pandas as pd


# ---------------------------------------------------------------------
# Annual returns
# ---------------------------------------------------------------------

def annual_returns(levels_df):
    """
    Calendar-year total return (%) per index: (year-end level / prior
    year-end level - 1) * 100. The first year in an index's history is
    dropped since there's no prior year-end to compare against.
    """
    if levels_df.empty:
        return pd.DataFrame()

    year_end = levels_df.resample("YE").last()
    returns = year_end.pct_change().dropna(how="all") * 100
    returns.index = returns.index.year

    return returns


def build_quilt(annual_df, start_year=None, end_year=None):
    """
    Reshape year x index calendar returns (from annual_returns) into a
    rank x year grid for the Quilt chart: row 1 is that year's best
    performer, row 2 the second-best, etc. Each cell is (index_name,
    return) or None if fewer indices had data that year than the
    tallest column needs.
    """
    if annual_df.empty:
        return pd.DataFrame()

    df = annual_df.copy()

    if start_year is not None:
        df = df[df.index >= start_year]
    if end_year is not None:
        df = df[df.index <= end_year]

    if df.empty:
        return pd.DataFrame()

    row_counts = df.notna().sum(axis=1)
    max_rank = int(row_counts.max()) if row_counts.max() > 0 else 0

    if max_rank == 0:
        return pd.DataFrame()

    columns = {}

    for year in df.index:
        ranked = df.loc[year].dropna().sort_values(ascending=False)
        cells = list(ranked.items())
        cells += [None] * (max_rank - len(cells))
        columns[year] = cells

    quilt = pd.DataFrame(columns)
    quilt.index = range(1, max_rank + 1)

    return quilt


# ---------------------------------------------------------------------
# Rolling returns
# ---------------------------------------------------------------------

def rolling_returns(levels_df, window_years):
    """
    Rolling annualised (CAGR) return (%) per index, computed on
    month-end levels. For a 1-year window this is just the trailing
    12-month return; for longer windows it's annualised so different
    windows are visually comparable on the same axis.
    """
    if levels_df.empty:
        return pd.DataFrame()

    monthly = levels_df.resample("ME").last()
    months = int(window_years * 12)

    ratio = monthly / monthly.shift(months)
    cagr = (ratio.pow(1 / window_years) - 1) * 100

    return cagr.dropna(how="all")


def rolling_outperformance(rolling_df, index_a, index_b):
    """
    Head-to-head comparison of two indices' rolling return series:
    how many rolling periods each one led in, and by how much on
    average when it did.
    """
    paired = rolling_df[[index_a, index_b]].dropna()

    if paired.empty:
        return None

    diff = paired[index_a] - paired[index_b]

    total = len(diff)
    wins_a = int((diff > 0).sum())
    wins_b = int((diff < 0).sum())
    ties = int((diff == 0).sum())

    return {
        "total_periods": total,
        "wins_a": wins_a,
        "wins_b": wins_b,
        "ties": ties,
        "pct_a": (wins_a / total * 100) if total else 0.0,
        "pct_b": (wins_b / total * 100) if total else 0.0,
        "avg_margin_when_a_leads": diff[diff > 0].mean() if wins_a else 0.0,
        "avg_margin_when_b_leads": (-diff[diff < 0]).mean() if wins_b else 0.0,
        "diff_series": diff,
    }


# ---------------------------------------------------------------------
# Rolling volatility
# ---------------------------------------------------------------------

def rolling_std(levels_df, window_years):
    """
    Rolling annualised volatility (%) per index, computed from monthly
    returns over the trailing window_years. Uses the same monthly-return
    convention as rolling_returns so the two line up on the same dates.
    """
    if levels_df.empty:
        return pd.DataFrame()

    monthly_levels = levels_df.resample("ME").last()
    monthly_returns = monthly_levels.pct_change() * 100

    months = int(window_years * 12)

    rolling_vol = (
        monthly_returns.rolling(months).std() * (12 ** 0.5)
    )

    return rolling_vol.dropna(how="all")


# ---------------------------------------------------------------------
# Drawdowns
# ---------------------------------------------------------------------

def drawdown_series(levels_df):
    """Running drawdown (%) from each index's own running peak."""
    if levels_df.empty:
        return levels_df

    result = {}
    for col in levels_df.columns:
        series = levels_df[col].dropna()
        if series.empty:
            continue
        running_max = series.cummax()
        result[col] = (series / running_max - 1) * 100

    return pd.DataFrame(result)


def drawdown_summary(levels_df):
    """Max drawdown and current drawdown per index, with dates."""
    dd = drawdown_series(levels_df)

    if dd.empty:
        return pd.DataFrame()

    rows = []
    for col in dd.columns:
        series = dd[col].dropna()
        if series.empty:
            continue

        trough_date = series.idxmin()

        rows.append({
            "Index": col,
            "Max Drawdown (%)": series.min(),
            "Max Drawdown Date": trough_date,
            "Current Drawdown (%)": series.iloc[-1],
        })

    return pd.DataFrame(rows).set_index("Index")


# ---------------------------------------------------------------------
# Upside / downside capture
# ---------------------------------------------------------------------

def capture_ratios(levels_df, index_names, benchmark_name, lookback_years=None):
    """
    Upside and downside capture ratio (%) for each name in index_names
    against benchmark_name, using monthly returns (Morningstar-style
    cumulative-return methodology):

      Upside Capture   = cumulative return of the index during months
                          the benchmark was UP, divided by the
                          benchmark's cumulative return over those same
                          months.
      Downside Capture = the same, over months the benchmark was DOWN.

    >100% upside capture means the index gained more than the
    benchmark during the benchmark's up months; <100% downside capture
    means the index lost less than the benchmark during its down
    months — both are the "good" direction.

    lookback_years bounds the comparison to the trailing N years; over
    multi-decade full-history windows the cumulative compounding makes
    ratios blow up to unhelpfully large numbers, so a lookback (e.g. 3
    or 5 years) is the more meaningful default for this metric.

    Indices equal to the benchmark itself are skipped. Returns a
    DataFrame indexed by index name; a row's ratios are NaN if there
    weren't enough up/down months in the overlap to compute one.
    """
    if levels_df.empty or benchmark_name not in levels_df.columns:
        return pd.DataFrame()

    levels = levels_df

    if lookback_years is not None:
        cutoff = levels.index.max() - pd.DateOffset(years=lookback_years)
        levels = levels[levels.index >= cutoff]

    monthly = levels.resample("ME").last()
    monthly_returns = monthly.pct_change() * 100

    def cum_return(series):
        return (1 + series / 100).prod() - 1

    rows = []

    for name in index_names:
        if name == benchmark_name or name not in monthly_returns.columns:
            continue

        paired = monthly_returns[[name, benchmark_name]].dropna()

        if paired.empty:
            continue

        up = paired[paired[benchmark_name] >= 0]
        down = paired[paired[benchmark_name] < 0]

        up_capture = float("nan")
        if not up.empty:
            bench_cum = cum_return(up[benchmark_name])
            if bench_cum != 0:
                up_capture = cum_return(up[name]) / bench_cum * 100

        down_capture = float("nan")
        if not down.empty:
            bench_cum = cum_return(down[benchmark_name])
            if bench_cum != 0:
                down_capture = cum_return(down[name]) / bench_cum * 100

        rows.append({
            "Index": name,
            "Upside Capture (%)": up_capture,
            "Downside Capture (%)": down_capture,
            "Up Months": len(up),
            "Down Months": len(down),
        })

    return pd.DataFrame(rows).set_index("Index")


def find_drawdown_episodes(levels_df, column, top_n=5):
    """
    Identify the top_n worst distinct drawdown episodes for one index:
    each episode's peak date/value, trough date/value, depth, and
    recovery date (None if the index hasn't recovered to its prior
    peak yet).
    """
    series = levels_df[column].dropna()

    if series.empty:
        return []

    running_max = series.cummax()
    dd = (series / running_max - 1) * 100

    episodes = []
    in_drawdown = False
    peak_date = series.index[0]
    peak_value = series.iloc[0]
    trough_date = None
    trough_value = None

    for date, value, dd_value, peak_now in zip(
        series.index, series.values, dd.values, running_max.values
    ):
        if dd_value < 0:
            if not in_drawdown:
                in_drawdown = True
                trough_date = date
                trough_value = value
            elif value < trough_value:
                trough_date = date
                trough_value = value

            # peak_now tracks the running max, i.e. the peak this
            # drawdown started from
            if peak_now != peak_value:
                # running max moved before the drawdown deepened past
                # it — shouldn't happen mid-drawdown, but guard anyway
                pass

        else:
            if in_drawdown:
                # recovered — close out the episode
                episodes.append({
                    "peak_date": peak_date,
                    "peak_value": peak_value,
                    "trough_date": trough_date,
                    "trough_value": trough_value,
                    "depth_pct": (trough_value / peak_value - 1) * 100,
                    "recovery_date": date,
                })
                in_drawdown = False

            peak_date = date
            peak_value = value

    if in_drawdown:
        # still underwater as of the last observation
        episodes.append({
            "peak_date": peak_date,
            "peak_value": peak_value,
            "trough_date": trough_date,
            "trough_value": trough_value,
            "depth_pct": (trough_value / peak_value - 1) * 100,
            "recovery_date": None,
        })

    episodes.sort(key=lambda e: e["depth_pct"])

    return episodes[:top_n]


# ---------------------------------------------------------------------
# Risk / return scatter
# ---------------------------------------------------------------------

def risk_return_points(levels_df, lookback_years=None):
    """
    Annualised return (%) and annualised volatility (%) per index,
    computed from monthly returns. If lookback_years is given, only
    the trailing N years of each index's history are used; otherwise
    each index's full available history is used (so indices with
    different launch dates are each measured "since inception").
    Indices with fewer than 3 monthly observations in the window are
    skipped as not meaningful.
    """
    if levels_df.empty:
        return pd.DataFrame()

    levels = levels_df

    if lookback_years is not None:
        cutoff = levels.index.max() - pd.DateOffset(years=lookback_years)
        levels = levels[levels.index >= cutoff]

    monthly = levels.resample("ME").last()
    monthly_returns = monthly.pct_change() * 100

    rows = []

    for col in monthly.columns:
        series = monthly_returns[col].dropna()

        if len(series) < 3:
            continue

        total_growth = (1 + series / 100).prod()
        years = len(series) / 12

        ann_return = (
            (total_growth ** (1 / years) - 1) * 100
            if years > 0 else float("nan")
        )
        ann_vol = series.std() * (12 ** 0.5)

        rows.append({
            "Index": col,
            "Return": ann_return,
            "Volatility": ann_vol,
            "Observations": len(series),
        })

    return pd.DataFrame(rows).set_index("Index")

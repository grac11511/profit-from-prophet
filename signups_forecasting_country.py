"""
Prophet Signup Forecasting Pipeline (Python).
 
Produces daily/monthly signup forecasts by country, region, user type,
signup channel, and platform.  Use ``forecast_parameter_table()`` for a
DataFrame of loop hyperparameters.  For notebooks, ``run_country_and_region_forecasts(state, data)``
runs all Prophet fits in one call (same as ``main()``).  Outputs match the companion R script:
  - All_F xlsx
  - Signups_Extract csv
  - Regressor CSVs (WeeklyMS, DailyMS, ClassDays)
 
Dependencies:
    pip install pandas numpy prophet matplotlib openpyxl
 
Environment variables:
    SIGNUPS_SHOW_PLOTS=1   -- matplotlib forecast for every model in each loop (verbose)
    SIGNUPS_STAN_VERBOSE=1 -- show cmdstanpy INFO (chain start/end) on every fit
"""
from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from itertools import product
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from prophet import Prophet


def _configure_stan_logging() -> None:
    """CmdStanPy logs INFO for every chain — hundreds of lines in Jupyter. Default: quiet."""
    level = (
        logging.INFO
        if os.environ.get("SIGNUPS_STAN_VERBOSE", "").lower() in ("1", "true", "yes")
        else logging.WARNING
    )
    for name in ("cmdstanpy", "stan"):
        logging.getLogger(name).setLevel(level)


_configure_stan_logging()

# ==========================================================================
# Configuration
# ==========================================================================
 
INPUT_DIRECTORY = (
    "/Users/grac/Library/CloudStorage/Box-Box/Internal Reporting (CPL)/FP&A/"
    "Modelling/03. MAU/07. Prophet Model/02. Prophet Inputs/"
)
OUTPUT_DIRECTORY = (
    "/Users/grac/Library/CloudStorage/Box-Box/Internal Reporting (CPL)/FP&A/"
    "Modelling/03. MAU/07. Prophet Model/03. Prophet Outputs/"
)
 
FILENAMES = {
    "holidays":  "2026.01.05 collated_holidays.csv",
    "campaigns": "2025.06.04 Campaigns.csv",
    "classdays": "2025.09.03 Class Days.csv",
    "outliers":  "2025.06.04 Outliers.csv",
    "signups":   "2026.03.02 Signups.csv",
    "ms_af_w":   "2026.03.02 Looker_MS_AF_W.csv",
    "ms_a_d":    "2026.03.02 Looker_MS_A_D.csv",
    "ms_f_m":    "2026.03.02 MS_F_M.csv",
}
 
D_ACTUAL_START   = pd.Timestamp("2022-01-01")
D_MS_ATOF        = pd.Timestamp("2026-02-28")
M_SCENARIO       = "202601"
D_FORECAST_START = D_MS_ATOF + pd.Timedelta(days=1)
D_FORECAST_END   = D_FORECAST_START + pd.Timedelta(days=364)
 
TODAY_TEXT  = pd.Timestamp.now().strftime("%Y.%m.%d")
SHOW_PLOTS = os.environ.get("SIGNUPS_SHOW_PLOTS", "").lower() in ("1", "true")

# Country / region lists (insertion-order preserved, matching R's union())
COUNTRY_SN = ["TR", "US", "CA", "AU", "UK", "BR", "JP", "IN", "ID", "PH",
               "FR", "DE", "ES", "IT", "MX"]
COUNTRY_FN = ["Turkey", "United States of America", "Canada", "Australia",
               "United Kingdom", "Brazil", "Japan", "India", "Indonesia",
               "Philippines", "France", "Germany", "Spain", "Italy", "Mexico"]
 
REGION_SN = ["SA", "EU", "LA", "ME", "SU"]
REGION_FN = ["SEA", "Europe", "LATAM", "MENAP", "Sub-Saharan Africa"]
 
KR_SN = ["VN", "KR", "TH", "PL", "NL"]
KR_FN = ["Vietnam", "South Korea", "Thailand", "Poland", "Netherlands"]
 
# Preserve insertion order (like R union(union(country, region), kr))
SN_LIST = list(dict.fromkeys(COUNTRY_SN + REGION_SN + KR_SN))
 
# Model / extract definitions
MODEL_LIST = {
    "M11": "_EDU_ORG_WEB", "M12": "_EDU_ORG_IOS", "M13": "_EDU_ORG_AND",
    "M14": "_EDU_MAR_WEB", "M17": "_NON_ORG_WEB", "M18": "_NON_ORG_IOS",
    "M19": "_NON_ORG_AND", "M20": "_NON_MAR_WEB",
}
EXCL_MODEL_LIST = {"M14": "_EDU_MAR_WEB", "M20": "_NON_MAR_WEB"}
 
EXT_SUFFIXES = [
    "EDU_ORG_WEB", "EDU_ORG_IOS", "EDU_ORG_AND", "EDU_MAR_WEB",
    "NON_ORG_WEB", "NON_ORG_IOS", "NON_ORG_AND", "NON_MAR_WEB",
]
 
# Filter definitions for signup splits
SPLIT_FILTERS: Dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "TSU":         lambda d: d,
    "EDU":         lambda d: d[d["CUSTOMER_TYPE"] == "Edu"],
    "ORG":         lambda d: d[d["SIGNUP_SOURCE"] == "organic"],
    "MAR":         lambda d: d[d["SIGNUP_SOURCE"] == "marketing"],
    "EDU_ORG":     lambda d: d[(d["CUSTOMER_TYPE"] == "Edu") & (d["SIGNUP_SOURCE"] == "organic")],
    "EDU_ORG_WEB": lambda d: d[(d["CUSTOMER_TYPE"] == "Edu") & (d["SIGNUP_SOURCE"] == "organic") & (d["PLATFORM"] == "web")],
    "EDU_ORG_IOS": lambda d: d[(d["CUSTOMER_TYPE"] == "Edu") & (d["SIGNUP_SOURCE"] == "organic") & (d["PLATFORM"] == "iOS")],
    "EDU_ORG_AND": lambda d: d[(d["CUSTOMER_TYPE"] == "Edu") & (d["SIGNUP_SOURCE"] == "organic") & (d["PLATFORM"] == "Android")],
    "EDU_MAR_WEB": lambda d: d[(d["CUSTOMER_TYPE"] == "Edu") & (d["SIGNUP_SOURCE"] == "marketing") & (d["PLATFORM"] == "web")],
    "NON":         lambda d: d[d["CUSTOMER_TYPE"] == "NonEdu"],
    "NON_ORG_WEB": lambda d: d[(d["CUSTOMER_TYPE"] == "NonEdu") & (d["SIGNUP_SOURCE"] == "organic") & (d["PLATFORM"] == "web")],
    "NON_ORG_IOS": lambda d: d[(d["CUSTOMER_TYPE"] == "NonEdu") & (d["SIGNUP_SOURCE"] == "organic") & (d["PLATFORM"] == "iOS")],
    "NON_ORG_AND": lambda d: d[(d["CUSTOMER_TYPE"] == "NonEdu") & (d["SIGNUP_SOURCE"] == "organic") & (d["PLATFORM"] == "Android")],
    "NON_MAR_WEB": lambda d: d[(d["CUSTOMER_TYPE"] == "NonEdu") & (d["SIGNUP_SOURCE"] == "marketing") & (d["PLATFORM"] == "web")],
}
 
# Region name mappings for extracts
ACTUALS_REGION_MAP = {
    r"\bUnited States of America\b": "US",
    r"\bUnited Kingdom\b": "UK",
}
FORECAST_REGION_MAP = {
    r"\bUnited States of America\b": "US",
    r"\bCA\b": "Canada", r"\bAU\b": "Australia", r"\bJP\b": "Japan",
    r"\bKR\b": "South Korea", r"\bIN\b": "India", r"\bID\b": "Indonesia",
    r"\bPH\b": "Philippines", r"\bVN\b": "Vietnam", r"\bTH\b": "Thailand",
    r"\bSA\b": "SEA", r"\bBR\b": "Brazil", r"\bMX\b": "Mexico",
    r"\bLA\b": "LATAM", r"\bUnited Kingdom\b": "UK",
    r"\bFR\b": "France", r"\bES\b": "Spain", r"\bIT\b": "Italy",
    r"\bME\b": "MENAP", r"\bMiddle_East_Africa\b": "MENAP",
    r"\bEU\b": "Europe", r"\bSU\b": "Sub-Saharan Africa",
    r"\bDE\b": "Germany", r"\bTR\b": "Turkey",
    r"\bPL\b": "Poland", r"\bNL\b": "Netherlands",
}
 
 
# ==========================================================================
# State container (replaces R's global assign/get pattern)
# ==========================================================================
 
@dataclass
class RunState:
    """Holds all models, forecasts, intermediate frames, and extracts."""
    models: Dict[str, Prophet] = field(default_factory=dict)
    forecasts: Dict[str, pd.DataFrame] = field(default_factory=dict)
    frames: Dict[str, pd.DataFrame] = field(default_factory=dict)
    extracts: Dict[str, pd.DataFrame] = field(default_factory=dict)
    all_f: Optional[pd.DataFrame] = None
 
 
@dataclass
class PipelineData:
    """All imported and pre-cleaned data."""
    su: pd.DataFrame
    su_a: pd.DataFrame
    holidays: pd.DataFrame
    campaigns: pd.DataFrame
    classdays: pd.DataFrame
    ms_af_w: pd.DataFrame
    ms_a_d: pd.DataFrame
    ms_f_m: pd.DataFrame
 
 
# ==========================================================================
# Build model name lists
# ==========================================================================
 
def build_model_names() -> Tuple[List[str], List[str], List[str]]:
    """Return (model_names, a_list, f_list) with R-compatible ordering."""
    model_names: List[str] = []
    for mid, sfx in MODEL_LIST.items():
        for ctry in SN_LIST:
            model_names.append(f"{mid}_R3_{ctry}{sfx}")
 
    excl: List[str] = []
    for mid, sfx in EXCL_MODEL_LIST.items():
        for ctry in REGION_SN:
            excl.append(f"{mid}_R3_{ctry}{sfx}")
    model_names = [m for m in model_names if m not in excl]
 
    a_list: List[str] = []
    for sfx in MODEL_LIST.values():
        for ctry in SN_LIST:
            a_list.append(f"{ctry}{sfx}_A")
    excl_a: List[str] = []
    for sfx in EXCL_MODEL_LIST.values():
        for ctry in REGION_SN:
            excl_a.append(f"{ctry}{sfx}_A")
    a_list = [a for a in a_list if a not in excl_a]
 
    f_list = [f"{m}_F" for m in model_names]
    return model_names, a_list, f_list
 
 
# ==========================================================================
# Single parameterised Prophet forecast
# ==========================================================================
 
def prophet_forecast(
    name: str,
    actuals: pd.DataFrame,
    regressors: pd.DataFrame,
    holidays: pd.DataFrame,
    state: RunState,
    *,
    regressor_specs: Optional[Dict[str, bool]] = None,
    multiplicative: bool = False,
    merge_train: bool = True,
    changepoint_range: float = 0.7,
    weekly_seasonality: float = 4,
    yearly_seasonality: float = 9.5,
    seasonality_prior_scale: float = 10,
) -> None:
    """
    Fit a Prophet model and store results in *state*.
 
    Parameters
    ----------
    regressor_specs : dict mapping regressor name -> standardize value.
        Use False for no standardisation (e.g. perMar, DperMar).
        Use 'auto' (the default when omitted) otherwise.
    changepoint_range : float – Prophet changepoint.range parameter.
    weekly_seasonality : float – weekly seasonality fourier order.
    yearly_seasonality : float – yearly seasonality fourier order.
    seasonality_prior_scale : float – Prophet seasonality.prior.scale.
    """
    if regressor_specs is None:
        regressor_specs = {}
 
    # Build holidays frame for Prophet
    hol = None
    if holidays is not None and not holidays.empty:
        hol = holidays[["holiday", "ds"]].copy()
        hol["ds"] = pd.to_datetime(hol["ds"]).dt.normalize()
 
    kw = dict(
        changepoint_range=changepoint_range,
        daily_seasonality=False,
        weekly_seasonality=weekly_seasonality,
        yearly_seasonality=yearly_seasonality,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=seasonality_prior_scale,
        holidays_prior_scale=10,
    )
    if hol is not None:
        kw["holidays"] = hol
    if multiplicative:
        kw["seasonality_mode"] = "multiplicative"
 
    m = Prophet(**kw)
 
    for reg_name, standardize in regressor_specs.items():
        m.add_regressor(reg_name, standardize=standardize)
 
    # Training data
    if merge_train:
        train = regressors.merge(actuals[["ds", "y"]], on="ds", how="left")
    else:
        train = actuals[["ds", "y"]].copy()
 
    m.fit(train)
    fc = m.predict(regressors)
    fc["yhat"] = fc["yhat"].clip(lower=0)
 
    state.models[name] = m
    state.forecasts[f"{name}_F"] = fc
 
 
# ==========================================================================
# Data loading & cleaning
# ==========================================================================
 
def _input_path(key: str) -> str:
    return os.path.join(INPUT_DIRECTORY, FILENAMES[key])
 
 
def load_and_prepare_data() -> PipelineData:
    holidays  = pd.read_csv(_input_path("holidays"))
    campaigns = pd.read_csv(_input_path("campaigns"))
    classdays = pd.read_csv(_input_path("classdays"))
    outliers  = pd.read_csv(_input_path("outliers"))
    su        = pd.read_csv(_input_path("signups"))
    ms_af_w   = pd.read_csv(_input_path("ms_af_w"))
    ms_a_d    = pd.read_csv(_input_path("ms_a_d"))
    ms_f_m    = pd.read_csv(_input_path("ms_f_m"))
 
    # --- Signups ---
    su["REGIONS"] = su["REGIONS"].replace({"US": "United States of America",
                                           "UK": "United Kingdom"})
    mask = (su["REGIONS"].isin(["SEA", "Europe", "LATAM", "MENAP",
                                "Sub-Saharan Africa"])
            & (su["SIGNUP_SOURCE"] == "marketing"))
    su.loc[mask, "SIGNUP_SOURCE"] = "organic"
    su["DATE"] = pd.to_datetime(su["DATE"], format="%m/%d/%Y", errors="coerce")
 
    # --- Weekly Marketing Spend (parse dates BEFORE filling NAs) ---
    ms_af_w["ds"] = pd.to_datetime(ms_af_w["ds"], format="%m/%d/%Y", errors="coerce")
    ms_af_w["perMar"] = ms_af_w["perMar"].fillna(0)
    ms_af_w["Country"] = ms_af_w["Country"].str.replace("GB", "UK", regex=False)
 
    # --- Monthly Marketing Budget ---
    ms_f_m["MONTH"] = pd.to_datetime(ms_f_m["MONTH"], format="%m/%d/%Y", errors="coerce")
    ms_f_m = (ms_f_m.loc[ms_f_m["BUDGET"] == "Performance Marketing",
                         ["COUNTRY_NAME", "MONTH", "TARGET"]]
              .rename(columns={"TARGET": "perMar"}))
 
    # --- Daily Marketing Spend (parse dates BEFORE filling NAs) ---
    ms_a_d["ds"] = pd.to_datetime(ms_a_d["ds"], format="%m/%d/%Y", errors="coerce")
    ms_a_d["perMar"] = ms_a_d["perMar"].fillna(0)
    ms_a_d["Country"] = ms_a_d["Country"].str.replace("GB", "UK", regex=False)
 
    # --- Class Days (parse dates BEFORE filling NAs on numeric cols) ---
    classdays["ds"] = pd.to_datetime(classdays["ds"], format="%m/%d/%Y", errors="coerce")
    num_cols = [c for c in classdays.columns if c != "ds"]
    classdays[num_cols] = classdays[num_cols].fillna(0)
 
    # --- Holidays (parse once) ---
    holidays["ds"] = pd.to_datetime(holidays["ds"], format="%m/%d/%Y", errors="coerce")
    holidays = holidays[holidays["country"].notna()]
 
    # --- Campaigns (parse once; note 2-digit year in source) ---
    campaigns["ds"] = pd.to_datetime(campaigns["ds"], format="%m/%d/%y", errors="coerce")
 
    # --- Outliers ---
    outliers["DATE"] = pd.to_datetime(outliers["DATE"], format="%m/%d/%Y", errors="coerce")
    outliers["REGIONS"] = outliers["REGIONS"].replace(
        {"US": "United States of America", "UK": "United Kingdom"})
 
    # Remove outlier rows from actuals
    su_a = su.loc[su["DATE"] >= D_ACTUAL_START].copy()
    key_cols = ["DATE", "PLATFORM", "SIGNUP_SOURCE", "CUSTOMER_TYPE", "REGIONS"]
    su_a = (su_a.merge(outliers[key_cols].drop_duplicates(),
                       on=key_cols, how="left", indicator=True)
            .query("_merge == 'left_only'")
            .drop(columns=["_merge"]))
 
    return PipelineData(su=su, su_a=su_a, holidays=holidays, campaigns=campaigns,
                        classdays=classdays, ms_af_w=ms_af_w, ms_a_d=ms_a_d,
                        ms_f_m=ms_f_m)
 
 
# ==========================================================================
# Helpers for regressor building
# ==========================================================================
 
def _weekly_ms_to_daily(ms_af_w: pd.DataFrame, country_sn: str,
                        cutoff_date: pd.Timestamp) -> pd.DataFrame:
    """Weekly actuals -> daily (forward-fill, divide by 7), up to cutoff_date."""
    sub = (ms_af_w.loc[ms_af_w["Country"] == country_sn, ["ds", "perMar"]]
           .sort_values("ds").drop_duplicates("ds"))
    if sub.empty:
        return pd.DataFrame({"ds": pd.Series(dtype="datetime64[ns]"),
                              "perMar": pd.Series(dtype="float64")})
    idx = pd.date_range(sub["ds"].min(), sub["ds"].max(), freq="D")
    sub = sub.set_index("ds").reindex(idx).ffill().reset_index(names="ds")
    sub["perMar"] = sub["perMar"] / 7.0
    return sub[sub["ds"] <= cutoff_date].reset_index(drop=True)
 
 
def _monthly_budget_to_daily(ms_f_m: pd.DataFrame, country_fn: str,
                              tsu_df: pd.DataFrame,
                              cutoff_date: pd.Timestamp) -> pd.DataFrame:
    """Monthly budget -> per-day value, for dates > cutoff_date."""
    monthly_slice = ms_f_m.loc[ms_f_m["COUNTRY_NAME"] == country_fn].copy()
 
    if monthly_slice.empty:
        future = tsu_df.loc[tsu_df["ds"] > cutoff_date].copy()
        future["perMar"] = 0.0
        return future[["ds", "perMar"]]
 
    monthly_slice["MONTH"] = pd.to_datetime(monthly_slice["MONTH"])
    monthly_slice["month"] = monthly_slice["MONTH"].dt.to_period("M").dt.to_timestamp()
    monthly_slice["perMar"] = (pd.to_numeric(monthly_slice["perMar"], errors="coerce")
                                / monthly_slice["MONTH"].dt.days_in_month.astype(float))
    monthly_daily = monthly_slice[["month", "perMar"]].copy()
 
    future = tsu_df.loc[tsu_df["ds"] > cutoff_date].copy()
    future["month"] = future["ds"].dt.to_period("M").dt.to_timestamp()
    future = future.merge(monthly_daily, on="month", how="left")[["ds", "perMar"]]
    return future
 
 
# ==========================================================================
# Unified forecast loop
# ==========================================================================
 
def run_forecast_loop(
    state: RunState,
    data: PipelineData,
    *,
    category: str,
    country_sn: str,
    country_fn: str,
    split_suffixes: List[str],
    model_ids: List[str],
    regressor_specs: Optional[Dict[str, bool]] = None,
    multiplicative: bool = False,
    build_regressors: bool = True,
    changepoint_range: float = 0.7,
    weekly_seasonality: float = 4,
    yearly_seasonality: float = 9.5,
    seasonality_prior_scale: float = 10,
) -> None:
    """Run Prophet forecasts for one country/region across its model splits."""
    if regressor_specs is None:
        regressor_specs = {}
    print(f"Running forecast for {category}: {country_sn}")
 
    b_names = [f"{country_sn}_{sfx}" for sfx in split_suffixes]
    a_names = [f"{bn}_A" for bn in b_names]
    m_names = [f"{mid}_R3_{bn}" for mid, bn in zip(model_ids, b_names)]
    f_names = [f"{mn}_F" for mn in m_names]
 
    # ---- Signups by split ----
    su_country = (data.su_a.loc[data.su_a["REGIONS"] == country_fn]
                  .rename(columns={"DATE": "ds", "TOTAL_SIGNUPS": "y"})
                  .copy())
    state.frames[f"{country_sn}_SU_A"] = su_country
 
    for sfx, fn in SPLIT_FILTERS.items():
        state.frames[f"{country_sn}_{sfx}_A"] = fn(su_country)
 
    # Format actuals: fill date gaps, ensure boundary dates exist
    boundary_dates = [D_ACTUAL_START, D_MS_ATOF]
    for a_name in a_names:
        df = state.frames[a_name][["ds", "y"]].copy()
        df["ds"] = pd.to_datetime(df["ds"]).dt.normalize()
        df = df.groupby("ds", as_index=False)["y"].sum()
        for boundary in boundary_dates:
            if boundary not in df["ds"].values:
                df = pd.concat([df, pd.DataFrame({"ds": [boundary], "y": [np.nan]})],
                               ignore_index=True)
        df = df.sort_values("ds")
        idx = pd.date_range(df["ds"].min(), df["ds"].max(), freq="D")
        df = df.set_index("ds").reindex(idx).reset_index(names="ds")
        state.frames[a_name] = df
 
    # Filter to actuals period
    cutoff = D_FORECAST_START - pd.Timedelta(days=1)
    for bn in b_names:
        df_a = state.frames[f"{bn}_A"].loc[
            lambda d: d["ds"] <= cutoff
        ].copy().sort_values("ds")
        idx_b = pd.date_range(df_a["ds"].min(), df_a["ds"].max(), freq="D")
        df_a = df_a.set_index("ds").reindex(idx_b).reset_index(names="ds")
        state.frames[bn] = df_a
 
    # ---- Holidays ----
    holidays_f = (data.holidays
                  .loc[data.holidays["country"] == country_sn, ["holiday", "ds"]]
                  .copy())
 
    # ---- Regressor table ----
    tsu_df = pd.DataFrame({"ds": pd.date_range(D_ACTUAL_START, D_FORECAST_END, freq="D")})
 
    if build_regressors:
        reg = tsu_df.copy()
 
        # Campaigns
        reg = reg.merge(data.campaigns[["ds", "Campaigns"]], on="ds", how="left")
        reg["Campaigns"] = reg["Campaigns"].fillna(0)
 
        # Weekly Marketing Spend -> daily
        cc_ms_af_w = _weekly_ms_to_daily(data.ms_af_w, country_sn, D_MS_ATOF)
 
        # Monthly budget -> daily
        cc_ms_f_m = _monthly_budget_to_daily(data.ms_f_m, country_fn, tsu_df, D_MS_ATOF)
 
        # Merge via left_join + coalesce (matching R pattern)
        reg = (reg
               .merge(cc_ms_af_w, on="ds", how="left")
               .merge(cc_ms_f_m.rename(columns={"perMar": "perMar_F"}), on="ds", how="left"))
        reg["perMar"] = reg["perMar"].fillna(reg["perMar_F"]).fillna(0)
        reg = reg.drop(columns=["perMar_F"])
 
        # Daily Marketing Spend
        cc_ms_a_d = (data.ms_a_d
                     .loc[(data.ms_a_d["Country"] == country_sn)
                          & (data.ms_a_d["ds"] < D_FORECAST_START),
                          ["ds", "perMar"]]
                     .rename(columns={"perMar": "DperMar"}))
 
        reg = (reg
               .merge(cc_ms_a_d, on="ds", how="left")
               .merge(cc_ms_f_m.rename(columns={"perMar": "DperMar_F"}), on="ds", how="left"))
        reg["DperMar"] = reg["DperMar"].fillna(reg["DperMar_F"]).fillna(0)
        reg = reg.drop(columns=["DperMar_F"])
 
        # Class Days
        if country_sn in data.classdays.columns:
            cd = (data.classdays[["ds", country_sn]]
                  .rename(columns={country_sn: "ClassDays"}))
            reg = reg.merge(cd, on="ds", how="left")
            reg["ClassDays"] = reg["ClassDays"].fillna(0)
 
        regressor_tbl = reg
    else:
        regressor_tbl = tsu_df
 
    state.frames[f"{country_sn}_TSU_R"] = regressor_tbl
 
    # ---- Forecast each model ----
    for i, mn in enumerate(m_names):
        prophet_forecast(
            mn,
            state.frames[b_names[i]],
            regressor_tbl,
            holidays_f,
            state,
            regressor_specs=regressor_specs,
            multiplicative=multiplicative,
            merge_train=build_regressors,
            changepoint_range=changepoint_range,
            weekly_seasonality=weekly_seasonality,
            yearly_seasonality=yearly_seasonality,
            seasonality_prior_scale=seasonality_prior_scale,
        )
 
    # ---- Plots ----
    if SHOW_PLOTS:
        for i, mn in enumerate(m_names):
            fig = state.models[mn].plot(state.forecasts[f_names[i]])
            fig.suptitle(f"Forecast for {mn}")
            fig.axes[0].set_xlabel("Year")
            fig.axes[0].set_ylabel("Sign Ups")
            plt.tight_layout()
            plt.show()
 
 
# ==========================================================================
# Compile forecasts & build MAU extracts
# ==========================================================================
 
def compile_forecasts(state: RunState, model_names: List[str]) -> pd.DataFrame:
    """Combine yhat from every model into one wide table."""
    key0 = f"{model_names[0]}_F"
    if key0 not in state.forecasts:
        raise KeyError(
            f"{key0!r} not in state.forecasts — run the country and region forecast "
            "loop cells before compile_forecasts."
        )
    base = state.forecasts[key0][["ds"]].copy()
    for m in model_names:
        base[m] = state.forecasts[f"{m}_F"]["yhat"].values
    return base
 
 
def process_model_extracts(
    state: RunState, prefix: str,
    user_type: str, signup_channel: str, platform: str,
    scenario: str = M_SCENARIO,
) -> None:
    """Build per-model extract dataframes and store in state.extracts."""
    if state.all_f is None:
        raise ValueError(
            "state.all_f is missing — run compile_forecasts(state, model_names) first."
        )
    df = state.all_f
    col_names = [c for c in df.columns if c != "ds" and str(c).startswith(prefix)]
    pat = re.compile(rf"^{re.escape(prefix)}_R3_([A-Z]{{2}})")
    for col_name in col_names:
        m = pat.match(col_name)
        region = m.group(1) if m else None
        sub = (df[["ds", col_name]]
               .rename(columns={col_name: "Signups"})
               .assign(Region=region, UserType=user_type,
                       SignupChannel=signup_channel, Platform=platform,
                       Scenario=scenario))
        clean = re.sub(rf"^{prefix}_R3_", "", col_name)
        state.extracts[f"{clean}_EXT"] = sub
 
 
# ==========================================================================
# Export regressor tables
# ==========================================================================
 
def export_regressor_tables(data: PipelineData) -> None:
    """Write WeeklyMS, DailyMS, ClassDays CSVs for all countries."""
    all_pms, all_dpms, all_cd = [], [], []
 
    for cs, cf in zip(COUNTRY_SN, COUNTRY_FN):
        tsu = pd.DataFrame({"ds": pd.date_range(D_ACTUAL_START, D_FORECAST_END, freq="D")})
 
        # Weekly MS -> daily
        w = _weekly_ms_to_daily(data.ms_af_w, cs, D_MS_ATOF)
 
        # Monthly budget -> daily
        fm = _monthly_budget_to_daily(data.ms_f_m, cf, tsu, D_MS_ATOF)
        fm["perMar"] = fm["perMar"].fillna(0)
 
        # Merge via left_join + coalesce
        rtp = (tsu
               .merge(w, on="ds", how="left")
               .merge(fm.rename(columns={"perMar": "perMar_F"}), on="ds", how="left"))
        rtp["perMar"] = rtp["perMar"].fillna(rtp["perMar_F"]).fillna(0)
        rtp = rtp.drop(columns=["perMar_F"])[["ds", "perMar"]]
        rtp["country"] = cs
        all_pms.append(rtp)
 
        # Daily MS
        d = (data.ms_a_d
             .loc[(data.ms_a_d["Country"] == cs)
                  & (data.ms_a_d["ds"] < D_FORECAST_START),
                  ["ds", "perMar"]]
             .rename(columns={"perMar": "DperMar"}))
 
        rtd = (tsu
               .merge(d, on="ds", how="left")
               .merge(fm.rename(columns={"perMar": "DperMar_F"}), on="ds", how="left"))
        rtd["DperMar"] = rtd["DperMar"].fillna(rtd["DperMar_F"]).fillna(0)
        rtd = rtd.drop(columns=["DperMar_F"])[["ds", "DperMar"]]
        rtd["country"] = cs
        all_dpms.append(rtd)
 
        # Class Days
        if cs in data.classdays.columns:
            cdf = data.classdays[["ds", cs]].rename(columns={cs: "ClassDays"})
            rtc = tsu.merge(cdf, on="ds", how="left")
        else:
            rtc = tsu.copy()
            rtc["ClassDays"] = np.nan
        rtc["country"] = cs
        all_cd.append(rtc)
 
    pd.concat(all_pms, ignore_index=True).to_csv(
        os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_WeeklyMS_AllCountries.csv"), index=False)
    pd.concat(all_dpms, ignore_index=True).to_csv(
        os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_DailyMS_AllCountries.csv"), index=False)
    pd.concat(all_cd, ignore_index=True).to_csv(
        os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_ClassDays_AllCountries.csv"), index=False)
 
 
# ==========================================================================
# Apply region name replacements
# ==========================================================================
 
def _replace_regions(series: pd.Series, mapping: dict) -> pd.Series:
    s = series.astype(str)
    for pat, rep in mapping.items():
        s = s.str.replace(pat, rep, regex=True)
    return s
 
 
# ==========================================================================
# Forecast loop configs (single source for main + parameter table)
# ==========================================================================
 
COUNTRY_FORECAST_CONFIGS: List[dict] = [
    dict(category="Marketing",
         split_suffixes=["EDU_MAR_WEB", "NON_MAR_WEB"],
         model_ids=["M14", "M20"],
         regressor_specs={"DperMar": False, "Campaigns": "auto"},
         multiplicative=False,
         changepoint_range=0.78, weekly_seasonality=4,
         yearly_seasonality=12, seasonality_prior_scale=10),
    dict(category="Edu Organic (iOS, Android)",
         split_suffixes=["EDU_ORG_IOS", "EDU_ORG_AND"],
         model_ids=["M12", "M13"],
         regressor_specs={"perMar": False, "Campaigns": "auto", "ClassDays": "auto"},
         multiplicative=True,
         changepoint_range=0.80, weekly_seasonality=4,
         yearly_seasonality=12, seasonality_prior_scale=10),
    dict(category="Edu Organic (web)",
         split_suffixes=["EDU_ORG_WEB"],
         model_ids=["M11"],
         regressor_specs={"Campaigns": "auto", "ClassDays": "auto"},
         multiplicative=True,
         changepoint_range=0.80, weekly_seasonality=5,
         yearly_seasonality=12, seasonality_prior_scale=10),
    dict(category="NonEdu Organic (iOS, Android)",
         split_suffixes=["NON_ORG_IOS", "NON_ORG_AND"],
         model_ids=["M18", "M19"],
         regressor_specs={"perMar": False, "Campaigns": "auto", "ClassDays": "auto"},
         multiplicative=False,
         changepoint_range=0.76, weekly_seasonality=4,
         yearly_seasonality=9.5, seasonality_prior_scale=5),
    dict(category="NonEdu Organic (web)",
         split_suffixes=["NON_ORG_WEB"],
         model_ids=["M17"],
         regressor_specs={"Campaigns": "auto", "ClassDays": "auto"},
         multiplicative=False,
         changepoint_range=0.76, weekly_seasonality=3,
         yearly_seasonality=9.5, seasonality_prior_scale=5),
]
 
REGION_FORECAST_CONFIGS: List[dict] = [
    dict(sn=REGION_SN, fn=REGION_FN, category="Regions Education",
         split_suffixes=["EDU_ORG_WEB", "EDU_ORG_IOS", "EDU_ORG_AND"],
         model_ids=["M11", "M12", "M13"], multiplicative=True,
         changepoint_range=0.80, weekly_seasonality=4,
         yearly_seasonality=12, seasonality_prior_scale=10),
    dict(sn=REGION_SN, fn=REGION_FN, category="Regions NonEdu",
         split_suffixes=["NON_ORG_WEB", "NON_ORG_IOS", "NON_ORG_AND"],
         model_ids=["M17", "M18", "M19"], multiplicative=False,
         changepoint_range=0.76, weekly_seasonality=3,
         yearly_seasonality=9.5, seasonality_prior_scale=5),
    dict(sn=KR_SN, fn=KR_FN, category="KR Education",
         split_suffixes=["EDU_ORG_WEB", "EDU_ORG_IOS", "EDU_ORG_AND"],
         model_ids=["M11", "M12", "M13"], multiplicative=True,
         changepoint_range=0.80, weekly_seasonality=4,
         yearly_seasonality=12, seasonality_prior_scale=10),
    dict(sn=KR_SN, fn=KR_FN, category="KR NonEdu",
         split_suffixes=["EDU_MAR_WEB", "NON_ORG_WEB", "NON_ORG_IOS",
                         "NON_ORG_AND", "NON_MAR_WEB"],
         model_ids=["M14", "M17", "M18", "M19", "M20"],
         multiplicative=False,
         changepoint_range=0.76, weekly_seasonality=3,
         yearly_seasonality=9.5, seasonality_prior_scale=5),
]
 
 
def forecast_parameter_table() -> pd.DataFrame:
    """Tabular view of Prophet loop configs (country + region/KR)."""
    rows: List[dict] = []
    for cfg in COUNTRY_FORECAST_CONFIGS:
        rs = cfg.get("regressor_specs", {})
        rows.append({
            "scope": "country",
            "category": cfg["category"],
            "geography": f"each of {len(COUNTRY_SN)} countries",
            "split_suffixes": ", ".join(cfg["split_suffixes"]),
            "model_ids": ", ".join(cfg["model_ids"]),
            "regressor_specs": repr(rs) if rs else "",
            "multiplicative": cfg["multiplicative"],
            "changepoint_range": cfg["changepoint_range"],
            "weekly_seasonality": cfg["weekly_seasonality"],
            "yearly_seasonality": cfg["yearly_seasonality"],
            "seasonality_prior_scale": cfg["seasonality_prior_scale"],
            "build_regressors": True,
        })
    for cfg in REGION_FORECAST_CONFIGS:
        sn = cfg["sn"]
        rows.append({
            "scope": "region_kr",
            "category": cfg["category"],
            "geography": ", ".join(sn),
            "split_suffixes": ", ".join(cfg["split_suffixes"]),
            "model_ids": ", ".join(cfg["model_ids"]),
            "regressor_specs": "",
            "multiplicative": cfg["multiplicative"],
            "changepoint_range": cfg["changepoint_range"],
            "weekly_seasonality": cfg["weekly_seasonality"],
            "yearly_seasonality": cfg["yearly_seasonality"],
            "seasonality_prior_scale": cfg["seasonality_prior_scale"],
            "build_regressors": False,
        })
    return pd.DataFrame(rows)
 
 
def run_country_and_region_forecasts(
    state: RunState, data: PipelineData
) -> Tuple[float, float]:
    """Fit every Prophet country and region/KR model. Returns (country_s, region_kr_s) wall times."""
    fc_start = time.perf_counter()
    for cfg in COUNTRY_FORECAST_CONFIGS:
        for cs, cf in zip(COUNTRY_SN, COUNTRY_FN):
            run_forecast_loop(state, data, country_sn=cs, country_fn=cf,
                              build_regressors=True, **cfg)
    fc_time = time.perf_counter() - fc_start

    fr_start = time.perf_counter()
    for cfg_template in REGION_FORECAST_CONFIGS:
        cfg = dict(cfg_template)
        sn_list = cfg.pop("sn")
        fn_list = cfg.pop("fn")
        for cs, cf in zip(sn_list, fn_list):
            run_forecast_loop(state, data, country_sn=cs, country_fn=cf,
                              build_regressors=False, **cfg)
    fr_time = time.perf_counter() - fr_start
    return fc_time, fr_time
 
 
# ==========================================================================
# Main
# ==========================================================================
 
def main() -> None:
    t0 = time.perf_counter()
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
 
    model_names, _a_list, _f_list = build_model_names()
    data = load_and_prepare_data()
    state = RunState()
 
    print(f"Actuals to Forecast Date: {D_MS_ATOF.date()} | "
          f"Forecast Start: {D_FORECAST_START.date()} | "
          f"Forecast End: {D_FORECAST_END.date()}")
 
    fc_time, fr_time = run_country_and_region_forecasts(state, data)
 
    # ---- Compile forecasts ----
    all_f = compile_forecasts(state, model_names)
    all_f["ds"] = pd.to_datetime(all_f["ds"]).dt.normalize()
    state.all_f = all_f
 
    out_xlsx = os.path.join(OUTPUT_DIRECTORY,
                            f"{TODAY_TEXT}_Outputs_TSU_AllCountries_.xlsx")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        all_f.to_excel(w, sheet_name="All_F", index=False)
    print(f"Wrote {out_xlsx}")
 
    # ---- MAU extracts ----
    extract_configs = [
        ("M11", "Edu",    "organic",   "web"),
        ("M12", "Edu",    "organic",   "iOS"),
        ("M13", "Edu",    "organic",   "Android"),
        ("M14", "Edu",    "marketing", "web"),
        ("M17", "NonEdu", "organic",   "web"),
        ("M18", "NonEdu", "organic",   "iOS"),
        ("M19", "NonEdu", "organic",   "Android"),
        ("M20", "NonEdu", "marketing", "web"),
    ]
    for prefix, ut, sc, plat in extract_configs:
        process_model_extracts(state, prefix, ut, sc, plat)
 
    # Build extract name list (full minus excluded)
    all_ext = [f"{c}_{s}_EXT" for c, s in product(SN_LIST, EXT_SUFFIXES)]
    excl_ext = [f"{c}_{s}_EXT"
                for c, s in product(REGION_SN, ["EDU_MAR_WEB", "NON_MAR_WEB"])]
    all_ext = [x for x in all_ext if x not in excl_ext]
 
    # Actuals extract
    extract_a = (data.su
                 .rename(columns={"DATE": "ds", "REGIONS": "Region",
                                  "CUSTOMER_TYPE": "UserType", "PLATFORM": "Platform",
                                  "SIGNUP_SOURCE": "SignupChannel",
                                  "TOTAL_SIGNUPS": "Signups"})
                 .loc[lambda d: (d["ds"] >= D_ACTUAL_START) & (d["ds"] < D_FORECAST_START)]
                 .assign(Scenario=M_SCENARIO)
                 [["ds", "Region", "UserType", "Platform", "SignupChannel",
                   "Scenario", "Signups"]]
                 .rename(columns={"ds": "Date"}))
    extract_a["Region"] = _replace_regions(extract_a["Region"], ACTUALS_REGION_MAP)
 
    # Forecast extract
    ext_dfs = [state.extracts[n] for n in all_ext if n in state.extracts]
    if ext_dfs:
        extract_f = (pd.concat(ext_dfs, ignore_index=True)
                     .loc[lambda d: d["ds"] >= D_FORECAST_START]
                     .rename(columns={"ds": "Date"}))
    else:
        extract_f = pd.DataFrame(
            columns=["Date", "Signups", "Region", "UserType",
                     "SignupChannel", "Platform", "Scenario"])
    extract_f["Region"] = _replace_regions(extract_f["Region"], FORECAST_REGION_MAP)
 
    # Combine & aggregate to monthly
    extract_af = pd.concat([extract_a, extract_f], ignore_index=True)
    extract_af["EOM"] = extract_af["Date"] + pd.offsets.MonthEnd(0)
    extract_af = (extract_af
                  .groupby(["EOM", "Region", "UserType", "Platform",
                            "SignupChannel", "Scenario"], as_index=False)["Signups"]
                  .sum()
                  .rename(columns={"EOM": "Date"}))
    extract_af = extract_af[["Date", "Region", "UserType", "Platform",
                             "SignupChannel", "Scenario", "Signups"]]
 
    # Replace forecast-period zeros with 100
    mask_zero = (extract_af["Date"] > D_FORECAST_START) & (extract_af["Signups"] == 0)
    extract_af.loc[mask_zero, "Signups"] = 100
 
    extract_csv = os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_py_Signups_Extract.csv")
    extract_af.to_csv(extract_csv, index=False)
    print(f"Wrote {extract_csv}")
 
    # ---- Summary ----
    total = time.perf_counter() - t0
    n = max(len(model_names), 1)
    print(f"Done. Country models: {fc_time:.1f}s | Region models: {fr_time:.1f}s | "
          f"Total: {total:.1f}s ({total / n:.2f}s per model).")
 
    # ---- Regressor tables (all countries) ----
    export_regressor_tables(data)
 
 
if __name__ == "__main__":
    main()
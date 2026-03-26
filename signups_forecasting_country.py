"""
Python replica of signups_forecasting_country (R).

Multi-country / region Prophet signups pipeline with marketing regressors,
campaigns, class days, extracts for MAU, and regressor CSV exports.

Dependencies (see requirements-prophet.txt):
  pip install pandas numpy prophet matplotlib openpyxl

Set INPUT_DIRECTORY / OUTPUT_DIRECTORY (or edit defaults). Input filenames match
the R script (update dates in FILENAMES as you refresh data).

Environment:
  SIGNUPS_SHOW_PLOTS=1  — show matplotlib forecast plots (slow for many models)

Notes:
  - Yearly seasonality uses 10 Fourier terms (R used 9.5; Python expects int).
  - Coefficient extraction (_Co) is omitted; R output tab All_Co was commented.
  - End-of-script cross_validation / APE tables reference undefined *_APE_names
    in the R file; that block is not ported.
"""
from __future__ import annotations

import calendar
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from prophet import Prophet

# ---------------------------------------------------------------------------
# Config (edit paths / file stamps like the R script)
# ---------------------------------------------------------------------------
INPUT_DIRECTORY = os.path.expanduser(
    "/Users/grac/Library/CloudStorage/Box-Box/Internal Reporting (CPL)/FP&A/"
    "Modelling/03. MAU/07. Prophet Model/02. Prophet Inputs/"
)
OUTPUT_DIRECTORY = os.path.expanduser(
    "/Users/grac/Library/CloudStorage/Box-Box/Internal Reporting (CPL)/FP&A/"
    "Modelling/03. MAU/07. Prophet Model/03. Prophet Outputs/"
)

FILENAMES = {
    "holidays": "2026.01.05 collated_holidays.csv",
    "campaigns": "2025.06.04 Campaigns.csv",
    "classdays": "2025.09.03 Class Days.csv",
    "outliers": "2025.06.04 Outliers.csv",
    "signups": "2026.03.02 Signups.csv",
    "ms_af_w": "2026.03.02 Looker_MS_AF_W.csv",
    "ms_a_d": "2026.03.02 Looker_MS_A_D.csv",
    "ms_f_m": "2026.03.02 MS_F_M.csv",
}

D_ACTUAL_START = date(2022, 1, 1)
D_MS_ATOF = date(2026, 2, 28)
M_SCENARIO = "202601"
D_FORECAST_START = D_MS_ATOF + timedelta(days=1)
D_FORECAST_END = D_FORECAST_START + timedelta(days=365 - 1)
D_LAST_DAY_ACTUALS = D_MS_ATOF

TODAY_TEXT = pd.Timestamp.now().strftime("%Y.%m.%d")
SHOW_PLOTS = os.environ.get("SIGNUPS_SHOW_PLOTS", "").lower() in ("1", "true", "yes")

YEARLY_FOURIER = 10  # R yearly.seasonality = 9.5 → int for Python


def days_in_month(ts: pd.Timestamp) -> int:
    return calendar.monthrange(int(ts.year), int(ts.month))[1]


def _monthly_budget_to_daily_per_day(ms_slice: pd.DataFrame) -> pd.DataFrame:
    """
    Rows with MONTH (any day in month) + perMar (monthly total) ->
    month (period start) + perMar spread per calendar day (matches R perMar / days_in_month).
    """
    if ms_slice.empty:
        return pd.DataFrame(columns=["month", "perMar"])
    sub = ms_slice.copy()
    sub["MONTH"] = pd.to_datetime(sub["MONTH"], errors="coerce")
    sub["month"] = sub["MONTH"].dt.to_period("M").dt.to_timestamp()
    dim = sub["MONTH"].dt.days_in_month.astype(np.float64)
    num = pd.to_numeric(sub["perMar"], errors="coerce").astype(np.float64)
    sub["perMar"] = num / dim
    return sub[["month", "perMar"]]


def clip_yhat(fc: pd.DataFrame) -> pd.DataFrame:
    out = fc.copy()
    out["yhat"] = np.where(out["yhat"] < 0, 0, out["yhat"])
    return out


def _prophet_base_kw(holidays_df: Optional[pd.DataFrame], multiplicative: bool = False) -> dict:
    kw = dict(
        changepoint_range=0.7,
        daily_seasonality=False,
        weekly_seasonality=4,
        yearly_seasonality=YEARLY_FOURIER,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10,
        holidays_prior_scale=10,
    )
    if multiplicative:
        kw["seasonality_mode"] = "multiplicative"
    if holidays_df is not None and not holidays_df.empty:
        h = holidays_df[["holiday", "ds"]].copy()
        h["ds"] = pd.to_datetime(h["ds"]).dt.normalize()
        return {**kw, "holidays": h}
    return kw


def prophet_forecast_country_dms(
    name: str, actuals: pd.DataFrame, regressors: pd.DataFrame, holidays: pd.DataFrame, state: "RunState"
) -> None:
    m = Prophet(**_prophet_base_kw(holidays, multiplicative=False))
    m.add_regressor("DperMar", standardize=False)
    m.add_regressor("Campaigns", standardize=True)
    train = regressors.merge(actuals[["ds", "y"]], on="ds", how="left")
    m.fit(train)
    forecast = clip_yhat(m.predict(regressors))
    state.models[name] = m
    state.forecasts[f"{name}_F"] = forecast


def prophet_forecast_country_wms_m(
    name: str, actuals: pd.DataFrame, regressors: pd.DataFrame, holidays: pd.DataFrame, state: "RunState"
) -> None:
    m = Prophet(**_prophet_base_kw(holidays, multiplicative=True))
    m.add_regressor("perMar", standardize=False)
    m.add_regressor("Campaigns", standardize=True)
    m.add_regressor("ClassDays", standardize=True)
    train = regressors.merge(actuals[["ds", "y"]], on="ds", how="left")
    m.fit(train)
    forecast = clip_yhat(m.predict(regressors))
    state.models[name] = m
    state.forecasts[f"{name}_F"] = forecast


def prophet_forecast_country_noms_m(
    name: str, actuals: pd.DataFrame, regressors: pd.DataFrame, holidays: pd.DataFrame, state: "RunState"
) -> None:
    m = Prophet(**_prophet_base_kw(holidays, multiplicative=True))
    m.add_regressor("Campaigns", standardize=True)
    m.add_regressor("ClassDays", standardize=True)
    train = regressors.merge(actuals[["ds", "y"]], on="ds", how="left")
    m.fit(train)
    forecast = clip_yhat(m.predict(regressors))
    state.models[name] = m
    state.forecasts[f"{name}_F"] = forecast


def prophet_forecast_country_wms(
    name: str, actuals: pd.DataFrame, regressors: pd.DataFrame, holidays: pd.DataFrame, state: "RunState"
) -> None:
    m = Prophet(**_prophet_base_kw(holidays, multiplicative=False))
    m.add_regressor("perMar", standardize=False)
    m.add_regressor("Campaigns", standardize=True)
    m.add_regressor("ClassDays", standardize=True)
    train = regressors.merge(actuals[["ds", "y"]], on="ds", how="left")
    m.fit(train)
    forecast = clip_yhat(m.predict(regressors))
    state.models[name] = m
    state.forecasts[f"{name}_F"] = forecast


def prophet_forecast_country_noms(
    name: str, actuals: pd.DataFrame, regressors: pd.DataFrame, holidays: pd.DataFrame, state: "RunState"
) -> None:
    m = Prophet(**_prophet_base_kw(holidays, multiplicative=False))
    m.add_regressor("Campaigns", standardize=True)
    m.add_regressor("ClassDays", standardize=True)
    train = regressors.merge(actuals[["ds", "y"]], on="ds", how="left")
    m.fit(train)
    forecast = clip_yhat(m.predict(regressors))
    state.models[name] = m
    state.forecasts[f"{name}_F"] = forecast


def prophet_forecast_region_m(
    name: str, actuals: pd.DataFrame, regressors: pd.DataFrame, holidays: pd.DataFrame, state: "RunState"
) -> None:
    m = Prophet(**_prophet_base_kw(holidays, multiplicative=True))
    train = actuals[["ds", "y"]].copy()
    m.fit(train)
    forecast = clip_yhat(m.predict(regressors))
    state.models[name] = m
    state.forecasts[f"{name}_F"] = forecast


def prophet_forecast_region(
    name: str, actuals: pd.DataFrame, regressors: pd.DataFrame, holidays: pd.DataFrame, state: "RunState"
) -> None:
    m = Prophet(**_prophet_base_kw(holidays, multiplicative=False))
    train = actuals[["ds", "y"]].copy()
    m.fit(train)
    forecast = clip_yhat(m.predict(regressors))
    state.models[name] = m
    state.forecasts[f"{name}_F"] = forecast


ForecastFn = Callable[[str, pd.DataFrame, pd.DataFrame, pd.DataFrame, "RunState"], None]


@dataclass
class RunState:
    models: Dict[str, Prophet] = field(default_factory=dict)
    forecasts: Dict[str, pd.DataFrame] = field(default_factory=dict)
    frames: Dict[str, pd.DataFrame] = field(default_factory=dict)
    extracts: Dict[str, pd.DataFrame] = field(default_factory=dict)
    all_f: Optional[pd.DataFrame] = None


# Filter rules: suffix -> mask on SU_Country (columns: ds, y, + original cols)
def _filters() -> Dict[str, Callable[[pd.DataFrame], pd.DataFrame]]:
    return {
        "TSU": lambda d: d,
        "EDU": lambda d: d[d["CUSTOMER_TYPE"] == "Edu"],
        "ORG": lambda d: d[d["SIGNUP_SOURCE"] == "organic"],
        "MAR": lambda d: d[d["SIGNUP_SOURCE"] == "marketing"],
        "EDU_ORG": lambda d: d[(d["CUSTOMER_TYPE"] == "Edu") & (d["SIGNUP_SOURCE"] == "organic")],
        "EDU_ORG_WEB": lambda d: d[
            (d["CUSTOMER_TYPE"] == "Edu")
            & (d["SIGNUP_SOURCE"] == "organic")
            & (d["PLATFORM"] == "web")
        ],
        "EDU_ORG_IOS": lambda d: d[
            (d["CUSTOMER_TYPE"] == "Edu")
            & (d["SIGNUP_SOURCE"] == "organic")
            & (d["PLATFORM"] == "iOS")
        ],
        "EDU_ORG_AND": lambda d: d[
            (d["CUSTOMER_TYPE"] == "Edu")
            & (d["SIGNUP_SOURCE"] == "organic")
            & (d["PLATFORM"] == "Android")
        ],
        "EDU_MAR_WEB": lambda d: d[
            (d["CUSTOMER_TYPE"] == "Edu")
            & (d["SIGNUP_SOURCE"] == "marketing")
            & (d["PLATFORM"] == "web")
        ],
        "NON": lambda d: d[d["CUSTOMER_TYPE"] == "NonEdu"],
        "NON_ORG_WEB": lambda d: d[
            (d["CUSTOMER_TYPE"] == "NonEdu")
            & (d["SIGNUP_SOURCE"] == "organic")
            & (d["PLATFORM"] == "web")
        ],
        "NON_ORG_IOS": lambda d: d[
            (d["CUSTOMER_TYPE"] == "NonEdu")
            & (d["SIGNUP_SOURCE"] == "organic")
            & (d["PLATFORM"] == "iOS")
        ],
        "NON_ORG_AND": lambda d: d[
            (d["CUSTOMER_TYPE"] == "NonEdu")
            & (d["SIGNUP_SOURCE"] == "organic")
            & (d["PLATFORM"] == "Android")
        ],
        "NON_MAR_WEB": lambda d: d[
            (d["CUSTOMER_TYPE"] == "NonEdu")
            & (d["SIGNUP_SOURCE"] == "marketing")
            & (d["PLATFORM"] == "web")
        ],
    }


def compile_forecasts(state: RunState, model_names: List[str]) -> pd.DataFrame:
    first = model_names[0]
    base = state.forecasts[f"{first}_F"][["ds"]].copy()
    for m in model_names:
        base[m] = state.forecasts[f"{m}_F"]["yhat"].values
    return base


def process_model_extracts(
    state: RunState,
    prefix: str,
    user_type: str,
    signup_channel: str,
    platform: str,
    scenario: str = M_SCENARIO,
) -> None:
    df = state.all_f
    assert df is not None
    col_names = [c for c in df.columns if c != "ds" and str(c).startswith(prefix)]
    pat = re.compile(rf"^{re.escape(prefix)}_R3_([A-Z]{{2}})")
    for col_name in col_names:
        m = pat.match(col_name)
        region = m.group(1) if m else None
        sub = (
            df[["ds", col_name]]
            .rename(columns={col_name: "Signups"})
            .assign(
                Region=region,
                UserType=user_type,
                SignupChannel=signup_channel,
                Platform=platform,
                Scenario=scenario,
            )
        )
        clean = re.sub(rf"^{prefix}_R3_", "", col_name)
        state.extracts[f"{clean}_EXT"] = sub


def run_countryloop_forecast(
    state: RunState,
    data: "PipelineData",
    *,
    category: str,
    country_sn: str,
    country_fn: str,
    split_suffixes: List[str],
    model_ids: List[str],
    forecast_func: ForecastFn,
) -> None:
    print(f"Running forecast for {category}: {country_sn}")
    flt = _filters()

    b_names = [f"{country_sn}_{sfx}" for sfx in split_suffixes]
    a_names = [f"{bn}_A" for bn in b_names]
    m_names = [f"{mid}_R3_{bn}" for mid, bn in zip(model_ids, b_names)]
    f_names = [f"{mn}_F" for mn in m_names]

    su_country = data.su_a.loc[data.su_a["REGIONS"] == country_fn].copy()
    su_country = su_country.rename(columns={"DATE": "ds", "TOTAL_SIGNUPS": "y"})
    state.frames[f"{country_sn}_SU_A"] = su_country

    for sfx, fn in flt.items():
        state.frames[f"{country_sn}_{sfx}_A"] = fn(su_country)

    d_start = pd.Timestamp(D_ACTUAL_START)
    d_cut = pd.Timestamp(D_MS_ATOF)
    f_start_bound = pd.Timestamp(D_FORECAST_START) - pd.Timedelta(days=1)

    for a_name in a_names:
        df = state.frames[a_name][["ds", "y"]].copy()
        df["ds"] = pd.to_datetime(df["ds"]).dt.normalize()
        df = df.groupby("ds", as_index=False)["y"].sum()
        if d_start not in set(df["ds"].dt.normalize()):
            df = pd.concat([df, pd.DataFrame({"ds": [d_start], "y": [np.nan]})], ignore_index=True)
        if d_cut not in set(df["ds"].dt.normalize()):
            df = pd.concat([df, pd.DataFrame({"ds": [d_cut], "y": [np.nan]})], ignore_index=True)
        df = df.sort_values("ds")
        idx = pd.date_range(df["ds"].min(), df["ds"].max(), freq="D")
        df = df.set_index("ds").reindex(idx).reset_index().rename(columns={"index": "ds"})
        state.frames[a_name] = df

    for bn in b_names:
        df_a = state.frames[f"{bn}_A"].copy()
        df_a = df_a[df_a["ds"] <= f_start_bound]
        df_a = df_a.sort_values("ds")
        idx_b = pd.date_range(df_a["ds"].min(), df_a["ds"].max(), freq="D")
        df_a = df_a.set_index("ds").reindex(idx_b).reset_index().rename(columns={"index": "ds"})
        state.frames[bn] = df_a

    holidays_raw = data.holidays.copy()
    holidays_raw["ds"] = pd.to_datetime(holidays_raw["ds"], format="%m/%d/%Y", errors="coerce")
    holidays_raw = holidays_raw[holidays_raw["country"].notna()]
    holidays_f = holidays_raw[holidays_raw["country"] == country_sn][["holiday", "ds"]].copy()

    tsu_df = pd.DataFrame(
        {"ds": pd.date_range(D_ACTUAL_START, D_FORECAST_END, freq="D")}
    )
    regressor_tbl = tsu_df.copy()

    camp = data.campaigns.copy()
    camp["ds"] = pd.to_datetime(camp["ds"], format="%m/%d/%y", errors="coerce")
    regressor_tbl = regressor_tbl.merge(camp, on="ds", how="left")
    regressor_tbl["Campaigns"] = regressor_tbl["Campaigns"].fillna(0)

    cc_ms_af_w = (
        data.ms_af_w.loc[data.ms_af_w["Country"] == country_sn, ["ds", "perMar"]]
        .sort_values("ds")
        .drop_duplicates("ds")
    )
    if not cc_ms_af_w.empty:
        dr = pd.date_range(cc_ms_af_w["ds"].min(), cc_ms_af_w["ds"].max(), freq="D")
        cc_ms_af_w = cc_ms_af_w.set_index("ds").reindex(dr).ffill().reset_index(names="ds")
        cc_ms_af_w["perMar"] = cc_ms_af_w["perMar"] / 7.0
    cc_ms_af_w = cc_ms_af_w[cc_ms_af_w["ds"] <= pd.Timestamp(D_MS_ATOF)]

    monthly_daily = _monthly_budget_to_daily_per_day(
        data.ms_f_m.loc[data.ms_f_m["COUNTRY_NAME"] == country_fn]
    )
    cc_ms_f_m = tsu_df.loc[tsu_df["ds"] > pd.Timestamp(D_MS_ATOF)].copy()
    cc_ms_f_m["month"] = cc_ms_f_m["ds"].dt.to_period("M").dt.to_timestamp()
    cc_ms_f_m = cc_ms_f_m.merge(monthly_daily, on="month", how="left")[["ds", "perMar"]]

    cc_ms = pd.concat([cc_ms_af_w, cc_ms_f_m], ignore_index=True)
    cc_ms["perMar"] = cc_ms["perMar"].replace({np.nan: 0})
    cc_ms["perMar"] = cc_ms["perMar"].replace({np.nan: 0})

    regressor_tbl = regressor_tbl.merge(cc_ms, on="ds", how="left")
    regressor_tbl["perMar"] = regressor_tbl["perMar"].fillna(0)

    cc_ms_a_d = (
        data.ms_a_d.loc[
            (data.ms_a_d["Country"] == country_sn) & (data.ms_a_d["ds"] < pd.Timestamp(D_FORECAST_START)),
            ["ds", "perMar"],
        ]
        .copy()
    )
    cc_ms_d = pd.concat([cc_ms_a_d, cc_ms_f_m], ignore_index=True)
    cc_ms_d["perMar"] = cc_ms_d["perMar"].fillna(0)
    regressor_tbl = regressor_tbl.merge(cc_ms_d.rename(columns={"perMar": "DperMar"}), on="ds", how="left")
    regressor_tbl["DperMar"] = regressor_tbl["DperMar"].fillna(0)

    cd = data.classdays[["ds", country_sn]].rename(columns={country_sn: "ClassDays"})
    cd["ds"] = pd.to_datetime(cd["ds"], format="%m/%d/%Y", errors="coerce")
    regressor_tbl = regressor_tbl.merge(cd, on="ds", how="left")
    if "ClassDays" in regressor_tbl.columns:
        regressor_tbl["ClassDays"] = regressor_tbl["ClassDays"].fillna(0)

    for i, mn in enumerate(m_names):
        forecast_func(mn, state.frames[b_names[i]], regressor_tbl, holidays_f, state)

    if SHOW_PLOTS:
        for i, mn in enumerate(m_names):
            fig = state.models[mn].plot(state.forecasts[f_names[i]])
            fig.suptitle(f"Forecast for {mn}")
            fig.axes[0].set_xlabel("Year")
            fig.axes[0].set_ylabel("Sign Ups")
            plt.tight_layout()
            plt.show()


def run_regionloop_forecast(
    state: RunState,
    data: "PipelineData",
    *,
    category: str,
    country_sn: str,
    country_fn: str,
    split_suffixes: List[str],
    model_ids: List[str],
    forecast_func: ForecastFn,
) -> None:
    print(f"Running forecast for {category}: {country_sn}")
    flt = _filters()

    b_names = [f"{country_sn}_{sfx}" for sfx in split_suffixes]
    a_names = [f"{bn}_A" for bn in b_names]
    m_names = [f"{mid}_R3_{bn}" for mid, bn in zip(model_ids, b_names)]
    f_names = [f"{mn}_F" for mn in m_names]

    su_country = data.su_a.loc[data.su_a["REGIONS"] == country_fn].copy()
    su_country = su_country.rename(columns={"DATE": "ds", "TOTAL_SIGNUPS": "y"})
    state.frames[f"{country_sn}_SU_A"] = su_country

    for sfx, fn in flt.items():
        state.frames[f"{country_sn}_{sfx}_A"] = fn(su_country)

    d_start = pd.Timestamp(D_ACTUAL_START)
    d_cut = pd.Timestamp(D_MS_ATOF)
    f_start_bound = pd.Timestamp(D_FORECAST_START) - pd.Timedelta(days=1)

    for a_name in a_names:
        df = state.frames[a_name][["ds", "y"]].copy()
        df["ds"] = pd.to_datetime(df["ds"]).dt.normalize()
        df = df.groupby("ds", as_index=False)["y"].sum()
        if d_start not in set(df["ds"].dt.normalize()):
            df = pd.concat([df, pd.DataFrame({"ds": [d_start], "y": [np.nan]})], ignore_index=True)
        if d_cut not in set(df["ds"].dt.normalize()):
            df = pd.concat([df, pd.DataFrame({"ds": [d_cut], "y": [np.nan]})], ignore_index=True)
        df = df.sort_values("ds")
        idx = pd.date_range(df["ds"].min(), df["ds"].max(), freq="D")
        df = df.set_index("ds").reindex(idx).reset_index().rename(columns={"index": "ds"})
        state.frames[a_name] = df

    for bn in b_names:
        df_a = state.frames[f"{bn}_A"].copy()
        df_a = df_a[df_a["ds"] <= f_start_bound]
        df_a = df_a.sort_values("ds")
        idx_b = pd.date_range(df_a["ds"].min(), df_a["ds"].max(), freq="D")
        df_a = df_a.set_index("ds").reindex(idx_b).reset_index().rename(columns={"index": "ds"})
        state.frames[bn] = df_a

    holidays_raw = data.holidays.copy()
    holidays_raw["ds"] = pd.to_datetime(holidays_raw["ds"], format="%m/%d/%Y", errors="coerce")
    holidays_raw = holidays_raw[holidays_raw["country"].notna()]
    holidays_f = holidays_raw[holidays_raw["country"] == country_sn][["holiday", "ds"]].copy()

    regressor_tbl = pd.DataFrame({"ds": pd.date_range(D_ACTUAL_START, D_FORECAST_END, freq="D")})

    for i, mn in enumerate(m_names):
        forecast_func(mn, state.frames[b_names[i]], regressor_tbl, holidays_f, state)

    if SHOW_PLOTS:
        for i, mn in enumerate(m_names):
            fig = state.models[mn].plot(state.forecasts[f_names[i]])
            fig.suptitle(f"Forecast for {mn}")
            fig.axes[0].set_xlabel("Year")
            fig.axes[0].set_ylabel("Sign Ups")
            plt.tight_layout()
            plt.show()


@dataclass
class PipelineData:
    su: pd.DataFrame
    su_a: pd.DataFrame
    holidays: pd.DataFrame
    campaigns: pd.DataFrame
    classdays: pd.DataFrame
    ms_af_w: pd.DataFrame
    ms_a_d: pd.DataFrame
    ms_f_m: pd.DataFrame


def load_and_prepare_data() -> PipelineData:
    def p(key: str) -> str:
        return os.path.join(INPUT_DIRECTORY, FILENAMES[key])

    holidays = pd.read_csv(p("holidays"))
    campaigns = pd.read_csv(p("campaigns"))
    classdays = pd.read_csv(p("classdays"))
    outliers = pd.read_csv(p("outliers"))
    su = pd.read_csv(p("signups"))
    ms_af_w = pd.read_csv(p("ms_af_w"))
    ms_a_d = pd.read_csv(p("ms_a_d"))
    ms_f_m = pd.read_csv(p("ms_f_m"))

    su = su.replace({"REGIONS": {"US": "United States of America", "UK": "United Kingdom"}})
    mask_reg = su["REGIONS"].isin(
        ["SEA", "Europe", "LATAM", "MENAP", "Sub-Saharan Africa"]
    ) & (su["SIGNUP_SOURCE"] == "marketing")
    su.loc[mask_reg, "SIGNUP_SOURCE"] = "organic"
    su["DATE"] = pd.to_datetime(su["DATE"], format="%m/%d/%Y", errors="coerce")

    ms_af_w = ms_af_w.fillna(0)
    ms_af_w["ds"] = pd.to_datetime(ms_af_w["ds"], format="%m/%d/%Y", errors="coerce")
    ms_af_w["Country"] = ms_af_w["Country"].str.replace("GB", "UK", regex=False)

    ms_f_m["MONTH"] = pd.to_datetime(ms_f_m["MONTH"], format="%m/%d/%Y", errors="coerce")
    ms_f_m = ms_f_m.loc[ms_f_m["BUDGET"] == "Performance Marketing", ["COUNTRY_NAME", "MONTH", "TARGET"]]
    ms_f_m = ms_f_m.rename(columns={"TARGET": "perMar"})

    ms_a_d = ms_a_d.fillna(0)
    ms_a_d["ds"] = pd.to_datetime(ms_a_d["ds"], format="%m/%d/%Y", errors="coerce")
    ms_a_d["Country"] = ms_a_d["Country"].str.replace("GB", "UK", regex=False)

    classdays = classdays.fillna(0)
    classdays["ds"] = pd.to_datetime(classdays["ds"], format="%m/%d/%Y", errors="coerce")

    outliers["DATE"] = pd.to_datetime(outliers["DATE"], format="%m/%d/%Y", errors="coerce")
    outliers = outliers.replace(
        {"REGIONS": {"US": "United States of America", "UK": "United Kingdom"}}
    )

    su_a = su.loc[su["DATE"] >= pd.Timestamp(D_ACTUAL_START)].copy()
    key_cols = ["DATE", "PLATFORM", "SIGNUP_SOURCE", "CUSTOMER_TYPE", "REGIONS"]
    out_keys = outliers[key_cols].drop_duplicates()
    su_a = su_a.merge(out_keys, on=key_cols, how="left", indicator=True)
    su_a = su_a.loc[su_a["_merge"] == "left_only"].drop(columns=["_merge"])

    return PipelineData(
        su=su,
        su_a=su_a,
        holidays=holidays,
        campaigns=campaigns,
        classdays=classdays,
        ms_af_w=ms_af_w,
        ms_a_d=ms_a_d,
        ms_f_m=ms_f_m,
    )


def build_model_names() -> Tuple[List[str], List[str], List[str]]:
    model_list = {
        "M11": "_EDU_ORG_WEB",
        "M12": "_EDU_ORG_IOS",
        "M13": "_EDU_ORG_AND",
        "M14": "_EDU_MAR_WEB",
        "M17": "_NON_ORG_WEB",
        "M18": "_NON_ORG_IOS",
        "M19": "_NON_ORG_AND",
        "M20": "_NON_MAR_WEB",
    }
    excl_model_list = {"M14": "_EDU_MAR_WEB", "M20": "_NON_MAR_WEB"}

    country_sn_list = [
        "TR",
        "US",
        "CA",
        "AU",
        "UK",
        "BR",
        "JP",
        "IN",
        "ID",
        "PH",
        "FR",
        "DE",
        "ES",
        "IT",
        "MX",
    ]
    country_fn_list = [
        "Turkey",
        "United States of America",
        "Canada",
        "Australia",
        "United Kingdom",
        "Brazil",
        "Japan",
        "India",
        "Indonesia",
        "Philippines",
        "France",
        "Germany",
        "Spain",
        "Italy",
        "Mexico",
    ]
    region_sn_list = ["SA", "EU", "LA", "ME", "SU"]
    region_fn_list = ["SEA", "Europe", "LATAM", "MENAP", "Sub-Saharan Africa"]
    kr_sn_list = ["VN", "KR", "TH", "PL", "NL"]
    kr_fn_list = ["Vietnam", "South Korea", "Thailand", "Poland", "Netherlands"]

    sn_list = sorted(set(country_sn_list) | set(region_sn_list) | set(kr_sn_list))

    model_names: List[str] = []
    for mid, sfx in model_list.items():
        for ctry in sn_list:
            model_names.append(f"{mid}_R3_{ctry}{sfx}")

    excl_names: List[str] = []
    for mid, sfx in excl_model_list.items():
        for ctry in region_sn_list:
            excl_names.append(f"{mid}_R3_{ctry}{sfx}")

    model_names = [m for m in model_names if m not in excl_names]

    a_list: List[str] = []
    for mid, sfx in model_list.items():
        for ctry in sn_list:
            a_list.append(f"{ctry}{sfx}_A")
    excl_a: List[str] = []
    for _mid, sfx in excl_model_list.items():
        for ctry in region_sn_list:
            excl_a.append(f"{ctry}{sfx}_A")
    a_list = [a for a in a_list if a not in excl_a]

    f_list = [f"{m}_F" for m in model_names]
    return model_names, a_list, f_list


EXT_SUFFIXES = [
    "EDU_ORG_WEB",
    "EDU_ORG_IOS",
    "EDU_ORG_AND",
    "EDU_MAR_WEB",
    "NON_ORG_WEB",
    "NON_ORG_IOS",
    "NON_ORG_AND",
    "NON_MAR_WEB",
]

REGION_EXTRACT_REPLACEMENTS = {
    r"\bUnited States of America\b": "US",
    r"\bUnited Kingdom\b": "UK",
}

FORECAST_REGION_REPLACEMENTS = {
    r"\bUnited States of America\b": "US",
    r"\bCA\b": "Canada",
    r"\bAU\b": "Australia",
    r"\bJP\b": "Japan",
    r"\bKR\b": "South Korea",
    r"\bIN\b": "India",
    r"\bID\b": "Indonesia",
    r"\bPH\b": "Philippines",
    r"\bVN\b": "Vietnam",
    r"\bTH\b": "Thailand",
    r"\bSA\b": "SEA",
    r"\bBR\b": "Brazil",
    r"\bMX\b": "Mexico",
    r"\bLA\b": "LATAM",
    r"\bUnited Kingdom\b": "UK",
    r"\bFR\b": "France",
    r"\bES\b": "Spain",
    r"\bIT\b": "Italy",
    r"\bME\b": "MENAP",
    r"\bMiddle_East_Africa\b": "MENAP",
    r"\bEU\b": "Europe",
    r"\bSU\b": "Sub-Saharan Africa",
    r"\bDE\b": "Germany",
    r"\bTR\b": "Turkey",
    r"\bPL\b": "Poland",
    r"\bNL\b": "Netherlands",
}


def export_regressor_tables(data: PipelineData, country_sn_list: List[str], country_fn_list: List[str]) -> None:
    all_pms = []
    all_dpms = []
    all_cd = []
    for country_sn, country_fn in zip(country_sn_list, country_fn_list):
        tsu_df = pd.DataFrame({"ds": pd.date_range(D_ACTUAL_START, D_FORECAST_END, freq="D")})
        reg = tsu_df.copy()

        cc_ms_af_w = (
            data.ms_af_w.loc[data.ms_af_w["Country"] == country_sn, ["ds", "perMar"]]
            .sort_values("ds")
            .drop_duplicates("ds")
        )
        if not cc_ms_af_w.empty:
            dr = pd.date_range(cc_ms_af_w["ds"].min(), cc_ms_af_w["ds"].max(), freq="D")
            cc_ms_af_w = cc_ms_af_w.set_index("ds").reindex(dr).ffill().reset_index(names="ds")
            cc_ms_af_w["perMar"] = cc_ms_af_w["perMar"] / 7.0
        cc_ms_af_w = cc_ms_af_w[cc_ms_af_w["ds"] <= pd.Timestamp(D_MS_ATOF)]

        ms_fm = (
            data.ms_f_m.loc[data.ms_f_m["COUNTRY_NAME"] == country_fn]
            .sort_values("MONTH")
            .drop_duplicates("MONTH")
        )
        if not ms_fm.empty:
            dr_m = pd.date_range(ms_fm["MONTH"].min(), ms_fm["MONTH"].max(), freq="D")
            ms_fm = ms_fm.set_index("MONTH").reindex(dr_m).ffill().reset_index(names="MONTH")
            ms_fm["MONTH"] = pd.to_datetime(ms_fm["MONTH"], errors="coerce")
            dim = ms_fm["MONTH"].dt.days_in_month.astype(np.float64)
            ms_fm["perMar"] = pd.to_numeric(ms_fm["perMar"], errors="coerce").astype(np.float64) / dim
            ms_fm = ms_fm.rename(columns={"MONTH": "ds"})[["ds", "perMar"]]
            ms_fm = ms_fm[ms_fm["ds"] > pd.Timestamp(D_MS_ATOF)]
        else:
            ms_fm = pd.DataFrame(columns=["ds", "perMar"])

        cc_ms = pd.concat([cc_ms_af_w, ms_fm], ignore_index=True)
        cc_ms["perMar"] = cc_ms["perMar"].fillna(0)
        rtp = reg.merge(cc_ms, on="ds", how="left")
        rtp["perMar"] = rtp["perMar"].fillna(0)
        rtp["country"] = country_sn
        all_pms.append(rtp)

        cc_ms_a_d = data.ms_a_d.loc[
            (data.ms_a_d["Country"] == country_sn) & (data.ms_a_d["ds"] < pd.Timestamp(D_FORECAST_START)),
            ["ds", "perMar"],
        ]
        cc_ms_d = pd.concat([cc_ms_a_d, ms_fm], ignore_index=True)
        cc_ms_d["perMar"] = cc_ms_d["perMar"].fillna(0)
        rtd = reg.merge(cc_ms_d.rename(columns={"perMar": "DperMar"}), on="ds", how="left")
        rtd["DperMar"] = rtd["DperMar"].fillna(0)
        rtd["country"] = country_sn
        all_dpms.append(rtd)

        cdf = data.classdays[["ds", country_sn]].rename(columns={country_sn: "ClassDays"})
        cdf["ds"] = pd.to_datetime(cdf["ds"], format="%m/%d/%Y", errors="coerce")
        rtc = reg.merge(cdf, on="ds", how="left")
        rtc["country"] = country_sn
        all_cd.append(rtc)

    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    pd.concat(all_pms, ignore_index=True).to_csv(
        os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_WeeklyMS_AllCountries.csv"), index=False
    )
    pd.concat(all_dpms, ignore_index=True).to_csv(
        os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_DailyMS_AllCountries.csv"), index=False
    )
    pd.concat(all_cd, ignore_index=True).to_csv(
        os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_ClassDays_AllCountries.csv"), index=False
    )


def main() -> None:
    t0 = time.perf_counter()
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

    model_names, _a_list, _f_list = build_model_names()
    country_sn_list = [
        "TR",
        "US",
        "CA",
        "AU",
        "UK",
        "BR",
        "JP",
        "IN",
        "ID",
        "PH",
        "FR",
        "DE",
        "ES",
        "IT",
        "MX",
    ]
    country_fn_list = [
        "Turkey",
        "United States of America",
        "Canada",
        "Australia",
        "United Kingdom",
        "Brazil",
        "Japan",
        "India",
        "Indonesia",
        "Philippines",
        "France",
        "Germany",
        "Spain",
        "Italy",
        "Mexico",
    ]
    region_sn_list = ["SA", "EU", "LA", "ME", "SU"]
    region_fn_list = ["SEA", "Europe", "LATAM", "MENAP", "Sub-Saharan Africa"]
    kr_sn_list = ["VN", "KR", "TH", "PL", "NL"]
    kr_fn_list = ["Vietnam", "South Korea", "Thailand", "Poland", "Netherlands"]
    sn_list = sorted(set(country_sn_list) | set(region_sn_list) | set(kr_sn_list))

    data = load_and_prepare_data()
    state = RunState()

    fc_start = time.perf_counter()
    for i, _ in enumerate(country_sn_list):
        run_countryloop_forecast(
            state,
            data,
            category="Marketing",
            country_sn=country_sn_list[i],
            country_fn=country_fn_list[i],
            split_suffixes=["EDU_MAR_WEB", "NON_MAR_WEB"],
            model_ids=["M14", "M20"],
            forecast_func=prophet_forecast_country_dms,
        )
    for i, _ in enumerate(country_sn_list):
        run_countryloop_forecast(
            state,
            data,
            category="Multiplicative Education Organic (iOS, Android)",
            country_sn=country_sn_list[i],
            country_fn=country_fn_list[i],
            split_suffixes=["EDU_ORG_IOS", "EDU_ORG_AND"],
            model_ids=["M12", "M13"],
            forecast_func=prophet_forecast_country_wms_m,
        )
    for i, _ in enumerate(country_sn_list):
        run_countryloop_forecast(
            state,
            data,
            category="Multiplicative Education Organic (web)",
            country_sn=country_sn_list[i],
            country_fn=country_fn_list[i],
            split_suffixes=["EDU_ORG_WEB"],
            model_ids=["M11"],
            forecast_func=prophet_forecast_country_noms_m,
        )
    for i, _ in enumerate(country_sn_list):
        run_countryloop_forecast(
            state,
            data,
            category="NonEdu Organic: iOS, Android",
            country_sn=country_sn_list[i],
            country_fn=country_fn_list[i],
            split_suffixes=["NON_ORG_IOS", "NON_ORG_AND"],
            model_ids=["M18", "M19"],
            forecast_func=prophet_forecast_country_wms,
        )
    for i, _ in enumerate(country_sn_list):
        run_countryloop_forecast(
            state,
            data,
            category="NonEdu Organic: web",
            country_sn=country_sn_list[i],
            country_fn=country_fn_list[i],
            split_suffixes=["NON_ORG_WEB"],
            model_ids=["M17"],
            forecast_func=prophet_forecast_country_noms,
        )
    fc_end = time.perf_counter() - fc_start

    fr_start = time.perf_counter()
    for i, _ in enumerate(region_sn_list):
        run_regionloop_forecast(
            state,
            data,
            category="Regions Education",
            country_sn=region_sn_list[i],
            country_fn=region_fn_list[i],
            split_suffixes=["EDU_ORG_WEB", "EDU_ORG_IOS", "EDU_ORG_AND"],
            model_ids=["M11", "M12", "M13"],
            forecast_func=prophet_forecast_region_m,
        )
    for i, _ in enumerate(region_sn_list):
        run_regionloop_forecast(
            state,
            data,
            category="Regions NonEdu",
            country_sn=region_sn_list[i],
            country_fn=region_fn_list[i],
            split_suffixes=["NON_ORG_WEB", "NON_ORG_IOS", "NON_ORG_AND"],
            model_ids=["M17", "M18", "M19"],
            forecast_func=prophet_forecast_region,
        )
    for i, _ in enumerate(kr_sn_list):
        run_regionloop_forecast(
            state,
            data,
            category="Korea Education",
            country_sn=kr_sn_list[i],
            country_fn=kr_fn_list[i],
            split_suffixes=["EDU_ORG_WEB", "EDU_ORG_IOS", "EDU_ORG_AND"],
            model_ids=["M11", "M12", "M13"],
            forecast_func=prophet_forecast_region_m,
        )
    for i, _ in enumerate(kr_sn_list):
        run_regionloop_forecast(
            state,
            data,
            category="Korea NonEdu",
            country_sn=kr_sn_list[i],
            country_fn=kr_fn_list[i],
            split_suffixes=["EDU_MAR_WEB", "NON_ORG_WEB", "NON_ORG_IOS", "NON_ORG_AND", "NON_MAR_WEB"],
            model_ids=["M14", "M17", "M18", "M19", "M20"],
            forecast_func=prophet_forecast_region,
        )
    fr_end = time.perf_counter() - fr_start

    all_f = compile_forecasts(state, model_names)
    all_f["ds"] = pd.to_datetime(all_f["ds"]).dt.normalize()
    state.all_f = all_f

    out_xlsx = os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_Outputs_TSU_AllCountries_.xlsx")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        all_f.to_excel(writer, sheet_name="All_F", index=False)
    print(f"Wrote {out_xlsx}")

    process_model_extracts(state, "M11", "Edu", "organic", "web")
    process_model_extracts(state, "M12", "Edu", "organic", "iOS")
    process_model_extracts(state, "M13", "Edu", "organic", "Android")
    process_model_extracts(state, "M14", "Edu", "marketing", "web")
    process_model_extracts(state, "M17", "NonEdu", "organic", "web")
    process_model_extracts(state, "M18", "NonEdu", "organic", "iOS")
    process_model_extracts(state, "M19", "NonEdu", "organic", "Android")
    process_model_extracts(state, "M20", "NonEdu", "marketing", "web")

    full_combos = pd.MultiIndex.from_product([sn_list, EXT_SUFFIXES]).to_frame(index=False)
    full_combos.columns = ["country", "suffix"]
    all_ext_names = (full_combos["country"] + "_" + full_combos["suffix"] + "_EXT").tolist()
    excl_combos = pd.MultiIndex.from_product(
        [region_sn_list, ["EDU_MAR_WEB", "NON_MAR_WEB"]]
    ).to_frame(index=False)
    excl_combos.columns = ["country", "suffix"]
    excl_ext = (excl_combos["country"] + "_" + excl_combos["suffix"] + "_EXT").tolist()
    all_ext_names = [x for x in all_ext_names if x not in excl_ext]

    extract_a_d = (
        data.su.rename(
            columns={
                "DATE": "ds",
                "REGIONS": "Region",
                "CUSTOMER_TYPE": "UserType",
                "PLATFORM": "Platform",
                "SIGNUP_SOURCE": "SignupChannel",
                "TOTAL_SIGNUPS": "Signups",
            }
        )
        .loc[lambda d: (d["ds"] >= pd.Timestamp(D_ACTUAL_START)) & (d["ds"] < pd.Timestamp(D_FORECAST_START))]
        .assign(Scenario=M_SCENARIO)[
            ["ds", "Region", "UserType", "Platform", "SignupChannel", "Scenario", "Signups"]
        ]
    )
    extract_a_d = extract_a_d.rename(columns={"ds": "Date"})
    for pat, rep in REGION_EXTRACT_REPLACEMENTS.items():
        extract_a_d["Region"] = extract_a_d["Region"].astype(str).str.replace(pat, rep, regex=True)

    ext_dfs = [state.extracts[n] for n in all_ext_names if n in state.extracts]
    if not ext_dfs:
        extract_f_d = pd.DataFrame(
            columns=["ds", "Signups", "Region", "UserType", "SignupChannel", "Platform", "Scenario"]
        )
    else:
        extract_f_d = pd.concat(ext_dfs, ignore_index=True)
    extract_f_d = extract_f_d.loc[extract_f_d["ds"] >= pd.Timestamp(D_FORECAST_START)]
    extract_f_d = extract_f_d.rename(columns={"ds": "Date"})
    for pat, rep in FORECAST_REGION_REPLACEMENTS.items():
        extract_f_d["Region"] = extract_f_d["Region"].astype(str).str.replace(pat, rep, regex=True)

    extract_af = pd.concat([extract_a_d, extract_f_d], ignore_index=True)
    extract_af = extract_af.assign(
        EOM=lambda x: x["Date"] + pd.offsets.MonthEnd(0)
    )
    extract_af = (
        extract_af.groupby(["EOM", "Region", "UserType", "Platform", "SignupChannel", "Scenario"], as_index=False)[
            "Signups"
        ]
        .sum()
        .rename(columns={"EOM": "Date"})
    )
    extract_af = extract_af[
        ["Date", "Region", "UserType", "Platform", "SignupChannel", "Scenario", "Signups"]
    ]
    mask_zero_fc = (extract_af["Date"] > pd.Timestamp(D_FORECAST_START)) & (extract_af["Signups"] == 0)
    extract_af.loc[mask_zero_fc, "Signups"] = 100

    extract_csv = os.path.join(OUTPUT_DIRECTORY, f"{TODAY_TEXT}_Signups_Extract.csv")
    extract_af.to_csv(extract_csv, index=False)
    print(f"Wrote {extract_csv}")

    export_regressor_tables(data, country_sn_list, country_fn_list)

    total = time.perf_counter() - t0
    print(
        f"Country/region forecast wall time: {fc_end:.1f}s + {fr_end:.1f}s; "
        f"total {total:.1f}s ({total / max(len(model_names), 1):.2f}s per model name)."
    )


if __name__ == "__main__":
    main()

# Packages ----------------------------------------------------------------

library(plyr)
library(data.table)
library(lubridate)
library(magrittr)
library(dplyr)
library(stringr)
library(tibble)
library(tidyr)
library(tidyverse)
library(ggplot2)
library(prophet)
library(mgsub)
library(openxlsx)

# Timer -------------------------------------------------------------------

All_start <- Sys.time()

# Configuration -----------------------------------------------------------

D_ActualStart   <- as.Date("2022-01-01")
D_MS_AtoF       <- as.Date("2026-02-28")
M_scenario      <- "202601"
D_ForecastStart <- D_MS_AtoF + 1
D_ForecastEnd   <- D_ForecastStart + 365 - 1
D_LastDayActuals <- D_MS_AtoF

Today      <- now()
Today_Text <- format(Today, "%Y.%m.%d")

message("Actuals to Forecast Date: ", D_MS_AtoF,
        " | Forecast Start: ", D_ForecastStart,
        " | Forecast End: ", D_ForecastEnd)

# Directories & File Names ------------------------------------------------

input_directory  <- "/Users/grac/Library/CloudStorage/Box-Box/Internal Reporting (CPL)/FP&A/Modelling/03. MAU/07. Prophet Model/02. Prophet Inputs/"
output_directory <- "/Users/grac/Library/CloudStorage/Box-Box/Internal Reporting (CPL)/FP&A/Modelling/03. MAU/07. Prophet Model/03. Prophet Outputs/"

# Country / Region Lists --------------------------------------------------

country_SN_list <- c("TR","US","CA","AU","UK","BR","JP","IN","ID","PH",
                     "FR","DE","ES","IT","MX")
country_FN_list <- c("Turkey","United States of America","Canada","Australia",
                     "United Kingdom","Brazil","Japan","India","Indonesia",
                     "Philippines","France","Germany","Spain","Italy","Mexico")

region_SN_list <- c("SA","EU","LA","ME","SU")
region_FN_list <- c("SEA","Europe","LATAM","MENAP","Sub-Saharan Africa")

KR_SN_list <- c("VN","KR","TH","PL","NL")
KR_FN_list <- c("Vietnam","South Korea","Thailand","Poland","Netherlands")

SN_list <- union(union(country_SN_list, region_SN_list), KR_SN_list)

# Model Definitions -------------------------------------------------------

Model_list <- list(
  M11 = "_EDU_ORG_WEB", M12 = "_EDU_ORG_IOS", M13 = "_EDU_ORG_AND",
  M14 = "_EDU_MAR_WEB", M17 = "_NON_ORG_WEB", M18 = "_NON_ORG_IOS",
  M19 = "_NON_ORG_AND", M20 = "_NON_MAR_WEB"
)

Excl_Model_list <- list(M14 = "_EDU_MAR_WEB", M20 = "_NON_MAR_WEB")

Model_names <- unlist(lapply(names(Model_list), function(mid) {
  paste0(mid, "_R3_", SN_list, Model_list[[mid]])
}))
Excl_Model_names <- unlist(lapply(names(Excl_Model_list), function(mid) {
  paste0(mid, "_R3_", region_SN_list, Excl_Model_list[[mid]])
}))
Model_names <- setdiff(Model_names, Excl_Model_names)

A_list <- unlist(lapply(names(Model_list), function(mid) {
  paste0(SN_list, Model_list[[mid]], "_A")
}))
Excl_A_list <- unlist(lapply(names(Excl_Model_list), function(mid) {
  paste0(region_SN_list, Excl_Model_list[[mid]], "_A")
}))
A_list <- setdiff(A_list, Excl_A_list)

F_list  <- paste0(Model_names, "_F")
Co_list <- paste0(Model_names, "_Co")

EXT_suffixes <- c("EDU_ORG_WEB","EDU_ORG_IOS","EDU_ORG_AND","EDU_MAR_WEB",
                  "NON_ORG_WEB","NON_ORG_IOS","NON_ORG_AND","NON_MAR_WEB")

SPLIT_FILTERS <- list(
  TSU         = quote(TRUE),
  EDU         = quote(CUSTOMER_TYPE == "Edu"),
  ORG         = quote(SIGNUP_SOURCE == "organic"),
  MAR         = quote(SIGNUP_SOURCE == "marketing"),
  EDU_ORG     = quote(CUSTOMER_TYPE == "Edu" & SIGNUP_SOURCE == "organic"),
  EDU_ORG_WEB = quote(CUSTOMER_TYPE == "Edu" & SIGNUP_SOURCE == "organic" & PLATFORM == "web"),
  EDU_ORG_IOS = quote(CUSTOMER_TYPE == "Edu" & SIGNUP_SOURCE == "organic" & PLATFORM == "iOS"),
  EDU_ORG_AND = quote(CUSTOMER_TYPE == "Edu" & SIGNUP_SOURCE == "organic" & PLATFORM == "Android"),
  EDU_MAR_WEB = quote(CUSTOMER_TYPE == "Edu" & SIGNUP_SOURCE == "marketing" & PLATFORM == "web"),
  NON         = quote(CUSTOMER_TYPE == "NonEdu"),
  NON_ORG_WEB = quote(CUSTOMER_TYPE == "NonEdu" & SIGNUP_SOURCE == "organic" & PLATFORM == "web"),
  NON_ORG_IOS = quote(CUSTOMER_TYPE == "NonEdu" & SIGNUP_SOURCE == "organic" & PLATFORM == "iOS"),
  NON_ORG_AND = quote(CUSTOMER_TYPE == "NonEdu" & SIGNUP_SOURCE == "organic" & PLATFORM == "Android"),
  NON_MAR_WEB = quote(CUSTOMER_TYPE == "NonEdu" & SIGNUP_SOURCE == "marketing" & PLATFORM == "web")
)

# Boundary dates for actuals (kept as a named list so for-loop preserves Date class)
BOUNDARY_DATES <- list(D_ActualStart, D_MS_AtoF)

# Helper Functions --------------------------------------------------------

transpose_df <- function(df) {
  t_df <- data.table::transpose(df)
  colnames(t_df) <- rownames(df)
  rownames(t_df) <- colnames(df)
  t_df %>%
    tibble::rownames_to_column() %>%
    tibble::as_tibble()
}

prophet_forecast <- function(name, actuals, regressors, holidays,
                             regressor_specs = list(),
                             multiplicative = FALSE,
                             merge_train = TRUE,
                             changepoint_range = 0.7,
                             weekly_seasonality = 4,
                             yearly_seasonality = 9.5,
                             seasonality_prior_scale = 10) {
  
  args <- list(
    changepoint.range       = changepoint_range,
    holidays                = holidays,
    daily.seasonality       = FALSE,
    weekly.seasonality      = weekly_seasonality,
    yearly.seasonality      = yearly_seasonality,
    changepoint.prior.scale = 0.05,
    seasonality.prior.scale = seasonality_prior_scale,
    holidays.prior.scale    = 10
  )
  if (multiplicative) args$seasonality.mode <- "multiplicative"
  model <- do.call(prophet, args)
  
  for (reg_name in names(regressor_specs)) {
    model <- add_regressor(model, reg_name,
                           standardize = regressor_specs[[reg_name]])
  }
  
  if (merge_train) {
    train <- merge(regressors, actuals, by = "ds", all.x = TRUE)
  } else {
    train <- actuals[, c("ds", "y")]
  }
  
  model    <- fit.prophet(model, train)
  forecast <- predict(model, regressors)
  forecast <- forecast %>% mutate(yhat = if_else(yhat < 0, 0, yhat))
  
  assign(name,               model,    envir = .GlobalEnv)
  assign(paste0(name, "_F"), forecast, envir = .GlobalEnv)
}

compile_forecasts <- function(M_names, F_list) {
  tibble_data <- list()
  for (model in M_names) {
    tibble_data[[model]] <- get(paste0(model, "_F"))$yhat
  }
  All_F <- tibble::tibble(ds = get(F_list[1])$ds, !!!tibble_data)
  return(All_F)
}

process_model_extracts <- function(prefix, user_type, signup_channel, platform,
                                   scenario = M_scenario) {
  df <- All_F %>% select(ds, contains(prefix))
  col_names <- setdiff(names(df), "ds")
  
  extracts <- map(col_names, function(col_name) {
    region <- str_extract(col_name, paste0("(?<=", prefix, "_R3_)[A-Z]{2}"))
    df %>%
      select(ds, !!sym(col_name)) %>%
      mutate(Region = region, UserType = user_type,
             SignupChannel = signup_channel, Platform = platform,
             Scenario = scenario) %>%
      rename(Signups = !!sym(col_name))
  })
  
  cleaned_names <- str_replace(col_names, paste0("^", prefix, "_R3_"), "")
  names(extracts) <- paste0(cleaned_names, "_EXT")
  list2env(extracts, envir = .GlobalEnv)
}

weekly_ms_to_daily <- function(ms_data, country_SN, cutoff_date) {
  filtered <- ms_data %>%
    filter(Country == country_SN) %>%
    select(ds, perMar)
  
  if (nrow(filtered) == 0) {
    return(tibble(ds = as.Date(character(0)), perMar = numeric(0)))
  }
  
  filtered %>%
    complete(ds = full_seq(ds, 1)) %>%
    fill(perMar) %>%
    mutate(perMar = perMar / 7) %>%
    filter(ds <= cutoff_date)
}

monthly_budget_to_daily <- function(ms_f_m, country_FN, tsu_df, cutoff_date) {
  monthly_slice <- ms_f_m %>%
    filter(COUNTRY_NAME == country_FN) %>%
    mutate(MONTH = as.Date(MONTH))
  
  if (nrow(monthly_slice) == 0) {
    return(tsu_df %>%
             filter(ds > cutoff_date) %>%
             mutate(perMar = 0))
  }
  
  monthly_daily <- monthly_slice %>%
    transmute(
      month  = floor_date(MONTH, "month"),
      perMar = perMar / days_in_month(MONTH)
    )
  
  tsu_df %>%
    filter(ds > cutoff_date) %>%
    mutate(month = floor_date(ds, "month")) %>%
    left_join(monthly_daily, by = "month") %>%
    select(ds, perMar)
}

# Data Import & Cleaning --------------------------------------------------

Holidays  <- fread(paste0(input_directory, "2026.01.05 collated_holidays.csv"), check.names = TRUE)
Campaigns <- fread(paste0(input_directory, "2025.06.04 Campaigns.csv"),         check.names = TRUE)
ClassDays <- fread(paste0(input_directory, "2025.09.03 Class Days.csv"),        check.names = TRUE)
Outliers  <- fread(paste0(input_directory, "2025.06.04 Outliers.csv"),          check.names = TRUE)
SU        <- fread(paste0(input_directory, "2026.03.02 Signups.csv"),           check.names = TRUE)
MS_AF_W   <- fread(paste0(input_directory, "2026.03.02 Looker_MS_AF_W.csv"),   check.names = TRUE)
MS_A_D    <- fread(paste0(input_directory, "2026.03.02 Looker_MS_A_D.csv"),    check.names = TRUE)
MS_F_M    <- fread(paste0(input_directory, "2026.03.02 MS_F_M.csv"),           check.names = TRUE)

# --- Signups ---
SU <- SU %>%
  mutate(
    REGIONS = str_replace(REGIONS, "^US$", "United States of America"),
    REGIONS = str_replace(REGIONS, "^UK$", "United Kingdom"),
    SIGNUP_SOURCE = if_else(
      REGIONS %in% c("SEA","Europe","LATAM","MENAP","Sub-Saharan Africa") &
        SIGNUP_SOURCE == "marketing",
      "organic", SIGNUP_SOURCE)
  )
SU$DATE <- as.Date(SU$DATE, format = "%m/%d/%Y")
SU_A <- SU %>% filter(DATE >= D_ActualStart)

# --- Weekly Marketing Spend (Actuals) ---
MS_AF_W$ds <- as.Date(MS_AF_W$ds, format = "%m/%d/%Y")
MS_AF_W$perMar[is.na(MS_AF_W$perMar)] <- 0
MS_AF_W <- as_tibble(MS_AF_W) %>%
  mutate(Country = str_replace(Country, "GB", "UK"))

# --- Marketing Spend (Forecast, Monthly) ---
MS_F_M$MONTH <- as.Date(MS_F_M$MONTH, format = "%m/%d/%Y")
MS_F_M <- as_tibble(MS_F_M) %>%
  filter(BUDGET == "Performance Marketing") %>%
  select(COUNTRY_NAME, MONTH, TARGET) %>%
  rename(perMar = TARGET)

# --- Daily Marketing Spend (Actuals) ---
MS_A_D$ds <- as.Date(MS_A_D$ds, format = "%m/%d/%Y")
MS_A_D$perMar[is.na(MS_A_D$perMar)] <- 0
MS_A_D <- as_tibble(MS_A_D) %>%
  mutate(Country = str_replace(Country, "GB", "UK"))

# --- Class Days ---
ClassDays$ds <- as.Date(ClassDays$ds, format = "%m/%d/%Y")
num_cols <- setdiff(names(ClassDays), "ds")
ClassDays[, (num_cols) := lapply(.SD, function(x) replace(x, is.na(x), 0)), .SDcols = num_cols]
ClassDays <- as_tibble(ClassDays)

# --- Holidays (parse dates once) ---
Holidays$ds <- as.Date(Holidays$ds, format = "%m/%d/%Y")
Holidays <- as_tibble(Holidays) %>% filter(!is.na(country))

# --- Campaigns (parse dates once) ---
Campaigns$ds <- as.Date(Campaigns$ds, format = "%m/%d/%y")
Campaigns <- as_tibble(Campaigns)

# --- Outliers ---
Outliers$DATE <- as.Date(Outliers$DATE, format = "%m/%d/%Y")
Outliers <- as_tibble(Outliers) %>%
  mutate(
    REGIONS = str_replace(REGIONS, "^US$", "United States of America"),
    REGIONS = str_replace(REGIONS, "^UK$", "United Kingdom")
  )

SU_A <- anti_join(SU_A, Outliers,
                  by = c("DATE","PLATFORM","SIGNUP_SOURCE","CUSTOMER_TYPE","REGIONS"))

# Unified Forecasting Loop ------------------------------------------------

run_forecast_loop <- function(category, country_SN, country_FN,
                              split_suffixes, model_ids,
                              regressor_specs = list(),
                              multiplicative = FALSE,
                              build_regressors = TRUE,
                              changepoint_range = 0.7,
                              weekly_seasonality = 4,
                              yearly_seasonality = 9.5,
                              seasonality_prior_scale = 10) {
  
  message("Running forecast for ", category, ": ", country_SN)
  
  B_names <- paste(country_SN, split_suffixes, sep = "_")
  A_names <- paste0(B_names, "_A")
  M_names <- paste0(model_ids, "_R3_", B_names)
  F_names <- paste0(M_names, "_F")
  
  # ---- Signups by split ----
  SU_Country <- SU_A %>%
    filter(REGIONS == country_FN) %>%
    rename(ds = DATE, y = TOTAL_SIGNUPS)
  assign(paste0(country_SN, "_SU_A"), SU_Country, envir = .GlobalEnv)
  
  for (sfx in names(SPLIT_FILTERS)) {
    assign(paste0(country_SN, "_", sfx, "_A"),
           SU_Country %>% filter(eval(SPLIT_FILTERS[[sfx]])),
           envir = .GlobalEnv)
  }
  
  # Format actuals: fill date gaps, ensure boundary dates exist
  # NOTE: iterate via index, NOT `for (boundary in dates)` which strips Date class
  for (A_name in A_names) {
    df <- get(A_name) %>%
      select(ds, y) %>%
      group_by(ds) %>%
      summarise(y = sum(y), .groups = "drop")
    
    for (i in seq_along(BOUNDARY_DATES)) {
      boundary <- BOUNDARY_DATES[[i]]
      if (!(boundary %in% df$ds)) {
        df <- bind_rows(df, tibble(ds = boundary, y = NA_real_))
      }
    }
    df <- df %>% arrange(ds) %>% complete(ds = full_seq(ds, 1))
    assign(A_name, df, envir = .GlobalEnv)
  }
  
  # Filter to actuals period
  for (B_name in B_names) {
    df_A <- get(paste0(B_name, "_A")) %>%
      filter(ds <= D_ForecastStart - 1) %>%
      complete(ds = full_seq(ds, 1))
    assign(B_name, df_A, envir = .GlobalEnv)
  }
  
  # ---- Holidays ----
  Holidays_filtered <- Holidays %>% filter(country == !!country_SN)
  assign(paste0(country_SN, "_Holidays"), Holidays_filtered, envir = .GlobalEnv)
  
  # ---- Regressor table ----
  tsu_df <- tibble(ds = seq(D_ActualStart, D_ForecastEnd, by = "1 day"))
  
  if (build_regressors) {
    regressor_tbl <- tsu_df
    
    # Campaigns
    regressor_tbl <- merge(regressor_tbl, Campaigns, by = "ds", all.x = TRUE)
    regressor_tbl$Campaigns[is.na(regressor_tbl$Campaigns)] <- 0
    
    # Weekly Marketing Spend -> daily
    CC_MS_AF_W <- weekly_ms_to_daily(MS_AF_W, country_SN, D_MS_AtoF)
    
    # Monthly budget -> daily
    CC_MS_F_M <- monthly_budget_to_daily(MS_F_M, country_FN, tsu_df, D_MS_AtoF)
    
    # Merge both into regressor table via left_join
    regressor_tbl <- regressor_tbl %>%
      left_join(CC_MS_AF_W, by = "ds") %>%
      left_join(CC_MS_F_M %>% rename(perMar_F = perMar), by = "ds") %>%
      mutate(perMar = coalesce(perMar, perMar_F, 0)) %>%
      select(-perMar_F)
    
    # Daily Marketing Spend
    CC_MS_A_D <- MS_A_D %>%
      filter(Country == country_SN) %>%
      select(ds, perMar) %>%
      filter(ds < D_ForecastStart) %>%
      rename(DperMar = perMar)
    
    regressor_tbl <- regressor_tbl %>%
      left_join(CC_MS_A_D, by = "ds") %>%
      left_join(CC_MS_F_M %>% rename(DperMar_F = perMar), by = "ds") %>%
      mutate(DperMar = coalesce(DperMar, DperMar_F, 0)) %>%
      select(-DperMar_F)
    
    # Class Days
    ClassDays_filtered <- ClassDays %>%
      select(ds, all_of(country_SN)) %>%
      rename(ClassDays = 2)
    regressor_tbl <- merge(regressor_tbl, ClassDays_filtered, by = "ds", all.x = TRUE)
  } else {
    regressor_tbl <- tsu_df
  }
  
  assign(paste0(country_SN, "_TSU_R"), regressor_tbl, envir = .GlobalEnv)
  
  # ---- Forecast each model ----
  merge_train <- build_regressors
  for (i in seq_along(M_names)) {
    prophet_forecast(
      name                    = M_names[i],
      actuals                 = get(B_names[i]),
      regressors              = regressor_tbl,
      holidays                = Holidays_filtered,
      regressor_specs         = regressor_specs,
      multiplicative          = multiplicative,
      merge_train             = merge_train,
      changepoint_range       = changepoint_range,
      weekly_seasonality      = weekly_seasonality,
      yearly_seasonality      = yearly_seasonality,
      seasonality_prior_scale = seasonality_prior_scale
    )
  }
  
  # ---- Plots ----
  for (i in seq_along(M_names)) {
    model    <- get(M_names[i])
    forecast <- get(F_names[i])
    print(plot(model, forecast) +
            ggtitle(paste("Forecast for", M_names[i])) +
            xlab("Year") + ylab("Sign Ups"))
  }
  
  # ---- Coefficients ----
  for (mn in M_names) {
    m <- get(mn)
    co <- m$params$beta %*% as.matrix(m$train.component.cols)
    co <- transpose_df(as_tibble(co))
    co <- co %>%
      rename(Regressor = rowname) %>%
      rename(!!mn := `1`)
    co <- rbind(co, list("Intercept", m$params$m))
    assign(paste0(mn, "_Co"), co, envir = .GlobalEnv)
  }
}

# Run Forecasting Loops ---------------------------------------------------

FC_start <- Sys.time()

country_loop_configs <- list(
  list(cat = "Marketing",
       sfx = c("EDU_MAR_WEB","NON_MAR_WEB"), ids = c("M14","M20"),
       specs = list(DperMar = FALSE, Campaigns = "auto"),
       mult = FALSE,
       chg_range = 0.78, weekly = 4, yearly = 12, seas_prior = 10),
  list(cat = "Edu Organic (iOS, Android)",
       sfx = c("EDU_ORG_IOS","EDU_ORG_AND"), ids = c("M12","M13"),
       specs = list(perMar = FALSE, Campaigns = "auto", ClassDays = "auto"),
       mult = TRUE,
       chg_range = 0.80, weekly = 4, yearly = 12, seas_prior = 10),
  list(cat = "Edu Organic (web)",
       sfx = c("EDU_ORG_WEB"), ids = c("M11"),
       specs = list(Campaigns = "auto", ClassDays = "auto"),
       mult = TRUE,
       chg_range = 0.80, weekly = 5, yearly = 12, seas_prior = 10),
  list(cat = "NonEdu Organic (iOS, Android)",
       sfx = c("NON_ORG_IOS","NON_ORG_AND"), ids = c("M18","M19"),
       specs = list(perMar = FALSE, Campaigns = "auto", ClassDays = "auto"),
       mult = FALSE,
       chg_range = 0.76, weekly = 4, yearly = 9.5, seas_prior = 5),
  list(cat = "NonEdu Organic (web)",
       sfx = c("NON_ORG_WEB"), ids = c("M17"),
       specs = list(Campaigns = "auto", ClassDays = "auto"),
       mult = FALSE,
       chg_range = 0.76, weekly = 3, yearly = 9.5, seas_prior = 5)
)

for (cfg in country_loop_configs) {
  for (i in seq_along(country_SN_list)) {
    run_forecast_loop(
      category                = cfg$cat,
      country_SN              = country_SN_list[i],
      country_FN              = country_FN_list[i],
      split_suffixes          = cfg$sfx,
      model_ids               = cfg$ids,
      regressor_specs         = cfg$specs,
      multiplicative          = cfg$mult,
      build_regressors        = TRUE,
      changepoint_range       = cfg$chg_range,
      weekly_seasonality      = cfg$weekly,
      yearly_seasonality      = cfg$yearly,
      seasonality_prior_scale = cfg$seas_prior
    )
  }
}

FC_end <- Sys.time() - FC_start

# --- Region / KR loops ---
FR_start <- Sys.time()

region_loop_configs <- list(
  list(sn = region_SN_list, fn = region_FN_list,
       cat = "Regions Education",
       sfx = c("EDU_ORG_WEB","EDU_ORG_IOS","EDU_ORG_AND"),
       ids = c("M11","M12","M13"), mult = TRUE,
       chg_range = 0.80, weekly = 4, yearly = 12, seas_prior = 10),
  list(sn = region_SN_list, fn = region_FN_list,
       cat = "Regions NonEdu",
       sfx = c("NON_ORG_WEB","NON_ORG_IOS","NON_ORG_AND"),
       ids = c("M17","M18","M19"), mult = FALSE,
       chg_range = 0.76, weekly = 3, yearly = 9.5, seas_prior = 5),
  list(sn = KR_SN_list, fn = KR_FN_list,
       cat = "KR Education",
       sfx = c("EDU_ORG_WEB","EDU_ORG_IOS","EDU_ORG_AND"),
       ids = c("M11","M12","M13"), mult = TRUE,
       chg_range = 0.80, weekly = 4, yearly = 12, seas_prior = 10),
  list(sn = KR_SN_list, fn = KR_FN_list,
       cat = "KR NonEdu",
       sfx = c("EDU_MAR_WEB","NON_ORG_WEB","NON_ORG_IOS","NON_ORG_AND","NON_MAR_WEB"),
       ids = c("M14","M17","M18","M19","M20"), mult = FALSE,
       chg_range = 0.76, weekly = 3, yearly = 9.5, seas_prior = 5)
)

for (cfg in region_loop_configs) {
  for (i in seq_along(cfg$sn)) {
    run_forecast_loop(
      category                = cfg$cat,
      country_SN              = cfg$sn[i],
      country_FN              = cfg$fn[i],
      split_suffixes          = cfg$sfx,
      model_ids               = cfg$ids,
      regressor_specs         = list(),
      multiplicative          = cfg$mult,
      build_regressors        = FALSE,
      changepoint_range       = cfg$chg_range,
      weekly_seasonality      = cfg$weekly,
      yearly_seasonality      = cfg$yearly,
      seasonality_prior_scale = cfg$seas_prior
    )
  }
}

FR_end <- Sys.time() - FR_start

# Outputs -----------------------------------------------------------------

All_F <- compile_forecasts(Model_names, F_list)

All_tabs <- list(All_F = All_F)
write.xlsx(All_tabs, file = paste0(output_directory, Today_Text, "_Outputs_TSU_AllCountries_.xlsx"))

# Extract for MAU Model ---------------------------------------------------

All_F$ds <- as.Date(as.POSIXct(All_F$ds, "GMT"))

process_model_extracts("M11", user_type = "Edu",    signup_channel = "organic",   platform = "web")
process_model_extracts("M12", user_type = "Edu",    signup_channel = "organic",   platform = "iOS")
process_model_extracts("M13", user_type = "Edu",    signup_channel = "organic",   platform = "Android")
process_model_extracts("M14", user_type = "Edu",    signup_channel = "marketing", platform = "web")
process_model_extracts("M17", user_type = "NonEdu", signup_channel = "organic",   platform = "web")
process_model_extracts("M18", user_type = "NonEdu", signup_channel = "organic",   platform = "iOS")
process_model_extracts("M19", user_type = "NonEdu", signup_channel = "organic",   platform = "Android")
process_model_extracts("M20", user_type = "NonEdu", signup_channel = "marketing", platform = "web")

full_combos <- expand.grid(country = SN_list, suffix = EXT_suffixes, stringsAsFactors = FALSE)
excl_combos <- expand.grid(country = region_SN_list,
                           suffix = c("EDU_MAR_WEB","NON_MAR_WEB"),
                           stringsAsFactors = FALSE)
All_EXT_names  <- paste0(full_combos$country, "_", full_combos$suffix, "_EXT")
Excl_EXT_names <- paste0(excl_combos$country, "_", excl_combos$suffix, "_EXT")
All_EXT_names  <- setdiff(All_EXT_names, Excl_EXT_names)

Extract_A_D <- SU %>%
  rename(ds = DATE, Region = REGIONS, UserType = CUSTOMER_TYPE,
         Platform = PLATFORM, SignupChannel = SIGNUP_SOURCE,
         Signups = TOTAL_SIGNUPS) %>%
  filter(ds >= D_ActualStart, ds < D_ForecastStart) %>%
  mutate(Scenario = M_scenario) %>%
  select(ds, Region, UserType, Platform, SignupChannel, Scenario, Signups)

ext_dfs    <- lapply(All_EXT_names, get)
Extract_F_D <- do.call(rbind, ext_dfs) %>% filter(ds >= D_ForecastStart)

Extract_A_D <- Extract_A_D %>%
  rename(Date = ds) %>%
  mutate(Region = str_replace_all(as.character(Region), c(
    "\\bUnited States of America\\b" = "US",
    "\\bUnited Kingdom\\b" = "UK"
  )))

Extract_F_D <- Extract_F_D %>%
  rename(Date = ds) %>%
  mutate(Region = str_replace_all(as.character(Region), c(
    "\\bUnited States of America\\b" = "US",
    "\\bCA\\b" = "Canada", "\\bAU\\b" = "Australia",
    "\\bJP\\b" = "Japan",  "\\bKR\\b" = "South Korea",
    "\\bIN\\b" = "India",  "\\bID\\b" = "Indonesia",
    "\\bPH\\b" = "Philippines", "\\bVN\\b" = "Vietnam",
    "\\bTH\\b" = "Thailand", "\\bSA\\b" = "SEA",
    "\\bBR\\b" = "Brazil",  "\\bMX\\b" = "Mexico",
    "\\bLA\\b" = "LATAM",   "\\bUnited Kingdom\\b" = "UK",
    "\\bFR\\b" = "France",  "\\bES\\b" = "Spain",
    "\\bIT\\b" = "Italy",   "\\bME\\b" = "MENAP",
    "\\bMiddle_East_Africa\\b" = "MENAP",
    "\\bEU\\b" = "Europe",  "\\bSU\\b" = "Sub-Saharan Africa",
    "\\bDE\\b" = "Germany", "\\bTR\\b" = "Turkey",
    "\\bPL\\b" = "Poland",  "\\bNL\\b" = "Netherlands"
  )))

Extract_AF <- rbind(Extract_A_D, Extract_F_D) %>%
  mutate(EOM = ceiling_date(Date, "month") - days(1)) %>%
  group_by(EOM, Region, UserType, Platform, SignupChannel, Scenario) %>%
  summarise(Signups = sum(Signups), .groups = "drop") %>%
  rename(Date = EOM) %>%
  select(Date, Region, UserType, Platform, SignupChannel, Scenario, Signups)

Extract_AF$Signups[Extract_AF$Date > D_ForecastStart & Extract_AF$Signups == 0] <- 100

write.csv(Extract_AF,
          file = paste0(output_directory, Today_Text, "_r_Signups_Extract.csv"),
          row.names = FALSE)

# Summary -----------------------------------------------------------------

All_end <- Sys.time() - All_start
F_num   <- length(F_list)

message(sprintf(
  "Done. Country models: %s | Region models: %s | Total: %s (%s per model).",
  format(FC_end, digits = 2), format(FR_end, digits = 2),
  format(All_end, digits = 2), format(All_end / F_num, digits = 2)
))

# Regressor Tables (all countries) ----------------------------------------

all_pms_tbl       <- tibble()
all_dpms_tbl      <- tibble()
all_classdays_tbl <- tibble()

for (i in seq_along(country_SN_list)) {
  cs <- country_SN_list[i]
  cf <- country_FN_list[i]
  
  tsu_df <- tibble(ds = seq(D_ActualStart, D_ForecastEnd, by = "1 day"))
  
  w  <- weekly_ms_to_daily(MS_AF_W, cs, D_MS_AtoF)
  fm <- monthly_budget_to_daily(MS_F_M, cf, tsu_df, D_MS_AtoF)
  fm$perMar[is.na(fm$perMar)] <- 0
  
  rtp <- tsu_df %>%
    left_join(w, by = "ds") %>%
    left_join(fm %>% rename(perMar_F = perMar), by = "ds") %>%
    mutate(perMar = coalesce(perMar, perMar_F, 0)) %>%
    select(ds, perMar)
  rtp$country <- cs
  all_pms_tbl <- bind_rows(all_pms_tbl, rtp)
  
  d <- MS_A_D %>%
    filter(Country == cs) %>%
    select(ds, perMar) %>%
    filter(ds < D_ForecastStart) %>%
    rename(DperMar = perMar)
  rtd <- tsu_df %>%
    left_join(d, by = "ds") %>%
    left_join(fm %>% rename(DperMar_F = perMar), by = "ds") %>%
    mutate(DperMar = coalesce(DperMar, DperMar_F, 0)) %>%
    select(ds, DperMar)
  rtd$country <- cs
  all_dpms_tbl <- bind_rows(all_dpms_tbl, rtd)
  
  cd <- ClassDays %>%
    select(ds, all_of(cs)) %>%
    rename(ClassDays = 2)
  rtc <- merge(tsu_df, cd, by = "ds", all.x = TRUE)
  rtc$country <- cs
  all_classdays_tbl <- bind_rows(all_classdays_tbl, rtc)
}

write.csv(all_pms_tbl,       file = paste0(output_directory, Today_Text, "_WeeklyMS_AllCountries.csv"))
write.csv(all_dpms_tbl,      file = paste0(output_directory, Today_Text, "_DailyMS_AllCountries.csv"))
write.csv(all_classdays_tbl, file = paste0(output_directory, Today_Text, "_ClassDays_AllCountries.csv"))

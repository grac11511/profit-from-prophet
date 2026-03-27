#Installing Packages

#Tables
install.packages('data.table') #Enhanced version of data frame
install.packages('tibble') #Simple data frames

#Cleaning & Transformation
install.packages('lubridate') #Date and time transformations
install.packages('magrittr') #%>% 
install.packages('stringr') #String mutations
#install.packages('plyr') 
install.packages('dplyr') 
install.packages('tidyr') 
install.packages('tidyverse') 
install.packages('mgsub') #Multiple Text Substitution 
install.packages("DatabaseConnector") #eoMonth function

#Modelling
install.packages('prophet')

#Charting
install.packages('ggplot2')

#Exporting
install.packages('openxlsx')

#Running Packages
#library(plyr)
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
library(DatabaseConnector) #why is this not loading
library(openxlsx)

# Dates
D_ActStart <- as.Date("2022-01-01")
D_ActEnd <- as.Date("2026-01-31")
D_FStart <- D_ActEnd+1
D_FEnd <- D_FStart+364*3
Scenario <- "202601"
D_Today <- format(Sys.Date(),"%Y.%m.%d")

# Directories
in_dir <- "/Users/grac/Library/CloudStorage/Box-Box/Internal Reporting (CPL)/FP&A/Modelling/03. MAU/07. Prophet Model/02. Prophet Inputs/"
out_dir <- "/Users/grac/Library/CloudStorage/Box-Box/Internal Reporting (CPL)/FP&A/Modelling/03. MAU/07. Prophet Model/03. Prophet Outputs/"

# Metric Selection
#metric <- "Signups"
metric <- "MAU"
col  <- if (metric == "Signups") "TOTAL_SIGNUPS" else "TOTAL_MAU"

# Input Files
file <- if (metric == "Signups") "2026.02.16 Signups.csv" else "2026.02.20 MAU.csv"
DF <- as_tibble(fread(file.path(in_dir, file)))
MS_A_D <- as_tibble(fread(paste0(in_dir,"2026.02.16 Looker_MS_A_D.csv")))
MS_F_M <- as_tibble(fread(paste0(in_dir,"2026.02.16 MS_F_M.csv")))
hol_raw <- as_tibble(fread(paste0(in_dir,"2026.01.05 collated_holidays.csv")))

# Actuals 
A <- DF %>%
  mutate(ds = as.Date(DATE, "%m/%d/%Y")) %>%
  filter(ds >= D_ActStart, ds <= D_ActEnd) %>%
  group_by(ds) %>%
  summarise(y = sum(.data[[col]], na.rm = TRUE), .groups = "drop") %>%
  complete(ds = seq.Date(D_ActStart, D_ActEnd, by = "day")) %>%
  mutate(y = replace_na(y, 0))

# Regressor Table
DS_MS_A_D <- MS_A_D %>%
  mutate(ds = as.Date(ds, "%m/%d/%Y")) %>%
  filter(ds <= D_ActEnd) %>%
  group_by(ds) %>% summarise(DperMar = sum(perMar, na.rm = TRUE), .groups = "drop")

DS_MS_F_M <- MS_F_M %>%
  mutate(MONTH = as.Date(MONTH, "%m/%d/%Y")) %>%
  filter(BUDGET == "Performance Marketing") %>%
  mutate(m = floor_date(MONTH, "month")) %>%
  group_by(m) %>% summarise(pm = sum(TARGET, na.rm = TRUE), .groups = "drop")

T_Full <- tibble(ds = seq.Date(D_ActStart, D_FEnd, "day")) 

T_FStart <- tibble(ds = seq.Date(D_FStart, D_FEnd, "day")) %>%
  mutate(m = floor_date(ds, "month"))

R <- T_Full %>%
  left_join(DS_MS_A_D, by = "ds") %>%
  left_join(T_FStart %>%
      left_join(DS_MS_F_M, by = "m") %>%
      transmute(ds, DperMar = replace_na(pm, 0) / days_in_month(m)), by = "ds") %>%
  transmute(ds, DperMar = coalesce(DperMar.x, DperMar.y, 0))

# Training Data
train <- R %>%
  left_join(A, by = "ds") %>%
  filter(ds <= D_ActEnd) %>%
  select(ds, y, DperMar) %>%
  mutate(
    ds     = as.Date(ds),
    y      = as.numeric(y),
    DperMar = readr::parse_number(as.character(DperMar))) %>%
  filter(!is.na(ds)) %>%
  arrange(ds) %>%
  as.data.frame()

# Holidays Dataset
holidays_df <- hol_raw %>%
  filter(country == "US") %>%     
  transmute(
    holiday = holiday,
    ds      = as.Date(ds, "%m/%d/%Y")
  )

# Model Parameters
m <- prophet::prophet(
  holidays = holidays_df,
  changepoint.range = .7,
  daily.seasonality = FALSE,
  weekly.seasonality = 4,
  yearly.seasonality = 10,
  changepoint.prior.scale = .05,
  seasonality.prior.scale = 10
)

# Define Regressors
m <- prophet::add_regressor(m, "DperMar", standardize = FALSE)

# Fitting
m <- prophet::fit.prophet(m, train)

# Forecasting
fc <- predict(m, R)

# Select Outputs
F <- fc %>% select(ds, yhat) %>% 
  rename(MAU = yhat)

# Excel Output
write.xlsx(list(
  Total_Daily=F,
  Total_Monthly=F %>% 
    mutate(Date=ceiling_date(ds,"month")-days(1)) %>% 
    group_by(Date) %>% 
    summarise(Total=sum(MAU),.groups="drop")), 
  paste0(out_dir,D_Today,"_Outputs_Total_Prophet_DperMar.xlsx"))

# Time Series Chart
print(
  plot(m, fc) +
    ggtitle(paste0("Forecast for Total ", metric)) +
    xlab("Year") +
    ylab("Total")
)

# Prophet Components Chart
print(
  prophet::prophet_plot_components(m, fc) +
    ggtitle(paste0("Prophet Components: ", metric))
)

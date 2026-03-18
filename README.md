# 📄 Design Document: Multi-Country Signup Forecasting Pipeline Using Prophet in R

## 📌 Objective

To forecast daily signups and MAU across multiple countries, regions, and user journey segments using the <a href="https://cran.r-project.org/web/packages/prophet/prophet.pdf" target="_blank">Prophet</a> package. The system dynamically integrates marketing spend, campaigns, holidays, and other regressors. It also compiles coefficients and generates an extract of all signups forecasts that inputs into the MAU forecast model.

## 📁 Repository Structure

### Signups
| File | Description |
|---------|---------|
| `signups_forecasting_country` | The official signups forecast that inputs downstream into the Topline MAU Model |
| `signups_ref_usonly` | Parameter tuning on the US models |

### MAU
| File | Description |
|---------|---------|
| `mau_forecasting_country` | The official MAU forecast for smaller countries: `Nordics-Sweden`, `Czech Republic`, `GCC`, `China`, `Argentina`, `South Africa`
| `mau_ref_global` | 3 year forecast for total global MAU |
| `mau_ref_regions` | 3 year forecast for MAU split by regions: `NAMER`, `Europe`, `GPTN`, `MENAP`, `SSA`, `LATAM`, `CJKI`, `SEA` |

## 📦 Dependencies

### Installed Packages
- **Data Handling**: `data.table`, `tibble`, `dplyr`, `tidyr`, `plyr`, `lubridate`, `stringr`, `magrittr`
- **Modeling**: `prophet`, `mgsub`
- **Exporting**: `openxlsx`
- **Utilities**: `DatabaseConnector` (used for date utilities like `eoMonth`)

## 📁 Inputs & Configuration

### Input Files
Loaded from a defined input directory:
- `Signups.csv`: Raw historical signup data.
- `collated_holidays.csv`: National holidays per country using the `generated_holiday.csv` made by <a href="https://github.com/facebook/prophet/blob/main/R/data-raw/generated_holidays.csv" target="_blank">tcuongd</a> as a base, the relevant holidays for regions have been collated with additional holidays that do not appear as national holidays also included. For example, Easter is not officially a national holiday in the US, however, it has an impact on signups, therefore, the `generated_holidays.csv` has been patched accordingly.
- `Campaigns.csv`: Binary daily campaign indicators that indicates when large <a href="https://www.canva.com/design/DAGhA6JlVV8/uqkHv6dBdYmRLxMG4PXUIQ/edit" target="_blank">promotional campaigns</a> have run. 
- `Looker_MS_AF_W.csv`: Weekly actual marketing spend. The historical marketing spend has been retrieved from <a href="https://canvalooker.au.looker.com/explore/marketing_and_engagement/marketing_spend_pacing?toggle=fil&qid=Fjgzh9s1hKVylNTp0S9dHO" target="_blank">Looker</a>
- `Looker_MS_AF_D.csv`: Daily actual marketing spend. The historical marketing spend has been retrieved from <a href="https://canvalooker.au.looker.com/explore/marketing_and_engagement/marketing_spend_pacing?toggle=fil&qid=GNKJ6xhXsBUbooUFhlAKQK" target="_blank">Looker</a>
- `MS_F_M.csv`: Monthly marketing budget forecasts. The marketing spend budget is retrieved from the `Finance` tab in <a href="https://docs.google.com/spreadsheets/d/14gZr9yRIwZ8c_sv5KOVUF8ZLZfZWXef9yL5BrewoO3c/edit?gid=1035177928#gid=1035177928" target="_blank">B2C Go-to-Market budget</a>. This weekly data is transformed into daily spend by taking the average spend per day. 

### Key Dates & Inputs
- `D_ActualStart`: Earliest signup data point
- `D_MS_AtoF`: Switch from actual to forecasted marketing spend
- `D_ForecastStart` / `D_ForecastEnd`: Forecasting window
- `M_scenario`: Label for scenario tagging (e.g., "Q2Forecast")

## 🧠 Core Functions

| Function | Purpose |
|---------|---------|
| `transpose_df` | Transposes and formats coefficient matrices |
| `prophet_forecast_country` | Trains a Prophet model with regressors |
| `prophet_forecast_region` | Trains a Prophet model without regressors |
| `compile_actuals`, `compile_forecasts`, `compile_Co`, `compile_APE` | Aggregates model outputs |
| `process_model_extracts` | Structures forecasts for MAU extract by user type and platform |

## 🌍 Countries & Regions 

### Countries 
| Region | Countries |
|---------|---------|
| NAMER | `US`, `Canada`, `Australia` |
| Europe | `UK`, `France`, `Spain`, `Italy` |
| LATAM | `Brazil`, `Mexico` |
| CJKI | `Japan`, `South Korea`, `India` |
| SEA | `Indonesia`, `Phillipines`, `Thailand`, `Vietnam` |
| GPTN | `Germany`, `Poland`, `Turkey`, `Netherlands` |

- Forecast at the country level with regressors.
- Models are trained and forecasts are generated for various user journey segments.

### Regions 
`Europe`, `LATAM`, `SEA`, `MENAP`, `Sub-Saharan Africa`

- Forecast at the region level without regressors due to data limitations.
- Reuses much of the country-level logic.

## 🏗️ Dimensions 

### User Journey Models
Each country/region is split into segments:
- **User Types**: `Edu`, `NonEdu` (B2C and B2B)
- **Signup Sources**: `organic` (direct and SEO), `marketing` (paid)
- **Platforms**: `web`, `iOS`, `Android`

### Model Data Components
- `*_A`: Actuals
- `*_F`: Forecasts
- `*_Co`: Coefficients

## 🔢 Forecasting Workflow

### For each country/region:
1. **Preprocess signup data**:
   - Filter by country/region
   - Create splits for each user journey segment

2. **Create regressors**:
   - Marketing Spend (actuals + forecasts)
   - Campaign dates
   - Public holidays

3. **Train Prophet models**:
   - Add regressors (for countries only)
   - Generate forecasts
   - Clamp negatives to zero

4. **Extract coefficients** from the trained Prophet models

5. **Visualize forecasts** using base Prophet plotting

## ⚙️ Parameter Tuning

|  | Countries: | | | | | Regions: | |
|---|---|---|---|---|---|---|---|
| **Parameter** | **Marketing** | **Edu** | **Edu** | **NonEdu** | **NonEdu** | **Edu** | **NonEdu** |
|Additional Dimensions|All|org, iOS/and|org, web|org, iOS/and|org, web|All|All|
|------------------------------|------------------------------|------------------------------|------------------------------|------------------------------|------------------------------|------------------------------|------------------------------|
| changepoint.range | `0.78` [1] | `0.80` [2] | `0.80` [2] | `0.76` [3] | `0.76` [3] | `0.80` [2] | `0.76` [3] |
| holidays | holidays |
| daily.seasonality | `FALSE` |
| weekly.seasonality | `4` | `4` | `5` [4] | `4` | `3` [5] | `4` | `3` [6] |
| yearly.seasonality | `12` [7] | `12` [8] | `12` [8] | `9.5` | `9.5` | `12` [9] | `9.5` |
| seasonality.mode | `additive` | `multiplicative` [10] | `multiplicative` [10] | `additive` | `additive` | `multiplicative` [10] | `additive` |
| changepoint.prior.scale | `0.05` | `0.05` | `0.05` | `0.05` | `0.05` | `0.05` | `0.05` |
| seasonality.prior.scale | `10` | `10` | `10` | `5` [11] | `5` [11] | `10` | `5` [12] |
| holidays.prior.scale | `10` | `10` | `10` | `10` | `10` | `10` | `10` |

### Notes

`changepoint.range`

1. Marketing spend drives structural shifts; `0.78` reaches ~Apr 2025 with a ~10-month buffer.
2. Edu growth decelerated structurally in 2024–25; later cutoff lets Prophet see this as a possible changepoint. Applies to Edu organic country (iOS, Android, web) and Regions Edu.
3. Trend is stable and cyclical; extra buffer protects against mistaking the Sep seasonal uplift for a trend break. Applies to NonEdu organic country (iOS, Android, web) and Regions NonEdu.

`weekly.seasonality`

4. Edu organic web has the strongest weekly signal of all segments (wk_cv `0.43`); extra Fourier term better captures the weekday/weekend shape.
5. NonEdu organic web has the weakest weekly seasonality of all country segments (wk_cv `0.18`); lower order reduces overfitting risk on a relatively flat weekly pattern.
6. Aggregation across countries dampens individual weekly patterns (wk_cv `0.07`–`0.17`); lower order avoids overfitting the smoother regional signal.

`yearly.seasonality`

7. Marketing has the highest yearly variation of all segments (yr_cv `0.45`); higher order needed to capture sharp back-to-school peaks.
8. Strong yearly seasonality across Edu organic (yr_cv `0.29`–`0.31`); school calendars drive distinct seasonal shapes that benefit from extra Fourier terms.
9. Region Edu iOS shows notably high yearly variation (yr_cv `0.36`); higher order helps model multi-country school calendar effects.

`seasonality.mode`

10. Seasonal amplitude scales with trend level for Edu; additive retained for NonEdu and Marketing where seasonal variance is stable relative to trend.

`seasonality.prior.scale`

11. NonEdu organic iOS/Android and web have flat yearly patterns (yr_cv `0.07`–`0.09`); the permissive default of `10` risks fitting noise as seasonal signal. Cross-validate against 10 before committing.
12. Aggregation further smooths seasonality in Regions NonEdu; tighter prior reduces overfitting risk in the regional series. Cross-validate against `10` before committing.

## 📤 Output Generation

### Final Outputs
1. `All_A.xlsx`: Combined actuals
2. `All_F.xlsx`: Combined forecasts
3. `All_Co.xlsx`: Combined model coefficients
4. `Signups_Extract.csv`: Extract at a monthly resolution, segmented by the following dimensions:
   - Date
   - Region
   - User Type
   - Signup Channel
   - Platform
   - Scenario

## ⚠️ Known Considerations

- Regressors only apply to country models, not regions.
- `prophet_plot_components()` currently commented out—could be included for further analysis.
- Run `Package Installation` line by line prior to all other sections. 


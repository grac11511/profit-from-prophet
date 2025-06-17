# 📄 Design Document: Multi-Country Signup Forecasting Pipeline Using Prophet in R

## 📌 Objective

To forecast daily signups across multiple countries, regions, and user journey segments using the <a href="https://cran.r-project.org/web/packages/prophet/prophet.pdf" target="_blank">Prophet</a> package. The system dynamically integrates marketing spend, campaigns, holidays, and other regressors. It also compiles coefficients and generates an extract of all signups forecasts that inputs into the MAU forecast model.

---

## 📦 Dependencies

### Installed Packages
- **Data Handling**: `data.table`, `tibble`, `dplyr`, `tidyr`, `plyr`, `lubridate`, `stringr`, `magrittr`
- **Modeling**: `prophet`, `mgsub`
- **Exporting**: `openxlsx`
- **Utilities**: `DatabaseConnector` (used for date utilities like `eoMonth`)

---

## 📁 Inputs & Configuration

### Input Files
Loaded from a defined input directory:
- `Signups.csv`: Raw historical signup data.
- `collated_holidays.csv`: National holidays per country using the `generated_holiday.csv` made by <a href="https://github.com/facebook/prophet/blob/main/R/data-raw/generated_holidays.csv" target="_blank">tcuongd</a> as a base, the relevant holidays for regions have been collated with additional holidays that do not appear as national holidays also included. For example, Easter is not officially a national holiday in the US, however, it has an impact on signups, therefore, the `generated_holidays.csv` has been patched accordingly.
- `Campaigns.csv`: Binary daily campaign indicators that indicates when large <a href="https://www.canva.com/design/DAGhA6JlVV8/uqkHv6dBdYmRLxMG4PXUIQ/edit" target="_blank">promotional campaigns</a> have run. 
- `Looker_MS_AF_W.csv`: Weekly actual marketing spend. The historical marketing spend has been retrieved from <a href="https://canvalooker.au.looker.com/explore/marketing_and_engagement/marketing_spend_pacing?toggle=fil&qid=Fjgzh9s1hKVylNTp0S9dHO" target="_blank">Looker</a>
- `MS_F_M.csv`: Monthly marketing budget forecasts. The marketing spend budget is retrieved from the `Finance` tab in <a href="https://docs.google.com/spreadsheets/d/14gZr9yRIwZ8c_sv5KOVUF8ZLZfZWXef9yL5BrewoO3c/edit?gid=1035177928#gid=1035177928" target="_blank">B2C Go-to-Market budget</a>. This weekly data is transformed into daily spend by taking the average spend per day. 

### Key Dates & Inputs
- `D_ActualStart`: Earliest signup data point
- `D_MS_AtoF`: Switch from actual to forecasted marketing spend
- `D_ForecastStart` / `D_ForecastEnd`: Forecasting window
- `M_scenario`: Label for scenario tagging (e.g., "Q2Forecast")

---

## 🧠 Core Functions

| Function | Purpose |
|---------|---------|
| `transpose_df` | Transposes and formats coefficient matrices |
| `prophet_forecast_country` | Trains a Prophet model with regressors |
| `prophet_forecast_region` | Trains a Prophet model without regressors |
| `compile_actuals`, `compile_forecasts`, `compile_Co`, `compile_APE` | Aggregates model outputs |
| `process_model_extracts` | Structures forecasts for MAU extract by user type and platform |

---

## 🌍 Regions 

### Countries 
- `US`, `Canada`, `Australia`, `UK`, `Brazil`, `Japan`, `South Korea`, `India`, `Indonesia`, `Phillipines`, `France`, `Germany`, `Spain`, `Italy`, `Mexico`
- Forecast at the country level with regressors.
- Models are trained and forecasts are generated for various user journey segments.

### Regions 
- `Emerging APAC`, `Developed APAC`, `East Europe`, `West Europe`, `LATAM`, `Middle East and Africa`
- Forecast at the region level without regressors due to data limitations.
- Reuses much of the country-level logic.

---

## 🏗️ Dimensions 

### User Journey Models
Each country/region is split into segments:
- **User Types**: `Edu`, `B2C`, `B2B`
- **Signup Sources**: `organic` (direct and SEO), `marketing` (paid)
- **Platforms**: `web`, `iOS`, `Android`

### Model Data Components
- `*_A`: Actuals
- `*_F`: Forecasts
- `*_Co`: Coefficients

---

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

### Variations in Forecasting 
1. **Marketing Models**:
   - Uses daily marketing spend as regressor 
   - Additive seasonality mode
  
2. **Education Organic Models**:
   - Multiplicative seasonality mode
  
3. **B2C/B2B Organic Models**:
   - Additive seasonality mode

4. **iOS & Android Models**:
   - Uses weekly marketing spend as regressor 
  
5. **web Models**:
   - Does not use marketing spend as regressor
---

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

---

## ⚠️ Known Considerations

- Regressors only apply to country models, not regions.
- `prophet_plot_components()` currently commented out—could be included for further analysis.
- Run `Package Installation` line by line prior to all other sections. 

# The Project 

This project forecasts daily sign-ups using Facebook's forecasting package <a href="https://cran.r-project.org/web/packages/prophet/prophet.pdf" target="_blank">Prophet</a> in R Studio. 

# Dimensions

#### 22 Regions:
- US
- Canada
- UK
- Australia
- Brazil
- Japan
- South Korea
- India
- Indonesia
- Philippines
- Mexico
- China
- France
- Germany
- Italy
- Spain
- Rest of World: APAC
- Rest of World: Western Europe
- Rest of World: Emerging APAC
- Rest of World: LATAM
- Rest of World: Middle East & Africa
- Rest of World: Eastern Europe

#### 3 User Journey Types:
- Education
- B2B
- B2C

#### 3 Platforms:
- Android
- Web
- iOS

#### 3 Sign-up Sources: 
- Marketing sign-ups (paid)
- Organic sign-ups (direct and SEO) 

# Regressors

This project employs 4 regressors. 

### 1) Holidays `[0,1]`
Using the `generated_holiday.csv` made by <a href="https://github.com/facebook/prophet/blob/main/R/data-raw/generated_holidays.csv" target="_blank">tcuongd</a> as a base, the relevant holidays for regions have been collated with additional holidays that do not appear as national holidays also included. For example, Easter is not officially a national holiday in the US, however, it has an impact on sign-ups, therefore, the `generated_holidays.csv` has been patched accordingly.

### 2) Performance Marketing (perMar) `[numeric]`
The historical monthly US marketing spend has been retrieved from <a href="https://canvalooker.au.looker.com/explore/marketing_and_engagement/marketing_spend_pacing?qid=NvoigkJQ18tDF0H4wetK6I&toggle=fil,vis" target="_blank">Looker</a> whilst the marketing spend budget is retrieved from <a href="https://docs.google.com/spreadsheets/d/1axKaqcPfyrkj2YaVDCN0K641uJDsBAlVFipQshugdvY/edit?gid=0#gid=0" target="_blank">B2C Go-to-Market team</a>. This weekly data is transformed into daily spend by taking the average spend per day. 

### 3) Campaign Dates `[0,1]`
Indicates when large <a href="https://www.canva.com/design/DAGhA6JlVV8/uqkHv6dBdYmRLxMG4PXUIQ/edit" target="_blank">promotional campaigns</a> have run. 

### 4) Country Manager `[0,1]`
Indicates when a region has introduced a country manager. 

# Variable Naming

`[model version]_[country]_[y]_[aspect]_[A/F]`

### 1) `[model version]` 

`M(1,2,3...)`: the model as it appears in the script.

### 2) `[country]` 

`[country]`: [US, AU, etc.]

### 3) `[y]` Forecast Dimensions

`TSU` Total Sign ups

Customer Type: 
- `EDU`
- `B2B`
- `B2C`

Sign-up Source:
- `MAR`: sign-ups from marketing
- `ORG`: organic sign-ups

Platform:
- `AND`: Android
- `WEB`: Web
- `iOS`: iOS

### 4) `[aspect]` 

- `MS`: Marketing spend (regressors) 
- `F`: Forecast
- `TF`: Timeframe
- `CV`: Cross validation
- `PM`: Performance metrics

### 5) `[A/F]`
- `A`: Actuals
- `F`: Forecast

# Model Directory
An example for US models with one regressor e.g. holidays. 

| **#** | **Region** | **User Journey** | **Source** | **Platform** | **Model Name**        |
| ----- | ---------- | ---------------- | ---------- | ------------ | --------------------- |
| 1     | US         | TSU              |            |              | M1_R3_US_TSU          |
| 2     | US         | EDU              |            |              | M2_R3_US_EDU          |
| 3     | US         | B2C              |            |              | M3_R3_US_B2C          |
| 4     | US         | B2B              |            |              | M4_R3_US_B2B          |
| 5     | US         | EDU              | ORG        |              | M5_R3_US_EDU_ORG      |
| 6     | US         | EDU              | MAR        |              | M6_R3_US_EDU_MAR      |
| 7     | US         | B2C              | ORG        |              | M7_R3_US_B2C_ORG      |
| 8     | US         | B2C              | MAR        |              | M8_R3_US_B2C_MAR      |
| 9     | US         | B2B              | ORG        |              | M9_R3_US_B2B_ORG      |
| 10    | US         | B2B              | MAR        |              | M10_R3_US_B2B_MAR     |
| 11    | US         | EDU              | ORG        | WEB          | M11_R3_US_EDU_ORG_WEB |
| 12    | US         | EDU              | ORG        | IOS          | M12_R3_US_EDU_ORG_IOS |
| 13    | US         | EDU              | ORG        | AND          | M13_R3_US_EDU_ORG_AND |
| 14    | US         | EDU              | MAR        | WEB          | M14_R3_US_EDU_MAR_WEB |
| 15    | US         | EDU              | MAR        | IOS          | M15_R3_US_EDU_MAR_IOS |
| 16    | US         | EDU              | MAR        | AND          | M16_R3_US_EDU_MAR_AND |
| 17    | US         | B2C              | ORG        | WEB          | M17_R3_US_B2C_ORG_WEB |
| 18    | US         | B2C              | ORG        | IOS          | M18_R3_US_B2C_ORG_IOS |
| 19    | US         | B2C              | ORG        | AND          | M19_R3_US_B2C_ORG_AND |
| 20    | US         | B2C              | MAR        | WEB          | M20_R3_US_B2C_MAR_WEB |
| 21    | US         | B2C              | MAR        | IOS          | M21_R3_US_B2C_MAR_IOS |
| 22    | US         | B2C              | MAR        | AND          | M22_R3_US_B2C_MAR_AND |
| 23    | US         | B2B              | ORG        | WEB          | M23_R3_US_B2B_ORG_WEB |
| 24    | US         | B2B              | ORG        | IOS          | M24_R3_US_B2B_ORG_IOS |
| 25    | US         | B2B              | ORG        | AND          | M25_R3_US_B2B_ORG_AND |
| 26    | US         | B2B              | MAR        | WEB          | M26_R3_US_B2B_MAR_WEB |
| 27    | US         | B2B              | MAR        | IOS          | M27_R3_US_B2B_MAR_IOS |
| 28    | US         | B2B              | MAR        | AND          | M28_R3_US_B2B_MAR_AND |

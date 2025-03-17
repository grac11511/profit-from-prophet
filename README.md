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
- Paid sign-ups
- Direct sign-ups
- SEO Marketing

# Regressors

This project employs 4 regressors. 

### 1) Holidays `[0,1]`
Using the `generated_holiday.csv` made by <a href="https://github.com/facebook/prophet/blob/main/R/data-raw/generated_holidays.csv" target="_blank">tcuongd</a> as a base, the relevant holidays for regions have been collated with additional holidays that do not appear as national holidays also included. For example, Easter is not officially a national holiday in the US, however, it has an impact on sign-ups, therefore, the `generated_holidays.csv` has been patched accordingly.

### 2) Performance Marketing (perMar) `[numeric]`
The historical monthly US marketing spend has been retrieved from <a href="https://canvalooker.au.looker.com/explore/marketing_and_engagement/marketing_spend_pacing?qid=NvoigkJQ18tDF0H4wetK6I&toggle=fil,vis" target="_blank">Looker</a> whilst the marketing spend budget is retrieved from <a href="https://docs.google.com/spreadsheets/d/1-Zr5iMikm-QQ6sWA9j3ml3OwEVUNbapL1Sg4IbXsFpg/edit?gid=720841330#gid=720841330" target="_blank">B2C Go-to-Market team</a>. This monthly data is transformed into daily spend by taking the average spend per day. 

### 3) Campaign Dates `[0,1]`
Indicates when large campaigns have run.

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
- `PSU`: Paid-sign-ups
- `DIR`: direct
- `SEO`: SEO Marketing

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

| **#** | **Regressors (0-4)** | **Region** | **User Journey** | **Source** | **Platform** | **Forecast** | **Model Name**          |
| ----- | -------------------- | ---------- | ---------------- | ---------- | ------------ | ------------ | ----------------------- |
| 1     | 1                    | US         | TSU              |            |              | F            | M1_R1_US_TSU_F          |
| 2     | 1                    | US         | EDU              |            |              | F            | M2_R1_US_EDU_F          |
| 3     | 1                    | US         | B2C              |            |              | F            | M3_R1_US_B2C_F          |
| 4     | 1                    | US         | B2B              |            |              | F            | M4_R1_US_B2B_F          |
| 5     | 1                    | US         | EDU              | PSU        |              | F            | M5_R1_US_EDU_PSU_F      |
| 6     | 1                    | US         | EDU              | DIR        |              | F            | M6_R1_US_EDU_DIR_F      |
| 7     | 1                    | US         | EDU              | SEO        |              | F            | M7_R1_US_EDU_SEO_F      |
| 8     | 1                    | US         | B2C              | PSU        |              | F            | M8_R1_US_B2C_PSU_F      |
| 9     | 1                    | US         | B2C              | DIR        |              | F            | M9_R1_US_B2C_DIR_F      |
| 10    | 1                    | US         | B2C              | SEO        |              | F            | M10_R1_US_B2C_SEO_F     |
| 11    | 1                    | US         | B2B              | PSU        |              | F            | M11_R1_US_B2B_PSU_F     |
| 12    | 1                    | US         | B2B              | DIR        |              | F            | M12_R1_US_B2B_DIR_F     |
| 13    | 1                    | US         | B2B              | SEO        |              | F            | M13_R1_US_B2B_SEO_F     |
| 14    | 1                    | US         | EDU              | PSU        | AND          | F            | M14_R1_US_EDU_PSU_AND_F |
| 15    | 1                    | US         | EDU              | PSU        | WEB          | F            | M15_R1_US_EDU_PSU_WEB_F |
| 16    | 1                    | US         | EDU              | PSU        | IOS          | F            | M16_R1_US_EDU_PSU_IOS_F |
| 17    | 1                    | US         | EDU              | DIR        | AND          | F            | M17_R1_US_EDU_DIR_AND_F |
| 18    | 1                    | US         | EDU              | DIR        | WEB          | F            | M18_R1_US_EDU_DIR_WEB_F |
| 19    | 1                    | US         | EDU              | DIR        | IOS          | F            | M19_R1_US_EDU_DIR_IOS_F |
| 20    | 1                    | US         | EDU              | SEO        | AND          | F            | M20_R1_US_EDU_SEO_AND_F |
| 21    | 1                    | US         | EDU              | SEO        | WEB          | F            | M21_R1_US_EDU_SEO_WEB_F |
| 22    | 1                    | US         | EDU              | SEO        | IOS          | F            | M22_R1_US_EDU_SEO_IOS_F |
| 23    | 1                    | US         | B2C              | PSU        | AND          | F            | M23_R1_US_B2C_PSU_AND_F |
| 24    | 1                    | US         | B2C              | PSU        | WEB          | F            | M24_R1_US_B2C_PSU_WEB_F |
| 25    | 1                    | US         | B2C              | PSU        | IOS          | F            | M25_R1_US_B2C_PSU_IOS_F |
| 26    | 1                    | US         | B2C              | DIR        | AND          | F            | M26_R1_US_B2C_DIR_AND_F |
| 27    | 1                    | US         | B2C              | DIR        | WEB          | F            | M27_R1_US_B2C_DIR_WEB_F |
| 28    | 1                    | US         | B2C              | DIR        | IOS          | F            | M28_R1_US_B2C_DIR_IOS_F |
| 29    | 1                    | US         | B2C              | SEO        | AND          | F            | M29_R1_US_B2C_SEO_AND_F |
| 30    | 1                    | US         | B2C              | SEO        | WEB          | F            | M30_R1_US_B2C_SEO_WEB_F |
| 31    | 1                    | US         | B2C              | SEO        | IOS          | F            | M31_R1_US_B2C_SEO_IOS_F |
| 32    | 1                    | US         | B2C              | PSU        | AND          | F            | M32_R1_US_B2C_PSU_AND_F |
| 33    | 1                    | US         | B2B              | PSU        | WEB          | F            | M33_R1_US_B2B_PSU_WEB_F |
| 34    | 1                    | US         | B2B              | PSU        | IOS          | F            | M34_R1_US_B2B_PSU_IOS_F |
| 35    | 1                    | US         | B2B              | DIR        | AND          | F            | M35_R1_US_B2B_DIR_AND_F |
| 36    | 1                    | US         | B2B              | DIR        | WEB          | F            | M36_R1_US_B2B_DIR_WEB_F |
| 37    | 1                    | US         | B2B              | DIR        | IOS          | F            | M37_R1_US_B2B_DIR_IOS_F |
| 38    | 1                    | US         | B2B              | SEO        | AND          | F            | M38_R1_US_B2B_SEO_AND_F |
| 39    | 1                    | US         | B2B              | SEO        | WEB          | F            | M39_R1_US_B2B_SEO_WEB_F |
| 40    | 1                    | US         | B2B              | SEO        | IOS          | F            | M40_R1_US_B2B_SEO_IOS_F |

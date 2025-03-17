# The Project. 

This project forecasts daily sign-ups using Facebook's forecasting package <a href="https://cran.r-project.org/web/packages/prophet/prophet.pdf" target="_blank">Prophet</a> in R Studio. 

# Dimensions.

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

# Regressors.

This project employs 4 regressors. 

### 1) Holidays `[0,1]`
Using the `generated_holiday.csv` made by <a href="https://github.com/facebook/prophet/blob/main/R/data-raw/generated_holidays.csv" target="_blank">tcuongd</a> as a base, the relevant holidays for regions have been collated with additional holidays that do not appear as national holidays also included. For example, Easter is not officially a national holiday in the US, however, it has an impact on sign-ups, therefore, the `generated_holidays.csv` has been patched accordingly.

### 2) Performance Marketing (perMar) `[numeric]`
The historical monthly US marketing spend has been retrieved from <a href="https://canvalooker.au.looker.com/explore/marketing_and_engagement/marketing_spend_pacing?qid=NvoigkJQ18tDF0H4wetK6I&toggle=fil,vis" target="_blank">Looker</a> whilst the marketing spend budget is retrieved from <a href="https://docs.google.com/spreadsheets/d/1-Zr5iMikm-QQ6sWA9j3ml3OwEVUNbapL1Sg4IbXsFpg/edit?gid=720841330#gid=720841330" target="_blank">B2C Go-to-Market team</a>. This monthly data is transformed into daily spend by taking the average spend per day. 

### 3) Campaign Dates `[0,1]`
Indicates when large campaigns have run.

### 4) Country Manager `[0,1]`
Indicates when a region has introduced a country manager. 

# Variable Names.

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

- MS: Marketing spend (regressors) 
- F: Forecast
- TF: Timeframe
- CV: Cross validation
- PM: Performance metrics

### 5) `[A/F]`
- `A`: Actuals
- `F`: Forecast

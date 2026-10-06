# US methane and F-gas emissions vs EU rules

![Overview page of the dashboard](images/01_overview.jpg)

From 2027 the EU starts asking importers of oil and gas to prove their suppliers measure and report methane the way EU producers have to (Regulation (EU) 2024/1787). The US now ships more LNG to Europe than anyone else. So I wanted to know three things:

1. How much methane and F-gas do US facilities actually report, and is it going down?
2. If the trend holds, does the US hit the Global Methane Pledge (30% below 2020 by 2030)?
3. How much US trade is exposed to the EU rule, and what would it cost to fix the problem at the source?

I pulled the public data, cleaned it in Python, built a small forecast, and put it all into a six-page Power BI report.

## What I found

- **Reported US methane fell 22% between 2011 and 2023**, from about 265 to 204 Mt CO2e. F-gases dropped 31% in 2023 alone, and much of that came from two Chemours plants cutting their HFC-23 emissions.
- **On a straight-line trend, methane lands at 148 Mt CO2e in 2030.** That is under the pledge path (163 Mt). But the top of the 90% range is 177 Mt, so it's likely, not guaranteed.
- **Gas production is getting cleaner per unit.** Methane lost per unit of methane sold went from 0.49% in 2015 to 0.19% in 2023. Emissions fell 42% while gas sold rose 55%.
- **The IEA thinks real US oil and gas methane is far higher than reported.** Its estimate (17.8 Mt CH4, the largest of any country) is roughly 8 times what the EPA facility data shows. Part of that is reporting thresholds, part is satellite-detected leaks that never make it into the reported numbers.
- **The EU now takes 55% of US LNG**, and it bought $64 bn of US oil and gas in 2025. If half of that failed the new rule and the hit was 5% of its value, about $1.6 bn a year would be at risk. The two scenario dropdowns on that page let you try other numbers.
- **The fixes are known and some are free.** Leak detection and repair (LDAR) and blowdown capture pay for themselves through the gas they save. Swapping gas-driven pneumatic devices for electric ones is the single biggest cut. Pneumatics and leaks are also the two biggest sources in the EPA data, which is a nice match.

## The dashboard

| Page | What it shows |
|---|---|
| [US greenhouse gas emissions](images/01_overview.jpg) | Total GHG, methane and F-gas from EPA facility data, 2011-2023 |
| [Methane outlook to 2030](images/02_methane_forecast.jpg) | Linear forecast with a 90% range against the Global Methane Pledge |
| [Oil and gas methane intensity](images/03_methane_intensity.jpg) | Methane lost per unit of gas sold, and which equipment it comes from |
| [US exports and EU methane rules](images/04_eu_exposure.jpg) | LNG flows to the EU and a what-if on trade value at risk |
| [Methane abatement options](images/05_abatement.jpg) | IEA abatement measures by net cost and size |
| [Global benchmark](images/06_global_benchmark.jpg) | US oil and gas methane next to other countries (IEA) |

There's a PDF of all six pages in [dashboard/ProjectL.pdf](dashboard/ProjectL.pdf) if you don't have Power BI. For a page-by-page explanation of every number, see [docs/dashboard_walkthrough.md](docs/dashboard_walkthrough.md).

![Methane forecast page](images/02_methane_forecast.jpg)

## Data

| Source | What I used |
|---|---|
| EPA Greenhouse Gas Reporting Program | Facility emissions by gas 2011-2023, parent companies, and Subpart W (oil and gas) emissions by equipment type, production and well counts 2015-2023 |
| EIA | US LNG exports by terminal and destination, gas exports by country, marketed gas production by state |
| Eurostat Comext | EU-27 imports of LNG, pipeline gas, crude, HFCs and fluoropolymers, 2015-2025, plus EUR/USD rates |
| IEA Methane Tracker | Country methane estimates for 2025 and abatement cost estimates |

The cleaned tables, a column-by-column dictionary and the source licences are in [data/](data/). Raw files aren't in the repo because they're about 180 MB, but [data/raw/README.md](data/raw/README.md) says where to get each one.

## How I built it

1. **Cleaning (Python, pandas).** Five scripts turn the raw EPA, EIA, Eurostat and IEA files into a set of fact and dimension tables. Every column carries its unit in the name (`_tCO2e`, `_bcm`, `_USD`), and every fix I made is written to `DQ_Log.csv` (76 entries). Some of the more annoying ones: EPA renamed its main sheet in 2018, the 2010 file has a different layout, Subpart W renamed some source categories, one 2019 gas volume was reported 1,000 times too high, and parent company names came in so many spellings that I had to fuzzy-match them (117 merges). The details are in [docs/data_cleaning.md](docs/data_cleaning.md).
2. **Forecast (Python).** An ordinary least-squares trend on 2016-2023 methane, by segment and in total, with a 90% prediction interval. I kept it simple on purpose: eight data points don't support anything fancier. Method and limits are in [docs/forecast_model.md](docs/forecast_model.md).
3. **Power BI.** Thirteen tables, a shared year dimension, and 95 DAX measures sorted into numbered folders. The EU exposure page uses two what-if parameters. The report is saved as a PBIP project (plain-text TMDL and JSON), so the model and every visual can be read and diffed on GitHub.

## Repo layout

```
project-L-methane-fgas/
├── images/       screenshots of each dashboard page
├── dashboard/    ProjectL.pdf and the Power BI project (ProjectL/ProjectL.pbip)
├── data/         cleaned CSVs, data dictionary, sources and licences
├── scripts/      cleaning, forecast and Power BI build scripts, in run order
└── docs/         dashboard walkthrough, forecast method, cleaning notes
```

## Running it yourself

**Just the dashboard:** clone the repo (all the cleaned CSVs are in `data/clean/`) and open `dashboard/ProjectL/ProjectL.pbip` in Power BI Desktop, then point the `DataFolder` parameter at `data/clean/` and hit Refresh. [HOW_TO_OPEN.md](dashboard/ProjectL/HOW_TO_OPEN.md) has the steps.

**Everything from scratch:** download the raw files into `data/raw/`, then run the scripts in order. See [scripts/README.md](scripts/README.md).

## Limits worth knowing

- EPA numbers are what facilities report above a 25,000 t CO2e threshold, mostly from engineering estimates. They are not total US emissions.
- Gathering and boosting and transmission pipelines only report from 2016, so there's a step in the trend that year. The forecast starts in 2016 for that reason.
- A straight line can't see new rules (EPA's methane fee, OOOOb/c) or production growth. Read the 2030 figure as "if nothing changes", not a prediction.
- The IEA data covers 2025 only, and it sits on a different basis from the EPA data. Pages 1-3 use EPA, pages 5-6 use IEA, and I don't mix the two in one number.
- The trade-at-risk figure is a scenario, not an estimate. The 50% and 5% are mine and you can change them with the dropdowns on the page.

## What's next

- A regression on what drives methane intensity at the facility level (basin, well type, gas composition). The data for it is already in `Fact_SubpartW_SubBasin`.
- A proper marginal abatement cost curve, with bar widths sized by potential.

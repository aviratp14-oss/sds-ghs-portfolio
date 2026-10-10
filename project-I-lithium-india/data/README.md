# Data

`raw/` holds the inputs exactly as each source reported them, and `clean/` holds the tables the model, the workbooks and the dashboard read. The raw files are described in [raw/README.md](raw/README.md).

Everything in `clean/` is written by the scripts. `01_clean_raw_data.py` does the cleaning (the same steps as [the cleaning workbook](../excel/Project_I_Data_Cleaning.xlsx)) and `02_demand_supply_model.py` writes the model tables. I never edited a CSV by hand. Every cleaning fix is in `clean/DQ_Log.csv` and explained in [../docs/data_cleaning.md](../docs/data_cleaning.md).

## Licence

The numbers come from public sources, listed below, and each source keeps its own terms. Trade data is UN Comtrade via World Bank WITS. My assumptions (source `A00`) and the tables I built are covered by the repo's MIT licence.

## Unit standard

The unit is the last part of each column name.

| Measure | Unit | Suffix |
|---|---|---|
| Lithium | tonnes of lithium carbonate equivalent | `_t_LCE` |
| Trade quantity | kilograms of product | `_kg` |
| Money | US dollars | `_USD` |
| Unit value | USD per kg | `_USD_per_kg` |
| Shares and ratios | 0 to 1 | `_Share`, `_Ratio`, `_Dependence` |

Conversions: 1 t lithium = 5.323 t LCE, 1 t lithium hydroxide monohydrate = 0.880 t LCE.

## Tables

### Model tables (used by the dashboard)

| Table | Rows | Grain | Joins on |
|---|---|---|---|
| Dim_Scenario | 3 | Low, Base, High | `Scenario` |
| Dim_Lever | 6 | policy lever setting (None, four levers, all four) | `Lever` |
| Dim_Year | 16 | year, 2025 to 2040 (`Is_Milestone` for 2025/30/35/40) | `Year` |
| Dim_Sector | 17 | one per use, grouped into sectors and Energy transition / Non-energy | `Sub_Sector` |
| Fact_Demand | 4,896 | scenario x lever x year x use | `Scenario`, `Lever`, `Year`, `Sub_Sector` |
| Fact_Supply | 1,152 | scenario x lever x year x supply source | `Scenario`, `Lever`, `Year` |
| Fact_Balance | 288 | scenario x lever x year: demand, supply, shortfall, coverage, import dependence | `Scenario`, `Lever`, `Year` |
| Fact_Lever_Impact | 240 | scenario x lever x year: gap closed compared with no lever | `Scenario`, `Lever`, `Year` |
| Assumptions | 111 | parameter x use x scenario, with values for 2025/30/35/40 and a source ID | `Sub_Sector`, `Scenario` |
| Ref_Value_Chain | 8 | step of the lithium value chain and where India stands | |

### Cleaned inputs

| Table | Rows | What it is |
|---|---|---|
| Fact_Trade_Lithium_Chemicals | 175 | India imports of lithium carbonate (HS 283691) and hydroxide (HS 282520) by partner, 2018 to 2024, with suspect quantities re-estimated |
| Summary_Trade_by_Year | 14 | year x HS code: world row vs sum of partners, quantity removed by cleaning, clean unit value, top partner |
| Fact_EV_Sales_Reported | 50 | every EV sales figure collected, mapped to a standard segment and period |
| Ref_Base_Year_2025 | 6 | 2025 EV units, EV share and total market by vehicle segment |
| Ref_Chemistry_Intensity | 4 | lithium per kWh for LFP, NMC811, LCO and sodium-ion, worked out from cathode chemistry |
| Ref_Industry_Baseline | 3 | 2025 lithium use in grease, glass and ceramics, and pharma and other, from the trade data |
| Ref_Exploration_Pipeline | 5 | Reasi, Katghora and KABIL Catamarca, with spodumene and brine benchmarks |
| Ref_Sources | 32 | source register (below) |
| DQ_Log | 12 | every cleaning rule and how many rows it touched |

## Rules worth knowing

1. **Pick one scenario and one lever.** Every fact table holds all 3 scenarios and all 6 lever settings. Summing without a filter adds 18 versions of the same year. The "None" lever is the scenario as defined. If you read the CSVs in pandas, use `keep_default_na=False` or "None" turns into a missing value.
2. **Supply sources.** `Fact_Supply` has four sources: Recycling, Domestic mining, Overseas equity and Import ceiling (open market). The import ceiling is India's accessible share of world supply (3% by default) and is a cap, not a forecast of what India will import.
3. **The squeeze rule.** `Available_Supply_t_LCE` = recycling + domestic mining + overseas equity + import ceiling. Non-energy uses are served first. `Energy_Coverage_Ratio` = MIN(1, MAX(0, available - non-energy demand) / energy demand). `Shortfall_t_LCE` = MAX(0, demand - available).
4. **Import dependence** is the share of demand not met by recycling or mining in India. Overseas equity counts as imported.
5. **Recycled content** (`Recycled_Content_Share`) is recycling supply divided by battery demand, the measure the 2022 battery rules use. `Recycled_Content_Mandate` is the rules' target for that year.
6. **The world share slicer in Power BI** recalculates the import ceiling, shortfall and coverage in DAX. At 3% it matches `Fact_Balance`.
7. **Assumptions** has values for 2025, 2030, 2035 and 2040. The model fills the years between in a straight line, except grid storage, where new GWh rises in a straight line within each five-year block so that installed GWh still hits each milestone.

## Sources

Every row in `Assumptions` names its source IDs. `A00` means my own assumption, with the reasoning in the `Note` column.

| ID | Publisher | Title | Year |
|---|---|---|---|
| S01 | USGS | [Mineral Commodity Summaries 2026: Lithium](https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-lithium.pdf) | 2026 |
| S02 | Lok Sabha (Ministry of Mines) | [Unstarred Question No. 267 on lithium in J&K (answered 24 Jul 2024)](https://eparlib.nic.in/bitstream/123456789/2980749/1/AU267_CULiB1.pdf) | 2024 |
| S03 | CEEW | [Making India a Hub for Critical Minerals Processing (Kumar; Chandhok; Jain)](https://www.ceew.in/node/4672) | 2025 |
| S04 | CEEW; CSEP; ICRIER; IISD; Shakti | [State of the Sector: Critical Energy Transition Minerals for India Vol. I](https://www.ceew.in/node/4306) | 2025 |
| S05 | CEEW; CSEP; ICRIER; IISD; Shakti | [State of the Sector: Critical Energy Transition Minerals for India Vol. II](https://www.ceew.in/sites/default/files/state-of-the-sector-cetms-for-india-vol-ii.pdf) | 2025 |
| S06 | World Bank WITS (UN Comtrade) | [India imports by partner: HS 283691 and 282520](https://wits.worldbank.org/trade/comtrade/en/country/IND/year/2023/tradeflow/Imports/partner/ALL/product/283691) | 2026 |
| S07 | Autocar Professional (Vahan data) | [EV sales grow 17% to 1.96 million in FY2025](https://autocarpro.in/analysis-sales/ev-sales-grow-17-to-196-million-in-fy2025-2-and-3ws-cars-and-suvs-hit-new-highs-125656) | 2025 |
| S08 | EVreporter | [India EV Report FY 2024-25 (excerpts)](https://evreporter.com/evreporter-india-ev-report-fy-2024-25-excerpts/) | 2025 |
| S09 | JMK Research | [Annual India EV Report Card FY2026](https://jmkresearch.com/annual-india-ev-report-card-fy2026/) | 2026 |
| S10 | IESA via EV Infrastructure News | [India registered 2.55 million EV sales in FY2025-26](https://www.evinfrastructurenews.com/emobility/india-registers-2-55-million-ev-sales-in-fy2025-26-says-iesa) | 2026 |
| S11 | CEA via Powerline | [National Electricity Plan (Generation) 2022-32](https://powerline.net.in/2023/07/03/green-roadmap-cea-prioritises-renewables-in-the-national-electricity-plan/) | 2023 |
| S12 | Powerline | [Growing Pipeline: battery storage market moves towards larger-scale deployment](https://powerline.net.in/2026/07/24/growing-pipeline-battery-storage-market-moves-towards-larger-scale-deployment/) | 2026 |
| S13 | IDC via EET India | [India smartphone market flat in 2025](https://www.eetindia.co.in/idc-india-smartphone-market-flat-in-2025/) | 2026 |
| S14 | IDC | [India PC market records strongest-ever year: 15.9 million units in 2025](https://www.idc.com/resource-center/press-releases/india-pc-market-2025/) | 2026 |
| S15 | IDC | [India wearables market 2025](https://www.idc.com/resource-center/press-releases/india-wearables-market-fy2025/) | 2026 |
| S16 | IEEFA | [Assessing India's ACC PLI scheme](https://ieefa.org/sites/default/files/2026-01/Assessing%20India%27s%20ACC%20PLI%20scheme.pdf) | 2026 |
| S17 | IEA Policies Database | [Battery Waste Management Rules 2022](https://www.iea.org/policies/25166-battery-waste-management-rules-2022) | 2022 |
| S18 | IANS | [Cabinet approves Rs 1500 crore incentive scheme to boost critical mineral recycling](https://ianslive.in/cabinet-approves-rs-1500-crore-incentive-scheme-to-boost-critical-mineral-recycling--20250903194204) | 2025 |
| S19 | Rio Times | [KABIL Argentina lithium 2030](https://www.riotimesonline.com/kabil-argentina-lithium-2030/) | 2026 |
| S20 | Goodreturns | [Maiki South Mining wins first lithium block (Katghora)](https://www.goodreturns.in/news/maiki-south-mining-wins-first-lithium-block-chhattisgarh-011-1353663.html) | 2024 |
| S21 | Swarajya | [Long road to lithium: what is stalling India's critical mineral pursuit](https://swarajyamag.com/amp/story/infrastructure/long-road-to-lithium-what-is-stalling-indias-critical-mineral-pursuit) | 2024 |
| S22 | IEA | [Global Critical Minerals Outlook 2025: overview of outlook for key minerals](https://www.iea.org/reports/global-critical-minerals-outlook-2025/overview-of-outlook-for-key-minerals) | 2025 |
| S23 | IEA | [Global Critical Minerals Outlook 2026: outlook](https://www.iea.org/reports/global-critical-minerals-outlook-2026/outlook) | 2026 |
| S24 | IEA | [Critical Minerals Policy Tracker: promoting exploration production and innovation](https://www.iea.org/reports/critical-minerals-policy-tracker/promoting-exploration-production-and-innovation) | 2023 |
| S25 | NITI Aayog and RMI via Business Today | [India could achieve high penetration of EVs by 2030](https://www.businesstoday.in/latest/story/india-could-achieve-high-penetration-of-electric-vehicles-by-2030-niti-aayog-184081-2019-04-05) | 2019 |
| S26 | Lubes'n'Greases (NLGI survey) | [Lithium greases rebound in China and India](https://www.lubesngreases.com/lubereport-asia/8_25/lithium-greases-rebound-in-china-india/) | 2021 |
| S27 | WRI India | [Roadmap for alternative batteries and financing ecosystem for e-rickshaws in India](https://wri-india.org/sites/default/files/Roadmap%20for%20alternative%20batteries%20and%20financing%20ecosystem%20for%20e-rickshaws%20in%20India%2011th%20April.pdf) | 2024 |
| S28 | ICEA via Morung Express | [Smartphones now India's largest export commodity](https://morungexpress.com/smartphones-now-indias-largest-export-commodity-total-production-hits-rs-524-lakh-cr) | 2025 |
| S29 | CES via Outlook Business | [India's EV battery demand to rise to 256.3 GWh by 2032](https://www.outlookbusiness.com/planet/industry/indias-ev-battery-demand-to-rise-multifold-to-2563-gwh-by-2032-report) | 2025 |
| S30 | Grant Thornton Bharat via IANS | [India's critical mineral demand likely to rise up to 10-fold by 2047](https://ianslive.in/indias-critical-mineral-demand-likely-to-rise-up-to-10-fold-by-2047-report--20260730141615) | 2026 |
| S31 | EVreporter | [Lithium deposits found in J&K: what to make of the discovery?](https://evreporter.com/lithium-deposits-found-in-jk-what-to-make-of-the-discovery/) | 2023 |
| A00 | Me | Modelling assumption (see Assumptions sheet for reasoning) | 2026 |

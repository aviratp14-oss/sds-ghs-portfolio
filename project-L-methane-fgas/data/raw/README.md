# Raw data

The raw files add up to about 180 MB, so they aren't in the repo. Everything here is free to download. Put each file at the path shown and the scripts will find it.

I downloaded all of this in October 2026. The sources do get revised, so a fresh download may not match my numbers to the last decimal.

## EPA Greenhouse Gas Reporting Program

From the [GHGRP data sets page](https://www.epa.gov/ghgreporting/data-sets):

| Save as | What it is |
|---|---|
| `summary/ghgp_data_2011.xlsx` ... `summary/ghgp_data_2023.xlsx` | Facility emissions by gas, one workbook per year. They come inside `2023_data_summary_spreadsheets.zip`. I left 2010 out because its layout is different and fewer industries reported that year. |
| `ghgp_data_parent_company.xlsb` | Facility to parent company, with ownership %, one sheet per year |

From EPA Envirofacts (one CSV per year, change the year in the link):

| Save as | Link |
|---|---|
| `epa_subpart_w/epa_subpart_w_emissions_by_source_2015.csv` ... `_2023.csv` | `https://data.epa.gov/efservice/EF_W_EMISSIONS_SOURCE_GHG/reporting_year/=/2023/CSV` |
| `epa_subpart_w_overview/epa_subpart_w_facility_overview_2015.csv` ... `_2023.csv` | `https://data.epa.gov/efservice/EF_W_FACILITY_OVERVIEW/reporting_year/=/2023/CSV` |

The Envirofacts links can be slow, and big pulls sometimes time out. Doing one year at a time works.

## EIA

Use "Download Series History" on each page:

| Save as | Page |
|---|---|
| `eia/NG_MOVE_POE2_A_EPG0_ENG_MMCF_A.xls` | [LNG exports by point of exit](https://www.eia.gov/dnav/ng/ng_move_poe2_a_EPG0_ENG_Mmcf_a.htm) |
| `eia/NG_MOVE_EXPC_S1_A.xls` | [Natural gas exports by country](https://www.eia.gov/dnav/ng/ng_move_expc_s1_a.htm) |
| `eia/NG_PROD_SUM_A_EPG0_VGM_MMCF_A.xls` | [Marketed production by state](https://www.eia.gov/dnav/ng/ng_prod_sum_a_EPG0_VGM_mmcf_a.htm) |
| `eia/eia_lng_exports_by_point_of_exit_and_country_annual.md` | The 2020-2025 LNG table from the first page, saved as a markdown table. Script 1 reads it, and script 2 then replaces it with the full xls series. |

## Eurostat

| Save as | What it is |
|---|---|
| `eurostat/comext_DS-045409_EU_imports_gas_crude_hfc_fluoropolymers_2015-2025.csv` | Comext dataset DS-045409 as SDMX-CSV: EU-27 imports from all partners, annual 2015-2025, HS codes 271111, 271121, 270900, 290339, 290341-290349, 390461 and 390469 |
| `eurostat/eurostat_ert_bil_eur_a_EUR_USD_annual_avg_2010-2025.csv` | Dataset `ert_bil_eur_a`, annual average EUR/USD |

## IEA Methane Tracker

From the [Methane Tracker](https://www.iea.org/data-and-statistics/data-tools/methane-tracker) (needs a free IEA account):

| Save as | What it is |
|---|---|
| `iea/iea_methane_tracker_ch4_by_production_source.csv` | Oil and gas methane by country, source and reason, 2025 (semicolon separated) |
| `iea/iea_methane_emissions_comparison_world.csv` | World methane by sector |
| `iea/iea_methane_abatement_oilgas_world.csv` | Abatement options and costs for all countries, from `https://api.iea.org/methane/abatement/OILGAS?region=World&csv=true` |

IEA data is licensed CC BY-SA 4.0.

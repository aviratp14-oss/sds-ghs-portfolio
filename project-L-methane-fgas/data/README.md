# Data

Everything in `clean/` was produced by the scripts in `../scripts/` from the raw downloads listed in [raw/README.md](raw/README.md). I never edited a CSV by hand. If a number looks wrong, the fix belongs in a script.

## The big ones

Three tables are much larger than the rest. They're all in `clean/`, but expect a slower clone:

| File | Size | Rows |
|---|---|---|
| Fact_Emissions.csv | 22 MB | 276,356 |
| Fact_SubpartW_Source.csv | 19 MB | 204,968 |
| Dim_Parent.csv | 10 MB | 122,964 |

## Units

The unit is always the last part of the column name, so you never have to guess.

| What | Unit | Suffix |
|---|---|---|
| Emissions | tonnes CO2 equivalent | `_tCO2e` (given in AR4, AR5, AR6-100 and AR6-20; the dashboard uses AR5) |
| Mass of a gas or product | metric tonnes | `_t` |
| Gas volume | billion cubic metres | `_bcm` |
| Oil volume | barrels | `_bbl` |
| Money | US dollars | `_USD` (EU trade also keeps `_EUR`, converted at Eurostat's annual average rate) |
| Gas price | USD per MMBtu | `_USD_per_MMBtu` (1.036 MMBtu per Mcf) |
| Abatement cost | USD per tonne | `_USD_per_tCH4`, `_USD_per_tCO2e_AR5` (52.6 MMBtu per tonne of methane, GWP 28) |
| Ownership | share, 0 to 1 | `_Share` |
| Year | calendar year | `Year` (integer) |

## Tables

| File | One row is | Rows | Source | Notes |
|---|---|---|---|---|
| Fact_Emissions | facility × year × gas | 276,356 | EPA GHGRP summary files, 2011-2023 | All reported emissions, including the oil and gas sheets. HFC/PFC mixtures stay in AR4 CO2e because EPA only reports them that way (`GWP_Converted = FALSE`). |
| Fact_SubpartW_Source | facility × year × source × gas | 204,968 | EPA Envirofacts Subpart W, 2015-2023 | Oil and gas emissions by equipment type (pneumatics, leaks, flares...). 2015 has no gathering or pipeline data. |
| Fact_SubpartW_Facility_Production | facility × year | 4,436 | EPA Subpart W facility overview | Gas and oil sold, well counts, methane content. The denominator for intensity. |
| Fact_SubpartW_SubBasin | facility × year × sub-basin | 40,880 | EPA Subpart W facility overview | Wells by county and formation type. Meant for the regression. |
| Dim_Facility | facility | 10,416 | EPA summary files | Name, location, NAICS, sectors, basin. |
| Bridge_Facility_Sector | facility × sector | 11,235 | from Dim_Facility | Use this to filter by sector when a facility has more than one. |
| Dim_Parent | facility × year × parent | 122,964 | EPA parent company file | Owners and ownership share. `Parent_Standard` is the cleaned name. |
| Parent_Fuzzy_Merges | merged name | 117 | built in cleaning | Every parent name spelling I merged, so you can check them. |
| Dim_Gas | gas | 5 | IPCC AR4/AR5/AR6 | GWP lookup. |
| Dim_Source_Category | Subpart W source | 21 | built in cleaning | Vented / fugitive / flare / combustion, plus the 40 CFR 98 citation. |
| Map_Source_Category_Legacy | old category name | 9 | built in cleaning | Pre-2018 EPA names mapped to the current ones. |
| Fact_Trade_EU_Imports | year × partner × HS6 code | 4,469 | Eurostat Comext DS-045409, 2015-2025 | EU-27 imports of LNG, pipeline gas, crude, HFCs and fluoropolymers, tagged with product group and regulation. |
| Eurostat_Totals | year × aggregate × product | 196 | Eurostat | Extra-EU and intra-EU totals, for reconciliation only. |
| Dim_FX_EUR_USD | year | 16 | Eurostat ert_bil_eur_a | Annual average USD per EUR. |
| Dim_Regulation | regulation | 3 | my summary | EU Methane Regulation, F-gas Regulation, proposed PFAS restriction, with key dates. |
| Fact_LNG_Exports_Terminal | year × terminal × destination | 2,136 | EIA, 1996-2025 | US LNG exports with an EU-27 flag. |
| LNG_Terminal_Totals | year × terminal | 250 | EIA | Terminal totals as EIA publishes them. |
| Fact_EIA_Gas_Exports | year × mode × destination | 1,045 | EIA, 1973-2025 | Pipeline, LNG and CNG exports, with price where EIA has it. |
| Fact_EIA_Marketed_Production | year × state | 2,452 | EIA | US marketed gas production. |
| Recon_SubpartW_vs_EIA_Production | year | 9 | built in cleaning | EPA-reported gas against EIA production. EPA covers 83-90%. |
| Fact_IEA_Methane | country × source × reason | 1,275 | IEA Methane Tracker, 2025 | Oil and gas methane by country. |
| IEA_Methane_Totals | aggregate × source × reason | 56 | IEA | World and EU totals. |
| Ref_IEA_Methane_By_Sector | sector | 4 | IEA | World methane by sector, for context. |
| Fact_IEA_Abatement | country × source × measure | 4,823 | IEA abatement data | How much each measure cuts and its net cost. Negative cost means the saved gas pays for it. Filter Country = United States for the US (102 rows). |
| Map_Abatement_Source_Category | measure × source | 20 | built in cleaning | Links each IEA measure to the EPA source it reduces. |
| Fact_Forecast_Methane | year × segment × series | 122 | `06_forecast_methane.py` | Actuals 2011-2023, forecast 2024-2030 with a 90% range, and the pledge path. |
| Ref_Forecast_Fit | segment | 6 | `06_forecast_methane.py` | Slope, intercept, standard error and R² for each fit. |
| DQ_Log | data quality issue | 76 | all scripts | Every issue I found, an example, how many rows it hit and what I did about it. |

## Don't double count

A few of these tables overlap on purpose. The ones that will bite you:

1. **Fact_Emissions and Fact_SubpartW_Source are the same oil and gas emissions cut two ways.** Use one or the other, never both.
2. **Fact_EIA_Gas_Exports** has total rows mixed in. Filter `Is_Total_Row = FALSE` and pick one `Mode` before summing.
3. **Fact_EIA_Marketed_Production:** sum only `Level = "State or federal offshore area"`. For 2025, add the `Other States total` row as well.
4. **Fact_LNG_Exports_Terminal and LNG_Terminal_Totals** are two views of the same volume. Sum either one, not both.
5. **Fact_SubpartW_SubBasin** is a breakdown of Fact_SubpartW_Facility_Production. Don't add their well counts.
6. **Map_Abatement_Source_Category** has two rows for some measures. Sum the IEA savings first, then join.
7. **Import `Basin_Code` as text.** Some codes have letters in them (160A).

## Licences and credits

| Source | Terms |
|---|---|
| US EPA (GHGRP, Envirofacts) | US government work, public domain |
| US EIA | US government work, public domain |
| Eurostat | Free to reuse with attribution (© European Union, 1995-2026), under the Commission's reuse policy (CC BY 4.0) |
| IEA Methane Tracker | CC BY-SA 4.0. Source: IEA, *Methane Tracker Database and Methane Abatement Model*, IEA, Paris. The IEA-based tables here (Fact_IEA_Methane, IEA_Methane_Totals, Ref_IEA_Methane_By_Sector, Fact_IEA_Abatement) are adapted from that data and shared under the same licence. |
| IPCC | GWP values from AR4, AR5 and AR6 (AR6 WG1 Table 7.15) |

The rest of the cleaned tables are derived from the public-domain US data and Eurostat. My code is MIT licensed (see the root LICENSE).

# Scripts

These rebuild everything in `data/clean/` from the raw downloads, then rebuild the Power BI project. They use paths relative to the project folder, so you can run them from anywhere.

## Setup

```
pip install -r requirements.txt
```

Then put the raw files in `data/raw/` using the folder names in [../data/raw/README.md](../data/raw/README.md).

## Run order

Order matters. Each script reads what the one before it wrote, and they all add rows to `DQ_Log.csv`.

| # | Script | What it does |
|---|---|---|
| 1 | `01_clean_epa_eurostat.py` | EPA facility emissions 2011-2023 (13 yearly workbooks stacked into one table), GWP conversion to AR4/AR5/AR6, facility and parent company tables with fuzzy name matching, Eurostat EU imports, regulation lookup |
| 2 | `02_clean_eia_iea.py` | EIA LNG exports, gas exports by country and marketed production (the old wide xls layouts turned into long tables), plus the IEA Methane Tracker files |
| 3 | `03_clean_subpart_w.py` | EPA Subpart W emissions by equipment type, one file per year, with the pre-2018 category names mapped to the current ones |
| 4 | `04_apply_unit_standard.py` | Puts every table on the same units and column naming (t, tCO2e, bcm, USD), with the unit in the column name |
| 5 | `05_clean_production_abatement.py` | Subpart W production and well counts (the intensity denominator), the EPA vs EIA reconciliation, and IEA abatement costs |
| 6 | `06_forecast_methane.py` | Linear methane forecast to 2030 with a 90% range and the pledge path. See [../docs/forecast_model.md](../docs/forecast_model.md) |
| 7 | `07_build_powerbi_project.py` | Writes the whole Power BI project (`dashboard/ProjectL/`) from the clean CSVs: tables, relationships, 95 measures and all six pages |

```
python scripts/01_clean_epa_eurostat.py
python scripts/02_clean_eia_iea.py
python scripts/03_clean_subpart_w.py
python scripts/04_apply_unit_standard.py
python scripts/05_clean_production_abatement.py
python scripts/06_forecast_methane.py
python scripts/07_build_powerbi_project.py
```

The full run takes about two minutes on a laptop. Script 1 is the slow one because it reads 13 Excel files and the parent company workbook.

`06_forecast_methane.py` takes `--fit-start` and `--fit-end` if you want to try a different fitting window.

Before publishing I reran all seven from the raw files and compared the output to the tables in `data/clean/`. Every table came out identical, apart from the run date in the forecast's log entry.

## Notes

- Raw files are never changed. Scripts only read from `data/raw/` and only write to `data/clean/` (and `dashboard/ProjectL/` for script 7).
- Script 7 deletes and rewrites `dashboard/ProjectL/` each time it runs, so make any manual Power BI edits after the last rebuild, or put them into the script.
- `assets/CY24SU10.json` is the standard Power BI base theme, which script 7 copies into the report.

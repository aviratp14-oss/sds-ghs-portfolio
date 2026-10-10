# Scripts

These rebuild everything in the project from the raw inputs: the clean tables, the model output, both Excel workbooks and the Power BI project. They use paths relative to the project folder, so you can run them from anywhere.

## Setup

```
pip install -r requirements.txt
```

Nothing to download. The raw inputs are already in `data/raw/`.

## Run order

| # | Script | What it does |
|---|---|---|
| 1 | `01_clean_raw_data.py` | Cleans the raw trade data, EV sales figures and source register into the reference tables in `data/clean/` (trade, base year 2025, chemistry intensity, industry baseline, exploration pipeline, value chain, sources) plus `DQ_Log.csv`. This is the Python cross-check of the cleaning workbook |
| 2 | `02_demand_supply_model.py` | Writes `Assumptions.csv`, then runs the model for 3 scenarios x 6 lever settings x 2025 to 2040 and writes the dimension tables, `Fact_Demand`, `Fact_Supply`, `Fact_Balance` and `Fact_Lever_Impact`. Prints a short summary at the end |
| 3 | `03_build_excel_cleaning.py` | Writes `excel/Project_I_Data_Cleaning.xlsx`: raw values in grey columns, cleaning formulas in yellow, and a DQ log tab |
| 4 | `04_build_excel_model.py` | Writes `excel/Project_I_Lithium_Demand_Model.xlsx`: a Control tab with the scenario, lever switches and world share, and every other tab in plain formulas that follow it |
| 5 | `05_build_powerbi_project.py` | Writes the whole Power BI project (`dashboard/ProjectI/`) from the clean CSVs: tables, relationships, measures and all four pages |

```
python scripts/01_clean_raw_data.py
python scripts/02_demand_supply_model.py
python scripts/03_build_excel_cleaning.py
python scripts/04_build_excel_model.py
python scripts/05_build_powerbi_project.py
```

The full run takes a few seconds.

Before publishing I ran all five into an empty folder and compared the output with what's in the repo. Every clean table and the Power BI project came out identical.

## Notes

- Scripts 1 and 2 only use the Python standard library. Scripts 3 and 4 need openpyxl, script 5 needs pandas.
- Scripts 3 and 4 write the formulas but not their results, because openpyxl can't calculate. Open the workbooks in Excel, Google Sheets or LibreOffice and they calculate on load. The copies in `excel/` have already been calculated, so the values show up in previews too.
- I checked the model workbook against script 2 by recalculating a copy for each of the 18 scenario and lever combinations in LibreOffice and comparing with `Fact_Balance.csv`.
- Script 5 deletes and rewrites `dashboard/ProjectI/` each time it runs, so make any manual Power BI edits after the last rebuild, or put them into the script.
- The default `DataFolder` in the Power BI project is `C:\ProjectI\data\clean\`. Change it in Power BI (Transform data > Edit parameters) or in `DEFAULT_FOLDER` at the top of script 5.
- If you read the CSVs with pandas, pass `keep_default_na=False`. Otherwise the lever called "None" is read as a missing value.
- `assets/CY24SU10.json` is the standard Power BI base theme, which script 5 copies into the report.

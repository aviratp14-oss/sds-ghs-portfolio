# Scripts

These rebuild everything in the project from scratch: the raw SAP exports, the clean tables, the Excel cleaning workbook and the Power BI project. They use paths relative to the project folder, so you can run them from anywhere.

## Setup

```
pip install -r requirements.txt
```

Nothing to download. The only real input, the FRED price index, is already in `data/raw/`.

## Run order

| # | Script | What it does |
|---|---|---|
| 1 | `01_generate_sap_data.py` | Writes the 12 simulated SAP export files to `data/raw/`: material master, plant data, CAS classification, bill of materials, customers, sales reps, suppliers, sales orders, purchase orders, production orders, month-end stock and standard cost history. The three business problems are built into the data, along with the usual export mess. Seeded, so you get the same files every time |
| 2 | `02_clean_sap_exports.py` | Cleans the raw files into the 17 tables in `data/clean/` plus `DQ_Log.csv`. This is the Python cross-check of the Excel workbook, and it also builds `Fact_Make_vs_Buy` (bought vs made materials matched on cleaned CAS number) and `Fact_Customer_Health` (reorder rhythm per customer) |
| 3 | `03_build_excel_cleaning.py` | Writes `excel/Project_C_Data_Cleaning.xlsx`: one tab per export, raw columns in grey, cleaning formulas in yellow, and a DQ log tab that counts each issue with formulas |
| 4 | `04_build_powerbi_project.py` | Writes the whole Power BI project (`dashboard/ProjectC/`) from the clean CSVs: 17 tables, relationships, 64 measures and all four pages |

```
python scripts/01_generate_sap_data.py
python scripts/02_clean_sap_exports.py
python scripts/03_build_excel_cleaning.py
python scripts/04_build_powerbi_project.py
```

The full run takes under half a minute.

Before publishing I ran all four into an empty folder and compared the output with what's in the repo. The raw files and every clean table came out identical.

## Notes

- Script 3 writes the formulas but not their results, because openpyxl can't calculate. Open the workbook in Excel (or LibreOffice) and it calculates on load. The copy in `excel/` has already been calculated, so the values show up in previews too.
- Script 4 deletes and rewrites `dashboard/ProjectC/` each time it runs, so make any manual Power BI edits after the last rebuild, or put them into the script.
- The default `DataFolder` in the Power BI project is `C:\ProjectC\data\clean\`. Change it in Power BI (Transform data > Edit parameters) or in `DEFAULT_FOLDER` at the top of script 4.
- `assets/CY24SU10.json` is the standard Power BI base theme, which script 4 copies into the report.

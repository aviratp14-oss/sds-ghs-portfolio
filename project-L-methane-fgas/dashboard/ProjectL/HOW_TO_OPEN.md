# Opening the report in Power BI Desktop

You need a recent version of Power BI Desktop, because the report is saved as a PBIP project rather than a .pbix.

1. Make sure all the CSVs are in one folder. If you cloned the repo, they're already together in `data/clean/`.
2. Double-click `ProjectL.pbip`.
3. Power BI will look for the CSVs in `C:\ProjectL\data\clean\`. If yours are somewhere else, go to Home > Transform data > Edit parameters and change **DataFolder**. Keep the backslash at the end, it breaks without it.
4. Click **Refresh**. It loads about half a million rows, so give it a minute or two.
5. If you'd rather have a single file, use File > Save as and pick .pbix.

## What's on each page

- **Overview:** total GHG, methane and F-gas, the methane trend and methane by segment (EPA, 2011-2023).
- **Methane Forecast:** the forecast to 2030 with its 90% range and the Global Methane Pledge path. Pick a year from 2024 to 2030.
- **Methane Intensity:** methane lost per unit of methane sold, and which equipment it comes from (2015-2023).
- **EU Exposure:** US LNG going to the EU, EU imports from the US, and trade value at risk. The two scenario dropdowns change the result.
- **Abatement:** US abatement measures by net cost and size (IEA).
- **Global Benchmark:** oil and gas methane by country, and US methane by cause (IEA, 2025).

The Year slicer on each page drives the four cards and the right-hand chart. The left-hand chart always shows every year so you keep the trend in view.

## Inside the model

- All 95 measures live in the `_Measures` table, in numbered folders. Forecast measures are in `7. Forecast`.
- Emissions are in AR5 CO2e throughout.
- The forecast itself comes from `scripts/06_forecast_methane.py`. The method is in `docs/forecast_model.md`.
- `scripts/07_build_powerbi_project.py` regenerates this whole folder from the CSVs.

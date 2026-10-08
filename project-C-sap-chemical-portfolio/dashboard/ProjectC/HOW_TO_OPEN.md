# Opening the report in Power BI Desktop

You need a recent version of Power BI Desktop, because the report is saved as a PBIP project rather than a .pbix.

1. Make sure all the CSVs are in one folder. If you cloned the repo, they're already together in `data/clean/`.
2. Double-click `ProjectC.pbip`.
3. Power BI will look for the CSVs in `C:\ProjectC\data\clean\`. If yours are somewhere else, go to Home > Transform data > Edit parameters and change **DataFolder**. Keep the backslash at the end, it breaks without it.
4. Click **Refresh**. It's about 30,000 rows, so it only takes a few seconds.
5. If you'd rather have a single file, use File > Save as and pick .pbix.

## What's on each page

- **Overview:** revenue, gross margin, volume and active customers for the selected year, compared with the same months a year earlier.
- **Product Mix:** DOTP (A) vs DINP (B) share, customers who switched, margin lost to switching, and DINP discount by sales rep.
- **Internal Sourcing:** spend on chemicals the company also makes, avoidable cost, and 2-EH bought outside vs surplus sold to a trader. The Year filter starts on 2025.
- **Customer Health:** active, at-risk and lapsed customers, and the list of customers to call first.

The left menu works like SAP Fiori navigation. In Desktop, hold Ctrl and click a menu item. In the Power BI service a normal click works.
The Year filter drives the cards and the right-hand chart. The left-hand trend chart always shows every year.

## Inside the model

- All measures are in the `_Measures` table, grouped in folders (Sales, Product mix, Internal sourcing, Customer health, Report visuals).
- The cards, menu, page title and top bar are SVG images built by the measures in `5. Report visuals`.
- Margin is at standard cost. When no year is picked, the cards show the latest year (2026, Jan-Sep).
- `scripts/04_build_powerbi_project.py` regenerates this whole folder from the CSVs.

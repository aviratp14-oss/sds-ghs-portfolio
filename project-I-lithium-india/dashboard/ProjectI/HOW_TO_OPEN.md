# Opening the Project I Power BI project

1. Copy the CSV files from `data/clean/` into `C:\ProjectI\data\clean\`, or point the DataFolder parameter at `data/clean/` in your clone.
2. Double-click **ProjectI.pbip**. You need a recent Power BI Desktop.
3. If you used a different data folder, go to Home > Transform data > Edit parameters and set **DataFolder** to it. Keep the `\` at the end.
4. Click **Refresh**.
5. Go to File > Save as and choose **.pbix** if you want a single file.

## Pages
- **Overview:** demand against the supply India can reach, and the year the gap opens.
- **Who uses it:** share of lithium demand by use, 2025 to 2040.
- **Where it comes from:** recycling, mining in India, overseas mines and imports, against demand.
- **What closes the gap:** the gap left in a milestone year with each policy lever, and India's value chain today.

The tabs at the top work as page buttons. In Desktop, hold Ctrl and click a tab; in the Power BI service a normal click works.
The three slicers (scenario, policy lever, India's share of world supply) are synced across pages.

## The model
- All measures are in the `_Measures` table, in four folders: Lithium balance, Charts (kt), Page text and Report visuals.
- India's share of world supply is a what-if table (`World_Share`, 1% to 6%). Imports, the shortfall and the share of EV and
  storage demand that can be met are recalculated from it in DAX, so the slicer works live. At 3% they match `Fact_Balance`.
- When supply is short, non-energy uses (phones, grease, glass, defence) are served first. EVs and storage get what is left.
- The headlines, "three things to know" and the tab bar are SVG images built by measures in `4. Report visuals`, so the
  numbers in the text follow the slicers.
- To rebuild the project from the CSVs, run `scripts/05_build_powerbi_project.py`.

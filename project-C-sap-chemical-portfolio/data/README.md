# Data

`raw/` holds the simulated SAP exports and `clean/` holds the tables the dashboard reads. The raw files and their columns are described in [raw/README.md](raw/README.md).

Everything in `clean/` comes from the raw files. The cleaning was done in [`../excel/Project_C_Data_Cleaning.xlsx`](../excel/Project_C_Data_Cleaning.xlsx) and repeated in [`../scripts/02_clean_sap_exports.py`](../scripts/02_clean_sap_exports.py), which writes these CSVs and also builds the make-vs-buy and customer health tables. I never edited a CSV by hand. Every fix is listed in `clean/DQ_Log.csv` (24 entries), and the cleaning itself is explained in [../docs/data_cleaning.md](../docs/data_cleaning.md).

## Licence

The SAP data is simulated by me and covered by the repo's MIT licence. `Ref_PPI.csv` and `raw/13_Ref_PPI_Basic_Organic_Chemicals_FRED.csv` are the US producer price index for basic organic chemicals (BLS, via FRED series PCU325199325199), which is public domain. Chemical names and CAS numbers are facts and carry no licence.

## Unit standard

The unit is the last part of each column name.

| Measure | Unit | Suffix |
|---|---|---|
| Quantity | kilograms | `_kg` |
| Money | US dollars | `_USD` |
| Price or cost | USD per kg | `_USD_per_kg` |
| Discount | share from 0 to 1 | `_Share` |
| Dates | ISO yyyy-mm-dd | `_Date`, `Month` (first day of the month) |

## Tables

| Table | Rows | Grain | Joins on |
|---|---|---|---|
| Dim_Material | 46 | one per material | `Material_Id` |
| Dim_Customer | 161 | one per customer (duplicates removed) | `Customer_Id`, `Sales_Rep_Id` |
| Dim_Sales_Rep | 9 | one per rep (+ Unassigned) | `Sales_Rep_Id` |
| Dim_Supplier | 19 | one per supplier | `Supplier_Id` |
| Dim_Plant | 2 | one per plant | `Plant` |
| Dim_Date | 1,826 | one per day, 2022-2026 | `Date` |
| Fact_Sales | 13,846 | sales order line | `Customer_Id`, `Material_Id`, `Plant`, `Order_Date` |
| Fact_Purchases | 4,660 | purchase order line | `Supplier_Id`, `Material_Id`, `Plant`, `PO_Date` |
| Fact_Production | 2,930 | production order | `Material_Id`, `Plant`, `Start_Date` |
| Fact_Stock | 2,622 | material x plant x month | `Material_Id`, `Plant`, `Month` |
| Fact_BOM | 44 | component of a product | `Parent_Material_Id`, `Component_Material_Id` |
| Fact_Std_Cost | 230 | material x year | `Material_Id`, `Year` |
| Fact_Make_vs_Buy | 171 | bought material x month | `Bought_Material_Id`, `Made_Material_Id`, `Month` |
| Map_Make_vs_Buy | 3 | pair of material numbers with the same CAS | `Bought_Material_Id` |
| Fact_Customer_Health | 160 | one per regular customer | `Customer_Id` |
| Map_Customer_Duplicates | 4 | duplicate to master customer | |
| Ref_PPI | 68 | month | `Month` |

## Rules worth knowing

1. **Fact_Sales** is net of returns: `Is_Return = TRUE` rows have negative quantity and value. Filter them out only when you count orders.
2. **Spot trader:** customer 1009990 (`Customer_Type = "Spot trader"`) buys only surplus 2-EH at a discount. Leave it out of churn and product-mix views.
3. **Margin** uses the standard cost for the order year (`Fact_Std_Cost`), so it is a gross margin at standard, not an actual margin.
4. **Make vs buy:** `Available_InHouse_kg` = surplus sold to the spot trader that month + own stock above one month of own sales. `Coverable_kg` = the smaller of that and what was bought. `Avoidable_Cost_USD` = coverable kg x (purchase price - our standard cost - USD 0.04/kg freight between plants), never below zero.
5. **Customer health** (as of 2026-09-30): Lapsed = no order for 3x the customer's median reorder gap (at least 120 days); At risk = more than 2x, or the last three gaps run at more than 2x the usual. `Revenue_at_Risk_USD` is filled for At risk customers, `Lost_Revenue_USD` for Lapsed ones.
6. **Plasticizer profile:** DINP share of the customer's DOTP + DINP volume in their first 12 months vs their last 12 months. Switched = 35% or less at the start and 65% or more at the end.
7. **Helper columns for the dashboard:** `Dim_Material[Product_Group]` (readable name of the material group), `Dim_Date[Year_Quarter]`, `Dim_Customer[Health_Status]` and `Dim_Customer[Plasticizer_Profile]` (copied from Fact_Customer_Health so they can be used as filters), `Pair_Label` on both make-vs-buy tables, `Fact_Customer_Health[Call_First]` (At risk, or lapsed in the last 12 months) and `Revenue_Exposure_USD` (revenue at risk plus revenue lost to a recent lapse).

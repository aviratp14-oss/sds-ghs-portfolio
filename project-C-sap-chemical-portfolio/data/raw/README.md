# Raw data: simulated SAP S/4HANA exports

Simulated SAP S/4HANA export for **Gulfport Oxo Chemicals**, a made-up US chemical producer
modelled on oxo-chemical companies like Eastman and BASF that make 2-ethylhexanol (2-EH) and also
use it to make plasticizers and acrylates.

- **Period:** Jan 2022 - Sep 2026 (57 months)
- **Currency / units:** USD, kg (some sales lines were keyed in MT or LB, see the cleaning notes below)
- **Generator:** [`scripts/01_generate_sap_data.py`](../../scripts/01_generate_sap_data.py). It's seeded, so re-running it gives exactly these files. File 13 is the one real input and isn't regenerated.

## What's real and what's simulated

| Real | Simulated |
|---|---|
| Chemical names and CAS numbers (46 real chemicals, CAS check digits validated) | Company, plants, customers, suppliers, sales reps (all fictional names) |
| Bills of materials based on real chemistry (2-EH + terephthalic acid -> DOTP, 2-EH + acrylic acid -> 2-EH acrylate, and so on) | Every order, PO, production order and stock figure |
| Monthly price movement from the FRED producer price index for basic organic chemicals (series PCU325199325199) | Base prices per chemical (realistic ballpark, not quotes) |

## The company

```
            Plant 1010 - Pasadena, TX                       Plant 1020 - Lake Charles, LA
  +-------------------------------------------+     +-------------------------------------------+
  | Propylene + H2 -> n-Butanal               |     | 2-EH* + Acrylic acid -> 2-EH Acrylate (D)  |
  | n-Butanal -> 2-Ethylhexanol (C) --+       |     | n-Butanol* + Acrylic acid -> Butyl Acrylate|
  | n-Butanal -> n-Butanol            |       |     | n-Butanol* + Acetic acid -> Butyl Acetate  |
  |                                   v       |     | Glycol ethers (PM, DPM, PMA), Ethyl Acetate|
  | 2-EH + Terephthalic acid -> DOTP (A)      |     | Traded goods: glycols, acetone, MEK, IPA...|
  | Isononanol + Phthalic anh. -> DINP (B)    |     +-------------------------------------------+
  | 2-EH -> DOA, TOTM plasticizers            |       * bought from outside suppliers under a
  +-------------------------------------------+         second material number, although plant
                                                         1010 makes the same chemical
```

## Files

| # | File | Rows | SAP source | What it holds |
|---|---|---|---|---|
| 01 | Material_Master_MARA | 46 | MARA | Material number, description, type (FERT finished, HALB semi-finished, ROH raw, HAWA traded), group |
| 02 | Material_Plant_MARC | 48 | MARC / MBEW | Plant extension, procurement type (E = make, F = buy), current standard price per 1,000 kg |
| 03 | Material_Classification_CAS | 81 | Classification | CAS number and GHS signal word per material (long format: one row per characteristic) |
| 04 | Bill_of_Materials_STPO | 44 | STPO | Components per 1,000 kg of output |
| 05 | Business_Partner_Customers | 165 | BP | Customers: country, city, industry, sales rep, customer since |
| 06 | Sales_Reps | 8 | - | Rep names and regions |
| 07 | Business_Partner_Suppliers | 19 | BP | Suppliers |
| 08 | Sales_Order_Items_VBAP | 13,887 | VBAK / VBAP | Sales order lines: date, customer, material, qty, list price, discount, net value, billing date |
| 09 | Purchase_Order_Items_EKPO | 4,660 | EKKO / EKPO | PO lines: date, supplier, material, qty, net price per 1,000 kg, value |
| 10 | Production_Orders_AFKO | 2,930 | AFKO / AFPO | Production orders: material, plant, dates, planned and confirmed qty |
| 11 | Month_End_Stock_MARD | 2,622 | MARD | Unrestricted stock per material, plant and month |
| 12 | Standard_Cost_History | 230 | MBEW history | Standard cost per material, re-set every January |
| 13 | Ref_PPI_Basic_Organic_Chemicals_FRED | 68 | FRED (real) | Monthly price index, Dec 2003 = 100 |

## Schema (after cleaning)

```
                         Dim_Sales_Rep
                              |
 Dim_Customer ------- Fact_Sales (08) ------- Dim_Material (01 + 02 + CAS from 03)
                              |                    |   |
                         Dim_Date            Fact_BOM (04)  Fact_Std_Cost (12)
                              |                    |
 Dim_Supplier ------- Fact_Purchases (09) ---------+
                              |                    |
                       Fact_Production (10) -------+
                       Fact_Stock (11) ------------+
                       Ref_PPI (13) -- Dim_Date
```

`Dim_Material` joins on material number. The scenario 2 check joins materials to each other on the
**cleaned CAS number**, which is why the CAS cleaning matters.

## Key materials per scenario

| Scenario | Material | Number | Plant | Type |
|---|---|---|---|---|
| 1 | A - DOTP (priority, higher margin) | 30000101 | 1010 | FERT |
| 1 | B - DINP (offset, lower margin) | 30000102 | 1010 | FERT |
| 2 | C - 2-Ethylhexanol (made in-house) | 30000201 | 1010 | FERT |
| 2 | C again - "Octanol 2-ethyl tech grade" (bought) | 10000209 | 1020 | ROH |
| 2 | D - 2-Ethylhexyl acrylate | 30000301 | 1020 | FERT |
| 2 | n-Butanol (made) / "Butan-1-ol" (bought) | 30000202 / 10000210 | 1010 / 1020 | FERT / ROH |
| 2 | PM (made) / "Cleaning solvent - glycol ether" (bought) | 30000403 / 10000109 | 1020 / 1010 | FERT / ROH |
| 3 | All customers in file 05, orders in file 08 | | | |

## Raw-data issues the cleaning step needs to handle

These are on purpose, the same kind of mess you get in a real SAP extract.

1. **Dates** are mostly `DD.MM.YYYY`, but about 8% of order and PO dates are `YYYY-MM-DD`.
2. **Units:** about 5% of sales lines are in MT and about 2% (plant 1020) in LB. The price per
   unit is in the same unit, so convert both qty and price to kg.
3. **Returns:** order type `RE` lines have negative qty and value (credit memo requests).
4. **Exact duplicate sales rows:** about 0.3% (same document and item twice).
5. **CAS formatting:** missing dashes (`104767`), leading/trailing spaces, a `CAS ` prefix, a
   `(mixture)` note, and two blanks.
6. **Country names:** `US`, `USA`, `United States`, `U.S.A.` and the like for the same country.
7. **Duplicate customers:** 4 customers appear twice (upper case, no punctuation, 9000xxx number).
8. **Blank sales rep** on about 4% of customers.
9. **Description case:** some material descriptions are in title case instead of upper case.
10. **Prices per 1,000 kg** in files 02, 09 and 12 (SAP price unit); sales prices are per unit.

## Columns in each file

Column names follow the SAP field descriptions. Quantities are in the unit given in the `Unit` or `Sales_Unit` column, and prices are per `Price_Unit` where there is one.

| File | Columns |
|---|---|
| 01_Material_Master_MARA.csv | `Material`, `Material_Description`, `Material_Type`, `Material_Group`, `Base_Unit`, `Created_On`, `Created_By` |
| 02_Material_Plant_MARC.csv | `Material`, `Plant`, `Procurement_Type`, `MRP_Controller`, `Standard_Price`, `Price_Unit`, `Currency` |
| 03_Material_Classification_CAS.csv | `Material`, `Class_Type`, `Class`, `Characteristic`, `Value` |
| 04_Bill_of_Materials_STPO.csv | `Parent_Material`, `Plant`, `BOM_Item`, `Component`, `Component_Qty`, `Base_Qty`, `Unit` |
| 05_Business_Partner_Customers.csv | `Business_Partner`, `Name`, `Country`, `City`, `Region`, `Industry`, `Sales_Rep`, `Customer_Since`, `Payment_Terms` |
| 06_Sales_Reps.csv | `Sales_Rep`, `Rep_Name`, `Sales_Region` |
| 07_Business_Partner_Suppliers.csv | `Supplier`, `Name`, `Country`, `City`, `Supplier_Type` |
| 08_Sales_Order_Items_VBAP.csv | `Sales_Document`, `Item`, `Order_Type`, `Created_On`, `Sold_To`, `Material`, `Plant`, `Order_Qty`, `Sales_Unit`, `List_Price_per_Unit`, `Discount_Pct`, `Net_Value`, `Currency`, `Billing_Date` |
| 09_Purchase_Order_Items_EKPO.csv | `Purchasing_Document`, `Item`, `Document_Date`, `Supplier`, `Material`, `Short_Text`, `Plant`, `PO_Qty`, `Order_Unit`, `Net_Price`, `Price_Unit`, `Currency`, `Delivery_Date`, `Net_Order_Value` |
| 10_Production_Orders_AFKO.csv | `Order`, `Order_Type`, `Material`, `Plant`, `Basic_Start`, `Basic_Finish`, `Planned_Qty`, `Confirmed_Qty`, `Unit`, `Status` |
| 11_Month_End_Stock_MARD.csv | `Material`, `Plant`, `Storage_Location`, `Fiscal_Period`, `Unrestricted_Stock`, `Unit` |
| 12_Standard_Cost_History.csv | `Material`, `Plant`, `Valid_From`, `Standard_Price`, `Price_Unit`, `Currency` |
| 13_Ref_PPI_Basic_Organic_Chemicals_FRED.csv | `observation_date`, `PCU325199325199` |

The PPI file comes from FRED (Federal Reserve Bank of St. Louis), series PCU325199325199, "Producer Price Index by Industry: All Other Basic Organic Chemical Manufacturing", from the US Bureau of Labor Statistics. BLS data is in the public domain. Source: https://fred.stlouisfed.org/series/PCU325199325199

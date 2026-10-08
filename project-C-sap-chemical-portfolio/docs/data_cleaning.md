# Data cleaning notes

The raw files are SAP-style exports, and they come with the problems I see in real extracts at work: two date formats in one column, lines keyed in the wrong unit, prices per 1,000 kg, duplicate customers, and CAS numbers typed every way possible. This page covers how I cleaned them, the calls I had to make, and how I checked the result.

Every issue is logged one per row in [`data/clean/DQ_Log.csv`](../data/clean/DQ_Log.csv) (24 entries), with an example, the rows affected and the fix.

## Where the cleaning happens

I did the cleaning in Excel: [`excel/Project_C_Data_Cleaning.xlsx`](../excel/Project_C_Data_Cleaning.xlsx).

- **One tab per SAP export.** The raw columns sit on the left exactly as they came out of SAP (grey headers).
- **Every fix is a formula** in the columns to the right (yellow headers), so you can click any cleaned value and see how it was derived from the raw one. Nothing is pasted over or typed in by hand.
- **Lookups** holds the mapping tables (country spellings to ISO codes, sales unit to kg factor).
- **DQ log** counts each issue with formulas (mostly SUMPRODUCT), so the counts update if the raw data changes.
- **Notes** explains the colour code and what each tab does.

The clean CSVs in `data/clean/` are the yellow columns plus the IDs, with the duplicate rows filtered out.

I then repeated the same cleaning in Python ([`scripts/02_clean_sap_exports.py`](../scripts/02_clean_sap_exports.py)) for two reasons. First, as a cross-check: the workbook and the script were built separately and they agree. Second, two tables need more than a row-by-row formula, so they're built in Python: make-vs-buy by month (matching bought and made materials on CAS number, then working out what was coverable each month) and customer health (each customer's median reorder gap).

## The issues

| Export | Issue | Rows | Fix |
|---|---|---|---|
| Material master | Descriptions in mixed case | 3 | Upper-cased all descriptions |
| Classification | CAS number badly formatted (`104767`, `' 71-36-3 '`, `CAS 80-62-6`, `107-98-2 (mixture)`) | 4 | Trimmed, stripped the prefix and the note, added the dashes |
| Classification | CAS number missing | 2 | Left blank. Both are traded goods we don't make, so they can't affect the make-vs-buy check |
| Classification | CAS check digit | 44 | Validated every cleaned CAS number with the check-digit rule. All pass |
| Material master + classification | Same chemical under two material numbers | 3 pairs | Kept both records, because the duplicate is the finding. Flagged in `Dim_Material` and listed in `Map_Make_vs_Buy` |
| Customers | Country written several ways (`BR`, `Brazil`, `DE`, `Germany`...) | 105 | Mapped to ISO 2-letter code and country name |
| Customers | Duplicate customer records (same name in upper case, no punctuation, 9000xxx number) | 4 | Removed the copies, which had no orders on them. Mapping kept in `Map_Customer_Duplicates` |
| Customers | Sales rep missing | 3 | Set to "Unassigned" |
| Suppliers | Country written several ways (`USA`, `U.S.A.`, `United States`) | 19 | Mapped to ISO code and name |
| Sales orders | Exact duplicate rows | 41 | Dropped |
| Sales orders | Two date formats in one column (`01.01.2022` and `2022-01-01`) | about 1,150 | Parsed both, stored as ISO dates |
| Sales orders | Lines keyed in MT instead of kg | 659 | Quantity x 1,000, price per unit / 1,000 |
| Sales orders | Lines keyed in LB instead of kg | 156 | 1 kg = 2.20462 lb, applied to quantity and price |
| Sales orders | Net value after unit conversion | 62 | Recomputed qty x price x (1 - discount) for every line. These 62 differ by more than $1, all from rounding |
| Sales orders | Returns with negative quantity and value | 96 | Kept and flagged `Is_Return`, so totals are net of returns |
| Sales orders | No cost or margin in the export | 13,846 | Added standard cost per kg for the order year, cost and margin |
| Purchase orders | Two date formats in one column | 408 | Same as sales orders |
| Prices (plant, PO, standard cost) | Stored per 1,000 kg, the SAP price unit | 230 | Divided by the price unit to get USD per kg |
| Bill of materials | Component quantities per 1,000 kg of output | 44 | Converted to kg of component per kg of product |
| Stock | Period stored as `YYYYMM` text | 2,622 | First day of the month, plus stock value at standard cost |

## Judgement calls

- **Keeping the duplicate materials.** In a real cleanup you'd merge 10000209 into 30000201. I kept both because the whole point of problem 2 is that they exist side by side, and the fix belongs in SAP, not in a CSV.
- **Returns stay in.** Revenue and volume are net of returns, which is how finance would report them. Order counts and customer health ignore return lines, because a credit memo isn't a sign the customer is still buying.
- **Standard cost, not actual.** The export has no actual cost, so margin uses the standard cost set each January. That's normal for this kind of analysis, but it means margin moves in steps once a year.
- **The spot trader.** Customer 1009990 only buys surplus 2-EH at a discount. It's kept in revenue, but left out of the product mix and customer health views, where it would skew everything.
- **Freight between plants.** I used $0.04/kg for moving 2-EH from Pasadena to Lake Charles. It's an assumption, and it's in one place in the script if you want to change it.
- **Churn thresholds.** "At risk" at 2x the usual gap and "lapsed" at 3x (minimum 120 days) are my rules of thumb. They're written in `DQ_Log` row 24 and in [data/README.md](../data/README.md).

## How I checked it

- The Excel workbook and the Python script were built independently. After recalculating the workbook, its cleaned sales tab has the same 13,846 lines and the same total kg as `Fact_Sales.csv`, and total margin agrees to within $750 out of $115M, which is rounding.
- Every CAS number passes the check-digit rule after cleaning.
- Sales net value after unit conversion matches qty x price x (1 - discount) to within $1 on all but 62 lines, and those are rounding.
- Customer count after removing duplicates is 160 regular customers plus the spot trader, which matches the business partner file once the 4 copies are gone.
- Every number on the four dashboard pages was recalculated from the CSVs with pandas, and they match the report to the rounding shown.
- The whole pipeline was rerun from scratch into an empty folder. The raw files and every clean table came out identical.

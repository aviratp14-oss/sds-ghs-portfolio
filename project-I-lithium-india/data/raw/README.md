# Raw data

These are the inputs exactly as each source reported them. Numbers are kept as text, with the source's own units, labels and quirks, so the cleaning in `../clean/` can be traced back to them. They're small, so they stay in the repo.

| File | Rows | What it is |
|---|---|---|
| `wits_india_imports_lithium_chemicals_2018_2024.csv` | 189 | India's imports of lithium carbonate (HS 283691) and lithium hydroxide (HS 282520) by partner, 2018 to 2024, downloaded from World Bank WITS (UN Comtrade). Includes a "World" row per year and product |
| `ev_sales_reported.csv` | 50 | Every EV sales figure I collected, as written in the source: period, segment label, value and unit |
| `other_facts_reported.csv` | 66 | Single figures from reports and articles (storage path, device sales, Reasi grade, recycling rules, world supply and so on), each with the quote or note it came from |
| `source_register.csv` | 32 | Source ID, publisher, title, year, link and the date I accessed it |

## Columns

**wits_india_imports_lithium_chemicals_2018_2024.csv**

| Column | Meaning |
|---|---|
| Reporter | Always India |
| Year | Calendar year |
| HS6 | 283691 lithium carbonate, 282520 lithium oxide and hydroxide |
| Product | Product name as WITS gives it |
| Partner | Country India imported from, or "World" for the total |
| Trade_Value_USD_Thousand | Import value in thousands of USD, as text with commas |
| Quantity | Quantity as text with commas |
| Quantity_Unit | Kg |

**ev_sales_reported.csv**

| Column | Meaning |
|---|---|
| Source_ID | Links to `source_register.csv` |
| Period_As_Reported | FY2025, FY 2024-25, CY2025 and so on, as written |
| Segment_As_Reported | The source's own name for the vehicle segment |
| Value_As_Reported | The number as written, including "lakh", "~" or Indian digit grouping |
| Unit_As_Reported | units, million, % of EV sales, % penetration, GWh and so on |
| Note | Anything the source said about what the number covers |

**other_facts_reported.csv**

| Column | Meaning |
|---|---|
| Source_ID | Links to `source_register.csv` |
| Topic | Grid storage, electronics, mining, recycling, supply and so on |
| Item | What the figure is |
| Period | The year or period it refers to |
| Value_As_Reported | The figure as written |
| Unit_As_Reported | Its unit |
| Quote_Or_Note | The sentence it came from, or a note on how I read it |

## Licence

Trade data: UN Comtrade via World Bank WITS, under their terms of use. The other files are short facts and figures quoted from public reports, each credited by source ID. The publishers keep their rights to the original reports.

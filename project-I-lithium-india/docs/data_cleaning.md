# Data cleaning

There was no single dataset for this project. Most inputs are figures scattered across reports, news articles and parliamentary answers, so the first job was to collect them in one place exactly as reported and then clean them in a way anyone can trace.

I did the cleaning twice. [`excel/Project_I_Data_Cleaning.xlsx`](../excel/Project_I_Data_Cleaning.xlsx) does it with formulas: grey columns hold the raw values as collected (numbers kept as text, like the source pages), and yellow columns next to them hold my cleaning formulas. It uses only plain functions (SUMIFS, VLOOKUP, SUBSTITUTE, IF), so it opens the same in Excel, Google Sheets and LibreOffice. [`scripts/01_clean_raw_data.py`](../scripts/01_clean_raw_data.py) repeats every step in Python, writes the clean CSVs and the DQ log, and acts as the cross-check.

| Workbook tab | What it does |
|---|---|
| Notes | How the workbook is laid out |
| DQ_Log | Every issue found and how many rows it affects |
| Lookups | Segment names, period formats and conversion factors |
| Raw_Trade | WITS import rows with the cleaning columns |
| Trade_Summary | World rows vs partner sums, clean quantities in LCE |
| EV_Reported | Every EV sales figure collected, mapped to a standard segment |
| Base_Year_2025 | 2025 EV units and market size per segment |
| Chemistry | Lithium per kWh from cathode chemistry |
| Industry_Baseline | Grease, glass and pharma use from the trade data |
| Sources | The source register |

## 1. Trade data (UN Comtrade via WITS)

India's imports of lithium carbonate (HS 283691) and lithium hydroxide (HS 282520) by partner, 2018 to 2024. 189 rows.

**Numbers stored as text.** Values came as "14,622.29" in thousands of USD and quantities as "1,656,320". Converted to numbers, and values to plain USD.

**World rows mixed in with partners.** Each year and product has a "World" row on top of the partner rows. I kept those 14 rows only to reconcile against the partner sum (differences were rounding only) and left them out of the partner table, so nothing gets counted twice.

**Quantities that can't be right.** This was the interesting one. Ireland shows up every year selling India "lithium carbonate" at about $0.55 a kg, for example 600 t for $354k in 2023. Real lithium carbonate cost $10 to $60 a kg over this period. The Netherlands, France and the UK did the same in some years. It's almost certainly a different, cheap product booked under the same code. I flagged any row below $3 a kg (16 rows) and re-estimated its quantity as value divided by that year's clean unit value for the same product.

This matters a lot for carbonate. The flagged rows were about half of the reported carbonate tonnage. In 2023, for example, reported imports were 1,180 t and the clean figure is 587 t. Without this step India's industrial lithium use would be overstated by roughly double.

**India as its own partner.** One 2024 row lists India as the partner (a re-import). Kept in value and flagged.

After cleaning, imports work out to about 2 to 3 kt LCE a year. The 2022 to 2024 average sets the 2025 baseline for grease (90% of hydroxide), glass and ceramics (50% of carbonate) and pharma and other uses (the rest). The grease figure, 1,080 t LCE, agrees within 5% with what an NLGI grease survey implies (about 1,031 t LCE).

## 2. EV sales (seven sources)

50 figures from Vahan (via Autocar Professional), EVreporter, JMK Research, IESA, WRI India, NITI Aayog and CES.

**36 names for the same few segments.** "Electric two-wheelers (e2W)", "E-2W (high-speed)", "e2W" and "Electric 2W" are all the same thing. A mapping table (on the Lookups tab in the workbook, `SEG_MAP` in the script) puts every label into a standard segment: 2W, 3W_L3, 3W_L5, 4W, Bus, Truck, CV or Total. Nothing was left unmapped.

**Numbers written the Indian way, or in words.** "20,37,831", ">25 lakh", "~29" and "almost 10" all had to become plain numbers. 11 values needed this.

**Fiscal years written three ways.** FY2025, FY 2024-25 and FY2025-26 were standardised to FYyyyy, using the year the fiscal year ends. Calendar years stay as CYyyyy.

**Sources disagree.** For FY2025, Vahan retail data says 1,964,831 EVs and EVreporter says 2,037,831, a 3.7% gap. EVreporter counts e-carts and some low-speed models that Vahan misses. I kept both, used Vahan for history and IESA's CY2025 figure for the base year.

## 3. Base year 2025

No single source gives calendar 2025 sales by segment. So units = IESA's CY2025 total (2.6 million) x IESA's segment shares, and the total market = EV units / EV penetration. Penetration comes from EVreporter's FY2025 figures (2W 6.2%, cars 2.7%, L5 three-wheelers about 22%), rolled forward one year.

| Segment | EV units 2025 | EV share | Market |
|---|---|---|---|
| Two-wheelers | 1,562,600 | 7.8% | 20.0 million |
| L5 three-wheelers | 205,400 | 25% | 822,000 |
| E-rickshaws (L3) | 616,200 | 100% | 616,000 |
| Cars | 200,200 | 4.5% | 4.4 million |
| Buses | 5,200 | 5.2% | 100,000 |
| Trucks | 10,400 | 1.1% | 945,000 |

## 4. Everything else

The other inputs (storage path, device sales, Reasi grade, recycling rules, world supply) are single figures from one source each. They sit in `data/raw/other_facts_reported.csv` with the quote or note they came from, and go into `Assumptions.csv` with their source ID.

## DQ log

All 12 rules, with row counts, are in [`data/clean/DQ_Log.csv`](../data/clean/DQ_Log.csv).

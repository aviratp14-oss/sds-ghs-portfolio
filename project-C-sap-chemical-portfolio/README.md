# Chemical portfolio analytics on SAP data

![Overview page of the dashboard](images/01_overview.jpg)

Most of my day job is cleaning up ERP data for chemical companies: material masters, customer records, order lines. The same few problems come up again and again, and they almost never look like data problems at first. They look like a sales problem, or a purchasing problem. So for this project I built a chemical company's SAP data from scratch, put three of those problems into it, and then worked through them the way I would on a real account.

The company is **Gulfport Oxo Chemicals**. It's made up, but it's modelled on oxo-chemical producers like Eastman and BASF: two US Gulf Coast plants that make 2-ethylhexanol (2-EH) and turn some of it into plasticizers and acrylates. It sells about $110M a year to 160 customers. The data covers January 2022 to September 2026.

The three questions:

1. **Why is the priority product losing?** DOTP earns more than twice the margin of DINP, yet DINP keeps taking its place.
2. **Why is one plant buying a chemical the other plant makes?** Lake Charles buys 2-EH outside every month while Pasadena sells its spare 2-EH to a trader at a discount.
3. **Which customers are drifting away?** Some customers stop ordering without saying anything, and a fixed "90 days without an order" rule misses most of them.

I cleaned the SAP exports in Excel, cross-checked them and built the scenario tables in Python, and put everything into a four-page Power BI report styled like an SAP Fiori app.

## What I found

- **DOTP went from 76% of plasticizer volume in 2022 to 21% in 2026.** DINP overtook it in early 2025. DOTP earns $0.62 a kg at standard cost and DINP $0.24.
- **21 of 55 plasticizer customers switched from DOTP to DINP**, and that cost $3.9M of margin since 2022 ($1.7M in 2025 alone). Two sales reps give DINP an 8% average discount against about 3% for everyone else. My read is that this is about how reps are paid, not the market: on a volume bonus, the cheaper product is the easier sale.
- **The company spent $10.2M in 2025 buying chemicals it already makes, and $2.1M of that was avoidable** ($10.6M since 2022). Almost all of it is 2-EH. In 2025 Lake Charles bought 2,419 t of 2-EH at about $1.98/kg, while Pasadena sold 3,946 t of its own to a trader at 26% below list. Pasadena's cost, freight included, was about $1.18/kg.
- **The root cause is master data, not purchasing.** A buyer created a second material record for 2-EH under a different name, and its CAS number was saved without dashes (`104767`), so neither a name search nor a CAS lookup found the original. Once I cleaned the CAS numbers, the same check found two more pairs (n-butanol and PM).
- **8 customers are at risk and 4 lapsed in the last 12 months.** That's $2.3M a year at risk and $5.0M a year already lost. Customers who switched to DINP are the most likely to be at risk (14%), and loyal DOTP buyers are the least likely to leave. Once a customer buys on price, they keep shopping on price.

The full write-up, with what I'd change in SAP to stop each problem happening again, is in [docs/business_problems.md](docs/business_problems.md).

## The dashboard

| Page | What it shows |
|---|---|
| [Overview](images/01_overview.jpg) | Revenue, gross margin, volume and active customers, compared with the same months a year earlier |
| [Product Mix](images/02_product_mix.jpg) | DOTP vs DINP share by quarter, customers who switched, margin lost, DINP discount by sales rep |
| [Internal Sourcing](images/03_internal_sourcing.jpg) | Spend on chemicals the company also makes, avoidable cost, 2-EH bought outside vs surplus sold cheap |
| [Customer Health](images/04_customer_health.jpg) | Active, at-risk and lapsed customers, revenue at risk, and a list of customers to call first |

There's a PDF of all four pages in [dashboard/ProjectC.pdf](dashboard/ProjectC.pdf) if you don't have Power BI. For a page-by-page explanation of every number, see [docs/dashboard_walkthrough.md](docs/dashboard_walkthrough.md).

![Internal sourcing page](images/03_internal_sourcing.jpg)

## Data

The data is simulated, but I tried hard to make it behave like a real SAP S/4HANA extract.

| What's real | What's simulated |
|---|---|
| 46 real chemicals with their real CAS numbers (check digits validated) | The company, plants, customers, suppliers and sales reps |
| Recipes based on real chemistry (2-EH + terephthalic acid makes DOTP, 2-EH + acrylic acid makes 2-EH acrylate, and so on) | Every sales order, purchase order, production order and stock figure |
| Monthly price movement from the US producer price index for basic organic chemicals (FRED series PCU325199325199) | Base prices per chemical (realistic ballpark, not quotes) |

The raw files follow SAP table layouts: material master (MARA, MARC), classification, bill of materials (STPO), business partners, sales order items (VBAP), purchase order items (EKPO), production orders (AFKO), month-end stock (MARD) and standard cost history. They also carry the kind of mess you get in a real extract: two date formats in one column, sales lines keyed in MT or LB instead of kg, duplicate rows, CAS numbers without dashes, the same country written four ways, and duplicate customers.

Raw files are in [data/raw/](data/raw/) with a column-by-column dictionary. The cleaned tables and their rules are in [data/](data/).

## How I built it

1. **Data generation (Python).** A seeded script writes the 12 SAP export files, so anyone can rebuild exactly the same data. The three scenarios are built in, but the script doesn't hand out the answers: you only find them by joining and cleaning the data.
2. **Cleaning (Excel).** [excel/Project_C_Data_Cleaning.xlsx](excel/Project_C_Data_Cleaning.xlsx) has one tab per SAP export. The raw columns stay as they came (grey), and every fix is a formula next to them (yellow), so each cleaned value can be traced back to the raw one. A DQ log tab counts each issue with formulas. More in [docs/data_cleaning.md](docs/data_cleaning.md).
3. **Cross-check and scenario tables (Python, pandas).** A script repeats the same cleaning to check the workbook, writes the clean CSVs, and builds the two tables that need more than a formula: make-vs-buy by month (matching materials on cleaned CAS number) and customer health (each customer's own reorder rhythm).
4. **Power BI.** Seventeen tables, 64 DAX measures in five folders, and four pages with the same layout. The top bar, side menu and KPI cards are SVG images drawn by DAX measures, which is how I got the Fiori look. The report is saved as a PBIP project (plain-text TMDL and JSON), so the model and every visual can be read on GitHub.

## Repo layout

```
project-C-sap-chemical-portfolio/
├── images/       screenshots of each dashboard page
├── dashboard/    ProjectC.pdf and the Power BI project (ProjectC/ProjectC.pbip)
├── data/         raw SAP exports, cleaned CSVs, data dictionary
├── excel/        the data cleaning workbook
├── scripts/      data generation, cleaning, workbook and Power BI build scripts, in run order
└── docs/         business problems, dashboard walkthrough, cleaning notes
```

## Running it yourself

**Just the dashboard:** clone the repo and open `dashboard/ProjectC/ProjectC.pbip` in Power BI Desktop, then point the `DataFolder` parameter at `data/clean/` and hit Refresh. [HOW_TO_OPEN.md](dashboard/ProjectC/HOW_TO_OPEN.md) has the steps.

**Everything from scratch:** run the four scripts in order. See [scripts/README.md](scripts/README.md).

## Limits worth knowing

- The data is simulated. The chemicals, recipes and price trend are real, but every order, customer and supplier is invented, so the findings show the method, not a real company.
- Margin is at standard cost, not actual cost.
- The make-vs-buy saving assumes the two plants can ship to each other at $0.04/kg and that the grades are interchangeable. In real life you'd check the specs first.
- Customer health is a rule based on order rhythm, not a predictive model. It's meant to give sales a short call list, not a churn probability.
- 2026 only runs to September, so the cards compare January to September with the same months a year earlier.

## What's next

- A proper churn model on top of the reorder-gap rule, using order size and product mix as well as timing.
- A what-if page for the rep incentive change: how much margin comes back if the two outlier reps discount like everyone else.

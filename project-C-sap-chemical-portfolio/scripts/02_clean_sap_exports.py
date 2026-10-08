"""Project C - clean the raw SAP exports into Power BI-ready tables (data/clean/).

Run order: 01_generate_sap_data.py (only if the raw files need rebuilding), then this script.
Unit standard: quantities in kg (_kg), money in USD (_USD), prices in USD per kg (_USD_per_kg),
dates ISO yyyy-mm-dd, Snake_Case column names with the unit as the last part.
Every fix is written to DQ_Log.csv.
"""
import re
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW, OUT = BASE / "data" / "raw", BASE / "data" / "clean"
OUT.mkdir(exist_ok=True)
AS_OF = pd.Timestamp("2026-09-30")  # data cut-off
FREIGHT_USD_PER_KG = 0.04  # truck/rail transfer Pasadena TX -> Lake Charles LA (assumption, see docs)
LB_PER_KG = 2.20462

log = []


def dq(dataset, issue, example, rows, fix):
    log.append(dict(ID=len(log) + 1, Dataset=dataset, Issue=issue, Example=example, Rows_Affected=rows, Fix=fix))


def read(name, **kw):
    return pd.read_csv(RAW / name, dtype=str, keep_default_na=False, **kw)


def parse_dates(s, dataset, col):
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}$")
    d = pd.to_datetime(s.where(~iso), format="%d.%m.%Y", errors="coerce")
    d = d.fillna(pd.to_datetime(s.where(iso), format="%Y-%m-%d", errors="coerce"))
    if iso.any():
        dq(dataset, f"{col}: two date formats in one column", "01.01.2022 and 2022-01-01", int(iso.sum()),
           "Parsed DD.MM.YYYY and YYYY-MM-DD separately; stored as ISO yyyy-mm-dd")
    assert d.notna().all(), f"unparsed dates in {dataset}.{col}"
    return d


def clean_cas(v):
    v = v.strip().upper().replace("CAS", "").strip()
    v = re.sub(r"\(.*?\)", "", v).strip()
    if re.fullmatch(r"\d{5,10}", v):  # dashes missing: last digit = check, two before = middle block
        v = f"{v[:-3]}-{v[-3:-1]}-{v[-1]}"
    return v if re.fullmatch(r"\d{2,7}-\d{2}-\d", v) else ""


def cas_ok(c):
    a, b, chk = c.split("-")
    return sum((i + 1) * int(x) for i, x in enumerate((a + b)[::-1])) % 10 == int(chk)


COUNTRY = {"US": "US", "USA": "US", "UNITED STATES": "US", "U.S.A.": "US", "CA": "CA", "CANADA": "CA",
           "MX": "MX", "MEXICO": "MX", "BR": "BR", "BRAZIL": "BR", "DE": "DE", "GERMANY": "DE",
           "NL": "NL", "NETHERLANDS": "NL", "BE": "BE", "BELGIUM": "BE", "IN": "IN", "INDIA": "IN"}
COUNTRY_NAME = {"US": "United States", "CA": "Canada", "MX": "Mexico", "BR": "Brazil", "DE": "Germany",
                "NL": "Netherlands", "BE": "Belgium", "IN": "India"}

# ------------------------------------------------------------------ materials
mara = read("01_Material_Master_MARA.csv")
title = mara["Material_Description"] != mara["Material_Description"].str.upper()
dq("01 Material master", "Descriptions in mixed case", mara.loc[title, "Material_Description"].iloc[0], int(title.sum()),
   "Upper-cased all descriptions")
mara["Material_Description"] = mara["Material_Description"].str.upper().str.strip()

cls = read("03_Material_Classification_CAS.csv")
cas = cls[cls["Characteristic"] == "CAS_NUMBER"][["Material", "Value"]].rename(columns={"Value": "CAS_Raw"})
cas["CAS_No"] = cas["CAS_Raw"].map(clean_cas)
changed = cas[(cas["CAS_Raw"] != cas["CAS_No"]) & (cas["CAS_No"] != "")]
for _, r in changed.iterrows():
    dq("03 Classification", "CAS number badly formatted", repr(r["CAS_Raw"]), 1,
       f"Normalised to {r['CAS_No']} (material {r['Material']})")
blank = cas[cas["CAS_No"] == ""]
dq("03 Classification", "CAS number missing", ", ".join(blank["Material"]), len(blank),
   "Left blank; these traded goods are not produced in-house, so they cannot affect the make-vs-buy check")
bad = [c for c in cas["CAS_No"] if c and not cas_ok(c)]
assert not bad, bad
dq("03 Classification", "CAS check digit", "all non-blank values", int((cas["CAS_No"] != "").sum()),
   "Validated every cleaned CAS number with the CAS check-digit rule; all pass")
sig = cls[cls["Characteristic"] == "GHS_SIGNAL_WORD"][["Material", "Value"]].rename(columns={"Value": "GHS_Signal_Word"})

marc = read("02_Material_Plant_MARC.csv")
home = marc.drop_duplicates("Material")[["Material", "Plant"]]  # first row = home plant
TYPE_NAME = {"FERT": "Finished good (made)", "HALB": "Intermediate (made)", "ROH": "Raw material (bought)",
             "HAWA": "Traded good (bought for resale)"}
ROLE = {"30000101": "A - priority product (DOTP)", "30000102": "B - offset product (DINP)",
        "30000201": "C - made in-house (2-EH)", "10000209": "C - bought from outside (2-EH)",
        "30000301": "D - product that uses C (2-EH acrylate)"}
dim_mat = (mara.merge(home, on="Material").merge(cas[["Material", "CAS_No", "CAS_Raw"]], on="Material", how="left")
           .merge(sig, on="Material", how="left"))
dim_mat = pd.DataFrame({
    "Material_Id": dim_mat["Material"], "Material_Name": dim_mat["Material_Description"],
    "Material_Type": dim_mat["Material_Type"], "Material_Type_Name": dim_mat["Material_Type"].map(TYPE_NAME),
    "Material_Group": dim_mat["Material_Group"], "Home_Plant": dim_mat["Plant"],
    "CAS_No": dim_mat["CAS_No"].fillna(""), "CAS_Raw": dim_mat["CAS_Raw"].fillna(""),
    "GHS_Signal_Word": dim_mat["GHS_Signal_Word"].fillna("").replace("", "Not recorded"),
    "Scenario_Role": dim_mat["Material"].map(ROLE).fillna(""),
    "Created_On": parse_dates(dim_mat["Created_On"], "01 Material master", "Created_On").dt.date,
    "Created_By": dim_mat["Created_By"],
})
# short display names for charts
SHORT = {"30000101": "DOTP", "30000102": "DINP", "30000103": "DOA", "30000104": "TOTM", "30000201": "2-EH",
         "30000202": "n-Butanol", "30000203": "Isobutanol", "30000204": "2-EH Acid", "30000301": "2-EH Acrylate",
         "30000302": "Butyl Acrylate", "30000401": "Butyl Acetate", "30000402": "Ethyl Acetate", "30000403": "PM",
         "30000404": "DPM", "30000405": "PMA", "20000101": "n-Butanal"}
dim_mat["Short_Name"] = dim_mat["Material_Id"].map(SHORT).fillna(dim_mat["Material_Name"].str.title())
GROUP_NAME = {"PLAST": "Plasticizers", "OXOALC": "Oxo alcohols", "ACRYL": "Acrylates", "SOLV": "Solvents", "GLYCOL": "Glycols",
              "POLYOL": "Polyols", "OXOINT": "Intermediates", "FEED": "Feedstocks", "CATAL": "Catalysts", "ADDIT": "Additives", "MRO": "Maintenance supplies"}
dim_mat["Product_Group"] = dim_mat["Material_Group"].map(GROUP_NAME)
assert dim_mat["Product_Group"].notna().all()

# make-vs-buy: bought materials (ROH/HAWA) sharing a CAS number with a made one (FERT/HALB)
made = dim_mat[dim_mat["Material_Type"].isin(["FERT", "HALB"]) & (dim_mat["CAS_No"] != "")]
bought = dim_mat[dim_mat["Material_Type"].isin(["ROH", "HAWA"]) & (dim_mat["CAS_No"] != "")]
pairs = bought.merge(made, on="CAS_No", suffixes=("_Bought", "_Made"))
pairs = pairs[["CAS_No", "Material_Id_Bought", "Material_Name_Bought", "Home_Plant_Bought",
               "Material_Id_Made", "Material_Name_Made", "Home_Plant_Made"]]
pairs.columns = ["CAS_No", "Bought_Material_Id", "Bought_Material_Name", "Buying_Plant", "Made_Material_Id",
                 "Made_Material_Name", "Making_Plant"]
dq("01+03 Material master", "Same chemical under two material numbers (one made, one bought)",
   "; ".join(f"{r.Bought_Material_Id} = {r.Made_Material_Id} (CAS {r.CAS_No})" for r in pairs.itertuples()),
   len(pairs), "Kept both records (the duplicate is the finding); flagged in Dim_Material and listed in Map_Make_vs_Buy")
dim_mat["Same_CAS_As"] = dim_mat["Material_Id"].map(
    dict(zip(pairs["Bought_Material_Id"], pairs["Made_Material_Id"])) | dict(zip(pairs["Made_Material_Id"], pairs["Bought_Material_Id"]))
).fillna("")

# ------------------------------------------------------------------ standard cost (per kg, by year)
sch = read("12_Standard_Cost_History.csv")
sch["Year"] = parse_dates(sch["Valid_From"], "12 Standard cost", "Valid_From").dt.year
sch["Std_Cost_USD_per_kg"] = sch["Standard_Price"].astype(float) / sch["Price_Unit"].astype(float)
dq("02/09/12 prices", "Prices stored per 1,000 kg (SAP price unit)", "Standard_Price 1385.10 per 1000 KG", len(sch),
   "Divided by Price_Unit to get USD per kg")
fact_std = sch[["Material", "Plant", "Year", "Std_Cost_USD_per_kg"]].rename(columns={"Material": "Material_Id"})
fact_std["Std_Cost_USD_per_kg"] = fact_std["Std_Cost_USD_per_kg"].round(4)
std_key = fact_std.set_index(["Material_Id", "Year"])["Std_Cost_USD_per_kg"]

# ------------------------------------------------------------------ customers
bp = read("05_Business_Partner_Customers.csv")
cn = bp["Country"].str.upper().str.strip()
dq("05 Customers", "Country written several ways", ", ".join(sorted(bp["Country"].unique())[:8]),
   int((bp["Country"] != cn.map(COUNTRY)).sum()), "Mapped to ISO 2-letter code + country name")
bp["Country_Code"] = cn.map(COUNTRY)
assert bp["Country_Code"].notna().all()
# duplicates: same name ignoring case and punctuation
key = bp["Name"].str.upper().str.replace(r"[^A-Z0-9 ]", "", regex=True).str.split().str.join(" ")
first = bp.groupby(key)["Business_Partner"].transform("first")
dup = bp[bp["Business_Partner"] != first]
dq("05 Customers", "Duplicate customer records (same name, upper case, no punctuation)",
   "; ".join(f"{a} = {b}" for a, b in zip(dup["Business_Partner"], first[dup.index])), len(dup),
   "Removed the copies (no orders were booked on them); mapping kept in Map_Customer_Duplicates")
map_dup = pd.DataFrame({"Duplicate_Customer_Id": dup["Business_Partner"], "Master_Customer_Id": first[dup.index]})
bp = bp[bp["Business_Partner"] == first]
nrep = bp["Sales_Rep"].eq("").sum()
dq("05 Customers", "Sales rep missing", "Sales_Rep blank", int(nrep), "Set to 'Unassigned'")
dim_cust = pd.DataFrame({
    "Customer_Id": bp["Business_Partner"], "Customer_Name": bp["Name"], "Country_Code": bp["Country_Code"],
    "Country": bp["Country_Code"].map(COUNTRY_NAME), "City": bp["City"], "State_Region": bp["Region"],
    "Industry": bp["Industry"], "Sales_Rep_Id": bp["Sales_Rep"].replace("", "Unassigned"),
    "Customer_Since": parse_dates(bp["Customer_Since"], "05 Customers", "Customer_Since").dt.date,
    "Payment_Terms": bp["Payment_Terms"],
    "Customer_Type": np.where(bp["Business_Partner"] == "1009990", "Spot trader", "Regular"),
})

reps = read("06_Sales_Reps.csv").rename(columns={"Sales_Rep": "Sales_Rep_Id"})
reps = pd.concat([reps, pd.DataFrame([{"Sales_Rep_Id": "Unassigned", "Rep_Name": "Unassigned", "Sales_Region": "Unassigned"}])])
sup = read("07_Business_Partner_Suppliers.csv")
dim_sup = pd.DataFrame({"Supplier_Id": sup["Supplier"], "Supplier_Name": sup["Name"],
                        "Country_Code": sup["Country"].str.upper().str.strip().map(COUNTRY), "City": sup["City"]})
dim_sup["Country"] = dim_sup["Country_Code"].map(COUNTRY_NAME)
dq("07 Suppliers", "Country written several ways", "USA, U.S.A., United States", len(sup), "Mapped to ISO code + name")
dim_plant = pd.DataFrame({"Plant": ["1010", "1020"], "Plant_Name": ["Pasadena, TX", "Lake Charles, LA"],
                          "Plant_Role": ["Oxo alcohols and plasticizers", "Acrylates, solvents and traded goods"]})

# ------------------------------------------------------------------ sales
so = read("08_Sales_Order_Items_VBAP.csv")
n0 = len(so)
so = so.drop_duplicates()
dq("08 Sales orders", "Exact duplicate rows", "same Sales_Document + Item twice", n0 - len(so), "Dropped the copies")
so["Order_Date"] = parse_dates(so["Created_On"], "08 Sales orders", "Created_On")
so["Billing_Date"] = parse_dates(so["Billing_Date"], "08 Sales orders", "Billing_Date")
qty, price = so["Order_Qty"].astype(float), so["List_Price_per_Unit"].astype(float)
factor = so["Sales_Unit"].map({"KG": 1.0, "MT": 1000.0, "LB": 1 / LB_PER_KG})
for u in ("MT", "LB"):
    dq("08 Sales orders", f"Lines keyed in {u} instead of KG", f"Sales_Unit = {u}", int((so["Sales_Unit"] == u).sum()),
       "Converted quantity and price per unit to kg (1 MT = 1,000 kg; 1 kg = 2.20462 lb)")
so["Qty_kg"] = (qty * factor).round(1)
so["List_Price_USD_per_kg"] = (price / factor).round(4)
so["Discount_Share"] = (so["Discount_Pct"].astype(float) / 100).round(4)
so["Net_Value_USD"] = so["Net_Value"].astype(float)
chk = (so["Qty_kg"] * so["List_Price_USD_per_kg"] * (1 - so["Discount_Share"]) - so["Net_Value_USD"]).abs()
dq("08 Sales orders", "Net value check after unit conversion", "qty x price x (1 - discount) vs Net_Value",
   int((chk > 1).sum()), "Recomputed for every line; differences above USD 1 counted here (rounding only)")
ret = so["Order_Type"] == "RE"
dq("08 Sales orders", "Returns (credit memo requests) with negative qty and value", "Order_Type = RE", int(ret.sum()),
   "Kept, flagged Is_Return = TRUE; volumes and revenue are net of returns")
so["Year"] = so["Order_Date"].dt.year
std = [std_key.get((m, y), np.nan) for m, y in zip(so["Material"], so["Year"])]
so["Std_Cost_USD_per_kg"] = std
so["Cost_USD"] = (so["Qty_kg"] * so["Std_Cost_USD_per_kg"]).round(2)
so["Margin_USD"] = (so["Net_Value_USD"] - so["Cost_USD"]).round(2)
fact_sales = pd.DataFrame({
    "Sales_Doc": so["Sales_Document"], "Item": so["Item"].astype(int), "Order_Type": so["Order_Type"],
    "Is_Return": ret, "Order_Date": so["Order_Date"].dt.date, "Billing_Date": so["Billing_Date"].dt.date,
    "Customer_Id": so["Sold_To"], "Material_Id": so["Material"], "Plant": so["Plant"],
    "Qty_kg": so["Qty_kg"], "List_Price_USD_per_kg": so["List_Price_USD_per_kg"],
    "Discount_Share": so["Discount_Share"], "Net_Value_USD": so["Net_Value_USD"].round(2),
    "Net_Price_USD_per_kg": (so["Net_Value_USD"] / so["Qty_kg"]).round(4),
    "Std_Cost_USD_per_kg": so["Std_Cost_USD_per_kg"].round(4), "Cost_USD": so["Cost_USD"], "Margin_USD": so["Margin_USD"],
}).sort_values(["Order_Date", "Sales_Doc", "Item"])
assert fact_sales["Std_Cost_USD_per_kg"].notna().all()
dq("08 Sales orders", "No cost or margin in the export", "-", len(fact_sales),
   "Added standard cost per kg for the order year (file 12), Cost_USD and Margin_USD")

# ------------------------------------------------------------------ purchases
po = read("09_Purchase_Order_Items_EKPO.csv")
po["Doc_Date"] = parse_dates(po["Document_Date"], "09 Purchase orders", "Document_Date")
po["Deliv"] = parse_dates(po["Delivery_Date"], "09 Purchase orders", "Delivery_Date")
fact_po = pd.DataFrame({
    "PO_Number": po["Purchasing_Document"], "Item": po["Item"].astype(int), "PO_Date": po["Doc_Date"].dt.date,
    "Delivery_Date": po["Deliv"].dt.date, "Supplier_Id": po["Supplier"], "Material_Id": po["Material"],
    "Plant": po["Plant"], "Qty_kg": po["PO_Qty"].astype(float),
    "Price_USD_per_kg": (po["Net_Price"].astype(float) / po["Price_Unit"].astype(float)).round(4),
    "Value_USD": po["Net_Order_Value"].astype(float).round(2),
}).sort_values(["PO_Date", "PO_Number"])

# ------------------------------------------------------------------ production, BOM, stock
pr = read("10_Production_Orders_AFKO.csv")
fact_prod = pd.DataFrame({
    "Production_Order": pr["Order"], "Material_Id": pr["Material"], "Plant": pr["Plant"],
    "Start_Date": parse_dates(pr["Basic_Start"], "10 Production orders", "Basic_Start").dt.date,
    "Finish_Date": parse_dates(pr["Basic_Finish"], "10 Production orders", "Basic_Finish").dt.date,
    "Planned_Qty_kg": pr["Planned_Qty"].astype(float), "Confirmed_Qty_kg": pr["Confirmed_Qty"].astype(float),
    "Status": pr["Status"].map({"TECO": "Completed", "REL": "Released"}),
})
bom = read("04_Bill_of_Materials_STPO.csv")
fact_bom = pd.DataFrame({"Parent_Material_Id": bom["Parent_Material"], "Plant": bom["Plant"],
                         "Component_Material_Id": bom["Component"],
                         "Component_kg_per_kg": (bom["Component_Qty"].astype(float) / bom["Base_Qty"].astype(float)).round(5)})
dq("04 BOM", "Component quantities per 1,000 kg of output", "Component_Qty 680 / Base_Qty 1000", len(bom),
   "Converted to kg of component per kg of product")
st = read("11_Month_End_Stock_MARD.csv")
st["Month"] = pd.to_datetime(st["Fiscal_Period"], format="%Y%m")
st["Year"] = st["Month"].dt.year
fact_stock = pd.DataFrame({"Month": st["Month"].dt.date, "Material_Id": st["Material"], "Plant": st["Plant"],
                           "Stock_kg": st["Unrestricted_Stock"].astype(float)})
fact_stock["Stock_Value_USD"] = (fact_stock["Stock_kg"] * [std_key.get((m, y), np.nan) for m, y in zip(st["Material"], st["Year"])]).round(2)
dq("11 Stock", "Period stored as YYYYMM text", "202201", len(st), "Converted to the first day of the month; added stock value at standard cost")

ppi = read("13_Ref_PPI_Basic_Organic_Chemicals_FRED.csv")
ref_ppi = pd.DataFrame({"Month": pd.to_datetime(ppi["observation_date"]).dt.date,
                        "PPI_Basic_Organic_Chemicals_Index": ppi["PCU325199325199"].astype(float)})

# ------------------------------------------------------------------ scenario 2: make vs buy, by month
fs = fact_sales.assign(Month=pd.to_datetime(fact_sales["Order_Date"]).dt.to_period("M").dt.to_timestamp())
fp = fact_po.assign(Month=pd.to_datetime(fact_po["PO_Date"]).dt.to_period("M").dt.to_timestamp())
stk = fact_stock.assign(Month=pd.to_datetime(fact_stock["Month"]))
spot_ids = set(dim_cust.loc[dim_cust["Customer_Type"] == "Spot trader", "Customer_Id"])
rows = []
for p in pairs.itertuples():
    b = fp[fp["Material_Id"] == p.Bought_Material_Id].groupby("Month").agg(Bought_kg=("Qty_kg", "sum"), Spend_USD=("Value_USD", "sum"))
    own = stk[(stk["Material_Id"] == p.Made_Material_Id) & (stk["Plant"] == p.Making_Plant)].set_index("Month")["Stock_kg"]
    sold = fs[fs["Material_Id"] == p.Made_Material_Id]
    demand = sold.groupby("Month")["Qty_kg"].sum()
    spot = sold[sold["Customer_Id"].isin(spot_ids)].groupby("Month")["Qty_kg"].sum()
    m = b.join(own.rename("Own_Stock_kg"), how="left").join(demand.rename("Own_Sales_kg"), how="left").join(spot.rename("Surplus_Sold_Spot_kg"), how="left").fillna(0)
    m = m.reset_index()
    m["Year"] = m["Month"].dt.year
    m["InHouse_Cost_USD_per_kg"] = [std_key.get((p.Made_Material_Id, y)) + FREIGHT_USD_PER_KG for y in m["Year"]]
    m["Buy_Price_USD_per_kg"] = m["Spend_USD"] / m["Bought_kg"]
    # in-house supply available that month: surplus dumped to the spot trader + stock above one month of own sales
    m["Available_InHouse_kg"] = m["Surplus_Sold_Spot_kg"] + (m["Own_Stock_kg"] - (m["Own_Sales_kg"] - m["Surplus_Sold_Spot_kg"])).clip(lower=0)
    m["Coverable_kg"] = np.minimum(m["Bought_kg"], m["Available_InHouse_kg"])
    m["Avoidable_Cost_USD"] = (m["Coverable_kg"] * (m["Buy_Price_USD_per_kg"] - m["InHouse_Cost_USD_per_kg"]).clip(lower=0)).round(2)
    for c in ("CAS_No", "Bought_Material_Id", "Made_Material_Id", "Buying_Plant", "Making_Plant"):
        m[c] = getattr(p, c)
    rows.append(m)
mvb = pd.concat(rows, ignore_index=True)
fact_mvb = mvb[["Month", "CAS_No", "Bought_Material_Id", "Made_Material_Id", "Buying_Plant", "Making_Plant", "Bought_kg",
                "Spend_USD", "Buy_Price_USD_per_kg", "InHouse_Cost_USD_per_kg", "Own_Stock_kg", "Surplus_Sold_Spot_kg",
                "Available_InHouse_kg", "Coverable_kg", "Avoidable_Cost_USD"]].copy()
fact_mvb["Month"] = fact_mvb["Month"].dt.date
for c in ("Buy_Price_USD_per_kg", "InHouse_Cost_USD_per_kg"):
    fact_mvb[c] = fact_mvb[c].round(4)
for c in ("Bought_kg", "Spend_USD", "Own_Stock_kg", "Surplus_Sold_Spot_kg", "Available_InHouse_kg", "Coverable_kg"):
    fact_mvb[c] = fact_mvb[c].round(1)
tot = fact_mvb.groupby("Bought_Material_Id")[["Spend_USD", "Avoidable_Cost_USD"]].sum()
pairs = pairs.merge(tot, left_on="Bought_Material_Id", right_index=True, how="left")
pairs = pairs.rename(columns={"Spend_USD": "Total_Spend_USD", "Avoidable_Cost_USD": "Total_Avoidable_Cost_USD"}).round(2)
short = dim_mat.set_index("Material_Id")["Short_Name"]
pairs["Pair_Label"] = [f"{short.get(m, m)} ({b} = {m})" for b, m in zip(pairs["Bought_Material_Id"], pairs["Made_Material_Id"])]
fact_mvb = fact_mvb.merge(pairs[["Bought_Material_Id", "Pair_Label"]], on="Bought_Material_Id", how="left")

# ------------------------------------------------------------------ scenario 1 + 3: customer health and A/B profile
reg = fs[~fs["Is_Return"] & ~fs["Customer_Id"].isin(spot_ids)].copy()
reg["Order_Date"] = pd.to_datetime(reg["Order_Date"])
orders = reg.groupby(["Customer_Id", "Sales_Doc"])["Order_Date"].min().reset_index().sort_values(["Customer_Id", "Order_Date"])
health = []
for cid, g in orders.groupby("Customer_Id"):
    d = g["Order_Date"].drop_duplicates().sort_values()
    gaps = d.diff().dt.days.dropna()
    med = float(gaps.median()) if len(gaps) else np.nan
    recent = float(gaps.tail(3).median()) if len(gaps) >= 3 else np.nan
    last = d.max()
    since = (AS_OF - last).days
    rev = reg[reg["Customer_Id"] == cid]
    life_years = max(((last - d.min()).days + med if med == med else 30) / 365.25, 0.25)
    annual = rev["Net_Value_USD"].sum() / life_years
    if since > max(3 * med, 120):
        status = "Lapsed"
    elif since > 2 * med or (recent == recent and recent > 2 * med):
        status = "At risk"
    else:
        status = "Active"
    # plasticizer profile: share of DINP (B) in the customer's first vs last 12 months of DOTP/DINP volume
    ab = rev[rev["Material_Id"].isin(["30000101", "30000102"])]
    prof = "No plasticizer"
    b_first = b_last = np.nan
    if ab["Qty_kg"].sum() > 0:
        f = ab[ab["Order_Date"] <= ab["Order_Date"].min() + pd.Timedelta(days=365)]
        l_ = ab[ab["Order_Date"] >= ab["Order_Date"].max() - pd.Timedelta(days=365)]
        b_first = f.loc[f["Material_Id"] == "30000102", "Qty_kg"].sum() / f["Qty_kg"].sum()
        b_last = l_.loc[l_["Material_Id"] == "30000102", "Qty_kg"].sum() / l_["Qty_kg"].sum()
        if b_first <= 0.35 and b_last >= 0.65:
            prof = "Switched A to B"
        elif b_last <= 0.2 and b_first <= 0.2:
            prof = "Loyal to A"
        elif b_last >= 0.8 and b_first >= 0.8:
            prof = "Loyal to B"
        else:
            prof = "Mixed"
    health.append(dict(Customer_Id=cid, First_Order_Date=d.min().date(), Last_Order_Date=last.date(), Orders=len(d),
                       Median_Reorder_Gap_days=med, Recent_Reorder_Gap_days=recent, Days_Since_Last_Order=since,
                       Overdue_Ratio=round(since / med, 2) if med == med and med > 0 else np.nan,
                       Status=status, Annual_Revenue_USD=round(annual, 2),
                       Revenue_at_Risk_USD=round(annual, 2) if status == "At risk" else 0.0,
                       Lapsed_In_Last_12m=bool(status == "Lapsed" and (AS_OF - last).days <= 365 + med),
                       Lost_Revenue_USD=round(annual, 2) if status == "Lapsed" else 0.0,
                       Plasticizer_Profile=prof, B_Share_First_12m=round(b_first, 3) if b_first == b_first else np.nan,
                       B_Share_Last_12m=round(b_last, 3) if b_last == b_last else np.nan))
fact_health = pd.DataFrame(health)
fact_health["Call_First"] = fact_health["Status"].eq("At risk") | fact_health["Lapsed_In_Last_12m"]
fact_health["Revenue_Exposure_USD"] = (fact_health["Revenue_at_Risk_USD"]
                                       + np.where(fact_health["Lapsed_In_Last_12m"], fact_health["Lost_Revenue_USD"], 0)).round(2)
dim_cust = dim_cust.merge(fact_health[["Customer_Id", "Status", "Plasticizer_Profile"]]
                          .rename(columns={"Status": "Health_Status"}), on="Customer_Id", how="left")
dq("Derived: Customer health", "Churn status is not stored in SAP", "-", len(fact_health),
   "Lapsed = no order for 3x the customer's usual reorder gap (min 120 days) as of 2026-09-30; At risk = more than 2x, "
   "or last 3 gaps more than 2x the usual; spot trader and returns excluded. Annual revenue = net revenue / active years; "
   "Revenue_at_Risk_USD for At risk only, Lost_Revenue_USD for Lapsed; Lapsed_In_Last_12m = last order within a year plus one usual gap")

# ------------------------------------------------------------------ dates
dim_date = pd.DataFrame({"Date": pd.date_range("2022-01-01", "2026-12-31")})
dim_date["Year"] = dim_date["Date"].dt.year
dim_date["Quarter"] = "Q" + dim_date["Date"].dt.quarter.astype(str)
dim_date["Month_Start"] = dim_date["Date"].dt.to_period("M").dt.to_timestamp().dt.date
dim_date["Month_Name"] = dim_date["Date"].dt.strftime("%b")
dim_date["Month_No"] = dim_date["Date"].dt.month
dim_date["Year_Month"] = dim_date["Date"].dt.strftime("%Y-%m")
dim_date["Year_Quarter"] = dim_date["Year"].astype(str) + " " + dim_date["Quarter"]
dim_date["Date"] = dim_date["Date"].dt.date

# ------------------------------------------------------------------ write
tables = {"Dim_Material": dim_mat, "Dim_Customer": dim_cust, "Dim_Sales_Rep": reps, "Dim_Supplier": dim_sup,
          "Dim_Plant": dim_plant, "Dim_Date": dim_date, "Fact_Sales": fact_sales, "Fact_Purchases": fact_po,
          "Fact_Production": fact_prod, "Fact_Stock": fact_stock, "Fact_BOM": fact_bom, "Fact_Std_Cost": fact_std,
          "Fact_Make_vs_Buy": fact_mvb, "Map_Make_vs_Buy": pairs, "Fact_Customer_Health": fact_health,
          "Map_Customer_Duplicates": map_dup, "Ref_PPI": ref_ppi}
for n, t in tables.items():
    t.to_csv(OUT / f"{n}.csv", index=False)
pd.DataFrame(log).to_csv(OUT / "DQ_Log.csv", index=False)
for n, t in tables.items():
    print(f"{n:24s} {len(t):>7,} rows")
print("DQ log entries", len(log))

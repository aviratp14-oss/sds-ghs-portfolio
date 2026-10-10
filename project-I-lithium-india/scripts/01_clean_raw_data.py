"""Project I cleaning: lithium demand in India.

Reads the raw files in raw/ and writes tidy tables to clean/.
The same rules are built as formulas in excel/Project_I_Data_Cleaning.xlsx
(see build_excel_cleaning.py); this script is the cross-check.

Run: python3 scripts/01_clean_raw_data.py
"""
import csv
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
CLEAN.mkdir(exist_ok=True)

# Lithium chemistry constants
LI_TO_LCE = 5.323          # t Li2CO3 per t Li
LIOH_H2O_TO_LCE = 0.880    # t LCE per t LiOH.H2O
TRADE_LCE_FACTOR = {"283691": 1.0, "282520": LIOH_H2O_TO_LCE}
UNIT_VALUE_FLOOR = 3.0     # USD/kg; below this a lithium chemical quantity is not credible

dq = []  # data quality log


def log(table, rule, rows, action, note=""):
    dq.append({"Table": table, "Rule": rule, "Rows_Affected": rows,
               "Action": action, "Note": note})


def num(text):
    """Parse numbers like '1,964,831', '20,37,831', '~29', '>25 lakh', 'almost 10'."""
    t = str(text).strip().lower()
    mult = 1.0
    if "lakh" in t:
        mult = 1e5
    t = re.sub(r"(almost|over|about|lakh|~|>|<)", "", t).replace(",", "").strip()
    return float(t) * mult


def write(name, rows, cols=None):
    cols = cols or list(rows[0].keys())
    with open(CLEAN / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


# ---------------------------------------------------------------- 1. Trade
raw_trade = list(csv.DictReader(open(RAW / "wits_india_imports_lithium_chemicals_2018_2024.csv")))
trade = []
for r in raw_trade:
    value_usd = num(r["Trade_Value_USD_Thousand"]) * 1000
    qty_kg = num(r["Quantity"])
    trade.append({
        "Year": int(r["Year"]), "HS6": r["HS6"], "Product": r["Product"],
        "Partner": r["Partner"], "Is_World_Row": r["Partner"] == "World",
        "Value_USD": round(value_usd, 2), "Qty_Reported_kg": qty_kg,
        "Unit_Value_USD_per_kg": round(value_usd / qty_kg, 4) if qty_kg else None,
    })

partners = [t for t in trade if not t["Is_World_Row"]]
flag_n = 0
self_import = 0
for t in partners:
    t["Flag"] = ""
    if t["Partner"] == "India":
        t["Flag"] = "Re-import (India as partner)"
        self_import += 1
    elif t["Unit_Value_USD_per_kg"] < UNIT_VALUE_FLOOR:
        t["Flag"] = "Unit value below floor"
        flag_n += 1

# clean unit value per year x HS from unflagged rows
ref_uv = {}
for key in {(t["Year"], t["HS6"]) for t in partners}:
    ok = [t for t in partners if (t["Year"], t["HS6"]) == key and not t["Flag"]]
    ref_uv[key] = sum(t["Value_USD"] for t in ok) / sum(t["Qty_Reported_kg"] for t in ok)

for t in partners:
    if t["Flag"] == "Unit value below floor":
        t["Qty_Clean_kg"] = round(t["Value_USD"] / ref_uv[(t["Year"], t["HS6"])], 1)
    else:
        t["Qty_Clean_kg"] = t["Qty_Reported_kg"]
    t["Qty_Clean_t_LCE"] = round(t["Qty_Clean_kg"] / 1000 * TRADE_LCE_FACTOR[t["HS6"]], 3)
    t["Ref_Unit_Value_USD_per_kg"] = round(ref_uv[(t["Year"], t["HS6"])], 4)

log("Fact_Trade_Lithium_Chemicals", "Numbers stored as text with thousands separators", len(raw_trade),
    "Converted to numbers; value from USD thousand to USD")
log("Fact_Trade_Lithium_Chemicals", "World total rows mixed with partner rows",
    sum(t["Is_World_Row"] for t in trade), "Kept only for reconciliation; excluded from partner table")
log("Fact_Trade_Lithium_Chemicals", f"Unit value below {UNIT_VALUE_FLOOR} USD/kg", flag_n,
    "Quantity re-estimated as value / clean unit value of that year and HS code",
    "Ireland shows up every year at ~0.55 USD/kg (e.g. 600 t for USD 354k in 2023), far below any lithium carbonate price; most likely a different product booked under 283691")
log("Fact_Trade_Lithium_Chemicals", "India listed as its own partner (re-import)", self_import,
    "Kept in value, flagged")

# reconcile world rows vs partner sums
recon = []
for key in sorted({(t["Year"], t["HS6"]) for t in trade}):
    world = next(t for t in trade if t["Is_World_Row"] and (t["Year"], t["HS6"]) == key)
    ps = [t for t in partners if (t["Year"], t["HS6"]) == key]
    sum_q = sum(p["Qty_Reported_kg"] for p in ps)
    clean_q = sum(p["Qty_Clean_kg"] for p in ps)
    clean_v = sum(p["Value_USD"] for p in ps)
    top = max(ps, key=lambda p: p["Value_USD"])
    recon.append({
        "Year": key[0], "HS6": key[1], "Product": world["Product"],
        "World_Value_USD": world["Value_USD"], "Partner_Sum_Value_USD": round(clean_v, 2),
        "World_Qty_kg": world["Qty_Reported_kg"], "Partner_Sum_Qty_kg": sum_q,
        "Qty_Clean_kg": round(clean_q, 1),
        "Qty_Removed_by_Cleaning_kg": round(sum_q - clean_q, 1),
        "Qty_Clean_t_LCE": round(clean_q / 1000 * TRADE_LCE_FACTOR[key[1]], 3),
        "Clean_Unit_Value_USD_per_kg": round(clean_v / clean_q, 2),
        "Top_Partner": top["Partner"],
        "Top_Partner_Value_Share": round(top["Value_USD"] / clean_v, 4),
    })
gap = [r for r in recon if abs(r["World_Qty_kg"] - r["Partner_Sum_Qty_kg"]) > 5]
log("Summary_Trade_by_Year", "World row vs sum of partners", len(gap),
    "Checked; differences are rounding only" if not gap else "Investigate")

write("Fact_Trade_Lithium_Chemicals.csv", partners,
      ["Year", "HS6", "Product", "Partner", "Value_USD", "Qty_Reported_kg", "Unit_Value_USD_per_kg",
       "Flag", "Ref_Unit_Value_USD_per_kg", "Qty_Clean_kg", "Qty_Clean_t_LCE"])
write("Summary_Trade_by_Year.csv", recon)

# industrial baseline: average clean LCE of 2022-2024
def avg_lce(hs):
    rows = [r["Qty_Clean_t_LCE"] for r in recon if r["HS6"] == hs and r["Year"] in (2022, 2023, 2024)]
    return sum(rows) / len(rows)

carb_lce, hyd_lce = avg_lce("283691"), avg_lce("282520")

# ---------------------------------------------------------------- 2. EV sales reported
SEG_MAP = {
    "total evs": "Total", "total ev": "Total",
    "electric two-wheelers (e2w)": "2W", "e-2w (high-speed)": "2W", "e2w": "2W", "electric 2w": "2W",
    "electric two-wheelers": "2W", "e-2w": "2W",
    "electric three-wheelers (e3w)": "3W", "electric three-wheelers": "3W",
    "e-rickshaw": "3W_L3", "e-cart": "3W_L3",
    "e-3w l5m": "3W_L5", "e-3w l5n": "3W_L5", "e3w passenger": "3W_Passenger",
    "electric passenger vehicles (cars, suvs, mpvs)": "4W", "electric passenger vehicles": "4W",
    "e-4w": "4W", "cars (4w)": "4W", "electric four-wheelers": "4W", "private cars": "4W",
    "electric commercial vehicles (buses, heavy and light goods)": "CV",
    "electric buses": "Bus", "buses": "Bus", "electric trucks": "Truck",
    "two- and three-wheelers": "2W_3W", "commercial cars": "4W_Commercial",
    "all vehicles": "All_Vehicles", "battery demand": "Battery", "ev battery demand": "Battery",
}
UNIT_MAP = {"units": "Units", "million": "Units", "% of ev sales": "Share_of_EV_Sales",
            "% penetration": "EV_Penetration", "% yoy growth": "YoY_Growth", "gwh": "GWh",
            "% of gwh": "Share_of_EV_GWh", "% of sales": "Target_Share_of_Sales",
            "% of e-rickshaw market": "Share_LiIon_in_L3", "years": "Years"}


def period(p):
    p = p.strip().upper().replace(" ", "")
    m = re.match(r"FY(\d{4})-(\d{2})$", p)
    if m:
        return "FY" + m.group(1)[:2] + m.group(2)
    if p.startswith("FY") or p.startswith("CY"):
        return p
    if "2030" in p:
        return "Target2030"
    return p


ev_raw = list(csv.DictReader(open(RAW / "ev_sales_reported.csv")))
ev = []
unmapped = 0
for r in ev_raw:
    seg_key = r["Segment_As_Reported"].strip().lower()
    std_seg = SEG_MAP.get(seg_key)
    if std_seg is None:
        if "battery share" in seg_key:
            std_seg = seg_key.split(" battery share")[0].title().replace("Four-Wheelers", "4W") \
                .replace("Three-Wheelers", "3W").replace("Two-Wheelers", "2W").replace("Buses", "Bus")
        elif "li-ion share" in seg_key:
            std_seg = "3W_L3"
        elif "battery life" in seg_key:
            std_seg = "3W_L3"
        else:
            std_seg = "Unmapped"
            unmapped += 1
    unit = UNIT_MAP.get(r["Unit_As_Reported"].strip().lower(), "Other")
    val = num(r["Value_As_Reported"])
    if r["Unit_As_Reported"].strip().lower() == "million":
        val *= 1e6
    ev.append({"Source_ID": r["Source_ID"], "Period": period(r["Period_As_Reported"]),
               "Std_Segment": std_seg, "Measure": unit, "Value": val,
               "Segment_As_Reported": r["Segment_As_Reported"],
               "Value_As_Reported": r["Value_As_Reported"]})
log("Fact_EV_Sales_Reported", "36 different segment labels across 7 sources", len(ev_raw),
    "Mapped to 2W / 3W_L3 / 3W_L5 / 4W / Bus / Truck / CV / Total via Map_Segment", f"{unmapped} unmapped")
log("Fact_EV_Sales_Reported", "Indian digit grouping (20,37,831) and words (lakh, ~, >, almost)",
    sum(1 for r in ev_raw if re.search(r"lakh|~|>|almost|\d,\d\d,\d{3}", r["Value_As_Reported"])),
    "Parsed to plain numbers")
log("Fact_EV_Sales_Reported", "Period labels mixed (FY2025, FY 2024-25, FY2025-26, CY2025)", len(ev_raw),
    "Standardised to FYyyyy (year the fiscal year ends) or CYyyyy")
log("Fact_EV_Sales_Reported", "Sources disagree on FY2025 total EV sales (1,964,831 vs 2,037,831)", 2,
    "Kept both; Vahan retail (S07) used for history, IESA CY2025 (S10) for the base year",
    "EVreporter counts e-carts and some low-speed models; gap is 3.7%")
write("Fact_EV_Sales_Reported.csv", ev)

# ---------------------------------------------------------------- 3. Base year 2025
cy_total = next(e["Value"] for e in ev if e["Period"] == "CY2025" and e["Std_Segment"] == "Total" and e["Measure"] == "Units")
share = {e["Std_Segment"]: e["Value"] / 100 for e in ev
         if e["Period"] == "CY2025" and e["Measure"] == "Share_of_EV_Sales"}
L3_SHARE_OF_3W = 0.75   # A00: FY2025 L3 = (474,503 + 65,060) / 699,062 = 77%; L5 growing faster
units_3w = cy_total * share["3W"]
base = [
    ("EV_2W", cy_total * share["2W"], 0.078),
    ("EV_3W_L5", units_3w * (1 - L3_SHARE_OF_3W), 0.25),
    ("EV_3W_L3", units_3w * L3_SHARE_OF_3W, 1.0),
    ("EV_4W", cy_total * share["4W"], 0.045),
    ("EV_Bus", cy_total * share["Bus"], 0.052),
    ("EV_Truck", cy_total * share["Truck"], 0.011),
]
base_rows = []
for sub, units, pen in base:
    base_rows.append({"Sub_Sector": sub, "EV_Units_2025": round(units),
                      "EV_Share_2025": pen, "Market_Units_2025": round(units / pen, -3)})
log("Ref_Base_Year_2025", "No single source gives CY2025 units by segment", 6,
    "Units = IESA CY2025 total (2.6m) x IESA segment shares; market = EV units / penetration",
    "Penetration from EVreporter FY2025 (2W 6.2%, 4W 2.7%, L5 ~22%) rolled forward one year")
write("Ref_Base_Year_2025.csv", base_rows)

# ---------------------------------------------------------------- 4. Chemistry intensity
M = {"Li": 6.941, "Fe": 55.845, "P": 30.974, "O": 15.999, "Ni": 58.693, "Mn": 54.938, "Co": 58.933}
chem = [
    # name, formula mass, practical capacity mAh/g, nominal V
    ("LFP", M["Li"] + M["Fe"] + M["P"] + 4 * M["O"], 160, 3.2),
    ("NMC811", M["Li"] + 0.8 * M["Ni"] + 0.1 * M["Mn"] + 0.1 * M["Co"] + 2 * M["O"], 195, 3.7),
    ("LCO", M["Li"] + M["Co"] + 2 * M["O"], 165, 3.85),
]
ELECTROLYTE_KG_LCE_PER_KWH = 0.012  # LiPF6 salt, A00 (about 1.2 M LiPF6 at ~1.5 g electrolyte per Ah)
CELL_YIELD = 0.92                   # A00: share of cathode Li that ends up in sold cells
chem_rows = []
for name, mass, cap, v in chem:
    wh_per_g = cap * v / 1000
    kg_cam_per_kwh = 1 / wh_per_g
    li_frac = M["Li"] / mass
    kg_li = kg_cam_per_kwh * li_frac
    kg_lce = (kg_li * LI_TO_LCE + ELECTROLYTE_KG_LCE_PER_KWH) / CELL_YIELD
    chem_rows.append({"Chemistry": name, "Formula_Mass_g_mol": round(mass, 3),
                      "Practical_Capacity_mAh_g": cap, "Nominal_Voltage_V": v,
                      "kg_CAM_per_kWh": round(kg_cam_per_kwh, 4), "Li_Mass_Fraction": round(li_frac, 5),
                      "kg_Li_per_kWh_Cathode": round(kg_li, 4),
                      "kg_LCE_per_kWh_Cell": round(kg_lce, 4)})
chem_rows.append({"Chemistry": "Sodium-ion", "Formula_Mass_g_mol": "", "Practical_Capacity_mAh_g": "",
                  "Nominal_Voltage_V": "", "kg_CAM_per_kWh": "", "Li_Mass_Fraction": 0,
                  "kg_Li_per_kWh_Cathode": 0, "kg_LCE_per_kWh_Cell": 0})
write("Ref_Chemistry_Intensity.csv", chem_rows)

# ---------------------------------------------------------------- 5. Industrial baseline
ind_rows = [
    {"Sub_Sector": "IND_Grease", "Basis": "Lithium hydroxide imports (HS 282520), avg 2022-24, 90% to grease",
     "t_LCE_2025": round(hyd_lce * 0.90, 1)},
    {"Sub_Sector": "IND_GlassCeramics", "Basis": "Lithium carbonate imports (HS 283691), avg 2022-24, 50% to glass and ceramics",
     "t_LCE_2025": round(carb_lce * 0.50, 1)},
    {"Sub_Sector": "IND_Pharma_Other", "Basis": "Rest of carbonate and hydroxide imports (pharma, air treatment, mould flux, other)",
     "t_LCE_2025": round(carb_lce * 0.50 + hyd_lce * 0.10, 1)},
]
# grease cross-check: ~86 kt grease (2020) x 85% lithium-based x ~1.6% LiOH.H2O
grease_check = 190e6 * 0.4536 / 1000 * 0.85 * 0.016 * LIOH_H2O_TO_LCE
log("Ref_Industry_Baseline", "Cross-check of grease share", 1,
    f"Grease survey implies ~{grease_check:,.0f} t LCE vs {hyd_lce*0.9:,.0f} t LCE from hydroxide imports",
    "190m lb grease (NLGI 2020) x 85% lithium soap x ~1.6% LiOH.H2O; survey covers 16 of 31 makers, so actual is higher")
write("Ref_Industry_Baseline.csv", ind_rows)

# ---------------------------------------------------------------- 6. Exploration pipeline and value chain
reasi_li = 5.9e6 * 583e-6
explo = [
    {"Asset": "Salal-Haimana, Reasi (J&K)", "Type": "Domestic block", "Deposit_Style": "Lithium in bauxite / clay",
     "Stage": "G3 inferred", "Ore_Mt": 5.9, "Grade_ppm_Li": 583, "Contained_t_Li": round(reasi_li),
     "Contained_t_LCE": round(reasi_li * LI_TO_LCE), "Status_2026": "Auction called off twice; no qualified bids",
     "Source_ID": "S02; S21"},
    {"Asset": "Katghora (Chhattisgarh)", "Type": "Domestic block", "Deposit_Style": "Hard rock (lithium and REE)",
     "Stage": "Composite licence (exploration then mining)", "Ore_Mt": "", "Grade_ppm_Li": "",
     "Contained_t_Li": "", "Contained_t_LCE": "", "Status_2026": "Awarded Jun 2024 to Maiki South Mining at 76.05% premium; resource not published",
     "Source_ID": "S20; S21"},
    {"Asset": "KABIL Catamarca (Argentina)", "Type": "Overseas equity", "Deposit_Style": "Brine",
     "Stage": "Exploration, 5 blocks, 15,703 ha", "Ore_Mt": "", "Grade_ppm_Li": "",
     "Contained_t_Li": "", "Contained_t_LCE": "", "Status_2026": "First production targeted Dec 2030 (not binding)",
     "Source_ID": "S19"},
    {"Asset": "Typical spodumene pegmatite (benchmark)", "Type": "Benchmark", "Deposit_Style": "Hard rock",
     "Stage": "Producing (Australia)", "Ore_Mt": "", "Grade_ppm_Li": 5800,
     "Contained_t_Li": "", "Contained_t_LCE": "", "Status_2026": "1.25% Li2O x 0.4645 = ~5,800 ppm Li",
     "Source_ID": "A00"},
    {"Asset": "Brine (benchmark range)", "Type": "Benchmark", "Deposit_Style": "Brine",
     "Stage": "Producing (Chile, Argentina)", "Ore_Mt": "", "Grade_ppm_Li": "200-2000",
     "Contained_t_Li": "", "Contained_t_LCE": "", "Status_2026": "", "Source_ID": "S03"},
]
write("Ref_Exploration_Pipeline.csv", explo)

chain = [
    ("1 Exploration", "Early", "G3 inferred resource at Reasi; one hard-rock block under composite licence", "S02; S20"),
    ("2 Mining", "None", "No operating lithium mine; auctions draw few bidders", "S21"),
    ("3 Beneficiation and processing", "R&D only", "CSIR-NML lab work; clay-hosted ore not proven commercially anywhere", "S05; S21"),
    ("4 Refining (carbonate, hydroxide)", "None operating", "One refinery MoU (Gujarat); ~2-3 kt LCE/yr of chemicals imported", "S05; S06"),
    ("5 Cathode active material", "Negligible", "China holds 98% of NMC and 48% of LFP cathode output", "S16"),
    ("6 Cell manufacturing", "Starting", "1.4 GWh commissioned under ACC PLI by Oct 2025; cell import dependence close to 100%", "S16"),
    ("7 Pack assembly and use", "Established", "Packs assembled in India for EVs, storage and electronics", "S16"),
    ("8 Recycling", "Scaling", "Rs 1,500 cr scheme targets 270 kt/yr recycling capacity by 2031", "S17; S18"),
]
write("Ref_Value_Chain.csv", [{"Stage": a, "India_Status": b, "Evidence": c, "Source_ID": d} for a, b, c, d in chain])

# sources
src = list(csv.DictReader(open(RAW / "source_register.csv")))
write("Ref_Sources.csv", src)
log("Ref_Sources", "Every number in the model carries a Source_ID; A00 marks my own assumption", len(src), "Register")

write("DQ_Log.csv", dq)
print(f"carbonate avg LCE {carb_lce:.1f} t, hydroxide avg LCE {hyd_lce:.1f} t, grease check {grease_check:.0f} t")

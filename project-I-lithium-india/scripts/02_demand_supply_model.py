"""Project I demand and supply-gap model: lithium in India, 2025-2040.

Every input lives in ASSUMPTIONS below (one row per parameter, with anchor values
for 2025, 2030, 2035 and 2040 and linear steps in between). The script:
  1. writes the assumption table to clean/Assumptions.csv (the Excel model reads the same table)
  2. runs 3 adoption scenarios x 6 policy-lever settings
  3. writes long tables for Power BI to clean/

Run after 01_clean_raw_data.py:  python3 scripts/02_demand_supply_model.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"

YEARS = list(range(2025, 2041))
HIST_YEARS = list(range(2013, 2025))
SCENARIOS = ["Low", "Base", "High"]
ANCHORS = [2025, 2030, 2035, 2040]

chem = {r["Chemistry"]: float(r["kg_LCE_per_kWh_Cell"]) for r in csv.DictReader(open(CLEAN / "Ref_Chemistry_Intensity.csv"))}
base = {r["Sub_Sector"]: r for r in csv.DictReader(open(CLEAN / "Ref_Base_Year_2025.csv"))}
ind = {r["Sub_Sector"]: float(r["t_LCE_2025"]) for r in csv.DictReader(open(CLEAN / "Ref_Industry_Baseline.csv"))}

EV = ["EV_2W", "EV_3W_L5", "EV_3W_L3", "EV_4W", "EV_Bus", "EV_Truck"]
ELEC = ["ELEC_Phone", "ELEC_PC", "ELEC_Tablet", "ELEC_Wearable", "ELEC_PowerBank", "ELEC_ExportAssembly"]
INDS = ["IND_Grease", "IND_GlassCeramics", "IND_Pharma_Other"]
SUBS = EV + ["BESS"] + ELEC + ["DEF_Defence"] + INDS
NA_ION_ELIGIBLE = ["EV_2W", "EV_3W_L5", "EV_3W_L3", "BESS"]

SECTOR = {**{s: "EVs" for s in EV}, "BESS": "Grid storage", **{s: "Electronics" for s in ELEC},
          "DEF_Defence": "Defence and aerospace", **{s: "Industry" for s in INDS}}
LABEL = {"EV_2W": "Electric two-wheelers", "EV_3W_L5": "Electric 3W (L5 autos and cargo)",
         "EV_3W_L3": "E-rickshaws and e-carts (L3)", "EV_4W": "Electric cars", "EV_Bus": "Electric buses",
         "EV_Truck": "Electric trucks and goods carriers", "BESS": "Grid battery storage",
         "ELEC_Phone": "Smartphones (domestic sales)", "ELEC_PC": "Laptops and PCs", "ELEC_Tablet": "Tablets",
         "ELEC_Wearable": "Wearables", "ELEC_PowerBank": "Power banks",
         "ELEC_ExportAssembly": "Phones assembled for export", "DEF_Defence": "Defence and aerospace",
         "IND_Grease": "Lubricating greases", "IND_GlassCeramics": "Glass and ceramics",
         "IND_Pharma_Other": "Pharma, air treatment and other"}
LIFE = {"EV_2W": 6, "EV_3W_L5": 6, "EV_3W_L3": 3, "EV_4W": 10, "EV_Bus": 8, "EV_Truck": 8, "BESS": 12,
        "ELEC_Phone": 3, "ELEC_PC": 5, "ELEC_Tablet": 4, "ELEC_Wearable": 2, "ELEC_PowerBank": 3}
ELEC_CHEM = {"ELEC_Phone": "LCO", "ELEC_PC": "NMC811", "ELEC_Tablet": "LCO", "ELEC_Wearable": "LCO",
             "ELEC_PowerBank": "NMC811", "ELEC_ExportAssembly": "LCO"}

# ---------------------------------------------------------------- assumptions
# (Param, Sub_Sector, Scenario, [2025, 2030, 2035, 2040], Unit, Source_ID, Note)
A = []


def add(param, sub, scen, vals, unit, src, note=""):
    A.append({"Param": param, "Sub_Sector": sub, "Scenario": scen, "Y2025": vals[0], "Y2030": vals[1],
              "Y2035": vals[2], "Y2040": vals[3], "Unit": unit, "Source_ID": src, "Note": note})


market_growth = {"EV_2W": 0.04, "EV_3W_L5": 0.03, "EV_3W_L3": 0.02, "EV_4W": 0.05, "EV_Bus": 0.04, "EV_Truck": 0.05}
for s in EV:
    m = float(base[s]["Market_Units_2025"])
    add("Market_Units", s, "All", [m, m * (1 + market_growth[s]) ** 5, m * (1 + market_growth[s]) ** 10,
                                   m * (1 + market_growth[s]) ** 15],
        "vehicles/yr", "S07; S08; S10; A00", f"2025 from Ref_Base_Year_2025; grows {market_growth[s]:.0%}/yr")

ev_share = {
    "EV_2W": {"Low": [.15, .25, .40], "Base": [.30, .55, .75], "High": [.55, .80, .95]},
    "EV_3W_L5": {"Low": [.40, .55, .70], "Base": [.55, .75, .90], "High": [.75, .90, 1.0]},
    "EV_3W_L3": {"Low": [1, 1, 1], "Base": [1, 1, 1], "High": [1, 1, 1]},
    "EV_4W": {"Low": [.08, .14, .25], "Base": [.13, .28, .45], "High": [.30, .55, .80]},
    "EV_Bus": {"Low": [.12, .25, .40], "Base": [.25, .50, .75], "High": [.40, .70, .95]},
    "EV_Truck": {"Low": [.03, .07, .15], "Base": [.06, .15, .30], "High": [.12, .30, .55]},
}
for s, d in ev_share.items():
    for sc, v in d.items():
        add("EV_Share", s, sc, [float(base[s]["EV_Share_2025"])] + v, "share of sales", "S08; S25; A00",
            "High tracks the NITI Aayog 2030 ambition (80% 2W/3W, 30% private cars, 40% buses)")
for sc, v in {"Low": [.40, .55, .70], "Base": [.60, .85, 1.0], "High": [.85, 1.0, 1.0]}.items():
    add("LiIon_Share", "EV_3W_L3", sc, [.25] + v, "share of L3 sales", "S27; A00",
        "~10% of e-rickshaws were Li-ion in FY2023; rest lead-acid")
for s in EV:
    if s != "EV_3W_L3":
        add("LiIon_Share", s, "All", [1, 1, 1, 1], "share", "A00")

kwh = {"EV_2W": [2.8, 3.2, 3.5, 3.8], "EV_3W_L5": [8, 10, 11, 12], "EV_3W_L3": [5, 6, 6.5, 7],
       "EV_4W": [38, 42, 45, 48], "EV_Bus": [280, 320, 350, 380], "EV_Truck": [40, 60, 90, 120]}
for s, v in kwh.items():
    add("kWh_per_Unit", s, "All", v, "kWh", "S10; A00",
        "2025 sizes calibrated so segment GWh shares match IESA CY2025 (4W 40%, 3W 27%, 2W 23%, bus 7.8%)")
lfp = {"EV_2W": [.6, .7, .75, .8], "EV_3W_L5": [.9, .95, .95, .95], "EV_3W_L3": [1, 1, 1, 1],
       "EV_4W": [.45, .6, .65, .7], "EV_Bus": [.9, .95, .95, .95], "EV_Truck": [.8, .85, .9, .9],
       "BESS": [1, 1, 1, 1]}
for s, v in lfp.items():
    add("LFP_Share", s, "All", v, "share of Li-ion kWh (rest NMC)", "A00")
for s in NA_ION_ELIGIBLE:
    add("NaIon_Share", s, "All", [0, .03, .08, .12], "share of kWh", "A00",
        "Sodium-ion enters low-range 2W/3W and storage first")

for sc, v in {"Low": [4, 60, 200, 320], "Base": [4, 110, 300, 500], "High": [4, 180, 420, 750]}.items():
    add("BESS_Cumulative_GWh", "BESS", sc, v, "GWh installed", "S11; S12; A00",
        "CEA NEP: 193-335 GWh by FY2032 (base 236); 4.7 GWh operating and 35 GWh awarded by May 2026")

elec_units = {"ELEC_Phone": (152e6, "S13"), "ELEC_PC": (15.9e6, "S14"), "ELEC_Tablet": (4.5e6, "A00"),
              "ELEC_Wearable": (114.2e6, "S15"), "ELEC_PowerBank": (25e6, "A00"),
              "ELEC_ExportAssembly": (90e6, "S28; A00")}
elec_growth = {"ELEC_Phone": (-.01, .01, .03), "ELEC_PC": (.02, .04, .06), "ELEC_Tablet": (0, .03, .05),
               "ELEC_Wearable": (-.02, .01, .04), "ELEC_PowerBank": (0, .02, .04),
               "ELEC_ExportAssembly": (.03, .07, .10)}
for s, (u, src) in elec_units.items():
    for sc, g in zip(SCENARIOS, elec_growth[s]):
        add("Units", s, sc, [u, u * (1 + g) ** 5, u * (1 + g) ** 10, u * (1 + g) ** 15], "devices/yr", src,
            f"grows {g:.0%}/yr" + ("; export phones = ICEA Rs 2 lakh cr / ~Rs 22k per phone" if s == "ELEC_ExportAssembly" else ""))
wh = {"ELEC_Phone": [19.4, 21, 23, 24], "ELEC_PC": [50, 52, 55, 55], "ELEC_Tablet": [28, 30, 32, 32],
      "ELEC_Wearable": [0.75, 0.8, 0.9, 0.9], "ELEC_PowerBank": [37, 40, 40, 40],
      "ELEC_ExportAssembly": [19.4, 21, 23, 24]}
for s, v in wh.items():
    add("Wh_per_Unit", s, "All", v, "Wh", "A00", "5,000 mAh x 3.87 V = 19.4 Wh for a phone")

for sc, g in zip(SCENARIOS, (.05, .08, .12)):
    add("t_LCE", "DEF_Defence", sc, [150, 150 * (1 + g) ** 5, 150 * (1 + g) ** 10, 150 * (1 + g) ** 15], "t LCE",
        "A00", f"No public data; band for drones, missiles, submarines, space cells and Al-Li alloy; grows {g:.0%}/yr")
for s in INDS:
    for sc, g in zip(SCENARIOS, (.03, .05, .07)):
        add("t_LCE", s, sc, [ind[s], ind[s] * (1 + g) ** 5, ind[s] * (1 + g) ** 10, ind[s] * (1 + g) ** 15],
            "t LCE", "S06; S26", f"2025 from cleaned trade data; grows {g:.0%}/yr")

# supply side
for sc, (start, v) in {"Low": (2099, [0, 0, 0, 0]), "Base": (2039, [0, 0, 0, 600]),
                       "High": (2033, [0, 0, 800, 2500])}.items():
    add("Domestic_Mining_t_LCE", "Supply", sc, v, "t LCE", "S02; S20; S24; A00",
        f"start {start if start < 2099 else 'none'}; Reasi holds ~18,300 t LCE in total; IEA lead time >16 yrs")
    add("Domestic_Mining_Start", "Supply", sc, [start] * 4, "year", "S24; A00")
for sc, (start, v) in {"Low": (2099, [0, 0, 0, 0]), "Base": (2032, [0, 0, 6000, 12000]),
                       "High": (2031, [0, 0, 15000, 30000])}.items():
    add("Overseas_Equity_t_LCE", "Supply", sc, v, "t LCE", "S19; A00", "KABIL Catamarca first output targeted Dec 2030")
    add("Overseas_Equity_Start", "Supply", sc, [start] * 4, "year", "S19; A00")
for sc, v in {"Low": [.2, .45, .6, .7], "Base": [.3, .7, .85, .9], "High": [.4, .85, .95, .95]}.items():
    add("Collection_Rate", "EV_BESS", sc, v, "share of retired", "S17; A00", "BWMR: 70% EV collection by 2027-28")
for sc, v in {"Low": [.1, .2, .35, .45], "Base": [.15, .35, .55, .7], "High": [.2, .5, .75, .85]}.items():
    add("Collection_Rate", "Electronics", sc, v, "share of retired", "A00", "informal sector handles most e-waste today")
for sc, v in {"Low": [.7, .8, .85, .85], "Base": [.8, .9, .92, .92], "High": [.85, .95, .95, .95]}.items():
    add("Li_Recovery", "Recycling", sc, v, "share of Li recovered", "S17; A00", "hydrometallurgy")
add("Global_Supply_t_LCE", "Supply", "All", [1544e3, 2600e3, 3400e3, 4300e3], "t LCE", "S01; S22; S23; A00",
    "2025 = 290 kt Li (USGS); IEA sees demand x3 to 2040 with a narrowing gap")
add("India_Accessible_Share", "Supply", "All", [.03, .03, .03, .03], "share of global supply", "A00",
    "stress-test lever; India is ~3.5% of world GDP and ~1% of lithium use today")
# BWMR recycled-content mandate (S17): 5% in 2027-28 rising to 20% by 2030-31, read as calendar years
MANDATE = {2027: .05, 2028: .10, 2029: .15}


def mandate(y):
    return 0 if y < 2027 else MANDATE.get(y, .20)


def fast_track(y):
    """Exploration fast-track: domestic mining from 2032, 1.5 kt LCE by 2035, 4 kt by 2040."""
    if y < 2032:
        return 0
    if y <= 2035:
        return 1500 * (y - 2031) / 4
    return 1500 + (4000 - 1500) * (y - 2035) / 5

LEVERS = ["None", "Recycling push", "Overseas assets", "Sodium-ion push", "Exploration fast-track", "All four levers"]
LEVER_NOTE = {
    "Recycling push": "Collection 90% (EV/BESS) and 70% (electronics) by 2030; Li recovery 95%",
    "Overseas assets": "Extra 10 / 30 / 50 kt LCE equity supply in 2030 / 2035 / 2040 (from 2031)",
    "Sodium-ion push": "Sodium-ion share in 2W, 3W and storage +15 / +30 / +40 points by 2030 / 2035 / 2040",
    "Exploration fast-track": "Domestic mining from 2032: 1.5 kt LCE by 2035, 4 kt by 2040",
}

# write assumptions
with open(CLEAN / "Assumptions.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(A[0].keys()))
    w.writeheader()
    w.writerows(A)


def interp(vals, y):
    for i in range(3):
        a, b = ANCHORS[i], ANCHORS[i + 1]
        if y <= b:
            return vals[i] + (vals[i + 1] - vals[i]) * (y - a) / (b - a)
    return vals[3]



def bess_new(scen, y):
    """New storage each year. Additions ramp in a straight line inside each five-year block so the
    cumulative total still hits the anchor years, without the jump a straight-line cumulative path gives."""
    cum = lambda t: get("BESS_Cumulative_GWh", "BESS", scen, t)
    a = cum(2025) - sum(HIST_BESS_ADD)
    if y == 2025:
        return a
    for y0 in (2025, 2030, 2035):
        k = (cum(y0 + 5) - cum(y0) - 5 * a) / 15
        if y <= y0 + 5:
            return max(0, a + k * (y - y0))
        a = a + 5 * k
    return a

def get(param, sub, scen, y):
    for r in A:
        if r["Param"] == param and r["Sub_Sector"] == sub and r["Scenario"] in (scen, "All"):
            return interp([r["Y2025"], r["Y2030"], r["Y2035"], r["Y2040"]], y)
    raise KeyError((param, sub, scen))


# history for recycling (A00 approximations, rounded from S07/S08 FY totals)
HIST_UNITS = {
    "EV_2W": [5e3, 10e3, 20e3, 25e3, 30e3, 50e3, 100e3, 100e3, 230e3, 630e3, 860e3, 1140e3],
    "EV_3W_L5": [0, 0, 0, 0, 0, 1e3, 2e3, 3e3, 6e3, 20e3, 60e3, 140e3],
    "EV_3W_L3": [50e3, 80e3, 120e3, 180e3, 250e3, 300e3, 350e3, 250e3, 300e3, 380e3, 480e3, 520e3],
    "EV_4W": [0, 0, 1e3, 1e3, 1.5e3, 2e3, 2e3, 4e3, 14e3, 38e3, 82e3, 100e3],
    "EV_Bus": [0, 0, 0, 0, 0, 300, 600, 600, 1.2e3, 2e3, 3.5e3, 4e3],
    "EV_Truck": [0] * 9 + [1e3, 3e3, 6e3],
}
HIST_L3_LI = [0.02] * 6 + [0.05] * 3 + [0.1, 0.1, 0.15]
HIST_BESS_ADD = [0.02] * 8 + [0.05, 0.1, 0.3, 0.8]


def run(scen, lever):
    on = lambda name: lever in (name, "All four levers")
    out_demand = {}  # (sub, year) -> dict
    na_extra = lambda y: interp([0, .15, .30, .40], y) if on("Sodium-ion push") else 0

    def ev_intensity(s, y):
        if s in base and y < 2025:
            y = 2025
        l = get("LFP_Share", s, scen, y)
        na = min(0.8, get("NaIon_Share", s, scen, y) + na_extra(y)) if s in NA_ION_ELIGIBLE else 0
        return (1 - na) * (l * chem["LFP"] + (1 - l) * chem["NMC811"])

    # history
    for i, y in enumerate(HIST_YEARS):
        for s in EV:
            li = HIST_L3_LI[i] if s == "EV_3W_L3" else 1
            gwh = HIST_UNITS[s][i] * li * get("kWh_per_Unit", s, scen, 2025) * 0.9 / 1e6
            out_demand[(s, y)] = {"t": gwh * ev_intensity(s, 2025) * 1000}
        out_demand[("BESS", y)] = {"t": HIST_BESS_ADD[i] * chem["LFP"] * 1000}
        for s in ELEC:
            gwh = get("Units", s, scen, 2025) * get("Wh_per_Unit", s, scen, 2025) / 1e9
            out_demand[(s, y)] = {"t": gwh * chem[ELEC_CHEM[s]] * 1000}

    bess_add = {y: HIST_BESS_ADD[i] for i, y in enumerate(HIST_YEARS)}
    for y in YEARS:
        for s in EV:
            units = get("Market_Units", s, scen, y) * get("EV_Share", s, scen, y)
            gwh = units * get("LiIon_Share", s, scen, y) * get("kWh_per_Unit", s, scen, y) / 1e6
            k = ev_intensity(s, y)
            out_demand[(s, y)] = {"units": units, "gwh": gwh, "k": k, "t": gwh * k * 1000}
        add_gwh = bess_new(scen, y) + bess_add.get(y - LIFE["BESS"], 0)
        bess_add[y] = add_gwh
        k = ev_intensity("BESS", y)
        out_demand[("BESS", y)] = {"units": None, "gwh": add_gwh, "k": k, "t": add_gwh * k * 1000}
        for s in ELEC:
            units = get("Units", s, scen, y)
            gwh = units * get("Wh_per_Unit", s, scen, y) / 1e9
            k = chem[ELEC_CHEM[s]]
            out_demand[(s, y)] = {"units": units, "gwh": gwh, "k": k, "t": gwh * k * 1000}
        for s in ["DEF_Defence"] + INDS:
            out_demand[(s, y)] = {"units": None, "gwh": None, "k": None, "t": get("t_LCE", s, scen, y)}

    balance = []
    for y in YEARS:
        dem = {s: out_demand[(s, y)]["t"] for s in SUBS}
        energy = sum(dem[s] for s in EV + ["BESS"])
        total = sum(dem.values())
        coll_ev = get("Collection_Rate", "EV_BESS", scen, y)
        coll_el = get("Collection_Rate", "Electronics", scen, y)
        rec = get("Li_Recovery", "Recycling", scen, y)
        if on("Recycling push"):  # lever lifts rates to at least these paths, never lowers them
            coll_ev = max(coll_ev, interp([get("Collection_Rate", "EV_BESS", scen, 2025), .9, .9, .9], y))
            coll_el = max(coll_el, interp([get("Collection_Rate", "Electronics", scen, 2025), .7, .7, .7], y))
            rec = max(rec, interp([get("Li_Recovery", "Recycling", scen, 2025), .95, .95, .95], y))
        recyc = 0
        for s, life in LIFE.items():
            src = out_demand.get((s, y - life), {"t": 0})["t"]
            recyc += src * (coll_el if s.startswith("ELEC") else coll_ev) * rec
        start = get("Domestic_Mining_Start", "Supply", scen, y)
        mining = get("Domestic_Mining_t_LCE", "Supply", scen, y) if y >= start else 0
        if on("Exploration fast-track"):
            mining = max(mining, fast_track(y))
        e_start = get("Overseas_Equity_Start", "Supply", scen, y)
        equity = get("Overseas_Equity_t_LCE", "Supply", scen, y) if y >= e_start else 0
        if on("Overseas assets") and y >= 2031:
            equity += interp([0, 10000, 30000, 50000], y)
        ceiling = get("Global_Supply_t_LCE", "Supply", scen, y) * get("India_Accessible_Share", "Supply", scen, y)
        net_import = max(0, total - recyc - mining)
        open_import = max(0, net_import - equity)
        available = recyc + mining + equity + ceiling
        non_energy = total - energy
        shortfall = max(0, total - available)
        coverage = min(1, max(0, available - non_energy) / energy) if energy else 1
        battery_dem = energy + sum(dem[s] for s in ELEC)
        balance.append({
            "Scenario": scen, "Lever": lever, "Year": y,
            "Demand_t_LCE": round(total, 1), "Energy_Demand_t_LCE": round(energy, 1),
            "NonEnergy_Demand_t_LCE": round(non_energy, 1),
            "Recycling_t_LCE": round(recyc, 1), "Domestic_Mining_t_LCE": round(mining, 1),
            "Overseas_Equity_t_LCE": round(equity, 1), "Import_Ceiling_t_LCE": round(ceiling, 1),
            "Global_Supply_t_LCE": round(get("Global_Supply_t_LCE", "Supply", scen, y), 1),
            "Net_Import_Need_t_LCE": round(net_import, 1), "Open_Market_Import_Need_t_LCE": round(open_import, 1),
            "Available_Supply_t_LCE": round(available, 1), "Shortfall_t_LCE": round(shortfall, 1),
            "Energy_Coverage_Ratio": round(coverage, 4),
            "Energy_Shortfall_t_LCE": round(energy * (1 - coverage), 1),
            "Import_Dependence": round(net_import / total, 4) if total else 0,
            "Domestic_Share": round((recyc + mining) / total, 4) if total else 0,
            "Recycled_Content_Share": round(recyc / battery_dem, 4) if battery_dem else 0,
            "Recycled_Content_Mandate": mandate(y),
            "India_Share_of_Global_Supply": round(total / get("Global_Supply_t_LCE", "Supply", scen, y), 4),
        })
    demand_rows = []
    for (s, y), d in out_demand.items():
        if y < 2025:
            continue
        demand_rows.append({
            "Scenario": scen, "Lever": lever, "Year": y, "Sub_Sector": s,
            "Units": round(d["units"]) if d.get("units") is not None else "",
            "GWh": round(d["gwh"], 4) if d.get("gwh") is not None else "",
            "kg_LCE_per_kWh": round(d["k"], 4) if d.get("k") is not None else "",
            "Demand_t_LCE": round(d["t"], 1)})
    return demand_rows, balance


all_demand, all_balance = [], []
for sc in SCENARIOS:
    for lv in LEVERS:
        d, b = run(sc, lv)
        all_demand += d
        all_balance += b


def write(name, rows):
    with open(CLEAN / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


write("Fact_Demand.csv", all_demand)
write("Fact_Balance.csv", all_balance)

# lever impact vs no lever
idx = {(b["Scenario"], b["Lever"], b["Year"]): b for b in all_balance}
impact = []
for (sc, lv, y), b in idx.items():
    if lv == "None":
        continue
    n = idx[(sc, "None", y)]
    impact.append({"Scenario": sc, "Lever": lv, "Year": y,
                   "Shortfall_Closed_t_LCE": round(n["Shortfall_t_LCE"] - b["Shortfall_t_LCE"], 1),
                   "Import_Need_Cut_t_LCE": round(n["Net_Import_Need_t_LCE"] - b["Net_Import_Need_t_LCE"], 1),
                   "Coverage_Gain_pts": round((b["Energy_Coverage_Ratio"] - n["Energy_Coverage_Ratio"]) * 100, 2)})
write("Fact_Lever_Impact.csv", impact)

# supply long table for stacked charts
supply = []
for b in all_balance:
    for src, col in [("Recycling", "Recycling_t_LCE"), ("Domestic mining", "Domestic_Mining_t_LCE"),
                     ("Overseas equity", "Overseas_Equity_t_LCE"), ("Import ceiling (open market)", "Import_Ceiling_t_LCE")]:
        supply.append({"Scenario": b["Scenario"], "Lever": b["Lever"], "Year": b["Year"], "Supply_Source": src,
                       "Supply_t_LCE": b[col]})
write("Fact_Supply.csv", supply)

# dimensions
write("Dim_Scenario.csv", [
    {"Scenario": "Low", "Sort": 1, "Description": "Slow EV uptake, storage below the CEA path, weak recycling, no new mines or equity"},
    {"Scenario": "Base", "Sort": 2, "Description": "Current trends extended; CEA storage path a little late; rules met on time; KABIL from 2032"},
    {"Scenario": "High", "Sort": 3, "Description": "NITI Aayog-style EV ambition, storage above the CEA path, strong recycling, faster mining and equity"}])
write("Dim_Lever.csv", [{"Lever": l, "Sort": i, "Description": LEVER_NOTE.get(l, "Scenario as defined" if l == "None" else "Recycling, overseas assets, sodium-ion and exploration together")}
                        for i, l in enumerate(LEVERS)])
write("Dim_Sector.csv", [{"Sub_Sector": s, "Label": LABEL[s], "Sector": SECTOR[s],
                          "Group": "Energy transition" if SECTOR[s] in ("EVs", "Grid storage") else "Non-energy",
                          "Sort": i} for i, s in enumerate(SUBS)])
write("Dim_Year.csv", [{"Year": y, "Is_Milestone": y in (2025, 2030, 2035, 2040)} for y in YEARS])

for sc in SCENARIOS:
    for y in (2025, 2030, 2035, 2040):
        b = idx[(sc, "None", y)]
        print(sc, y, f"demand {b['Demand_t_LCE']/1000:6.1f} kt  energy {b['Energy_Demand_t_LCE']/1000:6.1f}  "
              f"recyc {b['Recycling_t_LCE']/1000:5.1f}  ceiling {b['Import_Ceiling_t_LCE']/1000:6.1f}  "
              f"short {b['Shortfall_t_LCE']/1000:6.1f}  cover {b['Energy_Coverage_Ratio']:.2f}  "
              f"imp.dep {b['Import_Dependence']:.2f}  rc {b['Recycled_Content_Share']:.3f}")

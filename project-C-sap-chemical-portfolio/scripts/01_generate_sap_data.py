"""Project C - generate the simulated SAP S/4HANA export files.

Company: Gulfport Oxo Chemicals (fictional). Two plants:
  1010 Pasadena, TX     - oxo alcohols (n-butanal, 2-EH, butanols) and plasticizers (DOTP, DINP, DOA, TOTM)
  1020 Lake Charles, LA - acrylates, acetates, glycol ethers, plus traded goods

Scenarios built into the data:
  1. DOTP (Chemical A, priority) loses share to DINP (Chemical B, offset) - same end use (PVC plasticizer)
  2. Plant 1020 buys 2-EH (Chemical C) from outside under a second material number to make
     2-EH acrylate (Chemical D), while plant 1010 makes 2-EH and sits on surplus stock.
     Same pattern, smaller: n-butanol (1020 for butyl acrylate / butyl acetate) and PM (1010, cleaning solvent).
  3. Customer churn - customers lapse or slow down against their own reorder rhythm.

Real inputs: CAS numbers of real chemicals (check digits validated below) and the FRED producer
price index for basic organic chemicals (13_Ref_PPI_Basic_Organic_Chemicals_FRED.csv), used to move
prices month by month. Everything else is simulated. Seeded, so re-running gives the same files.

Raw files deliberately carry SAP-export mess (mixed date formats, CAS formatting, duplicate rows,
inconsistent country names, MT/LB units on some lines, blank fields) for the cleaning step.
"""
import os
import numpy as np
import pandas as pd

rng = np.random.default_rng(20261007)
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")

START, END = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-09-30")
MONTHS = pd.period_range(START, END, freq="M")

# ---------------------------------------------------------------- PPI (real)
ppi = pd.read_csv(os.path.join(RAW, "13_Ref_PPI_Basic_Organic_Chemicals_FRED.csv"))
ppi["m"] = pd.to_datetime(ppi["observation_date"]).dt.to_period("M")
ppi = ppi.set_index("m")["PCU325199325199"]
ppi_f = {m: float(ppi.get(m, ppi.iloc[-1])) / float(ppi[pd.Period("2022-01", "M")]) for m in MONTHS}


def cas_ok(cas):
    a, b, c = cas.split("-")
    digits = (a + b)[::-1]
    return sum((i + 1) * int(d) for i, d in enumerate(digits)) % 10 == int(c)


# ---------------------------------------------------------------- materials
# key, material no, description, type, group, plant, CAS, base price USD/kg (sell for FERT/HAWA, buy for ROH)
M = [
    # finished goods made at 1010
    ("DOTP", "30000101", "DOTP PLASTICIZER (BIS(2-ETHYLHEXYL) TEREPHTHALATE)", "FERT", "PLAST", "1010", "6422-86-2", 1.95),
    ("DINP", "30000102", "DINP PLASTICIZER (DIISONONYL PHTHALATE)", "FERT", "PLAST", "1010", "28553-12-0", 1.75),
    ("DOA", "30000103", "DOA PLASTICIZER (BIS(2-ETHYLHEXYL) ADIPATE)", "FERT", "PLAST", "1010", "103-23-1", 2.70),
    ("TOTM", "30000104", "TOTM PLASTICIZER (TRIS(2-ETHYLHEXYL) TRIMELLITATE)", "FERT", "PLAST", "1010", "3319-31-1", 3.30),
    ("2EH", "30000201", "2-ETHYLHEXANOL", "FERT", "OXOALC", "1010", "104-76-7", 1.95),
    ("NBUOH", "30000202", "N-BUTANOL", "FERT", "OXOALC", "1010", "71-36-3", 1.80),
    ("IBUOH", "30000203", "ISOBUTANOL", "FERT", "OXOALC", "1010", "78-83-1", 1.75),
    ("2EHACID", "30000204", "2-ETHYLHEXANOIC ACID", "FERT", "OXOALC", "1010", "149-57-5", 2.40),
    # finished goods made at 1020
    ("2EHA", "30000301", "2-ETHYLHEXYL ACRYLATE", "FERT", "ACRYL", "1020", "103-11-7", 2.90),
    ("BA", "30000302", "N-BUTYL ACRYLATE", "FERT", "ACRYL", "1020", "141-32-2", 2.70),
    ("BUAC", "30000401", "N-BUTYL ACETATE", "FERT", "SOLV", "1020", "123-86-4", 1.75),
    ("ETAC", "30000402", "ETHYL ACETATE", "FERT", "SOLV", "1020", "141-78-6", 1.40),
    ("PM", "30000403", "PROPYLENE GLYCOL METHYL ETHER (PM)", "FERT", "SOLV", "1020", "107-98-2", 2.05),
    ("DPM", "30000404", "DIPROPYLENE GLYCOL METHYL ETHER (DPM)", "FERT", "SOLV", "1020", "34590-94-8", 2.40),
    ("PMA", "30000405", "PROPYLENE GLYCOL METHYL ETHER ACETATE (PMA)", "FERT", "SOLV", "1020", "108-65-6", 2.25),
    # semi-finished
    ("NBAL", "20000101", "N-BUTANAL (BUTYRALDEHYDE) INTERMEDIATE", "HALB", "OXOINT", "1010", "123-72-8", 0.0),
    # traded goods (bought and resold from 1020)
    ("MEG", "40000101", "MONOETHYLENE GLYCOL", "HAWA", "GLYCOL", "1020", "107-21-1", 1.10),
    ("DEG", "40000102", "DIETHYLENE GLYCOL", "HAWA", "GLYCOL", "1020", "111-46-6", 1.25),
    ("TEG", "40000103", "TRIETHYLENE GLYCOL", "HAWA", "GLYCOL", "1020", "112-27-6", 1.70),
    ("MPG", "40000104", "MONOPROPYLENE GLYCOL USP", "HAWA", "GLYCOL", "1020", "57-55-6", 1.90),
    ("NPG", "40000105", "NEOPENTYL GLYCOL FLAKES", "HAWA", "POLYOL", "1020", "126-30-7", 2.20),
    ("TMP", "40000106", "TRIMETHYLOLPROPANE", "HAWA", "POLYOL", "1020", "77-99-6", 2.60),
    ("MMA", "40000107", "METHYL METHACRYLATE", "HAWA", "ACRYL", "1020", "80-62-6", 2.10),
    ("ACET", "40000108", "ACETONE", "HAWA", "SOLV", "1020", "67-64-1", 1.00),
    ("MEK", "40000109", "METHYL ETHYL KETONE", "HAWA", "SOLV", "1020", "78-93-3", 1.45),
    ("IPA", "40000110", "ISOPROPYL ALCOHOL", "HAWA", "SOLV", "1020", "67-63-0", 1.15),
    ("ESBO", "40000111", "EPOXIDIZED SOYBEAN OIL", "HAWA", "PLAST", "1020", "8013-07-8", 2.00),
    # raw materials
    ("PROPYLENE", "10000101", "PROPYLENE POLYMER GRADE", "ROH", "FEED", "1010", "115-07-1", 1.10),
    ("H2", "10000102", "HYDROGEN", "ROH", "FEED", "1010", "1333-74-0", 2.00),
    ("TPA", "10000103", "TEREPHTHALIC ACID PURIFIED", "ROH", "FEED", "1010", "100-21-0", 0.95),
    ("INA", "10000104", "ISONONANOL", "ROH", "FEED", "1010", "27458-94-2", 1.35),
    ("PA", "10000105", "PHTHALIC ANHYDRIDE", "ROH", "FEED", "1010", "85-44-9", 1.10),
    ("ADIP", "10000106", "ADIPIC ACID", "ROH", "FEED", "1010", "124-04-9", 2.10),
    ("TMA", "10000107", "TRIMELLITIC ANHYDRIDE", "ROH", "FEED", "1010", "552-30-7", 2.60),
    ("TIPT", "10000108", "TETRAISOPROPYL TITANATE CATALYST", "ROH", "CATAL", "1010", "546-68-9", 9.00),
    ("AA", "10000201", "ACRYLIC ACID GLACIAL", "ROH", "FEED", "1020", "79-10-7", 2.40),
    ("MEHQ", "10000202", "MEHQ INHIBITOR (4-METHOXYPHENOL)", "ROH", "ADDIT", "1020", "150-76-5", 12.0),
    ("H2SO4", "10000203", "SULFURIC ACID 98%", "ROH", "CATAL", "1020", "7664-93-9", 0.12),
    ("ACOH", "10000204", "ACETIC ACID GLACIAL", "ROH", "FEED", "1020", "64-19-7", 0.90),
    ("ETOH", "10000205", "ETHANOL ANHYDROUS", "ROH", "FEED", "1020", "64-17-5", 0.80),
    ("MEOH", "10000206", "METHANOL", "ROH", "FEED", "1020", "67-56-1", 0.45),
    ("PO", "10000207", "PROPYLENE OXIDE", "ROH", "FEED", "1020", "75-56-9", 1.80),
    ("NAOH", "10000208", "SODIUM HYDROXIDE 50% SOLUTION", "ROH", "CATAL", "1020", "1310-73-2", 0.55),
    # the hidden duplicates: purchased under a second number although the company makes them
    ("2EH_P", "10000209", "OCTANOL 2-ETHYL TECH GRADE", "ROH", "FEED", "1020", "104-76-7", 1.85),
    ("NBUOH_P", "10000210", "BUTAN-1-OL", "ROH", "FEED", "1020", "71-36-3", 1.70),
    ("PM_P", "10000109", "CLEANING SOLVENT - GLYCOL ETHER", "ROH", "MRO", "1010", "107-98-2", 1.90),
]
mat = pd.DataFrame(M, columns=["key", "matnr", "desc", "mtype", "mgroup", "plant", "cas", "price"])
assert all(cas_ok(c) for c in mat.cas), "bad CAS check digit"
K = mat.set_index("key")

# BOM per kg of output (plant, component qty per kg)
BOM = {
    "NBAL": {"PROPYLENE": 0.60, "H2": 0.03},
    "2EH": {"NBAL": 1.13, "H2": 0.02},
    "NBUOH": {"NBAL": 1.00, "H2": 0.03},
    "IBUOH": {"PROPYLENE": 0.60, "H2": 0.03},
    "2EHACID": {"NBAL": 1.05},
    "DOTP": {"2EH": 0.68, "TPA": 0.43, "TIPT": 0.001},
    "DINP": {"INA": 0.70, "PA": 0.35, "TIPT": 0.001},
    "DOA": {"2EH": 0.71, "ADIP": 0.40, "TIPT": 0.001},
    "TOTM": {"2EH": 0.72, "TMA": 0.36, "TIPT": 0.001},
    "2EHA": {"2EH_P": 0.72, "AA": 0.40, "MEHQ": 0.0002, "H2SO4": 0.005},
    "BA": {"NBUOH_P": 0.60, "AA": 0.58, "MEHQ": 0.0002, "H2SO4": 0.005},
    "BUAC": {"NBUOH_P": 0.66, "ACOH": 0.53, "H2SO4": 0.005},
    "ETAC": {"ETOH": 0.54, "ACOH": 0.70, "H2SO4": 0.005},
    "PM": {"MEOH": 0.37, "PO": 0.66, "NAOH": 0.002},
    "DPM": {"MEOH": 0.23, "PO": 0.80, "NAOH": 0.002},
    "PMA": {"PM": 0.70, "ACOH": 0.47, "H2SO4": 0.005},
}
CONV = {"NBAL": 0.10, "DOTP": 0.15, "DINP": 0.15, "DOA": 0.18, "TOTM": 0.20}
order_bom = ["NBAL", "2EH", "NBUOH", "IBUOH", "2EHACID", "DOTP", "DINP", "DOA", "TOTM",
             "2EHA", "BA", "BUAC", "ETAC", "PM", "DPM", "PMA"]


def std_cost(key, f):
    if key in BOM:
        return sum(q * std_cost(c, f) for c, q in BOM[key].items()) + CONV.get(key, 0.15)
    return K.loc[key, "price"] * f  # bought items valued at purchase price


# ---------------------------------------------------------------- business partners
first = ["Bayou", "Lone Star", "Prairie", "Summit", "Harbor", "Keystone", "Granite", "Cascade", "Redwood", "Pioneer",
         "Delta", "Northgate", "Silverline", "Meridian", "Copperfield", "Bluewater", "Ironbridge", "Westbrook",
         "Oakridge", "Riverbend", "Highland", "Evergreen", "Sunbelt", "Great Lakes", "Atlas", "Crescent", "Falcon",
         "Magnolia", "Tidewater", "Canyon", "Sierra", "Liberty", "Heartland", "Coastal", "Frontier", "Maple",
         "Aurora", "Rio Grande", "Ozark", "Vanguard", "Rhein", "Nordsee", "Alpen", "Brabant", "Ganges", "Andes"]
kind = {
    "PVC": ["Polymer Compounders", "Vinyl Products", "PVC Compounds", "Cable Compounds", "Flooring", "Hose & Tubing"],
    "COAT": ["Coatings", "Paint Works", "Industrial Finishes", "Protective Coatings"],
    "ADH": ["Adhesives", "Sealants", "Tapes & Labels", "Bonding Solutions"],
    "INK": ["Printing Inks", "Graphic Inks"],
    "CHEM": ["Specialty Chemicals", "Chemical Intermediates", "Lubricant Additives"],
    "PHARMA": ["Pharma Solutions", "Life Sciences"],
    "DIST": ["Chemical Distribution", "Solvents Supply"],
}
suffix = {"US": ["Inc.", "LLC", "Corp."], "CA": ["Ltd.", "Inc."], "MX": ["S.A. de C.V."], "BR": ["Ltda."],
          "DE": ["GmbH"], "NL": ["B.V."], "BE": ["NV"], "IN": ["Pvt. Ltd."]}
country_mess = {"US": ["US", "USA", "United States", "U.S.A."], "CA": ["CA", "Canada"], "MX": ["MX", "Mexico"],
                "BR": ["BR", "Brazil"], "DE": ["DE", "Germany"], "NL": ["NL", "Netherlands"],
                "BE": ["BE", "Belgium"], "IN": ["IN", "India"]}
cities = {"US": [("Houston", "TX"), ("Dallas", "TX"), ("Akron", "OH"), ("Cleveland", "OH"), ("Chicago", "IL"),
                 ("Charlotte", "NC"), ("Atlanta", "GA"), ("Louisville", "KY"), ("Newark", "NJ"),
                 ("Los Angeles", "CA"), ("Memphis", "TN"), ("Baton Rouge", "LA"), ("Pittsburgh", "PA"),
                 ("Grand Rapids", "MI"), ("Kansas City", "MO")],
          "CA": [("Toronto", "ON"), ("Montreal", "QC")], "MX": [("Monterrey", "NL"), ("Queretaro", "QRO")],
          "BR": [("Sao Paulo", "SP")], "DE": [("Ludwigshafen", "RP"), ("Cologne", "NW")],
          "NL": [("Rotterdam", "ZH")], "BE": [("Antwerp", "VAN")], "IN": [("Mumbai", "MH")]}
reps = pd.DataFrame({
    "rep": [f"R{i:02d}" for i in range(1, 9)],
    "rep_name": ["Dana Whitfield", "Marcus Lee", "Priya Raman", "Tom Kowalski", "Elena Ruiz",
                 "James Okafor", "Sophie Brandt", "Kevin Tran"],
    "region": ["US South", "US South", "US Midwest", "US Midwest", "US East", "US West", "Europe", "LATAM & Asia"],
})

N_CUST = 160
ind_p = {"PVC": 0.38, "COAT": 0.18, "ADH": 0.14, "INK": 0.06, "CHEM": 0.12, "PHARMA": 0.04, "DIST": 0.08}
ctry_p = {"US": 0.70, "CA": 0.06, "MX": 0.07, "BR": 0.03, "DE": 0.05, "NL": 0.04, "BE": 0.03, "IN": 0.02}
used = set()
cust = []
for i in range(N_CUST):
    ind = rng.choice(list(ind_p), p=list(ind_p.values()))
    ctry = rng.choice(list(ctry_p), p=list(ctry_p.values()))
    while True:
        nm = f"{rng.choice(first)} {rng.choice(kind[ind])} {rng.choice(suffix[ctry])}"
        if nm not in used:
            used.add(nm)
            break
    city, region = cities[ctry][rng.integers(len(cities[ctry]))]
    if ctry == "US":
        rep = {"TX": "R01", "LA": "R02", "TN": "R02", "OH": "R03", "IL": "R04", "MI": "R04", "MO": "R04",
               "KY": "R03", "PA": "R05", "NJ": "R05", "NC": "R05", "GA": "R02", "CA": "R06"}[region]
    elif ctry in ("DE", "NL", "BE"):
        rep = "R07"
    elif ctry == "CA":
        rep = "R04"
    else:
        rep = "R08"
    size = rng.choice(["S", "M", "L"], p=[0.45, 0.38, 0.17])
    cust.append(dict(bp=f"{1000100 + i * 7}", name=nm, ind=ind, ctry=ctry, city=city, region=region, rep=rep,
                     size=size))
cust = pd.DataFrame(cust)
# spot trader that takes surplus 2-EH
cust.loc[len(cust)] = dict(bp="1009990", name="Gulf Coast Spot Trading LLC", ind="DIST", ctry="US", city="Houston",
                           region="TX", rep="R01", size="L")

# customer life: start, churn, cadence, plasticizer behaviour
cust["start"] = [START + pd.Timedelta(days=int(d)) if rng.random() < 0.25 else START
                 for d in rng.integers(0, 900, len(cust))]
cust["cadence"] = np.where(cust["size"] == "L", rng.integers(10, 22, len(cust)),
                           np.where(cust["size"] == "M", rng.integers(18, 40, len(cust)),
                                    rng.integers(30, 75, len(cust))))
pvc = cust["ind"].eq("PVC")
# plasticizer behaviour; reps R03 and R05 push DINP (volume bonus) -> more switchers in their books
beh = []
for _, c in cust.iterrows():
    if c["ind"] != "PVC":
        beh.append("")
        continue
    p = [0.25, 0.20, 0.35, 0.20] if c["rep"] not in ("R03", "R05") else [0.10, 0.15, 0.60, 0.15]
    beh.append(rng.choice(["Loyal_A", "Loyal_B", "Switcher", "Mixed"], p=p))
cust["beh"] = beh
cust["switch_at"] = [pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 900))) if b == "Switcher"
                     else pd.NaT for b in cust["beh"]]
# churn: base 14%, switchers 32% (after moving to a commodity product they shop on price)
churn_p = np.where(cust["beh"].eq("Switcher"), 0.32, 0.14)
churn = rng.random(len(cust)) < churn_p
churn[cust["bp"].eq("1009990").values] = False
cust["end"] = END
lo, hi = pd.Timestamp("2023-03-01"), pd.Timestamp("2026-08-15")
for i in np.where(churn)[0]:
    s = max(lo, cust.at[i, "switch_at"] + pd.Timedelta(days=120)) if pd.notna(cust.at[i, "switch_at"]) else lo
    if s >= hi:
        s = hi - pd.Timedelta(days=60)
    cust.at[i, "end"] = s + pd.Timedelta(days=int(rng.integers(0, (hi - s).days)))
# at-risk: a further ~10% slow down sharply from 2026-03 (cadence x2.5) but have not stopped
slow = (~churn) & (rng.random(len(cust)) < 0.10)
slow[cust["bp"].eq("1009990").values] = False
cust["slow_from"] = [pd.Timestamp("2026-03-01") + pd.Timedelta(days=int(rng.integers(0, 90))) if s else pd.NaT
                     for s in slow]

basket = {
    "PVC": {"PLASTICIZER": 0.70, "DOA": 0.07, "TOTM": 0.07, "ESBO": 0.10, "2EHACID": 0.06},
    "COAT": {"BUAC": 0.18, "PMA": 0.14, "PM": 0.10, "DPM": 0.08, "BA": 0.14, "2EHA": 0.10, "MEK": 0.08,
             "ACET": 0.06, "NPG": 0.06, "TMP": 0.06},
    "ADH": {"2EHA": 0.40, "BA": 0.30, "ETAC": 0.12, "MMA": 0.10, "TOTM": 0.03, "DOA": 0.05},
    "INK": {"ETAC": 0.30, "PM": 0.18, "IPA": 0.20, "BUAC": 0.12, "PMA": 0.10, "NBUOH": 0.10},
    "CHEM": {"2EH": 0.30, "NBUOH": 0.20, "IBUOH": 0.15, "2EHACID": 0.15, "MEG": 0.10, "DEG": 0.10},
    "PHARMA": {"IPA": 0.35, "ETAC": 0.25, "ACET": 0.20, "MPG": 0.20},
    "DIST": {"MEG": 0.15, "DEG": 0.10, "TEG": 0.08, "MPG": 0.12, "IPA": 0.12, "ACET": 0.10, "MEK": 0.08,
             "BUAC": 0.10, "PM": 0.08, "2EH": 0.07},
}
lot = {"S": (2000, 8000), "M": (8000, 20000), "L": (20000, 44000)}


def prob_b(c, d):
    b = c["beh"]
    if b == "Loyal_A":
        return 0.05
    if b == "Loyal_B":
        return 0.93
    if b == "Mixed":
        return 0.30 + 0.35 * (d - START).days / (END - START).days
    x = (d - c["switch_at"]).days / 60.0
    return 0.08 + 0.85 / (1 + np.exp(-x))


# ---------------------------------------------------------------- sales orders
rows = []
doc = 5000000
for _, c in cust.iterrows():
    if c["bp"] == "1009990":
        continue
    d = c["start"] + pd.Timedelta(days=int(rng.integers(0, c["cadence"])))
    while d <= c["end"]:
        doc += 1
        items = basket[c["ind"]]
        n_it = rng.choice([1, 2, 3], p=[0.55, 0.32, 0.13])
        picks = rng.choice(list(items), size=n_it, replace=False, p=np.array(list(items.values())) / sum(items.values()))
        for it, p in enumerate(picks, start=1):
            key = p
            if p == "PLASTICIZER":
                key = "DINP" if rng.random() < prob_b(c, d) else "DOTP"
            qty = float(rng.uniform(*lot[c["size"]]))
            qty = round(qty / 100) * 100
            f = ppi_f[d.to_period("M")]
            list_price = K.loc[key, "price"] * f * rng.normal(1.0, 0.025)
            disc = max(0.0, rng.normal(0.03, 0.015))
            if key == "DINP" and c["rep"] in ("R03", "R05"):
                disc += max(0.0, rng.normal(0.05, 0.015))
            if c["size"] == "L":
                disc += 0.01
            rows.append(dict(doc=doc, item=it * 10, date=d, bp=c["bp"], key=key, qty=qty,
                             price=list_price, disc=disc))
        gap = c["cadence"] * rng.uniform(0.7, 1.35)
        if pd.notna(c["slow_from"]) and d >= c["slow_from"]:
            gap *= 2.5
        d = d + pd.Timedelta(days=int(max(3, gap)))
sales = pd.DataFrame(rows)

# ---------------------------------------------------------------- monthly plan: production, consumption, purchases
sales["m"] = sales["date"].dt.to_period("M")
dem = sales.groupby(["m", "key"])["qty"].sum().unstack(fill_value=0).reindex(MONTHS, fill_value=0)
prod = pd.DataFrame(0.0, index=MONTHS, columns=list(BOM))
cons = pd.DataFrame(0.0, index=MONTHS, columns=mat["key"])
EH_MIN = 1_000_000  # oxo unit minimum load, kg 2-EH per month
EH_CAP, EH_KEEP = 2_800_000, 2_200_000  # when tank stock passes the cap, surplus is sold spot down to EH_KEEP
s2 = 600_000.0
eh_need = []
spot_2eh = {}
for m in MONTHS:
    need = dem.loc[m].to_dict()
    for k in list(need):
        need[k] = need[k] * rng.uniform(1.0, 1.04)
    # top-down: finished goods first, then their components
    for key in reversed(order_bom):
        q = need.get(key, 0.0)
        if key == "2EH":
            out = q
            eh_need.append(out)
            q = max(q, EH_MIN * rng.uniform(0.97, 1.03))
            s2 += q - out
            spot_2eh[m] = 0.0
            if s2 > EH_CAP:
                spot_2eh[m] = s2 - EH_KEEP
                s2 = EH_KEEP
        prod.loc[m, key] = q
        for comp, r in BOM[key].items():
            cons.loc[m, comp] += q * r
            if comp in BOM:
                need[comp] = need.get(comp, 0.0) + q * r

# spot sales of 2-EH surplus to the trader (low price, end of month)
spot_rows = []
for m, q in spot_2eh.items():
    if q < 1000:
        continue
    doc += 1
    d = m.to_timestamp(how="end").normalize() - pd.Timedelta(days=int(rng.integers(1, 5)))
    spot_rows.append(dict(doc=doc, item=10, date=d, bp="1009990", key="2EH", qty=round(q / 1000) * 1000,
                          price=K.loc["2EH", "price"] * ppi_f[m] * 0.74, disc=0.0))

sales = pd.concat([sales, pd.DataFrame(spot_rows)], ignore_index=True)
sales["m"] = sales["date"].dt.to_period("M")
dem = sales.groupby(["m", "key"])["qty"].sum().unstack(fill_value=0).reindex(MONTHS, fill_value=0)

# purchases: ROH = consumption, HAWA = sales demand; small safety stock build
buy_keys = mat.loc[mat.mtype.isin(["ROH", "HAWA"]), "key"].tolist()
buy = pd.DataFrame(0.0, index=MONTHS, columns=buy_keys)
for k in buy_keys:
    base = cons[k] if K.loc[k, "mtype"] == "ROH" else dem.get(k, pd.Series(0.0, index=MONTHS))
    buy[k] = base * rng.uniform(0.97, 1.06, len(MONTHS))
buy["PM_P"] = rng.uniform(1500, 3500, len(MONTHS)).round(-2)  # MRO cleaning solvent, small
cons["PM_P"] = buy["PM_P"] * rng.uniform(0.9, 1.0, len(MONTHS))

# ---------------------------------------------------------------- stock (month end, MARD-like)
stock_rows = []
for _, r in mat.iterrows():
    k = r["key"]
    s = {"FERT": 1.0, "HAWA": 0.6, "ROH": 0.5, "HALB": 0.3}[r["mtype"]] * max(
        1.0, float(dem.get(k, pd.Series([0])).mean() if k in dem else 0) + float(cons[k].mean()) / 2)
    if k == "2EH":
        s = 600_000.0
    for m in MONTHS:
        inflow = (prod.loc[m, k] if k in prod else 0.0) + (buy.loc[m, k] if k in buy else 0.0)
        out = (dem.loc[m, k] if k in dem else 0.0) + cons.loc[m, k]
        s = max(0.0, s + inflow - out)
        if k != "2EH" and s > 3.0 * max(out, 1.0):  # planners trim overstock on everything except 2-EH
            s = 1.2 * out
        stock_rows.append(dict(key=k, plant=r["plant"], m=m, qty=s))
stock = pd.DataFrame(stock_rows)

# ---------------------------------------------------------------- suppliers
sup = pd.DataFrame([
    ("2000101", "Texan Olefins Supply LP", "US", "Houston", ["PROPYLENE", "H2"]),
    ("2000102", "Coastal Hydrogen Partners LLC", "US", "Pasadena", ["H2"]),
    ("2000103", "Meridian Aromatics Corp.", "US", "Decatur", ["TPA", "PA"]),
    ("2000104", "Northshore Alcohols B.V.", "NL", "Rotterdam", ["INA"]),
    ("2000105", "Keystone Diacids Inc.", "US", "Pensacola", ["ADIP", "TMA"]),
    ("2000106", "Catalyst Specialties GmbH", "DE", "Leverkusen", ["TIPT", "MEHQ"]),
    ("2000107", "Gulf Acrylics LLC", "US", "Clear Lake", ["AA"]),
    ("2000108", "Bayou Sulphur Co.", "US", "Baton Rouge", ["H2SO4", "NAOH"]),
    ("2000109", "Prairie Acetyls Corp.", "US", "Texas City", ["ACOH"]),
    ("2000110", "Heartland Ethanol Marketing LLC", "US", "Omaha", ["ETOH"]),
    ("2000111", "Sabine Methanol LP", "US", "Beaumont", ["MEOH"]),
    ("2000112", "Lakeside Oxides Inc.", "US", "Freeport", ["PO"]),
    ("2000113", "Gulf Coast Oxo Alcohols LLC", "US", "Port Arthur", ["2EH_P", "NBUOH_P"]),
    ("2000114", "Rheinland Alkohole GmbH", "DE", "Marl", ["2EH_P", "NBUOH_P"]),
    ("2000115", "Summit Solvents Distribution Inc.", "US", "Houston", ["PM_P", "ACET", "MEK", "IPA"]),
    ("2000116", "Atlas Glycols Trading LLC", "US", "Lake Jackson", ["MEG", "DEG", "TEG", "MPG"]),
    ("2000117", "Pioneer Polyols Corp.", "US", "Bishop", ["NPG", "TMP"]),
    ("2000118", "Cascade Monomers Ltd.", "CA", "Sarnia", ["MMA"]),
    ("2000119", "Heartland Soy Derivatives LLC", "US", "Decatur", ["ESBO"]),
], columns=["lifnr", "name", "ctry", "city", "keys"])
sup_for = {}
for _, s in sup.iterrows():
    for k in s["keys"]:
        sup_for.setdefault(k, []).append(s["lifnr"])

# purchase orders: split each month into 1-4 POs
po_rows = []
po = 4500000
for k in buy_keys:
    lots = 4 if K.loc[k, "price"] < 3 else 1
    for m in MONTHS:
        q = buy.loc[m, k]
        if q < 10:
            continue
        n = max(1, min(lots, int(q // 40000) + 1))
        for j in range(n):
            po += 1
            vend = rng.choice(sup_for[k])
            prem = 1.04 if vend == "2000114" else 1.0  # import premium
            d = m.to_timestamp() + pd.Timedelta(days=int(rng.integers(0, 27)))
            po_rows.append(dict(po=po, item=10, date=d, lifnr=vend, key=k, qty=round(q / n, -1),
                                price=K.loc[k, "price"] * ppi_f[m] * prem * rng.normal(1, 0.02),
                                deliv=d + pd.Timedelta(days=int(rng.integers(5, 21)))))
pos = pd.DataFrame(po_rows)

# production orders: 2-6 per month per material
pr_rows = []
ordno = 1000000
for k in BOM:
    for m in MONTHS:
        q = prod.loc[m, k]
        if q < 10:
            continue
        n = 2 if q < 200000 else 4 if q < 1000000 else 6
        for j in range(n):
            ordno += 1
            st = m.to_timestamp() + pd.Timedelta(days=int(j * 28 / n + rng.integers(0, 3)))
            plan = round(q / n, -2)
            pr_rows.append(dict(aufnr=ordno, key=k, plant=K.loc[k, "plant"], start=st,
                                finish=st + pd.Timedelta(days=int(rng.integers(2, 6))),
                                plan=plan, conf=round(plan * rng.normal(0.99, 0.015), -1)))
prods = pd.DataFrame(pr_rows)

# ---------------------------------------------------------------- write raw SAP-style exports (with mess)
os.makedirs(RAW, exist_ok=True)


def sap_date(d, mixed=False):
    if mixed and rng.random() < 0.08:
        return d.strftime("%Y-%m-%d")
    return d.strftime("%d.%m.%Y")


# 01 material master (MARA)
mara = pd.DataFrame({
    "Material": mat["matnr"], "Material_Description": mat["desc"], "Material_Type": mat["mtype"],
    "Material_Group": mat["mgroup"], "Base_Unit": "KG",
    "Created_On": [sap_date(pd.Timestamp("2014-03-01") + pd.Timedelta(days=int(x))) for x in rng.integers(0, 2500, len(mat))],
    "Created_By": rng.choice(["JSMITH", "MDM_BATCH", "AGARCIA", "PLANT1020_MM", "LCHEN"], len(mat)),
})
# the two duplicates were created by the 1020 buyer much later, the cleaning solvent by plant 1010 maintenance
mara.loc[mat.key.eq("2EH_P"), ["Created_On", "Created_By"]] = ["14.06.2021", "PLANT1020_MM"]
mara.loc[mat.key.eq("NBUOH_P"), ["Created_On", "Created_By"]] = ["02.09.2021", "PLANT1020_MM"]
mara.loc[mat.key.eq("PM_P"), ["Created_On", "Created_By"]] = ["19.01.2022", "MAINT1010"]
mara["Material_Description"] = [d.lower().title() if rng.random() < 0.1 else d for d in mara["Material_Description"]]
mara.to_csv(os.path.join(RAW, "01_Material_Master_MARA.csv"), index=False)

# 02 plant data + current standard price (MARC/MBEW)
f_now = ppi_f[pd.Period("2026-01", "M")]
marc = []
for _, r in mat.iterrows():
    proc = "E" if r["key"] in BOM else "F"
    marc.append(dict(Material=r["matnr"], Plant=r["plant"], Procurement_Type=proc,
                     MRP_Controller={"1010": "P01", "1020": "P02"}[r["plant"]],
                     Standard_Price=round(std_cost(r["key"], f_now) * 1000, 2), Price_Unit=1000, Currency="USD"))
# 2-EH and n-butanol are also extended to 1020 as finished goods for stock transfer - never used
for k in ("2EH", "NBUOH"):
    marc.append(dict(Material=K.loc[k, "matnr"], Plant="1020", Procurement_Type="F", MRP_Controller="P02",
                     Standard_Price=round((std_cost(k, f_now) + 0.04) * 1000, 2), Price_Unit=1000, Currency="USD"))
pd.DataFrame(marc).to_csv(os.path.join(RAW, "02_Material_Plant_MARC.csv"), index=False)

# 03 classification - CAS numbers (formatting mess on purpose)
cls = []
for _, r in mat.iterrows():
    cas = r["cas"]
    if r["key"] == "2EH_P":
        cas = "104767"
    elif r["key"] == "NBUOH_P":
        cas = " 71-36-3 "
    elif r["key"] == "PM_P":
        cas = "107-98-2 (mixture)"
    elif r["key"] in ("ESBO", "TEG"):
        cas = ""
    elif rng.random() < 0.08:
        cas = "CAS " + cas
    cls.append(dict(Material=r["matnr"], Class_Type="001", Class="CHEM_IDENT", Characteristic="CAS_NUMBER", Value=cas))
    if rng.random() < 0.7:
        cls.append(dict(Material=r["matnr"], Class_Type="001", Class="CHEM_IDENT", Characteristic="GHS_SIGNAL_WORD",
                        Value=rng.choice(["Warning", "Danger", ""])))
pd.DataFrame(cls).to_csv(os.path.join(RAW, "03_Material_Classification_CAS.csv"), index=False)

# 04 BOM (STPO)
bom_rows = []
for k, comps in BOM.items():
    for i, (c, q) in enumerate(comps.items(), start=1):
        bom_rows.append(dict(Parent_Material=K.loc[k, "matnr"], Plant=K.loc[k, "plant"], BOM_Item=i * 10,
                             Component=K.loc[c, "matnr"], Component_Qty=round(q * 1000, 3), Base_Qty=1000, Unit="KG"))
pd.DataFrame(bom_rows).to_csv(os.path.join(RAW, "04_Bill_of_Materials_STPO.csv"), index=False)

# 05 customers
bp = pd.DataFrame({
    "Business_Partner": cust["bp"], "Name": cust["name"],
    "Country": [rng.choice(country_mess[c]) for c in cust["ctry"]],
    "City": cust["city"], "Region": cust["region"],
    "Industry": cust["ind"].map({"PVC": "PVC & Vinyl", "COAT": "Paints & Coatings", "ADH": "Adhesives & Sealants",
                                 "INK": "Printing Inks", "CHEM": "Chemicals", "PHARMA": "Pharmaceuticals",
                                 "DIST": "Distribution"}),
    "Sales_Rep": cust["rep"],
    "Customer_Since": [sap_date(d - pd.Timedelta(days=int(rng.integers(0, 3000))) if d == START else d)
                       for d in cust["start"]],
    "Payment_Terms": rng.choice(["NT30", "NT45", "NT60"], len(cust)),
})
bp.loc[rng.random(len(bp)) < 0.04, "Sales_Rep"] = ""
dups = bp.sample(4, random_state=7).copy()
dups["Business_Partner"] = [str(9000001 + i) for i in range(4)]
dups["Name"] = dups["Name"].str.upper().str.replace(".", "", regex=False)
bp = pd.concat([bp, dups], ignore_index=True)
bp.to_csv(os.path.join(RAW, "05_Business_Partner_Customers.csv"), index=False)
reps.rename(columns={"rep": "Sales_Rep", "rep_name": "Rep_Name", "region": "Sales_Region"}).to_csv(
    os.path.join(RAW, "06_Sales_Reps.csv"), index=False)

# 07 suppliers
pd.DataFrame({"Supplier": sup["lifnr"], "Name": sup["name"],
              "Country": [rng.choice(country_mess[c]) for c in sup["ctry"]], "City": sup["city"],
              "Supplier_Type": "External"}).to_csv(os.path.join(RAW, "07_Business_Partner_Suppliers.csv"), index=False)

# 08 sales order items (VBAK/VBAP joined)
sales = sales.sort_values(["date", "doc", "item"]).reset_index(drop=True)
so = pd.DataFrame({
    "Sales_Document": sales["doc"], "Item": sales["item"], "Order_Type": "OR",
    "Created_On": [sap_date(d, mixed=True) for d in sales["date"]],
    "Sold_To": sales["bp"], "Material": sales["key"].map(K["matnr"]),
    "Plant": sales["key"].map(K["plant"]),
    "Order_Qty": sales["qty"].astype(float), "Sales_Unit": "KG",
    "List_Price_per_KG": sales["price"].round(4), "Discount_Pct": (sales["disc"] * 100).round(2),
})
so["Net_Value"] = (so["Order_Qty"] * so["List_Price_per_KG"] * (1 - so["Discount_Pct"] / 100)).round(2)
so["Currency"] = "USD"
so["Billing_Date"] = [sap_date(d + pd.Timedelta(days=int(rng.integers(2, 12)))) for d in sales["date"]]
# units: some lines entered in MT or LB (qty and price converted accordingly)
mt = rng.random(len(so)) < 0.05
so.loc[mt, "Order_Qty"] = so.loc[mt, "Order_Qty"] / 1000
so.loc[mt, "Sales_Unit"] = "MT"
so.loc[mt, "List_Price_per_KG"] = (so.loc[mt, "List_Price_per_KG"] * 1000).round(2)
lb = (~mt) & (rng.random(len(so)) < 0.02) & so["Plant"].eq("1020")
so.loc[lb, "Order_Qty"] = (so.loc[lb, "Order_Qty"] * 2.20462).round(0)
so.loc[lb, "Sales_Unit"] = "LB"
so.loc[lb, "List_Price_per_KG"] = (so.loc[lb, "List_Price_per_KG"] / 2.20462).round(4)
so = so.rename(columns={"List_Price_per_KG": "List_Price_per_Unit"})
# returns (credit memo requests)
ret = so.sample(frac=0.007, random_state=11).copy()
ret["Order_Type"] = "RE"
ret["Order_Qty"] = -(ret["Order_Qty"] * rng.uniform(0.05, 0.5, len(ret))).round(0)
ret["Net_Value"] = (ret["Order_Qty"] * ret["List_Price_per_Unit"] * (1 - ret["Discount_Pct"] / 100)).round(2)
ret["Sales_Document"] = range(6900001, 6900001 + len(ret))
so = pd.concat([so, ret, so.sample(frac=0.003, random_state=5)], ignore_index=True)  # + exact duplicate rows
so.to_csv(os.path.join(RAW, "08_Sales_Order_Items_VBAP.csv"), index=False)

# 09 purchase order items (EKKO/EKPO)
pos = pos.sort_values("date").reset_index(drop=True)
ek = pd.DataFrame({
    "Purchasing_Document": pos["po"], "Item": pos["item"], "Document_Date": [sap_date(d, True) for d in pos["date"]],
    "Supplier": pos["lifnr"], "Material": pos["key"].map(K["matnr"]),
    "Short_Text": pos["key"].map(K["desc"]), "Plant": pos["key"].map(K["plant"]),
    "PO_Qty": pos["qty"], "Order_Unit": "KG", "Net_Price": (pos["price"] * 1000).round(2), "Price_Unit": 1000,
    "Currency": "USD", "Delivery_Date": [sap_date(d) for d in pos["deliv"]],
})
ek["Net_Order_Value"] = (ek["PO_Qty"] * ek["Net_Price"] / ek["Price_Unit"]).round(2)
ek.to_csv(os.path.join(RAW, "09_Purchase_Order_Items_EKPO.csv"), index=False)

# 10 production orders (AFKO/AFPO)
prods = prods.sort_values("start").reset_index(drop=True)
pd.DataFrame({
    "Order": prods["aufnr"], "Order_Type": "PP01", "Material": prods["key"].map(K["matnr"]), "Plant": prods["plant"],
    "Basic_Start": [sap_date(d) for d in prods["start"]], "Basic_Finish": [sap_date(d) for d in prods["finish"]],
    "Planned_Qty": prods["plan"], "Confirmed_Qty": prods["conf"], "Unit": "KG",
    "Status": np.where(prods["finish"] > END, "REL", "TECO"),
}).to_csv(os.path.join(RAW, "10_Production_Orders_AFKO.csv"), index=False)

# 11 month-end stock (MARD snapshot)
pd.DataFrame({
    "Material": stock["key"].map(K["matnr"]), "Plant": stock["plant"], "Storage_Location": "0001",
    "Fiscal_Period": [m.strftime("%Y%m") for m in stock["m"]], "Unrestricted_Stock": stock["qty"].round(0),
    "Unit": "KG",
}).to_csv(os.path.join(RAW, "11_Month_End_Stock_MARD.csv"), index=False)

# 12 standard cost history (one price per January)
sch = []
for _, r in mat.iterrows():
    for y in range(2022, 2027):
        sch.append(dict(Material=r["matnr"], Plant=r["plant"], Valid_From=f"01.01.{y}",
                        Standard_Price=round(std_cost(r["key"], ppi_f[pd.Period(f"{y}-01", 'M')]) * 1000, 2),
                        Price_Unit=1000, Currency="USD"))
pd.DataFrame(sch).to_csv(os.path.join(RAW, "12_Standard_Cost_History.csv"), index=False)

print("2-EH monthly need t: mean", round(np.mean(eh_need) / 1000), "min", round(min(eh_need) / 1000), "max", round(max(eh_need) / 1000))
print("customers", len(bp), "sales lines", len(so), "PO lines", len(ek), "prod orders", len(prods),
      "stock rows", len(stock))

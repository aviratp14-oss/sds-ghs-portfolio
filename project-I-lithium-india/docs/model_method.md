# How the model works

The model answers one question: if India's lithium supply stays small and mostly imported, how much of it do EVs and grid storage actually get once everyone else has taken their share?

It runs once for every combination of 3 scenarios, 6 lever settings and 16 years (2025 to 2040). The Python version is [`scripts/02_demand_supply_model.py`](../scripts/02_demand_supply_model.py). The Excel version, [`excel/Project_I_Lithium_Demand_Model.xlsx`](../excel/Project_I_Lithium_Demand_Model.xlsx), does the same maths with plain formulas, and I checked all 18 scenario and lever combinations in it against the Python output.

```
 ┌──────────────────────────┐      ┌──────────────────────────────┐
 │  ACTIVITY                │      │  INTENSITY                   │
 │  EV sales by segment     │      │  kWh per vehicle / device    │
 │  storage GWh added       │ ───► │  chemistry mix (LFP, NMC,    │
 │  phones, laptops, etc.   │      │  sodium-ion share)           │
 │  grease, glass, defence  │      │  kg LCE per kWh              │
 └──────────────────────────┘      └──────────────┬───────────────┘
                                                  ▼
                                  ┌──────────────────────────────┐
                                  │  DEMAND (t LCE)              │
                                  │  17 uses x year x scenario   │
                                  └──────────────┬───────────────┘
                                                 ▼
 ┌──────────────────────────┐    ┌──────────────────────────────┐
 │  SUPPLY                  │    │  BALANCE                     │
 │  recycling               │    │  shortfall, import           │
 │  mining in India         │ ─► │  dependence, recycled        │
 │  overseas equity         │    │  content                     │
 │  import cap (share of    │    └──────────────┬───────────────┘
 │  world supply)           │                   ▼
 └──────────────────────────┘    ┌──────────────────────────────┐
                                  │  SQUEEZE                     │
                                  │  non-energy uses served      │
                                  │  first; EVs and storage get  │
                                  │  what is left                │
                                  └──────────────┬───────────────┘
                                                 ▼
                                  ┌──────────────────────────────┐
                                  │  POLICY LEVERS               │
                                  │  recycling, overseas assets, │
                                  │  sodium-ion, exploration     │
                                  └──────────────────────────────┘
```

## Demand

Each use is built bottom-up and converted to tonnes of LCE.

**EVs (six segments).** Vehicle market x EV share of sales x lithium-ion share x kWh per vehicle x lithium per kWh. The segments are two-wheelers, L5 three-wheelers (autos and cargo), L3 e-rickshaws, cars, buses and trucks. The 2025 base comes from IESA (2.6 million EVs). E-rickshaws are the odd one: most still run on lead-acid, so their lithium-ion share starts at 25% and reaches 100% by 2040.

| Base case | 2025 | 2030 | 2040 |
|---|---|---|---|
| EV share, two-wheelers | 7.8% | 30% | 75% |
| EV share, cars | 4.5% | 13% | 45% |
| EV share, buses | 5.2% | 25% | 75% |
| Pack size, two-wheeler | 2.8 kWh | 3.2 kWh | 3.8 kWh |
| Pack size, car | 38 kWh | 42 kWh | 48 kWh |

**Grid storage.** Installed storage follows the CEA path, a little late in the Base case: 4 GWh in 2025, 110 GWh in 2030 and 500 GWh in 2040. New GWh each year rises in a straight line within each five-year block, so the installed total still hits each milestone without a sudden jump in the first year. Systems are replaced after 12 years. Storage is all LFP, with a growing sodium-ion share.

**Electronics.** Units sold (IDC: 152 million phones, 15.9 million PCs and 114 million wearables in 2025) x Wh per device. Phones assembled for export are a separate line, estimated from ICEA export values, because that lithium leaves India.

**Industry.** Grease, glass and ceramics, and pharma and other, from the cleaned imports of lithium carbonate and hydroxide (average of 2022 to 2024). The grease figure from trade data (1,080 t LCE) agrees with an NLGI grease survey (about 1,031 t LCE) within 5%.

**Defence and aerospace.** No public data exists, so this is a labelled assumption: 150 t LCE in 2025, growing to about 480 t in 2040 in the Base case.

**Lithium per kWh** comes from cathode chemistry rather than a rule of thumb. For each chemistry I took the formula mass, practical capacity and voltage, worked out kg of cathode per kWh and its lithium content, then added electrolyte salt and manufacturing scrap. That gives about 0.51 kg LCE per kWh for LFP, 0.59 for NMC811 and 0.66 for LCO (phones). Sodium-ion uses none.

## Supply

| Source | How it's built |
|---|---|
| Recycling | Lithium sold N years ago x collection rate x lithium recovery. N is the battery life: 3 years for phones and e-rickshaws, 6 for two- and three-wheelers, 8 for buses and trucks, 10 for cars, 12 for storage. Base collection rises from 30% to 90% for EV and storage batteries and from 15% to 70% for electronics |
| Mining in India | Zero until a start year: never in Low, 2039 in Base, 2033 in High. Reasi holds about 18 kt LCE in total, and the IEA puts discovery to production at over 16 years |
| Overseas equity | KABIL's Catamarca blocks from 2032 in Base, reaching 12 kt LCE in 2040 |
| Import cap | World supply x India's accessible share. World supply starts at 290 kt lithium in 2025 (USGS), about 1,544 kt LCE, and grows to 4,300 kt LCE in 2040. The share is 3% by default |

The import cap is the assumption that matters most. India uses about 1% of world lithium today and is about 3.5% of world GDP, so 3% is a reasonable middle. I treat it as a stress test, not a forecast. The workbook and the dashboard both let you change it.

## The squeeze rule

When supply is short, non-energy uses are served first. A phone maker or a grease blender spends a tiny share of product cost on lithium and will outbid an EV maker, for whom the battery is a large part of the vehicle cost.

```
available       = recycling + mining + overseas equity + import cap
shortfall       = MAX(0, demand - available)
energy coverage = MIN(1, MAX(0, available - non-energy demand) / energy demand)
```

Energy coverage is the share of EV and storage demand that can still be met. That's the number the dashboard leads with.

## Scenarios

| | Low | Base | High |
|---|---|---|---|
| EV adoption | Slow | Current trend extended | NITI Aayog ambition (80% of 2W and 3W, 30% of cars by 2030) |
| Storage | Below the CEA path | CEA path, a little late | Above the CEA path |
| Electronics and industry growth | Slower | Trend | Faster |
| Recycling | Weak collection | Rules met on time | Rules met with higher collection |
| Mining in India | None | From 2039 | From 2033 |
| Overseas equity | None | From 2032 | From 2031, larger |

"Low" and "High" describe clean-energy adoption. High adoption makes the squeeze worse, which is the point of testing it.

## Policy levers

Each lever runs on top of the chosen scenario. "All four levers" runs them together.

| Lever | What changes |
|---|---|
| Recycling push | Collection 90% for EV and storage batteries and 70% for electronics by 2030, lithium recovery 95% |
| Overseas assets | Extra 10, 30 and 50 kt LCE of equity supply in 2030, 2035 and 2040, starting 2031 |
| Sodium-ion push | Sodium-ion share in two-wheelers, three-wheelers and storage up by 15, 30 and 40 points by 2030, 2035 and 2040 |
| Exploration fast-track | Mining in India from 2032, 1.5 kt LCE by 2035 and 4 kt by 2040 |

`Fact_Lever_Impact` compares each lever with "None" in the same scenario and year.

## Results (Base case, 3% share)

| | 2025 | 2030 | 2035 | 2040 |
|---|---|---|---|---|
| Demand (kt LCE) | 16 | 64 | 136 | 266 |
| Non-energy share | 38% | 12% | 7% | 5% |
| Supply in reach (kt LCE) | 47 | 81 | 126 | 203 |
| Shortfall (kt LCE) | 0 | 0 | 10 | 63 |
| EV and storage demand met | 100% | 100% | 92% | 75% |
| Recycling (kt LCE) | 0.4 | 3.0 | 18.2 | 61.1 |
| Import dependence | 97% | 95% | 87% | 77% |

Gap closed in 2040 by each lever: overseas assets 50 kt, sodium-ion 30 kt, exploration 3.4 kt, recycling push 2 kt, all four together 63 kt (the whole gap). The recycling push does little by 2040 because the Base case already assumes the rules are met on time.

| Scenario | First gap year | 2040 demand (kt) | 2040 shortfall (kt) | 2040 EV and storage met |
|---|---|---|---|---|
| Low | none | 145 | 0 | 100% |
| Base | 2034 | 266 | 63 | 75% |
| High | 2028 | 430 | 155 | 63% |

## Checks I ran

- Excel and Python agree on all 18 scenario and lever combinations, after recalculating the workbook in LibreOffice.
- The DAX in Power BI recalculates the shortfall and coverage from the world share slicer. At 3% it matches the CSV within 0.1 t.
- Grease from trade data vs the NLGI survey: within 5%.
- Each EV segment's 2025 share of GWh matches what IESA reported, which is how I set the pack sizes.

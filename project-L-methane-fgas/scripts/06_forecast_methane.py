"""Project L, step 6: US methane forecast 2024-2030 (see docs/forecast_model.md).

Linear trend (OLS) fitted to 2016-2023 EPA GHGRP methane, per segment and for the
total, with a 90% prediction interval on the total and a Global Methane Pledge path
(-30% vs 2020 by 2030). Reads data/clean/Fact_Emissions.csv, writes
data/clean/Fact_Forecast_Methane.csv and data/clean/Ref_Forecast_Fit.csv, logs to DQ_Log.csv.
Run: python scripts/06_forecast_methane.py [--fit-start 2016] [--fit-end 2023]
"""
import argparse, datetime
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / 'data' / 'clean'
HORIZON = 2030
PLEDGE_BASE, PLEDGE_CUT = 2020, 0.30
T90 = {4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895, 8: 1.860, 9: 1.833, 10: 1.812, 11: 1.796, 12: 1.782}  # t(0.95, df)
ALL = 'All Segments'

ap = argparse.ArgumentParser()
ap.add_argument('--fit-start', type=int, default=2016)
ap.add_argument('--fit-end', type=int, default=2023)
args = ap.parse_args()
run = datetime.date.today().isoformat()
method = f'OLS linear {args.fit_start}-{args.fit_end}'

d = pd.read_csv(CLEAN / 'Fact_Emissions.csv', usecols=['Year', 'Segment', 'Gas_Group', 'CO2e_AR5_tCO2e'])
d = d[d.Gas_Group == 'Methane']
seg = d.groupby(['Year', 'Segment']).CO2e_AR5_tCO2e.sum().div(1e6).unstack('Segment')
seg[ALL] = seg.sum(axis=1)
last = int(seg.index.max())

rows, fits = [], []
for s in seg.columns:
    for y, v in seg[s].dropna().items():
        rows.append(dict(Year=int(y), Segment=s, Series='Actual', Methane_MtCO2e=round(v, 3), Method='EPA GHGRP reported'))
    y_ = seg[s].loc[args.fit_start:args.fit_end].dropna()
    x = y_.index.values.astype(float); n = len(x)
    b, a = np.polyfit(x, y_.values, 1)
    res = y_.values - (a + b * x)
    se = float(np.sqrt((res ** 2).sum() / (n - 2)))
    r2 = float(1 - (res ** 2).sum() / ((y_.values - y_.values.mean()) ** 2).sum())
    sxx = ((x - x.mean()) ** 2).sum()
    fits.append(dict(Segment=s, Fit_Start=args.fit_start, Fit_End=args.fit_end, n=n, Slope_Mt_per_yr=round(b, 4),
                     Intercept=round(a, 3), Residual_SE=round(se, 4), R2=round(r2, 4), Run_Date=run))
    for yr in range(last + 1, HORIZON + 1):
        f = max(a + b * yr, 0.0)
        r = dict(Year=yr, Segment=s, Series='Forecast', Methane_MtCO2e=round(f, 3), Method=method)
        if s == ALL:  # band on the total only; segment errors are not independent
            h = T90[n - 2] * se * np.sqrt(1 + 1 / n + (yr - x.mean()) ** 2 / sxx)
            r.update(Lower_90_MtCO2e=round(max(f - h, 0), 3), Upper_90_MtCO2e=round(f + h, 3))
        rows.append(r)
    # Bridge the dotted line to the last actual so the chart has no gap
    if s == ALL:
        rows.append(dict(Year=last, Segment=s, Series='Forecast', Methane_MtCO2e=round(seg[s].loc[last], 3),
                         Lower_90_MtCO2e=round(seg[s].loc[last], 3), Upper_90_MtCO2e=round(seg[s].loc[last], 3),
                         Method='Last actual (line join)'))

base = seg[ALL].loc[PLEDGE_BASE]
for yr in range(PLEDGE_BASE, HORIZON + 1):
    rows.append(dict(Year=yr, Segment=ALL, Series='Pledge', Methane_MtCO2e=round(base * (1 - PLEDGE_CUT * (yr - PLEDGE_BASE) / (HORIZON - PLEDGE_BASE)), 3),
                     Method=f'Global Methane Pledge: -30% vs {PLEDGE_BASE} by {HORIZON}, straight line'))

cols = ['Year', 'Segment', 'Series', 'Methane_MtCO2e', 'Lower_90_MtCO2e', 'Upper_90_MtCO2e', 'Method', 'Run_Date']
out = pd.DataFrame(rows).assign(Run_Date=run).reindex(columns=cols).sort_values(['Series', 'Segment', 'Year'])
assert not out.duplicated(['Year', 'Segment', 'Series']).any()
out.to_csv(CLEAN / 'Fact_Forecast_Methane.csv', index=False)
pd.DataFrame(fits).to_csv(CLEAN / 'Ref_Forecast_Fit.csv', index=False)

fc = out[(out.Series == 'Forecast') & (out.Year > last)]
seg_sum = fc[fc.Segment != ALL].groupby('Year').Methane_MtCO2e.sum()
tot = fc[fc.Segment == ALL].set_index('Year').Methane_MtCO2e
print('max |segments - total|:', round(float((seg_sum - tot).abs().max()), 3))
t30 = fc[(fc.Segment == ALL) & (fc.Year == HORIZON)].iloc[0]
p30 = out[(out.Series == 'Pledge') & (out.Year == HORIZON)].Methane_MtCO2e.iloc[0]
print(f'rows {len(out)}; {HORIZON}: {t30.Methane_MtCO2e:.1f} Mt (90%: {t30.Lower_90_MtCO2e:.1f}-{t30.Upper_90_MtCO2e:.1f}); pledge {p30:.1f}')

log = pd.read_csv(CLEAN / 'DQ_Log.csv')
issue = 'EPA data ends in the last reporting year; dashboard needs values to 2030'
log = log[log.Issue != issue]
log.loc[len(log)] = [int(log.ID.max()) + 1, 'Forecast (Fact_Forecast_Methane)', issue, f'last actual year = {last}',
                     f'{len(out)} rows', f'{method} per segment + total, 90% prediction band on total, pledge path; script forecast_methane.py run {run}']
log.to_csv(CLEAN / 'DQ_Log.csv', index=False)

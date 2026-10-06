# Methane forecast to 2030

**Script:** [`scripts/06_forecast_methane.py`](../scripts/06_forecast_methane.py)
**Output:** `data/clean/Fact_Forecast_Methane.csv` and `data/clean/Ref_Forecast_Fit.csv`
**Used on:** the Methane Forecast page of the report

## Why I needed it

EPA's reporting data stops at 2023. The question I cared about, whether the US is on course for the Global Methane Pledge (30% below 2020 by 2030), is about 2030. So I needed something to bridge the gap. This model projects US reported methane from 2024 to 2030, both in total and for each industry segment, and puts it next to the pledge path.

It answers three things:

1. Where is reported methane heading if the 2016-2023 trend continues?
2. Does that get to the pledge by 2030?
3. Which segments are doing the work, and which are lagging?

## Why a straight line

I tried to keep this as simple as the data allows.

- **The trend is clear.** Methane went from 255.9 Mt CO2e in 2016 to 204.3 Mt in 2023, and a straight line explains 89% of the variation (R² = 0.89).
- **There isn't much history.** 2016 is the first year all five segments report, so there are only eight consistent data points. That isn't enough for anything with more parameters.
- **It's easy to explain.** "Down about 8 Mt a year" is something you can say in one breath and defend.
- **The pieces add up.** The segment forecasts sum exactly to the total, so the stacked view and the total view never disagree.
- **Power BI just reads it.** The forecast is a plain CSV, so the report doesn't need R or Python visuals.

## How it flows

```
EPA GHGRP files 2011-2023
        │
        ▼
data/clean/Fact_Emissions.csv      (keep Gas_Group = "Methane", use CO2e_AR5_tCO2e)
        │
        ▼
06_forecast_methane.py
   1. sum methane by year and segment, convert to Mt
   2. keep 2016-2023 for fitting
   3. fit a straight line per segment and for the total
   4. project 2024-2030
   5. 90% prediction interval on the total
   6. pledge path from the 2020 actual
        │
        ├──► Fact_Forecast_Methane.csv   (actuals + forecast + pledge, 2011-2030)
        ├──► Ref_Forecast_Fit.csv        (slope, intercept, error, R² per fit)
        └──► one new row in DQ_Log.csv
        │
        ▼
Power BI: Methane Forecast page
```

## The maths

| Item | Formula |
|---|---|
| Trend line | `ŷ(t) = a + b·t`, ordinary least squares on t = 2016 to 2023 (n = 8) |
| Residual standard error | `s = sqrt( Σ(y − ŷ)² / (n − 2) )` |
| 90% prediction interval | `ŷ(t) ± 1.943 · s · sqrt( 1 + 1/n + (t − t̄)² / Σ(tᵢ − t̄)² )`, where 1.943 is the t value for 6 degrees of freedom |
| Pledge path | `P(t) = A₂₀₂₀ · (1 − 0.30 · (t − 2020) / 10)` for 2020 to 2030 |
| Gap to pledge | `ŷ(2030) − P(2030)`, where a negative number means on track |

Forecasts are floored at zero. The 90% interval is worked out on the total series itself rather than by adding up the segment intervals, because the segment errors aren't independent.

## Output tables

### Fact_Forecast_Methane

One row per year, segment and series. Actuals live in the same table as the forecast, so a single line chart can draw both.

| Column | Example | Meaning |
|---|---|---|
| `Year` | 2027 | 2011 to 2030 |
| `Segment` | Onshore Production | One of the five GHGRP segments, or `All Segments` for the total |
| `Series` | Forecast | `Actual`, `Forecast` or `Pledge` |
| `Methane_MtCO2e` | 173.1 | Mt CO2e, AR5 (methane = 28) |
| `Lower_90_MtCO2e` | 149.8 | Lower bound. Only filled for the total forecast |
| `Upper_90_MtCO2e` | 196.3 | Upper bound. Same rule |
| `Method` | OLS linear 2016-2023 | How the row was made |
| `Run_Date` | 2026-10-05 | When the script ran |

There are 122 rows: 68 actual, 43 forecast and 11 pledge. One of the forecast rows is a 2023 copy of the last actual value. It's only there so the dotted forecast line joins up with the solid one (`Method` = `Last actual (line join)`).

### Ref_Forecast_Fit

Fit statistics for each segment and the total: fit window, n, slope, intercept, residual standard error and R². It isn't used in any visual. It's there so you can check the fits.

## In Power BI

`Fact_Forecast_Methane` joins to the shared `Dim_Year` table on `Year`. That's what lets the year slicer on the forecast page go up to 2030. `Segment` and `Series` stay as plain columns, and the measures pick the right series themselves.

The measures are in the `7. Forecast` folder:

| Measure | Returns |
|---|---|
| `Methane Actual Mt` | Reported total (the solid line) |
| `Methane Forecast Mt` | Forecast total (the dotted line and the main card) |
| `Forecast 90% Low Mt` / `Forecast 90% High Mt` | The 90% range |
| `Pledge Path Mt` | The pledge line |
| `Last Actual Year` | 2023 |
| `Forecast Year` | The year picked on the page, or 2030 if none is picked |
| `Forecast Gap to Pledge Mt` | Forecast minus pledge |
| `Forecast Trend Mt per yr` | Yearly change in the forecast |
| `Forecast Change by Segment Mt` | Change from 2023 to the picked year, per segment |

## Results

| Year | Forecast (Mt CO2e) | 90% low | 90% high | Pledge path |
|---|---|---|---|---|
| 2023 (actual) | 204.3 | | | |
| 2024 | 197.7 | 179.0 | 216.5 | |
| 2025 | 189.5 | 169.4 | 209.6 | |
| 2026 | 181.3 | 159.7 | 202.9 | |
| 2027 | 173.1 | 149.8 | 196.3 | |
| 2028 | 164.8 | 139.9 | 189.8 | |
| 2029 | 156.6 | 129.8 | 183.4 | |
| 2030 | **148.4** | 119.7 | 177.1 | **162.8** |

The total is falling by 8.2 Mt a year (R² 0.89, residual error 7.6 Mt). In 2020 methane was 232.5 Mt, which makes the 2030 pledge target 162.8 Mt. The central forecast of 148.4 Mt is under it, but the top of the range (177.1 Mt) isn't. So on the current trend the pledge is likely, but not a sure thing.

| Segment | Slope (Mt/yr) | 2023 actual | 2030 forecast |
|---|---|---|---|
| Direct Emitter | −3.66 | 145.2 | 117.4 |
| Onshore Production | −3.00 | 30.7 | 12.8 |
| Gathering & Boosting | −0.98 | 14.1 | 7.6 |
| Local Distribution | −0.40 | 12.5 | 9.7 |
| Transmission Pipelines | −0.20 | 1.7 | 0.9 |
| **All Segments** | **−8.22** | **204.3** | **148.4** |

## Other approaches I considered

| Approach | Why I didn't use it |
|---|---|
| Power BI's built-in forecast (exponential smoothing) | Can't split by segment and can't be exported or checked. Fine as a visual sanity check, though. |
| ARIMA | Eight points isn't enough to estimate it properly. |
| Log-linear (constant % decline) | Gives almost the same answer over seven years and is harder to explain. It works as a sensitivity check. |
| Driver-based (activity × intensity) | Better for policy what-ifs, but it needs a production forecast such as EIA's Annual Energy Outlook as another input. This is the obvious next step. |
| Policy scenarios (OOOOb/c, the methane fee) | The timing of those rules is too uncertain right now. Better as a layer on top of this baseline later. |

## Limits

1. **Eight points is not a lot.** One odd year moves the slope. 2020 (COVID) is the obvious one.
2. **It assumes the trend just continues.** A straight line can't see new rules, price shocks or production growth.
3. **These are reported emissions, not actual emissions.** GHGRP covers facilities above 25,000 t CO2e and mostly uses engineering estimates. Measurement studies put real oil and gas methane higher, and the forecast inherits that gap.
4. **Some segment declines look too good.** Onshore production drops from 30.7 to 12.8 Mt by 2030 on a straight line. Read that as "if the trend holds", not as a prediction that policy will work.
5. **One GWP basis.** Everything is AR5 (methane = 28). On AR6 20-year values the levels would be about 2.9 times higher, though the shape of the trend wouldn't change much.
6. **It's not tied to the scenario inputs.** The EU exposure dropdowns don't feed into this forecast.

## Rerunning it

1. Add the new reporting year to `Fact_Emissions.csv` (rerun scripts 1 to 5 with the new EPA file).
2. Run `python scripts/06_forecast_methane.py`. Add `--fit-start` or `--fit-end` to change the window.
3. Refresh the report in Power BI Desktop.
4. Check the new fit in `Ref_Forecast_Fit.csv` and the new row in `DQ_Log.csv`.

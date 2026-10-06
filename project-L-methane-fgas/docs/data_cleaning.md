# Data cleaning notes

Most of the time on this project went into cleaning, not charts. Four agencies publish this data and each has its own layout, units and habits. This page covers the problems that mattered, the calls I had to make, and what I'd still double-check. All 76 issues are logged one per row in [`data/clean/DQ_Log.csv`](../data/clean/DQ_Log.csv), each with an example, the rows affected and the fix.

## The worst offenders

**EPA yearly summary files.** There are 13 workbooks and no two are quite the same. The header sits on row 4. The main sheet changed name in 2018 ("Direct Emitters" became "Direct Point Emitters"). Column names have trailing spaces. Oil and gas methane doesn't sit in the main sheet at all, but in four separate sheets. Every gas is its own wide column, mostly empty. I stacked all of it into one long table (facility × year × gas) and dropped 2010, which has a shorter layout and fewer industries reporting.

**Global warming potentials.** EPA reports everything as CO2e using the old AR4 values (methane = 25). I converted each gas back to tonnes and then out to AR5, AR6-100 and AR6-20, so you can pick a basis. HFC and PFC columns are blends of many gases, so you can't back out a single GWP. Those stay in AR4 and are flagged `GWP_Converted = FALSE`.

**Parent companies.** The same owner turns up in many spellings ("EXXON MOBIL CORP", "ExxonMobil Corp", "Exxon Mobile Corporation"). There were 11,591 distinct raw names. Standardising case, punctuation and legal suffixes got that down to 7,236, and a careful fuzzy match merged another 117, leaving 7,119 parents. They're all listed in `Parent_Fuzzy_Merges.csv` so they can be checked. Some facilities also have owner shares that add up to more than 100%. I kept them as reported and added `Ownership_Share_Sum` so you can normalise if you need to.

**Subpart W by source.** It came from Envirofacts as one file per year, every one of them called `CSV.csv`. Every facility gets a row for all 22 source categories whether they apply or not, so most rows are zero. EPA also renamed several categories between 2015 and 2018. I mapped the old names to the current ones (`Map_Source_Category_Legacy.csv`) and stripped the 40 CFR 98 citations out of the names. The longest one was 190 characters.

**EIA spreadsheets.** These are wide (one column per series, 76 of them in the exports file), with totals, subtotals and countries all mixed together. That makes double counting very easy. I turned them into long tables and flagged the total rows. Country and terminal names also needed tidying ("Korea" vs "South Korea", "FL" vs "Florida").

**Eurostat.** Aggregate partners like "Extra-EU" sat in the same column as countries. HS codes for HFCs changed in 2022, when 290341-290349 replaced part of 290339.

**Units.** By the end of the first pass I had MMcf, Mscf, kt, 100 kg, USD per Mcf, EUR and percentages on two different scales. Script 4 puts every table on one standard and writes the unit into the column name. The table is in [data/README.md](../data/README.md).

## Judgement calls

These are the places where I had to decide something rather than just reshape. If you're reusing the data, these are the ones to look at.

- **One 2019 gas volume was about 1,000 times too high.** A single facility's gas sales made 2019 US production look double every other year. Its oil volume and its other years were normal, so I divided by 1,000 and flagged it (`Gas_Value_Corrected`). That's my fix, not EPA's.
- **Emission type.** Subpart W doesn't say whether a source is vented, fugitive, flared or combustion. I assigned each of the 21 categories myself (`Dim_Source_Category.csv`).
- **Linking IEA measures to EPA sources.** IEA and EPA don't share names. I mapped the 16 IEA measures to EPA source categories (`Map_Abatement_Source_Category.csv`). "Replace with electric motor" and "Monitor and plug abandoned wells" are the shakiest matches.
- **HFC trade before 2022.** HS 290339 covers more than HFCs before the 2022 code change, so pre-2022 HFC import volumes are overstated.
- **Primary sector.** `Primary_Sector` in `Dim_Facility` is the first sector EPA lists, which isn't always the facility's main business. Use `Bridge_Facility_Sector` when you need an exact filter.
- **Regulation dates.** `Dim_Regulation` reflects where things stood in October 2026. The EU Methane Regulation import rules and the PFAS restriction are both still moving.

## How I checked it

- Facility methane in Subpart W matches EPA's own summary for 99.9% of facility-years.
- LNG terminal totals match EIA exactly. State gas production adds up to the US total.
- IEA countries add up to the IEA World and EU totals exactly.
- EPA-reported gas production covers 83-90% of EIA's US total each year (`Recon_SubpartW_vs_EIA_Production.csv`). That's about what you'd expect given the reporting threshold.
- Every number on the six dashboard pages was recalculated from the CSVs with a separate script, and they all matched the report to the rounding shown.
- The whole pipeline was rerun from the raw files into an empty folder. Every table came out identical.

## Known gaps

- Gathering and boosting and transmission pipelines only report from 2016, so 2015 totals aren't comparable with later years.
- Subpart W production only covers facilities above EPA's 25,000 tCO2e threshold.
- The IEA data is a single year (2025). Its abatement costs are net of the gas saved at IEA's assumed price.
- The original units (MMcf, kt and so on) only exist in the raw files. The gas price conversion is good to about 1%, because heat content varies a little from year to year.

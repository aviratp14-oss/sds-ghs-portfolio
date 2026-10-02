# Regulation Impact Projects (like the Wood Mackenzie EU Methane Regulation analysis)

The Wood Mackenzie piece follows one pattern: take a new regulation, combine **real trade/supply data**
with **compliance or emissions data per supplier**, and report **how much volume or cost is at risk
under different scenarios**. In their case, only 57% of EU gas imports and about 13% of crude imports
would be compliant on 1 January 2027 under the Default scenario.

Every project below uses that same pattern with free public data, and is a reporting project
(get data, clean it, analyze it, build a Power BI dashboard), in the same format as Projects A-E.
Numbers in the bullets are realistic placeholders. Swap in the real figures once built.

---

### Project J - EU Methane Regulation (Article 28) Import Exposure Analysis  (RECOMMENDED - directly mirrors the article)
*(best for: energy/commodities analyst, regulatory analyst (oil & gas), ESG/methane, energy consulting)*
- Combined EU gas, LNG and crude import volumes by origin country (Eurostat / UN Comtrade, 2024)
  with country-level methane intensity (IEA Global Methane Tracker) and operator reporting maturity
  (UNEP IMEO OGMP 2.0 Gold Standard list) to estimate the share of imports meeting EU MRV
  equivalence requirements.
- Built a Power BI scenario dashboard comparing a strict-enforcement case with a flexible case,
  showing that roughly 4 in 10 gas import volumes and most crude volumes were exposed, and ranking
  supplier countries by volume at risk and methane intensity.

**Job roles:** Energy Market Analyst, Regulatory Analyst (Oil & Gas / Energy), Methane / Emissions
Analyst, ESG Analyst (energy), Energy Transition Consultant, Commodity / Trade Analyst, Research
Analyst at energy consultancies (Wood Mackenzie, S&P Global Commodity Insights, Rystad, Kpler, ICIS).

**Data:** Eurostat Comext / UN Comtrade (HS 2709 crude, HS 2711 natural gas and LNG), IEA Global
Methane Tracker (free download), UNEP IMEO OGMP 2.0 member reports, EU Methane Regulation
(EU) 2024/1787 text.

---

### Project K - EU CBAM Cost Exposure for Indian Steel & Aluminium Exports
*(best for: carbon/climate policy, trade compliance, steel and metals, ESG consulting)*
- Mapped India's exports to the EU of CBAM-covered goods (iron and steel, aluminium, fertilisers,
  cement) by HS code and volume, and applied embedded-emission intensities (EU CBAM default values
  and published steel route intensities for BF-BOF vs DRI-EAF) to estimate embedded CO2.
- Built a Power BI dashboard estimating annual CBAM certificate cost at EU ETS carbon prices across
  price scenarios, and quantified how much a shift to lower-carbon routes (e.g. biocoke, scrap EAF)
  would reduce the exposure.

Why it fits you: links directly to your RWTH biocoke / green steel thesis and GHG accounting work.

**Job roles:** Carbon / Climate Policy Analyst, CBAM Compliance Analyst, Sustainability / ESG
Analyst, Trade Compliance Analyst, Decarbonisation Consultant (Big 4, ERM, Wood Mackenzie),
Sustainability Analyst at steel or metals companies (Tata Steel, JSW, Hindalco, ArcelorMittal).

**Data:** UN Comtrade or India's DGCI&S / TradeStat (exports to EU by HS chapter 72, 73, 76, 31,
2523), EU CBAM default values (European Commission), EU ETS price history (EEX / public sources),
worldsteel CO2 intensity data.

---

### Project L - Non-CO2 "Super-Pollutant" Emissions & Regulatory Exposure: Methane and F-Gases (combines old L + M)
*(best for: GHG reporting, emissions data, oil & gas and chemicals regulatory roles, ESG data - covers both
your energy and your chemicals/REACH experience in one project)*
- Cleaned and joined 10 years of EPA GHGRP facility data (2,000+ facilities) covering methane from oil
  & gas operations (Subpart W) and fluorinated gases from chemical production and industrial gas
  suppliers (Subparts L and OO), converting all gases to CO2e using IPCC GWP values under GHG
  Protocol methodology.
- Layered in trade data (Eurostat / UN Comtrade) for US LNG exports to the EU and EU imports of HFCs
  and fluoropolymers, and built a Power BI dashboard showing which operators, basins and product
  groups are most exposed to the EU Methane Regulation, the EU F-gas phase-down and the proposed EU
  PFAS restriction under REACH.

Why it works as one project: methane and F-gases are both high-GWP non-CO2 gases, both are reported
in the same EPA dataset, and both face new EU regulation that hits trade flows. One dataset, one
story, two regulatory angles (energy + chemicals).

**Job roles:** GHG / Emissions Reporting Analyst, EHS Data Analyst, ESG Data Analyst, Environmental
Compliance Analyst, Regulatory Affairs / Product Stewardship Analyst (chemicals, REACH), Methane
Program Analyst (oil & gas), Climate Data Analyst at data providers (MSCI, Sustainalytics, S&P
Trucost), Sustainability / Regulatory Intelligence Analyst at energy or chemicals consultancies.

**Data:** EPA FLIGHT / GHGRP Envirofacts (Subparts W, L, OO), EIA production data, Eurostat Comext /
UN Comtrade (HS 2711 natural gas/LNG, HS 2903.4x fluorinated hydrocarbons, HS 3904.61 PTFE,
3904.69 other fluoropolymers), EEA F-gas reporting data, ECHA PFAS restriction proposal, IPCC GWP
tables.

---

### Project N - EU ETS Carbon Cost Exposure for Refineries & Chemical Plants
*(best for: refining/petrochemicals, carbon markets, energy & chemicals analytics)*
- Extracted verified emissions and free allowance allocations for 500+ EU refineries and chemical
  installations from the EU Transaction Log (2013-2024), cleaning installation names, activity codes
  and parent company mappings.
- Built a Power BI dashboard quantifying each site's carbon cost gap (emissions minus free
  allocation) at current and projected EU ETS prices, and showing how the free-allocation phase-down
  alongside CBAM raises exposure by country and operator.

**Job roles:** Carbon Markets Analyst, Energy / Refining Analyst, Petrochemicals Market Analyst,
Climate Risk Analyst, Sustainability Analyst (refining / chemicals), Energy Transition Consultant.

**Data:** EU Transaction Log / EEA EU ETS data viewer (verified emissions and allocations per
installation), EU ETS price history.

---

## Which to use

| Target role | Use |
|---|---|
| Energy / commodities / oil & gas analyst, energy consultancies | J (or N) |
| Carbon policy, CBAM, sustainability, steel & metals | K |
| GHG reporting, emissions data, EHS data, chemical regulatory affairs / REACH | L (combined methane + F-gases) |
| Refining / petrochemicals, carbon markets | N |

Recommendation: **J** if you want the exact Wood Mackenzie style (topical: Article 28 is due 1 Jan 2027, with a one-year delay under discussion; easy
LinkedIn post), **K** if you want the strongest link to your thesis.

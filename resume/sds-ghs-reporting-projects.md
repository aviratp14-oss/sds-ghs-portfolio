# SDS / GHS Reporting Projects - for the PROJECTS section

These replace the earlier scripting-style ideas (sds-ghs-project-ideas.md). All four follow the same
shape as Projects A and D: get a real public dataset, clean it, analyze it, report it in Power BI.
They use the same letters F-I as the earlier draft, so pick from this file only.

Numbers in the bullets are realistic placeholders. Swap in the real figures once the project is built.

---

### Project F - OSHA Hazard Communication (HazCom) Violation Analysis & Compliance Dashboard  (RECOMMENDED)
*(best for: SDS/GHS, EHS compliance, product stewardship, regulatory reporting, compliance analytics)*
- Cleaned and joined 10 years of OSHA inspection and violation records (100,000+ rows) to isolate
  citations under the Hazard Communication Standard (29 CFR 1910.1200), standardising NAICS
  industry codes, establishment sizes and penalty amounts.
- Built a Power BI dashboard breaking down HazCom violations by sub-requirement (SDS availability,
  GHS labelling, written program, employee training), industry, state and penalty trend, showing that
  missing or outdated SDSs and training gaps drove most citations.

**Job roles:** EHS Analyst, EHS Data/Reporting Analyst, Regulatory Compliance Analyst, Product
Stewardship Analyst, SDS/Hazard Communication Specialist, Safety Compliance Coordinator, HSE
Consultant (Big 4 / ESG consulting), Compliance Data Analyst.

**Data:** OSHA enforcement data (enforcedata.dol.gov - inspection, violation and related tables).
The standard sub-paragraph (e.g. 1910.1200(g) = SDS, (f) = labels, (h) = training) is in the
violation table, so you can do the SDS vs label vs training split.

---

### Project G - Global Chemical Regulatory List Harmonisation & Screening Dashboard
*(best for: regulatory affairs, product stewardship, MDM/data governance in chemicals, SDS Section 15)*
- Harmonised four global regulatory lists (EPA TSCA Inventory, ECHA SVHC Candidate List, EU CLP
  Annex VI, California Prop 65) into a single CAS-keyed master table, resolving CAS formatting
  errors, duplicate entries, salts/hydrates and group entries across 80,000+ records.
- Built a Power BI screening dashboard reporting list overlap, harmonised GHS hazard class
  distribution and substances restricted in one region but unlisted in another, enabling
  portfolio-level regulatory status checks.

**Job roles:** Regulatory Affairs Specialist/Analyst (chemicals), Product Stewardship Analyst,
Regulatory Data Analyst, Chemical Compliance Specialist, Master Data Specialist (chemicals/EHS),
SAP EHS / Product Compliance Data Analyst, Regulatory Data Steward (distributors like Brenntag,
Univar, IMCD, Nordmann).

**Data:** EPA TSCA Inventory (CSV), ECHA Candidate List (downloadable table), CLP Annex VI
(ECHA Excel), OEHHA Prop 65 list (CSV).

---

### Project H - GHS Classification Consistency Audit Across Supplier Notifications
*(best for: data quality / audit-heavy JDs, SDS review, hazard classification, product safety)*
- Collected and cleaned GHS classification data for 500 commonly traded industrial chemicals from
  PubChem (aggregated ECHA C&L notifications), normalising hazard statements (H-codes),
  categories and signal words across inconsistent notifier formats.
- Quantified classification disagreement between suppliers for the same substance, finding that
  roughly 1 in 3 chemicals had conflicting hazard categories, and built a Power BI audit report
  tracing each mismatch to the hazard class and supplier group driving it.

**Job roles:** SDS Reviewer/Author (junior), Hazard Communication Specialist, Product Safety
Analyst, Regulatory Data Quality Analyst, Data Quality Analyst (chemicals/EHS), Product Stewardship
Associate, Technical Data Specialist (chemical distribution / data providers like 3E, UL, Sphera).

**Data:** PubChem GHS Classification section (free PUG-View API or bulk download per compound list).

---

### Project I - Hazardous Materials Transport Incident Analysis (Dangerous Goods)
*(best for: DG/transport compliance, logistics/supply chain EHS, SDS Section 14)*
- Cleaned and analyzed 10 years of PHMSA hazardous materials incident records (150,000+ rows),
  standardising UN numbers, hazard classes, packaging types and transport modes.
- Built a Power BI dashboard reporting incidents, damages and causes by DG hazard class, mode
  (highway, rail, air, water) and failure point, highlighting packaging and loading failures as the
  leading root causes.

**Job roles:** Dangerous Goods / Hazmat Compliance Specialist, Transport Compliance Analyst,
Logistics EHS Analyst, Supply Chain Compliance Analyst, Trade & DG Compliance Coordinator (chemical
distributors, 3PLs, freight forwarders), EHS Analyst (logistics).

**Data:** PHMSA Hazmat Incident Report data (phmsa.dot.gov, downloadable).

---

## Which to use

| Target role | Use |
|---|---|
| EHS / compliance analyst, safety reporting | F |
| Regulatory affairs, product stewardship, chemical MDM | G |
| SDS review/authoring, hazard communication, data quality | H (or F) |
| Dangerous Goods / logistics compliance | I |

Recommendation: build F first (most direct SDS/GHS link and easy to explain in interviews), with G as
the alternate for regulatory-data roles at chemical distributors.

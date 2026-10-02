# SDS / GHS Project Ideas - for the PROJECTS section

Why a project is needed: your SDS/GHS story today rests on Project Nordmann (work) plus the Knowde training.
Regulatory JDs (SDS Author, Product Stewardship, Regulatory Affairs, EHS Data) screen for hands-on
classification, SDS data handling, regulatory list screening and regulatory change work. A project
gives you proof of the classification side that the training alone does not.

Each idea below is written in the same format as Projects A-E so it can be pasted straight into the
reference file. They are scoped so you can actually build them with public data (sources listed).

---

### Project F - SDS Data Extraction & Regulatory Screening Pipeline  (RECOMMENDED - best overall fit)
*(best for: SDS authoring/coordination, product stewardship, regulatory data, EHS data management,
regulatory + data hybrid roles)*
- Built a Python pipeline that parsed 150+ supplier SDS PDFs into a structured database
  (Sections 1, 2, 3, 14, 15), normalising hazard statements, CAS numbers and transport data
  across EU CLP, OSHA HazCom and WHMIS formats.
- Screened every CAS number against the ECHA SVHC Candidate List, CLP Annex VI, TSCA Inventory and
  California Prop 65, and flagged internal inconsistencies (e.g. Section 2 hazard classes not
  matching Section 14 transport class) in a Power BI compliance dashboard.

Why it fits you: it mirrors Project Nordmann, reuses your PDF-to-MDM pipeline and GenAI auditing
skills, and hits the most ATS keywords (SDS, GHS, CLP, HazCom, SVHC, TSCA, Prop 65, DG).

### Project G - GHS Mixture Classification Engine (CLP / HazCom calculation method)
*(best for: SDS Author, Regulatory Specialist, hazard classification / toxicology-adjacent roles)*
- Built a Python classification engine that derived GHS hazard classes for mixtures from component
  data, applying the ATEmix formula for acute toxicity, additivity rules for skin/eye corrosion,
  and the summation method with M-factors for aquatic chronic hazard.
- Auto-generated signal words, H/P statements and pictograms (Section 2 / label elements) and
  validated outputs against 25 published SDSs, matching the supplier classification in most cases
  and documenting the root cause of each mismatch.

Why it fits you: it proves you can classify, not just read SDSs. This is the strongest pick for pure
SDS authoring roles, where interviewers often ask how you would classify a mixture.

### Project H - Regulatory Change Impact Assessment: EU CLP New Hazard Classes & OSHA HazCom 2024
*(best for: product stewardship, regulatory change management, MOC/NOC, compliance program roles)*
- Assessed a 60-substance chemical portfolio against the new EU CLP hazard classes (endocrine
  disruptors, PBT/vPvB, PMT/vPvM) and the 2024 OSHA HazCom update, identifying which SDSs and
  labels required revision and prioritising them by compliance deadline.
- Built a Power BI regulatory change tracker mapping each affected product to its SDS sections,
  label changes and Management of Change (MOC) actions.

Why it fits you: very timely (the CLP new classes applied to new mixtures from May 2026, and the
HazCom deadlines run through 2026-2027), and it uses your MOC/NOC and dashboard skills.

### Project I - Dangerous Goods Transport Classification Tool (SDS Section 14)
*(best for: DG / logistics compliance, chemical distribution, transport safety roles)*
- Built a rules-based tool deriving UN number, proper shipping name, transport hazard class and
  packing group from GHS classification data, and comparing requirements across ADR, IMDG and IATA
  including marine pollutant and limited-quantity rules.

Why it fits you: niche, but strong for distributors (Brenntag, Univar, Nordmann-type employers).
Smaller scope - works well folded into F or G as an extra bullet.

---

## Recommendation
- Add **F** as your default SDS/GHS project (closest to your real work, most keywords).
- Add **G** as the alternate for pure SDS-authoring JDs.
- H is a good third option for product stewardship / regulatory affairs roles.

## Public data sources to actually build these
- ECHA C&L Inventory and CLP Annex VI harmonised classification list (ECHA website, downloadable)
- ECHA SVHC Candidate List (downloadable)
- EPA TSCA Chemical Substance Inventory (CSV download)
- California OEHHA Prop 65 list (CSV download)
- PubChem GHS classification data (free API)
- Supplier SDS PDFs: Sigma-Aldrich, Fisher Scientific, and distributor websites (public)
- UN Model Regulations Dangerous Goods List (for Project I)

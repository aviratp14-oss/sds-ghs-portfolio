# The three business problems

This is the long version of the project: for each problem, what was asked, what I did, what the numbers say, and what I'd change in SAP so it doesn't happen again. All figures come from the cleaned tables in [`data/clean/`](../data/clean/) and match the dashboard.

## The business in one picture

```
   Plant 1010 - Pasadena, TX                         Plant 1020 - Lake Charles, LA
   ---------------------------------                 ---------------------------------
   Propylene -> n-Butanal -> 2-EH (C) ---X--->       2-EH* + Acrylic acid -> 2-EH Acrylate (D)
                              |    (never shipped)   n-Butanol* -> Butyl Acrylate, Butyl Acetate
                              v                      Glycol ethers, acetates, traded solvents
   2-EH + Terephthalic acid -> DOTP (A)
   Isononanol + Phthalic anh. -> DINP (B)            * bought from outside suppliers under a
                                                       second material number
```

The company sells about $110M a year of chemicals to 160 customers in PVC, coatings, adhesives, inks, pharma and distribution.

---

## Problem 1: the priority product is losing to its cheaper substitute

### Problem statement
DOTP (Chemical A) and DINP (Chemical B) are both PVC plasticizers with the same end use. DOTP is the priority product: it earns **$0.62 margin per kg against $0.24 for DINP**. Even so, DINP has been taking over. Management wanted to know how fast, which customers moved, and what it's costing.

### What I did
- Joined sales order lines to the material master and standard cost history, so every line has a margin at standard.
- Tracked DOTP's share of combined DOTP + DINP volume by quarter.
- Classified every plasticizer customer by comparing their DINP share in their first 12 months with their last 12 months: Loyal to A, Loyal to B, Mixed, or Switched A to B.
- Compared discounts on DINP by sales rep.

### What I found
- DOTP's share fell from **76% in 2022 to 21% in 2026**. DINP overtook it in early 2025.
- **21 of 55 plasticizer customers switched** from DOTP to DINP. Nine stayed loyal to DOTP, 13 bought mostly DINP from the start, and 12 buy a mix.
- The margin lost on their DINP volume (compared with selling them DOTP) is **$3.9M since 2022**, and $1.7M of it was in 2025 alone.
- Two sales reps give DINP an average **8% discount, against about 3% for everyone else**. My read is that this is an incentive problem, not a market one: if reps are paid on volume, the cheaper product is the easier sale.

### How to prevent it
1. **Pay reps on margin, not volume.** A volume bonus rewards pushing the lower-margin product.
2. **Set discount limits per product.** Discounts above a set level on the offset product should need approval (an SAP pricing condition with an approval workflow).
3. **Watch the mix monthly.** A product-mix KPI with an alert when the priority product's share drops below a threshold (say 60%) would have flagged this in 2023, not 2025.
4. **Give sales a clear story for the priority product.** Phthalate-free DOTP has a regulatory advantage. Sales teams need that pitch, or price wins every time.

---

## Problem 2: buying a chemical the company already makes

### Problem statement
Plant 1010 makes 2-EH (Chemical C). Plant 1020 needs 2-EH to make 2-EH acrylate (Chemical D). Plant 1020 didn't know the company made it, so it bought 2-EH from outside suppliers every month. At the same time, plant 1010 had more 2-EH than it needed and sold the surplus to a trader at a discount.

### Why it happened (root cause)
This is a **master data problem**, not a purchasing one:
- In 2021 a plant 1020 buyer created a new raw material record, "OCTANOL 2-ETHYL TECH GRADE" (10000209), instead of extending the existing 2-ethylhexanol record (30000201) to their plant.
- The descriptions don't match, so nobody searching by name would find the duplicate.
- The CAS number was stored without dashes (`104767` instead of `104-76-7`), so even a CAS lookup missed it.
- With two material numbers, MRP at plant 1020 never saw the stock at plant 1010.

The same thing happened twice more on a smaller scale: n-butanol bought as "BUTAN-1-OL", and PM bought as "CLEANING SOLVENT - GLYCOL ETHER".

### What I did
- Cleaned the CAS numbers on every material (added the missing dashes, trimmed spaces, removed prefixes and notes) and checked each one against the CAS check-digit rule.
- Matched bought materials to made materials on the cleaned CAS number. This found **3 duplicate pairs**.
- For each pair and month, compared:
  - what was bought outside and the price paid
  - our own cost: standard cost plus $0.04/kg freight between the plants
  - how much we could have supplied ourselves: surplus sold to the trader, plus stock above one month of our own sales
- Avoidable cost = the volume we could have covered x (purchase price - our cost).

### What I found
- **$10.2M spent in 2025** buying chemicals the company already makes.
- **$2.1M of that was avoidable in 2025, and $10.6M since 2022.** 2-EH is almost all of it.
- In 2025 plant 1020 bought **2,419 t of 2-EH** at about $1.98/kg, while plant 1010 sold **3,946 t of its own 2-EH to a trader at 26% below list**. Its own cost was about $1.18/kg including freight.
- The problem got worse as Problem 1 grew: less DOTP means less 2-EH used in-house, so more surplus.

### How to prevent it
1. **Make CAS number a mandatory, validated field** for every chemical material. Enforce the format and the check digit when the record is created.
2. **Check for duplicates before a new material is created.** A new chemical record with the same CAS as an existing one should be blocked, and the request routed to "extend to plant" instead.
3. **Extend, don't duplicate.** One material number per chemical, extended to every plant that uses it, with a special procurement key for stock transfer between plants.
4. **Run a monthly make-vs-buy report.** Any purchase order for a material whose CAS number matches something we produce gets flagged to the buyer and the planner.
5. **Have one data owner for material master changes.** Plant-level users shouldn't be able to create chemical masters without a central MDM review.

---

## Problem 3: customers quietly slowing down

### Problem statement
Some customers stop ordering without saying anything. A simple "no order in 90 days" rule doesn't work, because a customer who orders weekly is in trouble long before 90 days, while a quarterly buyer isn't.

### What I did
- Worked out each customer's normal reorder gap: the median number of days between their orders.
- Compared the days since their last order (as of 30 Sep 2026) with their own normal gap:
  - **At risk:** more than 2x their usual gap, or their last three gaps running at more than 2x their usual
  - **Lapsed:** more than 3x their usual gap (at least 120 days)
- Estimated each customer's annual revenue and linked it to their plasticizer profile from Problem 1.
- Left the spot trader and returns out.

### What I found
- Of 160 regular customers, **128 are active, 8 are at risk and 24 have lapsed** since 2022 (4 of them in the last 12 months).
- **$2.3M a year is at risk** from the 8 at-risk customers, and **$5.0M a year has been lost** to the 4 recent lapses.
- Customers who switched to DINP have the **highest at-risk rate (14%)**. Loyal DOTP buyers churn the least: none are at risk, and 11% have lapsed, against 24% of switchers who are at risk or lapsed. Once a customer buys on price, they keep shopping on price.

### How to prevent it
1. **Give reps a weekly "call first" list:** at-risk customers sorted by revenue, from the dashboard.
2. **Alert on the customer's own rhythm,** not a fixed number of days.
3. **Review lost customers.** Ask lapsed customers why they left, and record the reason in SAP (CRM activity) so it can be reported.
4. **Protect the loyal DOTP base.** These customers are the least likely to leave and the most profitable, so they're worth keeping on supply agreements.

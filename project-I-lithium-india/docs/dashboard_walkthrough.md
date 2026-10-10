# Dashboard walkthrough

The report has four pages, and they all work the same way. At the top is a headline that states the finding in a sentence, with a line under it saying what the chart shows. Below that is one big chart on the left and three short "things to know" on the right. The slicers sit under the side panel.

The headline and side numbers aren't typed in. They're DAX measures drawn as SVG images, so they change with the slicers. All numbers below are for the Base case, no new policy, and India able to reach 3% of world supply.

## Slicers

| Slicer | What it does |
|---|---|
| Scenario | Low, Base or High clean-energy adoption |
| Policy lever | None, one of the four levers, or all four together |
| World share | India's accessible share of world lithium supply, 1% to 6%. Imports, the shortfall and the share of EV and storage demand met are recalculated live in DAX |

The slicers are synced, so a choice on one page carries to the others. Page 4 swaps the lever slicer for a year slicer, because that page compares the levers side by side.

The tabs at the top are page buttons. In Power BI Desktop hold Ctrl and click; in the Power BI service a normal click works.

## Page 1: Overview

**Headline:** "India will need 16 times more lithium by 2040. From 2034, there isn't enough for EVs and storage."

**Chart:** two lines from 2025 to 2040, demand and the supply India can reach. The gap opens where they cross.

**Three things to know:**

- **38%** of India's lithium in 2025 went to phones, laptops, grease, glass and defence, not clean energy. Worldwide it's 12%.
- **75%** of EV and storage demand can be met in 2040. Phones and grease are served first because they can pay more.
- **Overseas assets** is the biggest single fix. It closes 50 of the 63 kt gap in 2040.

Try the High case: the gap opens in 2028 and growth to 2040 is 26 times. Try 5% world share: the Base case has enough and the side panel says so.

## Page 2: Who uses it

**Headline:** "In 2025, 38% of India's lithium went to phones, grease and other non-energy uses. By 2040, EVs take 85%."

**Chart:** 100% stacked columns of demand share by sector, 2025 to 2040: EVs, grid storage, electronics, defence and industry.

**Three things to know:**

- **1.2 kt** a year goes into phones assembled in India for export. That lithium leaves the country and never comes back for recycling.
- **1.1 kt** goes into lubricating grease. 77% of the lithium hydroxide behind it came from Russia in 2023.
- **12%** is the non-energy share worldwide (USGS). India is higher because its EV fleet is still small. It drops to 5% by 2040.

## Page 3: Where it comes from

**Headline:** "Recycling becomes India's biggest home source of lithium, but only from the mid-2030s."

**Chart:** stacked columns of the supply India can reach (recycling, mining in India, overseas mines, import cap), with demand as a line on top. Where the line climbs above the columns, there's a shortfall.

**Three things to know:**

- **5%** is the recycled content India's own scrap can supply in 2030. The battery rules ask for 20%. Most batteries sold today retire after 2032.
- **18 kt** is all the lithium in Reasi, India's only proven find (583 ppm, Lok Sabha 2024). That's about seven weeks of 2035 demand in the Base case.
- **77%** of India's lithium is still imported in 2040, down from 97% in 2025.

## Page 4: What closes the gap

**Headline:** "Buying into overseas mines closes most of the gap. Mining at home closes only 3.4 kt of it."

The headline picks the lever that closes the most and checks whether it closes at least half the gap. If it doesn't (in the High case overseas assets close 50 of 155 kt), it says "closes more of the gap than any other step" instead. If there's no gap with the chosen settings, it says so and suggests trying the High case or a lower share.

**Chart:** horizontal bars of the gap left in the chosen year with each lever. The "No new policy" bar is the starting gap; shorter bars are better.

**Side panel:** India's value chain today, from exploration to recycling, with where India stands at each step. Below it, a short note: India is missing almost every step between the mine and the cell. Lithium is only about $5 of each kWh of battery, so the money is in cathode and cell making, not in mining.

## How the numbers tie together

- "Supply India can reach" = recycling + mining in India + overseas mines + India's share of world supply.
- Non-energy uses are served first. "EV and storage demand met" = whatever is left after them, divided by EV and storage demand, capped at 100%.
- At 3% world share every number on the pages matches `data/clean/Fact_Balance.csv`. At any other share the DAX recalculates the import cap from `Global_Supply_t_LCE`, so the CSV and the dashboard will differ, as they should.

# Data analytics portfolio: chemicals, energy and regulation

Hi, I'm Avirat Puranik. I'm a data analyst who works where chemicals, energy and regulation meet.

At Knowde I'm a PoC Specialist in Data and Sales Operations. I build data proofs of concept for enterprise customers. Day to day that means pulling messy ERP and supplier data (material masters, vendor records, order-to-cash) into one governed master data model, writing the mapping rules that keep it consistent, and building SQL, Python and Power BI tooling to check it. One example is an automated audit covering 20,000+ data points, which cut manual review time in half. I also handle the regulatory side of product data: SDS normalisation, GHS hazard classification, and inventory status under REACH, TSCA and DSL.

Before Knowde I did an M.Tech at IIT (ISM) Dhanbad. I spent seven months at RWTH Aachen in Germany as a DAAD scholar, developing a biocoke fuel for blast furnaces and using regression and emissions accounting to compare it with conventional coke.

This repo is for side projects built on public or simulated business data. Each one starts with a real question, usually about what a regulation, a market shift or a business problem means in numbers. From there I clean the data, model it and turn it into a dashboard.

Each project lives in its own folder with its own README, data, scripts and dashboard.

## Projects

| Project | What it looks at | Tools |
|---|---|---|
| [Methane and F-gas emissions vs EU rules](project-L-methane-fgas/) | How much methane and F-gas US facilities report, where it is heading to 2030, and how exposed US LNG exports are to the new EU Methane Regulation | Excel, Python (pandas), Power BI, DAX |
| [Chemical portfolio analytics on SAP data](project-C-sap-chemical-portfolio/) | A chemical maker's SAP sales, purchasing and production data: why its priority plasticizer is losing to a cheaper one, why one plant buys a chemical another plant makes, and which customers are quietly drifting away | SAP S/4HANA data model, Excel, Python (pandas), Power BI, DAX |
| [Competing demand for lithium in India](project-I-lithium-india/) | How much lithium India will need from 2025 to 2040 across 17 uses, how much it can realistically get, and what happens to EVs and grid storage when phones and grease are served first | Python, Excel, Power BI, DAX, policy brief |

More to come.

## Licence

Code and write-ups are MIT licensed (see [LICENSE](LICENSE)). Project L uses public data from EPA, EIA, Eurostat and the IEA, and each source keeps its own terms. Project C runs on simulated SAP data that I generated myself, plus one public price index from FRED. Project I uses public sources (USGS, UN Comtrade via WITS, CEA, IESA, IDC, IEA, Lok Sabha answers and others) plus my own stated assumptions. The details are in each project's `data/README.md`.

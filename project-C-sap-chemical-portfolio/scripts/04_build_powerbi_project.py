# Project C: builds the Power BI project (PBIP: TMDL semantic model + PBIR report) from the clean CSVs.
# Look: SAP Fiori style (shell bar, left navigation, white KPI tiles, blue/red charts). 4 pages.
# Open ProjectC.pbip in Power BI Desktop, set the DataFolder parameter to the folder holding the CSVs, refresh, then File > Save as .pbix.
import json, shutil, uuid, pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CLEAN = BASE / 'data' / 'clean'
OUT = BASE / 'dashboard' / 'ProjectC'
THEME = Path(__file__).resolve().parent / 'assets' / 'CY24SU10.json'
DEFAULT_FOLDER = 'C:\\ProjectC\\data\\clean\\'
SM, RP = 'ProjectC.SemanticModel', 'ProjectC.Report'

def tag(*k): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'projectC/' + '/'.join(k)))
def q(name):  # TMDL object name, quoted when needed
    return name if name.replace('_', '').isalnum() and name[0].isalpha() else "'" + name.replace("'", "''") + "'"

# ---------------- semantic model ----------------
TABLES = ['Dim_Material', 'Dim_Customer', 'Dim_Sales_Rep', 'Dim_Supplier', 'Dim_Plant', 'Dim_Date',
          'Fact_Sales', 'Fact_Purchases', 'Fact_Production', 'Fact_Stock', 'Fact_BOM', 'Fact_Std_Cost',
          'Fact_Make_vs_Buy', 'Map_Make_vs_Buy', 'Fact_Customer_Health', 'Map_Customer_Duplicates', 'Ref_PPI']
TEXT_COLS = {'Sales_Doc', 'Customer_Id', 'Material_Id', 'Plant', 'Supplier_Id', 'Sales_Rep_Id', 'Home_Plant', 'Same_CAS_As',
             'Bought_Material_Id', 'Made_Material_Id', 'Buying_Plant', 'Making_Plant', 'PO_Number', 'Production_Order',
             'Parent_Material_Id', 'Component_Material_Id', 'Duplicate_Customer_Id', 'Master_Customer_Id', 'CAS_No', 'CAS_Raw'}
DATE_COLS = {'Date', 'Month', 'Month_Start', 'Order_Date', 'Billing_Date', 'PO_Date', 'Delivery_Date', 'Start_Date', 'Finish_Date',
             'Customer_Since', 'Created_On', 'First_Order_Date', 'Last_Order_Date'}
NO_SUM = {'Year', 'Month_No', 'Item', 'List_Price_USD_per_kg', 'Discount_Share', 'Net_Price_USD_per_kg', 'Std_Cost_USD_per_kg',
          'Price_USD_per_kg', 'Buy_Price_USD_per_kg', 'InHouse_Cost_USD_per_kg', 'Component_kg_per_kg', 'PPI_Basic_Organic_Chemicals_Index',
          'Orders', 'Median_Reorder_Gap_days', 'Recent_Reorder_Gap_days', 'Days_Since_Last_Order', 'Overdue_Ratio',
          'Annual_Revenue_USD', 'Revenue_at_Risk_USD', 'Lost_Revenue_USD', 'Revenue_Exposure_USD', 'B_Share_First_12m', 'B_Share_Last_12m'}
FMT = {'Revenue_Exposure_USD': '\\$#,##0', 'Annual_Revenue_USD': '\\$#,##0', 'Median_Reorder_Gap_days': '0', 'Recent_Reorder_Gap_days': '0'}
MTYPE = {'int64': 'Int64.Type', 'double': 'type number', 'boolean': 'type logical', 'string': 'type text', 'dateTime': 'type date'}

def col_types(csv):
    d = pd.read_csv(CLEAN / csv, low_memory=False, dtype={c: str for c in TEXT_COLS})
    out = {}
    for c, t in d.dtypes.items():
        t = str(t)
        out[c] = ('string' if c in TEXT_COLS else 'dateTime' if c in DATE_COLS else 'int64' if t == 'int64'
                  else 'double' if t == 'float64' else 'boolean' if t == 'bool' else 'string')
    return out

def column_block(table, c, t, hidden=False, fmt=None, source=None):
    summ = 'none' if (c in NO_SUM or t in ('string', 'boolean', 'dateTime')) else 'sum'
    fmt = fmt or FMT.get(c) or ('0' if t == 'int64' else 'yyyy-mm-dd' if t == 'dateTime' else None)
    lines = [f'\tcolumn {q(c)}', f'\t\tdataType: {t}']
    if fmt: lines.append(f'\t\tformatString: {fmt}')
    if hidden: lines.append('\t\tisHidden')
    lines += [f'\t\tlineageTag: {tag(table, c)}', f'\t\tsummarizeBy: {summ}', f'\t\tsourceColumn: {source or c}', '',
              '\t\tannotation SummarizationSetBy = Automatic', '']
    return lines

def m_block(table, body):
    lines = [f'\tpartition {q(table)} = m', '\t\tmode: import', '\t\tsource =']
    lines += ['\t\t\t\t' + l for l in body.strip('\n').split('\n')]
    return lines + ['', '\tannotation PBI_ResultType = Table', '']

def csv_m(csv, types):
    tl = ', '.join(f'{{"{c}", {MTYPE[t]}}}' for c, t in types.items())
    return f'''let
    Source = Csv.Document(File.Contents(DataFolder & "{csv}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{{tl}}}, "en-US")
in
    Typed'''

files = {}
for t in TABLES:
    types = col_types(f'{t}.csv')
    L = [f'table {q(t)}', f'\tlineageTag: {tag(t)}', '']
    for c, ty in types.items(): L += column_block(t, c, ty)
    L += m_block(t, csv_m(f'{t}.csv', types))
    files[t] = L

# ---------------- measures ----------------
MS = []
def meas(folder, name, expr, fmt, cat=None):
    global MS
    lines = expr.strip('\n').split('\n')
    if len(lines) == 1: MS.append(f'\tmeasure {q(name)} = {lines[0]}')
    else: MS += [f'\tmeasure {q(name)} =', *['\t\t\t' + l for l in lines]]
    MS += [f'\t\tformatString: {fmt}', f'\t\tdisplayFolder: {folder}', f'\t\tlineageTag: {tag("m", name)}'] + ([f'\t\tdataCategory: {cat}'] if cat else []) + ['']

DOTP, DINP, EH_BOUGHT, EH_MADE, SPOT = '30000101', '30000102', '10000209', '30000201', '1009990'
def yr(base): return f'CALCULATE([{base}], REMOVEFILTERS(Dim_Date), Dim_Date[Year] = y)'
def py(base): return f'CALCULATE([{base}], REMOVEFILTERS(Dim_Date), Dim_Date[Year] = y - 1, Dim_Date[Month_No] <= lm)'

S = '1. Sales'
meas(S, 'Revenue USD', 'SUM(Fact_Sales[Net_Value_USD])', '\\$#,##0')
meas(S, 'Revenue M', 'DIVIDE([Revenue USD], 1e6)', '\\$#,##0.0')
meas(S, 'Margin USD', 'SUM(Fact_Sales[Margin_USD])', '\\$#,##0')
meas(S, 'Gross Margin %', 'DIVIDE([Margin USD], [Revenue USD])', '0.0%')
meas(S, 'Volume kt', 'DIVIDE(SUM(Fact_Sales[Qty_kg]), 1e6)', '#,##0.0')
meas(S, 'Active Customers', 'CALCULATE(DISTINCTCOUNT(Fact_Sales[Customer_Id]), Fact_Sales[Is_Return] = FALSE(), Dim_Customer[Customer_Type] = "Regular")', '#,##0')
meas(S, 'Selected Year', '''IF(
    HASONEVALUE(Dim_Date[Year]),
    VALUES(Dim_Date[Year]),
    YEAR(CALCULATE(MAX(Fact_Sales[Order_Date]), REMOVEFILTERS()))
)''', '0')
meas(S, 'Last Month In Year', '''-- last month with sales in the selected year, so a part year is compared with the same months a year earlier
VAR y = [Selected Year]
RETURN MONTH(CALCULATE(MAX(Fact_Sales[Order_Date]), REMOVEFILTERS(), Dim_Date[Year] = y))''', '0')
meas(S, 'Prior Period Label', '''VAR y = [Selected Year]
VAR lm = [Last Month In Year]
RETURN IF(lm = 12, FORMAT(y - 1, "0"), "Jan-" & FORMAT(DATE(y - 1, lm, 1), "mmm") & " " & FORMAT(y - 1, "0"))''', 'General')
meas(S, 'Revenue M (Year)', f'VAR y = [Selected Year]\nRETURN {yr("Revenue M")}', '\\$#,##0.0')

P = '2. Product mix'
meas(P, 'DOTP kg', f'CALCULATE(SUM(Fact_Sales[Qty_kg]), Fact_Sales[Material_Id] = "{DOTP}")', '#,##0')
meas(P, 'DINP kg', f'CALCULATE(SUM(Fact_Sales[Qty_kg]), Fact_Sales[Material_Id] = "{DINP}")', '#,##0')
meas(P, 'DOTP Share %', 'DIVIDE([DOTP kg], [DOTP kg] + [DINP kg])', '0%')
meas(P, 'DINP Share %', 'DIVIDE([DINP kg], [DOTP kg] + [DINP kg])', '0%')
meas(P, 'DOTP Margin per kg', f'DIVIDE(CALCULATE(SUM(Fact_Sales[Margin_USD]), Fact_Sales[Material_Id] = "{DOTP}"), [DOTP kg])', '\\$0.00')
meas(P, 'DINP Margin per kg', f'DIVIDE(CALCULATE(SUM(Fact_Sales[Margin_USD]), Fact_Sales[Material_Id] = "{DINP}"), [DINP kg])', '\\$0.00')
meas(P, 'Margin Gap per kg', '-- DOTP minus DINP margin per kg over all data, so the gap does not move with the filters\nCALCULATE([DOTP Margin per kg] - [DINP Margin per kg], REMOVEFILTERS())', '\\$0.00')
meas(P, 'Switched Customers', 'CALCULATE(COUNTROWS(Dim_Customer), Dim_Customer[Plasticizer_Profile] = "Switched A to B")', '#,##0')
meas(P, 'Plasticizer Customers', 'CALCULATE(COUNTROWS(Dim_Customer), Dim_Customer[Plasticizer_Profile] <> "No plasticizer" && Dim_Customer[Plasticizer_Profile] <> "" && NOT ISBLANK(Dim_Customer[Plasticizer_Profile]))', '#,##0')
meas(P, 'Margin Lost to Switching M', '''-- DINP bought by customers who switched, times what the same kg would have earned as DOTP
DIVIDE(CALCULATE([DINP kg], Dim_Customer[Plasticizer_Profile] = "Switched A to B") * [Margin Gap per kg], 1e6)''', '\\$#,##0.0')
meas(P, 'DINP Avg Discount %', f'CALCULATE(AVERAGE(Fact_Sales[Discount_Share]), Fact_Sales[Material_Id] = "{DINP}", Fact_Sales[Is_Return] = FALSE())', '0.0%')

M = '3. Internal sourcing'
meas(M, 'Spend on Own Chemicals M', 'DIVIDE(SUM(Fact_Make_vs_Buy[Spend_USD]), 1e6)', '\\$#,##0.0')
meas(M, 'Avoidable Cost M', 'DIVIDE(SUM(Fact_Make_vs_Buy[Avoidable_Cost_USD]), 1e6)', '\\$#,##0.00')
meas(M, 'Avoidable Cost M (Year)', f'VAR y = [Selected Year]\nRETURN {yr("Avoidable Cost M")}', '\\$#,##0.00"M"')
meas(M, '2-EH Bought t', f'CALCULATE(DIVIDE(SUM(Fact_Make_vs_Buy[Bought_kg]), 1000), REMOVEFILTERS(Map_Make_vs_Buy), Fact_Make_vs_Buy[Bought_Material_Id] = "{EH_BOUGHT}")', '#,##0')
meas(M, '2-EH Surplus Sold t', f'CALCULATE(DIVIDE(SUM(Fact_Make_vs_Buy[Surplus_Sold_Spot_kg]), 1000), REMOVEFILTERS(Map_Make_vs_Buy), Fact_Make_vs_Buy[Bought_Material_Id] = "{EH_BOUGHT}")', '#,##0')
meas(M, 'Duplicate Material Pairs', 'CALCULATE(COUNTROWS(Map_Make_vs_Buy), REMOVEFILTERS(Map_Make_vs_Buy))', '0')
meas(M, 'Spot Discount vs List %', f'''-- price the trader paid for our 2-EH vs the list price regular customers were quoted
VAR TraderPrice = DIVIDE(
    CALCULATE(SUM(Fact_Sales[Net_Value_USD]), Fact_Sales[Customer_Id] = "{SPOT}", Fact_Sales[Material_Id] = "{EH_MADE}", Fact_Sales[Is_Return] = FALSE()),
    CALCULATE(SUM(Fact_Sales[Qty_kg]), Fact_Sales[Customer_Id] = "{SPOT}", Fact_Sales[Material_Id] = "{EH_MADE}", Fact_Sales[Is_Return] = FALSE()))
VAR ListPrice = DIVIDE(
    CALCULATE(SUMX(Fact_Sales, Fact_Sales[Qty_kg] * Fact_Sales[List_Price_USD_per_kg]), Fact_Sales[Customer_Id] <> "{SPOT}", Fact_Sales[Material_Id] = "{EH_MADE}", Fact_Sales[Is_Return] = FALSE()),
    CALCULATE(SUM(Fact_Sales[Qty_kg]), Fact_Sales[Customer_Id] <> "{SPOT}", Fact_Sales[Material_Id] = "{EH_MADE}", Fact_Sales[Is_Return] = FALSE()))
RETURN IF(NOT ISBLANK(TraderPrice), 1 - DIVIDE(TraderPrice, ListPrice))''', '0%')

H = '4. Customer health'
meas(H, 'Regular Customers', 'COUNTROWS(Fact_Customer_Health)', '#,##0')
for st in ('Active', 'At risk', 'Lapsed'):
    meas(H, {'Active': 'Healthy Customers', 'At risk': 'At Risk Customers', 'Lapsed': 'Lapsed Customers'}[st], f'CALCULATE(COUNTROWS(Fact_Customer_Health), Fact_Customer_Health[Status] = "{st}")', '#,##0')
meas(H, 'Lapsed Last 12m', 'CALCULATE(COUNTROWS(Fact_Customer_Health), Fact_Customer_Health[Lapsed_In_Last_12m] = TRUE())', '#,##0')
meas(H, 'Revenue at Risk M', 'DIVIDE(SUM(Fact_Customer_Health[Revenue_at_Risk_USD]), 1e6)', '\\$#,##0.0')
meas(H, 'Recent Lost Revenue M', 'DIVIDE(CALCULATE(SUM(Fact_Customer_Health[Lost_Revenue_USD]), Fact_Customer_Health[Lapsed_In_Last_12m] = TRUE()), 1e6)', '\\$#,##0.0')
meas(H, 'At Risk or Lapsed %', 'DIVIDE([At Risk Customers] + [Lapsed Customers], [Regular Customers])', '0%')

# ---- report visuals: SVG shell bar, navigation, titles and KPI tiles (image visuals), bar colours ----
V = '5. Report visuals'
BLUE, RED, INK, MUTED, LINE = '%230A6ED1', '%23BB0000', '%2332363A', '%236A6D70', '%23E5E5E5'
FONT = "'72', Segoe UI, Arial, sans-serif"
SVG0 = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'"
def svg_text(s): return s.replace('&', '&amp;').replace('%', '%25').replace('#', '%23')

meas(V, 'Shell Bar', f'''"{SVG0} width='1280' height='48' viewBox='0 0 1280 48' preserveAspectRatio='none'>"
    & "<rect width='1280' height='48' fill='%23354A5F'/>"
    & "<text x='18' y='30' font-family=\\"{FONT}\\" font-size='16' font-weight='bold' fill='%23FFFFFF'>Gulfport Oxo Chemicals</text>"
    & "<text x='228' y='30' font-family=\\"{FONT}\\" font-size='15' fill='%23FFFFFF'>Chemical Portfolio Analytics</text>"
    & "<circle cx='1247' cy='24' r='14' fill='%230A6ED1'/>"
    & "<text x='1247' y='29' text-anchor='middle' font-family=\\"{FONT}\\" font-size='13' fill='%23FFFFFF'>AP</text>"
    & "</svg>"'''.replace('\\"', '""'), 'General', cat='ImageUrl')

NAV = [('Overview', 'Overview', '◧'), ('ProductMix', 'Product mix', '◑'), ('InternalSourcing', 'Internal sourcing', '⇄'), ('CustomerHealth', 'Customer health', '☺')]
NAV_Y0, NAV_H = 10, 44
def nav(active):
    parts = [f"<rect width='200' height='672' fill='%23FFFFFF'/><line x1='199.5' y1='0' x2='199.5' y2='672' stroke='{LINE}'/>"]
    for i, (pid, label, icon) in enumerate(NAV):
        y = NAV_Y0 + i * NAV_H
        on = pid == active
        if on: parts.append(f"<rect x='0' y='{y}' width='199' height='{NAV_H}' fill='%23E5F0FA'/><rect x='0' y='{y}' width='3' height='{NAV_H}' fill='{BLUE}'/>")
        c = BLUE if on else INK
        w = " font-weight='bold'" if on else ''
        parts.append(f"<text x='18' y='{y + 27}' font-family=\"{FONT}\" font-size='14' fill='{c}'>{icon}</text>"
                     f"<text x='44' y='{y + 27}' font-family=\"{FONT}\" font-size='14'{w} fill='{c}'>{svg_text(label)}</text>")
    body = ''.join(parts).replace('"', '""')
    meas(V, f'Nav {active}', f'"{SVG0} width=\'200\' height=\'672\' viewBox=\'0 0 200 672\'>" & "{body}" & "</svg>"', 'General', cat='ImageUrl')
for pid, _, _ in NAV: nav(pid)

def title(pid, text):
    meas(V, f'Title {pid}', f'''"{SVG0} width='560' height='44' viewBox='0 0 560 44'>"
    & "<text x='0' y='30' font-family=""{FONT}"" font-size='20' fill='{INK}'>{svg_text(text)}</text>"
    & "</svg>"''', 'General', cat='ImageUrl')

def kpi(name, title_txt, lines, fmt, unit='""'):
    """Fiori KPI tile. `lines` are DAX VAR lines that must define cur (the value), sub (subtitle text) and clr (value colour)."""
    L = list(lines) + [f'VAR unit = {unit}', f'VAR vTxt = IF(ISBLANK(cur), "–", FORMAT(cur, "{fmt}"))',
                       'VAR vOut = SUBSTITUTE(SUBSTITUTE(vTxt, "%", "%25"), "#", "%23")',
                       'VAR sOut = SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(sub, "&", "&amp;"), "%", "%25"), "#", "%23")',
                       'VAR uOut = SUBSTITUTE(SUBSTITUTE(unit, "%", "%25"), "#", "%23")', 'RETURN',
                       f'''"{SVG0} width='254' height='110' viewBox='0 0 254 110'>"''',
                       f'''    & "<rect x='0.5' y='0.5' width='253' height='109' rx='4' fill='%23FFFFFF' stroke='{LINE}'/>"''',
                       f'''    & "<text x='16' y='26' font-family=""{FONT}"" font-size='14' fill='{INK}'>{svg_text(title_txt)}</text>"''',
                       f'''    & "<text x='16' y='44' font-family=""{FONT}"" font-size='11' fill='{MUTED}'>" & sOut & "</text>"''',
                       f'''    & "<text x='16' y='90' font-family=""{FONT}"" font-size='32' font-weight='300' fill='" & clr & "'>" & vOut & "<tspan font-size='14' fill='{MUTED}'> " & uOut & "</tspan></text>"''',
                       '    & "</svg>"']
    meas(V, f'Card {name}', '\n'.join(L), 'General', cat='ImageUrl')

YR = ['VAR y = [Selected Year]', 'VAR lm = [Last Month In Year]', 'VAR pl = [Prior Period Label]']
def trend(base, kind='pct', good='up'):
    L = YR + [f'VAR cur = {yr(base)}', f'VAR prev = {py(base)}']
    if kind == 'pct':
        L += ['VAR chg = DIVIDE(cur - prev, prev)',
              'VAR sub = IF(ISBLANK(prev), FORMAT(y, "0"), IF(chg >= 0, "▲ +", "▼ -") & FORMAT(ABS(chg), "0%") & " vs " & pl)']
    elif kind == 'pts':
        L += ['VAR chg = (cur - prev) * 100',
              'VAR sub = IF(ISBLANK(prev), FORMAT(y, "0"), IF(chg >= 0, "▲ +", "▼ -") & FORMAT(ABS(chg), "0.0") & " pts vs " & pl)']
    else:
        L += ['VAR chg = cur - prev',
              'VAR sub = IF(ISBLANK(prev), FORMAT(y, "0"), IF(chg >= 0, "▲ " & FORMAT(chg, "0") & " more than ", "▼ " & FORMAT(ABS(chg), "0") & " fewer than ") & pl)']
    L.append(f'VAR clr = IF(chg >= 0, "{BLUE if good == "up" else RED}", "{RED if good == "up" else BLUE}")')
    return L
CBLUE, CRED = f'VAR clr = "{BLUE}"', f'VAR clr = "{RED}"'

# Overview
title('Overview', 'Overview')
kpi('Revenue', 'Revenue', trend('Revenue M'), '$#,##0.0', '"M"')
kpi('Margin', 'Gross margin', trend('Gross Margin %', 'pts'), '0.0%')
kpi('Volume', 'Volume sold', trend('Volume kt'), '#,##0.0', '"kt"')
kpi('Customers', 'Active customers', trend('Active Customers', 'count'), '#,##0')
# Product mix
title('ProductMix', 'Product Mix: DOTP (A) vs DINP (B)')
kpi('DOTPShare', 'DOTP share of plasticizer kg', ['VAR y = [Selected Year]', f'VAR cur = {yr("DOTP Share %")}',
    'VAR sub = FORMAT(y, "0") & " · was " & FORMAT(CALCULATE([DOTP Share %], REMOVEFILTERS(Dim_Date), Dim_Date[Year] = 2022), "0%") & " in 2022"', CRED], '0%')
kpi('MarginKg', 'Margin per kg, DOTP', ['VAR cur = CALCULATE([DOTP Margin per kg], REMOVEFILTERS(Dim_Date))',
    'VAR sub = "At standard cost, since 2022"', CBLUE], '$0.00', '"vs " & FORMAT(CALCULATE([DINP Margin per kg], REMOVEFILTERS(Dim_Date)), "$0.00") & " DINP"')
kpi('Switched', 'Customers who switched A to B', ['VAR cur = [Switched Customers]',
    'VAR sub = "Of " & FORMAT([Plasticizer Customers], "0") & " plasticizer customers"', CRED], '#,##0')
kpi('MarginLost', 'Margin lost to switching', ['VAR y = [Selected Year]', 'VAR cur = CALCULATE([Margin Lost to Switching M], REMOVEFILTERS(Dim_Date))',
    'VAR sub = "Since 2022 · " & FORMAT(' + yr('Margin Lost to Switching M') + ', "$0.0") & "M in " & FORMAT(y, "0")', CRED], '$#,##0.0', '"M"')
# Internal sourcing
title('InternalSourcing', 'Internal Sourcing')
kpi('Spend', 'Spent buying chemicals we make', ['VAR y = [Selected Year]', f'VAR cur = {yr("Spend on Own Chemicals M")}',
    'VAR sub = FORMAT(y, "0") & " · 2-EH, n-butanol, PM"', CBLUE], '$#,##0.0', '"M"')
kpi('Avoidable', 'Avoidable cost', ['VAR y = [Selected Year]', f'VAR cur = {yr("Avoidable Cost M")}',
    'VAR sub = FORMAT(y, "0") & " · " & FORMAT(CALCULATE([Avoidable Cost M], REMOVEFILTERS(Dim_Date)), "$0.0") & "M since 2022"', CRED], '$#,##0.0', '"M"')
kpi('Surplus', '2-EH surplus sold to a trader', ['VAR y = [Selected Year]', f'VAR cur = {yr("2-EH Surplus Sold t")}',
    f'VAR sub = FORMAT(y, "0") & " · " & FORMAT({yr("Spot Discount vs List %")}, "0%") & " below list price"', CRED], '#,##0', '"t"')
kpi('Duplicates', 'Duplicate material records', ['VAR cur = [Duplicate Material Pairs]', 'VAR sub = "Same CAS number, two material numbers"', CBLUE], '0')
# Customer health
title('CustomerHealth', 'Customer Health')
kpi('Active', 'Active customers', ['VAR cur = [Healthy Customers]', 'VAR sub = "Of " & FORMAT([Regular Customers], "0") & " regular customers, as of 30 Sep 2026"', CBLUE], '#,##0')
kpi('AtRisk', 'At risk', ['VAR cur = [At Risk Customers]', 'VAR sub = FORMAT([Revenue at Risk M], "$0.0") & "M a year of revenue at risk"', CRED], '#,##0')
kpi('Lapsed12', 'Lapsed in the last 12 months', ['VAR cur = [Lapsed Last 12m]', 'VAR sub = FORMAT([Lapsed Customers], "0") & " lapsed since 2022"', CRED], '#,##0')
kpi('Lost', 'Revenue lost to recent lapses', ['VAR cur = [Recent Lost Revenue M]', 'VAR sub = "Annual revenue of those " & FORMAT([Lapsed Last 12m], "0") & " customers"', CRED], '$#,##0.0', '"M/yr"')

meas(V, 'Color Discount', 'IF([DINP Avg Discount %] > 0.06, "#BB0000", "#91C8F6")', 'General')
meas(V, 'Color Pair', 'IF(LEFT(SELECTEDVALUE(Map_Make_vs_Buy[Pair_Label]), 4) = "2-EH", "#BB0000", "#E9B3B3")', 'General')
meas(V, 'Color Profile', '''SWITCH(SELECTEDVALUE(Fact_Customer_Health[Plasticizer_Profile]),
    "Switched A to B", "#BB0000",
    "Loyal to A", "#0A6ED1",
    "#B8C3CC")''', 'General')

files['_Measures'] = ['table _Measures', f'\tlineageTag: {tag("_Measures")}', ''] + MS + \
    column_block('_Measures', 'Placeholder', 'string', hidden=True) + m_block('_Measures', '#table(type table [Placeholder = text], {})')

RELS = [('Fact_Sales', 'Customer_Id', 'Dim_Customer', 'Customer_Id'), ('Fact_Sales', 'Material_Id', 'Dim_Material', 'Material_Id'),
        ('Fact_Sales', 'Plant', 'Dim_Plant', 'Plant'), ('Fact_Sales', 'Order_Date', 'Dim_Date', 'Date'),
        ('Dim_Customer', 'Sales_Rep_Id', 'Dim_Sales_Rep', 'Sales_Rep_Id'),
        ('Fact_Purchases', 'Supplier_Id', 'Dim_Supplier', 'Supplier_Id'), ('Fact_Purchases', 'Material_Id', 'Dim_Material', 'Material_Id'),
        ('Fact_Purchases', 'Plant', 'Dim_Plant', 'Plant'), ('Fact_Purchases', 'PO_Date', 'Dim_Date', 'Date'),
        ('Fact_Production', 'Material_Id', 'Dim_Material', 'Material_Id'), ('Fact_Production', 'Plant', 'Dim_Plant', 'Plant'),
        ('Fact_Production', 'Start_Date', 'Dim_Date', 'Date'),
        ('Fact_Stock', 'Material_Id', 'Dim_Material', 'Material_Id'), ('Fact_Stock', 'Plant', 'Dim_Plant', 'Plant'), ('Fact_Stock', 'Month', 'Dim_Date', 'Date'),
        ('Fact_Std_Cost', 'Material_Id', 'Dim_Material', 'Material_Id'),
        ('Fact_Make_vs_Buy', 'Month', 'Dim_Date', 'Date'), ('Fact_Make_vs_Buy', 'Bought_Material_Id', 'Map_Make_vs_Buy', 'Bought_Material_Id'),
        ('Fact_Customer_Health', 'Customer_Id', 'Dim_Customer', 'Customer_Id'), ('Ref_PPI', 'Month', 'Dim_Date', 'Date')]

if OUT.exists(): shutil.rmtree(OUT)
d = OUT / SM / 'definition'; (d / 'tables').mkdir(parents=True)
order = list(files)
(d / 'database.tmdl').write_text('database ProjectC\n\tcompatibilityLevel: 1600\n\n')
(d / 'model.tmdl').write_text('model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\tsourceQueryCulture: en-US\n'
    '\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n'
    'annotation __PBI_TimeIntelligenceEnabled = 0\n\n'
    f'annotation PBI_QueryOrder = {json.dumps(["DataFolder"] + order)}\n\n'
    + ''.join(f'ref table {q(t)}\n' for t in order))
(d / 'expressions.tmdl').write_text(f'/// Folder holding the Project C CSV files. Keep the backslash at the end.\nexpression DataFolder = "{DEFAULT_FOLDER}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
    f'\tlineageTag: {tag("DataFolder")}\n\n\tannotation PBI_ResultType = Text\n')
(d / 'relationships.tmdl').write_text(''.join(f'relationship {tag("rel", a, b, c2)}\n\tfromColumn: {q(a)}.{q(b)}\n\ttoColumn: {q(c)}.{q(c2)}\n\n' for a, b, c, c2 in RELS))
(d / 'cultures').mkdir()
(d / 'cultures' / 'en-US.tmdl').write_text('cultureInfo en-US\n\n\tlinguisticMetadata =\n\t\t\t{\n\t\t\t  "Version": "1.0.0",\n\t\t\t  "Language": "en-US"\n\t\t\t}\n\t\tcontentType: json\n\n')
for t, L in files.items(): (d / 'tables' / f'{t}.tmdl').write_text('\n'.join(L).rstrip('\n') + '\n')
(OUT / SM / 'definition.pbism').write_text(json.dumps({'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json', 'version': '4.2', 'settings': {}}, indent=2))

# ---------------- report (SAP Fiori style) ----------------
VC = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json'
MEAS = '_Measures'
BG, WHITE, BORDER, INKC, MUTEDC, GRID, BLUEC, REDC, SOFTRED = '#F5F6F7', '#FFFFFF', '#E5E5E5', '#32363A', '#6A6D70', '#E5E5E5', '#0A6ED1', '#BB0000', '#E9B3B3'
def lit(v): return {'expr': {'Literal': {'Value': v}}}
def s(v): return lit("'" + v.replace("'", "''") + "'")
def col(c): return {'solid': {'color': s(c)}}
def C(e, p): return ('Column', e, p)
def Mz(p): return ('Measure', MEAS, p)
def fref(f):
    kind, e, p = f
    return {kind: {'Expression': {'SourceRef': {'Entity': e}}, 'Property': p}}
def proj(f, active=False, label=None):
    pj = {'field': fref(f), 'queryRef': f'{f[1]}.{f[2]}', 'nativeQueryRef': f[2]}
    if active: pj['active'] = True
    if label: pj['displayName'] = label
    return pj
def hidden_chrome():
    o = {k: [{'properties': {'show': lit('false')}}] for k in ('title', 'subTitle', 'background', 'border', 'dropShadow', 'divider', 'visualHeader')}
    o['padding'] = [{'properties': {k: lit('0D') for k in ('top', 'bottom', 'left', 'right')}}]
    return o
def chrome(title=None, sub=None, bg=True):
    o = {'title': [{'properties': {'show': lit('true' if title else 'false')}}], 'dropShadow': [{'properties': {'show': lit('false')}}]}
    if title: o['title'][0]['properties'].update({'text': s(title), 'fontColor': col(INKC), 'fontSize': lit('14D'), 'bold': lit('false')})
    o['subTitle'] = [{'properties': {'show': lit('true'), 'text': s(sub), 'fontColor': col(MUTEDC), 'fontSize': lit('11D')}}] if sub else [{'properties': {'show': lit('false')}}]
    o['background'] = [{'properties': {'show': lit('true'), 'color': col(WHITE), 'transparency': lit('0D')}}] if bg else [{'properties': {'show': lit('false')}}]
    o['border'] = [{'properties': {'show': lit('true'), 'color': col(BORDER), 'radius': lit('4D')}}] if bg else [{'properties': {'show': lit('false')}}]
    o['padding'] = [{'properties': {k: lit('12D') for k in ('top', 'bottom', 'left', 'right')}}] if bg else [{'properties': {k: lit('0D') for k in ('top', 'bottom', 'left', 'right')}}]
    return o
def container(name, x, y, w, h, v, z, filters=None):
    o = {'$schema': VC, 'name': name, 'position': {'x': x, 'y': y, 'z': z, 'width': w, 'height': h, 'tabOrder': z}, 'visual': v}
    if filters: o['filterConfig'] = {'filters': filters}
    return o
def in_filter(name, f, values, entity_alias='t'):
    kind, e, p = f
    return {'name': name, 'field': fref(f), 'type': 'Categorical',
            'filter': {'Version': 2, 'From': [{'Name': entity_alias, 'Entity': e, 'Type': 0}],
                       'Where': [{'Condition': {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': entity_alias}}, 'Property': p}}],
                                                       'Values': [[{'Literal': {'Value': v}}] for v in values]}}}]}}
def image(name, measure, x, y, w, h, z):
    v = {'visualType': 'image', 'drillFilterOtherVisuals': True,
         'objects': {'image': [{'properties': {'sourceType': s('imageData'), 'transparency': lit('0D'), 'effects': lit('false'),
                                               'sourceField': {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': MEAS}}, 'Property': measure}}}}}],
                     'imageScaling': [{'properties': {'imageScalingType': s('Normal')}}]},
         'visualContainerObjects': hidden_chrome()}
    return container(name, x, y, w, h, v, z)
def nav_button(name, target, x, y, w, h, z):
    sel = {'id': 'default'}
    v = {'visualType': 'actionButton', 'drillFilterOtherVisuals': True,
         'objects': {'icon': [{'properties': {'shapeType': s('blank')}, 'selector': sel}],
                     'fill': [{'properties': {'show': lit('false')}, 'selector': sel}],
                     'outline': [{'properties': {'show': lit('false'), 'transparency': lit('100D'), 'weight': lit('0D')}, 'selector': {'id': st}} for st in ('default', 'hover', 'press', 'disabled')],
                     'text': [{'properties': {'show': lit('false')}, 'selector': sel}]},
         'visualContainerObjects': {**hidden_chrome(),
                                    'visualLink': [{'properties': {'show': lit('true'), 'type': s('PageNavigation'), 'navigationSection': s(target)}}]}}
    return container(name, x, y, w, h, v, z)
def slicer(name, f, x, y, w, h, z, label, default=None):
    o = {'data': [{'properties': {'mode': s('Dropdown')}}],
         'selection': [{'properties': {'singleSelect': lit('true')}}],
         'header': [{'properties': {'show': lit('true'), 'text': s(label), 'fontColor': col(MUTEDC), 'textSize': lit('9D')}}],
         'items': [{'properties': {'fontColor': col(INKC), 'textSize': lit('11D'), 'background': col(WHITE)}}]}
    if default is not None:  # pre-selected value
        flt = in_filter('d', f, [default])['filter']
        o['general'] = [{'properties': {'filter': {'filter': flt}}}]
    v = {'visualType': 'slicer', 'drillFilterOtherVisuals': True,
         'query': {'queryState': {'Values': {'projections': [proj(f, active=True)]}}},
         'objects': o, 'visualContainerObjects': chrome(bg=False)}
    return container(name, x, y, w, h, v, z)
def axes(legend=False):
    return {'categoryAxis': [{'properties': {'show': lit('true'), 'labelColor': col(MUTEDC), 'fontSize': lit('10D'), 'showAxisTitle': lit('false')}}],
            'valueAxis': [{'properties': {'show': lit('true'), 'labelColor': col(MUTEDC), 'fontSize': lit('10D'), 'showAxisTitle': lit('false'),
                                          'gridlineShow': lit('true'), 'gridlineColor': col(GRID)}}],
            'legend': [{'properties': {'show': lit('true'), 'position': s('Top'), 'labelColor': col(MUTEDC), 'fontSize': lit('10D')}}] if legend
                      else [{'properties': {'show': lit('false')}}]}
def chart(name, vtype, x, y, w, h, z, cat, series, title, sub, sort=None, color_measure=None, labels=False, filters=None, label_width=None):
    """series: list of (measure, legend label, colour)"""
    o = axes(legend=len(series) > 1)
    if color_measure:
        o['dataPoint'] = [{'properties': {'fill': {'solid': {'color': {'expr': fref(Mz(color_measure))}}}}, 'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}]}}]
    else:
        o['dataPoint'] = [{'properties': {'fill': col(c)}, 'selector': {'metadata': f'{MEAS}.{m}'}} for m, _, c in series]
    if vtype == 'lineChart':
        o['lineStyles'] = [{'properties': {'strokeWidth': lit('3D'), 'showMarker': lit('false')}}]
    if label_width: o['categoryAxis'][0]['properties']['maxMarginFactor'] = lit(f'{label_width}L')
    if labels: o['labels'] = [{'properties': {'show': lit('true'), 'color': col(INKC), 'fontSize': lit('9D')}}]
    qs = {'queryState': {'Category': {'projections': [proj(cat, active=True)]}, 'Y': {'projections': [proj(Mz(m), label=lb) for m, lb, _ in series]}}}
    if sort: qs['sortDefinition'] = {'sort': [{'field': fref(sort[0]), 'direction': sort[1]}], 'isDefaultSort': True}
    v = {'visualType': vtype, 'drillFilterOtherVisuals': True, 'query': qs, 'objects': o, 'visualContainerObjects': chrome(title, sub)}
    return container(name, x, y, w, h, v, z, filters)
def table(name, x, y, w, h, z, cols, title, sub, sort, filters):
    o = {'columnHeaders': [{'properties': {'fontColor': col(MUTEDC), 'backColor': col(WHITE), 'fontSize': lit('9D'), 'bold': lit('false'), 'wordWrap': lit('true')}}],
         'values': [{'properties': {'fontColor': col(INKC), 'fontSize': lit('9D'), 'backColorPrimary': col(WHITE), 'backColorSecondary': col(BG)}}],
         'grid': [{'properties': {'gridHorizontal': lit('true'), 'gridHorizontalColor': col(GRID), 'gridVertical': lit('false')}}],
         'total': [{'properties': {'totals': lit('false')}}]}
    qs = {'queryState': {'Values': {'projections': [proj(f, label=lb) for f, lb in cols]}},
          'sortDefinition': {'sort': [{'field': fref(sort[0]), 'direction': sort[1]}], 'isDefaultSort': True}}
    v = {'visualType': 'tableEx', 'drillFilterOtherVisuals': True, 'query': qs, 'objects': o, 'visualContainerObjects': chrome(title, sub)}
    return container(name, x, y, w, h, v, z, filters)

# layout (1280 x 720): shell bar 48, nav 200 wide, content from x 212 to 1260
X0, X1 = 212, 1260
CARD_Y, CARD_W, CARD_H, GAP = 122, 254, 110, 10
CH_Y = CARD_Y + CARD_H + 12
CH_H = 708 - CH_Y
LEFT_W = 588
RIGHT_X = X0 + LEFT_W + 12
RIGHT_W = X1 - RIGHT_X
PAGES = []
def page(pid, display, cards, left, right, slicers, nofilter=()):
    vis = [image(f'{pid}_shell', 'Shell Bar', 0, 0, 1280, 48, 0), image(f'{pid}_nav', f'Nav {pid}', 0, 48, 200, 672, 1)]
    for i, (target, _, _) in enumerate(NAV):
        if target != pid: vis.append(nav_button(f'{pid}_go{i}', target, 0, 48 + NAV_Y0 + i * NAV_H, 199, NAV_H, 10 + i))
    vis.append(image(f'{pid}_title', f'Title {pid}', X0, 64, 560, 44, 20))
    n = len(slicers); sw = 140
    for i, sl in enumerate(slicers):
        x = X1 - n * sw - (n - 1) * 10 + i * (sw + 10)
        vis.append(slicer(f'{pid}_slicer{i}', sl[0], x, 56, sw, 58, 100 + i, *sl[1:]))
    for i, c in enumerate(cards):
        vis.append(image(f'{pid}_card{i}', f'Card {c}', X0 + i * (CARD_W + GAP) + (2 if i == 3 else 0), CARD_Y, CARD_W, CARD_H, 200 + i))
    for i, (fn, kw) in enumerate((left, right)):
        x, w = (X0, LEFT_W) if i == 0 else (RIGHT_X, RIGHT_W)
        vis.append(fn(f'{pid}_chart{i}', x=x, y=CH_Y, w=w, h=CH_H, z=300 + i, **kw))
    inter = [(f'{pid}_slicer0', f'{pid}_chart{i}') for i in nofilter]
    PAGES.append((pid, display, vis, inter))

def ch(vtype, **kw): return (lambda name, x, y, w, h, z, **k: chart(name, vtype, x, y, w, h, z, **k), kw)
def tb(**kw): return (lambda name, x, y, w, h, z, **k: table(name, x, y, w, h, z, **k), kw)

YEAR, QTR, MONTH = C('Dim_Date', 'Year'), C('Dim_Date', 'Year_Quarter'), C('Dim_Date', 'Month_Start')
REP = C('Dim_Sales_Rep', 'Rep_Name')
page('Overview', 'Overview', ['Revenue', 'Margin', 'Volume', 'Customers'],
     ch('areaChart', cat=MONTH, series=[('Revenue M', 'Revenue (USD M)', BLUEC)], title='Revenue by month (USD M)',
        sub='About $110M a year since 2023, while the product mix shifted underneath'),
     ch('clusteredBarChart', cat=C('Dim_Material', 'Product_Group'), series=[('Revenue M (Year)', 'Revenue (USD M)', BLUEC)],
        title='Revenue by product group, selected year (USD M)', sub='Plasticizers are the largest group by revenue',
        sort=(Mz('Revenue M (Year)'), 'Descending'), labels=True),
     slicers=[(YEAR, 'Year'), (C('Dim_Plant', 'Plant_Name'), 'Plant'), (C('Dim_Material', 'Product_Group'), 'Product group')], nofilter=[0])
page('ProductMix', 'Product Mix', ['DOTPShare', 'MarginKg', 'Switched', 'MarginLost'],
     ch('lineChart', cat=QTR, series=[('DOTP Share %', 'DOTP (A)', BLUEC), ('DINP Share %', 'DINP (B)', REDC)],
        title='Share of plasticizer volume by quarter (%)', sub='DINP overtook DOTP in early 2025'),
     ch('clusteredBarChart', cat=REP, series=[('DINP Avg Discount %', 'Average discount', BLUEC)], title='Average discount on DINP by sales rep',
        sub='Two reps give DINP more than double the usual discount', sort=(Mz('DINP Avg Discount %'), 'Descending'),
        color_measure='Color Discount', labels=True),
     slicers=[(YEAR, 'Year'), (REP, 'Sales rep'), (C('Dim_Sales_Rep', 'Sales_Region'), 'Region')], nofilter=[0])
page('InternalSourcing', 'Internal Sourcing', ['Spend', 'Avoidable', 'Surplus', 'Duplicates'],
     ch('clusteredColumnChart', cat=YEAR, series=[('2-EH Bought t', 'Bought from outside (Lake Charles)', REDC), ('2-EH Surplus Sold t', 'Own surplus sold cheap (Pasadena)', BLUEC)],
        title='2-EH per year (t)', sub='Bought from outside vs our own surplus sold to a trader. 2026 is Jan-Sep', labels=True),
     ch('clusteredBarChart', cat=C('Map_Make_vs_Buy', 'Pair_Label'), series=[('Avoidable Cost M (Year)', 'Avoidable cost', REDC)],
        title='Avoidable cost by material, selected year (USD M)', sub='Matched on CAS number. 2-EH is almost all of it',
        sort=(Mz('Avoidable Cost M (Year)'), 'Descending'), color_measure='Color Pair', labels=True, label_width=45),
     slicers=[(YEAR, 'Year', '2025L'), (C('Map_Make_vs_Buy', 'Pair_Label'), 'Material pair')], nofilter=[0])
HC = 'Fact_Customer_Health'
page('CustomerHealth', 'Customer Health', ['Active', 'AtRisk', 'Lapsed12', 'Lost'],
     tb(cols=[(C('Dim_Customer', 'Customer_Name'), 'Customer'), (C('Dim_Customer', 'Industry'), 'Industry'), (C(HC, 'Status'), 'Status'),
              (C(HC, 'Days_Since_Last_Order'), 'Days since last order'), (C(HC, 'Median_Reorder_Gap_days'), 'Usual gap (days)'),
              (C(HC, 'Revenue_Exposure_USD'), 'Revenue / yr')],
        title='Customers to call first', sub='At risk, or lapsed in the last 12 months, by annual revenue',
        sort=(C(HC, 'Revenue_Exposure_USD'), 'Descending'), filters=[in_filter('call_first', C(HC, 'Call_First'), ['true'])]),
     ch('clusteredBarChart', cat=C(HC, 'Plasticizer_Profile'), series=[('At Risk or Lapsed %', 'At risk or lapsed', BLUEC)],
        title='At risk or lapsed, by plasticizer profile (%)', sub='Switchers churn twice as often as loyal DOTP buyers',
        sort=(Mz('At Risk or Lapsed %'), 'Descending'), color_measure='Color Profile', labels=True),
     slicers=[(C('Dim_Customer', 'Industry'), 'Industry'), (REP, 'Sales rep'), (C('Dim_Customer', 'Plasticizer_Profile'), 'Plasticizer profile')])

r = OUT / RP; dd = r / 'definition'
(dd / 'pages').mkdir(parents=True)
(r / 'StaticResources' / 'SharedResources' / 'BaseThemes').mkdir(parents=True)
shutil.copy(THEME, r / 'StaticResources' / 'SharedResources' / 'BaseThemes' / 'CY24SU10.json')
def wj(p, o): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(o, indent=2, ensure_ascii=False))
wj(r / 'definition.pbir', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json', 'version': '4.0', 'datasetReference': {'byPath': {'path': f'../{SM}'}}})
wj(dd / 'version.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json', 'version': '2.0.0'})
wj(dd / 'report.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.0.0/schema.json',
    'themeCollection': {'baseTheme': {'name': 'CY24SU10', 'reportVersionAtImport': {'visual': '1.8.95', 'report': '2.0.95', 'page': '1.3.95'}, 'type': 'SharedResources'}},
    'resourcePackages': [{'name': 'SharedResources', 'type': 'SharedResources', 'items': [{'name': 'CY24SU10', 'path': 'BaseThemes/CY24SU10.json', 'type': 'BaseTheme'}]}],
    'settings': {'useStylableVisualContainerHeader': True, 'exportDataMode': 'AllowSummarized', 'defaultDrillFilterOtherVisuals': True, 'allowChangeFilterTypes': True, 'useEnhancedTooltips': True, 'useDefaultAggregateDisplayName': True}})
wj(dd / 'pages' / 'pages.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json', 'pageOrder': [p[0] for p in PAGES], 'activePageName': PAGES[0][0]})
for pid, display, vis, inter in PAGES:
    pj = {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json', 'name': pid, 'displayName': display, 'displayOption': 'FitToPage', 'height': 720, 'width': 1280,
          'objects': {'background': [{'properties': {'color': col(BG), 'transparency': lit('0D')}}], 'outspace': [{'properties': {'color': col(BG), 'transparency': lit('0D')}}]}}
    if inter: pj['visualInteractions'] = [{'source': a, 'target': b, 'type': 'NoFilter'} for a, b in inter]
    wj(dd / 'pages' / pid / 'page.json', pj)
    for v in vis: wj(dd / 'pages' / pid / 'visuals' / v['name'] / 'visual.json', v)

wj(OUT / 'ProjectC.pbip', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json', 'version': '1.0', 'artifacts': [{'report': {'path': RP}}], 'settings': {'enableAutoRecovery': True}})
for folder, kind in ((RP, 'Report'), (SM, 'SemanticModel')):
    wj(OUT / folder / '.platform', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json',
        'metadata': {'type': kind, 'displayName': 'ProjectC'}, 'config': {'version': '2.0', 'logicalId': tag('platform', kind)}})
(OUT / '.gitignore').write_text('**/.pbi/localSettings.json\n**/.pbi/cache.abf\n')
print('tables', len(files), 'measures', sum(1 for l in MS if l.startswith('\tmeasure')), 'pages', len(PAGES), 'visuals', sum(len(p[2]) for p in PAGES))

(OUT / 'HOW_TO_OPEN.md').write_text(f'''# Opening the report in Power BI Desktop

You need a recent version of Power BI Desktop, because the report is saved as a PBIP project rather than a .pbix.

1. Make sure all the CSVs are in one folder. If you cloned the repo, they're already together in `data/clean/`.
2. Double-click `ProjectC.pbip`.
3. Power BI will look for the CSVs in `{DEFAULT_FOLDER}`. If yours are somewhere else, go to Home > Transform data > Edit parameters and change **DataFolder**. Keep the backslash at the end, it breaks without it.
4. Click **Refresh**. It's about 30,000 rows, so it only takes a few seconds.
5. If you'd rather have a single file, use File > Save as and pick .pbix.

## What's on each page

- **Overview:** revenue, gross margin, volume and active customers for the selected year, compared with the same months a year earlier.
- **Product Mix:** DOTP (A) vs DINP (B) share, customers who switched, margin lost to switching, and DINP discount by sales rep.
- **Internal Sourcing:** spend on chemicals the company also makes, avoidable cost, and 2-EH bought outside vs surplus sold to a trader. The Year filter starts on 2025.
- **Customer Health:** active, at-risk and lapsed customers, and the list of customers to call first.

The left menu works like SAP Fiori navigation. In Desktop, hold Ctrl and click a menu item. In the Power BI service a normal click works.
The Year filter drives the cards and the right-hand chart. The left-hand trend chart always shows every year.

## Inside the model

- All measures are in the `_Measures` table, grouped in folders (Sales, Product mix, Internal sourcing, Customer health, Report visuals).
- The cards, menu, page title and top bar are SVG images built by the measures in `5. Report visuals`.
- Margin is at standard cost. When no year is picked, the cards show the latest year (2026, Jan-Sep).
- `scripts/04_build_powerbi_project.py` regenerates this whole folder from the CSVs.
''')

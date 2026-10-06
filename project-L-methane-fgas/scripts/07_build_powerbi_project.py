# Project L: builds the Power BI project (PBIP: TMDL semantic model + PBIR report) from the clean CSVs.
# Open ProjectL.pbip in Power BI Desktop, set the DataFolder parameter to the folder holding the CSVs, refresh, then File > Save as .pbix.
import json, shutil, uuid, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / 'data' / 'clean'
OUT = ROOT / 'dashboard' / 'ProjectL'
THEME = Path(__file__).resolve().parent / 'assets' / 'CY24SU10.json'
DEFAULT_FOLDER = 'C:\\ProjectL\\data\\clean\\'  # change in Power BI: Transform data > Edit parameters
SM, RP = 'ProjectL.SemanticModel', 'ProjectL.Report'

def tag(*k): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'projectL/' + '/'.join(k)))
def q(name):  # TMDL object name, quoted when needed
    return name if name.replace('_', '').isalnum() and name[0].isalpha() else "'" + name.replace("'", "''") + "'"

# ---------------- semantic model ----------------
TABLES = {  # table: (csv, forced column types)
    'Fact_Emissions': ('Fact_Emissions.csv', {}),
    'Fact_SubpartW_Source': ('Fact_SubpartW_Source.csv', {}),
    'Fact_SubpartW_Facility_Production': ('Fact_SubpartW_Facility_Production.csv', {}),
    'Dim_Facility': ('Dim_Facility.csv', {'Primary_NAICS_Code': 'int64'}),
    'Dim_Source_Category': ('Dim_Source_Category.csv', {}),
    'Fact_Trade_EU_Imports': ('Fact_Trade_EU_Imports.csv', {}),
    'Dim_Regulation': ('Dim_Regulation.csv', {}),
    'Fact_LNG_Exports_Terminal': ('Fact_LNG_Exports_Terminal.csv', {}),
    'Fact_IEA_Methane': ('Fact_IEA_Methane.csv', {}),
    'Fact_IEA_Abatement': ('Fact_IEA_Abatement.csv', {}),
    'Fact_Forecast_Methane': ('Fact_Forecast_Methane.csv', {}),  # from scripts/forecast_methane.py
}
TEXT_COLS = {'Basin_Code', 'HS6', 'Partner_Code'}
NO_SUM = {'Year', 'Facility_Id', 'Row_Id', 'Primary_NAICS_Code', 'Latitude', 'Longitude', 'USD_per_EUR',
          'Unit_Value_USD_per_t', 'CH4_Mole_Fraction_Avg', 'Non-Compliant Share %', 'Penalty Rate %', 'Cost_USD_per_MMBtu', 'Cost_USD_per_tCH4', 'Cost_USD_per_tCO2e_AR5'}
MTYPE = {'int64': 'Int64.Type', 'double': 'type number', 'boolean': 'type logical', 'string': 'type text'}

def col_types(csv, forced):
    d = pd.read_csv(CLEAN / csv, nrows=5000, low_memory=False, dtype={c: str for c in TEXT_COLS})
    out = {}
    for c, t in d.dtypes.items():
        t = str(t)
        out[c] = forced.get(c) or ('string' if c in TEXT_COLS else 'int64' if t == 'int64' else 'double' if t == 'float64' else 'boolean' if t == 'bool' else 'string')
    return out

def column_block(table, c, t, hidden=False, fmt=None, source=None):
    summ = 'none' if (c in NO_SUM or t in ('string', 'boolean')) else 'sum'
    lines = [f'\tcolumn {q(c)}', f'\t\tdataType: {t}']
    if fmt or t == 'int64': lines.append(f'\t\tformatString: {fmt or "0"}')
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
for t, (csv, forced) in TABLES.items():
    types = col_types(csv, forced)
    L = [f'table {q(t)}', f'\tlineageTag: {tag(t)}', '']
    for c, ty in types.items(): L += column_block(t, c, ty)
    L += m_block(t, csv_m(csv, types))
    files[t] = L

# Dim_Year: 1967-2030 so every fact's years have a match (EIA history starts 1967, forecast to 2030)
L = ['table Dim_Year', f'\tlineageTag: {tag("Dim_Year")}', '']
L += column_block('Dim_Year', 'Year', 'int64')
L += m_block('Dim_Year', '''let
    Source = Table.FromList({1967..2030}, Splitter.SplitByNothing(), {"Year"}),
    Typed = Table.TransformColumnTypes(Source, {{"Year", Int64.Type}})
in
    Typed''')
files['Dim_Year'] = L

# Dim_Basin: one name per basin code, taken from the EPA emissions file
L = ['table Dim_Basin', f'\tlineageTag: {tag("Dim_Basin")}', '']
L += column_block('Dim_Basin', 'Basin_Code', 'string') + column_block('Dim_Basin', 'Basin_Name', 'string')
L += m_block('Dim_Basin', '''let
    Source = Table.SelectColumns(Fact_Emissions, {"Basin_Code", "Basin_Name"}),
    NonBlank = Table.SelectRows(Source, each [Basin_Code] <> null and [Basin_Code] <> ""),
    Distinct = Table.Distinct(NonBlank, {"Basin_Code"})
in
    Distinct''')
files['Dim_Basin'] = L

# What-if parameters (whole percents, divided by 100 in the measures)
def whatif(table, name, hi, default, desc):
    L = [f'/// {desc}', f'table {q(table)}', f'\tlineageTag: {tag(table)}', '',
         f'\tmeasure {q(name + " Value")} = SELECTEDVALUE({q(table)}[{name}], {default}) / 100',
         '\t\tformatString: 0%', f'\t\tlineageTag: {tag(table, "value")}', '']
    L += column_block(table, name, 'int64', source='[Value]')
    L += [f'\tpartition {q(table)} = calculated', '\t\tmode: import', f'\t\tsource = GENERATESERIES(0, {hi}, 1)', '',
          '\tannotation PBI_Id = ' + tag(table, 'id').replace('-', ''), '']
    return L
files['Non-Compliant Share'] = whatif('Non-Compliant Share', 'Non-Compliant Share %', 100, 50, 'What-if: share of US oil and gas exports to the EU that fail the EU Methane Regulation equivalence test')
files['Penalty Rate'] = whatif('Penalty Rate', 'Penalty Rate %', 20, 5, 'What-if: penalty or lost value as a share of the import value at risk')

# Measures
MS = []
def meas(folder, name, expr, fmt, cat=None):
    global MS
    lines = expr.strip('\n').split('\n')
    if len(lines) == 1: MS.append(f'\tmeasure {q(name)} = {lines[0]}')
    else: MS += [f'\tmeasure {q(name)} =', *['\t\t\t' + l for l in lines]]
    MS += [f'\t\tformatString: {fmt}', f'\t\tdisplayFolder: {folder}', f'\t\tlineageTag: {tag("m", name)}'] + ([f'\t\tdataCategory: {cat}'] if cat else []) + ['']

E = '1. Emissions'
meas(E, 'GHG tCO2e', 'SUM(Fact_Emissions[CO2e_AR5_tCO2e])', '#,##0')
meas(E, 'GHG MtCO2e', "DIVIDE([GHG tCO2e], 1e6)", '#,##0.0')
meas(E, 'Methane MtCO2e', 'CALCULATE([GHG MtCO2e], Fact_Emissions[Gas_Group] = "Methane")', '#,##0.0')
meas(E, 'F-gas MtCO2e', 'CALCULATE([GHG MtCO2e], Fact_Emissions[Gas_Group] = "F-gases")', '#,##0.00')
meas(E, 'Methane t', 'CALCULATE(SUM(Fact_Emissions[Gas_t]), Fact_Emissions[Gas] = "CH4")', '#,##0')
meas(E, 'Facilities Reporting', 'DISTINCTCOUNT(Fact_Emissions[Facility_Id])', '#,##0')
meas(E, 'Selected Year', '''IF(
    HASONEVALUE(Dim_Year[Year]),
    VALUES(Dim_Year[Year]),
    CALCULATE(MAX(Fact_Emissions[Year]), REMOVEFILTERS())
)''', '0')
for base in ('GHG MtCO2e', 'Methane MtCO2e', 'F-gas MtCO2e', 'Facilities Reporting'):
    meas(E, base + ' (Year)', f'''VAR y = [Selected Year]
RETURN CALCULATE([{base}], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = y)''', '#,##0.0' if 'Mt' in base else '#,##0')
meas(E, 'Methane Change since 2016 %', '''VAR y = [Selected Year]
VAR NowValue = CALCULATE([Methane MtCO2e], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = y)
VAR BaseValue = CALCULATE([Methane MtCO2e], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = 2016)
RETURN DIVIDE(NowValue - BaseValue, BaseValue)''', '+0.0%;-0.0%;0.0%')

I = '2. Oil & gas intensity'
meas(I, 'O&G Methane t', 'CALCULATE(SUM(Fact_SubpartW_Source[Gas_t]), Fact_SubpartW_Source[Gas] = "CH4")', '#,##0')
meas(I, 'O&G Methane MtCO2e', 'DIVIDE(CALCULATE(SUM(Fact_SubpartW_Source[CO2e_AR5_tCO2e]), Fact_SubpartW_Source[Gas] = "CH4"), 1e6)', '#,##0.00')
meas(I, 'Production Methane t', 'CALCULATE([O&G Methane t], Fact_SubpartW_Source[Segment] = "Onshore Production")', '#,##0')
meas(I, 'Gas Sold bcm', 'SUM(Fact_SubpartW_Facility_Production[Gas_Sales_bcm])', '#,##0.0')
meas(I, 'Methane Produced t', '''-- methane in the gas sold: bcm x 678,000 t per bcm (0.678 kg/m3) x methane share of the gas (0.85 when not reported)
SUMX(
    Fact_SubpartW_Facility_Production,
    Fact_SubpartW_Facility_Production[Gas_Sales_bcm] * 678000
        * IF(Fact_SubpartW_Facility_Production[CH4_Mole_Fraction_Avg] > 0, Fact_SubpartW_Facility_Production[CH4_Mole_Fraction_Avg], 0.85)
)''', '#,##0')
meas(I, 'Methane Intensity %', 'DIVIDE([Production Methane t], [Methane Produced t])', '0.00%')
meas(I, 'Producing Wells', 'SUM(Fact_SubpartW_Facility_Production[Wells_Producing])', '#,##0')
meas(I, 'Methane per Well t', 'DIVIDE([Production Methane t], [Producing Wells])', '#,##0.00')
for base, fmt in (('Methane Intensity %', '0.00%'), ('Production Methane t', '#,##0'), ('O&G Methane t', '#,##0'), ('Gas Sold bcm', '#,##0.0'), ('Producing Wells', '#,##0')):
    meas(I, base.replace(' %', '') + ' (Year)' + (' %' if '%' in base else ''), f'''VAR y = [Selected Year]
RETURN CALCULATE([{base}], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = y)''', fmt)

X = '3. EU exposure'
meas(X, 'US LNG Exports bcm', 'SUM(Fact_LNG_Exports_Terminal[Volume_bcm])', '#,##0.0')
meas(X, 'US LNG to EU bcm', 'CALCULATE([US LNG Exports bcm], Fact_LNG_Exports_Terminal[Destination_Is_EU27] = TRUE())', '#,##0.0')
meas(X, 'EU Share of US LNG %', 'DIVIDE([US LNG to EU bcm], [US LNG Exports bcm])', '0.0%')
meas(X, 'EU Imports from US USD bn', 'DIVIDE(CALCULATE(SUM(Fact_Trade_EU_Imports[Value_USD]), Fact_Trade_EU_Imports[Partner_Code] = "US"), 1e9)', '#,##0.0')
meas(X, 'EU Oil & Gas Imports from US USD bn', 'CALCULATE([EU Imports from US USD bn], Fact_Trade_EU_Imports[Product_Group] = "Oil & gas")', '#,##0.0')
meas(X, 'EU F-gas & Fluoropolymer Imports from US USD bn', 'CALCULATE([EU Imports from US USD bn], Fact_Trade_EU_Imports[Product_Group] <> "Oil & gas")', '#,##0.00')
meas(X, 'US Share of EU LNG Imports %', '''DIVIDE(
    CALCULATE(SUM(Fact_Trade_EU_Imports[Value_USD]), Fact_Trade_EU_Imports[Product] = "LNG", Fact_Trade_EU_Imports[Partner_Code] = "US"),
    CALCULATE(SUM(Fact_Trade_EU_Imports[Value_USD]), Fact_Trade_EU_Imports[Product] = "LNG", Fact_Trade_EU_Imports[Flow_Type] = "Extra-EU")
)''', '0.0%')
meas(X, 'Trade Year', '''IF(
    HASONEVALUE(Dim_Year[Year]),
    VALUES(Dim_Year[Year]),
    CALCULATE(MAX(Fact_Trade_EU_Imports[Year]), REMOVEFILTERS())
)''', '0')
for base, fmt in (('US LNG to EU bcm', '#,##0.0'), ('EU Share of US LNG %', '0.0%'), ('EU Oil & Gas Imports from US USD bn', '#,##0.0'), ('US Share of EU LNG Imports %', '0.0%')):
    meas(X, base.replace(' %', '') + ' (Year)' + (' %' if '%' in base else ''), f'''VAR y = [Trade Year]
RETURN CALCULATE([{base}], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = y)''', fmt)
meas(X, 'EU Value at Risk USD bn', "[EU Oil & Gas Imports from US USD bn (Year)] * [Non-Compliant Share % Value] * [Penalty Rate % Value]", '#,##0.00')

A = '4. Abatement'
meas(A, 'Abatement Potential MtCO2e', 'DIVIDE(SUM(Fact_IEA_Abatement[Savings_CO2e_AR5_tCO2e]), 1e6)', '#,##0.0')
meas(A, 'Abatement Potential Mt CH4', 'DIVIDE(SUM(Fact_IEA_Abatement[Savings_CH4_t]), 1e6)', '#,##0.00')
meas(A, 'Avg Cost USD per tCO2e', '''DIVIDE(
    SUMX(Fact_IEA_Abatement, Fact_IEA_Abatement[Cost_USD_per_tCO2e_AR5] * Fact_IEA_Abatement[Savings_CO2e_AR5_tCO2e]),
    SUM(Fact_IEA_Abatement[Savings_CO2e_AR5_tCO2e])
)''', '#,##0.00')
meas(A, 'Net-Saving Share %', '''DIVIDE(
    CALCULATE(SUM(Fact_IEA_Abatement[Savings_CO2e_AR5_tCO2e]), Fact_IEA_Abatement[Is_Net_Saving] = TRUE()),
    SUM(Fact_IEA_Abatement[Savings_CO2e_AR5_tCO2e])
)''', '0.0%')

B = '5. Global benchmark'
meas(B, 'IEA Methane Mt', 'DIVIDE(CALCULATE(SUM(Fact_IEA_Methane[CH4_t]), Fact_IEA_Methane[Region_Type] = "Country"), 1e6)', '#,##0.00')
meas(B, 'US Share of World O&G Methane %', '''DIVIDE(
    CALCULATE([IEA Methane Mt], Fact_IEA_Methane[Country] = "United States"),
    CALCULATE(DIVIDE(SUM(Fact_IEA_Methane[CH4_t]), 1e6), REMOVEFILTERS(Fact_IEA_Methane[Country]))
)''', '0.0%')

# ---- Option D report measures: SVG cards and headers (image visuals), colours, helper values ----
V = '6. Report visuals'
INK, MUTED, CARD, LINE, GREEN, GREEN_LT, RED = '%231D1C1A', '%237A756B', '%23FFFDF8', '%23E6DFD1', '%232F6B4F', '%23B9D1C2', '%23B3462E'
MUTED = '%2326241F'  # darker secondary text (Avirat, 2026-10-05)
meas(E, 'Methane Share %', 'DIVIDE([Methane MtCO2e], [GHG MtCO2e])', '0.0%')
meas(I, 'Production Methane kt', 'DIVIDE([Production Methane t], 1000)', '#,##0')
meas(I, 'O&G Methane kt (Year)', 'DIVIDE([O&G Methane t (Year)], 1000)', '#,##0')
meas(A, 'Net-Saving Potential MtCO2e', 'CALCULATE([Abatement Potential MtCO2e], Fact_IEA_Abatement[Is_Net_Saving] = TRUE())', '#,##0.0')
meas(B, 'US IEA Methane Mt', 'CALCULATE([IEA Methane Mt], Fact_IEA_Methane[Country] = "United States")', '#,##0.0')
meas(B, 'World IEA Methane Mt', 'CALCULATE(DIVIDE(SUM(Fact_IEA_Methane[CH4_t]), 1e6), REMOVEFILTERS(Fact_IEA_Methane))', '#,##0')
meas(B, 'US Methane Rank', '''RANKX(
    FILTER(ALL(Fact_IEA_Methane[Country]), CALCULATE([IEA Methane Mt]) > 0),
    CALCULATE([IEA Methane Mt]),
    CALCULATE([IEA Methane Mt], Fact_IEA_Methane[Country] = "United States"),
    DESC
)''', '0')
meas(B, 'IEA Methane Mt (Top 15)', '''VAR r = RANKX(FILTER(ALL(Fact_IEA_Methane[Country]), CALCULATE([IEA Methane Mt]) > 0), CALCULATE([IEA Methane Mt]), , DESC)
RETURN IF(HASONEVALUE(Fact_IEA_Methane[Country]) && r <= 15, [IEA Methane Mt])''', '#,##0.0')
meas(V, 'Color Country Bar', 'IF(SELECTEDVALUE(Fact_IEA_Methane[Country]) = "United States", "#2F6B4F", "#B9D1C2")', 'General')
meas(V, 'Color Latest Trade Year', 'IF(SELECTEDVALUE(Dim_Year[Year]) = CALCULATE(MAX(Fact_Trade_EU_Imports[Year]), REMOVEFILTERS()), "#2F6B4F", "#B9D1C2")', 'General')
meas(V, 'Color Cost Sign', 'IF([Avg Cost USD per tCO2e] < 0, "#2F6B4F", "#C9826B")', 'General')

def svg_text(s): return s.replace('&', '&amp;').replace('%', '%25').replace('#', '%23')

def header(name, title, sub):
    meas(V, f'Header {name}', f'''"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='1280' height='78' viewBox='0 0 1280 78' preserveAspectRatio='none'>"
    & "<rect width='1280' height='78' fill='%231F3B2D'/>"
    & "<text x='28' y='38' font-family='Georgia, serif' font-size='24' font-weight='bold' fill='%23FFFFFF'>{svg_text(title)}</text>"
    & "<text x='28' y='62' font-family='Segoe UI, sans-serif' font-size='13' fill='%23FFFFFF'>{svg_text(sub)}</text>"
    & "</svg>"''', 'General', cat='ImageUrl')

def kpi(name, title, base, year, fmt, unit='', delta=None, good=None, spark=None, foot=None):
    """SVG card: title, value for the selected year, change vs the year before, sparkline over the spark years."""
    L = []
    if year:
        L += [f'VAR y = [{year}]', f'VAR cur = CALCULATE([{base}], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = y)',
              f'VAR prev = CALCULATE([{base}], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = y - 1)']
    else:
        L += [f'VAR cur = [{base}]']
    if delta == 'pct':
        L += ['VAR chg = DIVIDE(cur - prev, prev)',
              'VAR dTxt = IF(ISBLANK(prev) || ISBLANK(cur), "", IF(chg >= 0, "▲ +", "▼ -") & FORMAT(ABS(chg), "0%") & " vs " & (y - 1))']
    elif delta == 'pts':
        L += ['VAR chg = (cur - prev) * 100',
              'VAR dTxt = IF(ISBLANK(prev) || ISBLANK(cur), "", IF(chg >= 0, "▲ +", "▼ -") & FORMAT(ABS(chg), "0.0") & " pts vs " & (y - 1))']
    if delta:
        if good == 'up': L.append(f'VAR dCol = IF(chg >= 0, "{GREEN}", "{RED}")')
        elif good == 'down': L.append(f'VAR dCol = IF(chg <= 0, "{GREEN}", "{RED}")')
        else: L.append(f'VAR dCol = "{MUTED}"')
    else:
        L += [f'VAR dTxt = {foot}', f'VAR dCol = "{MUTED}"']
    L.append(f'VAR vTxt = IF(ISBLANK(cur), "–", FORMAT(cur, "{fmt}"))')
    L += ['VAR vOut = SUBSTITUTE(SUBSTITUTE(vTxt, "%", "%25"), "#", "%23")', 'VAR dOut = SUBSTITUTE(SUBSTITUTE(dTxt, "%", "%25"), "#", "%23")']
    if spark:
        s, e = spark
        L += [f'VAR pts = FILTER(ADDCOLUMNS(FILTER(ALL(Dim_Year[Year]), Dim_Year[Year] >= {s} && Dim_Year[Year] <= {e}), "@v", [{base}]), NOT ISBLANK([@v]))',
              'VAR mx = MAXX(pts, [@v])', 'VAR mn = MIN(0, MINX(pts, [@v]))',
              f'VAR poly = CONCATENATEX(pts, FORMAT(ROUND(176 + 104 * (Dim_Year[Year] - {s}) / {e - s}, 0), "0") & "," & FORMAT(ROUND(78 - 34 * DIVIDE([@v] - mn, mx - mn), 0), "0"), " ", Dim_Year[Year], ASC)',
              'VAR lastYr = MAXX(pts, Dim_Year[Year])', 'VAR lastV = MAXX(FILTER(pts, Dim_Year[Year] = lastYr), [@v])',
              f'VAR dot = "<circle cx=\'" & FORMAT(ROUND(176 + 104 * (lastYr - {s}) / {e - s}, 0), "0") & "\' cy=\'" & FORMAT(ROUND(78 - 34 * DIVIDE(lastV - mn, mx - mn), 0), "0") & "\' r=\'3\' fill=\'{GREEN}\'/>"',
              f'VAR sp = IF(COUNTROWS(pts) > 1, "<polyline points=\'" & poly & "\' fill=\'none\' stroke=\'{GREEN}\' stroke-width=\'2\' stroke-linejoin=\'round\'/>" & dot)']
    else:
        L.append('VAR sp = ""')
    unit_t = f"<tspan font-size='14' font-weight='normal' fill='{MUTED}'> {svg_text(unit)}</tspan>" if unit else ''
    L += ['RETURN',
          f'''"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='296' height='118' viewBox='0 0 296 118'>"''',
          f'''    & "<rect x='0.5' y='0.5' width='295' height='117' rx='10' fill='{CARD}' stroke='{LINE}'/>"''',
          f'''    & "<text x='16' y='27' font-family='Segoe UI, sans-serif' font-size='12' fill='{MUTED}'>{svg_text(title)}</text>"''',
          f'''    & "<text x='16' y='72' font-family='Segoe UI Semibold, Segoe UI, sans-serif' font-size='30' font-weight='600' fill='{INK}'>" & vOut & "{unit_t}</text>"''',
          f'''    & "<text x='16' y='100' font-family='Segoe UI, sans-serif' font-size='12' fill='" & dCol & "'>" & dOut & "</text>"''',
          '    & sp & "</svg>"']
    meas(V, f'Card {name}', '\n'.join(L), 'General', cat='ImageUrl')

# Overview (EPA, 2011-2023)
header('Overview', 'US greenhouse gas emissions', 'Facility emissions reported to the EPA (GHGRP), in AR5 CO2e. Year filter drives the cards and the segment chart.')
kpi('GHG', 'Total GHG emissions', 'GHG MtCO2e', 'Selected Year', '#,##0', 'Mt CO2e', 'pct', 'down', (2011, 2023))
kpi('Methane', 'Methane', 'Methane MtCO2e', 'Selected Year', '#,##0', 'Mt CO2e', 'pct', 'down', (2011, 2023))
kpi('Fgas', 'F-gases', 'F-gas MtCO2e', 'Selected Year', '#,##0.0', 'Mt CO2e', 'pct', 'down', (2011, 2023))
kpi('MethaneShare', 'Methane share of all GHG', 'Methane Share %', 'Selected Year', '0.0%', '', 'pts', 'down', (2011, 2023))
# Intensity (Subpart W, 2015-2023)
header('Intensity', 'Oil and gas methane intensity', 'Onshore production facilities reporting under EPA Subpart W. Intensity = methane emitted / methane in the gas sold.')
kpi('Intensity', 'Methane intensity', 'Methane Intensity %', 'Selected Year', '0.00%', '', 'pct', 'down', (2015, 2023))
kpi('ProdMethane', 'Methane from production', 'Production Methane kt', 'Selected Year', '#,##0', 'kt CH4', 'pct', 'down', (2015, 2023))
kpi('GasSold', 'Gas sold by these facilities', 'Gas Sold bcm', 'Selected Year', '#,##0', 'bcm', 'pct', None, (2015, 2023))
kpi('PerWell', 'Methane per producing well', 'Methane per Well t', 'Selected Year', '0.00', 't CH4', 'pct', 'down', (2015, 2023))
# EU exposure (trade, 2016-2025)
header('EU', 'US exports and EU methane rules', 'How much US oil and gas trade the EU Methane Regulation touches. Eurostat and EIA data.')
kpi('LNGtoEU', 'US LNG shipped to the EU', 'US LNG to EU bcm', 'Trade Year', '#,##0.0', 'bcm', 'pct', 'up', (2016, 2025))
kpi('EUShare', 'EU share of US LNG exports', 'EU Share of US LNG %', 'Trade Year', '0.0%', '', 'pts', 'up', (2016, 2025))
kpi('USShare', 'US share of EU LNG imports', 'US Share of EU LNG Imports %', 'Trade Year', '0.0%', '', 'pts', 'up', (2016, 2025))
kpi('Risk', 'EU import value at risk', 'EU Value at Risk USD bn', None, '$#,##0.0', 'bn', foot='FORMAT([Non-Compliant Share % Value], "0%") & " failing x " & FORMAT([Penalty Rate % Value], "0%") & " penalty"')
# Abatement (IEA, US)
header('Abatement', 'US methane abatement options', 'IEA estimates for US oil and gas: how much methane each measure can cut and what it costs net of the gas saved.')
kpi('Potential', 'Abatement potential', 'Abatement Potential MtCO2e', None, '#,##0', 'Mt CO2e/yr', foot='"All 16 IEA measures, United States"')
kpi('NetSaving', 'Pays for itself', 'Net-Saving Potential MtCO2e', None, '#,##0', 'Mt CO2e/yr', foot='FORMAT([Net-Saving Share %], "0%") & " of the potential has a negative net cost"')
kpi('AvgCost', 'Average net cost', 'Avg Cost USD per tCO2e', None, '$#,##0.0', 'per t CO2e', foot='"Weighted by abatement potential"')
kpi('PotentialCH4', 'Methane that could be avoided', 'Abatement Potential Mt CH4', None, '#,##0.0', 'Mt CH4/yr', foot='"Equal to the CO2e figure at GWP 28"')
# Benchmark (IEA 2025)
header('Benchmark', 'Global oil and gas methane benchmark', 'IEA Global Methane Tracker, 2025 estimates (includes satellite-detected large leaks).')
kpi('USMethane', 'US oil & gas methane', 'US IEA Methane Mt', None, '#,##0.0', 'Mt CH4', foot='"IEA estimate, 2025"')
kpi('USShareWorld', 'US share of world total', 'US Share of World O&G Methane %', None, '0%', '', foot='"Of all oil and gas methane"')
kpi('USRank', 'US rank among countries', 'US Methane Rank', None, '"#"0', '', foot='"Largest emitter = #1"')
kpi('World', 'World oil & gas methane', 'World IEA Methane Mt', None, '#,##0', 'Mt CH4', foot='"All countries, 2025"')

# Forecast (docs/forecast_model.md): linear trend 2016-2023, 90% band on the total, Global Methane Pledge path
F = '7. Forecast'
FF = 'Fact_Forecast_Methane'
def ff(series, col='Methane_MtCO2e', total=True):
    return f'CALCULATE(SUM({FF}[{col}]), {FF}[Series] = "{series}"' + (f', {FF}[Segment] = "All Segments")' if total else ')')
meas(F, 'Methane Actual Mt', ff('Actual'), '#,##0.0')
meas(F, 'Methane Forecast Mt', ff('Forecast'), '#,##0.0')
meas(F, 'Forecast 90% Low Mt', ff('Forecast', 'Lower_90_MtCO2e'), '#,##0.0')
meas(F, 'Forecast 90% High Mt', ff('Forecast', 'Upper_90_MtCO2e'), '#,##0.0')
meas(F, 'Pledge Path Mt', ff('Pledge', total=False), '#,##0.0')
meas(F, 'Last Actual Year', f'CALCULATE(MAX({FF}[Year]), REMOVEFILTERS(), {FF}[Series] = "Actual")', '0')
meas(F, 'Forecast Year', f'''VAR s = SELECTEDVALUE(Dim_Year[Year])
VAR last = CALCULATE(MAX({FF}[Year]), REMOVEFILTERS())
RETURN IF(s > [Last Actual Year] && s <= last, s, last)''', '0')
meas(F, 'Forecast Gap to Pledge Mt', 'IF(NOT ISBLANK([Methane Forecast Mt]) && NOT ISBLANK([Pledge Path Mt]), [Methane Forecast Mt] - [Pledge Path Mt])', '+#,##0.0;-#,##0.0;0.0')
meas(F, 'Forecast Trend Mt per yr', f'''VAR last = CALCULATE(MAX({FF}[Year]), REMOVEFILTERS())
RETURN CALCULATE([Methane Forecast Mt], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = last) - CALCULATE([Methane Forecast Mt], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = last - 1)''', '#,##0.0')
meas(F, 'Forecast Change by Segment Mt', f'''VAR y = [Forecast Year]
VAR la = [Last Actual Year]
VAR f = CALCULATE(SUM({FF}[Methane_MtCO2e]), REMOVEFILTERS(Dim_Year), {FF}[Year] = y, {FF}[Series] = "Forecast")
VAR a = CALCULATE(SUM({FF}[Methane_MtCO2e]), REMOVEFILTERS(Dim_Year), {FF}[Year] = la, {FF}[Series] = "Actual")
RETURN IF(HASONEVALUE({FF}[Segment]) && SELECTEDVALUE({FF}[Segment]) <> "All Segments", f - a)''', '+#,##0.0;-#,##0.0;0.0')
header('Forecast', 'US methane outlook to 2030', 'Linear trend fitted to 2016-2023 EPA methane, with a 90% range and the Global Methane Pledge path. Year filter: 2024-2030.')
kpi('Forecast', 'Methane forecast', 'Methane Forecast Mt', 'Forecast Year', '#,##0', 'Mt CO2e', spark=(2023, 2030),
    foot='"90% range " & FORMAT(CALCULATE([Forecast 90% Low Mt], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = y), "0") & " to " & FORMAT(CALCULATE([Forecast 90% High Mt], REMOVEFILTERS(Dim_Year), Dim_Year[Year] = y), "0") & " Mt"')
kpi('Pledge', 'Global Methane Pledge path', 'Pledge Path Mt', 'Forecast Year', '#,##0', 'Mt CO2e', foot='"-30% vs 2020 by 2030"')
kpi('PledgeGap', 'Forecast vs pledge path', 'Forecast Gap to Pledge Mt', 'Forecast Year', '+#,##0;-#,##0;0', 'Mt CO2e',
    foot='IF(ISBLANK(cur), "", IF(cur <= 0, "Below the pledge path (on track)", "Above the pledge path (off track)"))')
kpi('Trend', 'Trend per year', 'Forecast Trend Mt per yr', None, '#,##0.0', 'Mt CO2e/yr', foot='"Linear fit to 2016-2023 EPA data"')

files['_Measures'] = ['table _Measures', f'\tlineageTag: {tag("_Measures")}', ''] + MS + \
    column_block('_Measures', 'Placeholder', 'string', hidden=True) + m_block('_Measures', '#table(type table [Placeholder = text], {})')

RELS = [('Fact_Emissions', 'Facility_Id', 'Dim_Facility', 'Facility_Id'), ('Fact_Emissions', 'Year', 'Dim_Year', 'Year'),
        ('Fact_SubpartW_Source', 'Facility_Id', 'Dim_Facility', 'Facility_Id'), ('Fact_SubpartW_Source', 'Year', 'Dim_Year', 'Year'),
        ('Fact_SubpartW_Source', 'Source_Category', 'Dim_Source_Category', 'Source_Category'),
        ('Fact_SubpartW_Facility_Production', 'Facility_Id', 'Dim_Facility', 'Facility_Id'), ('Fact_SubpartW_Facility_Production', 'Year', 'Dim_Year', 'Year'),
        ('Dim_Facility', 'Basin_Code', 'Dim_Basin', 'Basin_Code'),
        ('Fact_Trade_EU_Imports', 'Year', 'Dim_Year', 'Year'), ('Fact_Trade_EU_Imports', 'Regulation', 'Dim_Regulation', 'Regulation'),
        ('Fact_LNG_Exports_Terminal', 'Year', 'Dim_Year', 'Year'), ('Fact_Forecast_Methane', 'Year', 'Dim_Year', 'Year')]

if OUT.exists(): shutil.rmtree(OUT)
d = OUT / SM / 'definition'; (d / 'tables').mkdir(parents=True)
order = list(files)
QORDER = [t for t in order if t not in ('Non-Compliant Share', 'Penalty Rate')]
(d / 'database.tmdl').write_text(f'database ProjectL\n\tcompatibilityLevel: 1600\n\n')
(d / 'model.tmdl').write_text('model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\tsourceQueryCulture: en-US\n'
    '\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n'
    'annotation __PBI_TimeIntelligenceEnabled = 0\n\n'
    f'annotation PBI_QueryOrder = {json.dumps(["DataFolder"] + QORDER)}\n\n'
    + ''.join(f'ref table {q(t)}\n' for t in order))
(d / 'expressions.tmdl').write_text(f'/// Folder holding the Project L CSV files. Keep the backslash at the end.\nexpression DataFolder = "{DEFAULT_FOLDER}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
    f'\tlineageTag: {tag("DataFolder")}\n\n\tannotation PBI_ResultType = Text\n')
(d / 'relationships.tmdl').write_text(''.join(f'relationship {tag("rel", a, b, c2)}\n\tfromColumn: {q(a)}.{q(b)}\n\ttoColumn: {q(c)}.{q(c2)}\n\n' for a, b, c, c2 in RELS))
(d / 'cultures').mkdir()
(d / 'cultures' / 'en-US.tmdl').write_text('cultureInfo en-US\n\n\tlinguisticMetadata =\n\t\t\t{\n\t\t\t  "Version": "1.0.0",\n\t\t\t  "Language": "en-US"\n\t\t\t}\n\t\tcontentType: json\n\n')
for t, L in files.items(): (d / 'tables' / f'{t}.tmdl').write_text('\n'.join(L).rstrip('\n') + '\n')
(OUT / SM / 'definition.pbism').write_text(json.dumps({'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json', 'version': '4.2', 'settings': {}}, indent=2))

# ---------------- report (Option D style: cream page, forest-green header, SVG cards, 2 charts per page) ----------------
VC = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json'
MEAS = '_Measures'
BG, CARDC, BORDER, INKC, MUTEDC, GRID, GREENC, GREENLT = '#F6F2EA', '#FFFDF8', '#E6DFD1', '#1D1C1A', '#7A756B', '#EBE5D9', '#2F6B4F', '#B9D1C2'
MUTEDC = '#26241F'
def lit(v): return {'expr': {'Literal': {'Value': v}}}
def s(v): return lit("'" + v.replace("'", "''") + "'")
def col(c): return {'solid': {'color': s(c)}}
def C(e, p): return ('Column', e, p)
def Mz(p): return ('Measure', MEAS, p)
def fref(f):
    kind, e, p = f
    return {kind: {'Expression': {'SourceRef': {'Entity': e}}, 'Property': p}}
def proj(f, active=False):
    pj = {'field': fref(f), 'queryRef': f'{f[1]}.{f[2]}', 'nativeQueryRef': f[2]}
    if active: pj['active'] = True
    return pj
def chrome(title=None, sub=None, bg=True):
    o = {'title': [{'properties': {'show': lit('true' if title else 'false')}}], 'dropShadow': [{'properties': {'show': lit('false')}}]}
    if title: o['title'][0]['properties'].update({'text': s(title), 'fontColor': col(INKC), 'fontSize': lit('14D'), 'bold': lit('true')})
    o['subTitle'] = [{'properties': {'show': lit('true'), 'text': s(sub), 'fontColor': col(MUTEDC), 'fontSize': lit('11D')}}] if sub else [{'properties': {'show': lit('false')}}]
    o['background'] = [{'properties': {'show': lit('true'), 'color': col(CARDC), 'transparency': lit('0D')}}] if bg else [{'properties': {'show': lit('false')}}]
    o['border'] = [{'properties': {'show': lit('true'), 'color': col(BORDER), 'radius': lit('10D')}}] if bg else [{'properties': {'show': lit('false')}}]
    return o
def container(name, x, y, w, h, v, z, filters=None):
    o = {'$schema': VC, 'name': name, 'position': {'x': x, 'y': y, 'z': z, 'width': w, 'height': h, 'tabOrder': z}, 'visual': v}
    if filters: o['filterConfig'] = {'filters': filters}
    return o
def year_range(name, lo, hi):
    src = {'Column': {'Expression': {'SourceRef': {'Source': 'd'}}, 'Property': 'Year'}}
    return [{'name': name, 'field': fref(C('Dim_Year', 'Year')), 'type': 'Advanced',
             'filter': {'Version': 2, 'From': [{'Name': 'd', 'Entity': 'Dim_Year', 'Type': 0}],
                        'Where': [{'Condition': {'Comparison': {'ComparisonKind': 2, 'Left': src, 'Right': {'Literal': {'Value': f'{lo}L'}}}}},
                                  {'Condition': {'Comparison': {'ComparisonKind': 4, 'Left': src, 'Right': {'Literal': {'Value': f'{hi}L'}}}}}]}}]
def image(name, measure, x, y, w, h, z, fill_bg=None):
    v = {'visualType': 'image', 'drillFilterOtherVisuals': True,
         'objects': {'image': [{'properties': {'sourceType': s('imageData'), 'transparency': lit('0D'), 'effects': lit('false'),
                                               'sourceField': {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': MEAS}}, 'Property': measure}}}}}],
                     'imageScaling': [{'properties': {'imageScalingType': s('Fill' if fill_bg else 'Normal')}}]},
         'visualContainerObjects': {k: [{'properties': {'show': lit('false')}}] for k in ('title', 'subTitle', 'background', 'border', 'dropShadow', 'divider', 'visualHeader')}}
    v['visualContainerObjects']['padding'] = [{'properties': {k: lit('0D') for k in ('top', 'bottom', 'left', 'right')}}]
    if fill_bg:  # header: the container itself is green, so the band runs edge to edge
        v['visualContainerObjects']['background'] = [{'properties': {'show': lit('true'), 'color': col(fill_bg), 'transparency': lit('0D')}}]
    return container(name, x, y, w, h, v, z)
def slicer(name, f, x, y, w, h, z, label, lo=None, hi=None):
    v = {'visualType': 'slicer', 'drillFilterOtherVisuals': True,
         'query': {'queryState': {'Values': {'projections': [proj(f, active=True)]}}},
         'objects': {'data': [{'properties': {'mode': s('Dropdown')}}],
                     'selection': [{'properties': {'singleSelect': lit('true')}}],
                     'header': [{'properties': {'show': lit('true'), 'text': s(label), 'fontColor': col(MUTEDC), 'textSize': lit('10D')}}],
                     'items': [{'properties': {'fontColor': col(INKC), 'textSize': lit('12D')}}]},
         'visualContainerObjects': chrome()}
    return container(name, x, y, w, h, v, z, year_range(name + '_years', lo, hi) if lo else None)
def axes(cat_show=True):
    return {'categoryAxis': [{'properties': {'show': lit('true' if cat_show else 'false'), 'labelColor': col(MUTEDC), 'fontSize': lit('10D'), 'showAxisTitle': lit('false')}}],
            'valueAxis': [{'properties': {'show': lit('true'), 'labelColor': col(MUTEDC), 'fontSize': lit('10D'), 'showAxisTitle': lit('false'),
                                          'gridlineShow': lit('true'), 'gridlineColor': col(GRID)}}],
            'legend': [{'properties': {'show': lit('false')}}]}
def chart(name, vtype, x, y, w, h, z, cat, val, title, sub, sort=None, color=GREENC, color_measure=None, labels=False, years=None):
    o = axes()
    if color_measure:
        o['dataPoint'] = [{'properties': {'fill': {'solid': {'color': {'expr': fref(Mz(color_measure))}}}}, 'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}]}}]
    else:
        o['dataPoint'] = [{'properties': {'fill': col(color)}}]
        if vtype in ('areaChart', 'lineChart'):  # series colour needs a measure selector, else Power BI falls back to theme blue
            o['dataPoint'][0]['selector'] = {'metadata': proj(val)['queryRef']}
    if labels: o['labels'] = [{'properties': {'show': lit('true'), 'color': col(INKC), 'fontSize': lit('9D')}}]
    q = {'queryState': {'Category': {'projections': [proj(cat, active=True)]}, 'Y': {'projections': [proj(val)]}}}
    if sort: q['sortDefinition'] = {'sort': [{'field': fref(sort[0]), 'direction': sort[1]}], 'isDefaultSort': True}
    v = {'visualType': vtype, 'drillFilterOtherVisuals': True, 'query': q, 'objects': o, 'visualContainerObjects': chrome(title, sub)}
    return container(name, x, y, w, h, v, z, year_range(name + '_years', *years) if years else None)

def line_chart(name, x, y, w, h, z, cat, series, title, sub, years=None):
    """series: (measure, legend name, colour, 'solid'|'dashed'|'dotted', width)"""
    o = axes(); o['legend'] = [{'properties': {'show': lit('true'), 'position': s('Top'), 'labelColor': col(MUTEDC), 'fontSize': lit('10D')}}]
    o['dataPoint'] = [{'properties': {'fill': col(c)}, 'selector': {'metadata': f'{MEAS}.{m}'}} for m, _, c, _, _ in series]
    o['lineStyles'] = [{'properties': {'showMarker': lit('false')}}] + [
        {'properties': {'lineStyle': s(st), 'strokeWidth': lit(f'{wd}D'), 'showMarker': lit('false')}, 'selector': {'metadata': f'{MEAS}.{m}'}} for m, _, _, st, wd in series]
    ys = []
    for m, label, _, _, _ in series:
        pj = proj(Mz(m)); pj['displayName'] = label; ys.append(pj)
    q = {'queryState': {'Category': {'projections': [proj(cat, active=True)]}, 'Y': {'projections': ys}}}
    v = {'visualType': 'lineChart', 'drillFilterOtherVisuals': True, 'query': q, 'objects': o, 'visualContainerObjects': chrome(title, sub)}
    return container(name, x, y, w, h, v, z, year_range(name + '_years', *years) if years else None)

YEAR = C('Dim_Year', 'Year')
PAGES = []
def page(name, display, hdr, cards, charts, slicers=(), nofilter=()):
    vis = [image(f'{name}_header', f'Header {hdr}', 0, 0, 1280, 78, 0, fill_bg='#1F3B2D')]
    top = 96
    for i, sl in enumerate(slicers):
        vis.append(slicer(f'{name}_slicer{i}', *sl[:1], 28 + i * 256, 88, 240, 70, 100 + i, *sl[1:]))
    if slicers: top = 168
    for i, c in enumerate(cards):
        vis.append(image(f'{name}_card{i}', f'Card {c}', 28 + i * 310, top, 296, 118, 200 + i))
    ch_y = top + 130; ch_h = 704 - ch_y
    for i, c in enumerate(charts):
        if c[0] == 'line': vis.append(line_chart(f'{name}_chart{i}', 28 + i * 620, ch_y, 604, ch_h, 300 + i, *c[1:]))
        else: vis.append(chart(f'{name}_chart{i}', c[0], 28 + i * 620, ch_y, 604, ch_h, 300 + i, *c[1:5], **c[5]))
    inter = [(f'{name}_slicer0', f'{name}_chart{i}') for i in nofilter] if slicers else []
    PAGES.append((name, display, vis, inter, None))

page('Overview', 'Overview', 'Overview', ['GHG', 'Methane', 'Fgas', 'MethaneShare'], [
    ('areaChart', YEAR, Mz('Methane MtCO2e'), 'Methane emissions by year (Mt CO2e)', 'Reported methane fell 22% from 2011 to 2023', {}),
    ('clusteredBarChart', C('Fact_Emissions', 'Segment'), Mz('Methane MtCO2e (Year)'), 'Methane by reporting segment, selected year (Mt CO2e)',
     'Onshore production is the largest oil and gas segment', dict(sort=(Mz('Methane MtCO2e (Year)'), 'Descending'), labels=True)),
], slicers=[(YEAR, 'Year', 2011, 2023)], nofilter=[0])
page('Forecast', 'Methane Forecast', 'Forecast', ['Forecast', 'Pledge', 'PledgeGap', 'Trend'], [
    ('line', YEAR, [('Methane Actual Mt', 'Reported', '#2F6B4F', 'solid', 3), ('Methane Forecast Mt', 'Forecast', '#2F6B4F', 'dotted', 3),
                    ('Forecast 90% High Mt', '90% range (high)', '#9DBFAB', 'dashed', 1), ('Forecast 90% Low Mt', '90% range (low)', '#9DBFAB', 'dashed', 1),
                    ('Pledge Path Mt', 'Pledge path', '#B3462E', 'dashed', 2)],
     'Methane: reported and forecast (Mt CO2e)', 'The central forecast meets the pledge by 2030; the top of the 90% range does not', (2011, 2030)),
    ('clusteredBarChart', C('Fact_Forecast_Methane', 'Segment'), Mz('Forecast Change by Segment Mt'), 'Change by segment, 2023 to selected year (Mt CO2e)',
     'Direct emitters and onshore production drive most of the decline', dict(sort=(Mz('Forecast Change by Segment Mt'), 'Ascending'), labels=True)),
], slicers=[(YEAR, 'Forecast year', 2024, 2030)], nofilter=[0])
page('Intensity', 'Methane Intensity', 'Intensity', ['Intensity', 'ProdMethane', 'GasSold', 'PerWell'], [
    ('areaChart', YEAR, Mz('Methane Intensity %'), 'Methane intensity by year', 'Fell from 0.49% in 2015 to 0.19% in 2023', {}),
    ('clusteredBarChart', C('Dim_Source_Category', 'Source_Category'), Mz('O&G Methane kt (Year)'), 'Oil and gas methane by source, selected year (kt CH4)',
     'All Subpart W segments, not only production. Pneumatic devices and leaks lead', dict(sort=(Mz('O&G Methane kt (Year)'), 'Descending'), labels=True)),
], slicers=[(YEAR, 'Year', 2015, 2023)], nofilter=[0])
page('EU_Exposure', 'EU Exposure', 'EU', ['LNGtoEU', 'EUShare', 'USShare', 'Risk'], [
    ('areaChart', YEAR, Mz('EU Share of US LNG %'), 'EU share of US LNG exports (%)', 'From about 10% or less before 2019 to 55% in 2025', dict(years=(2016, 2025))),
    ('clusteredColumnChart', YEAR, Mz('EU Oil & Gas Imports from US USD bn'), 'EU oil & gas imports from the US (USD bn)',
     'Peaked in 2022 as the EU replaced Russian gas', dict(color_measure='Color Latest Trade Year', years=(2016, 2025))),
], slicers=[(YEAR, 'Year', 2016, 2025), (C('Non-Compliant Share', 'Non-Compliant Share %'), 'Exports failing EU rule (%)'), (C('Penalty Rate', 'Penalty Rate %'), 'Penalty or lost value (%)')],
   nofilter=[0, 1])
page('Abatement', 'Abatement', 'Abatement', ['Potential', 'NetSaving', 'AvgCost', 'PotentialCH4'], [
    ('clusteredBarChart', C('Fact_IEA_Abatement', 'Measure'), Mz('Avg Cost USD per tCO2e'), 'Net cost by measure, cheapest first (USD per t CO2e)',
     'Leak detection and blowdown capture pay for themselves', dict(sort=(Mz('Avg Cost USD per tCO2e'), 'Ascending'), color_measure='Color Cost Sign', labels=True)),
    ('clusteredBarChart', C('Fact_IEA_Abatement', 'Measure'), Mz('Abatement Potential MtCO2e'), 'Abatement potential by measure (Mt CO2e per year)',
     'Replacing gas-driven devices with electric motors offers the most', dict(sort=(Mz('Abatement Potential MtCO2e'), 'Descending'), labels=True)),
])
page('Benchmark', 'Global Benchmark', 'Benchmark', ['USMethane', 'USShareWorld', 'USRank', 'World'], [
    ('clusteredBarChart', C('Fact_IEA_Methane', 'Country'), Mz('IEA Methane Mt (Top 15)'), 'Top 15 countries by oil & gas methane (Mt CH4)',
     'The US is the largest emitter, ahead of Russia', dict(sort=(Mz('IEA Methane Mt (Top 15)'), 'Descending'), color_measure='Color Country Bar', labels=True)),
    ('clusteredBarChart', C('Fact_IEA_Methane', 'Reason'), Mz('US IEA Methane Mt'), 'US oil & gas methane by cause (Mt CH4)',
     'Venting is about 60% of US oil and gas methane', dict(sort=(Mz('US IEA Methane Mt'), 'Descending'), labels=True)),
])
US_FILTER = {'filters': [{'name': 'abate_country', 'field': fref(C('Fact_IEA_Abatement', 'Country')), 'type': 'Categorical',
    'filter': {'Version': 2, 'From': [{'Name': 'f', 'Entity': 'Fact_IEA_Abatement', 'Type': 0}],
               'Where': [{'Condition': {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 'f'}}, 'Property': 'Country'}}], 'Values': [[{'Literal': {'Value': "'United States'"}}]]}}}]},
    'howCreated': 'User'}]}
ai = [p[0] for p in PAGES].index('Abatement'); PAGES[ai] = PAGES[ai][:4] + (US_FILTER,)

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
for name, display, vis, inter, filt in PAGES:
    pj = {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json', 'name': name, 'displayName': display, 'displayOption': 'FitToPage', 'height': 720, 'width': 1280,
          'objects': {'background': [{'properties': {'color': col(BG), 'transparency': lit('0D')}}], 'outspace': [{'properties': {'color': col(BG), 'transparency': lit('0D')}}]}}
    if filt: pj['filterConfig'] = filt
    if inter: pj['visualInteractions'] = [{'source': a, 'target': b, 'type': 'NoFilter'} for a, b in inter]
    wj(dd / 'pages' / name / 'page.json', pj)
    for v in vis: wj(dd / 'pages' / name / 'visuals' / v['name'] / 'visual.json', v)

wj(OUT / 'ProjectL.pbip', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json', 'version': '1.0', 'artifacts': [{'report': {'path': RP}}], 'settings': {'enableAutoRecovery': True}})
for folder, kind in ((RP, 'Report'), (SM, 'SemanticModel')):
    wj(OUT / folder / '.platform', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json',
        'metadata': {'type': kind, 'displayName': 'ProjectL'}, 'config': {'version': '2.0', 'logicalId': tag('platform', kind)}})
(OUT / '.gitignore').write_text('**/.pbi/localSettings.json\n**/.pbi/cache.abf\n')
print('tables', len(files), 'measures', sum(1 for l in MS if l.startswith('\tmeasure')), 'pages', len(PAGES), 'visuals', sum(len(p[2]) for p in PAGES))

(OUT / 'HOW_TO_OPEN.md').write_text(f'''# Opening the report in Power BI Desktop

You need a recent version of Power BI Desktop, because the report is saved as a PBIP project rather than a .pbix.

1. Make sure all the CSVs are in one folder. If you cloned the repo, they're already together in `data/clean/`.
2. Double-click `ProjectL.pbip`.
3. Power BI will look for the CSVs in `{DEFAULT_FOLDER}`. If yours are somewhere else, go to Home > Transform data > Edit parameters and change **DataFolder**. Keep the backslash at the end, it breaks without it.
4. Click **Refresh**. It loads about half a million rows, so give it a minute or two.
5. If you'd rather have a single file, use File > Save as and pick .pbix.

## What's on each page

- **Overview:** total GHG, methane and F-gas, the methane trend and methane by segment (EPA, 2011-2023).
- **Methane Forecast:** the forecast to 2030 with its 90% range and the Global Methane Pledge path. Pick a year from 2024 to 2030.
- **Methane Intensity:** methane lost per unit of methane sold, and which equipment it comes from (2015-2023).
- **EU Exposure:** US LNG going to the EU, EU imports from the US, and trade value at risk. The two scenario dropdowns change the result.
- **Abatement:** US abatement measures by net cost and size (IEA).
- **Global Benchmark:** oil and gas methane by country, and US methane by cause (IEA, 2025).

The Year slicer on each page drives the four cards and the right-hand chart. The left-hand chart always shows every year so you keep the trend in view.

## Inside the model

- All 95 measures live in the `_Measures` table, in numbered folders. Forecast measures are in `7. Forecast`.
- Emissions are in AR5 CO2e throughout.
- The forecast itself comes from `scripts/06_forecast_methane.py`. The method is in `docs/forecast_model.md`.
- `scripts/07_build_powerbi_project.py` regenerates this whole folder from the CSVs.
''')

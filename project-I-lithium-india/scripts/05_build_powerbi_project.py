# Project I: builds the Power BI project (PBIP: TMDL semantic model + PBIR report) from the clean CSVs.
# Look: the "one story" layout Avirat picked (Option E). Each page has a headline that states the finding,
# one big chart, three things to know, and slicers for scenario, policy lever and India's share of world supply.
# Open ProjectI.pbip in Power BI Desktop, set the DataFolder parameter to the folder holding the CSVs, refresh,
# then File > Save as .pbix.
import json, shutil, uuid, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / 'data' / 'clean'
OUT = ROOT / 'dashboard' / 'ProjectI'
THEME = ROOT / 'scripts' / 'assets' / 'CY24SU10.json'
DEFAULT_FOLDER = 'C:\\ProjectI\\data\\clean\\'
SM, RP = 'ProjectI.SemanticModel', 'ProjectI.Report'


def tag(*k): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'projectI/' + '/'.join(k)))


def q(name):  # TMDL object name, quoted when needed
    return name if name.replace('_', '').isalnum() and name[0].isalpha() else "'" + name.replace("'", "''") + "'"


# ---------------- semantic model ----------------
TABLES = ['Dim_Scenario', 'Dim_Lever', 'Dim_Year', 'Dim_Sector', 'Fact_Balance', 'Fact_Demand', 'Ref_Value_Chain']
NO_SUM = {'Year', 'Sort', 'kg_LCE_per_kWh', 'Energy_Coverage_Ratio', 'Import_Dependence', 'Domestic_Share', 'Recycled_Content_Share',
          'Recycled_Content_Mandate', 'India_Share_of_Global_Supply', 'Units', 'GWh'}
MTYPE = {'int64': 'Int64.Type', 'double': 'type number', 'boolean': 'type logical', 'string': 'type text'}


def col_types(csv):
    d = pd.read_csv(CLEAN / csv)
    return {c: ('int64' if str(t) == 'int64' else 'double' if str(t) == 'float64' else 'boolean' if str(t) == 'bool' else 'string')
            for c, t in d.dtypes.items()}


def column_block(table, c, t, hidden=False, source=None, sort_by=None):
    summ = 'none' if (c in NO_SUM or t in ('string', 'boolean')) else 'sum'
    fmt = '0' if t == 'int64' else '#,##0.0' if t == 'double' else None
    lines = [f'\tcolumn {q(c)}', f'\t\tdataType: {t}']
    if fmt: lines.append(f'\t\tformatString: {fmt}')
    if hidden: lines.append('\t\tisHidden')
    lines += [f'\t\tlineageTag: {tag(table, c)}', f'\t\tsummarizeBy: {summ}', f'\t\tsourceColumn: {source or c}']
    if sort_by: lines.append(f'\t\tsortByColumn: {q(sort_by)}')
    return lines + ['', '\t\tannotation SummarizationSetBy = Automatic', '']


def m_block(table, body):
    lines = [f'\tpartition {q(table)} = m', '\t\tmode: import', '\t\tsource =']
    lines += ['\t\t\t\t' + l for l in body.strip('\n').split('\n')]
    return lines + ['', '\tannotation PBI_ResultType = Table', '']


def csv_m(csv, types, extra=''):
    tl = ', '.join(f'{{"{c}", {MTYPE[t]}}}' for c, t in types.items())
    return f'''let
    Source = Csv.Document(File.Contents(DataFolder & "{csv}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{{tl}}}, "en-US"){extra}
in
    Result'''


files = {}
SORT_BY = {('Dim_Scenario', 'Scenario'): 'Sort', ('Dim_Lever', 'Lever'): 'Sort', ('Dim_Sector', 'Sector'): None}
for t in TABLES:
    types = col_types(f'{t}.csv')
    L = [f'table {q(t)}', f'\tlineageTag: {tag(t)}', '']
    for c, ty in types.items():
        L += column_block(t, c, ty, sort_by=SORT_BY.get((t, c)))
    extra = ',\n    Result = Typed'
    if t == 'Dim_Lever':  # friendlier label for the bar chart
        L += column_block(t, 'Lever_Label', 'string', sort_by='Sort')
        extra = ',\n    Result = Table.AddColumn(Typed, "Lever_Label", each if [Lever] = "None" then "No new policy" else [Lever], type text)'
    L += m_block(t, csv_m(f'{t}.csv', types, extra))
    files[t] = L

# what-if table: India's share of world lithium supply
SHARES = [(f'{p:g}%', p / 100, i) for i, p in enumerate([1, 2, 3, 4, 5, 6])]
WS = ['table World_Share', f'\tlineageTag: {tag("World_Share")}', '']
WS += column_block('World_Share', 'Share_Label', 'string', sort_by='Sort')
WS += column_block('World_Share', 'Share', 'double')
WS += column_block('World_Share', 'Sort', 'int64', hidden=True)
WS += m_block('World_Share', '#table(type table [Share_Label = text, Share = number, Sort = Int64.Type], {'
              + ', '.join(f'{{"{a}", {b}, {c}}}' for a, b, c in SHARES) + '})')
files['World_Share'] = WS

# ---------------- measures ----------------
MS = []


def meas(folder, name, expr, fmt, cat=None):
    lines = expr.strip('\n').split('\n')
    if len(lines) == 1:
        MS.append(f'\tmeasure {q(name)} = {lines[0]}')
    else:
        MS.extend([f'\tmeasure {q(name)} =', *['\t\t\t' + l for l in lines]])
    MS.extend([f'\t\tformatString: {fmt}', f'\t\tdisplayFolder: {folder}', f'\t\tlineageTag: {tag("m", name)}']
              + ([f'\t\tdataCategory: {cat}'] if cat else []) + [''])


FB = 'Fact_Balance'
A = '1. Lithium balance'
meas(A, 'World Share', 'SELECTEDVALUE(World_Share[Share], 0.03)', '0%')
meas(A, 'Scenario Name', 'SELECTEDVALUE(Dim_Scenario[Scenario], "Base")', 'General')
meas(A, 'Demand t', f'SUM({FB}[Demand_t_LCE])', '#,##0')
meas(A, 'Energy Demand t', f'SUM({FB}[Energy_Demand_t_LCE])', '#,##0')
meas(A, 'Non-energy Demand t', f'SUM({FB}[NonEnergy_Demand_t_LCE])', '#,##0')
meas(A, 'Recycling t', f'SUM({FB}[Recycling_t_LCE])', '#,##0')
meas(A, 'Mining t', f'SUM({FB}[Domestic_Mining_t_LCE])', '#,##0')
meas(A, 'Overseas t', f'SUM({FB}[Overseas_Equity_t_LCE])', '#,##0')
meas(A, 'Imports in Reach t', f'''-- open-market imports are capped at India's share of world supply (the slicer)
VAR sh = [World Share]
RETURN SUMX({FB}, {FB}[Global_Supply_t_LCE] * sh)''', '#,##0')
meas(A, 'Supply in Reach t', '[Recycling t] + [Mining t] + [Overseas t] + [Imports in Reach t]', '#,##0')
meas(A, 'Shortfall t', f'''VAR sh = [World Share]
RETURN SUMX({FB},
    VAR avail = {FB}[Recycling_t_LCE] + {FB}[Domestic_Mining_t_LCE] + {FB}[Overseas_Equity_t_LCE] + {FB}[Global_Supply_t_LCE] * sh
    RETURN MAX(0, {FB}[Demand_t_LCE] - avail))''', '#,##0')
meas(A, 'Energy Coverage', f'''-- non-energy uses are served first; EVs and storage get what is left
VAR sh = [World Share]
VAR met = SUMX({FB},
    VAR avail = {FB}[Recycling_t_LCE] + {FB}[Domestic_Mining_t_LCE] + {FB}[Overseas_Equity_t_LCE] + {FB}[Global_Supply_t_LCE] * sh
    RETURN MIN({FB}[Energy_Demand_t_LCE], MAX(0, avail - {FB}[NonEnergy_Demand_t_LCE])))
RETURN DIVIDE(met, [Energy Demand t])''', '0%')
meas(A, 'Import Dependence', f'DIVIDE(SUM({FB}[Net_Import_Need_t_LCE]), [Demand t])', '0%')
meas(A, 'Recycled Content', f'AVERAGE({FB}[Recycled_Content_Share])', '0%')
meas(A, 'Non-energy Share', 'DIVIDE([Non-energy Demand t], [Demand t])', '0%')
meas(A, 'First Gap Year', '''MINX(
    FILTER(CALCULATETABLE(VALUES(Dim_Year[Year]), REMOVEFILTERS(Dim_Year)), [Shortfall t] > 1),
    Dim_Year[Year])''', '0')
for m in ['Demand', 'Supply in Reach', 'Shortfall', 'Recycling', 'Mining', 'Overseas', 'Imports in Reach']:
    meas('2. Charts (kt)', f'{m} kt', f'DIVIDE([{m} t], 1000)', '#,##0.0')
meas('2. Charts (kt)', 'Sector Demand kt', 'DIVIDE(SUM(Fact_Demand[Demand_t_LCE]), 1000)', '#,##0.0')
meas('2. Charts (kt)', 'Gap Left kt', '''-- shortfall in the selected year for each lever; the lever slicer is ignored on purpose
DIVIDE(CALCULATE([Shortfall t], REMOVEFILTERS(Dim_Lever), VALUES(Dim_Lever[Lever])), 1000)''', '#,##0')
meas('2. Charts (kt)', 'Gap Colour', '''VAR lv = SELECTEDVALUE(Dim_Lever[Lever])
VAR none = CALCULATE([Gap Left kt], REMOVEFILTERS(Dim_Lever), Dim_Lever[Lever] = "None")
RETURN IF(lv = "None", "#6B6B6B", IF([Gap Left kt] < none / 2, "#1F4E79", "#9BB3CC"))''', 'General')

P = '3. Page text'
y = lambda e, yr: f'CALCULATE({e}, Dim_Year[Year] = {yr})'
meas(P, 'Growth to 2040', f'DIVIDE({y("[Demand t]", 2040)}, {y("[Demand t]", 2025)})', '0')
meas(P, 'Page Year', 'SELECTEDVALUE(Dim_Year[Year], 2040)', '0')
meas(P, 'No Lever Gap t', 'VAR yr = [Page Year]\nRETURN CALCULATE([Shortfall t], Dim_Lever[Lever] = "None", Dim_Year[Year] = yr)', '#,##0')
meas(P, 'Best Lever', '''-- the single lever (not the bundle) that closes the most of the gap in the page year
VAR yr = [Page Year]
VAR base = [No Lever Gap t]
VAR t = ADDCOLUMNS(
    FILTER(ALL(Dim_Lever[Lever]), NOT Dim_Lever[Lever] IN {"None", "All four levers"}),
    "@closed", base - CALCULATE([Shortfall t], Dim_Year[Year] = yr))
RETURN MAXX(TOPN(1, t, [@closed], DESC), Dim_Lever[Lever])''', 'General')
meas(P, 'Best Lever Closed t', '''VAR yr = [Page Year]
VAR lv = [Best Lever]
RETURN [No Lever Gap t] - CALCULATE([Shortfall t], Dim_Lever[Lever] = lv, Dim_Year[Year] = yr)''', '#,##0')
meas(P, 'Mining Lever Closed t', '''VAR yr = [Page Year]
RETURN [No Lever Gap t] - CALCULATE([Shortfall t], Dim_Lever[Lever] = "Exploration fast-track", Dim_Year[Year] = yr)''', '#,##0')
meas(P, 'Sub-sector 2025 t', 'CALCULATE(SUM(Fact_Demand[Demand_t_LCE]), Dim_Year[Year] = 2025)', '#,##0')

# ---- SVG text blocks (image visuals). Static text is URL-encoded here; dynamic text is encoded in DAX.
V = '4. Report visuals'
INK, MUT, ACC, BLUE, RULE = '%23222222', '%236B6B6B', '%23C0392B', '%231F4E79', '%23DDDDDD'
FONT = 'Segoe UI, Arial, sans-serif'
SVG0 = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'"


def enc_static(s): return s.replace('&', '&amp;').replace('%', '%25').replace('#', '%23').replace('<', '&lt;')


def enc_dax(e): return f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({e}, "&", "&amp;"), "%", "%25"), "#", "%23"), "<", "&lt;")'


def T(x, y, size, color, content, weight='normal', anchor='start', spacing=None):
    """One line of text. content: str (static) or list of str / ('d', dax) pieces."""
    pieces = [content] if isinstance(content, (str, tuple)) else content
    ls = f" letter-spacing='{spacing}'" if spacing else ''
    out = [f"<text x='{x}' y='{y}' font-family='{FONT}' font-size='{size}' font-weight='{weight}' fill='{color}' text-anchor='{anchor}'{ls}>"]
    for p in pieces:
        out.append(p if isinstance(p, tuple) else enc_static(p))
    out.append('</text>')
    return out


def svg_measure(name, w, h, parts):
    """parts: list of static svg strings and ('d', dax) tuples."""
    expr, buf = [], f"{SVG0} width='{w}' height='{h}' viewBox='0 0 {w} {h}'>"
    for p in parts:
        if isinstance(p, tuple):
            expr.append('"' + buf.replace('"', '""') + '"')
            expr.append(enc_dax(p[1]))
            buf = ''
        else:
            buf += p
    buf += '</svg>'
    expr.append('"' + buf.replace('"', '""') + '"')
    meas(V, name, '\n    & '.join(expr), 'General', cat='ImageUrl')


def d(e): return ('d', e)


def F(e, fmt): return d(f'FORMAT({e}, "{fmt}")')


def ktx(e): return d(f'FORMAT(DIVIDE({e}, 1000), "#,0")')


# top band: kicker on the left, page tabs on the right (buttons sit on top of the tabs)
PAGES_DEF = [('Overview', 'Overview'), ('WhoUsesIt', 'Who uses it'), ('WhereFrom', 'Where it comes from'), ('ClosingGap', 'What closes the gap')]
TAB_W = [len(lbl) * 7.4 + 22 for _, lbl in PAGES_DEF]
TAB_X = []
x = 1200
for w in reversed(TAB_W):
    x -= w
    TAB_X.insert(0, x)


def top_band(pid, kicker):
    parts = T(0, 22, 12, ACC, kicker.upper(), 'bold', spacing='1')
    for (p, lbl), tx, tw in zip(PAGES_DEF, TAB_X, TAB_W):
        on = p == pid
        parts += T(round(tx + tw - 2), 22, 12.5, INK if on else MUT, lbl, '600' if on else 'normal', 'end')
        if on:
            parts.append(f"<rect x='{round(tx + 20)}' y='29' width='{round(tw - 22)}' height='2' fill='{ACC}'/>")
    svg_measure(f'Top {pid}', 1200, 34, parts)


def headline(pid, line1, line2, dek):
    svg_measure(f'Headline {pid}', 1060, 104, T(0, 28, 27, INK, line1, 'bold') + T(0, 62, 27, INK, line2, 'bold') + T(0, 92, 14, MUT, dek))


def things(pid, items, title='Three things to know', h=400):
    """items: (big value pieces, [line pieces, ...])"""
    parts = T(0, 14, 12, MUT, title.upper(), '600', spacing='0.8')
    yy = 30
    for big, lines in items:
        parts.append(f"<rect x='0' y='{yy}' width='366' height='1' fill='{RULE}'/>")
        parts += T(0, yy + 33, 24, INK, big, 'bold')
        for i, ln in enumerate(lines):
            parts += T(0, yy + 55 + i * 18, 13, '%23444444', ln)
        yy += 55 + len(lines) * 18 + 10
    svg_measure(f'Things {pid}', 370, h, parts)


def footer(pid, extra=''):
    svg_measure(f'Footer {pid}', 1200, 24, [f"<rect x='0' y='0' width='1200' height='1' fill='%23EEEEEE'/>"]
                + T(0, 17, 11, MUT, 'Source: model built on USGS, IEA, CEA, IESA, IDC and UN Comtrade data. ' + extra))


SC, SH = d('[Scenario Name]'), d('FORMAT([World Share], "0%")')
NE25 = f'CALCULATE([Non-energy Share], Dim_Year[Year] = 2025)'

# page 1
top_band('Overview', 'India lithium outlook, 2025 to 2040')
headline('Overview', ['India will need ', F('[Growth to 2040]', '0'), ' times more lithium by 2040.'],
         [d('IF(ISBLANK([First Gap Year]), "At this share of world supply, there is enough to go round.", '
            '"From " & [First Gap Year] & ", there isn\'t enough for EVs and storage.")')],
         ['Thousand tonnes of lithium carbonate equivalent (kt LCE) a year. ', SC, " case. India gets ", SH, " of the world's lithium."])
things('Overview', [
    ([F(NE25, '0%')], [["of India's lithium in 2025 went to phones, laptops,"], ['grease, glass and defence, not clean energy.'], ['Worldwide it is 12%.']]),
    ([F('CALCULATE([Energy Coverage], Dim_Year[Year] = 2040)', '0%')], [['of EV and storage demand can be met in 2040.'],
                                                                        ['Phones and grease are served first because'], ['they can pay more.']]),
    ([d('IF([No Lever Gap t] < 1, "No gap", [Best Lever])')],
     [[d('IF([No Lever Gap t] < 1, "With these settings India has enough lithium", '
         '"is the biggest single fix. It closes " & FORMAT(DIVIDE([Best Lever Closed t], 1000), "#,0") & " of the")')],
      [d('IF([No Lever Gap t] < 1, "through 2040.", FORMAT(DIVIDE([No Lever Gap t], 1000), "#,0") & " kt gap in 2040.")')]]),
])
footer('Overview', '"Supply India can reach" = recycling + mining in India + overseas mines + India\'s share of world output.')

# page 2
top_band('WhoUsesIt', "Who uses India's lithium")
headline('WhoUsesIt', ['In 2025, ', F(NE25, '0%'), " of India's lithium went to phones, grease and other"],
         ['non-energy uses. By 2040, EVs take ', F('CALCULATE(DIVIDE([Sector Demand kt], [Demand kt]), Dim_Year[Year] = 2040, Dim_Sector[Sector] = "EVs")', '0%'), '.'],
         ['Share of lithium demand by use, ', SC, ' case.'])
things('WhoUsesIt', [
    ([F('DIVIDE(CALCULATE([Sub-sector 2025 t], Dim_Sector[Sub_Sector] = "ELEC_ExportAssembly"), 1000)', '0.0'), ' kt'],
     [['a year goes into phones assembled in India for'], ['export. That lithium leaves the country and never'], ['comes back for recycling.']]),
    ([F('DIVIDE(CALCULATE([Sub-sector 2025 t], Dim_Sector[Sub_Sector] = "IND_Grease"), 1000)', '0.0'), ' kt'],
     [['goes into lubricating grease. 77% of the lithium'], ['hydroxide behind it came from Russia in 2023.']]),
    (['12%'], [['is the non-energy share worldwide (USGS). India is'],
               ['higher because its EV fleet is still small. It drops to'],
               [F('CALCULATE([Non-energy Share], Dim_Year[Year] = 2040)', '0%'), ' by 2040.']]),
])
footer('WhoUsesIt', 'Defence is an estimate, since no public data exists.')

# page 3
top_band('WhereFrom', "Where India's lithium could come from")
headline('WhereFrom', ["Recycling becomes India's biggest home source of lithium,"], ['but only from the mid-2030s.'],
         ['Supply India can reach by source, against demand (kt LCE a year). ', SC, ' case, ', SH, ' of world supply.'])
things('WhereFrom', [
    ([F('CALCULATE([Recycled Content], Dim_Year[Year] = 2030)', '0%')],
     [["is the recycled content India's own scrap can supply"], ['in 2030. The battery rules ask for 20%. Most'], ['batteries sold today retire after 2032.']]),
    (['18 kt'], [["is all the lithium in Reasi, India's only proven find"], ['(583 ppm, Lok Sabha 2024). That is about seven'], ['weeks of 2035 demand in the Base case.']]),
    ([F('CALCULATE([Import Dependence], Dim_Year[Year] = 2040)', '0%')],
     [["of India's lithium is still imported in 2040, down"], ['from ', F('CALCULATE([Import Dependence], Dim_Year[Year] = 2025)', '0%'), ' in 2025.']]),
])
footer('WhereFrom', "Imports are capped at India's share of world output, set with the slicer.")

# page 4
top_band('ClosingGap', 'What closes the gap')
LEVER_PHRASE = ('SWITCH([Best Lever], "Overseas assets", "Buying into overseas mines", "Sodium-ion push", "Switching to sodium-ion batteries", '
                '"Recycling push", "Recycling more", "Exploration fast-track", "Fast-tracking mines at home", [Best Lever])')
headline('ClosingGap',
         [d(f'IF([No Lever Gap t] < 1, "With these settings there is no gap to close in " & [Page Year] & ".", {LEVER_PHRASE} & IF([Best Lever Closed t] >= [No Lever Gap t] / 2, " closes most of the gap.", " closes more of the gap than any other step."))')],
         [d('IF([No Lever Gap t] < 1, "Try the High case or a lower share of world supply.", '
            '"Mining at home closes only " & FORMAT(DIVIDE([Mining Lever Closed t], 1000), "0.0") & " kt of it.")')],
         ['Lithium gap left in ', d('[Page Year]'), ' with each policy lever (kt LCE). ', SC, ' case, ', SH,
          ' of world supply. Gap with no new policy: ', ktx('[No Lever Gap t]'), ' kt.'])
svg_measure('Things ClosingGap', 370, 24, T(0, 14, 12, MUT, "INDIA'S VALUE CHAIN TODAY", '600', spacing='0.8'))
svg_measure('Note ClosingGap', 370, 90, [f"<rect x='0' y='0' width='366' height='1' fill='{RULE}'/>"]
            + T(0, 22, 13, '%23444444', 'India is missing almost every step between the mine')
            + T(0, 41, 13, '%23444444', 'and the cell. Lithium is only about $5 of each kWh of')
            + T(0, 60, 13, '%23444444', 'battery, so the money is in cathode and cell making,')
            + T(0, 79, 13, '%23444444', 'not in mining.'))
footer('ClosingGap', 'Levers: Recycling push, Overseas assets, Sodium-ion push and Exploration fast-track are defined in the model workbook.')

files['_Measures'] = ['table _Measures', f'\tlineageTag: {tag("_Measures")}', ''] + MS + \
    column_block('_Measures', 'Placeholder', 'string', hidden=True) + m_block('_Measures', '#table(type table [Placeholder = text], {})')

RELS = [(FB, 'Scenario', 'Dim_Scenario', 'Scenario'), (FB, 'Lever', 'Dim_Lever', 'Lever'), (FB, 'Year', 'Dim_Year', 'Year'),
        ('Fact_Demand', 'Scenario', 'Dim_Scenario', 'Scenario'), ('Fact_Demand', 'Lever', 'Dim_Lever', 'Lever'),
        ('Fact_Demand', 'Year', 'Dim_Year', 'Year'), ('Fact_Demand', 'Sub_Sector', 'Dim_Sector', 'Sub_Sector')]

if OUT.exists():
    shutil.rmtree(OUT)
dm = OUT / SM / 'definition'
(dm / 'tables').mkdir(parents=True)
order = list(files)
(dm / 'database.tmdl').write_text('database ProjectI\n\tcompatibilityLevel: 1600\n\n')
(dm / 'model.tmdl').write_text('model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\tsourceQueryCulture: en-US\n'
                               '\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n'
                               'annotation __PBI_TimeIntelligenceEnabled = 0\n\n'
                               f'annotation PBI_QueryOrder = {json.dumps(["DataFolder"] + order)}\n\n'
                               + ''.join(f'ref table {q(t)}\n' for t in order))
(dm / 'expressions.tmdl').write_text(f'/// Folder holding the Project I CSV files. Keep the backslash at the end.\n'
                                     f'expression DataFolder = "{DEFAULT_FOLDER}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
                                     f'\tlineageTag: {tag("DataFolder")}\n\n\tannotation PBI_ResultType = Text\n')
(dm / 'relationships.tmdl').write_text(''.join(f'relationship {tag("rel", a, b, c2)}\n\tfromColumn: {q(a)}.{q(b)}\n\ttoColumn: {q(c)}.{q(c2)}\n\n'
                                               for a, b, c, c2 in RELS))
(dm / 'cultures').mkdir()
(dm / 'cultures' / 'en-US.tmdl').write_text('cultureInfo en-US\n\n\tlinguisticMetadata =\n\t\t\t{\n\t\t\t  "Version": "1.0.0",\n\t\t\t  "Language": "en-US"\n\t\t\t}\n\t\tcontentType: json\n\n')
for t, L in files.items():
    (dm / 'tables' / f'{t}.tmdl').write_text('\n'.join(L).rstrip('\n') + '\n')
(OUT / SM / 'definition.pbism').write_text(json.dumps({'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json',
                                                       'version': '4.2', 'settings': {}}, indent=2))

# ---------------- report ----------------
VCS = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json'
MEAS = '_Measures'
WHITE, INKC, MUTC, GRIDC, BLUEC, ACCC = '#FFFFFF', '#222222', '#6B6B6B', '#E6E6E6', '#1F4E79', '#C0392B'
SECTOR_COL = {'EVs': '#2E7D55', 'Grid storage': '#D1A03A', 'Electronics': '#3F6FB0', 'Defence and aerospace': '#C4502F', 'Industry': '#8A5BB0'}


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


def bare():
    o = {k: [{'properties': {'show': lit('false')}}] for k in ('title', 'subTitle', 'background', 'border', 'dropShadow', 'divider', 'visualHeader')}
    o['padding'] = [{'properties': {k: lit('0D') for k in ('top', 'bottom', 'left', 'right')}}]
    return o


def container(name, x, y, w, h, v, z, filters=None):
    o = {'$schema': VCS, 'name': name, 'position': {'x': x, 'y': y, 'z': z, 'width': w, 'height': h, 'tabOrder': z}, 'visual': v}
    if filters: o['filterConfig'] = {'filters': filters}
    return o


def in_filter(name, f, values, alias='t'):
    kind, e, p = f
    return {'name': name, 'field': fref(f), 'type': 'Categorical',
            'filter': {'Version': 2, 'From': [{'Name': alias, 'Entity': e, 'Type': 0}],
                       'Where': [{'Condition': {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': alias}}, 'Property': p}}],
                                                       'Values': [[{'Literal': {'Value': v}}] for v in values]}}}]}}


def image(name, measure, x, y, w, h, z):
    v = {'visualType': 'image', 'drillFilterOtherVisuals': True,
         'objects': {'image': [{'properties': {'sourceType': s('imageData'), 'transparency': lit('0D'), 'effects': lit('false'),
                                               'sourceField': {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': MEAS}}, 'Property': measure}}}}}],
                     'imageScaling': [{'properties': {'imageScalingType': s('Normal')}}]},
         'visualContainerObjects': bare()}
    return container(name, x, y, w, h, v, z)


def nav_button(name, target, x, y, w, h, z):
    sel = {'id': 'default'}
    v = {'visualType': 'actionButton', 'drillFilterOtherVisuals': True,
         'objects': {'icon': [{'properties': {'shapeType': s('blank')}, 'selector': sel}],
                     'fill': [{'properties': {'show': lit('false')}, 'selector': sel}],
                     'outline': [{'properties': {'show': lit('false'), 'transparency': lit('100D'), 'weight': lit('0D')}, 'selector': {'id': st}}
                                 for st in ('default', 'hover', 'press', 'disabled')],
                     'text': [{'properties': {'show': lit('false')}, 'selector': sel}]},
         'visualContainerObjects': {**bare(), 'visualLink': [{'properties': {'show': lit('true'), 'type': s('PageNavigation'), 'navigationSection': s(target)}}]}}
    return container(name, x, y, w, h, v, z)


def slicer(name, f, x, y, w, h, z, label, default, group):
    o = {'data': [{'properties': {'mode': s('Dropdown')}}],
         'selection': [{'properties': {'singleSelect': lit('true')}}],
         'header': [{'properties': {'show': lit('true'), 'text': s(label), 'fontColor': col(MUTC), 'textSize': lit('9D')}}],
         'items': [{'properties': {'fontColor': col(INKC), 'textSize': lit('11D'), 'background': col(WHITE)}}],
         'general': [{'properties': {'filter': {'filter': in_filter('d', f, [default])['filter']}}}]}
    v = {'visualType': 'slicer', 'drillFilterOtherVisuals': True,
         'query': {'queryState': {'Values': {'projections': [proj(f, active=True)]}}},
         'objects': o, 'syncGroup': {'groupName': group, 'fieldChanges': True, 'filterChanges': True}, 'visualContainerObjects': bare()}
    return container(name, x, y, w, h, v, z)


def axes(legend):
    return {'categoryAxis': [{'properties': {'show': lit('true'), 'labelColor': col(MUTC), 'fontSize': lit('10D'), 'showAxisTitle': lit('false')}}],
            'valueAxis': [{'properties': {'show': lit('true'), 'labelColor': col(MUTC), 'fontSize': lit('10D'), 'showAxisTitle': lit('false'),
                                          'gridlineShow': lit('true'), 'gridlineColor': col(GRIDC)}}],
            'legend': [{'properties': {'show': lit('true'), 'position': s('Top'), 'showTitle': lit('false'), 'labelColor': col(INKC), 'fontSize': lit('11D')}}] if legend
            else [{'properties': {'show': lit('false')}}]}


def series_colours(series):
    return [{'properties': {'fill': col(c)}, 'selector': {'metadata': f'{MEAS}.{m}'}} for m, _, c in series]


YEAR = C('Dim_Year', 'Year')


def line_chart(name, x, y, w, h, z, series):
    o = axes(True)
    o['dataPoint'] = series_colours(series)
    o['lineStyles'] = [{'properties': {'strokeWidth': lit('3D'), 'showMarker': lit('false')}}]
    qs = {'queryState': {'Category': {'projections': [proj(YEAR, active=True)]}, 'Y': {'projections': [proj(Mz(m), label=lb) for m, lb, _ in series]}}}
    return container(name, x, y, w, h, {'visualType': 'lineChart', 'drillFilterOtherVisuals': True, 'query': qs, 'objects': o,
                                        'visualContainerObjects': bare()}, z)


def share_chart(name, x, y, w, h, z):
    o = axes(True)
    sec = C('Dim_Sector', 'Sector')
    o['dataPoint'] = [{'properties': {'fill': col(c)},
                       'selector': {'data': [{'scopeId': {'Comparison': {'ComparisonKind': 0, 'Left': fref(sec), 'Right': {'Literal': {'Value': f"'{k}'"}}}}}]}}
                      for k, c in SECTOR_COL.items()]
    qs = {'queryState': {'Category': {'projections': [proj(YEAR, active=True)]}, 'Series': {'projections': [proj(sec)]},
                         'Y': {'projections': [proj(Mz('Sector Demand kt'), label='Demand (kt LCE)')]}}}
    return container(name, x, y, w, h, {'visualType': 'hundredPercentStackedColumnChart', 'drillFilterOtherVisuals': True, 'query': qs, 'objects': o,
                                        'visualContainerObjects': bare()}, z)


def supply_chart(name, x, y, w, h, z):
    cols = [('Recycling kt', 'Recycling', '#2E7D55'), ('Mining kt', 'Mining in India', '#C4502F'),
            ('Overseas kt', 'Overseas mines', '#D1A03A'), ('Imports in Reach kt', 'Import cap', '#7FA3C9')]
    line = [('Demand kt', 'Demand', INKC)]
    o = axes(True)
    o['valueAxis'][0]['properties']['secShow'] = lit('false')  # line shares the left axis
    o['dataPoint'] = series_colours(cols + line)
    o['lineStyles'] = [{'properties': {'strokeWidth': lit('3D'), 'showMarker': lit('false')}}]
    qs = {'queryState': {'Category': {'projections': [proj(YEAR, active=True)]},
                         'Y': {'projections': [proj(Mz(m), label=lb) for m, lb, _ in cols]},
                         'Y2': {'projections': [proj(Mz(m), label=lb) for m, lb, _ in line]}}}
    return container(name, x, y, w, h, {'visualType': 'lineStackedColumnComboChart', 'drillFilterOtherVisuals': True, 'query': qs, 'objects': o,
                                        'visualContainerObjects': bare()}, z)


def lever_chart(name, x, y, w, h, z):
    o = axes(False)
    o['categoryAxis'][0]['properties']['fontSize'] = lit('12D')
    o['categoryAxis'][0]['properties']['labelColor'] = col(INKC)
    o['valueAxis'][0]['properties']['show'] = lit('false')
    o['dataPoint'] = [{'properties': {'fill': {'solid': {'color': {'expr': fref(Mz('Gap Colour'))}}}},
                       'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}]}}]
    o['labels'] = [{'properties': {'show': lit('true'), 'color': col(INKC), 'fontSize': lit('12D'), 'labelDisplayUnits': lit('1D')}}]
    lv = C('Dim_Lever', 'Lever_Label')
    qs = {'queryState': {'Category': {'projections': [proj(lv, active=True)]}, 'Y': {'projections': [proj(Mz('Gap Left kt'), label='Gap left (kt LCE)')]}},
          'sortDefinition': {'sort': [{'field': fref(Mz('Gap Left kt')), 'direction': 'Descending'}], 'isDefaultSort': True}}
    return container(name, x, y, w, h, {'visualType': 'clusteredBarChart', 'drillFilterOtherVisuals': True, 'query': qs, 'objects': o,
                                        'visualContainerObjects': bare()}, z)


def chain_table(name, x, y, w, h, z):
    o = {'columnHeaders': [{'properties': {'fontColor': col(MUTC), 'backColor': col(WHITE), 'fontSize': lit('10D'), 'bold': lit('false')}}],
         'values': [{'properties': {'fontColor': col(INKC), 'fontSize': lit('11D'), 'backColorPrimary': col(WHITE), 'backColorSecondary': col(WHITE)}}],
         'grid': [{'properties': {'gridHorizontal': lit('true'), 'gridHorizontalColor': col('#EEEEEE'), 'gridVertical': lit('false'), 'rowPadding': lit('4D')}}],
         'total': [{'properties': {'totals': lit('false')}}]}
    qs = {'queryState': {'Values': {'projections': [proj(C('Ref_Value_Chain', 'Stage'), label='Stage'), proj(C('Ref_Value_Chain', 'India_Status'), label='Where India is')]}},
          'sortDefinition': {'sort': [{'field': fref(C('Ref_Value_Chain', 'Stage')), 'direction': 'Ascending'}], 'isDefaultSort': True}}
    return container(name, x, y, w, h, {'visualType': 'tableEx', 'drillFilterOtherVisuals': True, 'query': qs, 'objects': o,
                                        'visualContainerObjects': bare()}, z)


# layout (1280 x 720)
LX, CHART_Y, CHART_W, CHART_H = 40, 168, 800, 500
SIDE_X, SIDE_W = 870, 370
SCEN, LEVER, SHARE = C('Dim_Scenario', 'Scenario'), C('Dim_Lever', 'Lever'), C('World_Share', 'Share_Label')
PAGES = []


def page(pid, display, chart_fn, side, slicers):
    vis = [image(f'{pid}_top', f'Top {pid}', LX, 14, 1200, 34, 0),
           image(f'{pid}_headline', f'Headline {pid}', LX, 56, 1060, 104, 1),
           image(f'{pid}_footer', f'Footer {pid}', LX, 690, 1200, 24, 2)]
    for i, ((target, _), tx, tw) in enumerate(zip(PAGES_DEF, TAB_X, TAB_W)):
        if target != pid:
            vis.append(nav_button(f'{pid}_go{i}', target, round(LX + tx + 14), 12, round(tw - 10), 30, 10 + i))
    vis.append(chart_fn(f'{pid}_chart', LX, CHART_Y, CHART_W, CHART_H, 20))
    sy = side(vis)
    sw = (SIDE_W - 2 * 10) // 3
    for i, (f, label, default, group) in enumerate(slicers):
        vis.append(slicer(f'{pid}_slicer{i}', f, SIDE_X + i * (sw + 10), sy, sw, 56, 100 + i, label, default, group))
    PAGES.append((pid, display, vis))


def things_side(pid, h=400):
    def f(vis):
        vis.append(image(f'{pid}_things', f'Things {pid}', SIDE_X, CHART_Y, SIDE_W, h, 30))
        return CHART_Y + h + 10
    return f


STD = [(SCEN, 'Scenario', "'Base'", 'scenario'), (LEVER, 'Policy lever', "'None'", 'lever'), (SHARE, 'World share', "'3%'", 'share')]
page('Overview', 'Overview',
     lambda n, x, y, w, h, z: line_chart(n, x, y, w, h, z, [('Demand kt', 'Demand', INKC), ('Supply in Reach kt', 'Supply India can reach', BLUEC)]),
     things_side('Overview'), STD)
page('WhoUsesIt', 'Who uses it', share_chart, things_side('WhoUsesIt'), STD)
page('WhereFrom', 'Where it comes from', supply_chart, things_side('WhereFrom'), STD)


def gap_side(vis):
    vis.append(image('ClosingGap_things', 'Things ClosingGap', SIDE_X, CHART_Y, SIDE_W, 24, 30))
    vis.append(chain_table('ClosingGap_chain', SIDE_X, CHART_Y + 26, SIDE_W, 262, 31))
    vis.append(image('ClosingGap_note', 'Note ClosingGap', SIDE_X, CHART_Y + 296, SIDE_W, 90, 32))
    return CHART_Y + 396


page('ClosingGap', 'What closes the gap', lever_chart, gap_side,
     [(SCEN, 'Scenario', "'Base'", 'scenario'), (C('Dim_Year', 'Year'), 'Year', '2040L', 'year'), (SHARE, 'World share', "'3%'", 'share')])
# the page 4 year slicer only offers the milestone years
for v in PAGES[-1][2]:
    if v['name'] == 'ClosingGap_slicer1':
        v['filterConfig'] = {'filters': [in_filter('milestones', C('Dim_Year', 'Is_Milestone'), ['true'])]}

r = OUT / RP
dd = r / 'definition'
(dd / 'pages').mkdir(parents=True)
(r / 'StaticResources' / 'SharedResources' / 'BaseThemes').mkdir(parents=True)
shutil.copy(THEME, r / 'StaticResources' / 'SharedResources' / 'BaseThemes' / 'CY24SU10.json')


def wj(p, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=2, ensure_ascii=False))


wj(r / 'definition.pbir', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json',
                           'version': '4.0', 'datasetReference': {'byPath': {'path': f'../{SM}'}}})
wj(dd / 'version.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json', 'version': '2.0.0'})
wj(dd / 'report.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.0.0/schema.json',
                        'themeCollection': {'baseTheme': {'name': 'CY24SU10', 'reportVersionAtImport': {'visual': '1.8.95', 'report': '2.0.95', 'page': '1.3.95'},
                                                          'type': 'SharedResources'}},
                        'resourcePackages': [{'name': 'SharedResources', 'type': 'SharedResources',
                                              'items': [{'name': 'CY24SU10', 'path': 'BaseThemes/CY24SU10.json', 'type': 'BaseTheme'}]}],
                        'settings': {'useStylableVisualContainerHeader': True, 'exportDataMode': 'AllowSummarized', 'defaultDrillFilterOtherVisuals': True,
                                     'allowChangeFilterTypes': True, 'useEnhancedTooltips': True, 'useDefaultAggregateDisplayName': True}})
wj(dd / 'pages' / 'pages.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json',
                                 'pageOrder': [p[0] for p in PAGES], 'activePageName': PAGES[0][0]})
for pid, display, vis in PAGES:
    wj(dd / 'pages' / pid / 'page.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json',
                                          'name': pid, 'displayName': display, 'displayOption': 'FitToPage', 'height': 720, 'width': 1280,
                                          'objects': {'background': [{'properties': {'color': col(WHITE), 'transparency': lit('0D')}}],
                                                      'outspace': [{'properties': {'color': col(WHITE), 'transparency': lit('0D')}}]}})
    for v in vis:
        wj(dd / 'pages' / pid / 'visuals' / v['name'] / 'visual.json', v)

wj(OUT / 'ProjectI.pbip', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json',
                           'version': '1.0', 'artifacts': [{'report': {'path': RP}}], 'settings': {'enableAutoRecovery': True}})
for folder, kind in ((RP, 'Report'), (SM, 'SemanticModel')):
    wj(OUT / folder / '.platform', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json',
                                    'metadata': {'type': kind, 'displayName': 'ProjectI'}, 'config': {'version': '2.0', 'logicalId': tag('platform', kind)}})
(OUT / '.gitignore').write_text('**/.pbi/localSettings.json\n**/.pbi/cache.abf\n')
print('tables', len(files), 'measures', sum(1 for l in MS if l.startswith('\tmeasure')), 'pages', len(PAGES), 'visuals', sum(len(p[2]) for p in PAGES))

(OUT / 'HOW_TO_OPEN.md').write_text(f'''# Opening the Project I Power BI project

1. Copy the CSV files from `data/clean/` into `{DEFAULT_FOLDER}`, or point the DataFolder parameter at `data/clean/` in your clone.
2. Double-click **ProjectI.pbip**. You need a recent Power BI Desktop.
3. If you used a different data folder, go to Home > Transform data > Edit parameters and set **DataFolder** to it. Keep the `\\` at the end.
4. Click **Refresh**.
5. Go to File > Save as and choose **.pbix** if you want a single file.

## Pages
- **Overview:** demand against the supply India can reach, and the year the gap opens.
- **Who uses it:** share of lithium demand by use, 2025 to 2040.
- **Where it comes from:** recycling, mining in India, overseas mines and imports, against demand.
- **What closes the gap:** the gap left in a milestone year with each policy lever, and India's value chain today.

The tabs at the top work as page buttons. In Desktop, hold Ctrl and click a tab; in the Power BI service a normal click works.
The three slicers (scenario, policy lever, India's share of world supply) are synced across pages.

## The model
- All measures are in the `_Measures` table, in four folders: Lithium balance, Charts (kt), Page text and Report visuals.
- India's share of world supply is a what-if table (`World_Share`, 1% to 6%). Imports, the shortfall and the share of EV and
  storage demand that can be met are recalculated from it in DAX, so the slicer works live. At 3% they match `Fact_Balance`.
- When supply is short, non-energy uses (phones, grease, glass, defence) are served first. EVs and storage get what is left.
- The headlines, "three things to know" and the tab bar are SVG images built by measures in `4. Report visuals`, so the
  numbers in the text follow the slicers.
- To rebuild the project from the CSVs, run `scripts/05_build_powerbi_project.py`.
''')

# Project C: builds Project_C_Data_Cleaning.xlsx, the Excel workbook where the raw SAP exports are cleaned.
# Grey columns = raw export pasted as is. Blue columns = cleaning formulas. DQ_Log counts every issue with formulas.
# The clean CSVs are the blue columns (plus the IDs), with Is_Duplicate = TRUE rows filtered out.
import pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / 'data' / 'raw'
OUT = BASE / 'excel' / 'Project_C_Data_Cleaning.xlsx'
OUT.parent.mkdir(exist_ok=True)

GREY, BLUE, HEAD = PatternFill('solid', fgColor='D9D9D9'), PatternFill('solid', fgColor='FFF2CC'), Font(bold=True)
TEXT_COLS = {'Material', 'Plant', 'Business_Partner', 'Supplier', 'Sold_To', 'Sales_Document', 'Purchasing_Document', 'Order',
             'Parent_Material', 'Component', 'Fiscal_Period', 'Storage_Location', 'Class_Type', 'Created_On', 'Billing_Date',
             'Document_Date', 'Delivery_Date', 'Basic_Start', 'Basic_Finish', 'Valid_From', 'Customer_Since', 'Sales_Rep', 'Value'}
wb = Workbook()

def raw(name):
    return pd.read_csv(RAW / name, dtype=str, keep_default_na=False)

def sheet(title, df, formulas, widths=None):
    """df = raw columns (grey); formulas = list of (header, template) where {r} is the row number (blue)."""
    ws = wb.create_sheet(title)
    cols = list(df.columns)
    for j, c in enumerate(cols + [h for h, _ in formulas], 1):
        cell = ws.cell(1, j, c); cell.font = HEAD; cell.fill = GREY if j <= len(cols) else BLUE
    for i, row in enumerate(df.itertuples(index=False), 2):
        for j, (c, v) in enumerate(zip(cols, row), 1):
            if c not in TEXT_COLS and v != '':
                try: v = float(v)
                except ValueError: pass
            ws.cell(i, j, v)
        for k, (_, f) in enumerate(formulas):
            ws.cell(i, len(cols) + 1 + k, '=' + f.format(r=i, p=i - 1))
    ws.freeze_panes = 'B2'
    ws.auto_filter.ref = f'A1:{get_column_letter(ws.max_column)}{ws.max_row}'
    for j in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(j, max(10, len(str(ws.cell(1, j).value)) + 3))
    return ws, len(df) + 1

def date(c):  # text date in DD.MM.YYYY or YYYY-MM-DD -> real date
    return f'IF(MID({c}{{r}},3,1)=".",DATE(RIGHT({c}{{r}},4),MID({c}{{r}},4,2),LEFT({c}{{r}},2)),DATE(LEFT({c}{{r}},4),MID({c}{{r}},6,2),RIGHT({c}{{r}},2)))'

# ---------------- README + lookups
ws = wb.active; ws.title = 'Notes'
readme = [
    ('Project C - data cleaning (SAP exports, Jan 2022 - Sep 2026)', True),
    ('', False),
    ('Grey headers = raw export, as downloaded. Yellow headers = my cleaning columns.', False),
    ('Clean tables for Power BI = ID columns + yellow columns, with Is_Duplicate filtered to FALSE, saved as CSV.', False),
    ('Issue counts are on the DQ log tab. Mapping tables (countries, units etc.) are on Lookups.', False),
    ('', False),
    ('What I fixed', True),
    ('- dates came in two formats (31.01.2022 and 2022-01-31), converted both with DATE()', False),
    ('- some sales lines were in MT or LB, converted qty and price to kg', False),
    ('- SAP prices are per 1,000 kg, divided by Price_Unit', False),
    ('- 41 sales lines were exact copies, sorted by doc + item and flagged the repeat', False),
    ('- returns (order type RE) kept as negatives so totals are net', False),
    ('- CAS numbers: trimmed, removed "CAS" and notes in brackets, added the dashes, checked the check digit', False),
    ('- 3 chemicals we buy have the same CAS as ones we make (see Same_CAS_As on MARA)', False),
    ('- customer countries written 4-5 ways, mapped to ISO codes; 4 duplicate customers merged into the original', False),
    ('- blank sales rep -> Unassigned', False),
    ('- added std cost for the order year so I could get cost and margin', False),
    ('', False),
    ('Make-vs-buy by month and the customer health table are built in Python (scripts/02_clean_sap_exports.py).', False),
]
for i, (t, b) in enumerate(readme, 1):
    ws.cell(i, 1, t).font = Font(bold=b, size=12 if i == 1 else 11)
ws.column_dimensions['A'].width = 110

lk = wb.create_sheet('Lookups')
COUNTRY = [('US', 'US'), ('USA', 'US'), ('UNITED STATES', 'US'), ('U.S.A.', 'US'), ('CA', 'CA'), ('CANADA', 'CA'), ('MX', 'MX'), ('MEXICO', 'MX'),
           ('BR', 'BR'), ('BRAZIL', 'BR'), ('DE', 'DE'), ('GERMANY', 'DE'), ('NL', 'NL'), ('NETHERLANDS', 'NL'), ('BE', 'BE'), ('BELGIUM', 'BE'), ('IN', 'IN'), ('INDIA', 'IN')]
NAMES = [('US', 'United States'), ('CA', 'Canada'), ('MX', 'Mexico'), ('BR', 'Brazil'), ('DE', 'Germany'), ('NL', 'Netherlands'), ('BE', 'Belgium'), ('IN', 'India')]
UNITS = [('KG', 1), ('MT', 1000), ('LB', '=1/2.20462')]
TYPES = [('FERT', 'Finished good (made)'), ('HALB', 'Intermediate (made)'), ('ROH', 'Raw material (bought)'), ('HAWA', 'Traded good (bought for resale)')]
GROUPS = [('PLAST', 'Plasticizers'), ('OXOALC', 'Oxo alcohols'), ('ACRYL', 'Acrylates'), ('SOLV', 'Solvents'), ('GLYCOL', 'Glycols'), ('POLYOL', 'Polyols'),
          ('OXOINT', 'Intermediates'), ('FEED', 'Feedstocks'), ('CATAL', 'Catalysts'), ('ADDIT', 'Additives'), ('MRO', 'Maintenance supplies')]
blocks = [('A', 'Country as written', 'ISO code', COUNTRY), ('D', 'ISO code', 'Country', NAMES), ('G', 'SAP unit', 'kg per unit', UNITS),
          ('J', 'Material type', 'Type name', TYPES), ('M', 'Material group', 'Product group', GROUPS)]
RNG = {}
for colL, h1, h2, rows in blocks:
    c0 = ord(colL) - 64
    for j, h in enumerate((h1, h2)):
        cell = lk.cell(1, c0 + j, h); cell.font = HEAD; cell.fill = BLUE
    for i, (a, b) in enumerate(rows, 2):
        lk.cell(i, c0, a); lk.cell(i, c0 + 1, b)
    RNG[h1] = f"Lookups!${colL}$2:${chr(ord(colL) + 1)}${len(rows) + 1}"
    lk.column_dimensions[colL].width = 18; lk.column_dimensions[chr(ord(colL) + 1)].width = 28

# ---------------- materials
cls = raw('03_Material_Classification_CAS.csv')
_, n3 = sheet('CAS', cls, [('Key', 'A{r}&"|"&D{r}')])
marc = raw('02_Material_Plant_MARC.csv')
_, n2 = sheet('MARC', marc, [('Std_Price_USD_per_kg', 'ROUND(E{r}/F{r},4)')])
mara = raw('01_Material_Master_MARA.csv')
digits = 'SUBSTITUTE(N{r},"-","")'
body = f'LEFT({digits},LEN({digits})-1)'
idx = f'ROW(INDIRECT("1:"&(LEN({digits})-1)))'
_, n1 = sheet('MARA', mara, [
    ('CAS_Raw', f"IFERROR(INDEX('CAS'!$E$2:$E${n3},MATCH(A{{r}}&\"|CAS_NUMBER\",'CAS'!$F$2:$F${n3},0))&\"\",\"\")"),
    ('Home_Plant', f"INDEX('MARC'!$B$2:$B${n2},MATCH(A{{r}},'MARC'!$A$2:$A${n2},0))"),
    ('Material_Name', 'UPPER(TRIM(B{r}))'),
    ('Created_On_Date', date('F')),
    ('CAS_Step1_Trim', 'TRIM(SUBSTITUTE(SUBSTITUTE(UPPER(H{r}),"CAS",""),":",""))'),
    ('CAS_Step2_No_Note', 'TRIM(IFERROR(LEFT(L{r},FIND("(",L{r})-1),L{r}))'),
    ('CAS_No', 'IF(M{r}="","",IF(ISERROR(FIND("-",M{r})),LEFT(M{r},LEN(M{r})-3)&"-"&MID(M{r},LEN(M{r})-2,2)&"-"&RIGHT(M{r},1),M{r}))'),
    ('CAS_Check_OK', f'IF(N{{r}}="","",MOD(SUMPRODUCT(--MID({body},LEN({digits})-{idx},1),{idx}),10)=--RIGHT({digits},1))'),
    ('Material_Type_Name', f'VLOOKUP(C{{r}},{RNG["Material type"]},2,FALSE)'),
    ('Product_Group', f'VLOOKUP(D{{r}},{RNG["Material group"]},2,FALSE)'),
    ('Is_Made', 'OR(C{r}="FERT",C{r}="HALB")'),
    ('CAS_Key', 'IF(N{r}="","",N{r}&"|"&IF(R{r},"MADE","BOUGHT"))'),
    ('Same_CAS_As', 'IF(N{r}="","",IFERROR(INDEX($A$2:$A$47,MATCH(N{r}&"|"&IF(R{r},"BOUGHT","MADE"),$S$2:$S$47,0)),""))'),
], widths={2: 48, 10: 48})

sch = raw('12_Standard_Cost_History.csv')
_, n12 = sheet('Std Cost', sch, [('Year', 'YEAR(' + date('C') + ')'), ('Std_Cost_USD_per_kg', 'ROUND(D{r}/E{r},4)')])

# ---------------- customers, reps, suppliers
bp = raw('05_Business_Partner_Customers.csv')
nb = len(bp) + 1
_, n5 = sheet('Customers', bp, [
    ('Country_Code', f'VLOOKUP(UPPER(TRIM(C{{r}})),{RNG["Country as written"]},2,FALSE)'),
    ('Country', f'VLOOKUP(J{{r}},{RNG["ISO code"]},2,FALSE)'),
    ('Name_Key', 'TRIM(UPPER(SUBSTITUTE(SUBSTITUTE(B{r},".",""),"&","")))'),
    ('Master_Customer_Id', f'INDEX($A$2:$A${nb},MATCH(L{{r}},$L$2:$L${nb},0))'),
    ('Is_Duplicate', 'A{r}<>M{r}'),
    ('Sales_Rep_Id', 'IF(TRIM(G{r})="","Unassigned",G{r})'),
    ('Customer_Since_Date', date('H')),
    ('Customer_Type', 'IF(A{r}="1009990","Spot trader","Regular")'),
], widths={2: 36})
sheet('Reps', raw('06_Sales_Reps.csv'), [])
sup = raw('07_Business_Partner_Suppliers.csv')
sheet('Suppliers', sup, [('Country_Code', f'VLOOKUP(UPPER(TRIM(C{{r}})),{RNG["Country as written"]},2,FALSE)'),
                            ('Country', f'VLOOKUP(F{{r}},{RNG["ISO code"]},2,FALSE)')], widths={2: 36})

# ---------------- sales (sorted by document and item so exact copies sit under the original)
so = raw('08_Sales_Order_Items_VBAP.csv')
so = so.sort_values(['Sales_Document', 'Item'], kind='stable').reset_index(drop=True)
_, n8 = sheet('Sales', so, [
    ('Is_Duplicate', 'AND(A{r}=A{p},B{r}=B{p},H{r}=H{p},L{r}=L{p})'),
    ('Order_Date', date('D')),
    ('Billing_Date_Clean', date('N')),
    ('Unit_Factor', f'VLOOKUP(I{{r}},{RNG["SAP unit"]},2,FALSE)'),
    ('Qty_kg', 'ROUND(H{r}*R{r},1)'),
    ('List_Price_USD_per_kg', 'ROUND(J{r}/R{r},4)'),
    ('Discount_Share', 'ROUND(K{r}/100,4)'),
    ('Is_Return', 'C{r}="RE"'),
    ('Order_Year', 'YEAR(P{r})'),
    ('Std_Cost_USD_per_kg', f"SUMIFS('Std Cost'!$H$2:$H${n12},'Std Cost'!$A$2:$A${n12},F{{r}},'Std Cost'!$G$2:$G${n12},W{{r}})"),
    ('Cost_USD', 'ROUND(S{r}*X{r},2)'),
    ('Margin_USD', 'ROUND(L{r}-Y{r},2)'),
    ('Net_Value_Off_by_1USD', 'ABS(S{r}*T{r}*(1-U{r})-L{r})>1'),
])

po = raw('09_Purchase_Order_Items_EKPO.csv')
_, n9 = sheet('POs', po, [('PO_Date', date('C')), ('Delivery_Date_Clean', date('M')), ('Price_USD_per_kg', 'ROUND(J{r}/K{r},4)')], widths={6: 30})
pr = raw('10_Production_Orders_AFKO.csv')
_, n10 = sheet('Production', pr, [('Start_Date', date('E')), ('Finish_Date', date('F')),
                                             ('Status_Clean', 'IF(J{r}="TECO","Completed",IF(J{r}="REL","Released",J{r}))')])
bom = raw('04_Bill_of_Materials_STPO.csv')
_, n4 = sheet('BOM', bom, [('Component_kg_per_kg', 'ROUND(E{r}/F{r},5)')])
st = raw('11_Month_End_Stock_MARD.csv')
_, n11 = sheet('Stock', st, [('Month', 'DATE(LEFT(D{r},4),RIGHT(D{r},2),1)'),
                                ('Std_Cost_USD_per_kg', f"SUMIFS('Std Cost'!$H$2:$H${n12},'Std Cost'!$A$2:$A${n12},A{{r}},'Std Cost'!$G$2:$G${n12},YEAR(G{{r}}))"),
                                ('Stock_Value_USD', 'ROUND(E{r}*H{r},2)')])
sheet('PPI', raw('13_Ref_PPI_Basic_Organic_Chemicals_FRED.csv'), [])

# date columns shown as yyyy-mm-dd
DATE_HEADS = {'Created_On_Date', 'Customer_Since_Date', 'Order_Date', 'Billing_Date_Clean', 'PO_Date', 'Delivery_Date_Clean', 'Start_Date', 'Finish_Date', 'Month'}
for w in wb.worksheets[2:]:
    for j in range(1, w.max_column + 1):
        if w.cell(1, j).value in DATE_HEADS and w.cell(1, j).fill == BLUE:
            for i in range(2, w.max_row + 1): w.cell(i, j).number_format = 'yyyy-mm-dd'

# ---------------- DQ log
dql = wb.create_sheet('DQ log', 1)
M, C8 = "'MARA'", "'Sales'"
def iso(sheet_, c, n): return f"SUMPRODUCT(--(MID('{sheet_}'!{c}2:{c}{n},5,1)=\"-\"))"
LOG = [
    ('01 Material master', 'Descriptions in mixed case', f'SUMPRODUCT(--NOT(EXACT({M}!B2:B{n1},UPPER({M}!B2:B{n1}))))', 'UPPER(TRIM())'),
    ('03 Classification', 'CAS number badly formatted', f'SUMPRODUCT(({M}!H2:H{n1}<>{M}!N2:N{n1})*({M}!N2:N{n1}<>""))', 'trim, strip prefix/note, add dashes'),
    ('03 Classification', 'CAS number missing', f'SUMPRODUCT(--({M}!N2:N{n1}=""))', 'left blank - traded goods only'),
    ('03 Classification', 'CAS check digit passes', f'COUNTIF({M}!O2:O{n1},TRUE)', 'all pass'),
    ('03 Classification', 'CAS check digit fails', f'COUNTIF({M}!O2:O{n1},FALSE)', 'should be 0'),
    ('01+03 Material master', 'Same chemical under two material numbers', f'SUMPRODUCT(({M}!T2:T{n1}<>"")*({M}!R2:R{n1}=FALSE))', 'kept both, flagged in Same_CAS_As'),
    ('05 Customers', 'Country written several ways', f"SUMPRODUCT(--('Customers'!C2:C{n5}<>'Customers'!J2:J{n5}))", 'mapped to ISO code (Lookups)'),
    ('05 Customers', 'Duplicate customer records', f"COUNTIF('Customers'!N2:N{n5},TRUE)", 'merged into the original'),
    ('05 Customers', 'Sales rep missing', f"SUMPRODUCT(--(TRIM('Customers'!G2:G{n5})=\"\"))", 'Unassigned'),
    ('07 Suppliers', 'Country written several ways', f"SUMPRODUCT(--('Suppliers'!C2:C{len(sup) + 1}<>'Suppliers'!F2:F{len(sup) + 1}))", 'mapped to ISO code'),
    ('08 Sales orders', 'Exact duplicate rows', f'COUNTIF({C8}!O2:O{n8},TRUE)', 'filtered out'),
    ('08 Sales orders', 'Created_On in two date formats', iso('Sales', 'D', n8), 'DATE()'),
    ('08 Sales orders', 'Lines keyed in MT', f'COUNTIFS({C8}!I2:I{n8},"MT",{C8}!O2:O{n8},FALSE)', 'qty x 1000, price / 1000'),
    ('08 Sales orders', 'Lines keyed in LB', f'COUNTIFS({C8}!I2:I{n8},"LB",{C8}!O2:O{n8},FALSE)', '1 kg = 2.20462 lb'),
    ('08 Sales orders', 'Returns with negative qty and value', f'COUNTIFS({C8}!C2:C{n8},"RE",{C8}!O2:O{n8},FALSE)', 'kept, flagged Is_Return'),
    ('08 Sales orders', 'Net value off by more than USD 1 after conversion', f'COUNTIFS({C8}!AA2:AA{n8},TRUE,{C8}!O2:O{n8},FALSE)', 'rounding, ok'),
    ('08 Sales orders', 'No cost or margin in the export', f'COUNTIF({C8}!O2:O{n8},FALSE)', 'added std cost, cost, margin'),
    ('09 Purchase orders', 'Document_Date in two date formats', iso('POs', 'C', n9), 'DATE()'),
    ('09/12 Prices', 'Prices stored per 1,000 kg', f"COUNTA('POs'!A2:A{n9})+COUNTA('Std Cost'!A2:A{n12})", '/ Price_Unit'),
    ('04 BOM', 'Component quantity per 1,000 kg of output', f"COUNTA('BOM'!A2:A{n4})", '/ Base_Qty'),
    ('11 Stock', 'Period stored as YYYYMM text', f"COUNTA('Stock'!A2:A{n11})", 'first day of month'),
]
for j, h in enumerate(['#', 'File', 'Issue', 'Rows', 'What I did'], 1):
    c = dql.cell(1, j, h); c.font = HEAD; c.fill = BLUE
for i, (ds, issue, f, fix) in enumerate(LOG, 2):
    dql.cell(i, 1, i - 1); dql.cell(i, 2, ds); dql.cell(i, 3, issue); dql.cell(i, 4, '=' + f); dql.cell(i, 5, fix)
for j, w in enumerate([5, 22, 48, 14, 55], 1): dql.column_dimensions[get_column_letter(j)].width = w

wb.properties.creator = 'Avirat'
wb.properties.lastModifiedBy = 'Avirat'
wb.properties.title = None
wb.save(OUT)
print('saved', OUT)

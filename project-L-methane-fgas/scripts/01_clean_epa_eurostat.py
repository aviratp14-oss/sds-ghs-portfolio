"""Project L, step 1: EPA GHGRP emissions, parent companies, Eurostat trade and the first LNG table.

Reads data/raw (never changed) and writes data/clean. Every fix goes into DQ_Log.csv.
Run from anywhere: python scripts/01_clean_epa_eurostat.py
"""
import difflib
import pandas as pd, numpy as np, re, csv, warnings, pycountry
from pyxlsb import open_workbook
from rapidfuzz import fuzz, process
warnings.filterwarnings('ignore')
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
R = str(ROOT / 'data' / 'raw') + '/'; O = str(ROOT / 'data' / 'clean') + '/'
dq=[]
def log(dataset, issue, example, rows, fix):
    dq.append(dict(ID=len(dq)+1, Dataset=dataset, Issue=issue, Example=example, Rows_Affected=rows, Fix=fix))

# ---------- 1. EPA emissions ----------
YEARS=range(2011,2024)
def load(y, prefix):
    xl=pd.ExcelFile(f'{R}summary/ghgp_data_{y}.xlsx')
    sn=[s for s in xl.sheet_names if s.startswith(prefix)]
    if not sn: return None, None
    df=xl.parse(sn[0], header=3, dtype={'Facility Id':'Int64'})
    raw_cols=list(df.columns)
    df.columns=[str(c).strip() for c in df.columns]
    df=df[[c for c in df.columns if not c.startswith('Unnamed')]]
    df=df[df['Facility Id'].notna()]
    df.insert(0,'Year',y)
    return df, (sn[0], raw_cols)
log('EPA GHGRP yearly files','2010 file has a shorter layout (53 vs 66 columns) and fewer industries reporting','ghgp_data_2010.xlsx','1 file','Excluded 2010; analysis covers 2011-2023')
log('EPA GHGRP yearly files','Header row is row 4; rows 1-3 are titles','ghgp_data_2023.xlsx rows 1-3','13 files','Read with header on row 4')
log('EPA GHGRP yearly files','Main sheet renamed in 2018','"Direct Emitters" (2011-2017) vs "Direct Point Emitters" (2018-2023)','13 files','Selected sheet by prefix "Direct"')
direct=[]; trailing=0
for y in YEARS:
    d,(sn,rc)=load(y,'Direct'); trailing+=sum(1 for c in rc if isinstance(c,str) and c!=c.strip())
    direct.append(d)
direct=pd.concat(direct, ignore_index=True)
log('EPA GHGRP yearly files','Column names have trailing spaces','"Methane (CH4) emissions "',f'{trailing} column headers across 13 files','Trimmed all column names')

GAS={'CO2 emissions (non-biogenic)':'CO2','Methane (CH4) emissions':'CH4','Nitrous Oxide (N2O) emissions':'N2O','HFC emissions':'HFC','PFC emissions':'PFC','SF6 emissions':'SF6','NF3 emissions':'NF3','Other Fully Fluorinated GHG emissions':'Other fully fluorinated GHG','HFE emissions':'HFE','Very Short-lived Compounds emissions':'Very short-lived compounds','Other GHGs (metric tons CO2e)':'Other GHGs'}
og=[]
for y in YEARS:
    for p,seg in [('Onshore','Onshore Production'),('Gathering','Gathering & Boosting'),('Transmission Pipelines','Transmission Pipelines'),('LDC','Local Distribution')]:
        d,_=load(y,p)
        if d is None: continue
        d=d.rename(columns={'Reported State':'State','State where Emissions Occur':'State','Reported City':'City','Reported County':'County','Reported Latitude':'Latitude','Reported Longitude':'Longitude'})
        d=d.loc[:,~d.columns.duplicated()]
        d['Segment']=seg; og.append(d)
og=pd.concat(og, ignore_index=True)
log('EPA GHGRP yearly files','Oil & gas production, gathering, transmission pipeline and distribution methane are in separate sheets, not in Direct Emitters','Sheets "Onshore Oil & Gas Prod.", "Gathering & Boosting"',f'{len(og):,} facility-year rows','Loaded the 4 sheets separately and appended with a Segment column')
log('EPA GHGRP yearly files','Gathering & Boosting and Transmission Pipelines only reported from 2016','No such sheets in 2011-2015 files','Trend break in 2016','Kept as is; flag the 2016 break on trend charts')

direct['Segment']='Direct Emitter'; direct['Basin']=np.nan
keep=['Year','Facility Id','Segment','Basin']
dl=direct[keep+list(GAS)].melt(id_vars=keep, var_name='Gas', value_name='CO2e_AR4_t')
ogl=og.reindex(columns=keep+[c for c in GAS if c in og.columns]).melt(id_vars=keep, var_name='Gas', value_name='CO2e_AR4_t')
fact=pd.concat([dl,ogl], ignore_index=True)
fact['Gas']=fact['Gas'].map(GAS)
fact['CO2e_AR4_t']=pd.to_numeric(fact['CO2e_AR4_t'], errors='coerce')
nb=len(fact); fact=fact[fact['CO2e_AR4_t'].fillna(0)!=0]
log('EPA emissions (long table)','Gases stored as wide columns, most cells blank or zero','11 gas columns per facility',f'{nb-len(fact):,} blank/zero cells dropped of {nb:,}','Unpivoted to one row per facility-year-gas; dropped blank and zero values')
neg=(fact['CO2e_AR4_t']<0).sum()
log('EPA emissions (long table)','Negative emission values','-',f'{neg} rows','Checked; kept as reported' if neg else 'None found')

# basin
fact['Basin_Code']=fact['Basin'].str.extract(r'^\s*([0-9]+[A-Z]?)\s*-')[0]
fact['Basin_Name']=fact['Basin'].str.replace(r'^\s*[0-9]+[A-Z]?\s*-\s*','',regex=True).str.strip()
log('EPA oil & gas sheets','Basin stored as "code - name" in one field','"430 - Permian Basin"',f'{fact.Basin.notna().sum():,} rows','Split into Basin_Code and Basin_Name')

# gas groups and GWPs
GWP={'CH4':(25,28,29.8,82.5),'N2O':(298,265,273,273),'SF6':(22800,23500,25200,18300),'NF3':(17200,16100,17400,13400),'CO2':(1,1,1,1)}
fact['Gas_Group']=fact['Gas'].map(lambda g:'Methane' if g=='CH4' else 'CO2' if g=='CO2' else 'N2O' if g=='N2O' else 'F-gases')
fact['Tonnes_Gas']=[v/GWP[g][0] if g in GWP else np.nan for g,v in zip(fact.Gas,fact.CO2e_AR4_t)]
for i,col in [(1,'CO2e_AR5_t'),(2,'CO2e_AR6_100_t'),(3,'CO2e_AR6_20_t')]:
    fact[col]=[t*GWP[g][i] if g in GWP else v for g,t,v in zip(fact.Gas,fact.Tonnes_Gas,fact.CO2e_AR4_t)]
fact['GWP_Converted']=fact['Gas'].isin(GWP.keys())
log('EPA emissions (long table)','All values are CO2e using IPCC AR4 GWPs (CH4 = 25)','FAQ tab of each file',f'{fact.GWP_Converted.sum():,} rows (CH4, N2O, SF6, NF3, CO2)','Back-calculated tonnes of gas and added AR5, AR6-100 and AR6-20 CO2e columns')
log('EPA emissions (long table)','HFC, PFC and other F-gas columns are mixtures of many gases, so a single GWP cannot be applied','HFC emissions',f'{(~fact.GWP_Converted).sum():,} rows','Kept AR4 CO2e in all GWP columns; GWP_Converted = FALSE')
fact=fact.drop(columns=['Basin'])

# dim facility: latest year attributes
attr=['Facility Id','Year','Facility Name','City','State','County','Latitude','Longitude','Primary NAICS Code']
d1=direct[attr+['Industry Type (subparts)','Industry Type (sectors)']].copy()
d2=og.reindex(columns=attr+['Industry Type (subparts)','Basin']).copy(); d2['Industry Type (sectors)']='Petroleum and Natural Gas Systems'
allf=pd.concat([d1,d2],ignore_index=True).sort_values('Year')
names=allf.groupby('Facility Id')['Facility Name'].nunique()
log('EPA facilities','Same facility appears under different names in different years','"3M CORDOVA" vs "3M Chemical Operations\' Cordova Facility"',f'{(names>1).sum():,} facilities','Keyed everything on Facility Id; Dim_Facility uses the latest reported name')
dim=allf.groupby('Facility Id').last().reset_index()
dim['Facility Name']=dim['Facility Name'].astype(str).str.strip()
dim['State']=dim['State'].astype(str).str.strip().str.upper()
dim['Industry Type (sectors)']=dim['Industry Type (sectors)'].astype(str).str.replace('Fluorintaed','Fluorinated')
log('EPA facilities','EPA typo in a sector label','"Import and Export of Equipment Containing Fluorintaed GHGs"','label','Corrected to "Fluorinated"')
dim['Primary_Sector']=dim['Industry Type (sectors)'].str.split(',').str[0].str.strip()
dim=dim.drop(columns=['Year'])
dim['Basin_Code']=dim['Basin'].str.extract(r'^\s*([0-9]+[A-Z]?)\s*-')[0]; dim=dim.drop(columns=['Basin'])
multi=(dim['Industry Type (sectors)'].str.contains(',')).sum()
br=dim[['Facility Id','Industry Type (sectors)']].assign(Sector=lambda x:x['Industry Type (sectors)'].str.split(',')).explode('Sector')
br['Sector']=br['Sector'].str.strip(); br=br[['Facility Id','Sector']].drop_duplicates()
log('EPA facilities','Industry sector field holds several values in one cell','"Chemicals,Waste"',f'{multi:,} facilities','Created Bridge_Facility_Sector (one row per facility-sector) and a Primary_Sector column')

# ---------- 2. Parent companies ----------
rows=[]
with open_workbook(R+'ghgp_data_parent_company.xlsb') as wb:
    for s in wb.sheets:
        with wb.get_sheet(s) as sh:
            it=sh.rows(); hdr=[c.v for c in next(it)]
            for r in it: rows.append([c.v for c in r])
par=pd.DataFrame(rows,columns=hdr)
n0=len(par); par=par[par['GHGRP FACILITY ID'].notna()]
log('EPA parent companies','Empty rows in the parent file','blank rows at sheet ends',f'{n0-len(par):,} rows','Dropped')
par=par.rename(columns={'GHGRP FACILITY ID':'Facility Id','REPORTING YEAR':'Year','PARENT COMPANY NAME':'Parent_Raw','PARENT CO. PERCENT OWNERSHIP':'Ownership_Pct'})
par['Facility Id']=par['Facility Id'].astype(int); par['Year']=par['Year'].astype(int)
par=par[par.Year.between(2011,2023)]
par['Parent_Raw']=par['Parent_Raw'].astype(str).str.strip()
SUF=r'\b(THE|INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LLC|L L C|LP|L P|LTD|LIMITED|HOLDINGS?|PLC|NA|USA|US|U S A|GROUP)\b'
def key(s):
    s=s.upper(); s=re.sub(r'&',' AND ',s); s=re.sub(r'[^A-Z0-9 ]',' ',s)
    s=re.sub(SUF,' ',s); return re.sub(r'\s+','',s)
par['Parent_Key']=par['Parent_Raw'].map(key)
nraw=par.Parent_Raw.nunique(); nkey=par.Parent_Key.nunique()
# fuzzy merge of near-identical keys (typos), conservative
em=fact[fact.Year==2023].groupby('Facility Id').CO2e_AR4_t.sum()
keys=par.Parent_Key.value_counts()
klist=[k for k in keys.index if len(k)>=8]
# keys that look alike but are different entities: numbered funds/units (II vs III, NO1 vs NO2),
# letter variants (FUND A vs B) and known name pairs
BLOCK={frozenset(p) for p in [('NORTHEASTERNUNIVERSITY','NORTHWESTERNUNIVERSITY'),('CITYOFTAUNTON','CITYOFSTAUNTON'),
       ('COUNTYOFKINGS','COUNTYOFKING'),('ASTRALENERGY','ASTRAENERGY'),('DAVIDBALMQUIST','DAVIDALMQUIST')]}
def distinct(a,b):
    if frozenset((a,b)) in BLOCK: return True
    for tag,i1,i2,j1,j2 in difflib.SequenceMatcher(None,a,b).get_opcodes():
        if tag=='equal': continue
        for chunk,end in ((a[i1:i2],i2==len(a)),(b[j1:j2],j2==len(b))):
            if re.search(r'\d',chunk): return True
            if chunk and re.fullmatch(r'[IVX]+',chunk) and (len(chunk)>=2 or end): return True
            if end and len(chunk)==1 and chunk!='S': return True
    return False
merge={}
for k in klist:
    if k in merge: continue
    for m,score,_ in process.extract(k,klist,scorer=fuzz.ratio,limit=5):
        if m!=k and m not in merge and score>=95 and abs(len(m)-len(k))<=2 and m[:5]==k[:5] and not distinct(k,m):
            merge[m]=k
par['Parent_Key']=par['Parent_Key'].replace(merge)
fm=pd.DataFrame([(a,b) for a,b in merge.items()],columns=['Merged_Key','Into_Key'])
std=par.groupby('Parent_Key')['Parent_Raw'].agg(lambda s:s.value_counts().index[0]).rename('Parent_Standard')
par=par.join(std,on='Parent_Key')
log('EPA parent companies','Same parent company spelled many ways','"EXXON MOBIL CORP", "ExxonMobil Corp", "Exxon Mobile Corporation"',f'{nraw:,} distinct raw names','Normalised (upper case, punctuation, legal suffixes, spaces) to a match key: '+f'{nkey:,} keys; then fuzzy-merged {len(merge)} near-identical keys (ratio >= 95, same first 5 letters; numbered or lettered entities and known different names kept apart): {par.Parent_Key.nunique():,} parents. Each group shows its most common spelling. Merges listed in Parent_Fuzzy_Merges for review')
par['Ownership_Pct']=pd.to_numeric(par['Ownership_Pct'],errors='coerce')
nn=par.Ownership_Pct.isna().sum()
par['Ownership_Share']=par['Ownership_Pct'].fillna(100)/100
tot=par.groupby(['Facility Id','Year']).Ownership_Share.transform('sum')
over=(tot>1.001).sum()
log('EPA parent companies','Missing ownership percentage','blank PERCENT OWNERSHIP',f'{nn:,} rows','Assumed 100% ownership')
log('EPA parent companies','Facilities with several owners, or owner shares summing above 100%','5.7% of facility-years have >1 parent',f'{over:,} rows where shares sum > 100%','Kept shares as reported; added Share_Sum so dashboards can normalise')
par['Share_Sum']=tot
dim_parent=par[['Facility Id','Year','Parent_Raw','Parent_Key','Parent_Standard','Ownership_Pct','Ownership_Share','Share_Sum']]

# ---------- 3. Eurostat ----------
eu=pd.read_csv(R+'eurostat/comext_DS-045409_EU_imports_gas_crude_hfc_fluoropolymers_2015-2025.csv',dtype={'product':str,'partner':str,'TIME_PERIOD':int})
agg=eu.partner.isin(['EXT_EU','INT_EU']).sum()
eu_tot=eu[eu.partner.isin(['EXT_EU','INT_EU'])]
eu=eu[~eu.partner.isin(['EXT_EU','INT_EU'])]
log('Eurostat imports','Aggregate partner rows mixed with country rows (double counting risk)','partner = EXT_EU, INT_EU',f'{agg:,} rows','Removed from the fact table; kept as Eurostat_Totals for reconciliation')
w=eu.pivot_table(index=['TIME_PERIOD','partner','product'],columns='indicators',values='OBS_VALUE',aggfunc='sum').reset_index()
w.columns.name=None
w=w.rename(columns={'TIME_PERIOD':'Year','partner':'Partner_Code','product':'HS6','VALUE_IN_EUROS':'Value_EUR','QUANTITY_IN_100KG':'Qty_100kg'})
w['Quantity_t']=w['Qty_100kg']/10; w=w.drop(columns='Qty_100kg')
log('Eurostat imports','Value and quantity stored as separate rows (long indicator column)','indicators = VALUE_IN_EUROS / QUANTITY_IN_100KG',f'{len(eu):,} rows to {len(w):,}','Pivoted to Value_EUR and Quantity_t columns; converted 100 kg to tonnes')
EU27='AT BE BG CY CZ DE DK EE ES FI FR GR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK'.split()
SPECIAL={'XK':'Kosovo','XS':'Serbia','XC':'Ceuta','XL':'Melilla','QP':'High seas','QV':'Countries not specified (intra-EU)','QW':'Countries not specified (extra-EU)','QY':'Secret (intra-EU)','QZ':'Secret (extra-EU)','GR':'Greece'}
def cname(c):
    if c in SPECIAL: return SPECIAL[c]
    x=pycountry.countries.get(alpha_2=c); return getattr(x,'common_name',None) or (x.name if x else c)
w['Partner_Name']=w.Partner_Code.map(cname)
w['Partner_Is_EU27']=w.Partner_Code.isin(EU27)
w['Flow_Type']=np.where(w.Partner_Is_EU27,'Intra-EU','Extra-EU')
log('Eurostat imports','Partner shown only as 2-letter codes, including Eurostat-only codes','QP, QZ, XS, XK',f'{w.Partner_Code.nunique()} codes','Added Partner_Name and an EU-27 flag (intra- vs extra-EU)')
PG={'270900':('Crude oil','EU Methane Regulation'),'271111':('LNG','EU Methane Regulation'),'271121':('Pipeline natural gas','EU Methane Regulation'),
    '290339':('Fluorinated hydrocarbons (pre-2022 code, incl. HFCs)','F-gas Regulation'),'290341':('HFC-23','F-gas Regulation'),'290342':('HFC-32 / HFC-41 (difluoro/fluoromethane)','F-gas Regulation'),
    '290343':('HFC-125 / HFC-134 group','F-gas Regulation'),'290344':('HFC-143 / HFC-152 group','F-gas Regulation'),'290345':('HFC-227 / HFC-236 group','F-gas Regulation'),'290346':('HFC-245 group','F-gas Regulation'),
    '290347':('HFC-365mfc / HFC-43-10mee','F-gas Regulation'),'290348':('HFC-134a and other saturated HFCs','F-gas Regulation'),'290349':('Other saturated fluorinated derivatives','F-gas Regulation'),
    '390461':('PTFE','PFAS restriction (proposed)'),'390469':('Other fluoropolymers','PFAS restriction (proposed)')}
w['Product']=w.HS6.map(lambda h:PG[h][0]); w['Regulation']=w.HS6.map(lambda h:PG[h][1])
w['Product_Group']=w.Regulation.map({'EU Methane Regulation':'Oil & gas','F-gas Regulation':'F-gases (HFCs)','PFAS restriction (proposed)':'Fluoropolymers'})
log('Eurostat imports','HFC codes changed in 2022 (HS2022): 290341-290349 replace part of 290339','290339 drops after 2021',f'{(w.HS6=="290339").sum()} rows on 290339','Kept both; use Product_Group "F-gases (HFCs)" for a continuous time series')
fact_trade=w[['Year','Partner_Code','Partner_Name','Partner_Is_EU27','Flow_Type','HS6','Product','Product_Group','Regulation','Value_EUR','Quantity_t']]
eu_tot=eu_tot.pivot_table(index=['TIME_PERIOD','partner','product'],columns='indicators',values='OBS_VALUE',aggfunc='sum').reset_index()

# ---------- 4. EIA LNG by terminal ----------
md=open(R+'eia/eia_lng_exports_by_point_of_exit_and_country_annual.md').read().splitlines()
yrs=[2020,2021,2022,2023,2024,2025]; out=[]; dest=None
for line in md:
    cells=[c.strip() for c in line.split('|')]
    if len(cells)<12: continue
    label=cells[2]
    m=re.match(r'\*\*To (.+)\*\*',label)
    if m: dest=m.group(1); continue
    if label.startswith('**') or dest is None: continue
    vals=cells[5:11]; link=cells[11] if len(cells)>11 else ''
    if not label or 'hist/' not in link: continue
    d_=('All destinations' if '-z00' in link else dest)
    for y,v in zip(yrs,vals):
        if v in ('','-','--','NA','W'): continue
        out.append(dict(Year=y,Destination=d_,Terminal=label,Volume_MMcf=float(v.replace(',',''))))
lng_all=pd.DataFrame(out)
term_tot=lng_all[lng_all.Destination=='All destinations'].drop(columns='Destination')
lng=lng_all[lng_all.Destination!='All destinations'].copy()
log('EIA LNG exports','The page ends with a terminal-total section (all destinations) that follows the last country block and would be double counted under it','"Cameron, LA" total rows after "To United Kingdom"',f'{len(term_tot):,} rows','Moved to Terminal_Totals using the EIA series code (-z00 = all destinations); used to reconcile')
lng['Volume_bcm']=(lng.Volume_MMcf*0.0283168/1000).round(6)
EUN={pycountry.countries.get(alpha_2=c).name for c in EU27 if c!='GR'}|{'Greece','Czech Republic','Netherlands'}
lng['Destination_Is_EU27']=lng.Destination.isin(EUN)
log('EIA LNG exports','Web table mixes country subtotals and terminal rows','"To France" then "Sabine Pass, LA"',f'{len(lng):,} terminal-country-year rows','Parsed terminal rows under each destination; dropped subtotal rows; blanks and "--" treated as no data')
log('EIA LNG exports','Volumes in million cubic feet','MMcf',f'{len(lng):,} rows','Added Volume_bcm (1 MMcf = 0.0283168 million m3)')
chk=lng.groupby('Year').Volume_MMcf.sum()

# ---------- 5. Lookups ----------
dim_gas=pd.DataFrame([dict(Gas=g,GWP_AR4=v[0],GWP_AR5=v[1],GWP_AR6_100=v[2],GWP_AR6_20=v[3]) for g,v in GWP.items()])
dim_gas['Note']=np.where(dim_gas.Gas=='CH4','AR6 values are for fossil methane','')
dim_reg=pd.DataFrame([
 dict(Regulation='EU Methane Regulation',Reference='Regulation (EU) 2024/1787',Scope='Methane MRV, LDAR, venting/flaring limits; Article 28 import equivalence for oil, gas and coal',Key_Date='Importer MRV equivalence from 1 Jan 2027 (one-year delay under discussion, Oct 2026)'),
 dict(Regulation='F-gas Regulation',Reference='Regulation (EU) 2024/573',Scope='HFC quota phase-down to zero by 2050; product bans',Key_Date='Quota cuts on a set schedule from 2024'),
 dict(Regulation='PFAS restriction (proposed)',Reference='ECHA universal PFAS restriction proposal under REACH',Scope='Manufacture, use and import of PFAS incl. fluoropolymers, with derogations',Key_Date='Proposal under evaluation by ECHA committees'),
])
# ---------- write ----------
fact=fact[['Year','Facility Id','Segment','Basin_Code','Basin_Name','Gas','Gas_Group','CO2e_AR4_t','Tonnes_Gas','CO2e_AR5_t','CO2e_AR6_100_t','CO2e_AR6_20_t','GWP_Converted']]
fact.to_csv(O+'Fact_Emissions.csv',index=False)
dim['Primary NAICS Code']=pd.to_numeric(dim['Primary NAICS Code'],errors='coerce').astype('Int64')   # 221112.0 -> 221112
dim.to_csv(O+'Dim_Facility.csv',index=False)
br.to_csv(O+'Bridge_Facility_Sector.csv',index=False)
dim_parent.to_csv(O+'Dim_Parent.csv',index=False)
fm.to_csv(O+'Parent_Fuzzy_Merges.csv',index=False)
fact_trade.to_csv(O+'Fact_Trade_EU_Imports.csv',index=False)
eu_tot.to_csv(O+'Eurostat_Totals.csv',index=False)
lng.to_csv(O+'Fact_LNG_Exports_Terminal.csv',index=False)
term_tot.assign(Volume_bcm=(term_tot.Volume_MMcf*0.0283168/1000).round(6)).to_csv(O+'LNG_Terminal_Totals.csv',index=False)
print('reconcile terminal totals',term_tot.groupby('Year').Volume_MMcf.sum().to_dict())
dim_gas.to_csv(O+'Dim_Gas.csv',index=False)
dim_reg.to_csv(O+'Dim_Regulation.csv',index=False)
pd.DataFrame(dq).to_csv(O+'DQ_Log.csv',index=False)
for n,d in [('Fact_Emissions',fact),('Dim_Facility',dim),('Bridge',br),('Dim_Parent',dim_parent),('Merges',fm),('Trade',fact_trade),('LNG',lng)]:
    print(n,d.shape,d.size)
print('LNG yearly total MMcf',chk.to_dict())
print('parents raw/key/final',nraw,nkey,par.Parent_Key.nunique())

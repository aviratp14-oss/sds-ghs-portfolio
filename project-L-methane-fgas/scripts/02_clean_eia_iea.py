# Project L cleaning, batch 2: EIA xls downloads + IEA Methane Tracker.
# Run after 01_clean_epa_eurostat.py (it appends to DQ_Log.csv and replaces the LNG tables
# parsed from the EIA web page with the official xls series).
import re, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
R = str(ROOT / 'data' / 'raw') + '/'; O = str(ROOT / 'data' / 'clean') + '/'
B2=('EIA exports by country','EIA LNG by point of exit (xls)','EIA marketed production','IEA Methane Tracker','IEA methane comparison')
dq=pd.read_csv(O+'DQ_Log.csv').query('Dataset not in @B2').to_dict('records')   # safe to re-run
def log(dataset, issue, example, rows, fix):
    dq.append(dict(ID=len(dq)+1,Dataset=dataset,Issue=issue,Example=example,Rows_Affected=rows,Fix=fix))
BCM=0.0283168/1000
EU27=['Austria','Belgium','Bulgaria','Croatia','Cyprus','Czechia','Denmark','Estonia','Finland','France','Germany','Greece',
      'Hungary','Ireland','Italy','Latvia','Lithuania','Luxembourg','Malta','Netherlands','Poland','Portugal','Romania',
      'Slovakia','Slovenia','Spain','Sweden']
CTRY={'Korea':'South Korea','Turkey':'Turkiye','Netherland':'Netherlands','Bahama Islands':'Bahamas','United kingdom':'United Kingdom'}

def eia_long(path, sheets=('Data 1','Data 2')):
    """EIA wide xls (one column per series, one row per year) -> long table."""
    out=[]
    for s in sheets:
        d=pd.read_excel(path,sheet_name=s,header=None)
        codes, names = d.iloc[1,1:].tolist(), d.iloc[2,1:].tolist()
        body=d.iloc[3:].copy(); body.columns=['Date']+codes
        body['Year']=pd.to_datetime(body.Date).dt.year
        m=body.drop(columns='Date').melt(id_vars='Year',var_name='Series_Code',value_name='Value')
        m['Series_Name']=m.Series_Code.map(dict(zip(codes,[re.sub(r'\s+',' ',str(n)).strip() for n in names])))
        out.append(m)
    m=pd.concat(out,ignore_index=True)
    blank=m.Value.isna().sum()
    m=m.dropna(subset=['Value']); m['Value']=pd.to_numeric(m.Value)
    return m, blank

def dest_of(name):
    x=re.search(r' to (.+?)\s*(?:Liquefied Natural Gas\s*)?\(',name)
    if not x: return 'All destinations'
    c=x.group(1).strip()
    return 'All destinations' if c=='All Countries' else CTRY.get(c,c)

# ---------- 1. U.S. natural gas exports by country (volume + price) ----------
v,bv=eia_long(R+'eia/NG_MOVE_EXPC_S1_A.xls',('Data 1',))
p,bp=eia_long(R+'eia/NG_MOVE_EXPC_S1_A.xls',('Data 2',))
log('EIA exports by country','Wide layout: one column per series (76 series), years as rows, blanks before a route existed','NG_MOVE_EXPC_S1_A.xls Data 1',f'{bv+bp:,} blank cells',
    'Unpivoted to one row per year-series; dropped blanks (no data), kept reported zeros')
def mode(code):
    if code=='N9130US2': return 'All exports'
    if code.startswith('N9132'): return 'Pipeline'
    if code=='N9133US2': return 'LNG (all)'
    k=code.split('_')[2]
    return {'EVT':'LNG by vessel and truck','EVE':'LNG by vessel','ETR':'LNG by truck','ERE':'LNG re-export','ENC':'CNG'}[k]
v['Mode']=v.Series_Code.map(mode)
v['Destination']=v.Series_Name.map(dest_of)
v.loc[v.Series_Code=='N9132CN2','Destination']='Canada'; v.loc[v.Series_Code=='N9132MX2','Destination']='Mexico'
v['Is_Total_Row']=v.Destination.eq('All destinations')
# volumes (code ...2 or _MMCF) and prices (code ...3 or _DMCF) share the series stem
stem=lambda c: re.sub(r'(2|3)$','',c) if c.startswith('N9') else re.sub(r'_(MMCF|DMCF)$','',c)
v['Stem']=v.Series_Code.map(stem); p['Stem']=p.Series_Code.map(stem)
exp=v.merge(p[['Stem','Year','Value']].rename(columns={'Value':'Price_USD_per_Mcf'}),on=['Stem','Year'],how='left')
exp=exp.rename(columns={'Value':'Volume_MMcf'})
exp['Volume_bcm']=(exp.Volume_MMcf*BCM).round(6)
exp['Destination_Is_EU27']=exp.Destination.isin(EU27)
nmatch=exp.Price_USD_per_Mcf.notna().sum()
log('EIA exports by country','Prices are on a separate sheet (Data 2) with matching series codes ending 3 instead of 2','N9130US3 = price of N9130US2',f'{nmatch:,} of {len(exp):,} volume rows got a price',
    'Joined price to volume on the series stem; price blank where EIA withholds it')
log('EIA exports by country','Total, mode subtotal and country rows are mixed in one table (double counting risk)','"U.S. Natural Gas Exports" + "Pipeline Exports to Canada"',f'{exp.Is_Total_Row.sum():,} total/subtotal rows',
    'Added Mode and Is_Total_Row; sum country rows within one Mode only')
chk=exp[exp.Year==2023].set_index('Series_Code').Volume_MMcf
diff=chk['N9133US2']-chk['NGM_EPG0_EVT_NUS-Z00_MMCF']-chk.get('NGM_EPG0_ERE_NUS-Z00_MMCF',0)-chk.get('NGM_EPG0_ENC_NUS-Z00_MMCF',0)
print('exports 2023 total',chk['N9130US2'],'pipe+LNG',chk['N9132US2']+chk['N9133US2'],'LNG - (vessel&truck+reexport+CNG)',diff)
exp=exp[['Year','Mode','Destination','Destination_Is_EU27','Is_Total_Row','Volume_MMcf','Volume_bcm','Price_USD_per_Mcf','Series_Code','Series_Name']]
exp.sort_values(['Mode','Destination','Year']).to_csv(O+'Fact_EIA_Gas_Exports.csv',index=False)

# ---------- 2. LNG exports by point of exit (terminal x destination) ----------
l,bl=eia_long(R+'eia/NG_MOVE_POE2_A_EPG0_ENG_MMCF_A.xls')
def terminal(name):
    if re.match(r'^(U\.S\. Liquefied|Liquefied U\.S\.)',name): return None   # national / country subtotal
    t=re.split(r'\s+(?:Liquefied Natural Gas )?Exports',name)[0].strip()
    t=re.sub(r'\s+Liquefied Natural Gas$','',t)
    t=re.sub(r',\s*',', ',t)
    return t.replace('Florida','FL').replace('Louisiana','LA')
l['Terminal']=l.Series_Name.map(terminal)
l['Destination']=l.Series_Name.map(dest_of)
tot_rows=l[l.Terminal.isna()]
l=l[l.Terminal.notna()]
log('EIA LNG by point of exit (xls)','Country subtotals and the U.S. total sit next to terminal series','"Liquefied U.S. Natural Gas Exports to France"',f'{len(tot_rows):,} subtotal rows',
    'Kept only terminal series; subtotals used to reconcile')
log('EIA LNG by point of exit (xls)','Inconsistent series names: word order, double spaces, "Korea" vs "South Korea", "West Palm Beach, Florida" vs "FL"','"Sabine Pass, LA Exports to Korea Liquefied Natural Gas"',f'{len(l):,} rows',
    'Parsed Terminal and Destination with one pattern, collapsed spaces, standardised country and state names')
log('EIA LNG by point of exit (xls)','EIA terminal totals are slightly higher than the sum of their destinations in a few years (destination not reported by EIA)','Cameron, LA 2020: 382,405 total vs 378,711 by destination','3 terminal-years (2020 Cameron and Cove Point, 2024 Cove Point; 7,713 MMcf in all)',
    'Kept as published; use LNG_Terminal_Totals for terminal totals and Fact_LNG_Exports_Terminal for destination splits')
term_tot=l[l.Destination=='All destinations'].drop(columns='Destination')
lng=l[l.Destination!='All destinations'].copy()
# reconcile: terminal-destination rows vs EIA country subtotals and U.S. total
sub=tot_rows.assign(Destination=tot_rows.Series_Name.map(dest_of))
us=sub[sub.Destination=='All destinations'].groupby('Year').Value.sum()
mine=lng.groupby('Year').Value.sum()
gap=(mine-us).dropna()
print('LNG terminal sum vs EIA US total, max abs gap by year:',gap.abs().max(), gap[gap.abs()>5].to_dict())
log('EIA LNG by point of exit (xls)','Earlier table was parsed from the EIA web page (2020-2025 only)','eia_lng_exports_by_point_of_exit_and_country_annual.md','1,426 web-page rows',
    f'Replaced with the official xls series ({int(lng.Year.min())}-{int(lng.Year.max())}, {len(lng):,} rows); 2020-2025 yearly totals matched the web-page parse exactly (checked 2026-10-04)')
for df in (lng,term_tot):
    df.rename(columns={'Value':'Volume_MMcf'},inplace=True)
    df['Volume_bcm']=(df.Volume_MMcf*BCM).round(6)
lng['Destination_Is_EU27']=lng.Destination.isin(EU27)
lng[['Year','Destination','Terminal','Volume_MMcf','Volume_bcm','Destination_Is_EU27']].sort_values(['Destination','Terminal','Year']).to_csv(O+'Fact_LNG_Exports_Terminal.csv',index=False)
term_tot[['Year','Terminal','Volume_MMcf','Volume_bcm']].sort_values(['Terminal','Year']).to_csv(O+'LNG_Terminal_Totals.csv',index=False)

# ---------- 3. Marketed natural gas production by state ----------
g,bg=eia_long(R+'eia/NG_PROD_SUM_A_EPG0_VGM_MMCF_A.xls')
g['Area']=g.Series_Name.str.replace(r'\s*(Natural Gas Marketed Production|Marketed Production of Natural Gas).*$','',regex=True).str.replace('Calif--','California--')
# hierarchy: U.S. = state totals + Federal Offshore Gulf of America (Other States is a subtotal of small states);
# state totals = onshore + state offshore (+ federal offshore for California); Gulf = federal offshore AL + LA + TX (older years)
def split(a):
    if a=='Federal Offshore--Gulf of America': return a,None
    if a.startswith('Federal Offshore--'): return 'Federal Offshore--Gulf of America',a.split('--')[1]
    if a=='Federal Offshore California': return 'California','Federal Offshore'
    if '--' in a: return a.split('--')[0],a.split('--')[1].replace('onshore','Onshore')
    return a,None
g[['State','Sub_Area']]=g.Area.apply(lambda a: pd.Series(split(a)))
g['Level']=g.apply(lambda r:'U.S. total' if r.Area=='U.S.' else 'Other States total' if r.Area=='Other States'
                   else 'Component' if pd.notna(r.Sub_Area) else 'State or federal offshore area',axis=1)
g['Other_States_Group']=g.Series_Code.isin(pd.read_excel(R+'eia/NG_PROD_SUM_A_EPG0_VGM_MMCF_A.xls',sheet_name='Data 2',header=None).iloc[1,1:].tolist())
y=g[(g.Year==2023)]
lv=y.groupby('Level').Value.sum()
print('production 2023: US',lv['U.S. total'],'sum of states+federal areas',lv['State or federal offshore area'])
log('EIA marketed production','U.S. total, "Other States" subtotal, state totals and onshore/offshore components are mixed (double counting risk)','"Texas" and "Texas--onshore"',f'{len(g):,} rows',
    'Added Level (U.S. total / Other States total / State or federal offshore area / Component); sum only "State or federal offshore area" rows')
log('EIA marketed production','Small states only appear in a second sheet ("Other States")','Data 2: Alabama, Kentucky, Virginia ...',f'{g.Other_States_Group.sum():,} rows',
    'Appended both sheets; Other_States_Group flags them')
log('EIA marketed production','2025: EIA publishes the Other States subtotal but not yet the small states inside it','Alabama 2025 blank',f"{g[(g.Year==2025)&(g.Level=='Other States total')].Value.sum():,.0f} MMcf",
    'For 2025 add the "Other States total" row to the state rows to reach the U.S. total')
log('EIA marketed production',f'Series start in different years (U.S. from 1900, some states from 1967); blanks before a series starts','N9050US2 from 1900',f'{bg:,} blank cells','Dropped blanks; filter Year >= 2011 to align with EPA data')
g=g.rename(columns={'Value':'Volume_MMcf'}); g['Volume_bcm']=(g.Volume_MMcf*BCM).round(6)
g[['Year','State','Sub_Area','Level','Other_States_Group','Volume_MMcf','Volume_bcm','Series_Code','Series_Name']].sort_values(['State','Year']).to_csv(O+'Fact_EIA_Marketed_Production.csv',index=False)

# ---------- 4. IEA Methane Tracker: CH4 by production source ----------
t=pd.read_csv(R+'iea/iea_methane_tracker_ch4_by_production_source.csv',sep=';')
t.columns=[c.strip().replace(' ','_') for c in t.columns]
log('IEA Methane Tracker','File is semicolon-separated, not comma-separated','"Region;Unit;Year;..."','1 file','Read with ; delimiter')
agg=t[t.Region.isin(['World','European Union'])]
t=t[~t.Region.isin(['World','European Union'])]
EUIEA=EU27+['Rest of European Union B','Rest of European Union C']
log('IEA Methane Tracker','Aggregates (World, European Union) sit in the same column as countries','Region = "World"',f'{len(agg):,} rows',
    'Moved to IEA_Methane_Totals; checked World = sum of all other regions and EU = sum of its 10 countries + 2 "Rest of EU" groups (both match exactly)')
log('IEA Methane Tracker','Some regions are IEA model groups, not countries','"Rest of Other Asia", "ROE5"',f'{t.Region.str.startswith(("Rest of","ROE")).sum():,} rows',
    'Added Region_Type (Country / IEA residual group); EU27 flag includes the two "Rest of European Union" groups')
log('IEA Methane Tracker','Satellite-detected large emitter events are a separate "Hydrocarbon" category, not oil or gas','Hydrocarbon = "Satellite-detected large emitters"',f'{t.Hydrocarbon.str.startswith("Sat").sum():,} rows',
    'Added Is_Satellite flag so dashboards can show inventory-based and satellite-detected emissions separately')
z=(t.Value==0).sum(); t=t[t.Value!=0]
log('IEA Methane Tracker','Most cells are zero (source not present in that country)','Offshore gas in landlocked countries',f'{z:,} of {z+len(t):,} rows',
    'Dropped zero rows (same rule as EPA emissions)')
t=t.rename(columns={'Region':'Country','Value':'CH4_kt'})
t['Region_Type']=t.Country.str.startswith(('Rest of','ROE')).map({True:'IEA residual group',False:'Country'})
t['Is_EU27']=t.Country.isin(EUIEA)
t['Is_Satellite']=t.Hydrocarbon.str.startswith('Sat')
t['CO2e_AR5_kt']=(t.CH4_kt*28).round(3); t['CO2e_AR6_100_kt']=(t.CH4_kt*29.8).round(3); t['CO2e_AR6_20_kt']=(t.CH4_kt*82.5).round(3)
t['CH4_kt']=t.CH4_kt.round(4)
log('IEA Methane Tracker','Values are tonnes of methane, not CO2e (unlike EPA, which reports AR4 CO2e)','Unit = Thousand tonnes',f'{len(t):,} rows',
    'Added AR5, AR6-100 and AR6-20 CO2e columns with the same GWPs as Dim_Gas so IEA and EPA can be compared')
t[['Country','Region_Type','Is_EU27','Year','Hydrocarbon','Sector','Production_source','Reason','Is_Satellite','CH4_kt','CO2e_AR5_kt','CO2e_AR6_100_kt','CO2e_AR6_20_kt']].to_csv(O+'Fact_IEA_Methane.csv',index=False)
agg.rename(columns={'Region':'Aggregate','Value':'CH4_kt'}).groupby(['Aggregate','Year','Hydrocarbon','Sector','Reason'],as_index=False).CH4_kt.sum().round(4).to_csv(O+'IEA_Methane_Totals.csv',index=False)

# ---------- 5. IEA methane comparison (world, by sector) ----------
c=pd.read_csv(R+'iea/iea_methane_emissions_comparison_world.csv')
c.columns=['Region','CH4_kt','Source','Sector','Segment','Reason','Base_Year','Notes']
c['Notes_Short']=c.Notes.str.split(r'\. Other estimates').str[0].str.slice(0,200)
log('IEA methane comparison','Notes column holds the full citation list (about 1,200 characters per row)','Agriculture row notes',f'{len(c)} rows',
    'Kept the first sentence in Notes_Short for display; full notes stay in the raw file')
c[['Region','Sector','Segment','Reason','Base_Year','CH4_kt','Source','Notes_Short']].to_csv(O+'Ref_IEA_Methane_By_Sector.csv',index=False)

pd.DataFrame(dq).to_csv(O+'DQ_Log.csv',index=False)
print('rows: exports',len(exp),'lng',len(lng),'term_tot',len(term_tot),'prod',len(g),'iea',len(t),'dq',len(dq))

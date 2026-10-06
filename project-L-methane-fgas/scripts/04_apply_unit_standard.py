# Project L cleaning, step 4: one unit standard and one naming style across every table.
# Run after 01, 02 and 03.
# Standard: mass in metric tonnes (t), emissions in tCO2e, gas volume in bcm, money in USD
# (EUR kept next to it for EU context), gas price in USD/MMBtu, shares as 0-1, Year as integer,
# column names in Snake_Case with the unit as suffix.
import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
R = str(ROOT / 'data' / 'raw') + '/'; O = str(ROOT / 'data' / 'clean') + '/'
DS='All tables (unit standard)'
dq=pd.read_csv(O+'DQ_Log.csv').query('Dataset != @DS').to_dict('records')   # safe to re-run
def log(issue, example, rows, fix):
    dq.append(dict(ID=len(dq)+1,Dataset=DS,Issue=issue,Example=example,Rows_Affected=rows,Fix=fix))
def rd(f): return pd.read_csv(O+f,low_memory=False,dtype={'Basin_Code':str,'HS6':str,'Primary NAICS Code':'Int64','Primary_NAICS_Code':'Int64'})
def wr(d,f): d.to_csv(O+f,index=False)
BCM=0.0283168/1000            # 1 MMcf = 0.0283168 million m3
MMBTU_PER_MCF=1.036           # EIA average heat content of dry natural gas, ~1,036 Btu per cubic foot
fx=pd.read_csv(R+'eurostat/eurostat_ert_bil_eur_a_EUR_USD_annual_avg_2010-2025.csv')
FX=dict(zip(fx.TIME_PERIOD,fx.OBS_VALUE))          # USD per 1 EUR, annual average
pd.DataFrame({'Year':list(FX),'USD_per_EUR':list(FX.values())}).to_csv(O+'Dim_FX_EUR_USD.csv',index=False)
COMMON={'Facility Id':'Facility_Id','Facility Name':'Facility_Name','Primary NAICS Code':'Primary_NAICS_Code',
        'Industry Type (subparts)':'Industry_Type_Subparts','Industry Type (sectors)':'Industry_Type_Sectors'}

# --- EPA tables ---
f=rd('Fact_Emissions.csv')
if 'Tonnes_Gas' in f:
    f=f.rename(columns={**COMMON,'Tonnes_Gas':'Gas_t','CO2e_AR4_t':'CO2e_AR4_tCO2e','CO2e_AR5_t':'CO2e_AR5_tCO2e','CO2e_AR6_100_t':'CO2e_AR6_100_tCO2e','CO2e_AR6_20_t':'CO2e_AR6_20_tCO2e'})
    f['Gas_t']=f.Gas_t.where(f.GWP_Converted)      # mixtures (HFC, PFC...) have no single-gas tonnage
    for c in [c for c in f if c.endswith('_tCO2e')]+['Gas_t']: f[c]=f[c].round(3)
    wr(f,'Fact_Emissions.csv')
log('Units were only implied by column names and differed between tables (Tonnes_Gas, CO2e_AR4_t, CH4_kt, Volume_MMcf, Value_EUR)','CH4_kt in IEA vs CO2e_AR4_t in EPA','20 tables',
    'One standard: t (mass of gas), tCO2e (emissions), bcm (gas volume), USD (money; EUR kept alongside), USD/MMBtu (gas price), 0-1 (shares). Unit is now the column suffix, e.g. CO2e_AR5_tCO2e, Volume_bcm, Value_USD')
log('Column names mixed spaces, brackets and underscores','"Facility Id", "Industry Type (sectors)", "TIME_PERIOD"','all tables','Renamed to Snake_Case (Facility_Id, Industry_Type_Sectors, Year)')
log('For HFC, PFC and other mixtures the "tonnes of gas" column held AR4 CO2e, not tonnes (EPA reports mixtures only as CO2e)','Gas = HFC',f'{(~f.GWP_Converted).sum():,} rows',
    'Gas_t left blank for mixtures so it is never summed as tonnes; their CO2e columns are unchanged (AR4)')
w=rd('Fact_SubpartW_Source.csv')
if 'Tonnes_Gas' in w:
    w=w.rename(columns={**COMMON,'Tonnes_Gas':'Gas_t','CO2e_AR4_t':'CO2e_AR4_tCO2e','CO2e_AR5_t':'CO2e_AR5_tCO2e','CO2e_AR6_100_t':'CO2e_AR6_100_tCO2e','CO2e_AR6_20_t':'CO2e_AR6_20_tCO2e'})
    wr(w,'Fact_SubpartW_Source.csv')
d=rd('Dim_Facility.csv'); wr(d.rename(columns=COMMON),'Dim_Facility.csv')
b=rd('Bridge_Facility_Sector.csv'); wr(b.rename(columns=COMMON),'Bridge_Facility_Sector.csv')
p=rd('Dim_Parent.csv')
if 'Ownership_Pct' in p:
    p=p.rename(columns={**COMMON,'Share_Sum':'Ownership_Share_Sum'}).drop(columns='Ownership_Pct')
    p['Ownership_Share']=p.Ownership_Share.round(4); p['Ownership_Share_Sum']=p.Ownership_Share_Sum.round(4)
    wr(p,'Dim_Parent.csv')
log('Ownership given twice, as a percent (0-100) and as a share (0-1)','Ownership_Pct = 50, Ownership_Share = 0.5',f'{len(p):,} rows','Kept Ownership_Share (0-1) only; renamed Share_Sum to Ownership_Share_Sum')

# --- Eurostat ---
t=rd('Fact_Trade_EU_Imports.csv')
if 'Value_USD' not in t:
    t['USD_per_EUR']=t.Year.map(FX); t['Value_USD']=(t.Value_EUR*t.USD_per_EUR).round(0)
    t['Unit_Value_USD_per_t']=(t.Value_USD/t.Quantity_t).where(t.Quantity_t>0).round(2)
    t['Quantity_t']=t.Quantity_t.round(3)
    t=t[['Year','Partner_Code','Partner_Name','Partner_Is_EU27','Flow_Type','HS6','Product','Product_Group','Regulation','Quantity_t','Value_EUR','Value_USD','USD_per_EUR','Unit_Value_USD_per_t']]
    wr(t,'Fact_Trade_EU_Imports.csv')
log('EU trade values are in EUR while EIA prices are in USD, so the two could not be compared','Value_EUR vs Price_USD_per_Mcf',f'{len(t):,} rows',
    'Added Value_USD using the Eurostat annual average EUR/USD rate for each year (ert_bil_eur_a; Dim_FX_EUR_USD) and Unit_Value_USD_per_t; EUR kept for EU context')
e=rd('Eurostat_Totals.csv')
if 'TIME_PERIOD' in e:
    e=e.rename(columns={'TIME_PERIOD':'Year','partner':'Aggregate','product':'HS6'})
    e['Quantity_t']=(e.QUANTITY_IN_100KG/10).round(3); e['Value_EUR']=e.VALUE_IN_EUROS
    e['Value_USD']=(e.Value_EUR*e.Year.map(FX)).round(0)
    e=e[['Year','Aggregate','HS6','Quantity_t','Value_EUR','Value_USD']]
    wr(e,'Eurostat_Totals.csv')
log('Eurostat_Totals still had raw units and names (100 kg, TIME_PERIOD)','QUANTITY_IN_100KG',f'{len(e)} rows','Converted to Quantity_t, Value_EUR, Value_USD; renamed to Year, Aggregate, HS6')

# --- EIA: volumes in bcm only, prices in USD/MMBtu ---
for fn in ('Fact_LNG_Exports_Terminal.csv','LNG_Terminal_Totals.csv','Fact_EIA_Marketed_Production.csv','Fact_EIA_Gas_Exports.csv'):
    x=rd(fn)
    if 'Volume_MMcf' in x:
        x['Volume_bcm']=(x.Volume_MMcf*BCM).round(9); x=x.drop(columns='Volume_MMcf')
    if 'Price_USD_per_Mcf' in x:
        x['Price_USD_per_MMBtu']=(x.Price_USD_per_Mcf/MMBTU_PER_MCF).round(3); x=x.drop(columns='Price_USD_per_Mcf')
    wr(x,fn)
log('Gas volumes were in million cubic feet (EIA) while EU data and the brief use bcm','Volume_MMcf','4 EIA tables',
    'Volume_bcm only (1 MMcf = 0.0000283168 bcm, 9 decimals so small terminals keep precision); MMcf stays in the raw files')
log('Gas export prices were in USD per thousand cubic feet','Price_USD_per_Mcf','Fact_EIA_Gas_Exports',
    f'Converted to Price_USD_per_MMBtu (the US benchmark unit) using {MMBTU_PER_MCF} MMBtu per Mcf (EIA average heat content); approximate by about 1% because heat content varies a little by year')

# --- IEA: kt -> t ---
i=rd('Fact_IEA_Methane.csv')
if 'CH4_kt' in i:
    i['CH4_t']=(i.CH4_kt*1000).round(1)
    for g in ('AR5','AR6_100','AR6_20'): i[f'CO2e_{g}_tCO2e']=(i[f'CO2e_{g}_kt']*1000).round(0)
    i=i.drop(columns=['CH4_kt','CO2e_AR5_kt','CO2e_AR6_100_kt','CO2e_AR6_20_kt']).rename(columns={'Production_source':'Production_Source'})
    wr(i,'Fact_IEA_Methane.csv')
for fn in ('IEA_Methane_Totals.csv','Ref_IEA_Methane_By_Sector.csv'):
    x=rd(fn)
    if 'CH4_kt' in x: x['CH4_t']=(x.CH4_kt*1000).round(1); x=x.drop(columns='CH4_kt'); wr(x,fn)
log('IEA reports thousand tonnes (kt) while EPA reports tonnes','CH4_kt','3 IEA tables','Converted to CH4_t and CO2e_*_tCO2e (x 1,000)')
pd.DataFrame(dq).to_csv(O+'DQ_Log.csv',index=False)
print('dq',len(dq))

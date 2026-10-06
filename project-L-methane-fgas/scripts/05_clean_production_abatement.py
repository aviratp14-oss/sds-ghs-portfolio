# Project L cleaning, step 5: Subpart W facility overview (production, wells) and IEA abatement costs.
# Run after 04_apply_unit_standard.py. Writes in the unit standard directly (bcm, t, USD).
import pandas as pd, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
R = str(ROOT / 'data' / 'raw') + '/'; O = str(ROOT / 'data' / 'clean') + '/'
DS_W='EPA Subpart W facility overview'; DS_I='IEA methane abatement (oil & gas)'
dq=pd.read_csv(O+'DQ_Log.csv').query('Dataset not in [@DS_W, @DS_I]').to_dict('records')   # safe to re-run
def log(ds, issue, example, rows, fix):
    dq.append(dict(ID=len(dq)+1,Dataset=ds,Issue=issue,Example=example,Rows_Affected=rows,Fix=fix))
BCM_PER_MSCF=0.0283168/1e6        # 1 Mscf = 28.3168 m3
MMBTU_PER_T_CH4=52.6              # methane higher heating value, 55.5 GJ per tonne / 1.055 GJ per MMBtu

# --- EPA Subpart W facility overview, 2015-2023 ---
o=pd.concat([pd.read_csv(f,low_memory=False) for f in sorted(glob.glob(R+'epa_subpart_w_overview/*.csv'))],ignore_index=True)
log(DS_W,'Overview file stacks 12 different EPA tables (AA.1 to AA.10) in one sheet, each using different columns',
    'Table AA.1.i production, AA.1.ii sub-basins, AA.10.i pipeline miles',f'{len(o):,} rows, 48 columns',
    'Kept the two onshore production tables needed for methane intensity (AA.1.i and AA.1.ii); other segments stay in Raw Data')
def basin(x):
    c,_,n=str(x).partition(' - '); return c.strip(), n.strip()

p=o[o.table_num=='Table AA.1.i'].copy()
p[['Basin_Code','Basin_Name']]=p.basin_associated_with_facility.apply(lambda x: pd.Series(basin(x)))
bad=(p.facility_id==1013342)&(p.reporting_year==2019)
log(DS_W,'One facility reported gas sales about 1,000 times too high, so 2019 US production looked double the other years',
    'Felix Energy Holdings II LLC (1013342), 2019: 25.3 billion Mscf = 25 Tcf, more than half of all US output; its oil (15.8 million bbl) points to about 25 Bcf',
    f'{int(bad.sum())} row','Divided by 1,000 (treated as reported in scf instead of Mscf); flagged Gas_Value_Corrected = TRUE')
p['Gas_Value_Corrected']=bad
p.loc[bad,'gas_prod_cal_year_for_sales']/=1000
p['Gas_Sales_bcm']=(p.gas_prod_cal_year_for_sales*BCM_PER_MSCF).round(9)
p['Oil_Sales_bbl']=p.oil_prod_cal_year_for_sales.round(1)
log(DS_W,'Production in EPA units (gas in thousand standard cubic feet, oil in barrels)','gas_prod_cal_year_for_sales',f'{len(p):,} rows',
    'Gas converted to Gas_Sales_bcm (1 Mscf = 0.0000000283168 bcm); oil kept in barrels (Oil_Sales_bbl), the standard oil unit')

s=o[o.table_num=='Table AA.1.ii'].copy()
s['sub_basin_identifier']=s.sub_basin_identifier.str.strip()
n0=len(s); s=s.drop_duplicates(subset=[c for c in s if c!='table_desc']); nd=n0-len(s)
key=['facility_id','reporting_year','sub_basin_identifier']
log(DS_W,'Exact duplicate sub-basin rows',f'{nd} identical rows (facility, year, sub-basin and all values the same)',f'{nd} rows','Dropped')
dup=s.duplicated(key,keep=False).sum()
s=s.drop_duplicates(key+['well_producing_end_of_year','ch4_average_mole_fraction'])
s['CH4_x_wells']=s.ch4_average_mole_fraction*s.well_producing_end_of_year
sb=s.groupby(key,as_index=False).agg(Wells_Producing=('well_producing_end_of_year','max'),Wells_Completed=('wells_completed','max'),
    Wells_Acquired=('producing_wells_acquired','max'),Wells_Divested=('producing_wells_divested','max'),Wells_Removed=('well_removed_from_production','max'),
    CH4_x=('CH4_x_wells','sum'),CH4_Mole_Fraction=('ch4_average_mole_fraction','mean'),
    CO2_Mole_Fraction=('co2_average_mole_fraction','mean'),Gas_Oil_Well_Ratio=('gas_oil_well_ratio','mean'),API_Gravity=('api_gravity','mean'))
log(DS_W,'Formation type written in mixed case','"Shale Gas", "Shale gas", "oil"',f'{len(sb):,} rows','Standardised to sentence case (Shale gas, Oil, ...)')
if dup: log(DS_W,'Some oil sub-basins have several rows that differ only in pressure, API gravity or gas-to-oil ratio; the well count is repeated on each row','Facility 1008287, 2023',f'{dup} rows',
            'One row per sub-basin: well counts take the largest value (not summed, which would double count); pressure-type values averaged')
parts=sb.sub_basin_identifier.str.rsplit(' - ',n=1)
sb['Sub_Basin_Formation_Type']=parts.str[1].str.strip().str.capitalize()
cb=parts.str[0].str.split(' - ',n=1)
sb['Basin_Code']=cb.str[0]; sb['Sub_Basin_County']=cb.str[1]
sb['State']=sb.Sub_Basin_County.str.extract(r',\s*([A-Z]{2})\b')[0]
sb=sb.rename(columns={'facility_id':'Facility_Id','reporting_year':'Year','sub_basin_identifier':'Sub_Basin_Id'})
for c in ('CH4_Mole_Fraction','CO2_Mole_Fraction','Gas_Oil_Well_Ratio','API_Gravity'): sb[c]=sb[c].round(4)
sb=sb[['Year','Facility_Id','Basin_Code','Sub_Basin_Id','Sub_Basin_County','State','Sub_Basin_Formation_Type','Wells_Producing','Wells_Completed',
       'Wells_Acquired','Wells_Divested','Wells_Removed','CH4_Mole_Fraction','CO2_Mole_Fraction','Gas_Oil_Well_Ratio','API_Gravity']]
sb.to_csv(O+'Fact_SubpartW_SubBasin.csv',index=False)
log(DS_W,'Sub-basin id packs basin, county, state and formation type into one text field','230 - CADDO, LA (17) - High permeability gas',f'{len(sb):,} rows',
    'Split into Basin_Code, Sub_Basin_County, State, Sub_Basin_Formation_Type; original id kept as Sub_Basin_Id')

w=sb.groupby(['Facility_Id','Year']).agg(Wells_Producing=('Wells_Producing','sum'),Wells_Completed=('Wells_Completed','sum'),Sub_Basins=('Sub_Basin_Id','count')).reset_index()
s['wf']=s.well_producing_end_of_year
ch=s.groupby(key[:2]).apply(lambda g:(g.CH4_x_wells.sum()/g.wf.sum()) if g.wf.sum()>0 else g.ch4_average_mole_fraction.mean(),include_groups=False).round(4).rename('CH4_Mole_Fraction_Avg').reset_index()
ch=ch.rename(columns={'facility_id':'Facility_Id','reporting_year':'Year'})
fp=p.rename(columns={'facility_id':'Facility_Id','reporting_year':'Year','facility_name':'Facility_Name'})
fp=fp[['Year','Facility_Id','Facility_Name','Basin_Code','Basin_Name','Gas_Sales_bcm','Oil_Sales_bbl','Gas_Value_Corrected']]
fp=fp.merge(w,on=['Facility_Id','Year'],how='left').merge(ch,on=['Facility_Id','Year'],how='left')
fp.to_csv(O+'Fact_SubpartW_Facility_Production.csv',index=False)

# reconcile to EIA marketed production
e=pd.read_csv(O+'Fact_EIA_Marketed_Production.csv'); e=e[e.Level=='U.S. total'].set_index('Year').Volume_bcm
rec=fp.groupby('Year').Gas_Sales_bcm.sum().to_frame('EPA_Reported_bcm'); rec['EIA_US_Marketed_bcm']=e.reindex(rec.index)
rec['EPA_Coverage_Share']=(rec.EPA_Reported_bcm/rec.EIA_US_Marketed_bcm).round(3); rec=rec.round(3).reset_index()
rec.to_csv(O+'Recon_SubpartW_vs_EIA_Production.csv',index=False)
print(rec.to_string(index=False))
log(DS_W,'Subpart W only covers onshore production facilities above the 25,000 tCO2e threshold, so it is not all US gas',
    f'EPA share of EIA marketed production: {rec.EPA_Coverage_Share.min():.0%} to {rec.EPA_Coverage_Share.max():.0%} by year','',
    'Kept as reported; Recon_SubpartW_vs_EIA_Production shows the coverage each year. Use EPA production for facility intensity and EIA for national totals')

# --- IEA abatement ---
a=pd.read_csv(R+'iea/iea_methane_abatement_oilgas_world.csv')
a.columns=['Region','Country','Production_Source','Segment','Type','Measure','Savings_kt','Cost_USD_per_MMBtu']
ex=a.duplicated().sum()
log(DS_I,'File for United States arrived empty (1 byte)','IEA-methane-abatement-OILGASdataregionUnited States.csv','1 file',
    f'Not needed: the World file has all 102 United States rows ({(a.Country=="United States").sum()} rows); filter Country = United States')
log(DS_I,'Two pairs of identical rows','Region Other, Country Other, savings 0.01 kt',f'{ex*2} rows',
    'Kept: IEA groups small countries under "Other", so identical rows can be different countries')
gwp=pd.read_csv(O+'Dim_Gas.csv').set_index('Gas')
a['Savings_CH4_t']=(a.Savings_kt*1000).round(1)
a['Savings_CO2e_AR5_tCO2e']=(a.Savings_CH4_t*gwp.loc['CH4','GWP_AR5']).round(0)
a['Cost_USD_per_tCH4']=(a.Cost_USD_per_MMBtu*MMBTU_PER_T_CH4).round(2)
a['Cost_USD_per_tCO2e_AR5']=(a.Cost_USD_per_tCH4/gwp.loc['CH4','GWP_AR5']).round(2)
a['Is_Net_Saving']=a.Cost_USD_per_MMBtu<0
a=a.drop(columns='Savings_kt')
a.insert(0,'Row_Id',range(1,len(a)+1))
a.to_csv(O+'Fact_IEA_Abatement.csv',index=False)
log(DS_I,'Savings in thousand tonnes of methane and cost per MMBtu of gas saved, which cannot be compared with EPA tonnes or carbon prices',
    'savings (kt) = 1320.99, cost (USD/MBtu) = -1.59',f'{len(a):,} rows',
    f'Savings_CH4_t (x 1,000) and Savings_CO2e_AR5_tCO2e (GWP {gwp.loc["CH4","GWP_AR5"]}); Cost_USD_per_tCH4 = cost x {MMBTU_PER_T_CH4} MMBtu per tonne of methane; '
    'Cost_USD_per_tCO2e_AR5 = that / GWP. IEA "MBtu" means million Btu. Negative cost = gas sales pay for the measure')
M={'Annual LDAR':['Equipment Leaks Surveys and Population Counts'],'Biannual LDAR':['Equipment Leaks Surveys and Population Counts'],
   'Quarterly LDAR':['Equipment Leaks Surveys and Population Counts'],'Daily LDAR':['Equipment Leaks Surveys and Population Counts'],
   'Continuous LDAR':['Equipment Leaks Surveys and Population Counts'],
   'Replace with instrument air systems':['Natural Gas Pneumatic Devices','Natural Gas Driven Pneumatic Pumps'],
   'Replace with electric motor':['Natural Gas Pneumatic Devices','Natural Gas Driven Pneumatic Pumps'],
   'Replace pumps':['Natural Gas Driven Pneumatic Pumps'],'Vapour recovery units':['Atmospheric Storage Tanks'],
   'Blowdown capture':['Blowdown Vent Stacks'],'Replace compressor seal or rod':['Centrifugal Compressors','Reciprocating Compressors'],
   'Associated gas utilisation':['Associated Gas Venting and Flaring'],'Install plunger':['Well Venting for Liquids Unloading'],
   'Improve flaring':['Flare Stacks'],'Monitor and plug abandoned wells':[None],'Other':[None]}
assert set(M)==set(a.Measure.unique())
sc=set(pd.read_csv(O+'Dim_Source_Category.csv').Source_Category)
mp=pd.DataFrame([(k,v) for k,vs in M.items() for v in vs],columns=['Measure','Source_Category'])
assert set(mp.Source_Category.dropna())<=sc
mp['Note']=mp.Source_Category.isna().map({True:'No matching Subpart W source (not reported to EPA)',False:'Analyst mapping, review'})
mp.to_csv(O+'Map_Abatement_Source_Category.csv',index=False)
log(DS_I,'IEA measures and EPA source categories use different names','Vapour recovery units vs Atmospheric Storage Tanks','16 measures',
    'Map_Abatement_Source_Category links each measure to the Subpart W source it cuts (judgement; please review). Abandoned wells and Other have no EPA match')
pd.DataFrame(dq).to_csv(O+'DQ_Log.csv',index=False)
print('dq',len(dq),'prod',len(fp),'subbasin',len(sb),'abate',len(a))

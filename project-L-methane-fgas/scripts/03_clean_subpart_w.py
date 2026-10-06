# Project L cleaning, batch 3: EPA Subpart W emissions by source (Envirofacts export, one CSV per year).
# Run after 01 and 02. Picks up every year in data/raw/epa_subpart_w/.
import glob, re, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
R = str(ROOT / 'data' / 'raw') + '/'; O = str(ROOT / 'data' / 'clean') + '/'
DS='EPA Subpart W by source'
dq=pd.read_csv(O+'DQ_Log.csv').query('Dataset != @DS').to_dict('records')   # safe to re-run
def log(issue, example, rows, fix):
    dq.append(dict(ID=len(dq)+1,Dataset=DS,Issue=issue,Example=example,Rows_Affected=rows,Fix=fix))
files=sorted(glob.glob(R+'epa_subpart_w/*.csv'))
d=pd.concat([pd.read_csv(f) for f in files],ignore_index=True)
years=sorted(d.reporting_year.unique()); n0=len(d)
log('Downloaded from Envirofacts as one file per year, all named "CSV.csv"','CSV.csv, CSV 1.csv ...',f'{len(files)} files, {n0:,} rows',
    f'Renamed by reporting year (epa_subpart_w_emissions_by_source_YYYY.csv) and appended; years {years[0]}-{years[-1]}')
log('Two columns are completely empty','bamm_desc_source_summary, bamm_indicator_source_summary',f'{n0:,} rows','Dropped')
d=d.drop(columns=['bamm_desc_source_summary','bamm_indicator_source_summary'])
G={'total_reported_co2_emissions':'CO2','total_reported_ch4_emissions':'CH4','total_reported_n2o_emissions':'N2O'}
blank=(d[list(G)].fillna(0)==0).all(axis=1)
log('Every facility gets a row for all 22 source categories, even ones that do not apply to its segment, so most rows are blank or zero',
    'Pipeline facility with a "Well Testing" row',f'{blank.sum():,} of {n0:,} rows','Dropped rows where CO2, CH4 and N2O are all blank or zero')
d=d[~blank].copy()
# split "Name [98.236(x)]" into name + rule citation
for col,new in (('reporting_category','Source_Category'),('industry_segment','Industry_Segment')):
    d[new]=d[col].str.replace(r'\s*\[.*$','',regex=True).str.strip()
    d[new+'_Citation']=d[col].str.extract(r'\[(.*?)\]?$')[0]
d['Source_Category_Reported']=d.Source_Category
# EPA renamed or merged categories after the 2015-2017 rule changes; map legacy names to the current ones
# (checked: no facility-year reports under both a legacy and a current name, so nothing is double counted)
LEGACY={'Combustion Equipment at Onshore Petroleum and Natural Gas Production and Natural Gas Distribution Facilities':'Combustion Equipment',
        'Onshore Petroleum and Natural Gas Production and Natural Gas Distribution Combustion Emissions':'Combustion Equipment',
        'Production Storage Tanks':'Atmospheric Storage Tanks','Gas from Produced Oil Sent to Atmospheric Tanks':'Atmospheric Storage Tanks',
        'Gas Well Completions and Workovers':'Completions and Workovers (not split by fracturing)',
        'Enhanced Oil Recovery Injection Pumps Blowdown':'Enhanced Oil Recovery Injection Pumps','Enhanced Oil Recovery Injection Pump Blowdown':'Enhanced Oil Recovery Injection Pumps',
        'Other Emissions from Equipment Leaks Estimated Using Emission Factors':'Equipment Leaks Surveys and Population Counts',
        'Local Distribution Companies':'Equipment Leaks Surveys and Population Counts','Transmission Tanks':'Transmission Storage Tanks',
        'Well Testing Venting and Flaring':'Well Testing','Offshore Sources':'Offshore Petroleum and Natural Gas Production'}
d.loc[d.Source_Category.str.startswith('Combustion Equipment at Onshore Petroleum and Natural Gas Production Facilities,'),'Source_Category']='Combustion Equipment'
nleg=d.Source_Category.isin(LEGACY).sum()
d['Source_Category']=d.Source_Category.replace(LEGACY)
log('EPA renamed source categories between 2015 and 2018 (e.g. "Production Storage Tanks" became "Atmospheric Storage Tanks"; 2015 completions are not split by hydraulic fracturing)',
    '"Gas Well Completions and Workovers [98.236(g,h)]" (2015)',f'{nleg:,} rows',
    'Mapped legacy names to the current category; original names listed in Map_Source_Category_Legacy. Checked that no facility-year reports under both names')
log('Source category and segment names carry the 40 CFR 98 citation in brackets; one category name is 190 characters long',
    '"Combustion Equipment at Onshore Petroleum and Natural Gas Production Facilities, ... [98.236(z)"',f'{len(d):,} rows',
    'Moved citations to *_Citation columns; shortened the combustion category to "Combustion Equipment"')
SEG={'Onshore petroleum and natural gas production':'Onshore Production','Onshore petroleum and natural gas gathering and boosting':'Gathering & Boosting',
     'Onshore natural gas transmission pipeline':'Transmission Pipelines','Natural gas distribution':'Local Distribution',
     'Offshore petroleum and natural gas production':'Offshore Production','Onshore natural gas processing':'Processing',
     'Onshore natural gas transmission compression':'Transmission Compression','Underground natural gas storage':'Underground Storage',
     'LNG import and export equipment':'LNG Import/Export','Liquefied natural gas (LNG) storage':'LNG Storage'}
d['Segment']=d.Industry_Segment.map(SEG)
assert d.Segment.notna().all(), d.loc[d.Segment.isna(),'Industry_Segment'].unique()
log('Segment names differ from the yearly summary files','"Onshore petroleum and natural gas gathering and boosting" vs "Gathering & Boosting"','10 segments',
    'Added a short Segment name matching Fact_Emissions so both tables filter the same way')
# emission type, for comparison with IEA "Reason" (Vented / Fugitive / Incomplete-flare)
ET={'Natural Gas Pneumatic Devices':'Vented','Natural Gas Driven Pneumatic Pumps':'Vented','Equipment Leaks Surveys and Population Counts':'Fugitive',
    'Reciprocating Compressors':'Vented','Centrifugal Compressors':'Vented','Blowdown Vent Stacks':'Vented','Well Venting for Liquids Unloading':'Vented',
    'Completions and Workovers with Hydraulic Fracturing':'Vented','Completions and Workovers (not split by fracturing)':'Vented','Completions and Workovers without Hydraulic Fracturing':'Vented',
    'Atmospheric Storage Tanks':'Vented','Transmission Storage Tanks':'Vented','Dehydrators':'Vented','Acid Gas Removal Units':'Vented',
    'Enhanced Oil Recovery Hydrocarbon Liquids':'Vented','Enhanced Oil Recovery Injection Pumps':'Vented',
    'Associated Gas Venting and Flaring':'Flared and vented','Well Testing':'Flared and vented','Flare Stacks':'Incomplete flare',
    'Combustion Equipment':'Combustion','Offshore Petroleum and Natural Gas Production':'Offshore (mixed)'}
d['Emission_Type']=d.Source_Category.map(ET)
assert d.Emission_Type.notna().all(), d.loc[d.Emission_Type.isna(),'Source_Category'].unique()
log('No emission type (vented, fugitive, flared, combustion) in the data','-','22 categories',
    'Added Emission_Type from the source category (analyst mapping, matches IEA Methane Tracker "Reason" where possible)')
b=d.basin_associated_with_facility.fillna('')
d['Basin_Code']=b.str.extract(r'^\s*([^\s-]+)\s*-')[0]; d['Basin_Name']=b.str.extract(r'-\s*(.+)$')[0].str.strip()
nb=d.Basin_Code.isna().sum()
log('Basin only reported for basin-based segments (production, gathering and boosting); blank elsewhere','Processing plant rows',f'{nb:,} rows',
    'Split "code - name" into Basin_Code and Basin_Name; left blank where the segment has no basin')
# units: metric tonnes of each gas (checked: per-facility CH4 matches the summary sheets x 1.0 for 99.8% of facility-years)
L=d.melt(id_vars=['reporting_year','facility_id','Segment','Industry_Segment_Citation','Source_Category','Source_Category_Reported','Source_Category_Citation','Emission_Type','Basin_Code','Basin_Name'],
         value_vars=list(G),var_name='Gas',value_name='Tonnes_Gas')
L['Gas']=L.Gas.map(G); nz=len(L)
L=L[L.Tonnes_Gas.fillna(0)!=0]
log('Values are metric tonnes of each gas, not CO2e (the yearly summary files use AR4 CO2e)','total_reported_ch4_emissions',
    f'{len(L):,} rows after unpivot ({nz-len(L):,} blank/zero gas cells dropped)',
    'Checked against the summary sheets: facility CH4 totals match (ratio 1.00) for 99.9% (2015-2023) of onshore production, gathering, transmission pipeline and distribution facility-years. Unpivoted to one row per gas and added AR4, AR5, AR6-100 and AR6-20 CO2e with the Dim_Gas GWPs')
gwp=pd.read_csv(O+'Dim_Gas.csv').set_index('Gas')
for c,g in (('CO2e_AR4_t','GWP_AR4'),('CO2e_AR5_t','GWP_AR5'),('CO2e_AR6_100_t','GWP_AR6_100'),('CO2e_AR6_20_t','GWP_AR6_20')):
    L[c]=(L.Tonnes_Gas*L.Gas.map(gwp[g])).round(3)
L['Tonnes_Gas']=L.Tonnes_Gas.round(4)
neg=(L.Tonnes_Gas<0).sum()
if neg: log('Negative emission values','-',f'{neg} rows','Checked; kept as reported')
dim=pd.read_csv(O+'Dim_Facility.csv',usecols=[0])
miss=~L.facility_id.isin(dim.iloc[:,0])
nf=L.loc[miss,'facility_id'].nunique()
if nf: log('Some Subpart W facilities are missing from Dim_Facility (they report only in Subpart W files)','-',f'{nf} facilities, {miss.sum():,} rows',
    'Kept; added their latest name to Dim_Facility_SubpartW_Extra so the Power BI relationship has no blanks')
if nf:
    names=d.sort_values('reporting_year').groupby('facility_id').facility_name.last()
    names[names.index.isin(L.loc[miss,'facility_id'])].rename('Facility Name').rename_axis('Facility Id').to_frame().to_csv(O+'Dim_Facility_SubpartW_Extra.csv')
L=L.rename(columns={'reporting_year':'Year','facility_id':'Facility Id'})
# keep the fact table narrow (Google Sheets cell limit); descriptive columns go to small lookup tables
L[['Source_Category','Emission_Type','Source_Category_Citation']].drop_duplicates('Source_Category').sort_values('Source_Category').to_csv(O+'Dim_Source_Category.csv',index=False)
L[['Source_Category_Reported','Source_Category']].drop_duplicates().query('Source_Category_Reported != Source_Category').to_csv(O+'Map_Source_Category_Legacy.csv',index=False)
log('Wide text columns repeat on every row (37 MB file)','Source category citation, basin name',f'{len(L):,} rows',
    'Moved category citation and emission type to Dim_Source_Category, legacy names to Map_Source_Category_Legacy; basin name is in Fact_Emissions/Dim_Facility via Basin_Code')
L=L[['Year','Facility Id','Segment','Basin_Code','Source_Category','Gas','Tonnes_Gas','CO2e_AR4_t','CO2e_AR5_t','CO2e_AR6_100_t','CO2e_AR6_20_t']]
L.sort_values(['Year','Facility Id','Source_Category','Gas']).to_csv(O+'Fact_SubpartW_Source.csv',index=False)
log('Gathering & Boosting and Transmission Pipelines segments only report from 2016, so 2015 totals are not comparable','2015 has no Gathering & Boosting rows','2015 (all rows)',
    'Kept 2015; use 2016-2023 for trends and intensity models, or compare like-for-like segments only')
pd.DataFrame(dq).to_csv(O+'DQ_Log.csv',index=False)
print('rows',len(L),'years',years,'missing facilities',nf,'dq',len(dq))
print(L[L.Gas=='CH4'].groupby('Year').Tonnes_Gas.sum().round(0).to_dict())
print(L[(L.Gas=='CH4')&(L.Year==L.Year.max())].groupby('Source_Category').CO2e_AR4_t.sum().sort_values(ascending=False).head(6).round(0).to_dict())

import pandas as pd, numpy as np, re, math
from scipy.stats import theilslopes, kendalltau
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HGA=ROOT/'data'/'HGA-28082026.xlsx'
COORD=ROOT/'data'/'Coordenadas.xlsx'
REF=pd.Timestamp('2026-08-28')
INI=REF-pd.DateOffset(years=10)
XMIN,YMIN,XMAX,YMAX=648700.4479,7760701.2652,667298.2571,7773899.3678

def norm(x): return re.sub(r'\s+','',str(x or '')).upper()
STATUS_OPERACIONAL_OVERRIDE = {'G00-11PTR006': 'Tamponado'}
def situacao_operacional(tag, cadastro):
    return STATUS_OPERACIONAL_OVERRIDE.get(norm(tag), str(cadastro or '').strip())
h=pd.read_excel(HGA)
c=pd.read_excel(COORD)
c['inst_id']=c['TAG HGA'].map(norm); h['inst_id']=h['Ponto'].map(norm)
c=c[pd.to_numeric(c['X(m)'],errors='coerce').between(XMIN,XMAX)&pd.to_numeric(c['Y(m)'],errors='coerce').between(YMIN,YMAX)].copy()
# Somente instrumentos ativos entram também na análise histórica/tendência.
c['situacao_operacional'] = c.apply(lambda r: situacao_operacional(r.get('TAG HGA'), r.get('Situacao Atual')), axis=1)
c = c[(c['situacao_operacional'].astype(str).str.strip().str.casefold() == 'ativo') &
      (c['Proposito'] == 'Monitoramento Hidrogeologico') &
      (c['Natureza do Ponto'] != 'Cava')].copy()
ids=set(c.inst_id); h=h[h.inst_id.isin(ids)].copy()
h['data']=pd.to_datetime(h['DATA_'],errors='coerce')
h['cota']=pd.to_numeric(h['Cota_NA_m'],errors='coerce')
h['na']=pd.to_numeric(h['NA_m'],errors='coerce')
h['cota_poco']=pd.to_numeric(h['Cota_Poco_m'],errors='coerce')
# window + valid numerical, no future
w=h[(h.data>=INI)&(h.data<=REF)&h.cota.notna()].copy()
# remove physically inconsistent: NA >=0 and if depth available <= depth (+0.1), cota <= cota_poco + tol
meta=c.set_index('inst_id')
w=w.join(meta[['Profundidade(m)']],on='inst_id')
dep=pd.to_numeric(w['Profundidade(m)'],errors='coerce')
valid=(w.na.isna() | (w.na>=0)) & (w.cota_poco.isna() | (w.cota<=w.cota_poco+0.05)) & (dep.isna() | w.na.isna() | (w.na<=dep+0.1))
w=w[valid].copy()
# daily median collapses multiple readings, and remove exact consecutive duplicate daily cota to avoid flatline overweight
rows=[]
for inst,g in w.groupby('inst_id'):
    m=meta.loc[inst]
    # Apenas ativos já chegaram até aqui; omite somente ponto virtual.
    if 'PVIRTUAL' in inst: continue
    d=(g.assign(data_dia=g.data.dt.normalize()).groupby('data_dia',as_index=False).agg(cota=('cota','median')).rename(columns={'data_dia':'data'}))
    d=d.sort_values('data')
    d=d[d.cota.ne(d.cota.shift())].copy()
    span=(d.data.max()-d.data.min()).days/365.25 if len(d) else 0
    if len(d)<40 or span<8: continue
    t=(d.data-d.data.min()).dt.total_seconds().to_numpy()/86400/365.25
    v=d.cota.to_numpy(float)
    slope=float(theilslopes(v,t,method='separate')[0])
    tau,p=kendalltau(t,v,variant='b',method='auto')
    rows.append(dict(inst_id=inst,x=m['X(m)'],y=m['Y(m)'],localidade=m['Localidade'],tipo=m['Natureza do Ponto'],anos=round(span,1),n=len(d),taxa=slope,p=float(p),significativo=bool(p<.05),bombeamento=m['Natureza do Ponto']=='Poco Tubular'))
r=pd.DataFrame(rows).sort_values('taxa')
r.to_csv(ROOT/'taxas.csv',index=False)
print('n',len(r),'sig',r.significativo.sum(),'pocos',r.bombeamento.sum())
print(r[~r.bombeamento & r.significativo].groupby('localidade').agg(n=('inst_id','size'),med=('taxa','median')).sort_index().round(3))
print('N/S', r[(~r.bombeamento)&r.significativo&r.localidade.isin(['Alegria Norte','Alegria Sul'])].groupby('localidade').taxa.median())

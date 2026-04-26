#!/usr/bin/env python3
"""
build_data_v3.py  —  Pipeline completo: lê os .xlsx do e-SUS → gera dashboard_data_v3.json
Roda a partir da pasta do projeto. Requer os arquivos .xlsx (não versionados por LGPD).

Uso:
    python build_data_v3.py

Pré-requisitos:
    pip install pandas openpyxl
"""
import json
import gc
from pathlib import Path

import pandas as pd
import numpy as np

# ─── CAMINHOS (relativos à pasta do script) ──────────────────────────────────
BASE = Path(__file__).parent
import glob as _glob

def _find(pattern):
    matches = _glob.glob(str(BASE / pattern), recursive=True)
    return matches[0] if matches else None

FAI_PATH     = _find("*fai*.xlsx")
FCI_PATH     = _find("*fci*.xlsx")
CIDADAO_PATH = _find("*cidadao*.xlsx")
BASE_JSON    = BASE / "dashboard_data.json"    # JSON base com populações e CIDs
OUT_JSON     = BASE / "dashboard_data_v3.json"

if not FAI_PATH or not FCI_PATH or not CIDADAO_PATH:
    raise FileNotFoundError(
        "Arquivos .xlsx do e-SUS não encontrados na pasta do projeto.\n"
        f"  FAI: {FAI_PATH}\n  FCI: {FCI_PATH}\n  CIDADAO: {CIDADAO_PATH}"
    )

print(f"FAI:     {Path(FAI_PATH).name}")
print(f"FCI:     {Path(FCI_PATH).name}")
print(f"CIDADAO: {Path(CIDADAO_PATH).name}")

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
RURAL_UBS = {
    'UBS VILA SAO JOSE', 'UBS POCAO', 'UBS PAU DARCO', 'UBS VILA APARECIDA',
    'UBS BOM JARDIM', 'UBS LARANJAL', 'UBS CANGANDU', 'UBS AGRESTE',
    'UBS BANANEIRAS', 'UBS CARRASCO', 'UBS VILA FERNANDES PAU FERRO',
    'UBS CAPIM', 'UBS BAIXA DA ONCA',
}
REFERENCE_DATE = pd.Timestamp('2025-07-01')
AGE_BINS   = [0, 1, 2, 5, 10, 18, 30, 45, 60, 200]
AGE_LABELS = ['<1a', '1a', '2-4a', '5-9a', '10-17a', '18-29a', '30-44a', '45-59a', '60+']
MES_NOMES  = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
              'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
SUPRESSAO_N = 5   # LGPD: suprimir células com n < SUPRESSAO_N

# ─── 1. CARREGAR DADOS ────────────────────────────────────────────────────────
print("\nCarregando FAI...")
fai = pd.read_excel(FAI_PATH, usecols=['CNS', 'CPF', 'SEXO', 'DATA DA CONSULTA', 'UNIDADE SAUDE', 'CIDS'])
print(f"  FAI: {fai.shape}")

print("Carregando FCI...")
fci = pd.read_excel(FCI_PATH, usecols=['CPF', 'CNS', 'UNIDADE SAUDE', 'EQUIPE', 'MICRO AREA', 'DATA NASCIMENTO'])
print(f"  FCI: {fci.shape}")

print("Carregando CIDADAO...")
try:
    cidadao = pd.read_excel(CIDADAO_PATH,
        usecols=['CPF', 'CNS', 'BAIRRO', 'CIDADE', 'UF', 'CEP',
                 'UNIDADE SAUDE', 'EQUIPE', 'DATA NASCIMENTO', 'LOGRADOURO', 'MICRO AREA'])
except ValueError:
    cidadao = pd.read_excel(CIDADAO_PATH,
        usecols=['CPF', 'CNS', 'BAIRRO', 'CIDADE', 'UF', 'CEP',
                 'UNIDADE SAUDE', 'EQUIPE', 'DATA NASCIMENTO', 'LOGRADOURO'])
    cidadao['MICRO AREA'] = None
print(f"  CIDADAO: {cidadao.shape}")

# ─── 2. PREPARAR CHAVES CPF/CNS ───────────────────────────────────────────────
def prep_cpf(col):
    return pd.to_numeric(col, errors='coerce').astype('Int64').replace(0, pd.NA)

for df_tmp in [fai, fci, cidadao]:
    df_tmp['CPF_int'] = prep_cpf(df_tmp['CPF'])
    df_tmp['CNS'] = df_tmp['CNS'].astype(str).str.strip()

# Desduplicar FCI e CIDADAO por CPF (manter registro mais completo)
print("\nDesduplicando...")
for df_tmp in [fci, cidadao]:
    df_tmp['_cnt'] = df_tmp.notna().sum(axis=1)
    df_tmp.sort_values(['CPF_int', '_cnt'], ascending=[True, False], inplace=True)
    df_tmp.drop_duplicates('CPF_int', keep='first', inplace=True)
    df_tmp.drop('_cnt', axis=1, inplace=True)
print(f"  FCI: {len(fci)}, CIDADAO: {len(cidadao)}")
gc.collect()

# ─── 3. MERGE ─────────────────────────────────────────────────────────────────
print("\nMerging...")
merged = fai.merge(
    fci[['CPF_int', 'CNS', 'UNIDADE SAUDE', 'EQUIPE', 'MICRO AREA', 'DATA NASCIMENTO']],
    on='CPF_int', how='left', suffixes=('', '_fci')
)
merged = merged.merge(
    cidadao[['CPF_int', 'CNS', 'BAIRRO', 'UNIDADE SAUDE', 'EQUIPE',
             'DATA NASCIMENTO', 'MICRO AREA']],
    on='CPF_int', how='left', suffixes=('', '_cid')
)
del fai, fci, cidadao
gc.collect()

# Consolidar campos com fallback
merged['UBS_FINAL']    = merged['UNIDADE SAUDE'].fillna(merged['UNIDADE SAUDE_cid'])
merged['EQ_FINAL']     = merged['EQUIPE'].fillna(merged['EQUIPE_cid'])
merged['MICRO_FINAL']  = merged['MICRO AREA'].fillna(merged['MICRO AREA_cid'])
merged['BAIRRO_FINAL'] = merged['BAIRRO'].str.upper().str.strip() if 'BAIRRO' in merged.columns else None
merged['DATA_NASC']    = pd.to_datetime(
    merged['DATA NASCIMENTO'].fillna(merged['DATA NASCIMENTO_cid']), errors='coerce')
merged['DATA_CONSULTA'] = pd.to_datetime(merged['DATA DA CONSULTA'], errors='coerce')

# Campos derivados
merged['idade']      = ((merged['DATA_CONSULTA'] - merged['DATA_NASC']).dt.days / 365.25).clip(0)
merged['FAIXA']      = pd.cut(merged['idade'], bins=AGE_BINS, labels=AGE_LABELS, right=False).astype(str)
merged['MENOR5']     = merged['idade'] < 5
merged['MES']        = merged['DATA_CONSULTA'].dt.month
merged['IS_COMPLEXO'] = merged['UNIDADE SAUDE'].astype(str).str.contains('COMPLEXO', na=False)
merged['SEXO_N']     = merged['SEXO'].fillna('I').astype(str).str.upper().str.strip()
merged['SEXO_N']     = merged['SEXO_N'].apply(lambda x: x if x in ('M', 'F') else 'I')
merged['CID_STR']    = merged['CIDS'].astype(str).str.replace('|', '', regex=False).str.strip()

# ─── 4. FILTRAR A09 ───────────────────────────────────────────────────────────
print("\nFiltrando CID A09...")
df = merged[merged['CID_STR'].str.contains('A09', na=False)].copy()
print(f"  Casos A09: {len(df)}")
del merged
gc.collect()

# Recorrência por CPF
cpf_count = df.groupby('CPF_int').size().rename('N_ATEND')
df = df.join(cpf_count, on='CPF_int')
df['IS_REPETIDO'] = df['N_ATEND'] > 1

# ─── 5. CARREGAR BASE JSON (populações, CIDs) ─────────────────────────────────
print("\nCarregando base JSON...")
with open(BASE_JSON, encoding='utf-8') as f:
    base = json.load(f)

# ─── 6. HELPERS ───────────────────────────────────────────────────────────────
def suprimir(n):
    """Retorna 0 se n < SUPRESSAO_N (LGPD), caso contrário n."""
    return 0 if (n is not None and 0 < int(n) < SUPRESSAO_N) else int(n) if n else 0

# ─── 7. METADATA ──────────────────────────────────────────────────────────────
total_atend       = len(df)
total_pacientes   = int(df.CPF_int.nunique())
total_menor5      = int(df.MENOR5.sum())
pac_menor5        = int(df[df.MENOR5].CPF_int.nunique())
total_repetidos   = int(df.IS_REPETIDO.sum())
pac_repetidos     = int(df[df.IS_REPETIDO].CPF_int.nunique())
total_complexo    = int(df.IS_COMPLEXO.sum())
pac_complexo      = int(df[df.IS_COMPLEXO].CPF_int.nunique())
menor5_repetidos  = int(df[df.MENOR5 & df.IS_REPETIDO].shape[0])
menor5_complexo   = int(df[df.MENOR5 & df.IS_COMPLEXO].shape[0])
pac5_repetidos    = int(df[df.MENOR5 & df.IS_REPETIDO].CPF_int.nunique())
pac5_complexo     = int(df[df.MENOR5 & df.IS_COMPLEXO].CPF_int.nunique())

metadata = {
    **base.get('metadata', {}),
    'total_atendimentos':  total_atend,
    'total_pacientes':     total_pacientes,
    'total_menor5':        total_menor5,
    'pacientes_menor5':    pac_menor5,
    'total_repetidos':     total_repetidos,
    'pacientes_repetidos': pac_repetidos,
    'total_complexo':      total_complexo,
    'pacientes_complexo':  pac_complexo,
    'menor5_repetidos':    menor5_repetidos,
    'menor5_complexo':     menor5_complexo,
    'pac5_repetidos':      pac5_repetidos,
    'pac5_complexo':       pac5_complexo,
}

# ─── 8. SERIE_TEMPORAL ────────────────────────────────────────────────────────
grp = df.groupby('MES')
st_df = grp.agg(
    total     =('CPF_int','count'),
    menor5    =('MENOR5','sum'),
    pacientes =('CPF_int','nunique'),
    repetidos =('IS_REPETIDO','sum'),
    complexo  =('IS_COMPLEXO','sum'),
).reset_index()
pm5 = df[df.MENOR5].groupby('MES').CPF_int.nunique().reset_index()
pm5.columns = ['MES','pacientes_menor5']
st_df = st_df.merge(pm5, on='MES', how='left').fillna(0)
m5rep = df[df.MENOR5 & df.IS_REPETIDO].groupby('MES').size().reset_index(name='menor5_repetidos')
m5cx  = df[df.MENOR5 & df.IS_COMPLEXO].groupby('MES').size().reset_index(name='menor5_complexo')
st_df = st_df.merge(m5rep, on='MES', how='left').fillna(0)
st_df = st_df.merge(m5cx,  on='MES', how='left').fillna(0)

serie_temporal = []
for _, r in st_df.iterrows():
    serie_temporal.append({
        'mes': int(r.MES), 'nome': MES_NOMES[int(r.MES)],
        'total': int(r.total), 'menor5': int(r.menor5),
        'pacientes': int(r.pacientes), 'pacientes_menor5': int(r.pacientes_menor5),
        'repetidos': int(r.repetidos), 'complexo': int(r.complexo),
        'menor5_repetidos': int(r.menor5_repetidos),
        'menor5_complexo':  int(r.menor5_complexo),
    })
serie_temporal.sort(key=lambda x: x['mes'])

# ─── 9. SERIE_TEMPORAL_FAIXA ──────────────────────────────────────────────────
stf = df.groupby(['MES','FAIXA']).agg(
    casos    =('CPF_int','count'),
    complexo =('IS_COMPLEXO','sum'),
    repetidos=('IS_REPETIDO','sum'),
).reset_index()
serie_temporal_faixa = [
    {'mes': int(r.MES), 'faixa': str(r.FAIXA),
     'casos': int(r.casos), 'complexo': int(r.complexo), 'repetidos': int(r.repetidos)}
    for _, r in stf.iterrows()
]

# ─── 10. SERIE_TEMPORAL_UBS ───────────────────────────────────────────────────
stubs = df.groupby(['MES','UBS_FINAL']).agg(
    casos    =('CPF_int','count'),
    menor5   =('MENOR5','sum'),
    repetidos=('IS_REPETIDO','sum'),
    complexo =('IS_COMPLEXO','sum'),
).reset_index()
serie_temporal_ubs = [
    {'ubs': str(r.UBS_FINAL), 'mes': int(r.MES),
     'casos': int(r.casos), 'menor5': int(r.menor5),
     'repetidos': int(r.repetidos), 'complexo': int(r.complexo)}
    for _, r in stubs.iterrows()
]

# ─── 11. SERIE_TEMPORAL_BAIRRO ────────────────────────────────────────────────
stbairro = df.groupby(['MES','BAIRRO_FINAL']).agg(
    casos    =('CPF_int','count'),
    menor5   =('MENOR5','sum'),
    repetidos=('IS_REPETIDO','sum'),
    complexo =('IS_COMPLEXO','sum'),
).reset_index()
serie_temporal_bairro = [
    {'bairro': str(r.BAIRRO_FINAL), 'mes': int(r.MES),
     'casos': int(r.casos), 'menor5': int(r.menor5),
     'repetidos': int(r.repetidos), 'complexo': int(r.complexo)}
    for _, r in stbairro.iterrows()
]

# ─── 12. SERIE_TEMPORAL_SEXO (NOVO) ───────────────────────────────────────────
stsexo = df.groupby(['MES','SEXO_N']).size().unstack(fill_value=0).reset_index()
for col in ['M','F','I']:
    if col not in stsexo.columns:
        stsexo[col] = 0
stsexo_m5 = df[df.MENOR5].groupby(['MES','SEXO_N']).size().unstack(fill_value=0).reset_index()
for col in ['M','F']:
    if col not in stsexo_m5.columns:
        stsexo_m5[col] = 0
stsexo_m5 = stsexo_m5.rename(columns={'M':'M_m5','F':'F_m5'})

serie_temporal_sexo = []
for _, r in stsexo.iterrows():
    m5_rows = stsexo_m5[stsexo_m5.MES == r.MES]
    m5_row = m5_rows.iloc[0] if len(m5_rows) > 0 else None
    serie_temporal_sexo.append({
        'mes': int(r.MES),
        'masculino': int(r.get('M', 0)),
        'feminino':  int(r.get('F', 0)),
        'nao_informado': int(r.get('I', 0)),
        'masculino_menor5': int(m5_row['M_m5']) if m5_row is not None and 'M_m5' in m5_row else 0,
        'feminino_menor5':  int(m5_row['F_m5']) if m5_row is not None and 'F_m5' in m5_row else 0,
    })
serie_temporal_sexo.sort(key=lambda x: x['mes'])

# ─── 13. POR_UBS ──────────────────────────────────────────────────────────────
ubs_grp = df.groupby('UBS_FINAL').agg(
    casos_total     =('CPF_int','count'),
    casos_menor5    =('MENOR5','sum'),
    pacientes_total =('CPF_int','nunique'),
    casos_repetidos =('IS_REPETIDO','sum'),
    casos_complexo  =('IS_COMPLEXO','sum'),
).reset_index()
ubs_pm5 = df[df.MENOR5].groupby('UBS_FINAL').CPF_int.nunique().reset_index()
ubs_pm5.columns = ['UBS_FINAL','pacientes_menor5']
ubs_grp = ubs_grp.merge(ubs_pm5, on='UBS_FINAL', how='left').fillna(0)

por_ubs_existing = {x['ubs']: x for x in base.get('por_ubs', [])}
por_ubs = []
for _, r in ubs_grp.iterrows():
    ubs_name = str(r.UBS_FINAL)
    ex = por_ubs_existing.get(ubs_name, {})
    pop_total  = int(ex.get('pop_total',  0) or 0)
    pop_menor5 = int(ex.get('pop_menor5', 0) or 0)
    casos  = int(r.casos_total)
    menor5 = int(r.casos_menor5)
    zona   = ex.get('zona', 'RURAL' if ubs_name in RURAL_UBS else 'URBANA')
    por_ubs.append({
        'ubs': ubs_name, 'zona': zona,
        'pop_total': pop_total, 'pop_menor5': pop_menor5,
        'casos_total': casos, 'casos_menor5': menor5,
        'pacientes_total': int(r.pacientes_total),
        'pacientes_menor5': int(r.pacientes_menor5),
        'casos_repetidos': int(r.casos_repetidos),
        'casos_complexo': int(r.casos_complexo),
        'pct_complexo': round(int(r.casos_complexo)/casos*100, 1) if casos > 0 else 0,
        'taxa_geral':  round(casos/pop_total*1000, 1) if pop_total > 0 else 0,
        'taxa_menor5': round(menor5/pop_menor5*1000, 1) if pop_menor5 > 0 else 0,
        'bairros': ex.get('bairros', []),
    })
por_ubs.sort(key=lambda x: x['casos_total'], reverse=True)

# ─── 14. POR_UBS_SEXO (NOVO) ──────────────────────────────────────────────────
ubs_sexo = df.groupby(['UBS_FINAL','SEXO_N']).size().unstack(fill_value=0).reset_index()
for col in ['M','F','I']:
    if col not in ubs_sexo.columns:
        ubs_sexo[col] = 0
ubs_sexo_m5 = df[df.MENOR5].groupby(['UBS_FINAL','SEXO_N']).size().unstack(fill_value=0).reset_index()
for col in ['M','F']:
    if col not in ubs_sexo_m5.columns:
        ubs_sexo_m5[col] = 0
ubs_sexo_m5 = ubs_sexo_m5.rename(columns={'M':'M_m5','F':'F_m5'})
ubs_sexo = ubs_sexo.merge(ubs_sexo_m5[['UBS_FINAL','M_m5','F_m5']], on='UBS_FINAL', how='left').fillna(0)

por_ubs_sexo = []
for _, r in ubs_sexo.iterrows():
    por_ubs_sexo.append({
        'ubs': str(r.UBS_FINAL),
        'masculino':        suprimir(int(r.get('M', 0))),
        'feminino':         suprimir(int(r.get('F', 0))),
        'nao_informado':    suprimir(int(r.get('I', 0))),
        'masculino_menor5': suprimir(int(r.get('M_m5', 0))),
        'feminino_menor5':  suprimir(int(r.get('F_m5', 0))),
    })

# ─── 15. POR_UBS_FAIXA (NOVO) ─────────────────────────────────────────────────
ubs_faixa = df.groupby(['UBS_FINAL','FAIXA']).agg(
    casos    =('CPF_int','count'),
    complexo =('IS_COMPLEXO','sum'),
    repetidos=('IS_REPETIDO','sum'),
).reset_index()

por_ubs_faixa = []
for ubs_name, grp in ubs_faixa.groupby('UBS_FINAL'):
    faixas_list = []
    for _, r in grp.iterrows():
        faixas_list.append({
            'faixa':     str(r.FAIXA),
            'casos':     suprimir(int(r.casos)),
            'complexo':  suprimir(int(r.complexo)),
            'repetidos': suprimir(int(r.repetidos)),
        })
    por_ubs_faixa.append({'ubs': str(ubs_name), 'faixas': faixas_list})

# ─── 16. CIDS_POR_UBS (NOVO) ──────────────────────────────────────────────────
df_cid = df[['UBS_FINAL','CID_STR','MENOR5']].copy()
df_cid['CID_EXPANDED'] = df_cid['CID_STR'].str.findall(r'A\d{2}(?:\.\d+)?')
df_cid = df_cid.explode('CID_EXPANDED').dropna(subset=['CID_EXPANDED'])
df_cid['CID_EXPANDED'] = df_cid['CID_EXPANDED'].str.strip()

cids_ubs_grp = df_cid.groupby(['UBS_FINAL','CID_EXPANDED']).agg(
    total  =('CID_EXPANDED','count'),
    menor5 =('MENOR5','sum'),
).reset_index()

cids_por_ubs = []
for ubs_name, grp in cids_ubs_grp.groupby('UBS_FINAL'):
    grp_sorted = grp.sort_values('total', ascending=False).head(15)
    cids_list = [
        {'cid': str(r.CID_EXPANDED),
         'total': suprimir(int(r.total)),
         'menor5': suprimir(int(r.menor5))}
        for _, r in grp_sorted.iterrows() if int(r.total) >= SUPRESSAO_N
    ]
    if cids_list:
        cids_por_ubs.append({'ubs': str(ubs_name), 'cids': cids_list})

# ─── 17. RECORRENCIA_POR_UBS ──────────────────────────────────────────────────
ubs_pat = df.groupby(['UBS_FINAL','CPF_int'])['N_ATEND'].max().reset_index()

def cat_n(n):
    if n <= 1: return '1_atend'
    if n == 2: return '2_atend'
    return '3_mais'

ubs_pat['cat'] = ubs_pat['N_ATEND'].apply(cat_n)
ubs_rec = ubs_pat.groupby(['UBS_FINAL','cat']).size().unstack(fill_value=0).reset_index()
for c in ['1_atend','2_atend','3_mais']:
    if c not in ubs_rec.columns:
        ubs_rec[c] = 0
recorrencia_por_ubs = [
    {'ubs': str(r.UBS_FINAL), '1_atend': int(r['1_atend']),
     '2_atend': int(r['2_atend']), '3_mais': int(r['3_mais'])}
    for _, r in ubs_rec.iterrows()
]

# ─── 18. POR_BAIRRO ───────────────────────────────────────────────────────────
bgrp = df.groupby('BAIRRO_FINAL').agg(
    casos_total =('CPF_int','count'),
    casos_menor5=('MENOR5','sum'),
    repetidos   =('IS_REPETIDO','sum'),
    complexo    =('IS_COMPLEXO','sum'),
).reset_index()
por_bairro_existing = {x['bairro']: x for x in base.get('por_bairro', [])}
por_bairro = []
for _, r in bgrp.iterrows():
    bairro_name = str(r.BAIRRO_FINAL)
    if bairro_name in ('nan', 'None', '') or int(r.casos_total) < SUPRESSAO_N:
        continue
    ex = por_bairro_existing.get(bairro_name.upper(), {})
    pop_total  = int(ex.get('pop_total',  0) or 0)
    pop_menor5 = int(ex.get('pop_menor5', 0) or 0)
    casos  = int(r.casos_total)
    menor5 = int(r.casos_menor5)
    por_bairro.append({
        'bairro': bairro_name,
        'pop_total':    pop_total,
        'pop_menor5':   pop_menor5,
        'casos_total':  casos,
        'casos_menor5': menor5,
        'repetidos':    int(r.repetidos),
        'complexo':     int(r.complexo),
        'taxa_geral':   round(casos/pop_total*1000,   1) if pop_total  > 0 else 0,
        'taxa_menor5':  round(menor5/pop_menor5*1000, 1) if pop_menor5 > 0 else 0,
    })
por_bairro.sort(key=lambda x: x['taxa_geral'], reverse=True)

# ─── 19. POR_EQUIPE ───────────────────────────────────────────────────────────
por_equipe_existing = {x['equipe']: x for x in base.get('por_equipe', [])}
eqgrp = df.groupby('EQ_FINAL').agg(
    ubs          =('UBS_FINAL', 'first'),
    casos_total  =('CPF_int','count'),
    casos_menor5 =('MENOR5','sum'),
    repetidos    =('IS_REPETIDO','sum'),
    complexo     =('IS_COMPLEXO','sum'),
).reset_index()

por_equipe = []
for _, r in eqgrp.iterrows():
    eq_name = str(r.EQ_FINAL)
    if eq_name in ('nan', 'None', '') or int(r.casos_total) < SUPRESSAO_N:
        continue
    ex = por_equipe_existing.get(eq_name, {})
    pop_total  = int(ex.get('pop_total',  0) or 0)
    pop_menor5 = int(ex.get('pop_menor5', 0) or 0)
    casos  = int(r.casos_total)
    menor5 = int(r.casos_menor5)
    por_equipe.append({
        'equipe':       eq_name,
        'ubs':          str(r.ubs),
        'pop_total':    pop_total,
        'pop_menor5':   pop_menor5,
        'casos_total':  casos,
        'casos_menor5': menor5,
        'repetidos':    int(r.repetidos),
        'complexo':     int(r.complexo),
        'taxa_geral':   round(casos/pop_total*1000,   1) if pop_total  > 0 else 0,
        'taxa_menor5':  round(menor5/pop_menor5*1000, 1) if pop_menor5 > 0 else 0,
    })
por_equipe.sort(key=lambda x: x['casos_total'], reverse=True)

# ─── 20. POR_FAIXA_ETARIA ─────────────────────────────────────────────────────
faixa_grp = df.groupby('FAIXA').agg(
    total    =('CPF_int','count'),
    complexo =('IS_COMPLEXO','sum'),
    repetidos=('IS_REPETIDO','sum'),
).reset_index()
sexo_faixa = df.groupby(['FAIXA','SEXO_N']).size().unstack(fill_value=0).reset_index()
for col in ['M','F','I']:
    if col not in sexo_faixa.columns:
        sexo_faixa[col] = 0
faixa_grp = faixa_grp.merge(sexo_faixa[['FAIXA','M','F','I']], on='FAIXA', how='left').fillna(0)
por_faixa_etaria = [
    {'faixa':    str(r.FAIXA),
     'total':    int(r.total),
     'masculino':int(r.get('M', 0)),
     'feminino': int(r.get('F', 0)),
     'complexo': int(r.complexo),
     'repetidos':int(r.repetidos)}
    for _, r in faixa_grp.iterrows()
]

# ─── 21. POR_SEXO ─────────────────────────────────────────────────────────────
sexo_total = df.groupby('SEXO_N').size()
sexo_m5    = df[df.MENOR5].groupby('SEXO_N').size()
por_sexo = {
    'masculino':        int(sexo_total.get('M', 0)),
    'feminino':         int(sexo_total.get('F', 0)),
    'nao_informado':    int(sexo_total.get('I', 0)),
    'masculino_menor5': int(sexo_m5.get('M', 0)),
    'feminino_menor5':  int(sexo_m5.get('F', 0)),
}

# ─── 22. CIDS_COMBINADOS ──────────────────────────────────────────────────────
df_cid_all = df[['CID_STR','MENOR5']].copy()
df_cid_all['CID_EXPANDED'] = df_cid_all['CID_STR'].str.findall(r'A\d{2}(?:\.\d+)?')
df_cid_all = df_cid_all.explode('CID_EXPANDED').dropna(subset=['CID_EXPANDED'])
df_cid_all['CID_EXPANDED'] = df_cid_all['CID_EXPANDED'].str.strip()
cid_all_grp = df_cid_all.groupby('CID_EXPANDED').agg(
    total  =('CID_EXPANDED','count'),
    menor5 =('MENOR5','sum'),
).reset_index().sort_values('total', ascending=False).head(30)
cids_combinados = [
    {'cid': str(r.CID_EXPANDED), 'total': int(r.total), 'menor5': int(r.menor5)}
    for _, r in cid_all_grp.iterrows() if int(r.total) >= SUPRESSAO_N
]

# ─── 23. RECORRÊNCIA ──────────────────────────────────────────────────────────
cpf_n = df.groupby('CPF_int').size()
recorrencia_geral = {
    '1_atend': int((cpf_n == 1).sum()),
    '2_atend': int((cpf_n == 2).sum()),
    '3_mais':  int((cpf_n >= 3).sum()),
}
cpf_m5 = df[df.MENOR5].groupby('CPF_int').size()
recorrencia_menor5 = {
    '1_atend': int((cpf_m5 == 1).sum()),
    '2_atend': int((cpf_m5 == 2).sum()),
    '3_mais':  int((cpf_m5 >= 3).sum()),
}
recorrencia = {'geral': recorrencia_geral, 'menor5': recorrencia_menor5}

# ─── 24. COMPLEXO ─────────────────────────────────────────────────────────────
cx_total = int(df.IS_COMPLEXO.sum())
cx_vinculo = df[df.IS_COMPLEXO & df['UBS_FINAL'].notna()]
cx_ubs = cx_vinculo.groupby('UBS_FINAL').size().sort_values(ascending=False).head(20)
complexo_ubs_origem = [
    {'ubs': str(ubs), 'casos': int(cnt),
     'pct': round(cnt/cx_total*100, 1) if cx_total > 0 else 0}
    for ubs, cnt in cx_ubs.items()
]
complexo = {
    'total_atendimentos': cx_total,
    'com_vinculo': len(cx_vinculo),
    'sem_vinculo': cx_total - len(cx_vinculo),
    'ubs_origem': complexo_ubs_origem,
}

# ─── 25. SEM_VÍNCULO ──────────────────────────────────────────────────────────
sem_vinc = df[df['UBS_FINAL'].isna()]
unid_cnts = sem_vinc.groupby('UNIDADE SAUDE').size().sort_values(ascending=False).head(10)
sem_vinculo = {
    'total': len(sem_vinc),
    'unidades_atendimento': [
        {'unidade': str(u), 'casos': int(c)} for u, c in unid_cnts.items()
    ],
}

# ─── 26. UBS_BAIRROS_MAP ──────────────────────────────────────────────────────
ubs_bairros_map = {}
for ubs_name, grp in df.groupby('UBS_FINAL'):
    bcts = grp['BAIRRO_FINAL'].value_counts().head(5)
    total_ubs = len(grp)
    lst = [
        f"{b} ({round(c/total_ubs*100, 1)}%)"
        for b, c in bcts.items()
        if str(b) not in ('nan', 'None', '') and c >= SUPRESSAO_N
    ]
    if lst:
        ubs_bairros_map[str(ubs_name)] = lst

# ─── 27. MICROAREAS_CRITICAS ──────────────────────────────────────────────────
mc_grp = df[df.MENOR5 & df['MICRO_FINAL'].notna()].groupby(['UBS_FINAL','MICRO_FINAL']).agg(
    casos_menor5=('CPF_int','count'),
).reset_index()
mc_total = df.groupby(['UBS_FINAL','MICRO_FINAL']).size().reset_index(name='casos_total')
mc = mc_grp.merge(mc_total, on=['UBS_FINAL','MICRO_FINAL'], how='left').fillna(0)
microareas_criticas = [
    {'ubs': str(r.UBS_FINAL), 'microarea': str(r.MICRO_FINAL),
     'casos_menor5': int(r.casos_menor5), 'casos_total': int(r.casos_total)}
    for _, r in mc.iterrows() if int(r.casos_menor5) >= 3
]

# ─── 28. EVASAO_COMPLEXO ──────────────────────────────────────────────────────
evasao_complexo = []
for _, r in ubs_grp.iterrows():
    total = int(r.casos_total)
    cx    = int(r.casos_complexo)
    no_cx = total - cx
    evasao_complexo.append({
        'ubs': str(r.UBS_FINAL),
        'casos_total':       total,
        'casos_complexo':    cx,
        'casos_no_complexo': no_cx,
        'taxa_evasao': round(no_cx/total*100, 1) if total > 0 else 0,
    })
evasao_complexo.sort(key=lambda x: x['taxa_evasao'], reverse=True)

# ─── 29. ESCREVER JSON ────────────────────────────────────────────────────────
print("\nGravando JSON...")
output = {
    'metadata':              metadata,
    'serie_temporal':        serie_temporal,
    'serie_temporal_faixa':  serie_temporal_faixa,
    'serie_temporal_ubs':    serie_temporal_ubs,
    'serie_temporal_bairro': serie_temporal_bairro,
    'serie_temporal_sexo':   serie_temporal_sexo,
    'por_ubs':               por_ubs,
    'por_bairro':            por_bairro,
    'por_equipe':            por_equipe,
    'por_faixa_etaria':      por_faixa_etaria,
    'por_sexo':              por_sexo,
    'por_ubs_sexo':          por_ubs_sexo,
    'por_ubs_faixa':         por_ubs_faixa,
    'cids_combinados':       cids_combinados,
    'cids_por_ubs':          cids_por_ubs,
    'recorrencia':           recorrencia,
    'recorrencia_por_ubs':   recorrencia_por_ubs,
    'complexo':              complexo,
    'sem_vinculo':           sem_vinculo,
    'microareas_criticas':   microareas_criticas,
    'evasao_complexo':       evasao_complexo,
    'ubs_bairros_map':       ubs_bairros_map,
}

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✓ JSON gravado em: {OUT_JSON}")
print(f"  Total atendimentos: {total_atend}")
print(f"  Total pacientes:    {total_pacientes}")
print(f"  Chaves do JSON:     {list(output.keys())}")
print("\nPipeline concluído.")

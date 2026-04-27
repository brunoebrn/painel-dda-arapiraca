"""
build_data_v3.py
Generates dashboard_data_v3.json from merged_slim.csv + dashboard_data_current.json
Adds: month-granular aggregates, per-UBS recorrencia, repetido/complexo fields everywhere
"""
import json
import pandas as pd
import numpy as np

print("Loading data...")
with open('/sessions/peaceful-nice-brown/dashboard_data_current.json') as f:
    base = json.load(f)

df = pd.read_csv('/sessions/peaceful-nice-brown/merged_slim.csv')

# Normalise sexo values
df['SEXO_N'] = df['SEXO_N'].fillna('I').str.upper().str.strip()
# Map: M=Masculino, F=Feminino, else=I (Indeterminado/Não Informado)
df['SEXO_N'] = df['SEXO_N'].map(lambda x: x if x in ('M','F') else 'I')

print(f"Records: {len(df)}, IS_COMPLEXO: {df.IS_COMPLEXO.sum()}, IS_REPETIDO: {df.IS_REPETIDO.sum()}")
print(f"Sexo: {df.SEXO_N.value_counts().to_dict()}")

MES_NOMES = ['','Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

# ─── METADATA ────────────────────────────────────────────────────────────────
total_atend       = int(len(df))
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
    'total_atendimentos': total_atend,
    'total_pacientes':    total_pacientes,
    'total_menor5':       total_menor5,
    'pacientes_menor5':   pac_menor5,
    'total_repetidos':    total_repetidos,
    'pacientes_repetidos': pac_repetidos,
    'total_complexo':     total_complexo,
    'pacientes_complexo': pac_complexo,
    'menor5_repetidos':   menor5_repetidos,
    'menor5_complexo':    menor5_complexo,
    'pac5_repetidos':     pac5_repetidos,
    'pac5_complexo':      pac5_complexo,
}

# ─── SERIE_TEMPORAL ───────────────────────────────────────────────────────────
grp = df.groupby('MES')
st_df = grp.agg(
    total      = ('CPF_int', 'count'),
    menor5     = ('MENOR5', 'sum'),
    pacientes  = ('CPF_int', 'nunique'),
    repetidos  = ('IS_REPETIDO', 'sum'),
    complexo   = ('IS_COMPLEXO', 'sum'),
).reset_index()

# pacientes_menor5 per month
pm5 = df[df.MENOR5].groupby('MES').CPF_int.nunique().reset_index()
pm5.columns = ['MES','pacientes_menor5']
st_df = st_df.merge(pm5, on='MES', how='left').fillna(0)

# Add menor5_repetidos and menor5_complexo per month
m5rep = df[df.MENOR5 & df.IS_REPETIDO].groupby('MES').size().reset_index(name='menor5_repetidos')
m5cx  = df[df.MENOR5 & df.IS_COMPLEXO].groupby('MES').size().reset_index(name='menor5_complexo')
st_df = st_df.merge(m5rep, on='MES', how='left').fillna(0)
st_df = st_df.merge(m5cx,  on='MES', how='left').fillna(0)

serie_temporal = []
for _, r in st_df.iterrows():
    serie_temporal.append({
        'mes': int(r.MES),
        'nome': MES_NOMES[int(r.MES)],
        'total': int(r.total),
        'menor5': int(r.menor5),
        'pacientes': int(r.pacientes),
        'pacientes_menor5': int(r.pacientes_menor5),
        'repetidos': int(r.repetidos),
        'complexo': int(r.complexo),
        'menor5_repetidos': int(r.menor5_repetidos),
        'menor5_complexo':  int(r.menor5_complexo),
    })
serie_temporal.sort(key=lambda x: x['mes'])

# ─── SERIE_TEMPORAL_FAIXA ─────────────────────────────────────────────────────
stf = df.groupby(['MES','FAIXA']).agg(
    casos=('CPF_int','count'),
    complexo=('IS_COMPLEXO','sum'),
    repetidos=('IS_REPETIDO','sum'),
).reset_index()

serie_temporal_faixa = []
for _, r in stf.iterrows():
    serie_temporal_faixa.append({
        'mes': int(r.MES), 'faixa': str(r.FAIXA),
        'casos': int(r.casos), 'complexo': int(r.complexo), 'repetidos': int(r.repetidos),
    })

# ─── SERIE_TEMPORAL_UBS ───────────────────────────────────────────────────────
stubs = df.groupby(['MES','UBS_FINAL']).agg(
    casos    = ('CPF_int','count'),
    menor5   = ('MENOR5','sum'),
    repetidos= ('IS_REPETIDO','sum'),
    complexo = ('IS_COMPLEXO','sum'),
).reset_index()

serie_temporal_ubs = []
for _, r in stubs.iterrows():
    serie_temporal_ubs.append({
        'ubs': str(r.UBS_FINAL), 'mes': int(r.MES),
        'casos': int(r.casos), 'menor5': int(r.menor5),
        'repetidos': int(r.repetidos), 'complexo': int(r.complexo),
    })

# ─── SERIE_TEMPORAL_BAIRRO ────────────────────────────────────────────────────
stbairro = df.groupby(['MES','BAIRRO_FINAL']).agg(
    casos    = ('CPF_int','count'),
    menor5   = ('MENOR5','sum'),
    repetidos= ('IS_REPETIDO','sum'),
    complexo = ('IS_COMPLEXO','sum'),
).reset_index()

serie_temporal_bairro = []
for _, r in stbairro.iterrows():
    serie_temporal_bairro.append({
        'bairro': str(r.BAIRRO_FINAL), 'mes': int(r.MES),
        'casos': int(r.casos), 'menor5': int(r.menor5),
        'repetidos': int(r.repetidos), 'complexo': int(r.complexo),
    })

# ─── POR_UBS ──────────────────────────────────────────────────────────────────
ubs_grp = df.groupby('UBS_FINAL').agg(
    casos_total      = ('CPF_int','count'),
    casos_menor5     = ('MENOR5','sum'),
    pacientes_total  = ('CPF_int','nunique'),
    casos_repetidos  = ('IS_REPETIDO','sum'),
    casos_complexo   = ('IS_COMPLEXO','sum'),
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
    taxa_geral  = round(casos  / pop_total  * 1000, 1) if pop_total  > 0 else 0
    taxa_menor5 = round(menor5 / pop_menor5 * 1000, 1) if pop_menor5 > 0 else 0
    pct_complexo = round(int(r.casos_complexo) / casos * 100, 1) if casos > 0 else 0
    por_ubs.append({
        'ubs': ubs_name,
        'zona': ex.get('zona',''),
        'pop_total': pop_total,
        'pop_menor5': pop_menor5,
        'casos_total': casos,
        'casos_menor5': menor5,
        'pacientes_total': int(r.pacientes_total),
        'pacientes_menor5': int(r.pacientes_menor5),
        'casos_repetidos': int(r.casos_repetidos),
        'casos_complexo': int(r.casos_complexo),
        'pct_complexo': pct_complexo,
        'taxa_geral': taxa_geral,
        'taxa_menor5': taxa_menor5,
        'bairros': ex.get('bairros', []),
    })
por_ubs.sort(key=lambda x: x['casos_total'], reverse=True)

# ─── RECORRENCIA_POR_UBS ──────────────────────────────────────────────────────
ubs_pat = df.groupby(['UBS_FINAL','CPF_int'])['N_ATEND'].max().reset_index()
def cat_n(n):
    if n <= 1: return '1_atend'
    if n == 2: return '2_atend'
    return '3_mais'
ubs_pat['cat'] = ubs_pat['N_ATEND'].apply(cat_n)
ubs_rec = ubs_pat.groupby(['UBS_FINAL','cat']).size().unstack(fill_value=0).reset_index()
# ensure all columns exist
for c in ['1_atend','2_atend','3_mais']:
    if c not in ubs_rec.columns:
        ubs_rec[c] = 0

recorrencia_por_ubs = []
for _, r in ubs_rec.iterrows():
    recorrencia_por_ubs.append({
        'ubs': str(r.UBS_FINAL),
        '1_atend': int(r['1_atend']),
        '2_atend': int(r['2_atend']),
        '3_mais': int(r['3_mais']),
    })

# ─── POR_BAIRRO ───────────────────────────────────────────────────────────────
bgrp = df.groupby('BAIRRO_FINAL').agg(
    casos_total  = ('CPF_int','count'),
    casos_menor5 = ('MENOR5','sum'),
    repetidos    = ('IS_REPETIDO','sum'),
    complexo     = ('IS_COMPLEXO','sum'),
).reset_index()

por_bairro_existing = {x['bairro']: x for x in base.get('por_bairro', [])}

por_bairro = []
for _, r in bgrp.iterrows():
    b = str(r.BAIRRO_FINAL)
    ex = por_bairro_existing.get(b, {})
    pop_total  = int(ex.get('pop_total',  0) or 0)
    pop_menor5 = int(ex.get('pop_menor5', 0) or 0)
    casos  = int(r.casos_total)
    menor5 = int(r.casos_menor5)
    taxa  = round(casos  / pop_total  * 1000, 1) if pop_total  > 0 else 0
    taxa5 = round(menor5 / pop_menor5 * 1000, 1) if pop_menor5 > 0 else 0
    por_bairro.append({
        'bairro': b,
        'pop_total': pop_total,
        'pop_menor5': pop_menor5,
        'casos_total': casos,
        'casos_menor5': menor5,
        'repetidos': int(r.repetidos),
        'complexo': int(r.complexo),
        'taxa_geral': taxa,
        'taxa_menor5': taxa5,
    })
por_bairro.sort(key=lambda x: x['casos_total'], reverse=True)

# ─── POR_EQUIPE ───────────────────────────────────────────────────────────────
eq_grp = df.groupby(['EQ_FINAL','UBS_FINAL']).agg(
    casos_total  = ('CPF_int','count'),
    casos_menor5 = ('MENOR5','sum'),
    repetidos    = ('IS_REPETIDO','sum'),
    complexo     = ('IS_COMPLEXO','sum'),
).reset_index()

por_equipe_existing = {x.get('equipe',''): x for x in base.get('por_equipe', [])}

por_equipe = []
for _, r in eq_grp.iterrows():
    eq = str(r.EQ_FINAL)
    ex = por_equipe_existing.get(eq, {})
    pop_total  = int(ex.get('pop_total',  0) or 0)
    pop_menor5 = int(ex.get('pop_menor5', 0) or 0)
    casos  = int(r.casos_total)
    menor5 = int(r.casos_menor5)
    taxa  = round(casos  / pop_total  * 1000, 1) if pop_total  > 0 else 0
    taxa5 = round(menor5 / pop_menor5 * 1000, 1) if pop_menor5 > 0 else 0
    por_equipe.append({
        'equipe': eq,
        'ubs': str(r.UBS_FINAL),
        'pop_total': pop_total,
        'pop_menor5': pop_menor5,
        'casos_total': casos,
        'casos_menor5': menor5,
        'repetidos': int(r.repetidos),
        'complexo': int(r.complexo),
        'taxa_geral': taxa,
        'taxa_menor5': taxa5,
    })
por_equipe.sort(key=lambda x: x['casos_total'], reverse=True)

# ─── POR_FAIXA_ETARIA ─────────────────────────────────────────────────────────
FAIXA_ORDER = ['<1a','1a','2-4a','5-9a','10-17a','18-29a','30-44a','45-59a','60+']
fgrp = df.groupby('FAIXA').agg(
    casos    = ('CPF_int','count'),
    complexo = ('IS_COMPLEXO','sum'),
    repetidos= ('IS_REPETIDO','sum'),
).reset_index()

por_faixa_etaria = []
for f in FAIXA_ORDER:
    row = fgrp[fgrp.FAIXA == f]
    if len(row) > 0:
        r = row.iloc[0]
        por_faixa_etaria.append({
            'faixa': f, 'casos': int(r.casos),
            'complexo': int(r.complexo), 'repetidos': int(r.repetidos),
        })

# ─── POR_SEXO ────────────────────────────────────────────────────────────────
sexo_c = df.SEXO_N.value_counts()
sexo_m5 = df[df.MENOR5].SEXO_N.value_counts()
por_sexo = {
    'masculino': int(sexo_c.get('M', 0)),
    'feminino':  int(sexo_c.get('F', 0)),
    'nao_informado': int(sexo_c.get('I', 0)),
    'masculino_menor5': int(sexo_m5.get('M', 0)),
    'feminino_menor5':  int(sexo_m5.get('F', 0)),
}
print(f"Sexo counts: {por_sexo}")

# ─── RECORRENCIA ─────────────────────────────────────────────────────────────
def recorrencia_stats(sub_df):
    pat = sub_df.groupby('CPF_int')['N_ATEND'].max()
    return {
        '1_atend': int((pat == 1).sum()),
        '2_atend': int((pat == 2).sum()),
        '3_mais':  int((pat >= 3).sum()),
    }

recorrencia = {
    'geral':  recorrencia_stats(df),
    'menor5': recorrencia_stats(df[df.MENOR5]),
}

# ─── MICROAREAS_CRITICAS ─────────────────────────────────────────────────────
micro_grp = df.groupby(['UBS_FINAL','MICRO_FINAL']).agg(
    casos       = ('CPF_int','count'),
    casos_menor5= ('MENOR5','sum'),
).reset_index()

microareas_criticas = []
for _, r in micro_grp.iterrows():
    microareas_criticas.append({
        'ubs': str(r.UBS_FINAL), 'microarea': str(r.MICRO_FINAL),
        'casos_menor5': int(r.casos_menor5), 'total': int(r.casos),
    })
# Sort by casos_menor5 desc
microareas_criticas.sort(key=lambda x: x['casos_menor5'], reverse=True)
microareas_criticas = microareas_criticas[:150]  # top 150

# ─── UBS_BAIRROS_MAP ─────────────────────────────────────────────────────────
ubs_bairros_map = {}
for ubs_name, sub in df.groupby('UBS_FINAL'):
    all_b = sub.BAIRRO_FINAL.dropna().unique().tolist()
    ubs_bairros_map[str(ubs_name)] = [str(b) for b in all_b]

# ─── EVASAO_COMPLEXO (from por_ubs) ──────────────────────────────────────────
evasao_complexo = []
for u in por_ubs:
    if u['casos_complexo'] > 0:
        taxa_ev = round(u['casos_complexo'] / u['casos_total'] * 100, 1) if u['casos_total'] > 0 else 0
        evasao_complexo.append({
            'ubs': u['ubs'],
            'total_casos': u['casos_total'],
            'no_complexo': u['casos_complexo'],
            'taxa_evasao': taxa_ev,
        })
evasao_complexo.sort(key=lambda x: x['taxa_evasao'], reverse=True)

# ─── COMPLEXO SUMMARY ────────────────────────────────────────────────────────
# Use existing complexo structure, update totals
cx_base = base.get('complexo', {})
complexo = {
    **cx_base,
    'total_atendimentos': total_complexo,
    'com_vinculo': cx_base.get('com_vinculo', 0),
    'sem_vinculo': cx_base.get('sem_vinculo', 0),
    # UBS origin sorted by casos
    'ubs_origem': sorted(
        [{'ubs': u['ubs'], 'casos': u['casos_complexo'],
          'pct': round(u['casos_complexo']/total_complexo*100,1) if total_complexo > 0 else 0}
         for u in por_ubs if u['casos_complexo'] > 0],
        key=lambda x: x['casos'], reverse=True
    )[:20],
}

# ─── ASSEMBLE ────────────────────────────────────────────────────────────────
data_v3 = {
    'metadata':              metadata,
    'serie_temporal':        serie_temporal,
    'serie_temporal_faixa':  serie_temporal_faixa,
    'serie_temporal_ubs':    serie_temporal_ubs,
    'serie_temporal_bairro': serie_temporal_bairro,
    'por_ubs':               por_ubs,
    'por_bairro':            por_bairro,
    'por_equipe':            por_equipe,
    'por_faixa_etaria':      por_faixa_etaria,
    'por_sexo':              por_sexo,
    'cids_combinados':       base.get('cids_combinados', []),
    'recorrencia':           recorrencia,
    'recorrencia_por_ubs':   recorrencia_por_ubs,
    'complexo':              complexo,
    'sem_vinculo':           base.get('sem_vinculo', {}),
    'microareas_criticas':   microareas_criticas,
    'evasao_complexo':       evasao_complexo,
    'ubs_bairros_map':       ubs_bairros_map,
}

out_path = '/sessions/peaceful-nice-brown/dashboard_data_v3.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(data_v3, f, ensure_ascii=False)

size_kb = len(json.dumps(data_v3, ensure_ascii=False)) / 1024
print(f"\nSaved to {out_path} ({size_kb:.0f} KB)")
print(f"Metadata: {metadata}")
print(f"por_ubs: {len(por_ubs)}, por_bairro: {len(por_bairro)}, por_equipe: {len(por_equipe)}")
print(f"serie_temporal: {len(serie_temporal)} months")
print(f"serie_temporal_ubs: {len(serie_temporal_ubs)} records")
print(f"serie_temporal_bairro: {len(serie_temporal_bairro)} records")
print(f"recorrencia_por_ubs: {len(recorrencia_por_ubs)} UBS")
print(f"por_faixa_etaria: {por_faixa_etaria}")
print(f"por_sexo: {por_sexo}")
print(f"recorrencia: {recorrencia}")

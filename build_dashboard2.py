"""
build_dashboard2.py  — Painel DDA Arapiraca 2025
Gera index.html como arquivo único e autocontido (GitHub Pages).

Uso:
    python build_dashboard2.py

Pré-requisitos:
    dashboard_data_v3.json  (gerado por build_data_v3.py)
    arapiraca_bairros.json
"""
import json, os
from pathlib import Path

BASE      = Path(__file__).parent
DATA_FILE = BASE / 'dashboard_data_v3.json'
GEO_FILE  = BASE / 'arapiraca_bairros.json'
OUT_HTML  = BASE / 'index.html'

with open(DATA_FILE, encoding='utf-8') as f:
    data = json.load(f)
with open(GEO_FILE, encoding='utf-8') as f:
    geojson = json.load(f)

json_str    = json.dumps(data,    ensure_ascii=False, separators=(',',':'))
geojson_str = json.dumps(geojson, ensure_ascii=False, separators=(',',':'))

# ─── CSS tooltip style ────────────────────────────────────────────────────────
TOOLTIP_CSS = """
.minfo{display:inline-flex;align-items:center;justify-content:center;
  width:14px;height:14px;border-radius:50%;background:#B2BABB;color:#fff;
  font-size:9px;font-weight:700;cursor:help;margin-left:4px;
  vertical-align:middle;line-height:1;flex-shrink:0;user-select:none}
.minfo:hover{background:#2E86C1}
"""

html_head = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Painel DDA — SMS Arapiraca 2025</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --ink-primary:#1C2B3A;--ink-secondary:#5D6D7E;--ink-muted:#95A5A6;
  --surface-base:#FAFBFC;--surface-card:#FFFFFF;--surface-hover:#F0F3F5;
  --border-subtle:rgba(0,0,0,0.06);--border-std:rgba(0,0,0,0.10);
  --brand:#1B4F72;--brand-l:#2E86C1;--brand-acc:#D4A017;
  --danger:#C0392B;--warn:#D4770B;--ok:#1E8449
}
body{font-family:'Inter',sans-serif;background:var(--surface-base);color:var(--ink-primary);line-height:1.5}
.hdr{position:fixed;top:0;left:0;right:0;height:68px;background:#fff;border-bottom:1px solid var(--border-subtle);
  display:flex;align-items:center;justify-content:space-between;padding:0 28px;z-index:200;
  box-shadow:0 1px 4px rgba(0,0,0,0.06)}
.hdr-left{flex:1}
.hdr-title{font-size:14px;font-weight:700;color:var(--brand);letter-spacing:.3px}
.hdr-sub{font-size:11px;color:var(--ink-muted);margin-top:1px}
.hdr-accent{height:3px;width:52px;background:var(--brand-acc);margin-top:3px;border-radius:2px}
.hdr-btns{display:flex;gap:8px;align-items:center}
.tbtn{padding:7px 13px;border:none;border-radius:4px;font-size:12px;font-weight:600;cursor:pointer;
  font-family:'Inter',sans-serif;transition:all .15s}
.tbtn-u5{background:#2E86C1;color:#fff}
.tbtn-u5:hover{background:#1B4F72}
.tbtn-u5.active{background:#D4A017;color:#1C2B3A}
.tbtn-rep{background:#E8F4FD;color:#2E86C1;border:1px solid #AED6F1}
.tbtn-rep:hover{background:#AED6F1}
.tbtn-rep.active{background:#D4A017;color:#1C2B3A;border-color:#B7950B}
.tbtn-cx{background:#FDEDEC;color:#C0392B;border:1px solid #F5B7B1}
.tbtn-cx:hover{background:#F5B7B1}
.tbtn-cx.active{background:#C0392B;color:#fff;border-color:#922B21}
.main{display:flex;margin-top:68px;min-height:calc(100vh - 68px)}
.sidebar{width:200px;background:#fff;border-right:1px solid var(--border-subtle);
  padding:16px 0;position:fixed;left:0;top:68px;height:calc(100vh - 68px);z-index:100;overflow-y:auto}
.nav-item{padding:10px 16px;cursor:pointer;font-size:13px;color:var(--ink-secondary);
  border-left:3px solid transparent;transition:all .15s;user-select:none}
.nav-item:hover{background:var(--surface-hover);color:var(--ink-primary)}
.nav-item.active{border-left-color:#2E86C1;background:rgba(46,134,193,.05);
  color:var(--brand);font-weight:600}
.content{margin-left:200px;flex:1;padding:24px 28px;max-width:1440px}
.page{display:none}
.page.active{display:block}
.fbr-toggle{padding:7px 14px;background:var(--surface-hover);border:1px solid var(--border-std);
  border-radius:4px;font-size:12px;font-weight:600;cursor:pointer;margin-bottom:16px;
  color:var(--ink-primary);font-family:'Inter',sans-serif}
.fbr{background:#fff;border:1px solid var(--border-subtle);border-radius:4px;
  max-height:0;overflow:hidden;transition:max-height .3s,padding .3s;margin-bottom:16px}
.fbr.open{max-height:300px;padding:14px;border-bottom:2px solid var(--brand-acc)}
.fbr-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:12px}
.fg{display:flex;flex-direction:column}
.fg label{font-size:10px;font-weight:700;color:var(--ink-muted);margin-bottom:3px;
  text-transform:uppercase;letter-spacing:.5px}
.fg select,.fg input{padding:6px 9px;border:1px solid var(--border-std);border-radius:4px;
  font-size:12px;font-family:'Inter',sans-serif;background:var(--surface-base);color:var(--ink-primary)}
.fbr-btns{display:flex;gap:8px;justify-content:flex-end}
.fbtn{padding:6px 13px;background:#2E86C1;color:#fff;border:none;border-radius:4px;
  font-size:12px;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif}
.fbtn:hover{background:#1B4F72}
.fbtn.reset{background:var(--surface-hover);color:var(--ink-primary);border:1px solid var(--border-std)}
.fbtn.export{background:#1E8449;color:#fff}
.fbtn.export:hover{background:#145A32}
#filterStatus{font-size:11px;color:var(--brand);background:rgba(46,134,193,.07);
  padding:6px 10px;border-radius:3px;margin-top:8px;display:none}
.sec-title{font-size:16px;font-weight:700;color:var(--ink-primary);
  margin-bottom:18px;border-bottom:2px solid var(--brand-acc);padding-bottom:8px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:12px;margin-bottom:22px}
.card{background:#fff;border:1px solid var(--border-subtle);border-radius:4px;padding:14px 16px;
  transition:all .15s;border-left:3px solid transparent}
.card:hover{box-shadow:0 2px 8px rgba(0,0,0,.05);border-color:var(--border-std)}
.card.cu5{border-left-color:#D4A017}
.card.ctog{border-left-color:#C0392B}
.card-lbl{font-size:10px;color:var(--ink-muted);text-transform:uppercase;font-weight:700;
  letter-spacing:.5px;margin-bottom:5px;display:flex;align-items:center;gap:2px}
.card-val{font-size:26px;font-weight:700;color:var(--brand);margin-bottom:3px;line-height:1.1}
.card-meta{font-size:11px;color:var(--ink-secondary)}
.chart-wrap{background:#fff;border:1px solid var(--border-subtle);border-radius:4px;
  padding:18px 18px 14px;margin-bottom:18px;position:relative}
.chart-wrap.h380{height:380px}
.chart-wrap.h460{height:460px}
.chart-wrap.h520{height:520px}
.chart-title{font-size:13px;font-weight:600;color:var(--ink-primary);margin-bottom:12px;
  display:flex;align-items:center;gap:4px}
canvas{max-width:100%;max-height:100%}
.filter-note{font-size:11px;color:var(--ink-muted);background:rgba(0,0,0,0.03);
  padding:5px 10px;border-radius:3px;margin-top:-10px;margin-bottom:14px;
  border-left:2px solid var(--brand-acc);display:none}
.filter-note.visible{display:block}
.tabs{display:flex;border-bottom:1px solid var(--border-subtle);margin-bottom:18px;gap:0}
.tab{padding:9px 16px;cursor:pointer;border:none;background:none;
  font-size:12px;font-weight:600;color:var(--ink-secondary);
  border-bottom:2px solid transparent;font-family:'Inter',sans-serif}
.tab:hover{color:var(--ink-primary)}
.tab.active{color:#2E86C1;border-bottom-color:#2E86C1}
.tab-pane{display:none}
.tab-pane.active{display:block}
.tbl-wrap{background:#fff;border:1px solid var(--border-subtle);border-radius:4px;
  overflow-x:auto;margin-bottom:18px}
table{width:100%;border-collapse:collapse;font-size:12px}
thead{background:var(--surface-hover)}
th{padding:9px 12px;text-align:left;font-weight:600;color:var(--ink-primary);
  border-bottom:1px solid var(--border-std);cursor:pointer;user-select:none;white-space:nowrap}
th:hover{background:rgba(46,134,193,.06)}
th.sort-asc::after{content:'';display:inline-block;margin-left:4px;width:0;height:0;
  border-left:4px solid transparent;border-right:4px solid transparent;border-bottom:5px solid #2E86C1;vertical-align:-1px}
th.sort-desc::after{content:'';display:inline-block;margin-left:4px;width:0;height:0;
  border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid #2E86C1;vertical-align:-1px}
td{padding:9px 12px;border-bottom:1px solid var(--border-subtle)}
tbody tr:hover{background:var(--surface-hover)}
tbody tr:last-child td{border-bottom:none}
.tn{text-align:right;font-variant-numeric:tabular-nums;color:var(--ink-secondary)}
.adanger{font-weight:700;color:var(--danger)}
.awarn{font-weight:700;color:var(--warn)}
.aok{font-weight:700;color:var(--ok)}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px}
#leafletMap{height:580px;border-radius:4px;border:1px solid var(--border-subtle)}
.footer{background:var(--surface-hover);border-top:1px solid var(--border-subtle);
  padding:18px 28px;margin-top:36px;font-size:10px;color:var(--ink-muted);text-align:center;line-height:1.7}
.minfo{display:inline-flex;align-items:center;justify-content:center;
  width:14px;height:14px;border-radius:50%;background:#B2BABB;color:#fff;
  font-size:9px;font-weight:700;cursor:help;margin-left:3px;
  vertical-align:middle;line-height:1;flex-shrink:0;user-select:none}
.minfo:hover{background:#2E86C1}
@media(max-width:768px){
  .sidebar{width:100%;height:auto;position:relative;top:0;border-right:none;
    border-bottom:1px solid var(--border-subtle);display:flex;overflow-x:auto;padding:0}
  .nav-item{flex-shrink:0;border-left:none;border-bottom:3px solid transparent}
  .nav-item.active{border-left:none;border-bottom-color:#2E86C1}
  .content{margin-left:0;padding:14px}
  .two-col{grid-template-columns:1fr}
  .cards{grid-template-columns:1fr 1fr}
  .hdr-btns{gap:4px}
  .tbtn{font-size:10px;padding:5px 8px}
}
</style>
</head>
<body>

<header class="hdr">
  <div class="hdr-left">
    <div class="hdr-title">Secretaria Municipal de Saúde de Arapiraca</div>
    <div class="hdr-sub">Painel Epidemiológico — Doença Diarreica Aguda (CID A09) — Arapiraca/AL — 2025</div>
    <div class="hdr-accent"></div>
  </div>
  <div class="hdr-btns">
    <button class="tbtn tbtn-u5" id="btnU5">&lt; 5 anos</button>
    <button class="tbtn tbtn-rep" id="btnRepetido">↺ Casos Repetidos</button>
    <button class="tbtn tbtn-cx" id="btnComplexo">🏥 Demanda Espon.</button>
  </div>
</header>

<div class="main">
  <aside class="sidebar">
    <div class="nav-item active" data-page="visao-geral">Visão Geral</div>
    <div class="nav-item" data-page="territorial">Análise Territorial</div>
    <div class="nav-item" data-page="epidemiologico">Perfil Epidemiológico</div>
    <div class="nav-item" data-page="mapa">Mapa Territorial</div>
  </aside>

  <main class="content">
    <button class="fbr-toggle" id="fbrToggle">⚙️ Filtros Avançados</button>
    <div class="fbr" id="filterBar">
      <div class="fbr-grid">
        <div class="fg"><label>Zona</label>
          <select id="fZona"><option value="">Todas</option><option value="URBANA">Urbana</option><option value="RURAL">Rural</option></select></div>
        <div class="fg"><label>UBS</label>
          <select id="fUBS"><option value="">Todas as UBS</option></select></div>
        <div class="fg"><label>Bairro</label>
          <select id="fBairro"><option value="">Todos os bairros</option></select></div>
        <div class="fg"><label>Faixa Etária</label>
          <select id="fFaixa"><option value="">Todas</option></select></div>
        <div class="fg"><label>Sexo</label>
          <select id="fSexo"><option value="">Todos</option><option value="M">Masculino</option><option value="F">Feminino</option></select></div>
        <div class="fg"><label>Mês</label>
          <select id="fMes">
            <option value="">Todos</option><option value="1">Janeiro</option><option value="2">Fevereiro</option>
            <option value="3">Março</option><option value="4">Abril</option><option value="5">Maio</option>
            <option value="6">Junho</option><option value="7">Julho</option><option value="8">Agosto</option>
            <option value="9">Setembro</option><option value="10">Outubro</option><option value="11">Novembro</option>
            <option value="12">Dezembro</option>
          </select></div>
      </div>
      <div class="fbr-btns">
        <button class="fbtn export" onclick="exportCSV()">⬇ Exportar CSV</button>
        <button class="fbtn reset" onclick="resetFilters()">Limpar</button>
        <button class="fbtn" onclick="applyFilters()">Aplicar</button>
      </div>
      <div id="filterStatus"></div>
    </div>

    <!-- PAGE: Visão Geral -->
    <div class="page active" id="page-visao-geral">
      <h2 class="sec-title">Visão Geral — Doença Diarreica Aguda</h2>
      <div class="cards" id="mainCards"></div>
      <div class="two-col">
        <div class="chart-wrap h380">
          <div class="chart-title">Série Temporal — Atendimentos Mensais<span class="minfo" data-tip="Contagem de registros A09 por mês da consulta (campo DATA DA CONSULTA da FAI). Ao aplicar filtros, recalculado a partir de serie_temporal_ubs (zona/UBS), serie_temporal_bairro (bairro) ou serie_temporal_faixa (faixa etária).">ⓘ</span></div>
          <canvas id="cTemporal"></canvas>
        </div>
        <div class="chart-wrap h380">
          <div class="chart-title">Distribuição por Faixa Etária<span class="minfo" data-tip="Distribuição de atendimentos A09 por faixa etária calculada na data da consulta. Faixas: &lt;1a, 1a, 2-4a, 5-9a, 10-17a, 18-29a, 30-44a, 45-59a, 60+. Dado global ou por_ubs_faixa ao filtrar por UBS/zona.">ⓘ</span></div>
          <canvas id="cFaixa"></canvas>
        </div>
      </div>
      <div class="cards" id="zonaCards"></div>
    </div>

    <!-- PAGE: Análise Territorial -->
    <div class="page" id="page-territorial">
      <h2 class="sec-title">Análise Territorial</h2>
      <div class="tabs">
        <button class="tab active" data-tab="tab-ubs">UBS</button>
        <button class="tab" data-tab="tab-bairro">Bairros</button>
        <button class="tab" data-tab="tab-equipe">Equipes</button>
        <button class="tab" data-tab="tab-micro">Microáreas</button>
      </div>
      <div class="tab-pane active" id="tab-ubs">
        <div class="chart-wrap h520"><div class="chart-title">Top 15 UBS por Casos</div><canvas id="cUBSTop"></canvas></div>
        <div class="tbl-wrap"><table id="tUBS"><thead><tr>
          <th>UBS</th><th>Zona</th>
          <th class="tn">População<span class="minfo" data-tip="Cadastros ativos na FCI (Ficha de Cadastro Individual) do e-SUS por UBS, referência Jul/2025.">ⓘ</span></th>
          <th class="tn">Pop &lt;5<span class="minfo" data-tip="Cadastros FCI com idade &lt; 5 anos em Jul/2025.">ⓘ</span></th>
          <th class="tn">Casos<span class="minfo" data-tip="Total de atendimentos com CID A09 vinculados a esta UBS (via CPF na FCI). Reflete o filtro de mês/toggle ativo.">ⓘ</span></th>
          <th class="tn">Casos &lt;5<span class="minfo" data-tip="Atendimentos A09 em crianças &lt; 5 anos vinculadas a esta UBS.">ⓘ</span></th>
          <th class="tn">Taxa/1.000<span class="minfo" data-tip="Taxa de incidência = (casos_total / pop_total) × 1.000. Denominador: cadastros FCI da UBS em Jul/2025.">ⓘ</span></th>
          <th class="tn">Taxa &lt;5<span class="minfo" data-tip="Taxa de incidência em &lt; 5 anos = (casos_menor5 / pop_menor5) × 1.000.">ⓘ</span></th>
          <th class="tn">Complexo<span class="minfo" data-tip="Atendimentos de pacientes desta UBS realizados no Complexo/UPA (identificado pelo nome da unidade contendo 'COMPLEXO').">ⓘ</span></th>
          <th class="tn">% Compl.<span class="minfo" data-tip="Percentual de casos da UBS atendidos no Complexo: (casos_complexo / casos_total) × 100. ≥40% = vermelho; ≥20% = laranja.">ⓘ</span></th>
        </tr></thead><tbody></tbody></table></div>
      </div>
      <div class="tab-pane" id="tab-bairro">
        <div class="tbl-wrap"><table id="tBairro"><thead><tr>
          <th>Bairro</th>
          <th class="tn">Pop<span class="minfo" data-tip="Cadastros CIDADAO do e-SUS residentes neste bairro.">ⓘ</span></th>
          <th class="tn">Pop &lt;5<span class="minfo" data-tip="Cadastros CIDADAO com &lt; 5 anos neste bairro.">ⓘ</span></th>
          <th class="tn">Casos<span class="minfo" data-tip="Atendimentos A09 de residentes deste bairro. Bairros com &lt;5 casos suprimidos por LGPD.">ⓘ</span></th>
          <th class="tn">Casos &lt;5<span class="minfo" data-tip="Atendimentos A09 em &lt; 5 anos residentes neste bairro.">ⓘ</span></th>
          <th class="tn">Taxa/1.000<span class="minfo" data-tip="Taxa de incidência = (casos / pop_bairro) × 1.000. Denominador: cadastros CIDADAO do bairro.">ⓘ</span></th>
          <th class="tn">Taxa &lt;5<span class="minfo" data-tip="Taxa de incidência em &lt; 5 anos = (casos_menor5 / pop_menor5_bairro) × 1.000.">ⓘ</span></th>
        </tr></thead><tbody></tbody></table></div>
      </div>
      <div class="tab-pane" id="tab-equipe">
        <div class="tbl-wrap"><table id="tEquipe"><thead><tr>
          <th>Equipe</th><th>UBS</th>
          <th class="tn">Pop<span class="minfo" data-tip="Cadastros FCI vinculados a esta equipe de saúde da família.">ⓘ</span></th>
          <th class="tn">Pop &lt;5<span class="minfo" data-tip="Cadastros FCI com &lt; 5 anos vinculados a esta equipe.">ⓘ</span></th>
          <th class="tn">Casos<span class="minfo" data-tip="Atendimentos A09 de pacientes cadastrados nesta equipe.">ⓘ</span></th>
          <th class="tn">Casos &lt;5<span class="minfo" data-tip="Atendimentos A09 em &lt; 5 anos cadastrados nesta equipe.">ⓘ</span></th>
          <th class="tn">Taxa/1.000<span class="minfo" data-tip="Taxa de incidência = (casos / pop_equipe) × 1.000.">ⓘ</span></th>
          <th class="tn">Taxa &lt;5<span class="minfo" data-tip="Taxa de incidência em &lt; 5 anos = (casos_menor5 / pop_menor5_equipe) × 1.000.">ⓘ</span></th>
        </tr></thead><tbody></tbody></table></div>
      </div>
      <div class="tab-pane" id="tab-micro">
        <div class="tbl-wrap"><table id="tMicro"><thead><tr>
          <th>UBS</th><th>Microárea</th>
          <th class="tn">Casos &lt;5<span class="minfo" data-tip="Atendimentos A09 em &lt; 5 anos vinculados a esta microárea via campo MICRO AREA da FCI. Microáreas com ≥3 casos em &lt;5 anos são destacadas como críticas.">ⓘ</span></th>
          <th class="tn">Total<span class="minfo" data-tip="Total de atendimentos A09 (todas as idades) desta microárea.">ⓘ</span></th>
        </tr></thead><tbody></tbody></table></div>
      </div>
    </div>

    <!-- PAGE: Perfil Epidemiológico -->
    <div class="page" id="page-epidemiologico">
      <h2 class="sec-title">Perfil Epidemiológico</h2>
      <div class="cards" id="epiCards"></div>
      <div id="noteEpiSexo" class="filter-note">ⓘ Distribuição por sexo disponível ao filtrar por UBS, zona ou mês.</div>
      <div class="two-col">
        <div class="chart-wrap h380">
          <div class="chart-title">Pirâmide Etária — Distribuição por Faixa<span class="minfo" data-tip="Atendimentos A09 por faixa etária (calculada na data da consulta). Ao filtrar por UBS, usa por_ubs_faixa; por zona, agrega UBS da zona; por mês, usa serie_temporal_faixa.">ⓘ</span></div>
          <canvas id="cPiramide"></canvas>
        </div>
        <div class="chart-wrap h380">
          <div class="chart-title">Distribuição por Sexo<span class="minfo" data-tip="Proporção M/F/NI nos atendimentos A09. Hierarquia de fonte: filtro UBS → por_ubs_sexo; zona → agrega por_ubs_sexo; mês → serie_temporal_sexo; sem filtro → por_sexo global. Filtros por bairro/faixa não possuem cruzamento por sexo.">ⓘ</span></div>
          <canvas id="cSexo"></canvas>
        </div>
      </div>
      <div id="noteCIDs" class="filter-note">ⓘ Detalhamento de CIDs por bairro não disponível. Filtre por UBS para ver CIDs específicos.</div>
      <div class="chart-wrap h460">
        <div class="chart-title">Principais CIDs Registrados (Top 15)<span class="minfo" data-tip="Top 15 CIDs registrados nos atendimentos A09, contando o campo CIDS da FAI (pode haver múltiplos CIDs por atendimento). Ao filtrar por UBS, usa cids_por_ubs; por zona, agrega. CIDs com &lt;5 ocorrências suprimidos por LGPD.">ⓘ</span></div>
        <canvas id="cCIDs"></canvas>
      </div>
      <div id="noteRecorrencia" class="filter-note">ⓘ Recorrência por bairro/faixa/mês não disponível. Filtre por UBS ou zona para detalhe específico.</div>
      <div class="chart-wrap h380">
        <div class="chart-title">Recorrência de Atendimentos por Paciente<span class="minfo" data-tip="Distribuição de pacientes por número de atendimentos A09 no período. 1 atend = paciente visto uma vez; 2 atend = duas vezes; 3+ = três ou mais. Calculado por CPF. Ao filtrar UBS/zona, usa recorrencia_por_ubs.">ⓘ</span></div>
        <canvas id="cRecorrencia"></canvas>
      </div>
      <h3 style="font-size:14px;font-weight:700;color:var(--ink-primary);margin:22px 0 14px;border-left:3px solid var(--danger);padding-left:10px">
        Demanda Espontânea (Complexo) — Análise Anual
      </h3>
      <div class="cards" id="complexoCards"></div>
      <div class="chart-wrap h520">
        <div class="chart-title">UBS de Origem — Pacientes no Complexo (Top 15)<span class="minfo" data-tip="UBS das quais mais pacientes buscaram atendimento no Complexo/UPA em vez da própria UBS. Identificado pelo campo UNIDADE SAUDE da FAI contendo 'COMPLEXO', cruzado com o cadastro UBS do paciente na FCI.">ⓘ</span></div>
        <canvas id="cComplexoUBS"></canvas>
      </div>
      <div class="tbl-wrap"><table id="tEvasao"><thead><tr>
        <th>UBS</th>
        <th class="tn">Total Casos<span class="minfo" data-tip="Total de atendimentos A09 de pacientes desta UBS, independente de onde foram atendidos.">ⓘ</span></th>
        <th class="tn">No Complexo<span class="minfo" data-tip="Atendimentos A09 de pacientes desta UBS realizados no Complexo/UPA.">ⓘ</span></th>
        <th class="tn">Taxa Evasão<span class="minfo" data-tip="Percentual de atendimentos que ocorreram no Complexo em vez da UBS: (no_complexo / total) × 100. Verde &lt;20%; laranja 20-40%; vermelho ≥40%.">ⓘ</span></th>
      </tr></thead><tbody></tbody></table></div>
    </div>

    <!-- PAGE: Mapa -->
    <div class="page" id="page-mapa">
      <h2 class="sec-title">Mapa Territorial — Incidência por Bairro</h2>
      <p style="font-size:12px;color:var(--ink-secondary);margin-bottom:12px">
        Choropleth por taxa de incidência/1.000 hab. <span class="minfo" data-tip="Taxa de incidência A09 por bairro = (casos_bairro / pop_bairro) × 1.000. Escala de cor proporcional ao intervalo [mín, máx] do conjunto filtrado. Cinza = sem dados ou &lt;5 casos (suprimido por LGPD). Ao filtrar por mês, recalcula com base em serie_temporal_bairro sobre população anual.">ⓘ</span>
        Passe o mouse ou clique para detalhes. Bairros sem dados populacionais exibem número absoluto de casos.
      </p>
      <div id="leafletMap"></div>
    </div>

    <footer class="footer">
      Secretaria Municipal de Saúde de Arapiraca &mdash; Vigilância em Saúde<br>
      Fonte: e-SUS APS &mdash; Ficha de Atendimento Individual &mdash; Período: Jan&ndash;Dez 2025<br>
      Dados anonimizados conforme LGPD (Lei 13.709/2018). Agregações com n&lt;5 suprimidas.
    </footer>
  </main>
</div>

<script>
"""

js_code = """
// ─── CONSTANTS ────────────────────────────────────────────────────────────────
var C = {
  blue:'#2E86C1', navy:'#1B4F72', gold:'#D4A017', red:'#C0392B', warn:'#D4770B', ok:'#1E8449',
  blueA:'rgba(46,134,193,0.75)', goldA:'rgba(212,160,23,0.75)',
  redA:'rgba(192,57,43,0.75)', grayA:'rgba(189,195,199,0.4)',
  fp:['#1B4F72','#2471A3','#2E86C1','#5DADE2','#85C1E9','#D4A017','#E6B02E','#F1C452','#F5CD79']
};
var MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
var MESES_F = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
var FAIXAS = ['<1a','1a','2-4a','5-9a','10-17a','18-29a','30-44a','45-59a','60+'];

// ─── STATE ────────────────────────────────────────────────────────────────────
var charts = {};
var leafletMap = null, gLayer = null;
var u5 = false, fRep = false, fCx = false;
var filters = { zona:'', ubs:'', bairro:'', faixa:'', sexo:'', mes:'' };
var currentPage = 'visao-geral';

// ─── FORMAT HELPERS ───────────────────────────────────────────────────────────
function fmt(n) {
  if (n === null || n === undefined || (typeof n === 'number' && isNaN(n))) return '—';
  return Number(n).toLocaleString('pt-BR');
}
function fmtR(n, d) {
  if (n === null || n === undefined || (typeof n === 'number' && isNaN(n))) return '—';
  d = d === undefined ? 1 : d;
  return Number(n).toLocaleString('pt-BR', {minimumFractionDigits:d, maximumFractionDigits:d});
}
function fmtP(n) { return fmtR(n) + '%'; }

// ─── DATA HELPERS ─────────────────────────────────────────────────────────────
function filteredUBS() {
  var list = DATA.por_ubs;
  if (filters.zona) list = list.filter(function(u){ return u.zona === filters.zona; });
  if (filters.ubs)  list = list.filter(function(u){ return u.ubs === filters.ubs; });
  return list;
}

function filteredSTUBS() {
  var list = DATA.serie_temporal_ubs;
  if (filters.ubs) list = list.filter(function(x){ return x.ubs === filters.ubs; });
  if (filters.zona) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    list = list.filter(function(x){ return ubsZ.indexOf(x.ubs) !== -1; });
  }
  return list;
}

function getMonthlyData() {
  var byM = {};
  for (var m=1; m<=12; m++) {
    byM[m] = {mes:m,casos:0,menor5:0,repetidos:0,complexo:0,pacientes:0,pac5:0,menor5_repetidos:0,menor5_complexo:0};
  }
  var hasUBS   = filters.ubs || filters.zona;
  var hasBairro = filters.bairro;
  var hasFaixa  = filters.faixa;

  if (hasUBS) {
    filteredSTUBS().forEach(function(x) {
      var r = byM[x.mes]; if (!r) return;
      r.casos += x.casos||0; r.menor5 += x.menor5||0;
      r.repetidos += x.repetidos||0; r.complexo += x.complexo||0;
    });
  } else if (hasBairro) {
    DATA.serie_temporal_bairro.filter(function(x){ return x.bairro===hasBairro; }).forEach(function(x) {
      var r = byM[x.mes]; if (!r) return;
      r.casos += x.casos||0; r.menor5 += x.menor5||0;
      r.repetidos += x.repetidos||0; r.complexo += x.complexo||0;
    });
  } else if (hasFaixa) {
    DATA.serie_temporal_faixa.filter(function(x){ return x.faixa===hasFaixa; }).forEach(function(x) {
      var r = byM[x.mes]; if (!r) return;
      r.casos += x.casos||0; r.repetidos += x.repetidos||0; r.complexo += x.complexo||0;
    });
  } else {
    DATA.serie_temporal.forEach(function(x) {
      var r = byM[x.mes]; if (!r) return;
      r.casos = x.total||0; r.menor5 = x.menor5||0;
      r.repetidos = x.repetidos||0; r.complexo = x.complexo||0;
      r.pacientes = x.pacientes||0; r.pac5 = x.pacientes_menor5||0;
      r.menor5_repetidos = x.menor5_repetidos||0;
      r.menor5_complexo  = x.menor5_complexo||0;
    });
  }
  return [1,2,3,4,5,6,7,8,9,10,11,12].map(function(m){ return byM[m]; });
}

function computeCardTotals() {
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var hasUBS    = filters.ubs || filters.zona;
  var hasBairro = filters.bairro;
  var hasFaixa  = filters.faixa;
  var hasSexo   = filters.sexo;
  var atend = 0, menor5 = 0, pac = null, pac5 = null;

  if (mesN) {
    var md = getMonthlyData();
    var mr = md.find(function(x){ return x.mes===mesN; }) || {};
    atend  = fRep ? (mr.repetidos||0) : fCx ? (mr.complexo||0) : (mr.casos||0);
    menor5 = fRep ? (mr.menor5_repetidos||mr.menor5||0) : fCx ? (mr.menor5_complexo||mr.menor5||0) : (mr.menor5||0);
    pac  = (!hasUBS && !hasBairro && !hasFaixa && mr.pacientes) ? mr.pacientes : null;
    pac5 = (!hasUBS && !hasBairro && !hasFaixa && mr.pac5) ? mr.pac5 : null;
  } else if (hasUBS) {
    var ubsF = filteredUBS();
    atend  = ubsF.reduce(function(s,u){ return s+(fRep?u.casos_repetidos:fCx?u.casos_complexo:u.casos_total)||0; },0);
    menor5 = ubsF.reduce(function(s,u){ return s+(u.casos_menor5||0); },0);
    pac    = ubsF.reduce(function(s,u){ return s+(u.pacientes_total||0); },0);
    pac5   = ubsF.reduce(function(s,u){ return s+(u.pacientes_menor5||0); },0);
  } else if (hasBairro) {
    var br = DATA.por_bairro.find(function(b){ return b.bairro===hasBairro; }) || {};
    atend  = fRep ? (br.repetidos||0) : fCx ? (br.complexo||0) : (br.casos_total||0);
    menor5 = br.casos_menor5||0;
  } else if (hasFaixa) {
    var fr = DATA.por_faixa_etaria.find(function(f){ return f.faixa===hasFaixa; }) || {};
    atend  = fRep ? (fr.repetidos||0) : fCx ? (fr.complexo||0) : (fr.total||fr.casos||0);
    var u5f = ['<1a','1a','2-4a'].indexOf(hasFaixa) !== -1;
    menor5 = u5f ? atend : 0;
  } else if (hasSexo) {
    var s = DATA.por_sexo;
    var sk = hasSexo==='M' ? 'masculino' : 'feminino';
    atend  = s[sk]||0;
    menor5 = s[sk+'_menor5']||0;
  } else {
    var m = DATA.metadata;
    atend  = fRep ? m.total_repetidos : fCx ? m.total_complexo : m.total_atendimentos;
    menor5 = fRep ? (m.menor5_repetidos||m.total_menor5) : fCx ? (m.menor5_complexo||m.total_menor5) : m.total_menor5;
    pac    = fRep ? m.pacientes_repetidos : fCx ? m.pacientes_complexo : m.total_pacientes;
    pac5   = fRep ? (m.pac5_repetidos||m.pacientes_menor5) : fCx ? (m.pac5_complexo||m.pacientes_menor5) : m.pacientes_menor5;
  }
  if (u5) { atend = menor5; pac = pac5; }
  return {atend:atend, menor5:menor5, pacientes:pac, pac5:pac5};
}

// ─── PERFIL EPI HELPERS ───────────────────────────────────────────────────────
function getSexoData() {
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  if (filters.ubs && DATA.por_ubs_sexo) {
    var found = DATA.por_ubs_sexo.find(function(x){ return x.ubs === filters.ubs; });
    if (found) return {masculino:found.masculino||0,feminino:found.feminino||0,
      nao_informado:found.nao_informado||0,
      masculino_menor5:found.masculino_menor5||0,feminino_menor5:found.feminino_menor5||0};
  }
  if (filters.zona && DATA.por_ubs_sexo) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    var agg = {masculino:0,feminino:0,nao_informado:0,masculino_menor5:0,feminino_menor5:0};
    DATA.por_ubs_sexo.filter(function(x){ return ubsZ.indexOf(x.ubs)!==-1; }).forEach(function(x){
      agg.masculino+=x.masculino||0; agg.feminino+=x.feminino||0;
      agg.nao_informado+=x.nao_informado||0;
      agg.masculino_menor5+=x.masculino_menor5||0; agg.feminino_menor5+=x.feminino_menor5||0;
    });
    return agg;
  }
  if (mesN && DATA.serie_temporal_sexo) {
    var mr = DATA.serie_temporal_sexo.find(function(x){ return x.mes===mesN; });
    if (mr) return {masculino:mr.masculino||0,feminino:mr.feminino||0,
      nao_informado:mr.nao_informado||0,
      masculino_menor5:mr.masculino_menor5||0,feminino_menor5:mr.feminino_menor5||0};
  }
  return DATA.por_sexo;
}

function getFaixaData() {
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  if (filters.ubs && DATA.por_ubs_faixa) {
    var found = DATA.por_ubs_faixa.find(function(x){ return x.ubs === filters.ubs; });
    if (found) return found.faixas;
  }
  if (filters.zona && DATA.por_ubs_faixa) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    var byF = {};
    DATA.por_ubs_faixa.filter(function(x){ return ubsZ.indexOf(x.ubs)!==-1; }).forEach(function(x){
      (x.faixas||[]).forEach(function(f){
        if (!byF[f.faixa]) byF[f.faixa]={faixa:f.faixa,casos:0,complexo:0,repetidos:0};
        byF[f.faixa].casos+=f.casos||0; byF[f.faixa].complexo+=f.complexo||0; byF[f.faixa].repetidos+=f.repetidos||0;
      });
    });
    return FAIXAS.map(function(f){ return byF[f]||{faixa:f,casos:0,complexo:0,repetidos:0}; });
  }
  if (mesN) {
    var byF2 = {};
    DATA.serie_temporal_faixa.filter(function(x){ return x.mes===mesN; }).forEach(function(x){ byF2[x.faixa]=x; });
    return FAIXAS.map(function(f){ return byF2[f]||{faixa:f,casos:0,complexo:0,repetidos:0}; });
  }
  var byF3 = {};
  DATA.por_faixa_etaria.forEach(function(x){ byF3[x.faixa]=x; });
  return FAIXAS.map(function(f){ return byF3[f]||{faixa:f,casos:0,complexo:0,repetidos:0}; });
}

function getCIDsData() {
  if (filters.ubs && DATA.cids_por_ubs) {
    var found = DATA.cids_por_ubs.find(function(x){ return x.ubs===filters.ubs; });
    if (found) return found.cids||[];
  }
  if (filters.zona && DATA.cids_por_ubs) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    var byC = {};
    DATA.cids_por_ubs.filter(function(x){ return ubsZ.indexOf(x.ubs)!==-1; }).forEach(function(x){
      (x.cids||[]).forEach(function(c){
        if (!byC[c.cid]) byC[c.cid]={cid:c.cid,total:0,menor5:0};
        byC[c.cid].total+=c.total||0; byC[c.cid].menor5+=c.menor5||0;
      });
    });
    return Object.values(byC).sort(function(a,b){ return b.total-a.total; }).slice(0,15);
  }
  return (DATA.cids_combinados||[]).slice(0,15);
}

function getRecorrenciaData() {
  if (filters.ubs && DATA.recorrencia_por_ubs) {
    var found = DATA.recorrencia_por_ubs.find(function(x){ return x.ubs===filters.ubs; });
    if (found) return {'1_atend':found['1_atend']||0,'2_atend':found['2_atend']||0,'3_mais':found['3_mais']||0};
  }
  if (filters.zona && DATA.recorrencia_por_ubs) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    var agg = {'1_atend':0,'2_atend':0,'3_mais':0};
    DATA.recorrencia_por_ubs.filter(function(x){ return ubsZ.indexOf(x.ubs)!==-1; }).forEach(function(x){
      agg['1_atend']+=x['1_atend']||0; agg['2_atend']+=x['2_atend']||0; agg['3_mais']+=x['3_mais']||0;
    });
    return agg;
  }
  return u5 ? DATA.recorrencia.menor5 : DATA.recorrencia.geral;
}

// ─── REFRESH ──────────────────────────────────────────────────────────────────
function refreshAll() {
  updateFilterStatus();
  renderMainCards();
  renderZonaCards();
  destroyCharts();
  chartTemporal();
  chartFaixa();
  chartUBSTop();
  chartPiramide();
  chartSexo();
  chartCIDs();
  chartRecorrencia();
  chartComplexoUBS();
  buildTables();
  renderEpiCards();
  renderComplexoCards();
  updateMapColors();
}

// ─── CARDS ────────────────────────────────────────────────────────────────────
function mkCard(lbl, val, meta, cls) {
  var tip = METODOLOGIA[lbl] || '';
  var tipHtml = tip ? ' <span class="minfo" data-tip="'+tip.replace(/"/g,'&quot;')+'">&#9432;</span>' : '';
  return '<div class="card'+(cls?' '+cls:'')+'">'+
    '<div class="card-lbl">'+lbl+tipHtml+'</div>'+
    '<div class="card-val">'+val+'</div>'+
    '<div class="card-meta">'+meta+'</div></div>';
}

function renderMainCards() {
  var t = computeCardTotals();
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var periodo = mesN ? MESES_F[mesN]+' 2025' : 'Jan – Dez 2025';
  var toggleMeta = fRep ? 'Pacientes recorrentes' : fCx ? 'Demanda espon.' : u5 ? 'Filtro < 5 anos' : '';
  var pct5 = (t.atend>0 && !u5) ? fmtP((t.menor5/t.atend)*100)+' do total' : '';
  document.getElementById('mainCards').innerHTML =
    mkCard('Total Atendimentos', fmt(t.atend||0), toggleMeta, (fRep||fCx)?'ctog':u5?'cu5':'')+
    mkCard('Pacientes Únicos', t.pacientes!==null?fmt(t.pacientes):'—', 'Indivíduos distintos', (fRep||fCx)?'ctog':u5?'cu5':'')+
    mkCard('Atend. < 5 anos', fmt(t.menor5||0), pct5, '')+
    mkCard('Pacientes < 5 anos', t.pac5!==null?fmt(t.pac5):'—', 'Crianças afetadas', '')+
    mkCard('Período', periodo, mesN?'Mês selecionado':'Anual', '');
}

function renderZonaCards() {
  var ubsAll = filteredUBS();
  var field = fRep?'casos_repetidos':fCx?'casos_complexo':u5?'casos_menor5':'casos_total';
  var rural  = ubsAll.filter(function(u){ return u.zona==='RURAL'; }).reduce(function(s,u){ return s+(u[field]||0); },0);
  var urbana = ubsAll.filter(function(u){ return u.zona==='URBANA'; }).reduce(function(s,u){ return s+(u[field]||0); },0);
  var tot = (rural+urbana)||1;
  document.getElementById('zonaCards').innerHTML =
    mkCard('Zona Urbana', fmt(urbana), fmtP(urbana/tot*100)+' do total', '')+
    mkCard('Zona Rural',  fmt(rural),  fmtP(rural/tot*100)+' do total', '');
}

function renderEpiCards() {
  var s = getSexoData();
  var tot = (s.masculino+s.feminino+(s.nao_informado||0))||1;
  document.getElementById('epiCards').innerHTML =
    mkCard('Masculino', fmt(s.masculino), fmtP(s.masculino/tot*100), '')+
    mkCard('Feminino',  fmt(s.feminino),  fmtP(s.feminino/tot*100), '')+
    mkCard('Não Informado', fmt(s.nao_informado||0), fmtP((s.nao_informado||0)/tot*100), '');
}

function renderComplexoCards() {
  var cx = DATA.complexo;
  var ubsF = filteredUBS();
  var totalCx, comVin, semVin;
  if (filters.ubs || filters.zona) {
    totalCx = ubsF.reduce(function(s,u){ return s+(u.casos_complexo||0); },0);
    comVin = null; semVin = null;
  } else {
    totalCx = cx.total_atendimentos||0;
    comVin  = cx.com_vinculo||0;
    semVin  = cx.sem_vinculo||0;
  }
  var metaTot = (filters.ubs||filters.zona)
    ? ubsF.reduce(function(s,u){ return s+(u.casos_total||0); },0)
    : DATA.metadata.total_atendimentos||1;
  var tot2 = totalCx||1;
  document.getElementById('complexoCards').innerHTML =
    mkCard('Demanda Esponânea (Complexo)', fmt(totalCx), fmtP(totalCx/metaTot*100)+' do total', 'ctog')+
    (comVin!==null?mkCard('Com Vínculo APS', fmt(comVin), fmtP(comVin/tot2*100)+' da demanda', ''):'')+
    (semVin!==null?mkCard('Sem Vínculo', fmt(semVin), fmtP(semVin/tot2*100)+' da demanda', ''):'')+
    mkCard('Pacientes Recorrentes', fmt(DATA.metadata.total_repetidos||0), 'atend. com ≥2 visitas', 'cu5');
}

// ─── CHARTS ───────────────────────────────────────────────────────────────────
function destroyCharts() {
  Object.keys(charts).forEach(function(k){ try{charts[k].destroy();}catch(e){} });
  charts = {};
}

function barColor() {
  if (fRep) return C.goldA;
  if (fCx)  return C.redA;
  if (u5)   return C.goldA;
  return C.blueA;
}

function chartTemporal() {
  var monthly = getMonthlyData();
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var vals = monthly.map(function(x){ return fRep?x.repetidos:fCx?x.complexo:u5?x.menor5:x.casos; });
  var bg = monthly.map(function(x){ return (mesN && x.mes!==mesN) ? C.grayA : barColor(); });
  var lbl = fRep?'Casos Repetidos':fCx?'Demanda Espon.':u5?'Atend. < 5 anos':'Total Atendimentos';
  charts.cTemporal = new Chart(document.getElementById('cTemporal'),{
    type:'bar',
    data:{labels:MESES,datasets:[{label:lbl,data:vals,backgroundColor:bg}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'top'}},scales:{y:{beginAtZero:true}}}
  });
}

function chartFaixa() {
  var faixaData = getFaixaData();
  var vals = faixaData.map(function(f){ return fRep?(f.repetidos||0):fCx?(f.complexo||0):(f.casos||f.total||0); });
  charts.cFaixa = new Chart(document.getElementById('cFaixa'),{
    type:'bar',
    data:{labels:FAIXAS,datasets:[{label:fRep?'Repetidos':fCx?'Complexo':'Casos',data:vals,backgroundColor:barColor(),borderRadius:3}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
  });
}

function chartUBSTop() {
  var ubsList = filteredUBS().slice();
  var field = fRep?'casos_repetidos':fCx?'casos_complexo':u5?'casos_menor5':'casos_total';
  ubsList.sort(function(a,b){ return (b[field]||0)-(a[field]||0); });
  var top = ubsList.slice(0,15);
  charts.cUBSTop = new Chart(document.getElementById('cUBSTop'),{
    type:'bar',
    data:{labels:top.map(function(u){ return u.ubs; }),
      datasets:[{label:fRep?'Repetidos':fCx?'Complexo':u5?'< 5 anos':'Casos',
        data:top.map(function(u){ return u[field]||0; }),backgroundColor:barColor()}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'top'}},scales:{x:{beginAtZero:true}}}
  });
}

function chartPiramide() {
  var faixaData = getFaixaData();
  var vals = faixaData.map(function(f){ return fRep?(f.repetidos||0):fCx?(f.complexo||0):(f.casos||f.total||0); });
  charts.cPiramide = new Chart(document.getElementById('cPiramide'),{
    type:'bar',
    data:{labels:FAIXAS,datasets:[{label:'Casos',data:vals,backgroundColor:C.fp,borderRadius:3}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true}}}
  });
}

function chartSexo() {
  var s = getSexoData();
  charts.cSexo = new Chart(document.getElementById('cSexo'),{
    type:'doughnut',
    data:{labels:['Masculino','Feminino','Não Informado'],
      datasets:[{data:[s.masculino,s.feminino,s.nao_informado||0],backgroundColor:['#2E86C1','#D4A017','#BDC3C7']}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right'}}}
  });
  var noteEl = document.getElementById('noteEpiSexo');
  var hasNote = (filters.bairro || filters.faixa) && !filters.ubs && !filters.zona && !filters.mes;
  if (noteEl) noteEl.classList.toggle('visible', !!hasNote);
}

function chartCIDs() {
  var cids = getCIDsData();
  var noteEl = document.getElementById('noteCIDs');
  var hasNote = filters.bairro && !filters.ubs && !filters.zona;
  if (noteEl) noteEl.classList.toggle('visible', !!hasNote);
  if (!cids || !cids.length) return;
  charts.cCIDs = new Chart(document.getElementById('cCIDs'),{
    type:'bar',
    data:{labels:cids.map(function(c){ return c.cid||'?'; }),
      datasets:[{label:'Registros',data:cids.map(function(c){ return c.total||0; }),backgroundColor:C.blueA}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true}}}
  });
}

function chartRecorrencia() {
  var r = getRecorrenciaData();
  var noteEl = document.getElementById('noteRecorrencia');
  var hasNote = (filters.bairro || filters.faixa || filters.mes) && !filters.ubs && !filters.zona;
  if (noteEl) noteEl.classList.toggle('visible', !!hasNote);
  charts.cRecorrencia = new Chart(document.getElementById('cRecorrencia'),{
    type:'bar',
    data:{labels:['1 atendimento','2 atendimentos','3 ou mais'],
      datasets:[{label:'Pacientes',data:[r['1_atend'],r['2_atend'],r['3_mais']],
        backgroundColor:[C.blueA,C.goldA,C.redA]}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
  });
}

function chartComplexoUBS() {
  var origem = DATA.complexo.ubs_origem||[];
  if (filters.zona) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    origem = origem.filter(function(u){ return ubsZ.indexOf(u.ubs)!==-1; });
  }
  if (filters.ubs) origem = origem.filter(function(u){ return u.ubs===filters.ubs; });
  var top = origem.slice(0,15);
  charts.cComplexoUBS = new Chart(document.getElementById('cComplexoUBS'),{
    type:'bar',
    data:{labels:top.map(function(u){ return u.ubs; }),
      datasets:[{label:'Casos no Complexo',data:top.map(function(u){ return u.casos; }),backgroundColor:C.redA}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true}}}
  });
}

// ─── TABLES ───────────────────────────────────────────────────────────────────
function buildTables() {
  buildUBSTable(); buildBairroTable(); buildEquipeTable(); buildMicroTable(); buildEvasaoTable();
}

function buildUBSTable() {
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var rows;
  if (mesN) {
    var stubs = filteredSTUBS().filter(function(x){ return x.mes===mesN; });
    var ubsPop = {}; DATA.por_ubs.forEach(function(u){ ubsPop[u.ubs]=u; });
    rows = stubs.map(function(x) {
      var p = ubsPop[x.ubs]||{};
      var casos = x.casos||0;
      return {ubs:x.ubs,zona:p.zona||'',pop_total:p.pop_total||0,pop_menor5:p.pop_menor5||0,
        casos_total:casos,casos_menor5:x.menor5||0,casos_repetidos:x.repetidos||0,
        casos_complexo:x.complexo||0,
        pct_complexo:casos>0?Math.round((x.complexo||0)/casos*1000)/10:0,
        taxa_geral:(p.pop_total||0)>0?Math.round(casos/(p.pop_total||1)*10000)/10:0,
        taxa_menor5:(p.pop_menor5||0)>0?Math.round((x.menor5||0)/(p.pop_menor5||1)*10000)/10:0};
    });
  } else { rows = filteredUBS(); }
  var field = fRep?'casos_repetidos':fCx?'casos_complexo':u5?'casos_menor5':'casos_total';
  rows = rows.slice().sort(function(a,b){ return (b[field]||0)-(a[field]||0); });
  var tbody = document.querySelector('#tUBS tbody');
  tbody.innerHTML = rows.map(function(u) {
    var cd = fRep?(u.casos_repetidos||0):fCx?(u.casos_complexo||0):u5?(u.casos_menor5||0):(u.casos_total||0);
    var pctC = u.pct_complexo||0;
    var aCls = pctC>=40?'adanger':pctC>=20?'awarn':'';
    return '<tr><td>'+u.ubs+'</td><td>'+(u.zona||'')+'</td>'+
      '<td class="tn">'+fmt(u.pop_total)+'</td><td class="tn">'+fmt(u.pop_menor5)+'</td>'+
      '<td class="tn"><strong>'+fmt(cd)+'</strong></td>'+
      '<td class="tn">'+fmt(u.casos_menor5||0)+'</td>'+
      '<td class="tn">'+fmtR(u.taxa_geral)+'</td>'+
      '<td class="tn">'+fmtR(u.taxa_menor5)+'</td>'+
      '<td class="tn">'+fmt(u.casos_complexo||0)+'</td>'+
      '<td class="tn '+aCls+'">'+fmtP(pctC)+'</td></tr>';
  }).join('');
}

function buildBairroTable() {
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var rows;
  if (mesN) {
    var byB = {};
    DATA.serie_temporal_bairro.filter(function(x){ return x.mes===mesN; }).forEach(function(x){
      if (!byB[x.bairro]) byB[x.bairro]={bairro:x.bairro,casos_total:0,casos_menor5:0,repetidos:0,complexo:0};
      byB[x.bairro].casos_total+=x.casos||0; byB[x.bairro].casos_menor5+=x.menor5||0;
      byB[x.bairro].repetidos+=x.repetidos||0; byB[x.bairro].complexo+=x.complexo||0;
    });
    var bPop={};DATA.por_bairro.forEach(function(b){ bPop[b.bairro]=b; });
    rows = Object.values(byB).map(function(r){
      var p=bPop[r.bairro]||{};
      r.pop_total=p.pop_total||0; r.pop_menor5=p.pop_menor5||0;
      r.taxa_geral=r.pop_total>0?Math.round(r.casos_total/r.pop_total*10000)/10:0;
      r.taxa_menor5=r.pop_menor5>0?Math.round(r.casos_menor5/r.pop_menor5*10000)/10:0;
      return r;
    });
    if (filters.bairro) rows=rows.filter(function(r){ return r.bairro===filters.bairro; });
  } else if (filters.ubs) {
    var bairrosForUBS = DATA.ubs_bairros_map[filters.ubs]||[];
    rows = DATA.por_bairro.filter(function(b){ return bairrosForUBS.indexOf(b.bairro)!==-1; });
  } else if (filters.bairro) {
    rows = DATA.por_bairro.filter(function(b){ return b.bairro===filters.bairro; });
  } else { rows = DATA.por_bairro; }
  var field = fRep?'repetidos':fCx?'complexo':u5?'casos_menor5':'casos_total';
  rows = rows.slice().sort(function(a,b){ return (b[field]||0)-(a[field]||0); });
  var tbody = document.querySelector('#tBairro tbody');
  tbody.innerHTML = rows.map(function(b){
    var cd = fRep?(b.repetidos||0):fCx?(b.complexo||0):u5?(b.casos_menor5||0):(b.casos_total||0);
    return '<tr><td>'+b.bairro+'</td>'+
      '<td class="tn">'+fmt(b.pop_total||0)+'</td><td class="tn">'+fmt(b.pop_menor5||0)+'</td>'+
      '<td class="tn"><strong>'+fmt(cd)+'</strong></td>'+
      '<td class="tn">'+fmt(b.casos_menor5||0)+'</td>'+
      '<td class="tn">'+fmtR(b.taxa_geral||0)+'</td>'+
      '<td class="tn">'+fmtR(b.taxa_menor5||0)+'</td></tr>';
  }).join('');
}

function buildEquipeTable() {
  var list = DATA.por_equipe||[];
  if (filters.zona) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    list = list.filter(function(e){ return ubsZ.indexOf(e.ubs)!==-1; });
  }
  if (filters.ubs) list = list.filter(function(e){ return e.ubs===filters.ubs; });
  var field = fRep?'repetidos':fCx?'complexo':u5?'casos_menor5':'casos_total';
  list = list.slice().sort(function(a,b){ return (b[field]||0)-(a[field]||0); });
  var tbody = document.querySelector('#tEquipe tbody');
  tbody.innerHTML = list.slice(0,60).map(function(e){
    var cd = fRep?(e.repetidos||0):fCx?(e.complexo||0):u5?(e.casos_menor5||0):(e.casos_total||0);
    return '<tr><td>'+e.equipe+'</td><td>'+e.ubs+'</td>'+
      '<td class="tn">'+fmt(e.pop_total||0)+'</td><td class="tn">'+fmt(e.pop_menor5||0)+'</td>'+
      '<td class="tn"><strong>'+fmt(cd)+'</strong></td>'+
      '<td class="tn">'+fmt(e.casos_menor5||0)+'</td>'+
      '<td class="tn">'+fmtR(e.taxa_geral||0)+'</td>'+
      '<td class="tn">'+fmtR(e.taxa_menor5||0)+'</td></tr>';
  }).join('');
}

function buildMicroTable() {
  var list = DATA.microareas_criticas||[];
  if (filters.zona) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    list = list.filter(function(m){ return ubsZ.indexOf(m.ubs)!==-1; });
  }
  if (filters.ubs) list = list.filter(function(m){ return m.ubs===filters.ubs; });
  var sortField = u5 ? 'casos_menor5' : 'casos_total';
  list = list.slice().sort(function(a,b){ return (b[sortField]||0)-(a[sortField]||0); });
  var tbody = document.querySelector('#tMicro tbody');
  tbody.innerHTML = list.slice(0,60).map(function(m){
    var m5cls = u5 ? ' style="font-weight:700;color:var(--brand)"' : '';
    return '<tr><td>'+m.ubs+'</td><td>'+m.microarea+'</td>'+
      '<td class="tn"'+m5cls+'>'+fmt(m.casos_menor5||0)+'</td>'+
      '<td class="tn">'+fmt(m.casos_total||0)+'</td></tr>';
  }).join('');
}

function buildEvasaoTable() {
  var list = DATA.evasao_complexo||[];
  if (filters.ubs) list = list.filter(function(e){ return e.ubs===filters.ubs; });
  if (filters.zona) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    list = list.filter(function(e){ return ubsZ.indexOf(e.ubs)!==-1; });
  }
  list = list.slice().sort(function(a,b){ return (b.taxa_evasao||0)-(a.taxa_evasao||0); });
  var tbody = document.querySelector('#tEvasao tbody');
  tbody.innerHTML = list.map(function(e){
    var aCls = e.taxa_evasao>=40?'adanger':e.taxa_evasao>=20?'awarn':'aok';
    return '<tr><td>'+e.ubs+'</td>'+
      '<td class="tn">'+fmt(e.casos_total||0)+'</td>'+
      '<td class="tn">'+fmt(e.casos_no_complexo||0)+'</td>'+
      '<td class="tn '+aCls+'">'+fmtP(e.taxa_evasao||0)+'</td></tr>';
  }).join('');
}

// ─── MAPA ─────────────────────────────────────────────────────────────────────
function getFilteredBairros() {
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var result = {};
  DATA.por_bairro.forEach(function(b){ result[b.bairro]=Object.assign({},b); });
  if (mesN) {
    var byB = {};
    DATA.serie_temporal_bairro.filter(function(x){ return x.mes===mesN; }).forEach(function(x){
      if (!byB[x.bairro]) byB[x.bairro]={casos_total:0,casos_menor5:0};
      byB[x.bairro].casos_total+=x.casos||0; byB[x.bairro].casos_menor5+=x.menor5||0;
    });
    Object.keys(byB).forEach(function(bNome){
      if (!result[bNome]) result[bNome]={bairro:bNome,pop_total:0,pop_menor5:0,taxa_geral:0,taxa_menor5:0};
      var pop=result[bNome].pop_total||0;
      result[bNome].casos_total=byB[bNome].casos_total;
      result[bNome].casos_menor5=byB[bNome].casos_menor5;
      result[bNome].taxa_geral=pop>0?Math.round(byB[bNome].casos_total/pop*10000)/10:0;
      result[bNome].taxa_menor5=(result[bNome].pop_menor5||0)>0?Math.round(byB[bNome].casos_menor5/(result[bNome].pop_menor5||1)*10000)/10:0;
    });
  }
  if (filters.ubs) {
    var bairrosUBS=DATA.ubs_bairros_map[filters.ubs]||[];
    var filtered={};
    bairrosUBS.forEach(function(b){ if(result[b]) filtered[b]=result[b]; });
    return filtered;
  }
  if (filters.zona) {
    var ubsZ=DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    var bairrosZona=[];
    ubsZ.forEach(function(ubs){ (DATA.ubs_bairros_map[ubs]||[]).forEach(function(b){ bairrosZona.push(b); }); });
    var filtered2={};
    bairrosZona.forEach(function(b){ if(result[b]) filtered2[b]=result[b]; });
    return filtered2;
  }
  if (filters.bairro && result[filters.bairro]) {
    var filtered3={}; filtered3[filters.bairro]=result[filters.bairro]; return filtered3;
  }
  return result;
}

function updateMapColors() {
  if (!leafletMap || !gLayer) return;
  var bLookup=getFilteredBairros();
  var taxa_field=u5?'taxa_menor5':'taxa_geral';
  var taxaVals=Object.values(bLookup).filter(function(b){ return (b[taxa_field]||0)>0; }).map(function(b){ return b[taxa_field]||0; });
  var maxTaxa=taxaVals.length?Math.max.apply(null,taxaVals):50;
  var minTaxa=taxaVals.length?Math.min.apply(null,taxaVals):0;
  function getColor(taxa) {
    if (!taxa||taxa<=0) return '#D5D8DC';
    var t=Math.min((taxa-minTaxa)/(maxTaxa-minTaxa+0.001),1);
    var r=Math.round(234+(27-234)*t),g=Math.round(243+(79-243)*t),b=Math.round(251+(114-251)*t);
    return 'rgb('+r+','+g+','+b+')';
  }
  gLayer.eachLayer(function(layer) {
    var feature=layer.feature;
    var bNome=(feature.properties.bairro||(feature.properties.NM_BAIRRO||'').toUpperCase());
    var bd=bLookup[bNome]||{};
    layer.setStyle({fillColor:getColor(bd[taxa_field]||0),weight:1,color:'#555',fillOpacity:bd[taxa_field]?0.75:0.2});
    layer.setPopupContent(
      '<strong style="font-size:13px">'+(feature.properties.NM_BAIRRO||bNome)+'</strong><br>'+
      'Casos: <strong>'+(bd.casos_total?fmt(bd.casos_total):'—')+'</strong><br>'+
      'Taxa: '+(bd.taxa_geral?fmtR(bd.taxa_geral)+'/1.000 hab':'—')+'<br>'+
      'Casos &lt;5: '+(bd.casos_menor5?fmt(bd.casos_menor5):'—')+'<br>'+
      'Pop: '+(bd.pop_total?fmt(bd.pop_total):'—'),
      {maxWidth:200});
  });
  if (leafletMap._mapLegend) leafletMap._mapLegend.remove();
  var legend=L.control({position:'bottomright'});
  legend.onAdd=function() {
    var div=L.DomUtil.create('div');
    div.style.cssText='background:#fff;padding:10px 12px;border-radius:4px;font-size:11px;font-family:system-ui,sans-serif;line-height:1.8;border:1px solid rgba(0,0,0,.15)';
    div.innerHTML='<strong>Taxa/1.000 hab</strong><br>';
    for (var i=0;i<=5;i++) {
      var v=minTaxa+(maxTaxa-minTaxa)*i/5;
      div.innerHTML+='<span style="display:inline-block;width:14px;height:10px;background:'+getColor(v)+';margin-right:6px;vertical-align:middle;border:1px solid #ccc"></span>'+fmtR(v)+'<br>';
    }
    div.innerHTML+='<span style="display:inline-block;width:14px;height:10px;background:#D5D8DC;margin-right:6px;vertical-align:middle;border:1px solid #ccc"></span>Sem dados';
    return div;
  };
  legend.addTo(leafletMap);
  leafletMap._mapLegend=legend;
}

function initMap() {
  if (leafletMap) { leafletMap.invalidateSize(); updateMapColors(); return; }
  leafletMap=L.map('leafletMap').setView([-9.752,-36.661],12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',maxZoom:18
  }).addTo(leafletMap);
  gLayer=L.geoJSON(BAIRROS_GEO,{
    style:function(){ return {fillColor:'#D5D8DC',weight:1,color:'#555',fillOpacity:0.5}; },
    onEachFeature:function(feature,layer){
      layer.bindPopup('Carregando...',{maxWidth:200});
      layer.on('mouseover',function(){ this.setStyle({weight:2,fillOpacity:0.92}); this.openPopup(); });
      layer.on('mouseout', function(){ gLayer.resetStyle(this); this.closePopup(); });
      layer.on('click',    function(){ this.openPopup(); });
    }
  }).addTo(leafletMap);
  setTimeout(function(){ leafletMap.invalidateSize(); updateMapColors(); },300);
}

// ─── CSV EXPORT ───────────────────────────────────────────────────────────────
function buildCSVFilename() {
  var parts=['DDA_Arapiraca'];
  if (filters.ubs) parts.push(filters.ubs.replace(/[^a-zA-Z0-9]/g,'_').slice(0,20));
  else if (filters.zona) parts.push(filters.zona);
  if (filters.mes) parts.push(MESES[parseInt(filters.mes)-1]+'2025');
  else parts.push('2025');
  parts.push(currentPage.replace('-','_'));
  return parts.join('_')+'.csv';
}
function buildCSVHeader() {
  var lines=[];
  lines.push('# Painel Epidemiológico — Doença Diarreica Aguda (CID A09) — Arapiraca/AL — 2025');
  var now=new Date();
  lines.push('# Exportado em: '+now.toLocaleDateString('pt-BR')+' '+now.toLocaleTimeString('pt-BR').slice(0,5));
  var fParts=[];
  if (filters.zona)   fParts.push('Zona: '+filters.zona);
  if (filters.ubs)    fParts.push('UBS: '+filters.ubs);
  if (filters.bairro) fParts.push('Bairro: '+filters.bairro);
  if (filters.faixa)  fParts.push('Faixa: '+filters.faixa);
  if (filters.sexo)   fParts.push('Sexo: '+(filters.sexo==='M'?'Masculino':'Feminino'));
  if (filters.mes)    fParts.push('Mês: '+MESES_F[parseInt(filters.mes)]);
  lines.push('# Filtros ativos: '+(fParts.length?fParts.join(' | '):'Nenhum'));
  var tParts=[];
  if (u5)   tParts.push('< 5 anos: Ativo');
  if (fRep) tParts.push('Casos Repetidos: Ativo');
  if (fCx)  tParts.push('Demanda Espontânea: Ativo');
  if (tParts.length) lines.push('# Toggles: '+tParts.join(' | '));
  var t=computeCardTotals();
  lines.push('# Total de atendimentos no filtro: '+(t.atend||0));
  lines.push('#');
  return lines.join('\r\n')+'\r\n';
}
function buildCSVRows() {
  var rows=[];
  if (currentPage==='visao-geral') {
    rows.push(['Mês','Nome','Total','Menor5','Repetidos','Complexo'].join(';'));
    getMonthlyData().forEach(function(m){ rows.push([m.mes,MESES[m.mes-1],m.casos,m.menor5,m.repetidos,m.complexo].join(';')); });
  } else if (currentPage==='territorial') {
    var activeTab=document.querySelector('.tab-pane.active');
    var tabId=activeTab?activeTab.id:'tab-ubs';
    if (tabId==='tab-ubs') {
      rows.push(['UBS','Zona','Pop Total','Pop <5','Casos','Casos <5','Taxa/1000','Taxa <5/1000','Complexo','% Complexo'].join(';'));
      filteredUBS().forEach(function(u){
        rows.push([u.ubs,u.zona||'',u.pop_total||0,u.pop_menor5||0,u.casos_total||0,u.casos_menor5||0,
          fmtR(u.taxa_geral||0),fmtR(u.taxa_menor5||0),u.casos_complexo||0,fmtP(u.pct_complexo||0)].join(';'));
      });
    } else if (tabId==='tab-bairro') {
      rows.push(['Bairro','Pop Total','Pop <5','Casos','Casos <5','Taxa/1000','Taxa <5/1000'].join(';'));
      DATA.por_bairro.forEach(function(b){ rows.push([b.bairro,b.pop_total||0,b.pop_menor5||0,b.casos_total||0,b.casos_menor5||0,fmtR(b.taxa_geral||0),fmtR(b.taxa_menor5||0)].join(';')); });
    } else if (tabId==='tab-equipe') {
      rows.push(['Equipe','UBS','Pop Total','Pop <5','Casos','Casos <5','Taxa/1000','Taxa <5/1000'].join(';'));
      DATA.por_equipe.forEach(function(e){ rows.push([e.equipe,e.ubs,e.pop_total||0,e.pop_menor5||0,e.casos_total||0,e.casos_menor5||0,fmtR(e.taxa_geral||0),fmtR(e.taxa_menor5||0)].join(';')); });
    } else {
      rows.push(['UBS','Microárea','Casos <5','Total'].join(';'));
      (DATA.microareas_criticas||[]).forEach(function(m){ rows.push([m.ubs,m.microarea,m.casos_menor5||0,m.casos_total||0].join(';')); });
    }
  } else if (currentPage==='epidemiologico') {
    rows.push(['Faixa Etária','Casos','Masculino','Feminino','Complexo','Repetidos'].join(';'));
    getFaixaData().forEach(function(f){
      var fd=DATA.por_faixa_etaria.find(function(x){ return x.faixa===f.faixa; })||{};
      rows.push([f.faixa,f.casos||f.total||0,fd.masculino||0,fd.feminino||0,f.complexo||0,f.repetidos||0].join(';'));
    });
    rows.push('#');
    var s=getSexoData();
    rows.push(['Sexo','Casos','Casos <5'].join(';'));
    rows.push(['Masculino',s.masculino||0,s.masculino_menor5||0].join(';'));
    rows.push(['Feminino',s.feminino||0,s.feminino_menor5||0].join(';'));
    rows.push(['Não Informado',s.nao_informado||0,'—'].join(';'));
  } else if (currentPage==='mapa') {
    rows.push(['Bairro','Pop Total','Pop <5','Casos','Casos <5','Taxa/1000','Taxa <5/1000'].join(';'));
    Object.values(getFilteredBairros()).forEach(function(b){ rows.push([b.bairro,b.pop_total||0,b.pop_menor5||0,b.casos_total||0,b.casos_menor5||0,fmtR(b.taxa_geral||0),fmtR(b.taxa_menor5||0)].join(';')); });
  }
  return rows;
}
function exportCSV() {
  var header=buildCSVHeader();
  var rows=buildCSVRows();
  var csv=header+rows.join('\r\n');
  var blob=new Blob(['\\uFEFF'+csv],{type:'text/csv;charset=utf-8'});
  var url=URL.createObjectURL(blob);
  var a=document.createElement('a');
  a.href=url; a.download=buildCSVFilename();
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ─── TOOLTIPS DE METODOLOGIA ──────────────────────────────────────────────────
var METODOLOGIA = {
  'Total Atendimentos': 'Contagem de registros com CID A09 na Ficha de Atendimento Individual (FAI) do e-SUS APS, Jan–Dez 2025. Toggle "< 5 anos": exibe somente atendimentos de crianças <5 anos (idade na data da consulta). Toggle "Casos Repetidos": atendimentos de pacientes com ≥2 visitas no período.',
  'Pacientes Únicos': 'CPFs distintos entre todos os atendimentos A09 do período. Pacientes com múltiplos atendimentos são contados uma única vez. Fonte: linkagem CPF entre FAI e cadastro e-SUS.',
  'Atend. < 5 anos': 'Atendimentos A09 em crianças com idade <5 anos na data da consulta, calculada como (DATA_CONSULTA – DATA_NASCIMENTO) / 365,25. Registros sem data de nascimento não são incluídos.',
  'Pacientes < 5 anos': 'CPFs distintos de crianças <5 anos com pelo menos um atendimento A09 no período.',
  'Período': 'Período de análise. "Anual" = Jan–Dez 2025. Ao selecionar mês no filtro, exibe dados daquele mês.',
  'Zona Urbana': 'Soma de atendimentos A09 de UBS classificadas como zona urbana. Classificação rural/urbana definida manualmente pela localização geográfica das unidades.',
  'Zona Rural': 'Soma de atendimentos A09 de UBS classificadas como zona rural. Ver critério em "Zona Urbana".',
  'Masculino': 'Atendimentos A09 com campo SEXO = "M" na FAI. Hierarquia de fonte: filtro UBS → por_ubs_sexo; zona → agrega por_ubs_sexo; mês → serie_temporal_sexo; sem filtro → por_sexo global.',
  'Feminino': 'Atendimentos A09 com SEXO = "F" na FAI. Mesma hierarquia de fonte que "Masculino".',
  'Não Informado': 'Atendimentos sem campo SEXO preenchido ou com valor diferente de M/F na FAI.',
  'Demanda Esponânea (Complexo)': 'Atendimentos realizados em unidade cujo nome contém "COMPLEXO" (Complexo Regulador/UPA/PA), identificados pelo campo UNIDADE SAUDE da FAI. Indica busca por serviço de urgência em vez da UBS de referência.',
  'Com Vínculo APS': 'Atendimentos no Complexo de pacientes com cadastro ativo em alguma UBS da APS (linkagem CPF entre FAI e FCI).',
  'Sem Vínculo': 'Atendimentos no Complexo de pacientes sem cadastro localizado na APS.',
  'Pacientes Recorrentes': 'Pacientes com ≥2 atendimentos A09 no período (independente de UBS/mês). Calculado pela frequência de CPF nos registros A09.',
};

// ─── DROPDOWNS ────────────────────────────────────────────────────────────────
function populateFilters() {
  var ubsSel=document.getElementById('fUBS');
  var faixaSel=document.getElementById('fFaixa');
  var bairroSel=document.getElementById('fBairro');
  DATA.por_ubs.slice().sort(function(a,b){ return a.ubs<b.ubs?-1:1; }).forEach(function(u){
    var opt=document.createElement('option'); opt.value=u.ubs; opt.text=u.ubs; ubsSel.appendChild(opt);
  });
  ['<1a','1a','2-4a','5-9a','10-17a','18-29a','30-44a','45-59a','60+'].forEach(function(f){
    var opt=document.createElement('option'); opt.value=f; opt.text=f; faixaSel.appendChild(opt);
  });
  var bairros=[];
  DATA.por_bairro.forEach(function(b){ if (bairros.indexOf(b.bairro)===-1) bairros.push(b.bairro); });
  bairros.sort().forEach(function(b){ var opt=document.createElement('option'); opt.value=b; opt.text=b; bairroSel.appendChild(opt); });
  document.getElementById('fZona').addEventListener('change',function(){
    var z=this.value;
    Array.from(ubsSel.options).forEach(function(opt){
      if (!opt.value) return;
      var ubs=DATA.por_ubs.find(function(u){ return u.ubs===opt.value; });
      opt.style.display=(z&&ubs&&ubs.zona!==z)?'none':'';
    });
  });
}

function applyFilters() {
  filters.zona=document.getElementById('fZona').value;
  filters.ubs=document.getElementById('fUBS').value;
  filters.bairro=document.getElementById('fBairro').value;
  filters.faixa=document.getElementById('fFaixa').value;
  filters.sexo=document.getElementById('fSexo').value;
  filters.mes=document.getElementById('fMes').value;
  refreshAll();
}

function resetFilters() {
  ['fZona','fUBS','fBairro','fFaixa','fSexo','fMes'].forEach(function(id){ document.getElementById(id).value=''; });
  filters={zona:'',ubs:'',bairro:'',faixa:'',sexo:'',mes:''};
  refreshAll();
}

function updateFilterStatus() {
  var el=document.getElementById('filterStatus'); if (!el) return;
  var parts=[];
  if (filters.zona)   parts.push('Zona: '+filters.zona);
  if (filters.ubs)    parts.push('UBS: '+filters.ubs);
  if (filters.bairro) parts.push('Bairro: '+filters.bairro);
  if (filters.faixa)  parts.push('Faixa: '+filters.faixa);
  if (filters.sexo)   parts.push('Sexo: '+(filters.sexo==='M'?'Masculino':'Feminino'));
  if (filters.mes)    parts.push('Mês: '+MESES_F[parseInt(filters.mes)]);
  if (u5)   parts.push('< 5 anos ativo');
  if (fRep) parts.push('Repetidos ativo');
  if (fCx)  parts.push('Complexo ativo');
  if (parts.length) { el.textContent='Filtros: '+parts.join(' | '); el.style.display='block'; }
  else { el.textContent=''; el.style.display='none'; }
}

// ─── NAV ──────────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(function(item){
  item.addEventListener('click',function(){
    document.querySelectorAll('.nav-item').forEach(function(n){ n.classList.remove('active'); });
    document.querySelectorAll('.page').forEach(function(p){ p.classList.remove('active'); });
    this.classList.add('active');
    var pg=this.getAttribute('data-page');
    currentPage=pg;
    var pageEl=document.getElementById('page-'+pg);
    if (pageEl) pageEl.classList.add('active');
    if (pg==='mapa') initMap();
    refreshAll();
  });
});
document.querySelectorAll('.tab').forEach(function(tab){
  tab.addEventListener('click',function(){
    var pane=this.getAttribute('data-tab');
    document.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
    document.querySelectorAll('.tab-pane').forEach(function(p){ p.classList.remove('active'); });
    this.classList.add('active');
    var paneEl=document.getElementById(pane);
    if (paneEl) paneEl.classList.add('active');
  });
});
document.getElementById('fbrToggle').addEventListener('click',function(){
  document.getElementById('filterBar').classList.toggle('open');
});
document.getElementById('btnU5').addEventListener('click',function(){
  u5=!u5; this.classList.toggle('active',u5); refreshAll();
});
document.getElementById('btnRepetido').addEventListener('click',function(){
  fRep=!fRep;
  if (fRep){ fCx=false; document.getElementById('btnComplexo').classList.remove('active'); }
  this.classList.toggle('active',fRep); refreshAll();
});
document.getElementById('btnComplexo').addEventListener('click',function(){
  fCx=!fCx;
  if (fCx){ fRep=false; document.getElementById('btnRepetido').classList.remove('active'); }
  this.classList.toggle('active',fCx); refreshAll();
});

// ─── TOOLTIP DISPLAY ──────────────────────────────────────────────────────────
document.addEventListener('mouseover',function(e){
  var el=e.target.closest?e.target.closest('.minfo'):null;
  if (!el) return;
  var existing=document.getElementById('_dTip'); if (existing) existing.remove();
  var div=document.createElement('div'); div.id='_dTip';
  div.style.cssText='position:fixed;z-index:9999;max-width:340px;background:#1C2B3A;color:#fff;'+
    'font-size:11.5px;line-height:1.6;padding:10px 13px;border-radius:5px;pointer-events:none;'+
    'box-shadow:0 4px 16px rgba(0,0,0,0.28);font-family:Inter,sans-serif;';
  div.textContent=el.getAttribute('data-tip');
  document.body.appendChild(div);
  var rect=el.getBoundingClientRect();
  var top=rect.bottom+8; var left=rect.left;
  if (left+340>window.innerWidth) left=window.innerWidth-350;
  if (top+200>window.innerHeight) top=rect.top-210;
  div.style.top=top+'px'; div.style.left=left+'px';
});
document.addEventListener('mouseout',function(e){
  if (e.target.closest&&e.target.closest('.minfo')){ var t=document.getElementById('_dTip'); if(t) t.remove(); }
});

// ─── INIT ─────────────────────────────────────────────────────────────────────
populateFilters();
refreshAll();
"""

html_tail = """
</script>
</body>
</html>"""

# ─── ASSEMBLE ────────────────────────────────────────────────────────────────
print("Gerando index.html...")
with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_head)
    f.write(f'var DATA = {json_str};\n')
    f.write(f'var BAIRROS_GEO = {geojson_str};\n')
    f.write(js_code)
    f.write(html_tail)

size = OUT_HTML.stat().st_size
print(f"✓ index.html gerado: {size/1024:.0f} KB")
print("Pronto.")

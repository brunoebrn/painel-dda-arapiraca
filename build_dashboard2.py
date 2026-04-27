"""
build_dashboard2.py  — Painel DDA Arapiraca 2025
Gera painel_dda_arapiraca.html como arquivo único e autocontido.
"""
import json, os, shutil

DATA_FILE   = '/sessions/peaceful-nice-brown/dashboard_data_v3.json'
GEO_FILE    = '/sessions/peaceful-nice-brown/arapiraca_bairros.json'
OUT_NFC     = '/sessions/peaceful-nice-brown/painel_dda_arapiraca.html'
OUT_NFD_DIR = '/sessions/peaceful-nice-brown/mnt/An\u00e1lise A09'   # NFC \u00e1
# Also try NFD path
import unicodedata
OUT_NFD_DIR2 = '/sessions/peaceful-nice-brown/mnt/Ana\u0301lise A09'  # NFD a + combining accent

# ─── Inline local assets (CDN-free, works offline) ────────────────────────────
_BASE = '/sessions/peaceful-nice-brown'
with open(os.path.join(_BASE, 'chartjs_440.min.js'),  encoding='utf-8') as _f: _CHARTJS  = _f.read()
with open(os.path.join(_BASE, 'leaflet_194.min.js'),  encoding='utf-8') as _f: _LEAFLETJS = _f.read()
with open(os.path.join(_BASE, 'leaflet_194.min.css'), encoding='utf-8') as _f: _LEAFLETCSS = _f.read()

with open(DATA_FILE, encoding='utf-8') as f:
    data = json.load(f)
with open(GEO_FILE, encoding='utf-8') as f:
    geojson = json.load(f)

json_str    = json.dumps(data,    ensure_ascii=False, separators=(',',':'))
geojson_str = json.dumps(geojson, ensure_ascii=False, separators=(',',':'))

# ─────────────────────────────────────────────────────────────────────────────
# HTML HEAD — CSS + structure (plain string, no f-string)
# ─────────────────────────────────────────────────────────────────────────────
html_head = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Painel DDA \u2014 SMS Arapiraca 2025</title>
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
/* Header */
.hdr{position:fixed;top:0;left:0;right:0;height:68px;background:#fff;border-bottom:1px solid var(--border-subtle);
  display:flex;align-items:center;justify-content:space-between;padding:0 28px;z-index:200;
  box-shadow:0 1px 4px rgba(0,0,0,0.06)}
.hdr-left{flex:1}
.hdr-title{font-size:14px;font-weight:700;color:var(--brand);letter-spacing:.3px}
.hdr-sub{font-size:11px;color:var(--ink-muted);margin-top:1px}
.hdr-accent{height:3px;width:52px;background:var(--brand-acc);margin-top:3px;border-radius:2px}
.hdr-btns{display:flex;gap:8px;align-items:center}
/* Toggle buttons in header */
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
/* Layout */
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
/* Filter bar */
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
#filterStatus{font-size:11px;color:var(--brand);background:rgba(46,134,193,.07);
  padding:6px 10px;border-radius:3px;margin-top:8px;display:none}
/* Section title */
.sec-title{font-size:16px;font-weight:700;color:var(--ink-primary);
  margin-bottom:18px;border-bottom:2px solid var(--brand-acc);padding-bottom:8px}
/* Cards */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:12px;margin-bottom:22px}
.card{background:#fff;border:1px solid var(--border-subtle);border-radius:4px;padding:14px 16px;
  transition:all .15s;border-left:3px solid transparent}
.card:hover{box-shadow:0 2px 8px rgba(0,0,0,.05);border-color:var(--border-std)}
.card.cu5{border-left-color:#D4A017}
.card.ctog{border-left-color:#C0392B}
.card-lbl{font-size:10px;color:var(--ink-muted);text-transform:uppercase;font-weight:700;
  letter-spacing:.5px;margin-bottom:5px}
.card-val{font-size:26px;font-weight:700;color:var(--brand);margin-bottom:3px;line-height:1.1}
.card-meta{font-size:11px;color:var(--ink-secondary)}
/* Charts */
.chart-wrap{background:#fff;border:1px solid var(--border-subtle);border-radius:4px;
  padding:18px 18px 14px;margin-bottom:18px;position:relative}
.chart-wrap.h380{height:380px}
.chart-wrap.h460{height:460px}
.chart-wrap.h520{height:520px}
.chart-title{font-size:13px;font-weight:600;color:var(--ink-primary);margin-bottom:12px}
canvas{max-width:100%;max-height:100%}
/* Tabs */
.tabs{display:flex;border-bottom:1px solid var(--border-subtle);margin-bottom:18px;gap:0}
.tab{padding:9px 16px;cursor:pointer;border:none;background:none;
  font-size:12px;font-weight:600;color:var(--ink-secondary);
  border-bottom:2px solid transparent;font-family:'Inter',sans-serif}
.tab:hover{color:var(--ink-primary)}
.tab.active{color:#2E86C1;border-bottom-color:#2E86C1}
.tab-pane{display:none}
.tab-pane.active{display:block}
/* Tables */
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
/* Two-col layout */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px}
/* Map */
#leafletMap{height:580px;border-radius:4px;border:1px solid var(--border-subtle)}
/* Footer */
.footer{background:var(--surface-hover);border-top:1px solid var(--border-subtle);
  padding:18px 28px;margin-top:36px;font-size:10px;color:var(--ink-muted);text-align:center;line-height:1.7}
/* Responsive */
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
    <div class="hdr-title">Secretaria Municipal de Sa\u00fade de Arapiraca</div>
    <div class="hdr-sub">Painel Epidemiol\u00f3gico \u2014 Doen\u00e7a Diarreica Aguda (CID A09) \u2014 Arapiraca/AL \u2014 2025</div>
    <div class="hdr-accent"></div>
  </div>
  <div class="hdr-btns">
    <button class="tbtn tbtn-u5" id="btnU5">&lt; 5 anos</button>
    <button class="tbtn tbtn-rep" id="btnRepetido">\u21ba Casos Repetidos</button>
    <button class="tbtn tbtn-cx" id="btnComplexo">🏥 Demanda Espon.</button>
  </div>
</header>

<div class="main">
  <aside class="sidebar">
    <div class="nav-item active" data-page="visao-geral">Vis\u00e3o Geral</div>
    <div class="nav-item" data-page="territorial">An\u00e1lise Territorial</div>
    <div class="nav-item" data-page="epidemiologico">Perfil Epidemiol\u00f3gico</div>
    <div class="nav-item" data-page="mapa">Mapa Territorial</div>
  </aside>

  <main class="content">

    <!-- Filter bar (shared across pages) -->
    <button class="fbr-toggle" id="fbrToggle">\u2699\ufe0f Filtros Avan\u00e7ados</button>
    <div class="fbr" id="filterBar">
      <div class="fbr-grid">
        <div class="fg"><label>Zona</label>
          <select id="fZona"><option value="">Todas</option><option value="URBANA">Urbana</option><option value="RURAL">Rural</option></select></div>
        <div class="fg"><label>UBS</label>
          <select id="fUBS"><option value="">Todas as UBS</option></select></div>
        <div class="fg"><label>Bairro</label>
          <select id="fBairro"><option value="">Todos os bairros</option></select></div>
        <div class="fg"><label>Faixa Et\u00e1ria</label>
          <select id="fFaixa"><option value="">Todas</option></select></div>
        <div class="fg"><label>Sexo</label>
          <select id="fSexo"><option value="">Todos</option><option value="M">Masculino</option><option value="F">Feminino</option></select></div>
        <div class="fg"><label>M\u00eas</label>
          <select id="fMes">
            <option value="">Todos</option><option value="1">Janeiro</option><option value="2">Fevereiro</option>
            <option value="3">Mar\u00e7o</option><option value="4">Abril</option><option value="5">Maio</option>
            <option value="6">Junho</option><option value="7">Julho</option><option value="8">Agosto</option>
            <option value="9">Setembro</option><option value="10">Outubro</option><option value="11">Novembro</option>
            <option value="12">Dezembro</option>
          </select></div>
      </div>
      <div class="fbr-btns">
        <button class="fbtn" onclick="applyFilters()">Aplicar</button>
        <button class="fbtn reset" onclick="resetFilters()">Limpar</button>
      </div>
      <div id="filterStatus"></div>
    </div>

    <!-- PAGE: Vis\u00e3o Geral -->
    <div class="page active" id="page-visao-geral">
      <h2 class="sec-title">Vis\u00e3o Geral \u2014 Doen\u00e7a Diarreica Aguda</h2>
      <div class="cards" id="mainCards"></div>
      <div class="two-col">
        <div class="chart-wrap h380">
          <div class="chart-title">S\u00e9rie Temporal \u2014 Atendimentos Mensais</div>
          <canvas id="cTemporal"></canvas>
        </div>
        <div class="chart-wrap h380">
          <div class="chart-title">Distribui\u00e7\u00e3o por Faixa Et\u00e1ria</div>
          <canvas id="cFaixa"></canvas>
        </div>
      </div>
      <div class="cards" id="zonaCards"></div>
    </div>

    <!-- PAGE: An\u00e1lise Territorial -->
    <div class="page" id="page-territorial">
      <h2 class="sec-title">An\u00e1lise Territorial</h2>
      <div class="tabs">
        <button class="tab active" data-tab="tab-ubs">UBS</button>
        <button class="tab" data-tab="tab-bairro">Bairros</button>
        <button class="tab" data-tab="tab-equipe">Equipes</button>
        <button class="tab" data-tab="tab-micro">Micro\u00e1reas</button>
      </div>
      <div class="tab-pane active" id="tab-ubs">
        <div class="chart-wrap h520"><div class="chart-title">Top 15 UBS por Casos</div><canvas id="cUBSTop"></canvas></div>
        <div class="tbl-wrap"><table id="tUBS"><thead><tr>
          <th>UBS</th><th>Zona</th><th class="tn">Popula\u00e7\u00e3o</th><th class="tn">Pop &lt;5</th>
          <th class="tn">Casos</th><th class="tn">Casos &lt;5</th><th class="tn">Taxa/1.000</th>
          <th class="tn">Taxa &lt;5</th><th class="tn">Complexo</th><th class="tn">% Compl.</th>
        </tr></thead><tbody></tbody></table></div>
      </div>
      <div class="tab-pane" id="tab-bairro">
        <div class="tbl-wrap"><table id="tBairro"><thead><tr>
          <th>Bairro</th><th class="tn">Pop</th><th class="tn">Pop &lt;5</th>
          <th class="tn">Casos</th><th class="tn">Casos &lt;5</th><th class="tn">Taxa/1.000</th><th class="tn">Taxa &lt;5</th>
        </tr></thead><tbody></tbody></table></div>
      </div>
      <div class="tab-pane" id="tab-equipe">
        <div class="tbl-wrap"><table id="tEquipe"><thead><tr>
          <th>Equipe</th><th>UBS</th><th class="tn">Pop</th><th class="tn">Pop &lt;5</th>
          <th class="tn">Casos</th><th class="tn">Casos &lt;5</th><th class="tn">Taxa/1.000</th><th class="tn">Taxa &lt;5</th>
        </tr></thead><tbody></tbody></table></div>
      </div>
      <div class="tab-pane" id="tab-micro">
        <div class="tbl-wrap"><table id="tMicro"><thead><tr>
          <th>UBS</th><th>Micro\u00e1rea</th><th class="tn">Casos &lt;5</th><th class="tn">Total</th>
        </tr></thead><tbody></tbody></table></div>
      </div>
    </div>

    <!-- PAGE: Perfil Epidemiol\u00f3gico -->
    <div class="page" id="page-epidemiologico">
      <h2 class="sec-title">Perfil Epidemiol\u00f3gico</h2>
      <div class="cards" id="epiCards"></div>
      <div class="two-col">
        <div class="chart-wrap h380"><div class="chart-title">Distribui\u00e7\u00e3o por Faixa Et\u00e1ria (Pir\u00e2mide)</div><canvas id="cPiramide"></canvas></div>
        <div class="chart-wrap h380"><div class="chart-title">Distribui\u00e7\u00e3o por Sexo</div><canvas id="cSexo"></canvas></div>
      </div>
      <div class="chart-wrap h460"><div class="chart-title">Principais CIDs Registrados (Top 15)</div><canvas id="cCIDs"></canvas></div>
      <div class="chart-wrap h380"><div class="chart-title">Recorr\u00eancia de Atendimentos por Paciente</div><canvas id="cRecorrencia"></canvas></div>
      <h3 style="font-size:14px;font-weight:700;color:var(--ink-primary);margin:22px 0 14px;border-left:3px solid var(--danger);padding-left:10px">
        Demanda Espon\u00e2nea (Complexo) \u2014 An\u00e1lise Anual
      </h3>
      <div class="cards" id="complexoCards"></div>
      <div class="chart-wrap h520"><div class="chart-title">UBS de Origem \u2014 Pacientes no Complexo (Top 15)</div><canvas id="cComplexoUBS"></canvas></div>
      <div class="tbl-wrap"><table id="tEvasao"><thead><tr>
        <th>UBS</th><th class="tn">Total Casos</th><th class="tn">No Complexo</th><th class="tn">Taxa Evas\u00e3o</th>
      </tr></thead><tbody></tbody></table></div>
    </div>

    <!-- PAGE: Mapa -->
    <div class="page" id="page-mapa">
      <h2 class="sec-title">Mapa Territorial \u2014 Incid\u00eancia por Bairro</h2>
      <p style="font-size:12px;color:var(--ink-secondary);margin-bottom:12px">
        Choropleth por taxa de incid\u00eancia/1.000 hab. Passe o mouse ou clique para detalhes.
        Bairros sem dados populacionais exibem n\u00famero absoluto de casos.
      </p>
      <div id="leafletMap"></div>
    </div>

    <footer class="footer">
      Secretaria Municipal de Sa\u00fade de Arapiraca &mdash; Vigil\u00e2ncia em Sa\u00fade<br>
      Fonte: e-SUS APS &mdash; Ficha de Atendimento Individual &mdash; Per\u00edodo: Jan&ndash;Dez 2025<br>
      Dados anonimizados conforme LGPD (Lei 13.709/2018). Agrega\u00e7\u00f5es com n&lt;5 suprimidas.
    </footer>
  </main>
</div>

<script>
"""

# ─────────────────────────────────────────────────────────────────────────────
# JS (plain string — no f-string, curly braces are literal)
# ─────────────────────────────────────────────────────────────────────────────
js_code = """
// ─── CONSTANTS ────────────────────────────────────────────────────────────────
var C = {
  blue:'#2E86C1', navy:'#1B4F72', gold:'#D4A017', red:'#C0392B', warn:'#D4770B', ok:'#1E8449',
  blueA:'rgba(46,134,193,0.75)', goldA:'rgba(212,160,23,0.75)',
  redA:'rgba(192,57,43,0.75)', grayA:'rgba(189,195,199,0.4)',
  fp:['#1B4F72','#2471A3','#2E86C1','#5DADE2','#85C1E9','#D4A017','#E6B02E','#F1C452','#F5CD79']
};
var MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
var MESES_F = ['','Janeiro','Fevereiro','Mar\u00e7o','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

// ─── STATE ────────────────────────────────────────────────────────────────────
var charts = {};
var sortSt = {};
var leafletMap = null;
var u5 = false, fRep = false, fCx = false;
var filters = { zona:'', ubs:'', bairro:'', faixa:'', sexo:'', mes:'' };

// ─── FORMAT HELPERS ────────────────────────────────────────────────────────────
function fmt(n) {
  if (n === null || n === undefined || (typeof n === 'number' && isNaN(n))) return '\u2014';
  return Number(n).toLocaleString('pt-BR');
}
function fmtR(n, d) {
  if (n === null || n === undefined || (typeof n === 'number' && isNaN(n))) return '\u2014';
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
  // Returns serie_temporal_ubs filtered by current ubs/zona
  var list = DATA.serie_temporal_ubs;
  if (filters.ubs) list = list.filter(function(x){ return x.ubs === filters.ubs; });
  if (filters.zona) {
    var ubsZ = DATA.por_ubs.filter(function(u){ return u.zona === filters.zona; }).map(function(u){ return u.ubs; });
    list = list.filter(function(x){ return ubsZ.indexOf(x.ubs) !== -1; });
  }
  return list;
}

function getMonthlyData() {
  // Returns array[12] aggregated according to current filters
  var byM = {};
  for (var m = 1; m <= 12; m++) {
    byM[m] = { mes:m, casos:0, menor5:0, repetidos:0, complexo:0, pacientes:0, pac5:0, menor5_repetidos:0, menor5_complexo:0 };
  }
  var hasUBS = filters.ubs || filters.zona;
  var hasBairro = filters.bairro;
  var hasFaixa  = filters.faixa;
  var hasSexo   = filters.sexo;

  if (hasUBS) {
    filteredSTUBS().forEach(function(x) {
      var r = byM[x.mes]; if (!r) return;
      r.casos += x.casos||0; r.menor5 += x.menor5||0;
      r.repetidos += x.repetidos||0; r.complexo += x.complexo||0;
    });
  } else if (hasBairro) {
    DATA.serie_temporal_bairro.filter(function(x){ return x.bairro === hasBairro; }).forEach(function(x) {
      var r = byM[x.mes]; if (!r) return;
      r.casos += x.casos||0; r.menor5 += x.menor5||0;
      r.repetidos += x.repetidos||0; r.complexo += x.complexo||0;
    });
  } else if (hasFaixa) {
    DATA.serie_temporal_faixa.filter(function(x){ return x.faixa === hasFaixa; }).forEach(function(x) {
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
  // Returns {atend, menor5, pacientes, pac5}
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var hasUBS   = filters.ubs || filters.zona;
  var hasBairro = filters.bairro;
  var hasFaixa  = filters.faixa;
  var hasSexo   = filters.sexo;
  var atend = 0, menor5 = 0, pac = null, pac5 = null;

  if (mesN) {
    var md = getMonthlyData();
    var mr = md.find(function(x){ return x.mes === mesN; }) || {};
    atend  = fRep ? (mr.repetidos||0) : fCx ? (mr.complexo||0) : (mr.casos||0);
    menor5 = fRep ? (mr.menor5_repetidos||mr.menor5||0) : fCx ? (mr.menor5_complexo||mr.menor5||0) : (mr.menor5||0);
    pac    = (mr.pacientes && !hasUBS && !hasBairro && !hasFaixa) ? mr.pacientes : null;
    pac5   = (mr.pac5 && !hasUBS && !hasBairro && !hasFaixa) ? mr.pac5 : null;
  } else if (hasUBS) {
    var ubsF = filteredUBS();
    atend  = ubsF.reduce(function(s,u){ return s+(fRep?u.casos_repetidos:fCx?u.casos_complexo:u.casos_total)||0; },0);
    menor5 = ubsF.reduce(function(s,u){ return s+(u.casos_menor5||0); },0);
    pac    = ubsF.reduce(function(s,u){ return s+(u.pacientes_total||0); },0);
    pac5   = ubsF.reduce(function(s,u){ return s+(u.pacientes_menor5||0); },0);
  } else if (hasBairro) {
    var br = DATA.por_bairro.find(function(b){ return b.bairro === hasBairro; }) || {};
    atend  = fRep ? (br.repetidos||0) : fCx ? (br.complexo||0) : (br.casos_total||0);
    menor5 = br.casos_menor5||0;
  } else if (hasFaixa) {
    var fr = DATA.por_faixa_etaria.find(function(f){ return f.faixa === hasFaixa; }) || {};
    atend  = fRep ? (fr.repetidos||0) : fCx ? (fr.complexo||0) : (fr.casos||0);
    var u5f = ['<1a','1a','2-4a'].indexOf(hasFaixa) !== -1;
    menor5 = u5f ? atend : 0;
  } else if (hasSexo) {
    var s = DATA.por_sexo;
    var sk = hasSexo === 'M' ? 'masculino' : 'feminino';
    atend  = s[sk]||0;
    menor5 = s[sk + '_menor5']||0;
  } else {
    var m = DATA.metadata;
    atend  = fRep ? m.total_repetidos  : fCx ? m.total_complexo  : m.total_atendimentos;
    menor5 = fRep ? (m.menor5_repetidos||m.total_menor5) : fCx ? (m.menor5_complexo||m.total_menor5) : m.total_menor5;
    pac    = fRep ? m.pacientes_repetidos : fCx ? m.pacientes_complexo : m.total_pacientes;
    pac5   = fRep ? (m.pac5_repetidos||m.pacientes_menor5) : fCx ? (m.pac5_complexo||m.pacientes_menor5) : m.pacientes_menor5;
  }

  if (u5) { atend = menor5; pac = pac5; }
  return { atend:atend, menor5:menor5, pacientes:pac, pac5:pac5 };
}

// ─── REFRESH ──────────────────────────────────────────────────────────────────
function refreshAll() {
  updateFilterStatus();
  renderMainCards();
  renderZonaCards();
  rebuildCharts();
  buildTables();
}

// ─── CARDS ────────────────────────────────────────────────────────────────────
function renderMainCards() {
  var t = computeCardTotals();
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var periodo = mesN ? MESES_F[mesN] + ' 2025' : 'Jan \u2013 Dez 2025';
  var toggleMeta = fRep ? 'Pacientes recorrentes' : fCx ? 'Demanda espon.' : u5 ? 'Filtro < 5 anos' : '';
  var tot4pct = DATA.metadata.total_atendimentos || 1;
  var pct5 = (t.atend > 0 && !u5) ? fmtP((t.menor5/t.atend)*100) + ' do total' : '';

  var items = [
    { lbl:'Total Atendimentos', val:fmt(t.atend||0), meta:toggleMeta, cls:(fRep||fCx)?'ctog':u5?'cu5':'' },
    { lbl:'Pacientes \u00danicos',    val:t.pacientes!==null?fmt(t.pacientes):'\u2014', meta:'Indiv\u00edduos distintos', cls:(fRep||fCx)?'ctog':u5?'cu5':'' },
    { lbl:'Atend. < 5 anos',    val:fmt(t.menor5||0), meta:pct5, cls:'' },
    { lbl:'Pacientes < 5 anos', val:t.pac5!==null?fmt(t.pac5):'\u2014', meta:'Crian\u00e7as afetadas', cls:'' },
    { lbl:'Per\u00edodo',           val:periodo, meta:mesN?'M\u00eas selecionado':'Anual', cls:'' }
  ];

  document.getElementById('mainCards').innerHTML = items.map(function(it) {
    return '<div class="card' + (it.cls ? ' ' + it.cls : '') + '">' +
      '<div class="card-lbl">' + it.lbl + '</div>' +
      '<div class="card-val">' + it.val + '</div>' +
      '<div class="card-meta">' + it.meta + '</div></div>';
  }).join('');
}

function renderZonaCards() {
  var ubsAll = filteredUBS();
  var field = fRep ? 'casos_repetidos' : fCx ? 'casos_complexo' : u5 ? 'casos_menor5' : 'casos_total';
  var rural  = ubsAll.filter(function(u){ return u.zona==='RURAL'; }).reduce(function(s,u){ return s+(u[field]||0); },0);
  var urbana = ubsAll.filter(function(u){ return u.zona==='URBANA'; }).reduce(function(s,u){ return s+(u[field]||0); },0);
  var tot = (rural+urbana)||1;
  document.getElementById('zonaCards').innerHTML =
    '<div class="card"><div class="card-lbl">Zona Urbana</div><div class="card-val">' + fmt(urbana) + '</div>' +
    '<div class="card-meta">' + fmtP(urbana/tot*100) + ' do total</div></div>' +
    '<div class="card"><div class="card-lbl">Zona Rural</div><div class="card-val">' + fmt(rural) + '</div>' +
    '<div class="card-meta">' + fmtP(rural/tot*100) + ' do total</div></div>';
}

function renderEpiCards() {
  var s = DATA.por_sexo;
  var tot = (s.masculino+s.feminino+s.nao_informado)||1;
  document.getElementById('epiCards').innerHTML =
    '<div class="card"><div class="card-lbl">Masculino</div><div class="card-val">' + fmt(s.masculino) + '</div>' +
    '<div class="card-meta">' + fmtP(s.masculino/tot*100) + '</div></div>' +
    '<div class="card"><div class="card-lbl">Feminino</div><div class="card-val">' + fmt(s.feminino) + '</div>' +
    '<div class="card-meta">' + fmtP(s.feminino/tot*100) + '</div></div>' +
    '<div class="card"><div class="card-lbl">N\u00e3o Informado</div><div class="card-val">' + fmt(s.nao_informado) + '</div>' +
    '<div class="card-meta">' + fmtP(s.nao_informado/tot*100) + '</div></div>';
  var cx = DATA.complexo;
  var metaTot = DATA.metadata.total_atendimentos||1;
  var tot2 = cx.total_atendimentos||1;
  document.getElementById('complexoCards').innerHTML =
    '<div class="card ctog"><div class="card-lbl">Demanda Espon\u00e2nea (Complexo)</div>' +
    '<div class="card-val">' + fmt(cx.total_atendimentos) + '</div>' +
    '<div class="card-meta">' + fmtP(cx.total_atendimentos/metaTot*100) + ' do total</div></div>' +
    '<div class="card"><div class="card-lbl">Com V\u00ednculo APS</div>' +
    '<div class="card-val">' + fmt(cx.com_vinculo||0) + '</div>' +
    '<div class="card-meta">' + fmtP((cx.com_vinculo||0)/tot2*100) + ' da demanda</div></div>' +
    '<div class="card"><div class="card-lbl">Sem V\u00ednculo</div>' +
    '<div class="card-val">' + fmt(cx.sem_vinculo||0) + '</div>' +
    '<div class="card-meta">' + fmtP((cx.sem_vinculo||0)/tot2*100) + ' da demanda</div></div>' +
    '<div class="card cu5"><div class="card-lbl">Pacientes Recorrentes</div>' +
    '<div class="card-val">' + fmt(DATA.metadata.total_repetidos||0) + '</div>' +
    '<div class="card-meta">atend. de pacientes com \u22652 visitas</div></div>';
}

// ─── CHARTS ────────────────────────────────────────────────────────────────────
function destroyCharts() {
  Object.keys(charts).forEach(function(k){ try{charts[k].destroy();}catch(e){} });
  charts = {};
}

function rebuildCharts() {
  destroyCharts();
  chartTemporal();
  chartFaixa();
  chartUBSTop();
  chartPiramide();
  chartSexo();
  chartCIDs();
  chartRecorrencia();
  chartComplexoUBS();
}

function barColor(idx) {
  if (fRep) return C.goldA;
  if (fCx)  return C.redA;
  if (u5)   return C.goldA;
  return C.blueA;
}

function chartTemporal() {
  var monthly = getMonthlyData();
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var vals = monthly.map(function(x){
    return fRep ? x.repetidos : fCx ? x.complexo : u5 ? x.menor5 : x.casos;
  });
  var bg = monthly.map(function(x){
    if (mesN && x.mes !== mesN) return C.grayA;
    return barColor();
  });
  var lbl = fRep ? 'Casos Repetidos' : fCx ? 'Demanda Espon.' : u5 ? 'Atend. < 5 anos' : 'Total Atendimentos';
  charts.cTemporal = new Chart(document.getElementById('cTemporal'), {
    type:'bar',
    data:{ labels:MESES, datasets:[{ label:lbl, data:vals, backgroundColor:bg }] },
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{position:'top'} }, scales:{ y:{beginAtZero:true} } }
  });
}

function chartFaixa() {
  var faixas = ['<1a','1a','2-4a','5-9a','10-17a','18-29a','30-44a','45-59a','60+'];
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var vals;
  if (mesN) {
    var byF = {};
    DATA.serie_temporal_faixa.filter(function(x){ return x.mes===mesN; }).forEach(function(x){ byF[x.faixa]=x; });
    vals = faixas.map(function(f){ var r=byF[f]||{}; return fRep?(r.repetidos||0):fCx?(r.complexo||0):(r.casos||0); });
  } else {
    var byF = {};
    DATA.por_faixa_etaria.forEach(function(x){ byF[x.faixa]=x; });
    vals = faixas.map(function(f){ var r=byF[f]||{}; return fRep?(r.repetidos||0):fCx?(r.complexo||0):u5?0:(r.casos||0); });
  }
  charts.cFaixa = new Chart(document.getElementById('cFaixa'), {
    type:'bar',
    data:{ labels:faixas, datasets:[{ label:fRep?'Repetidos':fCx?'Complexo':'Casos',
      data:vals, backgroundColor:barColor(), borderRadius:3 }] },
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{display:false} }, scales:{ y:{beginAtZero:true} } }
  });
}

function chartUBSTop() {
  var ubsList = filteredUBS().slice();
  var field = fRep ? 'casos_repetidos' : fCx ? 'casos_complexo' : u5 ? 'casos_menor5' : 'casos_total';
  ubsList.sort(function(a,b){ return (b[field]||0)-(a[field]||0); });
  var top = ubsList.slice(0,15);
  charts.cUBSTop = new Chart(document.getElementById('cUBSTop'), {
    type:'bar',
    data:{ labels:top.map(function(u){ return u.ubs; }),
      datasets:[{ label:fRep?'Repetidos':fCx?'Complexo':u5?'< 5 anos':'Casos',
        data:top.map(function(u){ return u[field]||0; }), backgroundColor:barColor() }] },
    options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{position:'top'} }, scales:{ x:{beginAtZero:true} } }
  });
}

function chartPiramide() {
  var faixas = ['<1a','1a','2-4a','5-9a','10-17a','18-29a','30-44a','45-59a','60+'];
  var byF = {}; DATA.por_faixa_etaria.forEach(function(x){ byF[x.faixa]=x.casos; });
  charts.cPiramide = new Chart(document.getElementById('cPiramide'), {
    type:'bar',
    data:{ labels:faixas, datasets:[{ label:'Casos', data:faixas.map(function(f){ return byF[f]||0; }),
      backgroundColor:C.fp, borderRadius:3 }] },
    options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{display:false} }, scales:{ x:{beginAtZero:true} } }
  });
}

function chartSexo() {
  var s = DATA.por_sexo;
  charts.cSexo = new Chart(document.getElementById('cSexo'), {
    type:'doughnut',
    data:{ labels:['Masculino','Feminino','N\u00e3o Informado'],
      datasets:[{ data:[s.masculino,s.feminino,s.nao_informado],
        backgroundColor:['#2E86C1','#D4A017','#BDC3C7'] }] },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{position:'right'} } }
  });
}

function chartCIDs() {
  var cids = (DATA.cids_combinados||[]).slice(0,15);
  if (!cids.length) return;
  charts.cCIDs = new Chart(document.getElementById('cCIDs'), {
    type:'bar',
    data:{ labels:cids.map(function(c){ return c.cid_combinado||c.cid||'?'; }),
      datasets:[{ label:'Registros', data:cids.map(function(c){ return c.total||c.casos||0; }),
        backgroundColor:C.blueA }] },
    options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{display:false} }, scales:{ x:{beginAtZero:true} } }
  });
}

function chartRecorrencia() {
  var r = DATA.recorrencia.geral;
  charts.cRecorrencia = new Chart(document.getElementById('cRecorrencia'), {
    type:'bar',
    data:{ labels:['1 atendimento','2 atendimentos','3 ou mais'],
      datasets:[{ label:'Pacientes',
        data:[r['1_atend'],r['2_atend'],r['3_mais']],
        backgroundColor:[C.blueA,C.goldA,C.redA] }] },
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{display:false} }, scales:{ y:{beginAtZero:true} } }
  });
}

function chartComplexoUBS() {
  var top = (DATA.complexo.ubs_origem||[]).slice(0,15);
  charts.cComplexoUBS = new Chart(document.getElementById('cComplexoUBS'), {
    type:'bar',
    data:{ labels:top.map(function(u){ return u.ubs; }),
      datasets:[{ label:'Casos no Complexo',
        data:top.map(function(u){ return u.casos; }), backgroundColor:C.redA }] },
    options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{display:false} }, scales:{ x:{beginAtZero:true} } }
  });
}

// ─── TABLES ─────────────────────────────────────────────────────────────────
function buildTables() {
  buildUBSTable();
  buildBairroTable();
  buildEquipeTable();
  buildMicroTable();
  buildEvasaoTable();
}

function buildUBSTable() {
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var rows;
  if (mesN) {
    var stubs = filteredSTUBS().filter(function(x){ return x.mes===mesN; });
    var ubsPop = {};
    DATA.por_ubs.forEach(function(u){ ubsPop[u.ubs]=u; });
    rows = stubs.map(function(x) {
      var p = ubsPop[x.ubs]||{};
      var casos = x.casos||0;
      return {
        ubs:x.ubs, zona:p.zona||'',
        pop_total:p.pop_total||0, pop_menor5:p.pop_menor5||0,
        casos_total:casos, casos_menor5:x.menor5||0,
        casos_repetidos:x.repetidos||0, casos_complexo:x.complexo||0,
        pct_complexo: casos>0 ? Math.round((x.complexo||0)/casos*1000)/10 : 0,
        taxa_geral: (p.pop_total||0)>0 ? Math.round(casos/(p.pop_total||1)*10000)/10 : 0,
        taxa_menor5: (p.pop_menor5||0)>0 ? Math.round((x.menor5||0)/(p.pop_menor5||1)*10000)/10 : 0
      };
    });
  } else {
    rows = filteredUBS();
  }
  var field = fRep?'casos_repetidos':fCx?'casos_complexo':u5?'casos_menor5':'casos_total';
  rows = rows.slice().sort(function(a,b){ return (b[field]||0)-(a[field]||0); });
  var tbody = document.querySelector('#tUBS tbody');
  tbody.innerHTML = rows.map(function(u) {
    var cd = fRep?(u.casos_repetidos||0):fCx?(u.casos_complexo||0):u5?(u.casos_menor5||0):(u.casos_total||0);
    var pctC = u.pct_complexo||0;
    var aCls = pctC>=40?'adanger':pctC>=20?'awarn':'';
    return '<tr><td>' + u.ubs + '</td><td>' + (u.zona||'') + '</td>' +
      '<td class="tn">' + fmt(u.pop_total) + '</td>' +
      '<td class="tn">' + fmt(u.pop_menor5) + '</td>' +
      '<td class="tn"><strong>' + fmt(cd) + '</strong></td>' +
      '<td class="tn">' + fmt(u.casos_menor5||0) + '</td>' +
      '<td class="tn">' + fmtR(u.taxa_geral) + '</td>' +
      '<td class="tn">' + fmtR(u.taxa_menor5) + '</td>' +
      '<td class="tn">' + fmt(u.casos_complexo||0) + '</td>' +
      '<td class="tn ' + aCls + '">' + fmtP(pctC) + '</td></tr>';
  }).join('');
}

function buildBairroTable() {
  var mesN = filters.mes ? parseInt(filters.mes) : null;
  var rows;
  if (mesN) {
    var byB = {};
    DATA.serie_temporal_bairro.filter(function(x){ return x.mes===mesN; }).forEach(function(x) {
      if (!byB[x.bairro]) byB[x.bairro]={bairro:x.bairro,casos_total:0,casos_menor5:0,repetidos:0,complexo:0};
      var r=byB[x.bairro];
      r.casos_total+=x.casos||0; r.casos_menor5+=x.menor5||0;
      r.repetidos+=x.repetidos||0; r.complexo+=x.complexo||0;
    });
    var bPop = {}; DATA.por_bairro.forEach(function(b){ bPop[b.bairro]=b; });
    rows = Object.values(byB).map(function(r) {
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
  } else {
    rows = DATA.por_bairro;
  }
  var field = fRep?'repetidos':fCx?'complexo':u5?'casos_menor5':'casos_total';
  rows = rows.slice().sort(function(a,b){ return (b[field]||0)-(a[field]||0); });
  var tbody = document.querySelector('#tBairro tbody');
  tbody.innerHTML = rows.map(function(b) {
    var cd = fRep?(b.repetidos||0):fCx?(b.complexo||0):u5?(b.casos_menor5||0):(b.casos_total||0);
    return '<tr><td>' + b.bairro + '</td>' +
      '<td class="tn">' + fmt(b.pop_total||0) + '</td>' +
      '<td class="tn">' + fmt(b.pop_menor5||0) + '</td>' +
      '<td class="tn"><strong>' + fmt(cd) + '</strong></td>' +
      '<td class="tn">' + fmt(b.casos_menor5||0) + '</td>' +
      '<td class="tn">' + fmtR(b.taxa_geral||0) + '</td>' +
      '<td class="tn">' + fmtR(b.taxa_menor5||0) + '</td></tr>';
  }).join('');
}

function buildEquipeTable() {
  var list = DATA.por_equipe||[];
  if (filters.zona) {
    var ubsZ=DATA.por_ubs.filter(function(u){ return u.zona===filters.zona; }).map(function(u){ return u.ubs; });
    list=list.filter(function(e){ return ubsZ.indexOf(e.ubs)!==-1; });
  }
  if (filters.ubs) list=list.filter(function(e){ return e.ubs===filters.ubs; });
  var field=fRep?'repetidos':fCx?'complexo':u5?'casos_menor5':'casos_total';
  list=list.slice().sort(function(a,b){ return (b[field]||0)-(a[field]||0); });
  var tbody=document.querySelector('#tEquipe tbody');
  tbody.innerHTML=list.slice(0,60).map(function(e) {
    var cd=fRep?(e.repetidos||0):fCx?(e.complexo||0):u5?(e.casos_menor5||0):(e.casos_total||0);
    return '<tr><td>' + e.equipe + '</td><td>' + e.ubs + '</td>' +
      '<td class="tn">' + fmt(e.pop_total||0) + '</td>' +
      '<td class="tn">' + fmt(e.pop_menor5||0) + '</td>' +
      '<td class="tn"><strong>' + fmt(cd) + '</strong></td>' +
      '<td class="tn">' + fmt(e.casos_menor5||0) + '</td>' +
      '<td class="tn">' + fmtR(e.taxa_geral||0) + '</td>' +
      '<td class="tn">' + fmtR(e.taxa_menor5||0) + '</td></tr>';
  }).join('');
}

function buildMicroTable() {
  var list=DATA.microareas_criticas||[];
  if (filters.ubs) list=list.filter(function(m){ return m.ubs===filters.ubs; });
  list=list.slice().sort(function(a,b){ return (b.casos_menor5||0)-(a.casos_menor5||0); });
  var tbody=document.querySelector('#tMicro tbody');
  tbody.innerHTML=list.slice(0,60).map(function(m) {
    return '<tr><td>' + m.ubs + '</td><td>' + m.microarea + '</td>' +
      '<td class="tn">' + fmt(m.casos_menor5||0) + '</td>' +
      '<td class="tn">' + fmt(m.total||0) + '</td></tr>';
  }).join('');
}

function buildEvasaoTable() {
  var list=DATA.evasao_complexo||[];
  if (filters.ubs) list=list.filter(function(e){ return e.ubs===filters.ubs; });
  list=list.slice().sort(function(a,b){ return (b.taxa_evasao||0)-(a.taxa_evasao||0); });
  var tbody=document.querySelector('#tEvasao tbody');
  tbody.innerHTML=list.map(function(e) {
    var aCls=e.taxa_evasao>=40?'adanger':e.taxa_evasao>=20?'awarn':'aok';
    return '<tr><td>' + e.ubs + '</td>' +
      '<td class="tn">' + fmt(e.total_casos||0) + '</td>' +
      '<td class="tn">' + fmt(e.no_complexo||0) + '</td>' +
      '<td class="tn ' + aCls + '">' + fmtP(e.taxa_evasao||0) + '</td></tr>';
  }).join('');
}

// ─── MAP ──────────────────────────────────────────────────────────────────────
function initMap() {
  if (leafletMap) { leafletMap.invalidateSize(); return; }
  var mapEl = document.getElementById('leafletMap');
  if (!mapEl) return;

  leafletMap = L.map('leafletMap').setView([-9.752, -36.661], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom:18
  }).addTo(leafletMap);

  // Build lookup by uppercase bairro name
  var bLookup = {};
  DATA.por_bairro.forEach(function(b) { bLookup[b.bairro] = b; });

  // Color scale: light (#EAF3FB) → dark navy (#1B4F72)
  var taxaVals = DATA.por_bairro.filter(function(b){ return (b.taxa_geral||0) > 0; }).map(function(b){ return b.taxa_geral; });
  var maxTaxa = taxaVals.length ? Math.max.apply(null, taxaVals) : 50;
  var minTaxa = taxaVals.length ? Math.min.apply(null, taxaVals) : 0;

  function getColor(taxa) {
    if (!taxa || taxa <= 0) return '#D5D8DC';
    var t = Math.min((taxa - minTaxa) / (maxTaxa - minTaxa + 0.001), 1);
    // Interpolate from #EAF3FB (light blue) to #1B4F72 (dark navy)
    var r = Math.round(234 + (27  - 234) * t);
    var g = Math.round(243 + (79  - 243) * t);
    var b = Math.round(251 + (114 - 251) * t);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  var gLayer = L.geoJSON(BAIRROS_GEO, {
    style: function(feature) {
      var bNome = (feature.properties.bairro || (feature.properties.NM_BAIRRO||'').toUpperCase());
      var bd = bLookup[bNome] || {};
      return { fillColor:getColor(bd.taxa_geral||0), weight:1, color:'#555', fillOpacity:0.75 };
    },
    onEachFeature: function(feature, layer) {
      var bNome = (feature.properties.bairro || (feature.properties.NM_BAIRRO||'').toUpperCase());
      var bd = bLookup[bNome] || {};
      var popStr = bd.pop_total ? fmt(bd.pop_total) : '\u2014';
      var casosStr = bd.casos_total ? fmt(bd.casos_total) : '\u2014';
      var taxaStr = bd.taxa_geral ? fmtR(bd.taxa_geral) + '/1.000 hab' : '\u2014';
      var menor5Str = bd.casos_menor5 ? fmt(bd.casos_menor5) : '\u2014';
      layer.bindPopup(
        '<strong style="font-size:13px">' + (feature.properties.NM_BAIRRO||bNome) + '</strong><br>' +
        'Casos: <strong>' + casosStr + '</strong><br>' +
        'Taxa: ' + taxaStr + '<br>' +
        'Casos < 5 anos: ' + menor5Str + '<br>' +
        'Popula\u00e7\u00e3o: ' + popStr,
        { maxWidth:200 }
      );
      layer.on('mouseover', function() { this.setStyle({weight:2,fillOpacity:0.92}); this.openPopup(); });
      layer.on('mouseout',  function() { gLayer.resetStyle(this); this.closePopup(); });
      layer.on('click',     function() { this.openPopup(); });
    }
  }).addTo(leafletMap);

  // Legend
  var legend = L.control({ position:'bottomright' });
  legend.onAdd = function() {
    var div = L.DomUtil.create('div');
    div.style.cssText = 'background:#fff;padding:10px 12px;border-radius:4px;font-size:11px;font-family:Inter,sans-serif;line-height:1.8;border:1px solid rgba(0,0,0,.15);box-shadow:0 1px 4px rgba(0,0,0,.1)';
    var steps = 5;
    div.innerHTML = '<strong>Taxa/1.000 hab</strong><br>';
    for (var i = 0; i <= steps; i++) {
      var v = minTaxa + (maxTaxa - minTaxa) * i / steps;
      div.innerHTML += '<span style="display:inline-block;width:14px;height:10px;background:' + getColor(v) + ';margin-right:6px;vertical-align:middle;border:1px solid #ccc"></span>' + fmtR(v) + '<br>';
    }
    div.innerHTML += '<span style="display:inline-block;width:14px;height:10px;background:#D5D8DC;margin-right:6px;vertical-align:middle;border:1px solid #ccc"></span>Sem dados';
    return div;
  };
  legend.addTo(leafletMap);

  setTimeout(function() { leafletMap.invalidateSize(); }, 300);
}

// ─── NAVIGATION & EVENTS ──────────────────────────────────────────────────────
function setupNav() {
  // Sidebar nav
  document.querySelectorAll('.nav-item').forEach(function(el) {
    el.addEventListener('click', function() {
      document.querySelectorAll('.nav-item').forEach(function(i){ i.classList.remove('active'); });
      el.classList.add('active');
      var pg = el.getAttribute('data-page');
      document.querySelectorAll('.page').forEach(function(p){ p.classList.remove('active'); });
      document.getElementById('page-' + pg).classList.add('active');
      if (pg === 'mapa') { setTimeout(initMap, 150); }
      else { setTimeout(function(){ Object.values(charts).forEach(function(c){ try{c.resize();}catch(e){} }); }, 100); }
    });
  });

  // Tabs
  document.querySelectorAll('.tab').forEach(function(t) {
    t.addEventListener('click', function() {
      var id = t.getAttribute('data-tab');
      var page = t.closest('.page');
      page.querySelectorAll('.tab-pane').forEach(function(p){ p.classList.remove('active'); });
      page.querySelectorAll('.tab').forEach(function(b){ b.classList.remove('active'); });
      t.classList.add('active');
      document.getElementById(id).classList.add('active');
    });
  });

  // Filter bar toggle
  document.getElementById('fbrToggle').addEventListener('click', function() {
    document.getElementById('filterBar').classList.toggle('open');
  });

  // Toggle buttons
  document.getElementById('btnU5').addEventListener('click', function() {
    u5 = !u5;
    this.classList.toggle('active', u5);
    this.textContent = u5 ? '\u2716 < 5 anos ATIVO' : '< 5 anos';
    refreshAll();
  });

  document.getElementById('btnRepetido').addEventListener('click', function() {
    fRep = !fRep;
    if (fRep) { fCx = false; document.getElementById('btnComplexo').classList.remove('active'); document.getElementById('btnComplexo').textContent = '🏥 Demanda Espon.'; }
    this.classList.toggle('active', fRep);
    this.textContent = fRep ? '\u2716 Repetidos ATIVO' : '\u21ba Casos Repetidos';
    refreshAll();
  });

  document.getElementById('btnComplexo').addEventListener('click', function() {
    fCx = !fCx;
    if (fCx) { fRep = false; document.getElementById('btnRepetido').classList.remove('active'); document.getElementById('btnRepetido').textContent = '\u21ba Casos Repetidos'; }
    this.classList.toggle('active', fCx);
    this.textContent = fCx ? '\u2716 Demanda ATIVO' : '🏥 Demanda Espon.';
    refreshAll();
  });

  // Zona → UBS cascade
  document.getElementById('fZona').addEventListener('change', function() {
    var zona = this.value;
    var sel = document.getElementById('fUBS');
    var cur = sel.value;
    sel.innerHTML = '<option value="">Todas as UBS</option>';
    var ubsList = zona ? DATA.por_ubs.filter(function(u){ return u.zona===zona; }) : DATA.por_ubs;
    ubsList.map(function(u){ return u.ubs; }).sort().forEach(function(n) {
      var o = document.createElement('option'); o.value = n; o.textContent = n;
      if (n === cur) o.selected = true;
      sel.appendChild(o);
    });
  });

  // Table sort
  document.querySelectorAll('table th').forEach(function(th) {
    th.addEventListener('click', function() {
      sortTbl(th.closest('table'), Array.from(th.parentNode.children).indexOf(th), th);
    });
  });
}

function sortTbl(tbl, ci, th) {
  var id = tbl.id + '_' + ci;
  var asc = sortSt[id] !== 'asc';
  sortSt[id] = asc ? 'asc' : 'desc';
  tbl.querySelectorAll('th').forEach(function(h){ h.classList.remove('sort-asc','sort-desc'); });
  th.classList.add(asc ? 'sort-asc' : 'sort-desc');
  var tb = tbl.querySelector('tbody');
  var rows = Array.from(tb.querySelectorAll('tr'));
  rows.sort(function(a,b) {
    var av = a.cells[ci] ? a.cells[ci].textContent.trim() : '';
    var bv = b.cells[ci] ? b.cells[ci].textContent.trim() : '';
    var an = parseFloat(av.replace(/\./g,'').replace(',','.'));
    var bn = parseFloat(bv.replace(/\./g,'').replace(',','.'));
    if (!isNaN(an) && !isNaN(bn)) return asc ? an-bn : bn-an;
    return asc ? av.localeCompare(bv,'pt-BR') : bv.localeCompare(av,'pt-BR');
  });
  rows.forEach(function(r){ tb.appendChild(r); });
}

function populateFilterDropdowns() {
  var selUBS = document.getElementById('fUBS');
  DATA.por_ubs.map(function(u){ return u.ubs; }).sort().forEach(function(n) {
    var o=document.createElement('option'); o.value=n; o.textContent=n; selUBS.appendChild(o);
  });
  var selB = document.getElementById('fBairro');
  DATA.por_bairro.map(function(b){ return b.bairro; }).sort().forEach(function(n) {
    var o=document.createElement('option'); o.value=n; o.textContent=n; selB.appendChild(o);
  });
  var selF = document.getElementById('fFaixa');
  ['<1a','1a','2-4a','5-9a','10-17a','18-29a','30-44a','45-59a','60+'].forEach(function(f) {
    var o=document.createElement('option'); o.value=f; o.textContent=f; selF.appendChild(o);
  });
}

function applyFilters() {
  filters.zona   = document.getElementById('fZona').value;
  filters.ubs    = document.getElementById('fUBS').value;
  filters.bairro = document.getElementById('fBairro').value;
  filters.faixa  = document.getElementById('fFaixa').value;
  filters.sexo   = document.getElementById('fSexo').value;
  filters.mes    = document.getElementById('fMes').value;
  refreshAll();
}

function resetFilters() {
  filters = { zona:'', ubs:'', bairro:'', faixa:'', sexo:'', mes:'' };
  ['fZona','fUBS','fBairro','fFaixa','fSexo','fMes'].forEach(function(id){ document.getElementById(id).value=''; });
  document.getElementById('fZona').dispatchEvent(new Event('change'));
  refreshAll();
}

function getActiveFilters() {
  var parts = [];
  if (filters.zona)   parts.push('Zona: ' + filters.zona);
  if (filters.ubs)    parts.push('UBS: ' + filters.ubs);
  if (filters.bairro) parts.push('Bairro: ' + filters.bairro);
  if (filters.faixa)  parts.push('Faixa: ' + filters.faixa);
  if (filters.sexo)   parts.push('Sexo: ' + (filters.sexo==='M'?'Masculino':'Feminino'));
  if (filters.mes)    parts.push('M\u00eas: ' + MESES[parseInt(filters.mes)-1]);
  if (u5)  parts.push('< 5 anos');
  if (fRep) parts.push('Casos Repetidos');
  if (fCx)  parts.push('Demanda Espon.');
  return parts;
}

function updateFilterStatus() {
  var el = document.getElementById('filterStatus');
  var parts = getActiveFilters();
  if (parts.length) {
    el.style.display = 'block';
    el.innerHTML = '<strong>Filtros ativos:</strong> ' + parts.join(' &nbsp;&bull;&nbsp; ');
  } else {
    el.style.display = 'none';
  }
}

// ─── INIT ────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', function() {
  try {
    populateFilterDropdowns();
    setupNav();
    renderEpiCards();
    refreshAll();
  } catch(e) {
    console.error('Dashboard init error:', e);
  }
});
"""

html_footer = """
</script>
</body>
</html>"""

# ─── ASSEMBLE ────────────────────────────────────────────────────────────────
full_html = (
    html_head
    + "    const DATA = "       + json_str    + ";\n"
    + "    const BAIRROS_GEO = " + geojson_str + ";\n"
    + js_code
    + html_footer
)

# ─── Make self-contained: replace CDN references with inline assets ───────────
# 1. Remove Google Fonts CDN link (fall back to system-ui stack)
full_html = full_html.replace(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
    ''
)
# 2. Replace 'Inter' font references with system-ui stack
full_html = full_html.replace("font-family:'Inter',sans-serif", "font-family:system-ui,-apple-system,'Segoe UI',Arial,sans-serif")
# 3. Inline Leaflet CSS (replace <link> tag)
full_html = full_html.replace(
    '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>',
    '<style id="leaflet-css">' + _LEAFLETCSS + '</style>'
)
# 4. Inline Chart.js (replace <script src> tag)
full_html = full_html.replace(
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>',
    '<script>' + _CHARTJS + '</script>'
)
# 5. Inline Leaflet JS (replace <script src> tag)
full_html = full_html.replace(
    '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>',
    '<script>' + _LEAFLETJS + '</script>'
)

with open(OUT_NFC, 'w', encoding='utf-8') as f:
    f.write(full_html)
print(f"Written: {OUT_NFC}  ({len(full_html)//1024} KB)")

# Copy to user folder (try both NFC and NFD encodings)
for target_dir in [OUT_NFD_DIR, OUT_NFD_DIR2]:
    if os.path.isdir(target_dir):
        target = os.path.join(target_dir, 'painel_dda_arapiraca.html')
        shutil.copy2(OUT_NFC, target)
        print(f"Copied to: {target}")
        break
else:
    print("WARNING: Could not find user folder to copy to")
    import subprocess
    result = subprocess.run(['find', '/sessions/peaceful-nice-brown/mnt', '-type', 'd', '-name', '*lise*'],
                          capture_output=True, text=True)
    print("Available dirs:", result.stdout)

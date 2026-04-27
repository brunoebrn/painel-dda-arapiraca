/* Painel DDA Arapiraca v2.1 — lógica do painel (parte 1/3)
 * Carrega dados via fetch, gerencia estado de filtros e navegação.
 */
'use strict';

// ─── ESTADO GLOBAL ──────────────────────────────────────────────────────────
window.METADATA = null;
window.REGISTROS = [];
window.BAIRROS_GEO = null;
window.MAP_INSTANCE = null;
window.CHARTS = {};

// Estado dos filtros (única fonte da verdade)
window.F = {
  zona: '',
  ubsRef: [], ubsAtend: [], bairro: [], faixa: [],
  sexo: '', mes: '', diaSemana: '',
  u5: false, rep: false, fora: false, semVinc: false
};

// ─── HELPERS ────────────────────────────────────────────────────────────────
const $ = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

function fmt(n) {
  if (n === null || n === undefined || isNaN(n)) return '0';
  return n.toLocaleString('pt-BR');
}
function pct(num, den) {
  if (!den) return '0,0%';
  return ((num / den) * 100).toLocaleString('pt-BR',
    { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
}
function uniq(arr) { return Array.from(new Set(arr)).filter(Boolean).sort(); }

// Mapeamento dia da semana inglês → português
const DIAS_PT = {
  'MON': 'Segunda', 'TUE': 'Terça', 'WED': 'Quarta',
  'THU': 'Quinta', 'FRI': 'Sexta', 'SAT': 'Sábado', 'SUN': 'Domingo'
};
const DIAS_ORDEM = ['MON','TUE','WED','THU','FRI','SAT','SUN'];
const MESES_PT = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const FAIXA_ORDEM = ['<1a','1a','2-4a','5-9a','10-17a','18-29a','30-44a','45-59a','60+','nd'];

// ─── FILTRO CENTRAL ─────────────────────────────────────────────────────────
function aplicarFiltros(registros) {
  const f = window.F;
  return registros.filter(r => {
    if (f.zona && r.zona !== f.zona) return false;
    if (f.sexo && r.sexo !== f.sexo) return false;
    if (f.mes && String(r.mes_atendimento) !== String(f.mes)) return false;
    if (f.diaSemana && r.dia_semana_atend !== f.diaSemana) return false;
    if (f.ubsRef.length && !f.ubsRef.includes(r.ubs_referencia)) return false;
    if (f.ubsAtend.length && !f.ubsAtend.includes(r.ubs_atendimento)) return false;
    if (f.bairro.length && !f.bairro.includes(r.bairro)) return false;
    if (f.faixa.length && !f.faixa.includes(r.faixa_etaria)) return false;
    if (f.u5 && !r.menor_5) return false;
    if (f.rep && !r.repetido) return false;
    if (f.fora && !r.fora_da_referencia) return false;
    if (f.semVinc && !r.sem_vinculacao_aps) return false;
    return true;
  });
}

function snapshotFiltrado() {
  return aplicarFiltros(window.REGISTROS);
}

// ─── INICIALIZAÇÃO ──────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async function() {
  try {
    setLoading('Carregando base anonimizada...');
    const r = await fetch('casos_anonimizados.json');
    if (!r.ok) throw new Error('HTTP ' + r.status + ' ao buscar casos_anonimizados.json');
    const payload = await r.json();
    window.METADATA = payload.metadata;
    window.REGISTROS = payload.registros || [];

    setLoading('Carregando dados geográficos...');
    try {
      const r2 = await fetch('arapiraca_bairros.json');
      if (r2.ok) window.BAIRROS_GEO = await r2.json();
    } catch (e) {
      console.warn('GeoJSON dos bairros não pôde ser carregado:', e);
    }

    clearLoading();
    popularDropdowns();
    setupNav();
    setupBannerLGPD();
    setupFiltrosToolbar();
    bindAllFilters();
    refreshAll();
    console.log('[DDA] Painel inicializado:', window.REGISTROS.length, 'registros.');
  } catch (e) {
    console.error('[DDA] Falha na inicialização:', e);
    showError('Não foi possível carregar a base. Detalhe: ' + e.message);
  }
});

function setLoading(msg) {
  const el = $('#mainCards');
  if (el) el.innerHTML = '<div class="loading">' + msg + '</div>';
}
function clearLoading() {
  const el = $('#mainCards');
  if (el) el.innerHTML = '';
}
function showError(msg) {
  const el = $('#mainCards');
  if (el) el.innerHTML = '<div class="error-box"><strong>Erro:</strong> ' + msg + '</div>';
}

// ─── BANNER LGPD ────────────────────────────────────────────────────────────
function setupBannerLGPD() {
  const banner = $('#bannerLGPD');
  if (!banner) return;
  if (sessionStorage.getItem('lgpd_fechado') === '1') {
    banner.classList.add('hidden');
    return;
  }
  const btn = banner.querySelector('.close-btn');
  if (btn) {
    btn.addEventListener('click', function() {
      banner.classList.add('hidden');
      try { sessionStorage.setItem('lgpd_fechado', '1'); } catch (e) {}
    });
  }
}

// ─── FILTROS TOOLBAR (botão abrir/fechar painel avançado) ──────────────────
function setupFiltrosToolbar() {
  const btn = $('#btnFiltrosAvancados');
  const painel = $('#painelFiltros');
  if (!btn || !painel) return;
  btn.addEventListener('click', function() {
    painel.classList.toggle('hidden');
    btn.classList.toggle('aberto');
  });
  const btnLimpar = $('#btnLimparFiltros');
  if (btnLimpar) btnLimpar.addEventListener('click', limparTodosFiltros);
}

function limparTodosFiltros() {
  window.F = {
    zona: '', ubsRef: [], ubsAtend: [], bairro: [], faixa: [],
    sexo: '', mes: '', diaSemana: '',
    u5: false, rep: false, fora: false, semVinc: false
  };
  // Reseta UI: selects, multi-selects, toggles
  $$('select[data-filter-key]').forEach(s => { s.value = ''; });
  $$('input[type="checkbox"][data-filter-key]').forEach(c => { c.checked = false; });
  $$('.toggle-rapido').forEach(t => t.classList.remove('active'));
  $$('.multiselect').forEach(m => {
    const opts = m.querySelectorAll('.ms-option input');
    opts.forEach(o => { o.checked = false; });
    atualizarLabelMultiselect(m);
  });
  refreshAll();
}

// ─── POPULAÇÃO DE DROPDOWNS ─────────────────────────────────────────────────
function popularDropdowns() {
  const regs = window.REGISTROS;
  // Single-selects
  popularSingleSelect('selZona', uniq(regs.map(r => r.zona)), 'Todas');
  popularSingleSelect('selSexo', uniq(regs.map(r => r.sexo)), 'Todos');
  // Mês
  const meses = uniq(regs.map(r => r.mes_atendimento)).sort((a,b)=>a-b);
  popularSingleSelect('selMes',
    meses.map(m => [String(m), MESES_PT[m] || ('Mês '+m)]), 'Todos');
  // Dia da semana
  popularSingleSelect('selDiaSemana',
    DIAS_ORDEM.filter(d => regs.some(r => r.dia_semana_atend === d))
              .map(d => [d, DIAS_PT[d]]), 'Todos');

  // Multi-selects
  popularMultiselect('msUbsRef', uniq(regs.map(r => r.ubs_referencia)));
  popularMultiselect('msUbsAtend', uniq(regs.map(r => r.ubs_atendimento)));
  popularMultiselect('msBairro', uniq(regs.map(r => r.bairro)));
  popularMultiselect('msFaixa',
    FAIXA_ORDEM.filter(f => regs.some(r => r.faixa_etaria === f)));
}

function popularSingleSelect(id, items, labelTodos) {
  const sel = document.getElementById(id);
  if (!sel) return;
  sel.innerHTML = '';
  const opt0 = document.createElement('option');
  opt0.value = ''; opt0.textContent = labelTodos || 'Todos';
  sel.appendChild(opt0);
  items.forEach(it => {
    const o = document.createElement('option');
    if (Array.isArray(it)) { o.value = it[0]; o.textContent = it[1]; }
    else { o.value = it; o.textContent = it; }
    sel.appendChild(o);
  });
}

function popularMultiselect(id, opcoes) {
  const root = document.getElementById(id);
  if (!root) return;
  root.dataset.opcoesTotais = opcoes.length;
  const optsBox = root.querySelector('.ms-options');
  optsBox.innerHTML = '';
  opcoes.forEach(v => {
    const lbl = document.createElement('label');
    lbl.className = 'ms-option';
    lbl.dataset.valor = v;
    lbl.innerHTML = '<input type="checkbox" value="' + escapeAttr(v) + '"> '
                  + '<span>' + escapeHtml(v) + '</span>';
    optsBox.appendChild(lbl);
  });
  atualizarLabelMultiselect(root);
}

function escapeAttr(s) { return String(s).replace(/"/g,'&quot;'); }
function escapeHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── MULTISELECT INTERATIVO ─────────────────────────────────────────────────
function setupMultiselects() {
  $$('.multiselect').forEach(root => {
    const btn = root.querySelector('.ms-button');
    const dd = root.querySelector('.ms-dropdown');
    if (!btn || !dd) return;
    btn.addEventListener('click', e => {
      e.stopPropagation();
      // fecha outros
      $$('.multiselect .ms-dropdown').forEach(o => {
        if (o !== dd) o.classList.add('hidden');
      });
      dd.classList.toggle('hidden');
    });
    // busca
    const search = root.querySelector('.ms-search input');
    if (search) {
      search.addEventListener('input', () => {
        const q = search.value.trim().toLowerCase();
        root.querySelectorAll('.ms-option').forEach(o => {
          const v = (o.dataset.valor || '').toLowerCase();
          o.style.display = (!q || v.includes(q)) ? '' : 'none';
        });
      });
    }
    // ações Todos/Nenhum
    const actAll = root.querySelector('[data-act="all"]');
    const actNone = root.querySelector('[data-act="none"]');
    if (actAll) actAll.addEventListener('click', e => {
      e.preventDefault();
      root.querySelectorAll('.ms-option').forEach(o => {
        if (o.style.display !== 'none') {
          const inp = o.querySelector('input'); if (inp) inp.checked = true;
        }
      });
      onMultiselectChange(root);
    });
    if (actNone) actNone.addEventListener('click', e => {
      e.preventDefault();
      root.querySelectorAll('.ms-option input').forEach(i => { i.checked = false; });
      onMultiselectChange(root);
    });
    // mudança em opções
    root.addEventListener('change', e => {
      if (e.target.matches('.ms-option input')) onMultiselectChange(root);
    });
  });
  // clique fora fecha dropdowns
  document.addEventListener('click', () => {
    $$('.multiselect .ms-dropdown').forEach(o => o.classList.add('hidden'));
  });
}

function onMultiselectChange(root) {
  const key = root.dataset.filterKey;
  const valores = Array.from(root.querySelectorAll('.ms-option input:checked'))
                        .map(i => i.value);
  window.F[key] = valores;
  atualizarLabelMultiselect(root);
  refreshAll();
}

function atualizarLabelMultiselect(root) {
  const lbl = root.querySelector('.ms-label');
  if (!lbl) return;
  const sel = root.querySelectorAll('.ms-option input:checked').length;
  const tot = parseInt(root.dataset.opcoesTotais || '0', 10);
  if (sel === 0) lbl.textContent = 'Todos';
  else if (sel === tot) lbl.textContent = 'Todos (' + sel + ')';
  else lbl.textContent = sel + ' selecionado' + (sel > 1 ? 's' : '');
}

// ─── BIND DE TODOS OS FILTROS ──────────────────────────────────────────────
function bindAllFilters() {
  // single-selects (sidebar e avançado, sincronizados via data-filter-key)
  $$('select[data-filter-key]').forEach(sel => {
    sel.addEventListener('change', () => {
      const key = sel.dataset.filterKey;
      const v = sel.value;
      window.F[key] = v;
      // sincroniza outros selects com mesma key
      $$('select[data-filter-key="' + key + '"]').forEach(s => {
        if (s !== sel) s.value = v;
      });
      refreshAll();
    });
  });
  // toggles e checkboxes booleanos (sidebar + avançado)
  $$('[data-filter-key][data-bool="1"]').forEach(el => {
    bindBoolToggle(el);
  });
  setupMultiselects();
}

function bindBoolToggle(el) {
  const key = el.dataset.filterKey;
  const inp = el.tagName === 'INPUT' ? el : el.querySelector('input[type="checkbox"]');
  if (!inp) return;
  inp.addEventListener('change', () => {
    const checked = inp.checked;
    window.F[key] = checked;
    // sincroniza todos os elementos com mesma key
    $$('[data-filter-key="' + key + '"][data-bool="1"]').forEach(other => {
      const otherInp = other.tagName === 'INPUT' ? other : other.querySelector('input[type="checkbox"]');
      if (otherInp && otherInp !== inp) otherInp.checked = checked;
      if (other.classList.contains('toggle-rapido')) {
        other.classList.toggle('active', checked);
      }
    });
    if (el.classList.contains('toggle-rapido')) {
      el.classList.toggle('active', checked);
    }
    refreshAll();
  });
}

// ─── NAVEGAÇÃO ENTRE PÁGINAS ───────────────────────────────────────────────
function setupNav() {
  $$('.nav-link[data-page]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const page = a.dataset.page;
      $$('.nav-link[data-page]').forEach(x => x.classList.remove('active'));
      a.classList.add('active');
      $$('.page').forEach(p => p.classList.remove('active'));
      const pg = document.getElementById('page-' + page);
      if (pg) pg.classList.add('active');
      // se for mapa, inicializar lazy
      if (page === 'mapa') initMapaLazy();
      // se for atendimento, render heatmap
      if (page === 'atendimento') renderHeatmap();
      refreshAll();
    });
  });
}

// ─── REFRESH MASTER ─────────────────────────────────────────────────────────
function refreshAll() {
  const filtrados = snapshotFiltrado();
  atualizarContador(filtrados.length);
  renderCardsPrincipais(filtrados);
  renderPaginaAtiva(filtrados);
}

function atualizarContador(n) {
  const el = $('#contagemFiltros');
  const tot = window.REGISTROS.length;
  if (el) {
    if (n === tot) el.innerHTML = '<strong>' + fmt(tot) + '</strong> atendimentos';
    else el.innerHTML = '<strong>' + fmt(n) + '</strong> de ' + fmt(tot) + ' atendimentos';
  }
}

function renderPaginaAtiva(filtrados) {
  const ativa = $('.page.active');
  if (!ativa) return;
  const id = ativa.id.replace('page-', '');
  const f = filtrados;
  if (id === 'visao')        renderVisaoGeral(f);
  else if (id === 'territorial') renderTerritorial(f);
  else if (id === 'perfil')      renderPerfil(f);
  else if (id === 'mapa')        renderMapa(f);
  else if (id === 'atendimento') renderAtendimento(f);
}

// ─── CARDS PRINCIPAIS ──────────────────────────────────────────────────────
function renderCardsPrincipais(regs) {
  const el = $('#mainCards');
  if (!el) return;
  const totalAtend = regs.length;
  const pacientesUnicos = new Set(regs.map(r => r.paciente_id)).size;
  const recorrentes = regs.filter(r => r.repetido).length;
  const u5 = regs.filter(r => r.menor_5).length;
  const semVinc = regs.filter(r => r.sem_vinculacao_aps).length;
  const fora = regs.filter(r => r.fora_da_referencia).length;
  el.innerHTML =
    card('Atendimentos', fmt(totalAtend), 'CID A09 · 2025') +
    card('Pacientes únicos', fmt(pacientesUnicos), pct(pacientesUnicos, totalAtend) + ' do total') +
    card('Recorrentes', fmt(recorrentes), pct(recorrentes, totalAtend) + ' dos atend.') +
    card('Menores de 5 anos', fmt(u5), pct(u5, totalAtend)) +
    card('Sem vinculação APS', fmt(semVinc), pct(semVinc, totalAtend)) +
    card('Fora da UBS de ref.', fmt(fora), pct(fora, totalAtend));
}
function card(label, value, sub) {
  return '<div class="card"><div class="label">' + label + '</div>'
       + '<div class="value">' + value + '</div>'
       + '<div class="sub">' + (sub || '') + '</div></div>';
}

// ─── VISÃO GERAL ───────────────────────────────────────────────────────────
function renderVisaoGeral(regs) {
  // Série temporal (mês de atendimento)
  const porMes = countBy(regs, r => r.mes_atendimento);
  const labels = []; const vals = [];
  for (let m = 1; m <= 12; m++) {
    if (porMes[m] || regs.some(r => r.mes_atendimento === m)) {
      labels.push(MESES_PT[m]); vals.push(porMes[m] || 0);
    }
  }
  drawBarChart('chartMensal', labels, vals, 'Atendimentos por mês');
  // Por sexo
  const porSexo = countBy(regs, r => r.sexo);
  drawDoughnut('chartSexo',
    Object.keys(porSexo).map(s => s === 'M' ? 'Masculino' : (s === 'F' ? 'Feminino' : s)),
    Object.values(porSexo));
  // Por faixa
  const porFaixa = countBy(regs, r => r.faixa_etaria);
  const ordemPresente = FAIXA_ORDEM.filter(f => porFaixa[f]);
  drawBarChart('chartFaixa', ordemPresente, ordemPresente.map(f => porFaixa[f]),
    'Atendimentos por faixa etária');
  // Por zona
  const porZona = countBy(regs, r => r.zona);
  drawDoughnut('chartZona', Object.keys(porZona), Object.values(porZona));
}

// ─── TERRITORIAL ───────────────────────────────────────────────────────────
function renderTerritorial(regs) {
  const porUbs = countBy(regs, r => r.ubs_referencia);
  renderTabelaTopN('tblUbsRef', porUbs, 'UBS de referência', 20);
  const porBairro = countBy(regs, r => r.bairro);
  renderTabelaTopN('tblBairro', porBairro, 'Bairro', 20);
  const porEquipe = countBy(regs, r => r.equipe_referencia);
  renderTabelaTopN('tblEquipe', porEquipe, 'Equipe de referência', 20);
}

// ─── PERFIL EPIDEMIOLÓGICO ─────────────────────────────────────────────────
function renderPerfil(regs) {
  // Distribuição cruzada sexo × faixa
  const cross = {};
  regs.forEach(r => {
    const k = (r.faixa_etaria || 'nd') + '|' + (r.sexo || 'nd');
    cross[k] = (cross[k] || 0) + 1;
  });
  const faixas = FAIXA_ORDEM.filter(f => regs.some(r => r.faixa_etaria === f));
  const dadosM = faixas.map(f => cross[f + '|M'] || 0);
  const dadosF = faixas.map(f => cross[f + '|F'] || 0);
  drawStackedBar('chartCross', faixas, dadosM, dadosF);
  // Recorrência: 1, 2, 3+ atendimentos
  const cnt = {};
  regs.forEach(r => { cnt[r.paciente_id] = (cnt[r.paciente_id] || 0) + 1; });
  const buckets = { '1': 0, '2': 0, '3+': 0 };
  Object.values(cnt).forEach(v => {
    if (v === 1) buckets['1']++;
    else if (v === 2) buckets['2']++;
    else buckets['3+']++;
  });
  drawBarChart('chartRecorrencia',
    ['1 atend.', '2 atend.', '3+ atend.'],
    [buckets['1'], buckets['2'], buckets['3+']],
    'Pacientes por número de atendimentos');
  // Flags clínicos
  const flags = {
    'Gestantes': regs.filter(r => r.gestante).length,
    'Diabéticos': regs.filter(r => r.diabetico).length,
    'Hipertensos': regs.filter(r => r.hipertenso).length,
    'Morador de rua': regs.filter(r => r.morador_rua).length,
  };
  drawBarChart('chartFlags', Object.keys(flags), Object.values(flags),
    'Pacientes por flag clínico');
}

// ─── ATENDIMENTO (UPA + UBS de atendimento + heatmap) ──────────────────────
function renderAtendimento(regs) {
  const porUbsAt = countBy(regs, r => r.ubs_atendimento);
  renderTabelaTopN('tblUbsAtend', porUbsAt, 'Local de atendimento', 30);
  const porEquipeAt = countBy(regs, r => r.equipe_atendimento);
  renderTabelaTopN('tblEquipeAtend', porEquipeAt, 'Equipe de atendimento', 20);
  // Por dia da semana
  const porDS = countBy(regs, r => r.dia_semana_atend);
  const dsOrdem = DIAS_ORDEM.filter(d => porDS[d]);
  drawBarChart('chartDiaSemana',
    dsOrdem.map(d => DIAS_PT[d]),
    dsOrdem.map(d => porDS[d]),
    'Atendimentos por dia da semana');
  renderHeatmap();
}

// ─── HEATMAP CALENDÁRIO ────────────────────────────────────────────────────
function renderHeatmap() {
  const wrap = $('#heatmapCalendario');
  if (!wrap) return;
  const regs = snapshotFiltrado();
  // Matriz: dia da semana (linha) × dia do mês (coluna 1..31)
  const matriz = {};
  DIAS_ORDEM.forEach(d => { matriz[d] = new Array(31).fill(0); });
  regs.forEach(r => {
    if (!r.data_atendimento || r.data_atendimento.length !== 8) return;
    const dia = parseInt(r.data_atendimento.substring(6, 8), 10);
    const ds = r.dia_semana_atend;
    if (matriz[ds] && dia >= 1 && dia <= 31) {
      matriz[ds][dia - 1] += 1;
    }
  });
  // Encontrar máximo para escala
  let max = 0;
  DIAS_ORDEM.forEach(d => matriz[d].forEach(v => { if (v > max) max = v; }));
  // Construir SVG
  const cellW = 22, cellH = 22, padL = 50, padT = 18;
  const w = padL + 31 * cellW + 10;
  const h = padT + 7 * cellH + 22;
  let svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg" width="100%">';
  // header dias do mês (1, 5, 10, 15, 20, 25, 30)
  for (let d = 1; d <= 31; d++) {
    if (d === 1 || d % 5 === 0 || d === 31) {
      const x = padL + (d - 1) * cellW + cellW / 2;
      svg += '<text x="' + x + '" y="' + (padT - 4) + '" class="hm-label" text-anchor="middle">' + d + '</text>';
    }
  }
  // linhas
  DIAS_ORDEM.forEach((ds, i) => {
    const y = padT + i * cellH;
    svg += '<text x="' + (padL - 8) + '" y="' + (y + cellH * 0.65) + '" class="hm-label" text-anchor="end">'
         + DIAS_PT[ds].substring(0, 3) + '</text>';
    for (let d = 0; d < 31; d++) {
      const v = matriz[ds][d];
      const c = corHeatmap(v, max);
      const x = padL + d * cellW;
      svg += '<rect class="hm-cell" x="' + x + '" y="' + y + '" '
           + 'width="' + (cellW - 2) + '" height="' + (cellH - 2) + '" '
           + 'fill="' + c + '" '
           + 'data-tip="' + DIAS_PT[ds] + ' dia ' + (d + 1) + ': ' + v + ' atend." />';
    }
  });
  svg += '</svg>';
  wrap.innerHTML = svg
    + '<div class="heatmap-legend">'
    + '<span>0</span><div class="gradient"></div><span>' + max + ' atend.</span>'
    + '</div>'
    + '<div class="hm-tooltip" id="hmTip"></div>';
  // tooltip handler
  const tip = $('#hmTip');
  wrap.querySelectorAll('.hm-cell').forEach(c => {
    c.addEventListener('mousemove', e => {
      tip.textContent = c.dataset.tip;
      tip.style.display = 'block';
      tip.style.left = (e.pageX + 10) + 'px';
      tip.style.top = (e.pageY - 30) + 'px';
    });
    c.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
  });
}

function corHeatmap(v, max) {
  if (!max || v === 0) return '#F0F3F5';
  const t = v / max;
  // Interpola entre cinza claro (#F0F3F5 = 240,243,245)
  // e azul institucional escuro (#1B4F72 = 27,79,114)
  const r = Math.round(240 + (27 - 240) * t);
  const g = Math.round(243 + (79 - 243) * t);
  const b = Math.round(245 + (114 - 245) * t);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}

// ─── HELPERS DE GRÁFICO E TABELA ───────────────────────────────────────────
function countBy(arr, fn) {
  const out = {};
  arr.forEach(x => { const k = fn(x); if (k === '' || k == null) return; out[k] = (out[k] || 0) + 1; });
  return out;
}

function renderTabelaTopN(id, dict, colLabel, n) {
  const tbody = $('#' + id + ' tbody');
  if (!tbody) return;
  const total = Object.values(dict).reduce((a,b)=>a+b,0);
  const rows = Object.entries(dict).sort((a,b)=>b[1]-a[1]).slice(0, n);
  tbody.innerHTML = rows.map(([k,v]) =>
    '<tr><td>' + escapeHtml(k) + '</td>'
    + '<td style="text-align:right">' + fmt(v) + '</td>'
    + '<td style="text-align:right">' + pct(v, total) + '</td></tr>'
  ).join('') || '<tr><td colspan="3" style="text-align:center;color:#999">Sem dados</td></tr>';
}

function destroyChart(id) {
  if (window.CHARTS[id]) { window.CHARTS[id].destroy(); delete window.CHARTS[id]; }
}

function drawBarChart(canvasId, labels, data, titulo) {
  const cv = document.getElementById(canvasId);
  if (!cv || typeof Chart === 'undefined') return;
  destroyChart(canvasId);
  window.CHARTS[canvasId] = new Chart(cv, {
    type: 'bar',
    data: { labels: labels, datasets: [{ label: titulo, data: data, backgroundColor: '#2E86C1' }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, title: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });
}

function drawDoughnut(canvasId, labels, data) {
  const cv = document.getElementById(canvasId);
  if (!cv || typeof Chart === 'undefined') return;
  destroyChart(canvasId);
  const cores = ['#2E86C1','#D4A017','#1E8449','#C0392B','#5DADE2','#85C1E9'];
  window.CHARTS[canvasId] = new Chart(cv, {
    type: 'doughnut',
    data: { labels: labels, datasets: [{ data: data, backgroundColor: cores.slice(0, labels.length) }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
  });
}

function drawStackedBar(canvasId, labels, dataM, dataF) {
  const cv = document.getElementById(canvasId);
  if (!cv || typeof Chart === 'undefined') return;
  destroyChart(canvasId);
  window.CHARTS[canvasId] = new Chart(cv, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: 'Masculino', data: dataM, backgroundColor: '#2E86C1' },
        { label: 'Feminino', data: dataF, backgroundColor: '#D4A017' }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { stacked: true },
        y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } }
      }
    }
  });
}

// ─── MAPA TERRITORIAL (Leaflet) ────────────────────────────────────────────
function initMapaLazy() {
  if (window.MAP_INSTANCE) return;
  if (typeof L === 'undefined') {
    console.warn('Leaflet não carregado.');
    return;
  }
  const el = document.getElementById('map');
  if (!el) return;
  window.MAP_INSTANCE = L.map('map').setView([-9.7536, -36.6611], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© OpenStreetMap'
  }).addTo(window.MAP_INSTANCE);
  window.MAP_LAYER = null;
}

function renderMapa(regs) {
  initMapaLazy();
  if (!window.MAP_INSTANCE || !window.BAIRROS_GEO) return;
  if (window.MAP_LAYER) {
    window.MAP_INSTANCE.removeLayer(window.MAP_LAYER);
    window.MAP_LAYER = null;
  }
  const porBairro = countBy(regs, r => r.bairro);
  let max = 0;
  Object.values(porBairro).forEach(v => { if (v > max) max = v; });
  function corBairro(v) {
    if (!v || !max) return '#F0F3F5';
    const t = v / max;
    // mesma escala do heatmap: cinza claro → azul institucional escuro
    const r = Math.round(240 + (27 - 240) * t);
    const g = Math.round(243 + (79 - 243) * t);
    const b = Math.round(245 + (114 - 245) * t);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }
  function nomeBairroGeo(feat) {
    const p = feat.properties || {};
    return (p.NOME || p.nome || p.bairro || p.NM_BAIRRO || '').toUpperCase();
  }
  window.MAP_LAYER = L.geoJSON(window.BAIRROS_GEO, {
    style: feat => {
      const nome = nomeBairroGeo(feat);
      const v = porBairro[nome] || 0;
      return {
        fillColor: corBairro(v),
        weight: 1, color: '#5a6b62',
        fillOpacity: 0.75
      };
    },
    onEachFeature: (feat, lyr) => {
      const nome = nomeBairroGeo(feat);
      const v = porBairro[nome] || 0;
      lyr.bindPopup('<strong>' + escapeHtml(nome) + '</strong><br>'
                  + fmt(v) + ' atendimento' + (v === 1 ? '' : 's'));
    }
  }).addTo(window.MAP_INSTANCE);
}

// ─── EXPORTAÇÃO CSV ────────────────────────────────────────────────────────
function exportarCSV() {
  const filtrados = snapshotFiltrado();
  if (!filtrados.length) {
    alert('Nenhum registro corresponde aos filtros atuais.');
    return;
  }
  const F = window.F;
  const filtrosTxt = [];
  if (F.zona) filtrosTxt.push('Zona=' + F.zona);
  if (F.sexo) filtrosTxt.push('Sexo=' + F.sexo);
  if (F.mes) filtrosTxt.push('Mês=' + (MESES_PT[+F.mes] || F.mes));
  if (F.diaSemana) filtrosTxt.push('Dia=' + (DIAS_PT[F.diaSemana] || F.diaSemana));
  if (F.ubsRef.length) filtrosTxt.push('UBS Ref.=' + F.ubsRef.length);
  if (F.ubsAtend.length) filtrosTxt.push('UBS Atend.=' + F.ubsAtend.length);
  if (F.bairro.length) filtrosTxt.push('Bairros=' + F.bairro.length);
  if (F.faixa.length) filtrosTxt.push('Faixas=' + F.faixa.length);
  if (F.u5) filtrosTxt.push('Menores de 5');
  if (F.rep) filtrosTxt.push('Recorrentes');
  if (F.fora) filtrosTxt.push('Fora da UBS de ref.');
  if (F.semVinc) filtrosTxt.push('Sem vinculação APS');

  const cabecalho = [
    '# Painel DDA Arapiraca — Exportação CSV',
    '# Gerado em: ' + new Date().toLocaleString('pt-BR'),
    '# Total filtrado: ' + filtrados.length + ' de ' + window.REGISTROS.length + ' atendimentos',
    '# Filtros aplicados: ' + (filtrosTxt.length ? filtrosTxt.join('; ') : 'nenhum'),
    '# AVISO LGPD: dados anonimizados. Hash determinístico SHA-256 + sal local.',
    '# Sem PII direta. Uso restrito a finalidades sanitárias e gestão pública.',
    '#'
  ].join('\n') + '\n';

  const cols = Object.keys(filtrados[0]);
  let linhas = cabecalho + cols.join(',') + '\n';
  filtrados.forEach(r => {
    linhas += cols.map(c => {
      let v = r[c];
      if (v === null || v === undefined) return '';
      v = String(v);
      if (v.includes(',') || v.includes('"') || v.includes('\n')) {
        v = '"' + v.replace(/"/g, '""') + '"';
      }
      return v;
    }).join(',') + '\n';
  });

  const blob = new Blob(['﻿' + linhas], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const ts = new Date().toISOString().slice(0, 10);
  a.download = 'painel-dda-arapiraca_' + ts + '.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// expor globalmente para o botão do header
window.exportarCSV = exportarCSV;

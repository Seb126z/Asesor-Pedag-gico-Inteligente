/* Módulo de analítica e informes. Consume datos persistidos en FastAPI. */
(function () {
  'use strict';
  var reportData = null;
  var mapData = null;
  var selectedNode = null;
  var filters = { cohort: '', student: '' };
  var loading = false;
  var errorMessage = '';

  function escA(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function queryString() {
    var params = new URLSearchParams();
    if (filters.cohort) params.set('cohort', filters.cohort);
    if (filters.student.trim()) params.set('student', filters.student.trim());
    var q = params.toString();
    return q ? '?' + q : '';
  }
  function scoreColor(value) {
    if (value == null) return 'var(--bd)';
    return value >= 4 ? 'var(--ok)' : value >= 3 ? 'var(--wa)' : 'var(--er)';
  }
  function scoreLabel(value) {
    if (value == null) return 'Sin datos';
    return value >= 4.5 ? 'Sobresaliente' : value >= 3.5 ? 'Alto' : value >= 2.5 ? 'Básico' : 'Bajo';
  }
  function cardStat(label, value, note) {
    return '<div class="card"><small>' + escA(label) + '</small><div class="big">' + escA(value) + '</div><small>' + escA(note || '') + '</small></div>';
  }
  async function loadReport() {
    loading = true; errorMessage = '';
    try {
      reportData = await api('/api/analytics/report' + queryString());
    } catch (error) { errorMessage = error.message; }
    loading = false;
    if (window.tab === 'inf') window.render();
  }
  async function loadMap() {
    loading = true; errorMessage = '';
    try {
      mapData = await api('/api/mindmap' + queryString());
    } catch (error) { errorMessage = error.message; }
    loading = false;
    if (window.tab === 'map') window.render();
  }
  function filterControls() {
    return '<div class="card row"><label> Cohorte <select id="analyticsCohort"><option value="">Todas</option><option value="1" ' + (filters.cohort === '1' ? 'selected' : '') + '>Cohorte 1</option><option value="2" ' + (filters.cohort === '2' ? 'selected' : '') + '>Cohorte 2</option></select></label>' +
      (window.isDoc && window.isDoc() ? '<label> Estudiante <input id="analyticsStudent" value="' + escA(filters.student) + '" placeholder="Nombre exacto (opcional)"></label>' : '') +
      '<button class="b" onclick="analyticsApplyFilters()">Aplicar filtros</button><button class="b s" onclick="analyticsClearFilters()">Limpiar</button></div>';
  }
  function emptyState(message) {
    return '<div class="card"><p>' + escA(message) + '</p><small>Los informes utilizan evaluaciones aprobadas por el docente y evidencias registradas en la base de datos.</small></div>';
  }
  function vInfAnalytics() {
    var html = filterControls();
    if (loading && !reportData) return html + emptyState('Cargando informe...');
    if (errorMessage && !reportData) return html + emptyState('No se pudo cargar el informe: ' + errorMessage);
    if (!reportData) { loadReport(); return html + emptyState('Consultando datos del proyecto...'); }
    var d = reportData, t = d.totals || {};
    html += '<div class="grid">' + cardStat('Promedio general', t.average_grade == null ? '—' : Number(t.average_grade).toFixed(2) + ' / 5', 'Evaluaciones aprobadas') +
      cardStat('Evaluaciones aprobadas', t.approved_evaluations || 0, 'De ' + (t.evaluations || 0) + ' registradas') +
      cardStat('Evidencias', t.evidences || 0, 'Archivos almacenados') +
      cardStat('Laboratorios', t.laboratories || 0, 'En los filtros seleccionados') + '</div>';
    html += '<div class="card"><div class="row" style="justify-content:space-between"><h3>Resultados por cohorte</h3><button class="b s" onclick="analyticsDownloadReport()">Descargar informe JSON</button></div>';
    if (!d.cohorts.length) html += '<p class="mu">No hay resultados para los filtros seleccionados.</p>';
    else html += '<div class="tw"><table><tr><th>Cohorte</th><th>Laboratorios</th><th>Evaluaciones aprobadas</th><th>Promedio</th></tr>' + d.cohorts.map(function (c) {
      return '<tr><td>' + c.cohort + '</td><td>' + c.laboratories + '</td><td>' + c.approved_evaluations + '</td><td><b>' + (c.average_grade == null ? '—' : Number(c.average_grade).toFixed(2)) + '</b></td></tr>';
    }).join('') + '</table></div>';
    html += '</div><div class="card"><h3>Desempeño por laboratorio</h3>';
    html += d.laboratories.map(function (l) {
      var grade = l.average_grade;
      return '<div class="row" style="flex-wrap:nowrap;margin:8px 0"><span style="width:220px;flex:none"><small>' + escA(l.laboratory) + '</small></span><div class="bar" style="flex:1"><i style="width:' + (grade == null ? 0 : grade / 5 * 100) + '%;background:' + scoreColor(grade) + '"></i></div><b style="width:76px;text-align:right">' + (grade == null ? '—' : Number(grade).toFixed(2)) + '</b></div><small class="mu">Cohorte ' + l.cohort + ' · ' + l.evaluations + ' aprobadas · ' + l.evidence_count + ' evidencias</small>';
    }).join('') + '</div>';
    html += '<div class="grid"><div class="card"><h3>Fortalezas identificadas</h3>';
    html += d.strengths.length ? '<ul>' + d.strengths.map(function (x) { return '<li><b>' + escA(x.criterion) + '</b>: ' + x.average_score.toFixed(2) + ' / 5 <small>(' + escA(x.laboratory) + ')</small></li>'; }).join('') + '</ul>' : '<p class="mu">Aún no hay criterios suficientes para identificar fortalezas.</p>';
    html += '</div><div class="card"><h3>Brechas por fortalecer</h3>';
    html += d.gaps.length ? '<ul>' + d.gaps.map(function (x) { return '<li><b>' + escA(x.criterion) + '</b>: ' + x.average_score.toFixed(2) + ' / 5 <small>(' + escA(x.laboratory) + ')</small></li>'; }).join('') + '</ul>' : '<p class="mu">No se registran brechas con promedio inferior a 3,5.</p>';
    html += '</div></div><div class="card"><h3>Plan de fortalecimiento sugerido</h3>';
    html += d.recommendations.length ? '<ol>' + d.recommendations.map(function (x) { return '<li>' + escA(x.recommendation) + '</li>'; }).join('') + '</ol>' : '<p class="mu">El plan se generará cuando existan evaluaciones aprobadas con brechas identificadas.</p>';
    html += '<small>Nota: los promedios y brechas se calculan con evaluaciones aprobadas. No se incluyen notas preliminares.</small></div>';
    return html;
  }
  function nodePosition(node, index, counts) {
    var groups = { root: 0, laboratory: 1, topic: 2, evidence: 3 };
    var col = groups[node.type] == null ? 1 : groups[node.type];
    var total = counts[col] || 1;
    var seen = 0;
    for (var i = 0; i < index; i++) if ((groups[mapData.nodes[i].type] == null ? 1 : groups[mapData.nodes[i].type]) === col) seen++;
    return { x: 90 + col * 230, y: 55 + (seen + 0.5) * (Math.max(430, total * 92) / total) };
  }
  function vMapAnalytics() {
    var html = filterControls();
    if (loading && !mapData) return html + emptyState('Cargando mapa de competencias...');
    if (errorMessage && !mapData) return html + emptyState('No se pudo cargar el mapa: ' + errorMessage);
    if (!mapData) { loadMap(); return html + emptyState('Consultando competencias y evidencias...'); }
    var nodes = mapData.nodes || [], edges = mapData.edges || [], counts = [0, 0, 0, 0];
    nodes.forEach(function (n) { var col = n.type === 'root' ? 0 : n.type === 'laboratory' ? 1 : n.type === 'topic' ? 2 : 3; counts[col]++; });
    var positions = {};
    nodes.forEach(function (n, i) { positions[n.id] = nodePosition(n, i, counts); });
    var svg = '<svg viewBox="0 0 850 ' + Math.max(500, Math.max.apply(null, counts) * 92 + 90) + '" style="width:100%;min-width:650px">';
    edges.forEach(function (e) { var a = positions[e.from], b = positions[e.to]; if (a && b) svg += '<line x1="' + a.x + '" y1="' + a.y + '" x2="' + b.x + '" y2="' + b.y + '" stroke="var(--bd)" stroke-width="1.5" />'; });
    nodes.forEach(function (n) {
      var p = positions[n.id], value = n.mastery != null ? n.mastery : n.grade;
      var color = n.type === 'root' ? 'var(--ac)' : n.type === 'evidence' ? 'var(--sf)' : scoreColor(value);
      var label = n.label.length > 25 ? n.label.slice(0, 22) + '...' : n.label;
      svg += '<g class="nd" onclick="analyticsSelectNode(\'' + escA(n.id) + '\')"><rect x="' + (p.x - 82) + '" y="' + (p.y - 22) + '" width="164" height="44" rx="9" fill="' + color + '" fill-opacity=".17" stroke="' + color + '" stroke-width="1.7"/><text x="' + p.x + '" y="' + (p.y + 4) + '" text-anchor="middle">' + escA(label) + '</text></g>';
    });
    svg += '</svg>';
    var selected = nodes.find(function (n) { return n.id === selectedNode; });
    var detail = selected ? '<h3>' + escA(selected.label) + '</h3><p>Tipo: ' + escA(selected.type) + '</p>' +
      (selected.cohort ? '<p>Cohorte: ' + selected.cohort + '</p>' : '') +
      (selected.mastery != null ? '<p>Dominio promedio: <b>' + selected.mastery.toFixed(2) + ' / 5 · ' + scoreLabel(selected.mastery) + '</b></p>' : '') +
      (selected.grade != null ? '<p>Nota promedio: <b>' + selected.grade.toFixed(2) + ' / 5</b></p>' : '') +
      (selected.approved_evaluations != null ? '<p>Evaluaciones aprobadas: ' + selected.approved_evaluations + '</p>' : '') +
      (selected.evidence_count != null ? '<p>Evidencias: ' + selected.evidence_count + '</p>' : '') +
      (selected.student ? '<p>Estudiante: ' + escA(selected.student) + '</p>' : '') +
      (selected.download_url ? '<p><button class="b s" onclick="analyticsDownloadEvidence(\'' + escA(selected.download_url) + '\',\'' + escA(selected.label) + '\')">Descargar evidencia</button></p>' : '') : '<p class="mu">Selecciona un nodo para consultar sus detalles.</p>';
    return html + '<div class="card"><div class="row" style="justify-content:space-between"><h3>Mapa de competencias y evidencias</h3><button class="b s" onclick="analyticsDownloadMap()">Descargar mapa JSON</button></div><div class="row"><span class="tag">Competencia</span><span class="tag">Laboratorio</span><span class="tag">Temática</span><span class="tag">Evidencia</span></div><div class="tw">' + svg + '</div><small>El color representa el dominio cuando existen evaluaciones aprobadas; gris indica que aún no hay calificación.</small></div><div class="card">' + detail + '</div>';
  }
  function download(name, data) {
    var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
  }
  window.analyticsApplyFilters = function () {
    filters.cohort = document.getElementById('analyticsCohort').value;
    var studentInput = document.getElementById('analyticsStudent');
    filters.student = studentInput ? studentInput.value : '';
    reportData = null; mapData = null; selectedNode = null;
    if (window.tab === 'inf') loadReport(); else loadMap();
  };
  window.analyticsClearFilters = function () {
    filters = { cohort: '', student: '' }; reportData = null; mapData = null; selectedNode = null;
    if (window.tab === 'inf') loadReport(); else loadMap();
  };
  window.analyticsDownloadEvidence = async function (url, name) {
    try {
      var token = window.getToken && window.getToken();
      var response = await fetch(url, { headers: token ? { Authorization: 'Bearer ' + token } : {} });
      if (!response.ok) throw new Error('Error ' + response.status);
      var blob = await response.blob();
      var href = URL.createObjectURL(blob), a = document.createElement('a');
      a.href = href; a.download = name || 'evidencia'; a.click(); URL.revokeObjectURL(href);
    } catch (error) { window.toast('No se pudo descargar la evidencia: ' + error.message, 'er'); }
  };
  window.analyticsSelectNode = function (id) { selectedNode = id; window.render(); };
  window.analyticsDownloadReport = function () { if (reportData) download('informe-analitica.json', reportData); };
  window.analyticsDownloadMap = function () { if (mapData) download('mapa-competencias.json', mapData); };
  window.vInf = vInfAnalytics;
  window.vMap = vMapAnalytics;
  window.analyticsReset = function () { reportData = null; mapData = null; selectedNode = null; filters = { cohort: '', student: '' }; };
  var originalGo = window.go;
  window.go = function (tab) {
    originalGo(tab);
    if (tab === 'inf' && reportData) loadReport();
    if (tab === 'map' && mapData) loadMap();
  };
  if (window.tab === 'inf') loadReport();
  if (window.tab === 'map') loadMap();
  window.render();
})();

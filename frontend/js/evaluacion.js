/* Pestaña Evaluación (estudiante y revisión docente) */
/* Evaluador simulado local: sustituir por llamada a un LLM con salida validada por JSON Schema */
function evaluate(l){
 var t=l.txt.toLowerCase(),sents=l.txt.split(/[.\n]/);
 var crit=l.rub.map(function(c){
  var hit=c.kw.filter(function(k){return t.indexOf(k)>-1});
  var sc=Math.round(hit.length/c.kw.length*5*2)/2;
  var ev=hit.length?(sents.filter(function(s){return s.toLowerCase().indexOf(hit[0])>-1})[0]||'').trim():'';
  return{criterio:c.n,peso:c.w,score:sc,nivel:lvl(sc),evidencia:ev||null,
   fortaleza:hit.length?'Evidencia de: '+hit.join(', '):null,
   brecha:hit.length<c.kw.length?'Falta evidenciar: '+c.kw.filter(function(k){return hit.indexOf(k)<0}).join(', '):null}});
 var r={laboratorio:l.name,version_rubrica:l.v,modelo:'simulado-local-v0',fecha:new Date().toISOString().slice(0,10),
  verificacion:{sintaxis:l.txt.length>40,pruebas_detectadas:/test|assert/.test(t),sandbox:'no ejecutado en este prototipo'},crit:crit};
 r.prelim=calc(l,r);return r}
function vEval(){
 var l=LABS[cur],r=l.res,ok=sumW(l)==100;
 var h='<div class="card row">'+labSel()+'<span class="tag">Cohorte '+l.c+'</span><span class="tag">Rúbrica v'+l.v+'</span></div>'+
 '<div class="card"><h3>Solución del estudiante (texto del informe y código)</h3><label>Adjuntar evidencia (PDF, ZIP, código o imagen): <input type="file" accept=".pdf,.zip,.txt,.py,.js,.html,.docx,.pptx,.png,.jpg,.jpeg,.mp4" onchange="uploadEvidence(this)"></label><p class="mu"><small>Los archivos se guardan en el backend. Tamaño máximo: 25 MB.</small></p><textarea oninput="LABS[cur].txt=this.value">'+esc(l.txt)+'</textarea><div class="row" style="margin-top:8px"><button class="b" '+(ok?'':'disabled')+' onclick="LABS[cur].res=evaluate(LABS[cur]);LABS[cur].ok=false;LABS[cur].adj=null;persistEvaluation(LABS[cur]);render()">Evaluar con IA</button>'+(ok?'':'<span class="er">Rúbrica inconsistente</span>')+'</div></div>';
 if(!r)return h;
 h+='<div class="card"><div class="row" style="justify-content:space-between"><div><div class="mu">Nota preliminar (calculada por el backend)</div><div class="big" style="color:'+col(r.prelim)+'">'+r.prelim.toFixed(1)+'</div></div><div><span class="tag">'+(l.ok?'Aprobada por docente':'Pendiente de revisión')+'</span></div></div>'+
 '<div class="tw"><table><tr><th>Criterio</th><th>Peso</th><th>Valor</th><th>Nivel</th><th>Evidencia y retroalimentación</th></tr>'+
 r.crit.map(function(c){return'<tr><td>'+esc(c.criterio)+'</td><td>'+c.peso+'%</td><td><b>'+c.score.toFixed(1)+'</b></td><td>'+c.nivel+'</td><td><small>'+(c.evidencia?'“'+esc(c.evidencia.slice(0,110))+'”<br>':'')+(c.fortaleza?'<span class="ok">'+esc(c.fortaleza)+'</span><br>':'')+(c.brecha?'<span class="wa">'+esc(c.brecha)+'</span>':'')+'</small></td></tr>'}).join('')+'</table></div>'+
 '<div class="row" style="margin-top:10px"><label>Ajuste docente: <input class="n" style="width:70px" type="number" step="0.1" min="0" max="5" value="'+(l.adj!=null?l.adj:'')+'" placeholder="'+r.prelim.toFixed(1)+'" onchange="var v=parseFloat(this.value);LABS[cur].adj=isNaN(v)?null:Math.min(5,Math.max(0,v))"></label><button class="b" onclick="LABS[cur].ok=true;approveOnApi(LABS[cur]);render()">Aprobar y publicar</button></div></div>'+
 '<div class="card"><h3>Registro de trazabilidad (JSON estructurado)</h3><pre>'+esc(JSON.stringify({laboratorio:r.laboratorio,version_rubrica:r.version_rubrica,modelo:r.modelo,fecha:r.fecha,verificacion:r.verificacion,nota_preliminar:r.prelim,nota_final:final(l),criterios:r.crit.map(function(c){return{criterio:c.criterio,peso:c.peso,valor:c.score,nivel:c.nivel}})},null,1))+'</pre></div>';
 return h}


/* Panel docente: revisión y aprobación de evaluaciones (solo rol docente) */
var PEND=null,pSel=null,pEvid=[],pGrade=null,pFb='',pAll=false;
function labName(id){var l=LABS.filter(function(x){return x.id===id})[0];return l?l.name:'Laboratorio '+id}
async function loadPanel(){PEND=null;render();try{PEND=await api('/api/evaluations'+(pAll?'':'?approved=false'));if(pSel&&!PEND.some(function(e){return e.id===pSel.id}))pSel=null}catch(e){PEND=[];toast('No se pudieron cargar las evaluaciones: '+e.message,'er')}render()}
function setPanelFilter(all){pAll=all;pSel=null;loadPanel()}
async function selectEval(id){var ev=PEND.filter(function(e){return e.id===id})[0];if(!ev)return;pSel=ev;pGrade=ev.final_grade;pFb=ev.teacher_feedback||'';pEvid=[];render();
 try{var all=await api('/api/laboratories/'+ev.laboratory_id+'/evidence');if(pSel&&pSel.id===id)pEvid=all.filter(function(x){return x.student===ev.student})}catch(e){toast('No se pudieron cargar las evidencias: '+e.message,'er')}render()}
async function savePanel(){if(!pSel)return;var g=pGrade!=null?pGrade:pSel.preliminary_grade;
 try{await api('/api/evaluations/'+pSel.id+'/approval',jsonOpts('PATCH',{approved:true,final_grade:g,teacher_feedback:pFb||null}));toast('Evaluación aprobada y publicada para '+pSel.student,'ok');pSel=null;await loadPanel()}catch(e){toast('No se registró la aprobación: '+e.message,'er')}}
function vPanel(){
 var h='<div class="card row"><b>Evaluaciones</b><button class="b '+(pAll?'s':'')+'" onclick="setPanelFilter(false)">Pendientes</button><button class="b '+(pAll?'':'s')+'" onclick="setPanelFilter(true)">Todas</button></div>';
 if(PEND===null)return h+'<div class="card mu">Cargando…</div>';
 if(!PEND.length)return h+'<div class="card mu">'+(pAll?'Todavía no hay evaluaciones.':'No hay evaluaciones pendientes de revisión.')+'</div>';
 h+='<div class="card"><div class="tw"><table><tr><th>Estudiante</th><th>Laboratorio</th><th>Nota preliminar</th><th>Estado</th><th></th></tr>'+
  PEND.map(function(e){return'<tr'+(pSel&&pSel.id===e.id?' style="background:var(--bg)"':'')+'><td>'+esc(e.student)+'</td><td><small>'+esc(labName(e.laboratory_id))+'</small></td><td><b style="color:'+col(e.preliminary_grade)+'">'+e.preliminary_grade.toFixed(1)+'</b></td><td>'+(e.approved?'<span class="tag ok">Aprobada · '+e.final_grade.toFixed(1)+'</span>':'<span class="tag">Pendiente</span>')+'</td><td><button class="b s" onclick="selectEval('+e.id+')">Revisar</button></td></tr>'}).join('')+'</table></div></div>';
 if(!pSel)return h;
 var e=pSel,r=e.result||{},crit=r.crit||[];
 h+='<div class="card"><h3>'+esc(e.student)+' · '+esc(labName(e.laboratory_id))+'</h3><p class="mu"><small>Rúbrica v'+esc(e.rubric_version)+' · modelo '+esc(e.model_name)+'</small></p>'+
  '<div class="tw"><table><tr><th>Criterio</th><th>Peso</th><th>Valor</th><th>Nivel</th><th>Evidencia y retroalimentación</th></tr>'+
  crit.map(function(c){return'<tr><td>'+esc(c.criterio||'')+'</td><td>'+(c.peso!=null?c.peso+'%':'')+'</td><td><b>'+(+c.score).toFixed(1)+'</b></td><td>'+esc(c.nivel||'')+'</td><td><small>'+(c.evidencia?'“'+esc(String(c.evidencia).slice(0,110))+'”<br>':'')+(c.fortaleza?'<span class="ok">'+esc(c.fortaleza)+'</span><br>':'')+(c.brecha?'<span class="wa">'+esc(c.brecha)+'</span>':'')+'</small></td></tr>'}).join('')+'</table></div>'+
  '<h3 style="margin-top:14px">Evidencias entregadas</h3>'+(pEvid.length?'<ul class="ft">'+pEvid.map(function(x){return'<li>'+esc(x.original_name)+' <small class="mu">('+esc(x.uploaded_at||'')+')</small></li>'}).join('')+'</ul>':'<p class="mu"><small>Este estudiante no ha adjuntado archivos para este laboratorio.</small></p>')+
  '<div class="row" style="margin-top:12px"><label>Nota final: <input class="n" style="width:70px" type="number" step="0.1" min="0" max="5" value="'+(pGrade!=null?pGrade:'')+'" placeholder="'+e.preliminary_grade.toFixed(1)+'" onchange="var v=parseFloat(this.value);pGrade=isNaN(v)?null:Math.min(5,Math.max(0,v))"></label><span class="mu"><small>Si la dejas vacía se usa la preliminar.</small></span></div>'+
  '<textarea placeholder="Comentarios para el estudiante" oninput="pFb=this.value" style="min-height:90px;margin-top:8px">'+esc(pFb)+'</textarea>'+
  '<div class="row" style="margin-top:8px"><button class="b" onclick="savePanel()">'+(e.approved?'Guardar cambios':'Aprobar y publicar')+'</button><button class="b s" onclick="pSel=null;render()">Cerrar</button></div></div>';
 return h}

/* Núcleo: datos de ejemplo, estado, utilidades y navegación (compartido) */
var TOPICS={busqueda:'Búsqueda',agentes:'Agentes',supervisado:'Aprendizaje supervisado',redes:'Redes neuronales',nlp:'Procesamiento de lenguaje',llm:'LLM y RAG',vision:'Visión artificial'};
var CATS=[['Razonamiento',['busqueda','agentes']],['Aprendizaje',['supervisado','redes']],['Lenguaje',['nlp','llm']],['Percepción',['vision']]];
function R(a){return a.map(function(r){return{n:r[0],w:r[1],kw:r[2]}})}
var LABS=[
{id:1,c:1,name:'Lab 1 · Búsqueda y agentes',topics:['busqueda','agentes'],v:'1.0',rub:R([['Algoritmo de búsqueda',40,['bfs','a*','heurística','nodos']],['Diseño del agente',30,['agente','percepción','acción','entorno']],['Análisis de resultados',30,['complejidad','comparación','tiempo']]]),
 txt:'Implementé BFS y A* con heurística de distancia sobre una cuadrícula de nodos. El agente percibe el entorno y elige una acción. Comparé tiempo de ejecución y complejidad.\ndef test_astar(): assert path'},
{id:2,c:1,name:'Lab 2 · Aprendizaje supervisado',topics:['supervisado'],v:'1.0',rub:R([['Preparación de datos',30,['normalización','partición','limpieza']],['Modelo y entrenamiento',40,['regresión','árbol','entrenamiento','hiperparámetros']],['Evaluación',30,['accuracy','f1','validación cruzada']]]),
 txt:'Hice limpieza y partición de datos. Entrené un árbol de decisión y una regresión logística, ajustando hiperparámetros. Evalué con accuracy.'},
{id:3,c:1,name:'Lab 3 · Redes neuronales',topics:['redes'],v:'1.1',rub:R([['Arquitectura',40,['capas','activación','neuronas']],['Entrenamiento',35,['backpropagation','épocas','optimizador','pérdida']],['Regularización',25,['dropout','overfitting']]]),txt:''},
{id:4,c:2,name:'Lab 4 · Procesamiento de lenguaje',topics:['nlp'],v:'1.0',rub:R([['Preprocesamiento',35,['tokenización','stopwords','lematización']],['Representación',35,['tf-idf','embeddings']],['Clasificación',30,['sentimiento','clasificador','f1']]]),txt:''},
{id:5,c:2,name:'Lab 5 · Visión artificial',topics:['vision'],v:'1.0',rub:R([['Datos de imágenes',30,['aumentación','etiquetas','resolución']],['Modelo CNN',40,['convolución','pooling','cnn']],['Métricas',30,['precisión','matriz de confusión']]]),txt:''},
{id:6,c:2,name:'Lab 6 · LLM y RAG',topics:['llm','nlp'],v:'1.2',rub:R([['Recuperación',35,['embeddings','vectorial','chunks']],['Prompting',35,['prompt','contexto','json']],['Evaluación y alucinaciones',30,['alucinación','citas','verificación']]]),txt:''}];
LABS.forEach(function(l){l.res=null;l.ok=false;l.adj=null});
var tab='res',cur=0,sel=null;
var TABS=[];
function $(i){return document.getElementById(i)}
function toast(t,k){var e=$('msg');e.textContent=t;e.className='msg '+(k||'');e.hidden=false;clearTimeout(toast.t);toast.t=setTimeout(function(){e.hidden=true},7000)}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function sumW(l){return l.rub.reduce(function(a,c){return a+(+c.w||0)},0)}
function lvl(s){return s>=4.5?'Sobresaliente':s>=3.5?'Alto':s>=2.5?'Básico':s>0?'Bajo':'Sin evidencia'}
function col(g){return g==null?'var(--bd)':g>=4?'var(--ok)':g>=3?'var(--wa)':'var(--er)'}
/* Backend: la nota la calcula el sistema, nunca el LLM */
function calc(l,r){var t=0;r.crit.forEach(function(c,i){t+=c.score*l.rub[i].w/100});return Math.round(t*10)/10}
function final(l){return l.res?(l.adj!=null?l.adj:l.res.prelim):null}
function nav(){$('nav').innerHTML=TABS.map(function(x){return'<button class="'+(x[0]==tab?'on':'')+'" onclick="go(\''+x[0]+'\')">'+x[1]+'</button>'}).join('')}
function go(t){tab=t;if(t==='pan')loadPanel();nav();render();window.scrollTo(0,0)}
function labSel(){return'<select onchange="cur=+this.value;render()">'+LABS.map(function(l,i){return'<option value="'+i+'"'+(i==cur?' selected':'')+'>'+esc(l.name)+'</option>'}).join('')+'</select>'}
function render(){if(!USER){$('app').innerHTML=vAuth();return}$('app').innerHTML={pan:vPanel,res:vRes,rub:vRub,eval:vEval,inf:vInf,map:vMap}[tab]()}


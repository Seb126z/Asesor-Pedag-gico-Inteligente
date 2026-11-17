/* Sesión: inicio de sesión, registro, roles y cierre de sesión */
var USER=null,TOKEN=null,authMode='login';
function getToken(){if(TOKEN)return TOKEN;try{TOKEN=sessionStorage.getItem('tok')}catch(e){}return TOKEN}
function setSession(t){TOKEN=t;try{sessionStorage.setItem('tok',t)}catch(e){}}
function clearSession(){TOKEN=null;try{sessionStorage.removeItem('tok')}catch(e){}}
function isDoc(){return !!USER&&USER.role==='docente'}
function tabsFor(role){var t=[['res','Proyecto']];if(role==='docente')t.push(['pan','Panel docente'],['rub','Rúbricas']);t.push(['eval','Evaluación'],['inf','Informe'],['map','Mapa mental']);return t}
function renderUser(){$('userbar').innerHTML=USER?'<span>'+esc(USER.name)+' <span class="tag">'+esc(USER.role)+'</span></span><button class="b s" onclick="logout()">Cerrar sesión</button>':''}
function draw(){renderUser();nav();render()}
function resetLabs(){if(window.analyticsReset)window.analyticsReset();LABS.forEach(function(l){l.res=null;l.ok=false;l.adj=null;l.apiEvaluationId=null;l.pending=null;l.feedback=null;l.fb='';l.dirty=false;l.evid=[];l.evLoaded=false;l.evLoading=false;l.busy=false})}
function logout(expired){clearSession();USER=null;TABS=[];tab='res';PEND=null;pSel=null;resetLabs();if(expired===true)toast('Tu sesión venció. Inicia sesión de nuevo.','er');draw()}
async function afterLogin(){TABS=tabsFor(USER.role);tab='res';
 try{await loadLabs()}catch(e){resetLabs();toast('No se pudieron cargar los laboratorios del servidor; se usan datos de ejemplo. '+e.message,'er')}
 if(USER.role==='estudiante'){try{await loadMyEvaluations()}catch(e){toast('No se pudieron cargar tus evaluaciones: '+e.message,'er')}}
 draw()}
async function restoreSession(){if(!getToken())return;try{USER=await api('/api/auth/me');await afterLogin()}catch(e){clearSession();USER=null}}
async function doAuth(ev){ev.preventDefault();var f=ev.target,email=f.email.value.trim(),pass=f.password.value,d;
 try{
  if(authMode==='login'){d=await api('/api/auth/login',{method:'POST',noAuth:true,headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({username:email,password:pass}).toString()})}
  else{var name=f.nombre.value.trim();if(name.length<2){toast('Escribe tu nombre completo','er');return false}if(pass.length<8){toast('La contraseña debe tener al menos 8 caracteres','er');return false}
   d=await api('/api/auth/register',Object.assign(jsonOpts('POST',{name:name,email:email,password:pass}),{noAuth:true}))}
  setSession(d.access_token);USER=d.user;await afterLogin()
 }catch(e){toast(e.message,'er')}
 return false}
function vAuth(){var reg=authMode==='register';
 return'<div class="card" style="max-width:420px;margin:30px auto"><h3>'+(reg?'Crear cuenta de estudiante':'Iniciar sesión')+'</h3><form onsubmit="return doAuth(event)">'+
 (reg?'<p><label>Nombre completo<br><input name="nombre" autocomplete="name" required style="width:100%"></label></p>':'')+
 '<p><label>Correo<br><input name="email" type="email" autocomplete="username" required style="width:100%"></label></p>'+
 '<p><label>Contraseña<br><input name="password" type="password" autocomplete="'+(reg?'new-password':'current-password')+'" required style="width:100%"></label></p>'+
 '<div class="row"><button class="b" type="submit">'+(reg?'Crear cuenta':'Entrar')+'</button><button class="b s" type="button" onclick="authMode=\''+(reg?'login':'register')+'\';render()">'+(reg?'Ya tengo cuenta':'Crear cuenta')+'</button></div></form></div>'}

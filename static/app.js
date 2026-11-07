'use strict';
let world=null, selected='alice', tab='mind', previousAgents={}, lastUpdate=0;
const $=id=>document.getElementById(id), canvas=$('world'),ctx=canvas.getContext('2d');
const tile=30, TW=32,TH=24;
const names={openness:'Ouverture',conscientiousness:'Conscience',extraversion:'Extraversion',agreeableness:'Agréabilité',neuroticism:'Sensibilité émotionnelle',energy:'Énergie',social:'Besoin social',stress:'Stress',loneliness:'Solitude'};
const categories={world:'Monde',meeting:'Rencontre',dialogue:'Dialogue',jev:'Évaluation Jev',jev_limit:'Quota Jev',injection:'Observation privée',plasticity:'Plasticité',reflection:'Réflexion',error:'Erreur',settings:'Configuration'};
function el(tag,attrs={},text=''){let e=document.createElement(tag);Object.entries(attrs).forEach(([k,v])=>{if(k==='class')e.className=v;else e.setAttribute(k,v)});if(text)e.textContent=text;return e}
function empty(node){node.replaceChildren()}
function status(msg){const node=$('toast');node.textContent=msg;node.classList.add('show');clearTimeout(status.timer);status.timer=setTimeout(()=>node.classList.remove('show'),3000)}
async function request(url,obj){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Smallville':'1'},body:JSON.stringify(obj)});const data=await r.json();if(!r.ok)throw Error(data.error||'Action impossible');return data}
function clock(min){const d=Math.floor(min/1440)+1;const m=min%1440;return `Jour ${d} · ${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`}
function timeOnly(min){const m=min%1440;return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`}
async function poll(){try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw Error('Serveur non disponible');const next=await r.json();if(world)previousAgents=Object.fromEntries(Object.entries(world.agents).map(([id,a])=>[id,{x:a.x,y:a.y}]));world=next;lastUpdate=performance.now();renderUI()}catch(e){$('state-label').textContent='Serveur déconnecté'} }
function renderUI(){if(!world)return;const w=world;const st=w.status;
 $('clock').textContent=clock(w.minute);$('state-label').textContent=w.paused?'En pause':'Monde en mouvement';$('play').textContent=w.paused?'▶ Démarrer':'Ⅱ Pause';$('step').disabled=!w.paused;
 $('brain-name').textContent=st.brain==='apple'?'Apple Foundation Models':st.brain==='mlx_local'?'MLX local':'Dialogues scriptés';$('brain-name').title=st.brain_note;
 $('jev-chip').textContent=st.jev_enabled?'Jev actif':'Jev désactivé';$('jev-chip').className=st.jev_enabled?'tag':'tag muted';$('jev-toggle').checked=st.jev_enabled;
 $('jev-toggle').disabled=!st.jev_key_set;$('jev-toggle').title=st.jev_key_set?'Activation volontaire des appels Jev':'Clé API absente : relancer Installer.command';
 const b=st.jev_budget;$('jev-calls').textContent=`${b.calls} / 100`;$('jev-cost').textContent=`$${b.used_or_reserved_usd.toFixed(5)} / $${b.budget_usd.toFixed(2)}`;
 $('budget-fill').style.width=`${Math.min(100,100*b.used_or_reserved_usd/Math.max(.01,b.budget_usd))}%`;$('pending').textContent=`${st.pending_jobs} tâche(s) cognitive(s)`;
 $('count').textContent=Object.keys(w.agents).length+' habitants';
 buildAgents();buildProfile();buildInspector();buildEvents();
}
function buildAgents(){const target=$('agents'),prev=target.scrollTop;empty(target);Object.values(world.agents).forEach(a=>{let b=el('button',{class:'agent-button'+(a.id===selected?' active':''),'aria-label':'Inspecter '+a.name});let p=el('span',{class:'portrait'},a.name[0]);p.style.background=a.color;let t=el('span');t.append(el('strong',{},a.name),el('small',{},labelActivity(a.activity)));b.append(p,t);b.onclick=()=>{selected=a.id;buildAgents();buildProfile();buildInspector()};target.append(b)});target.scrollTop=prev}
function labelActivity(s){return ({walking:'En déplacement',talking:'En conversation',working:'À ses occupations',resting:'Se repose',socialising:'Cherche de la compagnie',observe:'Observe',observing:'Observe'})[s]||s}
function buildProfile(){const a=world.agents[selected];if(!a)return;const p=$('profile');empty(p);const top=el('div',{class:'profile-top'}),portrait=el('span',{class:'portrait'},a.name[0]);portrait.style.background=a.color;const title=el('div');title.append(el('h2',{},a.name),el('p',{},labelActivity(a.activity)));top.append(portrait,title);p.append(top,el('p',{class:'bio'},a.bio),el('div',{class:'thought'},'« '+(a.thought||'Je réfléchis.')+' »'))}
function meter(node,label,value){const row=el('div',{class:'trait'}),head=el('div');head.append(el('span',{},label),el('strong',{},`${Math.round(value*100)} %`));const track=el('div',{class:'track'}),fill=el('div',{class:'fill'});fill.style.width=`${Math.max(0,Math.min(100,value*100))}%`;track.append(fill);row.append(head,track);node.append(row)}
function buildInspector(){const a=world.agents[selected];if(!a)return;const p=$('inspector-content');empty(p);
 if(tab==='mind'){p.append(el('div',{class:'section-label'},'STRUCTURE PERSONNELLE'));Object.entries(a.traits).forEach(([k,v])=>meter(p,names[k]||k,v));p.append(el('div',{class:'section-label'},'ÉTATS TRANSITOIRES'));['energy','social','stress','loneliness'].forEach(k=>meter(p,names[k],a[k]));meter(p,'Humeur positive',(a.mood+1)/2);p.append(el('div',{class:'section-label'},'OBJECTIF INDIVIDUEL'));p.append(el('p',{},a.goal))}
 else if(tab==='memory'){p.append(el('div',{class:'section-label'},'SOUVENIRS ACCESSIBLES À '+a.name.toUpperCase()));const items=world.individual[selected].memories;if(!items.length)p.append(el('p',{},'Aucun souvenir.'));items.forEach(m=>{const e=el('div',{class:'memory-item'});e.append(el('small',{},`J${Math.floor(m.minute/1440)+1} ${timeOnly(m.minute)} · ${m.kind} · importance ${Math.round(100*m.importance)} %`),el('p',{},m.content));p.append(e)})}
 else if(tab==='belief'){p.append(el('div',{class:'section-label'},'CONNAISSANCES ET CROYANCES SUBJECTIVES'));world.individual[selected].beliefs.forEach(b=>{const e=el('div',{class:'memory-item'});e.append(el('small',{},`Source : ${b.source||'inconnue'}`));const line=el('div',{class:'belief-bar'});line.append(el('p',{},b.proposition),el('strong',{},Math.round(b.confidence*100)+' %'));e.append(line);p.append(e)})}
 else{p.append(el('div',{class:'section-label'},'RELATIONS DIRIGÉES (OPINION DE '+a.name.toUpperCase()+')'));Object.entries(world.relations[selected]).forEach(([id,r])=>{const e=el('div',{class:'memory-item'});e.append(el('div',{class:'section-label'},world.agents[id].name));['trust','affinity','tension','familiarity'].forEach(k=>meter(e,{trust:'Confiance',affinity:'Affinité',tension:'Tension',familiarity:'Familiarité'}[k],r[k]));p.append(e)})}}
function buildEvents(){const p=$('events');empty(p);world.events.slice(0,25).forEach(e=>{const row=el('div',{class:'event '+e.type});row.append(el('div',{class:'time'},timeOnly(e.minute)));const body=el('div',{class:'event-body'});body.append(el('span',{class:'type'},categories[e.type]||e.type),el('span',{},e.text));row.append(body);p.append(row)})}
function roundedRect(x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r)}
function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);if(!world){requestAnimationFrame(draw);return}
 const g=world.grid;
 for(let y=0;y<TH;y++)for(let x=0;x<TW;x++){
  const cell=g[y][x];const pal={grass:'#355b51',road:'#a49a7b',plaza:'#c9b890',tree:'#366a52',building:'#6f7770'};
  let shade=((x*17+y*31)%7-3)*1.4;
  ctx.fillStyle=pal[cell]||'#314f49';ctx.fillRect(x*tile,y*tile,tile,tile);
  ctx.fillStyle=(cell==='grass'?'#51745d':cell==='road'?'#ccc09c':'#ffffff');ctx.globalAlpha=.10;ctx.fillRect(x*tile+4+(x*7)%11,y*tile+5+(y*11)%12,3,3);ctx.globalAlpha=1;
  ctx.strokeStyle='rgba(9,34,31,.1)';ctx.strokeRect(x*tile+.5,y*tile+.5,tile,tile);
  if(cell==='tree'){ctx.fillStyle='#224c3c';ctx.beginPath();ctx.arc(x*tile+15,y*tile+18,11,0,7);ctx.fill();ctx.fillStyle='#4c9169';ctx.beginPath();ctx.arc(x*tile+14,y*tile+12,10,0,7);ctx.fill();ctx.fillStyle='#75af7c';ctx.fillRect(x*tile+11,y*tile+7,4,3)}
 }
 // Bâtiments
 for(const b of world.buildings){const x=b.x*tile,y=b.y*tile,w=b.w*tile,h=b.h*tile;
  ctx.fillStyle='#0004';roundedRect(x+5,y+9,w-5,h-3,8);ctx.fill();ctx.fillStyle=b.color;roundedRect(x+2,y+1,w-4,h-6,5);ctx.fill();
  ctx.strokeStyle='#f0e3b780';ctx.lineWidth=2;ctx.strokeRect(x+6,y+6,w-12,h-17);
  ctx.fillStyle='#fff3cf';ctx.font='bold 13px system-ui';ctx.textAlign='center';ctx.fillText(b.name,x+w/2,y+h/2+2,w-8);
  ctx.fillStyle='#f6dda8';ctx.fillRect((b.door[0])*tile+7,(b.door[1])*tile+7,16,16);
 }
 // Place centrale
 ctx.textAlign='center';ctx.fillStyle='#514c3c';ctx.font='bold 11px system-ui';ctx.fillText('PLACE',16*tile,11.8*tile);
 const elapsed=Math.min(1,(performance.now()-lastUpdate)/1300);
 for(const a of Object.values(world.agents).sort((a,b)=>a.y-b.y)){
  const old=previousAgents[a.id]||a;let x=(old.x+(a.x-old.x)*elapsed)*tile+tile/2;
  let y=(old.y+(a.y-old.y)*elapsed)*tile+tile/2;
  ctx.fillStyle='#09201d80';ctx.beginPath();ctx.ellipse(x,y+10,13,5,0,0,Math.PI*2);ctx.fill();
  if(a.id===selected){ctx.strokeStyle='#e5f7c6';ctx.lineWidth=3;ctx.beginPath();ctx.arc(x,y,16,0,7);ctx.stroke()}
  ctx.fillStyle=a.color;ctx.beginPath();ctx.arc(x,y,12,0,7);ctx.fill();ctx.strokeStyle='#203b41';ctx.lineWidth=2;ctx.stroke();
  ctx.fillStyle='#25404b';ctx.beginPath();ctx.arc(x-4,y-2,1.4,0,7);ctx.arc(x+4,y-2,1.4,0,7);ctx.fill();
  ctx.fillStyle='#fdf7e7';ctx.font='bold 12px system-ui';ctx.fillText(a.name,x,y-19);
  if(a.dialogue&&a.id===selected){let text=a.dialogue.slice(0,38)+(a.dialogue.length>38?'…':'');ctx.font='11px system-ui';const width=Math.min(280,ctx.measureText(text).width+20);let bx=Math.max(4,Math.min(canvas.width-width-4,x-width/2));let by=y-66;ctx.fillStyle='#fbf1d8';roundedRect(bx,by,width,23,5);ctx.fill();ctx.fillStyle='#263e3b';ctx.textAlign='center';ctx.fillText(text,bx+width/2,by+15)}
 }
 requestAnimationFrame(draw)
}
canvas.addEventListener('click',e=>{if(!world)return;const rect=canvas.getBoundingClientRect();const x=(e.clientX-rect.left)*canvas.width/rect.width,y=(e.clientY-rect.top)*canvas.height/rect.height;let dist=Infinity,pick=null;for(let a of Object.values(world.agents)){let d=Math.hypot(a.x*tile+tile/2-x,a.y*tile+tile/2-y);if(d<dist){dist=d;pick=a.id}}if(dist<28){selected=pick;renderUI()}});
$('play').onclick=async()=>{if(!world)return;try{await request('/api/pause',{paused:!world.paused});await poll()}catch(e){status(e.message)}};
$('step').onclick=async()=>{try{await request('/api/step',{});await poll()}catch(e){status(e.message)}};
$('speed').onchange=async e=>{try{await request('/api/speed',{tick_seconds:Number(e.target.value)});status('Vitesse mise à jour')}catch(e){status(e.message)}};
$('jev-toggle').onchange=async e=>{const enabled=e.target.checked;if(enabled&&!confirm('Activer Jev ? Certaines conversations seront transmises à TypeSafe. Budget plafonné, quotas journaliers et compteurs visibles. Confirmer ?')){e.target.checked=false;return}try{await request('/api/jev',{enabled});await poll();status(enabled?'Jev activé':'Jev désactivé')}catch(err){e.target.checked=!enabled;status(err.message)}};
$('whisper-send').onclick=async()=>{const text=$('whisper').value.trim();if(!text)return status('Saisir une information.');try{await request('/api/whisper',{agent:selected,text});$('whisper').value='';await poll();status('Information ajoutée à la mémoire privée de '+world.agents[selected].name)}catch(e){status(e.message)}};
$('reset').onclick=async()=>{if(!confirm('Réinitialiser le monde et ses souvenirs ? La comptabilité Jev sera conservée.'))return;try{await request('/api/reset',{confirm:'RESET'});await poll();status('Simulation réinitialisée')}catch(e){status(e.message)}};
$('export').onclick=()=>{window.location.href='/api/export'};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b));buildInspector()});
poll();setInterval(poll,1300);requestAnimationFrame(draw);

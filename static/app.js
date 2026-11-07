'use strict';
let world=null, selected='alice', tab='mind', previousAgents={}, lastUpdate=0;
const $=id=>document.getElementById(id),canvas=$('world'),ctx=canvas.getContext('2d');
const tile=25,TW=44,TH=32;
const NAMES={openness:'Ouverture',conscientiousness:'Conscience',extraversion:'Extraversion',agreeableness:'Agréabilité',neuroticism:'Sensibilité émotionnelle',energy:'Énergie',social:'Besoin social',stress:'Stress',loneliness:'Solitude',health:'Santé',hunger:'Faim',hope:'Espoir',security:'Sécurité',conatus:'Conatus',reasoning:'Disposition cognitive',aggression:'Agressivité',religiosity:'Religiosité',credulity:'Crédulité',suspicion:'Soupçon',tolerance:'Tolérance',generosity:'Générosité',ambition:'Ambition',religious_authority:'Autorité religieuse',empirical_evidence:'Importance des preuves',collective_solidarity:'Solidarité',institutional_order:'Ordre institutionnel',tolerance_of_dissent:'Tolérance à la dissidence',perceived_witchcraft_risk:'Crainte de sorcellerie',political_equality:'Égalité politique',fear:'Peur',anger:'Colère',compassion:'Compassion',curiosity:'Curiosité',shame:'Honte',joy:'Joie',foi:'Foi',sorcellerie:'Sorcellerie',politique:'Politique',survie:'Survie',inegalites:'Inégalités',relations:'Relations',preuves:'Preuves'};
const CATEGORIES={world:'Monde',migration:'Migration',meeting:'Rencontre',dialogue:'Dialogue',group_dialogue:'Assemblée',assembly:'Réunion',campaign:'Campagne',election:'Élection',budget:'Répartition',jev:'Jev',jev_limit:'Quota Jev',jev_mind:'Décision Jev',belief_revision:'Révision de croyance',injection:'Information',plasticity:'Plasticité',reflection:'Réflexion',error:'Erreur',settings:'Configuration',economy:'Économie',trade:'Échange',solidarity:'Entraide'};
function el(tag,attrs={},text=''){const e=document.createElement(tag);for(const [k,v] of Object.entries(attrs)){if(k==='class')e.className=v;else e.setAttribute(k,v)}if(text!==''&&text!=null)e.textContent=String(text);return e}
function empty(node){node.replaceChildren()}
function status(msg){const node=$('toast');node.textContent=msg;node.classList.add('show');clearTimeout(status.timer);status.timer=setTimeout(()=>node.classList.remove('show'),4400)}
async function request(url,obj){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Smallville':'1'},body:JSON.stringify(obj)});const data=await r.json();if(!r.ok)throw Error(data.error||'Action impossible');return data}
function clock(min){const d=Math.floor(min/1440)+1,m=min%1440;return `Jour ${d} · ${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`}
function timeOnly(min){const m=min%1440;return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`}
async function poll(){try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw Error('Serveur indisponible');const next=await r.json();if(world)previousAgents=Object.fromEntries(Object.entries(world.agents).map(([id,a])=>[id,{x:a.x,y:a.y}]));world=next;lastUpdate=performance.now();if(!world.agents[selected])selected=Object.keys(world.agents)[0];renderUI()}catch(e){$('state-label').textContent='Serveur déconnecté'}}
function renderUI(){if(!world)return;const w=world,st=w.status,b=st.jev_budget;
 $('clock').textContent=clock(w.minute);$('state-label').textContent=w.paused?'En pause':'En mouvement';$('play').textContent=w.paused?'▶ Démarrer':'Ⅱ Pause';$('step').disabled=!w.paused;$('advance').disabled=!w.paused;$('election-jump').disabled=!w.paused||w.politics.phase==='complete';
 $('brain-name').textContent=st.brain==='apple'?'Apple Foundation Models':st.brain==='mlx_local'?'MLX local':'Dialogues scriptés';$('brain-name').title=st.brain_note;
 $('jev-chip').textContent=st.jev_enabled?'Jev actif':'Jev désactivé';$('jev-chip').className=st.jev_enabled?'tag':'tag muted';$('jev-toggle').checked=st.jev_enabled;$('jev-toggle').disabled=!st.jev_key_set;
 $('jev-calls').textContent=`${b.calls} / ${b.max_calls_total??3500}`;$('jev-cost').textContent=`$${b.used_or_reserved_usd.toFixed(5)} / $${b.budget_usd.toFixed(2)}`;
 $('budget-fill').style.width=`${Math.min(100,100*b.used_or_reserved_usd/Math.max(.01,b.budget_usd))}%`;$('pending').textContent=`${st.pending_jobs} tâche(s) cognitives`;
 $('graph-status').textContent=st.graph.status;$('graph-queue').textContent=st.graph.pending+' écritures à synchroniser en local';$('graph-status').title=st.graph.error||'Graphe local';
 $('count').textContent=Object.keys(w.agents).length+' habitants';
 buildAgents();buildProfile();buildInspector();buildPolitics();buildEvents();drawNetwork();
}
function buildAgents(){const target=$('agents'),prev=target.scrollTop;empty(target);Object.values(world.agents).forEach(a=>{
 const b=el('button',{class:'agent-button'+(a.id===selected?' active':''),'aria-label':'Inspecter '+a.name});const p=el('span',{class:'portrait'},a.name[0]);p.style.background=a.color;const t=el('span');t.append(el('strong',{},a.name),el('small',{},a.role));b.append(p,t);b.onclick=()=>{selected=a.id;renderUI()};target.append(b)});target.scrollTop=prev}
function labelActivity(s){return ({walking:'En marche',talking:'En conversation',working:'Travaille',resting:'Se repose',socialising:'Cherche du monde',observing:'Observe',seeking_food:'Cherche du pain',seeking_safety:'Cherche refuge',campaigning:'Campagne',praying:'Prière',investigating:'Recherche de preuves'})[s]||s}
function buildProfile(){const a=world.agents[selected];if(!a)return;const p=$('profile');empty(p);const top=el('div',{class:'profile-top'}),portrait=el('span',{class:'portrait'},a.name[0]);portrait.style.background=a.color;const title=el('div');title.append(el('h2',{},a.name),el('p',{},a.role+' · '+labelActivity(a.activity)));top.append(portrait,title);p.append(top,el('p',{class:'bio'},a.bio),el('div',{class:'thought'},'« '+(a.thought||'Je réfléchis.')+' »'))}
function meter(node,label,value){const row=el('div',{class:'trait'}),head=el('div');head.append(el('span',{},label),el('strong',{},`${Math.round(value*100)} %`));const track=el('div',{class:'track'}),fill=el('div',{class:'fill'});fill.style.width=`${Math.max(0,Math.min(100,value*100))}%`;track.append(fill);row.append(head,track);node.append(row)}
function buildInspector(){const a=world.agents[selected];if(!a)return;const p=$('inspector-content');empty(p);const individual=world.individual[selected]||{memories:[],beliefs:[]};
 if(tab==='mind'){p.append(el('div',{class:'section-label'},'CAPITAL ET CONDITIONS DE VIE'));p.append(el('p',{class:'values'},`Patrimoine initial : ${a.capital} écus · Liquidités : ${a.coins} · Revenu journalier : ${a.income} · Rations : ${a.provisions}`));for(const k of ['conatus','health','hunger','hope','security','energy','stress'])meter(p,NAMES[k],a[k]);p.append(el('div',{class:'section-label'},'STRUCTURE PERSONNELLE'));Object.entries(a.traits).forEach(([k,v])=>meter(p,NAMES[k]||k,v));p.append(el('div',{class:'section-label'},'DISPOSITIONS SOCIALES'));for(const k of ['reasoning','aggression','religiosity','credulity','suspicion','tolerance','generosity','ambition'])meter(p,NAMES[k],a[k]);p.append(el('div',{class:'section-label'},'RÉSEAU DE REPRÉSENTATIONS DU MONDE'));
  Object.entries(a.worldview||{}).forEach(([k,v])=>meter(p,NAMES[k]||k,v));
  p.append(el('div',{class:'section-label'},'ÉMOTIONS ACTUELLES'));
  Object.entries(a.emotions||{}).forEach(([k,v])=>meter(p,NAMES[k]||k,v));
  p.append(el('div',{class:'section-label'},'SALIENCE (QU’EST-CE QUI COMPTE POUR MOI ?)'));
  Object.entries(a.salience||{}).forEach(([k,v])=>meter(p,NAMES[k]||k,v));
  p.append(el('div',{class:'section-label'},'CONATUS / INTENTION / DERNIERS JUGEMENTS'));
  p.append(el('p',{},a.goal),el('p',{class:'values'},`Décisions Jev : ${a.decisions||0} · Révisions : ${a.revision_count||0} · Intention : ${a.intention||'observe'} · Valeur : ${a.political_priority||'—'}`),el('p',{},a.mental_trace||'Aucun jugement Jev enregistré.'))}
 else if(tab==='memory'){p.append(el('div',{class:'section-label'},'SOUVENIRS AUTOBIOGRAPHIQUES'));if(!individual.memories.length)p.append(el('p',{},'Aucun souvenir.'));individual.memories.forEach(m=>{const e=el('div',{class:'memory-item'});e.append(el('small',{},`${clock(m.minute)} · ${m.kind} · importance ${Math.round(100*m.importance)} %`),el('p',{},m.content));p.append(e)})}
 else if(tab==='belief'){p.append(el('div',{class:'section-label'},'CROYANCES SUBJECTIVES'));individual.beliefs.forEach(b=>{const e=el('div',{class:'memory-item'});e.append(el('small',{},`Source : ${b.source||'inconnue'} · ${clock(b.minute)}`));const line=el('div',{class:'belief-bar'});line.append(el('p',{},b.proposition),el('strong',{},Math.round(b.confidence*100)+' %'));e.append(line);p.append(e)});p.append(el('div',{class:'section-label'},'HISTORIQUE DES RÉVISIONS'));(individual.belief_history||[]).slice(0,12).forEach(b=>{const d=el('div',{class:'memory-item'});d.append(el('small',{},`${clock(b.minute)} · ${b.source||'inconnue'}`),el('p',{},`${b.before==null?'nouvelle croyance':Math.round(b.before*100)+' %'} → ${Math.round(b.after*100)} % : ${b.proposition}`));p.append(d)})}
 else{p.append(el('div',{class:'section-label'},'RELATIONS DIRIGÉES'));Object.entries(world.relations[selected]).sort((a,b)=>b[1].trust-a[1].trust).forEach(([id,r])=>{const e=el('div',{class:'memory-item'});e.append(el('div',{class:'section-label'},world.agents[id].name));for(const k of ['trust','affinity','tension','familiarity'])meter(e,{trust:'Confiance',affinity:'Affinité',tension:'Tension',familiarity:'Familiarité'}[k],r[k]);p.append(e)})}}
function buildPolitics(){const p=$('politics');empty(p);const poll=world.politics,r=world.resources;
 p.append(el('p',{class:'values'},`Maire : ${world.agents[poll.mayor]?.name||poll.mayor} · Trésorerie : ${r.treasury} écus · Grenier : ${r.granary} rations`));
 if(poll.phase==='campaign'){
  p.append(el('p',{},`Scrutin prévu : ${clock(poll.election_minute)} (dans ${Math.max(0,poll.election_minute-world.minute)} minutes simulées).`));
  p.append(el('p',{},`${poll.candidates.map(id=>world.agents[id]?.name||id).join(', ')} sont candidats.`));
  p.append(el('p',{class:'safety-law'},'Charte : aucun meurtre ni exécution, même en période de panique.'));
 }else{const result=poll.result;
  p.append(el('h3',{},`Élue ou élu : ${world.agents[result.mayor].name}`));
  p.append(el('p',{},`${result.turnout}/25 suffrages · ${result.total} écus distribués · ${clock(result.minute)}`));
  const counts=el('div',{class:'vote-count'});for(const [id,v] of Object.entries(result.tally).sort((a,b)=>b[1]-a[1]))counts.append(el('span',{},`${world.agents[id].name} : ${v}`));p.append(counts);
  p.append(el('div',{class:'section-label'},'ALLOCATION BUDGÉTAIRE'));const allocations=el('div',{class:'allocation'});for(const [id,v] of Object.entries(result.allocation).sort((a,b)=>b[1]-a[1]))allocations.append(el('span',{},`${world.agents[id].name} ${v} écus`));p.append(allocations);
 }
}
function buildEvents(){const p=$('events');empty(p);world.events.slice(0,50).forEach(e=>{const row=el('div',{class:'event '+e.type});row.append(el('div',{class:'time'},timeOnly(e.minute)));const body=el('div',{class:'event-body'});body.append(el('span',{class:'type'},CATEGORIES[e.type]||e.type),el('span',{},e.text));row.append(body);p.append(row)})}
function roundedRect(x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r)}
function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);if(!world){requestAnimationFrame(draw);return}
 const g=world.grid;for(let y=0;y<TH;y++)for(let x=0;x<TW;x++){
  const cell=g[y][x],pal={grass:'#355b51',road:'#a49a7b',plaza:'#c9b890',tree:'#366a52',building:'#6f7770'};
  ctx.fillStyle=pal[cell]||'#314f49';ctx.fillRect(x*tile,y*tile,tile,tile);
  ctx.strokeStyle='rgba(9,34,31,.10)';ctx.lineWidth=.5;ctx.strokeRect(x*tile+.5,y*tile+.5,tile,tile);
  if(cell==='tree'){ctx.fillStyle='#234c3e';ctx.beginPath();ctx.arc(x*tile+12,y*tile+15,9,0,7);ctx.fill();ctx.fillStyle='#55936c';ctx.beginPath();ctx.arc(x*tile+12,y*tile+9,8,0,7);ctx.fill()}
 }
 for(const b of world.buildings){const x=b.x*tile,y=b.y*tile,w=b.w*tile,h=b.h*tile;
  ctx.fillStyle='#0004';roundedRect(x+4,y+7,w-4,h-1,7);ctx.fill();ctx.fillStyle=b.color;roundedRect(x+2,y+1,w-4,h-5,5);ctx.fill();ctx.strokeStyle='#f0e3b780';ctx.lineWidth=1.3;ctx.strokeRect(x+6,y+6,w-12,h-14);
  ctx.fillStyle='#fff3cf';ctx.font='bold 12px system-ui';ctx.textAlign='center';ctx.fillText(b.name,x+w/2,y+h/2+2,w-8);
  ctx.fillStyle='#f6dda8';ctx.fillRect(b.door[0]*tile+5,b.door[1]*tile+5,15,15)
 }
 ctx.textAlign='center';ctx.fillStyle='#4c483c';ctx.font='bold 15px system-ui';ctx.fillText('PLACE PUBLIQUE',22*tile,15*tile);
 const elapsed=Math.min(1,(performance.now()-lastUpdate)/1300);
 for(const a of Object.values(world.agents).sort((a,b)=>a.y-b.y)){
  const old=previousAgents[a.id]||a,x=(old.x+(a.x-old.x)*elapsed)*tile+tile/2,y=(old.y+(a.y-old.y)*elapsed)*tile+tile/2;
  ctx.fillStyle='#09201d70';ctx.beginPath();ctx.ellipse(x,y+7,10,4,0,0,Math.PI*2);ctx.fill();
  if(a.id===selected){ctx.strokeStyle='#f1fbd5';ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(x,y,12.5,0,7);ctx.stroke()}
  ctx.fillStyle=a.color;ctx.beginPath();ctx.arc(x,y,9,0,7);ctx.fill();ctx.strokeStyle='#203b41';ctx.lineWidth=1.4;ctx.stroke();
  ctx.fillStyle='#fbf7de';ctx.font='bold 10px system-ui';ctx.fillText(a.name,x,y-13);
  if(a.dialogue&&a.id===selected){const txt=a.dialogue.slice(0,49)+(a.dialogue.length>49?'…':'');ctx.font='11px system-ui';const w=Math.min(300,ctx.measureText(txt).width+20),bx=Math.max(4,Math.min(canvas.width-w-4,x-w/2)),by=y-53;ctx.fillStyle='#fbf1d8';roundedRect(bx,by,w,25,5);ctx.fill();ctx.fillStyle='#263e3b';ctx.fillText(txt,bx+w/2,by+16)}
 }requestAnimationFrame(draw)
}
const ncanvas=$('network'),nctx=ncanvas.getContext('2d');let nodePositions={};
function drawNetwork(){if(!world)return;const W=ncanvas.width,H=ncanvas.height;nctx.clearRect(0,0,W,H);const agents=Object.values(world.agents);
 nodePositions={};agents.forEach((a,i)=>{const ang=(i/agents.length)*Math.PI*2;const radial=70+Math.min(20,Math.log1p(a.capital)*3);nodePositions[a.id]={x:W/2+Math.cos(ang)*radial*1.45,y:H/2+Math.sin(ang)*radial}});
 for(const [aid,others] of Object.entries(world.relations))for(const [bid,r] of Object.entries(others)){
  if(r.trust<.79&&r.tension<.4)continue;const a=nodePositions[aid],b=nodePositions[bid];
  if(!a||!b)continue;nctx.strokeStyle=r.tension>.4?'rgba(239,148,97,.32)':'rgba(149,213,192,.22)';nctx.lineWidth=.6;nctx.beginPath();nctx.moveTo(a.x,a.y);nctx.lineTo(b.x,b.y);nctx.stroke();
 }
 for(const a of agents){const p=nodePositions[a.id];nctx.beginPath();nctx.arc(p.x,p.y,a.id===selected?6:4,0,7);nctx.fillStyle=a.color;nctx.fill();if(a.id===selected){nctx.strokeStyle='#fff';nctx.lineWidth=2;nctx.stroke()}}
}
canvas.addEventListener('click',e=>{if(!world)return;const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*canvas.width/r.width,y=(e.clientY-r.top)*canvas.height/r.height;let dist=100000,pick=null;for(const a of Object.values(world.agents)){const d=Math.hypot(a.x*tile+tile/2-x,a.y*tile+tile/2-y);if(d<dist){dist=d;pick=a.id}}if(dist<21){selected=pick;renderUI()}});
ncanvas.addEventListener('click',e=>{const r=ncanvas.getBoundingClientRect(),x=(e.clientX-r.left)*ncanvas.width/r.width,y=(e.clientY-r.top)*ncanvas.height/r.height;let dist=10000,pick=null;for(const [id,p] of Object.entries(nodePositions)){const d=Math.hypot(p.x-x,p.y-y);if(d<dist){dist=d;pick=id}}if(dist<14){selected=pick;renderUI()}});
$('play').onclick=async()=>{if(!world)return;try{await request('/api/pause',{paused:!world.paused});await poll()}catch(e){status(e.message)}};
$('step').onclick=async()=>{try{await request('/api/step',{});await poll()}catch(e){status(e.message)}};
$('advance').onclick=async()=>{try{status('Avance rapide : 4 heures simulées…');await request('/api/advance',{minutes:240});await poll();status('Quatre heures simulées')}catch(e){status(e.message)}};
$('election-jump').onclick=async()=>{if(!world||world.politics.phase==='complete')return;if(!confirm('Simuler rapidement jusqu’au scrutin ? La simulation doit être en pause et Jev désactivé.'))return;try{const n=world.politics.election_minute-world.minute;status('Calcul des trajectoires jusqu’au scrutin…');await request('/api/advance',{minutes:n});await poll();status('Résultats du scrutin disponibles')}catch(e){status(e.message)}};
$('speed').onchange=async e=>{try{await request('/api/speed',{tick_seconds:Number(e.target.value)});status('Vitesse mise à jour')}catch(e){status(e.message)}};
$('jev-toggle').onchange=async e=>{const enabled=e.target.checked;if(enabled&&!confirm('Activer Jev ? Les jugements transmettent un contexte subjectif à TypeSafe. Plafond conservateur de 4,25 $ et quotas reconfigurés ; estimations locales, pas le solde fournisseur.')){e.target.checked=false;return}try{await request('/api/jev',{enabled});await poll();status(enabled?'Jev activé':'Jev désactivé')}catch(err){e.target.checked=!enabled;status(err.message)}};
$('whisper-send').onclick=async()=>{const text=$('whisper').value.trim();if(!text)return status('Saisir une information.');try{const result=await request('/api/inject',{agent:selected,text,mode:$('inject-mode').value,scope:$('inject-scope').value});$('whisper').value='';await poll();status('Message transmis à '+result.recipients+' habitant(s).')}catch(e){status(e.message)}};
$('reset').onclick=async()=>{if(!confirm('Réinitialiser la simulation ? Les archives SurrealDB et le budget Jev sont conservés.'))return;try{await request('/api/reset',{confirm:'RESET'});await poll();status('Nouvelle expérience démarrée')}catch(e){status(e.message)}};
$('export').onclick=()=>{window.location.href='/api/export'};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b));buildInspector()});
poll();setInterval(poll,1600);requestAnimationFrame(draw);

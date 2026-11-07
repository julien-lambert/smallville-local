'use strict';
let world=null, selected='alice', tab='mind', previousAgents={}, lastUpdate=0;
let insightData=null, insightAgent='', insightFetchedAt=0, influenceData={available:false,links:[]}, influenceMode=false;
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
 $('jev-calls').textContent=`${b.calls} / ${b.max_calls_total??12000}`;$('jev-cost').textContent=`$${b.used_or_reserved_usd.toFixed(5)} / $${b.budget_usd.toFixed(2)}`;
 $('budget-fill').style.width=`${Math.min(100,100*b.used_or_reserved_usd/Math.max(.01,b.budget_usd))}%`;$('pending').textContent=`${st.pending_jobs} tâche(s) cognitives`;
 $('graph-status').textContent=st.graph.status;$('graph-queue').textContent=st.graph.pending+' écritures à synchroniser en local';$('graph-status').title=st.graph.error||'Graphe local';
 $('count').textContent=Object.keys(w.agents).length+' habitants';
 buildAgents();buildProfile();buildInspector();buildPolitics();buildEvents();drawNetwork();refreshInsight();
}
function buildAgents(){const target=$('agents'),prev=target.scrollTop;empty(target);Object.values(world.agents).forEach(a=>{
 const b=el('button',{class:'agent-button'+(a.id===selected?' active':''),'aria-label':'Inspecter '+a.name});const p=el('span',{class:'portrait'},a.name[0]);p.style.background=a.color;const t=el('span');t.append(el('strong',{},a.name),el('small',{},a.role));b.append(p,t);b.onclick=()=>{selected=a.id;insightFetchedAt=0;renderUI()};target.append(b)});target.scrollTop=prev}
function labelActivity(s){return ({deceased:'Décédé',detained:'En détention',planning:'Planifie',negotiating:'Négocie',protesting:'Proteste',trading:'Échange',organizing:'Organise',shopping:'Approvisionnement',walking:'En marche',talking:'En conversation',working:'Travaille',resting:'Se repose',socialising:'Cherche du monde',observing:'Observe',seeking_food:'Cherche du pain',seeking_safety:'Cherche refuge',campaigning:'Campagne',praying:'Prière',investigating:'Recherche de preuves'})[s]||s}
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
 else if(tab==='agenda'){
  const ex=a.executive||{};const project=ex.project;
  p.append(el('div',{class:'section-label'},'PROJET ACTIF & ENGAGEMENTS'));
  if(!a.alive)p.append(el('p',{},'Personnage décédé.'));
  if(!project)p.append(el('p',{},'Aucun projet actif.'));
  else{
   p.append(el('h3',{},project.objective),el('p',{class:'values'},'Statut : '+project.status+' · Origine : '+project.origin+' · Échéance : '+clock(project.deadline)));
   (project.steps||[]).forEach((step,i)=>{
    const card=el('div',{class:'memory-item'});
    card.append(el('small',{},'Étape '+(i+1)+' · '+step.status+' · '+clock(step.due)),
                el('p',{},step.action+' — '+step.place+(step.target?' · '+(world.agents[step.target]?.name||step.target):'')));
    p.append(card);
   });
  }
  p.append(el('div',{class:'section-label'},'FUTURS IMAGINÉS — NON FACTUELS'));
  (ex.future_scenarios||[]).forEach(f=>p.append(el('p',{},f.if+' → '+f.then)));
  p.append(el('div',{class:'section-label'},'PROJETS PRÉCÉDENTS'));
  (ex.history||[]).slice(-6).forEach(pr=>p.append(el('p',{},pr.kind+' · '+pr.status+' · '+(pr.reason_closed||'terminé'))));
 }
 else if(tab==='trail'){p.append(el('div',{class:'section-label'},'PROVENANCE & CHAÎNES DE CROYANCES'));if(insightAgent!==selected||!insightData){p.append(el('p',{},'Chargement des archives...'))}else{p.append(el('p',{class:'values'},'Mémoire : '+insightData.origine));for(const b of insightData.croyances||[]){const e=el('div',{class:'memory-item'});e.append(el('small',{},`Source : ${b.source_declaree} · confiance ${Math.round(b.confiance*100)} %`),el('p',{},b.proposition));for(const c of b.evolution||[])e.append(el('small',{},`${c.avant==null?'nouvelle':Math.round(c.avant*100)+' %'} → ${Math.round(c.apres*100)} % · ${c.cause}`));p.append(e)}}}
 else{p.append(el('div',{class:'section-label'},'RELATIONS DIRIGÉES'));Object.entries(world.relations[selected]).sort((a,b)=>b[1].trust-a[1].trust).forEach(([id,r])=>{const e=el('div',{class:'memory-item'});e.append(el('div',{class:'section-label'},world.agents[id].name));for(const k of ['trust','affinity','tension','familiarity'])meter(e,{trust:'Confiance',affinity:'Affinité',tension:'Tension',familiarity:'Familiarité'}[k],r[k]);p.append(e)})}}
function buildPolitics(){const p=$('politics');empty(p);const poll=world.politics,r=world.resources;
 p.append(el('p',{class:'values'},`Maire : ${world.agents[poll.mayor]?.name||poll.mayor} · Trésorerie : ${r.treasury} écus · Grenier : ${r.granary} rations`));
 if(poll.phase==='campaign'){
  p.append(el('p',{},`Scrutin prévu : ${clock(poll.election_minute)} (dans ${Math.max(0,poll.election_minute-world.minute)} minutes simulées).`));
  p.append(el('p',{},`${poll.candidates.map(id=>world.agents[id]?.name||id).join(', ')} sont candidats.`));
  p.append(el('p',{class:'safety-law'},'Charte : meurtre et exécution interdits. La loi n’empêche pas toute transgression.'));
 }else{const result=poll.result;
  p.append(el('h3',{},`Élue ou élu : ${world.agents[result.mayor].name}`));
  p.append(el('p',{},`${result.turnout}/25 suffrages · ${result.total} écus distribués · ${clock(result.minute)}`));
  const counts=el('div',{class:'vote-count'});for(const [id,v] of Object.entries(result.tally).sort((a,b)=>b[1]-a[1]))counts.append(el('span',{},`${world.agents[id].name} : ${v}`));p.append(counts);
  p.append(el('div',{class:'section-label'},'ALLOCATION BUDGÉTAIRE'));const allocations=el('div',{class:'allocation'});for(const [id,v] of Object.entries(result.allocation).sort((a,b)=>b[1]-a[1]))allocations.append(el('span',{},`${world.agents[id].name} ${v} écus`));p.append(allocations);
 }
}
function buildEvents(){const p=$('events');empty(p);world.events.slice(0,50).forEach(e=>{const row=el('div',{class:'event '+e.type});row.append(el('div',{class:'time'},timeOnly(e.minute)));const body=el('div',{class:'event-body'});body.append(el('span',{class:'type'},CATEGORIES[e.type]||e.type),el('span',{},e.text));row.append(body);p.append(row)})}
// Salem art direction: procedural painted environment, no network assets.
// Geometry follows the simulation grid. All decoration is presentation-only.
const scene=document.createElement('canvas');scene.width=canvas.width;scene.height=canvas.height;
const sc=scene.getContext('2d');
let cacheKey='',hovered=null;
const motionDisabled=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const TAU=Math.PI*2;
function hash2(x,y,k=0){let n=Math.imul(x+71,374761393)+Math.imul(y+19,668265263)+Math.imul(k+13,1274126177);n=(n^(n>>>13));n=Math.imul(n,1274126177);return ((n^(n>>>16))>>>0)/4294967295}
function rr(c,x,y,w,h,r){c.beginPath();c.roundRect(x,y,w,h,r)}
function mix(a,b,t){return Math.round(a+(b-a)*t)}
function leaf(c,x,y,r,seed){c.fillStyle='#182d27';c.beginPath();c.ellipse(x+2,y+5,r*1.05,r*.56,-.22,0,TAU);c.fill();for(let j=0;j<6;j++){let ang=hash2(seed,j,5)*TAU;let d=r*.55*hash2(seed,j,7);let lg=r*(.38+.3*hash2(j,seed,9));c.beginPath();c.fillStyle=['#284936','#356146','#476a4b','#536c4a','#65805a'][Math.floor(hash2(seed,j,3)*5)];c.ellipse(x+Math.cos(ang)*d,y+Math.sin(ang)*d*.7,lg,lg*.72,ang,0,TAU);c.fill()}}
function drawBuilding(c,b){const x=b.x*tile,y=b.y*tile,w=b.w*tile,h=b.h*tile;const church=b.name==='Église',town=b.name==='Mairie',market=b.name==='Marché',school=b.name==='École';
 c.save();c.fillStyle='rgba(12,17,14,.37)';c.filter='blur(13px)';rr(c,x+7,y+19,w+12,h+9,10);c.fill();c.filter='none';
 c.fillStyle=church?'#857a68':town?'#956f62':market?'#ad9271':school?'#a19a7e':'#938573';
 rr(c,x+4,y+11,w-7,h-10,3);c.fill();c.fillStyle='rgba(34,25,23,.14)';c.fillRect(x+w-22,y+17,15,h-18);
 c.fillStyle=church?'#494d56':town?'#694b48':market?'#90745b':'#5c4b43';
 c.beginPath();c.moveTo(x-9,y+22);c.lineTo(x+13,y-10);c.lineTo(x+w-16,y-10);c.lineTo(x+w+9,y+22);c.closePath();c.fill();
 c.strokeStyle='rgba(235,208,158,.21)';c.lineWidth=1;for(let k=0;k<5;k++){const ry=y-4+k*5;c.beginPath();c.moveTo(x+9-k*2,ry);c.lineTo(x+w-9+k*2,ry);c.stroke()}
 c.strokeStyle='rgba(26,17,17,.43)';c.lineWidth=2;c.strokeRect(x+7,y+23,w-14,h-30);
 for(let k=0;k<(w>175?3:2);k++){const wx=x+29+k*(w-60)/(w>175?2:1);const wy=y+Math.min(h-34,54);c.fillStyle='#bd985b';c.fillRect(wx-8,wy-9,16,20);c.fillStyle='#533e32';c.fillRect(wx-6,wy-7,12,17);c.strokeStyle='#c6aa78';c.beginPath();c.moveTo(wx,wy-8);c.lineTo(wx,wy+10);c.moveTo(wx-7,wy+1);c.lineTo(wx+7,wy+1);c.stroke()}
 const dx=b.door[0]*tile+tile/2;const dy=b.door[1]*tile+tile/2;
 c.strokeStyle='rgba(232,214,172,.48)';c.lineWidth=2;c.beginPath();c.moveTo(dx,y+h-15);c.lineTo(dx,dy);c.stroke();
 c.fillStyle='#4f392e';rr(c,dx-9,y+h-24,18,24,2);c.fill();c.fillStyle='#d5ad68';c.beginPath();c.arc(dx+5,y+h-9,1.5,0,TAU);c.fill();
 if(church){const cx=x+w*.49;c.fillStyle='#685751';c.fillRect(cx-12,y-32,24,40);c.beginPath();c.moveTo(cx-20,y-32);c.lineTo(cx,y-66);c.lineTo(cx+20,y-32);c.fill();c.strokeStyle='#c6a67a';c.lineWidth=2;c.beginPath();c.moveTo(cx,y-75);c.lineTo(cx,y-60);c.moveTo(cx-6,y-69);c.lineTo(cx+6,y-69);c.stroke()}
 if(town){c.fillStyle='#d3b885';c.fillRect(x+w/2-20,y-23,40,13);c.fillStyle='#332d29';c.font='bold 11px Georgia';c.textAlign='center';c.fillText('1692',x+w/2,y-13)}
 if(market){c.fillStyle='#dfcbaa';c.fillRect(x+8,y+h-5,w-16,7);for(let k=0;k<6;k++){c.fillStyle=k%2?'#9e594c':'#e7c4a0';c.fillRect(x+14+k*(w-28)/6,y+h-12,(w-28)/6,8)}}
 if(school){c.strokeStyle='#d4b98b';c.lineWidth=2;c.beginPath();c.moveTo(x+w*.49,y+h*.45-12);c.lineTo(x+w*.49,y+h*.45+5);c.moveTo(x+w*.49-8,y+h*.45-4);c.lineTo(x+w*.49+8,y+h*.45-4);c.stroke()}
 const label=b.name.toLocaleUpperCase('fr');c.font='bold 11px Georgia';c.textAlign='center';const labelW=c.measureText(label).width+20;const lx=x+w/2-labelW/2,ly=y+h+5;c.fillStyle='rgba(28,33,29,.84)';rr(c,lx,ly,labelW,22,3);c.fill();c.strokeStyle='#a99066';c.lineWidth=.7;c.stroke();c.fillStyle='#f0dab0';c.fillText(label,x+w/2,ly+15);c.restore()}
function drawPlaza(c){const cx=22*tile+tile/2,cy=17*tile+tile/2;c.save();c.fillStyle='rgba(24,28,26,.30)';c.beginPath();c.ellipse(cx,cy+8,45,19,0,0,TAU);c.fill();c.fillStyle='#817e69';c.beginPath();c.ellipse(cx,cy+5,31,17,0,0,TAU);c.fill();c.fillStyle='#aaad9c';c.beginPath();c.ellipse(cx,cy+1,28,13,0,0,TAU);c.fill();c.fillStyle='#4a7675';c.beginPath();c.ellipse(cx,cy+2,23,9,0,0,TAU);c.fill();c.fillStyle='#a69d85';c.fillRect(cx-4,cy-19,8,19);c.beginPath();c.ellipse(cx,cy-19,11,4,0,0,TAU);c.fill();c.strokeStyle='rgba(196,226,223,.52)';c.lineWidth=1;c.beginPath();c.moveTo(cx,cy-24);c.quadraticCurveTo(cx-12,cy-38,cx-19,cy-8);c.stroke();c.restore()}
function prerender(){if(!world)return;let key=world.run_id+':'+world.version;if(key===cacheKey)return;cacheKey=key;const c=sc;const W=scene.width,H=scene.height;
 const ground=c.createLinearGradient(0,0,W,H);ground.addColorStop(0,'#51644c');ground.addColorStop(.55,'#3e594a');ground.addColorStop(1,'#263f38');c.fillStyle=ground;c.fillRect(0,0,W,H);
 for(let y=0;y<TH;y++)for(let x=0;x<TW;x++){const type=world.grid[y][x],px=x*tile,py=y*tile,h=hash2(x,y);if(type==='road'||type==='plaza'){
  c.fillStyle=type==='plaza'?(h>.5?'#988b70':'#a39578'):(h>.5?'#7b7c66':'#858570');c.fillRect(px,py,tile+1,tile+1);
  c.strokeStyle='rgba(233,216,173,.13)';c.lineWidth=.7;c.beginPath();c.moveTo(px+2,py+7+h*4);c.lineTo(px+13,py+5+h*2);c.lineTo(px+23,py+10);c.stroke();
  if(hash2(x,y,8)>.66){c.fillStyle='#c2b59a';c.beginPath();c.ellipse(px+5+h*10,py+15,2,1,.25,0,TAU);c.fill()}
 }else{
  const v=h*24|0;c.fillStyle=`rgb(${mix(46,69,h)},${mix(69,93,h)},${mix(48,65,h)})`;c.fillRect(px,py,tile+1,tile+1);
  if(type==='grass'&&h>.35){c.strokeStyle='rgba(187,190,132,.24)';c.lineWidth=.7;for(let k=0;k<3;k++){let xx=px+hash2(x,y,k)*25,yy=py+hash2(x,y,k+10)*25;c.beginPath();c.moveTo(xx,yy+3);c.lineTo(xx-1,yy);c.lineTo(xx+1,yy-2);c.stroke()}}
 }
 }
 // Distinct atmospheric edges: braided lanes and field borders.
 c.strokeStyle='rgba(202,177,122,.23)';c.lineWidth=1.2;for(let k=0;k<36;k++){let x=hash2(k,12)*W,y=hash2(k,41)*H;c.beginPath();c.moveTo(x,y);c.lineTo(x+14,y+5);c.stroke()}
 // Small field plots around the village margins.
 for(const [x,y] of [[258,704],[770,714],[86,565]]){c.save();c.strokeStyle='rgba(209,185,113,.44)';c.lineWidth=1;for(let k=0;k<6;k++){c.beginPath();c.moveTo(x+k*17,y);c.lineTo(x+k*17-7,y+43);c.stroke()}c.restore()}
 for(let y=0;y<TH;y++)for(let x=0;x<TW;x++)if(world.grid[y][x]==='tree')leaf(c,x*tile+tile*.5,y*tile+tile*.42,17,x*113+y*23);
 for(const b of world.buildings)drawBuilding(c,b);
 drawPlaza(c);
 // Engraved thin border and an aged-paper cartouche.
 const edge=c.createRadialGradient(W/2,H/2,200,W/2,H/2,760);edge.addColorStop(0,'rgba(7,15,13,0)');edge.addColorStop(1,'rgba(5,13,12,.59)');c.fillStyle=edge;c.fillRect(0,0,W,H);
 c.strokeStyle='rgba(226,201,143,.38)';c.lineWidth=2;c.strokeRect(11,11,W-22,H-22);
 c.strokeStyle='rgba(226,201,143,.25)';c.lineWidth=.8;c.strokeRect(17,17,W-34,H-34);
 c.fillStyle='rgba(22,34,30,.86)';rr(c,28,28,285,44,3);c.fill();c.strokeStyle='rgba(235,208,144,.50)';c.stroke();c.font='small-caps 24px Georgia';c.fillStyle='#e8ce97';c.textAlign='left';c.fillText('Salem-sur-Brume',43,57);
}
function paintCitizen(c,a,x,y,t,night){const stress=a.stress||0;const priest=/prêtr|prédi|diacre|dévot|paroiss/i.test(a.role);const thinker=/philosoph|instituteur|étudiant/i.test(a.role);const walk=a.activity==='walking';const bob=walk&&!motionDisabled?Math.sin(t*8+hash2(x,y)*20)*1.6:0;
 c.save();c.translate(x,y+bob);c.fillStyle='rgba(11,19,16,.46)';c.beginPath();c.ellipse(1,9,11,4,0,0,TAU);c.fill();
 if(a.id===selected){const glow=c.createRadialGradient(0,0,5,0,0,28);glow.addColorStop(0,'rgba(250,221,158,.16)');glow.addColorStop(1,'rgba(250,221,158,0)');c.fillStyle=glow;c.beginPath();c.arc(0,0,29,0,TAU);c.fill();c.strokeStyle='#ffe1a3';c.lineWidth=2;c.beginPath();c.ellipse(0,4,14,8,0,0,TAU);c.stroke()}
 const cloak=priest?'#332d36':thinker?'#374856':a.color||'#987c68';
 c.fillStyle=cloak;c.beginPath();c.moveTo(-7,-1);c.quadraticCurveTo(-12,4,-8,10);c.lineTo(8,10);c.quadraticCurveTo(12,3,7,-1);c.closePath();c.fill();
 c.fillStyle='#342f2b';c.fillRect(-5,9,3,4);c.fillRect(3,9,3,4);
 c.fillStyle='#d5ac85';c.beginPath();c.ellipse(0,-4,6,7,0,0,TAU);c.fill();
 c.fillStyle=priest?'#25262b':thinker?'#4c4e58':'#58463b';c.beginPath();c.ellipse(0,-10,7,3,0,0,TAU);c.fill();c.fillRect(-6,-11,12,4);
 if(priest){c.strokeStyle='#d1b98d';c.lineWidth=1.1;c.beginPath();c.moveTo(0,1);c.lineTo(0,7);c.moveTo(-2,4);c.lineTo(2,4);c.stroke()}
 if(a.id===selected||a.id===hovered||a.dialogue){c.font='600 11px Georgia';c.textAlign='center';let txt=a.name;const w=c.measureText(txt).width+16;c.fillStyle='rgba(22,27,25,.87)';rr(c,-w/2,-32,w,17,4);c.fill();c.fillStyle='#f6e6c1';c.fillText(txt,0,-20)}
 if(a.id===selected&&a.dialogue){const message=a.dialogue.slice(0,70);c.font='12px Georgia';const w=Math.min(330,c.measureText(message).width+26);let bubbleX=Math.max(4-x,Math.min(canvas.width-8-x-w,-w/2));c.fillStyle='#f2dfba';rr(c,bubbleX,-78,w,34,5);c.fill();c.fillStyle='#3b332b';c.fillText(message,bubbleX+w/2,-56)}
 if(stress>.84){c.fillStyle='#d5a35a';c.beginPath();c.arc(9,-14,2.5,0,TAU);c.fill()}
 c.restore()}
function draw(){if(!world){requestAnimationFrame(draw);return}prerender();const W=canvas.width,H=canvas.height;ctx.clearRect(0,0,W,H);ctx.drawImage(scene,0,0);
 const fraction=(world.minute%1440)/1440;const sun=Math.max(0,Math.sin((fraction-.24)*TAU));const darkness=1-sun;
 ctx.fillStyle=`rgba(12,19,35,${.06+darkness*.42})`;ctx.fillRect(0,0,W,H);
 // Lanterns and windows bloom at dusk, no external textures.
 const t=performance.now()/1000;for(const [px,py] of [[7,9],[36,9],[22,16],[31,17],[36,23],[17,8]]){const x=px*tile+12,y=py*tile+10;const light=ctx.createRadialGradient(x,y,2,x,y,38);light.addColorStop(0,`rgba(255,205,117,${.55*darkness})`);light.addColorStop(1,'rgba(255,170,90,0)');ctx.fillStyle=light;ctx.beginPath();ctx.arc(x,y,38,0,TAU);ctx.fill();ctx.fillStyle=`rgba(255,219,144,${.2+.55*darkness})`;ctx.beginPath();ctx.arc(x,y,2.3,0,TAU);ctx.fill()}
 // A few drifting luminous motes, gentle parallax fog.
 if(!motionDisabled){for(let i=0;i<31;i++){const x=(hash2(i,72)*W+t*(3+hash2(i,84)*6))%(W+50)-25;const y=hash2(i,32)*H+Math.sin(t*.32+i)*5;ctx.fillStyle=`rgba(224,206,158,${.05+.09*hash2(i,18)})`;ctx.beginPath();ctx.arc(x,y,1.2+hash2(i,81)*1.7,0,TAU);ctx.fill()}}
 const fogX=motionDisabled?W*.5:W*.5+Math.sin(t*.08)*120;const fog=ctx.createRadialGradient(fogX,H*.80,10,fogX,H*.80,W*.68);fog.addColorStop(0,`rgba(208,217,193,${.11*darkness+.045})`);fog.addColorStop(1,'rgba(216,227,196,0)');ctx.fillStyle=fog;ctx.fillRect(0,0,W,H);
 const elapsed=Math.min(1,(performance.now()-lastUpdate)/1100);for(const a of Object.values(world.agents).sort((a,b)=>a.y-b.y)){const old=previousAgents[a.id]||a;const x=(old.x+(a.x-old.x)*elapsed)*tile+tile/2,y=(old.y+(a.y-old.y)*elapsed)*tile+tile/2;paintCitizen(ctx,a,x,y,t,darkness)}
 requestAnimationFrame(draw)}

// Research graph: selectable trust view or verified SurrealDB influence edges.
const ncanvas=$('network'),nctx=ncanvas.getContext('2d');let nodePositions={};
function drawNetwork(){if(!world)return;const W=ncanvas.width,H=ncanvas.height;nctx.clearRect(0,0,W,H);
 const agents=Object.values(world.agents);const cx=W/2,cy=H/2;
 const halo=nctx.createRadialGradient(cx,cy,8,cx,cy,145);halo.addColorStop(0,'rgba(202,166,108,.13)');halo.addColorStop(1,'rgba(202,166,108,0)');nctx.fillStyle=halo;nctx.fillRect(0,0,W,H);
 nodePositions={};agents.forEach((a,i)=>{const angle=i*2.399963229728653;const radial=25+Math.sqrt((i+.5)/agents.length)*104;nodePositions[a.id]={x:cx+Math.cos(angle)*radial*1.26,y:cy+Math.sin(angle)*radial*.91}});
 if(influenceMode){
  const counts={};for(const link of influenceData.links||[]){const k=link.from+'|'+link.to;counts[k]=(counts[k]||0)+1}
  for(const [key,n] of Object.entries(counts)){const [src,dst]=key.split('|'),a=nodePositions[src],b=nodePositions[dst];if(!a||!b)continue;
   nctx.strokeStyle='rgba(213,152,111,.46)';nctx.lineWidth=Math.min(3,.5+Math.sqrt(n)*.42);nctx.beginPath();nctx.moveTo(a.x,a.y);nctx.lineTo(b.x,b.y);nctx.stroke()}
 }else{
  for(const [aid,others] of Object.entries(world.relations))for(const [bid,r] of Object.entries(others)){
   if(r.trust<.76&&r.tension<.37)continue;const a=nodePositions[aid],b=nodePositions[bid];if(!a||!b)continue;
   nctx.strokeStyle=r.tension>.37?'rgba(206,118,91,.31)':'rgba(212,185,131,.20)';nctx.lineWidth=.6+.9*r.tension;nctx.beginPath();nctx.moveTo(a.x,a.y);nctx.lineTo(b.x,b.y);nctx.stroke()}
 }
 for(const a of agents){const p=nodePositions[a.id],r=a.id===selected?7:4;
  nctx.beginPath();nctx.arc(p.x,p.y,r+3,0,TAU);nctx.fillStyle='rgba(24,25,23,.82)';nctx.fill();
  nctx.beginPath();nctx.arc(p.x,p.y,r,0,TAU);nctx.fillStyle=a.color;nctx.fill();nctx.strokeStyle=a.id===selected?'#f4d89e':'rgba(208,188,143,.45)';nctx.lineWidth=a.id===selected?2:1;nctx.stroke();
  if(a.id===selected){nctx.font='13px Georgia';nctx.fillStyle='#f2dab0';nctx.textAlign='center';nctx.fillText(a.name,p.x,p.y-13)}}
}
function renderInsight(){const panel=$('insight-panel');if(!panel)return;empty(panel);
 if(!insightData){panel.append(el('p',{},'Collecte des traces mémorielles…'));return}
 const a=world?.agents?.[insightAgent];const first=el('div',{class:'insight-card'});first.append(el('h4',{},`Traces de ${a?.name||insightAgent}`),el('p',{},`Source : ${insightData.origine} · ${insightData.provenance?.sources_distinctes||0} source(s) d’influence mémorisées`));
 const memories=insightData.souvenirs||[];if(!memories.length)first.append(el('p',{},'Aucun souvenir retrouvé.'));
 for(const m of memories.slice(0,5)){const item=el('div',{class:'evidence-row'});item.append(el('small',{},`${clock(m.minute)} · ${m.source||'inconnue'}`),el('p',{},m.texte));first.append(item)}
 const second=el('div',{class:'insight-card'});second.append(el('h4',{},'Croyances et provenance'));
 for(const b of (insightData.croyances||[]).slice(0,5)){const e=el('div',{class:'evidence-row'});e.append(el('p',{},b.proposition),el('small',{},`Source : ${b.source_declaree} · ${Math.round(b.confiance*100)} % · ${b.evolution.length} révision(s)`));second.append(e)}
 if(!insightData.croyances?.length)second.append(el('p',{},'Aucune croyance.'));
 panel.append(first,second)
}
async function refreshInsight(force=false){if(!world)return;const now=Date.now(),aid=selected;if(!force&&insightAgent===aid&&now-insightFetchedAt<13500)return;insightFetchedAt=now;insightAgent=aid;
 try{const response=await fetch('/api/insight?agent='+encodeURIComponent(aid),{cache:'no-store'});if(!response.ok)throw Error('Graphe indisponible');const result=await response.json();if(selected!==aid)return;insightData=result;renderInsight();if(tab==='trail')buildInspector()}
 catch(err){insightData={origine:'non disponible',souvenirs:[],croyances:[],provenance:{}};renderInsight()}}
async function loadInfluences(){try{const response=await fetch('/api/influences',{cache:'no-store'});influenceData=await response.json();}catch(err){influenceData={available:false,links:[]}}drawNetwork()}
canvas.addEventListener('mousemove',e=>{if(!world)return;const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*canvas.width/r.width,y=(e.clientY-r.top)*canvas.height/r.height;let d=1e6,id=null;for(const a of Object.values(world.agents)){const dx=a.x*tile+tile/2-x,dy=a.y*tile+tile/2-y,dd=Math.hypot(dx,dy);if(dd<d){d=dd;id=a.id}}hovered=d<17?id:null;canvas.style.cursor=hovered?'pointer':'crosshair'});
canvas.addEventListener('mouseleave',()=>{hovered=null});
canvas.addEventListener('click',e=>{if(!world)return;const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*canvas.width/r.width,y=(e.clientY-r.top)*canvas.height/r.height;let dist=100000,pick=null;for(const a of Object.values(world.agents)){const d=Math.hypot(a.x*tile+tile/2-x,a.y*tile+tile/2-y);if(d<dist){dist=d;pick=a.id}}if(dist<21){selected=pick;insightFetchedAt=0;renderUI()}});
ncanvas.addEventListener('mousemove',e=>{if(!world)return;const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*canvas.width/r.width,y=(e.clientY-r.top)*canvas.height/r.height;let d=1e6,id=null;for(const a of Object.values(world.agents)){const dx=a.x*tile+tile/2-x,dy=a.y*tile+tile/2-y,dd=Math.hypot(dx,dy);if(dd<d){d=dd;id=a.id}}hovered=d<17?id:null;canvas.style.cursor=hovered?'pointer':'crosshair'});
canvas.addEventListener('mouseleave',()=>{hovered=null});
canvas.addEventListener('click',e=>{const r=ncanvas.getBoundingClientRect(),x=(e.clientX-r.left)*ncanvas.width/r.width,y=(e.clientY-r.top)*ncanvas.height/r.height;let dist=10000,pick=null;for(const [id,p] of Object.entries(nodePositions)){const d=Math.hypot(p.x-x,p.y-y);if(d<dist){dist=d;pick=id}}if(dist<14){selected=pick;insightFetchedAt=0;renderUI()}});
$('play').onclick=async()=>{if(!world)return;try{await request('/api/pause',{paused:!world.paused});await poll()}catch(e){status(e.message)}};
$('step').onclick=async()=>{try{await request('/api/step',{});await poll()}catch(e){status(e.message)}};
$('advance').onclick=async()=>{try{status('Avance rapide : 4 heures simulées…');await request('/api/advance',{minutes:240});await poll();status('Quatre heures simulées')}catch(e){status(e.message)}};
$('election-jump').onclick=async()=>{if(!world||world.politics.phase==='complete')return;if(!confirm('Simuler rapidement jusqu’au scrutin ? La simulation doit être en pause et Jev désactivé.'))return;try{const n=world.politics.election_minute-world.minute;status('Calcul des trajectoires jusqu’au scrutin…');await request('/api/advance',{minutes:n});await poll();status('Résultats du scrutin disponibles')}catch(e){status(e.message)}};
$('speed').onchange=async e=>{try{await request('/api/speed',{tick_seconds:Number(e.target.value)});status('Vitesse mise à jour')}catch(e){status(e.message)}};
$('jev-toggle').onchange=async e=>{const enabled=e.target.checked;if(enabled&&!confirm('Activer Jev ? Les jugements transmettent un contexte subjectif à TypeSafe. Plafond interne de 4,50 $ et quotas majorés ; estimations locales, pas le solde fournisseur.')){e.target.checked=false;return}try{await request('/api/jev',{enabled});await poll();status(enabled?'Jev activé':'Jev désactivé')}catch(err){e.target.checked=!enabled;status(err.message)}};
$('whisper-send').onclick=async()=>{const text=$('whisper').value.trim();if(!text)return status('Saisir une information.');try{const result=await request('/api/inject',{agent:selected,text,mode:$('inject-mode').value,scope:$('inject-scope').value});$('whisper').value='';await poll();status('Message transmis à '+result.recipients+' habitant(s).')}catch(e){status(e.message)}};
$('reset').onclick=async()=>{if(!confirm('Réinitialiser la simulation ? Les archives SurrealDB et le budget Jev sont conservés.'))return;try{await request('/api/reset',{confirm:'RESET'});await poll();status('Nouvelle expérience démarrée')}catch(e){status(e.message)}};
$('network-mode').onclick=async()=>{influenceMode=!influenceMode;$('network-mode').textContent=influenceMode?'Voir les relations':'Voir les transmissions';if(influenceMode)await loadInfluences();else drawNetwork();if(influenceMode&&!influenceData.available)status('SurrealDB doit être connecté pour afficher les transmissions.');};
$('insight-refresh').onclick=()=>refreshInsight(true);
$('export').onclick=()=>{window.location.href='/api/export'};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b));buildInspector()});
poll();setInterval(poll,1600);requestAnimationFrame(draw);

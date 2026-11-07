"""Graphe temporel SurrealDB, exclusivement sur 127.0.0.1:8001.

SQLite conserve une outbox transactionnelle; SurrealDB permet les traversées et l'analyse.
Aucun accès Internet. Les erreurs SurrealDB n'effacent jamais l'outbox.
"""
import base64
import json
import re
import threading
import time
import urllib.error
import urllib.request
from .settings import read_var
from .mind import category

HOST = 'http://127.0.0.1:8001'
_NS, _DB = 'smallville', 'society'
_ID = re.compile(r'^[a-zA-Z0-9_]+$')


def identifier(value):
    value = str(value).replace('-', '_')
    if not _ID.fullmatch(value):
        raise ValueError('Identifiant de graphe invalide')
    return value


def quoted(value):
    """Encodage sécurisé des valeurs dans des expressions SurrealQL."""
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def statement(kind, p):
    """SurrealQL: identifiants validés; tout texte provient de JSON échappé."""
    r = identifier(p['run_id'])
    if kind == 'agent':
        a = identifier(p['id'])
        return f'UPSERT agent:{r}_{a} CONTENT {quoted({"run_id":r,**p["data"]})};'
    if kind == 'relation':
        a, b = identifier(p['from']), identifier(p['to'])
        edge = f'{r}_{a}_{b}'
        details = quoted({'run_id':r,**p['data']})
        return f'RELATE OR UPDATE agent:{r}_{a}->knows:{edge}->agent:{r}_{b} CONTENT {details};'
    if kind in ('memory', 'belief', 'dialogue', 'event', 'reflection', 'ballot', 'assembly', 'state', 'relation_change','belief_revision'):
        key = identifier(str(p['id']))
        data = dict(p.get('data') or {})
        data['run_id'] = r
        node_id = f'{kind}:{r}_{key}'
        sql = f'UPSERT {node_id} CONTENT {quoted(data)};'
        aid = p.get('agent')
        if aid:
            a = identifier(aid)
            rel = {'memory':'remembers','belief':'holds','dialogue':'uttered','event':'acts_in','reflection':'reflects_on','ballot':'casts','assembly':'attends','state':'experienced','relation_change':'relates','belief_revision':'revised'}.get(kind)
            if rel:
                edge_id = f'{r}_{a}_{key}'
                # Un ID déterministe rend la reprise des opérations idempotente.
                sql += f' RELATE OR UPDATE agent:{r}_{a}->{rel}:{edge_id}->{node_id} SET minute = {int(data.get("minute", 0))}, run_id = {quoted(r)};' 
        # Index sémantique : mémoire / événement / croyance -> thème partagé.
        # Une traversée agent -> mémoire -> thème permet de sélectionner les
        # épisodes associés à une préoccupation sans lire les secrets d'autrui.
        if kind in ('memory','belief','dialogue','event','reflection','belief_revision'):
            subject=str(data.get('proposition') or data.get('content') or data.get('text') or '')
            if subject:
                theme=identifier(category(subject))
                theme_id=f'theme:{r}_{theme}'
                sql+=f' UPSERT {theme_id} CONTENT {quoted({"name":theme,"run_id":r})};'
                sql+=f' RELATE OR UPDATE {node_id}->about:{r}_{kind}_{key}->{theme_id} SET run_id = {quoted(r)};'
        if kind=='belief_revision' and p.get('belief_id'):
            belief_key=identifier(str(p['belief_id']))
            sql+=f' RELATE OR UPDATE {node_id}->updates:{r}_{key}->belief:{r}_{belief_key} SET run_id = {quoted(r)};'
        if kind == 'dialogue' and p.get('listener'):
            b = identifier(p['listener'])
            sql += f' RELATE OR UPDATE agent:{r}_{b}->heard:{r}_{b}_{key}->{node_id} SET run_id = {quoted(r)};' 
        if kind == 'belief' and p.get('source') and p['source'] not in ('observateur','injection','observation privée','personnel','assemblée','annonce publique'):
            source = str(p['source'])
            if _ID.fullmatch(source.replace('-', '_')):
                s = identifier(source)
                sql += f' RELATE OR UPDATE agent:{r}_{s}->influenced:{r}_{s}_{a}_{key}->agent:{r}_{a} SET belief = {quoted(data.get("proposition", ""))}, minute = {int(data.get("minute",0))}, run_id = {quoted(r)};' 
        if kind == 'ballot':
            candidate = p.get('candidate')
            if candidate:
                c = identifier(candidate)
                sql += f' RELATE OR UPDATE agent:{r}_{a}->voted_for:{r}_{a}_{key}->agent:{r}_{c} SET minute = {int(data.get("minute",0))}, run_id = {quoted(r)};' 
        if kind == 'assembly':
            for member in p.get('participants', []):
                m = identifier(member)
                sql += f' RELATE OR UPDATE agent:{r}_{m}->attends:{r}_{m}_{key}->{node_id} SET run_id = {quoted(r)};' 
        return sql
    raise ValueError('Type de graphe inconnu : '+kind)


class GraphBridge:
    """Client HTTP stdlib, uniquement local, avec reprise des écritures par outbox."""
    def __init__(self, store):
        self.store = store
        self.user = read_var('SURREAL_USER', 'root')
        self.password = read_var('SURREAL_PASS', '')
        self.status = 'en attente'
        self.last_error = ''
        self.synced = 0
        self.closed = threading.Event()
        self.thread = None
        self.initialized = False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _post_sql(self, sql, timeout=2, scoped=True):
        """Envoie du SurrealQL local ; scoped=False pour le bootstrap root.

        La première requête ne peut PAS inclure les en-têtes Surreal-NS/DB :
        la base n'existe pas encore lors de la toute première installation.
        """
        if not self.password:
            raise RuntimeError('Identifiants SurrealDB absents : lancer Installer.command')
        auth = base64.b64encode(f'{self.user}:{self.password}'.encode()).decode()
        headers = {'Authorization':'Basic '+auth,
                   'Content-Type':'text/plain','Accept':'application/json'}
        if scoped:
            headers.update({'Surreal-NS':_NS, 'Surreal-DB':_DB})
        req = urllib.request.Request(HOST+'/sql', data=sql.encode('utf-8'),
                                     method='POST', headers=headers)
        with self.opener.open(req, timeout=timeout) as reply:
            response = json.loads(reply.read(4000000))
        if not isinstance(response, list):
            raise RuntimeError('Réponse SurrealDB inattendue')
        for item in response:
            if item.get('status') != 'OK':
                raise RuntimeError(str(item.get('result','SurrealQL en erreur'))[:240])
        return response

    def query(self, sql, timeout=2):
        """Requête dans la base de la simulation, une fois créée."""
        return self._post_sql(sql, timeout=timeout, scoped=True)

    def bootstrap(self):
        """Création idempotente du namespace et de la database, sans perte de données.

        Une requête root non scindée initialise les ressources une seule fois :
        les versions récentes de SurrealDB refusent parfois d'utiliser un
        namespace absent alors que le serveur /health est opérationnel.
        """
        self._post_sql(
            f'DEFINE NAMESPACE IF NOT EXISTS {_NS}; '
            f'USE NS {_NS}; '
            f'DEFINE DATABASE IF NOT EXISTS {_DB};',
            timeout=8, scoped=False)
        # Vérifier que les en-têtes de portée sont désormais acceptés.
        self.query('RETURN true;', timeout=3)
        self.initialized = True
        self.status = 'synchronisation'
        self.last_error = ''

    def flush(self, max_items=35):
        rows = self.store.outbox(max_items)
        if not rows:
            # Authentification/connexion vérifiées même si la file est vide.
            self.query('RETURN true;', timeout=1.5)
            self.status='connecté'
            return 0
        statements = [statement(x['kind'],json.loads(x['payload'])) for x in rows]
        # Les requêtes locales restent de taille modeste pour la faible RAM du Mac.
        self.query(' '.join(statements), timeout=8)
        self.store.mark_synced([x['id'] for x in rows])
        self.synced += len(rows)
        self.status = 'connecté'; self.last_error = ''
        return len(rows)

    def start(self):
        if self.thread: return
        self.thread=threading.Thread(target=self._loop, name='smallville-surreal', daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.closed.is_set():
            try:
                if not self.initialized:
                    self.bootstrap()
                count=self.flush()
                self.closed.wait(.06 if count else 3)
            except Exception as exc:
                self.status='hors ligne'
                self.last_error=f'{type(exc).__name__}: {str(exc)[:160]}'
                # Après redémarrage de SurrealDB ou changement du stockage,
                # recommencer le bootstrap (sans recréer les données existantes).
                if 'does not exist' in str(exc).lower():
                    self.initialized = False
                self.closed.wait(4)

    def close(self):
        self.closed.set()
        if self.thread: self.thread.join(timeout=3)

    def describe(self):
        return {'status':self.status,'error':self.last_error,'pending':self.store.outbox_count(),
                'synced_in_session':self.synced,'endpoint':HOST,'namespace':_NS,'database':_DB}

    def neighborhood(self, run_id, agent_id):
        """Récupération relationnelle du graphe pour les raisonnements; fallback local si hors ligne."""
        r,a=identifier(run_id),identifier(agent_id)
        try:
            data=self.query(f'SELECT ->knows->agent.name AS acquaintances, ->holds->belief.proposition AS beliefs FROM agent:{r}_{a};',timeout=1.2)
            result=data[0].get('result',[])
            if isinstance(result,list) and result:
                return result[0]
        except Exception: pass
        return {}

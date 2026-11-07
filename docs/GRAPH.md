# Corpus expérimental et graphe SurrealDB

**Une expérience = un `run_id` immuable.** La simulation maintient un journal transactionnel SQLite et projette les éléments dans SurrealDB. Aucune donnée du graphe n'est envoyée vers un service cloud. L'application fonctionne hors ligne ; Jev reste la seule API externe et seulement sur activation expresse.

## Pourquoi deux bases ?

- **SQLite** (`data/smallville.sqlite3`) est le journal local d'écriture, conserve l'état courant, les croyances, les souvenirs et le *ledger* Jev. Une table `graph_outbox` enregistre les modifications dans la même transaction que les données sources. La file n'est marquée synchronisée qu'après réponse positive de SurrealDB. Une panne du serveur Surreal ne détruit donc aucune observation ; elle reste dans l'outbox.
- **SurrealDB** (port `127.0.0.1:8001`, namespace `smallville`, database `society`, stockage `data/surreal/`) matérialise un **graphe temporel interrogeable**. Les runs anciens restent présents lors d'une remise à zéro ; leurs graphes sont séparés par `run_id`.

La mémoire est persistante dans les deux représentations, mais **SQLite est la source d'autorité** pour les décisions de la simulation. Le graphe ajoute un voisinage relationnel consultable par Apple Foundation Models pendant les échanges, quand SurrealDB est disponible. Nous évitons ainsi de perdre les trajectoires pendant une panne SurrealDB ou une migration. SurrealDB est donc nécessaire pour la partie analyse en graphe, pas pour préserver le dernier état courant en cas de panne.

## Structure

Nœuds : `agent`, `memory`, `belief`, `belief_revision`, `dialogue`, `event`, `ballot`, `assembly`, `reflection`, `state`, `relation_change`. Les nœuds `state` enregistrent des états psychologiques journaliers, `relation_change` des changements dans les relations lors des interactions et diffusions de croyances.

Arêtes orientées : `knows` (relation subjective source → cible), `remembers` (agent → mémoire), `holds` (agent → croyance), `uttered`/`heard` (agent → réplique), `influenced` (transmetteur → destinataire), `casts`/`voted_for` (électeur → bulletin/candidat), `attends` (participant → assemblée), `acts_in` (acteur → événement), `experienced` (agent → état journalier), `reflects_on` (agent → réflexion), `relates` (agent → variation relationnelle), `revised` (agent → mise à jour de conviction).

Toutes les arêtes comportent `run_id`, et les changements individuels comportent un horodatage en **minutes simulées**. Les records sont créés avec des identifiants déterministes pour éviter les doublons lors de la reprise de la file d'écriture.

Le graphe encode des observations de simulation et des **croyances subjectives**, pas des diagnostics cliniques ni des faits historiques sur Salem. La distribution des capitaux est lognormale, les dispositions cognitives et l'agressivité suivent des normales tronquées ; quelques caractères ont des paramètres extrêmes délibérément fictifs.

## Installation et exploitation

1. Lors de la première mise à jour vers V3, ouvre `Installer.command` ou exécute `./Installer.command` depuis ton dossier. Le script **préserve le `.env` déjà créé** et configure automatiquement un mot de passe SurrealDB différent de ta clé TypeSafe.
2. Accepte l'installation Homebrew de SurrealDB (`brew install surrealdb/tap/surreal`) si absent. C'est un téléchargement **uniquement lors de l'installation**.
3. Lance `./Lancer.command`. Il démarre SurrealDB sur le port 8001 dans un sous-processus local, puis le navigateur sur le port 8000. Les identifiants restent dans `.env`, fichier ignoré par Git (`chmod 600`). L'utilisateur `root` et le mot de passe SurrealDB ne sont pas écrits dans les arguments du processus.
4. Le panneau affiche `Graphe SurrealDB : connecté` puis `0 écritures à synchroniser` lorsqu'il a terminé les premières centaines de nœuds et arêtes. Si le serveur n'est pas installé, le compteur des opérations en attente augmente, mais l'application reste utilisable.

**Export immédiat du corpus SQLite/graphique** dans le navigateur : `http://127.0.0.1:8000/api/export` (JSON global) ou `http://127.0.0.1:8000/api/graph` (réseau dirigé courant et historiques de vote/assemblées).

**Export intégral de SurrealDB pour analyse ultérieure** :

```bash
cd ~/smallville-local
.venv/bin/python scripts/export_graph.py
# ou pour un run historique :
.venv/bin/python scripts/export_graph.py --run 123456789abc
```

La sortie est `data/exports/graph_<run_id>.json` (ignorée par Git). Elle conserve séparément les nœuds et les arêtes SurrealDB avec leurs attributs, temps, provenance et valeurs psychologiques.

## Exemples de requêtes SurrealQL

Dans la console locale SurrealDB, une fois la namespace `smallville` et la database `society` sélectionnées, remplace `RUN` par le `run_id` visible dans `/api/graph` :

```sql
-- Graphe de confiance actuel dans l'expérience
SELECT in, out, trust, tension, familiarity, minute
FROM knows WHERE run_id = 'RUN' ORDER BY trust DESC LIMIT 50;

-- Propositions de croyances et diffusion par provenance
SELECT in, out, belief, minute
FROM influenced WHERE run_id = 'RUN' ORDER BY minute;

-- Répliques et intervenants au fil du temps
SELECT speaker, listener, content, backend, minute
FROM dialogue WHERE run_id = 'RUN' ORDER BY minute;

-- Évolution d'un conatus, de l'humeur et du patrimoine
SELECT minute, conatus, emotions, worldview, salience, coins, health, traits
FROM state WHERE run_id = 'RUN' ORDER BY minute;

-- Scrutin individuel, candidat et proposition de répartition
SELECT voter, candidate, allocation, rationale, minute
FROM ballot WHERE run_id = 'RUN';
```

L'archive graph est un **journal analytique** : aucune interprétation causale ne doit être inférée uniquement à partir d'un graphe esthétique. Pour les analyses statistiques, compare les distributions initiales, les événements, les variations chronologiques et des répétitions sous différentes graines aléatoires.

## Confidentialité et limites

Les données restent **uniquement sur le Mac**, sauf les interactions que tu choisis de soumettre explicitement à Jev. Les corps de ces requêtes Jev contiennent un court contexte cognitif et des souvenirs : n'y injecte pas d'informations privées réelles. `data/`, `.env` et la base SurrealDB ne sont pas publiés. Le graphe ne produit pas d'inférences génératives à lui seul ; il enrichit la mémoire et l'explicabilité. La bonne synchronisation des écritures est contrôlée par le compteur de l'interface.

### Révisions de croyances

```sql
SELECT minute, proposition, before, after, source
FROM belief_revision WHERE run_id = 'RUN' ORDER BY minute;
```

Les changements successifs sont des nœuds immuables du graphe (contrairement au nœud `belief` qui porte la confiance courante). La table SQLite `belief_history` réplique ce journal pour préserver l’analyse même lorsque SurrealDB est arrêté.

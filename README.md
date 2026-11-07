# Salem-sur-Brume — Smallville Local, société d'agents Apple + Jev

**25 habitants dans une ville close**, inspirée de la défiance religieuse des procès de Salem. Simulation exploratoire de comportements, croyances, inégalités, alliances, conatus et élections. Tout est exécuté **localement sur Mac Apple silicon**, à l'exception des décisions TypeSafe/Jev que l'utilisateur active explicitement. Le modèle génératif de dialogues est **Apple Foundation Models sur l'appareil** lorsqu'il est disponible ; sinon un serveur MLX local peut être configuré, ou un mode scénarisé transparent.

**Interface :** `http://127.0.0.1:8000` · **Graphe SurrealDB :** `127.0.0.1:8001` · **Jev :** `https://api.typesafe.ai/v1/systemone` (seule API externe utilisée par la simulation).

## Mise à jour sur ton Mac (sans supprimer tes souvenirs ni ta clé)

**À chaque modification publiée sur GitHub :**

```bash
cd ~/smallville-local
git pull --ff-only origin main
./Lancer.command
```

Arrête d'abord l'ancien serveur avec `Ctrl+C`, puis relance `./Lancer.command`. **Il n'est pas nécessaire de réinstaller Python, Apple FM ou de ressaisir la clé Jev** si les dépendances sont déjà présentes. `.env`, `.venv`, les sauvegardes SQLite et SurrealKV, et les paramètres locaux sont exclus de Git.

**Une seule fois après le passage de la V1 à cette version :**

```bash
cd ~/smallville-local
./Installer.command
```

L'installateur **préserve la clé déjà présente dans `.env`** : appuie simplement sur Entrée à la question de la nouvelle clé. Il initialise en outre les identifiants locaux de SurrealDB et propose son installation via Homebrew (`brew install surrealdb/tap/surreal`). L'installation de SurrealDB et celle du SDK Apple sont des téléchargements *ponctuels* ; l'application n'utilise aucun CDN, aucune API d'IA externe hors Jev et ne télécharge jamais de modèle MLX automatiquement.

Sur Apple silicon M1/M2 avec 16 Go, le moteur 2D/SQLite/SurrealDB est léger. **Apple Foundation Models exige macOS 26+, Xcode 26+ et Apple Intelligence activé** ; le diagnostic `./Diagnostiquer.command` précise la situation. L'interface affiche « Dialogues scriptés » lorsque le modèle Apple est indisponible, sans faire croire qu'un LLM tourne.

## Univers et institutions

La carte passe à **44 × 32 cases** : église, presbytère, mairie, école, grenier, marché, dispensaire, taverne, champs et place des assemblées. Les 25 personnages ont des biographies et des rôles différenciés (prêtre, prédicateur, guérisseuse, sceptique, riche propriétaire, notable, garde impulsif, journalier pauvre, etc.). Les **capitaux initiaux suivent une loi lognormale** ; l'agressivité, le style cognitif et d'autres dispositions sont tirés de normales tronquées, avec certains profils volontairement typés. Aucun de ces paramètres n'est un jugement sur une personne réelle.

La commune possède une trésorerie et un grenier. Les agents ont faim, revenus, réserves, santé, intérêts, liens de solidarité, peur et **conatus**, formalisé comme une dynamique de préservation des conditions d'existence. Le moteur gère les achats, salaires, échanges de secours et conserve la masse monétaire. **Meurtre, exécution et actions violentes sont interdits par la physique normative du monde** (aucune action létale proposée).

**Demain, à 16 h simulées**, une élection désigne le nouveau maire parmi sept candidats ; les **25 habitants votent également** leur proposition de répartition de 2 500 écus entre les habitants. La décision finale utilise les propositions individuelles, les relations, besoins, croyances, valeurs politiques et, si disponible, la préférence récente évaluée par Jev. Chaque bulletin et le résultat complet sont enregistrés ; la somme des allocations reste exactement égale au budget voté. La simulation organise aussi bien des dialogues à deux que de plus rares conversations de 3 à 5 habitants.

## Le cerveau d'un habitant : mémoire, émotion, vision du monde, saillance

Pour chaque personnage sont persistés :

1. **Traits relativement stables** (Big Five, raisonnement, agressivité, religiosité, crédulité, soupçon, tolérance, générosité, ambition), modifiés lentement par consolidation.
2. **Conatus, besoins et émotions** (`fear`, `anger`, `compassion`, `curiosity`, `shame`, `joy`) avec décroissance vers des lignes de base individuelles.
3. **Réseau de représentation du monde**, distinct des faits objectifs (`religious_authority`, `empirical_evidence`, `collective_solidarity`, `institutional_order`, `tolerance_of_dissent`, `perceived_witchcraft_risk`, `political_equality`).
4. **Réseau de saillance** (`foi`, `sorcellerie`, `politique`, `survie`, `inegalites`, `relations`, `preuves`) qui oriente l'attention et la récupération des souvenirs.
5. **Souvenirs autobiographiques, croyances confidentielles et leur historique de révisions**, relations dirigées de confiance, tensions et intentions passées.

La sélection d'une mémoire tient compte de l'importance, de la récence, des mots de la scène et **de la saillance actuelle**. Une croyance n'est jamais assimilée à un fait universel. Le simulateur enregistre le passage de confiance *avant → après* avec une source précise.

### Répartition des tâches Apple / Jev

**Jev 1.14** peut être activé à partir de l'interface : le système programme des **jugements cognitifs récurrents** pour les 25 habitants (avec étalement, file d'attente et quotas), après certains événements saillants et lors de rencontres. Chaque requête regroupe typiquement **jusqu’à neuf jugements indépendants** sur la prochaine intention, l'émotion, la priorité politique, la qualité des preuves disponibles, l'observation directe, le risque social et la préférence électorale. Les rencontres interrogent également Jev sur le ton, la menace perçue et les éléments corroborant une affirmation. Un appel à Jev ne peut pas créer directement un événement ; **des transitions Python bornées transforment ses jugements en décisions et révisions auditables**.

**Apple Foundation Models**, ou MLX local, génère les dialogues et certaines réflexions. **Le contexte est reconstruit à chaque prise de parole et à chaque jugement Jev**, jamais figé : souvenirs propres, croyances personnelles, histoire relationnelle, état matériel et conatus, traits, émotions, saillance, vision du monde, intention actuelle et, si disponible, voisinage issu du graphe SurrealDB. L'autre agent ne transmet pas ses secrets au premier. **Il ne s'agit pas d'une nouvelle génération Apple à chaque minute simulée** : la génération intervient lors des échanges et réflexions, le moteur du monde évoluant entre-temps.

Sans Apple/MLX disponible, le moteur de secours génère des répliques déterministes et le présente clairement. Sans Jev, les décisions suivent une politique locale de repli : les personnages ne sont alors pas pilotés par un modèle décisionnel externe.

## Crédit Jev de 5 $ : garde-fou prudent, utilisation moins restrictive

Pour ne pas épuiser le crédit d'expérimentation, Jev est **désactivé au lancement** et reste activé uniquement après validation dans l'interface. Son coût est suivi dans SQLite et **n'est jamais remis à zéro** par le bouton Reset, y compris à travers différentes simulations.

| Paramètre | Plafond de la V3 |
|---|---:|
| Réserve budgétaire cumulée interne | **4,50 USD** |
| Appels cumulés | 12 000 |
| Appels par journée simulée | 700 |
| Appels par 24 heures réelles | 6 000 |
| Intervalle minimal entre réservations | 1 seconde |
| Taille du payload Jev | 12 000 octets |

Le tarif TypeSafe utilisé pour l'estimation est **0,042 USD par million de tokens d'entrée** (modèle Jev 1.14). Chaque demande est **réservée avant l'envoi** avec une estimation prudente (tokens estimés à partir des octets, surcharge et marge) ; tout appel potentiellement facturé, même interrompu, conserve sa réservation. **Les limites protègent uniquement cette application, pas les autres usages de ta clé ni le solde réel TypeSafe.** Vérifie périodiquement ton compte TypeSafe ; la facturation peut changer. Aucun test automatique n'émet de requête payante, et aucune requête Jev ne se relance après une erreur réseau.

Le modèle décide de jugements, **pas de la vérité des croyances** : les scores sont subjectifs et non validés comme des probabilités psychologiques humaines.

## Base de données et corpus en graphe

Le moteur conserve l'état et les journaux dans `data/smallville.sqlite3`. La **file d'événements transactionnelle** synchronise les observations vers un serveur SurrealDB **exclusivement local** : nœuds `agent`, `memory`, `belief`, `belief_revision`, `state`, `event`, `dialogue`, `reflection`, `ballot`, `assembly`, et liens `knows`, `remembers`, `holds`, `revised`, `influenced`, `uttered`, `heard`, `casts`, `voted_for`, etc. Chaque expérience possède un `run_id` distinct.

Si SurrealDB ne démarre pas, le monde reste utilisable et toutes les opérations s'empilent en SQLite pour être synchronisées au prochain démarrage. Le graphe aide à reconstituer chronologies, influences, propagation des rumeurs et coalitions ; sa consultation est facultative pour la cognition. Exports : interface « Exporter le corpus JSON », `/api/graph`, ou `python3 scripts/export_graph.py` (SurrealDB local requis). Voir [docs/GRAPH.md](docs/GRAPH.md).

## Interface et expériences

- Boutons **Démarrer/Pause**, pas à pas, accélération, progression vers le scrutin, **Réinitialiser**.
- Carte 2D, social network, journaux d'événements, concours électoral et répartition budgétaire.
- Inspecteur individuel : patrimoine, conatus, traits, **vision du monde**, émotions, saillance, derniers jugements Jev, mémoires, croyances, **historique des révisions**, relations.
- **Introduire une information ou suggérer une croyance** : à un agent précis ou à l'ensemble du village. Ce sont des observations subjectives, non des faits imposés. Le système peut ensuite solliciter Jev pour leur examen si activé.
- Reset crée un **nouveau run**, garde le journal budgétaire Jev et les anciens graphes SurrealDB. En cas d'échanges en cours, le reset attend leur fin pour éviter d'écrire des dialogues dans le mauvais run.

## Tests et diagnostics

```bash
cd ~/smallville-local
python3 -m unittest discover -s tests -v
python3 app.py                         # sans auto-démarrage SurrealDB
# ou ./Lancer.command                 # avec démarrage automatique SurrealDB
```

Les tests utilisent un faux backend Jev et **n'ouvrent aucun réseau public**. La disponibilité réelle d'Apple FM et de TypeSafe ne peut être testée que sur ton Mac/avec ton compte ; le fait que ces tests passent ne prouve pas la qualité psychologique des modèles.

### Références

[Apple Foundation Models SDK Python](https://github.com/apple/python-apple-fm-sdk) · [TypeSafe Jev](https://docs.typesafe.ai/) · [Skill TypeSafe](https://github.com/typesafe-ai/skills) · [SurrealDB](https://surrealdb.com/docs/)

Projet de recherche exploratoire sous licence MIT. L'application ne stocke pas les clés dans le dépôt public et ne transmet à Jev que le contexte choisi pour chaque jugement quand tu l'actives.

## V4 — Direction artistique et mémoire relationnelle (Salem vivant)

La carte a été redessinée en **Canvas 2D procédural**, sans ressources distantes :
maisons et institutions individualisées, clochers, toitures, marché, ruelles, arbres,
brume légère animée, éclairage de jour/nuit et personnages vêtus. L'interface adopte
une esthétique éditoriale inspirée des archives anciennes. Les mouvements sont
réduits automatiquement si `prefers-reduced-motion` est activé dans macOS.

### SurrealDB n'est plus seulement un entrepôt

Le module `smallville/graph_memory.py` prépare un **dossier de preuves subjectif**
pour chaque agent à partir des traversées SurrealQL suivantes :

- `agent → remembers → memory` : souvenirs liés à des épisodes effectivement vécus ;
- `agent → holds → belief` : croyances subjectives et degré de certitude ;
- `agent → revised → belief_revision → updates → belief` : évolution de croyances ;
- `agent ← influenced` : personnes et messages qui ont influencé cet agent ;
- `agent → knows` : relations dirigées et niveaux de confiance ;
- `memory / belief / event → about → theme` : indexation thématique de nouvelles observations.

Un algorithme de récupération limite et classe les éléments selon la pertinence
lexicale, le thème actuellement saillant, la récence et l'importance d'un souvenir.
**Seules les observations que l'agent pouvait connaître entrent dans son contexte** :
le graphe complet de l'observateur n'est jamais transmis à la pensée de l'agent.
Les requêtes Apple Foundation Models et Jev reconstruisent leur contexte à chaque
inférence. Ce dossier fait donc évoluer la conversation et le jugement en fonction
de l'histoire du personnage, sans entraîner un modèle ni prétendre que SurrealDB
est un modèle neuronal.

L'inspecteur affiche maintenant l'onglet « Traces » : chemins d'attribution des
croyances et changements de confiance. Le panneau « Archives vivantes » montre
les souvenirs et croyances sélectionnés pour un agent. Le graphe social peut
basculer vers le réseau de transmission des rumeurs lorsque SurrealDB est connecté.

Deux nouveaux points d'accès locaux :

- `GET /api/insight?agent=alice` : dossier subjectif borné d'Alice ;
- `GET /api/influences` : chaînes de rumeurs visibles par le chercheur (provenances,
  longueurs de cascade, diffuseurs, premiers témoins supposés).

Quand SurrealDB est indisponible ou en cours de synchronisation, l'application
conserve un **repli SQLite**. L'interface indique la provenance des traces et
n'invente pas de liens non observés. Le transfert SurrealDB passe exclusivement par
`127.0.0.1:8001`; la seule requête cloud potentielle reste Jev sur activation.

### Mise à jour d'une installation existante

```bash
cd ~/smallville-local
git pull --ff-only origin main
./Lancer.command
```

Aucune réinstallation n'est nécessaire si l'environnement local fonctionnait déjà
avec la version V3. Le fichier `.env`, la clé TypeSafe et les bases `data/` ne sont
pas suivis par Git. Pour une installation qui ne dispose pas de SurrealDB,
lancer une seule fois `./Installer.command` puis `./Lancer.command`.

### Vérifications

- `python -m unittest discover -s tests -v` : tests de mémoire et provenance,
  régressions socioéconomiques, budget Jev et confidentialité ;
- `node --check static/app.js` : vérification syntaxique du moteur graphique ;
- `curl http://127.0.0.1:8000/api/insight?agent=alice` : inspection locale des
  traces de l'agent choisi.

La nouvelle direction artistique est implémentée en code, mais doit être évaluée
visuellement dans un navigateur sur Mac : une validation pixel-par-pixel du rendu
n'a pas été possible dans l'environnement de test.

### SurrealDB affiche « hors ligne » alors que `/health` répond

Les versions antérieures au correctif de bootstrap n'initialisaient pas le
namespace `smallville` et la base `society` : la première requête SQL échouait
avec `The namespace 'smallville' does not exist`, bien que SurrealDB ait démarré.
Le démarrage V4.1 crée désormais ces deux ressources automatiquement par une
requête root locale **sans** en-têtes `Surreal-NS` et `Surreal-DB`, puis vérifie
la connexion normale. L'opération utilise `IF NOT EXISTS` : elle ne supprime
aucune donnée existante. La file SQLite `graph_outbox` reprend ensuite son
transfert vers le graphe ; une file de plusieurs milliers d'événements peut
prendre un moment à se vider. Vérification :

```bash
curl -s http://127.0.0.1:8000/api/health | python3 -m json.tool
```

La valeur `surrealdb.status` doit devenir `connecté` ; `pending` diminue
progressivement. Aucune modification de `.env` ni réinstallation n'est requise.

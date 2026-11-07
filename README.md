# Smallville Local — six intelligences dans un monde fermé

Un village interactif en 2D accessible sur **http://127.0.0.1:8000**, destiné à un Mac Apple silicon M1/M2 avec 16 Go de mémoire unifiée. Le monde, les souvenirs, la mémoire relationnelle, l'état psychologique et la représentation graphique tournent localement. **La seule API distante de l'application est Jev (TypeSafe), désactivée par défaut.**

## Démarrage sur Mac

1. Décompresse le ZIP, puis ouvre **`Installer.command`** dans le Terminal. Si macOS bloque le fichier, fais clic droit → Ouvrir. Si nécessaire : `chmod +x Installer.command Lancer.command`.
2. Saisis ta **clé TypeSafe Jev** à l'invite masquée. Elle est enregistrée dans `.env`, permissions `600`. Elle n'est jamais transmise au navigateur et n'est pas incluse dans le ZIP généré.
3. Pour l'IA Apple, accepte l'installation facultative de `apple-fm-sdk` **si** tu disposes de macOS 26+, Xcode 26+ et d'Apple Intelligence activé (Mac compatible).
4. Ouvre **`Lancer.command`**. L'interface s'ouvrira sur `http://127.0.0.1:8000`.
5. Clique sur **Démarrer**, puis sur un habitant. Les onglets « Psyché », « Mémoire », « Croyances » et « Relations » affichent les états individuels. Tu peux introduire une information **privée** à un personnage et observer comment elle se diffuse.
6. Pour tester Jev, active volontairement **Utiliser Jev pour juger les rencontres**. Sans activation, **zéro requête Jev**.

**Important :** l'installation facultative du SDK Apple utilise PyPI (téléchargement ponctuel de paquets). Une fois installé, l'application n'effectue pas de requête externe vers PyPI, OpenAI, Apple ou Hugging Face. Le modèle système Apple peut requérir son téléchargement et son activation préalable par macOS/Apple Intelligence ; il est hors du contrôle de l'application. L'application n'emploie jamais Private Cloud Compute. Le serveur MLX, s'il est activé, est strictement limité à `127.0.0.1:8080` et aucun modèle n'est téléchargé automatiquement.

## Trois modes cognitifs

| Mode | Conditions | Comportement |
|---|---|---|
| `apple` (préféré) | macOS 26+, Xcode 26+, Apple Intelligence, `apple-fm-sdk` | Dialogue et réflexion générés **sur le Mac**, via une session fraîche par interlocuteur et mémoire persistée séparément. |
| `mlx_local` | Serveur MLX déjà disponible sur `127.0.0.1:8080` et modèle local déjà présent | Dialogue généré localement ; aucun appel vers une API de cloud. |
| `scripted` | Python 3.10+ | Dialogues de secours scénarisés, simulation dynamique réelle mais **pas d'IA générative**. |

Le mode `auto` tente Apple, sinon revient à `scripted` en le signalant. L'installation ne prétend jamais que le modèle Apple fonctionne si le SDK ou le modèle système ne répond pas. Pour sélectionner manuellement le mode, copie `data/settings.example.json` vers `data/settings.json` puis édite ce dernier en définissant `"backend": "apple"`, `"mlx_local"` ou `"scripted"`, puis redémarre.

**Alternative MLX :** après avoir placé localement un modèle compatible MLX et installé `mlx-lm`, démarre le serveur depuis un autre terminal, par exemple `mlx_lm.server --model /chemin/local/vers/le/modele --port 8080`, puis sélectionne `backend: "mlx_local"` et relance Smallville. En l'absence du serveur, les dialogues reviennent explicitement au mode scénarisé. Un M1/M2 16 Go est adapté à un modèle compact quantifié de quelques milliards de paramètres, mais le débit réel doit être mesuré sur ta machine. **Attention :** la disponibilité exacte de l'endpoint et de l'option `--port` varie suivant la version de `mlx-lm` ; contrôle l'aide `mlx_lm.server --help`.

## Architecture cognitive

Chaque agent possède :

- un vecteur de traits Big Five (`openness`, `conscientiousness`, `extraversion`, `agreeableness`, `neuroticism`), initialisé différemment puis **lentement modifiable** ;
- des états transitoires : humeur, stress, énergie, solitude, sociabilité ;
- des croyances privées avec confiance subjective et source, **sans omniscience** ;
- des souvenirs autobiographiques horodatés, filtrés par importance, pertinence et récence ;
- des relations **dirigées** envers les cinq autres (confiance, affinité, tension et familiarité) ;
- des objectifs individuels et des activités spatiales.

Un moteur discret déplace les habitants sur un monde fini `32 × 24`. Une rencontre peut générer deux répliques : l'agent A s'exprime à partir de **ses** données, puis B se répond à partir de **ses** données et de ce qu'il a entendu. Si l'agent A partage un savoir inconnu de B, ce dernier peut l'ajouter comme croyance, avec provenance et incertitude. La dynamique sociale est persistante dans SQLite. Une consolidation quotidienne modifie les traits au plus de quelques millièmes ; le moteur note avant/après.

### Répartition Apple / Jev

- **Apple Foundation Models** (local) : formulation des dialogues et bilan autobiographique. Les prompts sont reconstruits à partir de mémoires privées sélectionnées, sans transférer les états intimes des autres agents.
- **Jev** (distant, optionnel) : uniquement **une appréciation sociale** lors d'une rencontre : tonalité (`Choice`), sentiment de menace (`Noul`), raison de rétablir la confiance (`Noul`), degré de blessure (`Score`). Ces quatre questions partagent **une seule requête**. L'action finale et la mise à jour des relations sont calculées en Python d'après une table de décision lisible dans `smallville/jev.py`.
- **Moteur déterministe** : déplacements, règles de mouvement, mise à jour des besoins, validation des actions, archivage des souvenirs, conservation des budgets.

Il s'agit d'une **simulation exploratoire** : le sentiment de vraisemblance ne constitue pas une validation des modèles psychologiques humains. Les jugements Jev sont des sorties du modèle, non des probabilités empiriques de comportements humains.

## Protection stricte du budget de 5 €

La facturation publiée le 7 novembre 2026 pour `jev-1.14.0` est **0,042 USD par million de tokens d'entrée** ; sortie non facturée. L'application utilise ces hypothèses et prévoit des limites bien plus basses que ton crédit disponible :

- Jev **désactivé au démarrage**, même si activé pendant la session précédente. Aucun test automatique n'envoie de requête facturée.
- Budget interne par installation **0,75 USD**, contre un crédit disponible d'environ 5 € ; limite modifiable en éditant `data/settings.json`, **maximum autorisé 4 USD**.
- **100 appels maximum au total**, **8 par jour simulé**, **24 sur 24 h réelles** et **30 secondes minimum entre deux appels**.
- Contexte Jev abrégé (quelques souvenirs et croyances), payload limité à **7 000 octets** ; **quatre questions regroupées en une seule requête**.
- Pas de réessai automatique, pas d'images Jev par défaut, pas de requêtes de diagnostic payantes.
- Chaque tentative est **réservée dans SQLite avant émission** ; toute erreur réseau conserve sa réserve faute de preuve de non-facturation. Le journal `jev_ledger` n'est jamais remis à zéro lors du reset du monde.

Le budget affiché correspond à une **estimation prudente locale, pas au solde officiel TypeSafe**. Aucune application cliente ne peut garantir le montant total du compte si les tarifs évoluent, si d'autres applications utilisent la clé ou si le fournisseur facture autrement ; surveille le console TypeSafe. L'interface expose le budget et les quotas, et Jev reste facultatif.

## Fonctions disponibles

- Démarrer/pause, pas à pas, vitesse variable, sauvegarde automatique, export JSON.
- Portraits et positions sur carte canvas **sans CDN** ni bibliothèque JS externe.
- Six agents différenciés, interactions sociales persistantes, réseaux de confiance dirigés.
- Information privée injectée à un seul personnage, propagation des croyances et mémoire autobiographique.
- Consolidation des traits une fois par jour simulé, scènes et évaluations consignées.
- Remise à zéro des souvenirs et du monde **sans effacer l'historique des dépenses Jev**.
- Mesures de coûts estimatifs et statut réel du backend (Apple / MLX / scripté).

Pour connaître la compatibilité exacte de ton Mac sans accès réseau, ouvre **`Diagnostiquer.command`**.

## Dépannage et limites

- `Apple indisponible` : vérifie `sw_vers`, Xcode 26+, l'activation d'Apple Intelligence et `.venv/bin/python -m pip show apple-fm-sdk`. Les Mac M1/M2 sont Apple silicon, mais la disponibilité dépend de l'OS et du modèle système.
- Si le SDK Apple n'est pas encore installé, l'interface marche en mode scénarisé, mais les répliques **ne sont pas générées par IA**.
- Si aucune conversation n'apparaît au début, laisse les personnages se rapprocher sur la place : le simulateur impose proximité et temps de repos entre rencontres.
- En cas d'interruption du processus pendant la génération, la conversation peut être partiellement écrite ; SQLite conserve les événements déjà produits.
- Par conception, l'historique de simulation n'est pas encore un outil de validation psychologique quantitative. La reproductibilité stricte des sorties LLM n'est pas garantie.
- Les personnages ne se parlent pas avec des modèles séparés chargés simultanément : ils partagent le même moteur neuronal local et gardent des historiques distincts en base.
- Les appels d'images Jev 1.14 ne sont pas activés dans cette V1 : inutile pour connaître les coordonnées d'un monde 2D déjà structurées, et source de coûts supplémentaires.
- La récupération d'un modèle MLX et l'installation de paquets nécessitent une préparation ponctuelle ; le simulateur, lui, n'utilise que la boucle locale et l'API Jev si elle est explicitement activée.

## Tests et exécution en ligne de commande

```bash
python3 -m unittest discover -s tests -v
python3 app.py
# Ouvrir http://127.0.0.1:8000
```

Si tu souhaites protéger encore davantage la confidentialité, garde Jev désactivé : tous les autres composants sont locaux. La clé `.env` ne doit jamais être placée dans un dépôt public ni partagée.

### Références officielles

- [Documentation Jev / System One](https://docs.typesafe.ai/api/system-one)
- [Modèles et tarifs TypeSafe](https://docs.typesafe.ai/models)
- [Jev 1.14](https://typesafe.ai/blog/jev-1-14)
- [Skill TypeSafe](https://github.com/typesafe-ai/skills/tree/main/skills/typesafe-ai)
- [Apple Foundation Models pour Python](https://github.com/apple/python-apple-fm-sdk)

Le code applicatif est distribué sous licence MIT. Il n'inclut aucun modèle neuronal propriétaire ni aucun poids Apple/MLX.

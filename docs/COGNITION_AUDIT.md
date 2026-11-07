# Audit scientifique des agents — 7 novembre 2026

## Provenance

Analyse de `Salem_Corpus_20261107_150305.zip` (quatre `run_id`, états et journaux SQLite, projections SurrealDB). Les données sont **fictives**, incomplètes et ne peuvent pas être interprétées comme une modélisation validée de personnes réelles. Les sauvegardes SQLite ne conservent qu’un run après un Reset, contrairement au graphe.

## Constats falsifiables

- 25 agents dans le run actif `4851caf59adb`; minutes 480 à 631; 7 rencontres, 14 répliques et aucun vote ni conversation de groupe.
- **97 tentatives Jev, 0 réponse réussie** ; échecs SSL `CERTIFICATE_VERIFY_FAILED` (certificat racine manquant dans le contexte TLS de Python). Réserve comptable d'environ 0,052 USD, ce qui ne prouve pas une facturation effective TypeSafe.
- Les 25 agents ont `decisions=0`, `revision_count=0`, `intention=observe` ; les révisions de croyance du corpus sont uniquement des premières acquisitions (`before=null`).
- Capital initial : Gini 0,572 ; les 5 habitants les plus riches détiennent 64,5 % du capital. Aucune journée économique complète dans la partie actuelle, donc ce n'est **pas** un résultat émergent.
- 600 relations dirigées préinitialisées pour 25 agents ; seulement sept paires se rencontrent dans le run actif. La corrélation proximité religieuse/confiance (r≈0,56) est principalement **imposée par le générateur**.
- Défectuosité causale : une croyance pouvait se transmettre sans avoir été énoncée. Exemple à la minute 620, Alice évoque l'interdiction de meurtre mais le graphe enregistrait la transmission d’une rumeur de guérison. Le correctif V5 exige une preuve de communication (Jev si disponible, chevauchement lexical conservateur sinon).
- Exemples d'incohérence des dialogues : plusieurs réponses Apple sont des refus génériques, le discours copie celui de l'interlocuteur et des mentions répétitives de la charte surgissent hors contexte.

## Système de planification recommandé (à implémenter et évaluer, pas présent dans V5 hotfix)

Architecture hybride **BDI + mémoire prospective + options temporelles**. Le réseau de saillance détermine ce qui réclame une délibération ; la mémoire épisodique et SurrealDB fournissent les faits subjectifs ; un module prospectif imagine des futurs *hypothétiques*, jamais recopiés comme faits ; un exécutif conserve les projets et engagements ; Jev estime les préférences subjectives, la faisabilité perçue, le risque social et les motifs de révision ; Python valide les lois du monde, les ressources et les effets d'actions.

**Objets à rendre persistants** :

- `goal`: but à horizon jours, intensité, satisfaction, conditions d'abandon ;
- `intention`: engagement choisi, justification et alternatives rejetées ;
- `project`: décomposition en tâches, dépendances, échéances, participants, ressources, statut ;
- `appointment`: heure et lieu convenus, état de confirmation et de présence ;
- `anticipated_event`: projection subjective et niveau de plausibilité, séparés des souvenirs avérés ;
- `plan_revision`: plan précédent, nouvelle version, événement causal et préconditions violées ;
- `deception`: différence entre proposition privée, croyance du locuteur, énoncé public et objectif intentionnel de tromper.

**Boucle cognitive** : besoin/événement → attention → rappel épisodique et social propre à l’agent → simulation de 2–3 options sur un horizon borné → Jev regroupe les jugements d'adéquation et risque → décision stochastique bornée avec inertie des engagements → agenda exécutable → constat → feedback en mémoire et révision conditionnelle. À chaque étape, consigner le contexte référencé, les plans écartés et les transitions avant/après.

**Échelles de temps** : minute pour physique, 10–30 min pour réactions sociales, 60–180 min pour réévaluation d’objectifs, nuit pour plan quotidien ; replanification à événement saillant seulement. Garantir des budgets Jev (limite quotidienne, coût réservé, échecs sans retry). Éviter les calendriers identiques d'une population entière.

**Mensonges/lois** : distinguer erreur sincère, dissimulation et mensonge intentionnel ; les accusations ou projets illégaux peuvent être simulés dans la mémoire et faire l'objet de sanctions. Le meurtre et l'exécution restent physiquement interdits tant que la règle `murder_forbidden` s'applique : ne pas faire croire qu'un meurtre est implémenté.

**Validation** : tester l'atteinte des objectifs, l'existence d'étapes exécutées dans l'ordre, la stabilité/révision justifiée des plans, la cohérence des dialogues avec les croyances personnelles, la séparation des rumeurs et des faits, le nombre de rendez-vous honorés, la diversité des stratégies, les chemins de diffusion attestés et les effets de perturbations contrôlées (Jev ON/OFF, mémoire ON/OFF, planning ON/OFF), avec plusieurs graines et horizons >10 jours.

## Références

- Park et al. (2023), [Generative Agents](https://arxiv.org/abs/2304.03442), UIST.
- Rao & Georgeff (1995), [The Semantics of Intention Maintenance](https://www.ijcai.org/Proceedings/95-1/Papers/092.pdf).
- Bratman (1987), *Intention, Plans, and Practical Reason*.
- Miller & Cohen (2001), [An Integrative Theory of Prefrontal Cortex Function](https://doi.org/10.1146/annurev.neuro.24.1.167).
- Schacter, Addis & Buckner (2007), [The Prospective Brain](https://doi.org/10.1038/nrn2213).
- Sridharan, Levitin & Menon (2008), [Switching Between Executive and Default Mode Networks](https://doi.org/10.1073/pnas.0800005105).
- Sutton, Precup & Singh (1999), [Temporal Abstraction / Options](https://doi.org/10.1016/S0004-3702(99)00052-1).
- Sumers et al. (2024), [CoALA](https://arxiv.org/abs/2309.02427).
- Larooij & Törnberg (2026), [Validation Is the Central Challenge](https://doi.org/10.1007/s10462-025-11412-6).

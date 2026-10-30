# PAM Financial Systems R1 — Clauses candidates et nombres réellement fondés (P01–P12)

**Version :** R1-APPROVAL-CLAUSE-CANDIDATES-v0.1, 2026-10-30
**Rôle / WO :** Program Manager / WO-FS-R1-POLICY-CLAUSE-CANDIDATES
**Statut :** PROPOSAL_ONLY / FINANCIAL_POLICY_NOT_APPROVED / INDEPENDENT_FINANCIAL_REVIEW_NOT_RUN / REAL_CALIBRATION_NOT_RUN / MODEL_NOT_CHANGED / NOT_LOADED / INTEGRATED_ACCEPTANCE_NOT_RUN
**Provenance :** [38 sélections CEO](CEO_THREE_ROUND_SIX_MODE_SELECTIONS_R1_20261030.md), [12 arbitrages CEO](SIX_MODE_FINANCIAL_POLICY_DECISION_PACKAGE_P01_P12_R1_20261030.md), Constitution et contrats techniques réellement consultés. Ceci n'est pas une politique de placement ni une recommandation personnelle.

## 1. État exact des nombres et conflit de méthodes

| Référence observée à la HEAD V2 | Constat réel | Conséquence R1 |
|---|---|---|
| [Constitution §3](../../../../PAM_PROJECT_CONSTITUTION.md) | High-CAGR : plafond **initial exceptionnel ~20 %**, VFV cible **~20 %**, plancher conceptuel **~15 %**, baisse temporaire **35–45 %** tolérable si thèse intacte; avantage attendu conceptuel VFV + **~2 points** société établie et + **~3–4 points** moins établie | Autorité historique dans son périmètre; le projet **12 % normal / 15 % exceptionnel** est distinct et NON APPROUVÉ. Aucune mise à jour V2. |
| [src/allocation_engine.py](../../../../src/allocation_engine.py), lignes 96–98 | HIGH_CAGR_SINGLE_NAME_WATCH_WEIGHT **0.18**, THROTTLE_WEIGHT **0.22**, STRICT_WEIGHT **0.30** | Seuils du moteur V1/ancien, distincts d'un plafond R1 et du maximum initial constitutionnel; **ne pas copier ni fusionner** ces sémantiques. |
| Même code, lignes 55–65 | DEFENSIVE_RESERVE_PCT : Balanced **0.45**, Family-Office **0.20**, Rational-Aggressive **0.05**, High-CAGR **0.0**; MODE_MIN_CAPITAL_SCORE **78/65/60/50** | Aucun de ces chiffres n'autorise un cash stratégique R1, une note universelle d'admission ou une bande d'allocation R1. |
| Même code, lignes 130–184 | mandatory_vfv_percent varie avec le mode et le score; High-CAGR peut retourner **5/10/15/20 %** | Ne pas résoudre tacitement la différence avec le plancher constitutionnel conceptuel ~15 %. Elle demande une revue de sémantique et de portée. |
| [Politique ER V2](../../../../src/expected_return_approved_policy_v1.py) | ORDINARY_COMPOUNDER, **USD, US_GAAP**, version 2026-09-29; croissance mature **0/3/5 %** et multiples P/E terminaux **12/16/20x**, nonpayeur uniquement en route réelle | **Ne pas généraliser** à IFRS, crédit, banque, FPI, biotech ou société payeuse. |
| [Comparateur entreprise–VFV](../../../../docs/contracts/v2/expected_return/COMPANY_VFV_EXPECTED_RETURN_COMPARATOR.md) | Diagnostic pour route PR5E réellement admise, horizon **7 ans**, FX constant, spreads bear/base/bull par même étiquette, aucune probabilité | Ne prouve aucun alpha statistique ni allocation; hors portée = UNAVAILABLE / UNSUPPORTED / SOURCE_CONFLICT. |
| [Classificateur recherche V2](../../../../docs/contracts/v2/capabilities/RESEARCH_PARTICIPATION_CLASSIFIER.md) | FULL_ANALYSIS_ELIGIBLE est un statut de **recherche**, pas d'investissement | Requiert un gate financier séparé. |
| [PI observations](../portfolio/OBSERVATION_AND_ROOM_R1.md) et [contributions](../portfolio/CONTRIBUTIONS_AND_COSTS_R1.md) | Poids visibles possibles; calcul monétaire après contribution exige total de compte, encaisse, devise/date cohérentes et frais connus ou limités | P11B ne doit pas contredire les gardes M3 ni faire passer une vue publique pour un compte vérifié. |

**Règle générale :** mêmes faits/source IDs entre les six modes, quatre étapes DISCOVERY → DEEP_ANALYSIS → STRATEGY_QUALIFICATION → PORTFOLIO_ROOM_AND_DESTINATION. Les cinq piliers QUALITY, DURABILITY, EXPECTED RETURN, CONFIDENCE, PORTFOLIO ROOM restent distincts. Une proposition n'est pas une admission. V1 main reste gelé et V2 challenger.

## 2. Douze clauses candidates à examiner — aucune règle activée

### P01 — Concentration High-CAGR directe

**Clause proposée :** pour un compte et un dénominateur réellement délimités, comparer les poids **directs** par entreprise économique à **12 % normal et 15 % exceptionnel**, après regroupement justifié des éventuelles actions/ADR/CDR du même émetteur. Les ETF demeurent un contrôle de chevauchement **distinct**, sans addition automatique au plafond. Les positions dépassant une cible par appréciation déclenchent une revue/limitation des apports, **jamais une vente automatique**. Un pourcentage Blossom peut caractériser le poids actuellement affiché si le dénominateur de la vue est suffisant; il ne permet pas de simuler le poids post-contribution sans valeur totale du compte.

**À approuver :** le 12/15, l'unité directe exacte, initial vs après contribution, le comportement en cas de données incomplètes et la relation au ~20 % constitutionnel existant. **Cas synthétiques à vérifier :** 11 %, 13 %, 16 %, position appréciée à 20 %, action+CDR, ETF sous-jacent inconnu, valeur monétaire absente.

### P02 — Gate commun de preuves et critères économiques sectoriels

**Clause proposée :** vérifier identité/date/classe de l'émetteur, sources et droits, liquidités réelles, levier/refinancement, dilution, réinvestissement, qualité/durabilité, valorisation et contre-thèse. Utiliser la méthode économique pertinente : logiciel, industrie/cycle, semiconducteurs, finance/crédit, FPI, biotech, ETF. Les indicateurs non comparables ne sont **pas** remplacés par un score universel. Séparer une analyse complète de l'admission d'un instrument à l'investissement.

**À approuver :** le seuil des faits critiques par famille, les exceptions et le statut de qualification. **Tests proposés :** cash d'activité de crédit vs cash distribuable, FPI avec FFO incomplet, société IFRS, profits cycliques à pic, refinancement menacé, source contradictoire. Aucun seuil chiffré sectoriel actuellement validé.

### P03 — ER indisponible et exception renforcée

**Clause proposée :** rechercher d'abord un rendement économique forward comparable et suffisamment vérifié; sinon continuer une recherche proportionnée et laisser EXPECTED_RETURN_UNAVAILABLE. **Aucune allocation individuelle chiffrée ordinaire** ne découle de l'absence d'ER. Une proposition conditionnelle exceptionnelle ne sera possible **qu'après un contrat spécifique approuvé** et preuve renforcée; la forme de cette exception reste à décider (revue humaine seulement ou allocation conditionnelle chiffrée). Ne jamais substituer rendement historique ou BEAR/BASE/BULL sans probabilités à une espérance vérifiée.

**À approuver :** conditions de véritable impossibilité, périmètre et droit exact de l'exception. Préserver VFV comme benchmark/repli normal de High-CAGR dans sa portée.

### P04 — Balanced multi-actifs

**Clause proposée :** rechercher actions/FNB et obligations souveraines de qualité ou corporatives **investment-grade**, y compris FNB obligataires **si admissibles à la plateforme et au compte**. Examiner qualité de crédit, durée, spreads, FX/couverture, frais, liquidité et pertes simultanées des diversificateurs. La baisse **10–20 %** est une **hypothèse de stress**, jamais plafond garanti ni stop-loss. Pas de portefeuille fixe 60/40 ni de réserve stratégique déduite du code V1.

**À approuver après étude :** planchers/plafonds actions, souverains/IG, autres facteurs, qualité/duration, concentration, FX et benchmark. Toutes les bandes numériques = UNKNOWN; la calibration historique et économique **NOT_RUN**. Évaluer différentes répartitions et des chocs taux+actions sans supposer une corrélation stable.

### P05 — Family-Office épargne par compte

**Clause proposée :** la contribution indiquée comme **épargne destinée à l'investissement** est analysée comme investissable sans questionnaire sur le budget familial. Évaluer le **compte désigné**, privilégier actions de qualité et ETF diversifiés, ajouter obligations si résilience réellement améliorée et instrument admissible. Aucun patrimoine familial consolidé ni réserve cash ne peut être inféré. Stress de conception **10–20 %**, non garantie.

**À approuver :** limites de concentration par compte, poids possibles des actifs, FX, risque de crédit, benchmark et exceptions de liquidité déclarées. Aucune plage numérique d'actifs n'est actuellement justifiée.

### P06 — Rational-Aggressive

**Clause proposée :** admission normale des entreprises dont l'économie et le financement sont solides, après scénarios de valorisation nets des coûts et contre-thèse. Les entreprises déficitaires peuvent faire l'objet de **recherche**, mais pas d'admission exceptionnelle sans contrat spécifique approuvé. Concentration future **inférieure à High-CAGR**, **sans plafond numérique fixé**. Stress **35–45 %** seulement comme scénario d'analyse.

**À approuver :** plafond normal/exceptionnel après revue, preuve de financement et asymétrie, conditions de déficits admissibles; aucune tolérance implicite de pertes permanentes.

### P07 — Dividend Harvester et fiscalité transfrontalière

**Clause proposée :** aucun rendement de dividendes minimum universel; distinguer sociétés, ETF et FPI; vérifier dividendes financés par l'économie récurrente, capacité de réinvestissement, bilan, retour de capital, dilution et rendement total. Si le mandat fixe un objectif de revenu **net**, vérifier frais et fiscalité applicables selon **résidence fiscale/pays de l'investisseur**, **type/pays du compte**, **domicile/pays de l'émetteur ou fonds**, **type de distribution**, **véhicule et date**. Les retenues à la source, conventions et crédits d'impôt ne sont intégrés que s'ils sont effectivement applicables et sourcés. Aucun taux fiscal présumé; revenu net = UNKNOWN lorsqu'il manque des données décisives.

**À approuver :** tests de couverture propres au véhicule, limites de diversification, exigences de revenu par mandat et procédure de validation fiscale. Les taux précis exigent des sources officielles, un cas défini et une vérification séparée; **aucun calcul fiscal réel effectué**.

### P08 — Modern Adaptive Browne

**Clause proposée :** étudier les quatre fonctions croissance, déflation/duration, inflation/choc monétaire, liquidité/courte duration. Considérer trois fonctions non liquides à poids positif **seulement sous politique future** et une liquidité structurelle éventuellement **0 %** si explicitement autorisée. Tester inflation, déflation, taux réels, actions/obligations baissant ensemble, change et crise de liquidité; une étiquette or ou obligation ne garantit pas une protection. Stress **10–20 %** : objectif indicatif et non perte maximale.

**À approuver après étude :** bandes de poids min/max des quatre fonctions et conditions du cash à zéro, instruments réellement accessibles, coût de rééquilibrage et benchmark. **Aucune bande 25/25/25/25 ni poids optimisé sans étude**; chiffres = UNKNOWN et analyse historique **NOT_RUN**.

### P09 — Benchmarks économiques distincts des véhicules

**Clause proposée :** catalogue de benchmarks économiques **par mode** choisi et expliqué selon objectif, horizon, devise, distributions, frais et contexte de risque. Le benchmark peut être analytiquement pertinent sans être achetable; la destination d'achat doit satisfaire un contrôle distinct de plateforme/compte. VFV reste la référence High-CAGR principale dans sa portée V2. Aucun comparateur hors modèle ni proxy historique ne fabrique un ER forward.

**À approuver :** noms réels, méthodologie et couverture des catalogues pour Balanced, Family-Office, Rational-Aggressive, Dividend Harvester et Browne, après source/rights/currency check.

### P10 — Action, ADR/CDR, ETF et substitut national

**Clause proposée :** relier action/ADR/CDR au même **émetteur économique** seulement lorsque prouvé, en distinguant ratio de conversion, frais, droits, couverture de devise, spread et fiscalité. Un ETF offre une exposition **indirecte**; un substitut local demeure une **entreprise différente à analyser**. Rechercher mondialement, mais n'inclure dans une répartition de contribution que les instruments **réellement disponibles et autorisés sur le compte/plateforme demandés**. Pas d'autorisation automatique de CFD, options, levier ou autres structures complexes.

**À approuver :** classes de véhicules autorisées par mode, vérification de capacité du courtier et matérialité des coûts. Sinon PLATFORM_UNVERIFIED, sans poids d'achat.

### P11 — Poids affichés Blossom et dénominateur

**Clause proposée :** distinguer 1) poids **visibles sur l'écran** et périmètre de la vue, 2) périmètre **attesté par le CEO** sans certification de compte, 3) valeurs du compte **réellement vérifiées**. Permettre un **calcul descriptif des concentrations à partir des poids affichés** seulement si le périmètre et son dénominateur sont assez établis; conserver les arrondis et les dates. Une somme affichée légèrement différente de 100 % n'est pas automatiquement corrigée. Une capture publique ne démontre ni positions privées ni encaisse. Une **projection monétaire après contribution** exige total du compte, cash, devise et autres éléments pertinents; sinon MONETARY_PROJECTION_UNAVAILABLE. Les statuts réels M3 restent inchangés.

**À approuver :** condition probatoire exacte et distinction entre descriptive/supported/conditional; tests de poids arrondis, vue tronquée, titre sans identité, ETF sans composition, total monétaire inconnu.

### P12 — Stress, apport et cycle de vie

**Clause proposée :** les bandes de baisse sélectionnées (**35–45 %** High-CAGR/Rational-Aggressive; **10–20 %** Balanced/Family-Office/Browne; **15–25 %** Dividend Harvester) sont **scénarios de stress et objectifs de résilience**, pas des maximums de pertes certifiés, stops ou signaux de vente. Toute analyse est **initiée par le CEO**; contributions nouvelles prioritaires, puis étude d'une modification existante seulement sur rupture de thèse, risque matériel ou option supérieure après coûts; vente toujours exceptionnelle, recommandation humaine et aucune exécution.

**À approuver :** mesures de matérialité des dérives et pertes permanentes, règles de calcul du coût net, conditions de revue, différences par mode. Pas de gestion automatique des baisses ni de suivi récurrent.

## 3. Matrice de préparation aux décisions

| Champ | Définition de conception assez précise pour une revue | Preuve / approbation encore requise |
|---|---|---|
| **P01** | Plafonds directs proposés 12/15, ETF séparés | Approbation des nombres + périmètre/direct regroupé et relation au V2 |
| **P02** | Socle de preuves commun + analyse sectorielle | Seuils et cas d'exception par profil; contrôle d'authenticité |
| **P03** | Recherche prioritaire, pas de % individuel normal sans ER | Autorité de l'exception conditionnelle |
| **P04** | Univers obligataire de qualité et ETF si accessibles | **Bandes chiffrées UNKNOWN**, études de stress, benchmark |
| **P05** | Épargne Family-Office investissable par compte | **Bandes UNKNOWN**, benchmark et résilience démontrée |
| **P06** | Qualité et asymétrie, concentration sous High-CAGR | **Cap UNKNOWN** et contrat entreprises déficitaires |
| **P07** | Dividendes couverts, fiscalité selon pays/compte | Couverture par véhicule, limites et **règles fiscales datées** |
| **P08** | Quatre fonctions et cas de cash 0 | **Bandes UNKNOWN**, étude de régimes économiques réelle |
| **P09** | Benchmark économique séparé du véhicule | Catalogues réels et comparabilité vérifiée |
| **P10** | Exposition directe/indirecte/substitut distinct | Instruments effectivement admissibles par mode et plateforme |
| **P11** | Poids affichés sous périmètre/dénominateur prouvés | Validation probatoire et méthode M3 compatible |
| **P12** | Contributions d'abord, vente rare, stress non garanti | Seuil de matérialité/risque, coûts et contrôle humain |

**Conclusion d'audit documentaire :** les contrats R1 peuvent être précisés sans modifier immédiatement V2. **Impossible de qualifier de robustes des fourchettes nouvelles Balanced, Family-Office ou Browne sur la base des seules constantes historiques V1**. Il faut un exercice de scénarios sourcés et de sensibilité sur des instruments autorisés, puis une revue indépendante proportionnée. Les anciennes constantes ne constituent pas une étude de validation.

## 4. Prochaine action et limites

1. **Revue indépendante à mandater** : Architecture & Audit pour portée des autorités/contrats/risques de contournement; Data & Evidence et Investment Research pour sources de qualité économique, fiscalité en cas réel, scénarios de résilience, benchmarks, incertitudes de valorisation. Personne n'a encore émis de conclusion indépendante sur ce dossier.
2. **Produire les hypothèses numériques seulement après sources et stress tests** : examiner diverses compositions/régimes, expliquer période, instrument, devise, frais, corrélations instables et contre-exemples; soumettre des **plages candidates avec justification**, plutôt que remplir les champs UNKNOWN par intuition.
3. **Décision CEO explicite** sur limites, critères, exceptions et toute modification de document CEO_PROTECTED; fusion documentaire distincte de l'approbation de politique.
4. **Développement intégré R1** avec les modules déjà présents (strategy_authority, strategy_research_brief, PI observations, coûts et trace); aucune duplication de moteurs et pas d'activation d'allocation mode avant politique approuvée. Relever ensuite les 36 statuts selon la preuve et faire UNE évaluation d'acceptation globale après assemblage.

**Ce document :** aucune modification de code, de droits/accès, du compte Blossom, des paramètres ChatGPT, de politique protégée, de statut IMPLEMENTED_AND_CHECKED, d'autorisation de trading, de dépenses ou de production. **Tests de marché, source fiscale, risque indépendant, acceptance R1 : NOT_RUN.**

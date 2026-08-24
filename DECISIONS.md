# Investment Automation — Decisions Log

## 🎯 Purpose

This file tracks all major design and investment decisions made in the system.

Each decision must include:
- what was changed
- why it was changed
- expected impact

This ensures long-term consistency and prevents model drift.

---

# 📌 Decisions

## [2026-08-16] Livraison Telegram sortante du rapport compact

### Decision
Ajouter au lanceur Linux une notification Telegram facultative pour le début,
l’échec et la réussite d’une analyse, puis livrer le rapport compact HTML en cas
de succès.

### Reasoning
- Telegram devient l’interface mobile de consultation sans déplacer la logique
  d’investissement hors du modèle existant.
- Les secrets restent dans un fichier local protégé hors Git.
- Une panne de messagerie ne doit jamais transformer un calcul réussi en échec
  ni modifier une recommandation.

### Change
- Nouveau client `scripts/telegram_notify.py`, sans dépendance externe.
- Intégration best-effort dans `scripts/run_investment_analysis.sh`.
- Configuration locale via
  `~/.config/investment_automation/telegram.env` avec permissions `600`.
- Communication sortante seulement dans cette phase; aucune commande Telegram
  entrante, transaction ou modification automatique.

### Expected impact
Visibilité mobile immédiate des runs et accès direct au rapport compact HTML.
Aucun changement au scoring, à l’allocation, au sizing, aux seuils, aux règles
de vente ou aux recommandations.

---

## [2026-08-16] Lanceur opérationnel Linux pour le modèle existant

### Decision
Ajouter un lanceur hôte léger pour exécuter le modèle existant sur le Chromebook
Debian, sans créer un second moteur ni automatiser l’exécution des transactions.

### Reasoning
- Le matériel validé dispose de peu de mémoire et doit exécuter les analyses
  séquentiellement.
- Un verrou explicite évite deux analyses concurrentes et la corruption possible
  des artefacts `latest_*`.
- La validation préalable, le contrôle du rapport produit et les journaux datés
  rendent les échecs visibles sans modifier le calcul d’investissement.

### Change
- Nouveau lanceur `scripts/run_investment_analysis.sh`.
- Mode `high-cagr` et capital `0` par défaut, tous deux configurables.
- Verrou anti-double-run, `validate-inputs`, journalisation, vérification du
  rapport compact et rétention des 20 derniers journaux.
- Aucun `git pull`, rafraîchissement de marché ou ordre de courtage automatique.

### Expected impact
Exécution plus fiable et reproductible sur l’hôte Linux. Aucun changement au
scoring, à l’allocation, au sizing, aux seuils, aux règles de vente ou aux
recommandations.

---

## [2026-08-16] Section compacte « Radar externe » orientée action

### Decision
Remplacer la section compacte « Surveillance externe » par un radar centré sur les décisions réellement utiles à l'utilisateur.

### Reasoning
- L'utilisateur consulte le rapport compact et ignorait cette section parce qu'elle mélangeait politique d'allocation, promotion vers le Core, validation personnelle, ETF externes et longues listes techniques.
- Un candidat surveillé n'est pas nécessairement une recommandation d'achat; cette distinction doit être visible immédiatement.
- La promotion vers le Core n'est pas une action quotidienne requise en mode `high-cagr`, puisque les candidats externes admissibles peuvent déjà recevoir une allocation directe.

### Change
- La section indique d'abord si un titre externe reçoit réellement du capital dans la recommandation courante.
- Elle distingue explicitement les titres « sur le radar » des achats à exécuter.
- Elle affiche le besoin éventuel d'un rapport BNCD/Morningstar et une action utilisateur unique.
- Les trois premiers candidats restent visibles; les listes complètes, promotions, règles et ETF externes sont conservés dans un bloc repliable.

### Expected impact
Lecture quotidienne plus rapide et moins de risque de confondre une idée surveillée avec une recommandation. Aucun changement au scoring, à l'éligibilité, à l'allocation, au sizing, aux promotions ou aux règles de vente.

---

## [2026-08-16] Section compacte de confiance des données orientée utilisateur

**Niveau : 1. Statut : Approuvé, implémenté.**

### Décision

Présenter la fiabilité sous forme de conséquence pratique pour le suivi
habituel et réserver les actions utilisateur aux rappels BNCD/Morningstar et
à la calibration des proxys déjà affichés dans le triage. Conserver les écarts
entre sources comme points de prudence avant un achat important et replier le
détail des sources. Exclure les ETF et benchmarks du taux de fiabilité
fondamentale des entreprises.

### Impact

Le rapport ne demande plus une validation technique champ par champ hors du
workflow réel de l'utilisateur et ne qualifie plus les ETF de données
fondamentales fragiles. Aucun calcul de fiabilité, score, seuil, sizing,
allocation ou signal d'achat/vente n'est modifié.

---

## [2026-08-16] Indicateurs secondaires dans le tableau compact des risques

**Niveau : 1. Statut : Approuvé, implémenté.**

### Décision

Afficher dans le tableau compact toutes les expositions agrégées de clusters
calculées par le moteur, y compris celles sous le seuil d'alerte. Marquer d'une
étoile les risques de niveau élevé afin de préserver une lecture priorisée.

### Impact

Les indicateurs secondaires redeviennent visibles sans restaurer l'ancienne
duplication des expositions par titre. Aucun calcul de risque, seuil, score,
sizing, achat, vente ou montant d'allocation n'est modifié.

---

## [2026-08-16] Tableau compact des risques du portefeuille

**Niveau : 1. Statut : Approuvé, implémenté.**

### Décision

Présenter les risques agrégés du portefeuille dans un tableau à quatre
colonnes : risque, niveau, exposition mesurée et lecture opérationnelle. Les
risques de régime, de clusters cachés et de devise conservent exactement les
mêmes données et seuils d'affichage que la narration précédente.

### Impact

Les expositions sont comparables d'un coup d'œil et leur signification est
explicite. Aucun risque, score, seuil, sizing, achat, vente ou montant
d'allocation n'est recalculé ou modifié.

---

## [2026-08-16] Clarification des deux classements de titres du rapport compact

**Niveau : 1. Statut : Approuvé, implémenté.**

### Décision

Expliquer dans le rapport compact que la liste `drawdown` est un signal de
prix sur des thèses intactes, tandis que les meilleurs titres non alloués
forment un classement général de candidats encore bloqués. Documenter que les
deux populations peuvent se chevaucher et traduire les catégories de blocage
dans un langage courant.

### Impact

Le lecteur peut distinguer une occasion de prix d'une autorisation réelle
d'allouer. Aucun classement, score, filtre, sizing, achat, vente ou montant
d'allocation n'est modifié.

---

## [2026-08-16] Simplification compacte de Vente & surveillance

**Niveau : 1. Statut : Approuvé, implémenté.**

### Décision

Présenter d'abord la réponse opérationnelle : vente ou réduction à exécuter,
puis au maximum trois positions sous surveillance avec une consigne simple et
une seule raison principale. Conserver les signaux techniques complets dans un
bloc repliable pour l'audit.

### Impact

La section distingue explicitement une action immédiate d'une simple
surveillance et réduit le bruit du rapport quotidien. Aucun signal, statut,
seuil, score, sizing, achat, vente ou allocation n'est modifié.

---

## [2026-08-16] Triage compact centré sur les actions de maintenance utilisateur

**Niveau : 1. Statut : Approuvé, implémenté.**

### Constat

Le compteur compact des priorités de validation additionnait les couples
ticker-champ de tous les univers, dont une majorité issue du Market Scanner.
Il ne correspondait pas au workflow réel de l'utilisateur, limité au dépôt
ponctuel de rapports BNCD/Morningstar selon `research-needed` et à la mise à
jour occasionnelle du fichier de calibration des proxys.

### Décision

- Retirer du triage compact le compteur brut des champs prioritaires. Les
  détails et l'événement de journal correspondant restent disponibles dans
  les CSV d'audit et le rapport complet, mais sont masqués dans toute la vue
  compacte.
- Afficher l'état de maintenance BNCD selon la date du dernier dépôt de rapport.
  La file `research-needed` donne le contenu du prochain lot, mais ne déclenche
  un rappel qu'après 60 jours sans nouveau dépôt.
- Recalculer à chaque rapport l'âge des `source_date` de
  `data/proxy_calibration.csv`. Afficher un état vert entre les échéances, un
  avertissement après 330 jours et une mise à jour requise après 365 jours.
  Cette cadence annuelle reflète le caractère structurel et très occasionnel
  de la calibration, avec une fenêtre de rappel d'environ un mois.
- Calculer les lignes `research-needed` une seule fois avant la génération des
  rapports, puis réutiliser exactement ces lignes pour le triage et le CSV.

### Impact

Le rapport compact reflète les seules maintenances que l'utilisateur peut
effectivement réaliser. Aucun score, seuil, filtre de recherche, statut
d'éligibilité, sizing, allocation ou signal d'achat/vente n'est modifié.

---

## [2026-08-16] Correction de la narration compacte des clusters de risque

**Niveau : 1. Statut : Approuvé, implémenté.**

### Constat

Le rapport compact attribuait l'exposition maximale d'un titre à chacun de ses
clusters cachés. Une exposition de 68,5 % au cluster
`RATES_SENSITIVE_GROWTH` pouvait ainsi être répétée à tort pour l'IA, le
Canada, les paiements ou l'électrification. Les lignes agrégées du rapport de
risque contenaient déjà les expositions correctes par cluster.

### Décision

La narration compacte utilise les expositions agrégées de
`portfolio_risk["alerts"]`. Les lignes par titre restent disponibles comme
diagnostic et servent uniquement de repli lorsque les données agrégées sont
absentes.

### Impact

Correction d'affichage uniquement. Aucun calcul de risque, cluster attribué,
score, ajustement de sizing, allocation ou signal d'achat/vente n'est modifié.

---

## [2026-08-16] Cohérence des signaux de validation et de stabilité dans les rapports

**Niveau : 1. Statut : Approuvé, implémenté.**

### Constat

Le moteur de priorité produit les libellés français `HAUTE` et `TRES_HAUTE`,
mais le triage compact et le journal de run ne reconnaissaient que `HIGH` et
`CRITICAL`. Le rapport pouvait donc afficher « aucune priorité haute » alors que
le CSV en contenait. Par ailleurs, un run `SCORE_STABILITY_BASELINE` sans lignes
comparables ne réécrivait pas `latest_score_stability.csv`, laissant visible un
résultat ancien comme s'il appartenait au run courant.

### Décision

- Reconnaître les libellés français et anglais de priorité haute dans le triage
  compact et le journal de run.
- Réécrire systématiquement le CSV de stabilité, ainsi que son miroir suffixé
  par mode. En l'absence de comparaison, le fichier contient uniquement son
  en-tête et ne conserve aucune ligne d'un run antérieur.
- Conserver la distinction entre `bncd_report_needed` et `research_needed` : le
  premier porte sur un champ précis sans rapport exploitable, tandis que le
  second peut demander une source qualitative ou une validation de gouvernance.

### Impact

Correction d'affichage et d'audit uniquement. Aucun score, seuil, statut
d'éligibilité, montant d'allocation ou signal d'achat/vente n'est modifié.

---

## [2026-07-25] Faux positif SCORE_STABILITY sur rafraîchissement du cache marché — porte de comparabilité (Option 2)

**Niveau : 2 (correction du contrôle de stabilité). Statut : Approuvé (décision CEO du 2026-07-25).**

### Contexte

Après la correction [2026-07-25] du faux positif SCORE_STABILITY lié à
data_reliability_score (retrait de NUMERIC_FIELDS, commit 0e9087c), deux runs
analyze --mode high-cagr restaient UNSTABLE sur 6 tickers (GOOGL, MA, INTU, LLY,
META, MSFT), déclenchés par conviction_score_delta / capital_allocation_score_delta.

### Diagnostics read-only

reports/diagnostics/conviction_reliability_cliff_20260725.md a INFIRMÉ
l'hypothèse d'un effet de seuil du cap fiabilité→conviction : les 6 tickers
restent data_reliability_level = HIGH aux deux snapshots, aucun ne traverse les
frontières 80/60, aucun conviction_score_raw n'est présent (aucun cap effectif).

L'analyse comparative champ à champ des deux snapshots comparés par la garde
(analysis_high-cagr_20260725_092340.json vs _205549.json) a établi la cause
réelle : le run de 09:23 lisait un cache marché STALE_CACHE, celui de 20:55 des
données FRESH. 264 des 265 tickers communs ont changé de market_data_freshness_level
(STALE_CACHE → FRESH) ET de current_price entre les deux runs. Les deltas de
conviction et d'allocation sont la conséquence normale de prix différents (et des
champs qui en dérivent : drawdown, unrealized_gain, expected_cagr_quality,
opportunity_cost_status, cycle_bubble_risk_level, long_term_durability). La hausse
de data_reliability_score (+1.75 à +3.0) est elle-même un effet de bord de la
pénalité de fraîcheur du cache stale, non une cause.

### Cause racine établie par lecture

src/score_stability_engine.py::compute_score_stability compare le run courant au
snapshot same-day le plus ancien, et son message UNSTABLE affirme « sans
changement de données connu » — une affirmation que le code ne vérifiait jamais.
La seule exclusion (_is_ignored_ticker) ne filtre que les ETF et VFV.TO. La garde
comparait donc deux runs aux entrées matériellement différentes (cache stale vs
frais) en prétendant les entrées identiques. SCORE_STABILITY étant un contrôle de
déterminisme (mêmes entrées → mêmes scores), ce jour-là il mesurait un mouvement
de marché, pas une non-déterminisme du code : faux positif.

### Décision

Option 2 retenue (parmi trois examinées) : porte de comparabilité au niveau du
run entier. Si la fraction de tickers (intersection non-ignorée) dont
market_data_freshness_level diffère entre les deux snapshots est ≥
MARKET_DATA_REFRESH_FRACTION (0.50), les runs ne partagent pas les mêmes entrées
et compute_score_stability retourne SCORE_STABILITY_BASELINE avec un message
dédié, au lieu de flaguer WATCH/UNSTABLE. Sur les jours où les deux runs
partagent le même cache, la comparaison complète — et donc la détection de
déterminisme — est préservée intégralement.

Option 1 (exclusion par ticker) explicitement REJETÉE : 264/265 tickers étant
non-comparables ce jour-là, elle aurait réduit la comparaison à un échantillon
de 1 ticker et rapporté STABLE — un signal trompeur. Option 3 (protocole de
double run sur cache gelé / nouveau mécanisme de comparaison à prix invariant)
REJETÉE en phase de maturation : elle résout par un mécanisme nouveau ce qu'une
porte d'entrée résout sans changer le scoring.

### Champ de gate

market_data_freshness_level (couverture 100 % sur les rows de analysis_*.json).
market_data_fetched_at, market_data_fetch_status et market_data_source sont
ABSENTS des rows de snapshot (présents seulement dans latest_data_freshness.csv)
et ne peuvent pas servir de clé.

### Portée et contraintes

Changement confiné à src/score_stability_engine.py + son fichier de tests.
main.py inchangé (site d'appel ligne 1847 déjà suffisant). Aucun seuil
WATCH/UNSTABLE modifié, aucun calcul de delta ni choix de snapshot modifié,
aucune fonction ajoutée à utils.py (REFACTOR-01), aucune dépendance ajoutée à
report_generator.py (REFACTOR-02). Aucun changement de comportement de scoring.

### Vérification

- Tests avant : Ran 587 / OK. Tests après : Ran 588 / OK.
- Test de non-régression ajouté couvrant (a) porte active sur ≥ 50 % de mismatch
  de fraîcheur → BASELINE, et (b) porte inactive sans mismatch avec delta ≥ 3.0 →
  UNSTABLE.
- SCORE_STABILITY final : SCORE_STABILITY_BASELINE — porte activée ;
  n_intersection=264, n_mismatch=263, fraction=0.9962.
- git diff --stat : src/score_stability_engine.py | 52 ++++++++++++++++++++++++++++++-; tests/test_score_stability_engine.py | 59 ++++++++++++++++++++++++++++++++++++; 2 files changed, 110 insertions(+), 1 deletion(-).
- Commit : hash final rapporté par `git log --oneline -1` après commit ; auto-référence impossible dans le contenu du même commit sans changer ce hash.

### Dette / suites

Aucune dette nouvelle. Piste optionnelle non prioritaire : persister
market_data_fetched_at dans les rows de analysis_*.json permettrait une clé de
comparabilité plus fine (égalité exacte du timestamp de fetch) que le niveau de
fraîcheur ; différée, non requise tant que le niveau de fraîcheur suffit.

## [2026-07-25] Incohérence cosmétique du signal ELIGIBLE_BUT_NOT_SELECTED — clôture Dossier 2 et clôture Phase 2 refonte BNCD

**Niveau : 1 (documentation d'une non-action). Statut : Approuvé (décision CEO du 2026-07-25).**

### Contexte

Observation consignée dans l'entrée [2026-07-22] Étape 7 : VLO portait
allocation_decision = ELIGIBLE_BUT_NOT_SELECTED et un add_eligibility_status
permissif, mais capital_allocation_score = 10.90 (très bas). Ces signaux
semblaient devoir être cohérents et ne l'étaient pas. Dernier item ouvert de la
Phase 2 de la refonte BNCD.

Diagnostic read-only reports/diagnostics/vlo_eligibility_incoherence_20260725.md,
run high-cagr capital 1000, dénominateur 266 lignes / 265 tickers distincts.

### Cause racine établie par lecture

La triade ne provient pas d'une base unique réconciliée. Trois champs, trois
chemins :
- allocation_decision est dérivé APRÈS allocation dans
  main.py::apply_final_decisions() : si le montant reçu est nul et que
  add_eligibility_status ∈ {ADD_ALLOWED, ADD_ALLOWED_SMALL}, la décision devient
  ELIGIBLE_BUT_NOT_SELECTED. capital_allocation_score n'entre PAS dans cette
  branche.
- add_eligibility_status (add_eligibility_engine.py) répond à « rien ne s'oppose-
  t-il à un ajout ? » à partir de thesis_status, liquidation_status,
  data_reliability_level, confirmed_fundamental_sell_signals, monitoring_status,
  expected_cagr_quality, conviction_score. Il ne lit jamais
  capital_allocation_score.
- capital_allocation_score (sizing_engine.py) répond à « quelle priorité de
  capital ? ». Il ne lit pas allocation_decision. Il lit en revanche
  add_eligibility_status (ligne 227) pour appliquer une pénalité de sizing sur
  ADD_ALLOWED_SMALL — couplage unidirectionnel, à sens inverse d'une
  réconciliation, et non un point de réconciliation de la triade.

L'incohérence est donc sémantique et voulue par l'architecture : « rien ne
s'oppose à l'ajout » et « faible priorité de capital » sont deux questions
distinctes qu'un même titre peut satisfaire simultanément. ELIGIBLE_BUT_NOT_
SELECTED signifie « admissible qualitativement, non retenu par le sizing marginal
de cette cotisation », ce que dit déjà allocation_decision_reason à ce site.

### Mesure de la population

6 tickers portent la triade exacte (allocation_decision ELIGIBLE_BUT_NOT_SELECTED
+ add_eligibility_status permissif + capital_allocation_score < 50), soit 12,5 %
des 48 ELIGIBLE_BUT_NOT_SELECTED : ASML (CORE, 40.29), CS.TO (MARKET, 47.66),
GWO.TO (MARKET, 49.60), MOD (MARKET, 49.17), WAB (MARKET, 37.54), VLO (DISCOVERY,
10.90). Motif non propre à un univers (4 MARKET_SCANNER, 1 DISCOVERY_IDEAS,
1 CORE_PORTFOLIO). Cinq des six scores frôlent le seuil de 50 (37–50) ; seul VLO
à 10.90 présente un écart béant entre les deux définitions.

### Impact décisionnel : nul

_eligible() rejette tout titre high-cagr sous MODE_MIN_CAPITAL_SCORE["high-cagr"]
= 50 ; _high_cagr_overflow_eligible() rejette sous 40. VLO à 10.90 échoue les
deux. Sur le run courant, VLO reçoit 0 $ (allocations : VFV.TO 525, RHM.NE 250,
APH 225 ; VLO absent du CSV d'allocations). L'incohérence est cosmétique /
d'auditabilité : une étiquette mésinterprétable, jamais un défaut d'allocation.

### Décision

1. Aucune correction de code. Le comportement d'allocation est correct ; aucun
   des 6 titres ne reçoit de capital indûment. La réponse proportionnée en phase
   de maturation à « une étiquette peut se mésinterpréter » est de documenter la
   sémantique, pas de refondre la logique qui la produit.
2. Sémantique actée : ELIGIBLE_BUT_NOT_SELECTED = « admissible qualitativement
   (thèse, liquidation, fiabilité), non retenu par le sizing marginal de la
   cotisation ». Il ne signifie NI « proche d'être alloué » NI « capital_
   allocation_score élevé ». Un capital_allocation_score bas coexiste
   légitimement avec ce statut.
3. Option de réconciliation (faire dépendre l'étiquette de capital_allocation_
   score) explicitement REJETÉE : elle déplacerait une distinction réelle sans
   augmenter la fiabilité d'une décision, et casserait des consommateurs de
   l'étiquette (rapport compact, ticker_validation_value_score). Échoue au filtre
   de maturation.

### Dette consignée — Dette-04 (nouvelle, optionnelle, différée)

Piste d'auditabilité, non prioritaire : distinguer visuellement les cas-frontière
(cap_score frôlant le seuil) des cas à écart béant (VLO à 10.90), p. ex. via une
étiquette dérivée ELIGIBLE_LOW_PRIORITY lorsque cap_score est nettement sous le
seuil du mode. Niveau 2 si un jour retenu. Ne rectifie aucun comportement ; pur
confort d'audit. Différée sans échéance.

### Clôture de la Phase 2 de la refonte BNCD

VLO était le dernier item ouvert de la Phase 2 (refonte du sous-système des
rapports de recherche BNCD, entrée [2026-07-21]). Avec cette entrée, la Phase 2
est CLOSE. Récapitulatif des livrables Phase 2 : étapes 6(a–e) priorisation,
étape 7 déclencheur externe, Option 3 plafond candidats externes, renommage 1b,
garde-fou de vraisemblance juste-valeur [2026-07-24], et la présente clôture VLO.
Dettes reportées hors Phase 2 : Dette-01 (conventions de slug high_cagr vs
high-cagr), Dette-02 (infrastructure mode-slug parallèle dans report_generator.py),
Dette-03 (pattern-matching de chaîne française dans
_has_unconfirmed_fundamental_warning), Dette-04 (clarification d'étiquette
ci-dessus). Validation walk-forward toujours différée jusqu'à accumulation
naturelle de points espacés.

### Contraintes respectées

REFACTOR-01, REFACTOR-02, isolation des modes [2026-07-01] : sans objet (aucun
code modifié). Aucun changement de comportement.

## [2026-07-25] Correction du faux positif structurel de la garde SCORE_STABILITY (exclusion de data_reliability_score du déclenchement)

**Niveau : 3 (architectural — la garde SCORE_STABILITY est un invariant de gouvernance conditionnant la précondition de tous les prompts).**
**Statut : Approuvé.**

### Contexte et symptôme

Deux runs `analyze --mode high-cagr` consécutifs le même jour, sans changement de
données volontaire, produisaient `SCORE_STABILITY_UNSTABLE` sur 17 tickers. Le
CSV `latest_score_stability.csv` du 2026-07-25 montrait un `data_reliability_score_delta`
quasi uniforme de +3.0 sur 16 tickers sur 17 (GOOGL +1.75), alors que
`score_total_delta`, `conviction_score_delta` et `capital_allocation_score_delta`
restaient à 0.0 pour la majorité. La variation de fiabilité, à elle seule,
faisait basculer 16 tickers en UNSTABLE.

### Cause racine (mesurée)

Deux faits établis par diagnostics read-only (rapports non commités sous
`reports/diagnostics/`, gitignorés) :

1. **Mécanisme de la garde.** `src/score_stability_engine.py` calcule, pour
   chaque ticker, `max_delta = max(|delta|)` sur `NUMERIC_FIELDS = [score_total,
   conviction_score, capital_allocation_score, data_reliability_score]`, et
   déclenche UNSTABLE si `max_delta >= 3.0` (WATCH si `>= 1.5`).
   `data_reliability_score` était donc traité à égalité stricte des trois scores
   de jugement. Or ce score encode une pénalité de **fraîcheur dépendante du
   temps** (fonction de l'écart entre l'instant du run et le timestamp de la
   donnée) : il ne peut par construction être identique entre deux runs à des
   instants différents. Le message de succès de la garde (« Tous les scores sont
   identiques entre les deux runs du jour ») décrivait ainsi un objectif que le
   design rendait inatteignable en usage normal.

2. **Réécriture du cache.** Un run `analyze` peut modifier `data/cached_market_data/`
   sans `--refresh-market-data` (maintenance de cache inconditionnelle ;
   sous-cache `instrument_profiles` réécrit à chaque run avec allocations
   positives ; rafraîchissement du cache prix racine conditionnel à
   absence/âge/schéma). L'empreinte du répertoire de cache change donc entre deux
   runs consécutifs, ce qui fait varier la pénalité de fraîcheur et, via le point
   1, déclenche UNSTABLE.

La conjonction produisait un **faux positif structurel** : la garde confondait
l'instabilité du *jugement* (qu'elle doit surveiller) avec la variation de la
*fraîcheur des données* (qui n'a aucune raison d'être stable dans le temps).

### Décision

Retrait de `data_reliability_score` de la liste `NUMERIC_FIELDS` qui pilote le
calcul de `max_delta` et le déclenchement du flag, dans
`src/score_stability_engine.py`.

Conséquences voulues :
- Le déclenchement UNSTABLE/WATCH ne dépend plus que des trois scores de jugement
  (`score_total`, `conviction_score`, `capital_allocation_score`), qui doivent
  légitimement être stables entre deux runs sur données identiques.
- Les colonnes `data_reliability_score_prev/curr/delta` demeurent présentes dans
  le CSV `latest_score_stability.csv` (renseignées par la fonction `_row`,
  indépendamment de `NUMERIC_FIELDS`) : la fiabilité reste visible pour audit,
  seule sa capacité à déclencher le flag est retirée.
- Un test de non-régression (`test_data_reliability_delta_alone_does_not_trigger`)
  fige ce comportement : un delta de fiabilité seul ≥ 3.0 ne déclenche plus.

Option retenue : exclusion du déclenchement avec conservation des colonnes
d'audit (« Option A »). L'alternative — neutraliser seulement la part de
fraîcheur en conservant une détection de dégradation de source — a été écartée :
elle exigerait de modifier le moteur de calcul de `data_reliability_score`
lui-même, ajoutant une complexité non justifiée en phase de maturation.

### Risque accepté et proposition future

En retirant `data_reliability_score` du déclenchement, la garde SCORE_STABILITY
ne signale plus une chute de fiabilité, y compris une vraie dégradation de source
(source morte, effondrement de couverture). Ce risque est **accepté** : la
détection d'une dégradation de données n'est pas le rôle d'une garde de
*stabilité inter-run du jugement*. Confondre les deux était la cause du faux
positif corrigé ici.

Proposition future (non engagée par cette décision) : ajouter une **alerte
distincte fondée sur le niveau absolu** de `data_reliability_score` (et non sur
son delta inter-run), afin de détecter une dégradation réelle de source sans
polluer la garde de stabilité. À évaluer séparément selon le filtre de maturation
(« confiance vs complexité »).

### Vérification

- Suite de tests complète : Ran 587 tests — OK.
- SCORE_STABILITY après correction, via deux runs `analyze --mode high-cagr
  --capital 1000` consécutifs sans `--refresh-market-data` :
  UNSTABLE — 6 tickers subsistent, déclenchés par `conviction_score_delta` et/ou
  `capital_allocation_score_delta` (GOOGL, MA, INTU, LLY, META, MSFT). Les deltas
  `data_reliability_score` restent visibles dans le CSV mais ne déclenchent plus
  seuls ; plusieurs lignes demeurent STABLE malgré `data_reliability_score_delta = 3.0`.
- `git diff --stat` : `src/score_stability_engine.py | 7 +++++--; tests/test_score_stability_engine.py | 33 +++++++++++++++++++++++++++++++++; 2 files changed, 38 insertions(+), 2 deletions(-)`.

### Portée des fichiers

- `src/score_stability_engine.py` (modification de `NUMERIC_FIELDS`).
- `tests/test_score_stability_engine.py` (ajout d'un test de non-régression).
- Aucun autre fichier de code. `report_generator.py`, `utils.py`, et le moteur de
  calcul de `data_reliability_score` ne sont PAS touchés.

Commit : même commit que cette entrée ; hash final rapporté dans le rapport Codex
(auto-référence impossible dans le contenu du commit sans changer ce hash).

## [2026-07-24] Garde-fou de vraisemblance juste-valeur — clôture Phase 2 refonte BNCD

**Niveau : 2. Statut : Approuvé (décision CEO du 2026-07-24).**

### Contexte

Dette technique explicitement différée en fin de Phase 2 dans l'entrée
[2026-07-21]. Le bug d'origine (safe_float("3,600") → 3.6 au lieu de 3600),
corrigé en Phase 1 étape 1, corrompait silencieusement des justes valeurs et
promouvait des titres à tort. Le parsing est corrigé, mais aucune garde de
vraisemblance n'était câblée : une valeur aberrante réapparaissant (autre
format, autre source) n'était détectée par rien.

Diagnostic read-only reports/diagnostics/fair_value_guard_denominateur_20260724.md,
run high-cagr capital 1000, dénominateur 266 lignes / 265 tickers distincts :
- 47 tickers analysés portent une fair_value issue d'un rapport.
- Ratio fair_value / current_price borné : min 0.5257 (MU), médiane 1.0913,
  max 1.9205 (CSGP). Aucun ratio > 20× ni < 1/20×.
- CSU.TO (ground zero du bug d'origine) : fair_value 3600.0, prix 2780.49,
  ratio 1.29 — sain, confirmant le correctif Phase 1.
- 4 justes valeurs proviennent de cours cibles courtier (CS.TO, GFL.TO,
  HPS-A.TO, WSP.TO), déjà marquées LOW / définition divergente par le code.

La garde est donc PRÉVENTIVE, pas urgente : elle protège contre une future
corruption d'extraction, pas une corruption vivante.

### Décision

1. Point de branchement : en aval, dans main.py::build_position_analyses(),
   après résolution des overrides manuels et avant compute_fundamental_score.
   parse_research_report ne reçoit pas le prix ; le faire remonter aurait exigé
   un changement de signature et de la plomberie. Le site de fusion dispose déjà
   de market["current_price"] — rejeté au profit du branchement aval sans
   changement de signature.
2. Seuil : écart > 20× (ou < 1/20×) entre juste valeur et dernier prix, fixé en
   constante FAIR_VALUE_IMPLAUSIBLE_RATIO = 20.0. La population réelle vit sous
   2× ; 20× ne peut se déclencher que sur une corruption d'extraction (le bug
   d'origine était un écart ~770×).
3. Comportement au déclenchement : REJET du champ fair_value (retiré de manual
   et de research_report_fields avant scoring), avec avertissement explicite
   nommant ticker, valeur, prix et ratio, dans le canal existant
   research_report_extraction_warnings. Choix assumé du rejet plutôt que d'un
   simple abaissement en confiance : un écart > 20× n'est pas une divergence de
   définition (traitée en LOW pour les cours cibles courtier), c'est une quasi-
   certitude de corruption ; une valeur corrompue laissée en LOW pourrait encore
   fausser la fiabilité et la comparaison VFV, exactement le défaut d'origine.
   Une juste valeur confirmée manuellement (fair_value ∈ manual_override_fields)
   n'est JAMAIS rejetée : l'humain prime.
4. Dette-01 (conventions de slug high_cagr vs high-cagr) et Dette-02
   (infrastructure mode-slug parallèle dans report_generator.py) confirmées
   séparables par lecture : research_reports.py n'a aucune logique de slug et le
   site de fusion ne dépend d'aucune convention de slug. Elles restent différées
   comme dossier distinct, hors périmètre de cette entrée.

### Effet mesuré sur la population courante

Aucun des 47 tickers exposés ne déclenche le rejet (tous ratios dans
[0.5257, 1.9205]). CSU.TO préservé (ratio 1.29). Comportement d'allocation
inchangé.

### Contraintes respectées

REFACTOR-01 (aucune fonction ajoutée à utils.py), REFACTOR-02 (aucune
dépendance ajoutée à report_generator.py), isolation des modes [2026-07-01].
Aucun changement de comportement hors la garde ; scoring, allocation et seuils
inchangés. research_reports.py non modifié.

### Vérification à l'exécution

Tests : 586 ; SCORE_STABILITY :
STABLE. Vérification comportementale
high-cagr : aucun message "Fair value rejetée" sur le run courant, CSU.TO
préservé. Fichiers touchés : main.py | 30 ++++++++++++++++++++++ ; tests/test_research_reports.py | 56 ++++++++++++++++++++++++++++++++++++++++++ ; 2 files changed, 86 insertions(+). Commit :
7b16df4.

## [2026-07-24] Option 3 — Plafond des déclencheurs de rapport BNCD pour candidats externes purs

**Niveau : 3 (architectural). Statut : Approuvé (décision CEO du 2026-07-24).**

### Contexte

Le déclencheur de rapport BNCD pour positions externes proposables
(`_external_allocation_candidate_needs_report`, livré au commit `1d031e4`) émettait, sur le
chemin pipeline autoritatif (`run_analysis`, 4 univers), une population non plafonnée de lignes
`EXTERNAL_CANDIDATE`. Deux diagnostics read-only ont établi la population réelle :

- `option3_denominateur_20260724.md` : dénominateur de la porte externe = 33 (> 30), ventilé
  WATCHLIST 1 / MARKET_SCANNER 27 / DISCOVERY_IDEAS 5 / CORE 0 ; contrôle-croisé sonde vs
  artefact mode-scoped 33 = 33 ; part moyenne de la Catégorie B (faiblesse des données) dans le
  score de tri = 32,4 % ; 6 lignes basculeraient au seuil de rang 30 selon que le tri utilise
  le score complet ou la seule Catégorie A ; intersection `EXTERNAL_CANDIDATE ∩ MANUAL_REVIEW`
  = 0/33.
- `option3_repartition_externe_20260724.md` : parmi les 33, **31 externe pur**
  (`need_type == "EXTERNAL_CANDIDATE"`) et **2 mixtes** `DATA+EXTERNAL_CANDIDATE` (`WAB`,
  `MOD`) ; contrôle-croisé 33 = 33, écart 0.

### Décision

1. Ajout d'un plafond sur le segment **externe-pur** des lignes émises par
   `research_needed_rows_from_analysis_rows`, fixé à **30**, appliqué par
   `ticker_potential_score` décroissant.
2. Le tri utilise le **score complet** `ticker_validation_value_score` (Catégorie B —
   faiblesse des données — incluse), décision CEO assumée : un titre mal documenté proposé à
   l'achat mérite un rapport précisément à cause de cette faiblesse. Le score n'est pas épuré.
3. Les lignes portant un besoin `DATA` et/ou `QUALITATIVE` (y compris les mixtes
   `DATA+EXTERNAL_CANDIDATE`) ne sont **jamais** coupées par ce plafond. La qualité des données
   reste prioritaire : le plafond régule la prolifération des candidats externes, pas les
   besoins de validation de données.
4. Implémentation par paramètre `limit: int | None = None` sur
   `research_needed_rows_from_analysis_rows` (pattern aligné sur `build_validation_priority_rows`),
   troncature **sélective** appliquée après le tri (les lignes préservées passent
   inconditionnellement ; les externe-pures sont retenues jusqu'à `limit`, l'ordre d'origine
   étant conservé). `limit=30` est passé **au seul site pipeline** (`run_analysis`) ; le site
   CLI (`build_research_needed_rows_from_current_inputs`) reste sans plafond.
5. Aucune assertion de test existante inversée. Un test de cap est ajouté couvrant : troncature
   du segment externe-pur à la limite, préservation des lignes mixtes, sélection des plus hauts
   scores, et rétrocompatibilité `limit=None`.

### Effet mesuré sur la population courante

Externe-pur 31 → 30 (1 externe-pure de plus bas score omise) ; 2 mixtes (`WAB`, `MOD`)
préservées ; total `EXTERNAL_CANDIDATE` 33 → 32.

### Contraintes respectées

REFACTOR-01 (aucune fonction ajoutée à `utils.py`), REFACTOR-02 (aucune dépendance ajoutée à
`report_generator.py`), isolation des modes [2026-07-01]. Aucun changement de comportement hors
du plafond ; portes de déclenchement et calcul de score inchangés.

### Vérification à l'exécution

Tests : 583 ; SCORE_STABILITY :
STABLE. Vérification comportementale pipeline `high-cagr` : externe-pur
30, mixtes `WAB`/`MOD` présentes, total
`EXTERNAL_CANDIDATE` 32. Fichiers touchés :
main.py | 2 ++ ; src/research_reports.py | 21 +++++++++++++- ; tests/test_research_reports.py | 62 ++++++++++++++++++++++++++++++++++++++++++ ; 3 files changed, 84 insertions(+), 1 deletion(-). Commit : 5c3d80e.

## [2026-07-24] Renommage MANUAL_REVIEW_BEFORE_ADD → RESEARCH_REPORT_REQUIRED_BEFORE_ADD (dossier MANUAL_REVIEW 1b)

Type : Level 1 (renommage d'un statut interne, aucun changement de comportement).
Statut : Appliqué.

### Motivation
Le statut MANUAL_REVIEW_BEFORE_ADD ne décrivait pas l'action attendue mais une
cause. Le micro-diagnostic read-only du 2026-07-24
(reports/diagnostics/manual_review_paths_20260724.md) a établi, contrôle croisé
FIABLE (127 live = 127 persistés, écart 0), que les 127 titres portant ce statut
proviennent à 100 % de la branche native (monitoring_status == "MANUAL_REVIEW",
« A1 ») : A2 synthétisé = 0, B WATCH non confirmé = 0, non classés = 0. Le statut
signifie en pratique « aucun rapport de recherche n'a jamais couvert ce titre ».
Le nouveau nom, RESEARCH_REPORT_REQUIRED_BEFORE_ADD, nomme l'action attendue et
s'aligne sur l'option 3 à venir, qui fera de ces titres des candidats
research_needed.

### Portée du renommage
Établie par l'audit des références (2026-07-23) et confirmée par relecture
directe des deux fichiers de tests (2026-07-24). Quatre occurrences littérales,
trois fichiers :
- src/add_eligibility_engine.py : 2 sites producteurs dans
  compute_add_eligibility_status (branche monitoring_status == "MANUAL_REVIEW",
  et branche WATCH + _has_unconfirmed_fundamental_warning).
- tests/test_add_eligibility.py : 1 assertion
  (test_unconfirmed_fundamental_warning_requires_manual_review).
- tests/test_research_reports.py : 1 valeur d'entrée
  (test_research_needed_external_candidate_requires_add_allowed_status).

### Exclusion assumée
src/liquidation_engine.py porte la même chaîne dans le champ DISTINCT
monitoring_decision (produit par _monitoring_fields()), régi par un contrat
séparé. Il est explicitement HORS périmètre. Un remplacement global aurait cassé
silencieusement ce contrat.

### Discontinuité des artefacts historiques
La chaîne apparaît dans des run logs JSON et CSV de backup antérieurs. AUCUNE
migration n'est effectuée. Le champ add_eligibility_status n'a été ajouté à
SNAPSHOT_FIELDS que le 2026-07-22 ; l'historique exploitable a un jour. Le
walk-forward compare des scores et des allocations, jamais des chaînes de statut.
Réécrire des artefacts datés falsifierait des traces d'audit. La discontinuité
est donc assumée et sans impact sur le walk-forward.

### Continuité de comportement et limite de portée
Le renommage ne modifie aucun comportement. En particulier, le test
test_research_needed_external_candidate_requires_add_allowed_status conserve son
assertion (rows == []) : à ce stade, le statut renommé n'est toujours pas traité
comme candidat externe. La sémantique de ce test changera à l'option 3 (le statut
renommé déclenchera research_needed), ce qui relèvera d'une entrée DECISIONS.md
distincte. La présente entrée ne fige donc aucun contrat que l'option 3 viderait.

### Vérification
- Tests avant : 582 OK. Tests après : 582 OK.
- SCORE_STABILITY après : STABLE.
- git diff --stat : src/add_eligibility_engine.py | 4 ++--; tests/test_add_eligibility.py | 2 +-; tests/test_research_reports.py | 2 +-; 3 files changed, 4 insertions(+), 4 deletions(-).
- Commit code+tests : ae91c04.

## [2026-07-23] Dossier MANUAL_REVIEW_BEFORE_ADD — 1a, propagation des raisons réelles

Niveau 1 — Approuvé, implémenté, vérifié.

### CONSTAT
`MANUAL_REVIEW_BEFORE_ADD` comptait 127 titres sur 266 (48 % de l'univers) avec
une seule et unique raison distincte, identique mot pour mot pour les 127 :
« Alerte de surveillance à valider manuellement avant ajout. »

Un statut porté par la moitié de l'univers avec un message rigoureusement
uniforme ne porte plus d'information. Le champ `add_eligibility_reason`
n'exposait pas les `monitoring_reasons` réelles pourtant déjà calculées par
`liquidation_engine._monitoring_fields()` et disponibles dans l'analyse.

### DIAGNOSTIC CHIFFRÉ — source, périmètre, dénominateur
Sources lues :
  reports/diagnostics/external_trigger_scope_2026-07-22_capital.md
  reports/diagnostics/manual_review_causes_2026-07-23.md
  reports/diagnostics/universe_duplicate_check_2026-07-23.md
Run analyze high-cagr, capital strictement positif.
Dénominateur : 266 lignes d'analyse pour 265 tickers distincts.

CAUSE RACINE ÉTABLIE : le statut n'est pas un jugement sur les entreprises.
C'est la conséquence mécanique de `_field_confirmed()` qui retourne
`field not in auto_fields` → False pour tout champ issu de
`auto_estimated_fields`. Mesure sur les 127 titres : entre 97 et 127 titres
ont chaque champ dans `auto_estimated_fields` selon le champ
(`sector_cagr_estimated` : 127/127). Le statut signifie en réalité
« ce titre n'a jamais fait l'objet d'un rapport de recherche ».

Chaîne réelle vérifiée par lecture du code, différente de l'hypothèse initiale :
`_monitoring_fields()` calcule `monitoring_status` AVANT tout branchement de
statut et l'injecte via `**monitoring` dans les retours GREEN, YELLOW et
fallback. MANUAL_REVIEW n'exige donc PAS un statut YELLOW.
Mesure : 128 GREEN / 9 YELLOW sur `monitoring_status` ;
127/127 GREEN sur MANUAL_REVIEW_BEFORE_ADD. Les YELLOW sont interceptés en
amont par les gardes DO_NOT_ADD de `compute_add_eligibility_status()`.

Boucle fermée confirmée : 126/127 absents de `research_needed`. Le seul présent
(ARAY) y est entré par `need_type=DATA`, pas par son statut.

Multi-causalité : seuls 13 titres sur 127 portent une raison unique.
114 en portent 2 à 9. Aucune correction chirurgicale ne débloque la majorité.

TSLA présent dans `watchlist_analyses` ET `discovery_analyses`, valeurs
strictement identiques. Hors population MANUAL_REVIEW. Impact sur les
diagnostics passés : nul (127 par lignes = 127 par tickers distincts).

### CHANGEMENT
`src/add_eligibility_engine.py` uniquement :
- La branche `monitoring_status == "MANUAL_REVIEW"` lit désormais
  `analysis["monitoring_reasons"]` et les joint par « | » dans
  `add_eligibility_reason`.
- Repli sur le message générique si `monitoring_reasons` est vide.
- Aucun changement de statut, de seuil, de tri ou d'allocation.

### VÉRIFICATION
582 tests, SCORE_STABILITY STABLE avant et après.
Code livré lu et validé, conforme au prompt, aucun ajout hors demande.
V3 : 127 → 127 titres MANUAL_REVIEW_BEFORE_ADD (non-régression du périmètre).
V4 : 1 → 82 chaînes de raison distinctes.
V5 : 0 anomalie.
V6 : aucune allocation modifiée.
git diff : 1 seul fichier touché.

### DETTE CONSIGNÉE — Dette-03 (nouvelle)
Le mécanisme de détection de `_has_unconfirmed_fundamental_warning()` repose
sur du pattern-matching de la chaîne littérale française
« Validation manuelle requise ». Toute correction de typo dans une chaîne
émise par `_unconfirmed_fundamental_sell_signals()` peut changer un statut
silencieusement sur 54 titres. Cause racine de la duplication de signaux
mesurée (bilan affaibli 54/54, Forward P/E 40/40). NE PAS déduplier en
l'état. Différé.

### SUITE
1b : renommage du statut vers un nom reflétant la cause réelle.
Audit read-only des références livré le 2026-07-23 : 2 occurrences
productrices dans `add_eligibility_engine.py`, 0 dans `main.py`, 0 dans
`report_generator.py`, 2 assertions de test. `liquidation_engine.py` porte la
même chaîne dans le champ DISTINCT `monitoring_decision` — hors périmètre du
renommage. Level 1 confirmé, pas Level 2.

## [2026-07-22] Étape 7 — déclencheur de rapport BNCD pour position externe proposable

Niveau 2 — Approuvé, implémenté, vérifié.

### CONSTAT
Une position externe proposée pour l'allocation mais non détenue ne générait
aucune recommandation de rapport BNCD. `research_needed_rows_from_analysis_rows()`
sortait en `continue` dès que `data_report_available` était vrai et que le besoin
qualitatif était faux, et `_qualitative_report_needed_from_analysis()` verrouille
ce besoin à CORE_PORTFOLIO. Un externe bien documenté produisait donc zéro ligne.

Interaction avec GOV-EXTERNAL-VALIDATION-GATE [2026-07-16] : le gate bloque
l'allocation réelle de tout externe sans champ validé personnellement. L'étape 7
ferme la boucle — le gate dit qu'il manque un rapport, l'étape 7 dit lequel aller
chercher. Les deux sont complémentaires, non conflictuels.

### DÉFINITION ARBITRÉE DE « PROPOSÉE ET NON DÉTENUE »
  universe ∈ {WATCHLIST, MARKET_SCANNER, DISCOVERY_IDEAS}
  ET allocation_status == "ELIGIBLE_BUT_NOT_SELECTED"
     (repli sur allocation_decision, comme discovery_for_validation dans main.py)
  ET add_eligibility_status ∈ ADD_ALLOWED_STATUSES  [garde de sécurité]

Définition A1 (external_validation_status == BLOCKED_PENDING_PERSONAL_VALIDATION)
ÉCARTÉE : mesurée à 203 titres externes. Le gate ne discrimine pas la qualité,
il constate l'absence de rapport. Un DO_NOT_ADD médiocre y est bloqué comme un
ADD_ALLOWED excellent. Déclencher sur A1 aurait produit un statut porté par la
moitié de l'univers — le défaut même que dénonce l'observation MANUAL_REVIEW.

Condition `allocation_status ∈ {ELIGIBLE_BUT_NOT_SELECTED, NO_NEW_ALLOCATION}`
initialement envisagée puis RESSERRÉE à ELIGIBLE_BUT_NOT_SELECTED seul :
le croisement mesuré donne NO_NEW_ALLOCATION × {ADD_ALLOWED, ADD_ALLOWED_SMALL}
= 0 titre. La branche NO_NEW_ALLOCATION n'apportait rien et ouvrait la porte aux
126 MANUAL_REVIEW_BEFORE_ADD si l'autre condition venait à bouger.

### DIAGNOSTIC CHIFFRÉ — source, périmètre, dénominateur
Source : reports/diagnostics/external_trigger_scope_2026-07-22_capital.md,
run analyze high-cagr, capital = 1000 $.
Dénominateur : 266 titres analysés, dont 243 externes.

Croisement add_eligibility_status × allocation_status, univers externes :
  ADD_ALLOWED (22)              → 21 ELIGIBLE_BUT_NOT_SELECTED, 1 DO_NOT_ADD, 0 NO_NEW
  ADD_ALLOWED_SMALL (23)        → 23 ELIGIBLE_BUT_NOT_SELECTED, 0 ailleurs
  MANUAL_REVIEW_BEFORE_ADD (126)→ 126 NO_NEW_ALLOCATION, 0 ailleurs

ELIGIBLE_BUT_NOT_SELECTED est le marqueur du candidat proposable : 44/44 des
titres portant ce statut ont un add_eligibility_status permissif.

Périmètre A3 : 44 titres — DISCOVERY_IDEAS 16, MARKET_SCANNER 27, WATCHLIST 1.
Écart avec les 45 externes permissifs : 1 titre ADD_ALLOWED en DO_NOT_ADD,
exclu à raison par la décision finale d'allocation.

### CHANGEMENT
`src/research_reports.py` uniquement :
- Ajout de `_external_allocation_candidate_needs_report(analysis, universe)`.
- Sortie anticipée étendue : `and not external_candidate_needed`.
- need_type "EXTERNAL_CANDIDATE" ajouté en dernier.
- Priorité HIGH intégrée via `_highest_priority()`, pas en dur.
- Raison et action dédiées, déduplication existante préservée.
- `_combined_research_suggested_action()` reçoit un paramètre optionnel
  `external_candidate_needed=False` — l'appelant `_from_reports` est inchangé.

Aucun import ajouté. Aucune dépendance vers allocation_engine.py : la contrainte
d'import circulaire ne mordait pas, la définition retenue ne l'exigeant pas.
RESEARCH_NEEDED_COLUMNS inchangé. Tri final inchangé (ticker_potential_score
reste primaire, conformément à [2026-07-22]).
`research_needed_rows_from_reports()` inchangé : cette fonction lit des CSV et
n'a pas accès à allocation_status.

### VÉRIFICATION
577 → 582 tests OK (N = 5). SCORE_STABILITY STABLE avant et après.
git diff : 2 fichiers (research_reports.py, test_research_reports.py).

Vérification comportementale : 33 lignes EXTERNAL_CANDIDATE produites là où il y
en avait 0. MARKET_SCANNER 27/27, WATCHLIST 1/1 — couverture complète sur les
univers non filtrés. DISCOVERY_IDEAS 5/16.

### PLAFOND STRUCTUREL DOCUMENTÉ — 33 au lieu de 44
Source : reports/diagnostics/external_trigger_scope_2026-07-22_ecart.md.
`main.py` transmet DISCOVERY_IDEAS via `discovery_for_validation`, qui exige
capital_allocation_score >= DISCOVERY_VALIDATION_PRIORITY_MIN_SCORE (70).
11 des 16 A3 DISCOVERY sont sous ce seuil :
  WFC 69.05, XYL 67.15, WTW 66.59, TRMB 65.13, WM 64.85, TFC 63.42,
  USB 62.45, TXT 60.92, SCHW 55.57, TROW 50.62, VLO 10.90
Les 5 passants : TEL 88.60, TER 79.56, STE 77.64, TDY 75.95, VRTX 72.79.

Ce plafond relève de la décision [2026-07-04], distincte de l'étape 7. Non
corrigé ici : le relever serait un arbitrage séparé sur le filtre de validation
DISCOVERY. L'étape 7 fait ce qu'elle doit sur les univers qu'elle reçoit.

### OBSERVATION CONSIGNÉE — à traiter séparément
VLO porte allocation_status ELIGIBLE_BUT_NOT_SELECTED et un add_eligibility_status
permissif avec capital_allocation_score = 10.90. Ces signaux devraient être
cohérents et ne le sont pas. Sans effet sur l'étape 7 (VLO est exclu par le
filtre DISCOVERY), mais sujet de CONFIANCE à rattacher au dossier MANUAL_REVIEW.

---

## [2026-07-22] Invalidation de l'Option B — le diagnostic de l'étape 7 était erroné

Niveau 3 — Proposition retirée avant spécification.

### CONTEXTE
L'étape 7 (déclencher une recommandation de rapport BNCD pour toute position
proposée à l'allocation mais non détenue) avait été abandonnée dans sa forme
initiale. Motif invoqué : sur 266 titres, aucun candidat externe n'atteignait
ADD_ALLOWED ; les 7 titres éligibles étaient tous CORE_PORTFOLIO ; le
déclencheur ajouterait 0 ligne. L'Option B avait été retenue en remplacement :
redéfinir le déclencheur vers les candidats externes bloqués UNIQUEMENT par
la donnée.

### CE QUE LE DIAGNOSTIC CHIFFRÉ RÉVÈLE
Le croisement add_eligibility_status × universe, lu directement dans
reports/latest_analysis_snapshot_high-cagr.json après persistance des champs
décisionnels, donne sur 266 titres :

  ADD_ALLOWED + ADD_ALLOWED_SMALL : 52 titres
- CORE_PORTFOLIO : 7
- externes : 45 (MARKET_SCANNER 28, DISCOVERY_IDEAS 16, WATCHLIST 1)

Le chiffre 7 du diagnostic précédent était le compte des CORE, et non le
compte des titres éligibles. Le diagnostic lisait un artefact restreint au
CORE, ou filtrait sur l'univers sans l'expliciter.

Sur les 9 candidats identifiés comme « proches », 8 portent déjà un statut
permissif :
  TER, AMAT : ADD_ALLOWED
  TEL, XYL, ADI, NVDA, TSM, TXN : ADD_ALLOWED_SMALL
  DELL : MANUAL_REVIEW_BEFORE_ADD

### CONSÉQUENCES
1. L'Option B est CADUQUE. Sa prémisse — des candidats externes bloqués par
   la donnée — est fausse. add_eligibility_engine.py les autorise déjà. Le
   blocage, s'il existe, est en aval de l'éligibilité.
2. L'étape 7 dans sa FORME INITIALE redevient viable. Le déclencheur
   porterait sur 45 positions externes proposables et non détenues, et non
   sur 0. Elle repasse en Niveau 2 : plus aucune redéfinition n'est requise.
3. Le motif d'abandon de l'étape 7 [voir entrée antérieure] est annulé.

### CAUSE RACINE ET LEÇON
Quatrième diagnostic successif de l'étape 7 à conclure faux en lisant un
artefact incomplet. Les trois premiers avaient été détectés par recoupement ;
celui-ci n'a pu être réfuté qu'après persistance des champs décisionnels dans
le snapshot, qui a rendu la mesure directe possible.

Règle retenue : tout diagnostic chiffré doit expliciter la source lue, son
périmètre d'univers, et le dénominateur exact. Un compte sans dénominateur
nommé n'est pas un diagnostic.

### OBSERVATION CONSIGNÉE — à traiter séparément
MANUAL_REVIEW_BEFORE_ADD compte 127 titres, soit 48 % de l'univers, avec une
seule et unique raison distincte, identique mot pour mot pour les 127 :
« Alerte de surveillance à valider manuellement avant ajout. »

Répartition : DISCOVERY_IDEAS 65, MARKET_SCANNER 59, WATCHLIST 2,
CORE_PORTFOLIO 1.

Ce statut ne peut provenir que de la branche monitoring_status ==
"MANUAL_REVIEW" de compute_add_eligibility_status(), atteinte via
liquidation_status == "YELLOW" avec signaux techniques/valorisation non
confirmés et détection de la chaîne « Validation manuelle requise » par
_has_unconfirmed_fundamental_warning().

Qu'un tel volume porte un message rigoureusement uniforme suggère un
déclencheur systématique plutôt qu'une file de validation légitime. Si la
moitié de l'univers porte en permanence une alerte que personne ne traite, le
statut cesse de porter de l'information. Sujet de CONFIANCE, distinct de
l'étape 7. Diagnostic requis dans liquidation_engine.py pour identifier
l'origine de la chaîne. Non traité à ce stade.

---

## [2026-07-22] Persistance des champs décisionnels dans le snapshot d'analyse

Niveau 2 — Approuvé, implémenté, vérifié.

Ajout de trois champs à `SNAPSHOT_FIELDS` (`src/history_engine.py`) :
`add_eligibility_status`, `add_eligibility_reason`, `auto_estimate_dependency`.

Aucun calcul nouveau. Ces champs sont déjà produits par
`compute_add_eligibility_status()` (`src/add_eligibility_engine.py`) et par
`src/data_reliability_engine.py` ; ils n'étaient simplement pas projetés dans
le snapshot par `_snapshot_row()`.

Motif : le système écartait des candidats à chaque run sans tracer pourquoi.
Lacune d'auditabilité réelle. Rend Dette-03 caduque.

Vérification : 577 tests OK avant et après, SCORE_STABILITY STABLE avant et
après, 266/266 titres portent les trois champs remplis, git diff = 3 lignes
ajoutées / 0 supprimée dans un seul fichier.

Diff CSV : exonéré par double run sans changement de code. Les deltas CSV
observés (`market_data_age_hours`, `market_data_fetched_at`, `run_id`,
`timestamp`, `canadian_checked_at`, `avg_latency_ms`, `observation_count`) se
reproduisent à l'identique entre deux runs consécutifs sans patch. Bruit de run,
pas régression.

Distribution obtenue sur 266 titres :
MANUAL_REVIEW_BEFORE_ADD 127, DO_NOT_ADD 81, ADD_ALLOWED_SMALL 28,
ADD_ALLOWED 24, ETF_HOLD_ONLY 5, BENCHMARK_FALLBACK 1.

Manifestation de Dette-01 : le snapshot mode-scoped s'écrit
`reports/latest_analysis_snapshot_high-cagr.json` (tiret, via `_mode_slug` de
`history_engine.py`), et non `high_cagr` comme le produit `mode_artifacts.py`.
Tout prompt futur référençant un artefact mode-scoped doit vérifier la
convention du moteur concerné avant de nommer le fichier.

Hors périmètre, à arbitrer ultérieurement : `add_eligibility_size` est produit
par `add_eligibility_engine.py` mais reste non persisté ; la nécessité de
propager ces champs aux trois CSV externes n'est pas tranchée.

---

## [2026-07-22] Artefacts research_needed et validation_priority mode-scoped (Niveau 2, Approuvé)

**Constat.** La décision [2026-07-01] impose que les artefacts `latest_*` produits
par `analyze` aient un miroir suffixé par mode. Deux artefacts y échappaient :
`latest_research_needed.csv` et `latest_validation_priority.csv`. Aucun fichier
suffixé n'existait sur disque, alors que ~38 autres artefacts avaient le leur.

Conséquence : la décision [2026-07-22] désignait
`latest_research_needed_high_cagr.csv` comme fichier de référence opérationnel
pour décider quels rapports BNCD déposer. Ce fichier n'existait pas.

**Décision.** Les deux artefacts reçoivent leur miroir mode-scoped. Traitements
différents car ils sont écrits à des moments différents du cycle :

- `latest_validation_priority.csv` est écrit à l'intérieur de `generate_reports()`,
  donc avant le passage du miroir. Inscription dans `_MODE_SCOPED_REPORT_OUTPUTS`
  (`report_generator.py`).
- `latest_research_needed.csv` est écrit dans `main.py` APRÈS l'appel à
  `generate_reports()`, donc après le passage du miroir. L'inscription dans la
  liste aurait échoué en silence (`if not source.exists(): continue`). Écriture
  de la paire via `write_csv_records_mode_pair()` de `mode_artifacts.py`.

**Infrastructure canonique.** Un premier correctif importait `_report_mode_slug`
depuis `report_generator.py`. Diagnostic ultérieur : `src/mode_artifacts.py`
(créé le 2026-07-01) est l'infrastructure canonique — 72 sites d'appel, 7 moteurs
consommateurs (backtest, walk-forward, full-audit, model-audit,
improvement-audit, audit-signal, walk-forward-signal), 4 tests dédiés. Elle
expose `write_csv_records_mode_pair()`, conçue exactement pour ce cas. L'import
parasite a été retiré ; il était le seul usage externe de l'infrastructure privée
de `report_generator.py`.

**Vérification empirique de [2026-07-01].** Premier test de non-contamination
cross-mode jamais exécuté depuis l'adoption de cette décision. Un run complet
`analyze --mode balanced` a été lancé après un run `high-cagr`, puis
`latest_scores_high_cagr.csv` a été comparé à sa référence en excluant les
colonnes d'horodatage réécrites à chaque run (`market_data_age_hours`,
`market_data_fetch_attempted_at`, `canadian_checked_at`). Résultat : identique.
Les artefacts `high_cagr` survivent à un run d'un autre mode. La décision
[2026-07-01] est vérifiée, pas seulement documentée.

**Dette identifiée, non corrigée.**
- Dette-01 : trois conventions de slug coexistent. `mode_artifacts.py` et
  `report_generator.py` produisent `high_cagr` ; les `_mode_slug()` locaux de
  `audit_snapshot_engine.py`, `history_engine.py`, `allocation_change_engine.py`
  et `model_audit_engine.py` conservent les tirets (`high-cagr`). Visible sur
  disque : `latest_scores_high_cagr.csv` vs `latest_audit_snapshot_high-cagr.json`.
  Aucune casse aujourd'hui, chaque module étant cohérent avec lui-même. Risque :
  un module qui lirait avec la mauvaise convention.
- Dette-02 : `report_generator.py` maintient `_report_mode_slug`,
  `_mode_report_path` et `_mirror_mode_specific_report_outputs` en parallèle de
  `mode_artifacts.py`. Après ce correctif, cette infrastructure n'a plus aucun
  consommateur externe. La faire déléguer serait un Niveau 2 propre.

Les deux dettes sont différées en fin de Phase 2, avec le garde-fou de
vraisemblance juste-valeur. Aucune ne bloque la Phase 2.

**Changements.**
- `src/report_generator.py` : `"latest_validation_priority.csv"` ajouté à
  `_MODE_SCOPED_REPORT_OUTPUTS`.
- `main.py` : import de `write_csv_records_mode_pair` depuis `mode_artifacts`,
  import de `RESEARCH_NEEDED_COLUMNS`, calcul des lignes factorisé en une seule
  fois, écriture de la paire générique + suffixée.
- `research_needed_command()` inchangée : la commande CLI reste sur le chemin
  dégradé assumé de [2026-07-22] et n'écrit que le fichier générique. Lui
  ajouter un miroir suffixé propagerait un classement dégradé dans un artefact
  mode-scoped.

**Vérifié.** 577 tests, SCORE_STABILITY STABLE avant et après. Miroirs identiques
aux génériques (diff vide). Aucune régression de contenu. Aucun fichier parasite
`latest_*_.csv`. Non-contamination cross-mode confirmée.

---

## [2026-07-22] Chemin CLI `research-needed` — classement dégradé assumé (Niveau 2, Approuvé)

**Constat.** `ticker_validation_value_score()` lit `allocation_decision`,
`final_action`, `capital_allocation_score` et `promotion_status`. Ces champs ne
sont écrits que par le moteur d'allocation. La commande `research-needed`
appelle `build_position_analyses()` sans jamais lancer l'allocation : ces clés
sont absentes, et le score se réduit aux composantes universe / evidence /
dependency / thesis.

Écarts mesurés (2026-07-22) : RHM.NE 57.0 → 43.0 ; WAB 48.0 → 34.0 ;
ASML 52.0 → 0.0 (score titre négatif borné par `max(0.0, ...)`).

Incomplétude préexistante à la Phase 2, masquée temporairement par un mécanisme
auto-référentiel introduit hors périmètre en 6c et retiré en 6c-fix.

**Décision.** `analyze` est la source de vérité unique du classement
`research_needed`. `research-needed` est un chemin dégradé assumé : ordre
cohérent en interne (CLI1 == CLI2 vérifié), mais non aligné sur `analyze`.
La commande émet un avertissement explicite.

**Rejeté — option A** (lancer l'allocation dans le CLI) : ajoute une seconde
invocation du moteur d'allocation à maintenir en cohérence, alourdit un chemin
secondaire, et n'augmente pas la confiance dans les décisions du modèle.
Échoue au filtre de phase de maturation.

**Rejeté — option C** (supprimer la commande) : perte fonctionnelle réelle
(relancer la liste sans refaire une analyse complète).

**Conséquence opérationnelle.** Le fichier de référence pour décider quels
rapports BNCD déposer est `latest_research_needed_high_cagr.csv` produit par
`analyze`, pas celui produit par `research-needed`.

---

## [2026-07-21] Refonte du sous-système des rapports de recherche BNCD

Statut : Approuvé
Niveau : 3 (architectural)

### Contexte
- Diagnostic lecture-seule du 2026-07-21 (`reports/diagnostics/bncd_report_subsystem_audit_2026-07-21.md`)
  sur 3 rapports réels CSU.TO : analyste Morningstar (19 mai), tear sheet Morningstar (17 mai),
  Banque Nationale (13 mai).
- Bug critique confirmé : le parsing extrait fair_value = 3.6 au lieu de 3600 pour les nombres à
  séparateur de milliers. Ce champ corrompu est compté comme confirmé et fait passer la fiabilité
  de 62 à 82 (HIGH), la dépendance aux proxys à LOW, et le verdict de SIMILAR_TO_VFV à
  CLEARLY_BETTER_THAN_VFV. Conséquence : une donnée fausse promeut le titre en conviction.
- Couverture partielle : le tear sheet seul est jugé non exploitable (1 champ) alors qu'il contient
  juste valeur, moat et P/E ; le format Banque Nationale ne livre que 3 champs.
- Inférence de ticker : suffixes .NE et .DE non gérés (RHM_... infère RHM au lieu de RHM.NE).
- Deux moteurs de priorité divergents : research_needed_rows_from_analysis_rows classe par titre et
  par sévérité des trous de données ; build_validation_priority_rows classe par champ et par potentiel.
- Une position proposée non détenue avec données gratuites complètes ne déclenche aucune
  recommandation de rapport BNCD (confirmé : research_needed_triggered = false).
- Le champ description d'entreprise du rapport compact est toujours vide, alors que les trois formats
  de rapport contiennent une description exploitable.

### Décision
Refonte en 2 phases, prompts atomiques séparés. Chaque prompt préserve la suite de tests (baseline
réelle : 558 tests) et SCORE_STABILITY, vérifiés avant et après.

### Phase 1 — Fiabilité et couverture de l'extraction
1. Parsing des nombres propre à l'extraction de rapports (format anglo-saxon : virgule = séparateur
   de milliers), sans modifier safe_float() global qui gère volontairement la décimale française des
   CSV. Capture du nombre groupé complet et ciblage de la valeur courante/en-tête plutôt que du
   premier match (les rapports contiennent des justes valeurs historiques).
2. Extraction de la description d'entreprise, du secteur et de l'industrie, alimentant le rapport compact.
3. Extension des extracteurs au format tear sheet Morningstar.
4. Extension des extracteurs au format Banque Nationale.
5. Correction des suffixes .NE et .DE dans l'inférence de ticker.

### Phase 2 — Priorisation
6. Le classement de research_needed dérive du score de valeur de validation
   (agrégé au niveau titre), pour que les deux listes soient cohérentes.
   6a. Extraction de la fonction titre dans validation_priority_engine.py
   (composantes univers, allocation, evidence, dependency, ticker_validation,
   thesis). La borne max(0.0, ...) reste dans _priority_score() : la fonction
   titre peut retourner une valeur négative.
   6b. Tri appliqué dans research_needed_rows_from_analysis_rows() :
   -ticker_potential_score primaire, priorité en départage. Import LOCAL de
   validation_priority_engine (ce module importe research_reports en tête).
   Colonne ticker_potential_score ajoutée en fin de RESEARCH_NEEDED_COLUMNS.
   6c. Même tri appliqué dans main.py::merge_research_needed_rows().
   6c-fix. Retrait d'un bloc auto-référentiel non demandé introduit hors
   périmètre en 6c (lecture de latest_research_needed.csv pour récupérer des
   scores antérieurs : écrasait des scores frais, lisait l'artefact générique
   non suffixé par mode en violation de [2026-07-01], parsing CSV fragile).
   Ce retrait a exposé une divergence réelle préexistante entre analyze et le
   CLI research-needed, tracée dans [2026-07-22].
   6d. Renommage ticker_investment_potential_score() →
   ticker_validation_value_score() (Niveau 1). Le nom d'origine suggérait un
   « potentiel d'investissement » alors que la fonction mesure la valeur
   d'une validation : 26 de ses points proviennent de la FAIBLESSE des
   données (evidence ESTIMATE_HEAVY +16, dependency HIGH +10). Un titre mal
   documenté score haut non parce qu'il est prometteur, mais parce que le
   valider a de la valeur. La colonne CSV ticker_potential_score reste
   inchangée pour ne pas casser les consommateurs. Docstring réécrite pour
   documenter cette sémantique et le fait que la fonction peut retourner une
   valeur négative.
   6e. Avertissement console sur la commande research-needed signalant le
   classement dégradé (voir [2026-07-22]).
7. Déclencheur : toute position proposée à l'allocation et non détenue génère une
   recommandation de rapport BNCD, indépendamment de la sévérité des trous de
   données. Définition arbitrée de « non détenue » : hors CORE_PORTFOLIO +
   proposé à l'allocation. PAS la définition stricte « 0 action dans
   portfolio.csv ».

### Règle de résolution multi-rapports (par catégorie de champ)
- Valorisation et estimations (fair_value, forward_pe_manual, peg_manual, valuation_vs_5y_avg_ok,
  eps_growth_estimated_3_5y) : récence d'abord, hiérarchie de source en départage.
- Jugements structurels (moat_clear, management_quality_good, description, secteur, industrie) :
  hiérarchie de source d'abord (Morningstar analyste > tear sheet Morningstar > Banque Nationale),
  récence en départage.
- roic_5y_avg : hiérarchie d'abord. Une source non-Morningstar n'est acceptée qu'en dernier recours et
  doit être marquée comme définition divergente (la BN publie un ROIC TTM ~23 % là où Morningstar
  affiche 15-16 % ; le champ est censé contenir une moyenne 5 ans).
- fair_value depuis une source non-Morningstar (cours cible de courtier) : accepté uniquement en
  dernier recours, si aucune juste valeur Morningstar n'est disponible pour le titre. Un cours cible
  à 12 mois n'est pas une juste valeur intrinsèque DCF : il intègre le momentum et le sentiment de
  marché sur un horizon court, alors que le modèle raisonne sur des décennies. Le champ doit donc
  être marqué comme définition divergente et sa confiance abaissée à LOW. Un titre dont la seule
  juste valeur provient d'un cours cible ne doit pas atteindre une fiabilité HIGH sur cette base.
  Justification : pour une petite entreprise sans couverture Morningstar, un cours cible tracé et
  marqué vaut mieux qu'un proxy yfinance non validé.
- Drapeaux de risque booléens : union prudente — si une source signale un risque, il est signalé.
- Plafond absolu : tout champ issu d'un rapport de plus de 24 mois est ignoré, toutes catégories confondues.

### Champs descriptifs
Nouvelle catégorie de champs (description d'entreprise, secteur, industrie) extraits des rapports mais
exclus du calcul de fiabilité, exclus de research_report_fields et sans effet sur
research_report_has_usable_fields ni sur les plafonds de fiabilité. Usage strictement informationnel.

### Contraintes
- REFACTOR-01 : aucune fonction ajoutée à utils.py.
- REFACTOR-02 : aucune dépendance ajoutée à report_generator.py.
- La logique partagée entre les deux moteurs de priorité vit côté validation_priority_engine.py
  (qui importe déjà research_reports) ou dans main.py, pour éviter un import circulaire.

### Conséquences
- Les rapports déjà déposés devront être re-parsés après la Phase 1 : les champs corrompus seront corrigés.
- Aucune décision d'allocation ne doit s'appuyer sur un dépôt de rapport tant que la Phase 1 étape 1
  n'est pas livrée et vérifiée.

---

## [2026-07-20] Réparation sources canadiennes — Niveau 2

### Decision
Réparer les sources canadiennes prouvées réparables et désactiver proprement
SEDAR+ dans le flux principal.

### Reasoning
- Diagnostic: `scripts/diagnose_canadian_sources.py`.
- TMX GraphQL répondait `400` parce que la requête utilisait `marketCap` alors
  que TMX attend `MarketCap`.
- StockAnalysis est vivant pour certains titres TSXV, mais les URLs avec segment
  d'échange peuvent retourner `404` pour certains tickers; un repli symbole seul
  est prudent et borné.
- SEDAR+ retourne une page captcha Radware sur les endpoints publics testés; la
  source n'est pas exploitable en automatisation gratuite sans contournement.

### Change
- `src/canadian_data_fetcher.py`: requête TMX GraphQL réduite aux champs validés.
- StockAnalysis: repli d'URL sans segment d'échange après trois `404` primaires.
- User-Agent remplacé par un User-Agent navigateur standard.
- `SEDARPLUS_ENABLED = False`; le flux principal inscrit SEDAR+ comme
  `DISABLED` avec raison `Captcha Radware — source non exploitable`.

### Constraints
- Aucun contournement captcha, proxy, service tiers ou source payante.
- Aucun impact scoring, allocation, sizing, DCA ou règles de vente.
- Le comportement 404 normal des ETF sans états financiers reste inchangé.

### Expected impact
Meilleure récupération canadienne via TMX/StockAnalysis quand disponible, et
moins de fausse impression qu'une source officielle SEDAR+ est utilisable alors
qu'elle est bloquée par captcha.

---

## [2026-07-16] GOV-EXTERNAL-VALIDATION-GATE — gouvernance externe niveau 3

### Decision
Aucun candidat d'univers externe (`WATCHLIST`, `MARKET_SCANNER`,
`DISCOVERY_IDEAS`) ne reçoit d'allocation réelle sans au moins un champ
validé personnellement.

### Reasoning
- Déclencheurs: TEL le 2026-07-15 et RHM.DE le 2026-07-05 ont montré qu'un
  ticker externe pouvait devenir admissible avec 100% de données auto-estimées
  yfinance.
- En mode `high-cagr`, un ticker externe peut être très prometteur, mais il ne
  doit pas recevoir de capital réel tant qu'au moins une donnée n'a pas été
  validée par l'utilisateur via rapport BNCD/Morningstar local ou
  `sync-manual-inputs`.
- La règle protège contre les faux positifs de données gratuites sans rendre le
  scoring plus conservateur pour le Core Portfolio.

### Change
- `src/allocation_engine.py`: ajout de `_has_personal_validation_evidence()`.
- Gate externe ajouté dans `_external_candidate_allowed()` et
  `_high_cagr_overflow_eligible()`.
- Blocage annoté avec `external_validation_status =
  BLOCKED_PENDING_PERSONAL_VALIDATION`.
- Candidats externes validés annotés `VALIDATED_DATA_PRESENT`.
- 2026-07-16 — Visibilité rapport compact: les candidats bloqués sont listés
  en section 6 avec nom de PDF suggéré (changement d'affichage, Niveau 2).

### Constraints
- Aucun changement au scoring, aux seuils des profils A/B, aux règles DCA ou au
  Core Portfolio.
- Aucune nouvelle fonction dans `utils.py`.
- Aucun changement décisionnel à `report_generator.py`; la mise à jour
  2026-07-16 est limitée à l'affichage compact.

### Expected impact
Un titre externe peut toujours être détecté comme intéressant, mais il doit
être validé au moins minimalement avant de recevoir une allocation réelle.
Le capital est redirigé vers VFV ou un autre candidat admissible si le gate
bloque un externe non validé.

---

## [2026-07-05] Correctifs opérationnels — session audit institutionnel

### Decision
Appliquer trois correctifs mineurs identifiés lors de l'audit institutionnel:
défense des fonctions money()/pct() contre les chaînes non-numériques,
export des champs data gap vers latest_scores.csv, et alias RHM.DE → RHM.NE.

### Reasoning
- money()/pct() plantaient sur "N/D" lu depuis un ancien CSV d'allocation
  → bloquait la génération de tout rapport après un run avec cache périmé.
- score_data_gap_haircut/flag/label étaient calculés mais non exportés
  → données d'audit inaccessibles sans modifier le code.
- RHM.DE (Xetra) et RHM.NE (NEO) sont la même entreprise (Rheinmetall AG)
  → sans alias, le modèle pouvait allouer vers RHM.DE comme position séparée.

### Change
- src/report_generator.py: money() et pct() défensifs contre toute valeur
  non-numérique; retournent la valeur brute si c'est un placeholder connu.
- src/report_generator.py: colonnes score_data_gap_haircut, score_data_gap_flag,
  score_data_gap_label ajoutées à SCORES_COLUMNS et _score_row_for_csv().
- config/ticker_aliases.yaml: alias RHM.DE → RHM.NE avec raison documentée.

### Constraints
- Aucun changement au scoring, à l'allocation, aux seuils, ni aux règles DCA.
- Aucune nouvelle fonction dans utils.py.
- Aucune nouvelle dépendance directe dans report_generator.py.

### Expected impact
Rapport généré correctement même après un run avec données périmées.
Champs data gap visibles dans latest_scores.csv pour chaque run.
RHM.DE résolu vers RHM.NE dans tous les univers.

---

## [2026-07-05] Gestion des exceptions top-level dans run_analysis()

### Decision
Entourer le corps complet de run_analysis() d'un try/except qui écrit
latest_run_crash_log.json avant de relancer l'exception.

### Reasoning
- Un crash non géré en milieu de run produisait silence total: aucun rapport
  partiel, aucune trace dans le run log, aucun diagnostic.
- En phase de maturation, chaque run doit laisser une trace auditale même
  en cas d'échec — c'est une exigence de fiabilité opérationnelle.

### Change
- main.py: try/except autour du corps de run_analysis() après make_run_id().
  Le bloc except écrit {run_id, timestamp, mode, capital, error_type,
  error_message, traceback_tail} dans reports/latest_run_crash_log.json.
  Le re-raise final préserve la visibilité du crash pour l'appelant.
- Aucun import global ajouté — imports inline dans le bloc except uniquement.

### Constraints
- Aucune logique à l'intérieur du try n'est modifiée.
- Aucun autre module modifié.

### Expected impact
Les runs qui plantent produisent maintenant un fichier de diagnostic
immédiatement lisible sans avoir à fouiller les logs système.

---

## [2026-07-05] Haircut données manquantes + labels data gap dans scoring.py

### Decision
Appliquer un haircut modéré à score_total quand plusieurs critères sont
MANUAL_REQUIRED, et produire un label de transparence des données.

### Reasoning
- Avant ce changement, une entreprise avec missing_count=5 et une avec
  missing_count=0 pouvaient avoir le même score_total si les critères
  présents étaient identiques. L'inconnu était traité comme le neutre.
- En phase de maturation, l'inconnu doit légèrement pénaliser le score
  pour discriminer les positions confirmées des positions estimées.
- Le label (COMPLET/PARTIEL_MINEUR/PARTIEL_MODERE/PARTIEL_SEVERE) rend
  la qualité des données visible sans modifier l'éligibilité.

### Change
- src/scoring.py: haircut de -0.2 par critère manquant au-delà de 2,
  plafonné à -1.0. Appliqué à score_total uniquement.
  score_confirmed reste non affecté par le haircut.
- Nouveaux champs retournés: score_data_gap_haircut (float),
  score_data_gap_flag (bool), score_data_gap_label (str).

### Constraints
- score_confirmed n'est pas affecté.
- Aucun changement à l'allocation, aux seuils d'éligibilité, ni à la
  logique de conviction.
- Aucune nouvelle fonction dans utils.py.

### Expected impact
Meilleure discrimination entre positions à données confirmées et positions
à données estimées. Visibilité accrue de la qualité des données dans
latest_scores.csv et le rapport compact.

---

## [2026-07-05] Scoring magnitude continu C1/C3/C5/C6

### Decision
Remplacer le scoring binaire 0/1 sur quatre critères quantitatifs par une
courbe continue proportionnelle au ratio valeur/seuil_profil.

### Reasoning
- Le scoring binaire était le défaut architectural le plus impactant du
  modèle: une entreprise à 15% ROIC (seuil pile) et une à 45% ROIC
  recevaient le même score C1. Cela compressait les scores dans une bande
  étroite et réduisait la discrimination entre compounders exceptionnels
  et compounders marginaux.
- Les seuils sont exprimés en multiples du seuil profil pour que la courbe
  soit équitable entre profiles (REIT vs compounder de qualité).
- Les critères qualitatifs (C2, C4, C9) et hybrides (C7, C8, C10) restent
  inchangés — la magnitude s'applique uniquement où les données le justifient.

### Change
- src/scoring.py: fonction locale _magnitude_score(value, threshold)
  avec courbe: 0.0 sous le seuil, 0.4 à 1×, 0.7 à 1.75×, 1.0 à 2.5×.
  Interpolation linéaire entre les points.
  Appliquée à C1 (ROIC), C3 (EPS hist 5y), C5 (EPS est 3-5y), C6 (CAGR secteur).
  Détails de critère affichent maintenant ratio=X.XX× pour auditabilité.
- src/model_version.py: MODEL_RULES_VERSION =
  "2026-07-05-continuous-magnitude-scoring-v2"
  Cela réinitialise proprement le SCORE_STABILITY baseline et sépare
  l'évidence walk-forward pre/post changement.

### Constraints
- C2, C4, C7, C8, C9, C10 inchangés.
- conviction_engine.py inchangé.
- allocation_engine.py inchangé.
- Aucun seuil d'éligibilité ou règle DCA modifié.
- La version modèle signale une rupture intentionnelle de version.

### Expected impact
Meilleure séparation entre compounders exceptionnels et marginaux.
Distribution des scores plus étalée (confirmé: 5.21–9.65 vs bande étroite
antérieure). Les décisions d'allocation reflètent mieux la qualité réelle.
Historique walk-forward antérieur correctement étiqueté comme pre-v2.

---

## [2026-07-05] Universe snapshotting par run

### Decision
Écrire un snapshot JSON léger par run d'analyse dans
reports/universe_snapshots/, capturant tous les tickers scorés avec leurs
métriques clés au moment de la décision.

### Reasoning
- Le walk-forward backtest utilise latest_scores.csv qui est écrasé à
  chaque run — aucune trace de l'univers et des scores au moment de
  chaque décision passée.
- Sans snapshots persistants, la validation walk-forward reste théorique:
  on ne peut pas comparer ce que le modèle recommandait à une date donnée
  avec ce qui s'est passé ensuite.
- Chaque run sans snapshot est un point de données walk-forward perdu
  pour toujours. L'infrastructure devait être en place maintenant.

### Change
- src/run_logging_engine.py: fonction write_universe_snapshot().
  Snapshot JSON par run_id, idempotent (n'écrase jamais un fichier existant).
  261 tickers capturés, ETFs/BENCHMARK exclus.
  Champs: score_total, conviction_score, capital_allocation_score,
  data_reliability_level, business_profile, universe, add_eligibility_status,
  opportunity_cost_status, long_term_durability_status, score_data_gap_label.
- main.py: appel de write_universe_snapshot() après chaque run réussi.

### Constraints
- Aucun engine existant (audit_snapshot, walk_forward, report_generator)
  modifié.
- Le snapshot ne peut jamais faire planter le run — I/O wrapped en try/except.
- Aucun nouveau CLI argument.

### Expected impact
Chaque run bimensuel accumule maintenant un point de données walk-forward
réel. Après 6+ périodes espacées, la validation out-of-sample devient
opérationnelle. Prérequis atteint pour la phase de validation.

---

## [2026-07-05] Alerte staleness données marché + commande sync-manual-inputs

### Decision
Ajouter une alerte visible dans le rapport compact quand les données marché
des positions détenues sont périmées (>48h), et créer une commande CLI
sync-manual-inputs pour maintenir manual_inputs_friendly.txt à jour depuis
proxy_calibration.csv avec gating de staleness par catégorie de champ.

### Reasoning
- Sans alerte de staleness, un run avec circuit-breaker yfinance actif
  produisait un rapport complet avec des prix vieux de 65h, sans aucun
  signal visuel. Les décisions d'achat pouvaient se baser sur des données
  marché périmées.
- Le fichier manual_inputs_friendly.txt n'avait jamais été rempli malgré
  la recherche Morningstar effectuée. La commande sync-manual-inputs élimine
  le besoin d'édition manuelle du fichier INI tout en préservant une séparation
  propre entre données confirmées (proxy_calibration.csv) et pipeline d'analyse.
- Le gating Catégorie A/B distingue les données lentes (ROIC, moat — toujours
  applicables) des données marché-sensitives (fair_value, forward_pe — périmées
  après 90j). Catégorie C (sector_cagr) exclue car le proxy auto est suffisant.

### Change
Alerte staleness:
- src/report_formatters.py: alerte dans ACTIONS SYSTÈME REQUISES quand
  market_data_age_hours > 48h pour position détenue. Absente sur données fraîches.
  Affiche: nombre de positions touchées, âge maximum, cause circuit-breaker.

Commande sync-manual-inputs:
- main.py: commande CLI sync-manual-inputs.
  Source: data/proxy_calibration.csv.
  Destination: data/manual_inputs_friendly.txt (format INI).
  Catégorie A (toujours): roic_5y_avg, net_margin_stable_or_expanding,
    eps_growth_5y, moat_clear, management_quality_good, balance_sheet_strong,
    margin_or_profitability_under_pressure, confidence → manual_confidence_level.
  Catégorie B (seulement si source_date < 90j): fair_value, forward_pe_manual,
    peg_manual, eps_growth_estimated_3_5y, valuation_vs_5y_avg_ok,
    forward_pe_growth_acceptable.
  Catégorie C (exclue): sector_cagr_estimated.
  Alertes progressives: WARNING à 75j, STALE à 90j.
  Journal: data/proxy_calibration_sync_log.json (lu par rapport compact).
  Alerte rapport compact: CALIBRATION DONNÉES MARCHÉ — MISE À JOUR REQUISE
    quand des tickers ont des champs Cat.B périmés ou sans source_date.

### Constraints
- run_analysis() n'appelle pas sync-manual-inputs — la commande est manuelle.
- Le crash du sync ne peut jamais bloquer un run d'analyse.
- Aucun changement au scoring, allocation, ni aux règles d'éligibilité.

### Expected impact
Données marché périmées impossibles à manquer dans le rapport.
Données confirmées Morningstar (ROIC, moat, fair_value pour 15 tickers)
maintenant actives dans le pipeline de scoring via manual_inputs_friendly.txt.
Workflow annuel: mettre à jour proxy_calibration.csv + sync-manual-inputs.

---

## [2026-07-04] Catégorie de blocage promotion — audit-only

### Decision
Ajouter `blocking_reason_category` et `promotion_proximity_score` aux lignes
de promotion externe, puis les exposer dans le rapport compact lorsque des
candidats sont bloqués.

### Reasoning
- Un statut comme `WAIT_FOR_BETTER_DATA_OR_PRICE` ne dit pas si le blocage
  vient d’un manque de données, d’un risque cycle/bulle, d’un manque de
  supériorité face au Core Portfolio ou d’une qualité fondamentale insuffisante.
- Ces situations appellent des actions différentes: chercher un rapport
  BNCD/Morningstar, patienter sur un cycle, comparer au core, ou ignorer le
  titre pour l’instant.
- Les checks existaient déjà dans `promotion_engine`; il fallait les rendre
  lisibles sans créer de nouvelle règle active.

### Change
- Champs audit-only ajoutés dans `src/promotion_engine.py`.
- Ligne compacte `→ [catégorie] | proximité: X/15` ajoutée via
  `src/report_formatters.py` lorsque la promotion est bloquée.
- Tests ajoutés pour `DATA_INSUFFICIENT` et `CYCLE_RISK`.

### Constraints
- Aucun changement à la logique active de promotion, scoring, allocation,
  sizing, DCA ou vente.
- Aucune modification de `report_generator.py`.
- Aucune nouvelle fonction dans `utils.py`.

### Expected impact
Meilleure auditabilité des candidats externes bloqués et meilleure distinction
entre “titre potentiellement bon mais données insuffisantes” et “titre vraiment
sous la barre”, sans rendre le modèle plus conservateur.

---

## [2026-07-04] Data quality audit v1 — robustesse encadrée des sources

### Decision
Ajouter une couche additive d’audit de qualité des données autour des sources,
du cache, des fallbacks officiels et du logging, sans modifier les scores,
allocations, seuils, sizing, DCA, promotions ou règles de vente.

### Reasoning
- Le modèle dépend de sources gratuites qui peuvent être incomplètes,
  contradictoires ou temporairement indisponibles.
- Les décisions haut CAGR doivent rester pilotées par les règles existantes,
  mais l’utilisateur et les audits doivent voir plus clairement quand une
  recommandation repose sur données confirmées, proxys, cache ou sources
  partielles.
- Le renforcement doit réduire le risque de mauvaise exécution sans rendre le
  modèle mécaniquement plus conservateur.

### Change
- Métriques audit-only de couverture des champs critiques dans
  `data_reliability_engine`.
- Signal de fraîcheur critique dans `data_freshness_engine`.
- Colonnes de santé des sources: taux de confirmation, couverture partielle,
  données critiques périmées et signal d’audit.
- Retry/backoff léger dans `official_data_fetcher` et résumés de résolution
  SEC/Canada dans `data_fetcher`.
- Journaux d’exécution enrichis avec les signaux d’audit des sources.

### Constraints
- Aucun changement à la logique active de scoring, allocation, sizing,
  DCA, promotions ou ventes.
- Aucune nouvelle fonction dans `utils.py`.
- Aucune nouvelle dépendance directe dans `report_generator.py`.
- Les nouveaux signaux sont diagnostics; ils informent les audits et la
  traçabilité sans bloquer automatiquement les recommandations.

### Expected impact
Meilleure traçabilité des données, meilleure capacité à détecter une faiblesse
de source ou de cache, et décisions plus auditables sans diminuer l’objectif
de rendement long terme du mode `high-cagr`.

---

## [2026-07-03] Section informative “Ce que vous achetez” — reporting-only

### Decision
Ajouter une section informative post-allocation “Ce que vous achetez” dans
les rapports, avec profils longs des entreprises et ETF qui reçoivent une
allocation positive.

### Reasoning
- L’utilisateur doit comprendre ce que chaque titre recommandé représente
  concrètement: activité, modèle économique, secteur, rôle portefeuille et
  points simples à surveiller.
- Les ETF doivent être expliqués comme instruments de portefeuille: objectif,
  exposition, stratégie ou indice suivi, principales positions si disponibles.
- L’amélioration augmente la compréhension, la confiance et l’auditabilité
  sans ajouter une nouvelle couche décisionnelle.

### Change
- Nouveau module `src/instrument_profile_engine.py`
- Enrichissement externe gratuit optionnel si clés API disponibles
  (`ALPHA_VANTAGE_API_KEY`, `OPENFIGI_API_KEY`)
- Cache local sous `data/cached_market_data/instrument_profiles/`
- Niveau de fiabilité par profil: HIGH / MEDIUM / LOW / MISSING
- Statut de profil: COMPLETE / PARTIAL / UNCONFIRMED
- Nouveau CSV `reports/latest_instrument_profiles.csv`

### Constraints
- Aucun impact sur scores, allocations, seuils, sizing, DCA, drift,
  promotions ou décisions buy/sell.
- Les profils d’instruments ne peuvent jamais influencer une recommandation.
- Les sources externes sont optionnelles et ne peuvent jamais faire échouer
  `python3 main.py analyze`.
- Si les sources sont insuffisantes, le rapport affiche un profil incomplet
  plutôt que d’inventer une description.

### Expected impact
Meilleure lisibilité des recommandations et meilleure auditabilité qualitative,
sans rendre le modèle plus conservateur ni modifier son objectif haut CAGR.

---

## [2026-07-01] Mode-scoped latest artifacts and audits

### Decision
Séparer les artefacts `latest_*`, backtests, walk-forward, audits et preuves
d’amélioration par mode (`balanced`, `family-office`, `rational-aggressive`,
`high-cagr`) avec suffixes stables.

### Reasoning
- Les quatre modes ont des philosophies différentes et doivent accumuler leur
  historique séparément.
- Un audit ou un backtest `balanced` ne doit jamais nourrir un audit,
  un backtest, un improvement-audit ou un apply-safe-tuning `high-cagr`.
- Les fichiers génériques `reports/latest_*` restent écrits pour compatibilité
  utilisateur, mais les commandes mode-specific utilisent maintenant les
  fichiers suffixés quand elles lisent une preuve historique du mode.

### Change
- Convention de suffixe: `balanced`, `family_office`,
  `rational_aggressive`, `high_cagr`.
- Les rapports d’analyse écrivent les artefacts génériques et leurs miroirs
  suffixés.
- Les backtests exigent `latest_scores_{mode}.csv` et refusent de lire un
  `latest_scores.csv` potentiellement contaminé.
- Walk-forward, model-audit, full-audit et improvement-audit écrivent ou lisent
  les artefacts suffixés par mode lorsque la preuve est mode-specific.
- `allocation_mode_contract_engine.py` reste cross-mode et audit-only.

### Expected impact
Meilleure séparation des preuves par philosophie d’investissement sans
changement aux scores, allocations, sizing, signaux achat/vente, DCA,
drift rule, promotions ou seuils actifs. Le modèle reste scoring
fondamental + allocation gloutonne contrainte, non mean-variance.

---

## [2026-07-01] Allocation mode contract audit — diagnostic only

### Decision
Ajouter un audit de contrat des modes d’allocation qui compare `balanced`,
`family-office`, `rational-aggressive` et `high-cagr` sur une même base
de scores, sans modifier les recommandations actives.

### Reasoning
- Les quatre modes ont maintenant des philosophies très différentes, donc
  leur comportement doit rester vérifiable dans le temps.
- L’audit permet de détecter si `balanced` devient trop offensif, si
  `high-cagr` perd son filet VFV, ou si les satellites émergents dépassent
  leur rôle prévu.
- Le contrôle reste diagnostic pour éviter qu’un test de cohérence ne
  change lui-même le scoring, le sizing ou l’allocation.

### Change
- Nouveau module `src/allocation_mode_contract_engine.py`
- Nouveau CSV `reports/latest_allocation_mode_contract_audit.csv`
- Intégration dans `full-audit` via `src/full_audit_engine.py`
- Tests unitaires dédiés dans `tests/test_allocation_mode_contracts.py`

### Expected impact
Meilleure auditabilité des modes sans changement aux recommandations
d’allocation. Aucun changement de score, seuil actif, achat, vente, sizing
ou logique DCA.

---

## [2026-06-30] Overflow émergents externes autorisé — audit anomalie 3

### Decision
Modifier `_high_cagr_overflow_eligible` pour autoriser les candidats
externes VERY_DURABLE_COMPOUNDER et HIGH_GROWTH_BUT_FRAGILE à recevoir
de l'allocation overflow en high-cagr, sous garde-fous plus stricts
que la boucle principale.

### Reasoning
Audit post-implémentation a révélé que l'exclusion totale des candidats
externes de l'overflow était trop restrictive pour le mode high-cagr —
dont l'objectif est de capturer les meilleurs compoundeurs long terme
sans biais préférentiel. Un émergent externe avec conviction 90 et CAGR
VERY_HIGH mérite de recevoir l'overflow plutôt que VFV par défaut.
Les seuils overflow sont plus stricts que la boucle principale pour
compenser le risque accru de la phase d'overflow (capital résiduel
après épuisement des candidats prioritaires).

### Change
- _high_cagr_overflow_eligible : VERY_DURABLE_COMPOUNDER externe
  autorisé avec conviction >= 80, capital_score >= 68
- _high_cagr_overflow_eligible : HIGH_GROWTH_BUT_FRAGILE externe
  autorisé avec conviction >= 85 (+3 vs boucle principale),
  capital_score >= 75 (+3 vs boucle principale), VERY_HIGH obligatoire
- Tous les autres profils externes toujours exclus de l'overflow
- Garde-fous communs (thesis, liquidation, drift, etc.) inchangés
- Fichier modifié : src/allocation_engine.py

---

## [2026-06-30] Séparation budget run vs cible poids émergents — audit anomalie 2

### Decision
Introduire `HIGH_CAGR_EMERGING_SATELLITE_TARGET_WEIGHT = 0.15` pour
séparer la cible de poids portefeuille du budget par run des émergents
HIGH_GROWTH_BUT_FRAGILE en high-cagr.

### Reasoning
Audit post-implémentation a révélé que HIGH_CAGR_EMERGING_SATELLITE_BUDGET
(0.225) était utilisée à deux fins distinctes dans _target_post_contribution_
weight : une fois comme budget run (correct) et une fois comme cible de
poids portefeuille (incorrect — trop élevé pour un satellite fragile).
Un émergent HIGH_GROWTH_BUT_FRAGILE ne devrait pas viser 22.5% du
portefeuille total — 15% est un plafond plus cohérent avec son rôle satellite.

### Change
- Nouvelle constante HIGH_CAGR_EMERGING_SATELLITE_TARGET_WEIGHT = 0.15
- _target_post_contribution_weight utilise la nouvelle constante pour
  les émergents HIGH_GROWTH_BUT_FRAGILE externes en high-cagr
- _external_budget_room conserve HIGH_CAGR_EMERGING_SATELLITE_BUDGET
  (0.225) pour le budget par run — inchangé
- Fichier modifié : src/allocation_engine.py

---

## [2026-06-30] Documentation constantes mortes high-cagr — audit intégration

### Decision
Ajouter des commentaires explicatifs dans EXTERNAL_ALLOCATION_BUDGETS
et EXTERNAL_INDIVIDUAL_CAPS pour signaler que les valeurs high-cagr
sont ignorées par le code.

### Reasoning
Audit post-implémentation de la Proposition 8 a révélé que les valeurs
high-cagr dans ces deux constantes ne sont jamais lues — les fonctions
_external_allocation_budget() et _external_individual_cap_fraction()
ont des cas spéciaux qui court-circuitent ces constantes pour high-cagr.
Sans documentation, un futur développeur pourrait modifier ces valeurs
en croyant changer le comportement, sans effet réel.

### Change
- Commentaires ajoutés dans EXTERNAL_ALLOCATION_BUDGETS["high-cagr"]
  et EXTERNAL_INDIVIDUAL_CAPS["high-cagr"]
- Aucune logique modifiée

---

## [2026-06-30] Ouverture high-cagr à tous les univers + budget satellite

### Decision
Ouvrir `high-cagr` à watchlist, market_scanner et discovery avec seuils
stricts différenciés par profil de durabilité, et introduire un budget
satellite de 22.5% par run pour les compoundeurs émergents.

### Reasoning
- La restriction à core_analyses créait un biais préférentiel non justifié :
  les meilleurs compoundeurs émergents en watchlist/market étaient invisibles.
- Le vrai objectif de high-cagr est de battre le S&P 500 sur plusieurs
  décennies — cela requiert de capturer les futurs Constellation Software
  au stade émergent, pas seulement les compoundeurs déjà établis.
- Deux profils acceptés avec seuils distincts :
  Profil A (VERY_DURABLE_COMPOUNDER) : seuils stricts standard
  Profil B (HIGH_GROWTH_BUT_FRAGILE) : seuils très stricts avec
  conviction >= 82, capital_score >= 72, CAGR VERY_HIGH obligatoire,
  opportunité CLEARLY_BETTER_THAN_VFV, fiabilité >= MEDIUM
- Budget satellite 22.5% par run pour les émergents : la colonne
  vertébrale de compoundeurs prouvés reste dominante.

### Change
- `allocation_universe_for_mode` : high-cagr reçoit tous les univers
- `_external_candidate_allowed` : deux profils autorisés avec seuils
  distincts au lieu de False systématique
- `HIGH_CAGR_EMERGING_SATELLITE_BUDGET = 0.225` : nouvelle constante
- Budget satellite implémenté dans la boucle gloutonne
- Fichier modifié : `src/allocation_engine.py`

### Expected impact
high-cagr peut maintenant identifier et allouer vers les meilleurs
compoundeurs émergents sans biais préférentiel. La colonne vertébrale
de VERY_DURABLE_COMPOUNDER reste dominante. Les émergents sont plafonnés
à 22.5% du capital par run pour éviter une sur-concentration sur des
profils dont la durabilité n'est pas encore entièrement prouvée.
Aucun impact sur les autres modes.

---

## [2026-06-30] Critère d'éligibilité opportunity_cost aligné sur balanced

### Decision
Modifier `_eligible()` dans `src/allocation_engine.py` pour accepter
`SIMILAR_TO_VFV` en plus de `CLEARLY_BETTER_THAN_VFV` comme statut
d'opportunité valide en mode `balanced`.

### Reasoning
- Le critère `CLEARLY_BETTER_THAN_VFV` forçait balanced à traiter chaque
  titre comme un challenger du S&P 500 — incompatible avec le vrai but du mode.
- Le vrai but de balanced : préserver un grand patrimoine, croître au-dessus
  de l'inflation, minimiser la volatilité. Pas battre le S&P 500.
- Un titre stable, durable, à dividende croissant (ex: grande banque
  canadienne) est `SIMILAR_TO_VFV` — exactement le profil voulu en balanced.
- `EXPENSIVE_BUT_EXCEPTIONAL` reste refusé : valorisation excessive inadaptée
  à un mode de préservation patrimoniale.
- Tous les autres filtres de balanced restent intacts : VERY_DURABLE_COMPOUNDER,
  conviction >= 85, business_quality >= 85, cycle != HIGH/EXTREME.

### Change
- balanced : accepte {CLEARLY_BETTER_THAN_VFV, SIMILAR_TO_VFV}
- balanced : refuse toujours WORSE_THAN_VFV, EXPENSIVE_BUT_EXCEPTIONAL,
  TOO_EXPENSIVE, REJECTED
- Autres modes : inchangés
- Fichier modifié : `src/allocation_engine.py` (_eligible())

### Expected impact
Le bassin de candidats éligibles en `balanced` s'élargit pour inclure les
titres stables de qualité institutionnelle qui ne surpassent pas le S&P 500
mais qui préservent le capital avec dividende et faible volatilité.
Les garde-fous de durabilité, conviction et qualité business restent les
plus stricts du modèle — l'élargissement ne crée pas de risque d'inclusion
de titres de faible qualité.

---

## [2026-06-30] Activation complète continuité défensive — 3C-Inline

### Decision
Activer la logique de continuité de la Proposition 3C en passant
`previous_baseline` comme paramètre optionnel à `_defensive_fallback_rows`
via `allocate_capital` et `_optimize_monthly_contribution`.

### Reasoning
- La Proposition 3C avait codé la logique de seuil de rotation (+5 points
  au reconduit) mais `previously_allocated_defensive` n'était jamais peuplé
  dans `defensive_etf_engine.py` → continuité inactive.
- Le `previous_baseline` est déjà disponible dans `main.py` via
  `load_previous_allocation_baseline` — aucune nouvelle donnée requise.
- L'approche inline évite de modifier `defensive_etf_engine.py` et reste
  entièrement locale à `allocation_engine.py` et `main.py`.

### Change
- `allocate_capital` : nouveau paramètre optionnel `previous_baseline`
- `_optimize_monthly_contribution` : nouveau paramètre optionnel
  `previous_baseline`
- `_defensive_fallback_rows` : `previous_defensive_tickers` construit
  depuis le baseline au lieu du champ `previously_allocated_defensive`
- `main.py` : passage de `previous_baseline` à `allocate_capital`
- Fichiers modifiés : `src/allocation_engine.py`, `main.py`

### Expected impact
La logique de continuité défensive de la Proposition 3C est maintenant
pleinement active. Les ETFs défensifs reconduits bénéficient du bonus
de +5 points dans le tri de sélection. Aucun impact si `previous_baseline`
est absent (premier run, baseline vide ou None).

---

## [2026-06-30] Seuil de rotation minimal défensif — allocation_engine

### Decision
Ajouter un seuil de rotation minimal de 5 points dans `_defensive_fallback_rows`
pour éviter le churn dans la réserve défensive.

### Reasoning
- Les ETFs défensifs étaient triés uniquement par `defensive_score` sans mémoire
  de l'allocation précédente.
- Une variation de 1-3 points de score pouvait générer une rotation inutile :
  frais de transaction réels et impact fiscal potentiel en compte taxable.
- Le churn dans la réserve défensive est particulièrement risqué en `balanced`
  (jusqu'à 45% du capital en réserve défensive) et `family-office` (20%).
- La correction est entièrement locale à `_defensive_fallback_rows` sans
  dépendance à `allocation_stability_engine` ni paramètre externe.

### Change
- Ajout de `DEFENSIVE_ROTATION_MIN_EDGE = 5.0` comme constante globale
- Un ETF défensif reconduit reçoit un bonus de continuité de +5 points
  dans le tri de sélection uniquement
- Un challenger doit dépasser le reconduit d'au moins 5 points pour
  déclencher une rotation
- Fallback sûr : si `previously_allocated_defensive` est absent,
  comportement identique à avant
- Fichier modifié : `src/allocation_engine.py` (_defensive_fallback_rows)

### Expected impact
Élimination du churn défensif causé par du bruit de score.
Les rotations défensives restent possibles mais exigent un avantage clair.
Aucun impact sur l'éligibilité, les plafonds de concentration, ni la
logique VFV ou des modes high-cagr et rational-aggressive.

---

## [2026-06-30] Chunk size différencié par mode — allocation_engine

### Decision
Modifier `_monthly_chunk_size` dans `src/allocation_engine.py` pour différencier
le plafond de chunk par mode.

### Reasoning
- Le plafond fixe de 50$ était identique pour les 4 modes malgré des philosophies
  d'investissement opposées.
- Pour les gros capitaux (>2 000$), balanced et high-cagr avaient la même
  granularité de boucle, effaçant la différence de concentration souhaitée.
- high-cagr doit concentrer directement → chunks plus grands.
- balanced doit fragmenter finement → plafond fixe conservé à 50$.

### Change
- high-cagr    : plafond = max(50$, capital * 2%)
- rational-aggressive : plafond = max(50$, capital * 1.5%)
- family-office : plafond = max(50$, capital * 1.2%)
- balanced     : plafond fixe 50$ (inchangé)
- Fichier modifié : `src/allocation_engine.py` (_monthly_chunk_size)

### Expected impact
La granularité de la boucle gloutonne reflète maintenant la philosophie de chaque
mode. Aucun impact sur les montants finals pour les petits capitaux (<2 000$).
Pour les gros capitaux, high-cagr concentre plus directement en moins d'itérations.
Aucun changement à l'éligibilité, aux plafonds de concentration, ni à la logique VFV.

---

## [2026-06-30] Durability adjustment asymétrique par mode — allocation_engine

### Decision
Modifier `_marginal_monthly_score` dans `src/allocation_engine.py` pour rendre
le signal de durabilité asymétrique en mode `high-cagr`.

### Reasoning
- Le signal `durability_adjustment` était identique pour les 4 modes malgré
  des philosophies d'investissement très différentes.
- En `balanced`, le filtre d'éligibilité exclut déjà les titres non durables —
  le penalty dans le score marginal était donc redondant.
- En `high-cagr`, pénaliser `HIGH_GROWTH_BUT_FRAGILE` à -2.0 risquait d'écarter
  des compoundeurs prospectifs à fort potentiel CAGR au profit de titres établis
  mais à croissance plus modérée.

### Change
- `high-cagr` : VERY_DURABLE_COMPOUNDER +4.5 (vs +3.0),
  HIGH_GROWTH_BUT_FRAGILE -1.0 (vs -2.0), DURABLE_BUT_CYCLICAL +0.75 (vs +0.5)
- Autres modes : table originale inchangée
- Fichier modifié : `src/allocation_engine.py` ligne ~1008

### Expected impact
Meilleure discrimination entre candidats durables en high-cagr sans sacrifier
le potentiel de rendement des titres à forte croissance prospective.
Le changement n'affecte pas l'éligibilité, les plafonds, ni la logique VFV.

---

## [2026-06-29] Thesis reversal audit — diagnostic only

### Decision
Add an audit-only `thesis_reversal_engine.py` layer to detect possible investment thesis deterioration or reversal across analyses.

### Reasoning
- `thesis_engine.py` gives the current thesis status, but the model also needs to know whether a change versus local history looks like a real deterioration.
- The layer uses only data already available in the pipeline: local history, thesis/proof/sell-validation fields, source reliability, source conflicts, parsed local research, official/company data already merged into analyses, yfinance/Yahoo fields and existing news context.
- It must explicitly separate fundamental conclusions from deterioration mainly caused by weak, stale or conflicting data.

### Expected impact
The reports now include `reports/latest_thesis_reversal_audit.csv`, a detailed audit-only table in the full report and a one-line compact signal. The change does not modify scoring, allocation, sizing, buy/sell recommendations, cash rules, or promotion gates.

---

## [2026-06-29] Backtest transaction friction audit — diagnostic only

### Decision
Add an audit-only transaction friction layer to theoretical and walk-forward backtests.

### Reasoning
- Gross backtests can overstate real execution if spreads, FX conversion drag or small illiquid trades are ignored.
- The model is used in a Canadian/Quebec context where commissions may be low, but CAD/USD FX and spreads can still matter.
- The friction layer should expose this execution drag without changing the fundamental scoring system or monthly allocation.

### Expected impact
Backtests now keep their gross results and add estimated net-after-friction fields plus `reports/latest_backtest_friction_audit.csv`. The change does not modify scoring, sizing, buy/sell recommendations, DCA rules, or promotion logic. The model remains a fundamental scoring + constrained greedy allocation system, not a mean-variance optimizer.

---

## [2026-06-29] Weakest core composite audit — observe before activation

### Decision
Add an audit-only comparison between the active weakest-core selection and a composite candidate selection.

### Reasoning
- The active weakest-core logic can influence external promotion decisions, so changing it directly would be too risky without evidence.
- The composite candidate considers durability and cycle/bubble risk, but remains observational only.
- Fallback benchmarks are excluded in the candidate logic through `is_fallback_benchmark()` instead of expanding hardcoded ticker exclusions.

### Expected impact
Better auditability of future promotion logic, with no change to scoring, allocation, buy/sell recommendations, or active external promotion behavior.
Primary visibility is `reports/latest_weakest_core_audit.csv` and the full audit. The compact report only shows a one-line `AUDIT-ONLY` alert when the active and candidate weakest-core selections differ.

---

## [2026-06-28] Alternative benchmark comparisons — audit only

### Decision
Add configurable passive and mechanical benchmark comparisons to the theoretical backtest and walk-forward validation.

### Reasoning
- VFV.TO remains the primary benchmark, but VFV-only validation is incomplete.
- XEQT, a Canadian 60/40 benchmark and a simple ETF momentum benchmark provide broader audit context.
- The momentum benchmark uses only price history available before each simulated decision date.

### Expected impact
Better validation of model behavior against simple alternatives, with no change to scoring, sizing, allocation, selling, cash levels or recommendation eligibility.

---

## [2026-06-28] Sequential crisis diagnostics — stress tests remain diagnostic only

### Decision
Add stylized multi-phase crisis scenarios to `src/stress_test_engine.py`.

### Reasoning
- Static one-shot shocks do not show the path risk of a crisis unfolding over several months.
- Sequential diagnostics help identify max drawdown, worst phase, resilient tickers and main loss contributors.
- The model should understand crisis trajectory risk without becoming a statistical optimizer.

### Expected impact
Better portfolio risk interpretation during crisis-style diagnostics, with no automatic sell signal, cash raise, allocation override or change to fundamental scoring.

---

## [2026-06-28] Architectural hubs — intentional deferral

### Decision
Keep src/utils.py and src/report_generator.py as central hubs for now.

### Reasoning
- Project is still in active feature development
- Refactoring hubs mid-development risks cascading bugs across 40+ modules
- The pattern is acceptable at current scale

### Constraints imposed immediately
- New engines must NOT add new functions to utils.py — only import from it
- New engines must follow the existing report_generator call pattern — 
  no new direct dependencies

### Planned resolution
- Phase 2 (stability): decompose utils into focused submodules 
  (utils_math, utils_dates, utils_formatting, utils_io)
- Phase 3 (productionize): decouple report_generator using an event 
  or facade pattern so engines emit data objects instead of calling 
  report_generator directly

---

## 2026-06-24 — Adopt long-term DCA as core strategy

### Decision
The system uses Dollar Cost Averaging (DCA) as the baseline investment strategy.

### Reason
- Reduces timing risk
- Improves behavioral discipline
- More robust than market timing

### Expected impact
More stable long-term returns with lower variance.

---

## 2026-06-24 — Avoid market timing strategies

### Decision
No strategy based on short-term market prediction is allowed.

### Reason
- Market timing is not statistically reliable
- High risk of overfitting in backtests

### Expected impact
Improved robustness and reduced model fragility.

---

## 2026-06-24 — Introduce Canadian tax-aware logic

### Decision
All investment evaluation must consider Canadian tax structure (TFSA, RRSP, taxable accounts).

### Reason
- Real investor is based in Canada (Quebec)
- After-tax return is more important than gross return

### Expected impact
More realistic portfolio optimization aligned with real-world returns.

---

## 2026-06-25 — Add moderate high-cagr allocation stability

### Decision
The `high-cagr` mode now uses `stability_strength_adjustment: 0.01` in `config/model_tuning.yaml`.

### Reason
- Reduce allocation churn when two eligible candidates are very close.
- Preserve responsiveness when a position deteriorates or a new candidate has a clear edge.
- Keep the high-CAGR profile focused on long-term compounding instead of short-term score noise.

### Expected impact
Slightly smoother monthly recommendations without making the mode materially more conservative.

---

## 2026-06-25 — Add soft single-name concentration throttle for high-cagr

### Decision
The `high-cagr` allocation engine now applies a soft single-name concentration throttle before the existing 30 % / 40 % drift limits.

### Reason
- Reduce repeated monthly additions to a position that is already large.
- Preserve the ability to let exceptional compounders keep growing without forced selling.
- Improve execution discipline when two high-quality candidates are close but one is materially less concentrated.

### Expected impact
More balanced contribution sizing inside the high-CAGR mandate, with lower single-name execution risk and no hard cap on existing winners.

---

## 2026-06-25 — Add durable proxy calibration evidence history

### Decision
The proxy calibration workflow now writes usable true-value/proxy comparisons to `data/proxy_calibration_history.csv` and mirrors the latest view to `reports/latest_proxy_calibration_history.csv`.

### Reason
- Preserve calibration evidence even after the user clears the working calibration CSV.
- Avoid learning from duplicate repeated analyses of the same true value/source.
- Prepare a safer future proxy bias engine without changing proxy formulas yet.

### Expected impact
Improved long-term proxy auditability with no immediate change to allocation recommendations.

---

## 2026-06-25 — Add guarded proxy bias detection

### Decision
Add `src/proxy_bias_engine.py` and export `reports/latest_proxy_bias_report.csv` after each analysis.

### Reason
- Detect possible systematic proxy bias from the durable calibration history.
- Require multiple independent, coherent examples before flagging a bias signal.
- Avoid overcorrection by not applying any formula change automatically.

### Expected impact
Better evidence for future proxy recalibration while preserving current allocation behavior and avoiding noisy self-correction.

---

## 2026-06-25 — Add supervised proxy correction layer

### Decision
Add `config/proxy_corrections.yaml` and `src/proxy_correction_engine.py` so validated multiplicative proxy correction factors can be applied before scoring.

### Reason
- Keep proxy formulas stable while allowing supervised correction factors.
- Avoid overcorrection by requiring explicit activation, numeric fields only, evidence thresholds and a ±25 % maximum factor change.
- Preserve traceability by showing active corrections in `latest_scores.csv`.

### Expected impact
No default change to recommendations because the correction file starts disabled. Future validated corrections can improve proxy accuracy without rewriting formulas directly.

---

## 2026-06-25 — Add proxy correction safety governor

### Decision
Integrate proxy corrections into `improvement-audit` and `apply-safe-tuning` with a dedicated history file at `data/proxy_correction_history.csv`.

### Reason
- Allow only very strong proxy bias signals to become SAFE auto-applicable correction suggestions.
- Require same-day audit, same mode, source-health gate, anti-overfitting gate and existing safe-tuning governor before activation.
- Record every applied proxy correction for cooldown and auditability.

### Expected impact
The model can self-correct small, repeated proxy biases under strict controls, while reducing the risk of overcorrecting formulas from noisy or stale evidence.

---

## 2026-06-26 — Add proxy correction post-activation audit

### Decision
Add `reports/latest_proxy_correction_audit.csv` and report sections that monitor active proxy corrections after they are applied.

### Reason
- Prevent a validated correction from becoming a stale or excessive source of false precision.
- Flag corrections near the ±25 % cap, old corrections, noisy new evidence or evidence pointing in the opposite direction.
- Keep rollback/review supervised instead of letting the model aggressively disable corrections during normal analysis.

### Expected impact
Active corrections remain useful but transparent. The model gains a controlled anti-overcorrection layer without making monthly allocation logic more conservative.

---

## 2026-06-26 — Add walk-forward backtest inventory foundation

### Decision
Add `src/walk_forward_backtest_engine.py` and the command `python3 main.py walk-forward-backtest --mode high-cagr`.

### Reason
- Prepare a future out-of-sample walk-forward backtest without pretending the model has enough evidence too early.
- Separate snapshots by analysis mode so `high-cagr` is never mixed with `balanced`, `family-office` or `rational-aggressive`.
- Deduplicate multiple analyses from the same day and require a minimum number of days between usable points.

### Expected impact
No change to monthly allocations. The model gains a safer audit foundation for future performance validation and lower overfitting risk.

---

## 2026-06-26 — Add guarded walk-forward period simulation

### Decision
Extend `python3 main.py walk-forward-backtest` so it simulates each usable historical allocation until the next sufficiently spaced analysis date and compares it to `VFV.TO`.

### Reason
- Test actual historical recommendations instead of rebuilding past decisions with today’s scores.
- Reduce look-ahead and survival-bias risk by using saved snapshots from the time of the recommendation.
- Avoid false confidence by excluding short periods and marking periods with excessive missing price data as non-simulated.

### Expected impact
No change to monthly allocation behavior. The model gains a more realistic audit signal, but results remain preliminary until enough spaced periods exist.

---

## 2026-06-26 — Integrate walk-forward evidence into audits and anti-overfitting gate

### Decision
`full-audit` now runs and reports the walk-forward check, and `improvement-audit` now passes walk-forward results into the anti-overfitting gate.

### Reason
- Use real historical recommendations as an out-of-sample evidence layer before applying automatic micro-tuning.
- Keep young or insufficient walk-forward history neutral so the model is not made unnecessarily conservative.
- Block only aggressive/reactive auto-tuning when enough walk-forward evidence clearly fails the do-no-harm test vs `VFV.TO`.

### Expected impact
No change to normal monthly recommendations. Safer `apply-safe-tuning` behavior with lower overfitting risk and clearer full-audit reporting.

---

## 2026-06-26 — Add walk-forward market regime diagnostics

### Decision
Add market-regime classification to walk-forward periods and export `reports/latest_walk_forward_regime_summary.csv`.

### Reason
- Avoid judging the model only from one market environment.
- Identify whether the strategy is weak in a specific regime, such as VFV weakness, flat markets or strong rallies.
- Keep the signal moderate: limited or single-regime history remains informational, not punitive.

### Expected impact
No change to monthly allocation behavior. Audit and safe-tuning decisions gain better context across market regimes without forcing broad conservatism.

---

## 2026-06-26 — Add walk-forward health and logging integration

### Decision
Add walk-forward checks to `health-check` and a dedicated run log for `python3 main.py walk-forward-backtest`.

### Reason
- Make the new walk-forward layer easier to monitor over months and years.
- Detect partial/missing walk-forward outputs without affecting monthly recommendations.
- Keep insufficient walk-forward history informational so it does not create false conservatism or false precision.

### Expected impact
No change to scoring or allocation. Better operational reliability, clearer audit trail and safer interpretation of walk-forward evidence.

---

## 2026-06-26 — Phase 2 engine-level correctness pass

### Decision
Apply the Phase 2 engine-level fixes from `PHASE2_CODEX_PROMPT.md` without changing investment thresholds, allocation philosophy, or scoring weights.

### Changes
- `src/sizing_engine.py`: reuse already-enriched cash-flow and shareholder-discipline values when present, instead of recomputing them with a slightly different dictionary.
- `src/sizing_engine.py`: prevent `sector_cagr_estimated` from being counted twice when `market_growth_thesis_score` is unavailable by using a neutral market-growth component.
- `src/conviction_engine.py`: make PEG penalties mutually exclusive so a very high PEG receives the stronger penalty only, not both penalties stacked.
- `src/add_eligibility_engine.py`: propagate a locally upgraded monitoring status through `resolved_monitoring_status` and `monitoring_status`.
- `src/allocation_stability_engine.py`: skip ETF analyses in the action-oriented stability layer.
- `main.py`: remove the first early `refresh_add_and_opportunity_context()` call and keep the final refresh after all context/risk passes.
- `src/thesis_engine.py`: memoize field-source sets inside `compute_thesis_status()` and document the two uncertainty thresholds.
- `src/opportunity_cost_engine.py`, `src/cagr_quality_engine.py`, `src/confidence_range_engine.py`, `src/sizing_engine.py`: add clarifying comments around intentional branching/constants/band differences.

### Verification
- `python3 main.py validate-inputs` passed after each fix group.
- Dead-code/integration checks confirmed:
  - `can_add_by_drift()` is used by `allocation_engine.py`.
  - Proxy bias/correction engines are integrated through `main.py`, `auto_fundamentals.py`, reports, and improvement audit.
  - `company_dossier_engine.py` is used by `report_generator.py`.
  - `sell_validation_checklist_engine.py` is used by `report_generator.py`.
  - `fund_price_fallback_engine.py` is used by `data_fetcher.py`.

### Expected impact
Minimal allocation impact except where prior behavior came from duplicated or stale intermediate calculations. The model should be more internally consistent, easier to audit, and less likely to over-penalize or mis-handle edge cases. No new conservatism was intentionally added.

---

## 2026-06-27 — Phase 3 controlled cleanup and optimization pass

### Decision
Apply the safe parts of `PHASE3_CODEX_PROMPT.md` while preserving all allocation rules, scoring thresholds, report schemas and investment behavior.

### Changes
- `src/sizing_engine.py`: added `_get_cached()` to centralize the cached/fallback read pattern introduced in Phase 2.
- `src/ticker_resolver.py`: added `load_and_resolve_universe()` and replaced repeated universe resolution blocks in `main.py`.
- `main.py`: documented the context enrichment order inside `run_analysis()` to make ordering dependencies explicit.
- `src/allocation_engine.py`: moved the small autonomous `allocation_universe_for_mode()` helper out of `main.py`.
- `src/report_generator.py`: removed confirmed unused imports and extracted pure report text helpers into `src/report_formatters.py`.
- `main.py`: documented the final ETF role guard in the allocation universe.

### Verification and deferrals
- `python3 main.py validate-inputs` passed after each change group.
- Verified that Phase 2 flagged items are active and should not be removed: drift add checks, proxy bias/corrections, company dossiers, sell checklist, fund price fallback and model version.
- `pyflakes` was not installed in the local virtual environment, so import cleanup used a conservative AST scan and removed only confirmed unused imports.
- A full split of `report_generator.py` and `main.py` was intentionally limited to safe extractions. The remaining large split is deferred because report sections, CSV writers and formatting helpers are tightly coupled and should be moved in smaller reviewed batches.
- `data_fetcher.py` was assessed but not split because the main `MarketDataFetcher` class and fallback/source logic are heavily coupled.
- `backtest_engine.py` and `walk_forward_backtest_engine.py` share only generic helper names like `_markdown_table`; their logic is intentionally different.
- `full_audit_engine.py` and `model_improvement_engine.py` share generic formatting/helper names, but no safe shared extraction was obvious without adding coupling.

### Expected impact
No intended change to recommendations. The model is slightly easier to maintain, has less duplicated plumbing, and has clearer guardrails for future refactors without reducing high-CAGR behavior.

---

## 2026-08-23 — Provenance-aware calibration freshness and confirmation

### Problem and root cause
`sync-manual-inputs` copied proxy-calibration observations into
`manual_inputs_friendly.txt` without field-level origin metadata. The loader
therefore added every populated field to `manual_override_fields`; merge logic
gave those values manual precedence, and thesis/liquidation/durability treated
them as confirmed. Category A fields, including `balance_sheet_strong`, had no
expiry, so an old calibration Boolean could become a permanent fundamental fact.

### Risk
- False fundamental `WEAKENING` from stale calibration evidence.
- Historical observations silently becoming current manual facts.
- Stale calibration outranking current automated, research, or official data.
- Contradictory semantics across thesis, monitoring, and sell-risk engines.
- Contamination of later validation evidence by incorrect source authority.

### Architectural principle and fix
`PROXY_CALIBRATION_SYNC` is not `HUMAN_MANUAL`. Generated friendly inputs now
retain source, source date, generated snapshot values, and field-level origin.
Human edits remain supported and are preserved through later syncs. Calibration
freshness is field-specific: valuation/forward fields use 90 days; balance sheet
and margin pressure 120 days; margin direction 180 days; sector 365 days;
historical ROIC/EPS 548 days; moat/management 730 days. Stale or undated
calibration remains visible as context but cannot independently establish
confirmation or outrank current research/official evidence. Material conflicts
are surfaced for monitoring/manual review. Genuine manual, qualifying research,
and current official confirmation remain authoritative.

The one-time upgrade of a legacy generated friendly-input file is fail-closed.
Before writing either the friendly file or sync log, every populated legacy field
must be safely reconcilable and equivalent to the current calibration source.
Any difference or legacy-only/unknown field raises a ticker/field diagnostic and
leaves both files unchanged; the operator must reconcile it before metadata is
generated, then reapply any intended human value to the metadata-bearing file.

### Non-goals and history
No ticker-specific exception, scoring-weight change, allocation-threshold change,
valuation-rule change, new alpha feature, automatic trading, or broad validation
redesign. Existing history is preserved; only future classifications use the
corrected evidence semantics. The behaviorally meaningful correction advances
`MODEL_RULES_VERSION` to
`2026-08-23-provenance-freshness-confirmation-v3`.

### Testing
Focused regression coverage includes explicit human, research, official,
automatic, fresh/stale calibration, source conflict, real deterioration,
catastrophic protection, valuation-only, generated-file round-trip, preserved
user edit, research precedence, and VRT-like cases. Model-wide impact analysis
uses stable fixtures when operational ignored inputs are unavailable.

---

# 🧠 Rule

No major change can be applied to the system without being documented here.

## 2026-08-23 - Validation evidence authority and causal history scope

The project now uses one validation contract in `src/validation_evidence.py`.
Current-score historical simulations are `MECHANICAL_DIAGNOSTIC`: favorable
returns have no positive strategy-validation or tuning authority, while
pathological results retain negative warning authority. Primary walk-forward
periods are built causally from explicit scheduled/manual decisions; diagnostic,
development, maintenance and zero-capital runs remain auditable without
fragmenting that timeline. Legacy purpose remains explicit uncertainty and is
never reconstructed from future returns.

Primary model stability is `CURRENT_VERSION_AUDIT`; older observations and
version transitions remain visible only through `CROSS_VERSION_DIAGNOSTIC`.
Execution/data/source confidence is separate from strategy/walk-forward
confidence, and evidence maturity preserves raw counts without claiming proven
skill. Behavioral tuning is code-level `PROPOSAL_ONLY` during Baseline V1
evidence accumulation. These validation-only changes add
`VALIDATION_SCHEMA_VERSION=2026-08-23-validation-architecture-v1` and do not
change `MODEL_RULES_VERSION`, scoring, allocation, holdings or deployment.

## 2026-08-23 - Primary model audit uses comparable decision purposes

The primary `CURRENT_VERSION_AUDIT` contract is now the intersection of the
current `MODEL_RULES_VERSION` and the canonical genuine-decision purposes
`SCHEDULED_DECISION` / `MANUAL_DECISION`. Diagnostic, development-test,
zero-capital, maintenance and `UNKNOWN_LEGACY` observations remain preserved and
counted as audit context, but cannot increase primary stability sample size,
evidence maturity, confidence, model health history or tuning support.

Daily model-audit selection retains `(date, model_rules_version, run_purpose)`
identity before applying the existing deterministic latest-observation rule.
Consequently, a later diagnostic cannot replace an earlier genuine decision on
the same day. Cross-version transition counts are computed only between
comparable decision observations; non-decision version changes remain visible
without becoming ordinary investment instability. This additive correction
advances `VALIDATION_SCHEMA_VERSION` to
`2026-08-23-validation-architecture-v2`; `MODEL_RULES_VERSION`, formulas,
thresholds, investment behavior and `PROPOSAL_ONLY` remain unchanged.

## 2026-08-23 - Legacy walk-forward is diagnostic, not genuine OOS authority

The causal `LEGACY_PARTIALLY_RECOVERABLE` fallback remains available for
simulation, price outcomes, robustness inspection and historical audit. It does
not reconstruct an unknown historical purpose. Periods sourced from
`UNKNOWN_LEGACY` are therefore classified as
`HISTORICAL_STRESS_SENSITIVITY` and explicitly carry no positive
strategy-validation authority.

Only current-version, successfully simulated periods sourced from explicit
`SCHEDULED_DECISION` or `MANUAL_DECISION` observations and classified
`POINT_IN_TIME_WALK_FORWARD` count as `genuine_oos_periods`, evidence maturity,
strategy/walk-forward confidence, full-audit positive authority or tuning
support. Period output now preserves `run_purpose_status`, `eligibility_basis`,
`evidence_class` and `strategy_validation_authority`; summaries preserve total,
genuine and legacy counts separately. This additive correction advances
`VALIDATION_SCHEMA_VERSION` to `2026-08-23-validation-architecture-v3` without
changing investment logic, `MODEL_RULES_VERSION` or `PROPOSAL_ONLY`.

## 2026-08-23 - Research-report semantic integrity

### Problem
Research-report extraction could promote semantically different or LOW-confidence
analyst observations into canonical confirmed model inputs. In particular, broker
12-month targets could become intrinsic `fair_value`, Morningstar Price/FVE could
become a historical five-year valuation signal, non-five-year ROIC could become
`roic_5y_avg`, and keyword presence could create qualitative false positives.

### Corrections
- Research fields now retain an auditable extracted/applied/advisory lifecycle.
- LOW-confidence fields remain visible but cannot replace automatic/proxy values,
  remove proxy corrections, or count as confirmed reliability evidence.
- MEDIUM fields apply only without higher-authority official evidence; HIGH remains
  research provenance and follows the same source hierarchy.
- Intrinsic fair value is separated from informational `broker_target_price_12m`.
- Report Price/FVE is retained as informational evidence and no longer populates
  `valuation_vs_5y_avg_ok`, removing that C9/C10 semantic double count.
- Only explicit five-year-average ROIC populates `roic_5y_avg`; current/TTM and
  trailing-decade observations remain informational.
- Qualitative risk extraction requires explicit high-risk semantics and ignores
  obvious reversal/negation contexts.
- OCR and poor-text confidence downgrades now reduce application authority through
  the existing provenance and reliability interfaces.

### Non-goals and compatibility
No scoring weight, allocation threshold, portfolio rule, investment factor,
historical record, workflow, deployment, NLP/ML engine, or operational input was
changed. The P1 provenance/freshness architecture remains authoritative; research
feeds its canonical `research_report_fields`, field provenance, source-conflict,
and `data_reliability` interfaces. There is no parsed-research cache, so no cache
schema migration or destructive cleanup is required; future runs parse reports
with the corrected semantics.

Because corrected canonical inputs can change valid scores and recommendations,
`MODEL_RULES_VERSION` advances from
`2026-08-23-provenance-freshness-confirmation-v3` to
`2026-08-23-research-semantic-integrity-v4`.

## 2026-08-23 - Deep averaging-down evidence safeguard and combined chart

### Problem and risk
The allocator could positively reward additional purchases into a falling owned
position even when current evidence was insufficient or materially conflicted.
That could create a feedback loop in which a price decline increased drawdown
attractiveness and new capital while the supporting thesis evidence was not
trustworthy enough.

### Policy
The safeguard uses the existing canonical whole-portfolio position across all
accounts. When positive CAD current value and positive CAD acquisition cost are
both available, `combined_position_return = current_value_cad /
acquisition_value_cad - 1`. At or below the single explicit policy threshold of
`-20%`, additional room is zero unless every pre-existing quality-drawdown
condition passes, canonical data reliability is `HIGH`, no existing
large-allocation manual review remains required, and neither a
`DIRECTIONAL_REVIEW` nor `MATERIAL_REVIEW` source profile (or a current
fundamental-evidence conflict) is unresolved. Technical/period differences do
not activate the material-conflict block.

The rule is stateless. It blocks only additional capital for the current
analysis, never sells, liquidates, blacklists, or creates a cooldown. Invalid or
missing normalized cost basis produces `UNKNOWN`; no return is fabricated and
the special `-20%` room block is not activated. New candidates are outside this
averaging-down policy. Existing positive drawdown rewards are gated by the same
quality-evidence exception; unrelated scoring and normal concentration/sizing
limits remain unchanged.

### Portfolio aggregation and chart
Portfolio 1 and Portfolio 2 remain one economic portfolio for ticker, sector,
cluster, factor, and total-risk concentration. The existing account SVG renderer
now also emits `charts/account_ALL_ACCOUNTS.svg` from the same canonical account
rows, aggregating a duplicate cross-account ticker into one combined slice while
preserving every existing account chart.

### Non-goals and versioning
No stop loss, sell rule, transaction memory, cooldown, ticker-specific rule,
reliability framework, concentration redesign, scoring weight, threshold sweep,
backtest optimization, systemd change, deployment, or operational-data mutation
is introduced. Because this is a behaviorally meaningful allocation correction,
`MODEL_RULES_VERSION` advances from
`2026-08-23-research-freshness-authority-v5` to
`2026-08-23-deep-drawdown-allocation-safeguard-v6`.
`VALIDATION_SCHEMA_VERSION` remains
`2026-08-23-validation-architecture-v3`.

## 2026-08-23 - P4B allocation-room integrity

### Problem and root cause

The normal high-CAGR path enforced the documented cumulative 22.5% run budget
for external `HIGH_GROWTH_BUT_FRAGILE` satellites through
`_external_budget_room()`. The intentional high-CAGR overflow path used a
separate room calculation that preserved watch and cycle budgets but omitted
the satellite run budget and its existing individual 15% portfolio target. A
deterministic $1,000 two-satellite fixture therefore allocated $650 combined.
The allocation denominator also silently became $100,000 whenever summed
current value was zero, authorizing percentage room that the inputs did not
support.

### Decision

Normal and overflow allocation now consume one shared applicable-hard-room
contract. It takes the minimum of each path's intentional strategy room and all
hard invariants applicable to that candidate. The aggregate satellite budget is
recomputed after every chunk across all qualifying tickers and includes normal
allocations before overflow. The existing 15% constant remains an individual
fragile-satellite post-purchase target. P3, reliability, drift, watch, and cycle
precedence remain authoritative; the shared helper only reduces room.

A genuinely empty portfolio uses zero current value and the current contribution
as its post-contribution denominator. An owned portfolio in which any position
lacks a valid positive current-value basis receives no percentage-based stock
room and falls through to the existing defensive/VFV path. A complete valid
current value, including the canonical `current_value_cad` fallback, retains
existing behavior. The fabricated $100,000 fallback is removed.

### Compatibility and versioning

Intentional core and durable-external high-CAGR overflow remains unchanged and
does not inherit the fragile-satellite budget. No new sector, hidden-cluster, or
factor threshold is introduced; no scoring, thesis, sell, rebalancing,
provenance, reliability-interpretation, validation-schema, or entity-resolution
logic changes. `MODEL_RULES_VERSION` advances from
`2026-08-23-deep-drawdown-allocation-safeguard-v6` to
`2026-08-23-allocation-room-integrity-v7`.
`VALIDATION_SCHEMA_VERSION` remains
`2026-08-23-validation-architecture-v3`.

### External-review correction: current-value authority and EMPTY denominator

The unmerged v7 implementation is corrected without a version change. An owned
position whose `portfolio_valuation_source` is `acquisition_value_fallback` is
now unsafe for percentage-based allocation room even though the loader retains
a positive acquisition-cost approximation in `current_value`. The fields and
loader semantics are unchanged; only allocation-room authority is denied. Valid
market/FX-derived values, explicit manual current-value fallbacks, legacy
explicit values, and positive backward-compatible fixtures without source
metadata remain accepted. Any mixed owned portfolio containing an
acquisition-cost fallback fails closed for whole-portfolio percentage room.

`EMPTY_PORTFOLIO_POST_CONTRIBUTION` has a trustworthy denominator equal to the
contribution, so the existing `>34%` high-CAGR overflow concentration check now
applies to EMPTY as well as VALID portfolios. The threshold, normal targets,
satellite budgets, scoring, and all other overflow semantics are unchanged.

## 2026-08-24 - P6 Final Baseline V1 hardening and freeze

### Decision

Baseline V1 is identified separately as `VALIDATION_BASELINE_V1`. The identity
is additive validation metadata: `MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7` and `VALIDATION_SCHEMA_VERSION`
remains `2026-08-23-validation-architecture-v3`. `baseline_started_at` is left
blank until the approved deployment, so this implementation cannot
retroactively label development observations as Baseline forward evidence.

Decision-capable analyses now write a deterministic manifest with the Git SHA,
run purpose, model/baseline/schema identity, configuration/input/research/data
fingerprints, dependency fingerprint, and final decision-output fingerprint.
Generation timestamps and run IDs do not enter the semantic manifest
fingerprint. Failed critical-input runs contain no allocation and have no
forward-evidence authority.

The direct `analyze` path no longer creates a missing portfolio or continues
through malformed critical portfolio/configuration state. A missing or empty
decision portfolio, corrupted required YAML, unusable VFV price, unsupported
cost basis, or unsafe acquisition-value portfolio basis fails closed. Optional
research/watchlist limitations and explicit manual current-value fallbacks
remain advisory. Scheduled input synchronization was already fail-closed and
is preserved.

Production raw analysis-log retention increases from 20 to a bounded default of
100; structured validation histories are not part of that rotation. Health
checks now expose the baseline/version/tuning identity, dependency drift,
manifest/history writeability, project/cache/research/log/history usage, and
free disk space without changing investment behavior or deleting evidence.

Python 3.12.13 and exact direct/transitive packages are recorded in
`requirements.lock`; minimal GitHub CI compiles the code and runs the complete
suite. Performance reporting continues to calculate TWR/XIRR for explicit
dated cash flows (or clean no-flow periods), but returns
`INSUFFICIENT_CASH_FLOW_HISTORY` instead of fabricating those metrics when the
flow date is only inferred from portfolio changes.

### Investment-logic compatibility

No scoring, valuation, conviction, CAGR, VFV, discovery, promotion, add/sell,
P3, P4B, concentration, ranking, sizing, overflow, defensive allocation,
universe, ticker, currency, or global-equity rule changes. Auto-tuning remains
`PROPOSAL_ONLY`; global coverage remains deferred until after Baseline V1.

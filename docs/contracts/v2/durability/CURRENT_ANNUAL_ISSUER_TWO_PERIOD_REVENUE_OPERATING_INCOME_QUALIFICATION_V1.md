# Contract A — CURRENT Annual Issuer Two-Period Revenue / Operating Income Qualification v1

**Draft revision:** `A-DRAFT-R3-2026-10-12`\
**Status:** `PROPOSED / NOT IMPLEMENTED / NO RUNTIME AUTHORITY`

## §1 — Identité et autorité

| Champ                | Valeur proposée                                                                         |
| -------------------- | --------------------------------------------------------------------------------------- |
| Evidence kind        | `CURRENT_ANNUAL_ISSUER_TWO_PERIOD_REVENUE_OPERATING_INCOME_QUALIFICATION_V1`            |
| Contract version     | `2026-10-12-current-annual-issuer-two-period-revenue-operating-income-qualification-v1` |
| Qualification policy | `2026-10-12-issuer-same-filing-adjacent-annual-pair-v1`                                 |
| Identity version     | `2026-10-12-d1-comparative-evidence-identities-v1`                                      |
| Result type          | `CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1`                     |
| Proposed module      | `economic_facts.sec_current_annual_issuer_two_period_revenue_operating_income`          |
| Authority            | `CURRENT_ISSUER_TWO_PERIOD_REPORTED_OPERATING_FACTS_EVIDENCE_ONLY`                      |
| Temporal mode        | `CURRENT_CAPTURE_BOUND_ONLY`                                                            |
| Source kind          | `SEC_COMPANYFACTS_SNAPSHOT`                                                             |

La qualification établit uniquement si une capture SEC Companyfacts vérifiée permet de constater quatre faits financiers, répartis sur deux périodes annuelles immédiatement adjacentes, dans une présentation commune cohérente.

Elle n'établit pas une continuité de périmètre économique, de sujet comptable, de structure juridique ou d'avantage concurrentiel.

La révision documentaire `A-DRAFT-R3` distingue cette proposition de la première rédaction. Elle ne constitue ni une nouvelle version native autorisée ni une adoption canonique.

## §2 — Entrées, capture et confiance

Factory proposée :

`qualify_sec_current_annual_issuer_two_period_revenue_operating_income_v1(archive, receipt_id)`

Entrées exactes :

- `archive` : instance native exacte de `SecArchive`.
- `receipt_id` : chaîne hexadécimale minuscule de 64 caractères.

Aucun CIK, montant, intervalle, accession privilégié, fait financier ou résultat de qualification ne peut être fourni par l'appelant.

La qualification SHALL :

1. Relire un reçu effectivement présent dans l'archive.
2. Vérifier son identité, son schéma et **l'égalité exacte** `receipt.acquisition_contract_version == "2026-09-11-sec-live-companyfacts-v1"`; la simple appartenance à la liste de contrats supportés par `SecArchive` ne suffit pas.
3. Vérifier **l'identité de source exacte** `receipt.endpoint == receipt.source_locator == endpoint_for(receipt.cik)`; ces trois valeurs doivent être égales, et non seulement individuellement valides.
4. Vérifier l'objet source, sa longueur et son SHA-256.
5. Vérifier le CIK du JSON normalisé contre `receipt.cik`; tout CIK absent ou incohérent est une erreur d'intégrité.
6. Extraire et qualifier exclusivement les octets vérifiés.

Sont interdits : acquisition réseau, nouvelle capture, recherche implicite d'un autre reçu, fallback temporel, mutation de l'archive ou dépendance à l'heure d'exécution.

La provenance LIVE reste une garantie locale fondée sur les mécanismes PAM, non une attestation cryptographique distante de la SEC.

Un reçu absent, corrompu ou détaché déclenche une erreur d'intégrité, pas `EVIDENCE_UNAVAILABLE`.

## §3 — Concepts, unités et faits exacts

Réutiliser l'extracteur natif `2026-10-07-sec-revenue-operating-income-extraction-v1`.

Concepts autorisés exclusivement :

- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`
- `us-gaap:OperatingIncomeLoss`

Unité : `USD`. Base comptable : `US_GAAP`.

Chaque observation conserve :

- Valeur originale `Decimal`, y compris zéro et valeurs négatives.
- Concept, namespace, unité.
- Dates `start` et `end`.
- `fy`, `fp`, `form`, `filed`, `accn`, `frame` facultatif.
- Ligne source brute, pointeur, limite de métadonnées et identité d'observation.
- Provenance de capture et d'extraction.

Aucun arrondi, float binaire, alias, changement de devise, remplacement de concept, annualisation ou normalisation n'est permis.

Les doublons égaux restent des observations distinctes. Leur valeur numérique peut être représentée par un scalaire canonique seulement après consensus exact.

L'inventaire exhaustif des deux concepts, toutes unités et présentations confondues, reste conservé pour l'audit.

## §4 — Surveillance annuelle et sélection CURRENT

La surveillance précède les filtres d'admissibilité.

Une observation est potentiellement annuelle si :

1. `fp=FY`, indépendamment des autres métadonnées.
2. Sa durée inclusive est comprise entre 364 et 371 jours.
3. Le contexte est incomplet dans une présentation 10-K/10-K/A susceptible d'être annuelle.
4. Des métadonnées incomplètes et un `fy` entier, sans `fp` trimestriel explicite, laissent une interprétation annuelle ouverte.

La valeur `fy` est une information de millésime de dépôt, non une preuve du calendrier économique.

Préserver les cas corrigés dans l'architecture Quality :

- 10-K/Q4 avec début manquant : surveillance.
- 10-Q/Q4 avec début manquant et `fy` entier : aucune présomption annuelle fondée uniquement sur `fy`.
- FY explicite : surveillance même lorsque les autres champs sont défavorables.
- Durée annuelle apparente : surveillance même lorsque `fp` ou `form` paraît défavorable.

L'endpoint `CURRENT` est le maximum des dates `end` valides des observations apparemment annuelles des deux concepts.

Une observation apparemment annuelle sans endpoint déterminable bloque l'établissement.

À cet endpoint, un seul intervalle annuel de 365 ou 366 jours inclusifs doit être démontré. Plusieurs débuts admissibles, une durée incompatible ou un contexte matériel non résolu bloquent l'établissement.

Il est interdit de choisir un endpoint plus ancien pour contourner un problème constaté sur le plus récent.

Le résultat ne prétend pas connaître l'exercice absolument le plus récent de l'émetteur, seulement le plus récent apparent dans la capture vérifiée.

## §5 — Populations et détermination de PRIOR

**Clause corrigée A-2.**

### 5.1 Populations normatives

Les populations sont dérivées exclusivement de l'inventaire source, sans sélection par l'appelant.

**U — Inventaire intégral**

Toutes les observations extraites des deux concepts, avec leurs limitations et leur contexte.

**L — Surveillance annuelle**

Toutes les observations de U identifiées comme apparemment annuelles selon §4, y compris celles qui ne seront pas admissibles.

**C — Intervalle CURRENT**

L'unique intervalle annuel qualifiable au dernier endpoint apparent.

**F — Dépôts liés à CURRENT**

Tous les accessions contenant au moins une observation potentiellement comparable à C, y compris une seule cellule CURRENT ou un contexte CURRENT incomplet qui n'est pas démontré étranger à C.

Cette population n'est limitée ni aux dépôts complets, ni aux amendements récents. Un dépôt antérieur et un dépôt ultérieur sont examinés suivant les mêmes règles.

**Q — Présentations comparatives candidates**

Sous-ensemble de F où un même accession contient les deux cellules CURRENT et des observations des deux concepts pour une période annuelle antérieure candidate.

Seules les présentations Q complètement qualifiables et cohérentes peuvent établir les quatre cellules. Les présentations Q incomplètes restent surveillées.

**H — Dépôts historiques PRIOR-only**

Accessions ne contenant aucune observation potentiellement comparable à C, et présentant seulement un exercice antérieur de millésime distinct.

H conserve une valeur documentaire, mais ne détermine pas automatiquement PRIOR et ne participe pas au consensus de présentation commune.

### 5.2 Garde préalable

Aucune sélection PRIOR ne peut réussir avant que :

- L'endpoint CURRENT soit établi.
- L'intervalle C soit unique et admissible.
- Les deux concepts CURRENT disposent d'une **paire cohérente dans au moins un même accession de F**.

**Transition négative fermée R2-1.** Une fois C établi, construire les ensembles d'accessions contenant au moins une observation admissible pour chacun des deux concepts CURRENT, sans assemblage entre dépôts. Si les deux ensembles sont non vides et disjoints, émettre `NO_COMMON_CURRENT_ACCESSION` (`EVIDENCE_UNAVAILABLE`) et interrompre l'évaluation dépendante de PRIOR. Aucun fait CURRENT n'est sélectionné comme paire et aucune présentation quatre-cellules ne peut être établie. Si les deux concepts se rencontrent dans un même accession mais que leur métadonnée commune est matériellement contradictoire ou indécidable, émettre respectivement les motifs existants `COMMON_FILING_METADATA_CONFLICT` ou `COMPARATIVE_CONTEXT_UNRESOLVED`, jamais `NO_COMMON_CURRENT_ACCESSION` comme substitut à cette anomalie. Une absence d'un des deux concepts continue à relever de `CURRENT_*_UNAVAILABLE`. L'absence de paire cohérente, quelle qu'en soit la cause, interdit toute sélection PRIOR positive.

Si C n'est pas déterminable, aucun motif spécifique au choix de PRIOR ne doit être émis. Les problèmes observables indépendamment sur CURRENT restent évalués.

### 5.3 Sélection du prédécesseur dans les présentations pertinentes

Pour chaque accession de F disposant d'une paire CURRENT cohérente :

1. Identifier les intervalles apparemment annuels distincts de C présentés dans cet accession.
2. Ne retenir comme candidats immédiats que les intervalles dont `end < current_end`.
3. Parmi ces candidats, examiner le ou les endpoints antérieurs les plus récents dans cet accession.
4. Conserver séparément les périodes plus anciennes comme historique exclu, sans les transformer en prédécesseurs supplémentaires.
5. Soumettre tous les candidats immédiats pertinents à la surveillance contradictoire.

Une présentation ancienne de FY2024 dans un dépôt contenant déjà FY2025 et FY2026 ne devient donc pas un second PRIOR concurrent simplement parce qu'elle est annuelle.

La condition d'adjacence demeure :

`required_prior_end = current_start - 1 calendar day`

Un PRIOR admissible doit :

- Se terminer exactement à `required_prior_end`.
- Avoir une durée inclusive de 365 ou 366 jours.
- Être strictement antérieur à CURRENT.
- Disposer des deux concepts dans le même accession que la paire CURRENT.
- Respecter les exigences de cohérence et de provenance du §6.

### 5.4 Unicité de l'intervalle PRIOR

L'unicité de PRIOR est évaluée sur les présentations comparatives admissibles Q de quatre cellules, **pas sur l'union de tous les dépôts historiques H**.

Si deux présentations Q complètes et matériellement comparables proposent des débuts PRIOR distincts pour le même `required_prior_end`, elles ne permettent pas de choisir arbitrairement un intervalle. Émettre `PRIOR_ANNUAL_INTERVAL_AMBIGUOUS`.

Si une seule présentation Q complète fournit le PRIOR adjacent et que H contient un intervalle antérieur différent, H reste exclu avec justification, sauf si une observation de H révèle également un lien CURRENT matériel qui la ferait entrer dans F.

### 5.5 Intervalles alternatifs

| Situation                                                                                      | Traitement                                                                    |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Intervalle alternatif uniquement dans H, sans lien CURRENT                                     | Exclusion justifiée, sans ambiguïté PRIOR                                     |
| Intervalle plus ancien que le prédécesseur déjà identifié dans le même dépôt                   | Exclusion historique traçable                                                 |
| Deux intervalles PRIOR admissibles à starts différents dans des présentations Q complètes      | `PRIOR_ANNUAL_INTERVAL_AMBIGUOUS`                                             |
| Prédécesseur pertinent se terminant avant `required_prior_end`                                 | `PERIODS_NOT_IMMEDIATELY_ADJACENT`                                            |
| Prédécesseur pertinent chevauchant CURRENT                                                     | `PERIODS_OVERLAP`                                                             |
| Prédécesseur pertinent de durée différente de 365/366 jours                                    | `PRIOR_ANNUAL_INTERVAL_UNSUPPORTED`                                           |
| Intervalle alternatif dans F partiel, susceptible de modifier PRIOR, mais relation indécidable | `COMPARATIVE_CONTEXT_UNRESOLVED`                                              |
| Valeur contradictoire dans F, pour exactement le même intervalle PRIOR qualifié                | `COMPETING_PRIOR_REVENUE_VALUES` ou `COMPETING_PRIOR_OPERATING_INCOME_VALUES` |

Un candidat non adjacent n'est jamais ajusté artificiellement.

Une valeur PRIOR dans H ne peut être empruntée pour compléter une présentation CURRENT de F.

## §6 — Qualification des quatre cellules et arbitrage des dépôts

**Clause corrigée A-1, avec articulation A-2.**

### 6.1 Cellules obligatoires

Pour deux périodes distinctes :

| Période | Revenue        | Operating Income |
| ------- | -------------- | ---------------- |
| PRIOR   | `Decimal` fini | `Decimal` fini   |
| CURRENT | `Decimal` fini | `Decimal` fini   |

L'établissement exige au moins un accession unique présentant les quatre cellules.

L'admissibilité d'une ligne exige :

- Concept et unité exacts.
- `fp=FY`.
- `form=10-K` ou `10-K/A`.
- Dates valides et durée annuelle supportée.
- `fy` entier valide, hors booléen.
- Accession conforme à `[0-9]{10}-[0-9]{2}-[0-9]{6}`.
- Date de dépôt `period_end <= filed <= capture_UTC_date`.
- Contexte et extensions de ligne supportés.
- Valeur financière exacte et finie.

Les quatre cellules d'un accession ont une forme, date de dépôt et métadonnées de millésime cohérentes.

Le même `fy` de dépôt peut accompagner des facts provenant des deux périodes économiques; `fy` ne remplace pas `start/end`.

### 6.2 Consensus des présentations complètes

Toutes les présentations Q complètes et admissibles doivent être comparées.

Pour les mêmes quatre périodes/cellules :

- Une seule valeur économique exacte est autorisée par cellule.
- Les doublons numériquement égaux sont admis et conservés.
- Des valeurs différentes pour une même cellule et le même intervalle produisent `SOURCE_CONFLICT`.
- Une incohérence de forme, date ou millésime à l'intérieur d'un accession pertinent produit `COMMON_FILING_METADATA_CONFLICT`.

Aucun ordre de préférence n'est établi entre 10-K et 10-K/A, ni entre dépôts antérieurs et postérieurs.

Une valeur majoritaire ne remplace pas le consensus.

### 6.3 Surveillance obligatoire des dépôts CURRENT partiels

Tous les accessions F sont examinés, même si leurs observations ne forment pas quatre cellules.

L'examen porte sur chacune des cellules CURRENT présentes ou potentiellement présentes, quel que soit :

- Le rang chronologique du dépôt.
- Son statut initial ou amendé.
- La présence ou non de l'autre concept CURRENT.
- La présence ou non de faits PRIOR.
- Le nombre de cellules effectivement observées.

Une observation partielle est **effectivement comparable** lorsque sa provenance, son concept, son unité, son intervalle CURRENT exact et son contexte annuel admissible sont suffisamment établis pour comparer la même mesure économique.

Règles :

1. Si elle est effectivement comparable et égale à la valeur de référence d'une présentation quatre-cellules cohérente (provisoire jusqu'à la décision finale), elle reçoit la disposition existante `NONSELECTED` et le **motif d'exclusion** `EXCLUDED_CONSISTENT_PARTIAL_CURRENT` dans `exclusion_reasons`. Ce libellé n'est ni un statut de qualification ni une sixième disposition. Elle ne devient pas une quatrième cellule manquante. Sans référence cohérente, ce motif ne doit pas être attribué sur la base d'une égalité supposée.
2. Si elle est effectivement comparable et porte une valeur différente, émettre le motif `COMPETING_CURRENT_*_VALUES` correspondant. L'établissement est interdit.
3. Si une métadonnée manque ou contredit une condition sans permettre de démontrer que l'observation est réellement étrangère à CURRENT, émettre `COMPARATIVE_CONTEXT_UNRESOLVED` ou le motif d'incompatibilité plus précis applicable.
4. Si le contexte démontre une période différente, un fait trimestriel distinct ou un autre périmètre explicitement exclu, conserver l'observation avec son motif d'exclusion. Aucune contradiction CURRENT n'est fabriquée.
5. Une observation complète et matériellement contradictoire n'est jamais dispensée de surveillance parce qu'un dépôt cohérent plus récent existe.

Les mêmes principes s'appliquent aux observations PRIOR dans un accession F lorsqu'elles sont effectivement comparables au PRIOR qualifié.

### 6.4 Amendements et dépôts de millésimes différents

Un amendement ne supplante pas automatiquement un dépôt initial.

Un accession partiel, qu'il soit antérieur ou ultérieur :

- Peut apporter une valeur contradictoire effectivement comparable : `SOURCE_CONFLICT`.
- Peut présenter un contexte matériel indécidable : `EVIDENCE_UNSUPPORTED`.
- Peut être démontré non comparable : exclusion documentée.

Un accession H contenant seulement PRIOR, d'un autre millésime et sans lien CURRENT, reste hors du consensus same-filing.

Chacune de ses observations effectivement exclues reçoit la disposition existante `NONSELECTED` et le **motif d'exclusion** `EXCLUDED_DIFFERENT_FILING_VINTAGE_PRIOR_ONLY` dans `exclusion_reasons`; ce libellé n'est pas une disposition supplémentaire.

Cette exclusion ne vaut pas certification de comparabilité inter-dépôts ou de continuité de périmètre.

### 6.5 Dispositions et complétude

Chaque observation pertinente reçoit une disposition déterministe parmi :

- `SELECTED`
- `NONSELECTED`
- `ORPHAN`
- `UNSUPPORTED`
- `COMPETING`

Les cinq valeurs ci-dessus forment le **vocabulaire fermé des dispositions**; aucune valeur `EXCLUDED_*` ne peut apparaître dans ce champ.

Les deux libellés `EXCLUDED_CONSISTENT_PARTIAL_CURRENT` et `EXCLUDED_DIFFERENT_FILING_VINTAGE_PRIOR_ONLY` sont des **motifs d'exclusion** et jamais des dispositions ni des motifs du statut économique. Ils sont enregistrés exclusivement dans le champ immuable `exclusion_reasons` des observations de disposition `NONSELECTED`. Ce sous-vocabulaire est fermé pour ces deux cas : attribution par leurs seuls prédicats §6.3/§6.4, unicité, ordre lexical stable et absence de valeurs non déclarées. Les autres motifs techniques d'exclusion et d'arbitrage déjà prévus dans R2 restent distincts et soumis à leurs propres prédicats documentés.

`SELECTED`, `ORPHAN`, `UNSUPPORTED` et `COMPETING` ne peuvent porter aucun de ces deux libellés. L'inventaire conserve séparément les raisons de qualification et les raisons attachées aux observations. Disposition et `exclusion_reasons` participent obligatoirement à `evidence_id`, sans promotion implicite dans `semantic_id`.

Seules les observations des présentations complètes admises sont `SELECTED`.

Les observations partielles égales peuvent être conservées comme références de surveillance; elles ne deviennent pas un support établi de quatre cellules.

Les quatre groupes sélectionnés sont non vides seulement en cas d'établissement. Leur partition par concept, période et accession est vérifiable.

L'ensemble des accessions admis couvre les quatre cellules dans chacun des dépôts de support.

La qualification ne peut jamais recomposer les quatre cellules à partir d'accessions différents.

## §7 — États fermés, motifs et transitions

**Clause corrigée A-3.**

### 7.1 États

- `COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED`
- `EVIDENCE_UNAVAILABLE`
- `EVIDENCE_UNSUPPORTED`
- `SOURCE_CONFLICT`

Hiérarchie :

`SOURCE_CONFLICT > EVIDENCE_UNSUPPORTED > EVIDENCE_UNAVAILABLE > ESTABLISHED`

Les motifs sont des enums natifs fermés, uniques et triés lexicographiquement.

Les motifs des étapes non atteintes ne sont pas inventés.

### 7.2 Règle de progression

La qualification procède par étapes :

`source vérifiée → surveillance annuelle → CURRENT déterminé → dépôts F identifiés → PRIOR candidat → quatre cellules → surveillance contradictoire → état final`

Les contrôles indépendamment observables sont accumulés. Les étapes dépendant d'un intervalle encore indéterminé ne sont pas évaluées artificiellement.

En particulier :

- Pas de motif PRIOR lorsque CURRENT est indéterminable.
- Pas de comparaison des valeurs CURRENT si le contexte ne prouve pas qu'elles désignent le même intervalle.
- Pas d'émission de `PERIODS_OVERLAP` pour les deux périodes effectivement sélectionnées : un chevauchement ne peut concerner qu'un candidat rejeté.
- Pas de motif `PRIOR_ANNUAL_INTERVAL_AMBIGUOUS` du seul fait d'un dépôt H extérieur à la population pertinente.

### 7.3 Matrice normative des motifs

| Population et condition vérifiée                                                                                                                                                         | Motif à émettre                             | Famille d'état |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | -------------- |
| L vide                                                                                                                                                                                   | `NO_APPARENT_ANNUAL_PERIOD`                 | UNAVAILABLE    |
| L contient une observation annuelle sans endpoint déterminable                                                                                                                           | `ANNUAL_ENDPOINT_UNLOCATABLE`               | UNSUPPORTED    |
| Dernier endpoint sans durée CURRENT 365/366 admissible                                                                                                                                   | `CURRENT_ANNUAL_INTERVAL_UNSUPPORTED`       | UNSUPPORTED    |
| Dernier endpoint avec plusieurs débuts CURRENT admissibles                                                                                                                               | `CURRENT_ANNUAL_INTERVAL_AMBIGUOUS`         | UNSUPPORTED    |
| C établi; aucune observation admissible Revenue CURRENT                                                                                                                                  | `CURRENT_REVENUE_UNAVAILABLE`               | UNAVAILABLE    |
| C établi; aucune observation admissible Operating Income CURRENT                                                                                                                         | `CURRENT_OPERATING_INCOME_UNAVAILABLE`      | UNAVAILABLE    |
| C établi; au moins une Revenue CURRENT admissible et une Operating Income CURRENT admissible, mais leurs ensembles d'accessions sont non vides et disjoints (§5.2)                         | `NO_COMMON_CURRENT_ACCESSION`               | UNAVAILABLE    |
| Cellule nécessaire attestée seulement par une valeur absente, invalide ou non finie                                                                                                      | `FINITE_VALUE_UNAVAILABLE`                  | UNAVAILABLE    |
| C établi, présentation CURRENT liée; aucune période annuelle PRIOR adjacente observée dans une présentation pertinente et aucune possibilité de quatre cellules distribuées entre dépôts | `ADJACENT_PRIOR_PERIOD_NOT_OBSERVED`        | UNAVAILABLE    |
| PRIOR identifiable; Revenue PRIOR admissible absente dans les présentations pertinentes                                                                                                  | `PRIOR_REVENUE_UNAVAILABLE`                 | UNAVAILABLE    |
| PRIOR identifiable; Operating Income PRIOR admissible absente dans les présentations pertinentes                                                                                         | `PRIOR_OPERATING_INCOME_UNAVAILABLE`        | UNAVAILABLE    |
| Quatre cellules présentes, mais jamais dans un même accession                                                                                                                            | `NO_COMMON_FOUR_CELL_ACCESSION`             | UNAVAILABLE    |
| Prédécesseur pertinent candidat d'une durée non supportée                                                                                                                                | `PRIOR_ANNUAL_INTERVAL_UNSUPPORTED`         | UNSUPPORTED    |
| Présentations Q complètes proposant plusieurs débuts PRIOR admissibles pour le même endpoint adjacent                                                                                    | `PRIOR_ANNUAL_INTERVAL_AMBIGUOUS`           | UNSUPPORTED    |
| Dernier prédécesseur pertinent se terminant trop tôt                                                                                                                                     | `PERIODS_NOT_IMMEDIATELY_ADJACENT`          | UNSUPPORTED    |
| Prédécesseur candidat de F ayant `start < current_start <= end < current_end`                                                                                                            | `PERIODS_OVERLAP`                           | UNSUPPORTED    |
| Ligne annuelle pertinente avec form/FP incompatible                                                                                                                                      | `UNSUPPORTED_FILING_CONTEXT`                | UNSUPPORTED    |
| Ligne annuelle pertinente avec unité ou extension de contexte non supportée                                                                                                              | `UNSUPPORTED_UNIT_OR_ROW_CONTEXT`           | UNSUPPORTED    |
| Présentation partielle matériellement possible, mais comparabilité indécidable                                                                                                           | `COMPARATIVE_CONTEXT_UNRESOLVED`            | UNSUPPORTED    |
| Ligne pertinente dont la date de dépôt est incompatible avec période ou capture                                                                                                          | `INVALID_FILING_CHRONOLOGY`                 | CONFLICT       |
| Contradiction form/filed/FY interne à un accession pertinent                                                                                                                             | `COMMON_FILING_METADATA_CONFLICT`           | CONFLICT       |
| Valeur CURRENT Revenue effectivement comparable différente                                                                                                                               | `COMPETING_CURRENT_REVENUE_VALUES`          | CONFLICT       |
| Valeur CURRENT Operating Income effectivement comparable différente                                                                                                                      | `COMPETING_CURRENT_OPERATING_INCOME_VALUES` | CONFLICT       |
| Valeur PRIOR Revenue effectivement comparable différente dans la population F                                                                                                            | `COMPETING_PRIOR_REVENUE_VALUES`            | CONFLICT       |
| Valeur PRIOR Operating Income effectivement comparable différente dans la population F                                                                                                   | `COMPETING_PRIOR_OPERATING_INCOME_VALUES`   | CONFLICT       |

### 7.4 Priorité des motifs concurrents

La matrice définit des conditions d'émission, non des raisons mutuellement exclusives.

Conserver toutes les raisons réellement observées dans les populations admissibles.

Quelques règles particulières :

- Lorsque les deux concepts CURRENT sont individuellement admissibles mais qu'aucun accession ne porte les deux, émettre `NO_COMMON_CURRENT_ACCESSION` et **ne pas** émettre `NO_COMMON_FOUR_CELL_ACCESSION`, `ADJACENT_PRIOR_PERIOD_NOT_OBSERVED` ou d'autres motifs dépendant de PRIOR. La présence de faits PRIOR dans H ne change pas cette transition.
- Lorsque les deux concepts CURRENT appartiennent au même accession mais présentent une incohérence de métadonnées, appliquer `COMMON_FILING_METADATA_CONFLICT` (ou `COMPARATIVE_CONTEXT_UNRESOLVED` si le contexte est indécidable), pas `NO_COMMON_CURRENT_ACCESSION`.
- Une période précédente absente, sans présentation alternative pertinente, produit `ADJACENT_PRIOR_PERIOD_NOT_OBSERVED` **seulement après une paire CURRENT cohérente**.
- Une période précédente présente seulement dans des accessions différents, alors que les quatre cellules existent globalement et qu'une paire CURRENT cohérente a été vérifiée, produit `NO_COMMON_FOUR_CELL_ACCESSION`, sans assemblage artificiel.
- Un prédécesseur pertinent explicitement non adjacent produit `PERIODS_NOT_IMMEDIATELY_ADJACENT`, plutôt qu'un simple constat d'absence.
- Un prédécesseur pertinent chevauchant CURRENT produit `PERIODS_OVERLAP`.
- Des débuts PRIOR distincts dans des présentations complètes réellement concurrentes produisent `PRIOR_ANNUAL_INTERVAL_AMBIGUOUS`.
- Un intervalle alternatif dans H n'émet aucun de ces motifs à lui seul.
- Un amendement partiel avec une valeur effectivement comparable et différente produit `SOURCE_CONFLICT`, même si son contexte ne suffit pas à former une présentation complète.
- Un amendement dont la comparabilité demeure matériellement indécidable produit `COMPARATIVE_CONTEXT_UNRESOLVED`, pas une contradiction chiffrée présumée.

Les motifs `PERIODS_NOT_IMMEDIATELY_ADJACENT`, `PERIODS_OVERLAP` et `PRIOR_ANNUAL_INTERVAL_AMBIGUOUS` sont ainsi atteignables uniquement sur des populations définies.

### 7.5 Sorties négatives

Si l'état final n'est pas `COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED` :

- Aucun des quatre montants établis n'est exposé.
- Aucune sélection de cellules n'est exposée comme valide.
- Les groupes de supports établis sont vides.
- Les endpoints, observations brutes, limitations, dispositions, conflits et motifs peuvent rester visibles, explicitement non qualifiés.

Des combinaisons impossibles d'état, de raisons ou de champs sont des erreurs de contrat, non de nouveaux états économiques.

## §8 — Résultat immuable et provenance

Le résultat proposé est un enregistrement typé, gelé, versionné.

Il contient :

- État et motifs fermés.
- CIK source.
- Périodes CURRENT et PRIOR, lorsqu'elles sont déterminables.
- Quatre montants exacts uniquement après établissement.
- Reçu, hash d'objet, longueur, timestamp, endpoint et version d'acquisition.
- Inventaire complet des observations et engagement d'inventaire d'extraction.
- Dossiers d'accessions, limites de contexte, dispositions fermées et `exclusion_reasons` immuables/triées.
- Identifiants des observations sélectionnées, lorsqu'elles sont établies.
- Accessions supports et partitions de leurs quatre cellules.
- Ensemble des valeurs contradictoires matérielles.
- Identités `semantic_id` et `evidence_id`.
- Autorité, limites et mode temporel fixés par le contrat.

Les observations historiques exclues restent inspectables; elles ne se transforment pas en supports de preuve.

## §9 — Identités déterministes

Utiliser SHA-256 à domaines séparés et JSON canonique avec encodage économique exact des `Decimal`.

### Identité sémantique

Engage :

- Versions et contrat.
- CIK et sémantique comptable.
- Les deux intervalles lorsque définis.
- État et motifs.
- Quatre valeurs établies.
- Contradictions matérielles.
- Autorité et limites.

N'engage pas les détails de capture incidentels : path, réception, horodatage, ordre des lignes, pointeurs physiques ou accession en tant que simple métadonnée de provenance.

### Identité de preuve

Engage :

- Identité sémantique.
- Identité de reçu et hash de source.
- Provenance d'acquisition.
- Inventaire et références exactes.
- Partitions d'accessions.
- Dispositions et raisons, dont les deux motifs `EXCLUDED_*` dans `exclusion_reasons` sous `NONSELECTED`.
- Présentations support et conflictuelles.

Une recapture cohérente peut conserver la même identité sémantique tout en produisant une identité de preuve différente.

Une variation matérielle de période, valeur, statut ou contradiction change l'identité sémantique.

Les collections sont canoniquement ordonnées. L'ordre du JSON source, les doublons et les représentations Decimal équivalentes ne peuvent modifier arbitrairement la sémantique économique.

## §10 — Replay et refus des résultats fabriqués

La qualification conserve une liaison privée au `SecArchive` et au reçu exact.

Cette liaison n'est ni un champ public librement fourni, ni une preuve transportable par sérialisation.

Tout consommateur natif SHALL :

1. Vérifier le type natif exact et toutes les versions.
2. Vérifier les constantes contractuelles.
3. Vérifier la liaison privée à l'archive et au reçu.
4. Relire reçu et objet source en revérifiant **les égalités exactes** du contrat LIVE et de l'endpoint/source locator exigées au §2.
5. Refaire l'extraction, la surveillance et l'arbitrage complets.
6. Comparer intégralement le résultat reconstruit aux champs publics reçus.
7. Vérifier les deux identités.
8. N'utiliser que le résultat reconstruit.

Rejeter les objets détachés, falsifiés, incompatibles ou liés à un ancien état des octets source.

Une intégrité incorrecte déclenche une exception typée; aucune dégradation silencieuse vers `UNAVAILABLE` ou `SOURCE_CONFLICT`.

Ce replay protège la frontière locale de confiance de PAM. Il ne constitue pas une attestation distante ni une protection contre un environnement Python arbitrairement compromis.

## §11 — Limites et compatibilité

La qualification représente uniquement une comparaison descriptive issuer-level au sein d'une capture CURRENT.

Ne sont pas établis :

- Comparabilité économique inter-dépôts.
- Continuité juridique, du reporting subject ou du périmètre opérationnel.
- Normalisation comptable, EBIT, EBITDA ou ROIC.
- Résilience face à un cycle économique.
- Avantage concurrentiel, moat ou persistance future.
- Score composite ou conclusion générale de Durability.
- Admissibilité Ordinary Compounder ou PR5C.
- Calcul, modification ou calibration de Confidence.
- Modification de Quality ou Expected Return.
- Autorité PIT ou `HISTORICAL_AS_OF`.
- Admission, recommandation, classement, allocation, exécution ou production.
- Droit de redistribution des données financières source.

V1 conserve son autorité opérationnelle figée. V2 demeure un challenger.

Les contrats Quality existants, PR143/PR146, PR5C, modèles financiers et règles d'investissement restent inchangés.

**Implémentation et adoption : non autorisées par cette proposition.**

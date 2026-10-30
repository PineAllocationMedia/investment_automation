# M4 R1 — Decision reports and CEO-requested follow-up analyses
**Owner:** Financial Systems Command Center; Product & UX review pending.  
**Status:** `CANDIDATE_TEMPLATE / USER_INITIATED_ONLY`. No report or analysis is generated automatically.

## Nouveau contrat de sortie : PAMalisé, directive CEO du 2026-10-30

La [norme de rapport final PAMalisé](PAMALISED_REPORT_MASTER_R1.md) devient le **produit de sortie cible** des analyses financières complètes. Elle précise les six sections adaptatives, l'apparence dérivée du prototype PDF CEO et les critères vérifiables d'export. La **longueur du rapport entier n'est pas fixe**; seul le premier niveau de lecture conserve l'objectif indicatif <=10 minutes. Les pages internes « Bibliothèque de modules visuels » et « Règles de production » ne sont pas ajoutées au livrable investisseur. Ce contrat plus récent **supersède la préférence de présentation chat-native** du paragraphe historique R1.1 ci-dessous pour les futurs rapports; les règles financières, les droits et les preuves du M4 sont inchangés.

La nouvelle candidate [CC R1.2 PAMalisé](../project_settings/CC_R1_PAMALISED_REPORT_FIRST_20261030.txt) transporte cette sortie attendue. **Ni le PDF prototype, ni une instruction GitHub fusionnée ne créent un PDF ni ne prouvent l'installation réelle des paramètres CC.** Sur une session dont l'export est indisponible, fournir un rapport autonome prêt à exporter et déclarer `REPORT_EXPORT_NOT_VERIFIED`. Après approbation CEO de la PR et adoption manuelle des instructions, vérifier un vrai rapport rendu et ses preuves, plutôt que de réexécuter une campagne complète de pilotes.


## Composant fonctionnel PAMalisé — sortie HTML privée et imprimable

Le mode local explicite `--output pamalised-html` réutilise le **même** rapport décisionnel et détail déjà assemblés par M7/session_bridge; il produit sur **stdout uniquement** un document HTML autonome, avec palette PAM, première lecture, tableau des cinq piliers et **annexe originale conservée comme texte**. Aucun fichier n'est écrit, aucune donnée envoyée au réseau, aucun graphique ou rendement ajouté, aucun PDF produit. Le navigateur de l'utilisateur peut imprimer le HTML en PDF uniquement dans un contexte privé autorisé. En absence de route complétée : `REPORT_NOT_AVAILABLE`. Ce composant n'est **pas** une installation de Project CC, n'établit ni un export PDF direct dans Work ni une acceptation visuelle complète du prototype : `HTML_PRINT_READY_PDF_NOT_GENERATED`. Tests synthétiques isolés uniquement; intégration réelle à démontrer.

## Raffinement CEO : ouverture rédigée par CC et modules visuels libres (2026-10-30)

Le texte rigide avant `01 | L'essentiel en 60 secondes` est remplacé dans le **PDF** par une **note d'ouverture narrative**. Le rédacteur de CC interprète le mandat effectivement demandé (2 à 4 phrases, sans fait additionnel), puis livre le texte dans `presentation_inputs.opening_paragraph` avec `analysis_id`, `as_of` et éventuellement les `support_refs` existants. Le moteur PDF ne génère pas lui-même de prose IA. En absence de la note, il emploie un cadrage strictement descriptif à partir du mandat reçu, sans prétendre qu'une analyse IA supplémentaire a été effectuée. Identité/méthodes/dates restent en section 06 et annexe.

**Discrétion créative de CC :** nombre, ordre et type de graphiques, diagrammes, infographies, timelines ou tableaux peuvent varier sans quota imposé, selon la question et les preuves. La bibliothèque visuelle est **ouverte comme objectif éditorial**, mais **ne confère aucune capacité technique non implantée**. À ce stade, `presentation_inputs.visuals` offre deux modules effectivement programmés et circonscrits : `evidence_flow` relie exclusivement des `F_ID` réellement présents dans la capsule IR; `contribution_bars` représente exclusivement des pourcentages de **nouvelles contributions** transmis par M3 avec `GROSS_PROJECTION_ONLY`, identifiant concordant et somme décimale exacte de 100. Un module non étayé est omis, aucun graphique de performance/poids public prétendu personnel n'est généré. Le plan de présentation n'est **ni une nouvelle source, ni une instruction d'achat**, et n'entre pas dans les contrats de calcul/stockage. L'acceptation authentique G1 et l'exécution complète du dépôt demeurent `UNVERIFIED / NOT_RUN`.

## Correction du rendu PDF — prototype fourni par le CEO (PR #422 révisée)

**Priorité visuelle explicite :** le PDF de huit pages **fourni dans la conversation CEO du 2026-10-30** constitue la **référence de composition**. Le premier générateur PDF générique de #422 ne convenait pas. La sortie `pamalised-pdf` appelle maintenant `ai_native/pamalised_visual.py` : couverture, quatre tuiles de mandat, carte de décision vert profond, fiches d'observations IR, tableau de comparaison, section avant/après, risques, horizon et traçabilité. Les six sections investisseur sont **conditionnelles aux paquets réellement reçus**; les deux pages de bibliothèque de visuels/règles internes ne sont **pas** exportées. L'annexe source complète reste lisible et les données non appuyées ne deviennent jamais graphiques ou allocations. La réutilisation du petit visuel de marque provient exclusivement du PDF de référence fourni par le CEO, sans copie de dossiers privés. Les autres pages du prototype n'ont pas été déposées dans GitHub.

**Entrées vraies :** `request`, `ir_capsule`, `pi_delta` du parcours R1 existant et projection de contribution `new_contribution_summary_private` du module M3 uniquement avec statut `GROSS_PROJECTION_ONLY`, ID concordant, pourcentages numériques finis et somme 100 %. Ce sont des **preuves/estimations telles que transmises**, et non une authentification originale ni une allocation recommandée. La comparaison au benchmark, les stress tests, la performance et les poids de portefeuille non qualifiés restent explicitement non démontrés. Le PDF n'invente ni tickers, ni valeurs, ni horizons; une annexe plus longue peut prolonger les six pages. La composition actuelle peut encore diverger de certains arrondis/typographies du prototype; cela requiert une évaluation visuelle ciblée, pas une prétention de reproduction parfaite.

**État et déclenchement :** démonstration locale PDF **synthétique** créée/rendue/inspectée depuis une version expérimentale du composant visuel; tests du code exact sur un checkout GitHub authentique et export depuis CC/Work **NOT_RUN / UNVERIFIED**. **G1 reste NO-GO** jusqu'à réception, ouverture et inspection d'un vrai fichier issu du parcours autorisé, avec mandat et données financières réellement accessibles. L'export `pamalised-pdf` exige un consommateur capable d'attacher les octets privés à l'utilisateur; aucune installation automatique de Project ni dépôt des données personnelles n'est supposé.

## Sortie PDF locale optionnelle (après HTML #420)

Le nouveau `--output pamalised-pdf` compose, à la demande, un **vrai PDF binaire sur stdout** depuis le même couple rapport exécutif/détail déjà validé. Le composant `ai_native.pamalised_pdf.render_pamalised_pdf` réutilise le contrôle strict de parité du générateur HTML, conserve le dossier source en annexe textuelle, et n'ajoute ni données, ni graphiques, ni calcul financier, ni fichier sur disque. Pour éviter une dépendance globale, l'environnement local souhaitant cette sortie doit installer explicitement la [dépendance PDF facultative](../../../../requirements-pamalised-pdf.txt) ReportLab BSD, depuis un environnement et des droits appropriés. Aucun achat, API payante ou licence commerciale n'est requis pour ce composant expérimental; la compatibilité réelle avec tous les appareils et la distribution commerciale globale de PAM ne sont pas évaluées.

**Preuve limitée :** un PDF synthétique a été effectivement créé, rouvert et inspecté visuellement dans l'environnement de développement PM; tests isolés du moteur `PASS`. Tests intégrés d'un checkout authentique, exécution du CLI GitHub par CC/Work, installation des paramètres de Project et livraison PDF à un utilisateur `NOT_RUN / UNVERIFIED`. Le CLI ne donne pas de fichier automatiquement au CEO : un consommateur autorisé doit recevoir ses octets privés et fournir le téléchargement. Ne pas déclarer le critère G1 atteint simplement parce que ce générateur est fusionné.

## Decision report — conclusions first, evidence after
Use [Operating Contract](../OPERATING_CONTRACT.md) and the actual, accessible R1 handoffs. Target at most ten minutes of reading where possible, without making report length an artificial minimum.

1. **Decision line/status:** distinguish exploratory, conditional and supported conclusions; explicit no-action when justified.
2. **Mandate:** CEO request, strategy, horizon, dated information cutoff, currencies and relevant account context only if authorized.
3. **Economic lenses:** separate Quality, Durability, Expected Return status, Confidence, and Portfolio Room only when PI has genuine dated holdings.
4. **Countercase and alternatives:** strongest contrary evidence, permanent-loss risk, material conflicting facts, qualified benchmark when available.
5. **Action or no-action:** contribution percentages only when actually justified and adding to 100%; known transaction costs, otherwise conditional.
6. **Recoverable evidence:** precise S/F/K/V/P identifiers, source dates and status, without false verification.
7. **Memory proposal:** versioned research record with analysis ID, original cutoff, actual method/prompt version and **PROPOSED_NOT_COMMITTED** archival status.

`ai_native.reporting.render_report(packet)` optionally formats a supplied packet; it does **not** collect evidence, certify facts, preserve data, schedule analyses or initiate trades.

## Reassessment — only when the CEO asks
The CEO may ask for the first analysis of a company or request re-evaluation **at any interval**. No weekly, monthly or annual default exists. A user-specified week is simply one possible historical window, never a recurring obligation.

When an actually accessible relevant previous analysis exists, compare:
- The original report ID, source cutoff, strategy/method version, thesis, assumptions, valuation and confidence as they were documented.
- Newly checked source facts with **their own** observation date, reporting basis, security class and evidence status.
- Which changes actually affect Quality, Durability, Expected Return assumptions, Confidence or Portfolio Room (the last only with a newly observed authorized portfolio).
- Contradictions, new information, key invalidation conditions, benchmark relevance and whether no investment action is justified.

Keep original findings immutable; corrections are appended, not rewritten. If no prior report is accessible, state `BASELINE_NOT_AVAILABLE` rather than claiming a change or inventing previous analysis. No update since the last user request means **NOT_CHECKED**, not no event.

## On-demand execution and required fields
The CC produces a result **only after a CEO-initiated request**. Neither these templates nor Project instructions authorize background monitoring, reminders, notifications, automatic weekly briefings or recurring analysis.

Minimum fields: `ANALYSIS_ID`, `REPORT_KIND=DECISION|FOLLOWUP`, `AS_OF`, actual `STRATEGY_ID@VERSION`, `METHOD_ID@VERSION` or `UNKNOWN_NOT_LOADED`, `FACT_IDS`, `SOURCE_LOCATORS`, `EVIDENCE_STATUS`, `CONFLICTS`, `DECISION_LINE`, `COUNTERCASE`, `NEXT_ACTION`. If FOLLOWUP: optional actual `PRIOR_ANALYSIS_ID`, with source cutoff, and optional CEO-defined interval. A comparison cannot be claimed when the previous report is inaccessible. No retrospective PIT claim.

## First decision-first executive view (component, not Project deployment)

The optional local `--output executive-report` reads the SAME completed manual R1 packet as `--output report` and produces a short French decision-first summary followed by the entire prevalidated detailed report. It does not fabricate an allocation, benchmark alpha, five-pillar rating, market-wide screening or private Portfolio Room. It preserves the source facts, dates, strategy-policy boundary, counter-thesis and next human action in the full annex. The original `--output report` and operator/closeout output contracts remain unchanged. Pending handoffs produce `REPORT_NOT_AVAILABLE`. This is a verified-source-independent formatter, not a ChatGPT Project installation or authentic three-Project acceptance; no archiving or writes.

## ChatGPT-native CC final report (R1.1 candidate, not installed)

The existing 8,000-character [copy-ready CC Project Settings](../project_settings/CC_R1_SINGLE_ACTION_PI_WORK_REVIEW_20261030.txt) now carry an explicit **final-turn** report contract: natural-language decision/status first; evidence-grounded five-pillar interpretations; a distinguishable researched candidate versus a justified new-cash percentage allocation; a precise blocker and one next human action when allocation is unavailable; and a separate S/F/K/V/P technical annex. No CLI/JSON is required of the CEO. This modifies the **Project instructions candidate**, not ChatGPT Project Settings: CEO adoption in CC and a real post-handoff report are **NOT_VERIFIED**. The existing optional local `--output executive-report` from PR #399 is unchanged and is not assumed executed by CC. No user data is archived.

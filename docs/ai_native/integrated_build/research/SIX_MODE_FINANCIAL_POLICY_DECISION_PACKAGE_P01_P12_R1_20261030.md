# PAM Financial Systems R1 — P01–P12 : paquet de propositions financières, six modes

**Version de travail :** R1-SIX-MODE-POLICY-PACK-DRAFT-v0.1 — 2026-10-30  
**Responsable :** Program Manager / WO-FS-R1-POLICY-P01-P12-DECISION-DRAFT  
**Statut :** PROPOSAL_ONLY / FINANCIAL_POLICY_NOT_APPROVED / INDEPENDENT_REVIEW_NOT_RUN / NOT_IMPLEMENTED / ACCEPTANCE_NOT_RUN  
**Périmètre :** une architecture R1 intégrée, six modes, quatre étapes de recherche et décision. **Ce dossier n'autorise ni opération ni activation.**  
**Références :** [38 choix et nuances du CEO](CEO_THREE_ROUND_SIX_MODE_SELECTIONS_R1_20261030.md), [cadre des six modes](SIX_MODE_POLICY_FRAMEWORK_R1.md), [analyse du test R1 #3](../integration/THIRD_CHATGPT_TRACE_DECISION_GAP_R1_20261030.md), [Constitution](../../../../PAM_PROJECT_CONSTITUTION.md), [contrat opérationnel](../OPERATING_CONTRACT.md).

## 0. Résultat recherché et limites d'autorité

**Problème du troisième test :** IR a trouvé des pistes valables et le transfert CC → PI → IR → PI → CC a fonctionné, mais la conclusion n'a pas suffisamment distingué admissibilité financière, véhicule achetable et destination normale de repli. Les propositions suivantes définissent les **questions exactes à trancher** pour éviter les faux blocages tout en préservant la rigueur. Elles n'ajoutent aucun rendement fictif ni vente automatique.

**Déjà contraignant :** V1 main reste gelé, V2 demeure challenger; Constitution, Gouvernance, Stratégie, DECISIONS et chartes de rôles protégées; High-CAGR V2 et les quatre modes V2 restent autoritaires **dans leur portée historique**. Une proposition R1 ne remplace ni les contrats V2 de qualification, ni le profil Expected Return déjà approuvé pour ORDINARY_COMPOUNDER/USD/US_GAAP, ni le benchmark VFV existant. Aucune règle ne s'étend par simple analogie à un modèle IFRS, une société de crédit, un FPI, une entreprise déficitaire ou une autre devise.

**Choix de conception du CEO :** 38 réponses (rondes 1–3) et nuances. Elles autorisent la **préparation** de contrats séparés, mais **pas l'approbation de politique**. Les chiffres non déjà approuvés sont étiquetés PROPOSED; les seuils manquants demeurent UNKNOWN, et non des valeurs à inventer.

**Avant toute activation :** décision explicite du CEO sur les clauses financières concernées, revue indépendante proportionnée du risque économique, des droits, de la preuve et du contrat, nouvelle version traçable, tests pertinents puis acceptation selon les gates distincts. Une fusion documentaire ne suffit pas. Le CEO contrôle séparément les fusions et la production.

**Contraintes générales :** aucun abonnement de données additionnel (coût externe de données financières 0 $), aucune transaction, aucune acquisition de portefeuille privé sans autorisation, aucun archivage de données personnelles en clair dans GitHub, aucun projet ne s'invoque automatiquement, aucun suivi récurrent par défaut. Mode choisi, objectif, horizon, type de compte, plateforme, frais/FX/taxes connus et restrictions proviennent du mandat; un fait absent reste UNKNOWN.

## 1. Contrat commun envisagé — préconditions pour tous les P

Quatre étapes distinctes :

1. **DISCOVERY** — univers ouvert mais recherche datée et délimitée; candidature économique, non admission. Identifier source, période, pays, marché, activité, instrument et couverture; conserver les rejets et cas différés.
2. **DEEP_ANALYSIS** — QUALITY/DURABILITY/EXPECTED_RETURN/CONFIDENCE et contre-thèse, normalisation sectorielle des chiffres, scénarios honnêtes et seuils de confiance séparés. Les États V2 de recherche RESEARCH_CANDIDATE, PARTIAL_ANALYSIS et FULL_ANALYSIS_ELIGIBLE décrivent la **recherche seulement**.
3. **STRATEGY_QUALIFICATION** — appliquer seulement la méthode du mode **effectivement approuvée, identifiée et chargée**. Classer séparément QUALIFIED, CONDITIONAL, EXPLORATORY et UNAVAILABLE (étiquettes proposées à définir, non nouvelles admissions V2). Une bonne entreprise n'est pas nécessairement un bon investissement au prix observé.
4. **PORTFOLIO_ROOM_AND_DESTINATION** — vérifier véhicule autorisé sur compte/plateforme, positions observées et périmètre, look-through, concentration, coûts connus, montants de nouvelle contribution, solution de repli et exceptionnelle réserve lorsque la **politique du mode** le permet. Sortie : allocation justifiée, alternative conditionnelle ou refus motivé. Jamais d'ordre.

**Registre de preuve minimal proposé (privé par analyse) :** ANALYSIS_ID; POLICY_ID et version/hash réellement chargés; stratégie, horizon et compte/plateforme explicitement déclarés; AS_OF et source/publication/observation/capture dates distinctes; issuer_economic_id; instrument_id, place de cotation, devise et éventuelle couverture; S/F/K/V/P et provenance; QUALITY/DURABILITY/EXPECTED_RETURN/CONFIDENCE/ROOM et états d'incertitude; méthode et vérification arithmétique réellement faites; coût/FX/fiscalité connue ou UNKNOWN; droits/source; résultat de chaque étape; contre-argument; décision et motif. En l'absence de base complète, produire du commentaire descriptif ou conditionnel, pas de fausse mesure d'exposition ou de rendement net.

**Comparaison et confiance :** prix actuel et devise du véhicule, année/TTM vs cash normalisé, dilution, horizon, distributions, hypothèses de valorisation terminale, benchmark et portefeuille doivent être compatibles. Un scénario BEAR/BASE/BULL n'est pas automatiquement une espérance mathématique ni un alpha probabilisé. Les données de source manquantes ne sont pas des « zéros ». Les simulations ne créent pas de faits.

**Conventions proposées d'évaluation de chaque P :** intérêt économique; formule/unité/périmètre; alternative A recommandée par PM **pour examen seulement**; option B ou C; données décisives et cas d'échec; test de régression; décision CEO en attente. La recommandation PM n'est pas un avis indépendant ni une approbation.

---

## P01 — Concentration High-CAGR : 12 % normal / 15 % exceptionnel

**Source du changement :** Q12B/Q31B/Q32A. **Conflit à examiner :** la Constitution V2 décrit un maximum initial exceptionnel autour de 20 %, alors que src/allocation_engine.py comporte en outre des seuils spécifiques WATCH/THROTTLE/STRICT : 0.18/0.22/0.30. Ces seuils de code et le maximum conceptuel ne se substituent pas l'un à l'autre; **ne pas les modifier ici**.

**Proposition A (PM) :** pour les **nouvelles contributions R1 seulement**, plafond normal initial 12 % et exceptionnel 15 % **du poids économique total de l'émetteur dans le compte explicitement analysé, après la contribution**, regroupant plusieurs cotations, ADR/CDR et détention directe ainsi que la portion ETF effectivement qualifiée et datée. Dénominateur = valeurs de marché et encaisse du périmètre de compte complet, en devise commune et date cohérente, avec nouvelle contribution. Le 15 % ne s'applique qu'après justification de la thèse, qualité des faits, risques corrélés et alternatives. Un dépassement ultérieur dû à l'appréciation déclenche **revue / ralentissement de nouvelles contributions**, jamais une vente automatique. V2 demeure tel quel.

**Alternative B :** 12/15 appliqués uniquement aux lignes directes avec revue qualitative des expositions indirectes; plus simple mais peut sous-estimer les doublons via ETF. **Alternative C :** différer le plafond numérique R1 tant que les preuves de look-through ne sont pas applicables à une source réelle.

**Faits requis :** positions et encaisse exhaustives du périmètre sélectionné, conversion datée, identité économique du sous-jacent, composition ETF datée et droits; traiter les compositions manquantes comme **fraction inconnue**, pas comme zéro exposition.

**Si information incomplète :** l'évaluation de plafond est CONDITIONAL ou UNAVAILABLE; la source visible seule permet une revue descriptive, pas une affirmation de plafond respecté. Les contributions à l'émetteur peuvent demeurer non chiffrables. La qualité de la compagnie n'est pas abaissée pour cette raison.

**À décider :** A, B ou C; application exacte aux positions historiques et exceptions de concentration (grandissement par appréciation, droits successoraux, comptes multiples) **non déterminée**. **Test :** même émetteur dans action+CDR+ETF; dénominateur incomplet; dépassement appréciation; coût FX; contribution petite/fractionnée; ancien portefeuille V2 inchangé.

## P02 — Qualification financière par modèle économique

**Source :** Q01A/Q02A/Q11C/Q20A et nuance « un peu B »; besoin du test #3. **Base V2 :** src/scoring.py et les contrats V2 QUALITY/DURABILITY/PIT sont des fondations à réutiliser selon leurs définitions et non un score opaque universel. Le Research Participation Classifier V2 indique expressément que FULL_ANALYSIS_ELIGIBLE n'est PAS une admission d'investissement.

**Proposition A :** contrat en deux gates après la découverte : **preuve économique de recherche approfondie** puis **preuve d'investissabilité, sous le mode sélectionné**. Pour toute entreprise : identifier classe/action, date, modèle d'affaires et génération/consommation de liquidité, croissance organique et par action, levier/refinancement, émission ou rachats, réinvestissement nécessaire, avantage concurrentiel, risques structurels, valorisation adaptée, source originale et contre-thèse. Contrôle indépendant des champs décisifs lorsque la conclusion serait décisionnelle. Une donnée manquante ne devient jamais un échec de qualité.

**Spécialisation requise, non scores universels :** services/logiciels (coûts récurrents, dilution, rétention), industriels (cycle, capex/ROIC), semiconducteurs (capacité, stocks, cycle), commerce+crédit (créances, risque de crédit, cash d'exploitation vs cash distribuable), banque/assurance (fonds propres/risque propres au secteur), FPI (flux distribuables/financement), biopharma (pipeline/probabilités documentées, brevets et financement) et ETF (méthodologie, coûts et look-through). Aucun multiple terminal ou ROIC non comparable n'est forcé.

**Alternative B :** exiger une grille uniforme de score V1/V2 comme admission; **non recommandé** sans équivalence démontrée, elle risque d'exclure injustement les modèles non ordinaires et de transformer une donnée indisponible en note négative.

**Conditions bloquantes :** identité/source primaire non établies, incohérence matérielle de chiffres, prix/classe/devise invérifiables, incapacité de comprendre le modèle économique ou risque de perte permanente déterminant, politique de mode absente. **Conséquence :** recherche partielle possible, investissement non admis.

**À décider :** accepter la méthode économique adaptée (A) et préciser les cas où le CEO souhaite des seuils chiffrés par famille d'entreprises; aucun seuil supplémentaire n'est ici adopté. **Tests :** entreprise de crédit avec CFO gonflé, dilution lourde, jeune société rentable en croissance, perte comptable temporaire, ETF, profil IFRS et US GAAP, source contradictoire.

## P03 — Rendement espéré manquant : Q30A prioritaire, C exceptionnel

**Source :** Q30A avec nuance du CEO : « A en priorité; si absolument impossible, recours à C ». **Doctrine actuelle :** pas d'alpha inventé, pas de rendement historique renommé « Expected Return », pas de transfert automatique du contrat mature-growth Ordinary Compounder USD/US-GAAP à d'autres profils.

**Proposition A :** 1) tenter une valorisation économiquement adaptée et une comparaison forward défendable avec un benchmark compatible; 2) approfondir les données manquantes les plus décisives sous budget de source autorisé; 3) si les conditions d'un rendement espéré calculé ne sont pas réunies, conclure EXPECTED_RETURN_UNAVAILABLE et **ne pas proposer d'allocation individuelle chiffrée**; 4) si réellement impossible (modèle non applicable, sources ne permettant pas de normaliser honnêtement les facteurs clés), autoriser uniquement une **comparaison qualitative explicitement conditionnelle** sous contrat nouveau approuvé, distinguée du droit d'allocation. La politique du mode doit définir si et comment une action humaine pourrait poursuivre une proposition.

**Alternative B :** interdire toute conclusion autre que « research only » sans ER chiffré, même lorsque la preuve économique demeure très forte. **Alternative C :** formuler directement des pourcentages conditionnels depuis une intuition qualitative; **non recommandé** sans contrat de risque et de confiance approuvé.

**Garde-fous :** attester la source de l'impossibilité, conserver hypothèses réfutables, ne pas fabriquer de probabilités, comparer coût d'opportunité et coûts connus, conserver la catégorie de recherche, envisager le benchmark/repli **autorisé** et réserver l'exception à des dossiers extraordinaires. Une différence BEAR vs BEAR ne suffit pas à établir une espérance.

**À décider :** A et conditions minimales de la voie qualitative exceptionnelle; précisément, **l'absence d'ER permet-elle seulement une sélection pour revue humaine ou, dans certains modes, une allocation conditionnelle chiffrée ?** Aucune seconde permission implicite. **Tests :** source originale manquante, ER V2 limité USD GAAP, ETF sans forward comparable, bonne entreprise mais action chère, scénario non probabilisé, source disponible malgré insuffisance de patience.

## P04 — Balanced : actifs admissibles, bandes de risque et allocation résiliente

**Source :** Q05A/Q14A/Q15C/Q16B avec nuance A/Q33A. **Base V2 :** mode balanced et hiérarchie d'investissements existants préservés; **la nouvelle adaptation multi-actifs R1 n'est pas autorisée** par le nom du mode.

**Proposition A :** recherche possible sur actions, FNB diversifiés, dette souveraine/investment-grade et or ou véhicules de couverture transparents **sans que cela constitue leur admission**. L'admission future requiert un inventaire d'instruments réellement disponibles sur compte/plateforme, de qualité de crédit, taux/duration, liquidité, change, coûts et corrélations sous stress. Définir des bandes d'exposition économique **ET** des bandes par classe d'actifs. Le mode examine avant tout la réduction des scénarios défavorables **et** de la concentration, sans allocation 60/40 par défaut. Stress de baisse 10–20 % = indicateur de conception, **pas plafond garanti**.

**Alternative B :** structure d'allocation cible fixe, revue moins fréquente; ne correspond pas à la flexibilité choisie sans nouveau choix explicite.

**Champs de politique encore UNKNOWN :** fourchettes min/max par classe et facteur, degré de diversification minimum, titres souverains/maturités/crédit admis, limite FX, références de comparaison (P09), risque de convexité/taux, budget de transaction et conditions de rééquilibrage exceptionnel. **Réserve stratégique non autorisée** par Balanced R1 sur la seule base du souhait de résilience; cash de règlement ou retrait connu reste opérationnel.

**À décider :** confirmer A; obtenir ensuite les **bandes chiffrées** et la liste des instruments (pays/qualité/crédit/duration/ETF) dans un contrat séparé, plutôt que les inventer. **Tests :** hausse brutale des taux et chute actions/obligations simultanées; ETF or non disponible; expositions sectorielles indirectes; volatilité sans détérioration; petit montant avec coût disproportionné.

## P05 — Family-Office : épargne investissable et résilience par compte

**Source :** Q06C/Q17C avec A/Q18C avec correction centrale du CEO/Q19A/Q33A. **Doctrine V2 :** family-office historique inchangé; pas d'enquête de budget familial ni d'inférence de bilan complet.

**Proposition A :** une nouvelle contribution à l'épargne déclarée dans le mandat est **investissable par défaut** pour l'analyse; ne pas redemander revenu/dépenses du foyer, patrimoine immobilier, épargne d'urgence ou budget. L'utilisateur nomme le compte, son objectif, sa période et ses contraintes connues; IR/PI analysent ce **compte individuel**. La sécurité familiale se traduit par qualité économique, diversification adaptée, risques de perte permanente, capacité de résistance aux chocs et coûts nets, **pas** par un coussin cash inventé. Une obligation explicite de liquidité est traitée comme restriction supplémentaire. Stress 10–20 % = objectif de conception, non garantie.

**Alternative B :** collecte obligatoire du budget et consolidation globale avant recommandation; **écarté par la précision du CEO**, sauf nouveau mandat express.

**Éléments à définir/faire approuver :** instruments admissibles, stress/risque vs véritables limites d'exposition, portefeuille individuel vs consolidation volontaire seulement sur preuves compatibles, liquidité déclarée et fiscalité connue, benchmark P09, différenciation claire de Balanced. Pas de vente ni de transfert intercomptes implicite.

**À décider :** confirmer la clause A et le périmètre de prudence; approuver plus tard les seuils chiffrés et instruments propres au mode. **Tests :** petite contribution sans revenus déclarés (doit progresser), compte unique, deux comptes aux données incohérentes, obligations familiales NON fournies, événement de risque sans signal de vente, réserve stratégique inventée (doit échouer).

## P06 — Rational-Aggressive : qualité et exception de société déficitaire

**Source :** Q07A/Q20A (un peu B)/Q21A/Q22A/Q34B. **Base V2 :** rational-aggressive historique, plus permissif en concentration que Family-Office mais moins que High-CAGR selon ordre conceptuel, sans transfert des propres limites High-CAGR.

**Proposition A :** admission normale fondée sur une économie et un financement déjà démontrés, qualité économique et valeur par action, prix payé et scénario d'asymétrie de rendement **net de coûts connus**. Les sociétés déficitaires sont admissibles à DISCOVERY/DEEP_ANALYSIS, pas automatiquement à INVESTMENT. Créer une **exception ultérieure, séparément approuvée**, nécessitant source vérifiée, trajectoire de financement et runway, dilution/levier, seuil de rentabilité plausible vérifiable, fragilité en stress, liquidité du titre, comparaison des alternatives, conditions de réexamen; dossier avec contre-thèse indépendante. Aucun « multiple de croissance » ne suffit à lever cette exception.

**Alternative B :** exclure définitivement toutes les entreprises déficitaires, y compris de la recherche; **incompatible** avec la nuance du CEO. **Alternative C :** accepter l'admission sur un upside théorique sans finance prouvée; non autorisé.

**Bandes encore UNKNOWN :** plafond par émetteur **inférieur à High-CAGR** (référence R1 proposée 12 % normal / 15 % exceptionnel, sous P01), sous-budgets du risque, conditions de convexité/asymétrie et classement des cas exceptionnels. Stress 35–45 % = scénario, pas niveau de perte garanti. Pas de vente sur drawdown seul.

**À décider :** forme et preuve de l'exception; plafond effectivement inférieur à celui choisi pour High-CAGR; traitement de l'overlap indirect. **Tests :** société très prometteuse avec runway insuffisant; rentabilité élevée mais valorisation excessive; scénario de dilution; société en déficit avec financement assuré mais catalyseurs incertains; deux véhicules du même émetteur.

## P07 — Intelligent Dividend Harvester : qualité des distributions sans prudence excessive

**Source :** Q08C/Q23C/Q24A/Q25C avec nuance « pas trop conservateur »/Q35C.

**Proposition A :** analyser dividende courant, croissance durable, couverture économique après besoins de réinvestissement, bilan, dette/refinancement, taux de distribution comparable au modèle, durée/historique de maintien, risque de coupure, inflation et valeur du capital. Distinguer sociétés ordinaires (dividendes issus d'économie récurrente), FPI/REIT (FFO/AFFO *définitions réconciliées* et dépenses nécessaires) et ETF (source de distribution, couverture, retour de capital, coûts, look-through). **Aucun minimum universel de 3 ou 5 ans**; une histoire courte doit néanmoins diminuer la confiance sans sanction automatique de qualité. Éviter les fausses « actions à rendement élevé » financées par dette ou liquidation.

**Équilibre choisi :** le mandat détermine cash immédiatement distribué vs dividendes réinvestis; ne pas imposer un revenu actuel s'il s'agit d'accumulation. Risque de baisse 15–25 % = stress de conception, pas stop-loss. Diversification par émetteur, secteur et moteurs de paiement **sans diluer automatiquement toutes les bonnes convictions**.

**Alternative B :** filtre uniforme de rendement en pourcentage et nombre fixe d'années pour toute classe d'actifs; rejeté comme inadéquat aux FPI/ETF et à la préférence du CEO. Les obligations et covered-call/derivés ne deviennent pas éligibles par le mot « revenu ».

**À décider :** preuves minimales de couverture par véhicule, seuils de concentration/risque et stratégie de revenu net par compte, comparateurs P09, critères de détérioration réelle des distributions et nouvelles contributions vs vente exceptionnelle. **Tests :** distribution d'ETF composée de retour de capital; FPI aux dépenses de maintien sous-estimées; société qui hausse le dividende tout en diluant; retenues FX/taxes UNKNOWN; réduction de distribution sans vente mécanique.

## P08 — Modern Adaptive Browne : fonctions obligatoires, liquidité potentiellement nulle

**Source :** Q09A/Q26B/Q27B/Q28A avec nuance C/Q29C/Q36A. **Mode R1 nouveau** : pas de permission d'emprunter l'allocation 25/25/25/25 ni la réserve V2.

**Proposition A :** analyser séparément les **quatre fonctions** : participation à la croissance; résistance à la déflation et/ou chocs de duration; protection face à inflation/choc monétaire; liquidité/courte duration. Les **trois premières fonctions seraient représentées par des positions positives** uniquement quand une règle R1 le permet et que la plateforme propose des instruments qualifiés; la quatrième fonction (réserve structurelle) **pourrait atteindre 0 %**, sous règles spéciales approuvées. Ne pas prétendre qu'un véhicule couvre une fonction simplement parce que son nom est « or » ou « obligation »; vérifier durée, risque souverain, devise, prix et corrélations en mauvais régimes. Le modèle ne prédit pas la prochaine récession.

**Alternative B :** poids fixes 25 % par fonction; non choisi. **Alternative C :** absence de seuils de fonction et poids nuls pour n'importe quelle fonction; ne reflète pas Q36A. La preuve de résistance simultanée actions/obligations est cruciale. Stress 10–20 % visé, sans garantie.

**UNKNOWN :** planchers/plafonds des trois fonctions positives; plafonds par instrument, définition exacte et support du compartiment liquide nul, seuil de révision/adaptation, benchmark multi-régime, rééquilibrages rares et après coûts. **Si une fonction positive est impossible via la plateforme**, signaler le mode NON_IMPLEMENTABLE/CONDITIONAL pour ce mandat plutôt que créer un ETF ou une exposition inexistante.

**À décider :** A et bandes par fonction, instruments admissibles, cas où le compartiment liquide peut être 0, conditions de revue et rebalancement. **Tests :** actions et obligations baissent ensemble; couverture or diverge; aucun véhicule obligataire accessible; somme des expositions incomplète; niveau de cash 0 avec accès encore adéquat; frais de rééquilibrage disproportionnés.

## P09 — Benchmarks autorisés par mode, VFV restant principal en High-CAGR

**Source :** Q03A/Q04A/Q37C. **Contrainte historique :** VFV est le benchmark High-CAGR principal et son repli normal. Le comparateur V2 company vs VFV est limité à une route d'entreprise PR5E réellement admise ORDINARY_COMPOUNDER USD US_GAAP, FX constant, et n'autorise ni recommandation ni assimilation globale.

**Proposition A :** chaque stratégie dispose d'un **catalogue versionné de comparateurs autorisés** et d'une règle de sélection fondée sur objectif, profil de risque, devise et coûts; IR explique pourquoi le comparateur choisi mesure réellement le coût d'opportunité. **High-CAGR : VFV principal, obligatoire** dans sa portée V2. Pour Balanced/Family-Office, envisager des références diversifiées compatibles avec les classes d'actifs approuvées; Rational-Aggressive, référence de rendement net et risque réellement comparable; Dividend Harvester, référence de revenu soutenable **ET** rendement total; Adaptive Browne, référence multi-régime/retour réel. Aucun ticker ni rendement prospectif additionnel n'est « approuvé » ici.

**Alternative B :** choisir arbitrairement une référence ad hoc à chaque analyse, sans catalogue; augmente le risque de benchmark-shopping. **Alternative C :** appliquer VFV et son hurdle à tous les six modes; contraire aux décisions de conception et à l'autorité de V2.

**Qualification :** instrument exact, date/prix, distributions et réinvestissement, horizon, devise d'analyse, frais, enveloppe fiscale, risque/volatilité et comparaison de scénarios identiques. Si les comparables forward sont UNAVAILABLE, nommer l'indisponibilité plutôt que mettre une rentabilité moyenne historique dans la colonne ER. Le rapport peut contenir une référence de contexte distincte d'un benchmark prospectif calculé.

**À décider :** accepter catalogue par mode A, puis choisir symboles, méthode, performances comparables et droits de source au sein d'un contrat vérifiable. **Tests :** benchmark historique vs ER futur, horizon incohérent, hypothèse FX arbitraire, frais de fonds absents, double comptage distributions, changement de benchmark opportuniste entre deux rapports.

## P10 — Accès via plateforme et alternative canadienne : action, ADR/CDR, FNB ou substitut distinct

**Source :** Q29C avec priorité plateforme et Q38A avec nuance CEO. **Ne pas assimiler CDR à options, CFD, futures ou leverage** : ces familles nécessitent une permission de risque distincte; un certificat représentatif d'actions est un instrument à examiner selon ses propres caractéristiques. Les produits couverts en CAD peuvent réduire certaines fluctuations FX mais ne sont pas une garantie d'équivalence à l'action originale.

**Proposition A :** garder la recherche d'émetteurs internationale; **après** la recherche, construire un registre d'instruments disponibles et admissibles : (i) action primaire; (ii) autre cotation/ADR; (iii) certificat de dépôt canadien ou autre enveloppe couverte si le cas existe réellement; (iv) ETF/FNB avec exposition documentée; (v) substitut domestique économique **en tant que nouvelle entreprise**, non la même action. Ne proposer une allocation que si le compte, courtier et plateforme indiqués permettent réellement d'y accéder et si le mode autorise sa structure. Si plateforme indisponible/UNKNOWN, décision d'achat reste CONDITIONNELLE ou INACCESSIBLE; ne pas inventer un ticker négociable.

**Vérifier par instrument :** émetteur économique; titre/juridiction, ratio de dépôt et corporate actions; exposition et risque de tracking, couverture FX réellement documentée, frais explicites/implicites, liquidité et spread; prix/quantité fractionnable, devise de règlement, taxes/retenues et droits; restrictions du compte. Un « substitut local semblable » exige sa **propre** analyse Quality/Durability/Expected Return/Confidence et une comparaison explicite des différences de risque; un ETF ne donne pas exposition directe sans composition qualifiée.

**Alternative B :** limiter toute découverte aux seuls titres actuellement disponibles; contraire à la découverte internationale ouverte. **Alternative C :** recommander une action non négociable dans le compte parce que sa thèse est bonne; interdit pour une contribution à cette plateforme.

**À décider :** A et limites permises sur les représentations d'actions, ETF, couverture et produits plus complexes par mode; responsabilité de vérification des capacités du courtier. **Tests :** action étrangère absente mais CDR observé; CDR non réellement négociable; coût de couverture caché; ETF ne réplique pas l'émetteur; ADR compté en double; substitut local inadéquat; achat fractionnaire UNKNOWN.

## P11 — PI : source visible, attestation de périmètre et compte vérifié

**Source :** Q10A et échec relatif du test #3. **Règle existante à ne pas contourner :** une vue Blossom publique n'est pas une liste de positions privées; une capture ne prouve pas cash 0 ni 100 % du compte. L'Observation and Room R1 exige visibilité par champ et un dénominateur complet pour calculer des poids monétaires.

**Proposition A :** trois niveaux d'usage **méthodologique** — VISIBLE_SOURCE (lignes réellement affichées, source/date de capture et limites); CEO_ATTESTED_SCOPE (le CEO atteste le périmètre qu'il souhaite analyser, sans authentification du courtier); ACCOUNT_VERIFIED (une source privée réellement consultée et vérifiée suffisante **pour les champs revendiqués**). Les noms sont proposés : ne pas prendre « VERIFIED » au sens certifié par le courtier s'il ne l'est pas. Une vue visible permet descriptif et éventuellement comparaison de **pourcentages affichés** si cohérents; elle n'autorise ni valeurs cachées, ni encaisse, ni pourcentage de patrimoine personnel. L'attestation peut permettre un raisonnement conditionnel par compte, pas fabriquer des poids ou une fraîcheur. Les calculs monétaires demandent scope/denominator/cash/devise/date et identité de sécurité réellement étayés.

**Alternative B :** exiger toujours le relevé courtier pour toute observation qualitative; prudent mais inutilisablement rigide pour une analyse exploratoire. **Alternative C :** promouvoir des poids Blossom publics en holdings CEO; non autorisé.

**Statuts séparés :** SOURCE_VISIBLE, SCOPE_ATTESTED, FIELD_VERIFIED_VISIBLE, ACCOUNT_SCOPE_VERIFIED, ROOM_CONDITIONAL, ROOM_UNAVAILABLE. Leur usage exact doit être revu pour compatibilité avec le contrat M3 existant, sans renommer ses statuts ni désactiver ses gardes avant revue. Les observations restent privées; aucun stockage en clair dans GitHub. Work/Cloud Browser seulement via session autorisée PI, jamais accès supposé ou CC naviguant directement Blossom.

**À décider :** A et seuils de preuve calcul par calcul (descriptif, comparaison de l'interface, concentration économique, projection d'après-contribution). **Tests :** liste publique exhaustive mais non privée; attestation CEO sans cash; somme des pourcentages d'écran arrondis >100; ETF look-through partiel; capture datée mais date de mise à jour inconnue; Work privé authentifié; aucun niveau ne forge une source.

## P12 — Risque, scénarios de baisse, contributions et cycle des positions

**Source :** Q13B/C→Q32A, Q14A, Q17A/C, Q22A, Q24A, Q28A/C, Q33A. **Interprétation contraignante du CEO :** les fourchettes sont des **objectifs/stress tests indicatifs**, pas pertes maximales garanties, stop-loss, distribution de probabilité prouvée ou ordre automatique de vente.

**Proposition A :** distinguer (i) stress du mandat — pertes possibles selon scénarios économiques, (ii) risque fondamental de perte permanente — dette, cash, dilution, moat, (iii) concentration directe/indirecte et facteurs communs, (iv) coût d'une contribution ou d'un rééquilibrage, (v) confiance séparée. Ordre d'évaluation : thèse réelle et données → portefeuille existant et obligations explicites → nouveaux fonds d'abord → conformité aux contraintes approuvées → revue humaine seulement en cas de détérioration ou dérive matérielle; **aucune vente sur baisse de prix seule**.

**Scénarios de conception sélectionnés, non contraintes exécutables :**
- High-CAGR et Rational-Aggressive : environ **35–45 %** sous chocs, mais objectif de limiter pertes permanentes et concentration.
- Balanced : **10–20 %**, plus tests de choc simultané des actifs.
- Family-Office : orientation prudente **10–20 %**, adaptable au mandat d'épargne familiale investissable et au compte.
- Dividend Harvester : **15–25 %**, sans devenir excessivement défensif au détriment du revenu/total return.
- Adaptive Browne : **10–20 %** et inflation/déflation/taux/chocs conjoints.

**Alternative B :** interpréter les bandes comme stop-loss mécaniques; interdit dans cette conception. **Alternative C :** calculer un « risque garanti » avec covariance ou données insuffisantes; non fondé. La réserve temporaire reste exceptionnelle dans la doctrine V2; seul Adaptive Browne R1 peut **proposer** un compartiment stratégique de liquidité distinct sous approbation future. Aucun autre mode ne reçoit de réserve permanente par implication.

**À décider :** traduction des stress en véritables **budgets de risque/limites d'exposition par mode**, seuils de dérive et revue humaine, politique de contribution vs rééquilibrage, et test de coûts. **Tests :** marché -40 % sans thèse rompue; crédit détérioré malgré cours stable; titres corrélés et ETF; fiscalité/FX incertains; réserve créée par panique macro (doit échouer); appréciation au-dessus du plafond sans vente forcée; compte à faible contribution et coûts disproportionnés.

---

## 2. Vue croisée des six modes — aucune règle chiffrée nouvelle n'est en vigueur

| Mode | Objectif principal | Stress de conception, non borne maximale | Politique financière qui reste à approuver |
|---|---|---|---|
| High-CAGR | croissance de qualité asymétrique | 35–45 % V2; concentr. initiale R1 12/15 PROPOSED | P01; élargissements de P02/P03; parcours instruments P10 |
| Balanced | croissance et défense multi-actifs | 10–20 % | P04/P09/P12, instruments et bandes |
| Family-Office | épargne investissable familiale, un compte à la fois | 10–20 % prudent, adapté | P05/P09/P12, pas de budget familial obligatoire |
| Rational-Aggressive | net compound return et asymétrie de qualité | 35–45 % | P06/P09/P12, exception de déficit |
| Dividend Harvester | revenu croissant durable et total return | 15–25 % | P07/P09/P12, flux distribuables réels |
| Adaptive Browne | résilience quatre fonctions | 10–20 % + chocs inflation/duration | P08/P09/P12, cash structurel possible 0 |

**Dépendances critiques :** P02 (qualité) → P03 (cas ER indisponible) → P09 (benchmarks comparables) et P10 (instrument de négociation); P11 (données portefeuille) → P01/P04/P05/P06/P07/P08 (Room) → P12 (cycle/contribution). Les six contrats peuvent partager le même moteur de faits et de transferts, jamais la même décision de risque par défaut.

## 3. Matrice d'arbitrage CEO — en attente

| ID | Décision précise à approuver ou renvoyer en révision | État |
|---|---|---|
| P01 | Plafonds 12/15 sur émetteur économique après contribution, look-through qualifié, exceptions et maintien des positions anciennes | PENDING_FINANCIAL_POLICY |
| P02 | Admission économique adaptée aux modèles et séparation recherche/investissabilité, vérification source et contre-thèse | PENDING_FINANCIAL_POLICY |
| P03 | Limites du recours qualitatif lorsque l'ER comparatif est réellement impossible, y compris éventuelle allocation conditionnelle | PENDING_FINANCIAL_POLICY |
| P04 | Instruments et bandes multi-actifs Balanced, protections et coûts | PENDING_FINANCIAL_POLICY |
| P05 | Épargne Family-Office investissable par compte, sans budget familial; contraintes de résilience | PENDING_FINANCIAL_POLICY |
| P06 | Qualité minimale, exception déficitaire et cap plus bas Rational-Aggressive | PENDING_FINANCIAL_POLICY |
| P07 | Couverture des dividendes, historique sans minimum universel, concentration et revenu net | PENDING_FINANCIAL_POLICY |
| P08 | Trois fonctions Browne positives, cash éventuel 0, instruments et rebalancement | PENDING_FINANCIAL_POLICY |
| P09 | Catalogues benchmark par mode, VFV High-CAGR maintenu, cohérence forward et coûts | PENDING_FINANCIAL_POLICY |
| P10 | Vérification plateforme et véhicules représentatifs (CDR/ADR/ETF) ou substitut distinct | PENDING_FINANCIAL_POLICY |
| P11 | Trois classes de preuve portefeuille et limites strictes des calculs | PENDING_METHOD_AND_PRIVACY_APPROVAL |
| P12 | Stress indicatif vs limite approuvée, contributions et déclencheurs de revue sans vente automatique | PENDING_FINANCIAL_POLICY |

Le CEO peut approuver, modifier ou différer chaque clause **uniquement après** son examen explicite. Les propositions PM A ne constituent pas une demande d'approbation globale silencieuse. Les champs indiqués UNKNOWN (bandes/benchmarks/instruments/critères quantitatifs) doivent encore être résolus dans une révision; aucune implémentation opérationnelle ne les remplace par des valeurs choisies par l'agent.

## 4. Vérification, revue indépendante et suite

### Vérification documentaire déjà possible

- Cohérence avec les 38 choix, leurs nuances Q13/Q16/Q17/Q18/Q20/Q25/Q28/Q29/Q30/Q38 et la doctrine High-CAGR VFV.
- Préservation des contrats V2 : research participation non investissabilité, ER USD US_GAAP strictement borné, comparateur company/VFV constant-FX diagnostic seulement, source-dated portfolio fields, coûts UNKNOWN, comptes/plateformes séparés.
- Absence de nouvelles dépenses de source, transactions ou exposition de données personnelles dans le document.
- Présence de 12 champs d'arbitrage; aucun test authentique des rendements/compte/portefeuille dans cette PR.

### Revue indépendante indispensable avant politique exécutable

Confier une **revue proportionnée** à Architecture & Audit et, pour les seuils et modèles financiers, Data & Evidence / Investment Research (sans feindre que ces rôles ont été consultés). Questions : conditions initiales et unités stables; contradictions Constitution/V2; préservation du patrimoine de méthodes; capacité à vérifier les preuves authentiques; droits des sources et CDR; risque d'optimisation non justifiée; coûts/fiscalité et confidentialité; qualité des tests; nécessité éventuelle d'un amendement CEO_PROTECTED. Un retour de revue critique ne constitue pas l'approbation du CEO.

### Parcours après la décision CEO

1. Résoudre les seules ambiguïtés restantes via arbitrages ciblés, sans reposer les 38 questions déjà répondues.
2. Versionner séparément six contrats de politique R1 (plus clauses communes P02/P03/P09–P12) **uniquement après approbation financière explicite**, en conservant les identités de V2. Réutiliser les modules déterministes pour vérifications exactes et provenance; éviter six moteurs dupliqués.
3. Modifier ensuite CC/IR/PI de façon intégrée, avec revue du mode réellement chargé, routage humain un geste à la fois, traçabilité S/F/K/V/P et confidentialité. Aucun transfert automatique ne peut être présumé.
4. Garder la matrice des 36 décisions en états fondés sur preuves; procéder à **une** évaluation d'acceptation globale après assemblage, incluant les six modes et des cas contradictoires. Ni un PR documentaire ni un test synthétique ne satisfait ce gate.

**État final de ce dossier : DRAFT_FOR_CEO_AND_INDEPENDENT_REVIEW. Tests code, modèles financiers authentiques, CI et acceptation intégrée : NOT_RUN.**

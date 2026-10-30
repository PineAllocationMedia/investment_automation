# Gabarit universel de démarrage CC — PAM Financial Systems R1

**Version:** `CC-START-R1-v1.0` (2026-10-30). **Statut:** `CEO_DESIGNATED_STANDARD_TEST_ENTRYPOINT / GitHub PR CANDIDATE / CHATGPT_SETTINGS_UNCHANGED / AUTHENTIC_ACCEPTANCE_NOT_RUN`. **Primary owner:** Program Manager / Product & UX integration. **Work Order:** `WO-FS-R1-UNIVERSAL-CC-ANALYSIS-START-PROMPT`.

## Objet et périmètre

Le CEO a demandé un **seul gabarit universel et reproductible** pour démarrer toute demande d'analyse complète dans Financial Systems Command Center (CC), avec espaces simples pour la situation, les objectifs, le montant, le mode et les autres éléments nécessaires. Ce texte est l'**entrée standard des futurs essais** et peut servir aux demandes financières normales; il n'établit pas que les Projects s'invoquent automatiquement, que Work/Blossom fonctionne, que les politiques de six modes sont toutes approuvées, ou que R1 est accepté.

Les champs facultatifs restent `INCONNU` ou `S/O`, jamais automatiquement zéro. Le CEO n'opère ni terminal, ni JSON, ni code. Les exigences internes détaillées restent dans les instructions canoniques CC/IR/PI, le contrat intégré et le prompt PI-1. Pour améliorer la fiabilité, l'utilisateur peut laisser certains champs non remplis; CC peut poser une seule question indispensable puis avancer conditionnellement.

**Source des règles pertinentes:** `docs/ai_native/project_instructions/{FINANCIAL_SYSTEMS_COMMAND_CENTER,INVESTMENT_RESEARCH,PORTFOLIO_INTELLIGENCE}.md`; `docs/ai_native/integrated_build/{DELIVERY_PLAN,OPERATING_CONTRACT}.md`; `docs/ai_native/integrated_build/integration/FIRST_CHATGPT_TRACE_CC_PI_ROUTING_REPAIR_R1.md`; `docs/ai_native/integrated_build/portfolio/PROMPT_PI_1_BLOSSOM_PORTFOLIO_WORK_R1.md`. Les règles protégées et approbations CEO prévalent.

## Texte unique à copier dans une nouvelle conversation du Project CC

```text
PAM FINANCIAL SYSTEMS — DEMANDE UNIVERSELLE D'ANALYSE COMPLÈTE
Gabarit CC-START-R1-v1.0

Remplis les champs entre crochets. Écris « inconnu » ou « sans objet » lorsqu'il le faut; ne fournis jamais de mot de passe ni de numéro de compte.

1. SITUATION ET OBJECTIFS
- Ma situation, en quelques phrases : [ ]
- Mes objectifs financiers et la décision à éclairer : [ ]
- Ma question prioritaire à PAM : [ ]

2. CONTRIBUTION À ANALYSER
- Montant et devise : [ex. 350 CAD / à déterminer / aucune]
- Contribution : [réelle envisagée / hypothétique]
- Échéance ou besoin de liquidité : [ ]

3. MODE D'INVESTISSEMENT
- Mode choisi : [High-CAGR / Balanced / Family-Office / Rational-Aggressive / Intelligent Dividend Harvester / Modern Adaptive Browne / à clarifier]
- Horizon d'investissement : [ ]
- Risques et pertes permanentes que je veux limiter : [ ]
Si les règles propres à mon mode ne sont pas approuvées pour R1, signale-le et conserve une analyse exploratoire; ne crée aucune nouvelle politique.

4. COMPTES, COÛTS ET CONTRAINTES
- Pays, type(s) de compte et courtier(s), sans données sensibles : [ ]
- Devise(s), commissions, frais FX, restrictions fiscales ou d'achat fractionnaire connus : [ ]
- Univers, exclusions, titres à examiner ou préférence de découverte ouverte : [ ]
- Référence/benchmark souhaité, si pertinent : [ ]

5. PORTEFEUILLE ACTUEL ET BLOSSOM
- Faut-il tenir compte de mes positions? [oui / non / à déterminer avec CC]
- Périmètre des comptes concernés : [ ]
- Source et date de l'observation existante : [Blossom / export / capture datée / aucune]
- URL du profil Blossom sélectionné, facultatif : [ ]
- J'autorise, pour cette demande uniquement, une consultation **en lecture seule** du Portfolio que je sélectionnerai dans une session Work que je lance moi-même, si disponible : [oui / non / à confirmer]
- Capture d'écran ou export daté possible en solution de repli : [oui / non / à confirmer]
Un profil public n'établit jamais la composition de mes avoirs privés.

6. CONTEXTE SUPPLÉMENTAIRE
- Analyse antérieure ou informations déjà disponibles à réutiliser : [ ]
- Date limite des informations : [actuelles / date historique]
- Autres critères, questions et préférences : [ ]
- Type de demande : [analyse normale / test fonctionnel R1]

INSTRUCTIONS PERMANENTES À COMMAND CENTER

**Lance réellement le parcours complet adapté à mon mandat.** Interprète mes réponses sans inventer les champs manquants; pose au plus une question strictement indispensable, sinon avance conditionnellement. Vérifie les méthodes et versions réellement accessibles, sans prétendre à un accès non testé.

**Routage.** Si une recherche est nécessaire, mandate Investment Research (IR) pour une découverte ou comparaison justifiée, la recherche fondamentale, la valorisation et les contre-thèses. Si la question dépend de mon portefeuille, engage Portfolio Intelligence (PI) dès le départ pour acquérir une observation autorisée, en parallèle d'IR si utile; ne reporte pas PI jusqu'à la fin d'IR. Pour la synthèse finale combinée, fournis à PI le dossier original complet d'IR, inchangé.

**Blossom.** PI doit proposer le parcours PI-1 de lecture seule via Work si réellement disponible et autorisé; je lancerai moi-même Work. Sinon, demander une seule capture/export daté. Distinguer PUBLIC_REFERENCE, OWN_PRIVATE_AUTHORIZED et INACCESSIBLE_OR_AMBIGUOUS; ne jamais déduire mes positions ou concentrations d'un aperçu public incomplet. Si les données manquent, obtenir de PI un statut clair UNAVAILABLE plutôt que l'omettre.

**Recherche et décision.** Conserver les cinq piliers QUALITY, DURABILITY, EXPECTED RETURN, CONFIDENCE et PORTFOLIO ROOM. Utiliser des sources datées, identifiées et permises, différencier faits/hypothèses, signaler les calculs et méthodes réellement vérifiés, les divergences et les risques. Ne pas inventer un alpha, des frais ou une allocation optimale. Ne pas suggérer de panier chiffré avant le retour approprié d'IR/PI.

**Mon expérience.** Explique brièvement le parcours et donne la première action concrète. Prépare toi-même les messages complets à copier vers le Project spécialisé ou Work, avec le destinataire et le retour attendu : je ne manipule ni JSON, ni terminal, ni code. Aucun transfert automatique entre Projects ne doit être supposé.

**Rapport final.** Lorsque les réponses disponibles sont revenues, présente une synthèse décisionnelle de moins de dix minutes de lecture : conclusion ou statut conditionnel, comparaisons, cinq piliers pertinents, sources, risques, coûts connus, limites et prochaine action. Privilégie les **pourcentages de NOUVELLES contributions** si l'information et une politique approuvée le permettent. Aucun achat, vente, suivi récurrent ou archivage privé automatique.

**Si TEST R1 :** ajoute une mini-trace des étapes réellement effectuées (IR sollicité, PI sollicité, Work tenté, méthodes chargées, transferts humains constatés et blocages). Ne déclare jamais un test réussi sur la seule base d'instructions ou de données supposées.
```

## Versions et apprentissage à partir des essais

- `v1.0` devient le **gabarit de comparaison** tant qu'une révision CEO/PM n'a pas été acceptée; changer les valeurs des champs selon le cas ne modifie pas la version.
- Pour chaque essai user-initiated, comparer les résultats et les traces réellement accessibles; noter séparément les défauts d'instructions, de routage, d'accès Work, de sources, d'analyse, de coûts ou de restitution. Ne pas déposer les sorties intégrales ni les portefeuilles privés dans GitHub.
- Les corrections futures peuvent produire `CC-START-R1-v1.1` ou une nouvelle version clairement étiquetée, avec motifs et résultats observés. **Cela ne réentraîne pas automatiquement le modèle ChatGPT** et n'est pas une acceptation du système.
- Aucun changement aux paramètres des Projects, aux décisions protégées, à la stratégie, au code runtime ou à une autorisation de transaction n'est fait par ce fichier. Fusion GitHub sous décision CEO seulement.

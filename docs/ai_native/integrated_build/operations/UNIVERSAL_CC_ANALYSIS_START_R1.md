# Gabarit universel de démarrage CC — PAM Financial Systems R1

**Version affichée du gabarit CEO:** `CC-START-R1-v1.0`; **révision datée dans GitHub:** 2026-10-30, après la première fusion #397. **Statut:** `CEO_SELECTED_REFERENCE / WORKFLOW_RECONCILIATION_PR_ONLY / CHATGPT_SETTINGS_UNCHANGED / AUTHENTIC_ACCEPTANCE_NOT_RUN`. **Primary owner:** Program Manager / Product & UX integration. **Work Order:** `WO-FS-R1-UNIVERSAL-CC-ANALYSIS-START-PROMPT`.

## Objet et périmètre

Le CEO a demandé un **seul gabarit universel et reproductible** pour démarrer toute demande d'analyse complète dans Financial Systems Command Center (CC), avec espaces simples pour la situation, les objectifs, le montant, le mode et les autres éléments nécessaires. Ce texte est l'**entrée standard des futurs essais** et peut servir aux demandes financières normales; il n'établit pas que les Projects s'invoquent automatiquement, que Work/Blossom fonctionne, que les politiques de six modes sont toutes approuvées, ou que R1 est accepté.

Les champs facultatifs restent `INCONNU` ou `S/O`, jamais automatiquement zéro. Le texte ci-dessous reprend exactement la version finale du gabarit sélectionnée par le CEO le 30 octobre 2026, avec les trois champs de la section 4 volontairement laissés vides. Le CEO n'opère ni terminal, ni JSON, ni code. Les exigences internes détaillées restent dans les instructions canoniques CC/IR/PI, le contrat intégré et le prompt PI-1. Pour améliorer la fiabilité, l'utilisateur peut laisser certains champs non remplis; CC peut poser une seule question indispensable puis avancer conditionnellement.

**Source des règles pertinentes:** `docs/ai_native/project_instructions/{FINANCIAL_SYSTEMS_COMMAND_CENTER,INVESTMENT_RESEARCH,PORTFOLIO_INTELLIGENCE}.md`; `docs/ai_native/integrated_build/{DELIVERY_PLAN,OPERATING_CONTRACT}.md`; `docs/ai_native/integrated_build/integration/FIRST_CHATGPT_TRACE_CC_PI_ROUTING_REPAIR_R1.md`; `docs/ai_native/integrated_build/portfolio/PROMPT_PI_1_BLOSSOM_PORTFOLIO_WORK_R1.md`. Les règles protégées et approbations CEO prévalent.

## Texte unique à copier dans une nouvelle conversation du Project CC

```text
PAM Financial Systems — DEMANDE UNIVERSELLE D'ANALYSE COMPLÈTE

**Gabarit : CC-START-R1-v1.0**

Remplis les champs entre crochets. Écris « inconnu » ou « sans objet » lorsqu'il le faut; ne fournis jamais de mot de passe ni de numéro de compte.

## 1. SITUATION ET OBJECTIFS

- **Ma situation, en quelques phrases :** [ ]
- **Mes objectifs financiers et la décision à éclairer :** [ ]

## 2. CONTRIBUTION À ANALYSER

- **Montant et devise :** [ex. 350 CAD / à déterminer / aucune]

## 3. MODE D'INVESTISSEMENT

- **Mode choisi :** [High-CAGR / Balanced / Family-Office / Rational-Aggressive / Intelligent Dividend Harvester / Modern Adaptive Browne / à clarifier]
- **Horizon d'investissement :** [ ]
- **Risques, pertes permanentes que je veux limiter, tolérances à la volatilité que je souhaite spécifier:** [ ]

Si les règles propres à mon mode ne sont pas approuvées pour R1, signale-le et conserve une analyse exploratoire; ne crée aucune nouvelle politique.

## 4. COMPTES, COÛTS ET CONTRAINTES

- **Pays, type(s) de compte et courtier(s), sans données sensibles :** [ ]
- **Devise(s), commissions, frais FX, restrictions fiscales ou d'achat fractionnaire connus :** [ ]
- **Univers, exclusions, titres à examiner ou préférence de découverte ouverte :** []

## 5. PORTEFEUILLE ACTUEL ET BLOSSOM

- **Faut-il tenir compte de mes positions?** [oui / non / à déterminer avec CC]
- **Source et date de l'observation existante :** [Blossom / export / capture datée / aucune]
- **URL du profil Blossom sélectionné (si rien est indiqué, se référer aux captures d’écran jointes) :** [ ]
- **J'autorise une consultation en lecture seule du Portfolio que je sélectionnerai dans une session Work que je lance moi-même, si disponible :** [oui / non / à confirmer]

## 6. CONTEXTE SUPPLÉMENTAIRE

- **Utilisation des rapports d’analyses passés et des rapports de capture du portefeuille Blossom rattachés à l’URL antérieurs fourni (si disponible) afin d’améliorer la qualité et la personnalisation de l’analyse effectuée:** [oui ou non ]
- **Autorisation de sauvegarder le rapport d’analyse, la capture des données compte rattaché à l’URL fourni ou du portefeuille démontré dans les captures d’écran lors de cette analyse, la capture des données financières actuelles du marchés et tout autre information utile à sauvegarder à des fins d’audit et d’analyse futur du modèle et de son fonctionnement à des fins d’amélioration :** [oui ou non ]
- **Autres critères, questions et préférences :** [ ]
- **Type de demande :** [analyse normale / test fonctionnel R1]



---



# INSTRUCTIONS PERMANENTES À COMMAND CENTER

**Lance réellement le parcours complet adapté à mon mandat.** Interprète mes réponses sans inventer les champs manquants; pose au plus une question strictement indispensable, sinon avance conditionnellement. Vérifie les méthodes et versions réellement accessibles, sans prétendre à un accès non testé.

**Routage.** Si une recherche est nécessaire, mandate Investment Research (IR) pour une découverte ou comparaison justifiée, la recherche fondamentale, la valorisation et les contre-thèses. Si la question dépend de mon portefeuille, engage Portfolio Intelligence (PI) dès le départ pour acquérir une observation autorisée, en parallèle d'IR si utile; ne reporte pas PI jusqu'à la fin d'IR. Pour la synthèse finale combinée, fournis à PI le dossier original complet d'IR, inchangé.

**Blossom.** PI doit proposer le parcours PI-1 de lecture seule via Work si réellement disponible et autorisé; je lancerai moi-même Work. Sinon, demander une seule capture/export daté. Distinguer PUBLIC_REFERENCE, OWN_PRIVATE_AUTHORIZED et INACCESSIBLE_OR_AMBIGUOUS; ne jamais déduire mes positions ou concentrations d'un aperçu public incomplet. Si les données manquent, obtenir de PI un statut clair UNAVAILABLE plutôt que de l'omettre.

**Recherche et décision.** Conserver les cinq piliers QUALITY, DURABILITY, EXPECTED RETURN, CONFIDENCE et PORTFOLIO ROOM. Utiliser des sources datées, identifiées et permises, différencier faits/hypothèses, signaler les calculs et méthodes réellement vérifiés, les divergences et les risques. Ne pas inventer un alpha, des frais ou une allocation optimale. Ne pas suggérer de panier chiffré avant le retour approprié d'IR/PI.

**Mon expérience.** Explique brièvement le parcours et donne la première action concrète. Prépare toi-même les messages complets à copier vers le Project spécialisé ou Work, avec le destinataire et le retour attendu : je ne manipule ni JSON, ni terminal, ni code. Aucun transfert automatique entre Projects ne doit être supposé.

**Rapport final.** Lorsque les réponses disponibles sont revenues, présente une synthèse décisionnelle de moins de dix minutes de lecture : conclusion ou statut conditionnel, comparaisons, cinq piliers pertinents, sources, risques, coûts connus, limites et prochaine action. Privilégie les **pourcentages de NOUVELLES contributions** si l'information et une politique approuvée le permettent. Aucun achat, vente, suivi récurrent ou archivage privé automatique.

**Si TEST R1 :** ajoute une mini-trace des étapes réellement effectuées (IR sollicité, PI sollicité, Work tenté, méthodes chargées, transferts humains constatés et blocages). Ne déclare jamais un test réussi sur la seule base d'instructions ou de données supposées.
```


## Décisions sur l'utilisation d'antécédents et l'archivage privé

Le CEO a retenu la version `CC-START-R1-v1.0` révisée dans la conversation du Project (30 octobre 2026). Le prompt conserve ses deux nouveaux choix **oui/non** : (1) réutiliser des analyses/captures antérieures lorsque celles-ci sont effectivement disponibles, datées, comparables et dans les droits autorisés; (2) autoriser la préparation d'une **sauvegarde privée future** des résultats et observations.

**Le « oui » à la sauvegarde n'est pas une permission générale de déposer les pièces dans GitHub ni une preuve de stockage réalisé.** Il ne remplace pas la sélection et la validation préalables d'un emplacement privé approuvé par le CEO, des permissions, de la confidentialité, des droits de source, de la conservation et de la restauration. Tant que cette destination manque, CC peut préparer une proposition ou un paquet à sauvegarder par un humain dans un contexte privé, et doit indiquer `ARCHIVE_NOT_SAVED`. Aucun stockage silencieux ou automatique. Les rapports antérieurs sont réutilisés seulement s'ils sont **réellement accessibles**, avec identité et horodatage compatibles; aucun suivi récurrent n'est instauré.

**Gabarit non personnalisé :** les trois champs de la section 4 sont vides dans la version choisie par le CEO. Aucun compte, courtier, restriction ou préférence de placement n'est présumé par ce modèle; les informations propres à chaque demande restent privées et ne sont pas archivées dans GitHub.

## Point de référence UX pour le développement R1 (CEO test #2)

**Le formulaire est le produit d'entrée, non une démonstration de fonctionnement.** Pour chaque demande, le scénario visible doit rester une **action CEO à la fois**. Lorsqu'un portefeuille Blossom est matériel et que la consultation autorisée est proposée, la première action est le **PI-1 dans une session ChatGPT Work/Cloud Browser déclenchée par le CEO**, de préférence dans le Project PI si Work y est réellement disponible; le Project CC **ne doit pas** ouvrir Blossom dans son navigateur Web et aucune erreur de son navigateur ne prouve un échec du navigateur Work PI. L'ordre de l'interface est **CC → PI acquisition Work (ou capture datée) → CC → IR → CC → PI synthèse avec IR original inchangé → CC rapport**, en omettant les étapes sans valeur ajoutée. Les besoins IR peuvent être préparés en interne « en parallèle », **pas remis au CEO comme deux prompts à traiter simultanément**. Si PI ne peut capturer, ne pas inventer les positions; CC peut poursuivre IR avec PORTFOLIO_ROOM UNAVAILABLE et revenir à PI sur une demande de source ultérieure.

Le CEO a confirmé les instructions CC/PI du PR #396 installées; **les versions de paramètres plus récentes proposées pour ce flux séquentiel ne sont PAS installées par GitHub**. Le gabarit affiché garde littéralement `CC-START-R1-v1.0` conformément au texte choisi par le CEO; la présente petite révision après fusion est identifiée **par date et Git SHA**, et doit être distinguée de la version déjà fusionnée #397 lors des comparaisons. Une prochaine évolution de méthode/UX plus large devra recevoir une nouvelle version explicite.

**Développement gouverné par ce gabarit :** les demandes et tests utilisent les six champs du modèle comme contexte utilisateur normal; rien ne doit requérir JSON/CLI. Critères de contrôle : destination Work réelle, un seul prochain transfert, PI consulté si nécessaire, statut de source/identité, aucune déduction publique→privée, IR original préservé, rapport intégré et effort CEO mesuré. Seul un test en Projects/Work peut satisfaire les critères, pas un changement GitHub. Voir [le plan de livraison](../DELIVERY_PLAN.md) et [le scénario de deuxième essai](../integration/SECOND_CHATGPT_TRACE_SINGLE_ACTION_PI_WORK_R1.md).

## Versions et apprentissage à partir des essais

- `v1.0` devient le **gabarit de comparaison** tant qu'une révision CEO/PM n'a pas été acceptée; changer les valeurs des champs selon le cas ne modifie pas la version.
- Pour chaque essai user-initiated, comparer les résultats et les traces réellement accessibles; noter séparément les défauts d'instructions, de routage, d'accès Work, de sources, d'analyse, de coûts ou de restitution. Ne pas déposer les sorties intégrales ni les portefeuilles privés dans GitHub.
- Les corrections futures peuvent produire `CC-START-R1-v1.1` ou une nouvelle version clairement étiquetée, avec motifs et résultats observés. **Cela ne réentraîne pas automatiquement le modèle ChatGPT** et n'est pas une acceptation du système.
- Aucun changement aux paramètres des Projects, aux décisions protégées, à la stratégie, au code runtime ou à une autorisation de transaction n'est fait par ce fichier. Fusion GitHub sous décision CEO seulement.

# Gabarit universel de démarrage CC — PAM Financial Systems R1

**Version:** `CC-START-R1-v1.0` (2026-10-30). **Statut:** `CEO_DESIGNATED_STANDARD_TEST_ENTRYPOINT / GitHub PR CANDIDATE / CHATGPT_SETTINGS_UNCHANGED / AUTHENTIC_ACCEPTANCE_NOT_RUN`. **Primary owner:** Program Manager / Product & UX integration. **Work Order:** `WO-FS-R1-UNIVERSAL-CC-ANALYSIS-START-PROMPT`.

## Objet et périmètre

Le CEO a demandé un **seul gabarit universel et reproductible** pour démarrer toute demande d'analyse complète dans Financial Systems Command Center (CC), avec espaces simples pour la situation, les objectifs, le montant, le mode et les autres éléments nécessaires. Ce texte est l'**entrée standard des futurs essais** et peut servir aux demandes financières normales; il n'établit pas que les Projects s'invoquent automatiquement, que Work/Blossom fonctionne, que les politiques de six modes sont toutes approuvées, ou que R1 est accepté.

Les champs facultatifs restent `INCONNU` ou `S/O`, jamais automatiquement zéro. Le CEO n'opère ni terminal, ni JSON, ni code. Les exigences internes détaillées restent dans les instructions canoniques CC/IR/PI, le contrat intégré et le prompt PI-1. Pour améliorer la fiabilité, l'utilisateur peut laisser certains champs non remplis; CC peut poser une seule question indispensable puis avancer conditionnellement.

**Source des règles pertinentes:** `docs/ai_native/project_instructions/{FINANCIAL_SYSTEMS_COMMAND_CENTER,INVESTMENT_RESEARCH,PORTFOLIO_INTELLIGENCE}.md`; `docs/ai_native/integrated_build/{DELIVERY_PLAN,OPERATING_CONTRACT}.md`; `docs/ai_native/integrated_build/integration/FIRST_CHATGPT_TRACE_CC_PI_ROUTING_REPAIR_R1.md`; `docs/ai_native/integrated_build/portfolio/PROMPT_PI_1_BLOSSOM_PORTFOLIO_WORK_R1.md`. Les règles protégées et approbations CEO prévalent.

## Texte unique à copier dans une nouvelle conversation du Project CC

```text
# PAM Financial Systems — DEMANDE UNIVERSELLE D'ANALYSE COMPLÈTE
Version du gabarit : CC-START-R1-v1.0

**À remplir :** remplace les éléments entre crochets. Tu peux écrire « inconnu » ou « sans objet » : CC doit distinguer les renseignements manquants des valeurs nulles. Ne partage pas d'identifiants, mots de passe ou numéros de compte.

## 1. Ma situation et mes objectifs financiers
- Situation actuelle, en quelques phrases : [décris brièvement]
- Objectif(s) et décision que je veux éclairer : [croissance, diversification, revenu, préservation, révision de positions, comparaison, autre]
- Question prioritaire : [ce que PAM doit m'aider à déterminer]

## 2. Nouvelle contribution à analyser
- Montant et devise : [ex. 350 CAD / aucun montant actuellement / à déterminer]
- Nature : [contribution réelle envisagée / scénario hypothétique]
- Horizon avant décision ou utilisation du capital, s'il y a lieu : [date / aucune échéance]

## 3. Mode d'investissement souhaité
- Mode : [High-CAGR / Balanced / Family-Office / Rational-Aggressive / Intelligent Dividend Harvester / Modern Adaptive Browne / à clarifier]
- Horizon d'investissement : [ex. 5–10 ans / inconnu]
- Objectif spécifique au mode, si pertinent : [texte libre]
Le choix du mode n'approuve pas de nouvelles règles : si sa politique R1 n'est pas encore approuvée, limiter la réponse à une analyse exploratoire et signaler clairement la décision de politique manquante.

## 4. Contraintes et paramètres pratiques
- Tolérance au risque, pertes permanentes à éviter, besoin de liquidités : [texte libre / inconnu]
- Pays, compte(s) et courtier(s) concernés, sans identifiants sensibles : [texte libre / inconnu]
- Devise(s), commissions, frais de conversion FX, fiscalité et achats fractionnaires connus : [texte libre / inconnu]
- Univers de placement, titres à comparer, exclusions ou préférences : [texte libre / libre découverte]
- Indice ou alternative de comparaison, si souhaité : [ex. VFV pour High-CAGR / à définir]

## 5. Mon portefeuille et les données accessibles
- La décision doit-elle tenir compte de mes positions actuelles? [oui / non / à déterminer avec CC]
- Périmètre réellement concerné : [compte(s), portion du patrimoine, ou inconnu]
- Source et date de dernière observation : [Blossom / export / capture datée / aucune]
- URL exacte d'un profil Blossom à examiner, si pertinente : [facultatif — ne présume pas que ce profil contient mes avoirs privés]
- J'autorise pour cette demande une consultation **en lecture seule** de la vue de portefeuille que je sélectionnerai dans une session ChatGPT Work ouverte par moi, si possible : [oui / non / à confirmer]
- À défaut de Work, je peux fournir une capture d'écran ou un export daté : [oui / non / à confirmer]

## 6. Contexte et attentes complémentaires
- Analyses précédentes à reprendre ou à contester : [identifiant/lien accessible / aucune]
- Date de référence de l'information : [informations actuelles / coupure historique précise]
- Questions supplémentaires, critères personnels et niveau de détail : [texte libre]
- Usage de cette demande : [analyse normale / test fonctionnel R1]

## Instructions à Command Center — à conserver pour chaque demande

**Démarrer le vrai processus.** Interprète ce mandat en langage naturel. Vérifie uniquement les références et méthodes réellement accessibles. Préserve les inconnues comme INCONNU, sans inventer de compte, d'horizon, de tolérance au risque, de politique approuvée ni de coût nul. Pose au plus une question strictement bloquante; sinon avance de manière conditionnelle.

**Choisir la bonne route.** Explique en quelques phrases le parcours requis. Pour une recherche fondamentale pertinente, sollicite Investment Research (IR), y compris une découverte d'opportunités justifiée, des sources, des scénarios et une comparaison adéquate. Si le portefeuille est matériel à la question, engage Portfolio Intelligence (PI) dès le départ pour **l'acquisition de la source**, en parallèle de la recherche IR lorsqu'elle est nécessaire. Pour la **synthèse finale combinée**, transmets à PI le dossier original complet d'IR sans modification. Ne saute jamais PI en interprétant toi-même un aperçu public.

**Portfolio Intelligence et Blossom.** Si une observation du portefeuille est pertinente, propose le parcours PI-1 en lecture seule via ChatGPT Work, seulement si cette capacité est réellement disponible et autorisée, avec session déclenchée par moi; sinon demande une seule capture/export daté comme solution de repli. Identifie clairement les vues PUBLIC_REFERENCE, OWN_PRIVATE_AUTHORIZED ou INACCESSIBLE_OR_AMBIGUOUS. Un profil public, quatre lignes visibles ou des poids totalisant 100 % ne prouvent pas la composition de mes comptes. Si l'observation demeure indisponible, demande tout de même un résultat PI_DELTA/UNAVAILABLE plutôt que d'omettre PI.

**Recherche, preuves et calculs.** Utilise les cinq piliers QUALITY, DURABILITY, EXPECTED RETURN, CONFIDENCE et PORTFOLIO ROOM, selon les rôles respectifs d'IR et PI. Vérifie autant que possible les sources primaires permises, les dates, devises, unités, périodes, conflits, hypothèses, calculs et contre-thèses. Ne prétends ni avoir exécuté un programme, ni avoir chargé une méthode, ni avoir démontré un alpha ou un rendement attendu sans preuves. Préserve les références et versions réellement consultées.

**Transferts sans complexité pour moi.** Si un autre Project ou Work doit intervenir, fournis **un message complet à copier**, avec sa destination et le retour attendu. Je ne reconstruis aucun JSON, ID technique, dossier de preuves ou ligne de commande. Les Projects ne communiquent pas automatiquement sauf capacité effectivement vérifiée. Conserve les identifiants et preuves nécessaires en interne.

**Rapport final.** Après les réponses réellement obtenues, remets un rapport intégré, décisionnel, lisible en environ dix minutes ou moins : réponse à ma question, comparaisons, cinq piliers applicables, incertitudes, scénarios, coûts réels connus, portefeuille observé et alternatives. Exprime de préférence les scénarios d'allocation en **pourcentages de NOUVELLES contributions**, seulement si les données et la stratégie approuvée le justifient; sinon présente un résultat conditionnel. Pas de panier d'achats chiffré prématuré. La décision et les transactions m'appartiennent.

**Pour un test R1.** Ajoute une mini-trace factuelle en fin de réponse : route réellement suivie, IR et PI effectivement sollicités ou non, Work tenté ou non, méthodes réellement chargées, sources/observations indisponibles, nombre de transferts humains réellement observés et principaux défauts. N'annonce pas PASS simplement parce qu'un prompt a été généré. Ce gabarit doit rester stable entre essais; toute amélioration se fait par une nouvelle version explicitement identifiée, jamais par réécriture silencieuse.

**Limites permanentes.** Aucun achat/vente, accès courtier, dépense de données financières externes, tâche récurrente, archivage privé automatique, publication, modification de politique ou prétention de mise en production. Ne pas déposer de données personnelles de portefeuille dans GitHub ou PAM Media.
```

## Versions et apprentissage à partir des essais

- `v1.0` devient le **gabarit de comparaison** tant qu'une révision CEO/PM n'a pas été acceptée; changer les valeurs des champs selon le cas ne modifie pas la version.
- Pour chaque essai user-initiated, comparer les résultats et les traces réellement accessibles; noter séparément les défauts d'instructions, de routage, d'accès Work, de sources, d'analyse, de coûts ou de restitution. Ne pas déposer les sorties intégrales ni les portefeuilles privés dans GitHub.
- Les corrections futures peuvent produire `CC-START-R1-v1.1` ou une nouvelle version clairement étiquetée, avec motifs et résultats observés. **Cela ne réentraîne pas automatiquement le modèle ChatGPT** et n'est pas une acceptation du système.
- Aucun changement aux paramètres des Projects, aux décisions protégées, à la stratégie, au code runtime ou à une autorisation de transaction n'est fait par ce fichier. Fusion GitHub sous décision CEO seulement.

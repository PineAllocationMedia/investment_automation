# Guide très simple pour utiliser l’agent d’investissement

Ce dossier contient un petit programme qui lit votre portefeuille, applique vos règles d’investissement, puis crée un rapport.

Vous n’avez pas besoin de savoir programmer. Il faut seulement suivre les étapes dans l’ordre.

Important :

> Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, retardées ou erronées. Toute décision finale doit être validée manuellement.

## 1. Ce que fait l’agent

L’agent répond à une question simple :

**Où devrait aller mon nouveau capital selon mes règles ?**

Il regarde :

- les actions dans votre liste;
- votre portefeuille actuel;
- les informations que vous avez remplies;
- les données fondamentales qu’il peut estimer automatiquement;
- les données de marché gratuites disponibles;
- le risque de concentration;
- la comparaison avec `VFV.TO`;
- la durabilité probable du modèle d’affaires sur 15 à 30 ans;
- les règles de vente, de prudence et d’allocation.

À la fin, il crée des rapports dans le dossier `reports`.

Quand une donnée manque, l’agent essaie maintenant plusieurs sources gratuites avant d’abandonner : historique de prix Yahoo Finance, données rapides Yahoo Finance, états financiers gratuits, bilan et compte de résultat quand ils sont disponibles, certaines données officielles SEC EDGAR pour les sociétés américaines, et une couche canadienne gratuite de secours pour certains titres TSX/TSXV. Si la donnée reste introuvable ou trop incertaine, il écrit simplement `Donnée pas dispo` ou `MANUAL_REQUIRED`.

L’agent applique aussi une hiérarchie simple entre les sources : Yahoo Finance reste prioritaire pour les prix, les rendements et les tendances de marché; la Banque du Canada est prioritaire pour les taux de change vers CAD; SEC EDGAR sert à remplir ou confirmer certains fondamentaux officiels américains; StockAnalysis peut servir de secours gratuit pour certains fondamentaux canadiens. Si deux sources donnent des chiffres trop différents pour une marge ou une croissance, l’agent n’écrase pas automatiquement la donnée: il signale le conflit dans le rapport.

Pour les titres canadiens, cette couche de secours peut aider à réduire les données manquantes sur certains champs comme les marges, la croissance, le cash-flow, la dette ou ROE/ROA. Elle ne remplace pas les rapports BNCD/Morningstar et elle ne transforme pas automatiquement une entreprise canadienne mal couverte en recommandation forte. Elle sert surtout à éviter qu’un bon titre canadien soit pénalisé uniquement parce que yfinance fournit moins de fondamentaux.

L’agent garde aussi une petite mémoire locale des tickers déjà observés. Cette mémoire aide surtout avec les titres canadiens, internationaux, nouveaux ou mal couverts. Elle peut retenir le secteur, la région, la devise, le type d’actif et le statut de couverture. Elle ne remplace pas les données fraîches: elle sert seulement de secours quand une source gratuite ne fournit pas bien ces informations.

Après chaque analyse, l’agent vérifie aussi s’il y a une anomalie inhabituelle: chute brusque d’un score, changement important d’allocation, source de marché fragile, surcharge de données à valider ou concentration élevée. Cette couche ne change pas l’allocation. Elle sert seulement d’alarme douce pour dire: “lis ceci avant d’exécuter une grosse décision” ou “lance un audit si le signal persiste”.

Quelques fichiers importants sont donc maintenant créés automatiquement :

```text
data/ticker_memory.csv
reports/latest_ticker_memory.csv
data/anomaly_history.csv
reports/latest_anomaly_report.csv
reports/latest_cache_health.csv
reports/latest_run_log.csv
```

Vous n’avez normalement pas à les modifier. Ils servent à rendre les prochaines analyses plus stables quand un ticker est difficile à classer et à garder une trace locale des signaux inhabituels.

L’agent entretient aussi son cache de données de marché. Il garde une “dernière bonne donnée connue” quand une source gratuite tombe temporairement, retire les vieux fichiers inutilisables et signale les caches trop anciens. Ce nettoyage ne change pas vos règles d’allocation: il sert seulement à éviter qu’un vieux fichier local brouille une analyse.

L’agent écrit aussi un petit journal d’exécution. Il résume les événements utiles de chaque analyse: cache fragile, données importantes manquantes, anomalies, contradictions de sources et alertes de règles. Ce journal sert à comprendre une recommandation surprenante; il ne change pas automatiquement les montants.

L’agent crée aussi une alerte plus visible quand les sources se contredisent :

```text
reports/latest_source_conflicts.csv
```

Cette alerte ne veut pas dire “vendre” ou “ne pas acheter”. Elle veut dire : “les sources gratuites et officielles ne disent pas exactement la même chose, donc valider avant une grosse décision”.

Important : `VFV.TO` n’est pas une compagnie. C’est l’ETF Vanguard S&P 500 coté au Canada. L’agent l’utilise comme référence, coût d’opportunité et destination de secours.

## Comment utiliser l’agent

Voici la version courte.

### Lanceur opérationnel Linux / Chromebook

Sur la machine Linux dédiée, le chemin recommandé est le lanceur sécurisé :

```bash
cd ~/investment_automation
./scripts/run_investment_analysis.sh
```

Par défaut, il exécute une analyse `high-cagr` avec un capital de `0`. Pour une
cotisation réelle ou un rafraîchissement volontaire :

```bash
./scripts/run_investment_analysis.sh --capital 330
./scripts/run_investment_analysis.sh --capital 330 --refresh-market-data
```

Le lanceur refuse un deuxième run simultané. Lorsqu'une source d'intrants est
configurée, il la synchronise avant `validate-inputs`, puis vérifie que le rapport
compact a bien été régénéré et conserve les 20 derniers journaux dans
`~/investment_automation_run_logs`. Un lancement direct ne fait aucun `git pull`,
aucun rafraîchissement forcé et aucune transaction automatiquement.

#### Notifications Telegram

Le lanceur peut signaler le début, l’échec ou la réussite du run et envoyer le
rapport compact HTML sur Telegram. Créez le fichier local suivant sur la machine
Linux; il ne doit jamais être ajouté au dépôt Git :

```bash
mkdir -p ~/.config/investment_automation
cat > ~/.config/investment_automation/telegram.env <<'EOF'
TELEGRAM_BOT_TOKEN=jeton_fourni_par_BotFather
TELEGRAM_CHAT_ID=identifiant_numerique_du_chat
EOF
chmod 600 ~/.config/investment_automation/telegram.env
```

Le bot doit avoir reçu au moins un message privé avant le premier envoi. Si la
configuration manque ou si Telegram est indisponible, l’analyse directe
continue et l’incident est seulement inscrit dans le journal local. Le jeton
n’est jamais affiché dans les journaux.

Pour demander le capital sur Telegram avant une analyse `high-cagr` :

```bash
.venv/bin/python scripts/request_telegram_analysis.py --mode high-cagr
```

Le bot attend un montant pendant 30 minutes, demande une seconde confirmation
explicite, puis appelle le même lanceur opérationnel. Seul le chat configuré est
accepté; les anciens messages sont ignorés. `ANNULER`, une expiration ou une
réponse invalide ne déclenchent aucune analyse. Cette interaction ne peut
effectuer aucune transaction chez un courtier et ne modifie pas le modèle.

#### Synchronisation des intrants depuis Google Drive

GitHub reste la source de vérité du code. Google Drive sert uniquement à faire
circuler les intrants humains entre le Mac et le Chromebook. Dans Drive, créez
exactement cette arborescence :

```text
Investment Automation/
└── data/
    ├── portfolio.csv
    ├── proxy_calibration.csv
    └── research_reports/
        └── bncd_morningstar/
            └── *.pdf
```

Partagez ce dossier avec Linux dans l'application Fichiers de ChromeOS, puis
repérez son chemin sous `/mnt/chromeos/GoogleDrive/MyDrive/`. Configurez ensuite
la source sur le Chromebook :

```bash
mkdir -p ~/.config/investment_automation
cat > ~/.config/investment_automation/input_sync.env <<'EOF'
INVESTMENT_AUTOMATION_INPUT_SOURCE=/mnt/chromeos/GoogleDrive/MyDrive/Investment Automation
EOF
chmod 600 ~/.config/investment_automation/input_sync.env
```

Vérifiez d'abord sans écrire, puis lancez une synchronisation réelle :

```bash
cd ~/investment_automation
.venv/bin/python scripts/sync_operational_inputs.py --dry-run
.venv/bin/python scripts/sync_operational_inputs.py
```

La liste blanche est limitée à `portfolio.csv`, `proxy_calibration.csv` et aux
PDF du dossier `bncd_morningstar`. Les fichiers remplacés sont sauvegardés dans
`~/.local/state/investment_automation/input_backups`, puis copiés atomiquement.
Un PDF absent de Drive n'est jamais supprimé localement. Une calibration modifiée
déclenche automatiquement `sync-manual-inputs`. Une source absente, un PDF
invalide ou une synchronisation manuelle en échec annule le run avant l'analyse.

#### Planification automatique sur Linux/Crostini

L'automatisation locale peut installer deux timers `systemd --user` :

- les 1er et 15 de chaque mois à **16 h 45 (America/Toronto)**, Telegram demande le capital et attend une confirmation pendant 12 heures;
- chaque dimanche à 9 h, un `health-check --repair-safe` est lancé. L'audit maître ou l'audit modèle n'est exécuté que si son signal existant est `STALE` ou `ABSENT`. Un audit maître rafraîchit déjà l'audit modèle, donc les deux ne sont jamais lancés inutilement le même jour.

Avant chaque service planifié, le déploiement exécute un `git pull --ff-only`
sur `origin/main`. Un conflit ou une divergence annule le run et envoie une
alerte Telegram. Le service synchronise ensuite les intrants Drive avant toute
validation, analyse ou maintenance.

Prévisualisez d'abord les unités, puis installez-les sur le Chromebook :

```bash
cd ~/investment_automation
.venv/bin/python scripts/install_systemd_automation.py --dry-run
.venv/bin/python scripts/install_systemd_automation.py
systemctl --user list-timers 'investment-automation-*'
```

Les timers sont `Persistent=true` : si Linux/Crostini est arrêté à l'heure prévue,
le travail manqué est lancé au prochain démarrage de l'environnement Linux. Ils ne
peuvent toutefois pas réveiller eux-mêmes un Chromebook complètement éteint. Les
journaux sont consultables avec :

```bash
journalctl --user -u investment-automation-analysis.service -n 100
journalctl --user -u investment-automation-maintenance.service -n 100
```

Pour désactiver temporairement l'automatisation sans supprimer les fichiers :

```bash
systemctl --user disable --now investment-automation-analysis.timer investment-automation-maintenance.timer
```

1. Je remplis `data/portfolio.csv` avec mes positions actuelles. J’écris le nombre d’actions, mon coût moyen, la devise du coût moyen et le type de compte.
2. L’historique des changements se fait automatiquement: après un achat ou une vente, je mets `portfolio.csv` à jour, puis je lance `python3 main.py sync-portfolio` pour enregistrer le changement sans relancer une analyse complète.
3. Je peux ignorer `data/account_locations.csv`: il est seulement gardé comme ancien fichier de secours.
4. Je peux remplir `data/market_universe.csv` avec seulement le ticker et le nom des compagnies à surveiller/scanner.
5. Optionnel : je peux mettre à jour `data/proxy_calibration.csv`, puis lancer `python3 main.py sync-manual-inputs` pour appliquer des données confirmées. Le fichier `data/manual_inputs_friendly.txt` est généré automatiquement par cette commande.
6. Je lance mon analyse principale :

```bash
python3 main.py analyze --capital 500 --mode high-cagr --refresh-market-data
```

Sur Windows, écrivez plutôt `python` à la place de `python3`.

7. L’agent me dit :

- où mettre ma cotisation;
- quelles positions conserver;
- quelles positions ne plus renforcer;
- quelles positions surveiller;
- quelles positions vendre partiellement;
- quelles candidates externes méritent une analyse manuelle;
- quels risques de concentration existent;
- quels titres ressemblent à de vrais compounders durables 15-30 ans;
- si `VFV.TO` est préférable.

Important : en mode `high-cagr`, les titres dans `market_universe.csv` ne reçoivent pas automatiquement d’argent. Ils servent à repérer des candidates à analyser manuellement ou à promouvoir volontairement vers le portefeuille. Dans les trois autres modes (`balanced`, `family-office`, `rational-aggressive`), l’agent peut utiliser directement un titre externe dans l’allocation seulement s’il passe des filtres très stricts et des plafonds de nouvelle position. Le mot “titre” inclut maintenant les actions et certains ETF/FNB externes, mais les ETF sont analysés avec des règles spéciales, pas comme des compagnies.

L’agent crée aussi une section de découverte externe auto-entretenue. Elle regarde une liste configurable de titres et, quand Internet est disponible, des listes publiques gratuites comme le Nasdaq 100, le S&P 500 et le TSX 60. Elle exclut les titres déjà dans votre portefeuille ou dans `market_universe.csv`. Si un titre ressort vraiment bien, il apparaîtra dans :

```text
reports/latest_discovery_ideas.csv
```

Cette liste ne veut pas dire “acheter”. Elle veut seulement dire : “ce titre mérite peut-être d’être ajouté dans `data/market_universe.csv` pour être surveillé aux prochaines analyses”.

S’il n’y a rien dans cette section, c’est correct. Cela veut simplement dire qu’aucune nouvelle idée externe n’a passé les filtres stricts cette fois-ci.

L’agent crée aussi :

```text
reports/latest_discovery_maintenance.csv
```

Ce fichier indique quels titres du radar automatique sont gardés, mis en quarantaine ou écartés par les filtres mécaniques.

## Workflow recommandé complet

Voici l’ordre idéal pour utiliser l’agent correctement.

### À chaque cotisation

1. Ouvrir le dossier du modèle :

```bash
cd /Users/jordansoucy/Documents/Codex/2026-04-28/tu-es-un-d-veloppeur-python/investment_automation
```

2. Activer l’environnement Python :

```bash
source .venv/bin/activate
```

3. Vérifier la santé générale du modèle :

```bash
python3 main.py health-check
```

Si le health-check indique seulement des problèmes mécaniques simples, vous pouvez laisser l’agent les réparer prudemment :

```bash
python3 main.py health-check --repair-safe
```

Cette commande peut ajouter des colonnes manquantes, recréer un CSV absent ou retirer des lignes totalement vides. Elle ne change pas vos montants, vos tickers ou vos décisions d’investissement.

Elle vérifie aussi le cache de marché et écrit le détail ici :

```bash
reports/latest_cache_health.csv
```

Si ce fichier affiche seulement de vieux caches ou une source temporairement indisponible, ce n’est pas automatiquement grave. Avant une grosse cotisation, utilisez simplement l’analyse avec `--refresh-market-data`.

Si le `health-check` affiche un avertissement sur `pytesseract`, ce n’est pas bloquant. Cela veut seulement dire que l’option OCR pour lire certains PDF scannés n’est pas installée. Les analyses normales, les rapports HTML, les audits et les fichiers CSV continuent de fonctionner.

4. Vérifier que les fichiers sont lisibles :

```bash
python3 main.py validate-inputs
```

5. Lancer l’analyse principale avec le montant de la cotisation à investir :

```bash
python3 main.py analyze --capital 500 --mode high-cagr --refresh-market-data
```

6. Lire le rapport compact en premier :

```bash
open reports/latest_report_compact.html
```

Le rapport complet reste disponible ici :

```bash
open reports/latest_report.html
```

7. Acheter les titres recommandés dans votre compte de courtage.

8. Mettre ensuite `data/portfolio.csv` à jour avec le nouveau nombre d’actions, le coût moyen et le compte :

```bash
open -a TextEdit data/portfolio.csv
```

9. Enregistrer seulement le changement de portefeuille, sans relancer une nouvelle analyse :

```bash
python3 main.py sync-portfolio
```

Cette commande met à jour l’historique du portefeuille, mais ne crée pas de nouvelle recommandation.

Si vous avez oublié de synchroniser le jour exact de l’achat, vous pouvez préciser la date :

```bash
python3 main.py sync-portfolio --date 2026-05-28
```

Utilisez `--refresh-market-data` avec `sync-portfolio` seulement si vous voulez rafraîchir les prix utilisés pour estimer la valeur du changement :

```bash
python3 main.py sync-portfolio --refresh-market-data
```

Si vous avez mis à jour le fichier de calibration proxy, appliquez les données confirmées au scoring avec :

```bash
python3 main.py sync-manual-inputs
```

Cette commande traduit `data/proxy_calibration.csv` → `data/manual_inputs_friendly.txt`
en conservant la provenance et la date de chaque champ. À relancer après chaque
mise à jour du fichier de calibration proxy. Une calibration n'est pas une
confirmation humaine: les valeurs actuelles peuvent corriger un proxy de scoring,
mais les valeurs périmées ou sans date restent seulement contextuelles. La durée
de validité dépend du champ (90 jours pour valorisation/estimations forward,
120-180 jours pour bilan/marges, davantage pour ROIC/EPS historiques et
moat/management). Les modifications explicites de l'utilisateur dans le fichier
convivial restent des overrides `HUMAN_MANUAL` et sont préservées au prochain sync.

Résumé simple :

```text
Analyse -> achat -> mise à jour de portfolio.csv -> sync-portfolio -> attendre la prochaine cotisation
```

Ne relancez pas une deuxième analyse complète juste après l’achat, sauf si vous voulez vraiment une nouvelle recommandation. `sync-portfolio` existe justement pour éviter de remplir l’historique avec deux analyses presque identiques.

Si vous modifiez `portfolio.csv` pour corriger une erreur sans vraie transaction, `sync-portfolio` peut quand même détecter une variation. Dans ce cas, corrigez le fichier avant de synchroniser.

### Une fois par mois

Vérifier quels rapports BNCD/Morningstar seraient les plus utiles :

```bash
python3 main.py research-needed --limit 20 --refresh-market-data
```

Vérifier que les rapports déjà déposés sont visibles :

```bash
python3 main.py research-status --limit 20
```

### Quelques fois par année

Faire l’audit maître du modèle :

```bash
python3 main.py full-audit --period all --mode high-cagr --refresh-market-data
```

Cet audit vérifie si la méthode reste saine : performance suivie, stabilité, concentration, risque de cycle/bulle, part VFV et backtest théorique.

### Après plusieurs mois d’historique

Demander au modèle s’il détecte des réglages secondaires à améliorer :

```bash
python3 main.py improvement-audit --period 12m --mode high-cagr
```

Lire ensuite :

```text
reports/latest_improvement_suggestions.html
```

Si le rapport dit `INSUFFICIENT_HISTORY`, ne rien faire. Cela veut dire que le modèle n’a pas encore assez de recul pour s’ajuster de manière responsable.

Pendant la période de validation Baseline V1, les suggestions restent en mode `PROPOSAL_ONLY`. La commande historique existe pour compatibilité, mais refuse toute modification :

```bash
python3 main.py apply-safe-tuning --mode high-cagr
```

Cette commande ne touche ni au code ni aux paramètres tant que la politique est `PROPOSAL_ONLY`. Les propositions restent visibles dans les rapports pour revue humaine.

Lorsque cette politique sera réévaluée dans un chantier ultérieur, les seuls fichiers historiquement prévus pour les micro-ajustements sont :

```text
config/model_tuning.yaml
```

Elle crée aussi une sauvegarde avant changement et garde l’historique ici :

```text
data/model_tuning_history.csv
```

### Résumé de la routine

```text
Chaque cotisation -> validate-inputs -> analyze -> acheter -> modifier portfolio.csv -> sync-portfolio
Chaque mois -> research-needed -> research-status
Quelques fois par année -> full-audit
Après assez d’historique -> improvement-audit
Suggestions -> revue humaine; apply-safe-tuning reste fail-closed en PROPOSAL_ONLY
```

Important : `apply-safe-tuning` n’est pas une commande mensuelle et n’applique actuellement aucun changement. Un simple drapeau YAML ne peut pas contourner ce garde-fou codé.

## Sauvegarder le modèle avant une grosse modification

Avant de faire une grosse modification au modèle, créez une sauvegarde.

Une sauvegarde est simplement une copie datée du dossier de l’agent. Elle sert de filet de sécurité si vous n’aimez pas un changement ou si vous voulez revenir à une ancienne version.

Pour créer une sauvegarde sur Mac :

```bash
python3 main.py backup
```

Sur Windows :

```bash
python main.py backup
```

L’agent crée alors un dossier dans :

```text
backups
```

Le nom ressemble à ceci :

```text
investment_automation_backup_2026-05-23_14-30-00
```

Cette sauvegarde garde les fichiers importants :

- vos fichiers `data`;
- vos fichiers `config`;
- le code du modèle;
- les rapports;
- les rapports BNCD/Morningstar que vous avez ajoutés.

Pour éviter une copie trop lourde, la sauvegarde ne copie pas :

- `.venv`;
- les caches Python;
- les anciennes sauvegardes;
- `data/cached_market_data`, qui peut être recréé avec `--refresh-market-data`.

Pour voir les sauvegardes déjà créées :

Sur Mac :

```bash
python3 main.py list-backups
```

Sur Windows :

```bash
python main.py list-backups
```

Important : l’agent ne restaure pas automatiquement une sauvegarde. C’est volontaire, pour éviter d’écraser vos fichiers par erreur. Si vous voulez revenir à une sauvegarde, gardez le dossier de sauvegarde et faites la restauration manuellement ou demandez de l’aide.

Bonne habitude :

```text
Avant une grosse modification -> python3 main.py backup
Après la modification -> lancer une analyse et vérifier le rapport compact
Si tout est correct -> continuer
Si quelque chose ne plaît pas -> garder la sauvegarde et demander une restauration
```

## Vérifier si le modèle reste sain dans le temps

Quelques fois par année, la commande la plus complète est l’audit maître :

```bash
python3 main.py full-audit --period all --mode high-cagr
```

Cette commande ne remplace pas l’analyse mensuelle. Elle sert à vérifier le critère important suivant : est-ce que le modèle a une méthode constante, robuste, comparable à `VFV.TO`, et capable d’être suivie sur plusieurs cycles?

L’audit maître regroupe :

- la stabilité des recommandations;
- la part moyenne envoyée vers `VFV.TO`;
- le risque de concentration;
- le risque de cycle, tendance ou bulle;
- la performance réelle suivie du portefeuille vs S&P 500;
- un backtest théorique 5 et 10 ans;
- le backtest walk-forward des recommandations réellement produites;
- la santé des sources utilisées;
- une revue des seuils à surveiller.

Vous n’avez pas besoin d’inscrire un capital mensuel. L’agent essaie d’utiliser la moyenne de vos cotisations détectées dans l’historique. Si l’historique est trop court, il utilise 500 $ par mois comme hypothèse par défaut pour le backtest.

À lire :

```text
reports/latest_full_audit.md
reports/latest_full_audit.html
reports/latest_full_audit_summary.csv
```

La commande suivante existe encore si vous voulez seulement vérifier la stabilité du modèle sans le backtest complet :

```bash
python3 main.py model-audit --period 12m --mode high-cagr
```

Cette commande ne choisit pas une nouvelle allocation. Elle regarde les anciennes analyses sauvegardées et vérifie si le modèle est trop instable, trop défensif avec `VFV.TO`, trop concentré ou encore bien aligné avec votre objectif long terme.

Important : l’historique des recommandations est séparé par mode. Une analyse `high-cagr` est comparée seulement à d’anciennes analyses `high-cagr`; elle n’est pas mélangée avec `balanced`, `family-office` ou `rational-aggressive`. L’historique réel de vos positions et transactions reste commun, car vos achats et ventes réels ne dépendent pas du mode choisi.

Elle inclut aussi une petite **revue des seuils**. Cette revue indique si certaines règles semblent peut-être trop strictes, trop permissives, trop concentrées ou trop sensibles. Elle ne modifie jamais les règles automatiquement. Elle sert seulement à dire : “à surveiller” ou “aucun ajustement suggéré”.

L’audit bénéficie aussi des nouvelles vérifications de données. Il lit la santé globale des sources et tient compte du risque qu’une source devienne moins fiable avant d’autoriser un micro-ajustement automatique. Les contradictions détaillées entre sources et la mémoire ticker restent surtout informatives: elles aident à comprendre les rapports et les futurs classements, mais elles ne déclenchent pas seules une modification automatique du modèle.

Si vous n’avez pas encore 12 mois d’historique, ce n’est pas grave. Le rapport fonctionne quand même, mais il indique que la conclusion est préliminaire. Les analyses lancées plusieurs fois la même journée comptent comme une seule date pour éviter de biaiser le diagnostic.

À lire :

```text
reports/latest_model_audit.md
reports/latest_model_audit.html
reports/latest_model_audit.csv
```

### Backtest walk-forward local

Le backtest walk-forward sert à vérifier si les recommandations historiques admissibles ont bien agi après leur publication, avec les informations disponibles à ce moment-là. Sa classe de preuve est `POINT_IN_TIME_WALK_FORWARD`.

Cette commande ne change jamais vos allocations. Elle sert seulement à évaluer la robustesse de la méthode.

```bash
python3 main.py walk-forward-backtest --mode high-cagr
```

Pour forcer un rafraîchissement des prix historiques utilisés dans la simulation :

```bash
python3 main.py walk-forward-backtest --mode high-cagr --refresh-market-data
```

Elle vérifie :

- les anciennes analyses sauvegardées;
- les anciennes allocations sauvegardées;
- le mode utilisé, par exemple seulement `high-cagr`;
- les dates distinctes d’analyse;
- le but du run (`SCHEDULED_DECISION`, `MANUAL_DECISION`, diagnostic, test, maintenance, capital nul ou legacy inconnu);
- si deux décisions admissibles sont assez espacées pour être utiles;
- si plusieurs analyses lancées la même journée doivent être dédupliquées.

Elle simule ensuite, quand c’est possible :

- l’allocation réellement recommandée à une date passée;
- son rendement jusqu’à la prochaine décision admissible, sans qu'un diagnostic intermédiaire fragmente la période;
- le rendement de `VFV.TO` sur la même période;
- l’écart entre le modèle et `VFV.TO`;
- les périodes exclues parce que les prix manquent ou parce que l’historique est trop court.

À lire :

```text
reports/latest_walk_forward_report.md
reports/latest_walk_forward_report.html
reports/latest_walk_forward_summary.csv
reports/latest_walk_forward_periods.csv
reports/latest_walk_forward_period_allocations.csv
reports/latest_walk_forward_regime_summary.csv
reports/latest_walk_forward_inventory.md
reports/latest_walk_forward_inventory.html
reports/latest_walk_forward_inventory.csv
reports/latest_walk_forward_coverage.csv
```

Interprétation rapide :

- `INSUFFICIENT_HISTORY` : pas encore assez d’historique.
- `EARLY_SIGNAL_ONLY` : quelques données existent, mais c’est encore trop préliminaire.
- `BUILDING_HISTORY` : l’historique devient utile, mais reste court.
- `READY_FOR_WALK_FORWARD_SIMULATION` : assez de périodes existent pour construire une vraie simulation walk-forward informative.

Interprétation des résultats de simulation :

- `NO_USABLE_PERIODS` : aucune période assez espacée.
- `NO_SIMULATED_PERIODS` : des périodes existent, mais les prix ne permettent pas encore un calcul propre.
- `EARLY_SIGNAL_ONLY` : le résultat est seulement un indice préliminaire.
- `PRELIMINARY_WALK_FORWARD` : utile pour observer, pas assez fort pour recalibrer.
- `READY_FOR_WALK_FORWARD_REVIEW` : assez de périodes pour une vraie revue, mais sans correction automatique agressive.

La simulation contient aussi un résumé par régime de marché :

```text
reports/latest_walk_forward_regime_summary.csv
```

Cette section classe les périodes selon le comportement de `VFV.TO`, par exemple marché faible, marché stable ou forte hausse. Elle sert à éviter de conclure que le modèle est robuste seulement parce qu’il a bien fonctionné dans un seul contexte. Si l’historique couvre trop peu de régimes, le signal reste informatif. Il ne bloque pas seul les recommandations.

Important : cette commande sépare l’historique par mode et par but de run. Le mode `high-cagr` n’est pas mélangé avec `balanced`, `family-office` ou `rational-aggressive`. Les anciens snapshots sans but explicite restent `UNKNOWN_LEGACY`; un repli causal espacé peut les rendre `PARTIALLY_RECOVERABLE` sans fabriquer une certitude historique.

Le walk-forward est aussi lu par `full-audit` et `improvement-audit`.

- Dans `full-audit`, il devient une preuve supplémentaire pour juger si la méthode tient dans le temps.
- Dans `improvement-audit`, il documente la maturité OOS et la portée de version; aucun résultat mécanique ou mixte ne peut autoriser un ajustement automatique.
- Si le walk-forward est trop jeune ou sans période courante utilisable, la confiance de validation reste `INSUFFICIENT` ou `EARLY`.
- S’il montre une faiblesse nette vs `VFV.TO`, il conserve une autorité d'avertissement et exige une revue humaine.
- `health-check` vérifie maintenant aussi si les fichiers walk-forward sont présents, complets et lisibles.
- `walk-forward-backtest` écrit aussi un journal dans `reports/latest_run_log.csv`, sans créer de nouvelle analyse mensuelle.

Lecture importante :

- Un walk-forward jeune sert à apprendre, pas à corriger automatiquement.
- Un régime faible isolé est un signal à surveiller, pas une raison de changer toute la méthode.
- Les garde-fous sont conçus pour réduire l’overfitting sans rendre `high-cagr` inutilement conservateur.
- Un nombre de périodes décrit la maturité des preuves; il ne prouve jamais l'alpha ou un skill statistique.

### Hiérarchie et confiance de validation

La hiérarchie canonique, de la plus forte à la plus faible autorité de validation de stratégie, est :

1. `LIVE_FORWARD_EVIDENCE`;
2. `POINT_IN_TIME_WALK_FORWARD`;
3. `HISTORICAL_STRESS_SENSITIVITY`;
4. `MECHANICAL_DIAGNOSTIC`;
5. `HEURISTIC_QUALITATIVE`.

Le backtest théorique à scores courants est conservé sous `MECHANICAL_DIAGNOSTIC`. Il peut révéler une concentration pathologique, une mécanique cassée ou un drawdown catastrophique. Ses bons rendements n'ont aucune autorité positive pour prouver l'alpha, augmenter la confiance de validation ou autoriser un tuning.

Les rapports séparent désormais `RUN_EXECUTION_CONFIDENCE`, `DATA_INTEGRITY_CONFIDENCE`, `SOURCE_CONFIDENCE`, `STRATEGY_VALIDATION_CONFIDENCE` et `WALK_FORWARD_CONFIDENCE`. Un niveau élevé de fraîcheur des données ne signifie donc pas que la stratégie est fortement validée.

L'audit de stabilité primaire est `CURRENT_VERSION_AUDIT`: il compare seulement les observations `SCHEDULED_DECISION` et `MANUAL_DECISION` produites sous le `MODEL_RULES_VERSION` courant. Les diagnostics, tests de développement, analyses zéro-capital, maintenances et snapshots `UNKNOWN_LEGACY` restent auditablement comptés, mais ne peuvent augmenter la maturité, la confiance ou l'historique primaire. Le regroupement intra-journée conserve l'identité `(date, version, run_purpose)`, de sorte qu'un diagnostic tardif ne remplace jamais une vraie décision du même jour. `CROSS_VERSION_DIAGNOSTIC` évalue les transitions entre décisions comparables et conserve séparément tout le contexte non décisionnel. Les maturités `INSUFFICIENT`, `EARLY`, `DEVELOPING` et `SUBSTANTIAL` décrivent le recul disponible, jamais une preuve statistique de skill.

## Améliorer les réglages du modèle sans Codex

L’agent possède une couche locale de propositions d’amélioration prudentes.

Elle ne réécrit pas le code. Elle propose seulement des micro-ajustements dans :

```text
config/model_tuning.yaml
```

Ce fichier contient des réglages secondaires comme :

- ajustement très léger de la part `VFV.TO`;
- force de la stabilité des recommandations;
- seuil minimal du capital allocation score;
- budget cycle/bulle/tendance;
- plafond marginal par titre;
- réserve défensive des modes prudents.

Les règles vitales restent verrouillées dans le code :

- ne pas acheter une thèse cassée;
- ne pas renforcer une position orange ou rouge;
- ne pas ignorer `VFV.TO`;
- ne pas promouvoir automatiquement une action externe;
- ne pas utiliser un ETF spéculatif comme ETF défensif.

Pour obtenir des suggestions :

```bash
python3 main.py improvement-audit --period 12m --mode high-cagr
```

À lire :

```text
reports/latest_improvement_suggestions.md
reports/latest_improvement_suggestions.html
reports/latest_improvement_suggestions.csv
reports/latest_improvement_summary.csv
reports/latest_underperformance_attribution.csv
```

L’audit d’amélioration inclut maintenant un gouverneur de sous-performance.
Son rôle est de vérifier si une sous-performance face au S&P 500 ressemble à une vraie faiblesse du modèle ou seulement à un retard temporaire d’un profil long terme.
Il protège contre deux erreurs : corriger trop vite après une mauvaise année, ou refuser de corriger après plusieurs années de signaux faibles.

La commande historique suivante reste disponible, mais elle est fail-closed sous la politique `PROPOSAL_ONLY` :

```bash
python3 main.py apply-safe-tuning --mode high-cagr
```

Pendant cette phase, cette commande :

- n'applique aucune suggestion;
- retourne explicitement `PROPOSAL_ONLY`;
- laisse toutes les propositions en revue humaine;
- ne peut pas être réactivée par le seul champ `safe_auto_apply.enabled` du YAML;
- exige, pour toute future politique différente, une preuve OOS authentique, homogène par version et dotée d'une provenance explicite.

Si l’historique est trop court, la commande ne change rien. C’est normal et voulu.

Bonne routine :

```text
À chaque cotisation -> analyze -> achat -> mise à jour portfolio.csv -> sync-portfolio
Quelques fois par année -> full-audit
Après plusieurs mois d’historique -> improvement-audit
Suggestions SAFE -> revue humaine; aucune auto-application pendant Baseline V1
```

Important aussi : si vous voyez une étoile `*` à côté d’un ticker dans le rapport, cela veut dire :

- il manque beaucoup de données importantes;
- ou l’agent n’a pas trouvé de prix;
- ou l’agent veut que vous vérifiiez que le ticker correspond bien à la compagnie voulue.

Si un ticker a seulement été corrigé automatiquement par alias, l’agent l’affiche entre parenthèses, par exemple `SBGSY (SCHN)`, sans étoile.

## 2. Ce qu’il faut installer une seule fois

Il faut installer Python.

Python est l’outil qui permet de faire fonctionner l’agent.

### Sur Mac

1. Ouvrez votre navigateur Internet.
2. Allez sur le site officiel : https://www.python.org/downloads/
3. Téléchargez Python pour Mac.
4. Installez-le comme une application normale.

### Sur Windows

1. Ouvrez votre navigateur Internet.
2. Allez sur le site officiel : https://www.python.org/downloads/
3. Téléchargez Python pour Windows.
4. Pendant l’installation, cochez la case :

```text
Add Python to PATH
```

5. Terminez l’installation.

## 3. Ouvrir le dossier de l’agent

Le dossier du projet s’appelle :

```text
investment_automation
```

Dans ce dossier, vous verrez :

```text
main.py
requirements.txt
data
reports
config
src
tests
```

Les deux dossiers les plus importants pour vous sont :

- `data` : les fichiers que vous remplissez;
- `reports` : les rapports créés par l’agent.

## 4. Ouvrir la fenêtre de commandes

La fenêtre de commandes sert seulement à dire à l’ordinateur quoi lancer.

### Sur Mac

1. Ouvrez l’application **Terminal**.
2. Écrivez `cd`, puis un espace.
3. Glissez le dossier `investment_automation` dans la fenêtre Terminal.
4. Appuyez sur **Entrée**.

Vous devriez avoir quelque chose qui ressemble à ceci :

```bash
cd /Users/votre-nom/.../investment_automation
```

Dans ce projet-ci, la commande complète est :

```bash
cd /Users/jordansoucy/Documents/Codex/2026-04-28/tu-es-un-d-veloppeur-python/investment_automation
```

### Sur Windows

1. Ouvrez le dossier `investment_automation`.
2. Cliquez dans la barre d’adresse du dossier.
3. Écrivez :

```text
cmd
```

4. Appuyez sur **Entrée**.

Une fenêtre noire s’ouvrira directement dans le bon dossier.

## 5. Préparer l’agent une seule fois

Copiez-collez les lignes suivantes dans la fenêtre de commandes.

Faites une ligne à la fois.

### Sur Mac ou Linux

```bash
python3 -m venv .venv
```

Puis :

```bash
source .venv/bin/activate
```

Puis :

```bash
python3 -m pip install -r requirements.txt
```

Si l’ordinateur dit que `python3` n’existe pas, Python n’est probablement pas encore installé.

Retournez alors à l’étape 2 et installez Python.

### Sur Windows

```bash
python -m venv .venv
```

Puis :

```bash
.venv\Scripts\activate
```

Puis :

```bash
python -m pip install -r requirements.txt
```

### Optionnel : lire les PDF scannés avec OCR

Cette étape n’est pas obligatoire.

L’agent fonctionne sans OCR. L’OCR sert seulement si certains rapports BNCD/Morningstar sont des PDF scannés comme des images et que le texte ne peut pas être extrait normalement.

Si le `health-check` affiche :

```text
pytesseract absent
```

cela veut seulement dire que cette option OCR n’est pas installée.

Sur Mac, dans le dossier `investment_automation`, avec l’environnement activé :

```bash
brew install tesseract
brew install tesseract-lang
python3 -m pip install pytesseract
```

Si le Terminal répond :

```text
brew: command not found
```

installez d’abord Homebrew depuis le site officiel :

```text
https://brew.sh/
```

Puis relancez les commandes OCR ci-dessus.

Pour vérifier que l’OCR est disponible :

```bash
python3 -c "import pytesseract; print(pytesseract.get_tesseract_version())"
python3 main.py health-check --repair-safe --limit 12
```

Sur Windows, il faut installer le programme Tesseract OCR séparément, l’ajouter au `PATH`, puis lancer :

```bash
python -m pip install pytesseract
python main.py health-check --repair-safe --limit 12
```

Si vous ne déposez que des PDF lisibles normalement, vous pouvez ignorer cette section.

## 6. Créer les fichiers de départ

Dans la fenêtre de commandes, lancez :

```bash
python3 main.py init
```

Sur Windows, utilisez :

```bash
python main.py init
```

Cette commande prépare les fichiers à remplir.

Le fichier manuel `manual_inputs_friendly.txt` est maintenant optionnel. Vous pouvez le laisser vide.

## 7. Remplir les fichiers importants

Ouvrez le dossier :

```text
data
```

Vous devez surtout remplir `portfolio.csv`.

Vous pouvez aussi remplir `market_universe.csv` pour surveiller/scanner des actions que vous ne possédez pas.

### Fichier 1 : portfolio.csv

Ce fichier indique ce que vous possédez déjà.

Format recommandé :

```csv
ticker,shares,average_cost,average_cost_currency,account_type
MSFT,3,250,USD,TFSA1
MSFT,2,260,USD,TFSA2
AVGO,1,900,USD,TFSA1
VFV.TO,3,140,CAD,FHSA
INTU,0,,,
```

Vous remplissez seulement :

- `ticker` = symbole de l’action;
- `shares` = nombre d’actions;
- `average_cost` = coût unitaire moyen;
- `average_cost_currency` = devise du coût moyen. Écrire `CAD` ou `USD`.
- `account_type` = type de compte. Écrire `TFSA`, `FHSA`, `RRSP` ou `NON_REGISTERED`.

Vous pouvez aussi distinguer plusieurs comptes du même type avec un chiffre :

```text
TFSA1
TFSA2
FHSA1
RRSP1
NON_REGISTERED1
```

L’agent garde ces comptes séparés dans l’analyse fiscale, mais il comprend que `TFSA1` et `TFSA2` sont tous les deux des `TFSA`.

Le reste se calcule automatiquement quand c’est possible.

Si vous remplissez `shares`, l’agent calcule :

```text
current_value = shares x prix actuel gratuit
```

Quand le prix est en USD ou EUR, l’agent essaie aussi de convertir gratuitement la valeur vers CAD. Il utilise d’abord les taux officiels gratuits de la Banque du Canada quand ils sont disponibles, puis Yahoo Finance comme secours. Vous n’avez donc plus besoin de mettre à jour la valeur actuelle à la main.

Si vous remplissez `average_cost` et `average_cost_currency`, l’agent calcule :

```text
acquisition_value = shares x average_cost
acquisition_value_cad = acquisition_value convertie en CAD
```

Pour que la protection des winners soit fiable, indiquez bien la devise du coût moyen.

Exemple : si votre courtier affiche un coût moyen de 250 $ US par action pour MSFT, écrivez `USD`.

Exemple : si votre courtier affiche un coût moyen de 396,94 $ CAD par action pour AAPL, écrivez `CAD`.

Exemple : si vous avez 5 actions MSFT et que votre coût moyen est 250 $ par action, écrivez :

```csv
MSFT,5,250,USD,TFSA
```

Si ces 5 actions MSFT sont réparties dans deux CELI, écrivez deux lignes :

```csv
MSFT,3,250,USD,TFSA1
MSFT,2,260,USD,TFSA2
```

Pour l’allocation, l’agent additionne les deux lignes comme une seule position MSFT. Pour la fiscalité, il garde `TFSA1` et `TFSA2` séparés.

Ancienne compatibilité : si votre fichier contient encore `average_cost_cad`, `current_value` ou `acquisition_value`, l’agent les accepte toujours. `average_cost_cad` sera traité comme un coût en CAD. Mais le format recommandé est maintenant `average_cost` + `average_cost_currency`.

Ancienne compatibilité fiscale : `account_locations.csv` est encore accepté si vous l’avez déjà, mais il n’est plus nécessaire. Le modèle utilise d’abord `account_type` dans `portfolio.csv`.

### Historique automatique des changements

Vous n’avez normalement rien à remplir pour l’historique.

`portfolio.csv` dit : “voici ce que je possède maintenant”.

À chaque analyse complète ou commande `sync-portfolio`, l’agent compare le `portfolio.csv` actuel avec l’état sauvegardé précédent.

Si vous avez changé le nombre d’actions, le compte ou le coût moyen, il crée automatiquement une ligne d’historique avec :

- la date de la commande lancée, ou la date fournie avec `--date`;
- le ticker;
- le compte exact, par exemple `TFSA1` ou `TFSA2`;
- le type de changement;
- le nombre d’actions avant;
- le nombre d’actions après;
- la variation;
- une valeur approximative en CAD quand le prix gratuit est disponible.

L’historique automatique est gardé ici :

```text
data/portfolio_change_history.csv
```

Et l’état de référence utilisé pour comparer est gardé ici :

```text
data/portfolio_state_snapshot.csv
```

Ne modifiez normalement pas ces deux fichiers. Ils sont créés et mis à jour par l’agent.

Après une analyse ou une synchronisation, l’agent produit :

```text
reports/latest_portfolio_changes.csv
reports/latest_portfolio_change_history.csv
reports/latest_portfolio_change_summary.csv
reports/latest_account_performance_vs_sp500.csv
```

Le rapport Markdown affiche aussi la section “Historique automatique des changements du portefeuille”.

#### Commande utile après un achat : sync-portfolio

Si vous achetez les titres recommandés et que vous mettez ensuite `portfolio.csv` à jour, vous pouvez enregistrer ce changement sans relancer une analyse complète :

```bash
python3 main.py sync-portfolio
```

Cette commande ne crée pas de nouvelle recommandation. Elle fait seulement ceci :

- compare le nouveau `portfolio.csv` avec le dernier état sauvegardé;
- inscrit les changements dans `data/portfolio_change_history.csv`;
- met à jour `data/portfolio_inferred_transactions.csv`;
- met à jour `data/account_performance_history.csv` pour la comparaison portefeuille vs S&P 500;
- met à jour les petits CSV de suivi dans `reports/`.

C’est utile si vous voulez que la date de l’achat soit proche de la vraie date, sans remplir l’historique avec deux analyses presque identiques.

Les rapports HTML complet et compact ne sont pas régénérés par `sync-portfolio`. Ils seront actualisés à la prochaine vraie analyse. Par contre, les CSV de suivi utilisés par l’audit et la performance sont mis à jour immédiatement.

Si vous avez oublié de le faire le jour même, vous pouvez inscrire une date manuellement :

```bash
python3 main.py sync-portfolio --date 2026-05-28
```

Workflow recommandé :

```text
1. Lancer l’analyse.
2. Acheter selon la recommandation.
3. Mettre à jour data/portfolio.csv.
4. Lancer python3 main.py sync-portfolio.
5. Attendre la prochaine cotisation pour relancer une vraie analyse.
```

### Registre manuel optionnel : portfolio_transactions.csv

Ce fichier existe encore, mais il est optionnel.

Il sert seulement si vous voulez inscrire une cotisation en espèces, un dividende ou une note de transaction que le simple changement de `portfolio.csv` ne peut pas deviner.

Vous n’avez pas besoin de le remplir pour que les ajouts ou ventes d’actions soient détectés.

Pour un titre que vous ne possédez pas encore, mais que vous voulez considérer dans les cotisations, écrivez `shares=0`.

Exception importante : `VFV.TO` est accepté dans ce fichier, mais c’est un ETF S&P 500, pas une action de compagnie.

N’ajoutez pas le symbole `$`.

Si vous écrivez un ticker canadien sans suffixe, l’agent peut corriger certains cas connus automatiquement.

Exemples :

```text
CSU devient CSU.TO
WSP devient WSP.TO
TOI devient TOI.V
NANO devient NANO.TO
SCHN devient SBGSY
CCO devient CCO.TO
DOL devient DOL.TO
DSG devient DSG.TO
PNG devient PNG.V
```

Ces corrections se trouvent dans :

```text
config/ticker_aliases.yaml
```

Si un jour l’agent prend la mauvaise compagnie, ajoutez une ligne dans ce fichier ou vérifiez le bon ticker Yahoo Finance.

### Fichier 2 optionnel : manual_inputs_friendly.txt

Ce fichier sert seulement à corriger ou confirmer les informations que l’agent estime automatiquement.

Vous n’êtes plus obligé de le remplir.

Si vous ne le remplissez pas, l’agent utilise les données gratuites disponibles et écrit clairement quelles données ont été estimées automatiquement.

Il est fait pour être ouvert dans TextEdit.

Il peut contenir vos positions actuelles, mais aussi des actions du `market_universe.csv` si vous voulez une analyse plus fiable.

Pour l’ouvrir sur Mac :

```bash
open -a TextEdit data/manual_inputs_friendly.txt
```

Vous pouvez ajouter un bloc comme ceci seulement si vous voulez corriger une action :

```text
[MSFT]
roic_5y_avg =
net_margin_stable_or_expanding =
eps_growth_5y =
moat_clear =
eps_growth_estimated_3_5y =
sector_cagr_estimated =
forward_pe_manual =
peg_manual =
fair_value =
current_price_manual =
valuation_vs_5y_avg_ok =
catastrophic_fraud =
catastrophic_moat_lost =
catastrophic_growth_broken =
catastrophic_roic_destroyed =
catastrophic_dangerous_debt =
catastrophic_obsolete_business =
catastrophic_destructive_management =
margin_or_profitability_under_pressure =
forward_pe_growth_acceptable =
management_quality_good =
balance_sheet_strong =
regulatory_risk_high =
geopolitical_risk_high =
single_product_dependency_high =
manual_confidence_level = MEDIUM
notes =
```

Vous pouvez laisser une case vide si vous ne savez pas.

Quand une case est vide, l’agent ne bloque pas. Il essaie d’utiliser une estimation automatique prudente.

Important : une estimation automatique faible est traitée comme un indice, pas comme une preuve.

Par contre, l’agent peut maintenant reconnaître une **preuve automatique forte** quand les données gratuites sont nombreuses, cohérentes et complètes. Le but est de garder un haut degré d’automatisation sans rendre les rapports BNCD/Morningstar obligatoires.

L’agent calcule donc aussi :

- `data_reliability_score`;
- `data_reliability_level`;
- `auto_estimate_dependency`;
- `automation_evidence_level`.

Si une entreprise semble excellente, mais que presque tout repose sur des estimations automatiques, l’agent peut :

- baisser le niveau de confiance;
- plafonner `conviction_score`;
- plafonner `expected_cagr_quality`;
- empêcher le statut `Winner accéléré`;
- réduire le `capital_allocation_score`;
- rediriger plus de capital vers `VFV.TO`.

Une donnée confirmée dans `manual_inputs_friendly.txt` ou dans un rapport BNCD/Morningstar local pèse plus lourd qu’une estimation automatique.

Le scoring fondamental utilise maintenant une courbe de magnitude continue pour les critères quantitatifs principaux. C1 (ROIC), C3 (EPS historique 5y), C5 (EPS estimé 3-5y) et C6 (CAGR secteur) utilisent un scoring magnitude continu: 0.0 sous le seuil, 0.4 au seuil, 0.7 à 1.75× le seuil, 1.0 à 2.5× le seuil (profil-spécifique). C2, C4, C7, C8, C9, C10 restent binaires ou partiels selon leur logique existante. Score maximum total: 10.0. Version des règles: `2026-07-05-continuous-magnitude-scoring-v2`.

L’agent surveille aussi la **fraîcheur des données**.

Cela veut dire qu’il regarde si :

- les prix gratuits ont été récupérés récemment;
- l’analyse utilise un vieux cache local;
- un prix est indisponible;
- un rapport BNCD/Morningstar utilisé est trop ancien.

Si une donnée est périmée, l’agent ne plante pas et ne bloque pas automatiquement la cotisation. Il réduit plutôt la confiance, ajoute une alerte visible dans le rapport et peut demander une validation avant une grosse allocation.

Dans le rapport, regardez :

- `latest_data_freshness.csv`;
- `overall_data_freshness_level`;
- `market_data_freshness_level`;
- `data_freshness_action`.

Mais une entreprise avec `automation_evidence_level = STRONG` peut rester admissible à une allocation raisonnable même sans rapport BNCD, si la thèse, la valorisation, la qualité et le risque respectent les règles.

Le rapport sépare maintenant :

- les **données vraiment manquantes**;
- les **estimations automatiques à valider**.

Une estimation automatique n’est donc pas une donnée absente. C’est une donnée approximative que l’agent a réussi à produire avec les sources gratuites.

L’agent adapte aussi certains seuils selon le type d’entreprise. Une banque, un assureur, une utility, une minière ou un pipeline n’est pas jugé exactement comme un compounder logiciel. Par contre, les secteurs défensifs, régulés ou cycliques restent plafonnés dans la qualité CAGR afin d’éviter de les traiter comme des titres haut CAGR automatiques.

L’agent essaie aussi d’utiliser un benchmark sectoriel pertinent au lieu de comparer trop souvent une entreprise à `VFV.TO` par défaut. Par exemple, une utility peut être comparée à `XLU`, un assureur à `KIE`, une foncière à `VNQ`, une aurifère à `GDX`, une entreprise uranium à `URA`, un gestionnaire d’actifs à `KCE`, et une entreprise de semi-conducteurs à `SOXX`.

L’agent ajoute aussi un garde-fou contre les bulles, les thèmes trop populaires et les cycles favorables déjà avancés. Il ne vend pas automatiquement à cause de ce signal. Il réduit plutôt le montant proposé quand une entreprise combine plusieurs éléments comme :

- industrie très cyclique;
- forte performance récente;
- prix proche du sommet 12 mois;
- valorisation déjà exigeante;
- ETF sectoriel très fort;
- portefeuille déjà très exposé au même thème.

Dans le rapport, regardez `cycle_bubble_risk_level`. Si le niveau est `HIGH` ou `EXTREME`, l’entreprise peut rester excellente, mais l’agent limite l’allocation pour éviter de payer trop cher une tendance.

L’agent ajoute maintenant aussi une couche **régime de marché**.

Elle regarde des ETF et indices gratuits comme `SPY`, `QQQ`, `SOXX`, `XLK`, `IWM`, `TLT`, `^VIX`, `^TNX`, `XLP`, `XLU` et `XLV`.
Elle sert à détecter un climat général comme `RISK_ON`, `NEUTRAL`, `RISK_OFF`, `BUBBLE_RISK`, `RATE_STRESS` ou `RECESSION_RISK`.

Important : cette couche ne fait pas de market timing.
Elle ne vend rien, ne garde pas de cash volontairement et ne remplace pas l’analyse fondamentale.
Elle influence seulement le sizing avec un impact plafonné.
En mode `high-cagr`, son effet est volontairement léger afin de ne pas tuer le potentiel long terme.
Dans les modes plus prudents, son effet est un peu plus fort.

Dans le rapport, regardez :

- `latest_market_regime_report.csv`;
- `latest_market_regime_allocations.csv`;
- `market_regime_status`;
- `market_regime_allocation_adjustment`.

L’agent ajoute aussi une couche **durabilité 15-30 ans**.

Elle ne prédit pas le rendement futur exact. Elle sert plutôt à distinguer :

- `VERY_DURABLE_COMPOUNDER` : entreprise qui semble très durable pour un horizon très long;
- `DURABLE_BUT_CYCLICAL` : entreprise de qualité, mais plus dépendante d’un cycle, d’un thème ou d’un secteur;
- `HIGH_GROWTH_BUT_FRAGILE` : fort potentiel, mais valorisation, cycle ou preuves encore fragiles;
- `SPECULATIVE_OR_UNPROVEN` : durabilité long terme insuffisamment prouvée.

Dans le rapport, regardez `long_term_durability_status` et `latest_long_term_durability_report.csv`.

L’agent utilise aussi une **stabilité mensuelle modérée**.

Cela veut dire :

- si un titre recevait une allocation le mois précédent et qu’il reste solide, il reçoit un petit bonus anti-bruit;
- si un titre se détériore, ce bonus disparaît et peut devenir un petit malus;
- si un nouveau titre devient clairement meilleur, il peut quand même passer devant;
- si un titre devient inadmissible, la stabilité ne le protège pas.

Le but est d’éviter une allocation qui change trop à cause d’un simple mouvement de marché, sans rester coincé dans les mêmes titres. Dans le rapport, regardez `allocation_stability_status` et `allocation_stability_adjustment`.

L’agent ajoute aussi une **protection des winners** si vous remplissez `shares`, `average_cost` et `average_cost_currency` dans `portfolio.csv`.

Cette couche sert à :

- laisser courir un winner quand la thèse reste intacte;
- éviter de vendre seulement parce que le prix baisse normalement;
- détecter un ancien winner qui recule fortement depuis son sommet personnel;
- déclencher une surveillance ou une revue de vente partielle si la baisse arrive avec une détérioration des fondamentaux.

Dans le rapport, regardez :

- `winner_protection_status`;
- `winner_protection_action`;
- `unrealized_gain_percent`;
- `drawdown_from_personal_high`.

Pour les colonnes vrai/faux, vous pouvez écrire :

```text
TRUE
FALSE
yes
no
oui
non
1
0
```

Pour `manual_confidence_level`, vous pouvez écrire :

```text
HIGH
MEDIUM
LOW
```

Si vous ne savez pas, mettez :

```text
MEDIUM
```

Les champs qui commencent par `catastrophic_` doivent rester vides ou `FALSE`, sauf si un vrai problème majeur est confirmé.

Le fichier manuel n’est pas obligatoire.

Pour savoir où trouver les informations, ouvrez aussi le guide :

```text
data/guide_de_recherche_des_informations_pour_manual_inputs_friendly.md
```

### Fichier de contrôle qualité : proxy_calibration.csv

Ce fichier sert à vérifier si les estimations automatiques de l’agent sont bonnes.

Vous pouvez l’utiliser quand vous avez de vraies données fiables pour une entreprise, par exemple avec MSFT, MA et AAPL.

Ce fichier n’est pas fait pour être rempli chaque mois.

Le fichier source est `data/proxy_calibration.csv` (colonnes avec suffixe `_true`).
Pour appliquer les données confirmées au pipeline de scoring:

```bash
python3 main.py sync-manual-inputs
```

Cette commande traduit le CSV vers `data/manual_inputs_friendly.txt` (format INI)
avec gating de staleness automatique. Ne pas éditer `manual_inputs_friendly.txt`
directement — il est écrasé à chaque sync.

Migration unique : si un ancien fichier généré ne contient pas encore les métadonnées
de provenance, la synchronisation vérifie d'abord que chaque valeur correspond sans
ambiguïté à `proxy_calibration.csv`. Au moindre écart ou champ non conciliable, elle
échoue sans modifier le fichier ni le journal. Conservez les valeurs humaines à part,
réconciliez ou retirez les champs signalés, lancez une fois la synchronisation pour
ajouter les métadonnées, puis réappliquez les valeurs humaines voulues.

Il sert plutôt à faire une calibration ponctuelle :

1. vous ajoutez plusieurs exemples fiables;
2. vous lancez une analyse;
3. l’agent compare les vraies données avec ses proxies;
4. on regarde les champs où les écarts sont répétés;
5. si les preuves sont suffisantes, les formules dans le code peuvent être recalibrées;
6. ensuite, vous pouvez vider les vraies valeurs du fichier.

Pour l’ouvrir sur Mac :

```bash
open -a TextEdit data/proxy_calibration.csv
```

Le fichier est fait pour être lisible dans TextEdit :

```csv
ticker,company_name,roic_5y_avg_true,eps_growth_5y_true,moat_clear_true,fair_value_true,source,source_date,confidence,notes
MSFT,Microsoft Corporation,,,,,Morningstar,2026-05-01,HIGH,
MA,Mastercard Incorporated,,,,,Morningstar,2026-05-01,HIGH,
```

Le principe est simple :

- une ligne = une compagnie;
- une colonne qui finit par `_true` = vraie donnée que vous avez trouvée;
- `source` : exemple BNCD, Morningstar, rapport annuel;
- `source_date` : date de la donnée si disponible;
- `notes` : commentaire optionnel.

Pour ajouter plus de candidats, ajoutez simplement une nouvelle ligne :

```csv
AVGO,Broadcom Inc.,,,,,Morningstar,2026-05-01,HIGH,
CSU.TO,Constellation Software Inc.,,,,,Morningstar,2026-05-01,HIGH,
```

Un guide des colonnes est disponible ici :

```text
data/proxy_calibration_field_guide.csv
```

Un guide rapide plus facile à lire est disponible ici :

```text
data/guide_rapide_proxy_calibration.md
```

Pour les pourcentages, écrivez un nombre simple :

```text
18
```

Cela veut dire 18 %, pas 0.18.

Pour les vrai/faux, écrivez :

```text
TRUE
FALSE
```

Vous pouvez laisser une case vide si vous ne trouvez pas la donnée. Si vous écrivez `X`, l’agent le traite aussi comme une donnée manquante.

Après la prochaine analyse, l’agent crée :

```text
reports/latest_proxy_calibration.csv
reports/latest_proxy_calibration_summary.csv
reports/latest_proxy_calibration_history.csv
reports/latest_proxy_bias_report.csv
```

Le fichier détaillé compare :

- la vraie donnée que vous avez fournie;
- le proxy automatique utilisé par l’agent;
- l’écart entre les deux;
- une conclusion comme `MATCH`, `CLOSE`, `REVIEW_PROXY` ou `PROXY_MISSING`.

Le fichier résumé indique, pour chaque donnée :

- combien d’exemples ont été fournis;
- combien sont utilisables;
- si le proxy semble acceptable;
- si le proxy semble trop haut ou trop bas;
- si la donnée mérite une recalibration.

Le fichier d’historique conserve les exemples fiables dans :

```text
data/proxy_calibration_history.csv
```

Il sert de mémoire durable pour les futures améliorations de proxies. Si vous relancez plusieurs fois la même analyse avec la même vraie donnée et la même source, l’agent met à jour la ligne existante au lieu de compter artificiellement le même exemple plusieurs fois.

Le fichier `reports/latest_proxy_bias_report.csv` est le diagnostic anti-surcorrection.

Il regarde l’historique durable et répond à une question simple :

```text
Est-ce qu’un proxy semble systématiquement trop haut ou trop bas?
```

Pour éviter une mauvaise correction, l’agent exige plusieurs preuves cohérentes :

- au moins 5 exemples utilisables;
- au moins 3 tickers différents;
- des écarts dans la même direction;
- un écart moyen assez important;
- une volatilité d’erreur raisonnable;
- aucune dépendance aux données de confiance LOW.

Important : ce fichier ne change pas les formules. Il sert seulement à dire si une formule mérite une revue. Les champs qualitatifs comme `moat_clear` ou `balance_sheet_strong` ne reçoivent jamais de facteur multiplicatif automatique.

Le fichier `config/proxy_corrections.yaml` est la couche de correction validée.

Par défaut, il est désactivé :

```yaml
enabled: false
corrections:
```

Même si une correction est écrite dans ce fichier, elle est ignorée si elle ne respecte pas les garde-fous :

- fichier explicitement activé avec `enabled: true`;
- champ numérique seulement;
- `status: ACTIVE`;
- facteur entre 0.75 et 1.25;
- au moins 5 exemples;
- confiance `HIGH`, ou `MEDIUM` avec au moins 8 exemples;
- aucune correction multiplicative sur les champs vrai/faux.

Quand une correction validée est active, elle est appliquée au proxy automatique avant le scoring. Le modèle laisse alors une trace dans `latest_scores.csv`, dans les colonnes `proxy_correction_status`, `proxy_correction_fields` et `proxy_corrections_applied`.

Important : l’agent ne change pas une formule de proxy directement. Il peut proposer une correction multiplicative très limitée, mais `apply-safe-tuning` reste fail-closed en `PROPOSAL_ONLY`. Le but est d'observer un biais répété sans surcorriger le modèle sur un petit échantillon.

La commande `improvement-audit` peut maintenant transformer un signal très solide du fichier `latest_proxy_bias_report.csv` en suggestion de correction proxy :

```text
proxy_correction:roic_5y_avg
```

Une éventuelle politique future ne pourrait l'appliquer que si toutes les conditions suivantes étaient respectées; la politique actuelle bloque avant toute écriture :

- l’audit d’amélioration a été lancé aujourd’hui;
- le mode est le même;
- la santé des sources ne bloque pas l’auto-tuning;
- la barrière anti-overfitting passe;
- le walk-forward ne montre pas de faiblesse hors-échantillon nette quand il y a assez d’historique;
- la correction est `SAFE`;
- le facteur reste entre 0.75 et 1.25;
- l’évidence est suffisante.

Quand une correction est appliquée, l’agent :

1. crée une sauvegarde avant modification;
2. active ou met à jour `config/proxy_corrections.yaml`;
3. inscrit l’action dans :

```text
data/proxy_correction_history.csv
```

À chaque analyse, l’agent crée aussi :

```text
reports/latest_proxy_correction_audit.csv
```

Ce fichier vérifie les corrections déjà actives :

- `ACTIVE_OK` : la correction reste raisonnable;
- `ACTIVE_NEEDS_MORE_FRESH_EVIDENCE` : elle n’est pas contredite, mais il faut plus de nouvelles preuves avant de l’élargir;
- `REVIEW_FACTOR_NEAR_LIMIT` : le facteur est près de la limite maximale;
- `REVIEW_STALE_CORRECTION` : la correction est ancienne;
- `REVIEW_NO_LONGER_CONFIRMED` : les nouvelles données ne confirment plus clairement le biais;
- `REVIEW_NOISY_EVIDENCE` ou `REVIEW_CONFLICTING_EVIDENCE` : les nouvelles données sont bruyantes ou opposées.

Ces alertes ne changent pas l’allocation toutes seules. Elles servent à éviter qu’une ancienne correction devienne une source de surconfiance.

Cette couche est volontairement prudente : elle corrige seulement un biais répété et cohérent, elle ne réécrit pas les formules du modèle.

Après une recalibration confirmée, vous pouvez vider les vraies valeurs avec :

```bash
python3 main.py clear-proxy-calibration
```

Sur Windows :

```bash
python main.py clear-proxy-calibration
```

Cette commande garde la structure du fichier, mais efface `true_value`, `source`, `source_date` et `notes`.
Elle n’efface pas `data/proxy_calibration_history.csv`.

### Ancien fichier optionnel : account_locations.csv

Vous n’avez normalement plus besoin de remplir ce fichier.

Le type de compte se met directement dans `portfolio.csv`, dans la colonne `account_type`.

Ce fichier est seulement gardé pour compatibilité avec les anciennes versions. Si `account_type` est vide dans `portfolio.csv`, l’agent peut encore utiliser `account_locations.csv` comme secours.

Exemple :

```csv
ticker,account_type,current_value
MSFT,TFSA,1200
AVGO,TFSA,900
VFV.TO,FHSA,500
BAM,NON_REGISTERED,700
```

Les types de comptes acceptés sont :

```text
TFSA
TFSA1
TFSA2
FHSA
RRSP
NON_REGISTERED
```

### Ancien fichier optionnel : watchlist.csv

Vous pouvez maintenant ignorer ce fichier.

Pour garder le système simple, utilisez plutôt `data/market_universe.csv` comme grande liste unique de surveillance externe.

Si vous laissez `watchlist.csv` vide, c’est normal.

### Fichier principal de surveillance externe : market_universe.csv

Ce fichier sert à donner à l’agent votre grande liste unique d’actions externes à surveiller.

Dans le rapport, cette partie s’appelle maintenant **Surveillance externe / Market Universe**. L’ancienne section watchlist est masquée quand `watchlist.csv` est vide.

Exemple :

```csv
ticker,company_name
NVDA,NVIDIA Corporation
COST,Costco Wholesale Corporation
```

Vous n’avez pas besoin d’écrire le secteur, la région ou la devise. L’agent peut continuer sans ces informations.

Si vous ne connaissez pas encore le nom exact de la compagnie, écrivez :

```csv
XYZ,...
```

Si vous ne créez pas ce fichier, l’agent utilise une liste par défaut.

Le scanner ne couvre pas tout le marché. Il analyse seulement la liste fournie ou la liste par défaut.

### Dossier optionnel : rapports BNCD / Morningstar

Si vous téléchargez des analyses BNCD ou Morningstar en PDF, vous pouvez les déposer ici :

```text
data/research_reports/bncd_morningstar
```

Nom recommandé :

```text
CSU.TO_2026-04-15_BNCD_Morningstar.pdf
WSP.TO_2026-04-15_BNCD_Morningstar.pdf
BAM_2026-04-15_BNCD_Morningstar.pdf
```

L’agent essaie d’extraire certains champs utiles quand ils sont présents :

- juste valeur;
- moat;
- croissance estimée;
- bilan;
- risques;
- pression sur les marges;
- valorisation.

Ces rapports servent à combler des données manquantes. Ils ne remplacent pas votre validation manuelle.

L’agent tient maintenant compte de la date des rapports :

- rapport de moins de 6 mois : utilisé normalement;
- rapport de 6 à 12 mois : utilisé avec une légère prudence;
- rapport de plus de 12 mois : utilisé avec une pénalité importante;
- rapport sans date détectée : validation fraîche recommandée avant grosse allocation.

Pour vérifier que l’agent voit bien vos PDF et qu’il peut les lire, lancez :

```bash
python3 main.py research-status
```

Sur Windows :

```bash
python main.py research-status
```

Cette commande crée :

```text
reports/latest_research_status.csv
```

Ce fichier indique, pour chaque rapport déposé, le ticker détecté, si le fichier est lisible, les champs extraits et le problème à corriger s’il y en a un.

Pour savoir quels rapports chercher en priorité, lancez :

```bash
python3 main.py research-needed
```

Sur Windows :

```bash
python main.py research-needed
```

Le résultat complet est créé ici :

```text
reports/latest_research_needed.csv
```

Cette commande couvre le portefeuille actuel et le `market_universe.csv`. Si une action externe souffre aussi de données manquantes, elle apparaîtra dans cette liste.

Cette commande peut être lancée **avant** l’analyse complète. Elle lit vos fichiers actuels, vérifie les rapports déjà déposés, puis recommande seulement les rapports qui pourraient vraiment combler des données importantes.

Si vous ajoutez un rapport lisible pour un titre recommandé, puis relancez :

```bash
python3 main.py research-needed
```

ce titre ne devrait normalement plus apparaître, sauf si le fichier ajouté ne contient aucun champ utile détectable.

## 8. Vérifier que les fichiers sont corrects

Après avoir rempli les fichiers, lancez :

```bash
python3 main.py validate-inputs
```

Sur Windows, utilisez :

```bash
python main.py validate-inputs
```

Si tout va bien, vous verrez :

```text
Validation réussie.
```

Si l’agent affiche une erreur, lisez le nom du fichier et la ligne indiquée. Corrigez cette ligne, puis relancez la vérification.

## 9. Lancer l’analyse

Pour analyser 1000 $ de nouveau capital avec le profil principal haut CAGR, lancez :

```bash
python3 main.py analyze --capital 1000 --mode high-cagr --refresh-market-data
```

Sur Windows, utilisez :

```bash
python main.py analyze --capital 1000 --mode high-cagr --refresh-market-data
```

Vous pouvez remplacer `1000` par le montant que vous voulez analyser.

Exemple pour 500 $ :

```bash
python3 main.py analyze --capital 500 --mode high-cagr --refresh-market-data
```

## 10. Choisir le mode

Il existe quatre modes. Ils vont du plus prudent au plus axé croissance.

### Mode très prudent

```bash
python3 main.py analyze --capital 1000 --mode balanced
```

Ce mode est le plus conservateur. Il est pensé pour une personne qui veut surtout protéger son patrimoine, par exemple une personne retraitée ou très prudente.

Il ne cherche pas la stagnation. Il garde une exposition de croissance suffisante pour viser une progression du patrimoine au-dessus de l’inflation, surtout avec `VFV.TO`, des ETF conservateurs diversifiés et, parfois, une petite allocation vers une action exceptionnelle.

Il met la majorité de la cotisation vers `VFV.TO` et vers des ETF défensifs autorisés avant de considérer les actions individuelles. Dans cette poche défensive, l’agent favorise maintenant les ETF conservateurs ou équilibrés plutôt qu’une poche trop lourde en cash pur. Il refuse les titres en surveillance, les opportunités de baisse plus spéculatives, les titres cycliques, les titres liés à une tendance chaude et les actions qui ne sont pas clairement meilleures que `VFV.TO`.

Dans ce mode, les actions individuelles peuvent encore recevoir une petite allocation, mais seulement si elles passent des filtres beaucoup plus stricts: excellente qualité, forte conviction, thèse intacte, moat durable et très faible risque de cycle/bulle.

Il peut aussi utiliser un titre de `market_universe.csv` ou de la découverte externe sans promotion manuelle, mais seulement comme petite nouvelle position très filtrée. Le mode `balanced` reste conçu pour la protection du patrimoine.

Pour les ETF/FNB externes, il favorise surtout les ETF conservateurs, équilibrés, obligataires, faible volatilité ou très diversifiés. Il évite les ETF spéculatifs, crypto, levier, options, ou trop axés tendance.

### Mode prudent-professionnel

```bash
python3 main.py analyze --capital 1000 --mode family-office
```

Ce mode est plus axé développement que `balanced`, mais il reste prudent. Il ajoute l’analyse du risque global, les stress tests, la fiscalité approximative, la concentration, la comparaison à `VFV.TO` et une réserve modérée d’ETF défensifs.

Il est utile pour une gestion complète qui cherche encore de la croissance, mais sans laisser une seule industrie, une seule tendance ou quelques titres dominer toute la cotisation. Les allocations par action y sont plus plafonnées qu’en `high-cagr`.

Contrairement au mode `high-cagr`, il peut considérer directement une action externe de `market_universe.csv` ou de la découverte externe si elle est comparable aux meilleurs titres du portefeuille, clairement meilleure que `VFV.TO`, bien couverte par les données et non trop chère.

Il peut aussi considérer un ETF/FNB externe s’il améliore réellement la diversification, la gestion du risque ou l’équilibre croissance/protection. Les ETF trop concentrés sur une tendance déjà dominante sont pénalisés.

### Mode haut CAGR avec garde-fous

```bash
python3 main.py analyze --capital 1000 --mode rational-aggressive
```

Ce mode cherche plus de croissance, mais refuse quand même les thèses faibles, les risques trop élevés ou les valorisations trop extrêmes.

Il peut utiliser une très petite couche d’ETF défensifs en dernier recours. Cette couche est plafonnée et ne doit pas remplacer les entreprises de qualité. Il est plus offensif que `family-office`, mais ses plafonds par titre, ses budgets de cycle/bulle et ses règles de diversification restent nettement plus prudents que `high-cagr`.

Il peut aussi considérer directement les meilleures actions externes sans promotion manuelle, mais seulement si elles passent les mêmes garde-fous: thèse intacte, liquidation GREEN, données fiables, avantage clair face à `VFV.TO`, valorisation non extrême et plafond de nouvelle position.

Pour les ETF/FNB externes, il peut accepter des ETF plus orientés croissance, par exemple marché large, Nasdaq 100 ou technologie, mais seulement avec plafonds et pénalités si le portefeuille est déjà très exposé à tech/IA/semi-conducteurs.

### Mode haut CAGR plus audacieux

```bash
python3 main.py analyze --capital 1000 --mode high-cagr
```

Ce mode accepte modérément plus de volatilité et un peu plus de concentration.

Il réduit la portion obligatoire vers `VFV.TO` quand les meilleures positions ont une qualité élevée.

Il limite aussi les gros blocs quand le moteur détecte un risque de bulle, de thème trop chaud ou de cycle industriel déjà très favorable.

Il ne renforce quand même pas une action en zone jaune, orange ou rouge.

Il ne renforce pas non plus une action dont la thèse n’est pas intacte.

Ce mode garde le fonctionnement original: les actions externes ne reçoivent pas automatiquement d’allocation. Si une action du scanner vous intéresse pour `high-cagr`, ajoutez-la au `portfolio.csv` avec une valeur de 0 $ ou une petite position réelle pour qu’elle soit considérée comme candidate core.

Même logique pour les ETF/FNB externes: en `high-cagr`, ils restent informatifs à moins d’être déjà dans votre portefeuille ou traités par les règles spécifiques existantes comme `VFV.TO`.

Pour le profil haut CAGR long terme utilisé dans ce projet, la commande habituelle est :

```bash
python3 main.py analyze --capital 1000 --mode high-cagr --refresh-market-data
```

## 11. Lire le rapport

Après l’analyse, ouvrez le dossier :

```text
reports
```

Les fichiers les plus utiles sont :

```text
latest_report.html
latest_report.md
latest_allocations.csv
latest_sell_signals.csv
latest_market_candidates.csv
latest_discovery_ideas.csv
latest_discovery_maintenance.csv
latest_promotion_candidates.csv
latest_trend_report.csv
latest_winner_protection_report.csv
latest_cycle_bubble_report.csv
latest_long_term_durability_report.csv
latest_portfolio_changes.csv
latest_portfolio_change_history.csv
latest_portfolio_change_summary.csv
latest_portfolio_transactions.csv
latest_portfolio_transaction_summary.csv
latest_portfolio_inferred_transactions.csv
latest_data_freshness.csv
latest_source_health.csv
latest_source_conflicts.csv
latest_ticker_memory.csv
latest_anomaly_report.csv
latest_cache_health.csv
latest_proxy_calibration.csv
latest_proxy_calibration_summary.csv
latest_proxy_calibration_history.csv
latest_proxy_bias_report.csv
latest_proxy_correction_audit.csv
reports/universe_snapshots/<run_id>.json
data/proxy_calibration_sync_log.json
latest_walk_forward_inventory.csv
latest_walk_forward_coverage.csv
latest_walk_forward_inventory.html
latest_walk_forward_report.html
latest_walk_forward_summary.csv
latest_walk_forward_periods.csv
latest_walk_forward_period_allocations.csv
latest_walk_forward_regime_summary.csv
data/proxy_correction_history.csv
latest_run_log.csv
latest_research_needed.csv
latest_ticker_issues.csv
latest_scores.csv
latest_risk_report.csv
latest_tax_location_report.csv
latest_data_gaps.csv
latest_auto_estimates.csv
latest_proxy_calibration.csv
latest_proxy_calibration_summary.csv
```

`reports/universe_snapshots/<run_id>.json`
Snapshot per-run de l'univers complet scoré (261 tickers).
Prérequis pour la validation walk-forward out-of-sample.
Écrit après chaque analyze réussi. Idempotent par run_id.

`data/proxy_calibration_sync_log.json`
Journal du dernier sync-manual-inputs: sections écrites, champs actuels,
périmés ou sans `source_date`, et politique de fraîcheur par champ. Lu par le
rapport compact pour générer l'alerte de calibration.

Le plus simple à lire est :

```text
latest_report.html
```

Ouvrez-le avec votre navigateur Internet.

### Fichier spécial : latest_ticker_issues.csv

Ce fichier sert à repérer les tickers à vérifier.

Il est très utile si :

- une action affiche `MANUAL_REQUIRED`;
- l’agent n’a pas trouvé de données de marché;
- le nom de compagnie trouvé ne semble pas correspondre au nom que vous vouliez.

Dans le rapport, les tickers concernés ont une étoile `*`.

Petite nuance : une petite donnée manquante normale ne met pas toujours une étoile. Un simple alias apparaît entre parenthèses, par exemple `SBGSY (SCHN)`. Les petites lacunes restent dans `latest_data_gaps.csv`; l’étoile sert surtout à attirer votre attention sur les cas importants.

Si le fichier dit que le ticker est bon mais que `yfinance` n’a pas trouvé les données, relancez parfois avec :

```bash
python3 main.py analyze --capital 500 --mode high-cagr --refresh-market-data
```

Sur Windows, utilisez `python` au lieu de `python3`.

### Fichier spécial : latest_ticker_memory.csv

Ce fichier est la mémoire locale des tickers.

Il répond à la question :

```text
Qu’est-ce que l’agent a déjà compris sur ce ticker?
```

Il peut contenir :

- le ticker résolu;
- le nom de compagnie trouvé;
- le secteur;
- la région;
- la devise;
- le type d’actif;
- le niveau de couverture gratuite;
- l’action suggérée si le ticker semble mal couvert.

Les statuts importants sont :

- `ACTIVE` : rien de spécial à faire;
- `FALLBACK_AVAILABLE` : l’agent a une mémoire de secours si une source future est incomplète;
- `LOW_FREE_COVERAGE` : le ticker semble valide, mais les données gratuites couvrent mal les fondamentaux;
- `NEEDS_TICKER_REVIEW` : le ticker doit être vérifié avant une grosse décision;
- `CLASSIFICATION_CHANGED_REVIEW` : la classification a changé par rapport à la mémoire précédente.

Ne modifiez normalement pas ce fichier. Si vous pensez que la mémoire est mauvaise, corrigez plutôt le ticker dans `portfolio.csv`, `market_universe.csv` ou `config/ticker_aliases.yaml`.

### Fichier spécial : latest_source_conflicts.csv

Ce fichier rend visibles les contradictions entre certaines sources, par exemple Yahoo Finance, SEC EDGAR pour les sociétés américaines, et StockAnalysis pour certains titres canadiens.

Il répond à la question :

```text
Est-ce que deux sources donnent des chiffres très différents pour la même entreprise?
```

Les statuts importants sont :

- `WATCH` : petite contradiction à surveiller;
- `REVIEW` : contradiction assez importante pour valider si le titre devient important;
- `HIGH_REVIEW` : contradiction prioritaire, surtout si le titre est dans le portefeuille ou dans la recommandation.

Ce fichier ne vend rien et ne bloque pas automatiquement une allocation. Il sert surtout à dire : “avant une grosse décision, vérifiez si la différence vient d’une période différente, d’un calcul différent, d’une unité différente ou d’une vraie donnée problématique”.

Dans le rapport compact, l’agent montre seulement les contradictions prioritaires. Le CSV garde plus de détails pour audit.

### Fichier spécial : latest_run_log.csv

Ce fichier est le journal simple de la dernière commande importante.

Il répond à la question :

```text
Est-ce que quelque chose de technique ou de méthodologique mérite mon attention dans cette analyse?
```

Il peut signaler :

- un cache de marché ancien ou fragile;
- des données importantes manquantes;
- une contradiction entre sources;
- une anomalie post-analyse;
- un avertissement de règle d’allocation;
- un ticker à vérifier.

Le fichier historique est gardé ici :

```text
data/run_log_history.csv
```

Vous n’avez rien à remplir. Si le rapport compact dit que le journal contient des avertissements, ouvrez simplement `reports/latest_run_log.csv` ou lisez la section “Journal d’exécution” du rapport.

### Fichier spécial : latest_discovery_ideas.csv

Ce fichier répond à la question :

```text
Y a-t-il une nouvelle entreprise, pas déjà dans mon portefeuille ni dans market_universe.csv, qui mérite d’être ajoutée à ma liste de surveillance?
```

Le statut le plus important est :

```text
ADD_TO_MARKET_UNIVERSE_REVIEW
```

Cela ne veut pas dire “acheter”.

Cela veut seulement dire :

- l’action semble très alignée avec votre profil selon les données gratuites;
- elle n’est pas déjà dans votre portefeuille ou dans `data/market_universe.csv`;
- vous pouvez lire la thèse manuellement;
- si elle vous intéresse vraiment, vous pouvez ajouter son ticker et son nom dans `data/market_universe.csv`.

Le radar utilise un cache local :

```text
data/discovery_universe_cache.csv
```

Cela évite de dépendre d’Internet à chaque analyse.

### Fichier spécial : latest_discovery_maintenance.csv

Ce fichier répond à la question :

```text
Est-ce que le radar externe doit garder, mettre en quarantaine ou écarter certains titres?
```

Les statuts principaux sont :

- `ACTIVE_TOP_IDEA` : idée très forte à lire manuellement;
- `KEEP_WATCHING` : titre intéressant, mais pas parfait aujourd’hui;
- `QUARANTINE` : données faibles, nouvelles inquiétantes, prix indisponible ou chute extrême;
- `REMOVE_CANDIDATE` : trop petit, prix trop faible, thèse cassée ou risque mécanique trop élevé;
- `IGNORE_FOR_NOW` : ne mérite pas d’attention prioritaire.

### Fichier spécial : latest_promotion_candidates.csv

Ce fichier répond à la question :

```text
Est-ce qu’une action du scanner mérite d’être ajoutée manuellement au portefeuille?
```

Ce fichier est volontairement très strict. Si aucune action externe ne mérite vraiment une promotion, il affiche :

```text
AUCUNE_PROMOTION_FONDEE
```

Dans ce cas, il ne faut rien ajouter au portefeuille. En mode `high-cagr`, les titres externes restent simplement dans `market_universe.csv` pour continuer la surveillance. Dans les autres modes, ils ne recevront une allocation que s’ils passent séparément les filtres stricts du moteur d’allocation.

Le statut le plus important est :

```text
PROMOTE_TO_CORE_REVIEW
```

Cela ne veut pas dire “acheter automatiquement”.

Cela veut dire :

- l’action externe semble assez forte pour une analyse manuelle sérieuse;
- elle reste hors allocation automatique;
- si vous êtes d’accord avec la thèse, vous pouvez l’ajouter vous-même dans `data/portfolio.csv` avec `shares=0`;
- si vous finissez par acheter le titre, remplissez son `account_type` directement dans `data/portfolio.csv`;
- ensuite, l’agent pourra considérer cette nouvelle position à 0 $ pour les prochaines cotisations.

## 12. Comprendre les résultats

Dans le rapport, regardez surtout :

- **Allocation recommandée** : où l’agent propose de mettre le nouveau capital;
- **Tableau des scores** : score, conviction, thèse, risque de vente;
- **Signaux de vente** : quelles positions sont à conserver, surveiller ou vérifier manuellement avant une réduction;
- **Surveillance externe / Market Universe** : candidates externes à analyser manuellement;
- **Découverte externe** : nouvelles idées potentielles à ajouter au `market_universe.csv`;
- **Données à valider manuellement** : ce que vous devez vérifier vous-même;
- **Historique et tendances** : ce qui s’améliore ou se détériore depuis les analyses précédentes;
- **Stress tests** : ce qui pourrait arriver dans des scénarios difficiles;
- **Fiscalité et localisation** : commentaires approximatifs sur les comptes;
- **Santé des sources** : si les sources gratuites ou locales semblent fiables;
- **Contradictions entre sources** : les écarts importants à valider avant une grosse décision;
- **Anomalies post-analyse** : les changements inhabituels à lire avant d’exécuter ou avant de lancer un audit;
- **Mémoire ticker** : les tickers nouveaux, mal classés ou mal couverts à surveiller.

### Comment lire les signaux de vente

L’agent sépare maintenant deux types de signaux :

- `technical_or_valuation_signals` : prix sous SMA 200, sous-performance, PEG élevé, ralentissement ou volatilité;
- `confirmed_fundamental_sell_signals` : marge détériorée, croissance cassée, moat affaibli, bilan affaibli ou autre problème fondamental confirmé.

Un signal technique ou de valorisation peut mener à :

```text
WATCH / DO_NOT_ADD
```

Il ne suffit pas pour vendre.

Une réduction comme `REVIEW_TRIM_25` ou `REVIEW_TRIM_50` exige maintenant :

- au moins 2 signaux fondamentaux confirmés;
- ou 1 signal fondamental confirmé + une détérioration répétée dans l’historique.

Si les signaux viennent surtout de données automatiques ou incertaines, l’agent demande une validation manuelle au lieu de recommander une vente.

## 13. Mémoire des anciennes analyses

L’agent garde une mémoire locale dans le dossier :

```text
reports/history
```

À chaque analyse, il compare les nouveaux résultats avec les anciennes analyses.

Pour éviter un faux signal si vous lancez plusieurs analyses la même journée, l’agent ne se base pas seulement sur la toute dernière analyse. Il utilise plutôt plusieurs dates distinctes précédentes et ignore les analyses de la journée courante comme référence historique.

Cela l’aide à repérer :

- une action qui se détériore;
- une action qui se solidifie;
- une action qui devient plus intéressante;
- une action dont la qualité des données s’améliore ou empire.

Ne supprimez pas le dossier `reports/history` si vous voulez garder cette mémoire.

## 14. Exemple simple

Vous lancez :

```bash
python3 main.py analyze --capital 500 --mode high-cagr
```

L’agent pourrait répondre :

```text
VFV.TO : 50 $
AVGO : 250 $
AAPL : 200 $
```

Cela veut dire :

- une partie va dans `VFV.TO` comme filet de sécurité;
- le reste va seulement vers les positions actuelles admissibles;
- chaque montant est choisi selon la qualité, la thèse, la comparaison à `VFV.TO` et le risque de concentration après achat;
- aucune action en zone jaune, orange ou rouge ne reçoit une nouvelle cotisation.

## 15. Comment l’allocation mensuelle est optimisée

L’agent ne coupe plus simplement la cotisation en blocs fixes.

Il simule plutôt l’effet de la nouvelle cotisation sur le portefeuille :

- il garde d’abord la portion obligatoire en `VFV.TO`;
- il regarde seulement les positions actuelles admissibles, plus `VFV.TO`;
- il refuse les actions dont la thèse n’est pas intacte;
- il refuse les actions en zone jaune, orange ou rouge;
- il évite de renforcer une position déjà trop lourde;
- il favorise les actions de grande qualité qui sont encore sous leur poids cible;
- il redirige automatiquement vers `VFV.TO` si aucun achat ne respecte les règles.

En mode `high-cagr`, l’agent accepte un peu plus de concentration et de volatilité, mais seulement si la qualité, la thèse, la conviction et la valorisation restent solides.

Important : la couche `Defensive ETF Fallback` est désactivée en mode `high-cagr`. Dans ce mode, `VFV.TO` reste le seul filet automatique. Les ETF défensifs existent surtout pour les modes plus prudents.

Le fichier de configuration des ETF défensifs est :

```text
config/defensive_etfs.yaml
```

Ce fichier contient maintenant deux listes :

- `defensive_etfs` : ETF défensifs principaux autorisés;
- `auto_universe` : univers automatique d’ETF prudents que l’agent peut comparer sans promotion manuelle.

Dans les modes `balanced`, `family-office` et très légèrement `rational-aggressive`, l’agent choisit automatiquement les meilleurs ETF défensifs admissibles par catégorie. Vous n’avez pas besoin de les promouvoir dans le portfolio. Il évite de retenir trop d’ETF semblables, par exemple plusieurs ETF obligataires court terme en même temps.

En mode `balanced` et `family-office`, si un ETF défensif pré-approuvé manque temporairement de prix gratuit dans le cache, l’agent peut quand même l’utiliser comme stabilisateur limité. Le rapport l’indique clairement et demande une validation manuelle avant achat.

En mode `high-cagr`, ce sélecteur reste désactivé.

Le rapport détaillé produit aussi :

```text
reports/latest_defensive_etf_fallback.csv
```

## 16. Comment l’allocation VFV est calculée

L’agent calcule une moyenne des scores du portefeuille pour savoir combien mettre automatiquement dans `VFV.TO`.

Cette moyenne est maintenant :

- pondérée selon la taille réelle des positions;
- calculée seulement sur les positions que vous détenez dans `portfolio.csv`;
- calculée hors `VFV.TO`;
- non influencée par les très petites positions satellites sous 2 % du portefeuille.

Exemple : une petite position spéculative de 55 $ ne pèse plus autant qu’une grosse position de 2 000 $.

### Benchmark sectoriel et pertinence

L’agent compare toujours les actions à `VFV.TO`, mais il utilise aussi parfois un ETF sectoriel gratuit comme repère.

Maintenant, il indique si ce repère est :

- `HIGH` : très pertinent;
- `MEDIUM` : utile, mais imparfait;
- `LOW` : trop général ou trop éloigné du vrai métier de l’entreprise.

Quand la pertinence est `LOW`, l’ETF ne peut plus pénaliser fortement l’action à lui seul. Il devient surtout une alerte informative.

Si une action n’a pas de benchmark configuré, l’agent essaie d’en choisir un automatiquement. Exemple : `AAPL` peut être comparé à `XLK` plutôt qu’à `VFV.TO` seulement.

## 17. Si l’agent met tout dans VFV.TO

Ce n’est pas forcément une erreur.

Cela peut vouloir dire :

- il manque trop de données;
- les données sont surtout estimées automatiquement et pas assez confirmées;
- aucune action n’est clairement meilleure que `VFV.TO`;
- la thèse d’une action est incertaine;
- la valorisation est trop élevée;
- le portefeuille est déjà trop concentré;
- une action est en zone jaune, orange ou rouge.

Regardez alors :

```text
latest_data_gaps.csv
```

Ce fichier indique quelles données doivent être ajoutées ou vérifiées.

## 18. Relancer plus tard

Chaque fois que vous voulez refaire l’analyse :

1. Ouvrez la fenêtre de commandes dans le dossier `investment_automation`.
2. Activez l’environnement.
3. Lancez l’analyse.

### Sur Mac

```bash
source .venv/bin/activate
python3 main.py analyze --capital 1000 --mode family-office
```

### Sur Windows

```bash
.venv\Scripts\activate
python main.py analyze --capital 1000 --mode family-office
```

## 19. À ne pas oublier

- L’agent applique des règles. Il ne connaît pas l’avenir.
- Une action qui a beaucoup baissé n’est pas automatiquement une bonne occasion.
- Une action ne reçoit du capital que si la qualité, la thèse, la croissance, la valorisation, la conviction et le risque restent solides.
- Le fichier manuel est optionnel, mais une donnée vérifiée manuellement reste meilleure qu’une estimation automatique.
- Les données gratuites peuvent être incomplètes.
- La mémoire ticker aide à classer les titres, mais elle ne remplace jamais une donnée fraîche de marché.
- Une contradiction entre sources est une alerte de validation, pas une recommandation automatique de vente.
- Les décisions finales doivent être validées manuellement.
- La partie fiscale est seulement approximative.
- Pour les questions fiscales, à valider avec un fiscaliste ou comptable.

## 20. Petit aide-mémoire

Première installation :

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 main.py init
```

Utilisation normale pour obtenir une recommandation :

```bash
source .venv/bin/activate
python3 main.py validate-inputs
python3 main.py analyze --capital 1000 --mode high-cagr --refresh-market-data
python3 main.py research-status
python3 main.py research-needed
```

Après avoir acheté et mis `data/portfolio.csv` à jour :

```bash
python3 main.py sync-portfolio
```

Sur Windows :

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py init
python main.py validate-inputs
python main.py analyze --capital 1000 --mode high-cagr --refresh-market-data
python main.py research-status
python main.py research-needed
```

# Guide d'audit — investment_automation

Ce fichier est destiné à Claude ou ChatGPT pour structurer
une session d'audit périodique du modèle. Seul Codex peut
modifier les fichiers du projet. Claude et ChatGPT analysent,
proposent et produisent des prompts Codex — ils n'implémentent
jamais directement.

---

## Workflow d'une session d'audit

1. Lire ce fichier en entier avant de commencer.
2. Lire `reports/latest_audit_snapshot_{mode}.json` pour le
   mode à auditer (ex: `latest_audit_snapshot_high-cagr.json`).
3. Lire `reports/latest_report_compact_{mode}.md` pour le
   contexte de la dernière décision.
4. Si un signal spécifique mérite investigation, lire le CSV
   correspondant (voir section Fichiers de référence).
5. Produire une analyse structurée (voir section Format de sortie).
6. Si des corrections sont nécessaires, produire un prompt Codex
   prêt à coller (voir section Format des prompts Codex).

---

## Fichiers à lire dans l'ordre

| Priorité | Fichier | Contenu |
| --- | --- | --- |
| 1 — Toujours | `reports/latest_audit_snapshot_{mode}.json` | Vue agrégée des 5 derniers runs : allocation, anomalies, walk-forward, calibration, model audit |
| 2 — Toujours | `reports/latest_report_compact_{mode}.md` | Dernière décision d'allocation avec contexte |
| 3 — Si signal | `reports/latest_anomaly_report.csv` | Détail des anomalies post-analyse |
| 3 — Si signal | `reports/latest_source_health.csv` | Santé des sources de données |
| 3 — Si signal | `data/proxy_calibration.csv` | Source des valeurs confirmées pour calibration et overrides manuels |
| 3 — Si signal | `reports/latest_proxy_calibration_history.csv` | Sortie historique de calibration des proxies automatiques |
| 3 — Si signal | `reports/latest_validation_priority.csv` | Données prioritaires à valider |
| 3 — Si signal | `reports/latest_walk_forward_inventory_{mode}.csv` | Statut walk-forward par période |
| 3 – Si walk-forward | `reports/universe_snapshots/<run_id>.json` | Snapshots per-run de l'univers scoré pour validation out-of-sample |
| 4 — Si audit profond | `reports/latest_model_audit.csv` | Résultat de l'audit du modèle |
| 4 — Si audit profond | `reports/latest_source_conflicts.csv` | Conflits entre sources de données |
| 5 — Si comparaison | `reports/history/audit_{mode}_*.json` | Archives des runs précédents |

---

## Signaux d'alerte prioritaires dans le JSON

Lire `delta_analysis` en premier. Les champs suivants méritent
une attention immédiate :

- `delta_analysis.anomaly_trend.direction == "WORSENING"` →
  les anomalies augmentent sur plusieurs runs consécutifs ;
  investiguer `latest_anomaly_report.csv`
- `delta_analysis.allocation_churn.status == "CHANGED"` →
  l'allocation a changé significativement ; vérifier si le
  changement est justifié par de nouvelles données ou par
  une instabilité du modèle
- `delta_analysis.calibration_trend.recalibration_candidates_new`
  non vide → de nouveaux candidats à recalibrer sont apparus ;
  lire `data/proxy_calibration.csv` et `reports/latest_proxy_calibration_history.csv`
- `delta_analysis.walk_forward_trend.direction == "WORSENING"` →
  le nombre de périodes utilisables diminue ; le modèle perd
  du recul comparable (sans implication automatique de skill statistique)
- `delta_analysis.decision_quality_trend.direction == "WORSENING"`
  → la qualité de décision se dégrade ; investiguer les données
  manquantes et les conflits de sources
- `runs_history[0].model_audit.audit_status == "FAIL"` →
  l'audit du modèle a échoué ; lire `latest_model_audit.csv`
  avant toute autre action
- `runs_history[0].walk_forward` est `null` → le walk-forward
  n'a jamais été lancé pour ce mode ; suggérer de lancer
  `python3 main.py walk-forward-backtest --mode {mode}`
- `runs_history[0].source_health.sources_degraded > 0` →
  au moins une source est dégradée ; identifier laquelle dans
  `latest_source_health.csv`
- `runs_history[0].meta.run_purpose` absent ou `UNKNOWN_LEGACY` →
  le run reste auditable mais ne doit pas être présenté comme une décision
  forward certaine
- l'audit indique peu d'observations `CURRENT_VERSION_AUDIT` malgré un long
  `CROSS_VERSION_DIAGNOSTIC` → ne jamais emprunter les anciennes versions pour
  augmenter la confiance primaire

---

## Format de sortie d'une session d'audit

Structurer la réponse en quatre blocs dans cet ordre :

### 1. Résumé exécutif (5 lignes max)
État général du modèle en une lecture rapide :
- Décision du dernier run
- Statut global (SAIN / SURVEILLER / ALERTE)
- Signal le plus important détecté
- Tendance sur 5 runs (stable / amélioration / dégradation)
- Recommandation principale

### 2. Signaux détectés
Pour chaque signal, préciser :
- Source (quel champ du JSON ou quel CSV)
- Niveau (INFO / WARN / CRITICAL)
- Description du problème
- Impact potentiel sur le modèle ou les décisions

### 3. Propositions d'amélioration
Pour chaque proposition :
- Ce que ça fait concrètement pour le modèle financier
- Modules touchés
- Niveau de risque : FAIBLE / MOYEN / ÉLEVÉ
- Contraintes DECISIONS.md respectées : OUI / NON

### 4. Prompts Codex (si corrections approuvées)
Format obligatoire de chaque prompt Codex :
- Fichiers à modifier explicitement listés
- Contraintes REFACTOR-01 et REFACTOR-02 rappelées
- Vérification attendue avec commandes exactes
  (`python3 main.py analyze`, `python3 main.py validate-inputs`)
- Aucune ambiguïté sur ce qui doit être modifié vs conservé

---

## Contraintes permanentes à rappeler dans chaque prompt Codex

Ces contraintes sont actives jusqu'à révocation explicite dans
DECISIONS.md :

- `utils.py` — import seulement, aucune nouvelle fonction
  (REFACTOR-01 différé)
- `report_generator.py` — aucune nouvelle dépendance directe
  (REFACTOR-02 différé)
- Modèle non mean-variance — scoring fondamental + allocation
  glottone uniquement
- Aucune matrice covariance/corrélation
- La commande d'analyse est `python3 main.py analyze` (pas
  `analyse`)
- La commande `python3 main.py sync-manual-inputs` est à relancer après
  mise à jour de `data/proxy_calibration.csv` pour appliquer les données
  confirmées au scoring.
- Toujours vérifier `python3 main.py validate-inputs` après
  chaque modification

---

## Fichiers de référence architecture

| Fichier | Rôle |
| --- | --- |
| `DECISIONS.md` | Décisions d'architecture actives et différées |
| `src/report_generator.py` | Générateur des rapports compact et complet |
| `src/report_formatters.py` | Fonctions de formatage des sections |
| `src/audit_snapshot_engine.py` | Moteur de génération du JSON d'audit |
| `src/history_engine.py` | Historique des snapshots d'analyse par ticker |
| `src/allocation_engine.py` | Logique d'allocation gloutonne |
| `src/scoring.py` | Scoring fondamental des titres |
| `src/walk_forward_backtest_engine.py` | Walk-forward et backtest |
| `src/anomaly_detection_engine.py` | Détection d'anomalies post-analyse |
| `src/model_audit_engine.py` | Audit du modèle |
| `src/validation_evidence.py` | Taxonomies canoniques de preuve, maturité, but de run et politique de tuning |
| `src/proxy_calibration.py` | Calibration des proxies automatiques |

---

## Gouvernance et rôles (phase de maturation)

**Rôles permanents et verrouillés:**
- Claude et ChatGPT: analyse, diagnostic, production de prompts Codex uniquement
- Codex: seul implémenteur — toutes les modifications de fichiers passent par Codex
- Ni Claude ni ChatGPT ne modifient aucun fichier du projet directement

**Phase actuelle: maturation et validation**
Le projet a transitionné de l'expansion rapide vers la validation et la
maturité. L'objectif principal n'est plus de maximiser le nombre de modules,
mais de maximiser la fiabilité, la robustesse et la confiance à long terme
du système existant.

**Ordre de priorité pour toute proposition:**
1. Augmenter la confiance dans les décisions du modèle
2. Réduire les risques d'implémentation, les bugs cachés et les cas limites
3. Améliorer la qualité des données, la validation et l'auditabilité
4. Renforcer les tests walk-forward, stress tests et validation out-of-sample
5. Améliorer la stabilité des décisions et minimiser le turnover inutile
6. Simplifier ou refactoriser quand cela augmente la maintenabilité sans
   réduire la fonctionnalité

**Nouvelles fonctionnalités:** seulement si elles apportent une amélioration
significative à la qualité d'investissement long terme non atteignable en
renforçant l'architecture existante.

**Format obligatoire des prompts Codex:**
- Fichiers à modifier listés explicitement
- Contraintes REFACTOR-01 et REFACTOR-02 rappelées
- Vérification attendue avec commandes exactes
- Aucune ambiguïté sur ce qui doit être modifié vs conservé

---

*Dernière mise à jour : 2026-08-23*
*Architecture de validation : CURRENT_VERSION_AUDIT, buts de run explicites, tuning PROPOSAL_ONLY*
*Modes disponibles : high-cagr, rational-aggressive, family-office, balanced*

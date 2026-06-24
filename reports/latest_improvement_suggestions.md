# Audit d’amélioration du modèle

- Date: 2026-06-01
- Mode audité: high-cagr
- Période: 12m
- Statut: **READY_FOR_SAFE_TUNING**
- Historique: 7 date(s) avec allocation; confiance USEFUL_BUT_SHORT_SPAN

> Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, retardées ou erronées. Toute décision finale doit être validée manuellement.

## Résumé

- Suggestions totales: 4
- Suggestions SAFE applicables automatiquement: 1
- Suggestions MODERATE: 0
- Suggestions RISKY: 0
- Attribution de sous-performance: **NO_UNDERPERFORMANCE**
- Gouverneur de correction: **NORMAL_SAFE_TUNING**
- Barrière anti-overfitting: **PASS**
- Santé des sources: **WATCH_SOURCE_QUALITY** / gate **PASS_WITH_CAUTION**
- Qualité tickers/sources: **REVIEW** (57.0/100)
- Interprétation: Des micro-ajustements sécuritaires peuvent être appliqués localement, avec sauvegarde.

## Attribution de sous-performance

- Cette couche décide si une sous-performance mérite une correction ou si elle ressemble plutôt à un retard temporaire acceptable.
- Elle protège contre deux erreurs opposées: corriger trop vite après une mauvaise année, ou refuser de corriger après une vraie dérive.

| metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- |
| Sous-performance observée | NONE | 5.0 % | Statut réel: TWR_FLOW_ADJUSTED_AHEAD_OF_SP500; écart préféré vs S&P 500: 5.0 %. | Évite de confondre une mauvaise année normale avec une erreur de modèle. |
| Horizon de preuve | TOO_SHORT |  | Historique trop court: une correction automatique serait fragile. | Plus l’horizon réel est long, plus une sous-performance devient significative. |
| Problèmes de processus | MINOR_PROCESS_SIGNAL | 1 | Rotation ou changement du titre principal élevé (18.5 % / 50.0 %). | Indique si la sous-performance semble venir d’une mécanique perfectible plutôt que du marché. |
| Diagnostic d’attribution | NO_UNDERPERFORMANCE |  | Aucune sous-performance significative détectée; les corrections doivent rester basées sur la mécanique, pas sur la performance. | Classe la sous-performance avant de laisser le modèle s’auto-ajuster. |
| Gouverneur de correction | NORMAL_SAFE_TUNING |  | Aucune sous-performance significative; conserver les règles normales d’amélioration. | Les corrections restent limitées aux paramètres secondaires. |

## Barrière anti-overfitting

- Cette couche ne rend pas l’analyse mensuelle plus conservatrice.
- Elle vérifie seulement si un auto-ajustement de règle risque d’être trop optimisé pour le dernier cycle de marché.
- Les suggestions qui ne passent pas restent en revue manuelle; les règles vitales ne sont jamais modifiées automatiquement.

| check | status | value | interpretation |
| --- | --- | --- | --- |
| Backtests multi-périodes | PASS | 2 résumé(s) | Vérifie que le modèle ne dépend pas seulement d’une fenêtre récente. |
| Ancien vs récent | PASS | 180 mois simulé(s) | Compare la robustesse des périodes anciennes et récentes quand les données existent. |
| Do-no-harm vs VFV | PASS |  | Refuse les auto-ajustements agressifs si le modèle détériore nettement le benchmark. |
| Rendement ajusté au risque | PASS |  | Évite de favoriser une hausse de rendement théorique obtenue avec trop de drawdown. |
| Cooldown tuning | 45 jours |  | Empêche de modifier trop souvent le même paramètre. |

## Santé des sources

- Cette couche ne modifie pas les allocations.
- Elle empêche seulement un auto-tuning si une source centrale devient critique, afin d’éviter de recalibrer le modèle sur de mauvaises données.
- Lecture: Certaines sources ou proxys sont faibles; l’audit peut continuer, mais les conclusions doivent être lues avec prudence.

| source | status | health_score | coverage_rate | freshness_rate | affected_ticker_count | affected_tickers | conflict_count | critical_gap_count | ticker_count | trend | action | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Yahoo/yfinance market data | OK | 99.5 | 0.9961 | 0.9961 | 1 | FI* | 0 | 0 | 257 | STABLE | Relancer avec --refresh-market-data si plusieurs tickers sont vieux ou indisponibles. | Prix, historique, SMA, drawdown et métriques de marché. |
| SEC/official fundamentals | WATCH | 75.0 | 1.0 | 1.0 | 0 |  | 759 | 0 | 205 | STABLE | Surveiller surtout les titres US importants sans confirmation officielle ou avec conflits. | Confirme certains champs fondamentaux quand disponible; moins utile pour titres non US. |
| Local BNCD/Morningstar reports | OK | 100 | 0.1946 | 1.0 | 0 |  | 0 | 0 | 257 | STABLE | Chercher un rapport seulement pour les titres importants ou recommandés qui manquent de preuves. | Source locale utile pour combler les angles morts; optionnelle pour les titres déjà bien couverts. |
| Free news context | OK | 99.6 | 0.996 | 0.996 | 1 | FI* | 0 | 0 | 253 | STABLE | Utiliser les nouvelles comme contexte seulement; valider manuellement si un mouvement de prix semble étrange. | Aide à comprendre les grosses baisses ou risques récents, sans remplacer les fondamentaux. |
| Automatic proxy estimates | DEGRADED | 65.7 | 0.9066 | 0.9066 | 24 | AEM.TO, BAM, CSU.TO (CSU), ENB.TO, FANG, FTS.TO, GFL.TO, INTC, MFC.TO, MOD, NANO.TO (NANO)*, NTR.TO, RBA.TO, SLF.TO, SMCI, SNDK, STN.TO, TD.TO, TFII.TO*, TOI.V (TOI)* | 0 | 71 | 257 | STABLE | Remplir le fichier de calibration ou ajouter un rapport local pour les titres importants dépendants des proxys. | Surveille le risque qu’un score confiant repose trop sur des estimations. |

## Qualité tickers et contradictions de sources

- Cette couche est informative: elle aide à repérer les tickers mal classés, peu couverts ou contradictoires avant une grosse décision.
- Elle ne déclenche aucune modification automatique de règles.

| check | status | value | interpretation | impact |
| --- | --- | --- | --- | --- |
| Statut global | REVIEW | 57.0/100 | Validation prioritaire recommandée sur WAB*, AVGO, APP, MA, INTU, BAM, LLY, LRCX avant une grosse décision. | Réduit très légèrement la qualité de preuve de l’audit; ne bloque pas l’allocation ni le tuning SAFE. |
| Tickers à revoir | WATCH | mémoire=0; issues=1 | WAB* | À valider avant grosse décision si le ticker est dans le portefeuille ou dans la recommandation. |
| Contradictions prioritaires | REVIEW | review=8; watch=6 | AVGO, APP, MA, INTU, BAM, LLY, LRCX, TSLA | Alerte de validation seulement; ne bloque pas automatiquement une allocation. |

## Suggestions

| suggestion_id | mode | parameter | current_value | suggested_delta | suggested_value | safety_level | can_auto_apply | status | evidence | reason | expected_effect | risk | guardrail | correction_governor | overfit_gate_status | overfit_gate_score | overfit_gate_reason | in_sample_out_of_sample_status | regime_consistency_status | do_no_harm_status | risk_adjusted_status | cooldown_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high-cagr:source_health:WATCH_SOURCE_QUALITY | high-cagr | source_health |  | 0.0 |  | INFO | False | WATCH_SOURCE_QUALITY | Source la plus faible: Automatic proxy estimates (65.7/100); gate tuning: PASS_WITH_CAUTION. | Certaines sources ou proxys sont faibles; l’audit peut continuer, mais les conclusions doivent être lues avec prudence. | Ajouter une couche anti-erreur à l’audit sans modifier l’allocation mensuelle. | Si ce garde-fou était trop strict, il pourrait retarder un micro-ajustement utile; il bloque seulement les cas critiques. | Règles vitales verrouillées; ajustement limité aux paramètres secondaires. | NORMAL_SAFE_TUNING | NOT_APPLICABLE | 100 | Suggestion informative ou non ajustable automatiquement. | PASS | PASS | PASS | PASS | NOT_APPLICABLE |
| high-cagr:ticker_source_quality:REVIEW | high-cagr | ticker_source_quality |  | 0.0 |  | INFO | False | REVIEW | Score: 57.0/100; tickers à revoir: WAB*, AVGO, APP, MA, INTU, BAM, LLY, LRCX. | Validation prioritaire recommandée sur WAB*, AVGO, APP, MA, INTU, BAM, LLY, LRCX avant une grosse décision. | Rendre l’audit plus robuste contre les erreurs de ticker ou les contradictions de sources sans changer l’allocation. | Peut ajouter du bruit si lu trop sévèrement; reste informatif et non auto-applicable. | Règles vitales verrouillées; ajustement limité aux paramètres secondaires. | NORMAL_SAFE_TUNING | NOT_APPLICABLE | 100 | Suggestion informative ou non ajustable automatiquement. | PASS | PASS | PASS | PASS | NOT_APPLICABLE |
| high-cagr:correction_governor:NO_UNDERPERFORMANCE | high-cagr | correction_governor |  | 0.0 |  | INFO | False | NO_UNDERPERFORMANCE | Écart vs S&P 500: 5.0 %; problèmes de processus: 1. | Aucune sous-performance significative détectée; les corrections doivent rester basées sur la mécanique, pas sur la performance. | Aucune sous-performance significative; conserver les règles normales d’amélioration. | Ce gouverneur évite à la fois l’over-correction après une mauvaise période et l’under-correction après une vraie dérive. | Règles vitales verrouillées; ajustement limité aux paramètres secondaires. | NORMAL_SAFE_TUNING | NOT_APPLICABLE | 100 | Suggestion informative ou non ajustable automatiquement. | PASS | PASS | PASS | PASS | NOT_APPLICABLE |
| high-cagr:stability_strength_adjustment:PENDING_SAFE_APPLY | high-cagr | stability_strength_adjustment | 0.0 | 0.25 | 0.25 | SAFE | True | PENDING_SAFE_APPLY | rotation moyenne 18.5 %, changement du titre principal 50.0 %. | Les recommandations semblent peut-être trop sensibles aux variations récentes. | Augmenter légèrement l’amortisseur anti-bruit sans empêcher un vrai changement de leader. | Trop de stabilité pourrait retarder un changement justifié; la variation est donc limitée. | Règles vitales verrouillées; ajustement limité aux paramètres secondaires. |  | PASS | 86 | La suggestion ne montre pas de risque évident de surapprentissage selon les preuves disponibles. | PASS | PASS | PASS | PASS | PASS |

## Ce que la commande peut appliquer

- `apply-safe-tuning` applique seulement les lignes `SAFE` avec `can_auto_apply = True`.
- Les suggestions `MODERATE`, `RISKY` ou `INFO` restent informatives.
- Les règles vitales restent verrouillées: thèse cassée, vente orange/rouge, comparaison VFV et promotions externes ne sont pas modifiables par tuning.
- Une sauvegarde est créée avant toute application via la commande CLI.

## Commandes

```bash
python3 main.py improvement-audit --period 12m --mode high-cagr
python3 main.py apply-safe-tuning --mode high-cagr
```

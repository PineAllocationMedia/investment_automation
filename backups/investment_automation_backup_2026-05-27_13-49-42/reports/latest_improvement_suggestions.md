# Audit d’amélioration du modèle

- Date: 2026-05-25
- Mode audité: high-cagr
- Période: 12m
- Statut: **INSUFFICIENT_HISTORY**
- Historique: 2 date(s) avec allocation; confiance PRELIMINARY

> Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, retardées ou erronées. Toute décision finale doit être validée manuellement.

## Résumé

- Suggestions totales: 2
- Suggestions SAFE applicables automatiquement: 0
- Suggestions MODERATE: 0
- Suggestions RISKY: 0
- Attribution de sous-performance: **NO_UNDERPERFORMANCE**
- Gouverneur de correction: **NORMAL_SAFE_TUNING**
- Interprétation: Historique trop court: l’audit informe, mais ne doit pas ajuster le modèle.

## Attribution de sous-performance

- Cette couche décide si une sous-performance mérite une correction ou si elle ressemble plutôt à un retard temporaire acceptable.
- Elle protège contre deux erreurs opposées: corriger trop vite après une mauvaise année, ou refuser de corriger après une vraie dérive.

| metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- |
| Sous-performance observée | NONE | 1.4 % | Statut réel: TWR_FLOW_ADJUSTED_SIMILAR_TO_SP500; écart préféré vs S&P 500: 1.4 %. | Évite de confondre une mauvaise année normale avec une erreur de modèle. |
| Horizon de preuve | TOO_SHORT |  | Historique trop court: une correction automatique serait fragile. | Plus l’horizon réel est long, plus une sous-performance devient significative. |
| Problèmes de processus | CLEAN_PROCESS | 0 | Aucun problème mécanique majeur détecté. | Indique si la sous-performance semble venir d’une mécanique perfectible plutôt que du marché. |
| Diagnostic d’attribution | NO_UNDERPERFORMANCE |  | Aucune sous-performance significative détectée; les corrections doivent rester basées sur la mécanique, pas sur la performance. | Classe la sous-performance avant de laisser le modèle s’auto-ajuster. |
| Gouverneur de correction | NORMAL_SAFE_TUNING |  | Aucune sous-performance significative; conserver les règles normales d’amélioration. | Les corrections restent limitées aux paramètres secondaires. |

## Suggestions

| suggestion_id | mode | parameter | current_value | suggested_delta | suggested_value | safety_level | can_auto_apply | status | evidence | reason | expected_effect | risk | guardrail | correction_governor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high-cagr:correction_governor:NO_UNDERPERFORMANCE | high-cagr | correction_governor |  | 0.0 |  | INFO | False | NO_UNDERPERFORMANCE | Écart vs S&P 500: 1.4 %; problèmes de processus: 0. | Aucune sous-performance significative détectée; les corrections doivent rester basées sur la mécanique, pas sur la performance. | Aucune sous-performance significative; conserver les règles normales d’amélioration. | Ce gouverneur évite à la fois l’over-correction après une mauvaise période et l’under-correction après une vraie dérive. | Règles vitales verrouillées; ajustement limité aux paramètres secondaires. | NORMAL_SAFE_TUNING |
| high-cagr:none:WAIT_FOR_MORE_HISTORY | high-cagr | none |  | 0.0 |  | INFO | False | WAIT_FOR_MORE_HISTORY | 2 date(s) avec allocation; confiance PRELIMINARY. | L’audit fonctionne, mais l’historique est trop court pour ajuster les paramètres sans risque de suradaptation. | Accumuler quelques analyses réelles avant de modifier le comportement du modèle. | Changer trop tôt pourrait optimiser le modèle pour du bruit de marché. | Règles vitales verrouillées; ajustement limité aux paramètres secondaires. |  |

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

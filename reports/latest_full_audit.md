# Audit maître du modèle

- Date: 2026-06-01
- Mode audité: high-cagr
- Période d’audit: 12m
- Backtest demandé: 5 ans, 10 ans
- Cotisation mensuelle utilisée pour le backtest: 618.35 $

> Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, retardées ou erronées. Toute décision finale doit être validée manuellement.

## Résumé exécutif

- Statut critère 7: **AUDIT_STRONG** (82.0/100)
- Santé du modèle: **STRONG** (100.0/100)
- Backtest: **THEORETICAL_ACCEPTABLE** (74.0/100)
- Performance réelle suivie: **TWR_FLOW_ADJUSTED_AHEAD_OF_SP500** (86.0/100)
- Santé des sources: **WATCH_SOURCE_QUALITY** (65.7/100)
- Qualité tickers/sources: **REVIEW** (57.0/100)
- Attribution de sous-performance: **NO_UNDERPERFORMANCE** / gouverneur **NORMAL_SAFE_TUNING**
- Conclusion: Le modèle possède une preuve de méthode solide selon les données disponibles, sans garantir l’avenir.

## Tableau maître

| section | metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- | --- |
| Résumé | Intégration du critère 7 | AUDIT_STRONG | 82.0/100 | Le modèle possède une preuve de méthode solide selon les données disponibles, sans garantir l’avenir. | Synthèse de la stabilité, du backtest, de la performance réelle suivie et de la qualité de l’historique. |
| Cotisation | Capital mensuel utilisé | PRELIMINARY | 618.35 $ | Cotisation mensuelle moyenne estimée à partir de 1 mois avec flux positif sur 1 mois civils observés. | Sert seulement au backtest théorique; l’analyse mensuelle normale garde son --capital réel. |
| Cohérence | Santé du modèle | STRONG | 100.0/100 | 7 date(s) avec allocation sur 9 jour(s). | Vérifie que le modèle ne devient pas trop instable, trop défensif ou trop concentré. |
| Cohérence | Rotation moyenne des recommandations | OK | 18.5 % | Part moyenne de cotisation qui change de destination entre deux dates d’analyse. | Protège contre les changements causés seulement par du bruit de marché. |
| Risque | Noyau VFV moyen | BALANCED_FOR_HIGH_CAGR | 5.0 % | Exposition core moyenne: 95.0 %. | Confirme que VFV sert de noyau/pare-chocs sans tuer le rendement recherché. |
| Risque | Plus gros bloc moyen | WATCH | 43.0 % | Moyenne de la plus grosse allocation individuelle. | Évite de transformer une stratégie high CAGR en pari trop concentré. |
| Risque | Exposition cycles/bulles | WATCH | 28.6 % | Fréquence où une recommandation financée portait un risque cycle/bulle élevé. | Vérifie que le modèle ne court pas seulement après le thème chaud du moment. |
| Backtest | Résultat théorique 5-10 ans | THEORETICAL_ACCEPTABLE | 74.0/100 | 5 ans au-dessus de VFV (56 659.60 $); 10 ans au-dessus de VFV (123 060.49 $) | Teste la mécanique avec des prix historiques gratuits, sans prétendre prédire l’avenir. |
| Performance réelle | Portefeuille vs S&P 500 local | TWR_FLOW_ADJUSTED_AHEAD_OF_SP500 | 86.0/100 | Lecture recommandée: TWR, la stratégie du compte est devant VFV.TO d’environ 5.0 points depuis le début du suivi après neutralisation des cotisations/retraits détectés. Écart TWR vs S&P 500: 5.0 %. Base VFV: ADJUSTED_CLOSE_TOTAL_RETURN_PROXY. | Construit progressivement une preuve réelle de ta stratégie à chaque analyse. |
| Attribution | Sous-performance et gouverneur | NO_UNDERPERFORMANCE | NORMAL_SAFE_TUNING | Aucune sous-performance significative détectée; les corrections doivent rester basées sur la mécanique, pas sur la performance. | Les corrections restent limitées aux paramètres secondaires. |
| Données | Qualité de preuve | LOW | 63.1/100 | Confiance modèle: USEFUL_BUT_SHORT_SPAN; confiance cotisation: PRELIMINARY. | Plus l’historique local s’allonge, plus l’audit devient représentatif. |
| Données | Santé des sources | WATCH_SOURCE_QUALITY | 65.7/100 | Source la plus faible: Automatic proxy estimates; gate tuning: PASS_WITH_CAUTION. | Sert de garde-fou d’audit: n’affecte pas l’allocation mensuelle, mais peut bloquer un auto-tuning si une source centrale est critique. |
| Données | Qualité tickers et contradictions | REVIEW | 57.0/100 | Validation prioritaire recommandée sur WAB*, AVGO, APP, MA, INTU, BAM, LLY, LRCX avant une grosse décision. | Garde-fou informatif: réduit très légèrement la qualité de preuve si un ticker/source prioritaire doit être validé. |

## Cotisation détectée

| monthly_capital | source | confidence | positive_flow_month_count | total_detected_contributions | first_flow_date | last_flow_date | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 618.35 | DETECTED_EXTERNAL_FLOWS | PRELIMINARY | 1 | 618.35 | 2026-05-21 | 2026-05-29 | Cotisation mensuelle moyenne estimée à partir de 1 mois avec flux positif sur 1 mois civils observés. |

## Backtest théorique

- Cette partie teste la mécanique actuelle avec prix historiques gratuits. Elle ne reconstruit pas parfaitement les fondamentaux historiques.

| period_years | start_date | end_date | total_contributed | final_value | vfv_final_value | excess_value_vs_vfv | price_return_basis | money_weighted_annual_return | max_drawdown_on_capital_multiple | avg_vfv_allocation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 2021-06-30 | 2026-05-29 | 37 101.00 $ | 117 111.33 $ | 60 451.73 $ | 56 659.60 $ | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | 47.90 % | -33.6 % | 10.4 % |
| 10 | 2016-06-30 | 2026-05-29 | 74 202.00 $ | 301 069.53 $ | 178 009.04 $ | 123 060.49 $ | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | 26.41 % | -34.9 % | 12.6 % |

## Performance réelle du portefeuille

- Cette section s’améliore avec le temps. Au début, elle sert surtout à créer une base de suivi.

| account_type | current_value_cad | tracking_start_date | benchmark_return_basis | preferred_performance_summary | portfolio_twr | sp500_twr | twr_excess_vs_sp500 | twr_status | portfolio_return_since_tracking | sp500_return_since_tracking | excess_return_vs_sp500 | portfolio_xirr | sp500_xirr | xirr_excess_vs_sp500 | xirr_status | value_added_vs_sp500_cad | comparison_status | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL_ACCOUNTS | 10337.52 | 2026-05-15 | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | Lecture recommandée: TWR, la stratégie du compte est devant VFV.TO d’environ 5.0 points depuis le début du suivi après neutralisation des cotisations/retraits détectés. | 0.076386 | 0.026377 | 0.050009 | TWR_FLOW_ADJUSTED_AHEAD_OF_SP500 | 0.146613 | 0.026377 | 0.120236 | 3.839664 | 0.744637 | 3.095028 | XIRR_AVAILABLE_SHORT_HISTORY | 460.99 | APPROXIMATE_CONTRIBUTIONS_CHANGED | Comparaison approximative: le compte a probablement reçu des cotisations, achats ou ventes depuis la base. Une mesure exacte demanderait les transactions datées et les prix historiques du benchmark. |
| TFSA1 | 9136.24 | 2026-05-15 | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | Lecture recommandée: TWR, la stratégie du compte est devant VFV.TO d’environ 5.1 points depuis le début du suivi. | 0.077444 | 0.026377 | 0.051067 | TWR_NO_EXTERNAL_FLOWS_AHEAD_OF_SP500 | 0.077444 | 0.026377 | 0.051067 | 3.966032 | 0.749572 | 3.216461 | XIRR_AVAILABLE_SHORT_HISTORY | 433.03 | AHEAD_OF_SP500 | Le compte est devant le proxy S&P 500 depuis le début du suivi local d’environ 5.1 points. |
| TFSA2 | 1201.28 | 2026-05-15 | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | Lecture recommandée: TWR, la stratégie du compte est devant VFV.TO d’environ 2.0 points depuis le début du suivi après neutralisation des cotisations/retraits détectés. | 0.046522 | 0.026377 | 0.020145 | TWR_FLOW_ADJUSTED_AHEAD_OF_SP500 | 1.240567 | 0.026377 | 1.21419 | 2.615376 | 0.690429 | 1.924947 | XIRR_AVAILABLE_SHORT_HISTORY | 27.96 | APPROXIMATE_CONTRIBUTIONS_CHANGED | Comparaison approximative: le compte a probablement reçu des cotisations, achats ou ventes depuis la base. Une mesure exacte demanderait les transactions datées et les prix historiques du benchmark. |

## Attribution de sous-performance

- Cette section évite de corriger le modèle simplement parce que le S&P 500 a gagné une période donnée.
- Elle sépare une sous-performance potentiellement normale d’un vrai problème de processus.

| metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- |
| Sous-performance observée | NONE | 5.0 % | Statut réel: TWR_FLOW_ADJUSTED_AHEAD_OF_SP500; écart préféré vs S&P 500: 5.0 %. | Évite de confondre une mauvaise année normale avec une erreur de modèle. |
| Horizon de preuve | TOO_SHORT |  | Historique trop court: une correction automatique serait fragile. | Plus l’horizon réel est long, plus une sous-performance devient significative. |
| Problèmes de processus | MINOR_PROCESS_SIGNAL | 1 | Rotation ou changement du titre principal élevé (18.5 % / 50.0 %). | Indique si la sous-performance semble venir d’une mécanique perfectible plutôt que du marché. |
| Diagnostic d’attribution | NO_UNDERPERFORMANCE |  | Aucune sous-performance significative détectée; les corrections doivent rester basées sur la mécanique, pas sur la performance. | Classe la sous-performance avant de laisser le modèle s’auto-ajuster. |
| Gouverneur de correction | NORMAL_SAFE_TUNING |  | Aucune sous-performance significative; conserver les règles normales d’amélioration. | Les corrections restent limitées aux paramètres secondaires. |

## Santé des sources

- Cette section évite qu’un audit ou un tuning automatique tire une conclusion trop forte si les sources sont fragiles.
- Elle ne change pas l’allocation mensuelle. Elle limite seulement l’auto-correction du modèle en cas de source centrale critique.

| source | status | health_score | coverage_rate | freshness_rate | affected_ticker_count | affected_tickers | conflict_count | critical_gap_count | ticker_count | trend | action | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Yahoo/yfinance market data | OK | 99.5 | 0.9961 | 0.9961 | 1 | FI* | 0 | 0 | 257 | STABLE | Relancer avec --refresh-market-data si plusieurs tickers sont vieux ou indisponibles. | Prix, historique, SMA, drawdown et métriques de marché. |
| SEC/official fundamentals | WATCH | 75.0 | 1.0 | 1.0 | 0 |  | 759 | 0 | 205 | STABLE | Surveiller surtout les titres US importants sans confirmation officielle ou avec conflits. | Confirme certains champs fondamentaux quand disponible; moins utile pour titres non US. |
| Local BNCD/Morningstar reports | OK | 100 | 0.1946 | 1.0 | 0 |  | 0 | 0 | 257 | STABLE | Chercher un rapport seulement pour les titres importants ou recommandés qui manquent de preuves. | Source locale utile pour combler les angles morts; optionnelle pour les titres déjà bien couverts. |
| Free news context | OK | 99.6 | 0.996 | 0.996 | 1 | FI* | 0 | 0 | 253 | STABLE | Utiliser les nouvelles comme contexte seulement; valider manuellement si un mouvement de prix semble étrange. | Aide à comprendre les grosses baisses ou risques récents, sans remplacer les fondamentaux. |
| Automatic proxy estimates | DEGRADED | 65.7 | 0.9066 | 0.9066 | 24 | AEM.TO, BAM, CSU.TO (CSU), ENB.TO, FANG, FTS.TO, GFL.TO, INTC, MFC.TO, MOD, NANO.TO (NANO)*, NTR.TO, RBA.TO, SLF.TO, SMCI, SNDK, STN.TO, TD.TO, TFII.TO*, TOI.V (TOI)* | 0 | 71 | 257 | STABLE | Remplir le fichier de calibration ou ajouter un rapport local pour les titres importants dépendants des proxys. | Surveille le risque qu’un score confiant repose trop sur des estimations. |

## Qualité tickers et contradictions de sources

- Cette section vérifie si un ticker important semble mal classé, peu couvert ou contradictoire entre sources.
- Elle ne change pas l’allocation mensuelle et ne bloque pas `apply-safe-tuning` à elle seule.
- Elle sert à éviter une mauvaise exécution avant une grosse décision.

| check | status | value | interpretation | impact |
| --- | --- | --- | --- | --- |
| Statut global | REVIEW | 57.0/100 | Validation prioritaire recommandée sur WAB*, AVGO, APP, MA, INTU, BAM, LLY, LRCX avant une grosse décision. | Réduit très légèrement la qualité de preuve de l’audit; ne bloque pas l’allocation ni le tuning SAFE. |
| Tickers à revoir | WATCH | mémoire=0; issues=1 | WAB* | À valider avant grosse décision si le ticker est dans le portefeuille ou dans la recommandation. |
| Contradictions prioritaires | REVIEW | review=8; watch=6 | AVGO, APP, MA, INTU, BAM, LLY, LRCX, TSLA | Alerte de validation seulement; ne bloque pas automatiquement une allocation. |

## Revue des seuils

- Diagnostic: **THRESHOLDS_OK**
- Interprétation: Les seuils semblent cohérents avec le profil high CAGR long terme selon l’historique disponible.

## Ce que cet audit améliore

- Il regroupe la stabilité du modèle, le risque, la comparaison à VFV, la performance réelle suivie et le backtest en un seul diagnostic.
- Il évite de juger le modèle sur une seule recommandation ponctuelle.
- Il utilise la cotisation moyenne détectée quand l’historique est exploitable, ce qui rend le backtest plus proche de ta vraie méthode.
- Il ne modifie pas automatiquement les règles: il signale les seuils à surveiller pour éviter de recalibrer le modèle sur trop peu de données.

## Limites

- Le backtest reste théorique: il utilise des scores/proxys actuels et des prix historiques gratuits.
- La performance réelle devient vraiment informative seulement après plusieurs mois, puis plusieurs années de suivi.
- Les taxes, frais exacts, prix exacts de transaction et données manquantes peuvent créer un écart avec la réalité.
- Une bonne note d’audit ne garantit pas une surperformance future.

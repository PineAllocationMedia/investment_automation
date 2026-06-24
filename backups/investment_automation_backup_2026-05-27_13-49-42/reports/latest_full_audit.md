# Audit maître du modèle

- Date: 2026-05-24
- Mode audité: high-cagr
- Période d’audit: all
- Backtest demandé: 5 ans, 10 ans
- Cotisation mensuelle utilisée pour le backtest: 248.45 $

> Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, retardées ou erronées. Toute décision finale doit être validée manuellement.

## Résumé exécutif

- Statut critère 7: **AUDIT_ACCEPTABLE** (71.3/100)
- Santé du modèle: **GOOD_BUT_WATCH** (82.0/100)
- Backtest: **THEORETICAL_ACCEPTABLE** (77.5/100)
- Performance réelle suivie: **TWR_FLOW_ADJUSTED_SIMILAR_TO_SP500** (60.0/100)
- Conclusion: Le modèle est utilisable sur le long terme, avec une surveillance périodique des seuils, du risque et de VFV.

## Tableau maître

| section | metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- | --- |
| Résumé | Intégration du critère 7 | AUDIT_ACCEPTABLE | 71.3/100 | Le modèle est utilisable sur le long terme, avec une surveillance périodique des seuils, du risque et de VFV. | Synthèse de la stabilité, du backtest, de la performance réelle suivie et de la qualité de l’historique. |
| Cotisation | Capital mensuel utilisé | PRELIMINARY | 248.45 $ | Cotisation mensuelle moyenne estimée à partir de 1 mois avec flux positif sur 1 mois civils observés. | Sert seulement au backtest théorique; l’analyse mensuelle normale garde son --capital réel. |
| Cohérence | Santé du modèle | GOOD_BUT_WATCH | 82.0/100 | 2 date(s) avec allocation sur 1 jour(s). | Vérifie que le modèle ne devient pas trop instable, trop défensif ou trop concentré. |
| Cohérence | Rotation moyenne des recommandations | OK | 0.0 % | Part moyenne de cotisation qui change de destination entre deux dates d’analyse. | Protège contre les changements causés seulement par du bruit de marché. |
| Risque | Noyau VFV moyen | BALANCED_FOR_HIGH_CAGR | 5.0 % | Exposition core moyenne: 95.0 %. | Confirme que VFV sert de noyau/pare-chocs sans tuer le rendement recherché. |
| Risque | Plus gros bloc moyen | WATCH | 45.0 % | Moyenne de la plus grosse allocation individuelle. | Évite de transformer une stratégie high CAGR en pari trop concentré. |
| Risque | Exposition cycles/bulles | OK | 0.0 % | Fréquence où une recommandation financée portait un risque cycle/bulle élevé. | Vérifie que le modèle ne court pas seulement après le thème chaud du moment. |
| Backtest | Résultat théorique 5-10 ans | THEORETICAL_ACCEPTABLE | 77.5/100 | 5 ans au-dessus de VFV (8 229.81 $); 10 ans au-dessus de VFV (66 443.11 $) | Teste la mécanique avec des prix historiques gratuits, sans prétendre prédire l’avenir. |
| Performance réelle | Portefeuille vs S&P 500 local | TWR_FLOW_ADJUSTED_SIMILAR_TO_SP500 | 60.0/100 | Lecture recommandée: TWR, la stratégie du compte est devant VFV.TO d’environ 1.4 points depuis le début du suivi après neutralisation des cotisations/retraits détectés. Écart TWR vs S&P 500: 1.4 %. Base VFV: ADJUSTED_CLOSE_TOTAL_RETURN_PROXY. | Construit progressivement une preuve réelle de ta stratégie à chaque analyse. |
| Données | Qualité de preuve | LOW | 57.5/100 | Confiance modèle: PRELIMINARY; confiance cotisation: PRELIMINARY. | Plus l’historique local s’allonge, plus l’audit devient représentatif. |

## Cotisation détectée

| monthly_capital | source | confidence | positive_flow_month_count | total_detected_contributions | first_flow_date | last_flow_date | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 248.45 | DETECTED_EXTERNAL_FLOWS | PRELIMINARY | 1 | 248.45 | 2026-05-21 | 2026-05-21 | Cotisation mensuelle moyenne estimée à partir de 1 mois avec flux positif sur 1 mois civils observés. |

## Backtest théorique

- Cette partie teste la mécanique actuelle avec prix historiques gratuits. Elle ne reconstruit pas parfaitement les fondamentaux historiques.

| period_years | start_date | end_date | total_contributed | final_value | vfv_final_value | excess_value_vs_vfv | money_weighted_annual_return | max_drawdown_on_capital_multiple | avg_vfv_allocation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 2021-06-30 | 2026-05-07 | 14 907.00 $ | 31 585.16 $ | 23 355.35 $ | 8 229.81 $ | 30.56 % | -19.8 % | 12.8 % |
| 10 | 2016-06-30 | 2026-05-07 | 29 814.00 $ | 135 197.61 $ | 68 754.50 $ | 66 443.11 $ | 28.46 % | -37.3 % | 11.8 % |

## Performance réelle du portefeuille

- Cette section s’améliore avec le temps. Au début, elle sert surtout à créer une base de suivi.

| account_type | current_value_cad | tracking_start_date | benchmark_return_basis | preferred_performance_summary | portfolio_twr | sp500_twr | twr_excess_vs_sp500 | twr_status | portfolio_return_since_tracking | sp500_return_since_tracking | excess_return_vs_sp500 | portfolio_xirr | sp500_xirr | xirr_excess_vs_sp500 | xirr_status | value_added_vs_sp500_cad | comparison_status | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL_ACCOUNTS | 9514.96 | 2026-05-15 | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | Lecture recommandée: TWR, la stratégie du compte est devant VFV.TO d’environ 1.4 points depuis le début du suivi après neutralisation des cotisations/retraits détectés. | 0.027504 | 0.01305 | 0.014454 | TWR_FLOW_ADJUSTED_SIMILAR_TO_SP500 | 0.055377 | 0.01305 | 0.042327 | 2.01521 | 0.694829 | 1.320381 | XIRR_AVAILABLE_SHORT_HISTORY | 131.76 | APPROXIMATE_CONTRIBUTIONS_CHANGED | Comparaison approximative: le compte a probablement reçu des cotisations, achats ou ventes depuis la base. Une mesure exacte demanderait les transactions datées et les prix historiques du benchmark. |
| TFSA1 | 8742.27 | 2026-05-15 | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | Lecture recommandée: TWR, la stratégie du compte est devant VFV.TO d’environ 1.8 points depuis le début du suivi. | 0.030983 | 0.01305 | 0.017933 | TWR_NO_EXTERNAL_FLOWS_SIMILAR_TO_SP500 | 0.030983 | 0.01305 | 0.017933 | 2.44974 | 0.69248 | 1.75726 | XIRR_AVAILABLE_SHORT_HISTORY | 152.06 | SIMILAR_TO_SP500 | Le compte évolue près du proxy S&P 500 depuis le début du suivi local. |
| TFSA2 | 772.69 | 2026-05-15 | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | Lecture recommandée: TWR, la stratégie du compte est derrière VFV.TO d’environ 4.0 points depuis le début du suivi après neutralisation des cotisations/retraits détectés. | -0.027356 | 0.01305 | -0.040406 | TWR_FLOW_ADJUSTED_BEHIND_SP500 | 0.441183 | 0.01305 | 0.428132 | -0.545163 | 0.727365 | -1.272527 | XIRR_AVAILABLE_SHORT_HISTORY | -20.3 | APPROXIMATE_CONTRIBUTIONS_CHANGED | Comparaison approximative: le compte a probablement reçu des cotisations, achats ou ventes depuis la base. Une mesure exacte demanderait les transactions datées et les prix historiques du benchmark. |

## Revue des seuils

- Diagnostic: **INSUFFICIENT_HISTORY**
- Interprétation: Pas encore assez de dates avec allocation pour proposer une vraie calibration des seuils.

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

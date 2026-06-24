# Backtest théorique du modèle

> Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, retardées ou erronées. Toute décision finale doit être validée manuellement.

## Lecture importante

- Ce backtest est théorique et sert à tester la mécanique, pas à prédire le futur.
- Les prix historiques viennent de yfinance quand disponibles.
- Quand disponible, le backtest utilise `Adj Close`, un proxy gratuit de rendement total approximatif qui inclut les dividendes/distributions réinvestis; sinon il revient à `Close`.
- Les fondamentaux historiques complets ne sont pas reconstruits gratuitement; les scores actuels du modèle servent d’ancrage.
- Le résultat peut surestimer ou sous-estimer la réalité à cause du biais de survie, des tickers récents, des taxes, des frais et du change.

## Résumé

| period_years | start_date | end_date | total_contributed | final_value | vfv_final_value | excess_value_vs_vfv | price_return_basis | money_weighted_annual_return | max_drawdown_on_capital_multiple | avg_vfv_allocation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 2021-06-30 | 2026-05-29 | 37 101.00 $ | 117 111.33 $ | 60 451.73 $ | 56 659.60 $ | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | 47.90 % | -33.6 % | 10.4 % |
| 10 | 2016-06-30 | 2026-05-29 | 74 202.00 $ | 301 069.53 $ | 178 009.04 $ | 123 060.49 $ | ADJUSTED_CLOSE_TOTAL_RETURN_PROXY | 26.41 % | -34.9 % | 12.6 % |

## Interprétation

- Sur 5 ans, la stratégie a battu VFV.TO de 56 659.60 $ avec un rendement annualisé approximatif de 47.90 %.
- Sur 10 ans, la stratégie a battu VFV.TO de 123 060.49 $ avec un rendement annualisé approximatif de 26.41 %.

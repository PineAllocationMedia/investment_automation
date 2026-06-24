# Audit du modèle d’allocation

- Date de création: 2026-06-01
- Période demandée: 12m
- Mode analysé: high-cagr
- Historique utilisé: 7 date(s) distincte(s) sur 9 jour(s)
- Dates avec allocation exploitable: 7
- Dates récentes incluses: 2026-05-24, 2026-05-27, 2026-05-29, 2026-05-30, 2026-05-31, 2026-06-01
- Analyses le même jour regroupées/ignorées pour l’audit: 56
- Versions de règles observées: 2026-05-12-high-cagr-stability-v3 (7)

> Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, retardées ou erronées. Toute décision finale doit être validée manuellement.

## Résumé

- Santé du modèle: **STRONG** (100/100)
- Confiance de l’audit: **USEFUL_BUT_SHORT_SPAN**
- Revue des seuils: **THRESHOLDS_OK**
- Titres principaux recommandés au moins une fois: APP, GOOGL
- Conclusion: La mécanique récente semble saine et alignée avec un profil haut CAGR long terme, tout en gardant des garde-fous.

## Revue des seuils

- Cette section ne modifie pas les règles. Elle indique seulement quels seuils mériteraient une revue manuelle si la tendance se répète.

| section | metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- | --- |
| Revue des seuils | Diagnostic de calibration | THRESHOLDS_OK | VFV 5.0 %, core 95.0 %, rotation 18.5 % | Les seuils semblent cohérents avec le profil high CAGR long terme selon l’historique disponible. | Suggestion seulement: l’agent ne modifie jamais automatiquement ses règles ou seuils. |
| Revue des seuils | Modification automatique des règles | DISABLED | 0 changement automatique | L’audit observe les règles, mais ne les réécrit jamais tout seul. | Toute modification de seuil doit être validée manuellement après plusieurs mois de données. |
| Revue des seuils | Action recommandée | KEEP_RULES | Aucun ajustement suggéré | Les seuils ne montrent pas de dérive importante dans l’historique disponible. | Continuer l’utilisation normale et réévaluer après quelques nouvelles cotisations. |

## Tableau d’audit

| section | metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- | --- |
| Résumé | Santé du modèle | STRONG | 100/100 | Le modèle semble stable, offensif avec discipline, et cohérent avec le profil long terme. | Indique si la mécanique récente semble saine, trop volatile, trop défensive ou trop concentrée. |
| Résumé | Confiance de l’audit | USEFUL_BUT_SHORT_SPAN | 7 date(s) distincte(s), 7 avec allocation, 9 jour(s) de recul | Plusieurs dates, mais période courte: utile pour détecter une volatilité récente. | Plus il y a de dates distinctes espacées dans le temps, plus l’audit est représentatif. |
| Mémoire | Analyses intra-journée regroupées | OK | 56 | Plusieurs tests le même jour comptent comme une seule date de référence. | Évite de biaiser l’audit si tu testes souvent le modèle dans la même journée. |
| Stabilité | Changement du titre principal | WATCH | 50.0 % | 3 changement(s) du principal titre recommandé. | Un peu de variation est sain; trop de rotation peut signaler une recommandation trop sensible. |
| Stabilité | Rotation moyenne de l’allocation | OK | 18.5 % | Mesure la part moyenne de cotisation qui change de destination entre deux dates. | Aide à détecter une recommandation qui bouge trop sans vraie raison long terme. |
| VFV | Part moyenne VFV | OK | 5.0 % | Fourchette observée: 0.0 % à 10.0 %. | VFV doit servir de filet; une part durablement trop élevée peut devenir trop défensive pour ton profil. |
| VFV | Volatilité VFV | WATCH | 10.0 % | Variation entre la plus petite et la plus grande part VFV observée. | Permet de voir si VFV monte pour une raison ponctuelle ou si la règle est trop nerveuse. |
| Profil | Exposition core moyenne | STRONG | 95.0 % | Nombre moyen de titres core financés: 3.3. | Mesure si la cotisation va surtout vers des compounders potentiels plutôt que vers le filet VFV. |
| Profil | Qualité moyenne de la recommandation | OK | 78.1/100 | Moyenne du score de qualité déjà calculé par l’agent après chaque analyse. | Confirme si les recommandations passées étaient robustes, pas seulement offensives. |
| Risque | Concentration du plus gros bloc | WATCH | 43.0 % | Part moyenne du plus gros titre individuel dans la cotisation. | Un gros bloc est acceptable pour high CAGR, mais l’audit surveille l’excès répété. |
| Risque | Exposition aux cycles/bulles sur titres financés | WATCH | 28.6 % | Risque extrême observé sur 14.3 % des dates. | Vérifie si le modèle devient trop dépendant d’un thème chaud ou cyclique. |
| Données | Titres financés avec données faibles | OK | 0.0 % | Part des dates où au moins un titre financé avait une qualité de données faible. | Aide à savoir si les recommandations reposent trop sur des angles morts. |

## Comment l’interpréter

- Cet audit ne choisit pas l’allocation du mois. Il vérifie si le moteur reste sain dans le temps.
- Quand un mode est indiqué, l’audit ignore les analyses faites avec les autres modes.
- Les analyses faites plusieurs fois dans la même journée sont regroupées pour éviter de créer une fausse impression d’historique.
- Avant 4 dates distinctes, les conclusions sont surtout préliminaires. Elles deviennent plus utiles après plusieurs mois de cotisations réelles.
- Une certaine variation est normale: le but n’est pas de figer les mêmes titres, mais d’éviter les changements causés seulement par du bruit de marché.

## Limites

- L’audit mesure la cohérence mécanique du modèle, pas la performance future garantie.
- Si les règles du modèle ont beaucoup changé, l’audit le signale et les anciennes recommandations doivent être interprétées avec prudence.
- Les résultats dépendent des données gratuites, des tickers, des rapports ajoutés et de la qualité du portefeuille saisi.

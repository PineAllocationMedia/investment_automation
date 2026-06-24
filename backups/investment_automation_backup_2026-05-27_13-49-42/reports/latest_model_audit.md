# Audit du modèle d’allocation

- Date de création: 2026-05-24
- Période demandée: all
- Mode analysé: high-cagr
- Historique utilisé: 2 date(s) distincte(s) sur 1 jour(s)
- Dates avec allocation exploitable: 2
- Dates récentes incluses: 2026-05-23, 2026-05-24
- Analyses le même jour regroupées/ignorées pour l’audit: 31
- Versions de règles observées: 2026-05-12-high-cagr-stability-v3 (2)

> Ceci n’est pas un conseil financier. Ce rapport applique seulement les règles mécaniques du guide fourni. Les données gratuites peuvent être incomplètes, retardées ou erronées. Toute décision finale doit être validée manuellement.

## Résumé

- Santé du modèle: **GOOD_BUT_WATCH** (82/100)
- Confiance de l’audit: **PRELIMINARY**
- Revue des seuils: **INSUFFICIENT_HISTORY**
- Titres principaux recommandés au moins une fois: GOOGL
- Conclusion: Le modèle est utilisable, mais il faut continuer de surveiller la volatilité des recommandations, VFV et la concentration.

## Revue des seuils

- Cette section ne modifie pas les règles. Elle indique seulement quels seuils mériteraient une revue manuelle si la tendance se répète.

| section | metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- | --- |
| Revue des seuils | Diagnostic de calibration | INSUFFICIENT_HISTORY | VFV 5.0 %, core 95.0 %, rotation 0.0 % | Pas encore assez de dates avec allocation pour proposer une vraie calibration des seuils. | Suggestion seulement: l’agent ne modifie jamais automatiquement ses règles ou seuils. |
| Revue des seuils | Modification automatique des règles | DISABLED | 0 changement automatique | L’audit observe les règles, mais ne les réécrit jamais tout seul. | Toute modification de seuil doit être validée manuellement après plusieurs mois de données. |
| Revue des seuils | Historique nécessaire | WAIT | 2 date(s) avec allocation | Attendre au moins 4 dates distinctes, idéalement 6 à 12 mois, avant de juger les seuils. | Évite de modifier le modèle sur la base de tests trop rapprochés. |

## Tableau d’audit

| section | metric | status | value | interpretation | impact |
| --- | --- | --- | --- | --- | --- |
| Résumé | Santé du modèle | GOOD_BUT_WATCH | 82/100 | Le modèle est utilisable, avec quelques points à surveiller. | Indique si la mécanique récente semble saine, trop volatile, trop défensive ou trop concentrée. |
| Résumé | Confiance de l’audit | PRELIMINARY | 2 date(s) distincte(s), 2 avec allocation, 1 jour(s) de recul | 2 à 3 dates distinctes: premières tendances seulement. | Plus il y a de dates distinctes espacées dans le temps, plus l’audit est représentatif. |
| Mémoire | Analyses intra-journée regroupées | OK | 31 | Plusieurs tests le même jour comptent comme une seule date de référence. | Évite de biaiser l’audit si tu testes souvent le modèle dans la même journée. |
| Stabilité | Changement du titre principal | OK | 0.0 % | 0 changement(s) du principal titre recommandé. | Un peu de variation est sain; trop de rotation peut signaler une recommandation trop sensible. |
| Stabilité | Rotation moyenne de l’allocation | OK | 0.0 % | Mesure la part moyenne de cotisation qui change de destination entre deux dates. | Aide à détecter une recommandation qui bouge trop sans vraie raison long terme. |
| VFV | Part moyenne VFV | OK | 5.0 % | Fourchette observée: 5.0 % à 5.0 %. | VFV doit servir de filet; une part durablement trop élevée peut devenir trop défensive pour ton profil. |
| VFV | Volatilité VFV | OK | 0.0 % | Variation entre la plus petite et la plus grande part VFV observée. | Permet de voir si VFV monte pour une raison ponctuelle ou si la règle est trop nerveuse. |
| Profil | Exposition core moyenne | STRONG | 95.0 % | Nombre moyen de titres core financés: 3.0. | Mesure si la cotisation va surtout vers des compounders potentiels plutôt que vers le filet VFV. |
| Profil | Qualité moyenne de la recommandation | STRONG | 91.5/100 | Moyenne du score de qualité déjà calculé par l’agent après chaque analyse. | Confirme si les recommandations passées étaient robustes, pas seulement offensives. |
| Risque | Concentration du plus gros bloc | WATCH | 45.0 % | Part moyenne du plus gros titre individuel dans la cotisation. | Un gros bloc est acceptable pour high CAGR, mais l’audit surveille l’excès répété. |
| Risque | Exposition aux cycles/bulles sur titres financés | OK | 0.0 % | Risque extrême observé sur 0.0 % des dates. | Vérifie si le modèle devient trop dépendant d’un thème chaud ou cyclique. |
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

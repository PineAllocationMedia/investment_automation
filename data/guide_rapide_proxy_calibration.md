# Guide rapide pour remplir proxy_calibration.csv

But du fichier :

Ce fichier sert à donner de vraies données fiables à l’agent pour comparer ses estimations automatiques. Vous n’avez pas besoin de tout remplir. Remplissez seulement les données que vous comprenez bien et que vous trouvez dans une source fiable.

Fichier à remplir :

```text
data/proxy_calibration.csv
```

Commande pour l’ouvrir sur Mac :

```bash
open -a TextEdit data/proxy_calibration.csv
```

## Règle générale

- Une ligne = une compagnie.
- Les colonnes qui finissent par `_true` sont les vraies données que vous fournissez.
- Si vous ne trouvez pas une donnée, laissez la case vide. Si vous écrivez `X`, l’agent le traitera aussi comme une donnée manquante.
- Pour les pourcentages, écrivez un nombre simple : `18` veut dire 18 %, pas 0.18.
- Pour les colonnes vrai/faux, écrivez seulement `TRUE` ou `FALSE`.

## Colonnes principales

### ticker

Symbole boursier de la compagnie.

Exemples :

```text
MSFT
MA
AAPL
CSU.TO
WSP.TO
```

Pour les compagnies canadiennes sur Yahoo Finance, utilisez souvent `.TO` ou `.V`.

### company_name

Nom de la compagnie.

Exemple :

```text
Microsoft Corporation
```

Ce champ aide seulement à éviter les erreurs de ticker.

## Données fondamentales

### roic_5y_avg_true

ROIC moyen sur 5 ans.

Si vous ne trouvez pas ROIC, vous pouvez utiliser une donnée proche comme ROE moyen 5 ans, mais écrivez-le dans `notes`.

Format :

```text
22
```

Cela veut dire 22 %.

Interprétation :

- 15 % ou plus = généralement très bon;
- 10 % à 15 % = correct;
- sous 10 % = moins exceptionnel, sauf secteur particulier.

### net_margin_stable_or_expanding_true

Est-ce que la marge nette est stable ou en hausse sur plusieurs années?

Format :

```text
TRUE
FALSE
```

Écrire `TRUE` si les marges sont stables ou s’améliorent.

Écrire `FALSE` si les marges baissent clairement ou deviennent instables.

### eps_growth_5y_true

Croissance historique du bénéfice par action sur 5 ans.

Format :

```text
12
```

Cela veut dire 12 % par an environ.

Si la source donne une croissance totale au lieu d’une croissance annuelle, ne l’utilisez pas sans la convertir.

### eps_growth_estimated_3_5y_true

Croissance estimée du bénéfice par action pour les 3 à 5 prochaines années.

Format :

```text
10
```

Cela veut dire environ 10 % par an.

À utiliser avec prudence, car les prévisions changent. Une source d’analyste récente est préférable.

### sector_cagr_estimated_true

Croissance estimée du secteur, du marché adressable ou de l’industrie.

Format :

```text
8
```

Cela veut dire 8 % par an.

Si vous n’êtes pas certain, laissez vide. Cette donnée est souvent plus difficile à confirmer proprement.

## Valorisation

### forward_pe_true

Forward P/E, soit le prix divisé par le bénéfice prévu.

Format :

```text
28
```

Plus le chiffre est élevé, plus le marché paie cher la croissance future.

### peg_true

PEG ratio.

Format :

```text
1.8
```

Interprétation générale :

- sous 2 = souvent raisonnable;
- 2 à 3 = plus exigeant;
- au-dessus de 3 = valorisation potentiellement très chère.

### fair_value_true

Juste valeur par action selon une source comme Morningstar.

Format :

```text
430
```

Utilisez la devise de la source. Si possible, notez la devise dans `notes`.

### valuation_vs_5y_avg_ok_true

Est-ce que la valorisation actuelle est raisonnable par rapport à sa moyenne historique?

Format :

```text
TRUE
FALSE
```

Écrire `TRUE` si la valorisation n’est pas beaucoup plus chère que sa moyenne 5 ans.

Écrire `FALSE` si elle est clairement plus chère que sa moyenne historique.

## Qualité qualitative

### moat_clear_true

La compagnie a-t-elle un avantage compétitif durable clair?

Format :

```text
TRUE
FALSE
```

Écrire `TRUE` si la source parle d’un moat, d’un avantage compétitif durable, d’un réseau, d’une marque forte, de coûts de changement élevés, d’échelle ou d’un leadership difficile à reproduire.

### forward_pe_growth_acceptable_true

Le P/E est-il acceptable par rapport à la croissance prévue?

Format :

```text
TRUE
FALSE
```

Écrire `TRUE` si la croissance semble justifier la valorisation.

Écrire `FALSE` si la valorisation semble trop élevée même avec la croissance prévue.

### management_quality_good_true

La gestion semble-t-elle bonne?

Format :

```text
TRUE
FALSE
```

Écrire `TRUE` si la compagnie a une bonne allocation du capital, une exécution constante, peu de décisions destructrices et une stratégie claire.

### balance_sheet_strong_true

Le bilan est-il solide?

Format :

```text
TRUE
FALSE
```

Écrire `TRUE` si la dette est raisonnable, la liquidité suffisante et le risque financier faible.

Écrire `FALSE` si la dette est élevée, dangereuse ou si la compagnie dépend fortement du refinancement.

### margin_or_profitability_under_pressure_true

Les marges ou la rentabilité sont-elles sous pression importante?

Format :

```text
TRUE
FALSE
```

Attention : ici `TRUE` signifie qu’il y a un problème.

Écrire `TRUE` si les marges baissent fortement, si les profits se détériorent ou si la rentabilité est sous pression.

Écrire `FALSE` si les marges sont solides ou stables.

## Colonnes de source

### source

Indiquez où vous avez trouvé les données.

Exemples :

```text
Morningstar
BNCD
Rapport annuel
Yahoo Finance
Macrotrends
```

### source_date

Date de la source.

Exemples :

```text
2026-05-01
2025
Q4 2025
```

### confidence

Votre niveau de confiance dans les données.

Utilisez :

```text
HIGH
MEDIUM
LOW
```

Mettez `HIGH` si la donnée vient d’un rapport fiable et récent.

Mettez `MEDIUM` si la donnée semble correcte, mais que vous n’êtes pas parfaitement certain.

Mettez `LOW` si la donnée est approximative.

### notes

Champ libre pour expliquer une nuance.

Exemples :

```text
ROE utilisé car ROIC introuvable
Fair value en USD
Donnée issue du rapport Morningstar du 2026-04-21
```

## Après avoir rempli le fichier

Lancez :

```bash
python3 main.py analyze --capital 500 --mode high-cagr
```

Puis regardez :

```text
reports/latest_proxy_calibration_summary.csv
reports/latest_proxy_calibration.csv
reports/latest_proxy_calibration_history.csv
reports/latest_proxy_bias_report.csv
reports/latest_proxy_correction_audit.csv
```

Le résumé `latest_proxy_calibration_summary.csv` indique si un proxy semble :

- acceptable;
- trop haut;
- trop bas;
- trop incertain;
- candidat à recalibration.

Le détail `latest_proxy_calibration.csv` montre, entreprise par entreprise, la comparaison entre :

- la vraie donnée que vous avez fournie;
- l’estimation automatique du modèle;
- l’écart entre les deux.

Le fichier `latest_proxy_calibration_history.csv` est la mémoire durable. Il garde les exemples fiables dans le temps, même si vous videz ensuite `proxy_calibration.csv`.

Le fichier `latest_proxy_bias_report.csv` répond à une question plus avancée :

```text
Est-ce qu’une formule automatique semble systématiquement trop haute ou trop basse?
```

Ce fichier ne change rien tout seul. Il sert seulement à détecter un biais répété sur plusieurs entreprises.

Le fichier `latest_proxy_correction_audit.csv` surveille les corrections de proxy déjà activées. Il aide à éviter qu’une ancienne correction devienne trop forte, trop vieille ou contredite par de nouvelles vraies données.

## Comment le modèle utilise vos vraies données

Le fonctionnement se fait en 5 étapes :

1. Vous remplissez quelques vraies données fiables dans `data/proxy_calibration.csv`.
2. L’analyse compare ces vraies données avec les estimations automatiques.
3. Les exemples fiables sont conservés dans `data/proxy_calibration_history.csv`.
4. L’agent cherche seulement les biais répétés, cohérents et diversifiés.
5. Une correction peut être proposée plus tard, mais seulement avec des garde-fous stricts.

Important : une seule compagnie ne suffit pas pour recalibrer une formule. Le modèle cherche des tendances répétées sur plusieurs titres.

## Si l’audit propose une correction

Quelques fois par année, vous pouvez lancer :

```bash
python3 main.py improvement-audit --period 12m --mode high-cagr
```

Si l’audit trouve un petit ajustement sécuritaire, il peut proposer une ligne du genre :

```text
proxy_correction:roic_5y_avg
```

Cela veut dire :

```text
Le modèle pense que l’estimation automatique du ROIC pourrait être systématiquement trop haute ou trop basse.
```

Même dans ce cas, la correction n’est pas appliquée librement. Elle doit passer :

- la santé des sources;
- la barrière anti-overfitting;
- le gouverneur de correction;
- les limites de facteur entre 0.75 et 1.25;
- un minimum d’exemples fiables.

Si tout est `SAFE`, vous pouvez appliquer :

```bash
python3 main.py apply-safe-tuning --mode high-cagr
```

L’agent crée alors une sauvegarde, active la correction dans `config/proxy_corrections.yaml`, puis inscrit l’action dans :

```text
data/proxy_correction_history.csv
```

## Comment lire les statuts de correction

Dans `latest_proxy_correction_audit.csv` :

- `DISABLED` : aucune correction active.
- `NO_ACTIVE_CORRECTIONS` : le fichier est activé, mais aucune correction ne modifie les proxies.
- `ACTIVE_OK` : correction active et raisonnable.
- `ACTIVE_NEEDS_MORE_FRESH_EVIDENCE` : correction non contredite, mais il faut plus de données récentes avant de l’élargir.
- `REVIEW_FACTOR_NEAR_LIMIT` : correction proche de la limite maximale; prudence.
- `REVIEW_STALE_CORRECTION` : correction ancienne; à revisiter.
- `REVIEW_NO_LONGER_CONFIRMED` : les nouvelles données ne confirment plus clairement le biais.
- `REVIEW_NOISY_EVIDENCE` : les nouvelles données sont trop bruyantes.
- `REVIEW_CONFLICTING_EVIDENCE` : les nouvelles données pointent dans le sens opposé; revue prioritaire.

Ces statuts ne vendent rien et ne changent pas l’allocation directement. Ils servent à rendre les estimations automatiques plus fiables dans le temps.

## Nettoyer le fichier après utilisation

Après une analyse ou après une correction validée, vous pouvez vider les vraies données du fichier de travail avec :

```bash
python3 main.py clear-proxy-calibration
```

Cette commande vide les vraies valeurs dans `data/proxy_calibration.csv`, mais elle ne supprime pas l’historique durable dans :

```text
data/proxy_calibration_history.csv
```

Donc vous pouvez nettoyer le fichier sans perdre les apprentissages utiles.

## Important

Ne forcez pas une donnée si vous n’êtes pas certain. Une case vide, ou `X`, est préférable à une mauvaise donnée.

Le but est d’améliorer les formules automatiques de l’agent, pas de créer une base de données parfaite.

Le modèle doit apprendre lentement. Une correction responsable doit venir de plusieurs preuves cohérentes, pas d’un seul rapport ou d’une seule entreprise.

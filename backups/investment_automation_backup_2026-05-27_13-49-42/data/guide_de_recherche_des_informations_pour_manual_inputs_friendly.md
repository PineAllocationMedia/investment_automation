# Guide de recherche pour corriger manual_inputs_friendly.txt

Ce guide sert seulement si vous voulez corriger ou confirmer manuellement le fichier optionnel :

```text
data/manual_inputs_friendly.txt
```

Objectif : trouver les informations avec des sources gratuites, fiables et faciles à vérifier.

Important : vous n’êtes plus obligé de remplir ce fichier. L’agent essaie maintenant d’estimer automatiquement ces données avec les sources gratuites disponibles. Ce guide sert à améliorer la précision quand vous voulez vérifier une action importante.

Règle d’or :

Si vous n’êtes pas sûr, laissez le champ vide. L’agent préfère une estimation automatique prudente à une mauvaise donnée manuelle.

## 1. Les sources gratuites à utiliser

Utilisez les sources dans cet ordre.

### Source 1 : Relations investisseurs de l’entreprise

Cherchez sur Google :

```text
MSFT investor relations annual report
```

Remplacez `MSFT` par le ticker voulu.

À chercher :

- annual report;
- quarterly results;
- investor presentation;
- financial statements;
- risk factors.

C’est souvent la meilleure source pour comprendre la thèse, les risques, la marge, la croissance et le bilan.

### Source 2 : SEC EDGAR pour les entreprises américaines

Site officiel :

```text
https://www.sec.gov/edgar/search/
```

Cherchez le ticker.

Documents utiles :

- `10-K` : rapport annuel complet;
- `10-Q` : rapport trimestriel;
- `8-K` : événement important;
- `DEF 14A` : proxy statement, utile pour la direction et la rémunération.

### Source 3 : SEDAR+ pour les entreprises canadiennes

Site officiel :

```text
https://www.sedarplus.ca/
```

À utiliser pour :

- `CSU.TO`;
- `WSP.TO`;
- entreprises canadiennes;
- rapports annuels;
- états financiers annuels;
- notices annuelles.

### Source 4 : Yahoo Finance

Site :

```text
https://finance.yahoo.com/
```

À utiliser pour :

- prix actuel;
- forward P/E;
- PEG;
- beta;
- market cap;
- dividend yield;
- analyst estimates, si disponibles.

Attention : Yahoo Finance peut être incomplet ou parfois erroné. Si une donnée semble bizarre, vérifiez avec une autre source.

### Source 5 : StockAnalysis

Site :

```text
https://stockanalysis.com/
```

Utile pour :

- revenus;
- bénéfices;
- marges;
- ratios;
- historique financier;
- croissance sur plusieurs années.

### Source 6 : rapports annuels et présentations PDF

Quand les sites financiers ne sont pas clairs, revenez au rapport annuel.

Le rapport annuel est plus lent à lire, mais souvent plus fiable.

## 2. Méthode rapide en 20 minutes par entreprise

Pour chaque action :

1. Ouvrez `manual_inputs_friendly.txt`.
2. Ajoutez une section seulement pour l’action que vous voulez corriger, par exemple `[MSFT]`.
3. Ouvrez Yahoo Finance pour le ticker.
4. Notez forward P/E, PEG, prix actuel, market cap et dividend yield si visibles.
5. Ouvrez le site Relations investisseurs de l’entreprise.
6. Téléchargez le dernier rapport annuel.
7. Vérifiez la croissance, les marges, les risques et la dette.
8. Remplissez seulement les champs où vous avez une réponse raisonnablement fiable.
9. Mettez `manual_confidence_level = MEDIUM` si vous n’êtes pas certain.
10. Lancez l’agent et regardez `latest_data_gaps.csv`.

## 3. Comment remplir chaque champ

### roic_5y_avg

Signification :

ROIC moyen sur 5 ans.

Quoi écrire :

Un nombre en pourcentage.

Exemple :

```text
roic_5y_avg = 22
```

Où chercher :

- rapports annuels;
- présentations investisseurs;
- sites de ratios financiers gratuits;
- calcul maison si vous êtes à l’aise.

Règle simple :

- `15` ou plus = très bon;
- sous `10` = moins intéressant;
- si vous ne trouvez pas une donnée fiable, laissez vide.

### net_margin_stable_or_expanding

Signification :

La marge nette est-elle stable ou en amélioration sur environ 5 ans ?

Quoi écrire :

```text
TRUE
```

ou :

```text
FALSE
```

Où chercher :

- income statement dans le rapport annuel;
- StockAnalysis;
- historique des marges sur Yahoo Finance ou autres sites gratuits.

Méthode simple :

Regardez la marge nette actuelle et celle d’il y a environ 5 ans.

Si elle est stable ou meilleure, écrivez `TRUE`.

Si elle baisse clairement, écrivez `FALSE`.

### eps_growth_5y

Signification :

Croissance annuelle moyenne du bénéfice par action sur 5 ans.

Quoi écrire :

Un nombre en pourcentage.

Exemple :

```text
eps_growth_5y = 14
```

Où chercher :

- StockAnalysis;
- rapports annuels;
- Yahoo Finance;
- historique EPS dilué dans les états financiers.

Si l’EPS est irrégulier ou négatif, laissez vide ou mettez une estimation prudente seulement si vous comprenez bien la situation.

### moat_clear

Signification :

L’entreprise a-t-elle un avantage compétitif clair ?

Quoi écrire :

```text
TRUE
```

ou :

```text
FALSE
```

Exemples de moat :

- réseau très difficile à remplacer;
- coûts de changement élevés;
- marque exceptionnelle;
- effets d’échelle;
- propriété intellectuelle;
- position dominante durable;
- distribution difficile à reproduire.

Si vous hésitez beaucoup, laissez vide.

### eps_growth_estimated_3_5y

Signification :

Croissance EPS estimée pour les 3 à 5 prochaines années.

Quoi écrire :

Un nombre en pourcentage.

Exemple :

```text
eps_growth_estimated_3_5y = 12
```

Où chercher :

- Yahoo Finance, section Analysis;
- consensus analystes gratuit si disponible;
- présentations investisseurs;
- guidance de l’entreprise.

Règle prudente :

N’écrivez pas un chiffre agressif juste parce que vous aimez l’entreprise.

Si plusieurs sources donnent des chiffres différents, utilisez le plus prudent.

### sector_cagr_estimated

Signification :

Croissance estimée du secteur ou du marché adressable.

Quoi écrire :

Un nombre en pourcentage.

Exemple :

```text
sector_cagr_estimated = 8
```

Où chercher :

- présentations investisseurs;
- rapports sectoriels gratuits;
- rapports annuels;
- commentaires de management;
- ETF de comparaison comme indice de santé du secteur.

Si vous ne trouvez qu’une estimation promotionnelle, soyez prudent ou laissez vide.

### forward_pe_manual

Signification :

Ratio prix / bénéfices futurs.

Quoi écrire :

Un nombre.

Exemple :

```text
forward_pe_manual = 28
```

Où chercher :

- Yahoo Finance;
- StockAnalysis;
- autres sites financiers gratuits.

Note :

L’agent essaie aussi de récupérer cette donnée automatiquement. Remplissez ce champ surtout si l’automatique est manquant ou faux.

### peg_manual

Signification :

PEG = valorisation comparée à la croissance.

Quoi écrire :

Un nombre.

Exemple :

```text
peg_manual = 1.8
```

Où chercher :

- Yahoo Finance;
- sites de statistiques financières gratuits.

Règle simple :

- autour de `2` ou moins = souvent acceptable;
- au-dessus de `3` = valuation à surveiller fortement.

### fair_value

Signification :

Votre estimation prudente de la juste valeur.

Quoi écrire :

Un prix par action.

Exemple :

```text
fair_value = 420
```

Important :

Ce champ est difficile. Ne l’inventez pas.

Méthodes possibles :

- estimation personnelle prudente;
- moyenne de plusieurs scénarios;
- valorisation basée sur multiples historiques;
- modèle DCF simple si vous savez le faire.

Si vous ne savez pas, laissez vide.

### current_price_manual

Signification :

Prix actuel par action, si l’agent ne réussit pas à le récupérer.

Quoi écrire :

Un prix.

Exemple :

```text
current_price_manual = 390
```

Où chercher :

- Yahoo Finance;
- site de votre courtier;
- Google Finance.

### valuation_vs_5y_avg_ok

Signification :

L’action n’est-elle pas beaucoup plus chère que sa valorisation moyenne des 5 dernières années ?

Quoi écrire :

```text
TRUE
```

ou :

```text
FALSE
```

Méthode simple :

Comparez le P/E ou forward P/E actuel à son historique.

Si le multiple actuel est raisonnablement proche de l’historique, écrivez `TRUE`.

Si le multiple est très au-dessus de l’historique sans justification solide, écrivez `FALSE`.

### catastrophic_fraud

Signification :

Fraude confirmée ou très crédible.

Quoi écrire :

En temps normal :

```text
FALSE
```

Écrivez `TRUE` seulement en cas de problème majeur confirmé.

### catastrophic_moat_lost

Signification :

L’avantage compétitif est perdu.

Exemple :

- disruption évidente;
- perte durable de part de marché;
- produit principal remplacé;
- réseau ou marque fortement abîmés.

En cas de doute, laissez vide ou `FALSE`.

### catastrophic_growth_broken

Signification :

La croissance structurelle est brisée.

Écrivez `TRUE` seulement si la croissance long terme semble vraiment cassée, pas seulement un mauvais trimestre.

### catastrophic_roic_destroyed

Signification :

Le ROIC est durablement détruit.

Écrivez `TRUE` seulement si le rendement sur capital s’est effondré et ne semble pas temporaire.

### catastrophic_dangerous_debt

Signification :

Dette dangereuse.

À vérifier :

- dette très élevée;
- intérêts difficiles à payer;
- refinancement risqué;
- notation de crédit sous pression;
- risque de dilution ou faillite.

### catastrophic_obsolete_business

Signification :

Le modèle d’affaires devient obsolète.

Exemple :

- technologie remplacée;
- demande structurellement en déclin;
- produit principal rendu inutile.

### catastrophic_destructive_management

Signification :

Management destructeur de capital.

Exemples :

- acquisitions très mauvaises;
- dilution excessive;
- fraude;
- décisions contraires aux actionnaires;
- endettement dangereux.

### margin_or_profitability_under_pressure

Signification :

Les marges ou profits sont sous pression.

Quoi écrire :

`TRUE` si les marges baissent clairement ou si la rentabilité est sous pression.

`FALSE` si les marges restent stables ou fortes.

### forward_pe_growth_acceptable

Signification :

Le forward P/E est-il acceptable par rapport à la croissance ?

Exemple :

Une entreprise qui croît lentement avec un P/E de 50 est souvent peu acceptable.

Une entreprise exceptionnelle qui croît vite peut justifier un multiple plus élevé.

Quoi écrire :

```text
TRUE
```

ou :

```text
FALSE
```

### management_quality_good

Signification :

La direction semble-t-elle compétente et alignée avec les actionnaires ?

À vérifier :

- historique d’exécution;
- allocation du capital;
- communication claire;
- acquisitions disciplinées;
- rachat d’actions intelligent;
- faible dilution.

### balance_sheet_strong

Signification :

Le bilan financier est-il solide ?

À vérifier :

- dette raisonnable;
- beaucoup de liquidités;
- flux de trésorerie solides;
- intérêts faciles à payer;
- pas de refinancement urgent.

### regulatory_risk_high

Signification :

Risque réglementaire élevé.

Exemples :

- antitrust;
- prix des médicaments;
- banques;
- énergie;
- défense;
- Chine/Europe/États-Unis.

### geopolitical_risk_high

Signification :

Risque géopolitique élevé.

Exemples :

- Chine / Taïwan;
- guerre commerciale;
- export controls;
- sanctions;
- dépendance à une région sensible.

### single_product_dependency_high

Signification :

L’entreprise dépend fortement d’un seul produit, client ou marché.

Quoi écrire :

`TRUE` si un seul produit ou client peut changer fortement l’avenir de l’entreprise.

### manual_confidence_level

Signification :

Votre confiance dans vos données.

Valeurs acceptées :

```text
HIGH
MEDIUM
LOW
```

Règle simple :

- `HIGH` : vous avez vérifié avec plusieurs sources fiables;
- `MEDIUM` : vous avez une bonne idée, mais pas parfaite;
- `LOW` : vous n’êtes pas très sûr.

### notes

Écrivez vos commentaires personnels.

Exemples :

```text
notes = Moat très fort, mais valorisation élevée.
```

```text
notes = Données à revérifier dans le prochain rapport annuel.
```

## 4. Routine trimestrielle simple

À chaque trimestre :

1. Mettez à jour `portfolio.csv`.
2. Ouvrez `manual_inputs_friendly.txt`.
3. Vérifiez seulement les positions importantes.
4. Corrigez les données devenues fausses.
5. Ajoutez des notes si une thèse change.
6. Lancez :

```bash
python3 main.py analyze --capital 1000 --mode family-office
```

7. Lisez :

```text
reports/latest_report.html
```

8. Regardez surtout :

- allocation recommandée;
- signaux de vente;
- données manquantes;
- risque de concentration;
- comparaison à VFV.TO;
- candidates watchlist/scanner.

## 5. Exemple complet

Exemple fictif pour `MSFT` :

```text
[MSFT]
roic_5y_avg = 25
net_margin_stable_or_expanding = TRUE
eps_growth_5y = 14
moat_clear = TRUE
eps_growth_estimated_3_5y = 12
sector_cagr_estimated = 8
forward_pe_manual = 30
peg_manual = 2.0
fair_value =
current_price_manual =
valuation_vs_5y_avg_ok = TRUE
catastrophic_fraud = FALSE
catastrophic_moat_lost = FALSE
catastrophic_growth_broken = FALSE
catastrophic_roic_destroyed = FALSE
catastrophic_dangerous_debt = FALSE
catastrophic_obsolete_business = FALSE
catastrophic_destructive_management = FALSE
margin_or_profitability_under_pressure = FALSE
forward_pe_growth_acceptable = TRUE
management_quality_good = TRUE
balance_sheet_strong = TRUE
regulatory_risk_high = FALSE
geopolitical_risk_high = FALSE
single_product_dependency_high = FALSE
manual_confidence_level = MEDIUM
notes = Exemple fictif seulement.
```

## 6. Ne pas faire

Ne remplissez pas une donnée au hasard.

Ne mettez pas `TRUE` partout pour forcer un bon score.

Ne mettez pas `fair_value` si vous ne savez pas comment l’estimer.

Ne changez pas une thèse juste parce que le prix baisse.

Une baisse est intéressante seulement si la qualité, la thèse, la croissance, la valorisation et le risque restent solides.

## 7. Sources officielles utiles

SEC EDGAR :

```text
https://www.sec.gov/edgar/search/
```

SEDAR+ :

```text
https://www.sedarplus.ca/
```

Yahoo Finance :

```text
https://finance.yahoo.com/
```

StockAnalysis :

```text
https://stockanalysis.com/
```

Vanguard Canada pour VFV.TO :

```text
https://www.vanguard.ca/
```

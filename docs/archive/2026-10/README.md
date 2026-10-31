# Archives de gouvernance — octobre 2026

Propriétaire : Chief of Staff, sous autorité du CEO.
Créé : 2026-10-31. Échéance de revue de cet index : 2026-11-07.
Ordre de travail : WO-PAM-CLEANUP-ARCHIVE-4-20261031.
Base : `76e0ac428365d799c5eed2619ba3156f0e42ac96`.

## Périmètre et intégrité

Le CEO a autorisé la préparation d’une PR pour ces quatre archives, sans fusion.
Les fichiers historiques réutilisent exactement leurs blobs Git d’origine :
aucune réécriture, normalisation, troncature ni suppression de contenu.
Les anciens chemins deviennent de courts renvois. Aucun autre document existant
n’est modifié; integrated_build, les contrats, le code et les règles restent hors périmètre.

| Source | Archive | Blob Git |
|---|---|---|
| `governance/PAM_CURRENT_STATE.md` | [governance/PAM_CURRENT_STATE.md](governance/PAM_CURRENT_STATE.md) | `c084781c0fbae83d5d02408314b27385afb2334a` |
| `PAM_ROADMAP.md` | [PAM_ROADMAP.md](PAM_ROADMAP.md) | `2f1eeb93c98ad06003efc6562b81e3e92fd9e78d` |
| `governance/PAM_WORKLOG.md` | [governance/PAM_WORKLOG.md](governance/PAM_WORKLOG.md) | `f2c799bdb1d2232dafd1e3813c6675e58fc4a368` |
| `DECISIONS.md` | [DECISIONS.md](DECISIONS.md) | `af3ec7b1e5a8eb637f69e85890a57b7e803a983d` |

## Lecture historique et liens

Ces archives sont des instantanés, pas une description de l’état actuel.
Leur usage comme état courant expire le 2026-10-31; leur conservation historique
est sans suppression automatique. Une date de revue ne révoque aucune décision.
Les décisions et réserves encore applicables restent en vigueur jusqu’à décision du CEO.

Les liens relatifs internes sont conservés comme partie des octets historiques :
ils ne sont pas tous navigables depuis le nouveau dossier. Pour les parcourir
dans leur contexte d’origine, utiliser ces vues figées, puis l’ancre recherchée :

- [governance/PAM_CURRENT_STATE.md à la révision d’origine](https://github.com/PineAllocationMedia/investment_automation/blob/76e0ac428365d799c5eed2619ba3156f0e42ac96/governance/PAM_CURRENT_STATE.md)
- [PAM_ROADMAP.md à la révision d’origine](https://github.com/PineAllocationMedia/investment_automation/blob/76e0ac428365d799c5eed2619ba3156f0e42ac96/PAM_ROADMAP.md)
- [governance/PAM_WORKLOG.md à la révision d’origine](https://github.com/PineAllocationMedia/investment_automation/blob/76e0ac428365d799c5eed2619ba3156f0e42ac96/governance/PAM_WORKLOG.md)
- [DECISIONS.md à la révision d’origine](https://github.com/PineAllocationMedia/investment_automation/blob/76e0ac428365d799c5eed2619ba3156f0e42ac96/DECISIONS.md)

Les liens entrants sans fragment atteignent les renvois aux anciens chemins.
Les anciens fragments n’y sont pas redirigés automatiquement : utiliser les vues
figées ci-dessus. Cette PR ne prétend pas réparer tous les liens historiques.

## Validation et passage de relais

Contrôler l’identité des quatre blobs et le diff limité à neuf chemins Markdown
(quatre archives, quatre renvois et cet index). Classe attendue : DOCS_ONLY.
Réutilisation technologique : NOT APPLICABLE, déplacement documentaire sans composant nouveau.

Garder cette PR en brouillon jusqu’à la préparation du nouveau STATE.md et des
briefings, puis décision explicite de fusion par le CEO. Aucun fichier STATE.md
inexistant n’est présenté comme disponible. L’archivage des rapports terminés
d’integrated_build reste un lot distinct à identifier et faire approuver.
Aucune acceptation de R1, résolution de blocage ou autorisation de nouveau chantier
ne découle de cet archivage.

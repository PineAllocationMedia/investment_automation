# Archives de gouvernance — octobre 2026

**Owner :** Program Manager / Chief of Staff · **Date :** 2026-11-01 · **Work Order :** WO-PAM-CLEANUP-ARCHIVE-4-20261031, périmètre ajusté pour respecter la gouvernance.
**Statut :** PR #441 candidate / non fusionnée; aucune autorité financière ou nouvelle séquence de développement.

## Contenus historiques effectivement archivés

| Chemin vivant (renvoi court) | Archive historique byte-identical | Blob original |
| --- | --- | --- |
| [PAM_ROADMAP.md](../../../PAM_ROADMAP.md) | [PAM_ROADMAP.md](PAM_ROADMAP.md) | `2f1eeb93c98ad06003efc6562b81e3e92fd9e78d` |
| [governance/PAM_CURRENT_STATE.md](../../../governance/PAM_CURRENT_STATE.md) | [governance/PAM_CURRENT_STATE.md](governance/PAM_CURRENT_STATE.md) | `c084781c0fbae83d5d02408314b27385afb2334a` |
| [governance/PAM_WORKLOG.md](../../../governance/PAM_WORKLOG.md) | [governance/PAM_WORKLOG.md](governance/PAM_WORKLOG.md) | `f2c799bdb1d2232dafd1e3813c6675e58fc4a368` |

**Décision de sécurité/gouvernance :** [DECISIONS.md](../../../DECISIONS.md) reste **à son emplacement canonique**, texte intégral inchangé, comme unique registre protégé et append-only. Il n'est ni supprimé, ni remplacé par un renvoi, ni dupliqué dans cette archive. Sa taille reste hors du chemin de lecture ordinaire : consulter seulement les décisions pertinentes.

## Retrouver les ancres d'origine

Les copies d'archives sont volontairement byte-identical, y compris leurs anciens liens relatifs. Certains de ces liens ne se résolvent donc pas à partir du nouvel emplacement; les vues GitHub figées ci-dessous permettent de lire les liens dans leur contexte d'origine et de retrouver une ancienne ancre :

- [Roadmap à l'ancienne position](https://github.com/PineAllocationMedia/investment_automation/blob/76e0ac428365d799c5eed2619ba3156f0e42ac96/PAM_ROADMAP.md)
- [État à l'ancienne position](https://github.com/PineAllocationMedia/investment_automation/blob/76e0ac428365d799c5eed2619ba3156f0e42ac96/governance/PAM_CURRENT_STATE.md)
- [Journal à l'ancienne position](https://github.com/PineAllocationMedia/investment_automation/blob/76e0ac428365d799c5eed2619ba3156f0e42ac96/governance/PAM_WORKLOG.md)

Les anciens liens pointant vers les nouveaux renvois ne redirigent **pas** automatiquement leurs fragments. La PR ne prétend pas réparer exhaustivement l'historique.

## Validation requise avant fusion

1. Comparer trois SHA blobs archivés aux originaux; aucune réécriture de l'historique.
2. Vérifier que la racine [DECISIONS.md](../../../DECISIONS.md) est inchangée.
3. Contrôler les liens locaux des nouveaux STATE, briefings et renvois, ainsi que les vues figées pour les anciens liens.
4. Exécuter `git diff --check` sur le diff réel V2 → PR; aucune copie de DECISIONS.md contenant les espaces historiques n'est ajoutée.
5. Vérifier CI réellement disponible, vérifier la branche à jour, examiner la portée et la capacité de rollback.
6. CEO décide séparément de la fusion; aucun status technique ne confère autorité de merge.

## Nouveau point d'entrée

[STATE.md](../../../STATE.md) · [Briefing Financial Systems](../../briefings/FINANCIAL_SYSTEMS_R1.md) · [Briefing Media](../../briefings/MEDIA_COMMUNICATION.md) · [Briefing Gouvernance](../../briefings/GOVERNANCE_AND_DELIVERY.md).

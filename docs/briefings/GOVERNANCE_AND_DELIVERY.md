# Briefing opérationnel — Gouvernance, livraison et mémoire

**État daté :** 2026-11-01 · **Owner :** Program Manager / Chief of Staff. Ce document n'est pas une charte, une décision CEO, ni un nouveau Work Order.

[Constitution](../../PAM_PROJECT_CONSTITUTION.md) · [Governance](../../governance/PAM_GOVERNANCE.md) · [AGENTS](../../AGENTS.md) · [STATE](../../STATE.md) · [Charte Program Manager](../../governance/roles/PROGRAM_MANAGER.md).

## Règles de reprise

1. Vérifier d'abord le **HEAD réel**, la branche, le Work Order et les éventuels changements concurrents; les SHA d'un briefing sont datés.
2. Charger l'autorité minimale : Constitution, Governance, actuel STATE, charte applicable, contrat de mission. Ne pas lire automatiquement toutes les archives.
3. Respecter les `CEO_PROTECTED`, dont **`DECISIONS.md`** : il reste à la racine le **seul registre canonique et append-only**. Ne créer aucun second registre; une entrée approuvée s'ajoute sans effacer les précédentes.
4. Transmettre un état précis `IMPLEMENTED / VALIDATED / PARTIAL / BLOCKED / NOT_RUN` avec références, limites, propriétaire du prochain contrôle; ne pas combler un manque de preuve par une hypothèse.
5. Pour une modification de documentation, vérifier les blobs et liens; si une archive garde ses octets historiques, référencer l'URL de commit original pour retrouver les ancres relatives au contexte initial.
6. Aucun commit dans les branches canoniques ni fusion sans approbation explicite du CEO. Une PR en brouillon n'est ni acceptation ni déploiement.

## Archive de gouvernance — PR #441

Cette PR vise uniquement les **trois fichiers de mémoire opérationnelle non protégés** : `PAM_ROADMAP.md`, `governance/PAM_CURRENT_STATE.md`, `governance/PAM_WORKLOG.md`. Leurs anciens corps sont archivés **sans modification des octets** sous `docs/archive/2026-10/`; les chemins actifs donnent un renvoi bref vers STATE/briefings et l'archive. Le registre des décisions n'est **pas déplacé** : aucun écart de whitespace propre à sa copie historique n'est créé par le diff final.

**Avant une décision de fusion :** comparer la PR contre V2 à jour; vérifier l'identité des trois blobs archivés, la présence du STATE et des trois briefings, les liens internes des nouveaux textes, l'absence de modification de `DECISIONS.md` et des documents protégés, les contrôles CI effectivement disponibles et les échecs éventuels. Les liens historiques internes aux trois archives ne sont pas réparés : les vues figées de l'index en restituent l'ancien contexte; ne pas revendiquer un passage automatique des ancres.

## Autorités inchangées

V1 `main` gelée, V2 challenger, interdiction de promotion implicite, limite 0 $ de données financières externes, confidentialité, approbation de publication et de transaction au CEO, suspension de l'orchestration unattended selon les restrictions canoniques. La création des briefings ne constitue pas un GO technique ni un chantier suivant.

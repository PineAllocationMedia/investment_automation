# ROADMAP — investment_automation
*Phase: Maturation et validation | Dernière mise à jour: 2026-07-05*

---

## Principes de la phase de maturation

Le projet a transitionné de l'expansion rapide vers la validation.
L'objectif est de maximiser la fiabilité, la robustesse et la confiance
à long terme du système existant — pas d'ajouter de nouveaux modules.

Toute proposition doit répondre à: "Est-ce que cela augmente la confiance
dans les décisions du modèle, ou seulement la complexité du système?"

---

## Section 1 — Accompli (implémenté et validé)

### Infrastructure de base
- DCA bimensuel en mode high-cagr comme stratégie centrale
- Scoring fondamental C1-C10 avec profils métier différenciés
- Allocation gloutonne contrainte (VFV.TO comme filet de sécurité)
- 4 modes: balanced, family-office, rational-aggressive, high-cagr
- Séparation des artéfacts par mode (suffixes stables)
- Walk-forward backtest engine (infrastructure prête)
- Audit snapshot engine, model audit, full audit, improvement audit
- Proxy calibration avec historique durable

### Corrections et robustesse (session 2026-07-05)
- Scoring magnitude continu C1/C3/C5/C6 (version modèle v2)
- Haircut données manquantes + labels COMPLET/PARTIEL_*/PARTIEL_SEVERE
- Gestion exceptions top-level dans run_analysis()
- Alerte staleness données marché dans rapport compact
- Universe snapshotting per run (prérequis walk-forward)
- Commande sync-manual-inputs avec gating staleness Cat.A/B/C
- Alias RHM.DE → RHM.NE
- Défense money()/pct() contre chaînes non-numériques
- Export score_data_gap_* dans latest_scores.csv

### Données confirmées actives
- proxy_calibration.csv rempli pour 15/17 tickers actifs (Morningstar/BNCD)
- manual_inputs_friendly.txt synchronisé via sync-manual-inputs
- Données Cat.A (ROIC, moat) actives pour tous les tickers remplis
- Données Cat.B (fair_value, forward_pe) actives pour tickers avec source_date < 90j

---

## Section 2 — En observation (attente de données)

Ces éléments sont implémentés mais nécessitent de l'évidence accumulée
avant d'être exploitables:

**Walk-forward out-of-sample:**
- Infrastructure: prête (universe_snapshots actifs depuis 2026-07-05)
- Prérequis: 6+ périodes espacées de 14j minimum
- Estimation: opérationnel ~octobre-novembre 2026 au rythme bimensuel
- Action: ne rien modifier — laisser l'évidence s'accumuler

**SCORE_STABILITY:**
- Actuel: UNSTABLE (transition de version v1 → v2 ce jour)
- Attendu: retour à STABLE au prochain run
- Action: aucune — comportement normal après changement de version

**Calibration proxy Cat.B:**
- BAM.TO: source_date périmée (>90j) — mettre à jour Morningstar
- MSFT, LLY: source_date manquante — ajouter 2026-07-05 dans proxy_calibration.csv
- Action: mise à jour manuelle avant prochain run DCA

---

## Section 3 — Explicitement différé (hors scope maturation)

Ces éléments ont été évalués et différés délibérément.
Ne pas proposer ou implémenter sans evidence walk-forward solide:

**Refactoring architectural:**
- Décomposition report_generator.py (385 KB) — Phase 4, après stabilisation
- Décomposition utils.py en sous-modules — Phase 4
- Découplage report_generator via pattern événement/facade — Phase 4

**Nouvelles fonctionnalités:**
- Matrice de corrélation des retours prix — non-mean-variance, hors scope
- Attribution de drawdown par position — informatif mais non prioritaire
- Tracking P&L par lot (cost basis réel) — avant première vente réelle
- Proposition 4B: drift thresholds différenciés high-cagr — besoin évidence
- Proposition 5A: conviction-tiered weight targets — besoin évidence

**Outils de reporting:**
- Refonte complète rapport HTML — après stabilisation du modèle
- Score distribution histogram dans rapport compact — faible priorité

---

## Section 4 — Prochain run DCA

Actions concrètes avant le prochain run bimensuel:

1. Ajouter source_date = 2026-07-05 pour MSFT et LLY dans proxy_calibration.csv
2. Mettre à jour BAM.TO dans proxy_calibration.csv (données périmées)
3. Relancer: python3 main.py sync-manual-inputs
4. Vérifier: SCORE_STABILITY = STABLE (après 1 run propre)
5. Relancer: python3 main.py analyze --refresh-market-data --capital [DCA] --mode high-cagr
6. Vérifier: aucune alerte CALIBRATION DONNÉES MARCHÉ après les updates ci-dessus

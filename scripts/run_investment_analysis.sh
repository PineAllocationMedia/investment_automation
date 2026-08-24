#!/usr/bin/env bash

set -u
set -o pipefail

EXIT_LOCKED=75
DEFAULT_MODE="high-cagr"
DEFAULT_CAPITAL="0"
PRODUCTION_LOG_RETENTION_COUNT="${INVESTMENT_AUTOMATION_PRODUCTION_LOG_RETENTION_COUNT:-100}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${INVESTMENT_AUTOMATION_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
LOG_DIR="${INVESTMENT_AUTOMATION_LOG_DIR:-$HOME/investment_automation_run_logs}"
LOCK_FILE="${INVESTMENT_AUTOMATION_LOCK_FILE:-$HOME/.local/state/investment_automation/operations.lock}"
FLOCK_COMMAND="${INVESTMENT_AUTOMATION_FLOCK_COMMAND:-/usr/bin/flock}"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
TELEGRAM_NOTIFIER="${INVESTMENT_AUTOMATION_TELEGRAM_NOTIFIER:-$SCRIPT_DIR/telegram_notify.py}"
TELEGRAM_CONFIG="${INVESTMENT_AUTOMATION_TELEGRAM_CONFIG:-$HOME/.config/investment_automation/telegram.env}"
TELEGRAM_PYTHON="${INVESTMENT_AUTOMATION_TELEGRAM_PYTHON:-$PYTHON}"
INPUT_SYNC_SCRIPT="${INVESTMENT_AUTOMATION_INPUT_SYNC_SCRIPT:-$SCRIPT_DIR/sync_operational_inputs.py}"
INPUT_SYNC_CONFIG="${INVESTMENT_AUTOMATION_INPUT_SYNC_CONFIG:-$HOME/.config/investment_automation/input_sync.env}"
PORTFOLIO_SYNC_SCRIPT="${INVESTMENT_AUTOMATION_PORTFOLIO_SYNC_SCRIPT:-$SCRIPT_DIR/run_automatic_portfolio_sync.py}"
REQUIRE_PORTFOLIO_SYNC="${INVESTMENT_AUTOMATION_REQUIRE_PORTFOLIO_SYNC:-0}"

mode="$DEFAULT_MODE"
capital="$DEFAULT_CAPITAL"
refresh_market_data=false

usage() {
    printf '%s\n' \
        "Usage: $0 [--capital AMOUNT] [--mode MODE] [--refresh-market-data]" \
        "" \
        "Defaults: --capital $DEFAULT_CAPITAL --mode $DEFAULT_MODE"
}

while (($# > 0)); do
    case "$1" in
        --capital)
            (($# >= 2)) || { echo "Erreur: --capital exige une valeur." >&2; exit 64; }
            capital="$2"
            shift 2
            ;;
        --mode)
            (($# >= 2)) || { echo "Erreur: --mode exige une valeur." >&2; exit 64; }
            mode="$2"
            shift 2
            ;;
        --refresh-market-data)
            refresh_market_data=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Erreur: argument inconnu: $1" >&2
            usage >&2
            exit 64
            ;;
    esac
done

case "$mode" in
    balanced|family-office|rational-aggressive|high-cagr) ;;
    *) echo "Erreur: mode non reconnu: $mode" >&2; exit 64 ;;
esac

if ! [[ "$capital" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "Erreur: le capital doit etre un nombre positif ou nul." >&2
    exit 64
fi

if ! [[ "$PRODUCTION_LOG_RETENTION_COUNT" =~ ^[1-9][0-9]*$ ]]; then
    echo "Erreur: INVESTMENT_AUTOMATION_PRODUCTION_LOG_RETENTION_COUNT doit être un entier positif." >&2
    exit 64
fi

if [[ ! -x "$PYTHON" || ! -f "$PROJECT_ROOT/main.py" ]]; then
    echo "Erreur: projet ou environnement Python introuvable dans $PROJECT_ROOT." >&2
    exit 66
fi

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_FILE")"

if [[ ! -x "$FLOCK_COMMAND" ]]; then
    echo "Erreur: commande flock introuvable ou non executable: $FLOCK_COMMAND" >&2
    exit 69
fi
LOCK_FD=9
exec 9>"$LOCK_FILE" || {
    echo "Erreur: impossible d'ouvrir le verrou partage: $LOCK_FILE" >&2
    exit 73
}
"$FLOCK_COMMAND" --exclusive --nonblock --conflict-exit-code "$EXIT_LOCKED" "$LOCK_FD"
lock_status=$?
if ((lock_status != 0)); then
    if ((lock_status == EXIT_LOCKED)); then
        echo "Une operation Investment Automation est deja active. Analyse non executee." >&2
    else
        echo "Erreur: acquisition du verrou partage impossible (statut $lock_status)." >&2
    fi
    exit "$lock_status"
fi

timestamp="$(date '+%Y%m%d_%H%M%S')"
log_file="$LOG_DIR/analysis_${mode}_${timestamp}.log"

notify_telegram() {
    if [[ ! -f "$TELEGRAM_NOTIFIER" ]]; then
        echo "AVERTISSEMENT: notifier Telegram introuvable: $TELEGRAM_NOTIFIER" | tee -a "$log_file"
        return 0
    fi
    if ! "$TELEGRAM_PYTHON" "$TELEGRAM_NOTIFIER" --config "$TELEGRAM_CONFIG" "$@" >>"$log_file" 2>&1; then
        echo "AVERTISSEMENT: notification Telegram non livrée; le run continue." | tee -a "$log_file"
    fi
}

{
    echo "=== Investment Automation ==="
    echo "Debut: $(date --iso-8601=seconds 2>/dev/null || date)"
    echo "Projet: $PROJECT_ROOT"
    echo "Mode: $mode"
    echo "Capital: $capital"
    echo "Refresh marche: $refresh_market_data"
    echo "Journal: $log_file"
} | tee -a "$log_file"

notify_telegram --message "Analyse $mode démarrée. Capital: ${capital} $. Rafraîchissement marché: ${refresh_market_data}."

cd "$PROJECT_ROOT" || exit 66

echo
source_configured=false
if [[ -n "${INVESTMENT_AUTOMATION_INPUT_SOURCE:-}" || -s "$INPUT_SYNC_CONFIG" ]]; then
    source_configured=true
fi

echo "[1/5] Reconciliation du portefeuille"
if [[ "$REQUIRE_PORTFOLIO_SYNC" == "1" && "$source_configured" != true ]]; then
    echo "ECHEC: source portefeuille requise mais non configuree. Analyse annulee." | tee -a "$log_file"
    notify_telegram --message "ÉCHEC analyse $mode: source portefeuille requise mais non configurée. Aucun rapport produit."
    exit 5
fi
if [[ "$REQUIRE_PORTFOLIO_SYNC" == "1" || "$source_configured" == true ]]; then
    "$PYTHON" "$PORTFOLIO_SYNC_SCRIPT" --config "$INPUT_SYNC_CONFIG" --project-root "$PROJECT_ROOT" 2>&1 | tee -a "$log_file"
    portfolio_sync_status=${PIPESTATUS[0]}
    if ((portfolio_sync_status != 0)); then
        echo "ECHEC: reconciliation du portefeuille impossible. Analyse annulee." | tee -a "$log_file"
        notify_telegram --message "ÉCHEC analyse $mode: réconciliation du portefeuille impossible. Aucun rapport produit."
        exit 5
    fi
else
    echo "Réconciliation désactivée: utilisation locale sans source Drive configurée." | tee -a "$log_file"
fi

echo
echo "[2/5] Synchronisation des autres intrants humains"
if [[ "$source_configured" == true ]]; then
    "$PYTHON" "$INPUT_SYNC_SCRIPT" --config "$INPUT_SYNC_CONFIG" --project-root "$PROJECT_ROOT" --skip-portfolio 2>&1 | tee -a "$log_file"
    sync_status=${PIPESTATUS[0]}
    if ((sync_status != 0)); then
        echo "ECHEC: synchronisation des intrants impossible. Analyse annulee." | tee -a "$log_file"
        notify_telegram --message "ÉCHEC analyse $mode: synchronisation Drive impossible. Aucun rapport produit."
        exit 4
    fi
else
    echo "Synchronisation désactivée: aucune source configurée." | tee -a "$log_file"
fi

echo
echo "[3/5] Validation des intrants"
"$PYTHON" main.py validate-inputs 2>&1 | tee -a "$log_file"
validation_status=${PIPESTATUS[0]}
if ((validation_status != 0)); then
    echo "ECHEC: validate-inputs a echoue. Analyse annulee." | tee -a "$log_file"
    notify_telegram --message "ÉCHEC analyse $mode: validation des intrants impossible. Aucun rapport produit."
    exit 2
fi

echo
echo "[4/5] Analyse"
analysis_args=(main.py analyze --capital "$capital" --mode "$mode" --run-purpose SCHEDULED_DECISION)
if [[ "$refresh_market_data" == true ]]; then
    analysis_args+=(--refresh-market-data)
fi

started_at="$(date +%s)"
"$PYTHON" "${analysis_args[@]}" 2>&1 | tee -a "$log_file"
status=${PIPESTATUS[0]}
if ((status != 0)); then
    echo "ECHEC: analyse terminee avec le statut $status." | tee -a "$log_file"
    notify_telegram --message "ÉCHEC analyse $mode: le moteur a terminé avec le statut $status."
    exit "$status"
fi
elapsed_seconds=$(( $(date +%s) - started_at ))

mode_slug="${mode//-/_}"
compact_report="$PROJECT_ROOT/reports/latest_report_compact_${mode_slug}.md"
if [[ ! -s "$compact_report" ]]; then
    echo "ECHEC: le rapport compact attendu est absent ou vide: $compact_report" | tee -a "$log_file"
    notify_telegram --message "ÉCHEC analyse $mode: rapport compact absent ou vide après le run."
    exit 3
fi

compact_html_report="$PROJECT_ROOT/reports/latest_report_compact_${mode_slug}.html"

stability="$(grep -Eo 'SCORE_STABILITY(_BASELINE|_STABLE|_WATCH|_UNSTABLE)?' "$compact_report" | head -1 || true)"
[[ -n "$stability" ]] || stability="NON_TROUVE"

echo
echo "[5/5] Walk-forward backtest"
"$PYTHON" main.py walk-forward-backtest --mode "$mode" 2>&1 | tee -a "$log_file"
walk_forward_status=${PIPESTATUS[0]}
walk_forward_warning=""
if ((walk_forward_status == 0)); then
    echo "SUCCES: walk-forward termine pour le mode $mode." | tee -a "$log_file"
else
    echo "AVERTISSEMENT: walk-forward echoue avec le statut $walk_forward_status; le rapport d'analyse reste valide." | tee -a "$log_file"
    walk_forward_warning=" AVERTISSEMENT: walk-forward échoué (statut $walk_forward_status)."
fi

{
    echo
    echo "SUCCES: analyse terminee en ${elapsed_seconds}s."
    echo "Rapport: $compact_report"
    echo "Score stability: $stability"
} | tee -a "$log_file"

if [[ -s "$compact_html_report" ]]; then
    notify_telegram \
        --message "SUCCÈS analyse $mode en ${elapsed_seconds}s. Score stability: $stability.${walk_forward_warning}" \
        --document "$compact_html_report" \
        --caption "Rapport compact $mode — capital ${capital} $ — $stability"
else
    notify_telegram --message "SUCCÈS analyse $mode en ${elapsed_seconds}s. Score stability: $stability. Rapport HTML absent; consulter le Markdown local.${walk_forward_warning}"
fi

shopt -s nullglob
log_files=("$LOG_DIR"/analysis_*.log)
if ((${#log_files[@]} > PRODUCTION_LOG_RETENTION_COUNT)); then
    ls -1t "${log_files[@]}" \
        | tail -n "+$((PRODUCTION_LOG_RETENTION_COUNT + 1))" \
        | while IFS= read -r old_log; do rm -f "$old_log"; done
fi

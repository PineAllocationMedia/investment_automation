#!/usr/bin/env bash

set -u
set -o pipefail

EXIT_LOCKED=75
DEFAULT_MODE="high-cagr"
DEFAULT_CAPITAL="0"
LOG_RETENTION_COUNT=20

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${INVESTMENT_AUTOMATION_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
LOG_DIR="${INVESTMENT_AUTOMATION_LOG_DIR:-$HOME/investment_automation_run_logs}"
LOCK_DIR="${INVESTMENT_AUTOMATION_LOCK_DIR:-$HOME/.local/state/investment_automation/analyze.lock}"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
TELEGRAM_NOTIFIER="${INVESTMENT_AUTOMATION_TELEGRAM_NOTIFIER:-$SCRIPT_DIR/telegram_notify.py}"
TELEGRAM_CONFIG="${INVESTMENT_AUTOMATION_TELEGRAM_CONFIG:-$HOME/.config/investment_automation/telegram.env}"
TELEGRAM_PYTHON="${INVESTMENT_AUTOMATION_TELEGRAM_PYTHON:-$PYTHON}"
INPUT_SYNC_SCRIPT="${INVESTMENT_AUTOMATION_INPUT_SYNC_SCRIPT:-$SCRIPT_DIR/sync_operational_inputs.py}"
INPUT_SYNC_CONFIG="${INVESTMENT_AUTOMATION_INPUT_SYNC_CONFIG:-$HOME/.config/investment_automation/input_sync.env}"

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

if [[ ! -x "$PYTHON" || ! -f "$PROJECT_ROOT/main.py" ]]; then
    echo "Erreur: projet ou environnement Python introuvable dans $PROJECT_ROOT." >&2
    exit 66
fi

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_DIR")"

acquire_lock() {
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        printf '%s\n' "$$" >"$LOCK_DIR/pid"
        return 0
    fi

    local existing_pid=""
    if [[ -r "$LOCK_DIR/pid" ]]; then
        existing_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
    fi
    if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
        echo "Analyse deja en cours (PID $existing_pid). Aucun second run lance." >&2
        return "$EXIT_LOCKED"
    fi

    rm -f "$LOCK_DIR/pid"
    if ! rmdir "$LOCK_DIR" 2>/dev/null || ! mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "Erreur: verrou obsolete impossible a recuperer: $LOCK_DIR" >&2
        return "$EXIT_LOCKED"
    fi
    printf '%s\n' "$$" >"$LOCK_DIR/pid"
}

acquire_lock || exit $?

cleanup() {
    rm -f "$LOCK_DIR/pid"
    rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

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
echo "[1/3] Synchronisation des intrants humains"
if [[ -n "${INVESTMENT_AUTOMATION_INPUT_SOURCE:-}" || -s "$INPUT_SYNC_CONFIG" ]]; then
    "$PYTHON" "$INPUT_SYNC_SCRIPT" --config "$INPUT_SYNC_CONFIG" --project-root "$PROJECT_ROOT" 2>&1 | tee -a "$log_file"
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
echo "[2/3] Validation des intrants"
"$PYTHON" main.py validate-inputs 2>&1 | tee -a "$log_file"
validation_status=${PIPESTATUS[0]}
if ((validation_status != 0)); then
    echo "ECHEC: validate-inputs a echoue. Analyse annulee." | tee -a "$log_file"
    notify_telegram --message "ÉCHEC analyse $mode: validation des intrants impossible. Aucun rapport produit."
    exit 2
fi

echo
echo "[3/3] Analyse"
analysis_args=(main.py analyze --capital "$capital" --mode "$mode")
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

{
    echo
    echo "SUCCES: analyse terminee en ${elapsed_seconds}s."
    echo "Rapport: $compact_report"
    echo "Score stability: $stability"
} | tee -a "$log_file"

if [[ -s "$compact_html_report" ]]; then
    notify_telegram \
        --message "SUCCÈS analyse $mode en ${elapsed_seconds}s. Score stability: $stability." \
        --document "$compact_html_report" \
        --caption "Rapport compact $mode — capital ${capital} $ — $stability"
else
    notify_telegram --message "SUCCÈS analyse $mode en ${elapsed_seconds}s. Score stability: $stability. Rapport HTML absent; consulter le Markdown local."
fi

shopt -s nullglob
log_files=("$LOG_DIR"/analysis_*.log)
if ((${#log_files[@]} > LOG_RETENTION_COUNT)); then
    ls -1t "${log_files[@]}" \
        | tail -n "+$((LOG_RETENTION_COUNT + 1))" \
        | while IFS= read -r old_log; do rm -f "$old_log"; done
fi

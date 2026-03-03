#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${OPENCODE_INSIGHTS_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUTPUT_DIR="${ROOT_DIR}/output"
RAW_FILE="${OUTPUT_DIR}/raw_metrics.json"
REPORT_FILE="${OUTPUT_DIR}/report_data.json"
REPORT_HTML="${OUTPUT_DIR}/report.html"

DAYS="14"
PROJECT=""
NARRATIVES="${OUTPUT_DIR}/narratives.json"
OPEN="false"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/generate-insights-report.sh [--days N] [--project ID] [--narratives PATH] [--output PATH] [--open]

Examples:
  ./scripts/generate-insights-report.sh
  ./scripts/generate-insights-report.sh --days 30
  ./scripts/generate-insights-report.sh --project abc123 --open
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days)
      DAYS="$2"
      shift 2
      ;;
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --narratives)
      NARRATIVES="$2"
      shift 2
      ;;
    --output)
      REPORT_HTML="$(realpath -m "$2")"
      OUTPUT_DIR="$(dirname "${REPORT_HTML}")"
      shift 2
      ;;
    --open)
      OPEN="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"
RAW_FILE="${OUTPUT_DIR}/raw_metrics.json"
REPORT_FILE="${OUTPUT_DIR}/report_data.json"
OUTPUT_DIR="$(realpath -m "${OUTPUT_DIR}")"
mkdir -p "${OUTPUT_DIR}"
NARRATIVES="$(realpath -m "${NARRATIVES}")"

if [[ ! -f "${NARRATIVES}" ]]; then
  echo "Missing narratives file: ${NARRATIVES}"
  echo "Generate it from raw metrics first, then rerun this script."
  exit 1
fi

COLLECT_CMD=(python3 "${ROOT_DIR}/src/collector.py" --days "${DAYS}" -o "${RAW_FILE}")
if [[ -n "${PROJECT}" ]]; then
  COLLECT_CMD+=(--project "${PROJECT}")
fi

"${COLLECT_CMD[@]}"

python3 -c "
import json
metrics = json.load(open('${RAW_FILE}'))
narratives = json.load(open('${NARRATIVES}'))
with open('${REPORT_FILE}', 'w', encoding='utf-8') as f:
    json.dump({'metrics': metrics, 'narratives': narratives}, f, indent=2, ensure_ascii=False)
"

python3 "${ROOT_DIR}/src/generator.py" -i "${REPORT_FILE}" -o "${REPORT_HTML}"

echo "Report generated: ${REPORT_HTML}"

if [[ "${OPEN}" == "true" ]]; then
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${REPORT_HTML}" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "${REPORT_HTML}" >/dev/null 2>&1 || true
  fi
fi

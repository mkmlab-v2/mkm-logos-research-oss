#!/usr/bin/env bash
# Move or remove root-level pixel showroom HTML; keep index.html + public_observe_v1.html.
set -euo pipefail

ROOT="${JEMAAI_WEB_ROOT:-/var/www/jemaai}"
LEGACY="${ROOT}/legacy"

echo "[cleanup] root=${ROOT} legacy=${LEGACY}"
mkdir -p "${LEGACY}"

shopt -s nullglob
for f in "${ROOT}"/public_showroom_*.html; do
  base="$(basename "$f")"
  dest="${LEGACY}/${base}"
  if [[ -f "${dest}" ]]; then
    echo "[cleanup] rm duplicate root ${base} (legacy copy exists)"
    rm -f "$f"
  else
    echo "[cleanup] mv ${base} -> legacy/"
    mv "$f" "${dest}"
  fi
done

if [[ -f "${ROOT}/compression_v2_explorer.html" ]]; then
  if [[ -f "${LEGACY}/compression_v2_explorer.html" ]]; then
    rm -f "${ROOT}/compression_v2_explorer.html"
  else
    mv "${ROOT}/compression_v2_explorer.html" "${LEGACY}/"
  fi
fi

echo "[cleanup] root html remaining:"
ls -1 "${ROOT}"/*.html 2>/dev/null || echo "(none)"
echo "[cleanup] legacy html count: $(ls -1 "${LEGACY}"/*.html 2>/dev/null | wc -l)"

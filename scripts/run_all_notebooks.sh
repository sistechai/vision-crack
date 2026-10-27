#!/usr/bin/env bash
# Execute every notebook in order. Stops at the first failure (a failed assert means a result changed).
# Usage: scripts/run_all_notebooks.sh            # full data in data/raw
#        VISIONCRACK_DATA=data/sample scripts/run_all_notebooks.sh 01 02 03 04   # CI subset
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "$#" -gt 0 ]; then
  nbs=(); for n in "$@"; do nbs+=(notebooks/"$n"_*.ipynb); done
else
  nbs=(notebooks/0*.ipynb)
fi

for nb in "${nbs[@]}"; do
  echo "▶ $nb"
  start=$(date +%s)
  jupyter nbconvert --to notebook --execute "$nb" --inplace --ExecutePreprocessor.timeout=600 >/dev/null
  echo "  ✓ $(( $(date +%s) - start )) s"
done
echo "all ${#nbs[@]} notebooks passed"

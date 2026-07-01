#!/usr/bin/env bash
# Hermes Cron Job: Monitor MTGStocks every 6 hours
# Runs: python main.py monitor-sets --min-ev 10.0 --budget 150.00

set -e

cd "$(dirname "$0")/.."

echo "=== Monitor Sets (MTGStocks) ==="
echo "Time: $(date)"
echo ""

.venv/bin/python main.py monitor-sets --min-ev 10.0 --budget 150.00 2>&1 | tee logs/monitor_sets_$(date +%Y%m%d_%H%M%S).log

echo ""
echo "=== Complete ==="

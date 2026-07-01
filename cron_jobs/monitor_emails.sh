#!/usr/bin/env bash
# Hermes Cron Job: Check Gmail for eBay sale notifications every hour
# Runs: python main.py check-emails --record-sales

set -e

cd "$(dirname "$0")/.."

echo "=== Monitor Emails (Gmail Sales) ==="
echo "Time: $(date)"
echo ""

.venv/bin/python main.py check-emails --record-sales 2>&1 | tee logs/monitor_emails_$(date +%Y%m%d_%H%M%S).log

echo ""
echo "=== Complete ==="

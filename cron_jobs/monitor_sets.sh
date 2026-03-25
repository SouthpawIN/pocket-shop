#!/bin/bash
# Pocket Shop - Monitor Sets Cron Job
# Runs every 6 hours to check MTGStocks for high EV sets

set -e

PROJECT_DIR="$HOME/projects/pocket-shop"
cd "$PROJECT_DIR"

echo "=== Pocket Shop Set Monitor ==="
echo "Started at: $(date)"

# Activate virtual environment if it exists
if [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Run the monitor script
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from browser_helpers.mtgstocks_monitor import MTGStocksMonitor

config_path = '$PROJECT_DIR/config.yaml'
try:
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
except:
    config = {'ev_threshold': 10.0}

threshold = config.get('ev_threshold', 10.0)
print(f'Checking MTGStocks for sets with EV >= \${threshold}')

monitor = MTGStocksMonitor()
high_ev_sets = monitor.find_high_ev_sets(threshold=threshold)

if high_ev_sets:
    print(f'\nFound {len(high_ev_sets)} high EV sets:')
    print('-' * 60)
    for set_data in high_ev_sets[:10]:  # Top 10
        print(f'{set_data["name"]}')
        print(f'  EV: \${set_data["ev"]:.2f}')
        print(f'  Buylist EV: \${set_data["buylist_ev"]:.2f}')
        print()
else:
    print('No high EV sets found above threshold.')
"

echo "=== Monitor Complete ==="
echo "Finished at: $(date)"

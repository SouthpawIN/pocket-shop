#!/bin/bash
# Pocket Shop - Email Monitor Cron Job  
# Runs every 15 minutes to check for eBay sale notifications

set -e

PROJECT_DIR="$HOME/projects/pocket-shop"
cd "$PROJECT_DIR"

echo "=== Pocket Shop Email Monitor ==="
echo "Started at: $(date)"

# Activate virtual environment if it exists
if [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Run the email monitor script
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from browser_helpers.gmail_monitor import GmailMonitor
from finance.tracker import FinanceTracker

config_path = '$PROJECT_DIR/config.yaml'
try:
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
except:
    print('Error loading config. Make sure config.yaml exists.')
    sys.exit(1)

print('Checking Gmail for eBay sale notifications...')

monitor = GmailMonitor(config)
sales = monitor.check_for_sales(limit=5)

if sales:
    print(f'\nFound {len(sales)} new sale(s):')
    print('-' * 60)
    
    # Auto-add to finance tracking
    tracker = FinanceTracker(config)
    
    for sale in sales:
        item_name = sale.get('item_name', 'Unknown Item')
        amount = sale.get('amount', 0)
        
        print(f'SALE: {item_name} - \${amount:.2f}')
        
        # Add to finance
        splits = tracker.add_sale(amount, item_name, source='ebay_auto')
        print(f'  +\${splits["savings"]:.2f} to savings')
        print(f'  +\${splits["profit"]:.2f} to profit')  
        print(f'  +\${splits["restock"]:.2f} to restock')
        print()
else:
    print('No new sales found.')
"

echo "=== Email Monitor Complete ==="
echo "Finished at: $(date)"

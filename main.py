#!/usr/bin/env python3
"""Pocket Shop CLI - Main entry point"""

import argparse
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml
except ImportError:
    print("Error: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)


def load_config():
    """Load configuration from config.yaml"""
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        print(f"Error: {config_path} not found.")
        print("Run 'cp config.example.yaml config.yaml' and fill in your values first.")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


class PocketShopCLI:
    def __init__(self):
        self.config = load_config()
        self.finance_path = PROJECT_ROOT / "data" / "finance.json"
        
        # Initialize finance file if it doesn't exist
        if not self.finance_path.parent.exists():
            self.finance_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.finance_path.exists():
            self._init_finance()
    
    def _init_finance(self):
        """Initialize finance tracking file"""
        initial_data = {
            "savings_fund": 0.0,
            "profit_total": 0.0,
            "restock_fund": 0.0,
            "transactions": [],
            "initialized": datetime.now().isoformat()
        }
        with open(self.finance_path, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    def get_finance_data(self):
        """Load finance tracking data"""
        with open(self.finance_path) as f:
            return json.load(f)
    
    def save_finance_data(self, data):
        """Save finance tracking data"""
        with open(self.finance_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def cmd_monitor_sets(self, args):
        """Monitor MTGStocks for high EV sets"""
        print("MTGStocks Monitor - Checking for high EV sets...")
        print(f"Threshold: ${args.threshold or self.config.get('ev_threshold', 10.0)}")
        print()
        print("This would connect to MTGStocks via browser automation.")
        print("Implementation pending - requires Playwright setup.")
    
    def cmd_price(self, args):
        """Get TCGPlayer price for a card"""
        print(f"Looking up price for: {args.name}")
        print(f"Condition: {args.condition}")
        print()
        print("This would connect to TCGPlayer via browser automation.")
        print("Implementation pending - requires Playwright setup.")
    
    def cmd_scan(self, args):
        """Scan a card using phone camera"""
        print(f"Card Scanner - Device: {args.device}")
        print()
        print("This would capture an image from the phone camera")
        print("and use vision AI to identify the card.")
        print("Implementation pending - requires Hermes vision endpoint.")
    
    def cmd_list(self, args):
        """Create eBay listing draft"""
        print(f"Creating listing for: {args.name}")
        print(f"Price: ${args.price}")
        print(f"Quantity: {args.quantity}")
        print()
        print("This would create a draft listing via eBay API.")
        print("Implementation pending - requires eBay OAuth setup.")
    
    def cmd_finance_status(self, args):
        """Show current finance status"""
        data = self.get_finance_data()
        
        print("=" * 50)
        print("POCKET SHOP FINANCE STATUS")
        print("=" * 50)
        print(f"Savings Fund:   ${data['savings_fund']:>12.2f}")
        print(f"Profit Total:   ${data['profit_total']:>12.2f}")
        print(f"Restock Fund:   ${data['restock_fund']:>12.2f}")
        print("-" * 50)
        total = data['savings_fund'] + data['profit_total'] + data['restock_fund']
        print(f"Total Tracked:  ${total:>12.2f}")
        print()
        print(f"Transactions: {len(data['transactions'])}")
        print(f"Initialized: {data.get('initialized', 'Unknown')}")
    
    def cmd_finance_add(self, args):
        """Add a sale transaction"""
        amount = float(args.amount)
        card_name = args.card_name
        
        # Get split ratios
        split = self.config.get('profit_split', {'savings': 0.3, 'profit': 0.3, 'restock': 0.4})
        
        # Calculate splits
        savings_add = amount * split['savings']
        profit_add = amount * split['profit']
        restock_add = amount * split['restock']
        
        # Update finance data
        data = self.get_finance_data()
        data['savings_fund'] += savings_add
        data['profit_total'] += profit_add
        data['restock_fund'] += restock_add
        data['transactions'].append({
            "amount": amount,
            "card_name": card_name,
            "date": datetime.now().isoformat(),
            "splits": {
                "savings": savings_add,
                "profit": profit_add,
                "restock": restock_add
            }
        })
        self.save_finance_data(data)
        
        print(f"Added ${amount:.2f} sale for '{card_name}'")
        print()
        print("Revenue Split:")
        print(f"  +${savings_add:.2f} to savings fund")
        print(f"  +${profit_add:.2f} to profit total")
        print(f"  +${restock_add:.2f} to restock fund")
    
    def cmd_finance_history(self, args):
        """Show transaction history"""
        data = self.get_finance_data()
        transactions = data.get('transactions', [])
        
        print("=" * 70)
        print("TRANSACTION HISTORY")
        print("=" * 70)
        
        if not transactions:
            print("No transactions yet.")
            return
        
        # Show last N transactions (most recent first)
        limit = getattr(args, 'limit', 10) or 10
        for t in reversed(transactions[-limit:]):
            date_str = t['date'][:10] if '.' in t['date'] else t['date']
            print(f"${t['amount']:>8.2f} | {t['card_name']:<30} | {date_str}")
        
        print()
        print(f"Showing last {min(len(transactions), limit)} of {len(transactions)} transactions")
    
    def cmd_monitor_emails(self, args):
        """Check Gmail for sale notifications"""
        print("Gmail Sale Monitor")
        print()
        print("This would check Gmail for eBay sale notification emails")
        print("and automatically add them to finance tracking.")
        print("Implementation pending - requires Gmail credentials.")


def main():
    parser = argparse.ArgumentParser(
        description="Pocket Shop - Automated MTG Card Store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pocket-shop monitor-sets              Check MTGStocks for high EV sets
  pocket-shop price "Lightning Bolt"    Get TCGPlayer price
  pocket-shop scan --device duo         Scan card with phone camera
  pocket-shop list "Black Lotus" --price=50000   Create listing draft
  pocket-shop finance status            Show current balances
  pocket-shop finance add 15.99 "Card Name"      Add sale transaction
  pocket-shop finance history           Show transaction history
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Monitor sets command
    monitor_sets = subparsers.add_parser("monitor-sets", help="Check MTGStocks for high EV sets")
    monitor_sets.add_argument("--threshold", type=float, default=None, 
                             help="EV threshold override")
    
    # Price card command
    price_card = subparsers.add_parser("price", help="Get TCGPlayer price for a card")
    price_card.add_argument("name", help="Card name to price")
    price_card.add_argument("--condition", 
                           choices=["near_mint", "excellent", "good", "light_play", 
                                   "heavy_play", "played"], 
                           default="near_mint")
    
    # Scan card command
    scan_card = subparsers.add_parser("scan", help="Scan a card using phone camera")
    scan_card.add_argument("--device", choices=["duo", "s10", "auto"], default="auto")
    
    # Create listing command
    create_listing = subparsers.add_parser("list", help="Create eBay listing draft")
    create_listing.add_argument("name", help="Card name")
    create_listing.add_argument("--price", type=float, help="Listing price")
    create_listing.add_argument("--quantity", type=int, default=1)
    create_listing.add_argument("--image", help="Path to card image")
    
    # Finance commands
    finance_group = subparsers.add_parser("finance", help="Finance tracking")
    finance_sub = finance_group.add_subparsers(dest="finance_cmd")
    
    fin_status = finance_sub.add_parser("status", help="Show current balances")
    fin_add = finance_sub.add_parser("add", help="Add a sale transaction")
    fin_add.add_argument("amount", type=float)
    fin_add.add_argument("card_name")
    fin_history = finance_sub.add_parser("history", help="Show transaction history")
    fin_history.add_argument("--limit", type=int, default=10)
    
    # Email monitor command
    email_monitor = subparsers.add_parser("monitor-emails", help="Check Gmail for sale notifications")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    cli = PocketShopCLI()
    
    # Route to appropriate command
    if args.command == "monitor-sets":
        cli.cmd_monitor_sets(args)
    elif args.command == "price":
        cli.cmd_price(args)
    elif args.command == "scan":
        cli.cmd_scan(args)
    elif args.command == "list":
        cli.cmd_list(args)
    elif args.command == "finance":
        if args.finance_cmd == "status":
            cli.cmd_finance_status(args)
        elif args.finance_cmd == "add":
            cli.cmd_finance_add(args)
        elif args.finance_cmd == "history":
            cli.cmd_finance_history(args)
        else:
            parser.print_help()
    elif args.command == "monitor-emails":
        cli.cmd_monitor_emails(args)


if __name__ == "__main__":
    main()

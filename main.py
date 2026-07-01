#!/usr/bin/env python3
"""
Pocket Shop CLI — Hackathon v2.0
=================================
Main entry point. Every command calls a real module implementation.

Wired modules:
  scan        → nemotron_vision + auto_card_processor
  price       → scryfall_pricing
  monitor-sets → mtgstocks_discovery
  finance     → finance_tracker
  list        → ebay_api (draft listing)
  monitor-emails → gmail_monitor
  purchase    → stripe_payments
  process     → auto_card_processor (batch)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from hermes_config import get_config, reload_config


class PocketShopCLI:
    """CLI controller — routes commands to real module implementations."""

    def __init__(self):
        self.config = get_config()

    # ─── SCAN: Nemotron vision card identification ───────────────────

    def cmd_scan(self, args):
        """Scan and identify a card using Nemotron 3 Ultra vision."""
        from nemotron_vision import identify_card

        image_path = args.image
        if not Path(image_path).exists():
            print(f"Error: Image not found: {image_path}")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"Scanning: {image_path}")
        print(f"{'='*60}")

        result = identify_card(image_path, provider=args.provider)

        if "error" in result:
            print(f"\n✗ Identification failed: {result['error']}")
            sys.exit(1)

        print(f"\n✓ Card Identified:")
        print(f"  Name:       {result.get('name', 'Unknown')}")
        print(f"  Set:        {result.get('set_name', 'Unknown')} [{result.get('set_code', '?')}]")
        print(f"  Condition:  {result.get('condition', 'Unknown')}")
        print(f"  Foil:       {'Yes' if result.get('is_foil') else 'No'}")
        print(f"  Confidence: {result.get('confidence', '?')}")
        print(f"  Provider:   {result.get('provider_used', '?')}")

        # Auto-price the card via Scryfall
        if args.price:
            print(f"\n{'='*60}")
            print("Pricing via Scryfall...")
            print(f"{'='*60}")
            self._price_card(result.get("name", ""), result.get("set_code", ""))

    # ─── PROCESS: Batch card processing pipeline ─────────────────────

    def cmd_process(self, args):
        """Process multiple card images: identify → price → save."""
        from auto_card_processor import process_batch

        images = args.images
        for img in images:
            if not Path(img).exists():
                print(f"Error: Image not found: {img}")
                sys.exit(1)

        print(f"\nProcessing {len(images)} card(s)...")
        results = process_batch(images, verbose=not args.quiet)

        identified = sum(1 for r in results if "error" not in r.get("identification", {}))
        print(f"\n{'='*60}")
        print(f"Batch complete: {identified}/{len(results)} identified")
        print(f"{'='*60}")

        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w") as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to: {out}")

    # ─── PRICE: Scryfall pricing lookup ──────────────────────────────

    def cmd_price(self, args):
        """Get real-time card pricing from Scryfall API."""
        self._price_card(args.name, args.set or "", show_full=True)

    def _price_card(self, card_name: str, set_code: str = "", show_full: bool = False):
        """Internal: lookup card price via Scryfall."""
        from scryfall_pricing import get_card_pricing, get_market_price

        result = get_card_pricing(card_name, set_code if set_code else None)

        if not result.get("success"):
            print(f"  ✗ Pricing failed: {result.get('error', 'Unknown')}")
            return

        prices = result.get("prices", {})
        usd = prices.get("usd_non_foil")
        usd_foil = prices.get("usd_foil")

        print(f"  Card:   {result.get('card_name', card_name)}")
        print(f"  Set:    {result.get('set_name', '?')} [{result.get('set_code', '?')}]")
        print(f"  Rarity: {result.get('rarity', '?')}")
        print(f"  USD:    ${usd or 'N/A'}")
        if usd_foil:
            print(f"  Foil:   ${usd_foil}")

        if show_full:
            links = result.get("marketplace_links", {})
            if links:
                print(f"\n  Marketplace Links:")
                for name, url in links.items():
                    if url:
                        print(f"    {name}: {url}")

    # ─── MONITOR-SETS: MTGStocks high-EV discovery ───────────────────

    def cmd_monitor_sets(self, args):
        """Discover high-EV MTG sets from MTGStocks."""
        threshold = args.threshold or self.config.get("financial", {}).get("ev_threshold", 10.0)
        budget = self.config.get("financial", {}).get("restock_target", 500.0)

        print(f"\n{'='*60}")
        print("MTGStocks Set Discovery")
        print(f"{'='*60}")
        print(f"  EV threshold:  {threshold}%")
        print(f"  Budget limit:  ${budget:.2f}")

        try:
            from mtgstocks_discovery import MTGStocksDiscovery

            with MTGStocksDiscovery(budget_threshold=budget, min_ev=threshold) as discoverer:
                sets = discoverer.find_high_ev_sets()

                if not sets:
                    print("\nNo sets found matching criteria.")
                    return

                print(f"\nFound {len(sets)} sets:\n")
                print(f"{'#':>3}  {'Set Name':<40}  {'URL'}")
                print("-" * 80)
                for i, s in enumerate(sets, 1):
                    print(f"{i:>3}  {s.get('name', 'Unknown'):<40}  {s.get('url', '')}")

        except ImportError:
            print("\nNote: MTGStocks discovery requires selenium + webdriver-manager.")
            print("Install: pip install selenium webdriver-manager")
        except Exception as e:
            print(f"\nError: {e}")
            print("MTGStocks requires browser automation (Selenium).")

    # ─── LIST: eBay draft listing creation ───────────────────────────

    def cmd_list(self, args):
        """Create an eBay draft listing via API."""
        print(f"\n{'='*60}")
        print("eBay Draft Listing")
        print(f"{'='*60}")
        print(f"  Card:     {args.name}")
        print(f"  Price:    ${args.price}")
        print(f"  Quantity: {args.quantity}")

        if args.image:
            print(f"  Image:    {args.image}")

        try:
            from ebay_api import create_ebay_draft_api

            card_info = {
                "name": args.name,
                "price": args.price,
                "quantity": args.quantity,
                "image_path": args.image,
            }

            result = create_ebay_draft_api(card_info)

            if result.get("success"):
                print(f"\n✓ Draft listing created!")
                print(f"  Listing ID: {result.get('listing_id', 'N/A')}")
                print(f"  URL: {result.get('url', 'N/A')}")
            else:
                print(f"\n✗ Listing failed: {result.get('error', 'Unknown')}")

        except ImportError:
            print("\nNote: eBay listing requires ebay_api module.")
            print("Configure eBay credentials in config.yaml first.")
        except Exception as e:
            print(f"\n✗ Error: {e}")

    # ─── FINANCE: 30/30/40 revenue tracking ─────────────────────────

    def cmd_finance_status(self, args):
        """Show current finance status with 30/30/40 split."""
        from finance_tracker import load_finance_data

        data = load_finance_data()

        print(f"\n{'='*50}")
        print("POCKET SHOP — FINANCE STATUS")
        print(f"{'='*50}")
        print(f"  Savings Fund:  ${data.get('savings_fund', 0):>12.2f}")
        print(f"  Profit Total:  ${data.get('profit_total', 0):>12.2f}")
        print(f"  Restock Fund:  ${data.get('restock_fund', 0):>12.2f}")
        print(f"{'─'*50}")
        total = data.get("savings_fund", 0) + data.get("profit_total", 0) + data.get("restock_fund", 0)
        print(f"  Total:         ${total:>12.2f}")
        print(f"  Total Sales:   ${data.get('total_sales', 0):>12.2f}")
        print(f"  Transactions:  {len(data.get('transactions', []))}")

        sets = data.get("sets_purchased", [])
        if sets:
            print(f"  Sets Bought:   {len(sets)}")
            for s in sets[-3:]:
                print(f"    • {s.get('set_name', '?')} — ${s.get('price', 0):.2f}")

        restock = data.get("restock_fund", 0)
        target = self.config.get("financial", {}).get("restock_target", 500.0)
        if restock >= target:
            print(f"\n  ⚡ Restock fund ready! Can purchase set (${restock:.2f} ≥ ${target:.2f})")
        else:
            pct = (restock / target * 100) if target > 0 else 0
            print(f"\n  Restock progress: {pct:.1f}% (${restock:.2f} / ${target:.2f})")

    def cmd_finance_add(self, args):
        """Record a sale and apply 30/30/40 split."""
        from finance_tracker import record_sale

        amount = float(args.amount)

        print(f"\nRecording sale: ${amount:.2f} — {args.card_name}")
        transaction = record_sale(amount, args.card_name)

        if transaction:
            print(f"\n✓ Sale recorded:")
            print(f"  → Savings (30%): ${transaction['savings']:.2f}")
            print(f"  → Profit  (30%): ${transaction['profit']:.2f}")
            print(f"  → Restock (40%): ${transaction['restock']:.2f}")
        else:
            print("\n✗ Failed to record sale.")

    def cmd_finance_history(self, args):
        """Show transaction history."""
        from finance_tracker import load_finance_data

        data = load_finance_data()
        transactions = data.get("transactions", [])

        print(f"\n{'='*70}")
        print("TRANSACTION HISTORY")
        print(f"{'='*70}")

        if not transactions:
            print("  No transactions yet.")
            return

        limit = args.limit or 10
        print(f"{'Date':<12} {'Amount':>10} {'Item':<35} {'Split (S/P/R)'}")
        print("-" * 70)
        for t in reversed(transactions[-limit:]):
            date = t.get("timestamp", t.get("date", ""))[:10]
            amt = t.get("sale_amount", t.get("amount", 0))
            item = t.get("item", t.get("card_name", "Unknown"))[:35]
            s = t.get("savings", 0)
            p = t.get("profit", 0)
            r = t.get("restock", 0)
            print(f"{date:<12} ${amt:>9.2f} {item:<35} ${s:.0f}/${p:.0f}/${r:.0f}")

        print(f"\nShowing last {min(len(transactions), limit)} of {len(transactions)} transactions")

    # ─── MONITOR-EMAILS: Gmail sale notification tracking ────────────

    def cmd_monitor_emails(self, args):
        """Check Gmail for eBay sale notifications and record them."""
        gmail_cfg = self.config.get("gmail", {})
        email = gmail_cfg.get("email", "")
        password = gmail_cfg.get("app_password", "")

        if not email or not password:
            print("\n✗ Gmail credentials not configured.")
            print("  Set gmail.email and gmail.app_password in config.yaml")
            sys.exit(1)

        from gmail_monitor import check_and_update_sales

        print(f"\n{'='*60}")
        print("Gmail Sale Monitor")
        print(f"{'='*60}")
        print(f"  Account: {email}")

        count = check_and_update_sales(email, password, limit=args.limit or 10)

        print(f"\n✓ Recorded {count} new sale(s) from Gmail.")

    # ─── PURCHASE: Stripe Link supply purchasing ─────────────────────

    def cmd_purchase(self, args):
        """Purchase supplies via Stripe Link (requires approval)."""
        stripe_cfg = self.config.get("stripe", {})
        if not stripe_cfg.get("enabled", False):
            print("\n✗ Stripe payments not enabled.")
            print("  Set stripe.enabled: true in config.yaml")
            sys.exit(1)

        from stripe_payments import purchase_supplies, check_auth_status

        # Check auth first
        auth = check_auth_status()
        if not auth.get("success"):
            print("\n✗ Not authenticated with Stripe Link.")
            print("  Run: link-cli auth login --client-name 'Pocket-Shop'")
            sys.exit(1)

        print(f"\n{'='*60}")
        print("Stripe Link Purchase")
        print(f"{'='*60}")
        print(f"  Item:     {args.item}")
        print(f"  Amount:   ${args.amount:.2f}")
        print(f"  Merchant: {args.merchant}")
        print(f"  URL:      {args.url}")
        print(f"\n  ⏳ This requires approval in the Stripe Link app...")

        result = purchase_supplies(
            item_name=args.item,
            amount_usd=args.amount,
            merchant_name=args.merchant,
            merchant_url=args.url,
        )

        if result.get("success"):
            print(f"\n✓ Purchase request created!")
            print(f"  Request ID: {result.get('data', {}).get('id', 'N/A')}")
            print(f"  Check your Link app to approve.")
        else:
            print(f"\n✗ Purchase failed: {result.get('error', 'Unknown')}")

    # ─── STRIPE-STATUS: Quick Stripe auth check ─────────────────────

    def cmd_stripe_status(self, args):
        """Check Stripe Link authentication status."""
        from stripe_payments import check_auth_status, list_payment_methods, get_daily_spend_summary

        print(f"\n{'='*50}")
        print("Stripe Link Status")
        print(f"{'='*50}")

        auth = check_auth_status()
        if auth.get("success"):
            print("  ✓ Authenticated")
        else:
            print(f"  ✗ Not authenticated: {auth.get('error', 'Unknown')}")
            return

        methods = list_payment_methods()
        if methods.get("success") and methods.get("data"):
            print(f"  Payment methods: {len(methods['data'])}")
        else:
            print("  No payment methods found")

        spend = get_daily_spend_summary()
        if spend.get("success"):
            data = spend.get("data", [])
            if isinstance(data, list):
                print(f"  Spend requests today: {len(data)}")


def main():
    parser = argparse.ArgumentParser(
        description="Pocket Shop v2.0 — Automated MTG Card Trading Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pocket-shop scan card.jpg --price          # Identify + price a card
  pocket-shop process *.jpg --output results.json  # Batch process
  pocket-shop price "Lightning Bolt"         # Get Scryfall pricing
  pocket-shop monitor-sets                   # Find high-EV sets
  pocket-shop list "Black Lotus" --price=50000   # Create eBay listing
  pocket-shop finance status                 # Show 30/30/40 balances
  pocket-shop finance add 15.99 "Sol Ring"   # Record a sale
  pocket-shop finance history --limit 20     # Show transactions
  pocket-shop monitor-emails                 # Check Gmail for sales
  pocket-shop purchase "Sleeves" 12.99 "Store" "https://store.com"
  pocket-shop stripe-status                  # Check Stripe Link auth

Hackathon: Hermes Agent × NVIDIA Nemotron × Stripe
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan = subparsers.add_parser("scan", help="Identify a card using Nemotron vision")
    scan.add_argument("image", help="Path to card image")
    scan.add_argument("--provider", choices=["nemotron", "qwen_omni", "openrouter"], default=None)
    scan.add_argument("--price", action="store_true", help="Also lookup Scryfall pricing")

    # Process (batch)
    process = subparsers.add_parser("process", help="Batch process card images")
    process.add_argument("images", nargs="+", help="Card image paths")
    process.add_argument("--output", help="Save results to JSON file")
    process.add_argument("--quiet", action="store_true")

    # Price command
    price = subparsers.add_parser("price", help="Get Scryfall pricing for a card")
    price.add_argument("name", help="Card name")
    price.add_argument("--set", help="Set code (e.g., 'dsk')")

    # Monitor sets
    monitor = subparsers.add_parser("monitor-sets", help="Discover high-EV MTG sets")
    monitor.add_argument("--threshold", type=float, default=None, help="EV threshold override")

    # Create listing
    listing = subparsers.add_parser("list", help="Create eBay draft listing")
    listing.add_argument("name", help="Card name")
    listing.add_argument("--price", type=float, required=True, help="Listing price")
    listing.add_argument("--quantity", type=int, default=1)
    listing.add_argument("--image", help="Path to card image")

    # Finance commands
    finance = subparsers.add_parser("finance", help="Finance tracking (30/30/40 split)")
    fin_sub = finance.add_subparsers(dest="finance_cmd")

    fin_sub.add_parser("status", help="Show current balances")
    fin_add = fin_sub.add_parser("add", help="Record a sale transaction")
    fin_add.add_argument("amount", type=float)
    fin_add.add_argument("card_name")
    fin_hist = fin_sub.add_parser("history", help="Show transaction history")
    fin_hist.add_argument("--limit", type=int, default=10)

    # Email monitor
    email_mon = subparsers.add_parser("monitor-emails", help="Check Gmail for eBay sales")
    email_mon.add_argument("--limit", type=int, default=10)

    # Stripe purchase
    purchase = subparsers.add_parser("purchase", help="Buy supplies via Stripe Link")
    purchase.add_argument("item", help="Item description")
    purchase.add_argument("amount", type=float, help="Price in USD")
    purchase.add_argument("merchant", help="Merchant name")
    purchase.add_argument("url", help="Merchant URL")

    # Stripe status
    subparsers.add_parser("stripe-status", help="Check Stripe Link auth status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    cli = PocketShopCLI()

    # Route to command handler
    if args.command == "scan":
        cli.cmd_scan(args)
    elif args.command == "process":
        cli.cmd_process(args)
    elif args.command == "price":
        cli.cmd_price(args)
    elif args.command == "monitor-sets":
        cli.cmd_monitor_sets(args)
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
            finance.print_help()
    elif args.command == "monitor-emails":
        cli.cmd_monitor_emails(args)
    elif args.command == "purchase":
        cli.cmd_purchase(args)
    elif args.command == "stripe-status":
        cli.cmd_stripe_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

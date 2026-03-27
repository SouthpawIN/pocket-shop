#!/usr/bin/env python3
"""Pocket Shop - Main Automated Trading Loop

Complete automation cycle:
1. Monitor MTGStocks for high EV sets
2. Research prices across sources (Amazon, MTGGoldfish, TCGPlayer)
3. Purchase sets when profitable (manual confirmation or auto with card)
4. Scan cards with vision when they arrive
5. Price each card with TCGPlayer lookup
6. Create eBay listings
7. Monitor sales and apply 30/30/40 split
8. Loop back when restock fund ready
"""

import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Import modules
from finance_tracker import (
    load_finance_data, save_finance_data, record_sale,
    get_finance_summary, record_set_purchase
)
from mtgstocks_monitor import MTGStocksMonitor
from card_scanner import CardScanner
from tcgplayer_lookup import lookup_card_price, search_tcgplayer
from ebay_listings import eBayListingManager
from gmail_monitor import GmailMonitor, update_finance_from_sales

### CONFIGURATION ###

try:
    import yaml
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
except:
    config = {
        "financial": {"restock_target": 500.00, "ev_threshold": 10.0},
        "gmail": {},
        "ebay": {"mode": "browser"}
    }

SET_PURCHASE_THRESHOLD = config.get("financial", {}).get("restock_target", 500.00)
EV_THRESHOLD = config.get("financial", {}).get("ev_threshold", 10.0)
GMAIL_EMAIL = config.get("gmail", {}).get("email", "")
GMAIL_APP_PASSWORD = config.get("gmail", {}).get("app_password", "")

### MAIN LOOP FUNCTIONS ###

def discover_sets():
    """Step 1: Monitor MTGStocks for high EV sets."""
    print("\n" + "="*60)
    print("STEP 1: Discovering High-EV Sets on MTGStocks")
    print("="*60)
    
    monitor = MTGStocksMonitor(ev_threshold=EV_THRESHOLD)
    sets = monitor.find_high_ev_sets()
    
    if not sets:
        print("No high-EV sets found at current threshold.")
        return []
    
    print(f"\nFound {len(sets)} sets with EV > {EV_THRESHOLD}%:")
    for i, set_data in enumerate(sets[:4], 1):  # Top 4
        print(f"  {i}. {set_data.get('name', 'Unknown')}")
        print(f"     EV: {set_data.get('ev', 0):.1f}% | Buy: ${set_data.get('buy_price', 0):.2f}")
    
    return sets

def research_prices(sets):
    """Step 2: Research actual purchase prices across sources."""
    print("\n" + "="*60)
    print("STEP 2: Researching Prices Across Sources")
    print("="*60)
    
    researched = []
    for set_data in sets:
        set_name = set_data.get('name', 'Unknown')
        print(f"\nResearching: {set_name}")
        
        # Would use browser automation to check each source
        prices = {
            "mtgstocks": set_data.get('buy_price', 0),
            "amazon": None,
            "mtggoldfish": None,
            "tcgplayer": None
        }
        
        available_prices = [p for p in prices.values() if p is not None]
        lowest_price = min(available_prices) if available_prices else None
        
        if lowest_price:
            ev = set_data.get('ev', 0)
            expected_value = lowest_price * (1 + ev/100)
            profit_margin = ((expected_value - lowest_price) / lowest_price) * 100
            
            researched.append({
                **set_data,
                "lowest_price": lowest_price,
                "expected_value": expected_value,
                "profit_margin": profit_margin
            })
    
    researched.sort(key=lambda x: x.get('profit_margin', 0), reverse=True)
    return researched

def check_can_purchase(researched_sets):
    """Check if we can afford any researched sets."""
    summary = get_finance_summary()
    restock_fund = summary['restock_fund']
    
    print(f"\nRestock Fund: ${restock_fund:.2f}")
    print(f"Purchase Threshold: ${SET_PURCHASE_THRESHOLD:.2f}")
    
    affordable = []
    for set_data in researched_sets:
        price = set_data.get('lowest_price', 0)
        if price and price <= restock_fund:
            affordable.append(set_data)
    
    return affordable

def purchase_set(set_data):
    """Step 3: Purchase a set (manual or automated)."""
    print("\n" + "="*60)
    print("STEP 3: Set Purchase")
    print("="*60)
    
    set_name = set_data.get('name', 'Unknown')
    set_code = set_data.get('code', 'UNK')
    price = set_data.get('lowest_price', 0)
    
    print(f"Set: {set_name}")
    print(f"Price: ${price:.2f}")
    print("\n[PURCHASE MODE: Manual confirmation required]")
    print("User should purchase this set from the recommended source.")
    
    return True

def scan_arrived_cards(card_image_paths):
    """Step 4: Scan cards that arrived from purchase."""
    print("\n" + "="*60)
    print("STEP 4: Card Scanning")
    print("="*60)
    
    scanner = CardScanner()
    identified_cards = scanner.batch_scan(card_image_paths)
    
    print(f"\nIdentified {len(identified_cards)} cards:")
    for card in identified_cards[:10]:
        print(f"  - {card.get('name', 'Unknown')} [{card.get('set_code', '?')}]")
    
    return identified_cards

def price_identified_cards(cards):
    """Step 5: Price each identified card."""
    print("\n" + "="*60)
    print("STEP 5: Pricing Cards")
    print("="*60)
    
    priced_cards = []
    for card in cards:
        name = card.get('name', 'Unknown')
        set_code = card.get('set_code')
        
        print(f"Pricing: {name}")
        
        try:
            price = lookup_card_price(name, set_code)
            card['tcgplayer_price'] = price
            priced_cards.append(card)
            print(f"  Price: ${price:.2f}")
        except Exception as e:
            print(f"  Error pricing: {e}")
    
    return priced_cards

def create_ebay_listings(priced_cards):
    """Step 6: Create eBay listings."""
    print("\n" + "="*60)
    print("STEP 6: Creating eBay Listings")
    print("="*60)
    
    ebay_manager = eBayListingManager()
    
    print(f"Creating {len(priced_cards)} listings...")
    results = ebay_manager.bulk_create_listings(priced_cards)
    
    successful = sum(1 for r in results if r.get('success'))
    print(f"Created {successful}/{len(priced_cards)} listings")
    
    return results

def monitor_sales_and_split():
    """Step 7: Monitor sales and apply splits."""
    print("\n" + "="*60)
    print("STEP 7: Sales Monitoring")
    print("="*60)
    
    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        print("Gmail credentials not configured. Skipping sales monitoring.")
        print("Run setup.py to configure Gmail app password.")
        return []
    
    try:
        monitor = GmailMonitor(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        sales = monitor.check_for_sales(limit=10)
        
        if sales:
            print(f"Found {len(sales)} new sales")
            update_finance_from_sales(sales)
            print("Sales recorded with 30/30/40 split applied")
        else:
            print("No new sales found")
        
        return sales
    except Exception as e:
        print(f"Error monitoring sales: {e}")
        return []

def main_loop():
    """Main automated trading loop."""
    print("="*60)
    print("POCKET SHOP - AUTOMATED MTG TRADING LOOP")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        summary = get_finance_summary()
        print(f"\n\n[LOOP CYCLE]")
        print(f"Restock Fund: ${summary['restock_fund']:.2f}")
        print(f"Can afford set: {summary['can_afford_set']}")
        
        # Monitor sales first (always run)
        monitor_sales_and_split()
        
        # Only discover/purchase if we have funds
        if summary['restock_fund'] >= SET_PURCHASE_THRESHOLD:
            sets = discover_sets()
            if sets:
                researched = research_prices(sets)
                affordable = check_can_purchase(researched)
                if affordable:
                    print(f"\nFound {len(affordable)} affordable sets!")
                    # User confirmation would go here
        else:
            print("\nWaiting for restock fund to reach threshold...")
            print("Focus on card scanning, pricing, and listing.")
        
        print("\n[PAUSING - waiting for user action or sales]")
        print("Press Ctrl+C to stop the loop")
        
        try:
            while summary['restock_fund'] < SET_PURCHASE_THRESHOLD:
                time.sleep(60)  # Check every minute
                summary = get_finance_summary()
                print(f"Restock: ${summary['restock_fund']:.2f} / ${SET_PURCHASE_THRESHOLD:.2f}")
        except KeyboardInterrupt:
            print("\nLoop stopped by user.")
            break

if __name__ == "__main__":
    main_loop()

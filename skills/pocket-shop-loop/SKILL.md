---
name: pocket-shop-loop
description: "Main orchestration for automated MTG card trading loop"
trigger_conditions:
  - "Running automated MTG trading business"
  - "User wants to start Pocket-Shop automation"
tools_required:
  - "browser_navigate"
  - "browser_snapshot"
  - "vision_analyze"
  - "read_file"
  - "write_file"
  - "execute_code"
calls_skills:
  - "mtgstocks-set-discovery"
  - "multi-source-price-comparison"
  - "card-scanner-vision"
  - "pocket-shop-finance-tracker"
---

# Pocket Shop Loop - Main Orchestration

## Overview

Main orchestration skill that runs the complete automated MTG card trading loop:
1. **Monitor MTGStocks** for high EV sets under budget
2. **Research prices** across Amazon, MTGGoldfish, TCGPlayer
3. **Purchase sets** when profitable (manual confirmation or auto)
4. **Scan cards** with vision when they arrive
5. **Price each card** with TCGPlayer lookup
6. **Create eBay listings**
7. **Track sales** with 30/30/40 splits
8. **Loop back** when restock fund ready

## Configuration

```python
# Default settings - customize per user
SET_PURCHASE_THRESHOLD = 150.00  # Restock fund target before buying
BUDGET_PER_SET = 200.00          # Max to spend on a single set
MIN_EV_PERCENTAGE = 10.0         # Minimum EV to consider
FINANCE_FILE = "~/.hermes/pocket-shop/finance.json"
```

## Step-by-Step Workflow

### Phase 1: Set Discovery and Research

```python
def discover_and_research_sets():
    """Find high-EV sets and compare prices across sources."""
    from hermes_tools import browser_navigate, browser_snapshot
    
    # Step 1: Navigate to MTGStocks
    print("Step 1: Discovering high-EV sets on MTGStocks...")
    browser_navigate(url="https://mtgstocks.com/sets")
    snapshot = browser_snapshot(full=True)
    page_text = snapshot.get("text", "")
    
    # Parse and filter sets under budget with sufficient EV
    candidates = filter_profitable_sets(page_text, max_price=BUDGET_PER_SET, min_ev=MIN_EV_PERCENTAGE)
    
    if not candidates:
        print(f"No sets found under ${BUDGET_PER_SET} with EV > {MIN_EV_PERCENTAGE}%")
        return []
    
    print(f"Found {len(candidates)} candidate sets")
    
    # Step 2: Research prices across sources
    print("Step 2: Researching prices across retailers...")
    researched = []
    for set_data in candidates:
        researched_result = compare_prices_across_sources(set_data)
        if researched_result:
            researched.append(researched_result)
    
    # Sort by profit margin descending
    researched.sort(key=lambda x: x.get("profit_margin_percent", 0), reverse=True)
    
    return researched[:4]  # Top 4 best opportunities
```

### Phase 2: Purchase Decision

```python
def check_can_purchase(researched_sets):
    """Check if restock fund can afford any researched sets."""
    from pocket_shop_finance_tracker import get_finance_summary
    
    summary = get_finance_summary()
    restock_fund = summary["restock_fund"]
    
    print(f"Restock Fund: ${restock_fund:.2f}")
    print(f"Purchase Threshold: ${SET_PURCHASE_THRESHOLD:.2f}")
    
    affordable = []
    for set_data in researched_sets:
        price = set_data.get("best_price", 0)
        if price and price <= restock_fund:
            affordable.append(set_data)
    
    return affordable
```

### Phase 3: Set Purchase (Manual Confirmation)

```python
def purchase_set(set_data):
    """Purchase a set - requires manual confirmation."""
    set_name = set_data.get("set_name", "Unknown")
    price = set_data.get("best_price", 0)
    source = set_data.get("best_source", "unknown")
    
    print(f"\n{'='*60}")
    print("SET PURCHASE REQUIRED")
    print(f"{'='*60}")
    print(f"Set: {set_name}")
    print(f"Price: ${price:.2f}")
    print(f"Source: {source}")
    print(f"Expected EV: {set_data.get('ev_percentage', 0):.1f}%")
    print(f"Potential Profit: ${set_data.get('potential_profit_dollars', 0):.2f}")
    print("\n[PURCHASE MODE: Manual confirmation required]")
    print("User should purchase this set from the recommended source.")
    print("After purchase arrives, continue to card scanning phase.")
    
    # Wait for user confirmation
    response = input("\nEnter 'confirm' when set has been purchased: ")
    if response.lower() == "confirm":
        from pocket_shop_finance_tracker import record_set_purchase
        record_set_purchase(set_name, set_data.get("set_code", ""), price)
        return True
    return False
```

### Phase 4: Card Scanning (When Sets Arrive)

```python
def scan_arrived_cards(card_image_paths):
    """Scan cards that arrived from purchase."""
    from card_scanner_vision import batch_scan
    
    print(f"\n{'='*60}")
    print("CARD SCANNING PHASE")
    print(f"{'='*60}")
    
    identified_cards = batch_scan(card_image_paths)
    
    print(f"\nIdentified {len(identified_cards)} cards:")
    for card in identified_cards[:10]:  # Show first 10
        print(f"  - {card.get('name', 'Unknown')} [{card.get('set_code', '?')}]")
    
    return identified_cards
```

### Phase 5: Price Identified Cards

```python
def price_identified_cards(cards):
    """Price each identified card using TCGPlayer lookup."""
    from tcgplayer_lookup import lookup_card_price
    
    print(f"\n{'='*60}")
    print("CARD PRICING PHASE")
    print(f"{'='*60}")
    
    priced_cards = []
    for card in cards:
        name = card.get("name", "Unknown")
        set_code = card.get("set_code")
        
        print(f"Pricing: {name}")
        
        try:
            price = lookup_card_price(name, set_code)
            card["tcgplayer_price"] = price
            priced_cards.append(card)
            print(f"  Price: ${price:.2f}")
        except Exception as e:
            print(f"  Error pricing: {e}")
    
    return priced_cards
```

### Phase 6: Create eBay Listings

```python
def create_ebay_listings(priced_cards):
    """Create eBay listings for all priced cards."""
    print(f"\n{'='*60}")
    print("EBAY LISTING PHASE")
    print(f"{'='*60}")
    
    print(f"Ready to list {len(priced_cards)} cards.")
    print("[EBAY LISTING MODE: Manual or API-based]")
    print("\nWould use eBay API or browser automation here.")
    print("Each card would get a draft listing created.")
    
    # TODO: Integrate with eBay API or browser automation
    # For now, this is manual
```

### Phase 7: Monitor Sales and Apply Splits

```python
def record_sale_from_ebay(sale_amount, item_name):
    """Record a sale and apply 30/30/40 split."""
    from pocket_shop_finance_tracker import record_sale
    
    print(f"\n{'='*60}")
    print("SALE RECORDING")
    print(f"{'='*60}")
    
    transaction = record_sale(sale_amount, item_name)
    return transaction
```

### Main Loop Orchestration

```python
def main_pocket_shop_loop():
    """Main automated trading loop."""
    from pocket_shop_finance_tracker import get_finance_summary
    
    print("="*60)
    print("POCKET SHOP - AUTOMATED MTG TRADING LOOP")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        # Check current status
        summary = get_finance_summary()
        restock_fund = summary["restock_fund"]
        
        print(f"\n\n[LOOP CYCLE]")
        print(f"Restock Fund: ${restock_fund:.2f}")
        print(f"Purchase Threshold: ${SET_PURCHASE_THRESHOLD:.2f}")
        print(f"Can afford set: {restock_fund >= SET_PURCHASE_THRESHOLD}")
        
        # Only discover/purchase if we have funds
        if restock_fund >= SET_PURCHASE_THRESHOLD:
            # Phase 1-2: Discover and research sets
            researched_sets = discover_and_research_sets()
            
            if researched_sets:
                affordable = check_can_purchase(researched_sets)
                if affordable:
                    print(f"\nFound {len(affordable)} affordable sets!")
                    # Show top option
                    best_option = affordable[0]
                    print(f"Best option: {best_option['set_name']} - ${best_option['best_price']} from {best_option['best_source']}")
                    print(f"Profit margin: {best_option['profit_margin_percent']:.1f}%")
                    
                    # User confirmation for purchase
                    if input("\nPurchase this set? (y/n): ").lower() == "y":
                        purchase_set(best_option)
        else:
            print("\nWaiting for restock fund to reach threshold...")
            print("Focus on card scanning, pricing, and listing.")
        
        # Wait before next cycle
        print("\n[PAUSING - waiting for user action or sales]")
        print("Press Ctrl+C to stop the loop")
        
        try:
            while restock_fund < SET_PURCHASE_THRESHOLD:
                import time
                time.sleep(60)  # Check every minute
                summary = get_finance_summary()
                restock_fund = summary["restock_fund"]
                print(f"Restock: ${restock_fund:.2f} / ${SET_PURCHASE_THRESHOLD:.2f}")
        except KeyboardInterrupt:
            print("\nLoop stopped by user.")
            break
```

## Running the Loop

```bash
# Start the automated loop
python3 -c "from pocket_shop_loop import main_pocket_shop_loop; main_pocket_shop_loop()"
```

## Cron Job Setup (Optional)

Run discovery automatically daily:

```bash
# Add to crontab
every day at 9 AM:0"
```

## Verification Steps

After each cycle, verify:
- Finance totals are correct (savings + profit + restock = total_sales)
- Sets discovered are under budget with sufficient EV
- Price research found valid prices from at least one source
- Card identification has reasonable confidence (> 0.7)

## Pitfalls & Notes

**Manual purchase confirmation** - Currently requires user to confirm purchases

**eBay integration pending** - Listings currently manual; API integration planned

**Sales monitoring pending** - Need Gmail/eBay polling for automatic sale detection

## Integration Summary

| Phase | Skill Used |
|-------|------------|
| Set Discovery | mtgstocks-set-discovery |
| Price Research | multi-source-price-comparison |
| Card Scanning | card-scanner-vision |
| Finance Tracking | pocket-shop-finance-tracker |
| Orchestration | pocket-shop-loop (this skill) |
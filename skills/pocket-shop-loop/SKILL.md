---
name: pocket-shop-loop
description: "Main orchestration for automated MTG card trading loop"
trigger_conditions:
  - "Running automated MTG trading business"
  - "User wants to start Pocket-Shop automation"
tools_required:
  - "browser_navigate"
  - "browser_snapshot"
  - "terminal"
  - "read_file"
  - "write_file"
calls_skills:
  - "nemotron-vision"
  - "stripe-payments"
  - "pocket-shop-finance-tracker"
---

# Pocket Shop Loop - Main Orchestration (v2.0)

## Overview

Complete automated MTG card trading loop integrated with Stripe payments and NVIDIA Nemotron vision:

1. **Monitor MTGStocks** for high EV sets under budget
2. **Purchase sets** via Stripe Link (human-approved transactions)
3. **Scan cards** with Nemotron 3 Ultra vision when they arrive
4. **Price cards** with Scryfall API
5. **Create eBay listings** via API
6. **Track sales** via Gmail monitoring
7. **Apply 30/30/40 splits** automatically
8. **Loop back** when restock fund reaches threshold

## Architecture

```
main_loop.py
    ├─→ mtgstocks_monitor.py (high EV discovery)
    ├─→ nemotron_vision.py (card identification)
    ├─→ scryfall_pricing.py (pricing)
    ├─→ ebay_api.py (listing creation)
    ├─→ gmail_monitor.py (sale tracking)
    ├─→ finance_tracker.py (30/30/40 splits)
    └─→ stripe_payments.py (supply purchasing)
```

## Configuration

In `config.yaml`:

```yaml
financial:
  restock_target: 150.00    # Fund threshold for purchases
  ev_threshold: 10.0        # Minimum EV percentage
  split:
    savings: 0.30
    profit: 0.30
    restock: 0.40

ebay:
  mode: "api"
  app_id: "..."
  dev_id: "..."
  cert_id: "..."
  refresh_token: "..."

gmail:
  email: "pocket-shop@gmail.com"
  app_password: "..."

stripe:
  enabled: true
  max_purchase_amount: 5000  # $50.00
```

## Step-by-Step Workflow

### Phase 1: Monitor MTGStocks

```bash
# Manual trigger
python main.py monitor-sets --min-ev 10.0 --budget 150.00

# Or via Hermes cron (every 6 hours)
# See cron_jobs/monitor_sets.sh
```

The `mtgstocks_monitor.py` module:
- Scrapes MTGStocks for sealed sets with EV > threshold
- Compares prices across Amazon, MTGGoldfish, TCGPlayer
- Returns top 4 most profitable sets under budget

### Phase 2: Purchase Supplies via Stripe

When restock fund reaches threshold:

```python
from stripe_payments import purchase_supplies

result = purchase_supplies(
    item_name="Booster Box - Modern Horizons 3",
    amount_usd=145.00,
    merchant_name="Amazon",
    merchant_url="https://amazon.com",
    require_approval=True,
)

if result.get("success"):
    print(f"Purchase approved: {result['data']['id']}")
```

**Security**: Every purchase requires human approval in Stripe Link app.

### Phase 3: Scan Cards with Nemotron Vision

When ordered sets arrive:

```bash
# Single card
python main.py scan card.jpg --price

# Batch scan
python main.py process *.jpg --output cards.json
```

The `nemotron_vision.py` module:
1. Encodes image to base64
2. Sends to Nemotron 3 Ultra (fallback: Qwen-Omni → OpenRouter)
3. Parses JSON response with card details
4. Prices via Scryfall API
5. Saves to `data/processed_cards/`

### Phase 4: Create eBay Listings

```python
from ebay_api import create_draft_listing

result = create_draft_listing(
    card_name="Black Lotus",
    set_code="lea",
    price=50000.00,
    condition="Near Mint",
    image_path="card.jpg",
)
```

The `ebay_api.py` module:
- Authenticates via OAuth
- Creates draft listing with structured data
- Returns listing ID for publishing

### Phase 5: Monitor Sales via Gmail

```bash
# Check for new eBay sale notifications
python main.py check-emails --record-sales
```

The `gmail_monitor.py` module:
- Fetches unread eBay sale emails
- Parses sale amount and item name
- Records via `finance_tracker.record_sale()`
- Applies 30/30/40 split automatically

### Phase 6: Finance Tracking

```bash
# View current status
python main.py finance status

# View transaction history
python main.py finance history --limit 20

# Manually record a sale
python main.py finance add 25.00 "Sol Ring" cmr
```

The `finance_tracker.py` module:
- Tracks savings/profit/restock funds
- Records every transaction with timestamp
- Persists to `data/finance.json`
- Enforces 30/30/40 split

### Phase 7: Loop Back

When `restock_fund >= restock_target`:
- Return to Phase 1 (discover new sets)
- Continue the cycle

## Hermes Cron Jobs

Automate the loop with scheduled jobs:

```bash
# Monitor MTGStocks every 6 hours
cron_jobs/monitor_sets.sh

# Check Gmail every hour
cron_jobs/monitor_emails.sh
```

These are Hermes-compatible cron scripts that:
- Run `main.py` commands on schedule
- Log output to `logs/`
- Handle errors gracefully

## Running the Full Loop

```bash
# Interactive mode (manual triggers)
python main_loop.py --interactive

# Automated mode (runs all phases)
python main_loop.py --auto --budget 150.00
```

## Verification Steps

1. **Finance accuracy**: `finance status` shows correct balances
2. **Vision pipeline**: Test with known cards, verify identification
3. **Pricing accuracy**: Compare Scryfall prices to TCGPlayer
4. **Listing creation**: Check eBay drafts have correct data
5. **Sale tracking**: Manually record a sale, verify split
6. **Stripe integration**: Test with low-amount purchase

## Pitfalls

- **Stripe approval delays**: Purchases require human approval (5-10 min)
- **Vision accuracy**: Poor lighting reduces Nemotron confidence
- **eBay rate limits**: Don't create >100 listings/hour
- **Gmail IMAP delays**: Sale emails arrive 1-5 min after sale
- **Scryfall rate limits**: Pricing has 50-100ms rate limit

## Integration Summary

| Phase | Module | Skill |
|-------|--------|-------|
| Discovery | `mtgstocks_monitor.py` | (built-in) |
| Purchasing | `stripe_payments.py` | `stripe-payments` |
| Scanning | `nemotron_vision.py` | `nemotron-vision` |
| Pricing | `scryfall_pricing.py` | (built-in) |
| Listings | `ebay_api.py` | (built-in) |
| Sales | `gmail_monitor.py` | (built-in) |
| Finance | `finance_tracker.py` | `pocket-shop-finance-tracker` |

## Related Skills

- `stripe-payments`: Detailed Stripe Link integration
- `nemotron-vision`: Vision model configuration
- `pocket-shop-finance-tracker`: Finance tracking logic
- `pocket-shop-gmail-monitor`: Gmail email monitoring

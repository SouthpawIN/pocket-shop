---
name: pocket-shop-finance-tracker
description: "Track MTG card trading finances with 30/30/40 revenue split"
trigger_conditions:
  - "Recording sales in Pocket-Shop loop"
  - "Tracking profits and restock fund"
tools_required:
  - "read_file"
  - "write_file"
---

# Pocket Shop Finance Tracker Skill

## Overview

Tracks all financial transactions for the automated MTG trading loop with automatic 30/30/40 revenue splits.

### Revenue Split:
- **30% Savings Fund** - Long-term savings
- **30% Profit Total** - Pure profit accumulation  
- **40% Restock Fund** - Reinvested for next set purchase

## Data Structure

Finance data stored in `~/.hermes/pocket-shop/finance.json`:

```json
{
  "savings_fund": 0.0,
  "profit_total": 0.0,
  "restock_fund": 0.0,
  "total_sales": 0.0,
  "transactions": [],
  "sets_purchased": []
}
```

## Step-by-Step Workflow

### 1. Record a Sale

```python
import json
from pathlib import Path
from datetime import datetime

FINANCE_FILE = Path("~/.hermes/pocket-shop/finance.json").expanduser()

def record_sale(sale_amount, item_name="Unknown Card"):
    """Record sale and apply 30/30/40 split."""
    if FINANCE_FILE.exists():
        with open(FINANCE_FILE) as f:
            data = json.load(f)
    else:
        data = {"savings_fund": 0, "profit_total": 0, "restock_fund": 0, 
                "total_sales": 0, "transactions": []}
    
    savings = sale_amount * 0.30
    profit = sale_amount * 0.30
    restock = sale_amount * 0.40
    
    data["savings_fund"] += savings
    data["profit_total"] += profit
    data["restock_fund"] += restock
    data["total_sales"] += sale_amount
    
    data["transactions"].append({
        "timestamp": datetime.now().isoformat(),
        "item": item_name,
        "sale_amount": sale_amount,
        "savings": savings, "profit": profit, "restock": restock
    })
    
    FINANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FINANCE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Sale Recorded: ${sale_amount:.2f}")
    print(f"  -> Savings (30%): ${savings:.2f}")
    print(f"  -> Profit (30%): ${profit:.2f}")
    print(f"  -> Restock (40%): ${restock:.2f}")
```

### 2. Check Finance Summary

```python
def get_finance_summary():
    if FINANCE_FILE.exists():
        with open(FINANCE_FILE) as f:
            return json.load(f)
    return {"savings_fund": 0, "profit_total": 0, "restock_fund": 0}
```

### 3. Check if Can Afford Set Purchase

```python
def can_afford_set(set_price, threshold=150):
    data = get_finance_summary()
    return data["restock_fund"] >= threshold and data["restock_fund"] >= set_price
```

## Example Usage

```python
record_sale(50.00, "Black Lotus Replica")
# Output:
# Sale Recorded: $50.00
#   -> Savings (30%): $15.00
#   -> Profit (30%): $15.00  
#   -> Restock (40%): $20.00

if can_afford_set(150, threshold=150):
    print("Ready to purchase next set!")
```

## Verification Steps

- Total of all three funds equals total_sales * 1.0 (all money accounted for)
- Each transaction has correct 30/30/40 split
- Restock fund decreases when sets purchased, increases with sales
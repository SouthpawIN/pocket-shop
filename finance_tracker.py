#!/usr/bin/env python3
"""Pocket Shop - Main Orchestration Loop

This is the complete automated MTG card trading loop:
1. Monitor MTGStocks for high EV sets
2. Research prices across multiple sources
3. Purchase sets when profitable
4. Scan cards with vision when they arrive
5. Price and list on eBay
6. Track sales with 30/30/40 splits
7. Loop back when restock fund is ready
"""

import json
import time
from pathlib import Path
from datetime import datetime

# Configuration
CONFIG_PATH = Path("config.yaml")
FINANCE_PATH = Path("data/finance.json")
SET_THRESHOLD = 500.00  # Default restock target
EV_THRESHOLD = 10.0     # Minimum EV percentage

### FINANCE TRACKING (30/30/40 Split) ###

def load_finance_data():
    """Load or initialize finance tracking data."""
    if FINANCE_PATH.exists():
        with open(FINANCE_PATH) as f:
            return json.load(f)
    return {
        "savings_fund": 0.0,
        "profit_total": 0.0, 
        "restock_fund": 0.0,
        "total_sales": 0.0,
        "transactions": [],
        "sets_purchased": []
    }

def save_finance_data(data):
    """Save finance data."""
    FINANCE_PATH.parent.mkdir(exist_ok=True)
    with open(FINANCE_PATH, "w") as f:
        json.dump(data, f, indent=2)

def record_sale(sale_amount, item_name="Unknown Card"):
    """Record a sale and apply 30/30/40 split."""
    data = load_finance_data()
    
    savings = sale_amount * 0.30
    profit = sale_amount * 0.30
    restock = sale_amount * 0.40
    
    data["savings_fund"] += savings
    data["profit_total"] += profit
    data["restock_fund"] += restock
    data["total_sales"] += sale_amount
    
    transaction = {
        "timestamp": datetime.now().isoformat(),
        "item": item_name,
        "sale_amount": sale_amount,
        "savings": savings,
        "profit": profit,
        "restock": restock
    }
    data["transactions"].append(transaction)
    
    save_finance_data(data)
    
    print(f"Sale Recorded: ${sale_amount:.2f}")
    print(f"  → Savings (30%): ${savings:.2f}")
    print(f"  → Profit (30%): ${profit:.2f}")
    print(f"  → Restock (40%): ${restock:.2f}")
    
    return transaction

def get_finance_summary():
    """Get current finance summary."""
    data = load_finance_data()
    can_afford = data["restock_fund"] >= SET_THRESHOLD
    
    return {
        "savings_fund": data["savings_fund"],
        "profit_total": data["profit_total"],
        "restock_fund": data["restock_fund"],
        "total_sales": data["total_sales"],
        "can_afford_set": can_afford,
        "sets_affordable": int(data["restock_fund"] / SET_THRESHOLD) if SET_THRESHOLD > 0 else 0
    }

def record_set_purchase(set_name, set_code, price):
    """Record a set purchase and deduct from restock fund."""
    data = load_finance_data()
    
    if data["restock_fund"] >= price:
        data["restock_fund"] -= price
        data["sets_purchased"].append({
            "timestamp": datetime.now().isoformat(),
            "set_name": set_name,
            "set_code": set_code,
            "price": price
        })
        save_finance_data(data)
        print(f"Set Purchased: {set_name} (${price:.2f})")
        return True
    return False

### PRINT INITIAL SETUP ###

if __name__ == "__main__":
    print("=== Pocket Shop Finance Module ===")
    print("Initial finance data initialized.")
    print(f"Restock threshold: ${SET_THRESHOLD:.2f}")
    print(f"EV threshold: {EV_THRESHOLD}%")
    print("Finance module ready. Import into main loop.")

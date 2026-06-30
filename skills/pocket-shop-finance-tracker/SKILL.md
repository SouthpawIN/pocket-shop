---
name: pocket-shop-finance-tracker
description: "Track MTG card trading finances with automatic 30/30/40 revenue splits (savings / profit / restock fund). Persists state via memory and data/finance.json."
version: 1.0.0
author: SouthpawIN
license: MIT
platforms:
  - linux
tags:
  - mtg
  - finance
  - tracking
  - revenue-split
  - pocket-shop
---

# Pocket Shop Finance Tracker

<!-- hermes.tags: mtg, finance, revenue-split, savings, profit, restock, tracking -->
<!-- hermes.related_skills: pocket-shop-loop, card-scanner-vision -->

This skill manages all financial tracking for the Pocket Shop MTG trading system. Every sale is automatically split 30/30/40 into savings, profit, and restock fund. State is persisted in both `data/finance.json` (structured data) and Hermes **memory** (for quick cross-session access).

## When to Use

- Recording a sale from eBay (the **pocket-shop-loop** skill calls this after each sale)
- Recording a set purchase (deducted from restock fund)
- Checking the current finance summary ("how much is in the restock fund?")
- Determining whether the restock fund has reached the purchase threshold
- Reviewing transaction history

## Revenue Split (30/30/40)

| Fund | Percentage | Purpose |
|------|-----------|---------|
| Savings Fund | 30% | Long-term savings, untouchable |
| Profit Total | 30% | Pure profit accumulation |
| Restock Fund | 40% | Reinvested for next set purchase |

Example: A $50.00 sale → $15.00 savings + $15.00 profit + $20.00 restock.

## Data Structure

Finance state is stored in `data/finance.json`:

```json
{
  "savings_fund": 45.00,
  "profit_total": 45.00,
  "restock_fund": 60.00,
  "total_sales": 150.00,
  "transactions": [
    {
      "timestamp": "2026-06-29T14:30:00",
      "item": "Lightning Bolt",
      "sale_amount": 50.00,
      "savings": 15.00,
      "profit": 15.00,
      "restock": 20.00
    }
  ],
  "sets_purchased": [
    {
      "timestamp": "2026-06-28T10:00:00",
      "set_name": "Modern Horizons 3",
      "set_code": "MH3",
      "amount": 156.00
    }
  ]
}
```

## Steps

### Step 1 — Load Current Finance State

Read the finance file to get the current state:

```
read_file: data/finance.json
```

If the file does not exist (first run), initialize it with all fields at 0.0 and empty arrays.

Also check **memory** for a quick summary:

```
memory: recall "pocket_shop_finance_summary"
```

### Step 2 — Record a Sale

Use the finance tracker script via **terminal**:

```
terminal: python3 finance_tracker.py --record-sale --item "Lightning Bolt" --amount 50.00
```

This script:
1. Loads the current finance state
2. Applies the 30/30/40 split
3. Adds the transaction to the `transactions` array
4. Updates all fund totals
5. Writes back to `data/finance.json`

Alternatively, do it manually with **read_file** + **write_file**:

1. **read_file** `data/finance.json`
2. Calculate: `savings = amount × 0.30`, `profit = amount × 0.30`, `restock = amount × 0.40`
3. Add the transaction object to the `transactions` array
4. Update `savings_fund`, `profit_total`, `restock_fund`, and `total_sales`
5. **write_file** the updated JSON back to `data/finance.json`

### Step 3 — Record a Set Purchase

When a set is purchased, deduct from the restock fund:

```
terminal: python3 finance_tracker.py --record-purchase --set "Modern Horizons 3" --amount 156.00
```

Or manually:

1. **read_file** `data/finance.json`
2. Subtract the purchase amount from `restock_fund`
3. Add the purchase to the `sets_purchased` array
4. **write_file** the updated JSON

### Step 4 — Check Finance Summary

Get a full summary of all funds:

```
terminal: python3 finance_tracker.py --summary
```

Output should show:
- Savings Fund: $XX.XX
- Profit Total: $XX.XX
- Restock Fund: $XX.XX
- Total Sales: $XX.XX
- Number of transactions
- Number of sets purchased

### Step 5 — Check Purchase Readiness

Determine if the restock fund can afford a new set:

```
terminal: python3 finance_tracker.py --can-afford --threshold 150
```

This returns true if `restock_fund >= threshold`. Use this to decide whether to proceed with set discovery and purchasing.

### Step 6 — Persist Summary to Memory

After any finance update, save a summary to **memory** for fast cross-session access:

```
memory: store "pocket_shop_finance_summary" with values:
  - savings_fund: <current_value>
  - profit_total: <current_value>
  - restock_fund: <current_value>
  - total_sales: <current_value>
  - last_updated: <current_timestamp>
```

This lets the **pocket-shop-loop** skill check finance state quickly without re-reading the JSON file.

### Step 7 — View Transaction History

List all recorded transactions:

```
terminal: python3 finance_tracker.py --history
```

Or read the `transactions` array from `data/finance.json` via **read_file** and display each entry.

### Step 8 — View Sets Purchased

List all sets that have been purchased:

```
terminal: python3 finance_tracker.py --sets-purchased
```

## Pitfalls

- **Concurrent writes** — if two processes (e.g., a cron job and a manual run) write to `data/finance.json` simultaneously, data can be lost. Always read-modify-write as an atomic sequence; consider using a lock file.
- **Rounding errors** — floating-point arithmetic on dollars can produce values like $14.999999999. The `finance_tracker.py` script should round to 2 decimal places; if doing it manually via **write_file**, round explicitly.
- **Negative restock fund** — if purchases exceed restock (e.g., user adds external money), `restock_fund` can go negative. This is valid; track it but warn the user.
- **Memory vs. file desync** — if a sale is recorded via `finance_tracker.py` but the memory update is skipped, the memory summary will be stale. Always update both.
- **Missing finance.json on first run** — the file won't exist initially. Create it with all zeroes and empty arrays before any read operations.
- **Transaction history grows unbounded** — over time, the `transactions` array can become very large. Consider archiving old transactions (e.g., move entries older than 90 days to `data/finance_archive.json`).

## Verification

- **Conservation of money**: `savings_fund + profit_total + restock_fund` should equal `total_sales` minus total set purchases (within $0.01 rounding tolerance).
- Each transaction's split should satisfy: `savings + profit + restock == sale_amount` (within $0.01).
- After recording a sale, `total_sales` should increase by exactly the sale amount.
- After recording a purchase, `restock_fund` should decrease by exactly the purchase amount.
- The **memory** summary should match the `data/finance.json` file contents.
- Transaction count should equal the length of the `transactions` array.

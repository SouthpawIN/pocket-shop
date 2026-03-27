---
name: mtgstocks-set-discovery
description: "Monitor MTGStocks for Magic sets with high Expected Value under budget"
trigger_conditions:
  - "Searching for profitable MTG set investments"
  - "Running automated trading loop"
tools_required:
  - "browser_navigate"
  - "browser_snapshot"
  - "browser_click"
  - "browser_scroll"
---

# MTGStocks Set Discovery Skill

## Overview

Monitors **MTGStocks.com** to find Magic: The Gathering sealed product sets with high Expected Value (EV) percentages under a configurable budget threshold.

### What it does:
- Navigates to MTGStocks sets page using browser automation
- Extracts set names, EV percentages, and buy prices
- Filters by budget (default $200) and minimum EV (default 10%)
- Returns top 3-4 most profitable set candidates

## Hermes Tools Used

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Navigate to MTGStocks.com/sets |
| `browser_snapshot` | Extract set data from page |
| `browser_click` | Interact with sort/filter controls |
| `browser_scroll` | Load more sets into viewport |

## Step-by-Step Workflow

### 1. Configure Budget Parameters

```python
# Default configuration - adjust per user needs
BUDGET_THRESHOLD = 200.00  # Max set price to consider
MIN_EV_PERCENTAGE = 10.0   # Minimum EV to qualify
TOP_N_RESULTS = 4          # Return top N sets
```

### 2. Navigate to MTGStocks Sets Page

```python
from hermes_tools import browser_navigate, browser_snapshot

browser_navigate(url="https://mtgstocks.com/sets")
```

### 3. Extract Set Data from Page

```python
# Get full page snapshot
snapshot = browser_snapshot(full=True)
page_text = snapshot.get("text", "")

# Parse set names, EV percentages, and prices from page
# MTGStocks shows sets with format like:
# "Set Name - EV: 15.2% - Buy Price: $45.00"
```

### 4. Filter by Budget and EV Threshold

```python
import re

def filter_profitable_sets(page_text, max_price=200, min_ev=10):
    """Filter sets under budget with sufficient EV."""
    sets = []
    # Pattern to match set data in page text
    pattern = r'([A-Za-z\s&]+?)\s*-?\s*EV:\s*([\d.]+)%.*?Buy\s*Price:\s*\$([\d,]+)'
    matches = re.findall(pattern, page_text, re.DOTALL)
    
    for match in matches:
        name, ev_str, price_str = match
        ev = float(ev_str)
        price = float(price_str.replace(',', ''))
        
        if price <= max_price and ev >= min_ev:
            sets.append({
                "name": name.strip(),
                "ev_percentage": ev,
                "buy_price": price,
                "expected_value": price * (1 + ev/100)
            })
    
    # Sort by EV descending, return top N
    sets.sort(key=lambda x: x["ev_percentage"], reverse=True)
    return sets[:TOP_N_RESULTS]
```

### 5. Return Top Results

Returns dictionary with discovered sets:

```python
{
    "sets_found": [
        {
            "name": "Modern Horizons 3",
            "ev_percentage": 24.5,
            "buy_price": 156.00,
            "expected_value": 194.22,
            "potential_profit": 38.22
        },
        # ... top 4 sets
    ],
    "search_parameters": {
        "max_price": 200.00,
        "min_ev": 10.0
    }
}
```

## Verification Steps

After discovery, verify:
- Set names are recognizable MTG sets
- EV percentages are realistic (5-50% range typically)
- Buy prices match budget constraints
- At least one set found under threshold

## Pitfalls & Notes

**MTGStocks requires JavaScript rendering** - Use browser automation, not simple HTTP requests

**EV calculation varies by source** - MTGStocks EV is based on historical sell-through data

**Set availability fluctuates** - A set showing high EV today may be sold out tomorrow

## Example Usage in Main Loop

```python
# Discover sets under $200 with EV > 10%
browser_navigate(url="https://mtgstocks.com/sets")
snapshot = browser_snapshot(full=True)
page_text = snapshot.get("text", "")

candidates = filter_profitable_sets(page_text, max_price=200, min_ev=10)

if candidates:
    print(f"Found {len(candidates)} high-EV sets under $200")
    for set_data in candidates:
        print(f"  - {set_data['name']}: EV {set_data['ev_percentage']}%, Price ${set_data['buy_price']}")
```

## Integration with Other Skills

This skill feeds into:
1. **multi-source-price-comparison** - Compare discovered sets across retailers
2. **pocket-shop-loop** - Main orchestration calls this first
3. **cron job** - Can run discovery periodically (e.g., daily at 9 AM)

## Testing

```python
# Quick test - does MTGStocks load?
browser_navigate(url="https://mtgstocks.com/sets")
snapshot = browser_snapshot(full=False)

if "Sets" in snapshot.get("text", ""):
    print("MTGStocks page loaded successfully")
```
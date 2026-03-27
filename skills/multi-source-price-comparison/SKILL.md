---
name: multi-source-price-comparison
description: "Compare MTG set prices across Amazon, MTGGoldfish, TCGPlayer for best deal"
trigger_conditions:
  - "Researching best price for MTG sets"
  - "After discovering high-EV sets on MTGStocks"
tools_required:
  - "browser_navigate"
  - "browser_snapshot"
  - "web_search"
---

# Multi-Source Price Comparison Skill

## Overview

Compares actual purchase prices for Magic: The Gathering sealed sets across multiple retailers to find the best real profit margin.

### Sources Compared:
1. **MTGStocks** - Already have from discovery phase
2. **Amazon** - Often has competitive pricing on sealed product
3. **MTGGoldfish** - Marketplace with various sellers
4. **TCGPlayer** - Largest MTG marketplace

## Hermes Tools Used

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Visit each retailer's website |
| `browser_snapshot` | Extract pricing data from pages |
| `web_search` | Find product listings on Amazon |

## Step-by-Step Workflow

### 1. Input: Set(s) to Research

Take set name/code from MTGStocks discovery:

```python
sets_to_research = [
    {"name": "Modern Horizons 3", "code": "MH3"},
    {"name": "Bloomburrow", "code": "BLB"}
]
```

### 2. Search Amazon for Set Price

```python
def search_amazon_price(set_name):
    """Search Amazon for sealed set price."""
    from hermes_tools import browser_navigate, browser_snapshot
    
    # Build Amazon search URL
    search_url = f"https://www.amazon.com/s?k={set_name.replace(' ', '+')}+booster+box"
    browser_navigate(url=search_url)
    
    snapshot = browser_snapshot(full=True)
    page_text = snapshot.get("text", "")
    
    # Extract first relevant price (booster box or bundle)
    import re
    price_match = re.search(r'\$([\d,]+\.\d{2})', page_text)
    if price_match:
        return float(price_match.group(1).replace(',', ''))
    return None
```

### 3. Check MTGGoldfish Marketplace Price

```python
def search_mtggoldfish_price(set_code):
    """Get MTGGoldfish marketplace price for set."""
    from hermes_tools import browser_navigate, browser_snapshot
    
    url = f"https://www mtggoldfish.com/product/search?Set={set_code}"
    browser_navigate(url=url)
    
    snapshot = browser_snapshot(full=True)
    # Parse lowest seller price from marketplace
    # MTGGoldfish shows "Buy" prices from various sellers
```

### 4. Check TCGPlayer Product Price

```python
def search_tcgplayer_price(set_name):
    """Search TCGPlayer for sealed set price."""
    from hermes_tools import browser_navigate, browser_snapshot
    
    url = f"https://www.tcgp layer.com/productsearch?q={set_name.replace(' ', '+')}"
    browser_navigate(url=url)
    
    snapshot = browser_snapshot(full=True)
    # Extract lowest product price
```

### 5. Compare All Sources and Calculate Real Profit

```python
def compare_prices(set_data):
    """Compare prices across all sources."""
    set_name = set_data["name"]
    set_code = set_data.get("code", "")
    
    prices = {
        "mtgstocks": set_data.get("buy_price"),
        "amazon": search_amazon_price(set_name),
        "mtggoldfish": search_mtggoldfish_price(set_code) if set_code else None,
        "tcgplayer": search_tcgplayer_price(set_name)
    }
    
    # Filter out None values
    valid_prices = {k: v for k, v in prices.items() if v is not None}
    
    if not valid_prices:
        return None
    
    # Find lowest price and source
    best_source = min(valid_prices, key=valid_prices.get)
    best_price = valid_prices[best_source]
    
    # Calculate real profit margin
    ev = set_data.get("ev_percentage", 0)
    expected_value = best_price * (1 + ev / 100)
    profit_margin = ((expected_value - best_price) / best_price) * 100
    
    return {
        "set_name": set_name,
        "set_code": set_code,
        "prices_by_source": valid_prices,
        "best_source": best_source,
        "best_price": best_price,
        "expected_value": expected_value,
        "profit_margin_percent": profit_margin,
        "potential_profit_dollars": expected_value - best_price
    }
```

### 6. Return Ranked Results

```python
{
    "researched_sets": [
        {
            "set_name": "Modern Horizons 3",
            "best_source": "amazon",
            "best_price": 145.00,
            "expected_value": 180.50,
            "profit_margin_percent": 24.5,
            "potential_profit_dollars": 35.50
        },
        # ... sorted by profit margin descending
    ]
}
```

## Verification Steps

- All prices are positive numbers
- Best price is actually the minimum of all sources
- Profit margin calculation: `(expected_value - best_price) / best_price * 100`
- At least one source returned a valid price

## Pitfalls & Notes

**Amazon requires search parsing** - Product titles vary; need to match "booster box" or "bundle"

**MTGGoldfish marketplace varies** - Prices change frequently based on seller inventory

**Shipping costs matter** - Compare final cost including shipping, not just base price

**Sales tax** - Varies by location; factor into real profit calculation

## Example Usage

```python
# Research a discovered set
set_from_mtgstocks = {
    "name": "Modern Horizons 3",
    "code": "MH3", 
    "ev_percentage": 24.5,
    "buy_price": 156.00
}

result = compare_prices(set_from_mtgstocks)
print(f"Best price: ${result['best_price']} from {result['best_source']}")
print(f"Potential profit: ${result['potential_profit_dollars']:.2f} ({result['profit_margin_percent']:.1f}%)")
```

## Integration with Other Skills

Called by:
- **pocket-shop-loop** - After MTGStocks discovery, before purchase decision

Feeds into:
- Purchase decision logic (is profit margin acceptable?)
- Order placement automation
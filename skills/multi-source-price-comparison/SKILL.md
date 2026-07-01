---
name: multi-source-price-comparison
description: "Compare MTG sealed set prices across Amazon, MTGGoldfish, TCGPlayer, and Scryfall to find the best deal and calculate real profit margins."
version: 1.0.0
author: SouthpawIN
license: MIT
platforms:
  - linux
tags:
  - mtg
  - pricing
  - comparison
  - amazon
  - tcgplayer
  - scryfall
---

# Multi-Source Price Comparison

<!-- hermes.tags: mtg, pricing, price-comparison, amazon, mtggoldfish, tcgplayer, scryfall -->
<!-- hermes.related_skills: pocket-shop-loop, mtgstocks-set-discovery, card-scanner-vision -->

This skill takes a set (or list of sets) discovered by **mtgstocks-set-discovery** and checks actual purchase prices across multiple retailers. It returns the best price, the source, and the calculated profit margin for each set.

## When to Use

- After discovering high-EV sets and needing to find the cheapest source
- The user says "compare prices for [set name]" or "find the best deal on [set]"
- The **pocket-shop-loop** skill calls this during Phase 3 (price research)
- The user wants to validate that a set is actually profitable at current market prices

## Sources Compared

| Source | Method | Notes |
|--------|--------|-------|
| Amazon | **web_search** + **browser_navigate** | Search for "[set name] booster box" or "bundle" |
| MTGGoldfish | **browser_navigate** | Marketplace with multiple sellers |
| TCGPlayer | **browser_navigate** | Largest MTG marketplace; sealed product section |
| Scryfall (card-level) | **terminal** → `scryfall_pricing.py` | Free API for individual card prices (fallback) |

## Steps

### Step 1 — Gather Set Information

Confirm the set(s) to research. Each set needs:
- Set name (e.g., "Modern Horizons 3")
- Set code (e.g., "MH3")
- EV percentage from MTGStocks discovery

### Step 2 — Search Amazon

Use **web_search** to find the product on Amazon:

```
web_search: "Modern Horizons 3 booster box site:amazon.com"
```

Then navigate to the top result:

```
browser_navigate to the Amazon product URL from search results
browser_snapshot to capture the page
```

Extract the price from the snapshot text. Look for the main product price (usually the first prominent dollar amount).

### Step 3 — Check MTGGoldfish

Navigate to MTGGoldfish's product search:

```
browser_navigate to https://www.mtggoldfish.com/product/search?query=Modern+Horizons+3
browser_snapshot to capture marketplace listings
```

Extract the lowest available price from the results. Note that MTGGoldfish prices may exclude shipping.

### Step 4 — Check TCGPlayer

Navigate to TCGPlayer's product search:

```
browser_navigate to https://www.tcgplayer.com/search?q=Modern+Horizons+3
browser_snapshot to capture product listings
```

Extract the lowest sealed product price (booster box, bundle, or similar).

### Step 5 — Use Scryfall API as Fallback (Card-Level Pricing)

If sealed product prices are unavailable, or for individual card pricing after scanning, use the project's Scryfall pricing module:

```
terminal: python3 scryfall_pricing.py --set MH3 --output json
```

This calls Scryfall's free API (no key required) and returns average card prices for the entire set. Sum these to estimate the set's total card-level value.

For a single card:

```
terminal: python3 scryfall_pricing.py --card "Lightning Bolt" --set M21
```

### Step 6 — Compare and Calculate

For each set, compile prices from all sources that returned valid data:

1. Discard any source that returned no price or an error.
2. Find the lowest price across all valid sources — this is the `best_price`.
3. Calculate:
   - `expected_value = best_price × (1 + EV_percentage / 100)`
   - `profit_margin_percent = ((expected_value − best_price) / best_price) × 100`
   - `potential_profit_dollars = expected_value − best_price`
4. Sort all researched sets by `profit_margin_percent` descending.

### Step 7 — Parallelize with delegate_task

For multiple candidate sets, use **delegate_task** to research prices concurrently:

```
delegate_task with tasks:
  - task: "Research price for Modern Horizons 3 (MH3) across Amazon, MTGGoldfish, TCGPlayer"
  - task: "Research price for Bloomburrow (BLB) across Amazon, MTGGoldfish, TCGPlayer"
  - task: "Research price for Duskmourn (DSK) across Amazon, MTGGoldfish, TCGPlayer"
```

Each subtask runs independently and returns its price comparison results. Collect and merge results when all tasks complete.

### Step 8 — Present Results

Report back to the user or the calling skill with:

- Set name and code
- Price from each source that returned data
- Best source and best price
- EV percentage, expected value, profit margin %, and potential profit $

## Pitfalls

- **Amazon search results are noisy** — the top result may be a single booster pack, not a booster box. Always verify the product title contains "booster box" or "bundle" before using the price.
- **Shipping costs are not always included** — TCGPlayer and MTGGoldfish may show item price only. Factor in estimated shipping ($5–$15) for accurate comparison.
- **Sales tax varies by state** — the listed price is pre-tax in most cases.
- **Scryfall prices are card-level averages** — they do not reflect sealed product premiums. Use Scryfall as a fallback for estimating set EV from individual card prices, not for comparing sealed purchase prices.
- **MTGGoldfish and TCGPlayer may block automated access** — if browser navigation consistently fails, fall back to `scryfall_pricing.py` and **web_search**.
- **Prices change frequently** — a price found at 9 AM may be different by noon. Treat all prices as point-in-time snapshots.
- **TCGPlayer URL uses special encoding** — make sure to URL-encode the set name properly (spaces become `+` or `%20`).

## Verification

- All returned prices should be positive numbers.
- The `best_price` should be the minimum across all valid sources (not always Amazon).
- `profit_margin_percent` should equal `((expected_value − best_price) / best_price) × 100`.
- At least one source should return a valid price for each set; zero prices means all scraping failed.
- Cross-check one price manually by visiting the source website and confirming the listed price.

---
name: pocket-shop-loop
description: "Main orchestration for the automated MTG card trading loop — runs discovery, pricing, purchasing, scanning, listing, and finance tracking end-to-end."
version: 1.0.0
author: SouthpawIN
license: MIT
platforms:
  - linux
tags:
  - mtg
  - automation
  - orchestration
  - trading
  - pocket-shop
---

# Pocket Shop Loop — Main Orchestration

<!-- hermes.tags: mtg, automation, orchestration, trading-loop, pocket-shop -->
<!-- hermes.related_skills: mtgstocks-set-discovery, multi-source-price-comparison, card-scanner-vision, pocket-shop-finance-tracker -->

This skill is the top-level orchestrator for the entire Pocket Shop system. It ties together set discovery, multi-source price comparison, card scanning, eBay listing, and finance tracking into a single repeatable loop.

## When to Use

- The user says "run the pocket shop loop" or "start the trading loop"
- The user wants to run a full cycle: discover → research → purchase → scan → list → track sales
- A cron job fires and triggers automated discovery
- The user wants to check the current state of the trading pipeline

## Configuration Defaults

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `SET_PURCHASE_THRESHOLD` | $150.00 | Minimum restock fund before buying a new set |
| `BUDGET_PER_SET` | $200.00 | Maximum to spend on a single set |
| `MIN_EV_PERCENTAGE` | 10.0% | Minimum expected value to consider a set |
| Config file | `config.example.yaml` | User-overridable settings |

## Steps

### Phase 1 — Load State and Check Finance

1. Use **read_file** to load `data/finance.json` (or run `finance_tracker.py` via **terminal** — see below) to get the current finance summary.
2. Check the `restock_fund` value. If it is below the `SET_PURCHASE_THRESHOLD`, skip to **Phase 6** (waiting / card processing).
3. Optionally use **memory** to recall the last discovery run timestamp and results so duplicate sets are not re-researched.

```
terminal: python3 finance_tracker.py --summary
```

### Phase 2 — Set Discovery

1. Load the **mtgstocks-set-discovery** skill (or run `mtgstocks_discovery.py` via **terminal**).
2. Alternatively, run the browser-based discovery manually:
   - **browser_navigate** to `https://mtgstocks.com/sets`
   - **browser_snapshot** (full page) to capture the sets table
   - Parse set names, EV percentages, and buy prices from the snapshot text
   - Filter to sets under `BUDGET_PER_SET` with EV ≥ `MIN_EV_PERCENTAGE`
3. Collect the top 4 candidate sets sorted by EV descending.

```
terminal: python3 mtgstocks_discovery.py
```

### Phase 3 — Multi-Source Price Research

1. For each candidate set, load the **multi-source-price-comparison** skill or use **delegate_task** to research prices in parallel:
   - **delegate_task** with `tasks` containing one subtask per candidate set, each calling the price comparison skill
2. Each subtask uses **web_search** and **browser_navigate** to check Amazon, MTGGoldfish, and TCGPlayer.
3. As a fallback, run `scryfall_pricing.py` for individual card pricing:

```
terminal: python3 scryfall_pricing.py --set MH3
```

4. Rank the researched sets by profit margin descending and pick the best opportunity.

### Phase 4 — Purchase Decision

1. Present the top set to the user with:
   - Set name, source, price, EV%, potential profit
2. Ask the user to confirm the purchase.
3. If confirmed, record the purchase using `finance_tracker.py`:

```
terminal: python3 finance_tracker.py --record-purchase --set "Modern Horizons 3" --amount 156.00
```

4. Use **memory** to store the purchase details (set name, code, price, date, source) for later reference when cards arrive.

### Phase 5 — Card Scanning and Listing (When Sets Arrive)

1. When cards physically arrive, the user triggers this phase.
2. Use **vision_analyze** on each card photo, or load the **card-scanner-vision** skill:
   - Provide the image path and a prompt asking for card name, set code, condition, foil status
3. For identified cards, run pricing:

```
terminal: python3 auto_card_processor.py --input-dir /path/to/card-photos/
```

4. Create eBay listings:

```
terminal: python3 create_draft_listing.py --card "Lightning Bolt" --set M21 --price 5.00
```

   Or use **browser_navigate** to open eBay's listing tool and fill in fields via **browser_type** / **browser_click**.

5. Use **delegate_task** to parallelize listing creation when many cards need listing at once.

### Phase 6 — Sales Monitoring

1. Check for new eBay sales via email or dashboard:

```
terminal: python3 gmail_monitor.py
terminal: python3 sales_monitor.py
```

2. For each confirmed sale, record revenue:

```
terminal: python3 finance_tracker.py --record-sale --item "Lightning Bolt" --amount 5.00
```

3. The 30/30/40 split is automatically applied (30% savings, 30% profit, 40% restock).
4. Loop back to **Phase 1** and check if restock fund has reached threshold.

### Phase 7 — Cron Job Setup (Automated Discovery)

1. To run set discovery daily at 9 AM, use **cronjob**:

```
cronjob: create a job named "pocket-shop-daily-discovery" that runs the mtgstocks-set-discovery skill every day at 09:00
```

2. This ensures new profitable sets surface automatically even when the agent is not actively running.

## Pitfalls

- **MTGStocks uses JavaScript rendering** — a simple HTTP fetch will return an empty page; always use **browser_navigate** + **browser_snapshot**, not `web_extract` alone.
- **Manual purchase confirmation required** — the agent cannot place real orders; always pause and ask the user before spending money.
- **eBay API integration is not yet live** — listing creation is currently via browser automation or `create_draft_listing.py` which generates draft data, not live listings.
- **Sales monitoring depends on Gmail/eBay notifications being configured** — if `gmail_monitor.py` returns nothing, check that OAuth credentials are set up.
- **Finance state can desync** — if `finance_tracker.py` is run concurrently by two processes, writes to `data/finance.json` may conflict. Use **memory** as a secondary source of truth.
- **Image quality matters for card scanning** — blurry or glare-heavy photos produce low-confidence vision results.

## Verification

- After running the full loop, check that `data/finance.json` totals are consistent: `savings_fund + profit_total + restock_fund == total_sales` (within rounding tolerance).
- Sets discovered should all be under `BUDGET_PER_SET` with EV ≥ `MIN_EV_PERCENTAGE`.
- Price research should return at least one valid price per set from at least one source.
- Card identification results should have confidence > 0.7; flag anything lower for manual review.
- Cron jobs should appear in the cron job list and have a valid next-run timestamp.

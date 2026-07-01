---
name: mtgstocks-set-discovery
description: "Scrape MTGStocks.com for Magic: The Gathering sealed sets with high Expected Value (EV) under a configurable budget threshold."
version: 1.0.0
author: SouthpawIN
license: MIT
platforms:
  - linux
tags:
  - mtg
  - mtgstocks
  - set-discovery
  - scraping
  - browser
---

# MTGStocks Set Discovery

<!-- hermes.tags: mtg, mtgstocks, set-discovery, ev, scraping, browser-automation -->
<!-- hermes.related_skills: pocket-shop-loop, multi-source-price-comparison -->

This skill scrapes **MTGStocks.com/sets** to find Magic: The Gathering sealed product sets whose Expected Value (EV) exceeds a minimum threshold while staying under a maximum budget. It returns the top 3–4 most profitable candidates for further price research.

## When to Use

- The user says "find profitable MTG sets" or "check MTGStocks for deals"
- The **pocket-shop-loop** skill calls this as its first phase
- A cron job fires for scheduled daily discovery
- The user wants to refresh the candidate list before making a purchase decision

## Configuration

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `BUDGET_THRESHOLD` | $200.00 | Maximum set price to consider |
| `MIN_EV_PERCENTAGE` | 10.0% | Minimum EV percentage to qualify |
| `TOP_N_RESULTS` | 4 | Number of top sets to return |

These can be overridden in `config.example.yaml` or passed as arguments to `mtgstocks_discovery.py`.

## Steps

### Step 1 — Navigate to MTGStocks Sets Page

Use **browser_navigate** to load the sets listing:

```
browser_navigate to https://mtgstocks.com/sets
```

Wait for the page to fully render (MTGStocks is a JavaScript-heavy site; tables may load after initial paint).

### Step 2 — Scroll to Load Full Table

The sets table may be lazy-loaded. Use **browser_scroll** to scroll down repeatedly until no new rows appear:

```
browser_scroll down 3 times, waiting 1 second between scrolls
```

### Step 3 — Capture Page Snapshot

Take a full-page snapshot to extract the rendered HTML/text:

```
browser_snapshot (full page)
```

The snapshot text contains the sets table with columns like: Set Name, EV%, Buy Price, and other metrics.

### Step 4 — Parse and Filter Sets

From the snapshot text, extract each set's:
- **Name** (e.g., "Modern Horizons 3")
- **EV percentage** (e.g., 24.5%)
- **Buy price** (e.g., $156.00)

Filter to sets where:
- `buy_price ≤ BUDGET_THRESHOLD`
- `ev_percentage ≥ MIN_EV_PERCENTAGE`

Sort the filtered sets by `ev_percentage` descending and keep the top `TOP_N_RESULTS`.

### Step 5 — Run the Python Module (Alternative)

Instead of manual browser parsing, run the dedicated discovery script via **terminal**:

```
terminal: python3 mtgstocks_discovery.py --budget 200 --min-ev 10 --top 4
```

This script handles navigation, parsing, and filtering internally and outputs JSON.

### Step 6 — Return Results

Present the discovered sets to the user or pass them to the **multi-source-price-comparison** skill. Each result should include:

- Set name
- Set code (if available)
- EV percentage
- Buy price
- Expected value (price × (1 + EV/100))
- Potential profit (expected_value − buy_price)

### Step 7 — Set Up Automated Discovery (Cron Job)

To run this skill automatically every day at 9 AM:

```
cronjob: create a job named "pocket-shop-daily-discovery"
  skill: mtgstocks-set-discovery
  schedule: "0 9 * * *"
```

This ensures new opportunities surface without manual triggering.

### Step 8 — Store Results in Memory

Use **memory** to save the discovery run details so the main loop can check for duplicates:

```
memory: store "mtgstocks_discovery_<date>" with the list of discovered set names and codes
```

## Pitfalls

- **MTGStocks requires full JavaScript rendering** — `web_extract` alone may return incomplete data; always use **browser_navigate** + **browser_snapshot**.
- **Set availability changes daily** — a high-EV set found today may be sold out or repriced by tomorrow. Treat results as point-in-time snapshots.
- **EV is based on historical sell-through data** — it does not guarantee future returns. High EV on a niche set may not translate to actual card sales on eBay.
- **Rate limiting** — repeatedly scraping MTGStocks in a short window may trigger IP blocks. Space out requests and respect robots.txt.
- **Table format may change** — if MTGStocks redesigns their sets page, the parsing logic in `mtgstocks_discovery.py` may need updating.
- **Some sets lack EV data** — skip sets where EV is missing or zero rather than treating them as 0% EV opportunities.

## Verification

- The returned set names should be recognizable MTG set names (e.g., "Modern Horizons 3", "Bloomburrow").
- EV percentages should be in a realistic range (typically 5–50%).
- Buy prices should all be ≤ `BUDGET_THRESHOLD`.
- At least one set should be found when the market is active; zero results may indicate a site scraping failure.
- Cross-check one set manually by visiting MTGStocks in a browser and confirming the EV and price match.
- The cron job (if created) should appear in the cron list with a valid next-run time.

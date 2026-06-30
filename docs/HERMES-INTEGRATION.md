# Hermes Agent Integration Guide

*Last updated: June 2026*

This guide covers how Pocket-Shop integrates with [Hermes Agent](https://hermes-agent.nousresearch.com) for autonomous MTG card trading.

---

## Overview

Pocket-Shop is not a script — it's an **AI agent that trades cards**. Hermes Agent provides the orchestration layer:

- **Skills** — Reusable procedures the agent follows (not Python code, but instruction documents)
- **Memory** — Persistent state across sessions (finance tracking, trade history)
- **Cron** — Scheduled automation (daily MTGStocks discovery)
- **Delegation** — Multi-agent coordination (orchestrator spawns workers)
- **Browser Automation** — Navigate eBay, MTGStocks, TCGPlayer like a human
- **Vision** — Identify cards from photos using local AI models

## Skill Architecture

Each skill is a `SKILL.md` file that an agent loads and follows:

```
skills/
├── pocket-shop-loop/SKILL.md          # Main orchestration (loads all others)
├── mtgstocks-set-discovery/SKILL.md   # Daily set discovery on MTGStocks
├── multi-source-price-comparison/SKILL.md  # Price research across sources
├── card-scanner-vision/SKILL.md       # Vision-based card identification
└── pocket-shop-finance-tracker/SKILL.md    # 30/30/40 revenue split tracking
```

### Loading Skills

```bash
# Preload all skills at session start
hermes -s pocket-shop-loop,mtgstocks-set-discovery,card-scanner-vision

# Or load on-demand during a session
/skill pocket-shop-loop
```

## Tools Used by Each Phase

| Phase | Hermes Tools | Python Modules |
|-------|-------------|----------------|
| Set Discovery | `web_extract`, `browser_navigate`, `cronjob` | `mtgstocks_monitor.py` |
| Price Research | `web_search`, `web_extract`, `terminal` | `scryfall_pricing.py` |
| Card Scanning | `vision_analyze`, `terminal` | `card_scanner.py`, `auto_card_processor.py` |
| Pricing | `terminal`, `web_search` | `scryfall_pricing.py` |
| eBay Listing | `browser_navigate`, `browser_click`, `browser_type` | `ebay_listings.py`, `ebay_api.py` |
| Sales Monitor | `terminal` | `gmail_monitor.py` |
| Finance | `memory`, `read_file`, `write_file` | `finance_tracker.py` |

## Cron Job Setup

Automate daily set discovery:

```bash
# Create daily discovery job (runs at 9 AM)
hermes cron create "0 9 * * *" \
  --name "mtg-discovery" \
  --prompt "Load the mtgstocks-set-discovery skill and run a full discovery cycle. Save results to data/latest-discovery.json and report any sets with EV > 10% under $200."

# Also automate sales monitoring every 4 hours
hermes cron create "every 4h" \
  --name "sales-monitor" \
  --prompt "Load the pocket-shop-finance-tracker skill. Check Gmail for new eBay sales notifications and record any found sales with the 30/30/40 split."

# Check your jobs
hermes cron list
```

## Memory Integration

Pocket-Shop uses Hermes `memory` tool to persist key trading facts:

- **User profile** — Trading preferences, budget thresholds, target EV%
- **Agent memory** — Last discovered sets, recent trade outcomes, lessons learned

Example facts stored:
```
User prefers EV > 15% and budget under $200 per set
Last profitable trade: Modern Horizons 3 booster box → $47.30 profit
Avoid sets from Wizards Play Network (low margins)
```

## Multi-Agent Fleet

When running with a multi-agent Hermes setup:

```
                  ┌─────────────┐
                  │   senter    │
                  │ (orchestrate)│
                  └──────┬──────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
        ┌─────▼────┐ ┌──▼───┐ ┌───▼────┐
        │   crow   │ │chizul│ │ anser  │
        │(research)│ │(work)│ │(notify)│
        └──────────┘ └──────┘ └────────┘
```

- **senter** — Orchestrates the loop, delegates tasks, manages kanban
- **crow** — Researches prices, scrapes MTGStocks, compares sources
- **chizul** — Processes cards, creates eBay listings, records sales
- **anser** — Sends notifications (Discord) about trades and profits

## Vision Pipeline

Card identification uses a two-tier vision stack:

1. **Primary**: Local Carnice model on RTX 3090 (GPU1) — fast, private, free
2. **Fallback**: OpenRouter vision model — when local is unavailable

```python
# auto_card_processor.py handles this automatically
# Just point it at a directory of card photos:
python auto_card_processor.py ~/card-photos/
```

## Running the Full Loop

### Manual (single agent)
```bash
hermes -s pocket-shop-loop
# Then tell it: "Run the full pocket shop trading cycle"
```

### Automated (cron + multi-agent)
```bash
# Set up the cron jobs (one-time)
hermes cron create "0 9 * * *" --name discover --skills mtgstocks-set-discovery
hermes cron create "every 4h" --name monitor --skills pocket-shop-finance-tracker

# The agents handle the rest autonomously
```

### Manual step-by-step
```bash
# 1. Discover sets
hermes chat -q "Load mtgstocks-set-discovery and find profitable sets"

# 2. Research prices
hermes chat -q "Load multi-source-price-comparison and check prices"

# 3. Process cards (when they arrive)
python auto_card_processor.py ~/card-photos/

# 4. Check finances
hermes chat -q "Load pocket-shop-finance-tracker and show summary"
```

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Skills not loading | Run `/skill pocket-shop-loop` manually |
| Vision fails | Check Carnice is running: `curl http://127.0.0.1:8082/v1/models` |
| eBay login fails | Browser automation needs you to be logged into eBay first |
| Cron not firing | Check `hermes cron list` and `hermes gateway status` |
| MTGStocks blocked | Use `web_extract` instead of `browser_navigate` |

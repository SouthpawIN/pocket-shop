# HERMES.md - Hermes Agent Project Rules

This project uses **Hermes Agent** (https://hermes-agent.nousresearch.com/docs) for orchestration and automation.

## Skills Directory

Located at `skills/`. Each agent profile loads relevant skills:

| Skill | Purpose |
|-------|---------|
| `pocket-shop-loop` | Orchestrates the full automation cycle |
| `pocket-shop-finance-tracker` | Manages financial state and allocations |
| `card-scanner-vision` | Vision-based card identification |
| `mtgstocks-set-discovery` | Discovers profitable sets from MTGStocks |
| `multi-source-price-comparison` | Aggregates prices from multiple sources |

## The pocket-shop-loop Skill

The `pocket-shop-loop` skill orchestrates the entire automation:

1. **DISCOVER**: Find sets with EV > 10% (via `mtgstocks-set-discovery` skill)
2. **RESEARCH**: Research prices using `multi-source-price-comparison` skill
3. **PURCHASE**: Buy when restock fund ≥ $500 (manual step via Gmail notification)
4. **SCAN**: Identify cards with `card-scanner-vision` skill (local Carnice model → OpenRouter fallback)
5. **PRICE**: Price individual cards
6. **LIST**: Create eBay listings via browser automation (`browser_use` tool)
7. **TRACK**: Monitor sales with `pocket-shop-finance-tracker` skill
8. **LOOP**: Repeat

## Finance State Persistence

Financial state is persisted via:
- **Memory tool**: Hermes memory for high-level project state
- **`data/finance.json`**: Detailed transaction history

```bash
# Check current finance state via Hermes
hermes ask "What is the current pocket-shop finance state?"
```

The `pocket-shop-finance-tracker` skill reads/writes `data/finance.json`:
- `savings`: 30% allocation (long-term savings)
- `profit`: 30% allocation (payout to owner)
- `restock`: 40% allocation (reinvestment fund)
- `restock_target`: Triggers purchase when `restock >= 500.00`

## Cron Job — Daily Discovery

The MTGStocks discovery runs daily at 9:00 AM via Hermes cron:

```bash
# Create the cron job (one-time setup)
hermes cron create '0 9 * * *' --name mtg-discovery

# List existing cron jobs
hermes cron list

# Manually trigger the discovery job
hermes cron run <job_id>

# Delete the cron job
hermes cron delete <job_id>
```

The cron job runs `mtgstocks_discovery.py` via the `mtgstocks-set-discovery` skill. Results are written to `data/discovery_results.json` and optionally emailed via `gmail_monitor.py`.

## Multi-Agent Fleet

This project uses a **multi-agent architecture** with Hermes profile delegation:

```
┌─────────────────────────────────────────────────────┐
│  senter (orchestrator)                              │
│  - Loads pocket-shop-loop skill                     │
│  - Manages kanban board (data/kanban.json)          │
│  - Delegates tasks via Hermes kanban tool            │
│  - Monitors finance state                           │
└──────────────┬──────────────────────────────────────┘
               │ kanban delegation
       ┌───────┴───────┐
       ▼               ▼
┌──────────────┐  ┌──────────────┐
│  chizul      │  │  crow        │
│  (worker)    │  │  (research)  │
│              │  │              │
│ • Process    │  │ • Scryfall   │
│   cards      │  │   pricing    │
│ • Create     │  │ • MTGStocks  │
│   listings   │  │   scraping   │
│ • Browser    │  │ • Multi-     │
│   automation │  │   source     │
│              │  │   comparison │
└──────────────┘  └──────────────┘
       │               │
       └───────┬───────┘
               ▼
┌─────────────────────────────────────────────────────┐
│  senter (kanban update / status check)              │
└─────────────────────────────────────────────────────┘
```

### Agent Profiles

| Profile | Role | Key Skills/Tools |
|---------|------|-----------------|
| `senter` | Orchestrator | `pocket-shop-loop`, `pocket-shop-finance-tracker`, kanban tool |
| `chizul` | Worker | `card-scanner-vision`, browser_use, `create_draft_listing` |
| `crow` | Researcher | `mtgstocks-set-discovery`, `multi-source-price-comparison`, Scryfall API |

### Kanban Flow
1. `senter` creates a task (e.g., "Process new card batch")
2. `chizul` picks up the task, processes cards, creates eBay listings
3. `chizul` marks task done
4. `senter` reviews and updates finance state

## Vision System

Card identification uses a two-tier vision approach:

| Tier | Model | Endpoint | Use Case |
|------|-------|----------|----------|
| **Primary** | Carnice (local) | `http://127.0.0.1:8082/v1` | GPU1, fast, no API costs |
| **Fallback** | OpenRouter | via `openrouter` provider | When local model unavailable |

The `card-scanner-vision` skill handles both tiers automatically.

```bash
# Check if Carnice is running
curl http://127.0.0.1:8082/v1/health
```

## Browser Automation

This project uses Hermes' `browser_use` tool (Browser Use) for:
- **eBay listing creation**: Fill seller forms, upload photos, set prices
- **MTGStocks scraping**: Navigate to set pages, extract EV data
- **Amazon price checks**: Fallback price verification

Browser automation is preferred over API mode because:
- No API keys required for eBay
- Works with standard eBay seller accounts
- More resilient to API changes

## Project Commands Cheat Sheet

```bash
# Start the main loop manually
python main_loop.py

# Run discovery only
python mtgstocks_discovery.py

# Run card scanner interactively
python card_scanner.py --interactive

# Check finance state
python finance_tracker.py --status

# Run Hermes daily discovery
hermes cron list                     # find the job ID
hermes cron run <mtg-discovery-id>

# Ask Hermes about project state
hermes ask "What is the pocket-shop finance state?"
```

## File Paths (Hermes-Aware)

```
pocket-shop-update/
├── config.yaml              # NEVER commit (gitignored)
├── config.example.yaml      # Template ( committed)
├── data/
│   ├── finance.json         # Finance state ( NEVER commit)
│   ├── kanban.json          # Kanban board state
│   └── discovery_results.json
├── skills/                  # Hermes skill definitions
│   ├── pocket-shop-loop/
│   ├── pocket-shop-finance-tracker/
│   ├── card-scanner-vision/
│   ├── mtgstocks-set-discovery/
│   └── multi-source-price-comparison/
├── vision/                  # Vision model wrappers
└── browser_helpers/         # Browser automation scripts
```

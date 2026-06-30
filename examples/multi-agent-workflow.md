# Multi-Agent Workflow

This document describes how the Pocket-Shop multi-agent fleet operates using Hermes Agent.

## Fleet Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CRON TRIGGER (Daily 9 AM)                          │
│                   hermes cron run <mtg-discovery-id>                    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                        senter (Orchestrator)                            │
│                                                                         │
│   Skills: pocket-shop-loop, pocket-shop-finance-tracker                │
│   Tools:  memory, kanban, execute_code                                  │
│                                                                         │
│   Reads finance state → decides next action → delegates via kanban     │
│                                                                         │
└──────────────┬──────────────────────────────────────┬───────────────────┘
               │                                      │
               │  Task: "Research set prices"         │  Task: "Process cards"
               │                                      │
               ▼                                      ▼
┌────────────────────────────┐          ┌────────────────────────────────┐
│                            │          │                                │
│      crow (Research)       │          │       chizul (Worker)          │
│                            │          │                                │
│  Skills:                   │          │  Skills:                       │
│  • mtgstocks-set-discovery │          │  • card-scanner-vision         │
│  • multi-source-price-     │          │                                │
│    comparison              │          │  Tools:                        │
│                            │          │  • browser_use (eBay listings) │
│  Tools:                    │          │  • execute_code                │
│  • web_search              │          │                                │
│  • firecrawl (scraping)    │          │  Actions:                      │
│  • Scryfall API            │          │  • Scan card images            │
│                            │          │  • Price individual cards      │
│  Actions:                  │          │  • Create eBay listings        │
│  • Scrape MTGStocks        │          │  • Update card database        │
│  • Compare prices          │          │                                │
│  • Calculate EV            │          │                                │
│  • Return ranked results   │          │                                │
│                            │          │                                │
└──────────┬─────────────────┘          └──────────────┬─────────────────┘
           │                                           │
           │  Result: Set rankings                     │  Result: Listings created
           │                                           │
           ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                     senter (Kanban Update)                              │
│                                                                         │
│   • Updates kanban task status                                         │
│   • Records results in data/discovery_results.json                     │
│   • If restock fund ≥ $500 → triggers purchase workflow                │
│   • Updates finance state in data/finance.json                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Detailed Flow

### 1. Daily Discovery (Cron-Triggered)

**Schedule**: Every day at 9:00 AM  
**Job Name**: `mtg-discovery`  
**Trigger**: `hermes cron create '0 9 * * *' --name mtg-discovery`

```
09:00 AM ──► Cron fires ──► senter loads pocket-shop-loop skill
                                │
                                ▼
                        Check finance state (data/finance.json)
                                │
                                ├─► If restock < $500: Skip purchase, continue discovery
                                │
                                └─► If restock ≥ $500: Flag "ready to buy"
                                        │
                                        ▼
                                Delegate to crow: "Research profitable sets"
                                        │
                                        ▼
                                [crow runs mtgstocks-set-discovery skill]
                                        │
                                        ▼
                                Returns: ranked list of sets with EV > 10%
                                        │
                                        ▼
                                senter updates kanban, saves to data/discovery_results.json
```

### 2. Card Processing (Manual or Kanban-Triggered)

When a new set arrives (manual trigger or kanban task):

```
senter creates task: "Process card batch [SET_NAME]"
        │
        ▼
chizul picks up task
        │
        ├─► Load card-scanner-vision skill
        │       │
        │       ▼
        │   Scan card images (local Carnice model on GPU1)
        │       │
        │       ├─► Success: Card identified, confidence > 0.75
        │       │
        │       └─► Fallback: Use OpenRouter API
        │
        ├─► Price each card (TCGPlayer, Scryfall)
        │
        ├─► Create eBay listings (browser automation)
        │       │
        │       ▼
        │   chizul uses browser_use tool to:
        │   • Navigate to eBay seller page
        │   • Fill listing form
        │   • Upload card photos
        │   • Set price (market price - 5%)
        │   • Submit listing
        │
        └─► Mark task complete, update kanban
                │
                ▼
        senter receives completion notification
                │
                ▼
        Updates finance projections
```

### 3. Sales Tracking (Continuous)

```
Every 5 minutes:
        │
        ▼
sales_monitor.py checks Gmail for eBay sold notifications
        │
        ├─► No new sales: Sleep 5 min
        │
        └─► New sale detected:
                │
                ▼
        Parse sale details (item, price, buyer)
                │
                ▼
        Update data/finance.json:
                │
                ├─► Add revenue to total
                ├─► Calculate allocations:
                │   • 30% → savings
                │   • 30% → profit
                │   • 40% → restock
                │
                └─► senter notified via kanban task
```

## Skills Loaded by Each Agent

### senter (Orchestrator)
```yaml
skills:
  - pocket-shop-loop          # Main automation orchestration
  - pocket-shop-finance-tracker  # Financial state management

tools:
  - memory                    # Persistent project state
  - kanban                    # Task delegation to workers
  - execute_code              # Run Python scripts
```

### chizul (Worker)
```yaml
skills:
  - card-scanner-vision       # Vision-based card identification

tools:
  - browser_use               # eBay listing automation
  - execute_code              # Run card processing scripts
  - vision_analyze            # Fallback vision API
```

### crow (Research)
```yaml
skills:
  - mtgstocks-set-discovery       # Scrape MTGStocks for EV data
  - multi-source-price-comparison # Aggregate prices from multiple sources

tools:
  - web_search                # General web research
  - firecrawl                 # Advanced web scraping
  - execute_code              # Run pricing scripts
```

## Setup & Execution

### 1. Create the Cron Job

```bash
# One-time setup: create daily discovery job
hermes cron create '0 9 * * *' --name mtg-discovery

# Verify it was created
hermes cron list
```

**Output example:**
```
ID          NAME             SCHEDULE        STATUS
abc123      mtg-discovery    0 9 * * *       active
```

### 2. Manually Trigger Discovery

```bash
# Run discovery immediately (don't wait for 9 AM)
hermes cron run abc123

# Or trigger via skill
hermes ask "Run the MTGStocks discovery now"
```

### 3. Check Fleet Status

```bash
# View kanban board (all agents)
hermes ask "Show me the pocket-shop kanban board"

# Check finance state
hermes ask "What is the current pocket-shop finance state?"

# View recent discovery results
cat data/discovery_results.json | jq .
```

### 4. Run Full Loop Manually

```bash
# Bypass cron, run the entire loop now
python main_loop.py

# This will:
# 1. Check MTGStocks for profitable sets
# 2. Research prices
# 3. If restock fund ready → notify for purchase
# 4. Process any pending cards
# 5. Create eBay listings
# 6. Track sales
```

## Kanban Task Examples

### Discovery Task (senter → crow)
```json
{
  "id": "task-001",
  "title": "Research MTGStocks sets",
  "assignee": "crow",
  "priority": "high",
  "details": {
    "action": "discovery",
    "ev_threshold": 10.0,
    "max_results": 5
  },
  "status": "in_progress"
}
```

### Card Processing Task (senter → chizul)
```json
{
  "id": "task-002",
  "title": "Process Modern Horizons 3 batch",
  "assignee": "chizul",
  "priority": "medium",
  "details": {
    "action": "process_cards",
    "set_name": "Modern Horizons 3",
    "card_count": 45,
    "image_dir": "data/cards/mh3/"
  },
  "status": "pending"
}
```

### Listing Creation Task (senter → chizul)
```json
{
  "id": "task-003",
  "title": "Create eBay listings for MH3 cards",
  "assignee": "chizul",
  "priority": "medium",
  "details": {
    "action": "create_listings",
    "cards": [
      {"name": "Ulamog, the Defiler", "price": 45.99},
      {"name": "Wasteland Strangler", "price": 12.50}
    ]
  },
  "status": "pending"
}
```

## Error Handling & Fallbacks

### Vision Model Unavailable
```
Local Carnice model (GPU1) unreachable
        │
        ▼
Automatically fall back to OpenRouter API
        │
        ▼
Log warning, continue processing
```

### Browser Automation Fails
```
eBay listing creation fails (CAPTCHA, timeout)
        │
        ▼
chizul marks task as "blocked"
        │
        ▼
senter notified, creates manual intervention task
        │
        ▼
Human intervention required
```

### Cron Job Failure
```
Daily discovery cron fails
        │
        ▼
Hermes logs error, sends notification
        │
        ▼
Manual trigger: hermes cron run <job_id>
```

## Monitoring & Debugging

```bash
# View Hermes logs
hermes logs --tail 50

# Check cron job status
hermes cron list

# View kanban board
cat data/kanban.json | jq .

# Check finance state
cat data/finance.json | jq .

# View recent discovery results
cat data/discovery_results.json | jq .

# Test individual skills
hermes ask "Run the card-scanner-vision skill on data/cards/mh3/"
```

## Environment Requirements

- **Python**: 3.11+
- **GPU1**: RTX 3090 running Carnice vision model at :8082
- **Hermes Profile**: `senter` (orchestrator)
- **Dependencies**: See `requirements.txt`
- **Config**: `config.yaml` (copy from `config.example.yaml`)

---

**Last Updated**: June 30, 2026  
**Hackathon Submission**: Pocket-Shop Multi-Agent Fleet

# Pocket Shop v2.0 — Automated MTG Trading Agent

**Hermes Agent Accelerated Business Hackathon Submission**

An autonomous Magic: The Gathering card trading system powered by Hermes Agent, Stripe payments, and NVIDIA Nemotron 3 Ultra vision.

---

## 🎯 What This Does

Pocket Shop is a **self-running MTG card arbitrage agent** that:

1. **Discovers** profitable sealed sets via MTGStocks API (EV > 10%)
2. **Purchases** sets automatically when restock fund reaches threshold
3. **Scans** individual cards using phone camera (ADB over Tailscale)
4. **Identifies** cards with Nemotron 3 Ultra vision (550B MoE model)
5. **Prices** cards via Scryfall API (real-time market data)
6. **Lists** on eBay via API (Auth'n'Auth or OAuth)
7. **Tracks** sales via Gmail monitoring
8. **Splits** revenue: 30% savings / 30% profit / 40% restock
9. **Purchases supplies** (sleeves, shipping) via Stripe Link

The agent runs continuously, learning from past trades and optimizing purchase decisions.

---

## 🏆 Hackathon Tech Stack

### Stripe Integration

**Stripe Link CLI** enables the agent to purchase supplies autonomously:

```bash
# Install Link CLI
npm install -g @stripe/link-cli

# Authenticate
link-cli auth login --client-name "Pocket-Shop"

# Agent purchases card sleeves
python stripe_payments.py purchase "100 penny sleeves" 12.99 "Game Night" "https://gamenight.com"
```

Every purchase requires Link app approval (human-in-the-loop safety). Budget limits enforced:
- Max single purchase: $50.00
- Daily spend limit: $200.00

### NVIDIA Nemotron 3 Ultra

**Vision model** for card identification (550B total parameters, 55B active MoE):

```python
from nemotron_vision import identify_card

result = identify_card("card_photo.jpg")
# Returns: {"name": "Black Lotus", "set_code": "lea", "condition": "Near Mint", ...}
```

Fallback chain: Nemotron → Qwen-Omni → OpenRouter (Claude/GPT-4V)

### Hermes Agent Features Used

- **Kanban orchestration** for multi-agent coordination
- **Cron jobs** for periodic MTGStocks monitoring
- **Memory persistence** across sessions (tracks profitable sets, card prices)
- **Skills** for reusable procedures (pricing logic, eBay API patterns)
- **Multi-platform gateway** (Discord, Telegram, CLI)

---

## 📦 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Pocket Shop v2.0                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ main_loop.py │  │ auto_card_   │  │   main.py    │     │
│  │              │  │ processor.py │  │   (CLI)      │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │             │
│         └─────────────────┴──────────────────┘             │
│                           │                                │
│         ┌─────────────────┼─────────────────┐             │
│         │                 │                 │             │
│    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐        │
│    │scryfall_│      │nemotron_│      │ stripe_ │        │
│    │pricing  │      │vision   │      │payments │        │
│    └────┬────┘      └────┬────┘      └────┬────┘        │
│         │                │                 │             │
│    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐        │
│    │  HTTP   │      │  HTTP   │      │link-cli │        │
│    │Scryfall │      │Nemotron │      │ Stripe  │        │
│    │  API    │      │  API    │      │  Link   │        │
│    └─────────┘      └─────────┘      └─────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              finance/tracker.py                      │  │
│  │  30/30/40 split • Transaction logging • Fund mgmt   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+ (for Stripe Link CLI)
- Hermes Agent installed
- eBay account (for listings)
- Gmail account (for sale monitoring)

### Installation

```bash
# Clone
git clone https://github.com/SouthpawIN/pocket-shop.git
cd pocket-shop
git checkout hackathon-update

# Create venv and install deps
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Install Stripe Link CLI
npm install -g @stripe/link-cli
```

### Configuration

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit config.yaml with your credentials
# - Gmail app password (for sale monitoring)
# - eBay API credentials (Auth'n'Auth or OAuth)
# - Vision model endpoint (Nemotron/Qwen-Omni/OpenRouter)

# Authenticate Stripe Link
link-cli auth login --client-name "Pocket-Shop"
# Open the URL it provides, sign in to Link, approve spend request
```

### Run Tests

```bash
source .venv/bin/activate
pytest -v
```

**51 tests passing** ✅

### Run the Agent

```bash
# Full automation loop
python main_loop.py

# Or individual commands:
python main.py monitor-sets          # Check MTGStocks
python main.py scan card.jpg         # Identify + price card
python main.py price "Lightning Bolt"# Lookup price
python main.py finance status        # Show balances
```

---

## 📊 Module Overview

| Module | Purpose | Hermes Integration |
|--------|---------|-------------------|
| `main_loop.py` | Full automated trading cycle | Cron jobs, memory |
| `auto_card_processor.py` | Vision + pricing pipeline | Nemotron, Scryfall |
| `nemotron_vision.py` | Card identification via vision AI | Nemotron 3 Ultra |
| `stripe_payments.py` | Purchase supplies via Stripe Link | Link CLI, budget limits |
| `scryfall_pricing.py` | Real-time card pricing | HTTP API |
| `finance/tracker.py` | 30/30/40 revenue split | Persistent JSON |
| `ebay_api.py` | eBay listing creation | Auth'n'Auth / OAuth |
| `mtgstocks_monitor.py` | High-EV set discovery | Browser automation |
| `gmail_monitor.py` | Sale notification tracking | IMAP |

---

## 🧪 Test Coverage

```
tests/
├── test_hermes_config.py       (5 tests) — Config loading
├── test_scryfall_pricing.py    (10 tests) — Card pricing API
├── test_nemotron_vision.py     (11 tests) — Vision identification
├── test_stripe_payments.py     (11 tests) — Stripe Link integration
└── test_finance_tracker.py     (14 tests) — Revenue splitting

Total: 51 tests, 100% pass rate
```

---

## 📁 File Structure

```
pocket-shop/
├── main.py                      # CLI entry point
├── main_loop.py                 # Automated trading loop
├── auto_card_processor.py       # Vision + pricing pipeline
├── hermes_config.py             # Centralized config loader
├── nemotron_vision.py           # NVIDIA Nemotron vision module
├── stripe_payments.py           # Stripe Link payments
├── scryfall_pricing.py          # Scryfall API pricing
├── ebay_api.py                  # eBay API integration
├── ebay_automation.py           # eBay browser automation (legacy)
├── mtgstocks_monitor.py         # MTGStocks set monitoring
├── mtgstocks_discovery.py       # High-EV set discovery
├── gmail_monitor.py             # Gmail sale notifications
├── finance_tracker.py           # Legacy finance module
├── finance/
│   ├── __init__.py
│   └── tracker.py               # Modern finance tracker
├── skills/                      # Hermes skills
│   ├── pocket-shop-loop/
│   ├── pocket-shop-finance-tracker/
│   ├── card-scanner-vision/
│   └── ...
├── tests/                       # pytest suite (51 tests)
├── config.example.yaml          # Configuration template
├── pyproject.toml               # Python packaging
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

---

## 💡 How It Works

### 1. Set Discovery (MTGStocks)

```python
from mtgstocks_monitor import MTGStocksMonitor

monitor = MTGStocksMonitor(ev_threshold=10.0)
sets = monitor.find_high_ev_sets()
# Returns sets where Expected Value > 10% above purchase price
```

### 2. Card Identification (Nemotron 3 Ultra)

```python
from nemotron_vision import identify_card

result = identify_card("card_photo.jpg")
# {
#   "name": "Black Lotus",
#   "set_name": "Limited Edition Alpha",
#   "set_code": "lea",
#   "condition": "Near Mint",
#   "is_foil": false,
#   "confidence": 0.95,
#   "provider_used": "nemotron"
# }
```

### 3. Pricing (Scryfall)

```python
from scryfall_pricing import get_card_pricing

pricing = get_card_pricing("Black Lotus", "lea")
# {
#   "success": true,
#   "prices": {
#     "usd_non_foil": "10000.00",
#     "usd_foil": "15000.00",
#     ...
#   }
# }
```

### 4. Revenue Split (30/30/40)

```python
from finance.tracker import FinanceTracker

ft = FinanceTracker(config)
ft.add_sale(100.00, "Lightning Bolt")
# savings_fund += $30.00
# profit_total += $30.00
# restock_fund += $40.00
```

### 5. Supply Purchases (Stripe Link)

```python
from stripe_payments import purchase_supplies

result = purchase_supplies(
    item_name="100 penny card sleeves",
    amount_usd=12.99,
    merchant_name="Game Night",
    merchant_url="https://gamenight.com"
)
# Triggers Link app approval request
# Returns credential file path on approval
```

---

## 🎥 Demo Video Script

**1-3 minute walkthrough:**

1. **Show config.yaml** — credentials, budget limits, vision provider
2. **Run `pytest -v`** — 51 tests passing
3. **Start agent**: `python main_loop.py`
4. **MTGStocks discovery** — shows high-EV sets found
5. **Card scan**: `python auto_card_processor.py card.jpg`
   - Nemotron identifies card
   - Scryfall returns price
   - Result saved to JSON
6. **Finance check**: `python main.py finance status`
   - Shows 30/30/40 split
   - Restock fund progress
7. **Stripe purchase**: `python stripe_payments.py purchase ...`
   - Link app approval popup
   - Transaction completes
8. **eBay listing** (if credentials configured) — draft created
9. **Wrap-up**: "Pocket Shop runs autonomously, making profitable trades while the agent sleeps."

---

## 🔒 Security

- **config.yaml** never committed (in `.gitignore`)
- **Card PAN** never printed to stdout (Stripe Link uses temp files with 0600 perms)
- **Budget limits** enforced in code (max $50/purchase, $200/day)
- **Link app approval** required for every spend
- **Gmail app passwords** (not main password) for email monitoring

---

## 🤝 Credits

- **Hermes Agent** by Nous Research
- **NVIDIA Nemotron 3 Ultra** for vision
- **Stripe Link** for agent payments
- **Scryfall API** for card pricing
- **MTGStocks** for set discovery
- **eBay API** for listings

---

## 📝 License

MIT License — see LICENSE file

---

## 🐛 Troubleshooting

### Tests fail on import
```bash
source .venv/bin/activate
uv pip install -e .
```

### Stripe Link auth fails
```bash
link-cli auth status
# If not authenticated:
link-cli auth login --client-name "Pocket-Shop"
```

### Vision API connection refused
Ensure Nemotron/Qwen-Omni is running on `localhost:8101`:
```bash
# Check if anything listens
ss -tlnp | grep 8101
```

### eBay API errors
- Verify credentials in `config.yaml`
- Check eBay sandbox vs production endpoints
- Ensure OAuth token not expired (use `get_ebay_token.py` to refresh)

---

## 📞 Support

- **Issues**: https://github.com/SouthpawIN/pocket-shop/issues
- **Discord**: Hermes Agent community
- **Hermes docs**: https://hermes-agent.nousresearch.com/docs

---

**Built for the Hermes Agent Accelerated Business Hackathon**  
Presented by Nous Research × NVIDIA × Stripe


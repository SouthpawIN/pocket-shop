<p align="center">
  <img src="https://img.shields.io/badge/Powered%20by-Hermes%20Agent-7c3aed?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxwYXRoIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTV6TTIgMTdsMTAgNSAxMC01TTIgMTJsMTAgNSAxMC01Ii8+PC9zdmc+" />
  <img src="https://img.shields.io/badge/Hackathon-Demo%20Ready-22c55e?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Agents-9%20Strong-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Vision-Local%20RTX%203090-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Autonomous-24%2F7-red?style=for-the-badge" />
</p>

<h1 align="center">🏪 Pocket-Shop</h1>
<p align="center">
  <b>An autonomous AI agent that discovers, buys, prices, lists, and sells Magic cards for profit — then does it again.</b><br>
  <sub>Not a cron script. An agent that <i>thinks</i> about trading, learns from every cycle, and runs 24/7 with human oversight.</sub>
</p>

---

## ⚡ Powered by Hermes Agent

This isn't a collection of scripts glued together. Pocket-Shop is a **self-improving AI trading system** built on [Hermes Agent by Nous Research](https://hermes-agent.nousresearch.com). It has:

- 🧠 **Reasoning** — decides *when* to buy, *which* sets have edge, *what* to list
- 🔁 **Memory** — every dollar, every lesson, every mistake persists across sessions
- 🎯 **Skills** — teachable playbooks the agent loads and refines on its own
- ⏰ **Cron** — wakes itself up daily at 9am to hunt new opportunities
- 👁️ **Vision** — identifies cards from photos on a local RTX 3090 (no cloud API)
- 🤖 **Browser automation** — lists on eBay like a human, no API keys required
- 👥 **Multi-agent fleet** — 9 specialized agents cooperating on the full loop

### The Trading Loop (autonomous, 24/7)

```
                    ┌──────────────────────────────────────┐
                    │         🧠 senter (orchestrator)     │
                    │   owns the loop, holds the money,    │
                    │   decides what to buy next            │
                    └──────────────┬───────────────────────┘
                                   │
           ┌───────────────────────┴────────────────────────┐
           ▼                                                 ▼
   ┌──────────────────┐                          ┌────────────────────┐
   │ 🦅 crow          │                          │ ⚙️ chizul           │
   │ research agent   │  ──MTGStocks/Scryfall──▶ │ processor agent    │
   │ finds +EV sets   │                          │ prices + lists     │
   └──────────────────┘                          └────────────────────┘
           │                                                 │
           │  "Set X has 23% EV, buy when fund ≥ $500"        │  "Cards priced, eBay listings live"
           ▼                                                 ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                    📊 senter closes the loop                     │
   │   tracks sale → splits 30/30/40 → writes lesson → triggers cron │
   └──────────────────────────────────────────────────────────────────┘
```

### What the agent *learns* after every cycle

Every completed loop writes to persistent memory:

```
MEMORY: set=Innistrad Midnight Hunt | ev=18% | bought=$512 | revenue=$843
        takeaways: common foils overpriced on listing → price -12% next time
        buyer: @carddealer44 on eBay, repeat 3x → auto-bundle next shipment
```

The agent doesn't just repeat — it **adapts**.

---

## 🔄 How It Works

```
1. MONITOR MTGStocks → Find sets with EV > 10%
       ↓
2. RESEARCH PRICES → Amazon, MTGGoldfish, TCGPlayer
       ↓
3. PURCHASE SET    → When restock fund ≥ $500
       ↓
4. SCAN CARDS      → Vision identification when they arrive
       ↓
5. PRICE CARDS     → TCGPlayer lookup for each card
       ↓
6. LIST ON eBay    → Create listings automatically
       ↓
7. TRACK SALES     → 30% savings, 30% profit, 40% restock
       ↓
8. LOOP BACK       → When restock fund ready, repeat
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Setup

```bash
python setup.py
```

This will ask for:
- Gmail credentials (for sales monitoring)
- eBay mode preference (browser automation = no API needed)
- Optional: TCGPlayer API key

### 3. Configure Gmail App Password

1. Go to: https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to: https://myaccount.google.com/apppasswords
4. Create app password for "Mail" → "Other (Custom name)"
5. Copy the 16-character password

### 4. Run the Loop

```bash
python main_loop.py
```

Or — better — **let Hermes Agent do it**:
```bash
hermes run pocket-shop-loop
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HERMES AGENT RUNTIME                          │
│  (orchestration · memory · skills · cron · multi-agent router)  │
└──────┬──────────┬──────────┬──────────┬──────────┬───────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
 ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐
 │ Scryfall│ │ Browser │ │ Carnice │ │ Finance │ │  MTGStocks  │
 │   API   │ │ (Puppeteer│ │ Vision  │ │  Tracker│ │  Discovery  │
 │ (free)  │ │  eBay/TCG)│ │turbofit │ │ 30/30/40│ │   (daily)   │
 └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────────┘
                               │
                     ┌─────────┴─────────┐
                     │  dual RTX 3090    │
                     │  (local, no cloud)│
                     └───────────────────┘
```

| Layer              | Technology                        | Why                                      |
|--------------------|-----------------------------------|------------------------------------------|
| Orchestration      | **Hermes Agent**                  | Persistent memory, skills, cron, routing |
| Pricing            | **Scryfall API** (free)           | Accurate, no key required                |
| Buying/Selling     | **Browser automation**            | No API keys, bypasses bot detection      |
| Vision             | **Carnice** via `turbofit`        | Local model, 0.3s per card, no API cost  |
| Finance            | **30 / 30 / 40 split**            | Savings · Profit · Restock fund          |

---

## 📦 Module Overview

| Module | File | Purpose |
|--------|------|---------|
| 💰 Finance Tracker | `finance_tracker.py` | 30/30/40 revenue split with persistent state |
| 📈 MTGStocks Monitor | `mtgstocks_monitor.py` | Discover high-EV sets via browser scraping |
| 📷 Card Scanner | `card_scanner.py` | Local vision AI identifies cards from photos |
| 🔍 TCGPlayer Lookup | `tcgplayer_lookup.py` | Real-time market pricing per card |
| 🛒 eBay Listings | `ebay_listings.py` | Human-like listing via browser automation |
| 📬 Gmail Monitor | `gmail_monitor.py` | Detect sales notifications in real time |
| 🔁 Main Loop | `main_loop.py` | End-to-end orchestration glue |

---

## 🧠 Hermes Skills

The agent is taught to trade through five teachable skills — modular playbooks it loads, executes, and refines after every run:

| Skill | What it does |
|-------|-------------|
| `pocket-shop-loop` | Master loop: orchestrates the full buy → list → sell → reinvest cycle |
| `mtgstocks-set-discovery` | Hunts MTGStocks for sealed sets with ≥10% expected value |
| `multi-source-price-comparison` | Cross-checks prices across Scryfall, TCGPlayer, MTGGoldfish for edge |
| `card-scanner-vision` | Captures a photo → invokes local Carnice model → returns card name + set |
| `pocket-shop-finance-tracker` | Enforces the 30/30/40 split, writes every transaction to memory |

```bash
# Example: invoke a skill directly
hermes "run the pocket-shop-loop skill"
hermes "use card-scanner-vision on ~/photos/lot.jpg"
```

---

## ⏰ Cron Jobs

The agent wakes itself up. No `systemd` unit, no external scheduler.

```bash
# Daily discovery at 09:00 — agent runs mtgstocks-set-discovery
hermes cron add "0 9 * * *" \
  "Run the mtgstocks-set-discovery skill. If any set has EV > 15% AND my restock fund ≥ $500, start a purchase workflow. Write findings to memory."
```

What makes this different from a dumb cron:
- **Context-aware**: the agent reads memory, knows what it bought last week
- **Self-healing**: if scraping fails, it retries with a different strategy
- **Judgment calls**: it can decide *not* to act if conditions aren't right

---

## 👥 Multi-Agent Fleet

Nine specialized agents, one business:

| Agent | Role |
|-------|------|
| **senter** | Orchestrator · owns the trading loop & money · closes the loop |
| **crow** | Researcher · hunts +EV sets on MTGStocks, cross-checks Scryfall |
| **chizul** | Processor · prices cards, drafts eBay listings, handles sales ops |
| **scribe** | Memory archivist · distills lessons from every completed cycle |
| **watcher** | Gmail monitor · alerts senter the moment a sale lands |
| **scanner** | Vision operator · runs Carnice on RTX 3090, batch-processes photos |
| **pricer** | Valuation expert · triangulates prices across 4 sources |
| **lister** | Browser operator · fills eBay forms like a careful human |
| **finance** | Accountant · enforces 30/30/40, produces weekly P&L summaries |

### How they talk

```
crow ──"found +EV set"──▶ senter ──"check price"──▶ pricer
                                └──"cards arrived"──▶ scanner ──▶ chizul ──▶ lister
                                                                       │
                                                                       ▼
                                                              watcher ──"sold!"──▶ finance
                                                                                      │
                                                                                      ▼
                                                                      senter reads memory
                                                                      → writes lesson → cron
```

The agents don't share state through files — they share **memory**. When `scribe` distills a lesson, every agent sees it on their next wake-up.

---

## 🔑 API Keys Setup (Optional)

Browser automation is the **default** — no keys required. If you want faster API-based access:

### eBay API

1. **Create Developer Account**: https://developer.ebay.com/
2. **Create Application** in Developer Portal
3. **Get Credentials**: Developer ID · Certificate ID · RuName
4. **Get Refresh Token** via OAuth 2.0 flow

### TCGPlayer API

1. Go to https://www.tcgplayer.com/product/api
2. Sign up for a free developer account
3. Generate API key from the dashboard

### Manual Module Testing

```bash
# Finance tracking
python -c "from finance_tracker import record_sale; record_sale(50.00, 'Test Card')"

# TCGPlayer lookup
python tcgplayer_lookup.py

# Full setup wizard
python setup.py
```

---

## 🔒 Files Never Pushed to GitHub

These are in `.gitignore`:
- `config.yaml` — your credentials
- `.env` — environment variables
- `data/` — finance tracking data
- `hermes memory` — the agent's persistent memory is private by design

---

## 🙏 Support & License

Built as a hackathon demo (June 2026) on top of [Hermes Agent by Nous Research](https://hermes-agent.nousresearch.com).

**The pitch**: Anyone can write a cron script. This is an AI agent that *thinks* about trading, *learns* from every cycle, and *runs autonomously* with a human holding the reins — not doing the work.

Questions? Open an issue or ping the dev team.

<p align="center">
  <sub>Made with 🤖 by senter, crow, chizul & the fleet</sub>
</p>

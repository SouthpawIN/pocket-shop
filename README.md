# Pocket Shop 🛒

Automated Magic: The Gathering card shop system for tracking, pricing, and selling cards.

## Overview

Pocket Shop is a fully automated system that helps you run a small MTG card business from your phone or computer:

- **Monitor Sets**: Automatically checks MTGStocks for high expected-value sets
- **Price Cards**: Looks up current market prices on TCGPlayer
- **Scan Cards**: Uses your phone camera + AI vision to identify cards
- **Create Listings**: Generates eBay listing drafts with one command
- **Track Finance**: Automatically splits revenue into savings, profit, and restock funds
- **Email Monitoring**: Detects eBay sale notifications and auto-updates your books

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    POCKET SHOP SYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [MTGStocks] → [TCGPlayer] ← [Card Scanner]                │
│       |                |                |                   │
│       v                v                v                   │
│  [Set Monitor]   [Pricer]        [Vision AI]               │
│       |                |                                     │
│       +---------------+-------------------------------------+
│                         |
│                         v
│                  [eBay Listings]
│                         |
│                         v
│                   [Gmail Monitor] → [Finance Tracker]
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Revenue Split

Every sale automatically splits:
| Fund | Percentage | Purpose |
|------|------------|----------|
| **Savings** | 30% | Long-term accumulation |
| **Profit** | 30% | Your actual earnings |
| **Restock** | 40% | Reinvestment capital |

Example: $10.00 sale
```
savings_fund:   $3.00 (accumulate over time)
profit_total:   $3.00 (your actual profit)
restock_fund:   $4.00 (buy more cards)
```

## Installation

### Prerequisites

```bash
# Python 3.10+
sudo apt install python3-pip python3-venv

# Browser automation dependencies
sudo apt install chromium-browser chromium-driver

# For vision/card scanning
sudo apt install ffmpeg
```

### Setup

```bash
# Clone or navigate to project
cd ~/projects/pocket-shop

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure
cp config.example.yaml config.yaml
nano config.yaml  # Fill in your credentials
```

## Configuration

### config.yaml (DO NOT COMMIT TO GIT)

```yaml
# Restock fund target - when reached, consider expanding inventory
restock_fund_target: 500.00

# EV threshold for set monitoring (minimum expected value to flag)
ev_threshold: 10.0

# Revenue split percentages (must sum to 1.0)
profit_split:
  savings: 0.30    # Long-term accumulation fund
  profit: 0.30     # Actual earnings you keep
  restock: 0.40    # Reinvestment for buying more cards

# eBay API credentials (get from https://developer.ebay.com)
ebay_developer_id: "YOUR_EBAY_DEVELOPER_ID"
ebay_app_id: "YOUR_EBAY_APP_ID" 
ebay_cert_id: "YOUR_EBAY_CERT_ID"
ebay_refresh_token: "YOUR_EBAY_REFRESH_TOKEN"
ebay_marketplace: "EBAY_US"

# Gmail configuration (for sale email monitoring)
# Use App Password if 2FA enabled: https://myaccount.google.com/apppasswords
gmail_email: "your.email@gmail.com"
gmail_password: "YOUR_GMAIL_APP_PASSWORD"
```

### Get eBay API Credentials

1. Go to https://developer.ebay.com
2. Create a new application
3. Get your Developer ID, App ID, and Cert ID
4. Generate a refresh token using OAuth 2.0

### Get Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and your device
3. Generate app password
4. Use this in config.yaml instead of your regular password

## Usage

### CLI Commands

```bash
# Monitor MTGStocks for high EV sets
python3 main.py monitor-sets
python3 main.py monitor-sets --threshold 15.0

# Price a card on TCGPlayer
python3 main.py price "Lightning Bolt"
python3 main.py price "Black Lotus" --condition excellent

# Scan a card using phone camera
python3 main.py scan --device duo
python3 main.py scan --device s10

# Create eBay listing draft
python3 main.py list "Mind Breaker" --price 45.99
python3 main.py list "Urza's Mine" --price 125.00 --quantity 2

# Finance tracking
python3 main.py finance status
python3 main.py finance add 15.99 "Card Name Here"
python3 main.py finance history
python3 main.py finance history --limit 20

# Monitor Gmail for sales
python3 main.py monitor-emails
```

### Example Workflow

```bash
# 1. Check what sets are worth buying into
$ python3 main.py monitor-sets --threshold 15
Checking MTGStocks for sets with EV >= $15.0

Found 3 high EV sets:
------------------------------------------------------------
Modern Horizons 3
  EV: $23.45
  Buylist EV: $17.59

...

# 2. Scan a card you just bought
$ python3 main.py scan --device duo
Scanning card from phone camera...
Identified: Lightning Bolt
Set: Core Set 2021
Rarity: Common

# 3. Check the price
$ python3 main.py price "Lightning Bolt"
Looking up price for: Lightning Bolt
  Market Price: $1.25
  Low Price: $0.99
  Direct Price: $1.15

# 4. Create a listing
$ python3 main.py list "Lightning Bolt" --price 1.49
Creating listing for: Lightning Bolt
Draft created successfully: 123456789
```

## Cron Jobs (Automated Monitoring)

### Set Up Cron Jobs

```bash
# Add to crontab
crontab -e

# Monitor sets every 6 hours
0 */6 * * * ~/projects/pocket-shop/cron_jobs/monitor_sets.sh >> ~/logs/pocket-shop-sets.log 2>&1

# Monitor emails every 15 minutes
*/15 * * * * ~/projects/pocket-shop/cron_jobs/monitor_emails.sh >> ~/logs/pocket-shop-emails.log 2>&1
```

### What Cron Jobs Do

| Job | Schedule | Action |
|-----|----------|--------|
| `monitor_sets.sh` | Every 6 hours | Checks MTGStocks, logs high EV sets |
| `monitor_emails.sh` | Every 15 minutes | Checks Gmail for sales, auto-updates finance |

## Project Structure

```
pocket-shop/
├── config.example.yaml      # Template (commit this)
├── config.yaml              # Your config (.gitignored)
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── .gitignore               # Git ignore rules
├── browser_helpers/         # Browser automation
│   ├── mtgstocks_monitor.py
│   ├── tcgplayer_pricer.py
│   └── gmail_monitor.py
├── vision/
│   └── card_scanner.py
├── ebay/
│   └── listing_creator.py
├── finance/
│   └── tracker.py
├── cron_jobs/               # Cron scripts
│   ├── monitor_sets.sh
│   └── monitor_emails.sh
└── data/
    └── finance.json         # Financial records (.gitignored)
```

## Troubleshooting

### Playwright Browser Errors

```bash
# Install Chromium browser
playwright install chromium

# Or manually
sudo apt install chromium-browser
```

### Gmail Connection Errors

Make sure you're using an App Password, not your regular password:
https://myaccount.google.com/apppasswords

### eBay API Errors

Check that your refresh token is still valid. Tokens expire and need to be regenerated.

## License

MIT License - feel free to use and modify!

## Contributing

Issues, pull requests, and ideas welcome!

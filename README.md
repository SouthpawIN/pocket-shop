# Pocket-Shop - Automated MTG Card Trading System

Complete automated loop for profitable Magic: The Gathering card trading.

## How It Works

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

## Quick Start

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

## API Keys Setup Guide

### eBay API (Optional - Browser Mode is Default)

**Browser automation mode requires NO API keys** - it just navigates to eBay and fills forms like a human.

If you want faster API-based listing:

1. **Create Developer Account**: https://developer.ebay.com/
2. **Create Application**: 
   - Go to Developer Portal
   - Click "Register your app"
   - Fill in app details
3. **Get Credentials**:
   - Developer ID
   - Certificate ID  
   - RuName (App ID)
4. **Get Refresh Token**:
   - Use OAuth 2.0 flow
   - Or use eBay's token generator tool

### TCGPlayer API (Optional)

Browser automation works without an API key.

For faster programmatic access:
1. Go to: https://www.tcgplayer.com/product/api
2. Sign up for free developer account
3. Generate API key from dashboard

## Module Overview

| Module | File | Purpose |
|--------|------|---------|
| Finance Tracker | `finance_tracker.py` | 30/30/40 revenue split tracking |
| MTGStocks Monitor | `mtgstocks_monitor.py` | High EV set discovery |
| Card Scanner | `card_scanner.py` | Vision-based card ID |
| TCGPlayer Lookup | `tcgplayer_lookup.py` | Card price lookup |
| eBay Listings | `ebay_listings.py` | Create listings (browser or API) |
| Gmail Monitor | `gmail_monitor.py` | Sales notification tracking |
| Main Loop | `main_loop.py` | Complete orchestration |

## Manual Testing Each Module

```bash
# Test finance tracking
cd /path/to/Pocket-Shop/Source
python -c "from finance_tracker import record_sale; record_sale(50.00, 'Test Card')"

# Test TCGPlayer lookup
python tcgplayer_lookup.py  # Searches for "black lotus" by default

# Run setup to configure credentials
python setup.py
```

## Files Never Pushed to GitHub

- `config.yaml` - Your credentials
- `.env` - Environment variables
- `data/` - Finance tracking data

These are in `.gitignore` for security.

## Support

For issues or questions, check the documentation in `/docs/` folder.

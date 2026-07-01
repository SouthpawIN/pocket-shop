# AGENTS.md - Pocket-Shop Project Instructions

This document provides instructions for AI coding agents (Hermes, Claude Code, Codex, etc.) working on the Pocket-Shop automated MTG card trading system.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run initial setup (creates data/ directory and config.yaml)
python setup.py

# Run the main automation loop
python main_loop.py
```

## Project Structure

| Module | Purpose | Key Files |
|--------|---------|-----------|
| **Discovery** | Find sets with positive EV | `mtgstocks_discovery.py`, `mtgstocks_monitor.py` |
| **Pricing** | Multi-source price lookup | `scryfall_pricing.py`, `tcgplayer_lookup.py`, `tcgplayer_price_lookup.py` |
| **Card Processing** | Vision-based card identification | `card_scanner.py`, `auto_card_processor.py`, `process_cards.py` |
| **eBay Integration** | List and manage sales | `ebay_automation.py`, `ebay_listings.py`, `ebay_api.py` |
| **Finance** | Track revenue, profit, restock | `finance_tracker.py`, `finance/` directory |
| **Gmail Monitoring** | Detect sales notifications | `gmail_monitor.py` |
| **Sales** | Process completed sales | `sales_monitor.py`, `create_draft_listing.py` |
| **Vision** | Local card recognition model | `vision/` directory |
| **Browser Automation** | eBay/MTGStocks scraping | `browser_helpers/` directory |

## Testing Each Module

### Discovery & Pricing
```bash
# Test MTGStocks discovery
python mtgstocks_discovery.py --test

# Test Scryfall pricing lookup
python scryfall_pricing.py --test "Black Lotus"
```

### Card Processing
```bash
# Test card scanner with sample image
python card_scanner.py --test sample_card.jpg
```

### eBay Integration
```bash
# Test browser automation (dry run)
python ebay_automation.py --dry-run
```

### Finance Tracking
```bash
# Check current finance state
python finance_tracker.py --status
```

## Configuration & Secrets

**NEVER commit these files:**
- `config.yaml` (contains API keys, credentials)
- `.env` (environment variables)
- `data/` directory (contains finance.json, transaction history)

**DO commit:**
- `config.example.yaml` (template with placeholders)
- All Python modules
- Skills and documentation

## Hermes Agent Integration

This project uses **Hermes Agent** for orchestration. See `HERMES.md` for Hermes-specific details.

### Multi-Agent Fleet
- **senter** (orchestrator): Coordinates workflow, manages kanban tasks
- **chizul** (worker): Processes cards, creates listings
- **crow** (research): Price discovery, market analysis

### Skills
Located in `skills/` directory:
- `pocket-shop-loop`: Main orchestration
- `mtgstocks-set-discovery`: Automated discovery
- `card-scanner-vision`: Vision-based card recognition
- `multi-source-price-comparison`: Price aggregation
- `pocket-shop-finance-tracker`: Financial state management

### Cron Job (Daily Discovery)
```bash
# Create daily discovery job (9 AM)
hermes cron create '0 9 * * *' --name mtg-discovery

# Manually trigger discovery
hermes cron run <job_id>
```

## Code Style Guidelines

### Python Standards
- **Python 3.11+** required
- Use `pathlib.Path` instead of `os.path`
- Use `logging` module, not `print()` in production
- Type hints for all function signatures
- Use f-strings for formatting

### Example
```python
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def process_cards(image_path: Path) -> list[dict]:
    """Process card images and return identified cards."""
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return []
    
    # Use logging, not print
    logger.info(f"Processing {image_path}")
    return []
```

### Error Handling
- Use try/except with specific exceptions
- Log errors with `logger.error()` or `logger.exception()`
- Return meaningful error states, don't crash

### File Paths
```python
# ✓ Good - pathlib
data_dir = Path("data")
finance_file = data_dir / "finance.json"

# ✗ Bad - os.path
import os
data_dir = "data"
finance_file = os.path.join(data_dir, "finance.json")
```

## Architecture Notes

### Vision System
- **Local Model**: Carnice model running on GPU1 (http://127.0.0.1:8082/v1)
- **Fallback**: OpenRouter API when local model unavailable
- **Usage**: Card identification from photos when sets arrive

### Financial State
- Persisted in `data/finance.json`
- Allocations: 30% savings, 30% profit, 40% restock
- Triggers set purchase when restock fund ≥ $500

### Browser Automation
- eBay listing creation
- MTGStocks scraping for set discovery
- Fallback to API mode if browser fails

## Workflow

```
1. Cron job (9 AM) → mtgstocks_discovery.py
2. Find sets with EV > 10%
3. Research prices (Scryfall, TCGPlayer, MTGGoldfish)
4. If restock fund ≥ $500 → Purchase set
5. When cards arrive → Scan with vision model
6. Price each card → List on eBay
7. Track sales → Allocate funds
8. Loop back to step 1
```

## Development Tips

1. **Testing without real purchases**: Set `restock_target: 999999` in config.yaml
2. **Dry-run eBay listings**: Use `--dry-run` flag with ebay_automation.py
3. **Mock pricing**: Create test fixtures in `tests/fixtures/`
4. **Vision testing**: Use sample card images in `tests/sample_cards/`

## Common Issues

### Vision Model Unavailable
- Check if Carnice is running: `curl http://127.0.0.1:8082/v1/health`
- Fallback to OpenRouter automatically if local model fails

### Gmail Authentication
- Must use App Password (not regular password)
- Enable 2FA first, then create app-specific password

### eBay Browser Automation
- May trigger CAPTCHA on first run
- Use `--interactive` flag to solve manually

## Resources

- **Hermes Documentation**: https://hermes-agent.nousresearch.com/docs
- **Scryfall API**: https://scryfall.com/docs/api
- **eBay Developer**: https://developer.ebay.com/
- **MTGStocks**: https://www.mtgstocks.com/

---

**Last Updated**: June 30, 2026  
**Python Version**: 3.11+  
**Project Owner**: sovthpaw

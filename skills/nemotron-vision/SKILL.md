---
name: nemotron-vision
description: "Identify MTG cards using NVIDIA Nemotron 3 Ultra vision model with fallback chain"
trigger_conditions:
  - "Scanning MTG cards from photos for identification"
  - "Batch processing card images for pricing"
  - "User wants to identify a card from an image"
tools_required:
  - "terminal"
  - "read_file"
---

# Nemotron Vision Skill

## Overview

Uses **NVIDIA Nemotron 3 Ultra** (550B total, 55B active MoE) as the primary vision
model for MTG card identification. Falls back to Qwen-Omni and OpenRouter if Nemotron
is unavailable.

## Hackathon Integration

This satisfies the **NVIDIA Nemotron** requirement of the Hermes Agent Accelerated
Business Hackathon (Nous Research × NVIDIA × Stripe).

## Provider Chain

```
Nemotron 3 Ultra (localhost:8101)
    ↓ (on failure)
Qwen-Omni (localhost:8101)
    ↓ (on failure)
OpenRouter (cloud — Claude Sonnet / GPT-4V)
```

## Configuration

In `config.yaml`:

```yaml
vision:
  provider: "nemotron"    # Primary provider
  nemotron:
    base_url: "http://localhost:8101/v1"
    model: "nvidia/nemotron-3-ultra"
    api_key: ""            # Leave empty for local deployment
  qwen_omni:
    base_url: "http://localhost:8101/v1"
    model: "qwen-omni"
  openrouter:
    api_key: ""            # Set OPENROUTER_API_KEY env var
    model: "anthropic/claude-sonnet-4"
```

## Step-by-Step Workflow

### 1. Identify a Single Card

```python
from nemotron_vision import identify_card

result = identify_card("card_photo.jpg")
# Returns:
# {
#   "name": "Black Lotus",
#   "set_name": "Limited Edition Alpha",
#   "set_code": "lea",
#   "card_number": "232",
#   "condition": "Near Mint",
#   "is_foil": false,
#   "has_stamp": false,
#   "confidence": 0.95,
#   "provider_used": "nemotron"
# }
```

### 2. Force a Specific Provider

```python
result = identify_card("card.jpg", provider="openrouter")
```

### 3. Capture from Phone (ADB over Tailscale)

```python
from nemotron_vision import scan_card_from_phone

result = scan_card_from_phone("100.79.15.54:5555")
# Pulls latest camera image via ADB, then identifies
```

### 4. Full Pipeline (Identify → Price → Save)

```python
from auto_card_processor import process_single_card, process_batch

# Single card
result = process_single_card("card.jpg")
# → Identifies via Nemotron
# → Prices via Scryfall API
# → Saves to data/processed_cards/

# Batch
results = process_batch(["card1.jpg", "card2.jpg", "card3.jpg"])
```

## Vision Prompt

The model receives this prompt:

```
Identify this Magic: The Gathering trading card. Provide exact details:
1. Card name (exact name as printed on card)
2. Set name and set code (e.g., "Duskmourn: House of Horror [dsk]")
3. Card number if visible
4. Condition assessment: Mint, Near Mint, Excellent, Good, Lightly Played, Heavily Played, or Damaged
5. Whether it's foil, stamped, or has any special variants
6. Confidence level (0.0 to 1.0)

Format: {"name", "set_name", "set_code", "card_number", "condition", "is_foil", "has_stamp", "confidence"}
```

## Response Parsing

The `parse_vision_response()` function:
1. Extracts JSON from model output using regex
2. Falls back to full-content JSON parse
3. Returns `{"error": "..."}` on failure

## Verification Steps

1. Nemotron endpoint responds at `localhost:8101/v1/chat/completions`
2. Image base64 encoding produces valid data URL
3. Response contains valid JSON with card name
4. Confidence > 0.7 indicates reliable identification
5. Fallback chain activates when primary provider fails

## Pitfalls

- **Local model must be running**: Nemotron needs GPU endpoint at localhost:8101
- **Image quality matters**: Poor lighting/angle reduces accuracy
- **Foil glare**: Reflective cards may need multiple angles
- **Rate limits**: Scryfall API (called after identification) has 50-100ms rate limit

## CLI Usage

```bash
# Scan single card
python main.py scan card.jpg --price

# Batch process
python main.py process *.jpg --output results.json
```

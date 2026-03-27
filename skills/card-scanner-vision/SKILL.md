---
name: card-scanner-vision
description: "Use Hermes vision analysis to identify MTG cards from photos"
trigger_conditions:
  - "Scanning ordered MTG cards when they arrive"
  - "Identifying cards for pricing and listing"
tools_required:
  - "vision_analyze"
---

# Card Scanner Vision Skill

## Overview

Uses Hermes **vision_analyze** tool to identify Magic: The Gathering cards from photos, extracting card name, set information, condition assessment, and variant details.

### What it extracts:
- Card name (exact name as printed)
- Set name and set code (e.g., "Fourth Edition [4ED]")
- Card number if visible
- Condition assessment (Mint through Damaged)
- Foil/stamp/variant status
- Confidence level

## Hermes Tools Used

| Tool | Purpose |
|------|---------|
| `vision_analyze` | AI-powered image analysis for card identification |

## Step-by-Step Workflow

### 1. Capture Card Image

Image can come from:
- File path (scanned photos)
- Phone camera via ADB (S10 device)
- Screenshot from browser

```python
# From file
image_path = "/path/to/card/photo.jpg"

# Or capture from S10 camera via ADB
import subprocess
temp_file = "/tmp/card-scan.png"
subprocess.run(["adb", "-s", "RF8M221SXHZ", "exec-out", "screencap", "-p"], 
               stdout=open(temp_file, "wb"))
image_path = temp_file
```

### 2. Analyze Image with Vision Tool

```python
from hermes_tools import vision_analyze

def identify_card(image_path):
    """Identify a single card from an image."""
    print(f"Scanning card: {image_path}")
    
    result = vision_analyze(
        image_url=image_path,
        question="""Identify this Magic: The Gathering trading card. Provide:
1. Card name (exact name as printed)
2. Set name and set code (e.g., "Fourth Edition [4ED]")
3. Card number if visible
4. Condition assessment: Mint, Near Mint, Excellent, Good, Lightly Played, Heavily Played, or Damaged
5. Whether it's foil, stamped, or has any variants
6. Confidence level (0-1)

Format as JSON with keys: name, set_name, set_code, card_number, condition, is_foil, has_stamp, confidence"""
    )
    
    return parse_vision_result(result, image_path)
```

### 3. Parse Vision Result into Structured Data

```python
import json
import re

def parse_vision_result(analysis_text, image_path):
    """Parse vision analysis into structured card data."""
    
    # Try to extract JSON if present
    json_match = re.search(r'\{[^{}]+\}', analysis_text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # Fallback: manual parsing
    text = analysis_text.lower()
    
    return {
        "image_path": image_path,
        "name": "Unknown - needs manual review",
        "set_code": None,
        "set_name": None,
        "condition": "Unknown",
        "is_foil": False,
        "confidence": 0.0,
        "raw_analysis": analysis_text[:500]  # First 500 chars for reference
    }
```

### 4. Batch Scan Multiple Cards

```python
def batch_scan(image_paths):
    """Scan multiple card images."""
    results = []
    for path in image_paths:
        print(f"Processing: {path}")
        result = identify_card(path)
        if result:
            results.append(result)
    
    return results
```

### 5. Return Identified Card Data

```python
{
    "name": "Lightning Bolt",
    "set_name": "Core Set 2021",
    "set_code": "M21",
    "card_number": "106",
    "condition": "Near Mint",
    "is_foil": False,
    "has_stamp": False,
    "confidence": 0.95
}
```

## Condition Assessment Scale

| Condition | Description |
|-----------|-------------|
| Mint (M) | Perfect condition, no wear |
| Near Mint (NM) | Minimal wear, plays like new |
| Excellent (EL) | Light edge wear, no face scratches |
| Good (GD) | Moderate wear, minor face scratches |
| Lightly Played (LP) | Visible wear, creases possible |
| Heavily Played (HP) | Significant wear, may be bent |
| Damaged (DG) | Major damage, stains, cuts |

## Verification Steps

- Card name matches known MTG card database
- Set code is valid 2-5 character identifier
- Condition is one of the standard grades
- Confidence > 0.7 indicates reliable identification

## Pitfalls & Notes

**Lighting affects accuracy** - Good lighting produces better results

**Card must be in frame** - Partial cards may not identify correctly

**Foil cards can reflect** - Adjust angle to reduce glare

**Some cards look similar** - Vision may confuse similar art cards; verify with set code

## Example Usage

```python
# Single card scan
card_data = identify_card("/tmp/card-scan-001.jpg")
print(f"Identified: {card_data['name']} from {card_data['set_name']}")
print(f"Condition: {card_data['condition']}, Foil: {card_data['is_foil']}")

# Batch scan a whole set
import glob
card_images = glob.glob("/path/to/card-photos/*.jpg")
all_cards = batch_scan(card_images)
print(f"Identified {len(all_cards)} cards")
```

## Integration with Other Skills

Called by:
- **pocket-shop-loop** - After ordered sets arrive, scan all cards

Feeds into:
- **tcgplayer-pricing** - Price each identified card
- **ebay-listing-creator** - Create listings with card details
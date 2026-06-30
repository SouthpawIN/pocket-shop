---
name: card-scanner-vision
description: "Identify MTG cards from photos using vision analysis, extract card details (name, set, condition, foil), price them, and prepare eBay listings."
version: 1.0.0
author: SouthpawIN
license: MIT
platforms:
  - linux
tags:
  - mtg
  - vision
  - card-scanning
  - identification
  - ebay
---

# Card Scanner Vision

<!-- hermes.tags: mtg, vision, card-identification, scanning, condition-assessment, ebay-listing -->
<!-- hermes.related_skills: pocket-shop-loop, multi-source-price-comparison, pocket-shop-finance-tracker -->

This skill identifies Magic: The Gathering cards from photographs using the agent's **vision_analyze** tool. It extracts card name, set code, condition, foil/variant status, and confidence level. Results feed into pricing (via TCGPlayer/Scryfall lookup) and eBay listing creation.

## When to Use

- Ordered MTG cards have arrived and need to be scanned
- The user says "scan these cards" or "identify cards from photos"
- The **pocket-shop-loop** skill calls this during Phase 5 (card scanning)
- The user wants to batch-process a folder of card images

## Tools Overview

| Tool | Purpose |
|------|---------|
| **vision_analyze** | AI-powered image analysis to identify the card |
| **terminal** | Run `card_scanner.py`, `auto_card_processor.py`, `scryfall_pricing.py` |
| **browser_navigate** | Open eBay listing creation pages |
| **read_file** | Load card image paths from a directory listing |
| **write_file** | Save scan results to a JSON file |
| **delegate_task** | Parallelize scanning of many cards |

## Steps

### Step 1 — Prepare Card Images

Identify the directory or file paths containing card photographs:

```
terminal: ls /path/to/card-photos/*.jpg
```

Or use **read_file** on a manifest file if one exists:

```
read_file: data/card_images.txt
```

Images can come from:
- Scanned photos saved to disk
- Phone camera via ADB (Samsung S10):

```
terminal: adb -s RF8M221SXHZ exec-out screencap -p > /tmp/card-scan.png
```

- Manual uploads by the user

### Step 2 — Analyze Each Card with vision_analyze

For each card image, use **vision_analyze** with a structured prompt:

```
vision_analyze:
  image: /path/to/card-photo.jpg
  prompt: "Identify this Magic: The Gathering trading card. Provide:
    1. Card name (exact name as printed)
    2. Set name and set code (e.g., 'Fourth Edition [4ED]')
    3. Card number if visible
    4. Condition: Mint, Near Mint, Excellent, Good, Lightly Played, Heavily Played, or Damaged
    5. Whether it is foil, stamped, or has any special variants
    6. Your confidence level (0.0 to 1.0)
    Respond in a structured format with these fields."
```

### Step 3 — Parse Vision Results

From the vision response, extract the structured fields:
- **name**: "Lightning Bolt"
- **set_name**: "Core Set 2021"
- **set_code**: "M21"
- **card_number**: "106"
- **condition**: "Near Mint"
- **is_foil**: false
- **confidence**: 0.95

If confidence is below 0.7, flag the card for manual review.

### Step 4 — Batch Process with Project Scripts

For large batches, use the project's card processing scripts via **terminal**:

```
terminal: python3 card_scanner.py --input-dir /path/to/card-photos/ --output data/scanned_cards.json
```

Or the auto-processor which handles scanning + pricing in one step:

```
terminal: python3 auto_card_processor.py --input-dir /path/to/card-photos/
```

These scripts iterate over all images and output a JSON file with identified cards.

### Step 5 — Price Identified Cards

After scanning, price each card using Scryfall lookup:

```
terminal: python3 scryfall_pricing.py --card "Lightning Bolt" --set M21
```

Or use **web_search** to check TCGPlayer:

```
web_search: "Lightning Bolt M21 near mint price site:tcgplayer.com"
```

Then **browser_navigate** to the TCGPlayer listing and **browser_snapshot** to extract the exact price.

### Step 6 — Create eBay Listings

For each priced card, either:

**Option A — Use project scripts:**

```
terminal: python3 create_draft_listing.py --card "Lightning Bolt" --set M21 --condition NM --price 5.00
```

**Option B — Use browser automation:**

1. **browser_navigate** to `https://www.ebay.com/sl/prelist/suggest`
2. **browser_type** the card name into the search/title field
3. **browser_click** to select matching suggestions
4. Fill in condition, price, and shipping details using **browser_type** and **browser_click**
5. **browser_snapshot** to verify the listing before submitting

**Option C — Use delegate_task for bulk listings:**

```
delegate_task with tasks:
  - task: "Create eBay listing for Lightning Bolt M21 NM at $5.00"
  - task: "Create eBay listing for Counterspell M21 NM at $3.50"
  - task: "Create eBay listing for Birds of Paradise M21 NM at $8.00"
```

### Step 7 — Save Results

Write the complete scan results to disk:

```
write_file: data/scanned_cards.json with the array of identified card objects
```

Also use **memory** to store a summary for quick access:

```
memory: store "card_scan_<date>" with count of cards scanned, total estimated value
```

## Condition Assessment Scale

| Grade | Abbreviation | Description |
|-------|-------------|-------------|
| Mint | M | Perfect condition, no visible wear |
| Near Mint | NM | Minimal wear, plays like new |
| Excellent | EX | Light edge wear, no face scratches |
| Good | GD | Moderate wear, minor face scratches |
| Lightly Played | LP | Visible wear, creases possible |
| Heavily Played | HP | Significant wear, may be bent |
| Damaged | DG | Major damage, stains, tears, or cuts |

## Pitfalls

- **Lighting is critical** — poor lighting or harsh glare on foil cards drastically reduces identification accuracy. Reshoot if confidence < 0.7.
- **Partial cards fail** — the entire card face must be visible in the frame. Cropped edges or fingers covering text will confuse the model.
- **Similar art cards** — some cards have nearly identical art across sets (e.g., basic lands, reprints). Always verify the set code, not just the card name.
- **Foil reflections** — foil cards reflect light unpredictably. Tilt the card slightly or use diffuse lighting.
- **Double-sided cards** — Transform and Modal DFC cards need both sides photographed for full identification.
- **Batch processing is slow** — `auto_card_processor.py` processes cards sequentially; for 50+ cards, use **delegate_task** to split the work across parallel subagents.
- **eBay browser automation may break** — eBay frequently updates their listing flow. If browser clicks stop working, fall back to `create_draft_listing.py` which generates draft data for manual entry.

## Verification

- Card names should match known MTG cards (verify against Scryfall if unsure).
- Set codes should be valid 2–5 character identifiers (e.g., "M21", "MH3", "4ED").
- Condition should be one of the seven standard grades.
- Confidence should be > 0.7 for the result to be considered reliable; anything lower needs manual review.
- The count of scanned cards should match the number of image files in the input directory.
- After pricing, each card should have a positive price value.
- Draft eBay listings (if created) should contain the correct card name, set, condition, and price.

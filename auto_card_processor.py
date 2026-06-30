#!/usr/bin/env python3
"""
Auto Card Processor - Modernized for Hackathon v2.0
=====================================================

Pipeline:
1. Capture card image from phone (ADB over Tailscale) or local file
2. Identify card using Nemotron 3 Ultra vision (fallback chain)
3. Get accurate pricing from Scryfall API
4. Optionally create eBay draft listing via API

Designed for batch processing hundreds of cards.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from hermes_config import get_config
from nemotron_vision import identify_card, scan_card_from_phone
from scryfall_pricing import get_card_pricing, get_market_price

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed_cards"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def process_single_card(image_path: str, verbose: bool = True) -> dict:
    """Process a single card: identify → price → output result."""
    result = {"timestamp": datetime.now().isoformat(), "image": str(image_path)}

    # Step 1: Vision identification
    if verbose:
        print(f"\n{'='*60}")
        print(f"Processing: {image_path}")
        print(f"{'='*60}")

    card_id = identify_card(image_path)
    result["identification"] = card_id

    if "error" in card_id:
        print(f"  ✗ Vision failed: {card_id['error']}")
        return result

    name = card_id.get("name", "Unknown")
    set_code = card_id.get("set_code", "")
    print(f"  ✓ Card: {name} [{set_code}] (confidence: {card_id.get('confidence', '?')})")

    # Step 2: Scryfall pricing
    if verbose:
        print(f"\n  Looking up pricing via Scryfall...")

    pricing = get_card_pricing(name, set_code or None)
    result["pricing"] = pricing

    if pricing.get("success"):
        prices = pricing.get("prices", {})
        usd = prices.get("usd_non_foil") or prices.get("usd_foil")
        print(f"  ✓ Price: ${usd or 'N/A'}")
    else:
        print(f"  ✗ Pricing failed: {pricing.get('error', 'Unknown')}")

    # Step 3: Save result
    out_file = OUTPUT_DIR / f"card_{int(time.time())}.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    if verbose:
        print(f"  ✓ Saved to: {out_file}")

    return result


def process_batch(image_paths: list, verbose: bool = True) -> list:
    """Process multiple cards in sequence."""
    results = []
    total = len(image_paths)
    for i, path in enumerate(image_paths, 1):
        if verbose:
            print(f"\n[{i}/{total}] Processing batch...")
        result = process_single_card(path, verbose=verbose)
        results.append(result)
        if i < total:
            time.sleep(1)  # Respect Scryfall rate limits
    return results


def process_from_phone(device_ip: str, count: int = 1) -> list:
    """Capture and process cards from phone camera."""
    results = []
    for i in range(count):
        print(f"\n📸 Capture {i+1}/{count} — position card and press Enter")
        input()
        result = scan_card_from_phone(device_ip)
        results.append(result)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pocket Shop Auto Card Processor v2.0")
    parser.add_argument("images", nargs="*", help="Card image paths to process")
    parser.add_argument("--phone", help="Phone device IP:port for ADB capture")
    parser.add_argument("--count", type=int, default=1, help="Number of cards to capture from phone")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    if args.phone:
        results = process_from_phone(args.phone, args.count)
    elif args.images:
        results = process_batch(args.images, verbose=not args.quiet)
    else:
        parser.print_help()
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"Processed {len(results)} card(s)")
    identified = sum(1 for r in results if "error" not in r.get("identification", {}))
    print(f"Successfully identified: {identified}/{len(results)}")

### CARD IDENTIFICATION ###


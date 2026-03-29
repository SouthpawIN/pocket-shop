#!/usr/bin/env python3
"""
Auto Card Processor - Complete Automated Loop
=============================================

This script automates the complete card processing pipeline:
1. Capture card image from S10 camera (via ADB over TailScale)
2. Identify card using Qwen-Omni vision analysis
3. Get accurate pricing from Scryfall API
4. Create eBay draft listing

Designed for batch processing hundreds of cards.
"""

import time
import json
import requests
import base64
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

### CONFIGURATION ###

# S10 Device Configuration (TailScale)
S10_ADB_DEVICE = "100.93.96.90:5555"  # TailScale IP with TCP/IP mode
S10_ADB_SERIAL = "RF8M221SXHZ"         # USB serial (if connected)

# Qwen-Omni Vision Model
QWEN_OMNI_URL = "http://localhost:8101/v1/chat/completions"

# Output directory for processed cards
OUTPUT_DIR = Path("~/projects/pocket-shop/data/processed_cards").expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

### IMPORT LOCAL MODULES ###

try:
    from scryfall_pricing import get_card_pricing as get_pricing_scryfall
    from ebay_automation import create_ebay_draft as create_draft_ebay
except ImportError:
    print("Warning: Local modules not found, using built-in functions")

### CARD IDENTIFICATION ###

def identify_card_vision(image_path: str) -> dict:
    """Use Qwen-Omni vision to identify a Magic card from image."""
    
    print(f"\n📸 Identifying card from: {image_path}")
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
        image_b64 = base64.b64encode(image_data).decode('utf-8')
    
    # Prepare vision request
    payload = {
        "model": "qwen-omni",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                {
                    "type": "text",
                    "text": """Identify this Magic: The Gathering trading card. Provide exact details:

1. Card name (exact name as printed on card)
2. Set name and set code (e.g., "Duskmourn: House of Horror [dsk]")
3. Card number if visible
4. Condition assessment: Mint, Near Mint, Excellent, Good, Lightly Played, Heavily Played, or Damaged
5. Whether it's foil, stamped, or has any special variants
6. Confidence level (0.0 to 1.0)

Format your response as a valid JSON object with these exact keys:
{"name", "set_name", "set_code", "card_number", "condition", "is_foil", "has_stamp", "confidence"}

Do not include markdown formatting or code blocks - just raw JSON."""
                }
            ]
        }],
        "max_tokens": 300,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(QWEN_OMNI_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[^{}]+\}', content)
            if json_match:
                card_data = json.loads(json_match.group())
                print(f"✓ Identified: {card_data.get('name', 'Unknown')}")
                return card_data
            else:
                print(f"⚠ Could not parse vision result: {content[:200]}")
                return {"error": "Parse failed", "raw": content}
        else:
            print(f"✗ Vision API error: {response.status_code}")
            return {"error": f"API error {response.status_code}"}
            
    except Exception as e:
        print(f"✗ Vision analysis failed: {e}")
        return {"error": str(e)}


### PRICING (SCRYFALL) ###

def get_card_pricing_scryfall(card_name: str, set_code: str = None) -> dict:
    """Get accurate card pricing from Scryfall API."""
    
    print(f"\n💰 Looking up pricing for: {card_name}")
    
    headers = {
        "User-Agent": "Pocket-Shop/1.0 (automated-mtg-trading)"
    }
    
    # Search for the card
    search_url = "https://api.scryfall.com/cards/search"
    params = {
        "q": f"name:\"{card_name}\"",
        "order": "relevancy",
        "unique": "prints",
        "include_extras": "true"
    }
    
    try:
        response = requests.get(search_url, params=params, headers=headers)
        
        if response.status_code != 200:
            print(f"✗ Scryfall search failed: {response.status_code}")
            return {"error": f"API error {response.status_code}"}
        
        data = response.json()
        
        if data.get('object') == 'error':
            print(f"✗ Card not found or error: {data.get('text', 'Unknown error')}")
            return {"error": "Card not found"}
        
        cards = data.get('data', [])
        
        if not cards:
            print("✗ No cards found in search results")
            return {"error": "No results"}
        
        # Find the best match (filter by set code if provided)
        best_card = None
        if set_code:
            for card in cards:
                if card.get('set') == set_code:
                    best_card = card
                    break
        
        if not best_card:
            best_card = cards[0]  # Use first result
        
        # Extract pricing info
        pricing_info = {
            "card_name": best_card.get('name'),
            "set_name": best_card.get('set_name'),
            "set_code": best_card.get('set'),
            "rarity": best_card.get('rarity'),
            "prices": {}
        }
        
        # Get Scryfall estimated prices
        if 'prices' in best_card:
            p = best_card['prices']
            pricing_info["prices"] = {
                "usd_non_foil": p.get('usd'),
                "usd_foil": p.get('usd_foil'),
                "eur_non_foil": p.get('eur'),
                "eur_foil": p.get('eur_foil'),
                "tix": p.get('tix')
            }
        
        # Get marketplace links
        if 'market_data' in best_card:
            mk = best_card['market_data']
            pricing_info["tcgplayer_url"] = mk.get('tcgplayer_url')
            pricing_info["cardkingdom_url"] = mk.get('cardkingdom_url')
            pricing_info["cardmarket_url"] = mk.get('cardmarket_url')
        
        print(f"✓ Pricing found:")
        prices = pricing_info.get('prices', {})
        if prices.get('usd_non_foil'):
            print(f"  Non-Foil: ${prices['usd_non_foil']}")
        if prices.get('usd_foil'):
            print(f"  Foil:     ${prices['usd_foil']}")
        
        return pricing_info
        
    except Exception as e:
        print(f"✗ Pricing lookup failed: {e}")
        return {"error": str(e)}


### CAMERA CAPTURE (S10) ###

def capture_from_s10(output_path: str = None) -> str:
    """Capture screen from S10 via ADB over TailScale."""
    
    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        output_path = tmp.name
    
    print(f"\n📱 Capturing from S10 ({S10_ADB_DEVICE})...")
    
    try:
        # Use ADB to capture screen
        cmd = [
            'adb', '-s', S10_ADB_DEVICE,
            'exec-out', 'screencap', '-p'
        ]
        
        result = subprocess.run(
            cmd,
            stdout=open(output_path, 'wb'),
            check=True,
            timeout=10
        )
        
        print(f"✓ Captured to: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Capture failed: {e}")
        return None
    except Exception as e:
        print(f"✗ Capture error: {e}")
        return None


### EBAY LISTING ###

def create_ebay_draft(card_info: dict, pricing_info: dict) -> dict:
    """Create eBay draft listing for a card."""
    
    # Determine listing price (use non-foil price by default)
    prices = pricing_info.get('prices', {})
    if card_info.get('is_foil'):
        listing_price = prices.get('usd_foil') or prices.get('usd_non_foil')
    else:
        listing_price = prices.get('usd_non_foil')
    
    if not listing_price:
        print("⚠ No price found - cannot create listing")
        return {"error": "No pricing available"}
    
    # Convert to float (Scryfall sometimes returns strings)
    try:
        listing_price = float(listing_price)
    except (TypeError, ValueError):
        print(f"⚠ Could not convert price to float: {listing_price}")
        return {"error": "Invalid price format"}
    
    # Prepare listing data
    listing_data = {
        "title": f"MTG {card_info['name']} [{pricing_info.get('set_code', '?')}]",
        "price": round(listing_price, 2),
        "quantity": 1,
        "condition": card_info.get('condition', 'Near Mint'),
        "description": f"Magic: The Gathering - {card_info['name']}\n"
                       f"Set: {pricing_info.get('set_name', 'Unknown')}\n"
                       f"Condition: {card_info.get('condition', 'Near Mint')}\n"
                       f"{'Foil' if card_info.get('is_foil') else 'Non-Foil'}"
    }
    
    print(f"\n📝 Prepared eBay listing:")
    print(f"   Title: {listing_data['title']}")
    print(f"   Price: ${listing_data['price']:.2f}")
    print(f"   Condition: {listing_data['condition']}")
    
    # TODO: Integrate with eBay browser automation or API
    # For now, just return the prepared data
    
    return {
        "success": True,
        "listing_data": listing_data,
        "status": "prepared"  # Not yet submitted
    }


### MAIN PROCESSING LOOP ###

def process_single_card(image_path: str = None, capture_from_s10_first: bool = False) -> dict:
    """Process a single card through the complete pipeline."""
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "steps_completed": [],
        "errors": []
    }
    
    # Step 1: Capture from S10 if requested
    if capture_from_s10_first:
        image_path = capture_from_s10()
        if not image_path:
            result["errors"].append("Failed to capture from S10")
            return result
        result["image_path"] = image_path
        result["steps_completed"].append("capture")
    elif not image_path:
        result["errors"].append("No image path provided and capture not requested")
        return result
    
    # Step 2: Identify card with vision
    card_info = identify_card_vision(image_path)
    if 'error' in card_info:
        result["errors"].append(f"Card identification failed: {card_info.get('error')}")
        return result
    result["card_info"] = card_info
    result["steps_completed"].append("identification")
    
    # Step 3: Get pricing from Scryfall
    pricing_info = get_card_pricing_scryfall(
        card_info.get('name'),
        card_info.get('set_code')
    )
    if 'error' in pricing_info:
        result["errors"].append(f"Pricing lookup failed: {pricing_info.get('error')}")
        return result
    result["pricing_info"] = pricing_info
    result["steps_completed"].append("pricing")
    
    # Step 4: Prepare eBay listing
    listing_result = create_ebay_draft(card_info, pricing_info)
    if 'error' in listing_result:
        result["errors"].append(f"Listing preparation failed: {listing_result.get('error')}")
        return result
    result["listing"] = listing_result
    result["steps_completed"].append("listing_preparation")
    
    # Save processed card data
    output_file = OUTPUT_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{card_info.get('name', 'unknown').replace(' ', '_')}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    result["saved_to"] = str(output_file)
    result["steps_completed"].append("saved")
    
    return result


def batch_process_from_directory(image_dir: str, output_file: str = None):
    """Process multiple card images from a directory."""
    
    image_path = Path(image_dir).expanduser()
    image_files = list(image_path.glob("*.png") + image_path.glob("*.jpg") + image_path.glob("*.jpeg"))
    
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING: {len(image_files)} images found")
    print(f"{'='*60}\n")
    
    all_results = []
    
    for i, img_file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] Processing: {img_file.name}")
        result = process_single_card(str(img_file))
        all_results.append({"file": str(img_file), "result": result})
        
        # Small delay between requests
        time.sleep(1)
    
    # Save batch summary
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\nBatch results saved to: {output_file}")
    
    return all_results


### CLI INTERFACE ###

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Card Processor - Complete MTG card automation pipeline")
    parser.add_argument("--capture", action="store_true", help="Capture from S10 camera first")
    parser.add_argument("--image", type=str, help="Path to card image file")
    parser.add_argument("--batch", type=str, help="Directory containing multiple card images")
    parser.add_argument("--output", type=str, help="Output file for batch results")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("POCKET-SHOP AUTO CARD PROCESSOR")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.batch:
        # Batch processing mode
        results = batch_process_from_directory(args.batch, args.output)
        
        # Summary
        successful = sum(1 for r in results if not r['result'].get('errors'))
        print(f"\n{'='*60}")
        print(f"BATCH COMPLETE")
        print(f"{'='*60}")
        print(f"Total: {len(results)} cards")
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        
    elif args.capture or args.image:
        # Single card mode
        result = process_single_card(
            image_path=args.image,
            capture_from_s10_first=args.capture
        )
        
        if not result.get('errors'):
            print(f"\n{'='*60}")
            print("CARD PROCESSED SUCCESSFULLY")
            print(f"{'='*60}")
            print(f"Card: {result['card_info'].get('name')}")
            print(f"Set: {result['pricing_info'].get('set_name')}")
            prices = result['pricing_info'].get('prices', {})
            if prices.get('usd_non_foil'):
                print(f"Price: ${prices['usd_non_foil']}")
            print(f"Saved to: {result.get('saved_to', 'N/A')}")
        else:
            print(f"\nProcessing failed:")
            for err in result.get('errors', []):
                print(f"  ✗ {err}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

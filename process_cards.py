#!/usr/bin/env python3
"""
Pocket-Shop Card Processor - Simple CLI
=======================================

Usage:
  # Capture from S10 and process single card:
  python3 process_cards.py --capture
  
  # Process an existing image:
  python3 process_cards.py --image /path/to/card.png
  
  # Batch process all images in a directory:
  python3 process_cards.py --batch ~/card-photos/
"""

from auto_card_processor import process_single_card, batch_process_from_directory
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(
        description="Pocket-Shop Card Processor - Automated MTG card pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Capture from S10 camera and identify card:
  python3 process_cards.py --capture
  
  # Process a saved image file:
  python3 process_cards.py --image /tmp/card-scan.png
  
  # Batch process all images in directory:
  python3 process_cards.py --batch ~/photos/cards/
  
  # Batch with custom output file:
  python3 process_cards.py --batch ~/photos/cards/ --output results.json
"""
    )
    
    parser.add_argument(
        "--capture", 
        action="store_true",
        help="Capture image from S10 camera via ADB, then process"
    )
    
    parser.add_argument(
        "--image", 
        type=str,
        help="Path to card image file to process"
    )
    
    parser.add_argument(
        "--batch", 
        type=str,
        help="Directory containing multiple card images for batch processing"
    )
    
    parser.add_argument(
        "--output", 
        type=str,
        help="Output file for batch results (JSON)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  POCKET-SHOP CARD PROCESSOR")
    print("  S10 Camera → Qwen-Omni Vision → Scryfall Pricing")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.batch:
        # Batch processing
        print(f"📁 Batching mode - processing directory: {args.batch}")
        results = batch_process_from_directory(args.batch, args.output)
        
        successful = sum(1 for r in results if not r['result'].get('errors'))
        print(f"\n{'='*60}")
        print("📊 BATCH SUMMARY")
        print(f"{'='*60}")
        print(f"  Total cards:    {len(results)}")
        print(f"  Successful:     {successful}")
        print(f"  Failed:         {len(results) - successful}")
        if args.output:
            print(f"  Results saved:  {args.output}")
            
    elif args.capture or args.image:
        # Single card processing
        result = process_single_card(
            image_path=args.image,
            capture_from_s10_first=args.capture
        )
        
        if not result.get('errors'):
            print(f"\n{'='*60}")
            print("✅ CARD PROCESSED")
            print(f"{'='*60}")
            
            card_name = result['card_info'].get('name', 'Unknown')
            set_name = result['pricing_info'].get('set_name', 'Unknown')
            set_code = result['pricing_info'].get('set_code', '?')
            rarity = result['pricing_info'].get('rarity', 'Unknown')
            
            print(f"  Card:    {card_name}")
            print(f"  Set:     {set_name} [{set_code}]")
            print(f"  Rarity:  {rarity}")
            print(f"  Condition: {result['card_info'].get('condition', 'Unknown')}")
            
            prices = result['pricing_info'].get('prices', {})
            if prices:
                print(f"\n  💰 PRICING:")
                if prices.get('usd_non_foil'):
                    print(f"    Non-Foil: ${prices['usd_non_foil']}")
                if prices.get('usd_foil'):
                    print(f"    Foil:     ${prices['usd_foil']}")
            
            if result.get('listing', {}).get('listing_data'):
                listing = result['listing']['listing_data']
                print(f"\n  📝 EBAY DRAFT PREPARED:")
                print(f"    Title: {listing.get('title')}")
                print(f"    Price: ${listing.get('price', 0):.2f}")
            
            print(f"\n  💾 Saved to: {result.get('saved_to', 'N/A')}")
            
        else:
            print(f"\n❌ PROCESSING FAILED")
            print(f"{'='*60}")
            for err in result.get('errors', []):
                print(f"  ✗ {err}")
                
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

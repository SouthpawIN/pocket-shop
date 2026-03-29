#!/usr/bin/env python3
"""TCGPlayer Price Lookup using Playwright with proper anti-detection

This script navigates to TCGPlayer, waits for JavaScript rendering,
and extracts actual market prices for a given card.
"""

import time
import re
import sys
from playwright.sync_api import sync_playwright

def get_tcgplayer_price(card_name: str) -> dict:
    """Get TCGPlayer price for a card using browser automation."""
    
    print(f"\n{'='*60}")
    print(f"TCGPlayer Price Lookup")
    print(f"{'='*60}")
    print(f"Searching for: {card_name}\n")
    
    with sync_playwright() as p:
        # Launch headless browser
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        
        # Create context with realistic settings
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        page = context.new_page()
        
        try:
            # Navigate to TCGPlayer with the card name in URL
            search_url = f"https://www.tcgplayer.com/search/products?q={card_name.replace(' ', '+')}"
            print(f"Navigating to: {search_url}")
            page.goto(search_url, wait_until="networkidle", timeout=30000)
            
            # Wait for content to load
            time.sleep(3)
            
            # Get page info
            title = page.title()
            current_url = page.url
            print(f"Page title: {title}")
            print(f"Current URL: {current_url}\n")
            
            # Extract visible text content
            visible_text = page.evaluate("() => document.body.innerText")
            
            # Check if card was found
            card_found_lower = card_name.lower().replace(' ', '-')
            if card_name.lower() in visible_text.lower():
                print(f"\u2713 Card '{card_name}' found in page content")
            else:
                print(f"\u26a0  Card name not directly found, checking for alternatives...")
            
            # Check for "no results" message
            if 'no results' in visible_text.lower() or 'no products' in visible_text.lower():
                print("\u2717 No results found on TCGPlayer")
                return {"success": False, "error": "No results found", "card_name": card_name}
            
            # Extract prices using multiple patterns
            price_patterns = [
                r'\$([\d,]+\.\d{2})',  # Standard format: $123.45
                r'data-price="([\d.]+)"',  # Data attribute format
            ]
            
            all_prices = []
            for pattern in price_patterns:
                matches = re.findall(pattern, visible_text)
                all_prices.extend(matches)
            
            # Also try to get prices from page source
            page_source = page.content()
            source_prices = re.findall(r'\$([\d,]+\.\d{2})', page_source)
            all_prices.extend(source_prices)
            
            # Convert to floats and filter reasonable range
            def parse_price(p):
                try:
                    return float(p.replace(',', ''))
                except:
                    return None
            
            valid_prices = [p for p in [parse_price(pr) for pr in all_prices] if p and 0.01 <= p <= 10000]
            
            if valid_prices:
                print(f"\nPrices found: {len(set(valid_prices))} unique prices")
                unique_sorted = sorted(set(valid_prices))
                
                # Show first few prices
                for i, price in enumerate(unique_sorted[:10], 1):
                    print(f"  {i}. ${price:.2f}")
                
                # Return pricing info
                return {
                    "success": True,
                    "card_name": card_name,
                    "min_price": min(valid_prices),
                    "max_price": max(valid_prices),
                    "avg_price": sum(valid_prices) / len(valid_prices),
                    "price_count": len(valid_prices),
                    "sample_prices": unique_sorted[:5]
                }
            else:
                print("\u26a0  No valid prices extracted")
                
                # Try to identify what's on the page
                print("\nPage content preview (first 500 chars):")
                print(visible_text[:500])
                
                return {"success": False, "error": "No prices extracted", "card_name": card_name}
                
        except Exception as e:
            print(f"Error during lookup: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e), "card_name": card_name}
            
        finally:
            browser.close()


def main():
    # Default card or use command line argument
    card_name = sys.argv[1] if len(sys.argv) > 1 else "Disturbing Mirth"
    
    result = get_tcgplayer_price(card_name)
    
    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    
    if result["success"]:
        print(f"Card: {result['card_name']}")
        print(f"Min Price: ${result['min_price']:.2f}")
        print(f"Max Price: ${result['max_price']:.2f}")
        print(f"Avg Price: ${result['avg_price']:.2f}")
        print(f"Samples: {[f'${p:.2f}' for p in result['sample_prices']]}")
    else:
        print(f"Failed to get price for {result.get('card_name', 'unknown')}")
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    return result


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create eBay Draft Listing for Disturbing Mirth

This script creates a draft listing using browser automation.
No API credentials needed - just log in to your eBay account when prompted.
"""

import time
from pathlib import Path

# Card information from our scan
CARD_INFO = {
    "name": "Disturbing Mirth",
    "set_code": "M3C",  # Modern Horizons 3
    "condition": "near_mint",
    "price": 0.29,  # Competitive price for uncommon single
    "quantity": 1,
    "description": "Single card from Modern Horizons 3. Near Mint condition - minimal wear, plays like new.",
    "image_path": "/tmp/card_capture.png"  # The screenshot we captured
}

def create_draft_listing():
    """Create a draft listing on eBay using browser automation."""
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Installing playwright...")
        import subprocess
        subprocess.run(["pip", "install", "playwright", "--break-system-packages"], check=True)
        subprocess.run(["playwright", "install", "chromium"], check=True)
        from playwright.sync_api import sync_playwright
    
    print("="*60)
    print("EBAY DRAFT LISTING CREATOR")
    print("="*60)
    print(f"\nCard: {CARD_INFO['name']}")
    print(f"Set: {CARD_INFO['set_code']} (Modern Horizons 3)")
    print(f"Condition: {CARD_INFO['condition'].replace('_', ' ').title()}")
    print(f"Price: ${CARD_INFO['price']:.2f}")
    print(f"Quantity: {CARD_INFO['quantity']}")
    print("\nBrowser will open - please log in to eBay if not already logged in.")
    print("Press Ctrl+C to cancel at any time.\n")
    
    with sync_playwright() as p:
        # Launch browser (visible, not headless)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Navigate to eBay Sell page
            print("Navigating to eBay Sell page...")
            page.goto("https://www.ebay.com/ws/eBayISAPI.dll?SellForm", wait_until="networkidle")
            time.sleep(2)
            
            # Wait for user to confirm they're ready
            print("\nBrowser is open at eBay.")
            print("Please ensure you're logged in, then press Enter to continue...")
            input()
            
            # Check if we're on the sell form
            print("Looking for title field...")
            
            # Try multiple selectors for the title field
            title_selectors = [
                'input[name="title"]',
                '[data-testid="sell-item-title-input"]',
                'input[placeholder*="title" i]',
                '.ebayui-sell-form__title'
            ]
            
            title_field = None
            for selector in title_selectors:
                if page.locator(selector).count > 0:
                    title_field = page.locator(selector).first
                    print(f"Found title field with selector: {selector}")
                    break
            
            if not title_field or title_field.count == 0:
                print("Could not automatically find title field.")
                print("\nPlease manually fill in the listing form:")
                print(f"  Title: MTG {CARD_INFO['name']} [{CARD_INFO['set_code']}]")
                print(f"  Price: ${CARD_INFO['price']:.2f}")
                print(f"  Condition: Near Mint")
                print("\nThen save as draft manually.")
                input("Press Enter when done...")
                browser.close()
                return
            
            # Fill in title
            full_title = f"MTG {CARD_INFO['name']} [{CARD_INFO['set_code']}]"
            print(f"Filling title: {full_title}")
            title_field.fill(full_title)
            time.sleep(1)
            
            # Find and fill price field
            price_selectors = [
                'input[name="price"]',
                '[data-testid*="price"]',
                'input[type="text"][placeholder*="$" i]'
            ]
            
            for selector in price_selectors:
                price_field = page.locator(selector)
                if price_field.count > 0:
                    print(f"Filling price: ${CARD_INFO['price']:.2f}")
                    price_field.fill(str(CARD_INFO['price']))
                    time.sleep(1)
                    break
            
            # Find and fill quantity field
            qty_selectors = [
                'input[name="quantity"]',
                '[data-testid*="quantity"]'
            ]
            
            for selector in qty_selectors:
                qty_field = page.locator(selector)
                if qty_field.count > 0:
                    print(f"Filling quantity: {CARD_INFO['quantity']}")
                    qty_field.fill(str(CARD_INFO['quantity']))
                    time.sleep(1)
                    break
            
            print("\nForm fields filled.")
            print("Please review the listing and click 'Save draft' manually.")
            print("Press Enter when you've saved the draft...")
            input()
            
            # Try to get the listing ID from URL
            current_url = page.url
            print(f"\nCurrent URL: {current_url}")
            
            if "listingId=" in current_url:
                import re
                match = re.search(r'listingId=(\d+)', current_url)
                if match:
                    listing_id = match.group(1)
                    print(f"Listing ID: {listing_id}")
            
        except KeyboardInterrupt:
            print("\nCancelled by user.")
        finally:
            browser.close()
    
    print("\nDone!")

if __name__ == "__main__":
    create_draft_listing()

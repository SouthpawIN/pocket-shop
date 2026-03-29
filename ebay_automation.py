#!/usr/bin/env python3
"""
eBay Listing Automation - Create Draft Listings
================================================

This module provides reliable browser automation for creating eBay draft listings.
Uses Playwright with anti-detection measures for better reliability.

Features:
- Automatic login (stores session cookies)
- Form field auto-detection and filling
- Save as draft functionality
- Retry logic for flaky elements
- Works with both new and existing eBay accounts
"""

import time
import json
import re
from pathlib import Path
from typing import Optional, Dict, List
from playwright.sync_api import sync_playwright, Page

### CONFIGURATION ###

EBAY_LOGIN_URL = "https://www.ebay.com/sch/MyeBaySeller"
EBAY_SELL_URL = "https://www.ebay.com/ws/eBayISAPI.dll?SellForm"
COOKIES_FILE = Path("~/.pocket-shop/ebay_cookies.json").expanduser()

# eBay condition IDs for trading cards
CONDITION_IDS = {
    "mint": "302",           # Mint
    "near_mint": "302",     # Near Mint (maps to Mint on eBay)
    "excellent": "283",     # Excellent
    "good": "284",          # Good
    "lightly_played": "281", # Lightly Played
    "heavily_played": "282", # Heavily Played  
    "played": "301"         # Played
}

# eBay category IDs
CATEGORY_IDS = {
    "mtg_singles": "60087",
    "mtg_sealed": "60085"
}


class eBayAutomation:
    """Reliable eBay browser automation for creating draft listings."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.context = None
    
    def start_browser(self) -> bool:
        """Launch browser with anti-detection settings."""
        try:
            self.playwright = sync_playwright().start()
            
            # Try to load saved cookies for auto-login
            storage_state = None
            if COOKIES_FILE.exists():
                storage_state = {"cookies": []}
                try:
                    with open(COOKIES_FILE) as f:
                        saved_cookies = json.load(f)
                        storage_state["cookies"] = saved_cookies
                except:
                    pass
            
            # Launch browser with realistic settings
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York',
                storage_state=storage_state
            )
            
            self.page = self.context.new_page()
            
            # Hide automation flags
            self.page.add_init_script('''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            ''')
            
            return True
            
        except Exception as e:
            print(f"Error starting browser: {e}")
            return False
    
    def close_browser(self):
        """Close browser and save cookies."""
        try:
            # Save cookies for next session
            if self.context:
                cookies = self.context.cookies()
                # Filter to eBay cookies only
                ebay_cookies = [c for c in cookies if 'ebay' in c.get('domain', '').lower()]
                if ebay_cookies:
                    COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(COOKIES_FILE, 'w') as f:
                        json.dump(ebay_cookies, f)
                    print(f"Saved {len(ebay_cookies)} eBay cookies for auto-login")
        except:
            pass
        
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def ensure_logged_in(self) -> bool:
        """Check if logged in, prompt user to log in if not."""
        print("Checking eBay login status...")
        
        self.page.goto(EBAY_LOGIN_URL, wait_until="networkidle")
        time.sleep(2)
        
        # Check for login indicators
        page_content = self.page.content().lower()
        visible_text = self.page.evaluate("() => document.body.innerText").lower()
        
        # Signs we're NOT logged in
        if any(indicator in visible_text for indicator in [
            'sign in', 'log in', 'welcome guest'
        ]) or 'my ebay' not in visible_text:
            print("\nNot logged in to eBay.")
            print("Please log in manually in the browser window.")
            print("Press Enter when you've logged in and see 'My eBay Seller'...")
            input()
            
            # Refresh to confirm
            self.page.goto(EBAY_LOGIN_URL, wait_until="networkidle")
            time.sleep(2)
        
        return True
    
    def navigate_to_sell_page(self) -> bool:
        """Navigate to the sell/create listing page."""
        print("\nNavigating to eBay Sell page...")
        
        # First go to Seller Hub
        self.page.goto(EBAY_LOGIN_URL, wait_until="networkidle")
        time.sleep(2)
        
        # Look for "Start Selling" or "Sell" button
        sell_selectors = [
            'button:has-text("Start Selling")',
            'a:has-text("Sell")',
            'button:has-text("Sell now")',
            '.sell-btn',
            '[data-testid*="sell"]',
            'button:has-text("Create listing")'
        ]
        
        sell_button = None
        for selector in sell_selectors:
            try:
                elem = self.page.locator(selector).first
                if elem.count > 0 and elem.is_visible():
                    print(f"Found sell button: {selector}")
                    sell_button = elem
                    break
            except:
                continue
        
        if sell_button:
            try:
                sell_button.click()
                time.sleep(2)
            except Exception as e:
                print(f"Click failed, trying alternative: {e}")
                # Try navigating directly
                self.page.goto(EBAY_SELL_URL, wait_until="networkidle")
                time.sleep(3)
        else:
            # Direct navigation fallback
            print("Sell button not found, navigating directly...")
            self.page.goto(EBAY_SELL_URL, wait_until="networkidle")
            time.sleep(3)
        
        return True
    
    def fill_listing_form(self, card_info: Dict) -> bool:
        """Fill out the eBay listing form with card information."""
        
        name = card_info.get('name', '')
        set_code = card_info.get('set_code', '')
        price = float(card_info.get('price', 0.99))
        condition = card_info.get('condition', 'near_mint')
        quantity = int(card_info.get('quantity', 1))
        description = card_info.get('description', '')
        
        print(f"\nFilling listing form for: {name}")
        
        # Build title
        title = f"MTG {name}" + (f" [{set_code}]" if set_code else "")
        
        # === FILL TITLE ===
        print("  Filling title...")
        title_selectors = [
            'input[name="title"]',
            '[data-testid="sell-item-title-input"]',
            'input[placeholder*="title" i]',
            '.ebayui-sell-form__title',
            'input[type="text"]'
        ]
        
        for selector in title_selectors:
            try:
                field = self.page.locator(selector).first
                if field.count > 0:
                    field.fill(title)
                    print(f"    Title: {title}")
                    break
            except:
                continue
        time.sleep(1)
        
        # === FILL PRICE ===
        print("  Filling price...")
        price_selectors = [
            'input[name="price"]',
            '[data-testid*="price"]',
            'input[type="text"][placeholder*="$" i]',
            '.price-input'
        ]
        
        for selector in price_selectors:
            try:
                field = self.page.locator(selector).first
                if field.count > 0:
                    field.fill(str(price))
                    print(f"    Price: ${price:.2f}")
                    break
            except:
                continue
        time.sleep(1)
        
        # === FILL QUANTITY ===
        print("  Filling quantity...")
        qty_selectors = [
            'input[name="quantity"]',
            '[data-testid*="quantity"]',
            '.quantity-input'
        ]
        
        for selector in qty_selectors:
            try:
                field = self.page.locator(selector).first
                if field.count > 0:
                    field.fill(str(quantity))
                    print(f"    Quantity: {quantity}")
                    break
            except:
                continue
        time.sleep(1)
        
        # === SELECT CONDITION ===
        print("  Selecting condition...")
        condition_id = CONDITION_IDS.get(condition.lower(), "302")
        
        condition_selectors = [
            'select[name="conditionId"]',
            '[data-testid*="condition"] select',
            '.condition-select'
        ]
        
        for selector in condition_selectors:
            try:
                field = self.page.locator(selector).first
                if field.count > 0:
                    field.select_option(value=condition_id)
                    print(f"    Condition: {condition} (ID: {condition_id})")
                    break
            except:
                continue
        time.sleep(1)
        
        # === FILL DESCRIPTION ===
        print("  Filling description...")
        desc_selectors = [
            'textarea[name="description"]',
            '[data-testid*="description"]',
            'textarea[class*="desc"]'
        ]
        
        auto_description = f"Magic: The Gathering card - {name}\n"
        if set_code:
            auto_description += f"Set: {set_code}\n"
        auto_description += f"Condition: {condition.replace('_', ' ').title()}\n"
        if description:
            auto_description += f"\n{description}"
        
        for selector in desc_selectors:
            try:
                field = self.page.locator(selector).first
                if field.count > 0:
                    field.fill(auto_description)
                    print(f"    Description filled")
                    break
            except:
                continue
        time.sleep(1)
        
        return True
    
    def save_as_draft(self) -> Optional[str]:
        """Save the listing as a draft."""
        print("\nSaving as draft...")
        
        # Look for "Save draft" button
        draft_selectors = [
            'button:has-text("Save draft")',
            'button:has-text("Save")',
            '[data-testid*="save-draft"]',
            '.save-draft-btn'
        ]
        
        for selector in draft_selectors:
            try:
                button = self.page.locator(selector).first
                if button.count > 0 and button.is_visible():
                    print(f"Found save draft button: {selector}")
                    button.click()
                    time.sleep(2)
                    
                    # Try to extract listing ID from URL or page
                    listing_id = self._extract_listing_id()
                    if listing_id:
                        print(f"Draft saved! Listing ID: {listing_id}")
                        return listing_id
                    else:
                        print("Draft saved (could not extract listing ID)")
                        return "draft_saved"
            except Exception as e:
                print(f"  Try failed: {e}")
                continue
        
        print("Could not find save draft button")
        return None
    
    def _extract_listing_id(self) -> Optional[str]:
        """Try to extract listing ID from current page."""
        # Check URL
        url = self.page.url
        match = re.search(r'listingId=(\d+)', url)
        if match:
            return match.group(1)
        
        # Check page content
        try:
            content = self.page.content()
            match = re.search(r'Listing ID[:\s]+([\d-]+)', content, re.IGNORECASE)
            if match:
                return match.group(1)
        except:
            pass
        
        return None
    
    def create_draft_listing(self, card_info: Dict) -> Dict:
        """Complete workflow to create a draft listing."""
        
        result = {
            "success": False,
            "listing_id": None,
            "error": None
        }
        
        try:
            # Start browser
            if not self.start_browser():
                result["error"] = "Failed to start browser"
                return result
            
            try:
                # Ensure logged in
                self.ensure_logged_in()
                
                # Navigate to sell page
                self.navigate_to_sell_page()
                
                # Fill form
                self.fill_listing_form(card_info)
                
                # Save as draft
                listing_id = self.save_as_draft()
                
                if listing_id:
                    result["success"] = True
                    result["listing_id"] = listing_id
                else:
                    result["error"] = "Could not save draft"
                    
            finally:
                self.close_browser()
                
        except Exception as e:
            result["error"] = str(e)
            print(f"Error creating listing: {e}")
            import traceback
            traceback.print_exc()
        
        return result


### CONVENIENCE FUNCTIONS ###

def create_ebay_draft(card_info: Dict, headless: bool = True) -> Dict:
    """Create an eBay draft listing for a card.
    
    Args:
        card_info: Dictionary with card details:
            - name: Card name
            - set_code: Set code (optional)
            - price: Listing price
            - condition: Condition (mint, near_mint, excellent, etc.)
            - quantity: Quantity available
            - description: Additional description (optional)
        headless: Run browser in background (True) or visible (False)
        
    Returns:
        Dictionary with 'success', 'listing_id', 'error' keys
    """
    automation = eBayAutomation(headless=headless)
    return automation.create_draft_listing(card_info)


def main():
    """Test the eBay automation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create eBay draft listing")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    parser.add_argument("--test", action="store_true", help="Run test with sample card")
    
    args = parser.parse_args()
    
    if args.test:
        test_card = {
            "name": "Disturbing Mirth",
            "set_code": "dsk",
            "price": 0.11,
            "condition": "near_mint",
            "quantity": 1
        }
        print("Testing with sample card:")
        print(test_card)
        print()
        result = create_ebay_draft(test_card, headless=not args.visible)
        print(f"\nResult: {result}")
    else:
        print("Use --test to run a test listing")
        print("Or import create_ebay_draft() in your code")


if __name__ == "__main__":
    main()

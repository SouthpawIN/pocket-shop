#!/usr/bin/env python3
"""eBay Listings Module - Create and manage eBay listings for Pocket-Shop"""

import time
import re
from typing import Optional, Dict, List, Any
from pathlib import Path
import json

# Condition mappings for eBay
EBAY_CONDITIONS = {
    "near_mint": "302",
    "excellent": "283",
    "good": "284",
    "light_play": "281",
    "heavy_play": "282",
    "played": "301"
}

# eBay category IDs for MTG cards
EBAY_CATEGORIES = {
    "mtg_singles": "60087",  # Trading Cards > Magic: The Gathering > Singles
    "mtg_sealed": "60085",  # Trading Cards > Magic: The Gathering > Sealed Products
}

class eBayListingManager:
    """Manage eBay listings via browser automation or API"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the eBay listing manager.
        
        Args:
            config: Optional configuration dictionary with:
                   - use_api: bool (default False) - Use API instead of browser
                   - api_key: str - eBay API key (if using API)
                   - api_secret: str - eBay API secret (if using API)
                   - refresh_token: str - OAuth refresh token (if using API)
                   - marketplace: str - eBay marketplace (default "EBAY_US")
        """
        self.config = config or {}
        self.use_api = self.config.get("use_api", False)
        self.marketplace = self.config.get("marketplace", "EBAY_US")
        
        # Browser automation setup
        self._playwright_installed = False
        try:
            from playwright.sync_api import sync_playwright
            self._playwright_installed = True
        except ImportError:
            pass
        
        self.browser = None
        self.page = None
    
    def _start_browser(self) -> bool:
        """Launch browser for automation"""
        if not self._playwright_installed:
            print("Warning: Playwright not installed. Run: pip install playwright")
            return False
        
        try:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=False)
            self.page = self.browser.new_page()
            return True
        except Exception as e:
            print(f"Error starting browser: {e}")
            return False
    
    def _stop_browser(self):
        """Close browser session"""
        if self.browser:
            self.browser.close()
            self.browser = None
        if hasattr(self, 'playwright'):
            self.playwright.stop()
    
    def create_listing(self, card_info: Dict) -> Optional[str]:
        """
        Create a single eBay listing for a card.
        
        Args:
            card_info: Dictionary containing:
                      - name: str - Card name
                      - set_code: str (optional) - Set code
                      - condition: str - Card condition (near_mint, excellent, etc.)
                      - price: float - Listing price
                      - quantity: int (optional, default 1) - Quantity available
                      - description: str (optional) - Custom description
                      - image_path: str (optional) - Path to card image
        
        Returns:
            Optional[str]: Listing ID if successful, None otherwise
        """
        # Extract card info
        name = card_info.get("name", "")
        set_code = card_info.get("set_code", "")
        condition = card_info.get("condition", "near_mint")
        price = float(card_info.get("price", 0.01))
        quantity = int(card_info.get("quantity", 1))
        description = card_info.get("description", "")
        image_path = card_info.get("image_path", "")
        
        print(f"Creating listing for: {name} (${price:.2f})")
        
        if self.use_api:
            return self._create_listing_api(card_info)
        else:
            return self._create_listing_browser(name, set_code, condition, price, quantity, description, image_path)
    
    def _create_listing_browser(self, name: str, set_code: str, condition: str, 
                                price: float, quantity: int, description: str,
                                image_path: Optional[str]) -> Optional[str]:
        """Create listing via browser automation"""
        
        if not self._start_browser():
            return None
        
        try:
            # Navigate to eBay selling page
            print("Navigating to eBay Seller Hub...")
            self.page.goto("https://www.ebay.com/sch/MyeBaySeller", wait_until="networkidle")
            time.sleep(2)
            
            # Click "Start Selling" or "Sell" button
            sell_button = None
            for selector in ["button:has-text('Start Selling')", "a:has-text('Sell')", 
                            ".sell-btn", "button:has-text('Sell now')"]:
                if self.page.locator(selector).count > 0:
                    sell_button = self.page.locator(selector).first
                    break
            
            if not sell_button or sell_button.count == 0:
                print("Could not find 'Sell' button. Please ensure you're logged in.")
                return None
            
            sell_button.click()
            time.sleep(2)
            
            # Wait for selling form to load
            self.page.wait_for_selector("input[name='title']", timeout=10000)
            time.sleep(1)
            
            # Fill in title
            title_field = self.page.locator("input[name='title']")
            if title_field.count > 0:
                full_title = f"MTG {name}" + (f" [{set_code}]" if set_code else "")
                title_field.fill(full_title)
                print(f"Title filled: {full_title}")
            
            # Fill in price
            price_field = self.page.locator("input[name='price']")
            if price_field.count > 0:
                price_field.fill(str(price))
                print(f"Price filled: ${price:.2f}")
            
            # Fill in quantity
            qty_field = self.page.locator("input[name='quantity']")
            if qty_field.count > 0:
                qty_field.fill(str(quantity))
                print(f"Quantity filled: {quantity}")
            
            # Select condition from dropdown
            condition_id = EBAY_CONDITIONS.get(condition, "302")
            condition_select = self.page.locator("select[name='conditionId']")
            if condition_select.count > 0:
                condition_select.select_option(value=condition_id)
                print(f"Condition selected: {condition}")
            
            # Fill in description
            desc_field = self.page.locator("textarea[name='description']")
            if desc_field.count > 0:
                auto_desc = f"Magic: The Gathering card - {name}"
                if set_code:
                    auto_desc += f" from set {set_code}"
                auto_desc += f". Condition: {condition.replace('_', ' ').title()}"
                auto_desc += f"\n{description}" if description else ""
                desc_field.fill(auto_desc)
                print("Description filled")
            
            # Upload image if provided
            if image_path and Path(image_path).exists():
                image_upload = self.page.locator("input[type='file']")
                if image_upload.count > 0:
                    image_upload.set_input_files(image_path)
                    print(f"Image uploaded: {image_path}")
            
            # Save as draft
            save_draft_btn = None
            for selector in ["button:has-text('Save draft')", "button:has-text('Save')",
                            ".save-draft-btn"]:
                if self.page.locator(selector).count > 0:
                    save_draft_btn = self.page.locator(selector).first
                    break
            
            if save_draft_btn and save_draft_btn.count > 0:
                save_draft_btn.click()
                print("Saved as draft")
                time.sleep(2)
                
                # Try to extract listing ID from URL or page
                listing_id = self._extract_listing_id()
                return listing_id
            else:
                print("Could not find 'Save draft' button")
                return None
                
        except Exception as e:
            print(f"Error creating listing via browser: {e}")
            return None
        finally:
            self._stop_browser()
    
    def _extract_listing_id(self) -> Optional[str]:
        """Try to extract listing ID from current page"""
        # Check URL for listing ID
        url = self.page.url
        match = re.search(r'listingId=(\d+)', url)
        if match:
            return match.group(1)
        
        # Search page content for listing ID
        try:
            text = self.page.content()
            match = re.search(r'Listing ID[:\s]+([\d-]+)', text, re.IGNORECASE)
            if match:
                return match.group(1)
        except:
            pass
        
        return None
    
    def _create_listing_api(self, card_info: Dict) -> Optional[str]:
        """Create listing via eBay API (requires authentication)"""
        try:
            import requests
            
            # OAuth endpoint
            oauth_url = "https://api.ebay.com/identity/v1/oauth/token"
            
            # Get access token
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.config.get("refresh_token"),
                "redirect_uri": self.config.get("redirect_uri", "http://localhost")
            }
            
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(oauth_url, data=data, headers=headers)
            
            if response.status_code != 200:
                print(f"OAuth error: {response.status_code} - {response.text}")
                return None
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            # Build listing data
            name = card_info.get("name", "")
            price = float(card_info.get("price", 0.01))
            condition = card_info.get("condition", "near_mint")
            quantity = int(card_info.get("quantity", 1))
            
            listing_data = {
                "title": f"MTG {name}",
                "type": "FIXED_PRICE",
                "startTime": "SELLER",
                "sellerUserId": "",
                "categoryId": EBAY_CATEGORIES["mtg_singles"],
                "conditionId": EBAY_CONDITIONS.get(condition, "302"),
                "price": {
                    "amount": f"{price:.2f}",
                    "currency": "USD"
                },
                "quantity": {
                    "quantityAvailable": quantity,
                    "quantitySold": 0
                },
                "shippingInfo": {
                    "shippingServiceCost": [{
                        "shippingServicePriority": 1,
                        "shippingType": "EXPEDITED",
                        "shippingServiceCost": {
                            "amount": "3.99",
                            "currency": "USD"
                        }
                    }],
                    "handlingTime": 1
                },
                "itemSpecifics": {
                    "CardTitle": [name],
                    "CardType": ["Single Card"]
                }
            }
            
            # Create listing
            api_headers = {
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
                "Content-Type": "application/json",
                "Ebay-Auth-Token": access_token
            }
            
            response = requests.post(
                "https://api.ebay.com/sell/listings/v1/listing",
                json=listing_data,
                headers=api_headers
            )
            
            if response.status_code == 201:
                result = response.json()
                listing_id = result.get("ebayListingId")
                print(f"Draft created via API: {listing_id}")
                return listing_id
            else:
                print(f"API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating listing via API: {e}")
            return None
    
    def bulk_create_listings(self, cards: List[Dict]) -> List[Dict]:
        """
        Create multiple eBay listings.
        
        Args:
            cards: List of card_info dictionaries (same format as create_listing)
        
        Returns:
            List[Dict]: Results with 'card_name', 'listing_id', 'success', 'error' keys
        """
        results = []
        
        for i, card in enumerate(cards):
            print(f"\n[{i+1}/{len(cards)}] Processing: {card.get('name', 'Unknown')}")
            
            try:
                listing_id = self.create_listing(card)
                results.append({
                    "card_name": card.get("name", "Unknown"),
                    "listing_id": listing_id,
                    "success": listing_id is not None,
                    "error": None
                })
            except Exception as e:
                results.append({
                    "card_name": card.get("name", "Unknown"),
                    "listing_id": None,
                    "success": False,
                    "error": str(e)
                })
            
            # Rate limiting delay
            if i < len(cards) - 1:
                time.sleep(2)
        
        # Print summary
        success_count = sum(1 for r in results if r["success"])
        print(f"\n=== Bulk Create Summary ===")
        print(f"Total: {len(cards)} cards")
        print(f"Success: {success_count}")
        print(f"Failed: {len(cards) - success_count}")
        
        return results
    
    def get_listing_status(self, listing_id: str) -> Optional[Dict]:
        """
        Get the status of an eBay listing.
        
        Args:
            listing_id: The eBay listing ID
        
        Returns:
            Optional[Dict]: Listing status information or None if not found
        """
        if self.use_api:
            return self._get_listing_status_api(listing_id)
        else:
            return self._get_listing_status_browser(listing_id)
    
    def _get_listing_status_browser(self, listing_id: str) -> Optional[Dict]:
        """Get listing status via browser automation"""
        if not self._playwright_installed:
            print("Warning: Playwright not installed")
            return None
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to listing
                url = f"https://www.ebay.com/itm/{listing_id}"
                page.goto(url, wait_until="networkidle")
                time.sleep(2)
                
                # Check if listing exists
                if "item not found" in page.content().lower():
                    return {"status": "not_found", "active": False}
                
                # Extract title and status
                title = page.locator("h1#view-item-title").inner_text()
                
                # Check if active (has Buy It Now or Add to Cart)
                is_active = (
                    page.locator("button:has-text('Buy It Now')").count > 0 or
                    page.locator("button:has-text('Add to cart')").count > 0
                )
                
                # Try to get price
                try:
                    price_elem = page.locator(".x-price-value")
                    if price_elem.count > 0:
                        price_text = price_elem.inner_text()
                        price_match = re.search(r'\$([\d,]+\.?\d*)', price_text)
                        current_price = float(price_match.group(1).replace(',', '')) if price_match else None
                    else:
                        current_price = None
                except:
                    current_price = None
                
                result = {
                    "listing_id": listing_id,
                    "title": title,
                    "active": is_active,
                    "current_price": current_price,
                    "status": "active" if is_active else "ended"
                }
                
                return result
                
        except Exception as e:
            print(f"Error getting listing status: {e}")
            return None
        finally:
            if 'browser' in locals():
                browser.close()
    
    def _get_listing_status_api(self, listing_id: str) -> Optional[Dict]:
        """Get listing status via eBay API"""
        try:
            import requests
            
            # Get access token
            oauth_url = "https://api.ebay.com/identity/v1/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.config.get("refresh_token"),
                "redirect_uri": self.config.get("redirect_uri", "http://localhost")
            }
            
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(oauth_url, data=data, headers=headers)
            
            if response.status_code != 200:
                return None
            
            access_token = response.json().get("access_token")
            
            # Get listing details
            api_headers = {
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
                "Ebay-Auth-Token": access_token
            }
            
            response = requests.get(
                f"https://api.ebay.com/sell/listings/v1/listing/{listing_id}",
                headers=api_headers
            )
            
            if response.status_code == 200:
                listing_data = response.json()
                return {
                    "listing_id": listing_id,
                    "title": listing_data.get("title", ""),
                    "active": listing_data.get("state") == "ACTIVE",
                    "status": listing_data.get("state", "unknown"),
                    "quantity_available": listing_data.get("quantity", {}).get("quantityAvailable", 0)
                }
            return None
            
        except Exception as e:
            print(f"Error getting listing status via API: {e}")
            return None
    
    def delete(self):
        """Cleanup method"""
        self._stop_browser()


# Convenience functions for direct usage

def create_listing(card_info: Dict, config: Optional[Dict] = None) -> Optional[str]:
    """Create a single eBay listing"""
    manager = eBayListingManager(config)
    try:
        return manager.create_listing(card_info)
    finally:
        manager.delete()


def bulk_create_listings(cards: List[Dict], config: Optional[Dict] = None) -> List[Dict]:
    """Create multiple eBay listings"""
    manager = eBayListingManager(config)
    try:
        return manager.bulk_create_listings(cards)
    finally:
        manager.delete()


def get_listing_status(listing_id: str, config: Optional[Dict] = None) -> Optional[Dict]:
    """Get the status of an eBay listing"""
    manager = eBayListingManager(config)
    try:
        return manager.get_listing_status(listing_id)
    finally:
        manager.delete()


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Test browser automation mode
    print("Testing eBay Listing Manager (Browser Mode)\n")
    
    # Single listing test
    card_info = {
        "name": "Black Lotus",
        "set_code": "LEA",
        "condition": "near_mint",
        "price": 50.00,
        "quantity": 1,
        "description": "Classic MTG card in excellent condition"
    }
    
    print(f"Would create listing for: {card_info['name']}")
    print("Note: Actual browser automation requires Playwright and Chrome installed")
    print("Run: pip install playwright && playwright install chromium")
    
    # Bulk test
    cards = [
        {"name": "Lightning Bolt", "set_code": "M15", "condition": "near_mint", "price": 2.50},
        {"name": "Forest", "set_code": "KTK", "condition": "excellent", "price": 0.25},
        {"name": "Mountain", "set_code": "KTK", "condition": "excellent", "price": 0.25}
    ]
    
    print(f"\nWould bulk create {len(cards)} listings")

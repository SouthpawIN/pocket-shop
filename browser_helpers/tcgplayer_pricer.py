#!/usr/bin/env python3
"""TCGPlayer Price Lookup - Browser Automation"""

import time
import re
from typing import Optional, Dict


class TCGPlayerPricer:
    """Get pricing information from TCGPlayer via browser automation"""
    
    def __init__(self):
        self.base_url = "https://tcgplayer.com"
        self._playwright_installed = False
        try:
            from playwright.sync_api import sync_playwright
            self._playwright_installed = True
        except ImportError:
            pass
    
    def get_price(self, card_name: str, condition: str = "near_mint") -> Optional[Dict]:
        """Get pricing information for a card from TCGPlayer"""
        
        if not self._playwright_installed:
            print("Warning: Playwright not installed. Run: pip install playwright")
            return None
        
        from playwright.sync_api import sync_playwright
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to product search
                search_url = f"{self.base_url}/products/search?q={card_name.replace(' ', '+')}"
                print(f"Searching for: {card_name}")
                page.goto(search_url, wait_until="networkidle")
                time.sleep(2)
                
                # Find first card result
                first_result = page.locator(".ProductCard").first
                
                try:
                    # Extract card name and link
                    card_link = first_result.locator("a").first.get_attribute("href")
                    page.goto(self.base_url + card_link, wait_until="networkidle")
                    time.sleep(1)
                    
                    # Extract prices from product page
                    prices = self._extract_prices(page)
                    return prices
                    
                except Exception as e:
                    print(f"Error finding card: {e}")
                    return None
        except Exception as e:
            print(f"Error pricing card: {e}")
            return None
        finally:
            if 'browser' in locals():
                browser.close()
    
    def _extract_prices(self, page) -> Dict:
        """Extract price information from product page"""
        prices = {
            "market": 0.0,
            "low": 0.0,
            "direct": 0.0,
            "1_of_1": 0.0,
            "holofoil": 0.0,
            "etched": 0.0
        }
        
        # Try to find market price
        selectors = [
            (".MarketPrice", "market"),
            (".OneOfOnePrice", "1_of_1"),
            (".LowPrice", "low"),
            (".DirectShipPrice", "direct")
        ]
        
        for selector, key in selectors:
            elem = page.locator(selector)
            if elem.count() > 0:
                text = elem.first.inner_text()
                match = re.search(r'\$([\d,]+\.?\d*)', text)
                if match:
                    prices[key] = float(match.group(1).replace(',', ''))
        
        return prices
    
    def get_price_range(self, card_name: str) -> Optional[Dict]:
        """Get price range (low to high) for a card"""
        price_info = self.get_price(card_name)
        if not price_info:
            return None
        
        return {
            "low": price_info.get("low", 0),
            "high": price_info.get("market", 0),
            "direct": price_info.get("direct", 0)
        }

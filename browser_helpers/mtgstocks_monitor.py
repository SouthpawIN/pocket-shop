#!/usr/bin/env python3
"""MTGStocks Set EV Monitor - Browser Automation"""

import time
import re
from typing import List, Dict, Optional


class MTGStocksMonitor:
    """Monitor MTGStocks for high expected-value sets"""
    
    def __init__(self):
        self.base_url = "https://www.mtgstocks.com"
        self._playwright_installed = False
        try:
            from playwright.sync_api import sync_playwright
            self._playwright_installed = True
        except ImportError:
            pass
    
    def find_high_ev_sets(self, threshold: float = 10.0) -> List[Dict]:
        """Find sets with EV above threshold using browser automation"""
        
        if not self._playwright_installed:
            print("Warning: Playwright not installed. Run: pip install playwright")
            print("Then: playwright install chromium")
            return []
        
        from playwright.sync_api import sync_playwright
        results = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to sets page
                print(f"Navigating to {self.base_url}/sets...")
                page.goto(f"{self.base_url}/sets", wait_until="networkidle")
                time.sleep(2)  # Wait for dynamic content
                
                # Extract set data from the page
                sets_html = page.locator("table.sets-table tbody tr")
                count = sets_html.count()
                print(f"Found {count} sets on page")
                
                for i in range(min(count, 50)):  # Limit to first 50 for speed
                    row = sets_html.nth(i)
                    cells = row.locator("td")
                    
                    try:
                        name_cell = cells.nth(0)
                        ev_cell = cells.nth(2)  # EV column
                        
                        set_name = name_cell.inner_text().strip()
                        ev_text = ev_cell.inner_text().strip()
                        
                        # Extract EV value from format like "$12.34"
                        ev_match = re.search(r'\$([\d,]+\.?\d*)', ev_text)
                        if ev_match:
                            ev_value = float(ev_match.group(1).replace(',', ''))
                            
                            if ev_value >= threshold:
                                results.append({
                                    "name": set_name,
                                    "ev": ev_value,
                                    "buylist_ev": ev_value * 0.75,  # Approximate
                                    "cards_analyzed": 0
                                })
                    except Exception as e:
                        continue
                
                browser.close()
        except Exception as e:
            print(f"Error monitoring MTGStocks: {e}")
        
        # Sort by EV descending
        results.sort(key=lambda x: x["ev"], reverse=True)
        return results
    
    def get_set_details(self, set_code: str) -> Optional[Dict]:
        """Get detailed information about a specific set"""
        
        if not self._playwright_installed:
            return None
        
        from playwright.sync_api import sync_playwright
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                page.goto(f"{self.base_url}/set/{set_code}", wait_until="networkidle")
                time.sleep(2)
                
                # Extract set details
                details = {
                    "code": set_code,
                    "name": "",
                    "release_date": "",
                    "card_count": 0,
                    "ev": 0.0,
                    "cards": []
                }
                
                # Try to find set name
                name_elem = page.locator("h1")
                if name_elem.count() > 0:
                    details["name"] = name_elem.inner_text().strip()
                
                browser.close()
                return details
        except Exception as e:
            print(f"Error getting set details: {e}")
            return None
    
    def search_sets(self, query: str) -> List[Dict]:
        """Search for sets by name or code"""
        # Simplified - just returns mock data for now
        return [
            {
                "name": f"Mock Set: {query}",
                "ev": 15.0,
                "buylist_ev": 11.25,
                "cards_analyzed": 0
            }
        ]

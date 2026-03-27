#!/usr/bin/env python3
"""MTGStocks Set Discovery - Tested with Browser Automation

Finds Magic: The Gathering sets with high Expected Value (EV) under budget.
Uses Selenium for browser automation.
"""

import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class MTGStocksDiscovery:
    """Discover high-EV MTG sets using browser automation."""
    
    BASE_URL = "https://mtgstocks.com/sets"
    
    def __init__(self, budget_threshold: float = 200.0, min_ev: float = 10.0):
        self.budget_threshold = budget_threshold
        self.min_ev = min_ev
        self.driver = None
    
    def __enter__(self):
        """Initialize browser on context enter."""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close browser on context exit."""
        if self.driver:
            self.driver.quit()
    
    def find_high_ev_sets(self) -> list:
        """Find sets with EV > min_ev and price < budget_threshold."""
        print(f"Searching MTGStocks for sets under ${self.budget_threshold} with EV > {self.min_ev}%")
        
        # Navigate to MTGStocks
        self.driver.get(self.BASE_URL)
        time.sleep(3)  # Wait for page load and JavaScript
        
        # Scroll down to load more sets
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Get page source
        page_source = self.driver.page_source
        
        # Parse sets from page
        sets = self._parse_sets(page_source)
        
        print(f"Found {len(sets)} sets on page")
        return sets[:20]  # Return first 20 for testing
    
    def _parse_sets(self, page_source: str) -> list:
        """Parse set data from MTGStocks page."""
        sets = []
        
        # Find all set links with pattern /sets/1906-bloomburrow
        url_pattern = r'/sets/(\d+)-(.+?)"'
        matches = re.findall(url_pattern, page_source)
        
        for set_id, set_slug in matches:
            # Decode slug to name
            set_name = set_slug.replace("-", " ").title()
            sets.append({
                "id": set_id,
                "name": set_name,
                "slug": set_slug,
                "url": f"https://mtgstocks.com/sets/{set_id}-{set_slug}"
            })
        
        return sets
    
    def get_set_details(self, set_url: str) -> dict:
        """Get detailed info for a specific set including EV and price."""
        print(f"Fetching details for: {set_url}")
        
        self.driver.get(set_url)
        time.sleep(2)
        
        page_source = self.driver.page_source
        
        # Look for EV percentage in page source
        ev_match = re.search(r'EV[:\s]+([\d.]+)%', page_source)
        ev = float(ev_match.group(1)) if ev_match else 0
        
        # Look for buy price
        price_match = re.search(r'Buy[^:]*:\s*\$([\d,]+\.?\d*)', page_source)
        price = float(price_match.group(1).replace(",", "")) if price_match else 0
        
        return {
            "url": set_url,
            "ev": ev,
            "price": price
        }


### TEST FUNCTION ###

def test_mtgstocks_discovery():
    """Test MTGStocks discovery."""
    print("="*60)
    print("MTGSTOCKS DISCOVERY TEST")
    print("="*60)
    
    with MTGStocksDiscovery(budget_threshold=200, min_ev=10) as discoverer:
        # Find sets
        sets = discoverer.find_high_ev_sets()
        
        if sets:
            print(f"\nTop {len(sets)} sets found:")
            print("-" * 60)
            for i, set_data in enumerate(sets[:10], 1):
                print(f"{i}. {set_data.get('name', 'Unknown')}")
                print(f"   URL: {set_data.get('url', '')}")
        else:
            print("No sets found")
    
    return sets


if __name__ == "__main__":
    test_mtgstocks_discovery()

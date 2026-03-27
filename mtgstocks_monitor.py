#!/usr/bin/env python3
"""MTGStocks Set Discovery Module

Monitors MTGStocks.com for Magic: The Gathering sets with high Expected Value (EV).
Uses browser automation to scrape set data and find profitable opportunities.
"""

import sys
import time
import re
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

class MTGStocksMonitor:
    BASE_URL = "https://mtgstocks.com/sets"
    
    def __init__(self, ev_threshold=10.0):
        """Initialize MTGStocks monitor.
        
        Args:
            ev_threshold: Minimum EV percentage to consider (default 10%)
        """
        self.ev_threshold = ev_threshold
    
    def find_high_ev_sets(self, min_ev=None):
        """Find sets with high Expected Value using browser automation.
        
        Uses Hermes browser tools to navigate MTGStocks and extract set data.
        
        Args:
            min_ev: Override minimum EV threshold
            
        Returns:
            List of dicts with set info: name, code, ev, buy_price
        """
        from hermes_tools import browser_navigate, browser_snapshot, browser_scroll
        
        threshold = min_ev or self.ev_threshold
        print(f"Searching MTGStocks for sets with EV > {threshold}%...")
        
        # Navigate to MTGStocks sets page
        browser_navigate(url=self.BASE_URL)
        time.sleep(3)  # Wait for page load
        
        # Scroll to load more sets
        browser_scroll(direction="down")
        time.sleep(2)
        browser_scroll(direction="down")
        time.sleep(2)
        
        # Get full page snapshot
        snapshot = browser_snapshot(full=True)
        
        # Parse set data from page text
        sets = self._parse_sets_from_snapshot(snapshot, threshold)
        
        print(f"Found {len(sets)} sets with EV > {threshold}%")
        
        return sets
    
    def _parse_sets_from_snapshot(self, snapshot_text, min_ev):
        """Parse set data from browser snapshot."""
        sets = []
        
        # Look for patterns like "Set Name
EV: 15.2%
Buy Price: $45.00"
        # This is a simplified parser - would need refinement based on actual page structure
        
        # Alternative: Use structured data extraction
        lines = snapshot_text.get("text", "").split("\n")
        
        current_set = None
        for line in lines:
            line = line.strip()
            
            # Detect set name (usually followed by EV or price info)
            if re.match(r"^.{3,50}$", line) and not line.startswith(("$", "EV", "%", "Buy", "Sell")):
                if current_set and current_set.get("ev", 0) > min_ev:
                    sets.append(current_set)
                current_set = {"name": line}
            
            # Extract EV percentage
            elif match := re.search(r"EV[:\s]+([\d.]+)\s*%", line):
                if current_set:
                    current_set["ev"] = float(match.group(1))
            
            # Extract buy price
            elif match := re.search(r"Buy[^:]*:\s*\$([\d,]+\.\d+)", line):
                if current_set:
                    current_set["buy_price"] = float(match.group(1).replace(",", ""))
            
            # Extract set code (usually in parentheses or brackets)
            elif match := re.search(r"([A-Z]{2,4})\s*EV", line):
                if current_set:
                    current_set["code"] = match.group(1)
        
        # Add last set if valid
        if current_set and current_set.get("ev", 0) > min_ev:
            sets.append(current_set)
        
        # Sort by EV descending
        sets.sort(key=lambda x: x.get("ev", 0), reverse=True)
        
        return sets[:10]  # Return top 10
    
    def get_set_details(self, set_code):
        """Get detailed information for a specific set."""
        from hermes_tools import browser_navigate, browser_snapshot
        
        url = f"https://mtgstocks.com/sets/{set_code.lower()}"
        print(f"Fetching details for {set_code}...")
        
        browser_navigate(url=url)
        time.sleep(2)
        
        snapshot = browser_snapshot(full=True)
        
        return {
            "set_code": set_code,
            "snapshot": snapshot
        }

### TEST FUNCTION ###

def test_mtgstocks_monitor():
    """Test the MTGStocks monitor."""
    monitor = MTGStocksMonitor(ev_threshold=10.0)
    
    print("=== MTGStocks Monitor Test ===")
    print(f"EV Threshold: {monitor.ev_threshold}%")
    
    # Find high EV sets
    sets = monitor.find_high_ev_sets()
    
    print(f"\nTop High-EV Sets Found:")
    print("-" * 60)
    
    for i, set_data in enumerate(sets[:5], 1):
        print(f"{i}. {set_data.get('name', 'Unknown')}")
        print(f"   EV: {set_data.get('ev', 0):.1f}%")
        print(f"   Buy Price: ${set_data.get('buy_price', 0):.2f}")
        print()

if __name__ == "__main__":
    test_mtgstocks_monitor()

#!/usr/bin/env python3
"""
TCGPlayer Price Lookup Script for Pocket-Shop
Uses browser automation to search TCGPlayer and extract card prices.
"""

import re
import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import json


def get_chrome_driver():
    """Initialize Chrome WebDriver with anti-detection settings."""
    chrome_options = Options()
    
    # Anti-detection settings
    chrome_options.add_argument('--headless=new')  # New headless mode
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Performance settings
    prefs = {
        "perf.enable_netlog": False,
        "download.default_directory": "/tmp"
    }
    chrome_options.experimental_options['prefs'] = {'download': prefs}
    
    # Disable automation detection
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute CDP commands to hide automation
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        '''
    })
    
    return driver


def browser_navigate(driver, url: str) -> None:
    """Navigate to a URL using the browser."""
    driver.get(url)
    print(f"Navigated to: {url}")


def browser_snapshot(driver) -> str:
    """Take a snapshot of the current page content."""
    return driver.page_source


def search_tcgplayer(card_name: str, use_manual_search: bool = True) -> dict:
    """
    Search TCGPlayer for a card and extract pricing information.
    
    Args:
        card_name: Name of the card to search for
        use_manual_search: If True, manually type into search box (more reliable)
        
    Returns:
        Dictionary containing search results and prices
    """
    driver = get_chrome_driver()
    
    try:
        base_url = "https://www.tcgplayer.com"
        
        print(f"\n{'='*50}")
        print(f"Searching TCGPlayer for: '{card_name}'")
        print(f"{'='*50}\n")
        
        if use_manual_search:
            # Navigate to homepage and manually search
            browser_navigate(driver, base_url)
            time.sleep(2)
            
            # Try to find search input - multiple possible selectors
            search_selectors = [
                'input[name="q"]',
                'input[role="search"]',
                '.search-input',
                'input[type="text"]',
                '[placeholder*="search" i]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"Found search input with selector: {selector}")
                    break
                except:
                    continue
            
            if search_input:
                search_input.clear()
                search_input.send_keys(card_name)
                search_input.send_keys(Keys.ENTER)
                time.sleep(3)
            else:
                print("Could not find search input, using URL method")
                encoded_name = urllib.parse.quote(card_name)
                browser_navigate(driver, f"{base_url}/products/search?q={encoded_name}")
                time.sleep(3)
        else:
            # Direct URL navigation
            encoded_name = urllib.parse.quote(card_name)
            search_url = f"{base_url}/products/search?q={encoded_name}"
            browser_navigate(driver, search_url)
            time.sleep(3)
        
        # Get current URL for debugging
        print(f"Current URL: {driver.current_url}")
        
        # Wait for content to load with multiple strategies
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.execute_script("return document.querySelectorAll('.product-item, .search-result, [data-testid*=product]').length")) > 0
            )
            print("Detected product elements")
        except:
            print("Note: Could not detect standard product elements, trying alternatives...")
        
        # Get page source
        html_content = browser_snapshot(driver)
        
        # Also try to get visible text content
        try:
            visible_text = driver.execute_script("return document.body.innerText")
        except:
            visible_text = ""
        
        # Extract prices using multiple patterns
        price_patterns = [
            r'\$[\d,]+\.\d{2}',  # Standard: $123.45 or $1,234.56
            r'\d{4}\s*\d{2}',   # Sometimes prices are separate digits
        ]
        
        all_prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, html_content)
            all_prices.extend(matches)
        
        # Filter to only valid price-like strings
        def is_valid_price(s):
            try:
                if '$' in s:
                    val = float(s.replace('$', '').replace(',', ''))
                    return 0.01 <= val < 1000000  # Reasonable price range
            except:
                pass
            return False
        
        valid_prices = [p for p in all_prices if is_valid_price(p)]
        unique_prices = sorted(set(valid_prices), key=lambda x: float(x.replace('$', '').replace(',', '')))
        
        # Try to find card-specific information
        page_title = "N/A"
        try:
            title_element = driver.find_element(By.TAG_NAME, "title")
            page_title = title_element.text
        except:
            pass
        
        # Check for any error messages or "no results" text
        no_results_found = any(text in html_content.lower() for text in [
            'no results found', 'no products found', 'sorry, no results'
        ])
        
        return {
            "card_name": card_name,
            "page_title": page_title,
            "current_url": driver.current_url,
            "prices_found": unique_prices[:20],  # First 20 unique prices
            "total_unique_prices": len(unique_prices),
            "no_results_detected": no_results_found,
            "html_length": len(html_content),
            "success": True
        }
        
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()
        return {
            "card_name": card_name,
            "error": str(e),
            "success": False
        }
        
    finally:
        try:
            driver.quit()
        except:
            pass


def format_price(price_str: str) -> float:
    """Convert price string to float."""
    cleaned = price_str.replace('$', '').replace(',', '')
    return float(cleaned)


def main():
    """Main function to run the TCGPlayer lookup."""
    # Test with 'black lotus'
    card_to_search = "black lotus"
    
    print("\n" + "="*60)
    print("TCGPlayer Price Lookup - Pocket-Shop")
    print("="*60)
    
    # Perform search
    result = search_tcgplayer(card_to_search, use_manual_search=True)
    
    # Display results
    if result["success"]:
        print(f"\nSearch Results for '{result['card_name']}':")
        print(f"Page Title: {result['page_title']}")
        print(f"Current URL: {result['current_url']}")
        print(f"HTML content length: {result['html_length']} chars")
        
        if result.get('no_results_detected'):
            print("WARNING: No results message detected on page!")
        
        print(f"Total unique prices found: {result['total_unique_prices']}")
        
        if result["prices_found"]:
            print(f"\nSample Prices (first 20):")
            for i, price in enumerate(result["prices_found"], 1):
                print(f"  {i:2d}. {price}")
            
            # Calculate statistics
            valid_prices = [format_price(p) for p in result["prices_found"] if format_price(p) > 0]
            if valid_prices:
                print(f"\nPrice Statistics:")
                print(f"  Minimum: ${min(valid_prices):,.2f}")
                print(f"  Maximum: ${max(valid_prices):,.2f}")
                print(f"  Average: ${sum(valid_prices)/len(valid_prices):,.2f}")
        else:
            print("\nNo prices found on page.")
    else:
        print(f"Search failed: {result.get('error', 'Unknown error')}")
    
    print("\n" + "="*60)
    return result


# Add this function to tcgplayer_lookup.py for use by main_loop.py

def lookup_card_price(card_name: str, set_code: str = None) -> float:
    """Look up a single card's price on TCGPlayer.
    
    Args:
        card_name: Name of the card to search
        set_code: Optional set code filter
        
    Returns:
        Average market price in dollars, or 0.0 if not found
    """
    result = perform_search(card_name)
    
    if result.get("success") and result.get("prices_found"):
        prices = [format_price(p) for p in result["prices_found"] if format_price(p) > 0]
        if prices:
            return sum(prices) / len(prices)  # Return average
    
    return 0.0  # Not found or error

# Also add a simpler direct lookup function
def get_card_average_price(card_name: str, set_code: str = None) -> dict:
    """Get average price for a card.
    
    Returns dict with: min, max, avg price and count
    """
    result = perform_search(card_name)
    
    if not result.get("success") or not result.get("prices_found"):
        return {"min": 0, "max": 0, "avg": 0, "count": 0}
    
    prices = [format_price(p) for p in result["prices_found"] if format_price(p) > 0]
    
    if not prices:
        return {"min": 0, "max": 0, "avg": 0, "count": 0}
    
    return {
        "min": min(prices),
        "max": max(prices),
        "avg": sum(prices) / len(prices),
        "count": len(prices)
    }

if __name__ == "__main__":
    main()

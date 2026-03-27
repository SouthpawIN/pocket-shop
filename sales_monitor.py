#!/usr/bin/env python3
"""Sales Monitor - Pocket Shop Sales Tracking Module

This module monitors for eBay sales through two channels:
1. Gmail email notifications (primary) - watches for "Congratulations! Someone bought your listing" emails
2. Direct eBay API polling (optional) - checks sold listings via eBay Selling API

Each detected sale is recorded in finance_tracker with the 30/30/40 split.
"""

import time
import re
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

# Import project modules
from finance_tracker import record_sale, load_finance_data
from browser_helpers.gmail_monitor import GmailMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SaleRecord:
    """Represents a detected sale"""
    item_name: str
    amount: float
    timestamp: float = field(default_factory=time.time)
    source: str = "gmail"  # "gmail" or "ebay_api"
    listing_id: Optional[str] = None
    recorded: bool = False


class SalesMonitor:
    """Monitor sales from eBay via Gmail notifications and optionally direct API polling."""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Gmail monitor setup
        self.gmail_monitor = GmailMonitor(config)
        
        # Tracking state
        self._processed_emails: Set[str] = set()  # Track processed email IDs
        self._last_sale_time: float = 0
        self._sales_cooldown: int = config.get("sales_cooldown_seconds", 60)  # Prevent duplicate recordings
        
        # eBay API setup (optional)
        self._ebay_api_enabled = config.get("ebay_api_enabled", False)
        self._last_ebay_check = 0
        self._ebay_poll_interval = 300  # 5 minutes between API checks
        
        # Load previously processed emails from state file
        self._load_processed_state()
        
        logger.info("SalesMonitor initialized")
        logger.info(f"  Gmail monitoring: ENABLED")
        logger.info(f"  eBay API polling: {'ENABLED' if self._ebay_api_enabled else 'DISABLED'}")
        
    def _load_processed_state(self):
        """Load state of processed emails to avoid duplicate processing."""
        state_file = Path("data/sales_monitor_state.json")
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    self._processed_emails = set(state.get("processed_emails", []))
                    logger.info(f"Loaded {len(self._processed_emails)} previously processed emails")
            except Exception as e:
                logger.warning(f"Could not load state file: {e}")
    
    def _save_processed_state(self):
        """Save state of processed emails."""
        state_file = Path("data/sales_monitor_state.json")
        try:
            state = {
                "processed_emails": list(self._processed_emails),
                "last_updated": datetime.now().isoformat()
            }
            state_file.parent.mkdir(exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save state file: {e}")
    
    def check_gmail_sales(self, limit: int = 10) -> List[SaleRecord]:
        """
        Check Gmail for new eBay sale notification emails.
        
        Args:
            limit: Maximum number of recent emails to check
            
        Returns:
            List of SaleRecord objects for newly detected sales
        """
        logger.info("Checking Gmail for sale notifications...")
        
        # Get raw sale data from Gmail monitor
        raw_sales = self.gmail_monitor.check_for_sales(limit=limit)
        
        sale_records = []
        for raw_sale in raw_sales:
            # Create a unique identifier for this sale (to avoid duplicates)
            sale_key = f"{raw_sale['item_name']}_{raw_sale['amount']}_{raw_sale['timestamp']}"
            
            if sale_key not in self._processed_emails:
                self._processed_emails.add(sale_key)
                record = SaleRecord(
                    item_name=raw_sale["item_name"],
                    amount=raw_sale["amount"],
                    timestamp=raw_sale["timestamp"],
                    source="gmail"
                )
                sale_records.append(record)
                logger.info(f"Detected new sale via Gmail: {record.item_name} - ${record.amount:.2f}")
        
        # Save state periodically
        if len(sale_records) > 0:
            self._save_processed_state()
        
        return sale_records
    
    def check_ebay_api_sales(self) -> List[SaleRecord]:
        """
        Check eBay API directly for sold listings (optional, requires eBay credentials).
        Uses the GetSoldListings call from eBay Selling APIs.
        
        Returns:
            List of SaleRecord objects for newly detected sales
        """
        if not self._ebay_api_enabled:
            return []
        
        # Rate limiting - only check every few minutes
        now = time.time()
        if now - self._last_ebay_check < self._ebay_poll_interval:
            return []
        self._last_ebay_check = now
        
        logger.info("Checking eBay API for sold listings...")
        
        try:
            import requests
            
            # eBay OAuth authentication
            oauth_url = "https://api.ebay.com/oauth/installationToken"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.config.get("ebay_refresh_token"),
                "redirect_uri": self.config.get("ebay_redirect_uri", "http://localhost")
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            response = requests.post(oauth_url, data=data, headers=headers)
            if response.status_code != 200:
                logger.error(f"eBay OAuth failed: {response.status_code}")
                return []
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            # Get sold listings
            marketplace_id = self.config.get("ebay_marketplace", "EBAY_US")
            api_url = f"https://api.ebay.com/sell/inventory/v1/sold_listings"
            
            headers = {
                "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
                "Ebay-Auth-Token": access_token
            }
            
            # Query parameters for sold listings
            params = {
                "page_size": 20,
                "sort_order": "DESC",
                "sort_by": "TIME_SOLD"
            }
            
            response = requests.get(api_url, headers=headers, params=params)
            if response.status_code != 200:
                logger.warning(f"eBay API error: {response.status_code}")
                return []
            
            result = response.json()
            sold_listings = result.get("soldListings", [])
            
            sale_records = []
            for listing in sold_listings:
                # Extract sale information
                listing_id = listing.get("ebayListingId")
                title = listing.get("title", "Unknown Item")
                quantity_sold = listing.get("quantitySold", 0)
                
                if quantity_sold <= 0:
                    continue
                
                # Get sold price (may need to check transaction details)
                sale_price = self._get_sold_price_from_listing(listing)
                
                if sale_price and listing_id not in self._processed_emails:
                    self._processed_emails.add(listing_id)
                    record = SaleRecord(
                        item_name=title,
                        amount=sale_price * quantity_sold,
                        listing_id=listing_id,
                        source="ebay_api"
                    )
                    sale_records.append(record)
                    logger.info(f"Detected sale via eBay API: {title} x{quantity_sold} - ${sale_price:.2f}")
            
            self._save_processed_state()
            return sale_records
            
        except Exception as e:
            logger.error(f"Error checking eBay API: {e}")
            return []
    
    def _get_sold_price_from_listing(self, listing: Dict) -> Optional[float]:
        """Extract sold price from a sold listing object."""
        # Try different fields where price might be stored
        price_fields = [
            ("soldPrice", "amount"),
            ("startPrice", "amount"),  # For fixed price listings
            ("reservePrice", "amount"),
        ]
        
        for field_path in price_fields:
            if len(field_path) == 2:
                parent, child = field_path
                if parent in listing and isinstance(listing[parent], dict):
                    amount_str = listing[parent].get(child)
                    if amount_str:
                        try:
                            return float(str(amount_str).replace("$", ""))
                        except ValueError:
                            continue
            else:
                amount_str = listing.get(field_path)
                if amount_str:
                    try:
                        return float(str(amount_str).replace("$", ""))
                    except ValueError:
                        continue
        
        return None
    
    def record_detected_sales(self, sales: List[SaleRecord]) -> int:
        """
        Record detected sales in the finance tracker.
        
        Args:
            sales: List of SaleRecord objects to record
            
        Returns:
            Number of sales successfully recorded
        """
        recorded_count = 0
        
        for sale in sales:
            # Check cooldown to prevent duplicate recordings
            if time.time() - self._last_sale_time < self._sales_cooldown:
                logger.warning(f"Sale within cooldown period, skipping: {sale.item_name}")
                continue
            
            try:
                # Record the sale with 30/30/40 split
                transaction = record_sale(sale.amount, sale.item_name)
                
                if transaction:
                    sale.recorded = True
                    self._last_sale_time = time.time()
                    recorded_count += 1
                    logger.info(f"Successfully recorded sale: {sale.item_name} (${sale.amount:.2f})")
                    
                    # Log the split
                    data = load_finance_data()
                    logger.info(f"Current funds - Savings: ${data['savings_fund']:.2f}, "
                              f"Profit: ${data['profit_total']:.2f}, "
                              f"Restock: ${data['restock_fund']:.2f}")
                
            except Exception as e:
                logger.error(f"Failed to record sale {sale.item_name}: {e}")
        
        return recorded_count
    
    def run_monitoring_cycle(self) -> Dict:
        """
        Run a complete monitoring cycle: check both sources and record any sales.
        
        Returns:
            Summary dictionary with counts of detected and recorded sales
        """
        summary = {
            "gmail_sales_detected": 0,
            "ebay_api_sales_detected": 0,
            "total_recorded": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        all_sales = []
        
        # Check Gmail for sale notifications
        gmail_sales = self.check_gmail_sales(limit=10)
        summary["gmail_sales_detected"] = len(gmail_sales)
        all_sales.extend(gmail_sales)
        
        # Optionally check eBay API directly
        ebay_sales = self.check_ebay_api_sales()
        summary["ebay_api_sales_detected"] = len(ebay_sales)
        all_sales.extend(ebay_sales)
        
        if all_sales:
            logger.info(f"Found {len(all_sales)} new sale(s) to record")
            recorded = self.record_detected_sales(all_sales)
            summary["total_recorded"] = recorded
        else:
            logger.info("No new sales detected")
        
        return summary
    
    def run_continuous(self, interval: int = 60, max_iterations: Optional[int] = None):
        """
        Run continuous monitoring loop.
        
        Args:
            interval: Seconds between monitoring cycles (default: 60)
            max_iterations: Maximum number of cycles (None for infinite)
        """
        iteration = 0
        logger.info(f"Starting continuous sales monitoring (interval: {interval}s)")
        
        try:
            while True:
                if max_iterations and iteration >= max_iterations:
                    logger.info("Max iterations reached, stopping.")
                    break
                
                summary = self.run_monitoring_cycle()
                iteration += 1
                
                # Wait for next cycle
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")


def main():
    """Main entry point for sales monitoring."""
    import yaml
    
    # Load configuration
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {
            "gmail_sale_keyword": "sold",
            "sales_cooldown_seconds": 60
        }
        logger.warning("No config.yaml found, using defaults")
    
    # Create and run sales monitor
    monitor = SalesMonitor(config)
    
    # Run a single cycle for testing
    print("\n=== Running single monitoring cycle ===")
    summary = monitor.run_monitoring_cycle()
    print(f"Gmail sales detected: {summary['gmail_sales_detected']}")
    print(f"eBay API sales detected: {summary['ebay_api_sales_detected']}")
    print(f"Total recorded: {summary['total_recorded']}")
    
    # Uncomment below for continuous monitoring
    # monitor.run_continuous(interval=60)


if __name__ == "__main__":
    main()

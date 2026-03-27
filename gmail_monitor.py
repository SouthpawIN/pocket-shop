#!/usr/bin/env python3
"""Gmail Sales Monitor - eBay sale notification detection for Pocket-Shop

Monitors Gmail for eBay sale notification emails, extracts sale amount and item name,
then calls finance_tracker.record_sale() to apply the 30/30/40 split.
"""

import re
import time
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Optional

# Import finance tracker for recording sales
from finance_tracker import record_sale


class GmailMonitor:
    """Monitor Gmail for eBay sale notification emails"""
    
    def __init__(self, gmail_email: str, gmail_password: str):
        """
        Initialize Gmail monitor with credentials.
        
        Args:
            gmail_email: Gmail address to monitor
            gmail_password: Gmail app password or OAuth token
        """
        self.email = gmail_email
        self.password = gmail_password
        self.mail = None  # IMAP connection
    
    def check_for_sales(self, limit: int = 10) -> List[Dict]:
        """
        Check Gmail for recent eBay sale notification emails.
        
        Args:
            limit: Maximum number of emails to check
            
        Returns:
            List of dictionaries containing sale information:
            - item_name: Name of the sold item
            - amount: Sale price in dollars
            """
        sales = []
        
        if not self.email or not self.password:
            print("Warning: Gmail credentials not configured.")
            print("Provide gmail_email and gmail_password to initialize GmailMonitor")
            return sales
        
        try:
            # Connect to Gmail IMAP
            print(f"Connecting to Gmail as {self.email}...")
            self.mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=30)
            self.mail.login(self.email, self.password)
            self.mail.select("inbox")
            
            # Search for eBay sale notifications with multiple criteria
            search_criteria = [
                ('FROM', '"eBay"', 'SUBJECT', 'sold'),
                ('FROM', '"eBay"', 'SUBJECT', 'bought your listing'),
                ('FROM', 'notifications@ebay.com', 'SUBJECT', 'sold'),
                ('FROM', '"eBay"', 'SUBJECT', 'sold out'),
            ]
            
            messages = None
            for criteria in search_criteria:
                try:
                    status, result = self.mail.search(None, *criteria)
                    if status == 'OK' and result[0] and result[0] != b'()':
                        messages = result[0]
                        print(f"Found {len(messages.split())} emails matching: {criteria}")
                        break
                except Exception as e:
                    print(f"Search criteria failed: {criteria}, error: {e}")
                    continue
            
            if messages and messages != b'()':
                # Get the last N message IDs (most recent)
                msg_ids = messages.split()[-limit:]
                print(f"Processing {len(msg_ids)} potential sale emails")
                
                for msg_id in msg_ids:
                    try:
                        status, msg_data = self.mail.fetch(msg_id, '(RFC822)')
                        if status != 'OK':
                            continue
                        
                        raw_msg = email.message_from_bytes(msg_data[0][1])
                        email_html = self._extract_email_body(raw_msg)
                        
                        # Parse sale information from email
                        sale_info = parse_sale_email(email_html)
                        if sale_info:
                            sales.append(sale_info)
                            print(f"  Found sale: {sale_info['item_name']} - ${sale_info['amount']:.2f}")
                    except Exception as e:
                        print(f"  Error processing email {msg_id}: {e}")
                        continue
            else:
                print("No eBay sale emails found.")
            
            self.mail.close()
            self.mail.logout()
            
        except imaplib.IMAP4.error as e:
            print(f"IMAP error: {e}")
            if self.mail:
                try:
                    self.mail.logout()
                except:
                    pass
        except Exception as e:
            print(f"Error checking Gmail: {e}")
        
        return sales
    
    def _extract_email_body(self, msg) -> str:
        """
        Extract HTML/text body from email.
        
        Args:
            msg: Email message object
            
        Returns:
            String containing the email body (HTML preferred for parsing)
        """
        if msg.is_multipart():
            # Prefer HTML content
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if content_type == "text/html" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload.decode('utf-8', errors='ignore')
                    except Exception:
                        continue
            
            # Fall back to plain text
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload.decode('utf-8', errors='ignore')
                    except Exception:
                        continue
        else:
            # Single part message
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    return payload.decode('utf-8', errors='ignore')
            except Exception:
                pass
        return ""
    
    def close(self):
        """Close the IMAP connection if open."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass
            self.mail = None


def parse_sale_email(email_html: str) -> Optional[Dict]:
    """
    Parse eBay sale notification email to extract item name and sale amount.
    
    Args:
        email_html: HTML content of the email
        
    Returns:
        Dictionary with 'item_name' and 'amount' keys, or None if parsing fails
    """
    if not email_html:
        return None
    
    # Convert HTML to plain text for easier parsing
    text_content = re.sub(r'<[^<]+?>', ' ', email_html)
    text_content = re.sub(r'\s+', ' ', text_content).strip()
    
    # Try multiple patterns to find the item name
    item_name = None
    
    # Pattern 1: "bought your listing:" followed by item name
    match = re.search(r'bought your listing[:\s]*(["\']?)([^"\'\n]{3,80})\1', text_content, re.IGNORECASE)
    if match:
        item_name = match.group(2).strip()
    
    # Pattern 2: "Your item sold!" followed by item name
    if not item_name:
        match = re.search(r'(?:your item sold|sold out)![:\s]*(["\']?)([^"\'\n]{3,80})\1', text_content, re.IGNORECASE)
        if match:
            item_name = match.group(2).strip()
    
    # Pattern 3: "Listing Title:" followed by item name
    if not item_name:
        match = re.search(r'listing title[:\s]*(["\']?)([^"\'\n]{3,80})\1', text_content, re.IGNORECASE)
        if match:
            item_name = match.group(2).strip()
    
    # Pattern 4: Look for the subject line in the email body
    if not item_name:
        match = re.search(r'subject[:\s]*(["\']?)([^"\'\n]{10,80})\1', text_content, re.IGNORECASE)
        if match:
            potential_name = match.group(2).strip()
            # Filter out generic subjects
            if 'sold' not in potential_name.lower() and 'bought' not in potential_name.lower():
                item_name = potential_name
    
    if not item_name or len(item_name) < 3:
        return None
    
    # Clean up item name - remove common noise
    item_name = re.sub(r'^\s*["\']|["\']\s*$', '', item_name)
    item_name = item_name.strip()
    
    # Extract sale amount - look for dollar amounts
    amount = None
    price_patterns = [
        # Pattern 1: Sale total
        r'sale total[:\s]+(\$[\d,]+\.\d{2})',
        # Pattern 2: You earned/You received
        r'you (?:earned|received)[:\s]+(\$[\d,]+\.\d{2})',
        # Pattern 3: Standard price format followed by context words
        r'(\$[\d,]+\.\d{2})\s*(?:shipping|total|you)',
        # Pattern 4: Price in parentheses or brackets
        r'[\(\[]\s*(\$[\d,]+\.\d{2})',
        # Pattern 5: Fallback - first reasonable dollar amount
        r'(\$[\d,]+\.\d{2})',
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text_content)
        if match:
            amount_str = match.group(1)
            try:
                amount = float(amount_str.replace(',', '').replace('$', ''))
                # Sanity check: reasonable sale amount
                if 0.01 <= amount <= 100000:
                    break
            except ValueError:
                continue
    
    if not amount or amount <= 0:
        return None
    
    return {
        "item_name": item_name,
        "amount": round(amount, 2)
    }


def update_finance_from_sales(sales: List[Dict], already_processed: set = None) -> int:
    """
    Update finance tracker with detected sales using the 30/30/40 split.
    
    Args:
        sales: List of sale dictionaries with 'item_name' and 'amount'
        already_processed: Set of (item_name, amount) tuples to skip
        
    Returns:
        Number of new sales recorded
    """
    if not sales:
        print("No sales to process.")
        return 0
    
    if already_processed is None:
        already_processed = set()
    
    recorded_count = 0
    
    for sale in sales:
        item_name = sale.get('item_name', 'Unknown')
        amount = sale.get('amount', 0)
        
        # Skip if already processed (avoid duplicates)
        sale_key = (item_name, amount)
        if sale_key in already_processed:
            print(f"Skipping duplicate: {item_name} - ${amount:.2f}")
            continue
        
        # Record the sale with 30/30/40 split
        print(f"\nRecording sale from Gmail...")
        transaction = record_sale(amount, item_name)
        
        if transaction:
            already_processed.add(sale_key)
            recorded_count += 1
    
    print(f"\nRecorded {recorded_count} new sales from Gmail.")
    return recorded_count


# Convenience function for quick use
def check_and_update_sales(gmail_email: str, gmail_password: str, limit: int = 10) -> int:
    """
    One-shot function to check Gmail for sales and update finance tracker.
    
    Args:
        gmail_email: Gmail address
        gmail_password: Gmail app password
        limit: Maximum emails to check
        
    Returns:
        Number of sales recorded
    """
    monitor = GmailMonitor(gmail_email, gmail_password)
    sales = monitor.check_for_sales(limit=limit)
    
    if sales:
        print(f"\n{'='*50}")
        print(f"Found {len(sales)} potential sale(s):")
        for sale in sales:
            print(f"  - {sale['item_name']}: ${sale['amount']:.2f}")
        print(f"{'='*50}\n")
        
        # Track processed sales to avoid duplicates
        already_processed = set()
        return update_finance_from_sales(sales, already_processed)
    else:
        print("No sales found in Gmail.")
        return 0


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Try to load credentials from environment or command line
    GMAIL_EMAIL = getattr(sys.modules.get('os', None), 'environ', {}).get(
        'GMAIL_EMAIL', input("Enter Gmail address: ") if len(sys.argv) < 2 else sys.argv[1]
    )
    
    if not GMAIL_EMAIL:
        print("Error: No Gmail email provided.")
        print("Set GMAIL_EMAIL environment variable or provide as argument.")
        sys.exit(1)
    
    # For demo purposes with test data
    print("\n=== Gmail Sales Monitor Demo ===")
    print(f"Email: {GMAIL_EMAIL}")
    print("\nTo use this module:")
    print("  from gmail_monitor import GmailMonitor, parse_sale_email, update_finance_from_sales")
    print("  monitor = GmailMonitor('your@email.com', 'app_password')")
    print("  sales = monitor.check_for_sales(limit=10)")
    print("  update_finance_from_sales(sales)")
    
    # Test parse_sale_email with sample content
    test_email = """
    Congratulations! Someone bought your listing: Black Lotus foil mint condition
    Your item sold for $42.99 shipping included.
    Sale total: $42.99
    """
    
    print("\n=== Testing parse_sale_email ===")
    result = parse_sale_email(test_email)
    if result:
        print(f"Parsed successfully:")
        print(f"  Item: {result['item_name']}")
        print(f"  Amount: ${result['amount']:.2f}")
    else:
        print("Failed to parse test email")

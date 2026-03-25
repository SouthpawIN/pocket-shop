#!/usr/bin/env python3
"""Gmail Sale Monitor - Email-based sale detection"""

import time
import re
from typing import List, Dict, Optional
import imaplib
import email
from email.header import decode_header


class GmailMonitor:
    """Monitor Gmail for eBay sale notification emails"""
    
    def __init__(self, config: Dict):
        self.email = config.get("gmail_email")
        self.password = config.get("gmail_password")
        
        if not self.email or not self.password:
            print("Warning: Gmail credentials not configured.")
            print("Add gmail_email and gmail_password to config.yaml")
    
    def check_for_sales(self, limit: int = 5) -> List[Dict]:
        """Check Gmail for eBay sale notification emails"""
        sales = []
        
        if not self.email or not self.password:
            return sales
        
        try:
            # Connect to Gmail IMAP
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.email, self.password)
            mail.select("inbox")
            
            # Search for eBay sale notifications
            # Try multiple search criteria
            search_criteria = [
                ('FROM', '"eBay"', 'SUBJECT', 'sold'),
                ('FROM', '"eBay"', 'SUBJECT', 'sold out'),
                ('FROM', '"eBay"', 'SUBJECT', 'bought your listing'),
                ('FROM', 'notifications@ebay.com', 'SUBJECT', 'sold')
            ]
            
            messages = None
            for criteria in search_criteria:
                status, result = mail.search(None, *criteria)
                if status == 'OK' and result[0]:
                    messages = result[0]
                    break
            
            if status == 'OK' and messages:
                # Get the last N message IDs
                msg_ids = messages.split()[-limit:]
                print(f"Found {len(msg_ids)} potential sale emails")
                
                for msg_id in msg_ids:
                    try:
                        status, msg_data = mail.fetch(msg_id, '(RFC822)')
                        if status != 'OK':
                            continue
                        
                        msg = email.message_from_bytes(msg_data[0][1])
                        body = self._extract_email_body(msg)
                        
                        # Parse sale information
                        sale_info = self._parse_ebay_sale(body)
                        if sale_info:
                            sales.append(sale_info)
                            print(f"Found sale: {sale_info['item_name']} - ${sale_info['amount']:.2f}")
                    except Exception as e:
                        print(f"Error processing email: {e}")
                        continue
            
            mail.logout()
            
        except imaplib.IMAP4.error as e:
            print(f"IMAP error: {e}")
        except Exception as e:
            print(f"Error checking Gmail: {e}")
        
        return sales
    
    def _extract_email_body(self, msg) -> str:
        """Extract text body from email"""
        if msg.is_multipart():
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
                elif content_type == "text/html" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            # Simple HTML to text conversion
                            html = payload.decode('utf-8', errors='ignore')
                            # Remove HTML tags
                            import re
                            text = re.sub('<[^<]+?>', '', html)
                            return text
                    except Exception:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    return payload.decode('utf-8', errors='ignore')
            except Exception:
                pass
        return ""
    
    def _parse_ebay_sale(self, body: str) -> Optional[Dict]:
        """Parse eBay sale notification for item name and price"""
        if not body:
            return None
        
        # Pattern 1: "Congratulations! Someone bought your listing: [Item Name]"
        item_match = re.search(r'bought your listing:\s*([^\n]+)', body, re.IGNORECASE)
        
        # Pattern 2: "Your item sold! [Item Name]"
        if not item_match:
            item_match = re.search(r'(?:sold out|item sold)![\s\n]*([^(\n]+)', body, re.IGNORECASE)
        
        # Pattern 3: Just look for the title in quotes or after "Listing Title:"
        if not item_match:
            item_match = re.search(r'Listing Title[:\s]+([^\n]+)', body, re.IGNORECASE)
        
        if not item_match:
            return None
        
        item_name = item_match.group(1).strip()
        # Clean up item name
        item_name = re.sub(r'^["\']|["\']$', '', item_name)  # Remove surrounding quotes
        item_name = item_name.strip()
        
        if not item_name or len(item_name) < 3:
            return None
        
        # Extract sale price - look for dollar amount
        price_patterns = [
            r'(\$[\d,]+\.\d{2})\s*(?:shipping|total|you)',
            r'sale total[:\s]+(\$[\d,]+\.\d{2})',
            r'(\$[\d,]+\.\d{2})',  # Fallback: first dollar amount
        ]
        
        amount = None
        for pattern in price_patterns:
            price_match = re.search(pattern, body)
            if price_match:
                amount_str = price_match.group(1)
                try:
                    amount = float(amount_str.replace(',', '').replace('$', ''))
                    if amount > 0 and amount < 10000:  # Sanity check
                        break
                except ValueError:
                    continue
        
        if not amount:
            return None
        
        return {
            "item_name": item_name,
            "amount": amount,
            "timestamp": time.time()
        }

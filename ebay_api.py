#!/usr/bin/env python3
"""
eBay API Integration - Create Draft Listings via Official API
============================================================

This module uses eBay's official Sell API with OAuth 2.0 authentication.
Much more reliable than browser automation - no CAPTCHAs or bot detection.

Setup Required:
1. Get eBay Developer credentials: https://developer.ebay.com
2. Create an app and get: Developer ID, Certificate ID, OAuth Token
3. Add credentials to config.yaml
"""

import requests
import time
import json
from pathlib import Path
from typing import Optional, Dict, List

### EBAY API CONFIGURATION ###

# eBay API Endpoints
EBAY_OAUTH_URL = "https://api.ebay.com/oauth/installationToken"
EBAY_CREATE_LISTING_URL = "https://api.ebay.com/sell/listings/v1/listing"
EBAY_GET_LISTING_URL = "https://api.ebay.com/sell/listings/v1/listing/{{listing_id}}"

# eBay Category IDs for MTG
EBAY_CATEGORIES = {
    "mtg_singles": "60087",  # Trading Cards > Magic: The Gathering > Singles
    "mtg_sealed": "60085"   # Trading Cards > Magic: The Gathering > Sealed Products
}

# eBay Condition IDs for Trading Cards
EBAY_CONDITIONS = {
    "mint": "302",
    "near_mint": "302",  # Maps to Mint on eBay
    "excellent": "283",
    "good": "284",
    "lightly_played": "281",
    "heavily_played": "282",
    "played": "301"
}


class eBayAPI:
    """eBay Sell API client for creating draft listings."""
    
    def __init__(self, config: Dict):
        """
        Initialize eBay API client.
        
        Args:
            config: Dictionary with eBay credentials:
                - ebay_developer_id: Your eBay Developer ID
                - ebay_cert_id: Your eBay Certificate ID  
                - ebay_refresh_token: OAuth refresh token
                - ebay_marketplace: Marketplace ID (default: EBAY_US)
        """
        self.developer_id = config.get('ebay_developer_id')
        self.cert_id = config.get('ebay_cert_id')
        self.refresh_token = config.get('ebay_refresh_token')
        self.marketplace = config.get('ebay_marketplace', 'EBAY_US')
        
        self.access_token = None
        self.token_expires_at = 0
        
        # Validate credentials
        if not all([self.developer_id, self.cert_id, self.refresh_token]):
            raise ValueError("Missing eBay API credentials. Add to config.yaml:")
    
    def authenticate(self) -> bool:
        """
        Authenticate with eBay using OAuth 2.0.
        
        Returns:
            True if authentication successful, False otherwise
        """
        # Check if we have a valid token
        if self.access_token and time.time() < self.token_expires_at:
            return True
        
        print("Authenticating with eBay API...")
        
        try:
            # Get new access token using refresh token
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            headers = {
                "X-EBAY-C-CUSTOMER-ID": self.developer_id,
                "X-EBAY-C-CERTIFICATE-ID": self.cert_id,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(EBAY_OAUTH_URL, data=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = time.time() + expires_in - 60  # Refresh before expiry
                print(f"✓ Authenticated with eBay API")
                return True
            else:
                print(f"✗ Authentication failed: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return False
    
    def create_draft_listing(self, card_info: Dict) -> Optional[str]:
        """
        Create a draft listing for a Magic card.
        
        Args:
            card_info: Dictionary with card details:
                - name: Card name
                - set_code: Set code (optional)
                - price: Listing price in USD
                - condition: Condition (mint, near_mint, excellent, etc.)
                - quantity: Quantity available
                - description: Additional description (optional)
        
        Returns:
            eBay listing ID if successful, None otherwise
        """
        # Authenticate first
        if not self.authenticate():
            print("✗ Failed to authenticate with eBay")
            return None
        
        # Extract card info
        name = card_info.get('name', '')
        set_code = card_info.get('set_code', '')
        price = float(card_info.get('price', 0.99))
        condition = card_info.get('condition', 'near_mint')
        quantity = int(card_info.get('quantity', 1))
        description = card_info.get('description', '')
        
        # Build listing title
        title = f"MTG {name}" + (f" [{set_code}]" if set_code else "")
        
        # Build listing data according to eBay API spec
        listing_data = {
            "title": title,
            "type": "FIXED_PRICE",
            "startTime": "SELLER",
            "sellerUserId": "",
            "location": {
                "city": "",
                "state": "",
                "postalCode": "",
                "country": "US"
            },
            "categoryId": EBAY_CATEGORIES["mtg_singles"],
            "conditionId": EBAY_CONDITIONS.get(condition.lower(), "302"),
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
            "returns": {
                "returnsEnforced": False,
                "returnPolicy": {
                    "returnsAcceptedEnum": "NOT_ACCEPTED",
                    "refundOptionEnum": "MONEY_BACK"
                }
            },
            "itemSpecifics": [
                {"name": "CardTitle", "value": [name]},
                {"name": "CardType", "value": ["Single Card"]},
                {"name": "Rarity", "value": [card_info.get('rarity', 'Uncommon')]}
            ]
        }
        
        # Add set information if available
        if set_code:
            listing_data["itemSpecifics"].append({"name": "Set", "value": [set_code]})
        
        print(f"\nCreating draft listing:")
        print(f"  Title: {title}")
        print(f"  Price: ${price:.2f}")
        print(f"  Condition: {condition}")
        print(f"  Quantity: {quantity}")
        
        try:
            # Send listing to eBay API
            headers = {
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
                "Content-Type": "application/json",
                "Ebay-Auth-Token": self.access_token
            }
            
            response = requests.post(EBAY_CREATE_LISTING_URL, json=listing_data, headers=headers, timeout=30)
            
            if response.status_code == 201:  # Created
                result = response.json()
                listing_id = result.get('ebayListingId')
                print(f"\n✓ Draft listing created!")
                print(f"  Listing ID: {listing_id}")
                
                # Get listing details URL
                state = result.get('state', 'DRAFT')
                print(f"  State: {state}")
                
                return listing_id
                
            elif response.status_code == 401:
                print(f"\n✗ Authentication failed - token may be expired")
                return None
                
            else:
                print(f"\n✗ Failed to create listing: {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"\n✗ Error creating listing: {e}")
            return None
    
    def get_listing(self, listing_id: str) -> Optional[Dict]:
        """
        Get details of an existing listing.
        
        Args:
            listing_id: eBay listing ID
            
        Returns:
            Listing details dictionary or None
        """
        if not self.authenticate():
            return None
        
        try:
            headers = {
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
                "Ebay-Auth-Token": self.access_token
            }
            
            url = EBAY_GET_LISTING_URL.replace("{{listing_id}}", listing_id)
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get listing: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error getting listing: {e}")
            return None
    
    def revise_listing(self, listing_id: str, revisions: Dict) -> bool:
        """
        Revise an existing draft listing.
        
        Args:
            listing_id: eBay listing ID
            revisions: Dictionary of fields to update
            
        Returns:
            True if revision successful
        """
        if not self.authenticate():
            return False
        
        try:
            headers = {
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
                "Content-Type": "application/json",
                "Ebay-Auth-Token": self.access_token
            }
            
            url = f"{EBAY_GET_LISTING_URL.replace('{{listing_id}}', listing_id)}/revise"
            response = requests.post(url, json=revisions, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                print(f"✓ Listing revised successfully")
                return True
            else:
                print(f"✗ Failed to revise listing: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error revising listing: {e}")
            return False


### CONVENIENCE FUNCTIONS ###

def load_ebay_config() -> Dict:
    """Load eBay credentials from config.yaml."""
    try:
        import yaml
        config_path = Path("~/projects/pocket-shop/config.yaml").expanduser()
        
        if not config_path.exists():
            print(f"Config file not found: {config_path}")
            print("Create it with eBay credentials:")
            print("  ebay_developer_id: YOUR_DEVELOPER_ID")
            print("  ebay_cert_id: YOUR_CERTIFICATE_ID")
            print("  ebay_refresh_token: YOUR_REFRESH_TOKEN")
            return {}
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        return {
            'ebay_developer_id': config.get('ebay_developer_id'),
            'ebay_cert_id': config.get('ebay_cert_id'),
            'ebay_refresh_token': config.get('ebay_refresh_token'),
            'ebay_marketplace': config.get('ebay_marketplace', 'EBAY_US')
        }
        
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def create_ebay_draft_api(card_info: Dict) -> Dict:
    """
    Create an eBay draft listing using the API.
    
    Args:
        card_info: Dictionary with card details
        
    Returns:
        Dictionary with 'success', 'listing_id', 'error' keys
    """
    config = load_ebay_config()
    
    if not config.get('ebay_developer_id'):
        return {
            "success": False,
            "error": "eBay API credentials not configured. Add to config.yaml:"
                       "\n  - ebay_developer_id"
                       "\n  - ebay_cert_id" 
                       "\n  - ebay_refresh_token"
        }
    
    try:
        api_client = eBayAPI(config)
        listing_id = api_client.create_draft_listing(card_info)
        
        if listing_id:
            return {
                "success": True,
                "listing_id": listing_id
            }
        else:
            return {
                "success": False,
                "error": "Failed to create listing"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Test the eBay API integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create eBay draft listing via API")
    parser.add_argument("--test", action="store_true", help="Run test with sample card")
    
    args = parser.parse_args()
    
    if args.test:
        # Test card data
        test_card = {
            "name": "Disturbing Mirth",
            "set_code": "dsk",
            "price": 0.11,
            "condition": "near_mint",
            "quantity": 1,
            "rarity": "uncommon"
        }
        
        print("Testing eBay API with sample card:")
        print(json.dumps(test_card, indent=2))
        print()
        
        result = create_ebay_draft_api(test_card)
        print(f"\nResult: {json.dumps(result, indent=2)}")
    else:
        print("Use --test to run a test listing")
        print("Or import create_ebay_draft_api() in your code")


if __name__ == "__main__":
    main()

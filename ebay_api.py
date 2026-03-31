#!/usr/bin/env python3
"""
eBay API Integration - Create Draft Listings via Official API
============================================================

This module supports TWO authentication methods:

1. AUTH'N'AUTH (Recommended for personal use):
   - Uses your eBay username and password directly
   - No OAuth flow needed, no CAPTCHAs
   - Token lasts ~18 months
   - Simple setup: just add ebay_username and ebay_password to config.yaml

2. OAUTH 2.0 (For production/shared use):
   - Uses developer credentials + refresh token
   - More secure for apps serving multiple users
   - Requires OAuth flow through browser

For the Pocket-Shop personal trading bot, Auth'n'Auth is recommended.
"""

import requests
import time
import json
from pathlib import Path
from typing import Optional, Dict

### EBAY API ENDPOINTS ###

# Auth'n'Auth token endpoint
EBAY_AUTHN_URL = "https://signin.ebay.com/ws/eBayISAPI.dll?SignIn"

# OAuth token endpoint (for refresh token flow)
EBAY_OAUTH_URL = "https://api.ebay.com/oauth/installationToken"

# Sell API endpoints
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
    """eBay Sell API client supporting both Auth'n'Auth and OAuth."""
    
    def __init__(self, config: Dict):
        """
        Initialize eBay API client.
        
        Supports two auth methods:
        1. Auth'n'Auth (simpler): ebay_username + ebay_password
        2. OAuth (more secure): ebay_developer_id + ebay_cert_id + ebay_refresh_token
        """
        self.config = config
        self.access_token = None
        self.token_expires_at = 0
        
        # Detect which auth method to use
        if config.get('ebay_username') and config.get('ebay_password'):
            self.auth_method = 'authn'
            self.username = config['ebay_username']
            self.password = config['ebay_password']
            self.app_id = config.get('ebay_app_id', 'Christop-PocketSh-PRD-72b0faaa2-33ae83df')
        elif all([config.get('ebay_developer_id'), config.get('ebay_cert_id'), config.get('ebay_refresh_token')]):
            self.auth_method = 'oauth'
            self.developer_id = config['ebay_developer_id']
            self.cert_id = config['ebay_cert_id']
            self.refresh_token = config['ebay_refresh_token']
        else:
            raise ValueError(
                "Missing eBay credentials. Add to config.yaml:\n"
                "  For Auth'n'Auth (recommended):\n"
                "    ebay_username: your_ebay_username\n"
                "    ebay_password: your_ebay_password\n"
                "    ebay_app_id: Christop-PocketSh-PRD-72b0faaa2-33ae83df\n"
                "  For OAuth:\n"
                "    ebay_developer_id, ebay_cert_id, ebay_refresh_token"
            )
        
        self.marketplace = config.get('ebay_marketplace', 'EBAY_US')
    
    def authenticate(self) -> bool:
        """Authenticate using the configured method."""
        if self.access_token and time.time() < self.token_expires_at:
            return True
        
        if self.auth_method == 'authn':
            return self._authenticate_authn()
        else:
            return self._authenticate_oauth()
    
    def _authenticate_authn(self) -> bool:
        """Authenticate using Auth'n'Auth (username/password)."""
        print("Authenticating with eBay (Auth'n'Auth)...")
        
        try:
            # Build the Auth'n'Auth request
            data = {
                "APPID": self.app_id,
                "USERCODE": self.username,
                "eBayAuthToken": self.password  # Password goes in eBayAuthToken field
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/xml"
            }
            
            response = requests.post(EBAY_AUTHN_URL, data=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Parse XML response for the token
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(response.content)
                    # Find eBayAuthToken in response
                    token_elem = root.find('.//eBayAuthToken')
                    if token_elem is not None:
                        self.access_token = token_elem.text.strip()
                        print(f"✓ Auth'n'Auth token received")
                        # Auth'n'Auth tokens typically last 18 months
                        self.token_expires_at = time.time() + (180 * 24 * 60 * 60)  # ~6 months buffer
                        return True
                    else:
                        print(f"✗ No token found in response")
                        print(f"Response: {response.text[:500]}")
                except ET.ParseError as e:
                    print(f"✗ Failed to parse XML: {e}")
                    print(f"Response: {response.text[:500]}")
            else:
                print(f"✗ Authentication failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
            
            return False
            
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return False
    
    def _authenticate_oauth(self) -> bool:
        """Authenticate using OAuth 2.0 (refresh token)."""
        print("Authenticating with eBay (OAuth)...")
        
        try:
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
                self.token_expires_at = time.time() + expires_in - 60
                print(f"✓ OAuth authentication successful")
                return True
            else:
                print(f"✗ Authentication failed: {response.status_code}")
                print(f"Response: {response.text[:200]}")
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
        if not self.authenticate():
            print("✗ Failed to authenticate with eBay")
            return None
        
        # Extract card info
        name = card_info.get('name', '')
        set_code = card_info.get('set_code', '')
        price = float(card_info.get('price', 0.99))
        condition = card_info.get('condition', 'near_mint')
        quantity = int(card_info.get('quantity', 1))
        rarity = card_info.get('rarity', 'uncommon')
        
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
                {"name": "Rarity", "value": [rarity]}
            ]
        }
        
        if set_code:
            listing_data["itemSpecifics"].append({"name": "Set", "value": [set_code]})
        
        print(f"\nCreating draft listing:")
        print(f"  Title: {title}")
        print(f"  Price: ${price:.2f}")
        print(f"  Condition: {condition}")
        print(f"  Quantity: {quantity}")
        
        try:
            headers = {
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
                "Content-Type": "application/json",
                "Ebay-Auth-Token": self.access_token
            }
            
            response = requests.post(EBAY_CREATE_LISTING_URL, json=listing_data, headers=headers, timeout=30)
            
            if response.status_code == 201:
                result = response.json()
                listing_id = result.get('ebayListingId')
                print(f"\n✓ Draft listing created!")
                print(f"  Listing ID: {listing_id}")
                print(f"  State: {result.get('state', 'DRAFT')}")
                return listing_id
            else:
                print(f"\n✗ Failed to create listing: {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"\n✗ Error creating listing: {e}")
            return None
    
    def get_listing(self, listing_id: str) -> Optional[Dict]:
        """Get details of an existing listing."""
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


def load_ebay_config() -> Dict:
    """Load eBay credentials from config.yaml."""
    try:
        import yaml
        config_path = Path("~/projects/pocket-shop/config.yaml").expanduser()
        
        if not config_path.exists():
            print(f"Config file not found: {config_path}")
            return {}
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        return {
            'ebay_username': config.get('ebay_username'),
            'ebay_password': config.get('ebay_password'),
            'ebay_app_id': config.get('ebay_app_id', 'Christop-PocketSh-PRD-72b0faaa2-33ae83df'),
            'ebay_developer_id': config.get('ebay_developer_id'),
            'ebay_cert_id': config.get('ebay_cert_id'),
            'ebay_refresh_token': config.get('ebay_refresh_token'),
            'ebay_marketplace': config.get('ebay_marketplace', 'EBAY_US')
        }
        
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def create_ebay_draft_api(card_info: Dict) -> Dict:
    """Create an eBay draft listing using the API."""
    config = load_ebay_config()
    
    if not config.get('ebay_username') and not config.get('ebay_developer_id'):
        return {
            "success": False,
            "error": "eBay credentials not configured. Add to config.yaml:\n"
                     "  ebay_username: YOUR_EBAY_USERNAME\n"
                     "  ebay_password: YOUR_EBAY_PASSWORD\n"
                     "  ebay_app_id: Christop-PocketSh-PRD-72b0faaa2-33ae83df"
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


if __name__ == "__main__":
    main()

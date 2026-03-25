#!/usr/bin/env python3
"""eBay Listing Creator - API Integration"""

import requests
import time
from typing import Optional, Dict, List
import json


class ListingCreator:
    """Create and manage eBay listings via API"""
    
    EBAY_CATEGORIES = {
        "mtg_cards": "1493",  # Trading Cards > Magic: The Gathering > Cards
        "mtg_singles": "60087",  > Singles
        "mtg_sealed": "60085",  > Sealed Products
    }
    
    CONDITIONS = {
        "near_mint": "302",
        "excellent": "283",
        "good": "284",
        "light_play": "281",
        "heavy_play": "282",
        "played": "301"
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.marketplace_id = config.get("ebay_marketplace", "EBAY_US")
        self.access_token = None
        self.token_expires_at = 0
        
        # eBay API endpoints
        self.oauth_url = "https://api.ebay.com/oauth/dreamlin"
        self.create_listing_url = f"https://api.ebay.com/sell/listings/v1/listing"
    
    def authenticate(self) -> bool:
        """Get eBay access token using OAuth 2.0"""
        
        # Check if we have a valid token
        if self.access_token and time.time() < self.token_expires_at:
            return True
        
        try:
            # Get new access token
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.config.get("ebay_refresh_token"),
                "redirect_uri": self.config.get("ebay_redirect_uri", "http://localhost")
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(self.oauth_url, data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in - 60  # Refresh before expiry
                return True
            else:
                print(f"eBay OAuth error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"eBay authentication failed: {e}")
            return False
    
    def create_draft(self, name: str, price: float, quantity: int = 1,
                     condition: str = "near_mint", 
                     image_path: Optional[str] = None) -> Optional[str]:
        """Create a draft listing on eBay"""
        
        if not self.authenticate():
            print("Failed to authenticate with eBay")
            return None
        
        # Build listing request
        listing_data = {
            "title": f"MTG Magic: The Gathering - {name}",
            "type": "FIXED_PRICE",
            "startTime": "SELLER",
            "sellerUserId": "",
            "location": {
                "city": "",
                "state": "",
                "postalCode": "",
                "country": "US"
            },
            "categoryId": self.EBAY_CATEGORIES["mtg_singles"],
            "conditionId": self.CONDITIONS.get(condition, "302"),
            "price": {
                "amount": f"{price:.2f}",
                "currency": "USD"
            },
            "quantity": {
                "quantityAvailable": quantity,
                "quantitySold": 0
            },
            "shippingInfo": {
                "shippingServiceCost": [
                    {
                        "shippingServicePriority": 1,
                        "shippingType": "EXPEDITED",
                        "shippingServiceCost": {
                            "amount": "3.99",
                            "currency": "USD"
                        }
                    }
                ],
                "expeditedShipping": {
                    "expeditedShippingServiceCost": [
                        {
                            "shippingType": "EXPEDITED",
                            "shippingServiceCost": {
                                "amount": "3.99",
                                "currency": "USD"
                            }
                        }
                    ]
                },
                "oneDayShipping": False,
                "handlingTime": 1
            },
            "paymentMethods": ["PAYPAL", "ALL_MAJOR_CREDIT_CARTS"]
        }
        
        # Add image if provided
        if image_path and Path(image_path).exists():
            # Upload image to eBay first, then reference it
            image_url = self._upload_image(image_path)
            if image_url:
                listing_data["itemSpecifics"] = {
                    "ImageLink": [image_url]
                }
        
        # Add MTG-specific item specifics
        listing_data["itemSpecifics"] = listing_data.get("itemSpecifics", {})
        listing_data["itemSpecifics"]["CardTitle"] = name
        listing_data["itemSpecifics"]["CardType"] = ["Single Card"]
        
        headers = {
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            "Content-Type": "application/json",
            "Ebay-Auth-Token": self.access_token
        }
        
        try:
            response = requests.post(
                self.create_listing_url,
                json=listing_data,
                headers=headers
            )
            
            if response.status_code == 201:
                result = response.json()
                listing_id = result.get("ebayListingId")
                print(f"Draft created successfully: {listing_id}")
                return listing_id
            else:
                print(f"eBay listing error: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"Error creating listing: {e}")
            return None
    
    def _upload_image(self, image_path: str) -> Optional[str]:
        """Upload an image to eBay and return the URL"""
        # Simplified - would need proper eBay image upload implementation
        print(f"Image upload not yet implemented for: {image_path}")
        return None
    
    def get_listing(self, listing_id: str) -> Optional[Dict]:
        """Get details of an existing listing"""
        if not self.authenticate():
            return None
        
        headers = {
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            "Ebay-Auth-Token": self.access_token
        }
        
        url = f"{self.create_listing_url}/{listing_id}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting listing: {e}")
            return None
    
    def end_listing(self, listing_id: str, reason: str = "SOLD") -> bool:
        """End an active listing"""
        if not self.authenticate():
            return False
        
        headers = {
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            "Ebay-Auth-Token": self.access_token
        }
        
        data = {"reason": reason}
        url = f"{self.create_listing_url}/{listing_id}/endListing"
        
        try:
            response = requests.post(url, json=data, headers=headers)
            return response.status_code == 200
        except Exception as e:
            print(f"Error ending listing: {e}")
            return False

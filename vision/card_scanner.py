#!/usr/bin/env python3
"""Card Scanner - Vision-based MTG card identification"""

import requests
import base64
from pathlib import Path
from typing import Optional, Dict
import re


class CardScanner:
    """Scan and identify MTG cards using vision AI"""
    
    def __init__(self, device: str = "auto"):
        self.device = device
        # Hermes API endpoint for vision analysis
        self.vision_endpoint = "http://localhost:8000/vision/analyze"
    
    def scan_card(self, image_path: Optional[str] = None) -> Optional[Dict]:
        """Scan a card and identify it using vision AI"""
        
        if image_path:
            # Use provided image path
            img_path = Path(image_path)
            if not img_path.exists():
                print(f"Error: Image not found at {img_path}")
                return None
        else:
            # Capture from phone camera via burner-phone framework
            img_path = self._capture_from_phone()
            if not img_path:
                return None
        
        print(f"Scanning card from: {img_path}")
        
        # Encode image to base64
        try:
            with open(img_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"Error reading image: {e}")
            return None
        
        # Send to vision API
        prompt = ("Identify this Magic: The Gathering card. Provide the exact card name, "
                  "set name, set code if visible, and rarity. Be precise with the card name "
                  "- it should match exactly what you'd search for on TCGPlayer.")
        
        try:
            response = requests.post(
                self.vision_endpoint,
                json={
                    "image": image_data,
                    "question": prompt
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_vision_result(result)
            else:
                print(f"Vision API error: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Error calling vision API: {e}")
            print("Make sure Hermes vision endpoint is running.")
            return None
    
    def _capture_from_phone(self) -> Optional[Path]:
        """Capture image from phone camera using burner-phone framework"""
        try:
            # This integrates with the burner-phone project's PhoneAgent
            from burner_phone import PhoneAgent
            
            agent = PhoneAgent(device=self.device)
            screenshot_path = agent.take_screenshot()
            return Path(screenshot_path)
        except ImportError:
            print("Error: burner-phone not available. Provide an image path directly.")
            return None
        except Exception as e:
            print(f"Error capturing from phone: {e}")
            return None
    
    def _parse_vision_result(self, result: Dict) -> Dict:
        """Parse vision API response into structured card data"""
        # Vision result format depends on the model
        # Typically returns a text description
        
        text_response = result.get("analysis", result.get("text", ""))
        
        if not text_response:
            return {
                "name": "Unknown",
                "set": "Unknown",
                "rarity": "Unknown",
                "confidence": 0.0,
                "raw_response": ""
            }
        
        # Try to extract card name from response
        # Pattern 1: "This is [Card Name] from..."
        name_match = re.search(r'(?:this is |the card is |identified as )\s*([A-Z][a-zA-Z\s\-\(\)]+?)(?:\s+from|\s+set|\s+rare|\s+uncommon|\s+common|\s+card|\.|$)', text_response, re.IGNORECASE)
        
        # Pattern 2: Just the card name at the start
        if not name_match:
            name_match = re.search(r'^([A-Z][a-zA-Z\s\-]+)(?:\s+is\s+a|\s+from|\s+is\s+the)', text_response, re.IGNORECASE)
        
        # Pattern 3: Card name in quotes
        if not name_match:
            name_match = re.search(r'["\']([A-Z][a-zA-Z\s\-]+)["\']', text_response)
        
        card_name = "Unknown"
        if name_match:
            card_name = name_match.group(1).strip()
            # Clean up the name
            card_name = re.sub(r'\s+', ' ', card_name)  # Multiple spaces to single
            card_name = card_name.strip(' ,.-')
        
        # Extract set info if present
        set_match = re.search(r'(?:from|set[:\s]+)([A-Z][a-zA-Z\s\-]+?)(?:\s+set|\s+rare|\s+uncommon|\s+common|\.|$)', text_response, re.IGNORECASE)
        card_set = set_match.group(1).strip() if set_match else "Unknown"
        
        # Extract rarity
        rarity = "Unknown"
        if re.search(r'\brare\b', text_response, re.IGNORECASE):
            rarity = "Rare"
        elif re.search(r'\buncommon\b', text_response, re.IGNORECASE):
            rarity = "Uncommon"
        elif re.search(r'\bcommon\b', text_response, re.IGNORECASE):
            rarity = "Common"
        elif re.search(r'\bymythic\b', text_response, re.IGNORECASE):
            rarity = "Mythic Rare"
        
        return {
            "name": card_name,
            "set": card_set,
            "rarity": rarity,
            "confidence": 0.85,  # Placeholder
            "raw_response": text_response
        }
    
    def verify_card(self, image_path: str, expected_name: str) -> bool:
        """Verify that a scanned card matches an expected name"""
        result = self.scan_card(image_path)
        if not result:
            return False
        
        scanned_name = result['name'].lower().strip()
        expected_lower = expected_name.lower().strip()
        
        # Simple fuzzy match
        return scanned_name in expected_lower or expected_lower in scanned_name

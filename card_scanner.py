#!/usr/bin/env python3
"""Card Scanner Module - Vision-based Card Identification

Uses Hermes vision_analyze tool to identify Magic: The Gathering cards from photos.
Outputs card name, set code, condition assessment, and variant details.
"""

import sys
from pathlib import Path
from typing import Dict, Optional, List

sys.path.insert(0, str(Path(__file__).parent))

class CardScanner:
    """Vision-based card identification using Hermes tools."""
    
    def __init__(self):
        pass
    
    def identify_card(self, image_path: str) -> Optional[Dict]:
        """Identify a single card from an image.
        
        Args:
            image_path: Path to card image file
            
        Returns:
            Dict with card info: name, set_code, set_name, condition, is_foil, confidence
        """
        from hermes_tools import vision_analyze
        
        print(f"Scanning card: {image_path}")
        
        # Use Hermes vision analysis
        result = vision_analyze(
            image_url=image_path,
            question="""Identify this Magic: The Gathering trading card. Provide:
1. Card name (exact name as printed)
2. Set name and set code (e.g., "Fourth Edition [4ED]")
3. Card number if visible
4. Condition assessment: Mint, Near Mint, Excellent, Good, Lightly Played, Heavily Played, or Damaged
5. Whether it's foil, stamped, or has any variants
6. Confidence level (0-1)

Format as JSON with keys: name, set_name, set_code, card_number, condition, is_foil, has_stamp, confidence"""
        )
        
        # Parse result - vision_analyze returns analysis text
        # We'd need to parse this into structured data
        return self._parse_vision_result(result, image_path)
    
    def _parse_vision_result(self, analysis_text: str, image_path: str) -> Dict:
        """Parse vision analysis into structured card data."""
        import json
        import re
        
        # Try to extract JSON if present
        json_match = re.search(r"\{[^{}]+\}", analysis_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Fallback: manual parsing
        text = analysis_text.lower()
        
        return {
            "image_path": image_path,
            "name": "Unknown - needs manual review",
            "set_code": None,
            "set_name": None,
            "condition": "Unknown",
            "is_foil": False,
            "confidence": 0.0,
            "raw_analysis": analysis_text[:500]  # First 500 chars for reference
        }
    
    def batch_scan(self, image_paths: List[str]) -> List[Dict]:
        """Scan multiple card images.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            List of card identification results
        """
        results = []
        for path in image_paths:
            print(f"Processing: {path}")
            result = self.identify_card(path)
            if result:
                results.append(result)
        
        return results
    
    def scan_from_camera(self, device_id: str = "RF8M221SXHZ") -> Optional[Dict]:
        """Capture and identify card from phone camera.
        
        Args:
            device_id: ADB device ID (default: S10)
            
        Returns:
            Card identification result
        """
        # Capture screenshot from device
        import subprocess
        import tempfile
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_path = temp_file.name
        
        # Take screenshot via ADB
        subprocess.run([
            "adb", "-s", device_id, 
            "exec-out", "screencap", "-p"
        ], stdout=open(temp_path, "wb"))
        
        print(f"Captured image from {device_id}")
        
        # Identify the card
        return self.identify_card(temp_path)

### TEST FUNCTION ###

def test_card_scanner():
    """Test the card scanner."""
    scanner = CardScanner()
    
    print("=== Card Scanner Test ===")
    print("Card scanner initialized.")
    print("\nTo test with a real card:")
    print("  scanner.identify_card('/path/to/card/image.jpg')")
    print("\nOr scan from S10 camera:")
    print("  scanner.scan_from_camera()")

if __name__ == "__main__":
    test_card_scanner()

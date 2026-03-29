#!/usr/bin/env python3
"""
Scryfall Pricing Module - Replace TCGPlayer with Scryfall API
================================================================

Scryfall provides:
- Free, open API with no rate limiting issues
- Aggregated pricing from multiple marketplaces (TCGPlayer, CardKingdom, etc.)
- Reliable JSON responses
- No JavaScript rendering required

This module replaces the TCGPlayer browser automation approach.
"""

import requests
from typing import Optional, Dict, List

SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT = "Pocket-Shop/1.0 (automated-mtg-trading)"

def search_card(card_name: str, set_code: str = None) -> Dict:
    """Search for a card by name.
    
    Args:
        card_name: Name of the card to search
        set_code: Optional set code filter (e.g., 'dsk' for Duskmourn)
        
    Returns:
        Dictionary with search results or error info
    """
    url = f"{SCRYFALL_BASE}/cards/search"
    params = {
        "q": f"name:\"{card_name}\"",
        "order": "relevancy",
        "unique": "prints",
        "include_extras": "true"
    }
    
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {"error": f"API error: {response.status_code}"}
        
        data = response.json()
        
        if data.get('object') == 'error':
            return {"error": data.get('text', 'Unknown error')}
        
        cards = data.get('data', [])
        
        # Filter by set code if provided
        if set_code:
            cards = [c for c in cards if c.get('set') == set_code]
        
        return {
            "success": True,
            "total": data.get('total_cards', 0),
            "cards": cards
        }
        
    except Exception as e:
        return {"error": str(e)}


def get_card_pricing(card_name: str, set_code: str = None) -> Dict:
    """Get pricing information for a card.
    
    Args:
        card_name: Name of the card
        set_code: Optional set code
        
    Returns:
        Dictionary with pricing information including:
        - usd_non_foil: Non-foil USD price
        - usd_foil: Foil USD price  
        - eur_non_foil: Non-foil EUR price
        - eur_foil: Foil EUR price
        - tcgplayer_url: Link to TCGPlayer
        - cardkingdom_url: Link to CardKingdom
        - cardmarket_url: Link to CardMarket
    """
    search_result = search_card(card_name, set_code)
    
    if not search_result.get('success') or not search_result.get('cards'):
        return search_result
    
    # Get first/best match
    card = search_result['cards'][0]
    
    pricing_info = {
        "success": True,
        "card_name": card.get('name'),
        "set_name": card.get('set_name'),
        "set_code": card.get('set'),
        "rarity": card.get('rarity'),
        "prices": {},
        "marketplace_links": {}
    }
    
    # Extract Scryfall estimated prices
    if 'prices' in card:
        p = card['prices']
        pricing_info["prices"] = {
            "usd_non_foil": p.get('usd'),
            "usd_foil": p.get('usd_foil'),
            "eur_non_foil": p.get('eur'),
            "eur_foil": p.get('eur_foil'),
            "tix": p.get('tix')  # Tournament piece value
        }
    
    # Extract marketplace links
    if 'market_data' in card:
        mk = card['market_data']
        pricing_info["marketplace_links"] = {
            "tcgplayer_url": mk.get('tcgplayer_url'),
            "cardkingdom_url": mk.get('cardkingdom_url'),
            "cardmarket_url": mk.get('cardmarket_url')
        }
    
    return pricing_info


def get_market_price(card_name: str, set_code: str = None, foil: bool = False) -> Optional[float]:
    """Get a single market price value for a card.
    
    Args:
        card_name: Card name
        set_code: Optional set code
        foil: Whether to get foil price
        
    Returns:
        Price in USD as float, or None if not available
    """
    pricing = get_card_pricing(card_name, set_code)
    
    if not pricing.get('success') or 'prices' not in pricing:
        return None
    
    # Select appropriate price key
    if foil:
        price_key = 'usd_foil'
    else:
        price_key = 'usd_non_foil'
    
    price = pricing['prices'].get(price_key)
    
    # Fallback to non-foil if foil price not available
    if price is None and foil:
        price = pricing['prices'].get('usd_non_foil')
    
    return float(price) if price else None


# Legacy compatibility functions (same names as old tcgplayer_lookup.py)

def lookup_card_price(card_name: str, set_code: str = None) -> float:
    """Legacy function - returns average market price."""
    price = get_market_price(card_name, set_code)
    return price if price else 0.0


def perform_search(card_name: str) -> Dict:
    """Legacy function - performs card search."""
    return get_card_pricing(card_name)


if __name__ == "__main__":
    # Test
    import sys
    card = sys.argv[1] if len(sys.argv) > 1 else "Lightning Bolt"
    result = get_card_pricing(card)
    
    import json
    print(json.dumps(result, indent=2))

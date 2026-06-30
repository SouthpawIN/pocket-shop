"""Tests for scryfall_pricing module."""
import pytest
from unittest.mock import patch, MagicMock

import scryfall_pricing


class TestSearchCard:
    """Tests for search_card()."""

    @patch("scryfall_pricing.requests.get")
    def test_successful_search(self, mock_get):
        """Should return card data on 200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "list",
            "total_cards": 1,
            "data": [{
                "name": "Lightning Bolt",
                "set": "lea",
                "set_name": "Limited Edition Alpha",
                "rarity": "common",
                "prices": {"usd": "50.00", "usd_foil": None, "eur": "40.00"},
            }],
        }
        mock_get.return_value = mock_response

        result = scryfall_pricing.search_card("Lightning Bolt")
        assert result["success"] is True
        assert result["total"] == 1
        assert result["cards"][0]["name"] == "Lightning Bolt"

    @patch("scryfall_pricing.requests.get")
    def test_card_not_found(self, mock_get):
        """Should return error when card doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = scryfall_pricing.search_card("Fake Card Name XYZ")
        assert "error" in result

    @patch("scryfall_pricing.requests.get")
    def test_api_error_response(self, mock_get):
        """Should handle Scryfall error object."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "error",
            "text": "No cards found",
        }
        mock_get.return_value = mock_response

        result = scryfall_pricing.search_card("Nonexistent")
        assert "error" in result

    @patch("scryfall_pricing.requests.get")
    def test_filter_by_set_code(self, mock_get):
        """Should filter results by set code."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "list",
            "total_cards": 2,
            "data": [
                {"name": "Lightning Bolt", "set": "lea"},
                {"name": "Lightning Bolt", "set": "m11"},
            ],
        }
        mock_get.return_value = mock_response

        result = scryfall_pricing.search_card("Lightning Bolt", set_code="m11")
        assert result["success"] is True
        assert len(result["cards"]) == 1
        assert result["cards"][0]["set"] == "m11"

    @patch("scryfall_pricing.requests.get")
    def test_connection_error(self, mock_get):
        """Should handle connection errors gracefully."""
        mock_get.side_effect = ConnectionError("Network unreachable")
        result = scryfall_pricing.search_card("Lightning Bolt")
        assert "error" in result


class TestGetCardPricing:
    """Tests for get_card_pricing()."""

    @patch("scryfall_pricing.search_card")
    def test_extracts_pricing(self, mock_search):
        """Should extract price fields from card data."""
        mock_search.return_value = {
            "success": True,
            "cards": [{
                "name": "Black Lotus",
                "set_name": "Limited Edition Alpha",
                "set": "lea",
                "rarity": "rare",
                "prices": {"usd": "10000.00", "usd_foil": "15000.00", "eur": "8000.00", "eur_foil": "12000.00", "tix": None},
            }],
        }

        result = scryfall_pricing.get_card_pricing("Black Lotus")
        assert result["success"] is True
        assert result["card_name"] == "Black Lotus"
        assert result["prices"]["usd_non_foil"] == "10000.00"
        assert result["prices"]["usd_foil"] == "15000.00"


class TestGetMarketPrice:
    """Tests for get_market_price()."""

    @patch("scryfall_pricing.get_card_pricing")
    def test_returns_float_price(self, mock_pricing):
        mock_pricing.return_value = {
            "success": True,
            "prices": {"usd_non_foil": "12.50", "usd_foil": "25.00"},
        }
        price = scryfall_pricing.get_market_price("Some Card")
        assert price == 12.50

    @patch("scryfall_pricing.get_card_pricing")
    def test_returns_foil_price(self, mock_pricing):
        mock_pricing.return_value = {
            "success": True,
            "prices": {"usd_non_foil": "12.50", "usd_foil": "25.00"},
        }
        price = scryfall_pricing.get_market_price("Some Card", foil=True)
        assert price == 25.00

    @patch("scryfall_pricing.get_card_pricing")
    def test_returns_none_when_unavailable(self, mock_pricing):
        mock_pricing.return_value = {"success": True, "prices": {}}
        price = scryfall_pricing.get_market_price("Some Card")
        assert price is None

    @patch("scryfall_pricing.get_card_pricing")
    def test_foil_fallback_to_nonfoil(self, mock_pricing):
        mock_pricing.return_value = {
            "success": True,
            "prices": {"usd_non_foil": "8.00", "usd_foil": None},
        }
        price = scryfall_pricing.get_market_price("Card", foil=True)
        assert price == 8.00

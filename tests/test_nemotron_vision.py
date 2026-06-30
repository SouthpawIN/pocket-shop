"""Tests for nemotron_vision module."""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import nemotron_vision


class TestEncodeImage:
    """Tests for encode_image()."""

    def test_encodes_file(self, tmp_path):
        """Should return base64 string for an image file."""
        img = tmp_path / "card.jpg"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        result = nemotron_vision.encode_image(str(img))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            nemotron_vision.encode_image("/nonexistent/path.jpg")


class TestParseVisionResponse:
    """Tests for parse_vision_response()."""

    def test_parses_valid_json(self):
        """Should extract card JSON from API response."""
        response = {
            "choices": [{
                "message": {
                    "content": '{"name": "Lightning Bolt", "set_name": "Alpha", "set_code": "lea", "card_number": "163", "condition": "Near Mint", "is_foil": false, "has_stamp": false, "confidence": 0.95}'
                }
            }]
        }
        result = nemotron_vision.parse_vision_response(response)
        assert result["name"] == "Lightning Bolt"
        assert result["set_code"] == "lea"
        assert result["confidence"] == 0.95

    def test_returns_error_on_bad_response(self):
        response = {"choices": [{"message": {"content": "I cannot identify this card."}}]}
        result = nemotron_vision.parse_vision_response(response)
        assert "error" in result

    def test_handles_empty_choices(self):
        result = nemotron_vision.parse_vision_response({"choices": []})
        assert "error" in result


class TestIdentifyCard:
    """Tests for identify_card()."""

    def test_returns_error_for_missing_image(self):
        result = nemotron_vision.identify_card("/nonexistent/path.jpg")
        assert "error" in result
        assert "not found" in result["error"].lower()

    @patch("nemotron_vision._call_vision_api")
    def test_uses_nemotron_first(self, mock_api, tmp_path):
        """Should try Nemotron as first provider."""
        img = tmp_path / "card.jpg"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")

        mock_api.return_value = {
            "success": True,
            "data": {
                "choices": [{
                    "message": {
                        "content": '{"name": "Black Lotus", "set_name": "Alpha", "set_code": "lea", "condition": "Near Mint", "is_foil": false, "has_stamp": false, "confidence": 0.9, "card_number": "232"}'
                    }
                }]
            },
        }

        result = nemotron_vision.identify_card(str(img), provider="nemotron")
        assert result["name"] == "Black Lotus"
        assert result["provider_used"] == "nemotron"
        assert mock_api.call_count == 1

    @patch("nemotron_vision._call_vision_api")
    def test_falls_back_on_failure(self, mock_api, tmp_path):
        """Should try next provider when first fails."""
        img = tmp_path / "card.jpg"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")

        # First call fails, second succeeds
        mock_api.side_effect = [
            {"success": False, "error": "Connection refused"},
            {
                "success": True,
                "data": {
                    "choices": [{
                        "message": {
                            "content": '{"name": "Sol Ring", "set_name": "Commander", "set_code": "cmr", "card_number": "5", "condition": "Good", "is_foil": false, "has_stamp": false, "confidence": 0.8}'
                        }
                    }]
                },
            },
        ]

        result = nemotron_vision.identify_card(str(img))
        assert result["name"] == "Sol Ring"
        assert mock_api.call_count == 2

    @patch("nemotron_vision._call_vision_api")
    def test_all_providers_fail(self, mock_api, tmp_path):
        """Should return error when all providers fail."""
        img = tmp_path / "card.jpg"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
        mock_api.return_value = {"success": False, "error": "Connection refused"}

        result = nemotron_vision.identify_card(str(img))
        assert "error" in result
        assert "all" in result["error"].lower() or "failed" in result["error"].lower()


class TestCallVisionApi:
    """Tests for _call_vision_api()."""

    @patch("nemotron_vision.requests.post")
    def test_successful_call(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}
        mock_post.return_value = mock_response

        result = nemotron_vision._call_vision_api(
            "http://localhost:8101/v1", "test-model", "base64data"
        )
        assert result["success"] is True

    @patch("nemotron_vision.requests.post")
    def test_connection_refused(self, mock_post):
        mock_post.side_effect = ConnectionError("Connection refused")
        result = nemotron_vision._call_vision_api(
            "http://localhost:8101/v1", "test-model", "base64data"
        )
        assert result["success"] is False
        assert "Connection refused" in result["error"]

    @patch("nemotron_vision.requests.post")
    def test_http_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = nemotron_vision._call_vision_api(
            "http://localhost:8101/v1", "test-model", "base64data"
        )
        assert result["success"] is False
        assert "500" in result["error"]

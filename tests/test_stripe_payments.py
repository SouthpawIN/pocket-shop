"""Tests for stripe_payments module."""
import pytest
import json
from unittest.mock import patch, MagicMock

import stripe_payments


class TestRunLinkCli:
    """Tests for _run_link_cli()."""

    @patch("stripe_payments.subprocess.run")
    def test_successful_json_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"status": "authenticated"}',
            stderr="",
        )
        result = stripe_payments._run_link_cli(["auth", "status"])
        assert result["success"] is True
        assert result["data"]["status"] == "authenticated"

    @patch("stripe_payments.subprocess.run")
    def test_command_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Not authenticated",
        )
        result = stripe_payments._run_link_cli(["auth", "status"])
        assert result["success"] is False
        assert "Not authenticated" in result["error"]

    @patch("stripe_payments.subprocess.run")
    def test_cli_not_installed(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        result = stripe_payments._run_link_cli(["auth", "status"])
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch("stripe_payments.subprocess.run")
    def test_timeout(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired("cmd", 60)
        result = stripe_payments._run_link_cli(["auth", "status"], timeout=60)
        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    @patch("stripe_payments.subprocess.run")
    def test_plain_text_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Authenticated as pocket-shop",
            stderr="",
        )
        result = stripe_payments._run_link_cli(["auth", "status"])
        assert result["success"] is True
        assert result.get("output") == "Authenticated as pocket-shop"


class TestCheckAuthStatus:
    """Tests for check_auth_status()."""

    @patch("stripe_payments._run_link_cli")
    def test_delegates_to_link_cli(self, mock_run):
        mock_run.return_value = {"success": True, "data": {"authenticated": True}}
        result = stripe_payments.check_auth_status()
        mock_run.assert_called_once_with(["auth", "status", "--format", "json"])
        assert result["success"] is True


class TestCreateSpendRequest:
    """Tests for create_spend_request()."""

    @patch("stripe_payments._run_link_cli")
    @patch("stripe_payments.get_config")
    def test_rejects_over_budget(self, mock_cfg, mock_run):
        mock_cfg.return_value = {"stripe": {"max_purchase_amount": 5000}}
        result = stripe_payments.create_spend_request(
            amount_cents=10000,
            merchant_name="Store",
            merchant_url="https://store.com",
            payment_method_id="pm_123",
            line_item_desc="Test item",
        )
        assert result["success"] is False
        assert "exceeds" in result["error"].lower()
        mock_run.assert_not_called()

    @patch("stripe_payments._run_link_cli")
    @patch("stripe_payments.get_config")
    def test_submits_within_budget(self, mock_cfg, mock_run):
        mock_cfg.return_value = {"stripe": {"max_purchase_amount": 5000}}
        mock_run.return_value = {"success": True, "data": {"id": "lsrq_123"}}

        result = stripe_payments.create_spend_request(
            amount_cents=2500,
            merchant_name="Card Sleeves Inc",
            merchant_url="https://sleeves.com",
            payment_method_id="pm_123",
            line_item_desc="100 penny sleeves",
        )
        assert result["success"] is True
        mock_run.assert_called_once()


class TestPurchaseSupplies:
    """Tests for purchase_supplies()."""

    @patch("stripe_payments.check_auth_status")
    def test_fails_when_not_authenticated(self, mock_auth):
        mock_auth.return_value = {"success": False, "error": "Not authenticated"}
        result = stripe_payments.purchase_supplies("sleeves", 12.99, "Store", "https://store.com")
        assert result["success"] is False
        assert "authenticated" in result["error"].lower()

    @patch("stripe_payments.list_payment_methods")
    @patch("stripe_payments.check_auth_status")
    def test_fails_when_no_payment_methods(self, mock_auth, mock_methods):
        mock_auth.return_value = {"success": True}
        mock_methods.return_value = {"success": True, "data": []}
        result = stripe_payments.purchase_supplies("sleeves", 12.99, "Store", "https://store.com")
        assert result["success"] is False


class TestCleanupCardFile:
    """Tests for cleanup_card_file()."""

    def test_removes_file(self, tmp_path):
        card_file = tmp_path / "card.json"
        card_file.write_text('{"pan": "4242"}')
        stripe_payments.cleanup_card_file(str(card_file))
        assert not card_file.exists()

    def test_no_error_on_missing_file(self):
        stripe_payments.cleanup_card_file("/tmp/nonexistent_pocket_shop_test.json")

"""Tests for finance/tracker module."""
import pytest
import json
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from finance.tracker import FinanceTracker


def make_tracker(tmp_path, config=None):
    """Create a FinanceTracker with data at a temp path."""
    if config is None:
        config = {"profit_split": {"savings": 0.30, "profit": 0.30, "restock": 0.40}, "restock_fund_target": 500.0}
    ft = FinanceTracker(config)
    ft.data_path = tmp_path / "finance.json"
    ft._initialize()
    return ft


class TestFinanceTrackerInit:
    def test_creates_file(self, tmp_path):
        ft = make_tracker(tmp_path)
        assert ft.data_path.exists()

    def test_initial_balances_zero(self, tmp_path):
        ft = make_tracker(tmp_path)
        balances = ft.get_balances()
        assert balances["savings_fund"] == 0.0
        assert balances["profit_total"] == 0.0
        assert balances["restock_fund"] == 0.0


class TestAddSale:
    def test_splits_30_30_40(self, tmp_path):
        ft = make_tracker(tmp_path)
        splits = ft.add_sale(100.00, "Lightning Bolt")
        assert abs(splits["savings"] - 30.00) < 0.01
        assert abs(splits["profit"] - 30.00) < 0.01
        assert abs(splits["restock"] - 40.00) < 0.01

    def test_balances_update(self, tmp_path):
        ft = make_tracker(tmp_path)
        ft.add_sale(100.00, "Black Lotus")
        balances = ft.get_balances()
        assert balances["savings_fund"] == 30.00
        assert balances["profit_total"] == 30.00
        assert balances["restock_fund"] == 40.00

    def test_multiple_sales_accumulate(self, tmp_path):
        ft = make_tracker(tmp_path)
        ft.add_sale(50.00, "Card A")
        ft.add_sale(50.00, "Card B")
        balances = ft.get_balances()
        assert balances["savings_fund"] == 30.00  # 15 + 15
        assert balances["profit_total"] == 30.00
        assert balances["restock_fund"] == 40.00  # 20 + 20

    def test_transaction_recorded(self, tmp_path):
        ft = make_tracker(tmp_path)
        ft.add_sale(75.50, "Sol Ring")
        txns = ft.get_transactions()
        assert len(txns) == 1
        assert txns[0]["amount"] == 75.50
        assert txns[0]["card_name"] == "Sol Ring"


class TestWithdrawFromFund:
    def test_debits_restock(self, tmp_path):
        ft = make_tracker(tmp_path)
        ft.add_sale(100.00, "Card")  # +40 restock
        success = ft.withdraw_from_fund("restock_fund", 35.00, "Sealed set purchase")
        assert success is True
        assert ft.get_balances()["restock_fund"] == 5.00

    def test_insufficient_funds(self, tmp_path):
        ft = make_tracker(tmp_path)
        success = ft.withdraw_from_fund("savings_fund", 100.00, "test")
        assert success is False

    def test_invalid_fund_name(self, tmp_path):
        ft = make_tracker(tmp_path)
        success = ft.withdraw_from_fund("fake_fund", 10.00)
        assert success is False


class TestGetSummary:
    def test_summary_has_balances(self, tmp_path):
        ft = make_tracker(tmp_path)
        ft.add_sale(200.00, "Card X")
        summary = ft.get_summary()
        assert summary["balances"]["savings_fund"] == 60.00
        assert summary["total_sales"] == 200.00
        assert summary["transaction_count"] == 1


class TestCheckRestockTarget:
    def test_below_target(self, tmp_path):
        ft = make_tracker(tmp_path)
        ft.add_sale(100.00, "Card")  # +40 restock
        check = ft.check_restock_target()
        assert check["reached"] is False
        assert check["remaining"] == 460.00

    def test_target_reached(self, tmp_path):
        ft = make_tracker(tmp_path)
        for _ in range(13):  # 13 * 40 = 520 > 500
            ft.add_sale(100.00, "Card")
        check = ft.check_restock_target()
        assert check["reached"] is True

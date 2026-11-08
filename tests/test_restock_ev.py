"""Decision math for the restock cycle. No network, no purchases."""
from __future__ import annotations

import json
import sys
from typing import Any
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

import restock_ev as rev  # noqa: E402


def candidate(**over: Any) -> rev.Candidate:
    base: dict[str, Any] = dict(
        name="Test Set Booster Box",
        sku="test-set",
        ev_box_value=300.0,
        ev_age_days=3,
        expected_hold_days=45,
        quotes=[rev.Quote(source="walmart", price=180.0, shipping=0.0)],
    )
    base.update(over)
    return rev.Candidate(**base)


def test_net_and_roi_math_is_exact() -> None:
    (evaluation,) = rev.evaluate(candidate(), sell_through=0.75)
    # gross 300*0.75 = 225; fees 225*0.1325 + 0.30 = 30.11; net = 225 - 180 - 30.11
    assert evaluation.gross == 225.0
    assert evaluation.fees == pytest.approx(30.11, abs=0.01)
    assert evaluation.net == pytest.approx(14.89, abs=0.01)
    assert evaluation.roi == pytest.approx(14.89 / 180.0, abs=0.001)
    assert evaluation.buyable


def test_sell_through_of_one_is_not_the_default() -> None:
    assert rev.DEFAULT_SELL_THROUGH == 0.75
    optimistic = rev.evaluate(candidate(), sell_through=1.0)[0]
    assert optimistic.net > rev.evaluate(candidate())[0].net


def test_stale_ev_is_refused_not_discounted() -> None:
    (evaluation,) = rev.evaluate(candidate(ev_age_days=45))
    assert not evaluation.buyable
    assert "45d old" in evaluation.refused


def test_low_marketplace_rating_is_refused() -> None:
    quote = rev.Quote(source="amazon", price=170.0, marketplace=True, seller_rating=0.91)
    (evaluation,) = rev.evaluate(candidate(quotes=[quote]))
    assert not evaluation.buyable
    assert "seller rating" in evaluation.refused


def test_price_above_balance_is_refused() -> None:
    (evaluation,) = rev.evaluate(candidate(), restock_balance=150.0)
    assert not evaluation.buyable
    assert "exceeds restock balance" in evaluation.refused


def test_unprofitable_at_the_prior_is_refused() -> None:
    (evaluation,) = rev.evaluate(candidate(ev_box_value=200.0))
    assert not evaluation.buyable
    assert "net $" in evaluation.refused


def test_mispriced_quotes_are_flagged_and_excluded_from_ranking() -> None:
    quotes = [
        rev.Quote(source="walmart", price=180.0),
        rev.Quote(source="amazon", price=185.0),
        rev.Quote(source="lgs-ebay", price=120.0),  # 34% under median
    ]
    evaluations = rev.evaluate(candidate(quotes=quotes))
    flagged = [e for e in evaluations if "possibly_mispriced" in e.flags]
    assert len(flagged) == 1 and flagged[0].quote_source == "lgs-ebay"
    assert all("lgs-ebay" != e.quote_source for e in rev.rank([candidate(quotes=quotes)]))


def test_rank_orders_by_roi_then_hold_then_cost() -> None:
    a = candidate(name="A", sku="a", ev_box_value=320.0, expected_hold_days=90)
    b = candidate(name="B", sku="b", ev_box_value=320.0, expected_hold_days=30)
    ranked = rev.rank([a, b])
    assert [e.candidate for e in ranked][:2] == ["B", "A"], "shorter hold wins the tie"


def test_tax_and_shipping_are_inside_landed_cost() -> None:
    quote = rev.Quote(source="tcg", price=180.0, shipping=12.0)
    (evaluation,) = rev.evaluate(candidate(quotes=[quote]), tax_rate=0.0825)
    assert evaluation.landed_cost == pytest.approx(180 + 12 + 180 * 0.0825, abs=0.01)


def test_trigger_price_hits_the_target_roi_exactly() -> None:
    target = 0.10
    trigger = rev.max_buy_price(candidate(), target_roi=target)
    quote = rev.Quote(source="walmart", price=trigger)
    (evaluation,) = rev.evaluate(candidate(quotes=[quote]))
    assert evaluation.roi == pytest.approx(target, abs=0.005)


def test_buy_order_states_the_numbers_and_needs_a_human() -> None:
    (evaluation,) = rev.evaluate(candidate())
    text = rev.buy_order(candidate(), evaluation, balance=520.0)
    assert "# Buy order" in text
    assert "Trigger price" in text
    assert "Nothing is purchased until Chris clicks" in text
    assert "$520.00" in text and "$340.00" in text  # balance and post-purchase


def test_cli_writes_an_order_and_buys_nothing(tmp_path: Path) -> None:
    payload = {"candidates": [{
        "name": "Innistrad Box", "sku": "in-mid", "ev_box_value": 310.0, "ev_age_days": 2,
        "expected_hold_days": 40,
        "quotes": [{"source": "walmart", "price": 175.0, "shipping": 0.0},
                   {"source": "amazon", "price": 182.5, "shipping": 5.99, "marketplace": True,
                    "seller_rating": 0.98}],
    }]}
    source = tmp_path / "candidates.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "restock"

    assert rev.main([str(source), "--balance", "500", "--out", str(out)]) == 0
    orders = list(out.glob("*.md"))
    assert len(orders) == 1
    assert "Buy order" in orders[0].read_text(encoding="utf-8")


def test_cli_reports_why_nothing_was_bought(tmp_path: Path, capsys) -> None:
    payload = [{"name": "Stale", "sku": "stale", "ev_box_value": 400.0, "ev_age_days": 60,
                "quotes": [{"source": "walmart", "price": 180.0}]}]
    source = tmp_path / "candidates.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    assert rev.main([str(source), "--balance", "500", "--out", str(tmp_path / "out")]) == 1
    assert "60d old" in capsys.readouterr().out

"""Per-card and per-box economics, using the operator's real shipping method."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from sale_economics import (  # noqa: E402
    Costs, EconomicsError, Sale, box_outcome, breakeven_price, net_for,
)

C = Costs()   # 1.99 charged, 0.40 cost, 13.25% + 0.30


def test_fee_applies_to_shipping_too():
    b = Sale(10.0).breakdown(C)
    # 13.25% of 11.99 (item + shipping), plus the fixed 0.30
    assert b["buyer_pays"] == 11.99
    assert b["marketplace_fee"] == round(11.99 * 0.1325 + 0.30, 2)


def test_fee_is_not_charged_on_item_alone():
    b = Sale(10.0).breakdown(C)
    item_only_fee = round(10.0 * 0.1325 + 0.30, 2)
    assert b["marketplace_fee"] > item_only_fee


def test_shipping_margin_and_contribution():
    assert round(C.shipping_margin, 2) == 1.59
    # margin minus the fee eBay takes on the shipping charged
    assert round(C.shipping_contribution(), 4) == 1.3263


def test_known_net_values():
    assert net_for(5.0, C) == 5.36
    assert net_for(20.0, C) == 18.38


def test_shipping_carries_a_cheap_card():
    # A quarter card still nets positive because shipping is charged at 1.99.
    assert net_for(0.25, C) == 1.24


def test_breakeven_is_negative_when_shipping_carries_fees():
    assert breakeven_price(C) == -1.18


def test_breakeven_rises_with_cost_basis():
    assert breakeven_price(C, cost_basis=5.0) > breakeven_price(C)


def test_cost_basis_reduces_net_one_for_one():
    assert round(net_for(10.0, C) - net_for(10.0, C, cost_basis=3.0), 2) == 3.0


def test_separate_orders_beat_one_combined_order():
    # Combining saves one fixed fee (0.30) but collects shipping once instead of
    # three times, losing two shipping contributions. With this shipping model
    # separate orders net more. Guarded so the trade-off stays deliberate.
    three_separate = 3 * net_for(5.0, C)
    combined = Sale(15.0, quantity=3).breakdown(C)
    assert three_separate > combined["net"]
    assert round(three_separate - combined["net"], 2) == 2.04


def test_combined_order_saves_fixed_fees_and_shipping_fees():
    combined = Sale(15.0, quantity=3).breakdown(C)
    three_fees = 3 * Sale(5.0).breakdown(C)["marketplace_fee"]
    # Two fewer orders means two fewer fixed fees AND two fewer shipping
    # charges for the percentage fee to apply to.
    saved = 2 * C.fixed_fee + 2 * C.shipping_charged * (C.fee_pct / 100.0)
    # Each order's fee is rounded to cents before summing, so allow one cent.
    assert (three_fees - combined["marketplace_fee"]) == pytest.approx(saved, abs=0.02)


def test_zero_shipping_cost_is_the_upper_bound():
    free = Costs(shipping_cost=0.0)
    assert net_for(10.0, free) > net_for(10.0, C)


def test_no_shipping_charge_removes_the_advantage():
    plain = Costs(shipping_charged=0.0)
    assert plain.shipping_contribution() == -0.40
    assert net_for(0.50, plain) < 0      # 0.43 after fee, less 0.70 of costs
    assert net_for(1.00, plain) == 0.17  # a dollar card only just clears


def test_impossible_inputs_refuse():
    with pytest.raises(EconomicsError):
        Costs(fee_pct=150)
    with pytest.raises(EconomicsError):
        Costs(shipping_cost=-1)
    with pytest.raises(EconomicsError):
        Sale(-5.0).breakdown(C)
    with pytest.raises(EconomicsError):
        Sale(5.0, quantity=0).breakdown(C)


def test_hundred_percent_fee_has_no_breakeven():
    with pytest.raises(EconomicsError):
        breakeven_price(Costs(fee_pct=100))


def test_box_outcome_uses_published_numbers():
    o = box_outcome(263.16, 169.29, 60, C)
    assert o["edge_before_costs"] == round(263.16 / 169.29, 4)
    assert o["net"] == 120.58
    assert o["shipping_contribution_total"] == round(1.3263 * 60, 2)


def test_box_outcome_charges_one_fixed_fee_per_listing():
    o = box_outcome(263.16, 169.29, 60, C)
    expected = (263.16 + 1.99 * 60) * 0.1325 + 0.30 * 60
    assert o["marketplace_fees"] == round(expected, 2)


def test_sales_tax_raises_the_landed_cost():
    o = box_outcome(263.16, 169.29, 60, C, sales_tax_rate=0.08)
    assert o["landed_cost"] == round(169.29 * 1.08, 2)
    assert o["net"] < box_outcome(263.16, 169.29, 60, C)["net"]


def test_partial_realisation_lowers_net():
    full = box_outcome(263.16, 169.29, 60, C)
    half = box_outcome(263.16, 169.29, 60, C, realised_fraction=0.5)
    assert half["net"] < full["net"]


def test_more_listings_raises_net_only_because_shipping_is_charged():
    # This is the model's known optimism: it assumes every card sells on its own
    # with 1.99 shipping attached. Guard the behaviour so it is a deliberate
    # choice, and pair it with the no-shipping-charge case below.
    a = box_outcome(263.16, 169.29, 40, C)["net"]
    b = box_outcome(263.16, 169.29, 120, C)["net"]
    assert b > a
    plain = Costs(shipping_charged=0.0)
    a2 = box_outcome(263.16, 169.29, 40, plain)["net"]
    b2 = box_outcome(263.16, 169.29, 120, plain)["net"]
    assert b2 < a2          # without the shipping margin, splitting costs money


def test_box_needs_at_least_one_listing():
    with pytest.raises(EconomicsError):
        box_outcome(263.16, 169.29, 0, C)


def test_realised_fraction_out_of_range_refuses():
    for bad in (0.0, -0.1, 1.5):
        with pytest.raises(EconomicsError):
            box_outcome(263.16, 169.29, 60, C, realised_fraction=bad)


def test_breakdown_is_json_shaped():
    b = Sale(5.0).breakdown(C)
    assert all(isinstance(v, (int, float, str)) for v in b.values())


# --- market parity, sourced in docs/shipping-market-rates.md -----------------

def test_tcgplayer_minimum_parity_contribution():
    # TCGplayer's sub-$5 floor is 1.49; matching it yields 0.893 per order.
    assert round(Costs(shipping_charged=1.49).shipping_contribution(), 3) == 0.893


def test_free_shipping_loses_money_below_eighty_one_cents():
    free = Costs(shipping_charged=0.0)
    assert breakeven_price(free) == 0.81
    assert net_for(0.50, free) < 0
    assert net_for(1.00, free) > 0


def test_shipping_charge_ranking_is_monotonic_in_net():
    nets = [net_for(5.0, Costs(shipping_charged=sc)) for sc in (0.0, 0.99, 1.49, 1.99)]
    assert nets == sorted(nets)


def test_one_order_covers_many_cards_when_shipping_is_free():
    # Free shipping is viable on a multi-card order: one 0.40 across ten cards.
    free = Costs(shipping_charged=0.0)
    lot = Sale(10.0, quantity=10).breakdown(free)
    assert lot["net"] > 0
    assert lot["per_card_net"] > 0

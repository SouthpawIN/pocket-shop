#!/usr/bin/env python3
"""What a single card actually nets, and what a box therefore nets.

The operator's real shipping method: a plain envelope he already owns, with two
bulk cards (worth pennies, unsellable) as front and back protectors instead of a
purchased sleeve. Buyer is charged a flat shipping fee; the actual cost is well
under a dollar. That gap is a genuine profit line, not a rounding error, and it
is modelled explicitly here rather than buried in a "fees" lump.

Two details that are easy to get wrong and are got right here:

* eBay's final value fee applies to the **total the buyer pays, including
  shipping** — not to the item price alone.
* The fixed per-order fee is charged once per order, so a multi-card order is
  cheaper per card than N separate orders.

Nothing here buys, lists or charges anything. It computes and explains.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Operator-supplied defaults. `shipping_cost` is his estimate and is meant to be
# replaced with a measured figure once he has weighed and posted a few.
DEFAULT_SHIPPING_CHARGED = 1.99
DEFAULT_SHIPPING_COST = 0.40
DEFAULT_FEE_PCT = 13.25          # eBay final value fee, most categories
DEFAULT_FIXED_FEE = 0.30         # eBay per-order fixed fee


class EconomicsError(ValueError):
    """An input is missing or impossible; do not produce a misleading number."""


def _non_negative(value: float, name: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise EconomicsError(f"{name} must be a number, got {value!r}") from exc
    if v < 0:
        raise EconomicsError(f"{name} must not be negative, got {v}")
    return v


@dataclass(frozen=True)
class Costs:
    shipping_charged: float = DEFAULT_SHIPPING_CHARGED
    shipping_cost: float = DEFAULT_SHIPPING_COST
    fee_pct: float = DEFAULT_FEE_PCT
    fixed_fee: float = DEFAULT_FIXED_FEE

    def __post_init__(self) -> None:
        for f in ("shipping_charged", "shipping_cost", "fee_pct", "fixed_fee"):
            _non_negative(getattr(self, f), f)
        if self.fee_pct > 100:
            raise EconomicsError(f"fee_pct must be <= 100, got {self.fee_pct}")

    @property
    def shipping_margin(self) -> float:
        """Gross gap between what the buyer pays for shipping and what it costs."""
        return self.shipping_charged - self.shipping_cost

    def shipping_contribution(self) -> float:
        """Shipping margin after the fee eBay takes on the shipping charged."""
        return self.shipping_charged * (1 - self.fee_pct / 100.0) - self.shipping_cost


@dataclass(frozen=True)
class Sale:
    price: float
    quantity: int = 1
    cost_basis: float = 0.0        # what the card(s) cost to acquire

    def breakdown(self, costs: Costs | None = None) -> dict[str, Any]:
        c = costs or Costs()
        price = _non_negative(self.price, "price")
        basis = _non_negative(self.cost_basis, "cost_basis")
        if self.quantity < 1:
            raise EconomicsError(f"quantity must be >= 1, got {self.quantity}")

        buyer_pays = price + c.shipping_charged
        fee = buyer_pays * (c.fee_pct / 100.0) + c.fixed_fee
        net = buyer_pays - fee - c.shipping_cost - basis
        return {
            "price": round(price, 2),
            "quantity": self.quantity,
            "shipping_charged": round(c.shipping_charged, 2),
            "buyer_pays": round(buyer_pays, 2),
            "marketplace_fee": round(fee, 2),
            "shipping_cost": round(c.shipping_cost, 2),
            "cost_basis": round(basis, 2),
            "net": round(net, 2),
            "shipping_contribution": round(c.shipping_contribution(), 2),
            "per_card_net": round(net / self.quantity, 2),
        }


def net_for(price: float, costs: Costs | None = None, *, cost_basis: float = 0.0,
            quantity: int = 1) -> float:
    return Sale(price, quantity, cost_basis).breakdown(costs)["net"]


def breakeven_price(costs: Costs | None = None, *, cost_basis: float = 0.0) -> float:
    """Lowest item price that still nets zero. Negative means shipping carries it."""
    c = costs or Costs()
    keep = 1 - c.fee_pct / 100.0
    if keep <= 0:
        raise EconomicsError("fee_pct of 100 leaves nothing; no break-even exists")
    return round((c.fixed_fee + c.shipping_cost + cost_basis) / keep - c.shipping_charged, 2)


def box_outcome(ev_market: float, sealed_price: float, sellable_cards: int,
                costs: Costs | None = None, *, realised_fraction: float = 1.0,
                sales_tax_rate: float = 0.0) -> dict[str, Any]:
    """Crack a box: what the contents net once every sellable card is posted.

    `ev_market` is MTGStocks' published contents value (commons already excluded).
    `sellable_cards` is how many separate listings that value is spread across —
    the operator's own count, because it drives the fixed fees and the shipping
    contribution, and guessing it would fabricate the answer.
    `realised_fraction` is how much of EV is actually achieved on sale; 1.0 means
    every card sells at its market price, which is optimistic and labelled so.
    """
    c = costs or Costs()
    ev = _non_negative(ev_market, "ev_market")
    paid = _non_negative(sealed_price, "sealed_price")
    if sellable_cards < 1:
        raise EconomicsError(f"sellable_cards must be >= 1, got {sellable_cards}")
    if not 0 < realised_fraction <= 1:
        raise EconomicsError(f"realised_fraction must be in (0, 1], got {realised_fraction}")

    landed = paid * (1 + _non_negative(sales_tax_rate, "sales_tax_rate"))
    achieved = ev * realised_fraction
    avg_price = achieved / sellable_cards

    # Each card posts separately: one fixed fee and one shipping margin each.
    buyer_total = achieved + c.shipping_charged * sellable_cards
    fees = buyer_total * (c.fee_pct / 100.0) + c.fixed_fee * sellable_cards
    shipping_out = c.shipping_cost * sellable_cards
    net = buyer_total - fees - shipping_out - landed

    return {
        "ev_market": round(ev, 2),
        "sealed_price": round(paid, 2),
        "landed_cost": round(landed, 2),
        "sellable_cards": sellable_cards,
        "realised_fraction": realised_fraction,
        "average_sale_price": round(avg_price, 2),
        "shipping_charged_total": round(c.shipping_charged * sellable_cards, 2),
        "marketplace_fees": round(fees, 2),
        "shipping_cost_total": round(shipping_out, 2),
        "shipping_contribution_total": round(c.shipping_contribution() * sellable_cards, 2),
        "net": round(net, 2),
        "edge_before_costs": round(ev / paid, 4) if paid else None,
        "note": "assumes every sellable card posts as its own order at market price",
    }

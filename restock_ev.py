#!/usr/bin/env python3
"""Restock decision math: pick the one sealed product worth buying this cycle.

This module never buys anything. It takes candidate sets with their real prices
from every source we can reach, computes net and ROI under the shop's own fee and
sell-through assumptions, and writes a buy order for a human to approve.

Design rules, all of which are enforced here rather than in prose:
  * EV data older than `MAX_EV_AGE_DAYS` is refused, not discounted.
  * A marketplace seller below `MIN_MARKETPLACE_RATING` is refused.
  * `sell_through` is a prior (default 0.75), never 1.0 - unsold stock is the
    real killer in sealed product.
  * A "sale" price far below the median is flagged `possibly_mispriced` and must
    be re-verified before it can win.
  * Ties break toward the shorter expected hold, then the lower absolute cost.

Usage:
    python restock_ev.py candidates.json --balance 520.00 --out data/restock/
"""
from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

# Shop assumptions. Change these in one place, not scattered through the code.
MARKETPLACE_FEE_RATE = 0.1325      # eBay final value fee
MARKETPLACE_FIXED_FEE = 0.30       # per order
DEFAULT_SELL_THROUGH = 0.75        # fraction of a cracked box that actually sells
MAX_EV_AGE_DAYS = 30
MIN_MARKETPLACE_RATING = 0.95
MISPRICED_DISCOUNT = 0.15          # >= 15% under median => re-verify
MIN_NET_PROFIT = 0.01

# Restock band from the project brief: set booster boxes, $150-$250 retail.
BAND_LOW, BAND_HIGH = 150.0, 250.0


@dataclass(frozen=True)
class Quote:
    source: str
    price: float
    url: str = ""
    shipping: float = 0.0
    in_stock: bool = True
    marketplace: bool = False       # 3rd-party seller (Amazon/Walmart marketplace)
    seller_rating: float = 1.0
    as_of: str = ""

    def landed(self, tax_rate: float = 0.0) -> float:
        return round(self.price + self.shipping + (self.price * tax_rate), 2)


@dataclass
class Candidate:
    name: str
    sku: str
    ev_box_value: float             # MTGStocks-style expected value of the box
    ev_age_days: int
    expected_hold_days: int = 60
    quotes: list[Quote] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> "Candidate":
        quotes = [Quote(**q) if isinstance(q, dict) else q for q in raw.get("quotes", [])]
        known = {f for f in cls.__dataclass_fields__ if f != "quotes"}
        return cls(quotes=quotes, **{k: v for k, v in raw.items() if k in known})


@dataclass(frozen=True)
class Evaluation:
    candidate: str
    quote_source: str
    price: float
    landed_cost: float
    gross: float
    fees: float
    net: float
    roi: float
    refused: str = ""
    flags: tuple[str, ...] = ()

    @property
    def buyable(self) -> bool:
        return not self.refused


def _median_price(quotes: Iterable[Quote]) -> float | None:
    prices = [q.price for q in quotes if q.in_stock and q.price > 0]
    return statistics.median(prices) if prices else None


def evaluate(
    candidate: Candidate,
    *,
    tax_rate: float = 0.0,
    sell_through: float = DEFAULT_SELL_THROUGH,
    fee_rate: float = MARKETPLACE_FEE_RATE,
    fixed_fee: float = MARKETPLACE_FIXED_FEE,
    bulk_disposal: float = 0.0,
    restock_balance: float | None = None,
) -> list[Evaluation]:
    """Every in-stock quote for one candidate, scored. Refusals keep their reason."""
    if candidate.ev_age_days > MAX_EV_AGE_DAYS:
        return [Evaluation(candidate.name, "", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                           refused=f"EV data is {candidate.ev_age_days}d old (max {MAX_EV_AGE_DAYS})")]

    median = _median_price(candidate.quotes)
    results: list[Evaluation] = []
    for quote in candidate.quotes:
        if not quote.in_stock:
            continue
        flags: list[str] = []
        refused = ""

        if quote.marketplace and quote.seller_rating < MIN_MARKETPLACE_RATING:
            refused = f"marketplace seller rating {quote.seller_rating:.2f} < {MIN_MARKETPLACE_RATING}"

        landed = quote.landed(tax_rate)
        if not (BAND_LOW <= landed <= BAND_HIGH * 1.35):
            flags.append(f"outside ${BAND_LOW:.0f}-${BAND_HIGH:.0f} band (landed ${landed:.2f})")

        if median and quote.price <= median * (1 - MISPRICED_DISCOUNT):
            flags.append("possibly_mispriced")

        gross = candidate.ev_box_value * sell_through
        fees = round(gross * fee_rate + fixed_fee, 2)
        net = round(gross - landed - fees - bulk_disposal, 2)
        roi = round(net / landed, 4) if landed else 0.0

        if net < MIN_NET_PROFIT and not refused:
            refused = f"net ${net:.2f} at {sell_through:.0%} sell-through"
        if restock_balance is not None and landed > restock_balance and not refused:
            refused = f"landed ${landed:.2f} exceeds restock balance ${restock_balance:.2f}"

        results.append(Evaluation(
            candidate=candidate.name, quote_source=quote.source, price=quote.price,
            landed_cost=landed, gross=round(gross, 2), fees=fees, net=net, roi=roi,
            refused=refused, flags=tuple(flags),
        ))
    return results


def rank(candidates: Iterable[Candidate], **kwargs) -> list[Evaluation]:
    """All buyable evaluations, best ROI first. Ties: shorter hold, then cheaper."""
    hold = {c.name: c.expected_hold_days for c in candidates}
    scored: list[Evaluation] = []
    for candidate in candidates:
        scored.extend(evaluate(candidate, **kwargs))
    buyable = [e for e in scored if e.buyable and "possibly_mispriced" not in e.flags]
    return sorted(buyable, key=lambda e: (-e.roi, hold.get(e.candidate, 999), e.landed_cost))


def max_buy_price(candidate: Candidate, *, target_roi: float = 0.10,
                  sell_through: float = DEFAULT_SELL_THROUGH,
                  fee_rate: float = MARKETPLACE_FEE_RATE,
                  fixed_fee: float = MARKETPLACE_FIXED_FEE) -> float:
    """Highest landed cost that still clears `target_roi` - the trigger price."""
    gross = candidate.ev_box_value * sell_through
    # net = gross - landed - (gross*fee + fixed); roi = net / landed
    # => landed * (1 + target_roi) = gross * (1 - fee) - fixed
    numerator = gross * (1 - fee_rate) - fixed_fee
    return round(numerator / (1 + target_roi), 2)


def buy_order(candidate: Candidate, evaluation: Evaluation, *, balance: float,
              target_roi: float = 0.10) -> str:
    """The markdown a human reads before clicking buy."""
    trigger = max_buy_price(candidate, target_roi=target_roi)
    lines = [
        f"# Buy order - {candidate.name}",
        "",
        f"- **SKU:** {candidate.sku}",
        f"- **Source:** {evaluation.quote_source} @ ${evaluation.price:.2f}"
        f" (landed ${evaluation.landed_cost:.2f})",
        f"- **EV of box:** ${candidate.ev_box_value:.2f}"
        f" (data {candidate.ev_age_days}d old)",
        f"- **Sell-through prior:** {DEFAULT_SELL_THROUGH:.0%}",
        f"- **Gross if it sells:** ${evaluation.gross:.2f}",
        f"- **Fees:** ${evaluation.fees:.2f}",
        f"- **Net:** ${evaluation.net:.2f}   **ROI:** {evaluation.roi:.1%}",
        f"- **Trigger price (ROI >= {target_roi:.0%}):** ${trigger:.2f}",
        f"- **Restock balance:** ${balance:.2f} -> ${balance - evaluation.landed_cost:.2f} after",
        f"- **Expected hold:** {candidate.expected_hold_days} days",
    ]
    if evaluation.flags:
        lines += ["", "**Flags:**"] + [f"- {f}" for f in evaluation.flags]
    lines += [
        "",
        "## Approval",
        "",
        "Nothing is purchased until Chris clicks. This file is the request.",
        "",
        f"_Generated {datetime.now().isoformat(timespec='seconds')}_",
    ]
    return "\n".join(lines) + "\n"


def load_candidates(path: str | Path) -> list[Candidate]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = raw.get("candidates", raw) if isinstance(raw, dict) else raw
    return [Candidate.from_dict(item) for item in items]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", help="JSON file of candidates with quotes")
    parser.add_argument("--balance", type=float, default=0.0, help="restock fund available")
    parser.add_argument("--tax-rate", type=float, default=0.0)
    parser.add_argument("--sell-through", type=float, default=DEFAULT_SELL_THROUGH)
    parser.add_argument("--out", default="data/restock", help="directory for the buy order")
    args = parser.parse_args(argv)

    candidates = load_candidates(args.candidates)
    ranked = rank(candidates, tax_rate=args.tax_rate, sell_through=args.sell_through,
                  restock_balance=args.balance)

    if not ranked:
        print("No buyable candidate this cycle. Reasons:")
        for candidate in candidates:
            for evaluation in evaluate(candidate, tax_rate=args.tax_rate,
                                       sell_through=args.sell_through,
                                       restock_balance=args.balance):
                if evaluation.refused:
                    print(f"  - {candidate.name} ({evaluation.quote_source or 'n/a'}): {evaluation.refused}")
        return 1

    best = ranked[0]
    winner = next(c for c in candidates if c.name == best.candidate)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    order = out_dir / f"{date.today().isoformat()}-{winner.sku.replace('/', '-')}.md"
    order.write_text(buy_order(winner, best, balance=args.balance), encoding="utf-8")

    print(f"Best: {best.candidate} via {best.quote_source} - net ${best.net:.2f}, ROI {best.roi:.1%}")
    print(f"Trigger price at 10% ROI: ${max_buy_price(winner):.2f}")
    print(f"Buy order written to {order} - awaiting approval, nothing purchased.")
    for evaluation in ranked[1:4]:
        print(f"  next: {evaluation.candidate} ({evaluation.quote_source}) ROI {evaluation.roi:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read MTGStocks' published expected value and sealed price for any set.

No browser, no Selenium: the per-set EV pages are server-rendered and parse with
plain HTTP given a normal User-Agent.

Two page formats exist and both are handled:

* **product tree** (newer sets) — a row per product with
  `Expected Avg | Expected Market | Sealed Avg | Sealed Market`.
  This is the useful one: it publishes what the box *costs* next to what its
  contents are *worth*, so the edge is a ratio of two published numbers.
* **rarity tables** (older sets) — `Booster` / `Boosterbox` rows with
  `Low | Average | Market`, plus per-rarity Average/Sum. No sealed price here.

MTGStocks states per set that "Commons are left out of the EV", so no bulk
haircut is applied on top of their figure — that would double-count.

Nothing in this module buys anything. It reports numbers and their source URL.
"""
from __future__ import annotations

import gzip
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any

BASE = "https://www.mtgstocks.com"
INDEX_URL = f"{BASE}/analytics/expectedvalue"
EV_URL = f"{BASE}/sets/expectedvalue/{{set_id}}"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_MONEY = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)")
_TAG = re.compile(r"<[^>]+>")
_ROW = re.compile(r"<tr\b[^>]*mtg-product-tree-node.*?</tr>", re.S)
_SEALED_LINK = re.compile(r'href="(/sealed/[^"]+)"[^>]*>\s*([^<]+?)\s*</a>', re.S)
_TD_RIGHT = re.compile(r"<td\b[^>]*text-right[^>]*>(.*?)</td>", re.S)
_SET_LINK = re.compile(r"/sets/(\d+)-([a-z0-9\-]+)")


class DiscoveryError(RuntimeError):
    """A page could not be read or did not contain the expected tables."""


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    text = raw.decode("utf-8", "replace")
    if not text.strip():
        raise DiscoveryError(f"empty response from {url}")
    return text


def _money(cell: str) -> float | None:
    plain = _TAG.sub(" ", cell)
    m = _MONEY.search(plain)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


@dataclass
class Product:
    """One published row. `expected_*` is contents value, `sealed_*` is price."""
    name: str
    expected_avg: float | None
    expected_market: float | None
    sealed_avg: float | None
    sealed_market: float | None
    url: str = ""

    @property
    def edge(self) -> float | None:
        """Contents value ÷ what the sealed product costs. >1 means upside."""
        if self.expected_market and self.sealed_market and self.sealed_market > 0:
            return self.expected_market / self.sealed_market
        return None

    @property
    def spread(self) -> float | None:
        if self.expected_market is not None and self.sealed_market is not None:
            return self.expected_market - self.sealed_market
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "expected_avg": self.expected_avg,
            "expected_market": self.expected_market,
            "sealed_avg": self.sealed_avg,
            "sealed_market": self.sealed_market,
            "edge": round(self.edge, 4) if self.edge is not None else None,
            "spread": round(self.spread, 2) if self.spread is not None else None,
            "url": self.url,
        }


@dataclass
class SetEV:
    set_id: int
    name: str
    products: list[Product] = field(default_factory=list)
    notes: str = ""
    url: str = ""

    def boxes(self) -> list[Product]:
        """Single booster boxes only — not cases, not individual packs."""
        out = []
        for p in self.products:
            n = p.name.lower()
            if "case" in n:
                continue
            if "box" in n:
                out.append(p)
        return out


def parse_product_tree(html: str) -> list[Product]:
    products: list[Product] = []
    for row in _ROW.findall(html):
        link = _SEALED_LINK.search(row)
        if not link:
            continue
        cells = [_money(c) for c in _TD_RIGHT.findall(row)]
        if len(cells) < 4:
            continue
        products.append(Product(
            name=re.sub(r"\s+", " ", link.group(2)).strip(),
            expected_avg=cells[0], expected_market=cells[1],
            sealed_avg=cells[2], sealed_market=cells[3],
            url=BASE + link.group(1),
        ))
    return products


def parse_rarity_tables(html: str) -> list[Product]:
    """Older layout: a `Boosterbox` row with Low/Average/Market and no sealed price."""
    plain = _TAG.sub("|", html)
    plain = re.sub(r"\|+", "|", plain)
    out: list[Product] = []
    for label in ("Boosterbox", "Booster Box", "Booster"):
        m = re.search(re.escape(label) + r"\|Low\|Average\|Market\|(.{0,200})", plain)
        if not m:
            continue
        vals = _MONEY.findall(m.group(1))
        if len(vals) < 3:
            continue
        low, avg, market = (float(v.replace(",", "")) for v in vals[:3])
        out.append(Product(
            name=label, expected_avg=avg, expected_market=market,
            sealed_avg=None, sealed_market=None,
        ))
        break
    return out


def parse_notes(html: str) -> str:
    plain = re.sub(r"\s+", " ", _TAG.sub(" ", html))
    found = []
    for phrase in ("Commons are left out", "buy-a-box promo", "guaranteed reprint",
                   "guaranteerd reprint", "old frame cards", "Beta Feature"):
        if phrase.lower() in plain.lower():
            found.append(phrase)
    return "; ".join(found)


def read_set(set_id: int, *, html: str | None = None) -> SetEV:
    url = EV_URL.format(set_id=set_id)
    html = html if html is not None else fetch(url)
    title = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    name = re.sub(r"\s+", " ", _TAG.sub(" ", title.group(1))).strip() if title else f"set {set_id}"
    name = name.replace(" - Expected Value", "").strip()
    products = parse_product_tree(html)
    if not products:
        products = parse_rarity_tables(html)
    return SetEV(set_id=set_id, name=name, products=products,
                 notes=parse_notes(html), url=url)


def list_set_ids(*, html: str | None = None) -> list[tuple[int, str]]:
    """Every set the index links to, deduplicated, in page order."""
    html = html if html is not None else fetch(INDEX_URL)
    seen: dict[int, str] = {}
    for sid, slug in _SET_LINK.findall(html):
        seen.setdefault(int(sid), slug)
    return sorted(seen.items())


def scan(set_ids: list[int], *, low: float = 150.0, high: float = 250.0,
         min_edge: float = 1.0, fetcher=fetch) -> dict[str, Any]:
    """Find single booster boxes priced in [low, high] with an edge above min_edge.

    Unreadable sets are reported as errors, never silently dropped.
    """
    hits: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    no_sealed: list[str] = []
    for sid in set_ids:
        try:
            ev = read_set(sid, html=fetcher(EV_URL.format(set_id=sid)))
        except Exception as exc:                     # noqa: BLE001 - reported, not hidden
            errors.append({"set_id": str(sid), "error": str(exc)[:160]})
            continue
        boxes = ev.boxes()
        if not boxes:
            continue
        if all(b.sealed_market is None for b in boxes):
            no_sealed.append(ev.name)
            continue
        for b in boxes:
            if b.sealed_market is None or b.edge is None:
                continue
            if low <= b.sealed_market <= high and b.edge >= min_edge:
                hits.append({"set_id": sid, "set": ev.name, "notes": ev.notes,
                             "source": ev.url, **b.as_dict()})
    hits.sort(key=lambda h: h["edge"], reverse=True)
    return {"candidates": hits, "errors": errors,
            "no_sealed_price": no_sealed,
            "band": [low, high], "min_edge": min_edge}


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import time

    ap = argparse.ArgumentParser(description="Scan MTGStocks for booster boxes worth cracking.")
    ap.add_argument("--low", type=float, default=150.0, help="minimum sealed price")
    ap.add_argument("--high", type=float, default=250.0, help="maximum sealed price")
    ap.add_argument("--min-edge", type=float, default=1.0, help="minimum EV / sealed price")
    ap.add_argument("--delay", type=float, default=0.25, help="seconds between requests")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    ap.add_argument("--sets", type=int, nargs="*", help="only these set ids")
    args = ap.parse_args(argv)

    ids = args.sets if args.sets else [i for i, _ in list_set_ids()]

    def polite(url: str) -> str:
        time.sleep(args.delay)
        return fetch(url)

    out = scan(ids, low=args.low, high=args.high, min_edge=args.min_edge, fetcher=polite)
    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"scanned {len(ids)} sets | {len(out['candidates'])} candidates "
          f"| {len(out['errors'])} unreadable | {len(out['no_sealed_price'])} without a sealed price")
    print(f"{'edge':>6}  {'price':>9}  {'EV':>9}  set")
    for c in out["candidates"]:
        print(f"{c['edge']:6.3f}  ${c['sealed_market']:8.2f}  ${c['expected_market']:8.2f}  "
              f"{c['set']} — {c['name']}")
    if out["errors"]:
        print("\nunreadable sets (reported, not dropped):")
        for e in out["errors"][:10]:
            print(f"  {e['set_id']}: {e['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

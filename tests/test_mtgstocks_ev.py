"""Parser tests against captured MTGStocks pages — no network in the suite."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mtgstocks_ev import (  # noqa: E402
    DiscoveryError, Product, list_set_ids, parse_product_tree,
    parse_rarity_tables, read_set, scan,
)

FIX = pathlib.Path(__file__).parent / "fixtures"


def fixture(name):
    return (FIX / name).read_text()


def test_product_tree_parses_all_four_columns():
    products = parse_product_tree(fixture("ev_110.html"))
    assert len(products) >= 3
    box = next(p for p in products if p.name == "Booster Box")
    assert box.expected_market > 0
    assert box.sealed_market > 0
    # All four columns are parsed independently; MTGStocks does not guarantee
    # an ordering between expected avg and expected market, so none is asserted.
    assert len({box.expected_avg, box.expected_market,
                box.sealed_avg, box.sealed_market}) == 4
    assert box.url.startswith("https://www.mtgstocks.com/sealed/")


def test_edge_is_contents_over_price():
    p = Product("Box", 300.0, 263.16, 180.0, 169.29)
    assert round(p.edge, 3) == 1.554
    assert round(p.spread, 2) == 93.87


def test_edge_is_none_without_a_sealed_price():
    p = Product("Box", 300.0, 263.16, None, None)
    assert p.edge is None and p.spread is None


def test_zero_sealed_price_does_not_divide_by_zero():
    assert Product("Box", 300.0, 263.16, 0.0, 0.0).edge is None


def test_cases_and_packs_are_not_boxes():
    ev = read_set(110, html=fixture("ev_110.html"))
    names = [b.name for b in ev.boxes()]
    assert "Booster Box" in names
    assert not any("case" in n.lower() for n in names)
    assert not any("pack" in n.lower() for n in names)


def test_old_format_parses_without_a_sealed_price():
    ev = read_set(359, html=fixture("ev_359.html"))
    assert ev.products, "rarity-table layout must still yield a row"
    box = ev.products[0]
    assert box.expected_market > 0
    assert box.sealed_market is None      # old layout publishes no sealed price
    assert box.edge is None


def test_notes_are_captured():
    ev = read_set(359, html=fixture("ev_359.html"))
    assert "Commons are left out" in ev.notes


def test_set_name_is_cleaned():
    ev = read_set(110, html=fixture("ev_110.html"))
    assert ev.name == "Gatecrash"
    assert "Expected Value" not in ev.name


def test_index_enumerates_sets_without_duplicates():
    ids = list_set_ids(html=fixture("index.html"))
    assert len(ids) > 50
    assert len({i for i, _ in ids}) == len(ids)
    assert all(isinstance(i, int) for i, _ in ids)


def test_scan_filters_by_band_and_edge():
    pages = {110: fixture("ev_110.html"), 359: fixture("ev_359.html")}

    def fetcher(url):
        sid = int(url.rstrip("/").split("/")[-1])
        return pages[sid]

    out = scan([110, 359], low=150.0, high=250.0, min_edge=1.0, fetcher=fetcher)
    assert out["errors"] == []
    assert any(c["set"] == "Gatecrash" for c in out["candidates"])
    # old-format set has no sealed price: reported, never silently dropped
    assert "Time Spiral: Remastered" in out["no_sealed_price"]


def test_scan_excludes_out_of_band_boxes():
    pages = {110: fixture("ev_110.html")}
    out = scan([110], low=1000.0, high=2000.0,
               fetcher=lambda u: pages[110])
    assert out["candidates"] == []


def test_scan_reports_unreadable_sets():
    def boom(url):
        raise DiscoveryError("empty response")

    out = scan([999], fetcher=boom)
    assert out["candidates"] == []
    assert out["errors"] and out["errors"][0]["set_id"] == "999"


def test_scan_ranks_by_edge_descending():
    pages = {110: fixture("ev_110.html")}
    out = scan([110], low=0.0, high=10000.0, min_edge=0.0,
               fetcher=lambda u: pages[110])
    edges = [c["edge"] for c in out["candidates"]]
    assert edges == sorted(edges, reverse=True)


def test_every_candidate_carries_its_source():
    out = scan([110], low=0.0, high=10000.0, min_edge=0.0,
               fetcher=lambda u: fixture("ev_110.html"))
    for c in out["candidates"]:
        assert c["source"].startswith("https://www.mtgstocks.com/sets/expectedvalue/")
        assert c["url"].startswith("https://www.mtgstocks.com/sealed/")


def test_non_money_cells_are_ignored():
    from mtgstocks_ev import _money
    assert _money("<td>N/A</td>") is None
    assert _money("<td> $1,234.56 </td>") == 1234.56


def test_row_with_too_few_columns_is_skipped():
    html = ('<tr mtg-product-tree-node><td><a href="/sealed/1-x"> Box </a></td>'
            '<td class="text-right">$10.00</td></tr>')
    assert parse_product_tree(html) == []

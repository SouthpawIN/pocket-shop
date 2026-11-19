# Shipping: what the market actually charges

Checked against TCGplayer's own help pages. Figures below are quoted, not
estimated, and each carries its source so a later change can be re-verified.

## TCGplayer marketplace (seller-fulfilled)

| Order value | Shipping the buyer pays |
|---|---|
| under $5.00 | **$1.49 minimum**, or the seller's own rate if higher |
| $5.00 and above | the seller's own rate — **Level 4 sellers may set $0** |

- The minimum is a floor TCGplayer imposes, not a suggestion: a seller who sets
  $0 still charges the buyer $1.49 on a sub-$5 order.
- "Free shipping on orders over $5" is a common Level 4 setting, so a $5+ card
  frequently ships free from competing sellers.
- **One shipping fee per seller per order**, not per card. Adding a second card
  from the same seller shows "Shipping: Included".
- Change log on that page: `5/26/26 - Updated Minimum Shipping fee`. An older
  cached copy of the same page says $1.31; $1.49 is current.

Source: <https://help.tcgplayer.com/hc/en-us/articles/23216633721495-Understanding-Shipping-Rates-in-Different-Situations>

## TCGplayer Direct (TCGplayer-fulfilled)

| Order value | Shipping |
|---|---|
| under $50 | **$3.99** standard, tracked |
| $50 and over | **free**, US only |
| international | flat **from $7.99**, tracked, no free tier |

Direct also rounds any card valued under $0.40 up to a **$0.40 price floor**.

Source: <https://help.tcgplayer.com/hc/en-us/articles/201996857-Buying-from-TCGplayer-Direct>

## What this means for a $1.99 shipping charge

$1.99 is **above** the market norm for cheap cards, not below it. The nearest
thing to a $9.99 figure anywhere in these pages is international Direct from
$7.99 — there is no $9.99 domestic tier.

Net per card at a $0.40 actual shipping cost, 13.25% + $0.30 fees:

| Card price | charge $1.99 | charge $1.49 | charge $0.99 | free |
|---|---|---|---|---|
| $0.50 | $1.46 | $1.03 | $0.59 | **−$0.27** |
| $1.00 | $1.89 | $1.46 | $1.03 | $0.17 |
| $2.00 | $2.76 | $2.33 | $1.89 | $1.04 |
| $5.00 | $5.36 | $4.93 | $4.50 | $3.64 |
| $10.00 | $9.70 | $9.27 | $8.83 | $7.97 |
| $20.00 | $18.38 | $17.94 | $17.51 | $16.65 |

Shipping contribution per order, after the fee taken on the shipping charged:

| Charged | Contribution | Break-even item price |
|---|---|---|
| $1.99 | $1.326 | −$1.18 |
| $1.49 | $0.893 | −$0.68 |
| $0.99 | $0.459 | −$0.18 |
| free | **−$0.400** | **$0.81** |

## The trade-off, stated plainly

Charging $1.99 earns $1.33 per order but is the least competitive option on a
cheap card, where rivals ship free above $5 and the platform floor is $1.49.
Shipping free costs $0.40 per order and means **any card under $0.81 loses
money** — so free shipping only works above that price, or on multi-card orders
where one $0.40 covers several cards.

The honest reading: the shipping margin is real but it is not free money. It is
paid for in conversion. A listing that ships free at $5 will sell faster than
one charging $1.99 on a $2 card, and unsold inventory earns nothing.

**Not yet measured:** the actual per-order cost. $0.40 is the operator's
estimate. Weigh and post a few real orders — envelope, postage, two bulk cards —
and replace `DEFAULT_SHIPPING_COST`. Every figure above moves with it.

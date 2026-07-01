---
name: stripe-payments
description: "Purchase supplies via Stripe Link CLI — agent-initiated payments with human approval"
trigger_conditions:
  - "Agent needs to purchase card sleeves, shipping supplies, or inventory"
  - "Restock fund has enough capital for supplies"
  - "User requests supply purchase"
tools_required:
  - "terminal"
  - "read_file"
---

# Stripe Payments Skill

## Overview

Uses **Stripe Link CLI** to let the Pocket Shop agent purchase supplies autonomously.
Every spend requires human approval in the Stripe Link mobile app — the agent cannot
self-approve. Budget limits are enforced in code.

## Hackathon Integration

This satisfies the **Stripe** requirement of the Hermes Agent Accelerated Business
Hackathon (Nous Research × NVIDIA × Stripe).

## Prerequisites

```bash
# Install Stripe Link CLI (Linux/macOS only, US-only)
npm install -g @stripe/link-cli

# Authenticate
link-cli auth login --client-name "Pocket-Shop"
# → Opens browser, sign in to Link, grant spend permissions
```

## Configuration

In `config.yaml`:

```yaml
stripe:
  enabled: true
  link_client_name: "Pocket-Shop"
  max_purchase_amount: 5000       # $50.00 per transaction
  daily_spend_limit: 20000        # $200.00 per day
  require_approval: true          # ALWAYS require Link app approval
```

## Step-by-Step Workflow

### 1. Check Auth Status

```python
from stripe_payments import check_auth_status

auth = check_auth_status()
if not auth.get("success"):
    print("Not authenticated. Run: link-cli auth login --client-name 'Pocket-Shop'")
```

### 2. List Available Payment Methods

```python
from stripe_payments import list_payment_methods

methods = list_payment_methods()
# Returns: {"success": True, "data": [{"id": "pm_...", ...}]}
```

### 3. Create a Spend Request

```python
from stripe_payments import create_spend_request

result = create_spend_request(
    amount_cents=1299,           # $12.99
    merchant_name="Game Night",
    merchant_url="https://gamenight.com",
    payment_method_id="pm_12345",
    line_item_desc="100 penny card sleeves",
)
# → Link app sends push notification for approval
# → Returns: {"success": True, "data": {"id": "lsrq_..."}}
```

### 4. Retrieve Credential (After Approval)

```python
from stripe_payments import retrieve_credential, cleanup_card_file

# Get virtual card details (written to temp file, NEVER printed)
cred = retrieve_credential("lsrq_12345", "/tmp/pocket-shop-card.json")

# Use the card file for checkout...

# ALWAYS clean up after
cleanup_card_file("/tmp/pocket-shop-card.json")
```

### 5. High-Level Purchase Flow

```python
from stripe_payments import purchase_supplies

result = purchase_supplies(
    item_name="100 penny sleeves",
    amount_usd=12.99,
    merchant_name="Game Night",
    merchant_url="https://gamenight.com",
)
# Handles: auth check → method selection → spend request → approval wait
```

## Budget Enforcement

- **Per-transaction max**: `$50.00` (5000 cents) — configurable
- **Daily spend limit**: `$200.00` (20000 cents) — configurable
- **Approval required**: Always `True` — agent cannot self-approve

## Security Rules

1. **Card PAN never printed** — credential goes to temp file with 0600 perms
2. **Temp file cleaned up** after every purchase
3. **Budget limits enforced** before creating spend request
4. **Human approval required** for every single transaction

## CLI Usage

```bash
# Check auth
python main.py stripe-status

# Purchase supplies
python main.py purchase "100 sleeves" 12.99 "Game Night" "https://gamenight.com"
```

## Verification Steps

1. `link-cli auth status` returns authenticated
2. `list_payment_methods()` returns at least one method
3. Spend request created with correct amount and merchant
4. Link app shows approval notification
5. Credential file exists after approval
6. Credential file deleted after use

## Pitfalls

- **US-only**: Stripe Link requires US bank account
- **No Windows**: Link CLI doesn't support Windows
- **Merchant blocks**: Some merchants block automated checkout
- **Approval timeout**: Link app approval expires after ~5 minutes

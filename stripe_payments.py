"""
Stripe Payments Integration for Pocket Shop
============================================

Integrates with Hermes Agent via:
  1. Stripe Link CLI — agent can purchase supplies (card sleeves, shipping, etc.)
  2. Stripe Projects — provision infrastructure (database, hosting, billing)

Hermes Skill: optional-skills/payments/stripe-link-cli
Requires: npm install -g @stripe/link-cli
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_config import get_config


def _run_link_cli(args: List[str], timeout: int = 60) -> Dict:
    """Run a link-cli command and return parsed result."""
    cmd = ["link-cli"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout.strip()

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr.strip() or output[:300],
                "exit_code": result.returncode,
            }

        # Try JSON parse
        if output.startswith("{") or output.startswith("["):
            try:
                return {"success": True, "data": json.loads(output)}
            except json.JSONDecodeError:
                pass

        return {"success": True, "output": output}

    except FileNotFoundError:
        return {"success": False, "error": "link-cli not found. Install: npm install -g @stripe/link-cli"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_auth_status() -> Dict:
    """Check if Stripe Link CLI is authenticated."""
    return _run_link_cli(["auth", "status", "--format", "json"])


def login(client_name: str = "Pocket-Shop", timeout: int = 300) -> Dict:
    """Authenticate with Stripe Link via in-browser flow."""
    return _run_link_cli(
        ["auth", "login", "--client-name", client_name, "--interval", "5", "--timeout", str(timeout)],
        timeout=timeout + 30,
    )


def list_payment_methods() -> Dict:
    """List available Link payment methods."""
    return _run_link_cli(["payment-methods", "list", "--format", "json"])


def list_shipping_addresses() -> Dict:
    """List available shipping addresses."""
    return _run_link_cli(["shipping-address", "list", "--format", "json"])


def create_spend_request(
    amount_cents: int,
    merchant_name: str,
    merchant_url: str,
    payment_method_id: str,
    line_item_desc: str,
    approval_required: bool = True,
) -> Dict:
    """
    Create a Stripe Link spend request.

    Args:
        amount_cents: Total amount in cents (e.g., 5000 = $50.00)
        merchant_name: Name of the merchant
        merchant_url: Merchant website URL
        payment_method_id: ID from list_payment_methods()
        line_item_desc: Description of what's being purchased
        approval_required: Require Link app approval (always True for safety)
    """
    config = get_config()
    stripe_cfg = config.get("stripe", {})
    max_amount = stripe_cfg.get("max_purchase_amount", 5000)

    if amount_cents > max_amount:
        return {
            "success": False,
            "error": f"Amount ${amount_cents/100:.2f} exceeds max ${max_amount/100:.2f}",
        }

    args = [
        "spend-request", "create",
        "--payment-method-id", payment_method_id,
        "--merchant-name", merchant_name,
        "--merchant-url", merchant_url,
        "--context", f"Pocket Shop purchase: {line_item_desc}",
        "--amount", str(amount_cents),
        "--line-item", f"name:{line_item_desc},unit_amount:{amount_cents},quantity:1",
        "--total", f"type:total,display_text:Total,amount:{amount_cents}",
        "--format", "json",
    ]
    if approval_required:
        args.append("--request-approval")

    return _run_link_cli(args, timeout=120)


def retrieve_credential(spend_request_id: str, output_file: str = "/tmp/pocket-shop-card.json") -> Dict:
    """Securely retrieve payment credential. Card PAN goes to file only."""
    return _run_link_cli([
        "spend-request", "retrieve", spend_request_id,
        "--include", "card",
        "--output-file", output_file,
        "--format", "json",
    ])


def cleanup_card_file(output_file: str = "/tmp/pocket-shop-card.json"):
    """Remove card credential file after use."""
    try:
        Path(output_file).unlink(missing_ok=True)
    except Exception:
        pass


def purchase_supplies(
    item_name: str,
    amount_usd: float,
    merchant_name: str,
    merchant_url: str,
) -> Dict:
    """
    High-level: purchase supplies using Stripe Link.

    Checks auth → selects payment method → creates spend request →
    waits for Link app approval → returns credential file path.

    Args:
        item_name: What is being purchased (e.g., "100 card sleeves")
        amount_usd: Price in USD (e.g., 12.99)
        merchant_name: Merchant name
        merchant_url: Merchant URL
    """
    # 1. Check auth
    auth = check_auth_status()
    if not auth.get("success"):
        return {"success": False, "error": "Not authenticated with Link. Run: login()"}

    # 2. Get payment methods
    methods = list_payment_methods()
    if not methods.get("success") or not methods.get("data"):
        return {"success": False, "error": "No payment methods found"}

    pm_id = methods["data"][0].get("id", "") if isinstance(methods.get("data"), list) else ""
    if not pm_id:
        return {"success": False, "error": "Could not extract payment method ID"}

    # 3. Create spend request
    amount_cents = int(amount_usd * 100)
    sr = create_spend_request(
        amount_cents=amount_cents,
        merchant_name=merchant_name,
        merchant_url=merchant_url,
        payment_method_id=pm_id,
        line_item_desc=item_name,
    )

    return sr


def get_daily_spend_summary() -> Dict:
    """Check how much has been spent today via Link."""
    return _run_link_cli(["spend-request", "list", "--format", "json"])


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python stripe_payments.py [status|login|methods|purchase]")
        sys.exit(0)

    action = sys.argv[1]
    if action == "status":
        print(json.dumps(check_auth_status(), indent=2))
    elif action == "login":
        print(json.dumps(login(), indent=2))
    elif action == "methods":
        print(json.dumps(list_payment_methods(), indent=2))
    elif action == "purchase":
        if len(sys.argv) < 5:
            print("Usage: purchase <item_name> <amount_usd> <merchant_name> <merchant_url>")
        else:
            result = purchase_supplies(sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5])
            print(json.dumps(result, indent=2))
    else:
        print(f"Unknown action: {action}")

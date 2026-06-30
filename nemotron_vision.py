"""
NVIDIA Nemotron 3 Ultra Vision Module for Card Identification
=============================================================

Uses Nemotron 3 Ultra (550B, 55B active MoE) via OpenAI-compatible API.
Falls back to other vision providers if Nemotron is unavailable.

Supported backends:
  - NVIDIA Nemotron 3 Ultra (local or hosted)
  - Qwen-Omni (local)
  - OpenRouter (various vision models)
"""

import base64
import json
import os
import re
from pathlib import Path
from typing import Dict, Optional

import requests

from hermes_config import get_config

VISION_PROMPT = """Identify this Magic: The Gathering trading card. Provide exact details:

1. Card name (exact name as printed on card)
2. Set name and set code (e.g., "Duskmourn: House of Horror [dsk]")
3. Card number if visible
4. Condition assessment: Mint, Near Mint, Excellent, Good, Lightly Played, Heavily Played, or Damaged
5. Whether it's foil, stamped, or has any special variants
6. Confidence level (0.0 to 1.0)

Format your response as a valid JSON object with these exact keys:
{"name", "set_name", "set_code", "card_number", "condition", "is_foil", "has_stamp", "confidence"}

Do not include markdown formatting or code blocks - just raw JSON."""


def encode_image(image_path: str) -> str:
    """Read and base64 encode an image file."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_vision_api(base_url: str, model: str, image_b64: str, api_key: str = "") -> Dict:
    """Make a vision API call in OpenAI-compatible format."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                    {"type": "text", "text": VISION_PROMPT},
                ],
            }
        ],
        "max_tokens": 400,
        "temperature": 0.1,
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"{base_url.rstrip('/')}/chat/completions"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        return {"success": False, "error": f"HTTP {response.status_code}", "body": response.text[:500]}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection refused"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_vision_response(response_json: dict) -> Dict:
    """Extract structured card data from a vision API response."""
    choices = response_json.get("choices", [])
    if not choices:
        return {"error": "No choices in response"}
    content = choices[0].get("message", {}).get("content", "")

    # Try regex extraction of JSON object
    json_match = re.search(r'\{[^{}]*"name"[^{}]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Try full content as JSON
    try:
        return json.loads(content.strip())
    except (json.JSONDecodeError, ValueError):
        pass

    return {"error": "Failed to parse vision response", "raw": content[:200]}


def identify_card(image_path: str, provider: Optional[str] = None) -> Dict:
    """
    Identify an MTG card from an image file.

    Tries providers in order: Nemotron 3 Ultra → Qwen-Omni → OpenRouter.

    Args:
        image_path: Path to the card image
        provider: Force a specific provider ('nemotron', 'qwen_omni', 'openrouter')

    Returns:
        Dict with card identification or error info.
    """
    if not Path(image_path).exists():
        return {"error": f"Image not found: {image_path}"}

    image_b64 = encode_image(image_path)
    config = get_config()
    vision_config = config.get("vision", {})

    # Build provider chain
    if provider:
        providers = [provider]
    else:
        providers = [vision_config.get("provider", "nemotron"), "qwen_omni", "openrouter"]

    # De-duplicate while preserving order
    seen = set()
    ordered = []
    for p in providers:
        if p not in seen:
            seen.add(p)
            ordered.append(p)

    for prov in ordered:
        print(f"  Trying {prov}...")
        try:
            if prov == "nemotron":
                nc = vision_config.get("nemotron", {})
                result = _call_vision_api(
                    base_url=nc.get("base_url", "http://localhost:8101/v1"),
                    model=nc.get("model", "nvidia/nemotron-3-ultra"),
                    image_b64=image_b64,
                    api_key=nc.get("api_key", ""),
                )
            elif prov == "qwen_omni":
                qc = vision_config.get("qwen_omni", {})
                result = _call_vision_api(
                    base_url=qc.get("base_url", "http://localhost:8101/v1"),
                    model=qc.get("model", "qwen-omni"),
                    image_b64=image_b64,
                )
            elif prov == "openrouter":
                orc = vision_config.get("openrouter", {})
                api_key = orc.get("api_key", "") or os.environ.get("OPENROUTER_API_KEY", "")
                if not api_key:
                    print(f"  {prov}: no API key configured, skipping")
                    continue
                result = _call_vision_api(
                    base_url="https://openrouter.ai/api/v1",
                    model=orc.get("model", "anthropic/claude-sonnet-4"),
                    image_b64=image_b64,
                    api_key=api_key,
                )
            else:
                print(f"  Unknown provider: {prov}")
                continue

            if result.get("success"):
                card = parse_vision_response(result["data"])
                if card and "error" not in card:
                    print(f"  ✓ Identified via {prov}: {card.get('name', 'Unknown')}")
                    card["provider_used"] = prov
                    return card
                else:
                    print(f"  {prov}: parse failed — {card.get('error', 'unknown')}")
            else:
                print(f"  {prov}: {result.get('error', 'failed')}")

        except Exception as e:
            print(f"  {prov}: exception — {e}")

    return {"error": "All vision providers failed"}


def scan_card_from_phone(device_ip: str, output_dir: str = "/tmp/cards") -> Dict:
    """
    Capture a card image from an Android phone via ADB over Tailscale,
    then identify it using the vision chain.

    Args:
        device_ip: Tailscale IP:port of the device (e.g. '100.79.15.54:5555')
        output_dir: Directory to save captured images

    Returns:
        Dict with identification result or error.
    """
    import subprocess
    import time

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    image_path = str(out / f"card_{timestamp}.jpg")

    try:
        # Pull latest camera image from phone
        result = subprocess.run(
            ["adb", "-s", f"{device_ip}", "pull",
             "/sdcard/DCIM/Camera/latest.jpg", image_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"error": f"ADB pull failed: {result.stderr[:200]}"}
    except FileNotFoundError:
        return {"error": "adb not found in PATH"}
    except subprocess.TimeoutExpired:
        return {"error": "ADB pull timed out"}

    return identify_card(image_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        result = identify_card(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python nemotron_vision.py <image_path>")

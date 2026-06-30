"""
Centralized configuration loader for Pocket Shop.
Loads config.yaml, provides safe defaults, and handles missing files gracefully.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import os

try:
    import yaml
except ImportError:
    yaml = None


def get_config_dir() -> Path:
    """Get the config directory (project root)."""
    return Path(__file__).parent


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from config.yaml.

    Returns a dict with safe defaults if the file doesn't exist.
    """
    if config_path is None:
        config_path = get_config_dir() / "config.yaml"

    defaults = {
        "financial": {
            "restock_target": 500.00,
            "ev_threshold": 10.0,
            "split": {"savings": 0.30, "profit": 0.30, "restock": 0.40},
        },
        "gmail": {"email": "", "app_password": ""},
        "ebay": {"mode": "api", "marketplace": "EBAY_US"},
        "scryfall": {"user_agent": "Pocket-Shop/2.0 (automated-mtg-trading)"},
        "vision": {
            "provider": "nemotron",
            "nemotron": {
                "base_url": "http://localhost:8101/v1",
                "model": "nvidia/nemotron-3-ultra",
                "api_key": "",
            },
            "qwen_omni": {
                "base_url": "http://localhost:8101/v1",
                "model": "qwen-omni",
            },
            "openrouter": {
                "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
                "model": "anthropic/claude-sonnet-4",
            },
        },
        "stripe": {
            "enabled": False,
            "link_client_name": "Pocket-Shop",
            "max_purchase_amount": 5000,
            "daily_spend_limit": 20000,
            "require_approval": True,
        },
    }

    if config_path.exists() and yaml is not None:
        try:
            with open(config_path) as f:
                user_config = yaml.safe_load(f) or {}
            # Deep merge
            for key, value in user_config.items():
                if isinstance(value, dict) and isinstance(defaults.get(key), dict):
                    defaults[key].update(value)
                else:
                    defaults[key] = value
        except Exception:
            pass

    return defaults


# Module-level config instance
_config: Optional[Dict[str, Any]] = None


def get_config() -> Dict[str, Any]:
    """Get the singleton config, loading on first access."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Force reload the config."""
    global _config
    _config = load_config(config_path)
    return _config

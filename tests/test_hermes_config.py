"""Tests for hermes_config module."""
import pytest
import tempfile
from pathlib import Path
import yaml

import hermes_config


class TestLoadConfig:
    """Tests for load_config()."""

    def test_returns_defaults_when_no_file(self, tmp_path):
        """Config should return sensible defaults if config.yaml doesn't exist."""
        cfg = hermes_config.load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(cfg, dict)
        assert cfg["financial"]["restock_target"] == 500.00
        assert cfg["financial"]["ev_threshold"] == 10.0
        assert cfg["stripe"]["enabled"] is False
        assert cfg["vision"]["provider"] == "nemotron"

    def test_loads_yaml_file(self, tmp_path):
        """Config should merge user values over defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "financial": {"restock_target": 1000.00, "ev_threshold": 15.0},
            "stripe": {"enabled": True, "link_client_name": "TestBot"},
        }))
        cfg = hermes_config.load_config(config_file)
        assert cfg["financial"]["restock_target"] == 1000.00
        assert cfg["financial"]["ev_threshold"] == 15.0
        assert cfg["stripe"]["enabled"] is True
        assert cfg["stripe"]["link_client_name"] == "TestBot"
        # Defaults still present
        assert cfg["stripe"]["max_purchase_amount"] == 5000

    def test_handles_malformed_yaml(self, tmp_path):
        """Config should fall back to defaults on malformed YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{{{{not: yaml: [")
        cfg = hermes_config.load_config(config_file)
        assert cfg["financial"]["restock_target"] == 500.00


class TestGetConfig:
    """Tests for the singleton get_config()."""

    def test_returns_dict(self):
        cfg = hermes_config.get_config()
        assert isinstance(cfg, dict)
        assert "financial" in cfg

    def test_reload_config(self, tmp_path):
        """reload_config should return fresh config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"financial": {"ev_threshold": 99.0}}))
        cfg = hermes_config.reload_config(config_file)
        assert cfg["financial"]["ev_threshold"] == 99.0

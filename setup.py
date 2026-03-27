#!/usr/bin/env python3
"""Pocket Shop Setup Script

This script helps you configure all required credentials and settings.
Credentials are stored locally - NEVER pushed to GitHub.
"""

import os
import json
from pathlib import Path

CONFIG_PATH = Path("config.yaml")
ENV_PATH = Path(".env")

def get_input(prompt, default=None, secret=False):
    """Get user input with optional default."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default

def main():
    print("="*60)
    print("POCKET SHOP SETUP")
    print("="*60)
    print("\nThis script will help you configure all required credentials.")
    print("Credentials are stored locally - NEVER shared or pushed to GitHub.")
    print("\n" + "="*60)
    
    # Financial settings
    print("\n[FINANCIAL SETTINGS]")
    restock_target = get_input("Restock fund target ($)", "500.00")
    ev_threshold = get_input("Minimum EV threshold (%)", "10.0")
    
    # Gmail settings for sales monitoring
    print("\n[GMAIL SETTINGS - For Sales Monitoring]")
    print("You'll need a Gmail App Password:")
    print("1. Go to: https://myaccount.google.com/security")
    print("2. Enable 2-Step Verification if not already enabled")
    print("3. Go to: https://myaccount.google.com/apppasswords")
    print("4. Create app password for 'Mail' on 'Other (Custom name)'")
    print("5. Copy the 16-character password")
    
    gmail_email = get_input("Gmail address (for sale notifications)")
    gmail_app_password = get_input("Gmail App Password", secret=True)
    
    # eBay settings
    print("\n[EBAY SETTINGS - For Creating Listings]")
    print("\nOption A: Browser Automation (No API keys needed - DEFAULT)")
    print("Option B: eBay API (Faster, requires developer account)")
    
    ebay_mode = get_input("Choose option (A or B)", "A").upper()
    
    if ebay_mode == "B":
        print("\nTo get eBay API credentials:")
        print("1. Go to: https://developer.ebay.com/")
        print("2. Sign up for a developer account (free)")
        print("3. Create an application in the Developer Portal")
        print("4. Get your credentials from the application dashboard")
        print("\nYou'll need:")
        print("- Developer ID")
        print("- Certificate ID") 
        print("- RuName (App ID)")
        print("- Refresh Token (generated after OAuth flow)")
        
        ebay_developer_id = get_input("eBay Developer ID")
        ebay_cert_id = get_input("eBay Certificate ID")
        ebay_app_id = get_input("eBay RuName/App ID")
        ebay_refresh_token = get_input("eBay Refresh Token")
    
    # TCGPlayer settings (optional - API key for faster lookups)
    print("\n[TCGPLAYER SETTINGS - Optional]")
    print("Browser automation works without an API key.")
    print("API key enables faster programmatic access.")
    print("Get key at: https://www.tcgplayer.com/product/api")
    
    tcgplayer_api_key = get_input("TCGPlayer API Key (optional)")
    
    # Save configuration
    config = {
        "financial": {
            "restock_target": float(restock_target),
            "ev_threshold": float(ev_threshold)
        },
        "gmail": {
            "email": gmail_email,
            "app_password": gmail_app_password if gmail_app_password else "CHANGE_ME"
        },
        "ebay": {
            "mode": "api" if ebay_mode == "B" else "browser",
        }
    }
    
    if ebay_mode == "B":
        config["ebay"]["developer_id"] = ebay_developer_id
        config["ebay"]["cert_id"] = ebay_cert_id
        config["ebay"]["app_id"] = ebay_app_id
        config["ebay"]["refresh_token"] = ebay_refresh_token
    
    if tcgplayer_api_key:
        config["tcgplayer"] = {"api_key": tcgplayer_api_key}
    
    # Save as YAML
    try:
        import yaml
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"\nConfiguration saved to: {CONFIG_PATH}")
    except ImportError:
        # Fallback to JSON if PyYAML not installed
        with open(CONFIG_PATH.with_suffix('.json'), "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nConfiguration saved to: {CONFIG_PATH.with_suffix('.json')}")
    
    # Create .gitignore if it doesn't exist
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        with open(gitignore_path, "w") as f:
            f.write("""# Credentials and configuration
config.yaml
config.json
.env

# Data files
data/
*.json

# Python
__pycache__/
*.pyc
*.pyo
.DS_Store
""")
        print(f"Created: .gitignore")
    
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Test the system: python main_loop.py")
    print("\nFor browser automation to work, you may need:")
    print("  - Chrome/Chromium browser installed")
    print("  - chromedriver (usually auto-downloaded)")

if __name__ == "__main__":
    main()

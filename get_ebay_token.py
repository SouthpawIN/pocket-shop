#!/usr/bin/env python3
"""
eBay OAuth Token Helper - One-Click Refresh Token Generator
===========================================================

This script automates getting an eBay OAuth refresh token:
1. Starts a local web server
2. Opens your browser to eBay's OAuth page
3. You log in and grant consent (once)
4. eBay redirects back with authorization code
5. We exchange it for access + refresh tokens
6. Automatically saves refresh token to config.yaml

Run this ONCE, then you're set forever (tokens last ~18 months).
"""

import http.server
import socketserver
import webbrowser
import urllib.parse
import requests
import threading
import time
from pathlib import Path

### LOAD CREDENTIALS FROM CONFIG ###

try:
    import yaml
except ImportError:
    print("Error: pyyaml not installed. Run: pip install pyyaml")
    exit(1)

CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_ebay_creds():
    """Load eBay credentials from config.yaml."""
    if not CONFIG_PATH.exists():
        print("\u274c config.yaml not found!")
        print("   Copy config.example.yaml to config.yaml and fill in your values.")
        exit(1)
    
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    
    return {
        'dev_id': config.get('ebay_developer_id'),
        'cert_id': config.get('ebay_cert_id'),
        'app_id': config.get('ebay_app_id')
    }

creds = load_ebay_creds()

### OAUTH CONFIGURATION ###

AUTH_URL = "https://www.ebay.com/epi/auth"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth/token"
LOCAL_PORT = 8089
REDIRECT_URI = f"http://localhost:{LOCAL_PORT}/callback"

SCOPES = [
    "https://api.ebay.com/sell.listings",
    "https://api.ebay.com/sell.orders",
    "https://api.ebay.com/sell.transactions"
]

class TokenCaptureHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/callback"):
            query_string = self.path.split("?")[1] if "?" in self.path else ""
            params = urllib.parse.parse_qs(query_string)
            
            code = params.get("code", [None])[0]
            error = params.get("error", [None])[0]
            
            if error:
                print(f"\n\u274c OAuth Error: {error}")
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h1>\u274c Error: {error}</h1>".encode())
                return
            
            if code:
                print(f"\n\u2705 Authorization code received!")
                print(f"   Exchanging for tokens...")
                
                tokens = exchange_code_for_token(code)
                
                if tokens:
                    save_refresh_token(tokens.get('refresh_token'))
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    msg = f"<h1>\u2705 Success!</h1><p>Refresh token saved to config.yaml</p>"
                    self.wfile.write(msg.encode())
                else:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h1>\u274c Failed to get token</h1>")
            else:
                self.send_error_page("No authorization code")
        elif self.path == "/":
            auth_url = build_authorization_url()
            print(f"\n\ud83d\udccd Redirecting to eBay OAuth...")
            self.send_response(302)
            self.send_header("Location", auth_url)
            self.end_headers()
        else:
            self.send_error_page("Not found")
    
    def send_error_page(self, message):
        html = f"<html><body style='padding:40px;text-align:center'><h1>\u274c {message}</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        pass

def build_authorization_url():
    scope = "%20".join(SCOPES)
    params = {
        "client_id": creds['app_id'],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": scope,
        "state": "pocket-shop-oauth"
    }
    return f"{AUTH_URL}?{"&".join(f"{k}={v}" for k, v in params.items())}"

def exchange_code_for_token(auth_code):
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": creds['app_id'],
        "client_secret": creds['cert_id']
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        response = requests.post(TOKEN_URL, data=data, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"\u274c Token exchange failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"\u274c Error: {e}")
        return None

def save_refresh_token(refresh_token):
    config_path = Path("~/projects/pocket-shop/config.yaml").expanduser()
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        import re
        if "ebay_refresh_token:" in content:
            content = re.sub(
                r'ebay_refresh_token:\s*"[^"]*"',
                f'ebay_refresh_token: "{refresh_token}"',
                content
            )
        else:
            content = content.replace(
                'ebay_cert_id:',
                f'ebay_cert_id:\n  ebay_refresh_token: "{refresh_token}"'
            )
        
        with open(config_path, 'w') as f:
            f.write(content)
        
        print(f"\n\u2705 Refresh token saved to {config_path}")
        return True
    except Exception as e:
        print(f"\u274c Error saving config: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  EBAY OAUTH TOKEN HELPER")
    print("  Get your refresh token in one click!")
    print("="*60)
    print()
    print("\ud83d\udccb What will happen:")
    print("   1. Your browser will open to eBay OAuth page")
    print("   2. Log in with your eBay account")
    print("   3. Grant consent for PocketShop app")
    print("   4. Refresh token will be auto-saved to config.yaml")
    print()
    print("\u23f1\ufe0f  This only needs to be done ONCE (tokens last ~18 months)")
    print()
    input("Press Enter to start...")
    
    print(f"\n\ud83d\ude80 Starting local server on port {LOCAL_PORT}...")
    
    with socketserver.TCPServer(("", LOCAL_PORT), TokenCaptureHandler) as httpd:
        def open_browser():
            time.sleep(0.5)
            auth_url = build_authorization_url()
            print(f"\ud83d\udcf1 Opening browser...")
            webbrowser.open(auth_url)
        
        threading.Thread(target=open_browser).start()
        
        print("\n\u23f3 Waiting for OAuth callback...")
        print("   (Complete the login in your browser)")
        print()
        
        try:
            httpd.handle_request()
        except KeyboardInterrupt:
            print("\n\u274c Cancelled")
            return
    
    print("\n\u2705 OAuth flow complete!")

if __name__ == "__main__":
    main()

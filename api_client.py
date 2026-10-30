import ssl
import socket
import http.client
import json
import requests
import logging
from config import SELLER_KEY, API_BASE_URL, API_HOST, CF_EDGE_IP, DEFAULT_PRODUCT

class AuthZenAPI:
    def __init__(self, seller_key=None, host=None, edge_ip=None):
        self.seller_key = seller_key or SELLER_KEY
        self.host = host or API_HOST
        self.edge_ip = edge_ip or CF_EDGE_IP
        self.default_product = DEFAULT_PRODUCT
        self.headers = {
            "X-Seller-Key": self.seller_key,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AuthZenBot/2.0"
        }

    def _post_request(self, endpoint_php: str, payload: dict) -> dict:
        """
        Sends POST request to the license API.
        1. Attempts direct HTTPS request to https://protal.authzen.site/api/v1/licenses/<endpoint_php>
        2. Fallbacks to direct Cloudflare IP + SNI if DNS fails due to registrar client hold.
        """
        url = f"https://{self.host}/api/v1/licenses/{endpoint_php}"
        
        # 1. Standard HTTPS request
        try:
            res = requests.post(url, json=payload, headers=self.headers, timeout=8)
            try:
                return res.json()
            except Exception:
                return {"ok": False, "error": f"HTTP {res.status_code}: {res.text[:200]}"}
        except requests.exceptions.RequestException as e:
            logging.warning(f"Direct request failed ({e}), attempting Cloudflare edge SNI fallback...")

        # 2. Cloudflare Edge Direct SNI Connection
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            s = socket.create_connection((self.edge_ip, 443), timeout=8)
            ss = ctx.wrap_socket(s, server_hostname=self.host)
            conn = http.client.HTTPSConnection(self.host, timeout=8)
            conn.sock = ss

            body = json.dumps(payload)
            path = f"/api/v1/licenses/{endpoint_php}"
            conn.request("POST", path, body=body, headers=self.headers)
            res = conn.getresponse()
            raw_data = res.read().decode("utf-8", errors="ignore")
            
            try:
                return json.loads(raw_data)
            except Exception:
                return {"ok": False, "error": f"HTTP {res.status} ({res.reason}): {raw_data[:200]}"}
        except Exception as e:
            return {"ok": False, "error": f"Connection Error: {str(e)}"}

    def create_license(self, hours: int, product: str = None) -> dict:
        """
        Create 1 license key based on selected hours.
        """
        # Calculate days if hours is a multiple of 24
        calc_days = hours // 24 if (hours >= 24 and hours % 24 == 0) else 0
        payload = {
            "product": product or self.default_product,
            "hours": hours,
            "days": calc_days,
            "count": 1
        }
        return self._post_request("create.php", payload)

    def delete_license(self, key: str, product: str = None) -> dict:
        """
        Delete a license key.
        """
        payload = {
            "product": product or self.default_product,
            "key": key.strip(),
            "license": key.strip()
        }
        return self._post_request("delete.php", payload)

    def reset_hwid(self, key: str, product: str = None) -> dict:
        """
        Reset HWID lock for a license key.
        """
        payload = {
            "product": product or self.default_product,
            "key": key.strip(),
            "license": key.strip()
        }
        return self._post_request("reset-hwid.php", payload)

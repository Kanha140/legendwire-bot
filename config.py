import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Token
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

# Strict Security Constraints requested by User
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "1565799819736387646"))
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", "1565799860114817165"))

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://protal.authzen.site/api/v1/licenses")
SELLER_KEY = os.getenv("SELLER_KEY", "")
DEFAULT_PRODUCT = os.getenv("DEFAULT_PRODUCT", "LEGEND WIRE")

# Fallback Cloudflare edge IP in case registrar puts authzen.site on client hold
CF_EDGE_IP = os.getenv("CF_EDGE_IP", "104.21.7.28")
API_HOST = os.getenv("API_HOST", "protal.authzen.site")

# Bot Prefix
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")

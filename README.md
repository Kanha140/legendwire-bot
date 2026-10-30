# LegendWire AuthZen Discord Bot & License API

Discord bot integrated with your exact AuthZen License API (`https://protal.authzen.site/api/v1/licenses/create.php`).

---

## 🔒 Strict Security Constraints
* **Allowed Channel ID:** `1565799819736387646` (Commands only execute in this channel)
* **Allowed Role ID:** `1565799860114817165` (Only users with this role can execute commands)

---

## ⚡ Slash Commands (`/`) & Prefix (`!`)

### 1. `/create` or `/createkey`
* **Options:**
  * `days` *(int)*: Validity in days (e.g. 0, 1, 7, 30)
  * `hours` *(int)*: Validity in hours (e.g. 0, 1, 12, 24)
  * `quantity` *(int)*: Number of keys (default: 1)
  * `product` *(str)*: Product name (default: `LEGEND WIRE`)
* **Behavior:**
  * Calls `https://protal.authzen.site/api/v1/licenses/create.php`
  * **📩 Keys are sent directly to the user's DMs** (Private Message) to prevent keys from leaking in public channels!
  * Channel shows confirmation with balance left (`$balance_left`).

### 2. `/delete` or `/deletekey`
* **Options:**
  * `key` *(str)*: The license key to delete
  * `product` *(str)*: Product name (default: `LEGEND WIRE`)
* **Behavior:**
  * Calls `https://protal.authzen.site/api/v1/licenses/delete.php`
  * Deletes the key and confirms in channel.

### 3. `/resethwid`
* **Options:**
  * `key` *(str)*: The license key to reset HWID for
  * `product` *(str)*: Product name (default: `LEGEND WIRE`)
* **Behavior:**
  * Calls `https://protal.authzen.site/api/v1/licenses/reset-hwid.php`
  * Resets HWID lock for the license.

---

## 🌐 Render Hosting Instructions (24/7 Free)

1. Upload files to your **GitHub repository** (except `.env`).
2. Go to [Render Dashboard](https://dashboard.render.com/) ➔ **New +** ➔ **Web Service**.
3. Select your repository.
4. Set:
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python bot.py`
5. Under **Environment Variables**, add:
   * `DISCORD_BOT_TOKEN` = `your_discord_bot_token`
   * `ALLOWED_CHANNEL_ID` = `1565799819736387646`
   * `ALLOWED_ROLE_ID` = `1565799860114817165`
   * `SELLER_KEY` = `YOUR_SELLER_KEY`
   * `DEFAULT_PRODUCT` = `LEGEND WIRE`
   * `PORT` = `10000`
6. Click **Deploy**.
7. To keep alive 24/7 on free tier, add a 5-minute ping monitor on [cron-job.org](https://cron-job.org) for:
   `https://<your-app>.onrender.com/health`

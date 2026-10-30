import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import asyncio
import os
import aiohttp
from config import (
    DISCORD_BOT_TOKEN,
    ALLOWED_CHANNEL_ID,
    ALLOWED_ROLE_ID,
    BOT_PREFIX,
    DEFAULT_PRODUCT
)
from api_client import AuthZenAPI
from web_server import start_web_server

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)
api = AuthZenAPI()

def is_authorized(ctx: commands.Context) -> tuple[bool, str]:
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return False, f"❌ This command can ONLY be used in <#{ALLOWED_CHANNEL_ID}>."

    user_role_ids = [r.id for r in ctx.author.roles] if hasattr(ctx.author, "roles") else []
    if ALLOWED_ROLE_ID not in user_role_ids:
        return False, f"❌ You do not have permission! Required Role: <@&{ALLOWED_ROLE_ID}>."

    return True, ""

def is_interaction_authorized(interaction: discord.Interaction) -> tuple[bool, str]:
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        return False, f"❌ This slash command can ONLY be used in <#{ALLOWED_CHANNEL_ID}>."

    user_role_ids = [r.id for r in interaction.user.roles] if hasattr(interaction.user, "roles") else []
    if ALLOWED_ROLE_ID not in user_role_ids:
        return False, f"❌ You do not have permission! Required Role: <@&{ALLOWED_ROLE_ID}>."

    return True, ""

def make_embed(title: str, description: str, color: int = 0x5865F2) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="LegendWire AuthZen Bot • Strict Channel & Role Guard")
    return embed

def format_duration(hours: int) -> str:
    if hours >= 99999:
        return "Lifetime Unlimited"
    elif hours % 24 == 0:
        days = hours // 24
        return f"{days} Day(s) ({hours} Hours)"
    else:
        return f"{hours} Hour(s)"

# Keep-alive background ping task for permanent Render uptime
@tasks.loop(minutes=5)
async def render_keep_alive():
    port = os.getenv("PORT", "10000")
    render_url = os.getenv("RENDER_EXTERNAL_URL", f"http://127.0.0.1:{port}")
    target = f"{render_url}/health"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(target, timeout=10) as resp:
                logging.info(f"Keep-alive self-ping {target} -> HTTP {resp.status}")
    except Exception as e:
        logging.debug(f"Keep-alive ping error: {e}")

@bot.event
async def on_ready():
    logging.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Legend Wire Licenses"))
    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} application slash commands.")
    except Exception as e:
        logging.error(f"Error syncing slash commands: {e}")

    if not render_keep_alive.is_running():
        render_keep_alive.start()

# ==========================================
# SLASH COMMANDS (/create, /delete, /resethwid)
# ==========================================

HOURS_CHOICES = [
    app_commands.Choice(name="1 Hour", value=1),
    app_commands.Choice(name="2 Hours (Test / Trial)", value=2),
    app_commands.Choice(name="3 Hours", value=3),
    app_commands.Choice(name="6 Hours", value=6),
    app_commands.Choice(name="12 Hours", value=12),
    app_commands.Choice(name="24 Hours (1 Day)", value=24),
    app_commands.Choice(name="48 Hours (2 Days)", value=48),
    app_commands.Choice(name="72 Hours (3 Days)", value=72),
    app_commands.Choice(name="168 Hours (7 Days / 1 Week)", value=168),
    app_commands.Choice(name="360 Hours (15 Days)", value=360),
    app_commands.Choice(name="720 Hours (30 Days / 1 Month)", value=720),
    app_commands.Choice(name="1440 Hours (60 Days / 2 Months)", value=1440),
    app_commands.Choice(name="2160 Hours (90 Days / 3 Months)", value=2160),
    app_commands.Choice(name="8760 Hours (365 Days / 1 Year)", value=8760),
    app_commands.Choice(name="99999 Hours (Lifetime)", value=99999),
]

@bot.tree.command(name="help", description="Show all Legend Wire license commands")
async def slash_help(interaction: discord.Interaction):
    ok, err_msg = is_interaction_authorized(interaction)
    if not ok:
        await interaction.response.send_message(embed=make_embed("Access Denied", err_msg, 0xED4245), ephemeral=True)
        return

    desc = (
        f"**Allowed Channel:** <#{ALLOWED_CHANNEL_ID}>\n"
        f"**Required Role:** <@&{ALLOWED_ROLE_ID}>\n\n"
        "### Available Commands:\n"
        "• `/create` or `/createkey` — Select duration (Hours) from dropdown & receives key in DM\n"
        "• `/delete` or `/deletekey` — Delete an existing license key\n"
        "• `/resethwid` — Reset HWID lock for a key\n"
        "• `/help` — Display this guide\n\n"
        f"*(Note: Prefix `{BOT_PREFIX}` commands like `{BOT_PREFIX}create <hours>` are also supported)*"
    )
    embed = make_embed("🔐 Legend Wire License Manager", desc, 0x5865F2)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="create", description="Create a license key and receive it in your DM")
@app_commands.describe(hours="Select license duration in hours")
@app_commands.choices(hours=HOURS_CHOICES)
async def slash_create(interaction: discord.Interaction, hours: app_commands.Choice[int]):
    ok, err_msg = is_interaction_authorized(interaction)
    if not ok:
        await interaction.response.send_message(embed=make_embed("Access Denied", err_msg, 0xED4245), ephemeral=True)
        return

    selected_hours = hours.value
    duration_str = format_duration(selected_hours)

    await interaction.response.defer(thinking=True)
    res = api.create_license(hours=selected_hours, product=DEFAULT_PRODUCT)

    if res.get("ok"):
        keys_list = res.get("keys", [])
        balance_left = res.get("balance_left", "N/A")
        first_key = keys_list[0] if keys_list else "N/A"

        # Prepare DM Embed
        dm_desc = (
            f"Here is your generated license key for **{DEFAULT_PRODUCT}**:\n\n"
            f"**License Key:**\n```\n{first_key}\n```\n"
            f"**Duration:** `{duration_str}`\n"
            f"**Balance Left:** `${balance_left}`"
        )
        dm_embed = make_embed("🔑 Your Generated License Key", dm_desc, 0x57F287)

        # Send DM
        dm_sent = False
        try:
            await interaction.user.send(embed=dm_embed)
            dm_sent = True
        except discord.Forbidden:
            dm_sent = False

        if dm_sent:
            channel_desc = (
                f"✅ **License key created successfully!**\n\n"
                f"📩 **The key has been sent directly to your DMs**, {interaction.user.mention}!\n\n"
                f"**Product:** `{DEFAULT_PRODUCT}`\n"
                f"**Duration:** `{duration_str}`\n"
                f"**Balance Left:** `${balance_left}`"
            )
            await interaction.followup.send(embed=make_embed("Key Generated & Sent to DM", channel_desc, 0x57F287))
        else:
            channel_desc = (
                f"⚠️ {interaction.user.mention}, your DMs are closed!\n"
                f"Here is your license key (visible only to you):\n\n"
                f"**License Key:**\n```\n{first_key}\n```\n"
                f"**Duration:** `{duration_str}`\n"
                f"**Balance Left:** `${balance_left}`"
            )
            await interaction.followup.send(
                embed=make_embed("Key Generated (DMs Closed)", channel_desc, 0xFEE75C),
                ephemeral=True
            )
    else:
        err = res.get("error") or res.get("message") or "Unknown error"
        await interaction.followup.send(embed=make_embed("Creation Failed", f"❌ API Error: `{err}`", 0xED4245))

@bot.tree.command(name="createkey", description="Create a license key (alias of /create)")
@app_commands.describe(hours="Select license duration in hours")
@app_commands.choices(hours=HOURS_CHOICES)
async def slash_createkey(interaction: discord.Interaction, hours: app_commands.Choice[int]):
    await slash_create.callback(interaction, hours)

@bot.tree.command(name="delete", description="Delete an existing license key")
@app_commands.describe(key="The license key to delete")
async def slash_delete(interaction: discord.Interaction, key: str):
    ok, err_msg = is_interaction_authorized(interaction)
    if not ok:
        await interaction.response.send_message(embed=make_embed("Access Denied", err_msg, 0xED4245), ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    res = api.delete_license(key=key, product=DEFAULT_PRODUCT)

    if res.get("ok") or res.get("success"):
        desc = f"✅ Key `{key}` has been successfully deleted from **{DEFAULT_PRODUCT}**."
        await interaction.followup.send(embed=make_embed("Key Deleted", desc, 0x57F287))
    else:
        err = res.get("error") or res.get("message") or "Deletion failed"
        await interaction.followup.send(embed=make_embed("Delete Failed", f"❌ API Error: `{err}`", 0xED4245))

@bot.tree.command(name="deletekey", description="Delete an existing license key (alias of /delete)")
@app_commands.describe(key="The license key to delete")
async def slash_deletekey(interaction: discord.Interaction, key: str):
    await slash_delete.callback(interaction, key)

@bot.tree.command(name="resethwid", description="Reset HWID lock for a license key")
@app_commands.describe(key="The license key to reset HWID for")
async def slash_resethwid(interaction: discord.Interaction, key: str):
    ok, err_msg = is_interaction_authorized(interaction)
    if not ok:
        await interaction.response.send_message(embed=make_embed("Access Denied", err_msg, 0xED4245), ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    res = api.reset_hwid(key=key, product=DEFAULT_PRODUCT)

    if res.get("ok") or res.get("success"):
        desc = f"✅ HWID lock successfully reset for key `{key}` on **{DEFAULT_PRODUCT}**."
        await interaction.followup.send(embed=make_embed("HWID Reset", desc, 0x57F287))
    else:
        err = res.get("error") or res.get("message") or "Reset HWID failed"
        await interaction.followup.send(embed=make_embed("Reset Failed", f"❌ API Error: `{err}`", 0xED4245))

# ==========================================
# PREFIX COMMANDS (!create, !delete, !resethwid)
# ==========================================

@bot.command(name="create", aliases=["createkey", "genkey"])
async def cmd_create(ctx: commands.Context, hours: int = 24):
    ok, err_msg = is_authorized(ctx)
    if not ok:
        await ctx.reply(embed=make_embed("Access Denied", err_msg, 0xED4245))
        return

    duration_str = format_duration(hours)
    msg = await ctx.reply(embed=make_embed("Processing", f"⏳ Generating key for `{duration_str}`...", 0xFEE75C))
    res = api.create_license(hours=hours, product=DEFAULT_PRODUCT)

    if res.get("ok"):
        keys_list = res.get("keys", [])
        balance_left = res.get("balance_left", "N/A")
        first_key = keys_list[0] if keys_list else "N/A"

        dm_desc = (
            f"Here is your generated license key for **{DEFAULT_PRODUCT}**:\n\n"
            f"**License Key:**\n```\n{first_key}\n```\n"
            f"**Duration:** `{duration_str}`\n"
            f"**Balance Left:** `${balance_left}`"
        )
        try:
            await ctx.author.send(embed=make_embed("🔑 Your Generated License Key", dm_desc, 0x57F287))
            ch_desc = (
                f"✅ **License key created successfully!**\n\n"
                f"📩 The key has been sent to your DMs, {ctx.author.mention}!\n"
                f"**Duration:** `{duration_str}`\n"
                f"**Balance Left:** `${balance_left}`"
            )
            await msg.edit(embed=make_embed("Key Generated & Sent to DM", ch_desc, 0x57F287))
        except discord.Forbidden:
            await msg.edit(embed=make_embed("Key Generated", f"⚠️ DMs closed!\n```\n{first_key}\n```", 0xFEE75C))
    else:
        err = res.get("error") or res.get("message") or "Unknown error"
        await msg.edit(embed=make_embed("Creation Failed", f"❌ API Error: `{err}`", 0xED4245))

@bot.command(name="delete", aliases=["deletekey", "delkey"])
async def cmd_delete(ctx: commands.Context, key: str):
    ok, err_msg = is_authorized(ctx)
    if not ok:
        await ctx.reply(embed=make_embed("Access Denied", err_msg, 0xED4245))
        return

    msg = await ctx.reply(embed=make_embed("Processing", f"⏳ Deleting key `{key}`...", 0xFEE75C))
    res = api.delete_license(key=key, product=DEFAULT_PRODUCT)

    if res.get("ok") or res.get("success"):
        await msg.edit(embed=make_embed("Key Deleted", f"✅ Key `{key}` deleted successfully.", 0x57F287))
    else:
        err = res.get("error") or res.get("message") or "Deletion failed"
        await msg.edit(embed=make_embed("Delete Failed", f"❌ API Error: `{err}`", 0xED4245))

@bot.command(name="resethwid", aliases=["resetkey"])
async def cmd_resethwid(ctx: commands.Context, key: str):
    ok, err_msg = is_authorized(ctx)
    if not ok:
        await ctx.reply(embed=make_embed("Access Denied", err_msg, 0xED4245))
        return

    msg = await ctx.reply(embed=make_embed("Processing", f"⏳ Resetting HWID for `{key}`...", 0xFEE75C))
    res = api.reset_hwid(key=key, product=DEFAULT_PRODUCT)

    if res.get("ok") or res.get("success"):
        await msg.edit(embed=make_embed("HWID Reset", f"✅ HWID successfully reset for key `{key}`.", 0x57F287))
    else:
        err = res.get("error") or res.get("message") or "Reset HWID failed"
        await msg.edit(embed=make_embed("Reset Failed", f"❌ API Error: `{err}`", 0xED4245))

@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    ok, err_msg = is_authorized(ctx)
    if not ok:
        await ctx.reply(embed=make_embed("Access Denied", err_msg, 0xED4245))
        return

    desc = (
        f"**Allowed Channel:** <#{ALLOWED_CHANNEL_ID}>\n"
        f"**Required Role:** <@&{ALLOWED_ROLE_ID}>\n\n"
        "### Available Commands:\n"
        f"• `{BOT_PREFIX}create <hours>` — Generate key & DM to you\n"
        f"• `{BOT_PREFIX}delete <key>` — Delete a license key\n"
        f"• `{BOT_PREFIX}resethwid <key>` — Reset HWID for a key\n"
        f"• `{BOT_PREFIX}help` — View commands\n\n"
        "*(Slash commands `/create`, `/delete`, `/resethwid` with dropdown options are active)*"
    )
    await ctx.reply(embed=make_embed("🔐 Legend Wire License Manager", desc, 0x5865F2))

# ==========================================
# BOT STARTUP
# ==========================================

async def main():
    token = DISCORD_BOT_TOKEN
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("\n" + "="*60)
        print("⚠️ ERROR: DISCORD_BOT_TOKEN is not set!")
        print("Please set DISCORD_BOT_TOKEN in .env or Render Environment Variables.")
        print("="*60 + "\n")
        return

    # Start web server for Render keep-alive and health checks
    await start_web_server()

    # Start Discord Bot
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutdown requested.")

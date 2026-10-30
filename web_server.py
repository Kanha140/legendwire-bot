import os
import logging
from aiohttp import web

async def handle_health(request):
    return web.json_response({
        "status": "online",
        "service": "LegendWire AuthZen Discord Bot",
        "message": "Bot is running healthy"
    })

async def start_web_server(port: int = None):
    """Starts a lightweight web server on the assigned PORT for Render Web Service compatibility."""
    if port is None:
        port = int(os.getenv("PORT", "8080"))
    
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Web server started on http://0.0.0.0:{port} (Render ready)")
    return runner

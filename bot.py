import asyncio
from aiohttp import web
from flask import Flask
from threading import Thread
import os
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
import pytz
import aria2p
from config import *
from dotenv import load_dotenv
from database.db_premium import remove_expired_users
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# Silence APScheduler logs completely
logging.getLogger("apscheduler").setLevel(logging.CRITICAL)

load_dotenv(".env")

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Rohit")

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647


def get_indian_time():
    """Returns the current time in IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)

aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret=""
    )
)

# Scheduler (shared)
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(remove_expired_users, "interval", seconds=10)


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        await super().start()
        scheduler.start()
        usr_bot_me = await self.get_me()
        self.uptime = get_indian_time()
        
        # Start background task for resetting free limits
        try:
            from plugins.free_limit_reset import reset_free_limits_task
            asyncio.create_task(reset_free_limits_task(self))
            logging.info("Started free limit reset background task")
        except Exception as e:
            logging.error(f"Error starting free limit reset task: {e}")

        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(
                f"Make Sure bot is Admin in DB Channel, and Double check the CHANNEL_ID Value, Current Value {CHANNEL_ID}"
            )
            self.LOGGER(__name__).info("\nBot Stopped. @rohit_1888 for support")
            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username
        bot_name = usr_bot_me.first_name
        bot_id = usr_bot_me.id
        
        # Print bot information clearly
        print("\n" + "="*50)
        print("🤖 BOT SUCCESSFULLY STARTED!")
        print("="*50)
        print(f"Bot Username: @{self.username}")
        print(f"Bot Name: {bot_name}")
        print(f"Bot ID: {bot_id}")
        print("="*50)
        print("Bot is now active and ready to receive commands!")
        print("="*50 + "\n")
        
        self.LOGGER(__name__).info(f"Bot Running..! Made by @rohit_1888")
        self.LOGGER(__name__).info(f"Bot Username: @{self.username}")

        # Start Web Server
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        try:
            await self.send_message(
                OWNER_ID,
                text=f"<b><blockquote>🤖 Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ by @rohit_1888</blockquote></b>"
            )
        except:
            pass

    async def stop(self, *args):
        self.scheduler.shutdown(wait=False)  
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        """Run the bot."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        self.LOGGER(__name__).info("Bot is now running. Thanks to @rohit_1888")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())


if __name__ == "__main__":
    Bot().run()
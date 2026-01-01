# Don't remove This Line From Here. Tg: @rohit_1888 | @Javpostr
import os
import sys
import time
import random
import logging
import asyncio
import subprocess
from datetime import datetime, timedelta

from pytz import timezone
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton
)
from pyrogram.errors import (
    FloodWait, UserIsBlocked, InputUserDeactivated
)
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid

from bot import Bot
from config import *
from helper_func import *
from database.database import db

db_channel_id=CHANNEL_ID



@Bot.on_message(filters.command('update') & filters.private & is_admin)
async def update_bot(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("You are not authorized to update the bot.")

    try:
        msg = await message.reply_text("<b><blockquote>Pulling the latest updates and restarting the bot...</blockquote></b>")

        # Run git pull
        git_pull = subprocess.run(["git", "pull"], capture_output=True, text=True)

        if git_pull.returncode == 0:
            await msg.edit_text(f"<b><blockquote>Updates pulled successfully:\n\n{git_pull.stdout}</blockquote></b>")
        else:
            await msg.edit_text(f"<b><blockquote>Failed to pull updates:\n\n{git_pull.stderr}</blockquote></b>")
            return

        await asyncio.sleep(3)

        await msg.edit_text("<b><blockquote>✅ Bᴏᴛ ɪs ʀᴇsᴛᴀʀᴛɪɴɢ ɴᴏᴡ...</blockquote></b>")

    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
        return

    finally:
        os.execl(sys.executable, sys.executable, *sys.argv)


@Bot.on_message(filters.private & ~filters.command([
    'start', 'users', 'broadcast', 'stats', 'addpaid', 'removepaid', 'listpaid',
    'help', 'add_fsub', 'fsub_chnl', 'restart', 'del_fsub', 'add_admins', 'del_admins', 
    'admin_list', 'cancel', 'auto_del', 'forcesub', 'files', 'add_banuser', 'token', 'del_banuser', 'banuser_list', 
    'status', 'req_fsub', 'myplan', 'short', 'check', 'free', 'set_free_limit', 'update', 'status', 'genlink', 'batch', 'custom_batch', 'referral'])# ✅ ADD EXCEPTION FOR BUTTON TEXTS
    & ~filters.regex("^Get Video 🍒$")
    & ~filters.regex("^Get Photo 📸$")
    & ~filters.regex("^Get Batch 📦$")
)
async def handle_message(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is admin - admins can send any message
    if await db.admin_exist(user_id) or user_id == OWNER_ID:
        return  # Allow admins to send any message
    
    # For non-admin users, reply with configured message
    await message.reply_text(
        USER_REPLY_TEXT,
        protect_content=False,
        quote=True
    )
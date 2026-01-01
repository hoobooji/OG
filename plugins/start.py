import asyncio
import base64
import logging
import os
import random
import re
import string
import time

from datetime import datetime, timedelta
from pytz import timezone
import pytz

from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import (
    Message,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
    ReplyKeyboardMarkup,
)
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from plugins.autoDelete import auto_del_notification, delete_message
from bot import Bot
from config import *
from helper_func import *
from database.database import db
from database.db_premium import *
from plugins.FORMATS import *

# Logging + timezone
logging.basicConfig(level=logging.INFO)

# Store preloaded videos per user for faster next/last navigation
user_video_cache = {}  # {user_id: [list of video dicts]}
IST = timezone("Asia/Kolkata")



            
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    user_id = id
    text = (message.text or "").replace("/start", "").strip()
    logging.info(f"Received /start command from user ID: {id}")

    # ================= VERIFY STATUS =================
    try:
        verify_status = await db.get_verify_status(id) or {}
    except Exception as e:
        logging.error(f"Error fetching verify status for {id}: {e}")
        verify_status = {
            "is_verified": False,
            "verified_time": 0,
            "verify_token": "",
            "link": ""
        }

    try:
        VERIFY_EXPIRE = await db.get_verified_time()
    except Exception as e:
        logging.error(f"Error fetching verify expiry config: {e}")
        VERIFY_EXPIRE = None

    # ================= EXPIRE VERIFY =================
    try:
        if verify_status.get("is_verified") and VERIFY_EXPIRE:
            verified_time = verify_status.get("verified_time", 0)
            if (time.time() - verified_time) > VERIFY_EXPIRE:
                await db.update_verify_status(id, is_verified=False)
                verify_status["is_verified"] = False
    except Exception as e:
        logging.error(f"Verify expiry check error: {e}")

    # ================= ENSURE USER =================
    try:
        if not await db.present_user(id):
            await db.add_user(id)
    except Exception as e:
        logging.error(f"Error adding user {id}: {e}")

    # ================= VERIFY TOKEN =================
    if text.startswith("verify_"):
        token = text.replace("verify_", "", 1)
        if verify_status.get("verify_token") != token:
            return await message.reply("⚠️ Invalid or expired token. Use /start again.")

        await db.update_verify_status(
            id,
            is_verified=True,
            verified_time=time.time()
        )

        expiry_text = get_exp_time(VERIFY_EXPIRE) if VERIFY_EXPIRE else "configured duration"
        return await message.reply(
            f"✅ Token Verified Successfully!\n\n🔑 Valid For: {expiry_text}.",
            quote=True
        )

    # ================= GET AGAIN =================
    if text.startswith("get_video_"):
        try:
            uid = int(text.split("_")[-1])
            if uid == user_id:
                return await get_video(client, message)
        except:
            pass

    # ================= LINK HANDLING =================
    if text and not text.startswith("verify_"):
        from helper_func import decode

        # ---------- BATCH LINK (pl_) ----------
        if text.startswith("pl_"):
            try:
                base64_data = text.replace("pl_", "", 1)

                # padding only
                pad = (-len(base64_data) % 4)
                if pad:
                    base64_data += "=" * pad

                decoded = await decode(base64_data)
                if decoded.startswith("batch-"):
                    f_enc, s_enc = decoded.replace("batch-", "").split("-", 1)
                    f_msg_id = int(f_enc) // abs(client.db_channel.id)
                    s_msg_id = int(s_enc) // abs(client.db_channel.id)

                    await send_batch_from_link(client, message, f_msg_id, s_msg_id)
                    return
            except Exception as e:
                logging.error(f"Batch decode error: {e}")

        # ---------- SINGLE GENLINK ----------
        try:
            base64_data = text

            # padding only (NO replace)
            pad = (-len(base64_data) % 4)
            if pad:
                base64_data += "=" * pad

            decoded = await decode(base64_data)
            if decoded.startswith("vid-"):
                encoded_id = int(decoded.replace("vid-", ""))
                msg_id = encoded_id // abs(client.db_channel.id)

                await send_video_from_link(client, message, msg_id)
                return
        except Exception as e:
            logging.error(f"Genlink decode error: {e}")

        # ---------- OLD FORMAT (BACKWARD) ----------
        try:
            decoded = await decode(text)
            if decoded.startswith("get-"):
                parts = decoded.replace("get-", "").split("-")

                if len(parts) == 1:
                    msg_id = int(parts[0]) // abs(client.db_channel.id)
                    await send_video_from_link(client, message, msg_id)
                    return

                elif len(parts) == 2:
                    f_msg_id = int(parts[0]) // abs(client.db_channel.id)
                    s_msg_id = int(parts[1]) // abs(client.db_channel.id)
                    await send_batch_from_link(client, message, f_msg_id, s_msg_id)
                    return
        except:
            pass

    # ================= DEFAULT START =================
    reply_kb = ReplyKeyboardMarkup(
        [
            [KeyboardButton("Get Video 🍒"), KeyboardButton("Plan Status 🔖")],
        ],
        resize_keyboard=True,
    )

    try:
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name or "",
                last=message.from_user.last_name or "",
                username=f"@{message.from_user.username}" if message.from_user.username else None,
                mention=message.from_user.mention,
                id=message.from_user.id,
            ),
            reply_markup=reply_kb
        )
    except:
        await message.reply(
            START_MSG.format(
                first=message.from_user.first_name or "",
                last=message.from_user.last_name or "",
                username=f"@{message.from_user.username}" if message.from_user.username else None,
                mention=message.from_user.mention,
                id=message.from_user.id,
            ),
            reply_markup=reply_kb
        )
                    
                

#=====================================================================================##

@Bot.on_message(filters.command('check') & filters.private)
async def check_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is premium
    is_premium = await is_premium_user(user_id)
    
    if is_premium:
        # Premium user - no verification needed
        return await message.reply_text(
            "✅ Yᴏᴜ ᴀʀᴇ ᴀ Pʀᴇᴍɪᴜᴍ Usᴇʀ.\n\n🔓 Nᴏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ɴᴇᴇᴅᴇᴅ!",
            protect_content=False,
            quote=True
        )
    
    # Not premium - check verification status
    try:
        verify_status = await db.get_verify_status(user_id) or {}
        VERIFY_EXPIRE = await db.get_verified_time()
    except Exception as e:
        logging.error(f"Error fetching verify status: {e}")
        verify_status = {"is_verified": False}
        VERIFY_EXPIRE = None
    
    if verify_status.get("is_verified", False):
        expiry_text = get_exp_time(VERIFY_EXPIRE) if VERIFY_EXPIRE else "the configured duration"
        return await message.reply_text(
            f"✅ Yᴏᴜ ᴀʀᴇ ᴠᴇʀɪғɪᴇᴅ.\n\n🔑 Vᴀʟɪᴅ ғᴏʀ: {expiry_text}.",
            protect_content=False,
            quote=True
        )
    
    # Not verified - check if shortener is available
    try:
        shortener_url = await db.get_shortener_url()
        shortener_api = await db.get_shortener_api()
    except Exception as e:
        logging.error(f"Error fetching shortener settings: {e}")
        shortener_url = None
        shortener_api = None
    
    if shortener_url and shortener_api:
        # Show verification prompt with shortlink
        try:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            await db.update_verify_status(user_id, verify_token=token, link="")
            
            long_url = f"https://telegram.dog/{client.username}?start=verify_{token}"
            short_link = await get_shortlink(long_url)
            
            tut_vid_url = await db.get_tut_video() or TUT_VID
            
            btn = [
                [InlineKeyboardButton("Click here", url=short_link),
                 InlineKeyboardButton('How to use the bot', url=tut_vid_url)],
                [InlineKeyboardButton('BUY PREMIUM', callback_data='buy_prem')]
            ]
            
            expiry_text = get_exp_time(VERIFY_EXPIRE) if VERIFY_EXPIRE else "the configured duration"
            return await message.reply(
                f"Your ads token is expired or invalid. Please verify to access the files.\n\n"
                f"Token Timeout: {expiry_text}\n\n"
                f"What is the token?\n\n"
                f"This is an ads token. By passing 1 ad, you can use the bot for {expiry_text}.",
                reply_markup=InlineKeyboardMarkup(btn),
                protect_content=False,
                quote=True
            )
        except Exception as e:
            logging.error(f"Error in verification process: {e}")
            return await message.reply_text(
                "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ. Pʟᴇᴀsᴇ ᴜsᴇ /start ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ.",
                protect_content=False,
                quote=True
            )
    else:
        # No shortener available
        return await message.reply_text(
            "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ. Pʟᴇᴀsᴇ ᴜsᴇ /start ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ.",
            protect_content=False,
            quote=True
        )


@Bot.on_message(filters.regex("Plan Status 🔖"))
async def on_plan_status(client: Client, message: Message):
    from pytz import timezone
    ist = timezone("Asia/Kolkata")

    user_id = message.from_user.id

    # Check premium status
    is_premium = await is_premium_user(user_id)

    # Free user related data
    free_limit = await db.get_free_limit(user_id)
    free_enabled = await db.get_free_state(user_id)
    free_count = await db.check_free_usage(user_id)

    if is_premium:
        # Fetch expiry timestamp directly from DB
        user_data = await collection.find_one({"user_id": user_id})
        expiration_timestamp = user_data.get("expiration_timestamp") if user_data else None

        if expiration_timestamp:
            expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
            remaining_time = expiration_time - datetime.now(ist)

            days = remaining_time.days
            hours = remaining_time.seconds // 3600
            minutes = (remaining_time.seconds // 60) % 60
            seconds = remaining_time.seconds % 60
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"

            status_message = (
                f"Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Sᴛᴀᴛᴜs: Pʀᴇᴍɪᴜᴍ ✅\n\n"
                f"Rᴇᴍᴀɪɴɪɴɢ Tɪᴍᴇ: {expiry_info}\n\n"
                f"Vɪᴅᴇᴏs Rᴇᴍᴀɪɴɪɴɢ Tᴏᴅᴀʏ: Uɴʟɪᴍɪᴛᴇᴅ 🎉"
            )
        else:
            status_message = (
                f"Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Sᴛᴀᴛᴜs: Pʀᴇᴍɪᴜᴍ ✅\n\n"
                f"Pʟᴀɴ Exᴘɪʀʏ: N/A"
            )

        # Premium reply with normal keyboard
        await message.reply_text(
            status_message,
            reply_markup=ReplyKeyboardMarkup(
                [["Plan Status 🔖", "Get Video 🍒"]],
                resize_keyboard=True
            ),
            protect_content=False,
            quote=True
        )

    elif free_enabled:
        # Free user logic
        remaining_attempts = free_limit - free_count
        status_message = (
            f"Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Sᴛᴀᴛᴜs: Fʀᴇᴇ (ᘜᗩᖇᗴᗴᗷ) 🆓\n\n"
            f"Vɪᴅᴇᴏs Rᴇᴍᴀɪɴɪɴɢ Tᴏᴅᴀʏ: {remaining_attempts}/{free_limit}"
        )

        await message.reply_text(
            status_message,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            ),
            protect_content=False,
            quote=True
        )

    else:
        # Free plan disabled
        status_message = (
            f"Sᴜʙsᴄʀɪᴘᴛɪᴏɴ Sᴛᴀᴛᴜs: Fʀᴇᴇ (ᘜᗩᖇᗴᗴᗷ) (Dɪsᴀʙʟᴇᴅ)\n\n"
            f"Vɪᴅᴇᴏs Rᴇᴍᴀɪɴɪɴɢ Tᴏᴅᴀʏ: 0/{free_limit}"
        )

        await message.reply_text(
            status_message,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            ),
            protect_content=False,
            quote=True
        )


@Bot.on_message(filters.regex("Get Video 🍒"))
async def on_get_video(client: Client, message: Message):
    user_id = message.from_user.id
    await get_video(client, message)


@Bot.on_message(filters.command('bookmark') & filters.private)
async def on_bookmark_command(client: Client, message: Message):
    user_id = message.from_user.id
    await get_bookmarked_videos(client, message)


# --- Store Videos from Channel ---
async def store_videos(app: Client, channel_id: int = None):
    """Store videos from a specific channel. If channel_id is None, fetch from all category channels"""
    from config import CATEGORY_CHANNELS, CHANNEL_ID
    
    # If no channel specified, fetch from all category channels
    channels_to_fetch = CATEGORY_CHANNELS if CATEGORY_CHANNELS else [CHANNEL_ID]
    
    if channel_id:
        # Fetch from specific channel only
        channels_to_fetch = [channel_id]
    
    all_videos = []
    
    for channel_to_fetch in channels_to_fetch:
        try:
            logging.info(f"Fetching videos from channel: {channel_to_fetch}")
            
            # Start from message ID 1 and keep fetching until no more messages
            batch_size = 200
            last_message_id = 1
            max_consecutive_empty = 10  # Stop after 10 consecutive empty batches
            consecutive_empty = 0
            
            while consecutive_empty < max_consecutive_empty:
                try:
                    # Get a batch of messages
                    message_ids = list(range(last_message_id, last_message_id + batch_size))
                    messages = await try_until_get(
                        app.get_messages(channel_to_fetch, message_ids)
                    )
                    
                    if not messages:
                        consecutive_empty += 1
                        last_message_id += batch_size
                        continue
                    
                    batch_videos = []
                    for msg in messages:
                        if msg and msg.video:
                            file_id = msg.video.file_id
                            # Check if video exists for this channel
                            exists = await db.video_exists(file_id, channel_id=channel_to_fetch)
                            if not exists:
                                batch_videos.append({
                                    "file_id": file_id,
                                    "channel_id": channel_to_fetch
                                })
                    
                    if batch_videos:
                        consecutive_empty = 0  # Reset counter
                        all_videos.extend(batch_videos)
                        logging.info(f"Found {len(batch_videos)} new videos in batch (last_message_id: {last_message_id})")
                    else:
                        consecutive_empty += 1
                    
                    last_message_id += batch_size
                    
                    # Add small delay to avoid rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logging.error(f"Error fetching batch from channel {channel_to_fetch} (starting at {last_message_id}): {e}")
                    consecutive_empty += 1
                    last_message_id += batch_size
                    await asyncio.sleep(1)
            
            logging.info(f"Finished fetching from channel {channel_to_fetch}. Total videos collected: {len([v for v in all_videos if v.get('channel_id') == channel_to_fetch])}")
            
        except Exception as e:
            logging.error(f"Error fetching videos from channel {channel_to_fetch}: {e}")
            continue
    
    # Insert all videos found
    if all_videos:
        try:
            await db.insert_videos(all_videos)
            logging.info(f"Inserted {len(all_videos)} videos into database")
        except Exception as e:
            logging.error(f"Error inserting videos: {e}")
            # Try inserting in smaller batches
            batch_size = 500
            for i in range(0, len(all_videos), batch_size):
                batch = all_videos[i:i + batch_size]
                try:
                    await db.insert_videos(batch)
                except Exception as batch_error:
                    logging.error(f"Error inserting batch {i//batch_size + 1}: {batch_error}")


# --- Send Random Video ---
async def send_random_video(client: Client, chat_id, user_id=None, protect=True, caption="", reply_markup=None, hide_caption=False, category_channel_id=None):
    import uuid
    from config import CATEGORY_CHANNELS, CHANNEL_ID
    
    # Determine which channel to use
    channel_to_use = CHANNEL_ID  # Default
    if user_id:
        user_category = await db.get_user_category(user_id)
        if user_category < len(CATEGORY_CHANNELS):
            channel_to_use = CATEGORY_CHANNELS[user_category]
    
    # Use provided category channel if specified
    if category_channel_id:
        channel_to_use = category_channel_id
    
    # Get videos from the selected category channel
    vids = await db.get_videos(channel_id=channel_to_use)
    
    # If no videos, fetch from the specific channel
    if not vids:
        await store_videos(client, channel_id=channel_to_use)
        vids = await db.get_videos(channel_id=channel_to_use)

    if vids:
        random_video = random.choice(vids)
        file_id = random_video["file_id"]
        
        # Generate unique numeric video ID if not exists
        video_metadata = await db.get_video_by_file_id(file_id)
        if video_metadata:
            video_id = video_metadata.get("video_id")
        else:
            # Generate numeric ID based on hash of file_id
            import hashlib
            hash_obj = hashlib.md5(file_id.encode())
            hash_int = int(hash_obj.hexdigest()[:8], 16)
            video_id = str(hash_int)  # Numeric ID
            await db.save_video_metadata(video_id, file_id)
        
        # If hide_caption is enabled, clear the caption
        final_caption = "" if hide_caption else (caption if caption else None)
        
        try:
            sent_msg = await client.send_video(
                chat_id, 
                file_id, 
                caption=final_caption,
                parse_mode=ParseMode.HTML if final_caption else None,
                reply_markup=reply_markup,
                protect_content=protect
            )
            # Update metadata with message ID
            await db.save_video_metadata(video_id, file_id, sent_msg.id)
            return sent_msg, video_id, file_id
        except FloodWait as e:
            await asyncio.sleep(e.x)
            sent_msg = await client.send_video(
                chat_id, 
                file_id, 
                caption=final_caption,
                parse_mode=ParseMode.HTML if final_caption else None,
                reply_markup=reply_markup,
                protect_content=protect
            )
            await db.save_video_metadata(video_id, file_id, sent_msg.id)
            return sent_msg, video_id, file_id
    else:
        await client.send_message(chat_id, "No videos available right now.")
        return None, None, None



# --- Safe Fetch Wrapper ---
async def try_until_get(func):
    try:
        result = await func
        return result if result else []
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await try_until_get(func)
    except Exception as e:
        print(f'Cannot get videos: {e}')
        return []


# --- Helper function to create video buttons ---
async def create_video_buttons(
    user_id: int, 
    video_id: str, 
    is_premium: bool = False,
    is_first: bool = False,
    is_last: bool = False,
    is_bookmark_context: bool = False,
    bookmark_index: int = None,
    bookmark_total: int = None,
    show_change_category: bool = True,
    use_channel_buttons: bool = True,
    show_nav_buttons: bool = True,
    show_reaction_buttons: bool = True,
):
    """Create buttons for video interaction with context"""
    
    # Check like/dislike/bookmark status
    is_liked = await db.is_liked(user_id, video_id)
    is_disliked = await db.is_disliked(user_id, video_id)
    is_bookmarked = await db.is_bookmarked(user_id, video_id)
    
    buttons = []
    
    # First row: Like, Dislike, Mark (can be disabled for /start/genlink flows)
    if show_reaction_buttons:
        like_btn = "❤️" if is_liked else "🤍"
        dislike_btn = "🦠" if is_disliked else "😐"
        mark_btn = "🔖" if is_bookmarked else "📌"
        
        buttons.append([
            InlineKeyboardButton(like_btn, callback_data=f"like_{video_id}"),
            InlineKeyboardButton(dislike_btn, callback_data=f"dislike_{video_id}"),
            InlineKeyboardButton(mark_btn, callback_data=f"mark_{video_id}"),
        ])
    
    # Second row: Last, Save, Next (with context-aware buttons)
    second_row = []
    # Add Last button only if not first video and nav buttons enabled
    if show_nav_buttons and not is_first:
        if is_bookmark_context:
            second_row.append(InlineKeyboardButton("🙆🏻‍♂️ Last", callback_data=f"bookmark_nav_{user_id}_{bookmark_index - 1}"))
        else:
            second_row.append(InlineKeyboardButton("🙆🏻‍♂️ Last", callback_data=f"last_{user_id}_{video_id}"))
    
    # Save button always shown
    second_row.append(InlineKeyboardButton("⬇️ Save", callback_data=f"save_{video_id}"))
    
    # Add Next button only if not last video and nav buttons enabled
    if show_nav_buttons and not is_last:
        if is_bookmark_context:
            second_row.append(InlineKeyboardButton("😋 Next", callback_data=f"bookmark_nav_{user_id}_{bookmark_index + 1}"))
        else:
            second_row.append(InlineKeyboardButton("😋 Next", callback_data=f"next_{user_id}_{video_id}"))
    
    if second_row:
        buttons.append(second_row)
    
    # Third row: Purchase Premium (shown for non-premium users)
    if not is_premium:
        buttons.append([
            InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem"),
        ])
    
    try:
        logging.debug(f"CATEGORY_CHANNELS in create_video_buttons: {CATEGORY_CHANNELS}, length: {len(CATEGORY_CHANNELS) if CATEGORY_CHANNELS else 0}")
        if show_change_category and CATEGORY_CHANNELS and len(CATEGORY_CHANNELS) > 1:
            buttons.append([
                InlineKeyboardButton("📁 Change Category", callback_data="change_category"),
            ])
    except Exception as e:
        logging.error(f"Error checking CATEGORY_CHANNELS: {e}")
        try:
            import config
            if hasattr(config, 'CATEGORY_CHANNELS') and config.CATEGORY_CHANNELS and len(config.CATEGORY_CHANNELS) > 1:
                buttons.append([
                    InlineKeyboardButton("📁 Change Category", callback_data="change_category"),
                ])
        except:
            pass

    # Add channel buttons from DB if enabled and requested
    if use_channel_buttons:
        CHNL_BTN = await db.get_channel_button()
        if CHNL_BTN:
            try:
                button_name, button_link, button_name2, button_link2 = await db.get_channel_button_links()
                channel_buttons = []
                if button_name and button_link:
                    channel_buttons.append(InlineKeyboardButton(text=button_name, url=button_link))
                if button_name2 and button_link2:
                    channel_buttons.append(InlineKeyboardButton(text=button_name2, url=button_link2))
                if channel_buttons:
                    buttons.append(channel_buttons)
            except Exception as e:
                logging.error(f"Error adding channel buttons: {e}")
    
    return InlineKeyboardMarkup(buttons)

# --- Helper to get last video for user ---
async def get_last_video(user_id: int):
    """Get last video ID and file_id for user"""
    # Store last video in user data - simple approach
    try:
        # Use video_metadata to track last video per user
        # We'll use a simple document per user
        last_video_data = await db.database["user_last_videos"].find_one({"_id": user_id})
        if last_video_data:
            return last_video_data.get("video_id"), last_video_data.get("file_id")
    except:
        pass
    return None, None

# --- Helper to save last video for user ---
async def save_last_video(user_id: int, video_id: str, file_id: str):
    """Save last video info for user"""
    try:
        await db.database["user_last_videos"].update_one(
            {"_id": user_id},
            {"$set": {"video_id": video_id, "file_id": file_id}},
            upsert=True
        )
    except:
        pass

# --- Helper to edit video message with new video ---
async def edit_video_message(client: Client, message, file_id: str, caption: str, reply_markup, protect_content: bool = True):
    """Edit a video message with new video"""
    from pyrogram.types import InputMediaVideo
    from pyrogram.errors import MessageNotModified
    try:
        await message.edit_media(
            InputMediaVideo(
                media=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=reply_markup
        )
        return True
    except MessageNotModified:
        # Message is already the same - this is fine, just update buttons if needed
        try:
            if reply_markup:
                await message.edit_reply_markup(reply_markup=reply_markup)
        except:
            pass
        return True
    except Exception as e:
        logging.error(f"Error editing video message: {e}")
        return False

# --- Helper to get category name for user ---
async def get_category_name(user_id: int):
    """Get category name for user"""
    from config import CATEGORY_NAMES
    try:
        category_index = await db.get_user_category(user_id)
        if category_index < len(CATEGORY_NAMES):
            return CATEGORY_NAMES[category_index]
    except:
        pass
    return None

# --- Helper to send video from link ---
async def send_video_from_link(client: Client, message: Message, msg_id: int):
    """Send video from message ID (from genlink)"""
    user_id = message.from_user.id
    is_premium = await is_premium_user(user_id)
    
    try:
        # Get message from channel
        channel_msg = await client.get_messages(client.db_channel.id, msg_id)
        if not channel_msg or not channel_msg.video:
            return await message.reply_text("❌ Video not found.", quote=True)
        
        file_id = channel_msg.video.file_id
        
        # Generate numeric video ID
        import hashlib
        hash_obj = hashlib.md5(file_id.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        video_id = str(hash_int)
        
        # Save metadata
        await db.save_video_metadata(video_id, file_id, channel_msg.id)
        
        # Load settings (removed AUTO_DEL and DEL_TIMER)
        try:
            HIDE_CAPTION = await db.get_hide_caption()
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            HIDE_CAPTION = False
        
        # Get custom caption
        custom_caption = await db.get_custom_caption()
        if not custom_caption:
            from config import CUSTOM_CAPTION
            custom_caption = CUSTOM_CAPTION or ""
        
        # Get category name
        category_name = await get_category_name(user_id)
        
        # Get like and dislike percentage for video
        like_percentage = await db.get_like_percentage(video_id)
        dislike_percentage = await db.get_dislike_percentage(video_id)
        
        # Prepare caption with video ID, category name, and like/dislike percentage
        caption_parts = []
        if custom_caption:
            caption_parts.append(custom_caption)
        caption_parts.append(f"\n<b>ID: <code>{video_id}</code></b>")
        if category_name:
            caption_parts.append(f"<b>Category: {category_name}</b>")
        caption_parts.append(f"<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>")
        final_caption = "\n".join(caption_parts) if not HIDE_CAPTION else f"<b>ID: <code>{video_id}</code></b>" + (f"\n<b>Category: {category_name}</b>" if category_name else "") + f"\n<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>"
        
        # Create buttons (same as get_video)
        # For single genlink, remove nav buttons and change-category by default
        start_buttons_enabled = await db.get_start_buttons()
        start_reactions_enabled = await db.get_start_reactions()
        reply_markup = await create_video_buttons(
            user_id,
            video_id,
            is_premium=is_premium,
            is_first=True,
            is_last=True,
            show_change_category=False,
            use_channel_buttons=False,
            show_nav_buttons=False if not start_buttons_enabled else False,
            show_reaction_buttons=start_reactions_enabled,
        )
        
        # Save as last video
        await save_last_video(user_id, video_id, file_id)

        # Respect CHNL_BTN and PROTECT_MODE when sending: override reply_markup to channel button only if CHNL_BTN and button exist
        try:
            AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
                db.get_auto_delete(), db.get_del_timer(), db.get_hide_caption(), db.get_channel_button(), db.get_protect_content()
            )
        except:
            CHNL_BTN = False
            PROTECT_MODE = True

        if CHNL_BTN:
            try:
                button_name, button_link = await db.get_channel_button_link()
                if button_name and button_link:
                    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text=button_name, url=button_link)]])
            except:
                pass

        try:
            sent_msg = await client.send_video(
                message.chat.id,
                file_id,
                caption=final_caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                protect_content=PROTECT_MODE
            )
            return sent_msg
        except Exception as e:
            logging.error(f"Error sending video from link: {e}")
            return await message.reply_text("❌ Error sending video.", quote=True)
    except Exception as e:
        logging.error(f"Error in send_video_from_link: {e}")
        return await message.reply_text("❌ Error processing link.", quote=True)

# --- Helper to send batch from link ---
async def send_batch_from_link(client: Client, message: Message, f_msg_id: int, s_msg_id: int):
    """Send batch videos from message IDs (from batch link)"""
    user_id = message.from_user.id
    is_premium = await is_premium_user(user_id)
    
    try:
        # Get range of messages
        msg_ids = list(range(min(f_msg_id, s_msg_id), max(f_msg_id, s_msg_id) + 1))
        messages = await try_until_get(
            client.get_messages(client.db_channel.id, msg_ids)
        )
        
        videos = []
        for msg in messages:
            if msg and msg.video:
                videos.append(msg.video.file_id)
        
        if not videos:
            return await message.reply_text("❌ No videos found in batch.", quote=True)
        
        # Send first video with buttons (same as get_video)
        file_id = videos[0]
        
        # Generate numeric video ID
        import hashlib
        hash_obj = hashlib.md5(file_id.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        video_id = str(hash_int)
        
        # Save metadata
        await db.save_video_metadata(video_id, file_id)
        
        # Load settings
        try:
            AUTO_DEL, DEL_TIMER, HIDE_CAPTION, PROTECT_MODE = await asyncio.gather(
                db.get_auto_delete(),
                db.get_del_timer(),
                db.get_hide_caption(),
                db.get_protect_content(),
            )
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            AUTO_DEL, DEL_TIMER, HIDE_CAPTION, PROTECT_MODE = False, 0, False, True
        
        # Get custom caption
        custom_caption = await db.get_custom_caption()
        if not custom_caption:
            from config import CUSTOM_CAPTION
            custom_caption = CUSTOM_CAPTION or ""
        
        # Get category name
        category_name = await get_category_name(user_id)
        
        # Prepare caption
        caption_parts = []
        if custom_caption:
            caption_parts.append(custom_caption)
        caption_parts.append(f"\n<b>ID: <code>{video_id}</code></b>")
        if category_name:
            caption_parts.append(f"<b>Category: {category_name}</b>")
        final_caption = "\n".join(caption_parts) if not HIDE_CAPTION else f"<b>ID: <code>{video_id}</code></b>" + (f"\n<b>Category: {category_name}</b>" if category_name else "")
        
        # Create buttons (same as get_video)
        # For batch links: if multiple videos in batch, enable nav buttons (playlist behavior).
        show_nav = len(videos) > 1
        start_buttons_enabled = await db.get_start_buttons()
        start_reactions_enabled = await db.get_start_reactions()

        batch_buttons = []
        # Add reaction row only if reactions enabled
        if start_reactions_enabled:
            like_btn = "🤍"
            dislike_btn = "😐"
            mark_btn = "📌"
            try:
                if await db.is_liked(user_id, video_id):
                    like_btn = "❤️"
                if await db.is_disliked(user_id, video_id):
                    dislike_btn = "🦠"
                if await db.is_bookmarked(user_id, video_id):
                    mark_btn = "🔖"
            except:
                pass

            batch_buttons.append([
                InlineKeyboardButton(like_btn, callback_data=f"like_{video_id}"),
                InlineKeyboardButton(dislike_btn, callback_data=f"dislike_{video_id}"),
                InlineKeyboardButton(mark_btn, callback_data=f"mark_{video_id}"),
            ])

        second = []
        # last and next will be handled by next_batch/last_batch callbacks
        # No 'Last' button for the first video (index 0). Navigation will be added when appropriate.
        second.append(InlineKeyboardButton("⬇️ Save", callback_data=f"save_{video_id}"))
        if show_nav and start_buttons_enabled and len(videos) > 1:
            second.append(InlineKeyboardButton("😋 Next", callback_data=f"next_batch_{user_id}_{1}"))

        if second:
            batch_buttons.append(second)

        if not is_premium:
            batch_buttons.append([InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem")])

        reply_markup = InlineKeyboardMarkup(batch_buttons)

        # Respect CHNL_BTN and PROTECT_MODE when sending: override reply_markup to channel button only if CHNL_BTN and button exist
        try:
            AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
                db.get_auto_delete(), db.get_del_timer(), db.get_hide_caption(), db.get_channel_button(), db.get_protect_content()
            )
        except:
            CHNL_BTN = False
            PROTECT_MODE = True

        if CHNL_BTN:
            try:
                button_name, button_link = await db.get_channel_button_link()
                if button_name and button_link:
                    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text=button_name, url=button_link)]])
            except:
                pass        
        # Save as last video
        await save_last_video(user_id, video_id, file_id)
        
        try:
            sent_msg = await client.send_video(
                message.chat.id,
                file_id,
                caption=final_caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                protect_content=PROTECT_MODE
            )
            if AUTO_DEL and sent_msg:
                asyncio.create_task(auto_del_notification(client.username, sent_msg, DEL_TIMER, f"get_video_{user_id}"))
            # Register batch session for navigation
            try:
                await db.set_batch_session(sent_msg.chat.id, sent_msg.id, f_msg_id, s_msg_id, index=0)
            except:
                pass
            return sent_msg
        except Exception as e:
            logging.error(f"Error sending batch video from link: {e}")
            return await message.reply_text("❌ Error sending video.", quote=True)
    except Exception as e:
        logging.error(f"Error in send_batch_from_link: {e}")
        return await message.reply_text("❌ Error processing batch link.", quote=True)

# --- Video Access Control ---
async def get_video(client: Client, message: Message, video_id=None, edit_message=None):
    from pytz import timezone
    ist = timezone("Asia/Kolkata")

    user_id = message.from_user.id
    current_time = datetime.now(ist)

    # Check for active session (5 minutes) - if get_video is triggered again within 5 mins
    # and previous message is still available, reply to that message instead of sending new
    active_session_message = None
    if not edit_message:
        active_session = await db.get_user_session(user_id)
        if active_session:
            try:
                # Try to get the message from the session
                session_message = await client.get_messages(
                    active_session["chat_id"],
                    active_session["message_id"]
                )
                # If message exists, we'll reply to it
                if session_message:
                    active_session_message = session_message
                    logging.info(f"Using active session message for user {user_id} - will reply to it")
            except Exception as e:
                # Message might be deleted or inaccessible, clear session and continue
                logging.info(f"Active session message not available for user {user_id}: {e}")
                await db.clear_user_session(user_id)
                active_session_message = None

    # Spam protection check (skip if editing message)
    if not edit_message:
        is_allowed, remaining_time = await db.check_spam_limit(user_id, "get_video", max_requests=5, time_window=60)
        if not is_allowed:
            if edit_message:
                await edit_message.edit_text(
                    f"⏳ Pʟᴇᴀsᴇ ᴡᴀɪᴛ {remaining_time} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ʀᴇǫᴜᴇsᴛɪɴɢ ᴀɢᴀɪɴ.",
                    protect_content=False
                )
            else:
                return await message.reply_text(
                    f"⏳ Pʟᴇᴀsᴇ ᴡᴀɪᴛ {remaining_time} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ʀᴇǫᴜᴇsᴛɪɴɢ ᴀɢᴀɪɴ.",
                    protect_content=False,
                    quote=True
                )

    # Check premium status FIRST - premium users skip verification
    is_premium = await is_premium_user(user_id)
    
    # For free users, check and deduct usage (but only if not editing - editing means already deducted)
    if not is_premium and not edit_message:
        # Check free limit
        free_limit = await db.get_free_limit(user_id)
        free_enabled = await db.get_free_state(user_id)
        free_count = await db.check_free_usage(user_id)
        
        if not free_enabled:
            buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            if edit_message:
                await edit_message.edit_text(
                    "Yᴏᴜʀ ғʀᴇᴇ ᴘʟᴀɴ ɪs ᴅɪsᴀʙʟᴇᴅ. 🚫\n\nUɴʟᴏᴄᴋ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ᴡɪᴛʜ Pʀᴇᴍɪᴜᴍ!",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    protect_content=False
                )
            else:
                return await message.reply_text(
                    "Yᴏᴜʀ ғʀᴇᴇ ᴘʟᴀɴ ɪs ᴅɪsᴀʙʟᴇᴅ. 🚫\n\nUɴʟᴏᴄᴋ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ᴡɪᴛʜ Pʀᴇᴍɪᴜᴍ!",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    protect_content=False,
                    quote=True
                )
        
        remaining_attempts = free_limit - free_count
        if remaining_attempts <= 0:
            # Out of free limit - show premium message
            buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
            if edit_message:
                await edit_message.edit_text(
                    f"Yᴏᴜ'ᴠᴇ ᴜsᴇᴅ ᴀʟʟ ʏᴏᴜʀ {free_limit} ғʀᴇᴇ ᴠɪᴅᴇᴏs ғᴏʀ ᴛᴏᴅᴀʏ. 🍒\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss!",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    protect_content=False
                )
            else:
                return await message.reply_text(
                    f"Yᴏᴜ'ᴠᴇ ᴜsᴇᴅ ᴀʟʟ ʏᴏᴜʀ {free_limit} ғʀᴇᴇ ᴠɪᴅᴇᴏs ғᴏʀ ᴛᴏᴅᴀʏ. 🍒\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss!",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    protect_content=False,
                    quote=True
                )
        
        # Deduct usage for free users (only on new requests, not edits)
        await db.update_free_usage(user_id)

    if is_premium:
        # Premium users: always unlimited videos (skip verification)
        user_data = await collection.find_one({"user_id": user_id})
        expiration_timestamp = user_data.get("expiration_timestamp") if user_data else None

        # If premium expired, downgrade to free
        if expiration_timestamp:
            expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
            if current_time > expiration_time:
                await collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"expiration_timestamp": None}}
                )
                # Downgrade to free flow - recheck limits
                is_premium = False
                # Now check free limits for downgraded user
                free_limit = await db.get_free_limit(user_id)
                free_enabled = await db.get_free_state(user_id)
                free_count = await db.check_free_usage(user_id)
                
                if not free_enabled or (free_limit - free_count) <= 0:
                    buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
                    if edit_message:
                        await edit_message.edit_text(
                            "Yᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ʜᴀs ᴇxᴘɪʀᴇᴅ. 🚫\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss!",
                            reply_markup=InlineKeyboardMarkup(buttons),
                            protect_content=False
                        )
                    else:
                        return await message.reply_text(
                            "Yᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ʜᴀs ᴇxᴘɪʀᴇᴅ. 🚫\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss!",
                            reply_markup=InlineKeyboardMarkup(buttons),
                            protect_content=False,
                            quote=True
                        )
                
                if not edit_message:
                    await db.update_free_usage(user_id)

        if is_premium:
            # Premium users skip verification - proceed directly
            # Load settings (removed AUTO_DEL and DEL_TIMER)
            try:
                HIDE_CAPTION = await db.get_hide_caption()
            except Exception as e:
                logging.error(f"Error loading settings: {e}")
                HIDE_CAPTION = False

            # Get custom caption (CUSTOM_CAPTION imported at top)
            custom_caption = await db.get_custom_caption()
            if not custom_caption:
                custom_caption = CUSTOM_CAPTION

            # Get or generate video
            new_video_id = video_id
            file_id = None
            sent_msg = None
            
            if not new_video_id:
                # Get random video file_id and generate video_id
                # CATEGORY_CHANNELS, CHANNEL_ID imported at top
                
                # Determine which channel to use based on user category (default is category 0)
                channel_to_use = CATEGORY_CHANNELS[0] if CATEGORY_CHANNELS else CHANNEL_ID
                user_category = await db.get_user_category(user_id)
                if user_category < len(CATEGORY_CHANNELS):
                    channel_to_use = CATEGORY_CHANNELS[user_category]
                
                # Get videos from the user's selected category channel (filtered by category)
                vids = await db.get_videos(channel_id=channel_to_use, sort_by_likes=False)
                if not vids:
                    # Fetch videos from this specific channel
                    await store_videos(client, channel_id=channel_to_use)
                    vids = await db.get_videos(channel_id=channel_to_use, sort_by_likes=False)
                
                if not vids:
                    if edit_message:
                        await edit_message.edit_text("No videos available right now.")
                    else:
                        await message.reply_text("No videos available right now.", quote=True)
                    return
                
                # Get watched videos for this user to prevent repeats
                watched_video_ids = await db.get_watched_videos(user_id)
                
                # Filter out watched videos (convert file_ids to video_ids for comparison)
                unwatched_vids = []
                for vid in vids:
                    file_id = vid.get("file_id")
                    # Generate video_id from file_id to check if watched
                    import hashlib
                    hash_obj = hashlib.md5(file_id.encode())
                    hash_int = int(hash_obj.hexdigest()[:8], 16)
                    vid_id = str(hash_int)
                    
                    if vid_id not in watched_video_ids:
                        unwatched_vids.append(vid)
                
                # If all videos are watched, reset and start fresh
                if not unwatched_vids:
                    await db.clear_watched_videos(user_id)
                    unwatched_vids = vids
                    logging.info(f"All videos watched for user {user_id} in category {channel_to_use}, resetting")
                
                # Preload videos for faster next/last navigation (cache 20 videos from unwatched)
                if user_id not in user_video_cache or len(user_video_cache.get(user_id, [])) < 5:
                    # Cache more videos for this user from unwatched videos
                    cache_size = min(20, len(unwatched_vids))
                    user_video_cache[user_id] = random.sample(unwatched_vids, cache_size) if len(unwatched_vids) > cache_size else unwatched_vids.copy()
                
                # Fast video selection - pick from unwatched videos only
                random_video = random.choice(unwatched_vids)
                file_id = random_video["file_id"]
                
                # Generate numeric video ID
                import hashlib
                hash_obj = hashlib.md5(file_id.encode())
                hash_int = int(hash_obj.hexdigest()[:8], 16)
                new_video_id = str(hash_int)
                
                # Save metadata
                await db.save_video_metadata(new_video_id, file_id)
                
                # Mark video as watched to prevent repeats
                await db.add_watched_video(user_id, new_video_id, channel_to_use)
                
                # Save as last video
                await save_last_video(user_id, new_video_id, file_id)
                
                # Send new video only if not editing and no active session
                if not edit_message and not active_session_message:
                    try:
                        sent_msg = await client.send_video(
                            message.chat.id,
                            file_id,
                            caption="",  # Will be set below
                            reply_markup=None,  # Will be set below
                            protect_content=True  # Disable forward everywhere
                        )
                    except FloodWait as e:
                        await asyncio.sleep(e.x)
                        sent_msg = await client.send_video(
                            message.chat.id,
                            file_id,
                            caption="",
                            reply_markup=None,
                            protect_content=True  # Disable forward everywhere
                        )
                else:
                    sent_msg = edit_message if edit_message else None
            else:
                # Get video by ID (for next/last navigation)
                video_metadata = await db.get_video_metadata(new_video_id)
                if not video_metadata:
                    if edit_message:
                        await edit_message.edit_text("Video not found.")
                    else:
                        await message.reply_text("Video not found.", quote=True)
                    return
                
                file_id = video_metadata.get("file_id")
                
                channel_to_use = CATEGORY_CHANNELS[0] if CATEGORY_CHANNELS else CHANNEL_ID
                user_category = await db.get_user_category(user_id)
                if user_category < len(CATEGORY_CHANNELS):
                    channel_to_use = CATEGORY_CHANNELS[user_category]
                await db.add_watched_video(user_id, new_video_id, channel_to_use)
                
                # Send new video only if not editing and no active session
                if not edit_message and not active_session_message:
                    try:
                        sent_msg = await client.send_video(
                            message.chat.id,
                            file_id,
                            caption="",  
                            reply_markup=None, 
                            protect_content=True
                        )
                    except FloodWait as e:
                        await asyncio.sleep(e.x)
                        sent_msg = await client.send_video(
                            message.chat.id,
                            file_id,
                            caption="",
                            reply_markup=None,
                            protect_content=True
                        )
                else:
                    sent_msg = edit_message if edit_message else None

            # Get category name
            category_name = await get_category_name(user_id)
            
            # Get like and dislike percentage for video
            like_percentage = await db.get_like_percentage(new_video_id)
            dislike_percentage = await db.get_dislike_percentage(new_video_id)
            
            # Prepare caption with video ID, category name, and like/dislike percentage
            caption_parts = []
            if custom_caption:
                caption_parts.append(custom_caption)
            caption_parts.append(f"\n<b>ID: <code>{new_video_id}</code></b>")
            if category_name:
                caption_parts.append(f"<b>Category: {category_name}</b>")
            caption_parts.append(f"<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>")
            final_caption = "\n".join(caption_parts) if not HIDE_CAPTION else f"<b>ID: <code>{new_video_id}</code></b>" + (f"\n<b>Category: {category_name}</b>" if category_name else "") + f"\n<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>"

            # Create buttons (for first video, no last button - but we don't track if it's first in regular flow)
            # For regular videos, we always show both buttons since we don't track position
            reply_markup = await create_video_buttons(
                user_id, 
                new_video_id, 
                is_premium=True,
                is_first=False,
                is_last=False 
            )

            try:
                if edit_message:
                    # Edit the video with new video file
                    success = await edit_video_message(client, edit_message, file_id, final_caption, reply_markup, True)  # Disable forward
                    if not success:
        
                        from pyrogram.errors import MessageNotModified
                        try:
                            await edit_message.edit_caption(
                                caption=final_caption,
                                reply_markup=reply_markup,
                                parse_mode=ParseMode.HTML
                            )
                        except MessageNotModified:
                            try:
                                if reply_markup:
                                    await edit_message.edit_reply_markup(reply_markup=reply_markup)
                            except:
                                pass
                        except Exception as e:
                            logging.error(f"Error editing caption: {e}")
                    # Save session for active message tracking
                    await db.save_user_session(user_id, edit_message.id, edit_message.chat.id)
                    return edit_message
                elif active_session_message:
                    # Only highlight existing message - reply with simple text message (no caption, no buttons)
                    try:
                        await client.send_message(
                            active_session_message.chat.id,
                            "🎬 Your video is there 👇",
                            reply_to_message_id=active_session_message.id
                        )
                    except:
                        pass
                    # Don't save new session - keep existing one
                    return active_session_message
                else:
                    if sent_msg:  # Only edit if sent_msg exists (not None)
                        await sent_msg.edit_caption(
                            caption=final_caption,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.HTML
                        )
                        # Save session for active message tracking
                        await db.save_user_session(user_id, sent_msg.id, sent_msg.chat.id)
                    return sent_msg
            except Exception as e:
                logging.error(f"Error editing/sending video: {e}")
                return sent_msg if not edit_message else edit_message

    # --- Free User Logic ---
    # Check free limit FIRST - if user has points, allow them to use even without verification
    free_limit = await db.get_free_limit(user_id)
    free_enabled = await db.get_free_state(user_id)
    free_count = await db.check_free_usage(user_id)

    if not free_enabled:
        # Free plan disabled
        buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
        return await message.reply_text(
            "Yᴏᴜʀ ғʀᴇᴇ ᴘʟᴀɴ ɪs ᴅɪsᴀʙʟᴇᴅ. 🚫\n\nUɴʟᴏᴄᴋ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ᴡɪᴛʜ Pʀᴇᴍɪᴜᴍ!",
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False,
            quote=True
        )

    remaining_attempts = free_limit - free_count

    if remaining_attempts <= 0:
        # Out of free limit - now check verification
        try:
            VERIFY_EXPIRE = await db.get_verified_time()
        except Exception as e:
            logging.error(f"Error fetching verify expiry config: {e}")
            VERIFY_EXPIRE = None

        if VERIFY_EXPIRE is not None:
            # Fetch verify status for free users
            try:
                verify_status = await db.get_verify_status(user_id) or {}
            except Exception as e:
                logging.error(f"Error fetching verify status for {user_id}: {e}")
                verify_status = {"is_verified": False, "verified_time": 0, "verify_token": "", "link": ""}

            # Handle expired verification
            try:
                if verify_status.get("is_verified") and VERIFY_EXPIRE:
                    verified_time = verify_status.get("verified_time", 0)
                    if (time.time() - verified_time) > VERIFY_EXPIRE:
                        await db.update_verify_status(user_id, is_verified=False)
                        verify_status["is_verified"] = False
            except Exception as e:
                logging.error(f"Error while checking/refreshing verify expiry for {user_id}: {e}")

            # Verification check for free users (only if no points left)
            if not verify_status.get("is_verified", False):
                try:
                    shortener_url = await db.get_shortener_url()
                    shortener_api = await db.get_shortener_api()
                    
                    if shortener_url and shortener_api:
                        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        await db.update_verify_status(user_id, verify_token=token, link="")
                        
                        long_url = f"https://telegram.dog/{client.username}?start=verify_{token}"
                        short_link = await get_shortlink(long_url)
                        
                        tut_vid_url = await db.get_tut_video() or TUT_VID
                        
                        btn = [
                            [InlineKeyboardButton("Click here", url=short_link),
                             InlineKeyboardButton('How to use the bot', url=tut_vid_url)],
                            [InlineKeyboardButton('BUY PREMIUM', callback_data='buy_prem')]
                        ]
                        
                        verify_msg = (
                            f"Your ads token is expired or invalid. Please verify to access the files.\n\n"
                            f"Token Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\n"
                            f"What is the token?\n\n"
                            f"This is an ads token. By passing 1 ad, you can use the bot for  {get_exp_time(VERIFY_EXPIRE)}."
                        )
                        
                        # Edit message if edit_message provided, otherwise send new
                        if edit_message:
                            try:
                                await edit_message.edit_text(
                                    verify_msg,
                                    reply_markup=InlineKeyboardMarkup(btn),
                                    protect_content=False
                                )
                                return
                            except:
                                pass
                        
                        return await message.reply(
                            verify_msg,
                            reply_markup=InlineKeyboardMarkup(btn),
                            protect_content=False
                        )
                except Exception as e:
                    logging.error(f"Error in verification process: {e}")
                    buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
                    error_msg = "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ ʏᴏᴜʀ ᴛᴏᴋᴇɴ ғɪʀsᴛ. Pʟᴇᴀsᴇ ᴜsᴇ /start ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ."
                    
                    if edit_message:
                        try:
                            await edit_message.edit_text(
                                error_msg,
                                reply_markup=InlineKeyboardMarkup(buttons),
                                protect_content=False
                            )
                            return
                        except:
                            pass
                    
                    return await message.reply_text(
                        error_msg,
                        reply_markup=InlineKeyboardMarkup(buttons),
                        protect_content=False,
                        quote=True
                    )
        
        # No points left and no verification
        buttons = [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
        error_msg = f"Yᴏᴜ'ᴠᴇ ᴜsᴇᴅ ᴀʟʟ ʏᴏᴜʀ {free_limit} ғʀᴇᴇ ᴠɪᴅᴇᴏs ғᴏʀ ᴛᴏᴅᴀʏ. 🍒\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss!"
        
        if edit_message:
            try:
                await edit_message.edit_text(
                    error_msg,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    protect_content=False
                )
                return
            except:
                pass
        
        return await message.reply_text(
            error_msg,
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False,
            quote=True
        )

    if remaining_attempts == 1:
        if not edit_message:
            await message.reply_text(
                "⚠️ Tʜɪs ɪs ʏᴏᴜʀ ʟᴀsᴛ ғʀᴇᴇ ᴠɪᴅᴇᴏ ғᴏʀ ᴛᴏᴅᴀʏ.\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ғᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴠɪᴅᴇᴏs!",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="buy_prem")]]
                ),
                protect_content=False,
                quote=True
            )

    # Load settings for free users
    try:
        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, PROTECT_MODE = await asyncio.gather(
            db.get_auto_delete(),
            db.get_del_timer(),
            db.get_hide_caption(),
            db.get_protect_content(),
        )
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        AUTO_DEL, DEL_TIMER, HIDE_CAPTION, PROTECT_MODE = False, 0, False, True

    # Get custom caption (CUSTOM_CAPTION imported at top)
    custom_caption = await db.get_custom_caption()
    if not custom_caption:
        custom_caption = CUSTOM_CAPTION

    # Deduct usage only if not editing (editing means user already used their quota)
    if not edit_message:
        await db.update_free_usage(user_id)
    
    # Get or generate video
    new_video_id = video_id
    file_id = None
    sent_msg = None
    
    if not new_video_id:
        channel_to_use = CATEGORY_CHANNELS[0] if CATEGORY_CHANNELS else CHANNEL_ID
        user_category = await db.get_user_category(user_id)
        if user_category < len(CATEGORY_CHANNELS):
            channel_to_use = CATEGORY_CHANNELS[user_category]
        
        # Get videos from the user's selected category channel (filtered by category)
        vids = await db.get_videos(channel_id=channel_to_use, sort_by_likes=False)
        if not vids:
            # Fetch videos from this specific channel
            await store_videos(client, channel_id=channel_to_use)
            vids = await db.get_videos(channel_id=channel_to_use, sort_by_likes=False)
        
        if not vids:
            if edit_message:
                await edit_message.edit_text("No videos available right now.")
            else:
                await message.reply_text("No videos available right now.", quote=True)
            return
        
        # Get watched videos for this user to prevent repeats
        watched_video_ids = await db.get_watched_videos(user_id)
        
        # Filter out watched videos (convert file_ids to video_ids for comparison)
        unwatched_vids = []
        for vid in vids:
            file_id = vid.get("file_id")
            # Generate video_id from file_id to check if watched
            import hashlib
            hash_obj = hashlib.md5(file_id.encode())
            hash_int = int(hash_obj.hexdigest()[:8], 16)
            vid_id = str(hash_int)
            
            if vid_id not in watched_video_ids:
                unwatched_vids.append(vid)
        
        # If all videos are watched, reset and start fresh
        if not unwatched_vids:
            await db.clear_watched_videos(user_id)
            unwatched_vids = vids
            logging.info(f"All videos watched for user {user_id} in category {channel_to_use}, resetting")
        
        # Preload videos for faster next/last navigation (cache 20 videos from unwatched)
        if user_id not in user_video_cache or len(user_video_cache.get(user_id, [])) < 5:
            # Cache more videos for this user from unwatched videos
            cache_size = min(20, len(unwatched_vids))
            user_video_cache[user_id] = random.sample(unwatched_vids, cache_size) if len(unwatched_vids) > cache_size else unwatched_vids.copy()
        
        # Fast video selection - pick from unwatched videos only
        random_video = random.choice(unwatched_vids)
        file_id = random_video["file_id"]
        
        # Generate numeric video ID
        import hashlib
        hash_obj = hashlib.md5(file_id.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        new_video_id = str(hash_int)
        
        # Save metadata
        await db.save_video_metadata(new_video_id, file_id)
        
        # Mark video as watched to prevent repeats
        await db.add_watched_video(user_id, new_video_id, channel_to_use)
        
        # Save as last video
        await save_last_video(user_id, new_video_id, file_id)
        
        # Send new video only if not editing and no active session
        if not edit_message and not active_session_message:
            try:
                sent_msg = await client.send_video(
                    message.chat.id,
                    file_id,
                    caption="", 
                    reply_markup=None, 
                    protect_content=True                  )
            except FloodWait as e:
                await asyncio.sleep(e.x)
                sent_msg = await client.send_video(
                    message.chat.id,
                    file_id,
                    caption="",
                    reply_markup=None,
                    protect_content=True  # Disable forward everywhere
                )
        else:
            sent_msg = edit_message if edit_message else None
    else:
        # Get video by ID
        video_metadata = await db.get_video_metadata(new_video_id)
        if not video_metadata:
            if edit_message:
                await edit_message.edit_text("Video not found.")
            else:
                await message.reply_text("Video not found.", quote=True)
            return
        
        file_id = video_metadata.get("file_id")
   
        if not edit_message and not active_session_message:
            try:
                sent_msg = await client.send_video(
                    message.chat.id,
                    file_id,
                    caption="",  # Will be set below
                    reply_markup=None,  # Will be set below
                    protect_content=PROTECT_MODE
                )
            except FloodWait as e:
                await asyncio.sleep(e.x)
                sent_msg = await client.send_video(
                    message.chat.id,
                    file_id,
                    caption="",
                    reply_markup=None,
                    protect_content=PROTECT_MODE
                )
        elif edit_message:
            sent_msg = edit_message
        else:
            # Will reply to active_session_message later
            sent_msg = None

    # Get category name (for free users too, if they have one set)
    category_name = await get_category_name(user_id)
    
    # Get like and dislike percentage for video
    like_percentage = await db.get_like_percentage(new_video_id)
    dislike_percentage = await db.get_dislike_percentage(new_video_id)
    
    # Prepare caption with video ID, category name, and like/dislike percentage
    caption_parts = []
    if custom_caption:
        caption_parts.append(custom_caption)
    caption_parts.append(f"\n<b>ID: <code>{new_video_id}</code></b>")
    if category_name:
        caption_parts.append(f"<b>Category: {category_name}</b>")
    caption_parts.append(f"<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>")
    final_caption = "\n".join(caption_parts) if not HIDE_CAPTION else f"<b>ID: <code>{new_video_id}</code></b>" + (f"\n<b>Category: {category_name}</b>" if category_name else "") + f"\n<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>"

    # Create buttons (Change Category button shown to all, but only premium can use it)
    reply_markup = await create_video_buttons(
        user_id, 
        new_video_id, 
        is_premium=False,
        is_first=False,  # Regular videos always show last button
        is_last=False    # Regular videos always show next button
    )

    # Edit or send message (or reply to active session)
    try:
        if edit_message:
            # Edit the video with new video file
            success = await edit_video_message(client, edit_message, file_id, final_caption, reply_markup, True)  # Disable forward
            if not success:
                # Fallback: edit caption only if video edit fails
                from pyrogram.errors import MessageNotModified
                try:
                    await edit_message.edit_caption(
                        caption=final_caption,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                except MessageNotModified:
                    # Message already correct, just update buttons if needed
                    try:
                        if reply_markup:
                            await edit_message.edit_reply_markup(reply_markup=reply_markup)
                    except:
                        pass
                except Exception as e:
                    logging.error(f"Error editing caption: {e}")
            # Save session for active message tracking
            await db.save_user_session(user_id, edit_message.id, edit_message.chat.id)
        elif active_session_message:
            # Only highlight existing message - reply with simple text message (no caption, no buttons)
            try:
                await client.send_message(
                    active_session_message.chat.id,
                    "🎬 Your video is there 👇",
                    reply_to_message_id=active_session_message.id
                )
            except:
                pass
            # Don't save new session - keep existing one
            return
        else:
            await sent_msg.edit_caption(
                caption=final_caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            # Save session for active message tracking
            await db.save_user_session(user_id, sent_msg.id, sent_msg.chat.id)
    except Exception as e:
        logging.error(f"Error editing/sending video: {e}")

# --- Bookmark Command ---
async def get_bookmarked_videos(client: Client, message: Message, bookmark_index: int = 0, edit_message: Message = None):
    """Display bookmarked videos with navigation - Premium only"""
    user_id = message.from_user.id
    is_premium = await is_premium_user(user_id)
    
    # Premium check - bookmark command is premium only
    if not is_premium:
        buttons = [[InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem")]]
        return await message.reply_text(
            "💳 Tʜɪs ғᴇᴀᴛᴜʀᴇ ɪs ᴀᴠᴀɪʟᴀʙʟᴇ ғᴏʀ Pʀᴇᴍɪᴜᴍ ᴜsᴇʀs ᴏɴʟʏ.\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ᴛᴏ ᴠɪᴇᴡ ʏᴏᴜʀ ʙᴏᴏᴋᴍᴀʀᴋs!",
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )
    
    bookmarked_video_ids = await db.get_bookmarked_videos(user_id)
    
    if not bookmarked_video_ids:
        buttons = []
        if not is_premium:
            buttons.append([InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem")])
        return await message.reply_text(
            "🔖 Yᴏᴜ ʜᴀᴠᴇ ɴᴏ ʙᴏᴏᴋᴍᴀʀᴋᴇᴅ ᴠɪᴅᴇᴏs.\n\nUsᴇ ᴛʜᴇ 🔖 ʙᴜᴛᴛᴏɴ ᴛᴏ ᴍᴀʀᴋ ᴠɪᴅᴇᴏs.",
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
            quote=True
        )
    
    # Validate index
    if bookmark_index < 0:
        bookmark_index = 0
    if bookmark_index >= len(bookmarked_video_ids):
        bookmark_index = len(bookmarked_video_ids) - 1
    
    # Get video at index
    video_id = bookmarked_video_ids[bookmark_index]
    video_metadata = await db.get_video_metadata(video_id)
    
    if not video_metadata:
        return await message.reply_text("❌ Vɪᴅᴇᴏ ɴᴏᴛ ғᴏᴜɴᴅ.", quote=True)
    
    file_id = video_metadata.get("file_id")
    
    # Load settings (removed AUTO_DEL and DEL_TIMER)
    try:
        HIDE_CAPTION = await db.get_hide_caption()
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        HIDE_CAPTION = False
    
    # Get custom caption (CUSTOM_CAPTION imported at top)
    custom_caption = await db.get_custom_caption()
    if not custom_caption:
        custom_caption = CUSTOM_CAPTION or ""
    
    # Get category name
    category_name = await get_category_name(user_id)
    
    # Get like and dislike percentage for video
    like_percentage = await db.get_like_percentage(video_id)
    dislike_percentage = await db.get_dislike_percentage(video_id)
    
    # Prepare caption with video ID, category name, and like/dislike percentage
    caption_parts = []
    if custom_caption:
        caption_parts.append(custom_caption)
    caption_parts.append(f"\n<b>ID: <code>{video_id}</code></b>")
    if category_name:
        caption_parts.append(f"<b>Category: {category_name}</b>")
    caption_parts.append(f"<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>")
    final_caption = "\n".join(caption_parts) if not HIDE_CAPTION else f"<b>ID: <code>{video_id}</code></b>" + (f"\n<b>Category: {category_name}</b>" if category_name else "") + f"\n<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>"
    
    # Create buttons with bookmark context
    is_first = bookmark_index == 0
    is_last = bookmark_index == len(bookmarked_video_ids) - 1
    reply_markup = await create_video_buttons(
        user_id, 
        video_id, 
        is_premium=is_premium,
        is_first=is_first,
        is_last=is_last,
        is_bookmark_context=True,
        bookmark_index=bookmark_index,
        bookmark_total=len(bookmarked_video_ids)
    )
    
    try:
        if edit_message:
            # Edit existing message
            success = await edit_video_message(client, edit_message, file_id, final_caption, reply_markup, True)  # Disable forward
            if not success:
                await edit_message.edit_caption(
                    caption=final_caption,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            return edit_message
        else:
            # Send new message
            sent_msg = await client.send_video(
                message.chat.id,
                file_id,
                caption=final_caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                protect_content=True  # Disable forward everywhere
            )
            return sent_msg
    except Exception as e:
        logging.error(f"Error sending bookmarked video: {e}")
        if edit_message:
            return edit_message
        return await message.reply_text("❌ Eʀʀᴏʀ sᴇɴᴅɪɴɢ ᴠɪᴅᴇᴏ.", quote=True)

#=====================================================================================##

WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""

#=====================================================================================##


# Global cache for chat data to reduce API calls
chat_data_cache = {}

async def not_joined(client: Client, message: Message):
    temp = await message.reply(f"<b>??</b>")

    user_id = message.from_user.id

    REQFSUB = await db.get_request_forcesub()
    buttons = []
    count = 0

    try:
        for total, chat_id in enumerate(await db.get_all_channels(), start=1):
            await message.reply_chat_action(ChatAction.PLAYING)

            # Show the join button of non-subscribed Channels.....
            if not await is_userJoin(client, user_id, chat_id):
                try:
                    # Check if chat data is in cache
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]  # Get data from cache
                    else:
                        data = await client.get_chat(chat_id)  # Fetch from API
                        chat_data_cache[chat_id] = data  # Store in cache

                    cname = data.title

                    # Handle private channels and links
                    if REQFSUB and not data.username: 
                        link = await db.get_stored_reqLink(chat_id)
                        await db.add_reqChannel(chat_id)

                        if not link:
                            link = (await client.create_chat_invite_link(chat_id=chat_id, creates_join_request=True)).invite_link
                            await db.store_reqLink(chat_id, link)
                    else:
                        link = data.invite_link

                    # Add button for the chat
                    buttons.append([InlineKeyboardButton(text=cname, url=link)])
                    count += 1
                    await temp.edit(f"<b>{'! ' * count}</b>")

                except Exception as e:
                    print(f"Can't Export Channel Name and Link..., Please Check If the Bot is admin in the FORCE SUB CHANNELS:\nProvided Force sub Channel:- {chat_id}")
                    return await temp.edit(f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @rohit_1888</i></b>\n<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>")

        await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        print(f"Error: {e}")  # Print the error message for debugging
        # Optionally, send an error message to the user or handle further actions here
        await temp.edit(f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @rohit_1888</i></b>\n<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>")


@Bot.on_message(filters.command('users') & filters.private & filters.user(OWNER_ID))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await db.full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")


@Bot.on_message(filters.command('status') & filters.private & is_admin)
async def info(client: Bot, message: Message):   
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("• Close •", callback_data="close")]]
    )

    # Measure ping
    start_time = time.time()
    temp_msg = await message.reply(
        "<b><i>Processing...</i></b>", 
        quote=True, 
        parse_mode=ParseMode.HTML
    )
    end_time = time.time()
    ping_time = (end_time - start_time) * 1000

    # User count
    users = await db.full_userbase()

    # Uptime - use IST timezone to match client.uptime
    try:
        ist = timezone("Asia/Kolkata")
        now = datetime.now(ist)
        # Ensure client.uptime is timezone-aware
        if hasattr(client, 'uptime') and client.uptime:
            uptime = client.uptime
            if uptime.tzinfo is None:
                uptime = ist.localize(uptime)
            delta = now - uptime
            bottime = get_readable_time(int(delta.total_seconds()))
        else:
            bottime = "N/A"
    except Exception as e:
        logging.error(f"Error calculating uptime: {e}")
        bottime = "N/A"

    # Edit message with final status
    await temp_msg.edit(
        f"<b>Users: {len(users)}\n\n"
        f"Uptime: {bottime}\n\n"
        f"Ping: {ping_time:.2f} ms</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

#--------------------------------------------------------------[[ADMIN COMMANDS]]---------------------------------------------------------------------------#
# Handler for the /cancel command
cancel_lock = asyncio.Lock()
is_canceled = False


@Bot.on_message(filters.command('cancel') & filters.private & is_admin)
async def cancel_broadcast(client: Bot, message: Message):
    global is_canceled
    async with cancel_lock:
        is_canceled = True

@Bot.on_message(filters.private & filters.command('broadcast') & is_admin)
async def broadcast(client: Bot, message: Message):
    global is_canceled
    args = message.text.split()[1:]

    if not message.reply_to_message:
        msg = await message.reply(
            "Reply to a message to broadcast.\n\nUsage examples:\n"
            "`/broadcast normal`\n"
            "`/broadcast pin`\n"
            "`/broadcast delete 30`\n"
            "`/broadcast pin delete 30`\n"
            "`/broadcast silent`\n"
        )
        await asyncio.sleep(8)
        return await msg.delete()

    # Defaults
    do_pin = False
    do_delete = False
    duration = 0
    silent = False
    mode_text = []

    i = 0
    while i < len(args):
        arg = args[i].lower()
        if arg == "pin":
            do_pin = True
            mode_text.append("PIN")
        elif arg == "delete":
            do_delete = True
            try:
                duration = int(args[i + 1])
                i += 1
            except (IndexError, ValueError):
                return await message.reply("<b>Provide valid duration for delete mode.</b>\nUsage: `/broadcast delete 30`")
            mode_text.append(f"DELETE({duration}s)")
        elif arg == "silent":
            silent = True
            mode_text.append("SILENT")
        else:
            mode_text.append(arg.upper())
        i += 1

    if not mode_text:
        mode_text.append("NORMAL")

    # Reset cancel flag
    async with cancel_lock:
        is_canceled = False

    query = await db.full_userbase()
    broadcast_msg = message.reply_to_message
    total = len(query)
    successful = blocked = deleted = unsuccessful = 0

    pls_wait = await message.reply(f"<i>Broadcasting in <b>{' + '.join(mode_text)}</b> mode...</i>")

    bar_length = 20
    progress_bar = ''
    last_update_percentage = 0
    update_interval = 0.05  # 5%

    for i, chat_id in enumerate(query, start=1):
        async with cancel_lock:
            if is_canceled:
                await pls_wait.edit(f"›› BROADCAST ({' + '.join(mode_text)}) CANCELED ❌")
                return

        try:
            sent_msg = await broadcast_msg.copy(chat_id, disable_notification=silent)

            if do_pin:
                await client.pin_chat_message(chat_id, sent_msg.id, both_sides=True)
            if do_delete:
                asyncio.create_task(auto_delete(sent_msg, duration))

            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                sent_msg = await broadcast_msg.copy(chat_id, disable_notification=silent)
                if do_pin:
                    await client.pin_chat_message(chat_id, sent_msg.id, both_sides=True)
                if do_delete:
                    asyncio.create_task(auto_delete(sent_msg, duration))
                successful += 1
            except:
                unsuccessful += 1
        except UserIsBlocked:
            await db.del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await db.del_user(chat_id)
            deleted += 1
        except:
            unsuccessful += 1
            await db.del_user(chat_id)

        # Progress
        percent_complete = i / total
        if percent_complete - last_update_percentage >= update_interval or last_update_percentage == 0:
            num_blocks = int(percent_complete * bar_length)
            progress_bar = "●" * num_blocks + "○" * (bar_length - num_blocks)
            status_update = f"""<b>›› BROADCAST ({' + '.join(mode_text)}) IN PROGRESS...

<blockquote>⏳:</b> [{progress_bar}] <code>{percent_complete:.0%}</code></blockquote>

<b>›› Total Users: <code>{total}</code>
›› Successful: <code>{successful}</code>
›› Blocked: <code>{blocked}</code>
›› Deleted: <code>{deleted}</code>
›› Unsuccessful: <code>{unsuccessful}</code></b>

<i>➪ To stop broadcasting click: <b>/cancel</b></i>"""
            await pls_wait.edit(status_update)
            last_update_percentage = percent_complete

    # Final status
    final_status = f"""<b>›› BROADCAST ({' + '.join(mode_text)}) COMPLETED ✅

<blockquote>Dᴏɴᴇ:</b> [{progress_bar}] {percent_complete:.0%}</blockquote>

<b>›› Total Users: <code>{total}</code>
›› Successful: <code>{successful}</code>
›› Blocked: <code>{blocked}</code>
›› Deleted: <code>{deleted}</code>
›› Unsuccessful: <code>{unsuccessful}</code></b>"""
    return await pls_wait.edit(final_status)


# helper for delete mode
async def auto_delete(sent_msg, duration):
    await asyncio.sleep(duration)
    try:
        await sent_msg.delete()
    except:
        pass



# Command to add premium user
@Bot.on_message(filters.command('addpaid') & filters.private & is_admin)
async def add_premium_user_command(client, msg):
    if len(msg.command) != 4:
        await msg.reply_text("Usage: /addpaid (user_id) time_value time_unit (m/d)")
        return

    try:
        user_id = int(msg.command[1])
        time_value = int(msg.command[2])
        time_unit = msg.command[3].lower()  # 'm' or 'd'

        # Call add_premium function
        expiration_time = await add_premium(user_id, time_value, time_unit)

        # Notify the admin about the premium activation
        await msg.reply_text(
            f"User {user_id} added as a premium user for {time_value} {time_unit}.\n"
            f"Expiration Time: {expiration_time}"
        )

        # Notify the user about their premium status
        await client.send_message(
            chat_id=user_id,
            text=(
                f"🎉 Congratulations! You have been upgraded to premium for {time_value} {time_unit}.\n\n"
                f"Expiration Time: {expiration_time}.\n\n"
                f"Happy Downloading 💦"
            ),
        )

    except ValueError:
        await msg.reply_text("Invalid input. Please check the user_id, time_value, and time_unit.")
    except Exception as e:
        await msg.reply_text(f"An error occurred: {str(e)}")


# Command to remove premium user
@Bot.on_message(filters.command('removepaid') & filters.private & is_admin)
async def pre_remove_user(client: Client, msg: Message):
    if len(msg.command) != 2:
        await msg.reply_text("useage: /removeuser user_id ")
        return
    try:
        user_id = int(msg.command[1])
        await remove_premium(user_id)
        await msg.reply_text(f"User {user_id} has been removed.")
    except ValueError:
        await msg.reply_text("user_id must be an integer or not available in database.")


# Command to list active premium users
@Bot.on_message(filters.command('listpaid') & filters.private & is_admin)
async def list_premium_users_command(client, message):
    # Define IST timezone
    ist = timezone("Asia/Kolkata")

    # Retrieve all users from the collection
    premium_users_cursor = collection.find({})
    premium_user_list = ['<b>Active Premium Users in database:</b>']
    current_time = datetime.now(ist)  # Get current time in IST

    # Use async for to iterate over the async cursor
    async for user in premium_users_cursor:
        user_id = user.get("user_id")
        expiration_timestamp = user.get("expiration_timestamp")

        if not expiration_timestamp:
            # If expiry missing, clean up
            await collection.delete_one({"user_id": user_id})
            continue

        try:
            # Convert expiration_timestamp to datetime
            expiration_time = datetime.fromisoformat(str(expiration_timestamp)).astimezone(ist)
            remaining_time = expiration_time - current_time

            if remaining_time.total_seconds() <= 0:
                # Expired → remove from DB
                await collection.delete_one({"user_id": user_id})
                continue

            # Try fetching Telegram user details
            try:
                user_info = await client.get_users(user_id)
                username = f"@{user_info.username}" if user_info.username else "No Username"
                first_name = user_info.first_name or "N/A"
            except Exception:
                username = "Unknown"
                first_name = "Unknown"

            # Calculate days, hours, minutes, seconds left
            days, hours, minutes, seconds = (
                remaining_time.days,
                remaining_time.seconds // 3600,
                (remaining_time.seconds // 60) % 60,
                remaining_time.seconds % 60,
            )
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"

            # Add user details to the list
            premium_user_list.append(
                f"👤 <b>UserID:</b> <code>{user_id}</code>\n"
                f"🔗 <b>User:</b> {username}\n"
                f"📛 <b>Name:</b> <code>{first_name}</code>\n"
                f"⏳ <b>Expiry:</b> {expiry_info}"
            )

        except Exception as e:
            # Log users that fail due to bad timestamp or parse error
            premium_user_list.append(
                f"⚠️ <b>UserID:</b> <code>{user_id}</code>\n"
                f"Error: Unable to fetch details ({str(e)})"
            )

    if len(premium_user_list) == 1:  # Only header present
        await message.reply_text("I found 0 active premium users in my DB")
    else:
        await message.reply_text("\n\n".join(premium_user_list), parse_mode=ParseMode.HTML)

@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id  # Get user ID from the message

    # Get the premium status of the user
    status_message = await check_user_plan(user_id)

    # Send the response message to the user
    await message.reply(status_message)

@Bot.on_message(filters.command('forcesub') & filters.private & ~banUser)
async def fsub_commands(client: Client, message: Message):
    button = [[InlineKeyboardButton("Cʟᴏsᴇ ✖️", callback_data="close")]]
    await message.reply(text=FSUB_CMD_TXT, reply_markup=InlineKeyboardMarkup(button), quote=True)


@Bot.on_message(filters.command('help') & filters.private & ~banUser)
async def help(client: Client, message: Message):
    buttons = [
        [
            InlineKeyboardButton("🤖 Oᴡɴᴇʀ", url=f"tg://openmessage?user_id={OWNER_ID}"), 
            InlineKeyboardButton("🥰 Dᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/rohit1888")
        ]
    ]
    
    try:
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo = FORCE_PIC,
            caption = HELP_TEXT.format(
                first = message.from_user.first_name,
                last = message.from_user.last_name,
                username = None if not message.from_user.username else '@' + message.from_user.username,
                mention = message.from_user.mention,
                id = message.from_user.id
            ),
            reply_markup = reply_markup#,
            #message_effect_id = 5046509860389126442 #🎉
        )
    except Exception as e:
        return await message.reply(f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @rohit_1888</i></b>\n<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>")

@Bot.on_message(filters.command('short') & filters.private & is_admin)
async def shorten_link_command(client, message):
    id = message.from_user.id

    try:
        # Prompt the user to send the link to be shortened
        set_msg = await client.ask(
            chat_id=id,
            text="<b><blockquote>⏳ Sᴇɴᴅ ᴀ ʟɪɴᴋ ᴛᴏ ʙᴇ sʜᴏʀᴛᴇɴᴇᴅ</blockquote>\n\nFᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>https://example.com/long_url</code></b>",
            timeout=60
        )

        # Validate the user input for a valid URL
        original_url = set_msg.text.strip()

        if original_url.startswith("http") and "://" in original_url:
            try:
                # Call the get_shortlink function
                short_link = await get_shortlink(original_url)

                # Inform the user about the shortened link
                await set_msg.reply(f"<b>🔗 Lɪɴᴋ Cᴏɴᴠᴇʀᴛᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ ✅</b>\n\n<blockquote>🔗 Sʜᴏʀᴛᴇɴᴇᴅ Lɪɴᴋ: <code>{short_link}</code></blockquote>")
            except ValueError as ve:
                # If shortener details are missing
                await set_msg.reply(f"<b>❌ Error: {ve}</b>")
            except Exception as e:
                # Handle errors during the shortening process
                await set_msg.reply(f"<b>❌ Error while shortening the link:\n<code>{e}</code></b>")
        else:
            # If the URL is invalid, prompt the user to try again
            await set_msg.reply("<b>❌ Invalid URL. Please send a valid link that starts with 'http'.</b>")

    except asyncio.TimeoutError:
        # Handle timeout exceptions
        await client.send_message(
            id,
            text="<b>⏳ Tɪᴍᴇᴏᴜᴛ. Yᴏᴜ ᴛᴏᴏᴋ ᴛᴏᴏ ʟᴏɴɢ ᴛᴏ ʀᴇsᴘᴏɴᴅ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.</b>",
            disable_notification=True
        )
        print(f"! Timeout occurred for user ID {id} while processing '/shorten' command.")

    except Exception as e:
        # Handle any other exceptions
        await client.send_message(
            id,
            text=f"<b>❌ Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:\n<code>{e}</code></b>",
            disable_notification=True
        )
        print(f"! Error occurred on '/short' command: {e}")


@Bot.on_message(filters.command("check"))
async def check_command(client, message):
    user_id = message.from_user.id

    verify_status = await db.get_verify_status(user_id)
    logging.info(f"Verify status for user {user_id}: {verify_status}")

    try:
        VERIFY_EXPIRE = await db.get_verified_time()
    except Exception as e:
        logging.error(f"Error fetching verify expiry config: {e}")
        VERIFY_EXPIRE = None

    if verify_status.get('is_verified') and VERIFY_EXPIRE:
        expiry_time = get_exp_time(VERIFY_EXPIRE - (time.time() - verify_status.get('verified_time', 0)))
        await message.reply(f"Your token is verified and valid for {expiry_time}.")
    else:
        await message.reply("Your token is not verified or has expired , /start to generate! Verify token....")


@Bot.on_message(filters.command("set_free_limit") & is_admin)
async def set_free_limit(client: Client, message: Message):
    try:
        limit = int(message.text.split()[1])
        await db.set_free_limit(limit=limit)
        await message.reply(f"✅ Free usage limit has been set to {limit}.")
    except (IndexError, ValueError):
        await message.reply("❌ Invalid usage. Use the command like this:\n`/set_free_limit 10`")


@Bot.on_message(filters.command('free') & filters.private & is_admin)
async def toggle_freemode(client: Client, message: Message):
    await message.reply_chat_action(ChatAction.TYPING)

    # Check the current caption state (enabled or disabled)
    current_state = await db.get_free_state(message.from_user.id)

    # Toggle the state
    new_state = not current_state
    await db.set_free_state(message.from_user.id, new_state)

    # Create buttons for ✅ and ❌ based on the new state
    caption_button = InlineKeyboardButton(
        text="✅ Free Enabled" if new_state else "❌ Free  Disabled", 
        callback_data="toggle_caption"
    )

    # Send a message with the toggle button
    await message.reply_text(
        f"Free Mode is now {'enabled' if new_state else 'disabled'}.",
        reply_markup=InlineKeyboardMarkup([
            [caption_button]
        ])
    )


@Bot.on_message(filters.command("stats") & is_admin)
async def stats_command(client, message):
    total_users = await db.full_userbase()
    verified_users = await db.full_userbase({"verify_status.is_verified": True})
    unverified_users = total_users - verified_users

    free_settings = await db.get_free_settings()
    free_limit = free_settings["limit"]
    free_enabled = free_settings["enabled"]

    status = f"""<b><u>Verification Stats</u></b>

Total Users: <code>{total_users}</code>
Verified Users: <code>{verified_users}</code>
Unverified Users: <code>{unverified_users}</code>

<b><u>Free Usage Settings</u></b>
Free Usage Limit: <code>{free_limit}</code>
Free Usage Enabled: <code>{free_enabled}</code>"""

    await message.reply(status)


# Referral command removed - functionality disabled


@Bot.on_message(filters.command("fetch") & filters.private & is_admin)
async def fetch_videos_command(client: Client, message: Message):
    """Fetch/update videos from all category channels with progress bar"""
    from config import CATEGORY_CHANNELS, CHANNEL_ID, OWNER_ID
    
    admin_id = message.from_user.id
    pls_wait = await message.reply_text("🔄 Starting video fetch process...")
    
    try:
        channels_to_fetch = CATEGORY_CHANNELS if CATEGORY_CHANNELS else [CHANNEL_ID]
        total_channels = len(channels_to_fetch)
        total_videos_fetched = 0
        
        status_msg = f"<b>📥 Fetching Videos...</b>\n\n"
        status_msg += f"<b>Channels to process:</b> {total_channels}\n"
        status_msg += f"<b>Progress:</b> 0/{total_channels} channels\n"
        status_msg += f"<b>Videos fetched:</b> 0"
        await pls_wait.edit(status_msg)
        
        for idx, channel_id in enumerate(channels_to_fetch):
            try:
                # Update progress
                progress_percent = int((idx / total_channels) * 100)
                progress_bar = "█" * int(progress_percent / 5) + "░" * (20 - int(progress_percent / 5))
                
                status_msg = f"<b>📥 Fetching Videos...</b>\n\n"
                status_msg += f"<b>Channel:</b> {idx + 1}/{total_channels}\n"
                status_msg += f"<b>Progress:</b> [{progress_bar}] {progress_percent}%\n"
                status_msg += f"<b>Videos fetched so far:</b> {total_videos_fetched}\n\n"
                status_msg += f"<i>Processing channel {channel_id}...</i>"
                await pls_wait.edit(status_msg)
                
                # Fetch videos from this channel
                await store_videos(client, channel_id=channel_id)
                
                # Get updated total count (more efficient than summing)
                total_videos_fetched = await db.videos_collection.count_documents({})
                
            except Exception as e:
                logging.error(f"Error fetching from channel {channel_id}: {e}")
                continue
        
        # Get final count
        final_count = await db.videos_collection.count_documents({})
        
        # Final status
        final_status = f"<b>✅ Video Fetch Completed!</b>\n\n"
        final_status += f"<b>Channels processed:</b> {total_channels}\n"
        final_status += f"<b>Total videos in database:</b> {final_count}\n\n"
        final_status += f"<i>All videos have been updated from category channels.</i>"
        await pls_wait.edit(final_status)
        
        # Notify admin
        try:
            await client.send_message(
                admin_id,
                f"✅ <b>Video Fetch Complete</b>\n\n"
                f"<b>Channels:</b> {total_channels}\n"
                f"<b>Total Videos:</b> {final_count}",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
            
    except Exception as e:
        logging.error(f"Error in fetch command: {e}")
        await pls_wait.edit(f"❌ Error occurred: {e}")


@Bot.on_message(filters.command("set_caption") & filters.private & is_admin)
async def set_caption_command(client: Client, message: Message):
    try:
        if len(message.command) < 2:
            await message.reply_text(
                "❌ Invalid usage. Use the command like this:\n`/set_caption Your custom caption text here`\n\n"
                "To remove caption, use: `/set_caption None`"
            )
            return
        
        caption_text = message.text.split("/set_caption", 1)[1].strip()
        
        if caption_text.lower() == "none":
            caption_text = None
        
        success = await db.set_custom_caption(caption_text)
        
        if success:
            if caption_text:
                await message.reply_text(
                    f"✅ Custom caption has been set successfully!\n\n"
                    f"<b>Caption:</b> {caption_text}",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.reply_text("✅ Custom caption has been removed.")
        else:
            await message.reply_text("❌ Failed to set custom caption. Please try again.")
    except Exception as e:
        logging.error(f"Error setting caption: {e}")
        await message.reply_text(f"❌ An error occurred: {e}")


@Bot.on_message(filters.command('startbuttons') & filters.private & is_admin)
async def toggle_start_buttons_command(client: Client, message: Message):
    """Toggle showing navigation buttons for videos served from /start, genlink and batch."""
    try:
        current = await db.get_start_buttons()
        await db.set_start_buttons(not current)
        status = 'Enabled' if not current else 'Disabled'
        await message.reply_text(f"✅ Start video nav buttons are now: {status}")
    except Exception as e:
        logging.error(f"Error toggling start buttons: {e}")
        await message.reply_text("❌ Failed to toggle start buttons.")


@Bot.on_message(filters.command('startreactions') & filters.private & is_admin)
async def toggle_start_reactions_command(client: Client, message: Message):
    """Toggle like/dislike/bookmark buttons for videos served from /start/genlink (keeps nav for batch)."""
    try:
        current = await db.get_start_reactions()
        await db.set_start_reactions(not current)
        status = 'Enabled' if not current else 'Disabled'
        await message.reply_text(f"✅ Start video reaction buttons are now: {status}")
    except Exception as e:
        logging.error(f"Error toggling start reactions: {e}")
        await message.reply_text("❌ Failed to toggle start reactions.")


@Bot.on_message(filters.command('verifstats') & filters.private & is_admin)
async def verif_stats_command(client: Client, message: Message):
    """Show verification counts: daily, weekly, monthly, total."""
    try:
        stats = await db.get_verification_summary()
        txt = (
            f"📊 Verification Stats:\n\n"
            f"• Today: {stats.get('daily',0)}\n"
            f"• Last 7 days: {stats.get('weekly',0)}\n"
            f"• Last 30 days: {stats.get('monthly',0)}\n"
            f"• Total verified: {stats.get('total',0)}"
        )
        await message.reply_text(txt)
    except Exception as e:
        logging.error(f"Error fetching verification stats: {e}")
        await message.reply_text("❌ Failed to fetch verification stats.")


@Bot.on_message(filters.command("get_caption") & filters.private & is_admin)
async def get_caption_command(client: Client, message: Message):
    try:
        caption = await db.get_custom_caption()
        
        if caption:
            await message.reply_text(
                f"📝 <b>Current Custom Caption:</b>\n\n{caption}",
                parse_mode=ParseMode.HTML
            )
        else:
            # Check if CUSTOM_CAPTION from config exists
            from config import CUSTOM_CAPTION
            if CUSTOM_CAPTION:
                await message.reply_text(
                    f"📝 <b>No custom caption set in database.</b>\n\n"
                    f"<b>Using config caption:</b> {CUSTOM_CAPTION}",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.reply_text("📝 No custom caption is currently set.")
    except Exception as e:
        logging.error(f"Error getting caption: {e}")
        await message.reply_text(f"❌ An error occurred: {e}")

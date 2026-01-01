# Credit: @rohit_1888
# Modified to match new /start parser

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from helper_func import encode, get_message_id, is_admin


@Bot.on_message(filters.command("batch") & filters.private & is_admin)
async def batch(client: Client, message: Message):
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"

    # -------- FIRST MESSAGE --------
    while True:
        try:
            first_message = await client.ask(
                chat_id=message.from_user.id,
                text=(
                    f"<b>Fᴏʀᴡᴀʀᴅ Tʜᴇ Fɪʀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel}\n"
                    f"Oʀ Sᴇɴᴅ Tʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</b>"
                ),
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60,
                disable_web_page_preview=True
            )
        except:
            return

        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break

        await first_message.reply(
            f"<b>❌ Nᴏᴛ A Vᴀʟɪᴅ {channel} Pᴏsᴛ</b>",
            quote=True
        )

    # -------- LAST MESSAGE --------
    while True:
        try:
            second_message = await client.ask(
                chat_id=message.from_user.id,
                text=(
                    f"<b>Fᴏʀᴡᴀʀᴅ Tʜᴇ Lᴀsᴛ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel}\n"
                    f"Oʀ Sᴇɴᴅ Tʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</b>"
                ),
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60,
                disable_web_page_preview=True
            )
        except:
            return

        s_msg_id = await get_message_id(client, second_message)
        if s_msg_id:
            break

        await second_message.reply(
            f"<b>❌ Nᴏᴛ A Vᴀʟɪᴅ {channel} Pᴏsᴛ</b>",
            quote=True
        )

    # -------- ENCODE (NEW FORMAT) --------
    encoded_first = f_msg_id * abs(client.db_channel.id)
    encoded_last = s_msg_id * abs(client.db_channel.id)

    raw = f"batch-{encoded_first}-{encoded_last}"
    b64 = await encode(raw)

    # Batch links MUST start with pl_
    link = f"https://t.me/{client.username}?start=pl_{b64}"

    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f"https://telegram.me/share/url?url={link}")]]
    )

    await second_message.reply_text(
        f"<b>✅ Bᴀᴛᴄʜ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ:</b>\n\n{link}",
        quote=True,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

@Bot.on_message(filters.command("genlink") & filters.private & is_admin)
async def link_generator(client: Client, message: Message):
    channel = f"<a href={client.db_channel.invite_link}>ᴅʙ ᴄʜᴀɴɴᴇʟ</a>"

    while True:
        try:
            channel_message = await client.ask(
                chat_id=message.from_user.id,
                text=(
                    f"<b>Fᴏʀᴡᴀʀᴅ Tʜᴇ Mᴇssᴀɢᴇ ғʀᴏᴍ {channel}\n"
                    f"Oʀ Sᴇɴᴅ Tʜᴇ {channel} Pᴏsᴛ Lɪɴᴋ</b>"
                ),
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60,
                disable_web_page_preview=True
            )
        except:
            return

        msg_id = await get_message_id(client, channel_message)
        if msg_id:
            break

        await channel_message.reply(
            f"<b>❌ Nᴏᴛ A Vᴀʟɪᴅ {channel} Pᴏsᴛ</b>",
            quote=True
        )

    # -------- ENCODE (NEW FORMAT) --------
    encoded = msg_id * abs(client.db_channel.id)
    raw = f"vid-{encoded}"

    b64 = await encode(raw)

    # Replace '=' with '-' (matches your /start logic)
    safe_b64 = b64.replace("=", "-")

    link = f"https://t.me/{client.username}?start={safe_b64}"

    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔁 Sʜᴀʀᴇ URL", url=f"https://telegram.me/share/url?url={link}")]]
    )

    await channel_message.reply_text(
        f"<b>✅ Vɪᴅᴇᴏ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ:</b>\n\n{link}",
        quote=True,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
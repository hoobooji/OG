import random
import logging
import asyncio
from bot import Bot
from pyrogram import __version__
from pyrogram.enums import ParseMode
from plugins.FORMATS import *
from plugins.start import *
from config import *
from pyrogram.enums import ChatAction
from plugins.autoDelete import convert_time
from database.database import db
from datetime import timedelta
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, ReplyKeyboardMarkup, ReplyKeyboardRemove



logging.basicConfig(
    level=logging.INFO,  # Set the logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def fileSettings(getfunc, setfunc=None, delfunc=False):
    btn_mode, txt_mode, pic_mode = '❌', off_txt, off_pic
    del_btn_mode = 'Eɴᴀʙʟᴇ Mᴏᴅᴇ ✅'
    try:
        if not setfunc:
            if await getfunc():
                txt_mode = on_txt
                btn_mode = '✅'
                del_btn_mode = 'Dɪsᴀʙʟᴇ Mᴏᴅᴇ ❌'

            return txt_mode, (del_btn_mode if delfunc else btn_mode)

        else:
            if await getfunc():
                await setfunc(False)
            else:
                await setfunc(True)
                pic_mode, txt_mode = on_pic, on_txt
                btn_mode = '✅'
                del_btn_mode = 'Dɪsᴀʙʟᴇ Mᴏᴅᴇ ❌'

            return pic_mode, txt_mode, (del_btn_mode if delfunc else btn_mode)

    except Exception as e:
        print(
            f"Error occured at [fileSettings(getfunc, setfunc=None, delfunc=False)] : {e}")

# Provide or Make Button by takiing required modes and data


def buttonStatus(pc_data: str, hc_data: str, cb_data: str) -> list:
    button = [
        [
            InlineKeyboardButton(
                f'Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ: {pc_data}', callback_data='pc'),
            InlineKeyboardButton(
                f'Hɪᴅᴇ Cᴀᴘᴛɪᴏɴ: {hc_data}', callback_data='hc')
        ],
        [
            InlineKeyboardButton(
                f'Cʜᴀɴɴᴇʟ Bᴜᴛᴛᴏɴ: {cb_data}', callback_data='cb'),
            InlineKeyboardButton(f'◈ Sᴇᴛ Bᴜᴛᴛᴏɴ ➪', callback_data='setcb')
        ],
        [
            InlineKeyboardButton('🔄 Rᴇғʀᴇsʜ', callback_data='files_cmd'),
            InlineKeyboardButton('Cʟᴏsᴇ ✖️', callback_data='close')
        ],
    ]
    return button

# Verify user, if he/she is admin or owner before processing the query...


async def authoUser(query, id, owner_only=False):
    if not owner_only:
        if not any([id == OWNER_ID, await db.admin_exist(id)]):
            await query.answer("❌ Yᴏᴜ ᴀʀᴇ ɴᴏᴛ Aᴅᴍɪɴ !", show_alert=True)
            return False
        return True
    else:
        if id != OWNER_ID:
            await query.answer("❌ Yᴏᴜ ᴀʀᴇ ɴᴏᴛ Oᴡɴᴇʀ !", show_alert=True)
            return False
        return True


@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data
    if data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except BaseException:
            pass

    elif data.startswith("get_again_"):
        # Handle get again callback
        # Format: get_again_get_video_{user_id}
        try:
            user_id = query.from_user.id
            action = data.replace("get_again_", "")
            
            # Parse the action (format: get_video_{user_id})
            if action.startswith("get_video_"):
                # Extract user_id from the end
                parts = action.split("_")
                if len(parts) >= 3:
                    try:
                        action_user_id = int(parts[-1])
                        
                        # Verify user authorization
                        if action_user_id != user_id:
                            await query.answer("❌ Unauthorized access!", show_alert=True)
                            return
                        
                        await query.answer("🔄 Getting video...")
                        
                        # Create a message wrapper for get_video
                        class MessageWrapper:
                            def __init__(self, msg, user):
                                self.from_user = user
                                self.chat = msg.chat
                                self.reply_text = msg.reply_text if hasattr(msg, 'reply_text') else None
                        
                        msg_wrapper = MessageWrapper(query.message, query.from_user)
                        
                        # Call get_video
                        await get_video(client, msg_wrapper)
                        
                        # Delete the notification message
                        try:
                            await query.message.delete()
                        except:
                            pass
                    except ValueError:
                        await query.answer("❌ Invalid user ID format!", show_alert=True)
                else:
                    await query.answer("❌ Invalid format!", show_alert=True)
            else:
                await query.answer("❌ Invalid action type!", show_alert=True)
        except Exception as e:
            logging.error(f"Error handling get_again callback: {e}")
            import traceback
            logging.error(traceback.format_exc())
            await query.answer("❌ An error occurred!", show_alert=True)

    elif data == "about":
        await query.message.edit_text(
            text=(
                f"<b>○ Updates : <a href='https://t.me/rohit_1888'>Rohit</a>\n"
                f"○ Language : <code>Python3</code>\n"
                f"○ Library : <a href='https://docs.pyrogram.org/'>Pyrogram asyncio {__version__}</a>"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('⬅️ Bᴀᴄᴋ', callback_data='start'), InlineKeyboardButton(
                    'Cʟᴏsᴇ ✖️', callback_data='close')]
            ]),
        )

    elif data == "buy_prem":
        # Delete the current message and send a new one with the photo
        await query.message.delete()
        await client.send_photo(
            chat_id=query.message.chat.id,
            photo=QR_PIC,
            caption=(
                f"👋 {query.from_user.username}\n\n"
                f"🎖️ Available Plans :\n\n"
                f"● {PRICE1}  For 0 Days Prime Membership\n\n"
                f"● {PRICE2}  For 1 Month Prime Membership\n\n"
                f"● {PRICE3}  For 3 Months Prime Membership\n\n"
                f"● {PRICE4}  For 6 Months Prime Membership\n\n"
                f"● {PRICE5}  For 1 Year Prime Membership\n\n\n"
                f"💵 ASK UPI ID TO ADMIN AND PAY THERE -  <code>{UPI_ID}</code>\n\n\n"
                f"♻️ After Payment You Will Get Instant Membership \n\n\n"
                f"‼️ Must Send Screenshot after payment & If anyone want custom time membrship then ask admin"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("ADMIN 24/7", url=(SCREENSHOT_URL))],
                    [InlineKeyboardButton("🔒 Close", callback_data="close")],
                ]
            )
        )

    elif data == "setting":
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), "<b>Pʟᴇᴀsᴇ wᴀɪᴛ !\n\n<i>🔄 Rᴇᴛʀɪᴇᴠɪɴɢ ᴀʟʟ Sᴇᴛᴛɪɴɢs...</i></b>"))
        try:
            total_fsub = len(await db.get_all_channels())
            total_admin = len(await db.get_all_admins())
            total_ban = len(await db.get_ban_users())
            autodel_mode = 'Eɴᴀʙʟᴇᴅ' if await db.get_auto_delete() else 'Dɪsᴀʙʟᴇᴅ'
            protect_content = 'Eɴᴀʙʟᴇᴅ' if await db.get_protect_content() else 'Dɪsᴀʙʟᴇᴅ'
            hide_caption = 'Eɴᴀʙʟᴇᴅ' if await db.get_hide_caption() else 'Dɪsᴀʙʟᴇᴅ'
            chnl_butn = 'Eɴᴀʙʟᴇᴅ' if await db.get_channel_button() else 'Dɪsᴀʙʟᴇᴅ'
            reqfsub = 'Eɴᴀʙʟᴇᴅ' if await db.get_request_forcesub() else 'Dɪsᴀʙʟᴇᴅ'

            await query.edit_message_media(
                InputMediaPhoto(random.choice(PICS),
                                SETTING_TXT.format(
                                    total_fsub=total_fsub,
                                    total_admin=total_admin,
                                    total_ban=total_ban,
                                    autodel_mode=autodel_mode,
                                    protect_content=protect_content,
                                    hide_caption=hide_caption,
                                    chnl_butn=chnl_butn,
                                    reqfsub=reqfsub
                )
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('⬅️ Bᴀᴄᴋ', callback_data='start'), InlineKeyboardButton(
                        'Cʟᴏsᴇ ✖️', callback_data='close')]
                ]),
            )
        except Exception as e:
            print(f"! Error Occurred on callback data = 'setting' : {e}")

    elif data == "start":
        await query.edit_message_media(
            InputMediaPhoto(random.choice(PICS),
                            START_MSG.format(
                                first=query.from_user.first_name,
                                last=query.from_user.last_name,
                                username=None if not query.from_user.username else '@' + query.from_user.username,
                                mention=query.from_user.mention,
                                id=query.from_user.id
            )
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🤖 Aʙᴏᴜᴛ ᴍᴇ', callback_data='about'), InlineKeyboardButton(
                    'Sᴇᴛᴛɪɴɢs ⚙️', callback_data='setting')],
                    [InlineKeyboardButton('Get Video 🍒', callback_data='start=getvideo')],
                [InlineKeyboardButton('Verifications 📊', callback_data='verif_stats')]
            ]),
        )

    elif data == "start=getvideo":
        # Trigger get_video from start inline button
        try:
            user_id = query.from_user.id
            await query.answer("🔄 Getting video...")

            # Create a simple message wrapper to call get_video
            class MessageWrapper:
                def __init__(self, msg, user):
                    self.from_user = user
                    self.chat = msg.chat
                    self.reply_text = msg.reply_text if hasattr(msg, 'reply_text') else None

            msg_wrapper = MessageWrapper(query.message, query.from_user)
            await get_video(client, msg_wrapper)
            try:
                await query.message.delete()
            except:
                pass
        except Exception as e:
            logging.error(f"Error handling start=getvideo callback: {e}")
            await query.answer("❌ An error occurred!", show_alert=True)

    elif data == "verif_stats":
        # Show verification stats to admins only
        if not await authoUser(query, query.from_user.id):
            return
        try:
            stats = await db.get_verification_summary()
            await query.edit_message_text(
                f"📊 Verification Stats:\n\n• Today: {stats.get('daily',0)}\n• Last 7 days: {stats.get('weekly',0)}\n• Last 30 days: {stats.get('monthly',0)}\n• Total verified: {stats.get('total',0)}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Error showing verif stats: {e}")
            await query.answer("❌ Failed to fetch stats", show_alert=True)

    elif data == "files_cmd":
        if await authoUser(query, query.from_user.id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            try:
                protect_content, pcd = await fileSettings(db.get_protect_content)
                hide_caption, hcd = await fileSettings(db.get_hide_caption)
                channel_button, cbd = await fileSettings(db.get_channel_button)
                name, link, name2, link2 = await db.get_channel_button_links()
                if not name2:
                    name2 = "Not Set"
                if not link2:
                    link2 = "Not Set"

                await query.edit_message_media(
                    InputMediaPhoto(files_cmd_pic,
                                    FILES_CMD_TXT.format(
                                        protect_content=protect_content,
                                        hide_caption=hide_caption,
                                        channel_button=channel_button,
                                        name=name,
                                        link=link,
                                        name2=name2,
                                        link2=link2
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup(
                        buttonStatus(pcd, hcd, cbd)),
                )
            except Exception as e:
                print(f"! Error Occurred on callback data = 'files_cmd' : {e}")

    elif data == "pc":
        if await authoUser(query, query.from_user.id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            try:
                pic, protect_content, pcd = await fileSettings(db.get_protect_content, db.set_protect_content)
                hide_caption, hcd = await fileSettings(db.get_hide_caption)
                channel_button, cbd = await fileSettings(db.get_channel_button)
                name, link, name2, link2 = await db.get_channel_button_links()
                if not name2:
                    name2 = "Not Set"
                if not link2:
                    link2 = "Not Set"

                await query.edit_message_media(
                    InputMediaPhoto(pic,
                                    FILES_CMD_TXT.format(
                                        protect_content=protect_content,
                                        hide_caption=hide_caption,
                                        channel_button=channel_button,
                                        name=name,
                                        link=link,
                                        name2=name2,
                                        link2=link2
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup(
                        buttonStatus(pcd, hcd, cbd))
                )
            except Exception as e:
                print(f"! Error Occurred on callback data = 'pc' : {e}")

    elif data == "hc":
        if await authoUser(query, query.from_user.id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            try:
                protect_content, pcd = await fileSettings(db.get_protect_content)
                pic, hide_caption, hcd = await fileSettings(db.get_hide_caption, db.set_hide_caption)
                channel_button, cbd = await fileSettings(db.get_channel_button)
                name, link, name2, link2 = await db.get_channel_button_links()
                if not name2:
                    name2 = "Not Set"
                if not link2:
                    link2 = "Not Set"

                await query.edit_message_media(
                    InputMediaPhoto(pic,
                                    FILES_CMD_TXT.format(
                                        protect_content=protect_content,
                                        hide_caption=hide_caption,
                                        channel_button=channel_button,
                                        name=name,
                                        link=link,
                                        name2=name2,
                                        link2=link2
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup(
                        buttonStatus(pcd, hcd, cbd))
                )
            except Exception as e:
                print(f"! Error Occurred on callback data = 'hc' : {e}")

    elif data == "cb":
        if await authoUser(query, query.from_user.id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            try:
                protect_content, pcd = await fileSettings(db.get_protect_content)
                hide_caption, hcd = await fileSettings(db.get_hide_caption)
                pic, channel_button, cbd = await fileSettings(db.get_channel_button, db.set_channel_button)
                name, link, name2, link2 = await db.get_channel_button_links()
                if not name2:
                    name2 = "Not Set"
                if not link2:
                    link2 = "Not Set"

                await query.edit_message_media(
                    InputMediaPhoto(pic,
                                    FILES_CMD_TXT.format(
                                        protect_content=protect_content,
                                        hide_caption=hide_caption,
                                        channel_button=channel_button,
                                        name=name,
                                        link=link,
                                        name2=name2,
                                        link2=link2
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup(
                        buttonStatus(pcd, hcd, cbd))
                )
            except Exception as e:
                print(f"! Error Occurred on callback data = 'cb' : {e}")

    elif data == "setcb":
        id = query.from_user.id
        if await authoUser(query, id):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            try:
                button_name, button_link, button_name2, button_link2 = await db.get_channel_button_links()
                
                # Create preview with existing buttons
                button_preview = []
                if button_name and button_link:
                    if button_name2 and button_link2:
                        button_preview = [[InlineKeyboardButton(text=button_name, url=button_link), InlineKeyboardButton(text=button_name2, url=button_link2)]]
                    else:
                        button_preview = [[InlineKeyboardButton(text=button_name, url=button_link)]]
                
                example_text = (
                    '<b>Tᴏ sᴇᴛ ᴛʜᴇ ʙᴜᴛᴛᴏɴ(s), Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛs ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ.\n\n'
                    '<b>Fᴏʀ 1 ʙᴜᴛᴛᴏɴ:</b>\n'
                    '<blockquote><code>Join Channel - https://t.me/btth480p</code></blockquote>\n\n'
                    '<b>Fᴏʀ 2 ʙᴜᴛᴛᴏɴs:</b>\n'
                    '<blockquote><code>Join Channel - https://t.me/btth480p | Support - https://t.me/support</code></blockquote>\n\n'
                    '<i>Bᴇʟᴏᴡ ɪs ᴄᴜʀʀᴇɴᴛ ʙᴜᴛᴛᴏɴ(s) Pʀᴇᴠɪᴇᴡ ⬇️</i></b>'
                )
                
                set_msg = await client.ask(
                    chat_id=id, 
                    text=example_text, 
                    timeout=60, 
                    reply_markup=InlineKeyboardMarkup(button_preview) if button_preview else None, 
                    disable_web_page_preview=True
                )
                
                # Check if user sent 2 buttons (separated by |)
                if ' | ' in set_msg.text:
                    # Two buttons format: "Name1 - Link1 | Name2 - Link2"
                    parts = set_msg.text.split(' | ')
                    if len(parts) != 2:
                        markup = [[InlineKeyboardButton(f'◈ Sᴇᴛ Cʜᴀɴɴᴇʟ Bᴜᴛᴛᴏɴ ➪', callback_data='setcb')]]
                        return await set_msg.reply(
                            "<b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛs.\n\n"
                            "<b>Fᴏʀ 2 ʙᴜᴛᴛᴏɴs:</b>\n"
                            "<blockquote><code>Join Channel - https://t.me/btth480p | Support - https://t.me/support</code></blockquote>\n\n"
                            "<i>Tʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ..</i></b>", 
                            reply_markup=InlineKeyboardMarkup(markup), 
                            disable_web_page_preview=True
                        )
                    
                    # Parse first button
                    button1 = parts[0].split(' - ')
                    if len(button1) != 2:
                        markup = [[InlineKeyboardButton(f'◈ Sᴇᴛ Cʜᴀɴɴᴇʟ Bᴜᴛᴛᴏɴ ➪', callback_data='setcb')]]
                        return await set_msg.reply(
                            "<b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛs.\n\n"
                            "<b>Fᴏʀ 2 ʙᴜᴛᴛᴏɴs:</b>\n"
                            "<blockquote><code>Join Channel - https://t.me/btth480p | Support - https://t.me/support</code></blockquote>\n\n"
                            "<i>Tʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ..</i></b>", 
                            reply_markup=InlineKeyboardMarkup(markup), 
                            disable_web_page_preview=True
                        )
                    
                    # Parse second button
                    button2 = parts[1].split(' - ')
                    if len(button2) != 2:
                        markup = [[InlineKeyboardButton(f'◈ Sᴇᴛ Cʜᴀɴɴᴇʟ Bᴜᴛᴛᴏɴ ➪', callback_data='setcb')]]
                        return await set_msg.reply(
                            "<b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛs.\n\n"
                            "<b>Fᴏʀ 2 ʙᴜᴛᴛᴏɴs:</b>\n"
                            "<blockquote><code>Join Channel - https://t.me/btth480p | Support - https://t.me/support</code></blockquote>\n\n"
                            "<i>Tʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ..</i></b>", 
                            reply_markup=InlineKeyboardMarkup(markup), 
                            disable_web_page_preview=True
                        )
                    
                    button_name = button1[0].strip()
                    button_link = button1[1].strip()
                    button_name2 = button2[0].strip()
                    button_link2 = button2[1].strip()
                    
                    button_preview = [[
                        InlineKeyboardButton(text=button_name, url=button_link),
                        InlineKeyboardButton(text=button_name2, url=button_link2)
                    ]]
                    
                    await set_msg.reply(
                        "<b><i>Aᴅᴅᴇᴅ Sᴜᴄcᴇssғᴜʟʟʏ ✅</i>\n<blockquote>Sᴇᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴs ᴀs Pʀᴇᴠɪᴇᴡ ⬇️</blockquote></b>", 
                        reply_markup=InlineKeyboardMarkup(button_preview)
                    )
                    await db.set_channel_button_links(button_name, button_link, button_name2, button_link2)
                else:
                    # Single button format: "Name - Link"
                    button = set_msg.text.split(' - ')

                    if len(button) != 2:
                        markup = [[InlineKeyboardButton(f'◈ Sᴇᴛ Cʜᴀɴɴᴇʟ Bᴜᴛᴛᴏɴ ➪', callback_data='setcb')]]
                        return await set_msg.reply(
                            "<b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛs.\n\n"
                            "<b>Fᴏʀ 1 ʙᴜᴛᴛᴏɴ:</b>\n"
                            "<blockquote><code>Join Channel - https://t.me/btth480p</code></blockquote>\n\n"
                            "<b>Fᴏʀ 2 ʙᴜᴛᴛᴏɴs:</b>\n"
                            "<blockquote><code>Join Channel - https://t.me/btth480p | Support - https://t.me/support</code></blockquote>\n\n"
                            "<i>Tʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ..</i></b>", 
                            reply_markup=InlineKeyboardMarkup(markup), 
                            disable_web_page_preview=True
                        )

                    button_name = button[0].strip()
                    button_link = button[1].strip()
                    button_preview = [[InlineKeyboardButton(text=button_name, url=button_link)]]

                    await set_msg.reply(
                        "<b><i>Aᴅᴅᴇᴅ Sᴜᴄcᴇssғᴜʟʟʏ ✅</i>\n<blockquote>Sᴇᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴀs Pʀᴇᴠɪᴇᴡ ⬇️</blockquote></b>", 
                        reply_markup=InlineKeyboardMarkup(button_preview)
                    )
                    await db.set_channel_button_links(button_name, button_link)
                return
            except Exception as e:
                try:
                    await set_msg.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>")
                    print(f"! Error Occurred on callback data = 'setcb' : {e}")
                except BaseException:
                    await client.send_message(id, text=f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n<blockquote><i>Rᴇᴀsᴏɴ: 1 minute Time out ..</i></b></blockquote>", disable_notification=True)
                    print(f"! Error Occurred on callback data = 'setcb' -> Rᴇᴀsᴏɴ: 1 minute Time out ..")

    elif data == 'autodel_cmd':
        if await authoUser(query, query.from_user.id, owner_only=True):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            try:
                timer = convert_time(await db.get_del_timer())
                autodel_mode, mode = await fileSettings(db.get_auto_delete, delfunc=True)

                await query.edit_message_media(
                    InputMediaPhoto(autodel_cmd_pic,
                                    AUTODEL_CMD_TXT.format(
                                        autodel_mode=autodel_mode,
                                        timer=timer
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(mode, callback_data='chng_autodel'), InlineKeyboardButton(
                            '◈ Sᴇᴛ Tɪᴍᴇʀ ⏱', callback_data='set_timer')],
                        [InlineKeyboardButton('🔄 Rᴇғʀᴇsʜ', callback_data='autodel_cmd'), InlineKeyboardButton(
                            'Cʟᴏsᴇ ✖️', callback_data='close')]
                    ])
                )
            except Exception as e:
                print(
                    f"! Error Occurred on callback data = 'autodel_cmd' : {e}")

    elif data == 'chng_autodel':
        if await authoUser(query, query.from_user.id, owner_only=True):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            try:
                timer = convert_time(await db.get_del_timer())
                pic, autodel_mode, mode = await fileSettings(db.get_auto_delete, db.set_auto_delete, delfunc=True)

                await query.edit_message_media(
                    InputMediaPhoto(pic,
                                    AUTODEL_CMD_TXT.format(
                                        autodel_mode=autodel_mode,
                                        timer=timer
                                    )
                                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(mode, callback_data='chng_autodel'), InlineKeyboardButton(
                            '◈ Sᴇᴛ Tɪᴍᴇʀ ⏱', callback_data='set_timer')],
                        [InlineKeyboardButton('🔄 Rᴇғʀᴇsʜ', callback_data='autodel_cmd'), InlineKeyboardButton(
                            'Cʟᴏsᴇ ✖️', callback_data='close')]
                    ])
                )
            except Exception as e:
                print(
                    f"! Error Occurred on callback data = 'chng_autodel' : {e}")

    elif data == 'set_timer':
        id = query.from_user.id
        if await authoUser(query, id, owner_only=True):
            try:

                timer = convert_time(await db.get_del_timer())
                set_msg = await client.ask(chat_id=id, text=f'<b><blockquote>⏱ Cᴜʀʀᴇɴᴛ Tɪᴍᴇʀ: {timer}</blockquote>\n\nTᴏ ᴄʜᴀɴɢᴇ ᴛɪᴍᴇʀ, Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ɪɴ sᴇᴄᴏɴᴅs ᴡɪᴛʜɪɴ 1 ᴍɪɴᴜᴛᴇ.\n<blockquote>Fᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>300</code>, <code>600</code>, <code>900</code></b></blockquote>', timeout=60)
                del_timer = set_msg.text.split()

                if len(del_timer) == 1 and del_timer[0].isdigit():
                    DEL_TIMER = int(del_timer[0])
                    await db.set_del_timer(DEL_TIMER)
                    timer = convert_time(DEL_TIMER)
                    await set_msg.reply(f"<b><i>Aᴅᴅᴇᴅ Sᴜᴄcᴇssғᴜʟʟʏ ✅</i>\n<blockquote>⏱ Cᴜʀʀᴇɴᴛ Tɪᴍᴇʀ: {timer}</blockquote></b>")
                else:
                    markup = [[InlineKeyboardButton(
                        '◈ Sᴇᴛ Dᴇʟᴇᴛᴇ Tɪᴍᴇʀ ⏱', callback_data='set_timer')]]
                    return await set_msg.reply("<b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ɪɴ sᴇᴄᴏɴᴅs.\n<blockquote>Fᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>300</code>, <code>600</code>, <code>900</code></blockquote>\n\n<i>Tʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ..</i></b>", reply_markup=InlineKeyboardMarkup(markup))

            except Exception as e:
                try:
                    await set_msg.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>")
                    print(
                        f"! Error Occurred on callback data = 'set_timer' : {e}")
                except BaseException:
                    await client.send_message(id, text=f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n<blockquote><i>Rᴇᴀsᴏɴ: 1 minute Time out ..</i></b></blockquote>", disable_notification=True)
                    print(
                        f"! Error Occurred on callback data = 'set_timer' -> Rᴇᴀsᴏɴ: 1 minute Time out ..")

    elif data == 'chng_req':
        if await authoUser(query, query.from_user.id, owner_only=True):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            try:
                on = off = ""
                if await db.get_request_forcesub():
                    await db.set_request_forcesub(False)
                    off = "🔴"
                    texting = off_txt
                else:
                    await db.set_request_forcesub(True)
                    on = "🟢"
                    texting = on_txt

                button = [
                    [InlineKeyboardButton(f"{on} ON", "chng_req"), InlineKeyboardButton(
                        f"{off} OFF", "chng_req")],
                    [InlineKeyboardButton(
                        "⚙️ Mᴏʀᴇ Sᴇᴛᴛɪɴɢs ⚙️", "more_settings")]
                ]
                # 🎉)
                await query.message.edit_text(text=RFSUB_CMD_TXT.format(req_mode=texting), reply_markup=InlineKeyboardMarkup(button))

            except Exception as e:
                print(f"! Error Occurred on callback data = 'chng_req' : {e}")

    elif data == 'more_settings':
        if await authoUser(query, query.from_user.id, owner_only=True):
            # await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")
            try:
                await query.message.edit_text("<b>Pʟᴇᴀsᴇ wᴀɪᴛ !\n\n<i>🔄 Rᴇᴛʀɪᴇᴠɪɴɢ ᴀʟʟ Sᴇᴛᴛɪɴɢs...</i></b>")
                LISTS = "Eᴍᴘᴛʏ Rᴇǫᴜᴇsᴛ FᴏʀᴄᴇSᴜʙ Cʜᴀɴɴᴇʟ Lɪsᴛ !?"

                REQFSUB_CHNLS = await db.get_reqChannel()
                if REQFSUB_CHNLS:
                    LISTS = ""
                    channel_name = "<i>Uɴᴀʙʟᴇ Lᴏᴀᴅ Nᴀᴍᴇ..</i>"
                    for CHNL in REQFSUB_CHNLS:
                        await query.message.reply_chat_action(ChatAction.TYPING)
                        try:
                            name = (await client.get_chat(CHNL)).title
                        except BaseException:
                            name = None
                        channel_name = name if name else channel_name

                        user = await db.get_reqSent_user(CHNL)
                        channel_users = len(user) if user else 0

                        link = await db.get_stored_reqLink(CHNL)
                        if link:
                            channel_name = f"<a href={link}>{channel_name}</a>"

                        LISTS += f"NAME: {channel_name}\n(ID: <code>{CHNL}</code>)\nUSERS: {channel_users}\n\n"

                buttons = [
                    [InlineKeyboardButton("ᴄʟᴇᴀʀ ᴜsᴇʀs", "clear_users"), InlineKeyboardButton(
                        "cʟᴇᴀʀ cʜᴀɴɴᴇʟs", "clear_chnls")],
                    [InlineKeyboardButton(
                        "♻️  Rᴇғʀᴇsʜ Sᴛᴀᴛᴜs  ♻️", "more_settings")],
                    [InlineKeyboardButton("⬅️ Bᴀᴄᴋ", "req_fsub"), InlineKeyboardButton(
                        "Cʟᴏsᴇ ✖️", "close")]
                ]
                await query.message.reply_chat_action(ChatAction.CANCEL)
                await query.message.edit_text(text=RFSUB_MS_TXT.format(reqfsub_list=LISTS.strip()), reply_markup=InlineKeyboardMarkup(buttons))

            except Exception as e:
                print(
                    f"! Error Occurred on callback data = 'more_settings' : {e}")

    elif data == 'clear_users':
        # if await authoUser(query, query.from_user.id, owner_only=True) :
        # await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")
        try:
            REQFSUB_CHNLS = await db.get_reqChannel()
            if not REQFSUB_CHNLS:
                return await query.answer("Eᴍᴘᴛʏ Rᴇǫᴜᴇsᴛ FᴏʀᴄᴇSᴜʙ Cʜᴀɴɴᴇʟ !?", show_alert=True)

            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            REQFSUB_CHNLS = list(map(str, REQFSUB_CHNLS))
            buttons = [REQFSUB_CHNLS[i:i + 2]
                       for i in range(0, len(REQFSUB_CHNLS), 2)]
            buttons.insert(0, ['CANCEL'])
            buttons.append(['DELETE ALL CHANNELS USER'])

            user_reply = await client.ask(query.from_user.id, text=CLEAR_USERS_TXT, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))

            if user_reply.text == 'CANCEL':
                return await user_reply.reply("<b><i>🆑 Cᴀɴᴄᴇʟʟᴇᴅ...</i></b>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text in REQFSUB_CHNLS:
                try:
                    await db.clear_reqSent_user(int(user_reply.text))
                    return await user_reply.reply(f"<b><blockquote>✅ Usᴇʀ Dᴀᴛᴀ Sᴜᴄᴄᴇssғᴜʟʟʏ Cʟᴇᴀʀᴇᴅ ғʀᴏᴍ Cʜᴀɴɴᴇʟ ɪᴅ: <code>{user_reply.text}</code></blockquote></b>", reply_markup=ReplyKeyboardRemove())
                except Exception as e:
                    return await user_reply.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ...\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text == 'DELETE ALL CHANNELS USER':
                try:
                    for CHNL in REQFSUB_CHNLS:
                        await db.clear_reqSent_user(int(CHNL))
                    return await user_reply.reply(f"<b><blockquote>✅ Usᴇʀ Dᴀᴛᴀ Sᴜᴄᴄᴇssғᴜʟʟʏ Cʟᴇᴀʀᴇᴅ ғʀᴏᴍ Aʟʟ Cʜᴀɴɴᴇʟ ɪᴅs</blockquote></b>", reply_markup=ReplyKeyboardRemove())
                except Exception as e:
                    return await user_reply.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ...\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            else:
                return await user_reply.reply(f"<b><blockquote>INVALID SELECTIONS</blockquote></b>", reply_markup=ReplyKeyboardRemove())

        except Exception as e:
            print(f"! Error Occurred on callback data = 'clear_users' : {e}")

    elif data == 'clear_chnls':
        # if await authoUser(query, query.from_user.id, owner_only=True)

        try:
            REQFSUB_CHNLS = await db.get_reqChannel()
            if not REQFSUB_CHNLS:
                return await query.answer("Eᴍᴘᴛʏ Rᴇǫᴜᴇsᴛ FᴏʀᴄᴇSᴜʙ Cʜᴀɴɴᴇʟ !?", show_alert=True)

            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            REQFSUB_CHNLS = list(map(str, REQFSUB_CHNLS))
            buttons = [REQFSUB_CHNLS[i:i + 2]
                       for i in range(0, len(REQFSUB_CHNLS), 2)]
            buttons.insert(0, ['CANCEL'])
            buttons.append(['DELETE ALL CHANNEL IDS'])

            user_reply = await client.ask(query.from_user.id, text=CLEAR_CHNLS_TXT, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))

            if user_reply.text == 'CANCEL':
                return await user_reply.reply("<b><i>🆑 Cᴀɴᴄᴇʟʟᴇᴅ...</i></b>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text in REQFSUB_CHNLS:
                try:
                    chnl_id = int(user_reply.text)

                    await db.del_reqChannel(chnl_id)

                    try:
                        await client.revoke_chat_invite_link(chnl_id, await db.get_stored_reqLink(chnl_id))
                    except BaseException:
                        pass

                    await db.del_stored_reqLink(chnl_id)

                    return await user_reply.reply(f"<b><blockquote><code>{user_reply.text}</code> Cʜᴀɴɴᴇʟ ɪᴅ ᴀʟᴏɴɢ ᴡɪᴛʜ ɪᴛs ᴅᴀᴛᴀ sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ ✅</blockquote></b>", reply_markup=ReplyKeyboardRemove())
                except Exception as e:
                    return await user_reply.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ...\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text == 'DELETE ALL CHANNEL IDS':
                try:
                    for CHNL in REQFSUB_CHNLS:
                        chnl = int(CHNL)

                        await db.del_reqChannel(chnl)

                        try:
                            await client.revoke_chat_invite_link(chnl, await db.get_stored_reqLink(chnl))
                        except BaseException:
                            pass

                        await db.del_stored_reqLink(chnl)

                    return await user_reply.reply(f"<b><blockquote>Aʟʟ Cʜᴀɴɴᴇʟ ɪᴅs ᴀʟᴏɴɢ ᴡɪᴛʜ ɪᴛs ᴅᴀᴛᴀ sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ ✅</blockquote></b>", reply_markup=ReplyKeyboardRemove())

                except Exception as e:
                    return await user_reply.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ...\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            else:
                return await user_reply.reply(f"<b><blockquote>INVALID SELECTIONS</blockquote></b>", reply_markup=ReplyKeyboardRemove())

        except Exception as e:
            print(f"! Error Occurred on callback data = 'more_settings' : {e}")

    elif data == 'clear_links':
        # if await authoUser(query, query.from_user.id, owner_only=True) :
        # await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

        try:
            REQFSUB_CHNLS = await db.get_reqLink_channels()
            if not REQFSUB_CHNLS:
                return await query.answer("Nᴏ Sᴛᴏʀᴇᴅ Rᴇǫᴜᴇsᴛ Lɪɴᴋ Aᴠᴀɪʟᴀʙʟᴇ !?", show_alert=True)

            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

            REQFSUB_CHNLS = list(map(str, REQFSUB_CHNLS))
            buttons = [REQFSUB_CHNLS[i:i + 2]
                       for i in range(0, len(REQFSUB_CHNLS), 2)]
            buttons.insert(0, ['CANCEL'])
            buttons.append(['DELETE ALL REQUEST LINKS'])

            user_reply = await client.ask(query.from_user.id, text=CLEAR_LINKS_TXT, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))

            if user_reply.text == 'CANCEL':
                return await user_reply.reply("<b><i>🆑 Cᴀɴᴄᴇʟʟᴇᴅ...</i></b>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text in REQFSUB_CHNLS:
                channel_id = int(user_reply.text)
                try:
                    try:
                        await client.revoke_chat_invite_link(channel_id, await db.get_stored_reqLink(channel_id))
                    except BaseException:
                        text = """<b>❌ Uɴᴀʙʟᴇ ᴛᴏ Rᴇᴠᴏᴋᴇ ʟɪɴᴋ !
<blockquote expandable>ɪᴅ: <code>{}</code></b>
<i>Eɪᴛʜᴇʀ ᴛʜᴇ ʙᴏᴛ ɪs ɴᴏᴛ ɪɴ ᴀʙᴏᴠᴇ ᴄʜᴀɴɴᴇʟ Oʀ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘʀᴏᴘᴇʀ ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs</i></blockquote>"""
                        return await user_reply.reply(text=text.format(channel_id), reply_markup=ReplyKeyboardRemove())

                    await db.del_stored_reqLink(channel_id)
                    return await user_reply.reply(f"<b><blockquote><code>{channel_id}</code> Cʜᴀɴɴᴇʟs Lɪɴᴋ Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ ✅</blockquote></b>", reply_markup=ReplyKeyboardRemove())

                except Exception as e:
                    return await user_reply.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ...\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            elif user_reply.text == 'DELETE ALL REQUEST LINKS':
                try:
                    result = ""
                    for CHNL in REQFSUB_CHNLS:
                        channel_id = int(CHNL)
                        try:
                            await client.revoke_chat_invite_link(channel_id, await db.get_stored_reqLink(channel_id))
                        except BaseException:
                            result += f"<blockquote expandable><b><code>{channel_id}</code> Uɴᴀʙʟᴇ ᴛᴏ Rᴇᴠᴏᴋᴇ ❌</b>\n<i>Eɪᴛʜᴇʀ ᴛʜᴇ ʙᴏᴛ ɪs ɴᴏᴛ ɪɴ ᴀʙᴏᴠᴇ ᴄʜᴀɴɴᴇʟ Oʀ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘʀᴏᴘᴇʀ ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs.</i></blockquote>\n"
                            continue
                        await db.del_stored_reqLink(channel_id)
                        result += f"<blockquote><b><code>{channel_id}</code> IDs Lɪɴᴋ Dᴇʟᴇᴛᴇᴅ ✅</b></blockquote>\n"

                    return await user_reply.reply(f"<b>⁉️ Oᴘᴇʀᴀᴛɪᴏɴ Rᴇsᴜʟᴛ:</b>\n{result.strip()}", reply_markup=ReplyKeyboardRemove())

                except Exception as e:
                    return await user_reply.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ...\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>", reply_markup=ReplyKeyboardRemove())

            else:
                return await user_reply.reply(f"<b><blockquote>INVALID SELECTIONS</blockquote></b>", reply_markup=ReplyKeyboardRemove())

        except Exception as e:
            print(f"! Error Occurred on callback data = 'more_settings' : {e}")

    elif data == 'req_fsub':
        # if await authoUser(query, query.from_user.id, owner_only=True) :
        await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")

        try:
            on = off = ""
            if await db.get_request_forcesub():
                on = "🟢"
                texting = on_txt
            else:
                off = "🔴"
                texting = off_txt

            button = [
                [InlineKeyboardButton(f"{on} ON", "chng_req"), InlineKeyboardButton(
                    f"{off} OFF", "chng_req")],
                [InlineKeyboardButton("⚙️ Mᴏʀᴇ Sᴇᴛᴛɪɴɢs ⚙️", "more_settings")]
            ]
            # 🎉)
            await query.message.edit_text(text=RFSUB_CMD_TXT.format(req_mode=texting), reply_markup=InlineKeyboardMarkup(button))

        except Exception as e:
            print(f"! Error Occurred on callback data = 'chng_req' : {e}")
    

    # Handle shortener settings
    elif data == "shortener_settings":
        if await authoUser(query, query.from_user.id, owner_only=True):
            try:
                await query.answer("💫 Fetching Shortener details...")

            # Fetch shortener details
                shortener_url = await db.get_shortener_url()
                shortener_api = await db.get_shortener_api()
                verified_time = await db.get_verified_time()
                tut_video = await db.get_tut_video()

            # Prepare the details for display
                shortener_url_display = shortener_url or "Not set"
                shortener_api_display = shortener_api or "Not set"
                status = "Active" if shortener_url and shortener_api else "Inactive"
                verified_time_display = (
                    f"{verified_time} seconds" if verified_time else "Not set"
                )
                tut_video_display = (
                    f"[Tutorial Video]({tut_video})" if tut_video else "Not set"
                )

            # Response message
                response_text = (
                    f"𝗦𝗵𝗼𝗿𝘁𝗲𝗻𝗲𝗿 𝗗𝗲𝘁𝗮𝗶𝗹𝘀\n\n"
                    f"Sɪᴛᴇ: {shortener_url_display}\n"
                    f"API Tᴏᴋᴇɴ:  {shortener_api_display}\n"
                    f"Sᴛᴀᴛᴜs: {status}\n\n"
                    f"Vᴇʀɪғɪᴇᴅ Tɪᴍᴇ:  {verified_time_display}\n"
                    f"Tᴜᴛᴏʀɪᴀʟ Vɪᴅᴇᴏ: {tut_video_display}"
                )

            # Update the message with the fetched details
                await query.message.edit_text(
                    text=response_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('🔙', callback_data='set_shortener')]
                    ]),
                    disable_web_page_preview=True  # Disable preview for tutorial video link
                )

            except Exception as e:
                logging.error(f"Error fetching shortener settings: {e}")
                await query.message.reply(
                    "⚠️ An error occurred while fetching shortener settings. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('Back', callback_data='set_shortener')]
                    ])
                )


    elif data == "chng_shortener": 
        user_id = query.from_user.id
        shortener_details = await db.get_shortener()

    # Toggle the shortener status in the database
        if shortener_details:
        # Disable shortener
            await db.set_shortener("", "")
            await query.answer("Shortener Disabled ❌", show_alert=True)
        else:
        # Enable shortener, prompt for URL and API Key
            await query.answer("Shortener Enabled ✅. Please provide the Shortener URL and API Key.", show_alert=True)
            await query.message.reply("Send the Shortener URL and API Key in the format:\n`<shortener_url> <api_key>`")

    


    elif data == 'set_shortener_details':
        if await authoUser(query, query.from_user.id, owner_only=True):
            try:
                await query.answer("Please send the shortener URL within 1 minute...")
                set_msg_url = await query.message.reply(
                    "⏳ Please provide the Shortener site URL (e.g., https://example.com) within 1 minute.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data='set_shortener')]])
                )
                site_msg = await client.ask(
                    chat_id=query.from_user.id,
                    text="⏳ Enter Shortener site URL:",
                    timeout=60
                )

                shortener_url = site_msg.text.strip()


            # Confirm the shortener site URL
                await site_msg.reply(f"Shortener site URL set to: {shortener_url}\nNow please send the API key.")

            # Step 3: Prompt for API key
                set_msg_api = await query.message.reply(
                    "⏳ Please provide the API key for the shortener within 1 minute.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data='set_shortener')]])
                )

                api_msg = await client.ask(
                    chat_id=query.from_user.id,
                    text="⏳ Enter API key for the shortener:",
                    timeout=60
                )

                api_key = api_msg.text.strip()

            # Step 4: Save the shortener details in the database
                await db.set_shortener_url(shortener_url)
                await db.set_shortener_api(api_key)
            
            # Confirmation message
                await api_msg.reply(
                    "✅ Shortener details have been successfully set!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('◈ Disable Shortener ❌', callback_data='disable_shortener')],
                        [InlineKeyboardButton('Back', callback_data='set_shortener')]
                    ])
                )
            except asyncio.TimeoutError:
                await query.message.reply(
                    "⚠️ You did not provide the details in time. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data='set_shortener')]])
                )
            except Exception as e:
                logging.error(f"Error setting shortener details: {e}")  # This now works correctly
                await query.message.reply(
                    f"⚠️ Error occurred: {e}",
    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data='set_shortener')]])
    )


    elif data == "set_shortener":
        if await authoUser(query, query.from_user.id, owner_only=True):
            try:
                message = query.message

                shortener_url = await db.get_shortener_url()
                shortener_api = await db.get_shortener_api()

                if shortener_url and shortener_api:
                    shortener_status = "Enabled ✅"
                    mode_button = InlineKeyboardButton('Disable Shortener ❌', callback_data='disable_shortener')
                else:
                    shortener_status = "Disabled ❌"
                    mode_button = InlineKeyboardButton('Enable Shortener ✅', callback_data='set_shortener_details')

            # Edit the same message instead of sending a new one
                await message.edit_media(
                    media=InputMediaPhoto(
                        media=START_PIC,
                        caption=SET_SHORTENER_CMD_TXT.format(shortener_status=shortener_status),
                        parse_mode=ParseMode.HTML
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [mode_button],
                        [
                            InlineKeyboardButton('Settings ⚙️', callback_data='shortener_settings'),
                            InlineKeyboardButton('🔄 Refresh', callback_data='set_shortener')
                        ],
                        [
                            InlineKeyboardButton('Set Verified Time ⏱', callback_data='set_verify_time'),
                            InlineKeyboardButton('Set Tutorial Video 🎥', callback_data='set_tut_video')
                        ],
                        [InlineKeyboardButton('Close ✖️', callback_data='close')]
                    ])
                )

            except Exception as e:
                await query.message.edit_text(
                    f"<b>! Error Occurred..\n<blockquote>Reason:</b> {e}</blockquote><b><i>Contact developer: @rohit_1888</i></b>",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("Close ✖️", callback_data="close")]]
                    )
                )

    elif data == "set_tut_video":
        id = query.from_user.id

        if await authoUser(query, id, owner_only=True):
            await query.answer("♻️ Qᴜᴇʀʏ Pʀᴏᴄᴇssɪɴɢ....")
        
            try:
            # Fetch the current tutorial video URL from the database
                current_video_url = await db.get_tut_video()

            # Prompt the user to input the new tutorial video URL
                set_msg = await client.ask(
                    chat_id=id,
                    text=f'<b><blockquote>⏳ Cᴜʀʀᴇɴᴛ Tᴜᴛᴏʀɪᴀʟ Vɪᴅᴇᴏ URL: {current_video_url if current_video_url else "Not Set"}</blockquote>\n\nTᴏ ᴄʜᴀɴɢᴇ, Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴠɪᴅᴇᴏ URL.\n<blockquote>Fᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>https://youtube.com/some_video</code></b></blockquote>',
                    timeout=60
                )

            # Validate the user input for a valid URL
                video_url = set_msg.text.strip()

                if video_url.startswith("http") and "://" in video_url:
                # Save the new tutorial video URL to the database
                    await db.set_tut_video(video_url)

                # Confirm the update to the user
                    await set_msg.reply(f"<b><i>Tᴜᴛᴏʀɪᴀʟ Vɪᴅᴇᴏ URL sᴇᴛ sᴜᴄᴄᴇssғᴜʟʟʏ ✅</i>\n<blockquote>📹 Cᴜʀʀᴇɴᴛ Tᴜᴛᴏʀɪᴀʟ Vɪᴅᴇᴏ URL: {video_url}</blockquote></b>")
                else:
                # If the URL is invalid, prompt the user to try again
                    markup = [[InlineKeyboardButton(
                        '◈ Sᴇᴛ Tᴜᴛᴏʀɪᴀʟ Vɪᴅᴇᴏ URL 📹', callback_data='set_tut_video')]]
                    return await set_msg.reply(
                        "<b>Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ ʟɪɴᴋ ᴛᴏ ᴀ ᴠᴀʟɪᴅ ᴠɪᴅᴇᴏ.\n<blockquote>Fᴏʀ ᴇxᴀᴍᴘʟᴇ: <code>https://youtube.com/some_video</code></blockquote>\n\n<i>Tʀʏ ᴀɢᴀɪɴ ʙʏ ᴄʟɪᴄᴋɪɴɢ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ..</i></b>", reply_markup=InlineKeyboardMarkup(markup))

            except Exception as e:
                try:
                # Handle any exceptions that occur during the process
                    await set_msg.reply(f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n<blockquote>Rᴇᴀsᴏɴ:</b> {e}</blockquote>")
                    print(f"! Error Occurred on callback data = 'set_tut_video' : {e}")
                except BaseException:
                # If an error occurs while sending the error message, send a timeout message
                    await client.send_message(id, text=f"<b>! Eʀʀᴏʀ Oᴄᴄᴜʀᴇᴅ..\n<blockquote><i>Rᴇᴀsᴏɴ: 1 minute Time out ..</i></b></blockquote>", disable_notification=True)
                    print(f"! Error Occurred on callback data = 'set_tut_video' -> Reason: 1 minute Time out ..")


    elif data == 'set_verify_time':
        id = query.from_user.id

        if await authoUser(query, id, owner_only=True):
            await query.answer("♻️ Processing request...")

            try:
                # Fetch the current verified time from the database
                current_verify_time = await db.get_verified_time()
                time_display = f"{current_verify_time} seconds" if current_verify_time else "Not set"

                # Prompt the user to input a new verified time
                set_msg = await client.ask(
                    chat_id=id,
                    text=(
                        f"<b><blockquote>⏱ Current Timer: {time_display}</blockquote>\n\n"
                        f"To change the timer, please send a valid number in seconds within 1 minute.\n"
                        f"<blockquote>For example: <code>300</code>, <code>600</code>, <code>900</code></blockquote></b>"
                    ),
                    timeout=60
                )

                # Validate the user input
                verify_time_input = set_msg.text.strip()
                if verify_time_input.isdigit():
                    verify_time = int(verify_time_input)

                    # Save the new verified time to the database
                    await db.set_verified_time(verify_time)
                    formatted_time = f"{verify_time} seconds"
                    
                    # Confirm the update to the user
                    await set_msg.reply(
                        f"<b><i>Timer updated successfully ✅</i>\n"
                        f"<blockquote>⏱ Current Timer: {formatted_time}</blockquote></b>"
                    )
                else:
                    # Handle invalid input
                    markup = [[InlineKeyboardButton('◈ Set Verify Timer ⏱', callback_data='set_verify_time')]]
                    return await set_msg.reply(
                        "<b>Please send a valid number in seconds.\n"
                        "<blockquote>For example: <code>300</code>, <code>600</code>, <code>900</code></blockquote>\n\n"
                        "<i>Try again by clicking the button below.</i></b>",
                        reply_markup=InlineKeyboardMarkup(markup)
                    )

            except asyncio.TimeoutError:
                # Handle timeout if user doesn't respond in time
                await client.send_message(
                    id,
                    text="<b>⚠️ Timeout occurred. You did not respond within the time limit.</b>",
                    disable_notification=True
                )
            except Exception as e:
                # Handle any other exceptions
                await client.send_message(
                    id,
                    text=f"<b>⚠️ Error occurred:\n<blockquote>{e}</blockquote></b>",
                    disable_notification=True
                )
                print(f"! Error occurred on callback data = 'set_verify_time' : {e}")



    elif data == "enable_shortener":
        await query.answer()

        try:
            # Check if shortener details are already set
            shortener_url = await db.get_shortener_url()
            shortener_api = await db.get_shortener_api()

            if shortener_url and shortener_api:
                # Enable the shortener
                success_url = await db.set_shortener_url(shortener_url)
                success_api = await db.set_shortener_api(shortener_api)

                if success_url and success_api:
                    await query.edit_message_caption(
                        caption="Shortener has been enabled ✅",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton('Disable Shortener ❌', callback_data='disable_shortener')],
                            [InlineKeyboardButton('Close ✖️', callback_data='close')]
                        ])
                    )
                else:
                    await query.message.reply(
                        "Failed to enable the shortener. Please try again."
                    )
            else:
                # If no shortener details are found, prompt the user to set them
                await query.edit_message_caption(
                    caption="No shortener details found. Please set the shortener details first.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('Set Shortener Details', callback_data='set_shortener_details')],
                        [InlineKeyboardButton('Close ✖️', callback_data='close')]
                    ])
                )
        except Exception as e:
            logging.error(f"Error enabling shortener: {e}")
            await query.message.reply(
                "An unexpected error occurred while enabling the shortener. Please try again later."
            )

    elif data == "disable_shortener":
        await query.answer()
    
    # Deactivate the shortener
        success = await db.deactivate_shortener()
        if success:
            await query.edit_message_caption(
                caption="Shortener has been disabled ❌",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('Enable Shortener ✅', callback_data='enable_shortener')],
                    [InlineKeyboardButton('Close ✖️', callback_data='close')]
                ])
            )
        else:
            await query.message.reply("Failed to disable the shortener. Please try again.")

    # ---------------------------
    # Video Interaction Callbacks
    # ---------------------------
    elif data.startswith("like_"):
        video_id = data.replace("like_", "")
        user_id = query.from_user.id
        
        # Check user plan (like/dislike/mark don't require premium, but we check for consistency)
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        
        # Toggle like
        is_liked = await db.is_liked(user_id, video_id)
        if is_liked:
            # Remove like
            await db.dislikes_collection.update_one(
                {"user_id": user_id},
                {"$pull": {"video_ids": video_id}}
            )
            await db.likes_collection.update_one(
                {"user_id": user_id},
                {"$pull": {"video_ids": video_id}}
            )
        else:
            await db.add_like(user_id, video_id)
        
        # Refresh buttons (respect batch session if present)
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        try:
            sess = await db.get_batch_session(query.message.chat.id, query.message.id)
        except:
            sess = None

        if sess:
            f_msg_id = int(sess.get('f_msg_id'))
            s_msg_id = int(sess.get('s_msg_id'))
            idx = int(sess.get('index', 0))
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

            buttons = [[InlineKeyboardButton(like_btn, callback_data=f"like_{video_id}"), InlineKeyboardButton(dislike_btn, callback_data=f"dislike_{video_id}"), InlineKeyboardButton(mark_btn, callback_data=f"mark_{video_id}")]]
            second = []
            if idx > 0:
                # Use compact callback_data referencing session index to avoid hitting Telegram callback data size limits
                second.append(InlineKeyboardButton("🙆🏻‍♂️ Last", callback_data=f"last_batch_{user_id}_{idx-1}"))
            second.append(InlineKeyboardButton("⬇️ Save", callback_data=f"save_{video_id}"))
            try:
                msg_ids = list(range(min(f_msg_id, s_msg_id), max(f_msg_id, s_msg_id) + 1))
                messages = await try_until_get(client.get_messages(client.db_channel.id, msg_ids))
                videos = [m.video.file_id for m in messages if m and m.video]
                total = len(videos)
            except:
                total = None
            if total is None or idx < (total - 1 if total else 0):
                second.append(InlineKeyboardButton("😋 Next", callback_data=f"next_batch_{user_id}_{idx+1}"))
            if second:
                buttons.append(second)
            if not is_premium:
                buttons.append([InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem")])
            reply_markup = InlineKeyboardMarkup(buttons)
        else:
            # No batch session -> preserve buttons originally present in message
            try:
                inline_kb = query.message.reply_markup.inline_keyboard if query.message.reply_markup else []
                texts = [btn.text for row in inline_kb for btn in row]
                show_change_category = any(t == '📁 Change Category' for t in texts)
                use_channel_buttons = any(getattr(btn, 'url', None) for row in inline_kb for btn in row)
                show_nav_buttons = any(t in ('🙆🏻‍♂️ Last','😋 Next') for t in texts)
            except:
                show_change_category = True
                use_channel_buttons = True
                show_nav_buttons = True

            reply_markup = await create_video_buttons(
                user_id,
                video_id,
                is_premium=is_premium,
                show_change_category=show_change_category,
                use_channel_buttons=use_channel_buttons,
                show_nav_buttons=show_nav_buttons,
            )
        
        # Get current caption
        current_caption = query.message.caption if query.message.caption else ""
        
        try:
            await query.message.edit_caption(
                caption=current_caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            await query.answer("❤️ Liked!" if not is_liked else "🤍 Like removed", show_alert=False)
        except:
            await query.answer("Updated", show_alert=False)

    elif data.startswith("dislike_"):
        video_id = data.replace("dislike_", "")
        user_id = query.from_user.id
        
        # Check user plan
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        
        # Toggle dislike
        is_disliked = await db.is_disliked(user_id, video_id)
        if is_disliked:
            # Remove dislike
            await db.dislikes_collection.update_one(
                {"user_id": user_id},
                {"$pull": {"video_ids": video_id}}
            )
        else:
            await db.add_dislike(user_id, video_id)
        
        # Refresh buttons and preserve original keyboard structure when present
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        try:
            inline_kb = query.message.reply_markup.inline_keyboard if query.message.reply_markup else []
            texts = [btn.text for row in inline_kb for btn in row]
            show_change_category = any(t == '📁 Change Category' for t in texts)
            use_channel_buttons = any(getattr(btn, 'url', None) for row in inline_kb for btn in row)
            show_nav_buttons = any(t in ('🙆🏻‍♂️ Last','😋 Next') for t in texts)
        except:
            show_change_category = True
            use_channel_buttons = True
            show_nav_buttons = True

        reply_markup = await create_video_buttons(
            user_id,
            video_id,
            is_premium=is_premium,
            show_change_category=show_change_category,
            use_channel_buttons=use_channel_buttons,
            show_nav_buttons=show_nav_buttons,
        )

        # Get current caption
        current_caption = query.message.caption if query.message.caption else ""
        
        try:
            await query.message.edit_caption(
                caption=current_caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            await query.answer("🦠 Disliked!" if not is_disliked else "😐 Dislike removed", show_alert=False)
        except:
            await query.answer("Updated", show_alert=False)

    elif data.startswith("mark_"):
        video_id = data.replace("mark_", "")
        user_id = query.from_user.id
        
        # Check user plan (bookmarking is available to all users)
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        
        # Toggle bookmark
        is_bookmarked = await db.is_bookmarked(user_id, video_id)
        if is_bookmarked:
            await db.remove_bookmark(user_id, video_id)
        else:
            await db.add_bookmark(user_id, video_id)
        
        # Refresh buttons and preserve original keyboard structure when present
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        try:
            inline_kb = query.message.reply_markup.inline_keyboard if query.message.reply_markup else []
            texts = [btn.text for row in inline_kb for btn in row]
            show_change_category = any(t == '📁 Change Category' for t in texts)
            use_channel_buttons = any(getattr(btn, 'url', None) for row in inline_kb for btn in row)
            show_nav_buttons = any(t in ('🙆🏻‍♂️ Last','😋 Next') for t in texts)
        except:
            show_change_category = True
            use_channel_buttons = True
            show_nav_buttons = True

        reply_markup = await create_video_buttons(
            user_id,
            video_id,
            is_premium=is_premium,
            show_change_category=show_change_category,
            use_channel_buttons=use_channel_buttons,
            show_nav_buttons=show_nav_buttons,
        )
        
        # Get current caption
        current_caption = query.message.caption if query.message.caption else ""
        
        try:
            await query.message.edit_caption(
                caption=current_caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            await query.answer("🔖 Bookmarked!" if not is_bookmarked else "📌 Bookmark removed", show_alert=False)
        except:
            await query.answer("Updated", show_alert=False)

    elif data.startswith("last_") and not data.startswith("last_batch_"):
        # Parse: last_userid_videoid
        parts = data.replace("last_", "").split("_", 1)
        if len(parts) < 1:
            return await query.answer("❌ Invalid format", show_alert=True)
        
        try:
            user_id = int(parts[0])
        except ValueError:
            return await query.answer("❌ Invalid user ID", show_alert=True)
        
        if query.from_user.id != user_id:
            return await query.answer("❌ Unauthorized", show_alert=True)
        
        # Check user plan
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        
        # For free users, check limits before proceeding
        if not is_premium:
            free_limit = await db.get_free_limit(user_id)
            free_enabled = await db.get_free_state(user_id)
            free_count = await db.check_free_usage(user_id)
            
            if not free_enabled:
                return await query.answer("💳 Premium required", show_alert=True)
            
            remaining_attempts = free_limit - free_count
            if remaining_attempts <= 0:
                return await query.answer(
                    f"❌ You've used all your {free_limit} free videos. Upgrade to Premium!",
                    show_alert=True
                )
            
            # Check if this is the last free video - show popup alert
            if remaining_attempts == 1:
                await query.answer(
                    "⚠️ This is your last free video for today. Upgrade to Premium for unlimited videos!",
                    show_alert=True
                )
            
            # Deduct free usage for last video (viewing previous video also counts)
            await db.update_free_usage(user_id)
        
        # Get last video (get_last_video and get_video are imported at top with *)
        last_video_id, last_file_id = await get_last_video(user_id)
        
        if not last_video_id:
            return await query.answer("❌ No previous video found", show_alert=True)
        
        # Edit message with last video
        await query.answer("🔄 Loading last video...")
        try:
            # Create a message-like object from query.message
            # Use query.from_user (the actual user clicking) not msg.from_user (the bot)
            class MessageWrapper:
                def __init__(self, msg, user):
                    self.from_user = user  # Use the actual user who clicked
                    self.chat = msg.chat
                    self.reply_text = msg.reply_text if hasattr(msg, 'reply_text') else None
            
            msg_wrapper = MessageWrapper(query.message, query.from_user)
            await get_video(client, msg_wrapper, video_id=last_video_id, edit_message=query.message)
        except Exception as e:
            logging.error(f"Error loading last video: {e}")
            import traceback
            logging.error(traceback.format_exc())
            await query.answer("❌ Error loading video", show_alert=True)

    elif data.startswith("save_"):
        video_id = data.replace("save_", "")
        user_id = query.from_user.id
        
        # Check premium
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        
        if not is_premium:
            # Send premium buy message (no buttons in the message)
            await query.answer("💳 Premium required", show_alert=True)
            try:
                await client.send_message(
                    user_id,
                    "💳 Pʀᴇᴍɪᴜᴍ Rᴇǫᴜɪʀᴇᴅ\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ ᴠɪᴅᴇᴏs!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem")]
                    ])
                )
            except:
                pass
            return
        
        # Get video metadata
        video_metadata = await db.get_video_metadata(video_id)
        if not video_metadata:
            return await query.answer("❌ Video not found", show_alert=True)
        
        file_id = video_metadata.get("file_id")
        
        # Get custom caption
        custom_caption = await db.get_custom_caption()
        if not custom_caption:
            from config import CUSTOM_CAPTION
            custom_caption = CUSTOM_CAPTION or ""
        
        # Get category name (get_category_name imported at top with *)
        category_name = await get_category_name(user_id)
        
        # Prepare caption with video ID and category name (no buttons)
        caption_parts = []
        if custom_caption:
            caption_parts.append(custom_caption)
        caption_parts.append(f"\n<b>ID: <code>{video_id}</code></b>")
        if category_name:
            caption_parts.append(f"<b>Category: {category_name}</b>")
        final_caption = "\n".join(caption_parts)
        
        # Send video with forward enabled (protect_content=False to allow forwarding)
        # Premium user download - allow forwarding
        await query.answer("⬇️ Downloading...")
        try:
            # Respect CHNL_BTN and PROTECT_MODE when sending to user
            try:
                AUTO_DEL, DEL_TIMER, HIDE_CAPTION, CHNL_BTN, PROTECT_MODE = await asyncio.gather(
                    db.get_auto_delete(), db.get_del_timer(), db.get_hide_caption(), db.get_channel_button(), db.get_protect_content()
                )
            except:
                CHNL_BTN = False
                PROTECT_MODE = True

            reply_markup = None
            if CHNL_BTN:
                try:
                    button_name, button_link = await db.get_channel_button_link()
                    if button_name and button_link:
                        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text=button_name, url=button_link)]])
                except:
                    reply_markup = None

            await client.send_video(
                user_id,
                file_id,
                caption=final_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=PROTECT_MODE
            )
            await query.answer("✅ Video sent to your DM!", show_alert=True)
        except Exception as e:
            logging.error(f"Error sending video for download: {e}")
            await query.answer("❌ Error sending video", show_alert=True)

    elif data.startswith("bookmark_nav_"):
        # Parse: bookmark_nav_userid_index
        parts = data.replace("bookmark_nav_", "").split("_", 1)
        if len(parts) < 2:
            return await query.answer("❌ Invalid format", show_alert=True)
        
        try:
            user_id = int(parts[0])
            bookmark_index = int(parts[1])
        except ValueError:
            return await query.answer("❌ Invalid format", show_alert=True)
        
        if query.from_user.id != user_id:
            return await query.answer("❌ Unauthorized", show_alert=True)
        
        # Navigate to bookmarked video
        await query.answer("🔄 Loading bookmarked video...")
        try:
            # Create a message-like object from query.message
            class MessageWrapper:
                def __init__(self, msg, user):
                    self.from_user = user
                    self.chat = msg.chat
                    self.reply_text = msg.reply_text if hasattr(msg, 'reply_text') else None
            
            msg_wrapper = MessageWrapper(query.message, query.from_user)
            await get_bookmarked_videos(client, msg_wrapper, bookmark_index=bookmark_index, edit_message=query.message)
        except Exception as e:
            logging.error(f"Error loading bookmarked video: {e}")
            import traceback
            logging.error(traceback.format_exc())
            await query.answer("❌ Error loading video", show_alert=True)

    elif data.startswith("next_") and not data.startswith("next_batch_"):
        # Parse: next_userid_videoid
        parts = data.replace("next_", "").split("_", 1)
        if len(parts) < 1:
            return await query.answer("❌ Invalid format", show_alert=True)
        
        try:
            user_id = int(parts[0])
        except ValueError:
            return await query.answer("❌ Invalid user ID", show_alert=True)
        
        current_video_id = parts[1] if len(parts) > 1 else None
        
        if query.from_user.id != user_id:
            return await query.answer("❌ Unauthorized", show_alert=True)
        
        # Check user plan
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        
        # For free users, check limits before proceeding
        if not is_premium:
            free_limit = await db.get_free_limit(user_id)
            free_enabled = await db.get_free_state(user_id)
            free_count = await db.check_free_usage(user_id)
            
            if not free_enabled:
                return await query.answer("💳 Premium required", show_alert=True)
            
            remaining_attempts = free_limit - free_count
            if remaining_attempts <= 0:
                return await query.answer(
                    f"❌ You've used all your {free_limit} free videos. Upgrade to Premium!",
                    show_alert=True
                )
            
            # Check if this is the last free video - show popup alert
            if remaining_attempts == 1:
                await query.answer(
                    "⚠️ This is your last free video for today. Upgrade to Premium for unlimited videos!",
                    show_alert=True
                )
            
            # Deduct free usage for next video
            await db.update_free_usage(user_id)
        
        # Save current as last (save_last_video is imported at top with *)
        if current_video_id:
            video_metadata = await db.get_video_metadata(current_video_id)
            if video_metadata:
                await save_last_video(user_id, current_video_id, video_metadata.get("file_id"))
        
        # Get next video - let get_video handle category filtering and watched videos
        await query.answer("😋 Loading...", show_alert=False)
        try:
            # Call get_video directly - it will handle category filtering and prevent repeats
            class MessageWrapper:
                def __init__(self, msg, user):
                    self.from_user = user
                    self.chat = msg.chat
                    self.reply_text = msg.reply_text if hasattr(msg, 'reply_text') else None
            
            msg_wrapper = MessageWrapper(query.message, query.from_user)
            await get_video(client, msg_wrapper, video_id=None, edit_message=query.message)
        except Exception as e:
            logging.error(f"Error loading next video: {e}")
            import traceback
            logging.error(traceback.format_exc())
            await query.answer("❌ Error loading video", show_alert=True)

    elif data.startswith("next_batch_"):
        # Format: next_batch_{user_id}_{index} (session is looked up by message id)
        rest = data.replace("next_batch_", "")
        parts = rest.split("_", 1)
        if len(parts) < 2:
            return await query.answer("❌ Invalid batch format", show_alert=True)
        try:
            user_id = int(parts[0])
            index = int(parts[1])
        except ValueError:
            return await query.answer("❌ Invalid format", show_alert=True)

        if query.from_user.id != user_id:
            return await query.answer("❌ Unauthorized", show_alert=True)

        # Lookup batch session by the message that contains the buttons
        try:
            sess = await db.get_batch_session(query.message.chat.id, query.message.id)
            if not sess:
                return await query.answer("❌ Session not found", show_alert=True)
            f_msg_id = int(sess.get('f_msg_id'))
            s_msg_id = int(sess.get('s_msg_id'))
        except Exception:
            return await query.answer("❌ Session error", show_alert=True)

        await query.answer("🔄 Loading...")
        from database.db_premium import is_premium_user
        try:
            # fetch messages in range and build videos list
            msg_ids = list(range(min(f_msg_id, s_msg_id), max(f_msg_id, s_msg_id) + 1))
            messages = await try_until_get(client.get_messages(client.db_channel.id, msg_ids))
            videos = [m for m in messages if m and m.video]
            if index < 0 or index >= len(videos):
                return await query.answer("❌ No more videos", show_alert=True)

            file_id = videos[index].video.file_id
            # generate video_id and save
            import hashlib
            hash_obj = hashlib.md5(file_id.encode())
            video_id = str(int(hash_obj.hexdigest()[:8], 16))
            await db.save_video_metadata(video_id, file_id, messages[index].id if messages[index] else None)

            # build caption
            HIDE_CAPTION = await db.get_hide_caption()
            custom_caption = await db.get_custom_caption() or CUSTOM_CAPTION
            category_name = await get_category_name(user_id)
            like_percentage = await db.get_like_percentage(video_id)
            dislike_percentage = await db.get_dislike_percentage(video_id)
            caption_parts = []
            if custom_caption:
                caption_parts.append(custom_caption)
            caption_parts.append(f"\n<b>ID: <code>{video_id}</code></b>")
            if category_name:
                caption_parts.append(f"<b>Category: {category_name}</b>")
            caption_parts.append(f"<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>")
            final_caption = "\n".join(caption_parts) if not HIDE_CAPTION else f"<b>ID: <code>{video_id}</code></b>" + (f"\n<b>Category: {category_name}</b>" if category_name else "") + f"\n<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>"

            # build batch buttons (respect start reactions toggle)
            start_reactions_enabled = await db.get_start_reactions()
            buttons = []
            if start_reactions_enabled:
                like_btn = "❤️" if await db.is_liked(user_id, video_id) else "🤍"
                dislike_btn = "🦠" if await db.is_disliked(user_id, video_id) else "😐"
                mark_btn = "🔖" if await db.is_bookmarked(user_id, video_id) else "📌"
                buttons.append([InlineKeyboardButton(like_btn, callback_data=f"like_{video_id}"), InlineKeyboardButton(dislike_btn, callback_data=f"dislike_{video_id}"), InlineKeyboardButton(mark_btn, callback_data=f"mark_{video_id}")])

            second = []
            # Use compact callback_data (session lookup) to avoid callback_data length issues
            if index > 0:
                second.append(InlineKeyboardButton("🙆🏻‍♂️ Last", callback_data=f"last_batch_{user_id}_{index-1}"))
            second.append(InlineKeyboardButton("⬇️ Save", callback_data=f"save_{video_id}"))
            if index < len(videos) - 1:
                second.append(InlineKeyboardButton("😋 Next", callback_data=f"next_batch_{user_id}_{index+1}"))
            if second:
                buttons.append(second)
            if not await is_premium_user(user_id):
                buttons.append([InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem")])

            reply_markup = InlineKeyboardMarkup(buttons)

            success = await edit_video_message(client, query.message, file_id, final_caption, reply_markup, protect_content=True)
            if success:
                await db.update_batch_index(query.message.chat.id, query.message.id, index)
        except Exception as e:
            logging.error(f"Error in next_batch: {e}")
            await query.answer("❌ Error loading video", show_alert=True)

    elif data.startswith("last_batch_"):
        # Format: last_batch_{user_id}_{index} (session is looked up by message id)
        rest = data.replace("last_batch_", "")
        parts = rest.split("_", 1)
        if len(parts) < 2:
            return await query.answer("❌ Invalid batch format", show_alert=True)
        try:
            user_id = int(parts[0])
            index = int(parts[1])
        except ValueError:
            return await query.answer("❌ Invalid format", show_alert=True)

        if query.from_user.id != user_id:
            return await query.answer("❌ Unauthorized", show_alert=True)

        # Lookup batch session by the message that contains the buttons
        try:
            sess = await db.get_batch_session(query.message.chat.id, query.message.id)
            if not sess:
                return await query.answer("❌ Session not found", show_alert=True)
            f_msg_id = int(sess.get('f_msg_id'))
            s_msg_id = int(sess.get('s_msg_id'))
        except Exception:
            return await query.answer("❌ Session error", show_alert=True)

        await query.answer("🔄 Loading...")
        from database.db_premium import is_premium_user
        try:
            msg_ids = list(range(min(f_msg_id, s_msg_id), max(f_msg_id, s_msg_id) + 1))
            messages = await try_until_get(client.get_messages(client.db_channel.id, msg_ids))
            videos = [m for m in messages if m and m.video]
            if index < 0 or index >= len(videos):
                return await query.answer("❌ No previous video", show_alert=True)
            file_id = videos[index].video.file_id
            import hashlib
            hash_obj = hashlib.md5(file_id.encode())
            video_id = str(int(hash_obj.hexdigest()[:8], 16))
            await db.save_video_metadata(video_id, file_id, messages[index].id if messages[index] else None)

            HIDE_CAPTION = await db.get_hide_caption()
            custom_caption = await db.get_custom_caption() or CUSTOM_CAPTION
            category_name = await get_category_name(user_id)
            like_percentage = await db.get_like_percentage(video_id)
            dislike_percentage = await db.get_dislike_percentage(video_id)
            caption_parts = []
            if custom_caption:
                caption_parts.append(custom_caption)
            caption_parts.append(f"\n<b>ID: <code>{video_id}</code></b>")
            if category_name:
                caption_parts.append(f"<b>Category: {category_name}</b>")
            caption_parts.append(f"<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>")
            final_caption = "\n".join(caption_parts) if not HIDE_CAPTION else f"<b>ID: <code>{video_id}</code></b>" + (f"\n<b>Category: {category_name}</b>" if category_name else "") + f"\n<b>👍 Like: {like_percentage}% | 👎 Dislike: {dislike_percentage}%</b>"

            # Build batch buttons (respect start reactions toggle)
            start_reactions_enabled = await db.get_start_reactions()
            buttons = []
            if start_reactions_enabled:
                like_btn = "❤️" if await db.is_liked(user_id, video_id) else "🤍"
                dislike_btn = "🦠" if await db.is_disliked(user_id, video_id) else "😐"
                mark_btn = "🔖" if await db.is_bookmarked(user_id, video_id) else "📌"
                buttons.append([InlineKeyboardButton(like_btn, callback_data=f"like_{video_id}"), InlineKeyboardButton(dislike_btn, callback_data=f"dislike_{video_id}"), InlineKeyboardButton(mark_btn, callback_data=f"mark_{video_id}")])

            second = []
            # Use compact callback_data (session lookup)
            if index > 0:
                second.append(InlineKeyboardButton("🙆🏻‍♂️ Last", callback_data=f"last_batch_{user_id}_{index-1}"))
            second.append(InlineKeyboardButton("⬇️ Save", callback_data=f"save_{video_id}"))
            if index < len(videos) - 1:
                second.append(InlineKeyboardButton("😋 Next", callback_data=f"next_batch_{user_id}_{index+1}"))
            if second:
                buttons.append(second)
            if not await is_premium_user(user_id):
                buttons.append([InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem")])

            reply_markup = InlineKeyboardMarkup(buttons)
            success = await edit_video_message(client, query.message, file_id, final_caption, reply_markup, protect_content=True)
            if success:
                await db.update_batch_index(query.message.chat.id, query.message.id, index)
        except Exception as e:
            logging.error(f"Error in last_batch: {e}")
            await query.answer("❌ Error loading video", show_alert=True)

    elif data == "change_category":
        user_id = query.from_user.id
        
        # Check premium
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        
        if not is_premium:
            await query.answer("💳 Premium required", show_alert=True)
            await query.message.reply(
                "💳 Pʀᴇᴍɪᴜᴍ Rᴇǫᴜɪʀᴇᴅ\n\nUᴘɢʀᴀᴅᴇ ᴛᴏ Pʀᴇᴍɪᴜᴍ ᴛᴏ ᴄʜᴀɴɢᴇ ᴄᴀᴛᴇɢᴏʀʏ!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Purchase Premium", callback_data="buy_prem")]
                ]),
                quote=False
            )
            return
        
        # Show category selection (CATEGORY_NAMES, CATEGORY_CHANNELS imported at top)
        if len(CATEGORY_CHANNELS) <= 1:
            return await query.answer("❌ Only one category available", show_alert=True)
        
        buttons = []
        current_category = await db.get_user_category(user_id)
        
        # Create category buttons in 2 rows
        category_buttons = []
        for idx, name in enumerate(CATEGORY_NAMES):
            if idx < len(CATEGORY_CHANNELS):
                check = "✅ " if idx == current_category else ""
                category_buttons.append(
                    InlineKeyboardButton(
                        f"{check}{name}",
                        callback_data=f"set_category_{idx}"
                    )
                )
        
        # Split into 2 rows (2 buttons per row)
        row1 = []
        row2 = []
        for i, btn in enumerate(category_buttons):
            if i < 2:  # First 2 buttons in first row
                row1.append(btn)
            else:  # Remaining buttons in second row
                row2.append(btn)
        
        if row1:
            buttons.append(row1)
        if row2:
            buttons.append(row2)
        
        # Add back button
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_video")])
        
        try:
            await query.message.edit_caption(
                caption="📁 Sᴇʟᴇᴄᴛ ᴀ ᴄᴀᴛᴇɢᴏʀʏ:",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )
            await query.answer("📁 Select category")
        except:
            await query.answer("❌ Error", show_alert=True)

    elif data.startswith("set_category_"):
        category_index = int(data.replace("set_category_", ""))
        user_id = query.from_user.id
        
        # Check premium
        from database.db_premium import is_premium_user
        is_premium = await is_premium_user(user_id)
        
        if not is_premium:
            return await query.answer("💳 Premium required", show_alert=True)
        
        # Get current category to check if it changed
        current_category = await db.get_user_category(user_id)
        
        # Set category
        await db.set_user_category(user_id, category_index)
        
        # If category changed, clear watched videos to show fresh videos from new category
        if current_category != category_index:
            await db.clear_watched_videos(user_id)
            # Also clear video cache for this user
            from plugins.start import user_video_cache
            if user_id in user_video_cache:
                user_video_cache[user_id] = []
        
        # CATEGORY_NAMES imported at top
        category_name = CATEGORY_NAMES[category_index] if category_index < len(CATEGORY_NAMES) else f"Category {category_index + 1}"
        
        await query.answer(f"✅ Category changed to {category_name}", show_alert=False)
        
        # Automatically go back and update video with selected category
        # Reload video with new category (get_video imported at top with *)
        try:
            # Create a message-like object from query.message
            # Use query.from_user (the actual user clicking) not msg.from_user (the bot)
            class MessageWrapper:
                def __init__(self, msg, user):
                    self.from_user = user  # Use the actual user who clicked
                    self.chat = msg.chat
                    self.reply_text = msg.reply_text if hasattr(msg, 'reply_text') else None
            
            msg_wrapper = MessageWrapper(query.message, query.from_user)
            await get_video(client, msg_wrapper, video_id=None, edit_message=query.message)
        except Exception as e:
            logging.error(f"Error loading video with new category: {e}")
            import traceback
            logging.error(traceback.format_exc())

    
    
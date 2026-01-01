import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

#Bot token @Botfather
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8207086549:AAGzJJkqAsoIkhu0zc0jTkmX6Sfq_KF35Uo")

#Your API ID from my.telegram.org
APP_ID = int(os.environ.get("APP_ID", "9698652"))

#Your API Hash from my.telegram.org
API_HASH = os.environ.get("API_HASH", "b354710ab18b84e00b65c62ba7a9c043")

#Your db channel Id
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003489581232"))

#OWNER ID
OWNER_ID = int(os.environ.get("OWNER_ID", "7558932006"))

#Port
PORT = os.environ.get("PORT", "3435")
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://obito:umaid2008@cluster0.engyc.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("DATABASE_NAME", "telesbs")

IS_VERIFY = os.environ.get("IS_VERIFY", "True")

TUT_VID = os.environ.get("TUT_VID", "https://t.me/delight_link/2")

TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "200"))

START_PIC = os.environ.get("START_PIC", "https://telegra.ph/file/ec17880d61180d3312d6a.jpg")

FORCE_PIC = os.environ.get("FORCE_PIC", "https://telegra.ph/file/e292b12890b8b4b9dcbd1.jpg")

QR_PIC = os.environ.get("QR_PIC", "https://envs.sh/B7w.png")

#Collection of pics for Bot // #Optional but atleast one pic link should be replaced if you don't want predefined links

PICS = (os.environ.get("PICS", "https://envs.sh/4Iq.jpg https://envs.sh/4IW.jpg https://envs.sh/4IB.jpg https://envs.sh/4In.jpg")).split() #Required

#set your Custom Caption here, Keep None for Disable Custom Caption
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "<b>ʙʏ @Javpostr</b>")


#Set true if you want Disable your Channel Posts Share button
DISABLE_CHANNEL_BUTTON = os.environ.get("True", True) == 'True'


#==========================(BUY PREMIUM)====================#

PREMIUM_BUTTON = reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("Remove Ads In One Click", callback_data="buy_prem")]]
)
PREMIUM_BUTTON2 = reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("Remove Ads In One Click", callback_data="buy_prem")]]
) 

OWNER_TAG = os.environ.get("OWNER_TAG", "rohit_1888")

#UPI ID
UPI_ID = os.environ.get("UPI_ID", "rohit23pnb@axl")

#UPI QR CODE IMAGE
UPI_IMAGE_URL = os.environ.get("UPI_IMAGE_URL", "https://t.me/paymentbot6/2")

#SCREENSHOT URL of ADMIN for verification of payments
SCREENSHOT_URL = os.environ.get("SCREENSHOT_URL", f"t.me/rohit_1888")

#Time and its price
#7 Days
PRICE1 = os.environ.get("PRICE1", "0 rs")
#1 Month
PRICE2 = os.environ.get("PRICE2", "60 rs")
#3 Month
PRICE3 = os.environ.get("PRICE3", "150 rs")
#6 Month
PRICE4 = os.environ.get("PRICE4", "280 rs")
#1 Year
PRICE5 = os.environ.get("PRICE5", "550 rs")
#===================(END)========================#

#==========================(REFERRAL SYSTEM)====================#
# Referral system settings
# How many referrals needed to get premium
REFERRAL_COUNT = int(os.environ.get("REFERRAL_COUNT", "5"))  # Default: 5 referrals
# How many days of premium to give for referrals
REFERRAL_PREMIUM_DAYS = int(os.environ.get("REFERRAL_PREMIUM_DAYS", "7"))  # Default: 7 days
#===================(END)========================#

#==========================(USER REPLY TEXT)====================#
# Reply text for unnecessary messages from non-admin users
USER_REPLY_TEXT = os.environ.get("USER_REPLY_TEXT", "⚠️ Pʟᴇᴀsᴇ ᴜsᴇ ᴛʜᴇ ᴘʀᴏᴘᴇʀ ᴄᴏᴍᴍᴀɴᴅs ᴏʀ ʙᴜᴛᴛᴏɴs ᴛᴏ ɪɴᴛᴇʀᴀᴄᴛ ᴡɪᴛʜ ᴛʜᴇ ʙᴏᴛ.\n\nUse /help to see available commands.")
#===================(END)========================#

#==========================(CATEGORY CONFIGURATION)====================#
# Category configuration - up to 4 categories
# Format: CATEGORY_CHANNELS = [channel_id_1, channel_id_2, channel_id_3, channel_id_4]
# Format: CATEGORY_NAMES = ["Category 1", "Category 2", "Category 3", "Category 4"]
# Build CATEGORY_CHANNELS list - use env vars if set, otherwise use defaults
CATEGORY_CHANNELS = [
    int(os.environ.get("CATEGORY_CHANNEL_1", -1003655585616)),
]

# Add channel 2 (use env var if set, otherwise use default)
channel_2 = os.environ.get("CATEGORY_CHANNEL_2", "-1003299201791")
if channel_2 and channel_2 != "":
    try:
        CATEGORY_CHANNELS.append(int(channel_2))
    except (ValueError, TypeError):
        pass

# Add channel 3 (use env var if set, otherwise use default)
channel_3 = os.environ.get("CATEGORY_CHANNEL_3", "-1003104118765")
if channel_3 and channel_3 != "":
    try:
        CATEGORY_CHANNELS.append(int(channel_3))
    except (ValueError, TypeError):
        pass

# Add channel 4 (use env var if set, otherwise use default)
channel_4 = os.environ.get("CATEGORY_CHANNEL_4", "-1003270622902")
if channel_4 and channel_4 != "":
    try:
        CATEGORY_CHANNELS.append(int(channel_4))
    except (ValueError, TypeError):
        pass

# Remove duplicates and invalid values
CATEGORY_CHANNELS = list(dict.fromkeys([ch for ch in CATEGORY_CHANNELS if ch and ch != 0]))  # Remove duplicates, None and 0

# Build CATEGORY_NAMES list to match CATEGORY_CHANNELS
CATEGORY_NAMES = [
    os.environ.get("CATEGORY_NAME_1", "Category 1"),
]

# Add names for additional channels
if len(CATEGORY_CHANNELS) > 1:
    name_2 = os.environ.get("CATEGORY_NAME_2", "Category 2")
    if name_2:
        CATEGORY_NAMES.append(name_2)

if len(CATEGORY_CHANNELS) > 2:
    name_3 = os.environ.get("CATEGORY_NAME_3", "Category 3")
    if name_3:
        CATEGORY_NAMES.append(name_3)

if len(CATEGORY_CHANNELS) > 3:
    name_4 = os.environ.get("CATEGORY_NAME_4", "Category 4")
    if name_4:
        CATEGORY_NAMES.append(name_4)

# Ensure category names match channels count (fill missing names)
while len(CATEGORY_NAMES) < len(CATEGORY_CHANNELS):
    CATEGORY_NAMES.append(f"Category {len(CATEGORY_NAMES) + 1}")

# Limit to actual channels count
CATEGORY_NAMES = CATEGORY_NAMES[:len(CATEGORY_CHANNELS)]
#===================(END)========================#
LOG_FILE_NAME = "testingbot.txt"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)



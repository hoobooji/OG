import motor.motor_asyncio
from config import DB_URI, DB_NAME
from pytz import timezone
from datetime import datetime, timedelta

# Create an async client with Motor
dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]
collection = database['premium-users']


# Check if the user is a premium user (active only)
async def is_premium_user(user_id):
    user = await collection.find_one({"user_id": user_id})
    if not user:
        return False

    expiration_timestamp = user.get("expiration_timestamp")
    if not expiration_timestamp:
        return False 

    ist = timezone("Asia/Kolkata")

    if isinstance(expiration_timestamp, str):
        expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
    elif isinstance(expiration_timestamp, datetime):
        expiration_time = expiration_timestamp.astimezone(ist)
    else:
        return False 

    return expiration_time > datetime.now(ist)


# Remove premium user
async def remove_premium(user_id):
    await collection.delete_one({"user_id": user_id})


# Remove expired users
async def remove_expired_users():
    current_time = datetime.now().isoformat()
    await collection.delete_many({"expiration_timestamp": {"$lte": current_time}})


# List active premium users
async def list_premium_users():
    ist = timezone("Asia/Kolkata")
    premium_users = collection.find({})
    premium_user_list = []

    async for user in premium_users:
        expiration_time = datetime.fromisoformat(user["expiration_timestamp"]).astimezone(ist)
        remaining_time = expiration_time - datetime.now(ist)

        if remaining_time.total_seconds() > 0:  # Active only
            days, hours, minutes, seconds = (
                remaining_time.days,
                remaining_time.seconds // 3600,
                (remaining_time.seconds // 60) % 60,
                remaining_time.seconds % 60,
            )
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"
            formatted_expiry_time = expiration_time.strftime('%Y-%m-%d %I:%M:%S %p IST')
            premium_user_list.append(
                f"UserID: {user['user_id']} - Expiry: {expiry_info} (Expires at {formatted_expiry_time})"
            )

    return premium_user_list


# Add premium user
async def add_premium(user_id, time_value, time_unit):
    """
    Add a premium user for a specific duration in minutes or days.
    
    Args:
        user_id (int): The ID of the user to add premium access for.
        time_value (int): The numeric value of the duration.
        time_unit (str): The time unit - 'm' for minutes, 'd' for days.
    """
    ist = timezone("Asia/Kolkata")

    if time_unit == 'm':
        expiration_time = datetime.now(ist) + timedelta(minutes=time_value)
    elif time_unit == 'd':
        expiration_time = datetime.now(ist) + timedelta(days=time_value)
    else:
        raise ValueError("Invalid time unit. Use 'm' for minutes or 'd' for days.")

    premium_data = {
        "user_id": user_id,
        "expiration_timestamp": expiration_time.isoformat(),
    }

    await collection.update_one(
        {"user_id": user_id},
        {"$set": premium_data},
        upsert=True
    )

    formatted_expiration_time = expiration_time.strftime('%Y-%m-%d %I:%M:%S %p IST')
    print(f"User {user_id} premium access expires on {formatted_expiration_time}")
    return formatted_expiration_time


# Check user plan (Premium / Not Premium)
async def check_user_plan(user_id):
    user = await collection.find_one({"user_id": user_id})
    if not user:
        return "❌ Yᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ Pʀᴇᴍɪᴜᴍ Usᴇʀ."

    expiration_timestamp = user.get("expiration_timestamp")
    if not expiration_timestamp:
        return "❌ Yᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ Pʀᴇᴍɪᴜᴍ Usᴇʀ."

    ist = timezone("Asia/Kolkata")

    # Handle string or datetime
    if isinstance(expiration_timestamp, str):
        expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
    elif isinstance(expiration_timestamp, datetime):
        expiration_time = expiration_timestamp.astimezone(ist)
    else:
        return "❌ Yᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ Pʀᴇᴍɪᴜᴍ Usᴇʀ."

    remaining_time = expiration_time - datetime.now(ist)

    if remaining_time.total_seconds() > 0:
        days, hours, minutes, seconds = (
            remaining_time.days,
            remaining_time.seconds // 3600,
            (remaining_time.seconds // 60) % 60,
            remaining_time.seconds % 60,
        )
        return f"✅ Yᴏᴜ ᴀʀᴇ ᴀ Pʀᴇᴍɪᴜᴍ Usᴇʀ.\n\nPʟᴀɴ Vᴀʟɪᴅɪᴛʏ: {days}d {hours}h {minutes}m {seconds}s left."

    return "❌ Yᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ Pʀᴇᴍɪᴜᴍ Usᴇʀ."
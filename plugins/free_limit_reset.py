
import asyncio
import time
import logging
from database.database import db
from pyrogram.enums import ParseMode, ChatAction
from database.db_premium import is_premium_user

async def reset_free_limits_task(client):
    """Reset free limits for users after 24 hours and notify them"""
    while True:
        try:
            # Get all free users
            free_users = await db.get_all_free_users()
            
            current_time = time.time()
            reset_count = 0
            
            for user_data in free_users:
                try:
                    user_id = user_data.get("user_id")
                    if not user_id:
                        continue
                    
                    # Check if user is premium - skip premium users
                    is_premium = await is_premium_user(user_id)
                    if is_premium:
                        continue
                    
                    count = user_data.get("count", 0)
                    last_reset = user_data.get("last_reset", 0)
                    
                    # Check if 24 hours have passed since last reset
                    # Reset if user has used their limit and 24 hours have passed
                    if count > 0 and (current_time - last_reset) >= 86400:
                        # Reset the limit
                        await db.free_data.update_one(
                            {"user_id": user_id},
                            {"$set": {"count": 0, "last_reset": current_time}}
                        )
                        
                        # Notify user
                        try:
                            await client.send_message(
                                user_id,
                                "🎉 <b>Good News!</b>\n\n"
                                "Your free video limit has been restored!\n"
                                "You can now access free videos again.\n\n"
                                "Upgrade to Premium for unlimited access! 💳",
                                parse_mode=ParseMode.HTML
                            )
                            reset_count += 1
                        except Exception as e:
                            # User might have blocked the bot or deleted account
                            logging.debug(f"Could not notify user {user_id}: {e}")
                            continue
                            
                except Exception as e:
                    logging.error(f"Error processing user {user_data.get('user_id')}: {e}")
                    continue
            
            if reset_count > 0:
                logging.info(f"Reset free limits for {reset_count} users")
            
            # Wait 1 hour before next check
            await asyncio.sleep(3600)
            
        except Exception as e:
            logging.error(f"Error in reset_free_limits_task: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour before retry




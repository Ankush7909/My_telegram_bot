# migrate_chat_titles.py

import asyncio
from pyrogram import Client
from config import APP_ID, API_HASH, TG_BOT_TOKEN, DB_URI, DB_NAME
from motor.motor_asyncio import AsyncIOMotorClient

async def migrate_chat_titles():
    # Initialize Pyrogram client
    bot = Client(
        "migration_bot",
        api_id=APP_ID,
        api_hash=API_HASH,
        bot_token=TG_BOT_TOKEN
    )
    
    # Initialize MongoDB client
    mongo_client = AsyncIOMotorClient(DB_URI)
    db = mongo_client["linkssharing"]
    channels_collection = db['channels']
    
    async with bot:
        # Find all channels without chat_title
        cursor = channels_collection.find({"chat_title": {"$exists": False}})
        channels_without_titles = await cursor.to_list(length=None)
        
        total = len(channels_without_titles)
        print(f"Found {total} channels without chat titles")
        
        updated_count = 0
        errors = []
        
        for idx, channel in enumerate(channels_without_titles, 1):
            channel_id = channel['channel_id']
            print(f"Processing {idx}/{total}: Channel {channel_id}")

            await asyncio.sleep(1)
            
            try:
                # Get chat information from Telegram
                chat = await bot.get_chat(channel_id)
                
                # Update database entry
                await channels_collection.update_one(
                    {"channel_id": channel_id},
                    {"$set": {"chat_title": chat.title}}
                )
                updated_count += 1
                print(f"Updated title for {channel_id}: {chat.title}")
                
            except Exception as e:
                errors.append((channel_id, str(e)))
                print(f"Error processing {channel_id}: {str(e)}")
                continue
        
        print(f"\nMigration complete!")
        print(f"Successfully updated: {updated_count}/{total}")
        
        if errors:
            print("\nErrors encountered:")
            for channel_id, error in errors:
                print(f"Channel {channel_id}: {error}")

if __name__ == "__main__":
    asyncio.run(migrate_chat_titles())
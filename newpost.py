import asyncio
import base64
from pyrogram import Client as Bot, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.errors import UserNotParticipant, FloodWait, ChatAdminRequired, RPCError
from pyrogram.errors import InviteHashExpired, InviteRequestSent
from database.database import save_channel, delete_channel, get_channels
from config import ADMINS, OWNER_ID
from database.database import save_encoded_link, get_channel_by_encoded_link, save_encoded_link2, get_channel_by_encoded_link2, search_channels_by_title
from helper_func import encode
from datetime import datetime, timedelta

PAGE_SIZE = 6

@Bot.on_inline_query()
async def handle_inline_query(client, inline_query):
    # Check if user is admin first
    if inline_query.from_user.id not in ADMINS:
        
        return
    
    query = inline_query.query.strip()
    results = []

    try:
        if not query:
            await inline_query.answer(
                results=[],
                switch_pm_text="🔍 Search channels...",
                switch_pm_parameter="start",
                cache_time=0
            )
            return

        # Split query into command and search term
        parts = query.split(None, maxsplit=1)
        command = parts[0].lower()
        search_query = parts[1] if len(parts) > 1 else ""

        if command == "direct":
            if not search_query:
                await inline_query.answer(
                    results=[],
                    switch_pm_text="Enter search term for direct links",
                    switch_pm_parameter="help_direct",
                    cache_time=0
                )
                return

            channels = await search_channels_by_title(search_query)
            if not channels:
                await inline_query.answer(
                    results=[],
                    switch_pm_text="❌ No channels found",
                    switch_pm_parameter="help",
                    cache_time=0
                )
                return

            for channel in channels[:10]:  # Limit to 10 results
                encoded_link = await save_encoded_link(channel["channel_id"])
                button_link = f"https://t.me/{client.username}?start={encoded_link}"
                
                results.append(
                    InlineQueryResultArticle(
                        title=f"Direct: {channel['chat_title']}",
                        description="Click to get direct invite link",
                        input_message_content=InputTextMessageContent(
                            message_text="Direct invite link generated!"
                        ),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(
                                text=channel["chat_title"],
                                url=button_link
                            )]
                        ])
                    )
                )

        elif command == "req":
            if not search_query:
                await inline_query.answer(
                    results=[],
                    switch_pm_text="Enter search term for request links",
                    switch_pm_parameter="help_request",
                    cache_time=0
                )
                return

            channels = await search_channels_by_title(search_query)
            if not channels:
                await inline_query.answer(
                    results=[],
                    switch_pm_text="❌ No channels found",
                    switch_pm_parameter="help",
                    cache_time=0
                )
                return

            for channel in channels[:10]:
                encoded_link = await encode(str(channel["channel_id"]))
                await save_encoded_link2(channel["channel_id"], encoded_link)
                button_link = f"https://t.me/{client.username}?start=req_{encoded_link}"
                
                results.append(
                    InlineQueryResultArticle(
                        title=f"Request: {channel['chat_title']}",
                        description="Click to get join request link",
                        input_message_content=InputTextMessageContent(
                            message_text="Join request link generated!"
                        ),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(
                                text=channel["chat_title"],
                                url=button_link
                            )]
                        ])
                    )
                )

        else:
            await inline_query.answer(
                results=[],
                switch_pm_text="❌ Invalid command. Use 'direct' or 'req'",
                switch_pm_parameter="help",
                cache_time=0
            )
            return

        await inline_query.answer(
            results=results,
            cache_time=0,
            is_personal=True
        )

    except Exception as e:
        print(f"Inline query error: {e}")
        await inline_query.answer(
            results=[],
            switch_pm_text="❌ Error processing request",
            switch_pm_parameter="help",
            cache_time=0
        )

# Revoke invite link after 10 minutes
async def revoke_invite_after_10_minutes(client: Bot, channel_id: int, link: str, is_request: bool = False):
    await asyncio.sleep(600)  # 10 minutes
    try:
        if is_request:
            await client.revoke_chat_invite_link(channel_id, link)
            print(f"Join request link revoked for channel {channel_id}")
        else:
            await client.revoke_chat_invite_link(channel_id, link)
            print(f"Invite link revoked for channel {channel_id}")
    except Exception as e:
        print(f"Failed to revoke invite for {channel_id}: {e}")

##----------------------------------------------------------------------------------------------------        
##----------------------------------------------------------------------------------------------------

@Bot.on_message(filters.command('setchannel') & filters.private & filters.user(ADMINS))
async def set_channel(client: Bot, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply("You are not an admin.")
    
    try:
        channel_id = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply("Please check the channel ID. Example: /setchannel <channel_id>")
    
    try:
        chat = await client.get_chat(channel_id)

        if chat.permissions and not (chat.permissions.can_post_messages or chat.permissions.can_edit_messages):
            return await message.reply(f"I am in this channel-{chat.title} but I don't have the necessary permissions.")
        
        await save_channel(channel_id, chat.title)
        return await message.reply(f"✅ Channel-({chat.title})-({channel_id}) has been added successfully.")
    
    except UserNotParticipant:
        return await message.reply("I am not a member of this channel. Please add me and try again.")
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await set_channel(client, message)
    except RPCError as e:
        return await message.reply(f"RPC Error: {str(e)}")
    except Exception as e:
        return await message.reply(f"Unexpected Error: {str(e)}")

##----------------------------------------------------------------------------------------------------
##----------------------------------------------------------------------------------------------------        

@Bot.on_message(filters.command('delchannel') & filters.private & filters.user(ADMINS))
async def del_channel(client: Bot, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply("You are not an admin.")
    
    try:
        channel_id = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply("Invalid channel ID.")
    
    await delete_channel(channel_id)
    return await message.reply(f"❌ Channel {channel_id} has been removed.")

##----------------------------------------------------------------------------------------------------        
##----------------------------------------------------------------------------------------------------

@Bot.on_message(filters.command('channelpost') & filters.private & filters.user(ADMINS))
async def channel_post(client: Bot, message: Message):
    channels = await get_channels()
    if not channels:
        return await message.reply("No channels available. Please use /setchannel first.")

    await send_channel_page(client, message, channels, page=0)


async def send_channel_page(client, message, channels, page):
    total_pages = (len(channels) + PAGE_SIZE - 1) // PAGE_SIZE
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    buttons = []

    row = []
    for channel_id in channels[start_idx:end_idx]:
        try:
            base64_invite = await save_encoded_link(channel_id)
            button_link = f"https://t.me/{client.username}?start={base64_invite}"
            chat = await client.get_chat(channel_id)
            
            row.append(InlineKeyboardButton(chat.title, url=button_link))
            
            if len(row) == 2:
                buttons.append(row)
                row = [] 
        except Exception as e:
            print(f"Error for {channel_id}: {e}")

    if row: 
        buttons.append(row)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Previous", callback_data=f"channelpage_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"channelpage_{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply("📢 Select a channel to post:", reply_markup=reply_markup)


@Bot.on_callback_query(filters.regex(r"channelpage_(\d+)"))
async def paginate_channels(client, callback_query):
    page = int(callback_query.data.split("_")[1])
    channels = await get_channels()
    await callback_query.message.delete()
    await send_channel_page(client, callback_query.message, channels, page)


##----------------------------------------------------------------------------------------------------

@Bot.on_message(filters.command('reqpost') & filters.private & filters.user(ADMINS))
async def req_post(client: Bot, message: Message):
    channels = await get_channels()
    if not channels:
        return await message.reply("No channels available. Please use /setchannel first.")

    await send_request_page(client, message, channels, page=0)


async def send_request_page(client, message, channels, page):
    total_pages = (len(channels) + PAGE_SIZE - 1) // PAGE_SIZE
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    buttons = []

    row = []
    for channel_id in channels[start_idx:end_idx]:
        try:
            base64_request = await encode(str(channel_id))
            await save_encoded_link2(channel_id, base64_request)
            button_link = f"https://t.me/{client.username}?start=req_{base64_request}"
            chat = await client.get_chat(channel_id)

            row.append(InlineKeyboardButton(chat.title, url=button_link))

            if len(row) == 2:
                buttons.append(row)
                row = [] 
        except Exception as e:
            print(f"Error generating request link for {channel_id}: {e}")

    if row: 
        buttons.append(row)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Previous", callback_data=f"reqpage_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"reqpage_{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons) 
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply("📢 Select a channel to request access:", reply_markup=reply_markup)


@Bot.on_callback_query(filters.regex(r"reqpage_(\d+)"))
async def paginate_requests(client, callback_query):
    page = int(callback_query.data.split("_")[1])
    channels = await get_channels()
    await callback_query.message.delete()
    await send_request_page(client, callback_query.message, channels, page)
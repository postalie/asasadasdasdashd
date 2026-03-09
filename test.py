
from telethon import TelegramClient
from config import API_ID, API_HASH
import asyncio

async def main():
    c = TelegramClient('user.session', API_ID, API_HASH)
    await c.connect()
    print('Auth:', await c.is_user_authorized())
    if await c.is_user_authorized():
        me = await c.get_me()
        print('User:', me.first_name, me.username)
    await c.disconnect()

asyncio.run(main())

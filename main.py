from telethon import TelegramClient
import asyncio
from aiogram import Bot, Dispatcher
from parametrs.config import BOT_TOKEN
from client.client import client
from keyboards import adm_keyboards
from dataBase.database import Database
from aiogram import types
from callbacks import adm_callback
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.message_sender import send_daily_digest
import sys
from datetime import datetime
import os

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        filename = datetime.now().strftime("logs/log_%Y-%m-%d_%H-%M.txt")
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

bot_tg = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database(bot_instance=bot_tg)
scheduler = AsyncIOScheduler()
sys.stdout = Logger()
sys.stderr = sys.stdout





async def main():
    await db.connect()
    dp = Dispatcher()
    dp.update.middleware(DatabaseMiddleware(db))
    
    scheduler.add_job(send_daily_digest, 'cron', hour = 15, minute=0, kwargs={'db': db, 'bot': bot_tg})
    scheduler.start()

    ''' from client import client
    dp.include_router(client.router)'''
    
    from handlers import admin_handlers
    dp.include_router(admin_handlers.router)
    
    from callbacks import adm_callback
    dp.include_router(adm_callback.router)
    
    try:
        await dp.start_polling(bot_tg, db=db)
    except Exception as e:
        print(e)
   
    finally:
        await client.disconnect()
    
    print("Бот готов к работе!")

class DatabaseMiddleware:
    def __init__(self, db: Database):
        self.db = db
    
    async def __call__(self, handler, event: types.Update, data):
        data["db"] = self.db  
        return await handler(event, data)


if __name__ == "__main__":
    asyncio.run(main())

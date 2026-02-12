from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
import asyncio
from aiogram import Router, Bot, types
from dataclasses import dataclass
import random 
from parametrs.config_client import api_id_my, api_hash_my, auth_key_hex, dc_id, lang_pack, app_version, lang_code, system_lang_code
from utils.message_sender import send_message_aiogram 
from utils.telegram_session_encoder import TelegramSessionEncoder


#Добавить отправку сообщений от тг бота

@dataclass(frozen=True)
class APIConfig:
    # Используем ваши данные
    api_id: int = api_id_my
    api_hash: str = api_hash_my
    # Остальные параметры устройства можно оставить как есть
    device_model: str = "Desktop"
    system_version: str = "Windows 10"
    app_version: str = app_version
    lang_code: str = lang_code
    system_lang_code: str = system_lang_code
    lang_pack: str = lang_pack



#client = TelegramClient('anon', api_id=api_id, api_hash=api_hash ) 
#client.flood_sleep_threshold = 24*60*60
auth_key = bytes.fromhex(auth_key_hex)
dc_id = dc_id 
session_encoder = TelegramSessionEncoder(auth_key, dc_id)
string_session_str = session_encoder.to_string()
string_session = StringSession(string_session_str)
api_config = APIConfig()
client =  TelegramClient(
            session=string_session,
            api_id=api_config.api_id,
            api_hash=api_config.api_hash,
            flood_sleep_threshold=24 * 60 * 60 
        )

#когда будете запускать у себя или на серваке не пугайтесь, если попросит данные акка, это специально, и только один раз(если устройство не поменяется)
#Пароля видно не будет, просто в txt напишите пароль, в кмд бота, просто один раз пкм жми, и всё.
async def main_aggregator(user_id, db, bot: Bot ):
    try:
        
        '''channels = await db.get_all_channel_ids()
        for channel in channels:
                print(channel)'''
        
        await client.start()
        await asyncio.sleep(random.randint(1, 15))
        await send_message_aiogram(user_id, 'Бот запущен', bot)
        await asyncio.sleep(random.randint(1, 15))
        await client.send_message('me', 'Hello, myself!')
        await asyncio.sleep(random.randint(1, 15))
        me = await client.get_me()
        await asyncio.sleep(random.randint(1, 15))
        print(me)
        print(f"✅ Бот запущен: @{me.username}")
        print(f"ID: {me.id}")
        print(f"Имя: {me.first_name}")
        print(f"Тип: {'Бот' if me.bot else 'Пользователь'}")
    
    finally:
        await client.disconnect()
        await send_message_aiogram(user_id, 'Бот остановился, работа оконченна', bot)

"""if __name__ == "__main__":
    asyncio.run(main_aggregator(ADMIN_ID))
"""
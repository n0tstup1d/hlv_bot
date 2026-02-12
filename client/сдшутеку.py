from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
import asyncio
from aiogram import Router, Bot, types
from dataclasses import dataclass
from parametrs.config import CHANNEL_POST
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


async def check_subscriptions(client, channel_list, user_id, bot):
    """
    Проверяет, состоит ли клиент в каждом из каналов списка.
    Возвращает список только тех каналов, куда есть доступ.
    """
    valid_channels = []
    print("\nНачинаю проверку подписок на каналы...")

    for channel_id_or_url in channel_list:
        try:
            # client.get_entity пытается получить полную информацию о канале.
            # Если доступ запрещен (аккаунт не состоит в нем), будет вызвано исключение.
            await asyncio.sleep(random.randint(1, 15))
            entity = await client.get_entity(channel_id_or_url)
            await asyncio.sleep(random.randint(1, 15))
            # Если ошибок нет, мы успешно состоим в канале
            valid_channels.append(channel_id_or_url)
            await asyncio.sleep(random.randint(1, 15))
            chat_title = getattr(entity, 'title', str(channel_id_or_url))
            await asyncio.sleep(random.randint(1, 15))
            print(f"✅ Успешная подписка на канал: {chat_title}")
            await asyncio.sleep(random.randint(1, 15))
            await send_message_aiogram(user_id, f"✅ Есть доступ к каналу: {chat_title}", bot)

        except errors.ChannelPrivateError:
            print(f"⚠️ Ошибка: Канал {channel_id_or_url} является закрытым, и аккаунт в нем не состоит.")
            await send_message_aiogram(user_id, f"⚠️ Нет доступа к закрытому каналу: {channel_id_or_url}", bot)
        except errors.RPCError as e:
            print(f"⚠️ Ошибка доступа к каналу {channel_id_or_url}: {e}")
            await send_message_aiogram(user_id, f"⚠️ Ошибка доступа к каналу {channel_id_or_url}: {e}", bot)
        except ValueError:
             print(f"⚠️ Ошибка: Некорректный формат ID/URL канала: {channel_id_or_url}")


#когда будете запускать у себя или на серваке не пугайтесь, если попросит данные акка, это специально, и только один раз(если устройство не поменяется)
#Пароля видно не будет, просто в txt напишите пароль, в кмд бота, просто один раз пкм жми, и всё.
async def main_aggregator(user_id, db, bot: Bot ):
    try:
        
        raw_channels_list = await db.get_all_channel_ids()
        
        await client.start()
        await asyncio.sleep(random.randint(1, 15))
        await send_message_aiogram(user_id, 'Бот запущен', bot)
        
        channels = await check_subscriptions(client, raw_channels_list, user_id, bot)
        await asyncio.sleep(random.randint(1, 15))
        
        me = await client.get_me()
        await asyncio.sleep(random.randint(1, 15))
        print(me)
        print(f"✅ Бот запущен: вошли как @{me.username}")
        print(f"ID: {me.id}")
        await asyncio.sleep(random.randint(1, 15))
        @client.on(events.NewMessage(chats=channels))
        async def handler(event):
            """
            Эта функция срабатывает каждый раз, когда появляется новое сообщение 
            в любом из каналов списка SOURCE_CHANNELS.
            """
            print(f"Новое сообщение в чате {event.chat.title or event.chat_id}: {event.message.message[:50]}...")
            
            # 1. Получаем информацию из поста
            message_text = event.message.message
            sender_name = event.chat.title or "Канал"

            # 2. Пересылаем пост в канал назначения
            try:
                print("-"*30)
                print(message_text)
                print("-"*30)
                print(sender_name)
                print("-"*30)
                await client.forward_messages(
                    entity=CHANNEL_POST, # Куда пересылаем (username или ID)
                    messages=event.message.id, # ID сообщения-источника
                    from_peer=event.chat_id    # Откуда берем сообщение (ID чата-источника)
                )
                await send_message_aiogram(user_id, f"➡️ Переслано новое сообщение из {sender_name}.", bot)
            except Exception as e:
                print(f"Ошибка при пересылке сообщения: {e}")
                await send_message_aiogram(user_id, f"⚠️ Не удалось переслать сообщение: {e}", bot)

        # *** Запуск клиента в режиме ожидания ***
        # Эта функция блокирует выполнение, пока клиент не будет отключен вручную (Ctrl+C)
        await client.run_until_disconnected()

    finally:
        
        if client.is_connected():
            await client.disconnect()
        await send_message_aiogram(user_id, '🛑 Бот остановлен.', bot)
"""if __name__ == "__main__":
    asyncio.run(main_aggregator(ADMIN_ID))
"""
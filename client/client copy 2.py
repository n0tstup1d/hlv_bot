from telethon import TelegramClient, events, errors, Button
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon import utils
import asyncio
from aiogram import Router, Bot, types
from dataclasses import dataclass
from parametrs.config import CHANNEL_POST
import random 
from parametrs.config_client import api_id_my, api_hash_my, auth_key_hex, dc_id, lang_pack, app_version, lang_code, system_lang_code
from utils.message_sender import send_message_aiogram, send_post_in_channel
from utils.telegram_session_encoder import TelegramSessionEncoder
# from analyzers.post_analyzer import SimpleAnalyzer
import os
# from utils.analyze_post import PreciseGiveawayFilter
from analyzers.post_analyzer import PostAnalyzer
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from utils.filter_post_ai import request_gigachat_filter_post

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
            #full_channel_id = utils.get_peer_id(entity)
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

async def start_subscriptions(user_id, db, bot: Bot):
    client =  TelegramClient(
            session=string_session,
            api_id=api_config.api_id,
            api_hash=api_config.api_hash,
            flood_sleep_threshold=24 * 60 * 60 
        )
    raw_channels_list = await db.get_all_channel_ids()
    await asyncio.sleep(random.randint(1, 15))
    await client.start()
    await check_subscriptions(client, raw_channels_list, user_id, bot)   


async def main_aggregator(user_id, db, bot: Bot ):
    try:
        
        analyzer = PostAnalyzer(db)
        
        channels = await db.get_all_channel_ids()
        
        await client.start()
        await asyncio.sleep(random.randint(1, 15))
        await send_message_aiogram(user_id, 'Бот запущен', bot)        
        print(f"✅ Бот запущен")
        
        await asyncio.sleep(random.randint(1, 15))
      
        msg = await client.get_messages("@konkyrstelegram", ids=16157) 
        
        print(msg)
        #channels = await check_subscriptions(client, raw_channels_list, user_id, bot)
        await asyncio.sleep(random.randint(1, 15))
        
        # Инициализируем анализатор

        # Проверяем, не обработан ли уже пост
        if msg.fwd_from:
            await asyncio.sleep(random.randint(1, 15))
            channel_id = utils.get_peer_id(msg.fwd_from.from_id)
            await asyncio.sleep(random.randint(1, 15))
            original_id = msg.fwd_from.channel_post
        else:
            await asyncio.sleep(random.randint(1, 15))
            original_id = msg.id
            await asyncio.sleep(random.randint(1, 15))
            channel_id = utils.get_peer_id(msg.peer_id)
        
        is_giveaway, analysis_data = await analyzer.analyze_message(msg)
        print(f"Результат анализа: {analysis_data['decision']}")
        print(f"Ключевые слова: {analysis_data['matched_keywords']}")
        print(f"Баллы: розыгрыш={analysis_data['giveaway_score']:.2f}, "
                f"реклама={analysis_data['ad_score']:.2f}, "
                f"итог={analysis_data['total_score']:.2f}")
        
        
        if is_giveaway:
            print("🎁 Найден розыгрыш! Пересылаем...")
            
   
            try:
                await asyncio.sleep(random.randint(1, 15))
                entity = await client.get_entity(channel_id)
                await asyncio.sleep(random.randint(1, 15))
                if getattr(entity, 'username', None):
                    post_url = f"https://t.me/{entity.username}/{original_id}"
                else:
                    post_url = f"https://t.me/c/{str(channel_id)[4:]}/{original_id}"
            except Exception:
                post_url = f"https://t.me/c/{str(channel_id)[4:]}/{original_id}"
            
            try:
                path = None
                
                if msg.media:
                    await asyncio.sleep(random.randint(1, 15))
                    path = await client.download_media(msg.media, f"file_{msg.id}")
                await asyncio.sleep(random.randint(1, 15))
                data = await request_gigachat_filter_post(msg.message)
                if data.get('is_giveaway') == True:
                    message_text_post = f"🎁{data.get('giveaway_name')}🎁"
                    message_text_post += "\n"
                    message_text_post += f"🎁 Призы:{', '.join(data.get('prizes', []))}"
                    message_text_post += "\n"
                    message_text_post += f"⚠️ Условия:{', '.join(data.get('conditions', []))}"
                    message_text_post += "\n"
                    message_text_post += f"🕓 Окончание розыгрыша:{', '.join(data.get('conditions', []))}"
                    
                    await send_post_in_channel(
                        message_text_post, 
                        bot, 
                        path, 
                        post_url
                    )

            except Exception as e:
                print(f"Ошибка при пересылке: {e}")
            finally:

                if path and os.path.exists(path):
                    os.remove(path)
        else:
            print(f"Пост не является розыгрышем. Решение: {analysis_data['decision']}")
    
        await client.run_until_disconnected()    
    finally:
        
        if client.is_connected():
            await client.disconnect()
        await send_message_aiogram(user_id, '🛑 Бот остановлен.', bot)

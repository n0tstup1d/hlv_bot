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
import os
from analyzers.post_analyzer import PostAnalyzer
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from utils.filter_post_ai import request_gigachat_filter_post
from datetime import datetime


@dataclass(frozen=True)
class APIConfig:

    api_id: int = api_id_my
    api_hash: str = api_hash_my
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
            flood_sleep_threshold=24 * 60 * 60,
            connection_retries=10,  # Увеличиваем количество попыток
            retry_delay=5,  # Задержка между попытками
            auto_reconnect=True,  # Автоматическое переподключение
            timeout=60,  # Таймаут 60 секунд
            request_retries=10,
            sequential_updates=True,  # Обрабатывать обновления последовательно
            receive_updates=True,# Повторы запросов
            raise_last_call_error=False  # Не падать при ошибке последнего вызова
        )

async def check_subscriptions(client, channel_list, user_id, bot):
    valid_channels = []
    print("\nНачинаю проверку и подписку на каналы...")

    for channel_id_or_url in channel_list:
        try:
            await asyncio.sleep(random.randint(1, 5))
            # Пытаемся получить сущность канала
            entity = await client.get_entity(channel_id_or_url)
            await asyncio.sleep(random.randint(1, 5))
            chat_title = getattr(entity, 'title', str(channel_id_or_url))

            # Попытка вступления в канал
            await asyncio.sleep(random.randint(1, 5))
            await client(JoinChannelRequest(entity))
            await asyncio.sleep(random.randint(1, 5))
            
            valid_channels.append(channel_id_or_url)
            print(f"✅ Успешная подписка: {chat_title}")
            await send_message_aiogram(user_id, f"✅ Вы подписались на канал: {chat_title}", bot)

        except errors.FloodWaitError as e:
            print(f"⏳ Ожидание {e.seconds} секунд из-за флуд-контроля...")
            await asyncio.sleep(e.seconds)
        except (errors.ChannelPrivateError, errors.InviteHashExpiredError):
            print(f"⚠️ Канал {channel_id_or_url} закрыт или ссылка недействительна.")
            await send_message_aiogram(user_id, f"⚠️ Нет доступа к закрытому каналу: {channel_id_or_url}", bot)
        except Exception as e:
            print(f"⚠️ Ошибка с каналом {channel_id_or_url}: {e}")

    await send_message_aiogram(user_id, "🏁 Процесс подписки завершен", bot)
    return valid_channels
'''async def check_subscriptions(client, channel_list, user_id, bot):
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

    await send_message_aiogram(user_id, f"🏁 Подписались на все каналы", bot)'''

#когда будете запускать у себя или на серваке не пугайтесь, если попросит данные акка, это специально, и только один раз(если устройство не поменяется)
#Пароля видно не будет, просто в txt напишите пароль, в кмд бота, просто один раз пкм жми, и всё.

async def start_subscriptions(user_id, db, bot: Bot):
    client =  TelegramClient(
            session=string_session,
            api_id=api_config.api_id,
            api_hash=api_config.api_hash,
            flood_sleep_threshold=24 * 60 * 60,
            auto_reconnect=True 
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
        await send_message_aiogram(user_id, '✅ Бот запущен', bot)        
        print(f"✅ Бот запущен")
        
        await asyncio.sleep(random.randint(1, 15))
      
        @client.on(events.NewMessage(chats=channels))
        async def handler(msg):
            await asyncio.sleep(0.5)
            if not msg.message:
                return
            
            # Пропускаем редактирования сообщений
            if msg.edit_date and msg.edit_date != 0:
                return
            
            # Пропускаем сообщения без текста и медиа
            if not msg.text and not msg.media:
                return
            # msg = await client.get_messages("@konkyrstelegram", ids=16125)
            
            post_id = msg.id           
            await asyncio.sleep(random.randint(1, 15))
            print("="*30)
            print(msg)
            print("="*30)
            if hasattr(msg.message, 'message'):
                message_obj = msg.message.message
            else:
            
                message_obj = msg.message or ""
            print(f"нашли пост {message_obj[:20]}") 
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
                    data = await request_gigachat_filter_post(message_obj)
                    if msg.media:
                        await asyncio.sleep(random.randint(1, 15))
                        path = await client.download_media(msg.media, f"file_{msg.id}")
                    await asyncio.sleep(random.randint(1, 15))
                    
                    if data.get('is_giveaway') == True:
                        EMOJIS = ["🎁", "🎉", "🎊", "✨", "⭐", "🌟", "💫", "🔥", "💎"]
                        emojis1 = random.choice(EMOJIS)
                        EMOJIS_CAUTION = ["❗","⚠️","‼️","🛑","❣️"]
                        emojis2 = random.choice(EMOJIS_CAUTION)
                        message_text_post = f"{emojis1} {data.get('giveaway_name')} {emojis1}"
                        message_text_post += "\n\n"
                        if data.get('prizes', []):
                            message_text_post += f"🎁 Призы:\n- " + "\n- ".join(data.get('prizes', []))
                        else:
                            message_text_post += "🎁 Призы: будут объявлены позже"
                        message_text_post += "\n\n"
                        if data.get('conditions', []):
                            message_text_post += f"{emojis2} Условия:\n- " + "\n- ".join(data.get('conditions', []))
                            message_text_post += "\n\n"
                        
                        today = datetime.now().date()
                        end_date_str = data.get('end_date', 'Не указана')
                        
                        # Проверяем, что end_date_str не None и не строка "Не указана"
                        if end_date_str and end_date_str != 'Не указана':
                            try:
                                # Пробуем распарсить дату из строки
                                if isinstance(end_date_str, str):
                                    # Убираем возможное время, оставляем только дату
                                    date_part = end_date_str.split()[0] if ' ' in end_date_str else end_date_str
                                    # Убираем лишние символы (точки в конце, скобки и т.д.)
                                    date_part = date_part.strip('.,;!?()[]{}')
                                    # Парсим дату
                                    end_date_obj = datetime.strptime(date_part, '%d.%m.%Y')
                                    end_date_only = end_date_obj.date()
                                    
                                    delta = (end_date_only - today).days
                                    if delta < -3:  # Более 3 дней назад
                                        print(f"⚠️ Дата в прошлом: {end_date_only}. Исправляю...")
                                        # Переносим на следующий год
                                        end_date_only = end_date_only.replace(year=today.year + 1)
                                        delta = (end_date_only - today).days
                                    
                                    has_valid_date = True
                                else:
                                    # Если это уже объект datetime
                                    end_date_only = end_date_str.date()
                                    delta = (end_date_only - today).days
                                    has_valid_date = True
                            except (ValueError, AttributeError) as e:
                                print(f"⚠️ Ошибка парсинга даты: {e}, дата: {end_date_str}")
                                delta = None
                                has_valid_date = False
                        else:
                            delta = None
                            has_valid_date = False
                        
                        if has_valid_date:
                            if delta < 0:
                                # Если все еще отрицательно, показываем просто дату без подсчета дней
                                message_text_time = f"🗓️ Финал: {end_date_obj.strftime('%d.%m.%Y')}"
                            if delta == 0:
                                message_text_time = f"🔥 Итоги сегодня!"
                            elif delta == 1:
                                message_text_time = f"⏳ Итоги завтра"
                            elif delta <= 3:
                                message_text_time = f"⏰ Осталось {delta} дня/дней"
                            else:
                                message_text_time = f"🗓️ Финал: {end_date_obj.strftime('%d.%m.%Y')}"
                        else:
                            # Если дата не указана или невалидна, используем исходную строку
                            message_text_time = f"🗓️ Финал: {end_date_str}"
                        
                        message_text_post += message_text_time
                        
                        await send_post_in_channel(
                            message_text_post, 
                            bot, 
                            path, 
                            post_url
                        )
                        
                        analysis_data['filtered_message_text'] = message_text_post
                        
                        await db.save_post_analysis_simple(
                            analysis_data=analysis_data,
                            channel_id=channel_id,          # Полученный ранее
                            original_id=original_id,        # Полученный ранее
                            message_text=msg.message        # Исходный текст поста
                        )
                        
                        await db.mark_post_as_forwarded(
                            post_id=post_id, 
                            forwarded_to=CHANNEL_POST,
                            post_link=post_url
                        )
                        
                        
                        

                except Exception as e:
                    print(f"Ошибка при пересылке: {e}")
                finally:

                    if path and os.path.exists(path):
                        os.remove(path)
            else:
                print(f"Пост не является розыгрышем. Решение: {analysis_data['decision']}")
        print("👂 Слушаем тгк")
        await send_message_aiogram(user_id, '👂 Слушаем тгк', bot)  
        await client.run_until_disconnected()    
    finally:
        
        if client.is_connected():
            await client.disconnect()
       
        await send_message_aiogram(user_id, '🛑 Бот остановлен.', bot)

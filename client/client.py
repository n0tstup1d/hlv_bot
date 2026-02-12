from telethon import TelegramClient, events, errors, Button
from telethon import types as type
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon import utils
import asyncio
from utils.get_file_type import get_file_type_from_path
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
from datetime import datetime, date
import re
import python_socks
from parametrs.config_proxy import ip, port, login, password

message_queue = asyncio.Queue()

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
main_aggregator_task = None
queue_consumer_task = None
stop_event = asyncio.Event()
proxy = (python_socks.ProxyType.SOCKS5, ip, port, True, login, password)


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
            device_model=api_config.device_model,
            flood_sleep_threshold=24 * 60 * 60,
            connection_retries=None,  # Увеличиваем количество попыток
            retry_delay=5,  # Задержка между попытками
            auto_reconnect=True,  # Автоматическое переподключение
            timeout=100,  # Таймаут 60 секунд
            request_retries=10,
              # Обрабатывать обновления последовательно
            receive_updates=True,
            # Повторы запросов
            raise_last_call_error=False  # Не падать при ошибке последнего вызова
        )

#sequential_updates=True,

# Создаем функцию для запуска потребителя очереди
async def start_queue_consumer(user_id, db, bot, analyzer, processed_groups, client):
    """Запуск потребителя очереди сообщений"""
    global queue_consumer_task, stop_event
    
    stop_event.clear()  # Сбрасываем флаг остановки
    
    async def process_queue_messages():
        """Потребитель очереди - обрабатывает сообщения из очереди"""
        while not stop_event.is_set():
            try:
                # Ждем новое сообщение с таймаутом для проверки stop_event
                try:
                    msg = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue  # Проверяем stop_event и продолжаем
                
                # Вставьте сюда весь ваш код обработки сообщений из handler
                # (от строки 142 "if not msg.message:" до конца функции)
                # ... ваш код обработки ...
                
                message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Ошибка при обработке сообщения из очереди: {e}")
                if not message_queue.empty():
                    message_queue.task_done()
    
    # Запускаем потребителя
    queue_consumer_task = asyncio.create_task(process_queue_messages())
    return queue_consumer_task

# Функция для остановки всех задач
async def stop_all_tasks():
    """Остановка всех фоновых задач"""
    global queue_consumer_task, stop_event
    
    # Устанавливаем флаг остановки
    stop_event.set()
    
    # Отменяем задачу потребителя
    if queue_consumer_task and not queue_consumer_task.done():
        queue_consumer_task.cancel()
        try:
            await queue_consumer_task
        except asyncio.CancelledError:
            pass
    
    # Очищаем очередь (опционально)
    while not message_queue.empty():
        try:
            message_queue.get_nowait()
            message_queue.task_done()
        except asyncio.QueueEmpty:
            break
    
    queue_consumer_task = None


async def process_queue_messages(user_id, db, bot, analyzer, processed_groups, client):
    """Потребитель очереди - обрабатывает сообщения из очереди"""
    while True:
        try:
            # Ждем новое сообщение из очереди
            msg = await message_queue.get()
            
            # Здесь перенесите ВЕСЬ код обработки сообщения из вашего текущего handler
            # начиная с if not msg.message: и до конца функции handler
            
            if msg.fwd_from:
                
                channel_id = utils.get_peer_id(msg.fwd_from.from_id)
                
                original_id = msg.fwd_from.channel_post
                try:
                    
                    entity = await client.get_entity(channel_id)
            
                    channel_username = entity.username
                    channel_title = entity.title # Название канала (например, "Новости")
                    
                    name_to_print = f"@{channel_username}" if channel_username else f"'{channel_title}'"
                    print(f"🔎 Нашел канал в пересланном: {name_to_print}")

                    await check_subscription_one(client, channel_username, user_id, bot)
                    print(f"✅ Успешная подписка на канал: {name_to_print} (ID: {entity.id})")
                    await send_message_aiogram(user_id, f"✅ Успешная подписка на канал: {name_to_print} (ID: {entity.id})", bot)
                except Exception as e:
                    print(f"❌ Ошибка при подписке: {e}")
            else:
                
                original_id = msg.id
                
                channel_id = utils.get_peer_id(msg.peer_id)
            
            if msg.fwd_from:
                
                channel_id = utils.get_peer_id(msg.fwd_from.from_id)
                
                original_id = msg.fwd_from.channel_post
                
                is_processed = await db.is_post_processed(original_id, channel_id)
                if is_processed:
                    print(f"⏭️ Пост уже обработан в БД, пропускаем. channel_id={channel_id}, original_id={original_id}")
                    return
                
                
            else:
                
                original_id = msg.id
                
                channel_id = utils.get_peer_id(msg.peer_id)
            
            is_processed = await db.is_post_processed(original_id, channel_id)
            if is_processed:
                print(f"⏭️ Пост уже обработан в БД, пропускаем. channel_id={channel_id}, original_id={original_id}")
                return
                        
            
            print("="*30)
            print(msg)
            print("="*30)
            if hasattr(msg.message, 'message'):
                message_obj = msg.message.message
            else:
            
                message_obj = msg.message or ""
            try:
                
                
                if msg.fwd_from:
                    # Для пересланных сообщений получаем entity оригинального канала
                    try:
                        # Получаем сущность оригинального канала из пересылки
                        original_channel_id = utils.get_peer_id(msg.fwd_from.from_id)
                        original_entity = await client.get_entity(original_channel_id)
                        
                        # Используем ID сообщения из пересылки
                        original_message_id = msg.fwd_from.channel_post
                        
                        # Формируем ссылку на оригинальный пост
                        if getattr(original_entity, 'username', None):
                            post_url = f"https://t.me/{original_entity.username}/{original_message_id}"
                        else:
                            chat_id = str(utils.get_peer_id(original_entity))
                            post_url = f"https://t.me/c/{chat_id.replace('-100', '')}/{original_message_id}"
                            
                    except Exception as e:
                        print(f"Ошибка при получении информации об оригинальном канале: {e}")
                        # Fallback: используем текущий канал
                        entity = await client.get_entity(msg.peer_id)
                        original_id = msg.fwd_from.channel_post if msg.fwd_from else msg.id
                        if getattr(entity, 'username', None):
                            post_url = f"https://t.me/{entity.username}/{original_id}"
                        else:
                            chat_id = str(utils.get_peer_id(entity))
                            post_url = f"https://t.me/c/{chat_id.replace('-100', '')}/{original_id}"
                else:
                    # Для непересланных сообщений используем текущий канал
                    entity = await client.get_entity(msg.peer_id)
                    if getattr(entity, 'username', None):
                        post_url = f"https://t.me/{entity.username}/{msg.id}"
                    else:
                        chat_id = str(utils.get_peer_id(entity))
                        post_url = f"https://t.me/c/{chat_id.replace('-100', '')}/{msg.id}"
                        
            except Exception as e:
                print(f"Ошибка при формировании ссылки: {e}")
                post_url = "Ссылка недоступна"

            print(f"нашли пост: {message_obj[:20]}... | URL: {post_url}")
            # await send_message_aiogram(user_id, f"нашли пост: {message_obj[:20]}... | URL: {post_url}", bot)  
            
            is_giveaway, analysis_data = await analyzer.analyze_message(msg)
            
            print(f"Результат анализа: {analysis_data['decision']}")
            print(f"Ключевые слова: {analysis_data['matched_keywords']}")
            print(f"Баллы: розыгрыш={analysis_data['giveaway_score']:.2f}, "
                    f"реклама={analysis_data['ad_score']:.2f}, "
                    f"итог={analysis_data['total_score']:.2f}")
            
            print(f"analysis_data['end_date'] {analysis_data['end_date']}")
            if is_giveaway:
                print("🎁 Найден розыгрыш! Пересылаем...")
                if msg.fwd_from:
                    try:
                        
                        entity = await client.get_entity(channel_id)
                
                        channel_username = entity.username
                        channel_title = entity.title # Название канала (например, "Новости")
                        
                        name_to_print = f"@{channel_username}" if channel_username else f"'{channel_title}'"

                        await send_message_aiogram("-1003802732454", text= f"Взгляните на такой телеграмм канал: {name_to_print} (ID: {entity.id})",bot= bot)
                    except Exception as e:
                        print(f"❌ Ошибка при подписке: {e}")
                try:
                    path = None
                    data = await request_gigachat_filter_post(message_obj)
                    print(data)
                    
                    print(f"🎯 Получены данные от ИИ: качество={data.get('quality_score')}")

                    if not data.get('is_giveaway', False):
                        print(f"📭 ИИ определил, что это не розыгрыш")
                        
                        # Сохраняем в БД с флагом REJECTED
                        analysis_data['decision'] = 'REJECTED'
                        analysis_data['decision_reason'] = f"ИИ определил, что это не розыгрыш"
                        analysis_data['quality_score'] = data.get('quality_score', 5)
                        
                        # Сохраняем в БД и выходим
                        result = await db.save_post_analysis_simple(
                            analysis_data=analysis_data,
                            channel_id=channel_id,
                            original_id=original_id,
                            message_text=str(message_obj)
                        )
                        
                        if result:
                            print(f"✅ Отклонённый пост сохранён в БД с ID: {result}")
                        
                        return
                    
                    if data["audience_scale"] == "local":
                        return

                    
                    quality_score = data.get('quality_score', 5)  # По умолчанию 5
                    trash_reason = data.get('trash_reason', '')
                    
                    # Проверяем порог отсечения
                    if quality_score <= 4:
                        print(f"🚫 Пост отсеян. Качество: {quality_score}/10. Причина: {trash_reason}")
                        
                        # Сохраняем в БД с флагом REJECTED
                        analysis_data['decision'] = 'REJECTED'
                        analysis_data['decision_reason'] = f"Низкое качество ({quality_score}/10): {trash_reason}"
                        analysis_data['quality_score'] = quality_score
                        
                        # Сохраняем в БД и выходим
                        result = await db.save_post_analysis_simple(
                            analysis_data=analysis_data,
                            channel_id=channel_id,
                            original_id=original_id,
                            message_text=str(message_obj)
                        )
                        
                        if result:
                            print(f"✅ Отклонённый пост сохранён в БД с ID: {result}")
                        
                        return 
                    
            
                    print(f"✅ Пост одобрен. Качество: {quality_score}/10")
                    if msg.media:
                        
                        path = await client.download_media(msg.media, f"file_{msg.id}")
                        if path:
                        
                            file_type = await get_file_type_from_path(path)
                            print(f"📁 Тип файла: {file_type}, путь: {path}")
                    
                    
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
                        if data.get('end_date'):
                            data['end_date'] = parse_date_from_text(data['end_date'])
                        end_date_str = data.get('end_date')
                        
                        if end_date_str and end_date_str.lower() not in ['null', 'не указана', 'none']:
                            message_text_post += f"🗓️ Финал: {end_date_str}"
                        
                        message = await send_post_in_channel(
                            message_text_post, 
                            bot, 
                            path, 
                            post_url,
                            file_type
                        )
                        
                        our_post_link = None
                    if message:
                        # Формируем ссылку на наш пост
                        chat_username = CHANNEL_POST
                        if isinstance(CHANNEL_POST, int):
                            # Если это числовой ID канала
                            # Для приватных каналов ссылка будет в формате t.me/c/xxxxx/123
                            our_post_link = f"https://t.me/c/{str(CHANNEL_POST).replace('-100', '')}/{message.message_id}"
                        elif CHANNEL_POST.startswith('@'):
                            # Если это username канала
                            our_post_link = f"https://t.me/{CHANNEL_POST[1:]}/{message.message_id}"
                        else:
                            our_post_link = f"https://t.me/{CHANNEL_POST}/{message.message_id}"
                    
                    data['filtered_message_text'] = message_text_post
                    
                    try:
                        if data.get('end_date') and data.get('end_date').lower() not in ['null', 'не указана', 'none']:
                            data['end_date'] = datetime.strptime(data.get('end_date'), '%d.%m.%Y').date()
                        else:
                            data['end_date'] = None
                    except Exception as e:
                        print(f"Ошибка парсинга даты: {e}")
                        data['end_date'] = None
                    
                    data['post_link'] = post_url
                    
                    if data:
                        print("✅ Есть данные для сохранения в БД")
                        
                        # Сохраняем анализ
                        result = await db.save_post_analysis_simple(
                            analysis_data=data,
                            channel_id=channel_id,
                            original_id=original_id,
                            message_text=str(message_obj)
                        )
                        
                        if result:
                            print(f"✅ Анализ успешно сохранен в БД с ID: {result}")
                            
                            # Отмечаем пост как пересланный с сохранением ссылки на наш пост
                            await db.mark_post_as_forwarded(
                                post_id=result, 
                                forwarded_to=CHANNEL_POST,
                                post_link=post_url,
                                our_post_link=our_post_link  # Добавляем ссылку на наш пост
                            )
                        else:
                            print("❌ Не удалось сохранить анализ в БД")
                    else:
                        print("❌ Нет данных анализа для сохранения")
                        
                        
                        

                except Exception as e:
                    print(f"Ошибка при пересылке: {e}")
                finally:

                    if path and os.path.exists(path):
                        os.remove(path)
            else:
                print(f"Пост не является розыгрышем. Решение: {data['decision']}")
            
           
            message_queue.task_done()
            
        except asyncio.CancelledError:
            # Задача была отменена
            break
        except Exception as e:
            print(f"Ошибка при обработке сообщения из очереди: {e}")


async def check_subscription_one(client, channel_id_or_url, user_id, bot):
    print(f"\nНачинаю проверку и подписку на канал: {channel_id_or_url}...")
    
    try:
        await asyncio.sleep(random.randint(1, 5))
        # Получаем сущность канала (username или ID)
        entity = await client.get_entity(channel_id_or_url)
        chat_title = getattr(entity, 'title', str(channel_id_or_url))

        # Попытка вступления
        await asyncio.sleep(random.randint(1, 5))
        await client(JoinChannelRequest(entity))
        
        print(f"✅ Успешная подписка: {chat_title}")
        await send_message_aiogram(user_id, f"✅ Вы подписались на канал: {chat_title}", bot)
        
        return True # Подписка прошла успешно

    except errors.FloodWaitError as e:
        print(f"⏳ Ожидание {e.seconds} секунд из-за флуд-контроля...")
        await asyncio.sleep(e.seconds)
        return False
    except (errors.ChannelPrivateError, errors.InviteHashExpiredError):
        print(f"⚠️ Канал {channel_id_or_url} закрыт или ссылка недействительна.")
        await send_message_aiogram(user_id, f"⚠️ Нет доступа к каналу: {channel_id_or_url}", bot)
        return False
    except Exception as e:
        print(f"⚠️ Ошибка с каналом {channel_id_or_url}: {e}")
        return False

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
            valid_channels.append(channel_id_or_url)
            print(f"✅ Успешная подписка: {chat_title}")
            await send_message_aiogram(user_id, f"✅ Вы подписались на канал: {chat_title}", bot)

            print("таймер")
            await asyncio.sleep(random.randint(180, 300))
            await asyncio.sleep(random.randint(1, 5))
            
            
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
    try:
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
    finally:
        if client.is_connected():
            await client.disconnect()
       
        await send_message_aiogram(user_id, '🛑 Бот остановлен.', bot)
        

async def keep_alive(client):
    while True:
        try:
            # Используем клиент, который передадим
            await client.get_me()
        except Exception as e:
            # Логирование ошибки, если нужно
            print(f"Keep-alive error: {e}")
        await asyncio.sleep(60)

async def parse_date_from_text(date_text):
    """Парсит дату из текста в форматах: '11 февраля', 'ДД.ММ.ГГГГ' и т.д."""
    if not date_text or isinstance(date_text, date):
        return date_text
    
    date_text = str(date_text).strip().lower()
    
    # Проверяем специальные значения
    if date_text in ['null', 'не указана', 'none', '']:
        return None
    
    # Пробуем стандартный формат ДД.ММ.ГГГГ
    try:
        return datetime.strptime(date_text, '%d.%m.%Y').date()
    except ValueError:
        pass
    
    # Пробуем русский месяц: "11 февраля"
    month_map = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }
    
    for month_ru, month_num in month_map.items():
        if month_ru in date_text:
            # Извлекаем число
            match = re.search(r'(\d{1,2})', date_text)
            if match:
                day = int(match.group(1))
                current_year = datetime.now().year
                try:
                    return datetime(current_year, month_num, day).date()
                except ValueError:
                    pass
    
    return None


async def main_aggregator(user_id, db, bot: Bot ):
    try:

        
        analyzer = PostAnalyzer(db)
        channels = await db.get_all_channel_ids()
        
        print(f"📊 Загружено каналов: {len(channels)}")
        await asyncio.sleep(random.randint(1, 5))
        await client.start()
        print("✅ Клиент Telegram запущен")
        await asyncio.sleep(random.randint(1, 5))
        asyncio.create_task(keep_alive(client))
        print("✅ Задача keep_alive запущена")
        
        await send_message_aiogram(user_id, '✅ Бот запущен', bot)
        
        await asyncio.sleep(random.randint(1, 5))
        
        processed_groups = set()
        
        consumer_task = asyncio.create_task(
            process_queue_messages(user_id, db, bot, analyzer, processed_groups, client)
        )
        
        # ПРОБЛЕМА ВОЗМОЖНО ЗДЕСЬ:
        @client.on(events.NewMessage(chats=channels))
        async def handler(msg):
            
        # try:
        #     await asyncio.sleep(random.randint(1, 5))
        #     # msg = await client.get_messages("@toporlive", ids=175503)
        #     print(f"✅ Сообщение получено: {msg}")
        # except Exception as e:
        #     print(f"❌ Ошибка при получении сообщения: {e}")
            
        #     await send_message_aiogram(user_id, f'❌ Ошибка: {e}', bot)
        #     return
        
            if not msg:
                print("❌ Сообщение не найдено или пустое")
                await send_message_aiogram(user_id, '❌ Сообщение не найдено', bot)
                return
            
            print(f"📝 Начинаем обработку сообщения ID: {msg.id}")
            
            # analyzer = PostAnalyzer(db)
            
            # channels = await db.get_all_channel_ids()
            
            # await client.start()
            # asyncio.create_task(keep_alive(client))
            # print("✅ Задача keep_alive запущена.")
            # await asyncio.sleep(random.randint(1, 15))
            # await send_message_aiogram(user_id, '✅ Бот запущен', bot)        
            # print(f"✅ Бот запущен")
            
            
            
            
                
                
            # # msg = await client.get_messages("@konkyrstelegram", ids=16263)https://t.me/konkyrstelegram/16315
            # msg = await client.get_messages("@konkyrstelegram", ids=16576)
                    
            await asyncio.sleep(0.5)
            if not msg.message:
                print("Скипнули пост")
                return
            
            if hasattr(msg, 'grouped_id') and msg.grouped_id:
                # Проверяем, не обрабатывали ли мы уже эту группу
                if msg.grouped_id in processed_groups:
                    print("Скипнули пост")
                    return
                
                # Добавляем в кэш (храним 5 минут)
                processed_groups.add(msg.grouped_id)
                
                # Создаем таймер для очистки кэша
                async def clear_group():
                    await asyncio.sleep(300)  # 5 минут
                    if msg.grouped_id in processed_groups:
                        processed_groups.remove(msg.grouped_id)
                
                asyncio.create_task(clear_group())
                
                # Берем только первое сообщение группы для анализа
                # (или можно агрегировать все сообщения)
                print(f"📸 Сообщение входит в группу медиа (ID группы: {msg.grouped_id})")
                    
            # Пропускаем редактирования сообщений
            if msg.edit_date and msg.edit_date != 0:
                print("Скипнули пост")
                return
            
            # # Пропускаем сообщения без текста и медиа
            if not msg.text and not msg.media:
                print("Скипнули пост")
                return
            
            #post_id = msg.id
            
            try:
                await message_queue.put(msg)
                print(f"📥 Сообщение добавлено в очередь. Размер очереди: {message_queue.qsize()}")
            except Exception as e:
                print(f"Ошибка при добавлении в очередь: {e}")
            
            
            
        print("👂 Слушаем тгк")
        await send_message_aiogram(user_id, '👂 Слушаем тгк', bot)  
        await client.run_until_disconnected()    
    
    finally:
        # Отменяем задачу потребителя при завершении
        if 'consumer_task' in locals():
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        
        if client.is_connected():
            await client.disconnect()
       
        await send_message_aiogram(user_id, '🛑 Бот остановлен.', bot)
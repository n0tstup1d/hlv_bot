from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
import asyncio
from aiogram import Router, Bot, types
from dataclasses import dataclass
from parametrs.config import CHANNEL_POST
import random 
from parametrs.config_client import api_id_my, api_hash_my, auth_key_hex, dc_id, lang_pack, app_version, lang_code, system_lang_code
from utils.message_sender import send_message_aiogram 
from utils.telegram_session_encoder import TelegramSessionEncoder
from analyzers.post_analyzer import SimpleAnalyzer

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
    '''"""
    Автоматически присоединяется к каналам из списка.
    Возвращает список сущностей успешно присоединенных каналов.
    """
    joined_entities = []
    print("\nНачинаю присоединение к каналам...")
    
    for channel_identifier in channel_list:
        try:
            # Пробуем получить entity канала
            entity = await client.get_entity(channel_identifier)
            await asyncio.sleep(random.randint(1, 3))
            
            chat_title = getattr(entity, 'title', str(channel_identifier))
            print(f"🔍 Проверяю канал: {chat_title}")
            
            # Проверяем, является ли это супергруппой/каналом
            if hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast'):
                # Проверяем, подписан ли уже
                try:
                    # Получаем информацию о чате
                    full_chat = await client.get_full_entity(entity)
                    if hasattr(full_chat, 'left') and full_chat.left:
                        print(f"🤖 Бот не состоит в канале {chat_title}, присоединяюсь...")
                        await asyncio.sleep(random.randint(2, 5))
                        
                        # Пробуем присоединиться
                        try:
                            await client.join_chat(entity)
                            await asyncio.sleep(random.randint(2, 5))
                            print(f"✅ Успешно присоединился к каналу: {chat_title}")
                            await send_message_aiogram(user_id, f"✅ Присоединился к каналу: {chat_title}", bot)
                            joined_entities.append(entity)
                        except errors.InviteRequestSentError:
                            print(f"⚠️ Запрос на вступление отправлен для: {chat_title}")
                            await send_message_aiogram(user_id, f"⚠️ Отправлен запрос на вступление в: {chat_title}", bot)
                            joined_entities.append(entity)
                        except errors.UserAlreadyParticipantError:
                            print(f"ℹ️ Уже состою в канале: {chat_title}")
                            joined_entities.append(entity)
                    else:
                        print(f"ℹ️ Уже состою в канале: {chat_title}")
                        joined_entities.append(entity)
                        
                except Exception as e:
                    print(f"⚠️ Не удалось проверить статус подписки для {chat_title}: {e}")
                    # Пробуем просто присоединиться
                    try:
                        await client.join_chat(entity)
                        await asyncio.sleep(random.randint(2, 5))
                        print(f"✅ Успешно присоединился к каналу: {chat_title}")
                        await send_message_aiogram(user_id, f"✅ Присоединился к каналу: {chat_title}", bot)
                        joined_entities.append(entity)
                    except errors.InviteRequestSentError:
                        print(f"⚠️ Запрос на вступление отправлен для: {chat_title}")
                        await send_message_aiogram(user_id, f"⚠️ Отправлен запрос на вступление в: {chat_title}", bot)
                        joined_entities.append(entity)
                    except errors.UserAlreadyParticipantError:
                        print(f"ℹ️ Уже состою в канале: {chat_title}")
                        joined_entities.append(entity)
                    except Exception as join_e:
                        print(f"❌ Не удалось присоединиться к {chat_title}: {join_e}")
                        await send_message_aiogram(user_id, f"❌ Не удалось присоединиться к {chat_title}", bot)
            
            else:
                print(f"⚠️ {channel_identifier} не является каналом/супергруппой")
                
        except errors.UsernameNotOccupiedError:
            print(f"❌ Канал {channel_identifier} не существует")
            await send_message_aiogram(user_id, f"❌ Канал {channel_identifier} не существует", bot)
        except errors.ChannelPrivateError:
            print(f"❌ Канал {channel_identifier} приватный, нужна инвайт-ссылка")
            await send_message_aiogram(user_id, f"❌ Канал {channel_identifier} приватный", bot)
        except Exception as e:
            print(f"❌ Ошибка с каналом {channel_identifier}: {type(e).__name__}: {e}")
            await send_message_aiogram(user_id, f"❌ Ошибка с каналом {channel_identifier}", bot)
    
    print(f"\n📊 Итог: успешно присоединился к {len(joined_entities)} из {len(channel_list)} каналов")
    return joined_entities'''
    """
    Пытается принудительно присоединиться ко всем каналам в списке.
    Возвращает список Entity каналов, в которых аккаунт теперь состоит.
    """
    verified_entities = []
    print("\n🔄 Начинаю процесс принудительного присоединения ко всем каналам...")
    
    for channel_identifier in channel_list:
        chat_title = str(channel_identifier)
        try:
            # Превращаем в строку для проверки
            identifier_str = str(channel_identifier).strip()
            print(f"Попытка обработки: {identifier_str}")
            
            entity = None

            # 1. Проверяем, является ли это ссылкой-приглашением (t.me/+... или joinchat/...)
            if 't.me/+' in identifier_str or 't.me/joinchat/' in identifier_str:
                # Извлекаем хэш (все, что после последнего слеша или знака +)
                invite_hash = identifier_str.split('/')[-1].replace('+', '')
                
                try:
                    await asyncio.sleep(random.randint(2, 5))
                    # Пытаемся вступить по ссылке
                    await client(ImportChatInviteRequest(invite_hash))
                    await asyncio.sleep(random.randint(2, 5))
                    # После вступления получаем entity, чтобы добавить в список прослушивания
                    entity = await client.get_entity(identifier_str)
                    await asyncio.sleep(random.randint(2, 5))
                except errors.UserAlreadyParticipantError:
                    # Если уже в канале, просто получаем entity
                    entity = await client.get_entity(identifier_str)
            
            else:
                await asyncio.sleep(random.randint(2, 5))
                # 2. Если это юзернейм или ID
                entity = await client.get_entity(identifier_str)
                await client(JoinChannelRequest(entity))

            # Если entity получен, добавляем в список
            if entity:
                verified_entities.append(entity)
                title = getattr(entity, 'title', identifier_str)
                print(f"✅ Успешно: {title} (ID: {entity.id})")
                await send_message_aiogram(user_id, f"✅ Присоединился к каналу: {title}", bot)
            
            await asyncio.sleep(random.randint(2, 5)) # Анти-спам задержка

        except errors.InviteHashExpiredError:
            print(f"❌ Ошибка: Ссылка просрочена {identifier_str}")
            await send_message_aiogram(user_id, f"⚠️ Ссылка просрочена: {identifier_str}", bot)
        
        except errors.ChannelPrivateError:
            print(f"❌ Ошибка: Канал {chat_title} приватный. Для присоединения нужна полная ссылка-приглашение (t.me/+Code).")
            await send_message_aiogram(user_id, f"⚠️ Не удалось присоединиться к приватному каналу: {chat_title}. Нужна ссылка-приглашение.", bot)

        except errors.InviteHashInvalidError:
            print(f"❌ Ошибка: Ссылка-приглашение недействительна для {chat_title}.")
            await send_message_aiogram(user_id, f"⚠️ Неверная ссылка-приглашение: {chat_title}", bot)
            
        except Exception as e:
            # Обработка других ошибок (например, вы забанены в канале)
            print(f"❌ Критическая ошибка при присоединении к каналу {chat_title}: {type(e).__name__}: {e}")
            await send_message_aiogram(user_id, f"⚠️ Критическая ошибка при присоединении к {chat_title}: {e}", bot)

    print(f"\n📊 Итог: буду отслеживать {len(verified_entities)} каналов")
    return verified_entities
#когда будете запускать у себя или на серваке не пугайтесь, если попросит данные акка, это специально, и только один раз(если устройство не поменяется)
#Пароля видно не будет, просто в txt напишите пароль, в кмд бота, просто один раз пкм жми, и всё.

async def start_subscriptions(db, bot: Bot, user_id):
    client =  TelegramClient(
            session=string_session,
            api_id=api_config.api_id,
            api_hash=api_config.api_hash,
            flood_sleep_threshold=24 * 60 * 60 
        )
    raw_channels_list = await db.get_all_channel_ids()
    await asyncio.sleep(random.randint(1, 15))
    await check_subscriptions(client, raw_channels_list, user_id, bot)    
    await client.start()


async def main_aggregator(user_id, db, bot: Bot ):
    try:
        
        channels = await db.get_all_channel_ids()
        
        await client.start()
        await asyncio.sleep(random.randint(1, 15))
        await send_message_aiogram(user_id, 'Бот запущен', bot)
        
        #channels = await check_subscriptions(client, raw_channels_list, user_id, bot)
        await asyncio.sleep(random.randint(1, 15))
        
        # Инициализируем анализатор
        analyzer = SimpleAnalyzer()
        
        me = await client.get_me()
        await asyncio.sleep(random.randint(1, 15))
        print(me)
        print(f"✅ Бот запущен: вошли как @{me.username}")
        print(f"ID: {me.id}")
        await asyncio.sleep(random.randint(1, 15))
        @client.on(events.NewMessage(chats=channels))
        async def handler(event):
            try:
                # Пропускаем служебные сообщения
                if not event.message:
                    return
                
                print(f"\n📨 Новый пост из: {event.chat.title}")
                
                # Проверяем, не обрабатывали ли уже этот пост
                already_processed = await db.is_post_processed(
                    event.message.id,
                    event.chat_id
                )
                
                if already_processed:
                    print(f"⏭️ Пост уже обработан, пропускаем")
                    return
                
                
                
            except Exception as e:
                print(f"❌ Ошибка при обработке поста: {e}")
                import traceback
                traceback.print_exc()
                
                try:
                    await send_message_aiogram(
                        user_id,
                        f"⚠️ Ошибка при обработке поста из {event.chat.title}: {str(e)[:100]}",
                        bot
                    )
                except:
                    pass
        
        # Запускаем клиент
        
            '''"""
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
        await client.run_until_disconnected()'''
        print("\n👂 Начинаю прослушивание каналов...")
        await client.run_until_disconnected()    
    finally:
        
        if client.is_connected():
            await client.disconnect()
        await send_message_aiogram(user_id, '🛑 Бот остановлен.', bot)
"""if __name__ == "__main__":
    asyncio.run(main_aggregator(ADMIN_ID))
"""
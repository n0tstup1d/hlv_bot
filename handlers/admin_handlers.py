from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.types import Message
from aiogram.filters import Command, StateFilter

import asyncio
import json
import time
import io
from typing import List, Dict, Any

from aiogram.fsm.context import FSMContext
from aiogram.methods import GetChat
from openpyxl import load_workbook

import keyboards.adm_keyboards as kb
from states.states import States
from parametrs.config import ADMIN_ID as AD
from client.client import start_subscriptions, main_aggregator, client

router = Router()



@router.message(Command('start'))
async def cmd_start(message: types.Message, db):
   
        user_id = message.from_user.id

        adm_id = await db.get_all_user_ids()
        if user_id in adm_id:
                await message.answer(f"Добро пожаловать {message.from_user.first_name}", reply_markup=kb.main_menu_panel())
        else:
                await message.answer(f"Ваш user_id: <code>{user_id}</code>", parse_mode="HTML")

# @router.message(States.waiting_add_channel)
# async def waiting_add_adm(message: types.Message, state: FSMContext, db, bot: Bot):
#    text_data = ""

    # if message.document and message.document.mime_type == 'text/plain':
    #     file_bytes = await bot.download(message.document.file_id)
    #     text_data = file_bytes.read().decode('utf-8')
    # elif message.text:
    #     text_data = message.text
    # else:
    #     await message.answer("Пришли текст или .txt файл со списком каналов/ссылок")
    #     return

    # raw_channels = text_data.split()
    # channels = []

    # for item in raw_channels:
    #     item = item.strip()
    #     # Проверяем: это юзернейм ИЛИ ссылка t.me
    #     if item.startswith('@') or 't.me/' in item:
    #         channels.append(item)
    
    # if not channels:
    #     await message.answer("Не нашел в сообщении ни @username, ни ссылок t.me")
    #     return

    # existing_channels = await db.get_all_channel_ids()
    # added_count = 0
    # skipped_count = 0

    # # 3. Добавляем в базу
    # for chan in channels:
    #     if chan not in existing_channels:
    #         try:
    #             await db.add_channel(chan)
    #             added_count += 1
    #         except Exception as e:
    #             print(f"Ошибка при добавлении {chan}: {e}")
    #     else:
    #         skipped_count += 1

    # await message.answer(
    #     f"✅ Готово!\n"
    #     f"Добавлено: {added_count}\n"
    #     f"Уже были в базе: {skipped_count}", reply_markup=kb.start_sub
    # )
    # await state.clear()

@router.message(States.waiting_add_channel)
async def waiting_add_channel(message: types.Message, state: FSMContext, db, bot: Bot):
    text_data = ""
    
    if message.document and message.document.mime_type == 'text/plain':
        file_bytes = await bot.download(message.document.file_id)
        text_data = file_bytes.read().decode('utf-8')
    elif message.text:
        text_data = message.text
    else:
        await message.answer("Пришлите текстовый файл (.txt) или текст со списком каналов")
        return
    
    lines = text_data.strip().split('\n')
    channels = [line.strip() for line in lines if line.strip()]
    
    if not channels:
        await message.answer("Список каналов пуст")
        return
    
    existing_channels = await db.get_all_channel_ids()
    progress_msg = await message.answer(f"Начинаю обработку {len(channels)} каналов...")
    
    added_count = 0
    skipped_count = 0
    error_count = 0
    
    # ИЗМЕНЕНИЕ: Убрали жесткий список allowed_targets
    for i, channel in enumerate(channels, 1):
        try:
            if i % 5 == 0:
                await progress_msg.edit_text(
                    f"Прогресс: {i}/{len(channels)}\nДобавлено: {added_count}\nПропущено: {skipped_count}"
                )

            # ИЗМЕНЕНИЕ: Проверяем корректный формат канала
            # Принимаем каналы в формате:
            # - @username
            # - https://t.me/username
            # - t.me/username
            if not (channel.startswith('@') or 't.me/' in channel or 'https://t.me/' in channel):
                skipped_count += 1
                print(f"Пропущен неверный формат: {channel}")
                continue
            
            # ИЗМЕНЕНИЕ: Приводим к единому формату @username для хранения в БД
            normalized_channel = channel
            if 't.me/' in channel or 'https://t.me/' in channel:
                # Извлекаем username из ссылки
                parts = channel.split('/')
                username = parts[-1].replace('@', '').strip()
                if username:
                    normalized_channel = f"@{username}"
                else:
                    skipped_count += 1
                    continue
            
            # Проверяем на дубликат в БД
            if normalized_channel in existing_channels:
                skipped_count += 1
                continue
            
            # Добавляем в БД
            await db.add_channel(normalized_channel)
            added_count += 1
            existing_channels.append(normalized_channel)
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            error_count += 1
            print(f"Ошибка на {channel}: {e}")
    
    result_text = (
        f"✅ Обработка завершена!\n\n"
        f"Всего: {len(channels)}\n"
        f"Добавлено: {added_count}\n"
        f"Пропущено: {skipped_count}\n"
        f"Ошибок: {error_count}"
    )
    
    await progress_msg.edit_text(result_text, reply_markup=kb.cancel_to_adm_menu())
    
    if added_count > 0:
        await message.answer("Начать подписку?", reply_markup=kb.start_sub())
    
    await state.clear()

'''@router.message(States.waiting_add_channel)
async def waiting_add_adm(message: types.Message, state: FSMContext, db, bot: Bot):
    text_data = ""

    # 1. Проверяем, прислали файл или текст
    if message.document and message.document.mime_type == 'text/plain':
        file_bytes = await bot.download(message.document.file_id)
        text_data = file_bytes.read().decode('utf-8')
    elif message.text:
        text_data = message.text
    else:
        await message.answer("Пришли текст или .txt файл со списком каналов")
        return

    # 2. Получаем список всех username (убираем лишние пробелы и пустые строки)
    channels = [c.strip() for c in text_data.split() if c.strip().startswith('@')]
    
    if not channels:
        await message.answer("Не нашел в сообщении ни одного корректного username (начинающегося с @)")
        return

    chan_id_list = await db.get_all_channel_ids()
    added_count = 0

    # 3. Цикл обработки
    for new_chat in channels:
        if new_chat not in chan_id_list:
            try:
                await db.add_channel(new_chat)
                added_count += 1
            except Exception as e:
                print(f"Ошибка при добавлении {new_chat}: {e}")

    await message.answer(f"Обработка завершена!\nДобавлено новых каналов: {added_count}")
    await state.clear()
'''
'''@router.message(States.waiting_add_channel)
async def waiting_add_adm(message: types.Message, state: FSMContext, db, bot: Bot):
    new_chat = message.text
    
    if new_chat.startswith('@'):
        print("Строка начинается с символа '@'")
        print(new_chat)
        chan_id = await db.get_all_channel_ids()
        print(chan_id)
        if new_chat in chan_id:
            await message.answer("Канал с таким username, уже есть", reply_markup=kb.cancel_to_adm_menu())
            return
        try:        
            await message.answer(text=f"Добавляем новый тгк: \n\nchannel_id: {new_chat}")
            
            await db.add_channel(new_chat)
            
            await message.answer(text=f'Успешно добавлен ноый ТГК {new_chat}', parse_mode="HTML")
            
        except Exception as e:
            await message.answer(f"Неудалось добавить канал {e}")
        finally:
            await state.clear()
    else:
        await message.answer("Строка НЕ начинается с символа '@'.\nТы точно username кидаешь?")
        return
'''
@router.message(States.waiting_add_adm)
async def waiting_add_adm(message: types.Message, state: FSMContext, db, bot: Bot):
    if not message.text.isdigit():
            await message.answer("Введите ID админа")
            return
    id_adm = int(message.text)
    print(id_adm)
    adm_id = await db.get_all_user_ids()
    print(adm_id)
    if id_adm in adm_id:
        await message.answer("Админ с таким user_id, уже есть", reply_markup=kb.cancel_to_adm_menu())
        return
    try:

        await message.answer(text=f"Добавляем нового админа, {id_adm}")
        
        await db.add_admin(id_adm)
        
        message = await bot.send_message(text=f'Поздравляем, вы стали администратором!!!\n <a href="tg://user?id={AD}">чат с ГА</a> ', chat_id=id_adm, parse_mode="HTML")
        await bot.send_message(text=f'Cтал администратором <a href="tg://user?id={id_adm}">ЧАТ</a>', chat_id=AD, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"Неудалось добавить нового администраторa {e}")
    finally:
        await state.clear()

@router.message(StateFilter(None), F.text)
async def handle_buttons(message: types.Message, db, bot: Bot):
    text = message.text
    user_id = message.from_user.id
    adm_id = await db.get_all_user_ids()
    
    if user_id in adm_id:
        if text == "СТАРТ":
            
            try:
                await main_aggregator(AD, db, bot)
                
            except Exception as e:
                await message.answer(text=f"Неудалось запустить бота {e}")

        if text == "СТОП":
            try:
                await client.disconnect()
                await message.answer(text=f"Бот успешно остановлен")
                print("Останавили бота")
            except Exception as e:
                await message.answer(text=f"Неудалось остановить бота {e}")
                
        if text == "Меню запуска":
            
            await message.answer(text="Меню запусков ботов", reply_markup=kb.menu_start_stop_client())
            
        elif text == "админ панель":
            try:
                await message.answer(text=f"ADMIN PANEL v0.1", reply_markup= kb.admin_panel() )
            except Exception as e:
                await message.answer(text=f"Неудалось открыть админ панель {e}")
    else:
        message.answer("T - T")
        
        

@router.message(Command("stats"))
async def cmd_stats(message: Message, db):
    """Получение статистики"""
    stats = await db.get_analysis_stats(7)
    
    text = (
        f"📊 Статистика за 7 дней:\n"
        f"• Всего постов: {stats['total_posts'] or 0}\n"
        f"• Розыгрышей: {stats['giveaway_posts'] or 0}\n"
        f"• Рекламы: {stats['ad_posts'] or 0}\n"
        f"• Переслано: {stats['forwarded_posts'] or 0}\n"
        f"• Средний скор: {stats['avg_score'] or 0:.2f}"
    )
    
    await message.answer(text)


@router.message(Command("channel_stats"))
async def cmd_channel_stats(message: Message, db):
    """Статистика по каналу"""
    user_id = message.from_user.id

    adm_id = await db.get_all_user_ids()
    if user_id in adm_id:
        try:
            # Получаем username из команды
            parts = message.text.split()
            if len(parts) < 2:
                await message.answer("Укажите username канала: /channel_stats @username")
                return
            
            username = parts[1].replace('@', '')
            
            # Получаем канал из БД
            async with db.pool.acquire() as conn:
                channel = await conn.fetchrow(
                    'SELECT * FROM channels WHERE channel_username = $1',
                    username
                )
                
                if not channel:
                    await message.answer(f"Канал {username} не найден в БД")
                    return
                
                # Получаем статистику
                stats = await db.get_channel_stats(channel['channel_id'])
                
                if stats:
                    text = (
                        f"📊 Статистика канала {username}:\n"
                        f"• Всего постов: {stats['total_posts']}\n"
                        f"• Розыгрышей: {stats['giveaway_posts']}\n"
                        f"• Рекламы: {stats['ad_posts']}\n"
                        f"• Последний розыгрыш: {stats['last_giveaway_date'].strftime('%d.%m.%Y %H:%M') if stats['last_giveaway_date'] else 'нет'}"
                    )
                else:
                    text = f"Для канала {username} нет статистики"
                
                await message.answer(text)
        
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")


# ======================================================================
#  Работа с загрузкой аккаунтов (JSON / TXT / Excel) и их редактированием
# ======================================================================


def _normalize_field_name(name: str) -> str:
    """
    Нормализация имени столбца / ключа в единый формат:
    - в нижний регистр
    - пробелы/дефисы/точки -> подчеркивание
    """
    if not name:
        return ""
    n = str(name).strip().lower()
    for ch in [" ", "-", ".", "\u00a0"]:
        n = n.replace(ch, "_")
    return n


def _parse_json_accounts(text: str) -> List[Dict[str, Any]]:
    """
    Парсинг JSON в список аккаунтов.
    Поддерживает:
    - список словарей
    - объект {"accounts": [ ... ]}
    - по одному JSON-объекту в строке.
    """
    text = text.strip()
    if not text:
        return []

    # 1. Пытаемся разобрать весь текст как один JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None

    accounts: List[Dict[str, Any]] = []

    if isinstance(data, list):
        accounts = [item for item in data if isinstance(item, dict)]
    elif isinstance(data, dict):
        if isinstance(data.get("accounts"), list):
            accounts = [item for item in data["accounts"] if isinstance(item, dict)]
        else:
            accounts = [data]
    else:
        # 2. Пробуем читать "по одной JSON-строке на строку"
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    accounts.append(obj)
            except json.JSONDecodeError:
                continue

    return accounts


def _parse_delimited_text_accounts(text: str) -> List[Dict[str, Any]]:
    """
    Простой парсер табличного текста: первая строка — заголовки столбцов,
    далее строки со значениями, разделённые ; , или табом.
    Это позволяет использовать .txt как "псевдо-Excel".
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return []

    header_line = lines[0]
    delimiter = ";"
    if "," in header_line and header_line.count(",") >= header_line.count(";"):
        delimiter = ","
    if "\t" in header_line:
        delimiter = "\t"

    headers_raw = [h.strip() for h in header_line.split(delimiter)]
    headers = [_normalize_field_name(h) for h in headers_raw]

    accounts: List[Dict[str, Any]] = []
    for row_line in lines[1:]:
        parts = [p.strip() for p in row_line.split(delimiter)]
        if not any(parts):
            continue
        account: Dict[str, Any] = {}
        for key, value in zip(headers, parts):
            if not key:
                continue
            account[key] = value
        if account:
            accounts.append(account)

    return accounts


def _parse_excel_accounts(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Парсинг Excel (.xlsx / .xls) в список словарей:
    - первая строка: заголовки
    - остальные: значения
    """
    wb = load_workbook(filename=io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header_row = rows[0]
    headers = [_normalize_field_name(cell) for cell in header_row]

    accounts: List[Dict[str, Any]] = []
    for row in rows[1:]:
        if row is None:
            continue
        if not any(row):
            continue
        account: Dict[str, Any] = {}
        for key, value in zip(headers, row):
            if not key:
                continue
            if value is None:
                continue
            account[key] = value
        if account:
            accounts.append(account)

    return accounts


def _format_account_message(account: Dict[str, Any], index: int, total: int) -> str:
    """
    Красивое текстовое представление аккаунта для показа админу.
    """
    api_id = account.get("api_id") or account.get("apiId") or account.get("api-id")
    api_hash = account.get("api_hash") or account.get("apiHash") or account.get("api-hash")

    app_version = account.get("app_version")
    lang_code = account.get("lang_code")
    system_lang_code = account.get("system_lang_code")
    lang_pack = account.get("lang_pack")
    type_account = account.get("type_account")

    proxy = account.get("proxy") or {}
    proxy_host = account.get("proxy_host") or proxy.get("host")
    proxy_port = account.get("proxy_port") or proxy.get("port")
    proxy_username = account.get("proxy_username") or proxy.get("username")
    proxy_password = account.get("proxy_password") or proxy.get("password")
    proxy_type = account.get("proxy_type") or proxy.get("type")

    lines = [
        f"Аккаунт {index + 1}/{total}",
        "",
        f"api_id: {api_id}",
        f"api_hash: {api_hash}",
        f"app_version: {app_version}",
        f"lang_code: {lang_code}",
        f"system_lang_code: {system_lang_code}",
        f"lang_pack: {lang_pack}",
        f"type_account: {type_account}",
        "",
        "Прокси:",
        f"  host: {proxy_host}",
        f"  port: {proxy_port}",
        f"  username: {proxy_username}",
        f"  password: {proxy_password}",
        f"  type: {proxy_type}",
    ]

    return "\n".join(lines)


@router.message(States.waiting_upload_data)
async def waiting_upload_data(message: types.Message, state: FSMContext, bot: Bot):
    """
    Приём файла/текста с аккаунтами (JSON / TXT / Excel),
    парсинг в список аккаунтов и предложение начать пошаговый обзор.
    """
    # Возможность отменить
    if message.text and message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Загрузка аккаунтов отменена.", reply_markup=kb.cancel_to_adm_menu())
        return

    accounts: List[Dict[str, Any]] = []

    # ------------ Обработка файла ------------
    if message.document:
        file = await bot.download(message.document.file_id)
        file_bytes = file.read()
        file_name = (message.document.file_name or "").lower()
        mime = (message.document.mime_type or "").lower()

        # JSON
        if file_name.endswith(".json") or "json" in mime:
            try:
                text = file_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = file_bytes.decode("utf-8", errors="ignore")
            accounts = _parse_json_accounts(text)

        # Excel
        elif file_name.endswith((".xlsx", ".xls")) or "spreadsheet" in mime:
            try:
                accounts = _parse_excel_accounts(file_bytes)
            except Exception as e:
                await message.answer(f"Не удалось прочитать Excel-файл: {e}")
                return

        # Текстовый файл: пробуем как JSON, потом как табличный текст
        else:
            try:
                text = file_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = file_bytes.decode("utf-8", errors="ignore")

            accounts = _parse_json_accounts(text)
            if not accounts:
                accounts = _parse_delimited_text_accounts(text)

    # ------------ Обработка текста ------------
    elif message.text:
        text = message.text.strip()
        accounts = _parse_json_accounts(text)
        if not accounts:
            accounts = _parse_delimited_text_accounts(text)

    else:
        await message.answer(
            "Пришлите файл (.json / .xlsx / .txt) или текст с таблицей аккаунтов."
        )
        return

    if not accounts:
        await message.answer(
            "Не удалось распознать ни одного аккаунта.\n"
            "Убедитесь, что:\n"
            "- JSON содержит список объектов или поле 'accounts',\n"
            "- или в .txt первая строка — заголовки колонок (api_id;api_hash;...)."
        )
        return

    await state.update_data(accounts=accounts, current_index=0)

    await message.answer(
        f"Найдено аккаунтов: {len(accounts)}.\n"
        "Нажмите «Начать просмотр», чтобы по очереди отредактировать и сохранить каждый аккаунт.",
        reply_markup=kb.accounts_review_start(),
    )


@router.message(States.editing_account_field)
async def editing_account_field(message: types.Message, state: FSMContext):
    """
    Получаем новое значение выбранного поля аккаунта и обновляем его в списке.
    """
    new_value = (message.text or "").strip()

    if new_value.lower() == "отмена":
        await state.clear()
        await message.answer("Редактирование аккаунтов отменено.", reply_markup=kb.cancel_to_adm_menu())
        return

    data = await state.get_data()
    accounts: List[Dict[str, Any]] = data.get("accounts") or []
    current_index: int = data.get("current_index", 0)
    field_to_edit: str = data.get("field_to_edit")

    if not accounts or current_index >= len(accounts) or not field_to_edit:
        await message.answer("Нет активного аккаунта для редактирования.")
        await state.clear()
        return

    account = accounts[current_index]

    # Обработка прокси-полей: proxy_host/port/... могут лежать в account["proxy"] или в корне
    if field_to_edit.startswith("proxy_"):
        # Пытаемся сохранить и в вложенный объект proxy, и в плоское поле
        account_proxy = account.get("proxy") or {}

        # Имя внутри proxy без префикса proxy_
        inner_name = field_to_edit[len("proxy_") :]
        inner_name = inner_name if inner_name != "proxy" else "host"

        account_proxy[inner_name] = new_value
        account["proxy"] = account_proxy
        account[field_to_edit] = new_value
    else:
        account[field_to_edit] = new_value

    accounts[current_index] = account
    await state.update_data(accounts=accounts, field_to_edit=None)

    # Показываем ОБНОВЛЁННЫЕ данные в том же сообщении с кнопками
    text = _format_account_message(account, current_index, len(accounts))

    account_message_id = data.get("account_message_id")
    account_message_chat_id = data.get("account_message_chat_id")

    # Сообщение-подсказка, что обновление прошло успешно
    await message.answer("Значение обновлено.")

    # Если знаем, какое сообщение содержит аккаунт, редактируем именно его
    if account_message_id and account_message_chat_id:
        await message.bot.edit_message_text(
            chat_id=account_message_chat_id,
            message_id=account_message_id,
            text=text,
            reply_markup=kb.account_edit_keyboard(),
        )
    else:
        # На всякий случай, если по какой-то причине ID не сохранились — шлём новое сообщение
        await message.answer(text, reply_markup=kb.account_edit_keyboard())

    await state.set_state(States.reviewing_accounts)
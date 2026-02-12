from aiogram import Bot,Router, Dispatcher, types, Bot, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputFile
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from parametrs.config import ADMIN_ID as AD
from datetime import timedelta
from keyboards import adm_keyboards as kb
from states.states import States 
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
from dataBase.database import Database
import random
from client.client import start_subscriptions, main_aggregator, client
from utils.message_sender import send_daily_digest


import os
import uuid
from pathlib import Path
import re


router = Router()



@router.callback_query(lambda c: c.data.startswith("edit_performer_"))
async def add_channel(callback: types.CallbackQuery, db, state: FSMContext ):
    try:
        await state.clear()
        part = callback.data.split('_')
        print(part[2])
        id_track = part[2]
        performer = await db.get_performer(id_track)
        print(performer)
        
        await callback.message.edit_text(text="Вставьте ID канала:", parse_mode = "HTML",reply_markup=kb.add_channel())# 
        
        await state.set_state(States.waiting_add_channel)
        
    except Exception as e:
        print(e)
        #start_sub_all_channel

@router.callback_query(F.data == "start_sub_all_channel")
async def start_sub(callback: types.CallbackQuery, db: Database):
    await callback.answer() 
    await callback.message.edit_text("Запускаем подписку...")
    await start_subscriptions(callback.from_user.id, db, callback.bot)

@router.callback_query(F.data == "start_main_client")
async def start_sub(callback: types.CallbackQuery, db: Database):
    await callback.answer() 
    try:
        await main_aggregator(AD, db, callback.bot)
        
    except Exception as e:
        await callback.message.answer(text=f"Неудалось запустить бота {e}")


@router.callback_query(F.data == "stop_main_client")
async def start_sub(callback: types.CallbackQuery, db: Database):
    await callback.answer() 
    try:
        await client.disconnect()
        await callback.message.answer(text=f"Бот успешно остановлен")
        print("Останавили бота")
    except Exception as e:
        await callback.message.answer(text=f"Неудалось остановить бота {e}")
@router.callback_query(F.data == "post_daydjest")
async def start_sub(callback: types.CallbackQuery, db: Database):
    await callback.answer() 
    await callback.message.edit_text("Запускаем дайджест...")
    await db.debug_today_giveaways()
    await send_daily_digest( db, callback.bot)
    
@router.callback_query(F.data == "backup_bd")
async def add_admin(callback: types.CallbackQuery, db: Database):
    await callback.answer()
    await callback.message.edit_text("Выгружаем из сервера бэкап базы данных...")
    await db.backup_database_and_send_to_admin(callback.from_user.id)
     

@router.callback_query(F.data == "add_adm")
async def add_admin(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Пришлите user_id нового админа.\n \n p.s. Обычный пользователь может узнать свой user_id через нашего бота прописав /start", reply_markup=kb.cancel_to_adm_menu())
    await state.set_state(States.waiting_add_adm)
    await callback.answer() 

@router.callback_query(F.data == "add_channel")
async def add_channel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Пришлите тгк. \n\nКидаем @username \n\nПока что только публичные...', parse_mode='HTML', reply_markup=kb.cancel_to_adm_menu())
    await state.set_state(States.waiting_add_channel)
    await callback.answer()


@router.callback_query(F.data == "upload_data")
async def upload_data(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        'Пришлите файл .json с аккаунтами (или .xlsx / .txt / .json для обычного парсинга).\n\n'
        'Если это таблица JSON-аккаунтов, бот предложит отредактировать каждый и сохранить в базу.\n\n'
        'Напишите «отмена» чтобы отменить.',
        reply_markup=kb.cancel_to_adm_menu()
    )
    await state.set_state(States.waiting_upload_data)
    await callback.answer() 


@router.callback_query(F.data == "manage_accounts")
async def manage_accounts(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """
    Просмотр и редактирование уже сохранённых в БД аккаунтов.
    Использует те же состояния/клавиатуры, что и обзор загруженных аккаунтов.
    """
    await callback.answer()

    try:
        accounts = await db.get_all_accounts()
    except Exception as e:
        await callback.message.edit_text(f"❌ Не удалось получить список аккаунтов: {e}", reply_markup=kb.admin_panel())
        return

    if not accounts:
        await callback.message.edit_text("В базе данных пока нет аккаунтов.", reply_markup=kb.admin_panel())
        return

    current_index = 0

    from handlers.admin_handlers import _format_account_message

    text = _format_account_message(accounts[current_index], current_index, len(accounts))

    await state.update_data(
        accounts=accounts,
        current_index=current_index,
        account_message_id=callback.message.message_id,
        account_message_chat_id=callback.message.chat.id,
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.account_edit_keyboard()
    )
    await state.set_state(States.reviewing_accounts)


@router.callback_query(F.data == "acc_start_review")
async def acc_start_review(callback: types.CallbackQuery, state: FSMContext):
    """
    Старт пошагового просмотра/редактирования загруженных JSON-аккаунтов.
    """
    data = await state.get_data()
    accounts = data.get("accounts") or []
    current_index = data.get("current_index", 0)

    if not accounts:
        await callback.answer("Нет загруженных аккаунтов", show_alert=True)
        return

    if current_index >= len(accounts):
        current_index = 0
        await state.update_data(current_index=current_index)

    from handlers.admin_handlers import _format_account_message  # локальный импорт, чтобы избежать циклов на старте

    text = _format_account_message(accounts[current_index], current_index, len(accounts))
    await callback.message.edit_text(
        text,
        reply_markup=kb.account_edit_keyboard()
    )
    # Запоминаем, какое сообщение содержит данные аккаунта и кнопки
    await state.update_data(
        account_message_id=callback.message.message_id,
        account_message_chat_id=callback.message.chat.id,
    )
    await state.set_state(States.reviewing_accounts)
    await callback.answer()


@router.callback_query(F.data.startswith("acc_edit_"))
async def acc_edit_field(callback: types.CallbackQuery, state: FSMContext):
    """
    Нажатие на кнопку редактирования конкретного поля аккаунта.
    Запоминаем, какое поле нужно изменить, и просим текстом прислать новое значение.
    """
    field_map = {
        "acc_edit_api_id": "api_id",
        "acc_edit_api_hash": "api_hash",
        "acc_edit_app_version": "app_version",
        "acc_edit_lang_code": "lang_code",
        "acc_edit_system_lang_code": "system_lang_code",
        "acc_edit_lang_pack": "lang_pack",
        "acc_edit_type_account": "type_account",
        "acc_edit_proxy_host": "proxy_host",
        "acc_edit_proxy_port": "proxy_port",
        "acc_edit_proxy_username": "proxy_username",
        "acc_edit_proxy_password": "proxy_password",
        "acc_edit_proxy_type": "proxy_type",
    }

    field = field_map.get(callback.data)
    if not field:
        await callback.answer("Неизвестное поле", show_alert=True)
        return

    # Запоминаем, какое поле редактируем и в каком сообщении отображается аккаунт
    await state.update_data(
        field_to_edit=field,
        account_message_id=callback.message.message_id,
        account_message_chat_id=callback.message.chat.id,
    )
    await state.set_state(States.editing_account_field)

    await callback.message.answer(f"Введите новое значение для поля: {field}")
    await callback.answer()


@router.callback_query(F.data == "acc_save")
async def acc_save(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """
    Сохранение текущего аккаунта в БД и переход к следующему.
    """
    data = await state.get_data()
    accounts = data.get("accounts") or []
    current_index = data.get("current_index", 0)

    if not accounts or current_index >= len(accounts):
        await callback.answer("Нет аккаунта для сохранения", show_alert=True)
        return

    account = accounts[current_index]

    try:
        account_id = account.get("account_id")
        if account_id is not None:
            # Обновляем уже существующий аккаунт в БД
            await db.update_account(account_id, account)
        else:
            # Новый аккаунт — добавляем (ON CONFLICT обновит по api_id/api_hash)
            await db.add_account(account)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка сохранения аккаунта: {e}")
        await callback.answer()
        return

    current_index += 1

    if current_index >= len(accounts):
        await state.clear()
        await callback.message.edit_text(
            "✅ Все аккаунты обработаны.",
            reply_markup=kb.cancel_to_adm_menu()
        )
        await callback.answer()
        return

    # Переходим к следующему аккаунту
    await state.update_data(
        current_index=current_index,
        accounts=accounts,
        account_message_id=callback.message.message_id,
        account_message_chat_id=callback.message.chat.id,
    )

    from handlers.admin_handlers import _format_account_message

    next_account = accounts[current_index]
    text = _format_account_message(next_account, current_index, len(accounts))
    await callback.message.edit_text(
        text,
        reply_markup=kb.account_edit_keyboard()
    )
    await state.set_state(States.reviewing_accounts)
    await callback.answer("Аккаунт сохранён")


@router.callback_query(F.data == "acc_delete")
async def acc_delete(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """
    Удаление текущего аккаунта.
    - Если у аккаунта есть account_id, то удаляем его из БД.
    - В любом случае удаляем его из локального списка и показываем следующий (или завершаем).
    """
    data = await state.get_data()
    accounts = data.get("accounts") or []
    current_index = data.get("current_index", 0)

    if not accounts or current_index >= len(accounts):
        await callback.answer("Нет аккаунта для удаления", show_alert=True)
        return

    account = accounts[current_index]
    account_id = account.get("account_id")

    if account_id is not None:
        try:
            await db.delete_account(account_id)
        except Exception as e:
            await callback.message.answer(f"❌ Не удалось удалить аккаунт: {e}")
            await callback.answer()
            return

    # Удаляем из локального списка
    del accounts[current_index]

    if not accounts:
        await state.clear()
        await callback.message.edit_text(
            "Список аккаунтов пуст.",
            reply_markup=kb.cancel_to_adm_menu()
        )
        await callback.answer("Удалён")
        return

    # Корректируем индекс, если мы удалили последний элемент
    if current_index >= len(accounts):
        current_index = len(accounts) - 1

    await state.update_data(
        accounts=accounts,
        current_index=current_index,
        account_message_id=callback.message.message_id,
        account_message_chat_id=callback.message.chat.id,
    )

    from handlers.admin_handlers import _format_account_message

    next_account = accounts[current_index]
    text = _format_account_message(next_account, current_index, len(accounts))
    await callback.message.edit_text(
        text,
        reply_markup=kb.account_edit_keyboard()
    )
    await state.set_state(States.reviewing_accounts)
    await callback.answer("Удалён")


@router.callback_query(F.data == "acc_skip")
async def acc_skip(callback: types.CallbackQuery, state: FSMContext):
    """
    Пропустить текущий аккаунт (не сохранять в БД) и перейти к следующему.
    """
    data = await state.get_data()
    accounts = data.get("accounts") or []
    current_index = data.get("current_index", 0)

    if not accounts or current_index >= len(accounts):
        await callback.answer("Нет аккаунта для пропуска", show_alert=True)
        return

    current_index += 1

    if current_index >= len(accounts):
        await state.clear()
        await callback.message.edit_text(
            "Обработка завершена. Больше аккаунтов нет.",
            reply_markup=kb.cancel_to_adm_menu()
        )
        await callback.answer()
        return

    await state.update_data(current_index=current_index, accounts=accounts)

    from handlers.admin_handlers import _format_account_message

    next_account = accounts[current_index]
    text = _format_account_message(next_account, current_index, len(accounts))
    await callback.message.edit_text(
        text,
        reply_markup=kb.account_edit_keyboard()
    )
    await state.set_state(States.reviewing_accounts)
    await callback.answer("Пропущено")


@router.callback_query(F.data == "adm_cancel_to_panel")
async def adm_cancel_to(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(f"Админ панель", reply_markup=kb.admin_panel())
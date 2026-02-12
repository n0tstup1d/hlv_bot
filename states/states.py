from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


class States(StatesGroup):
    # Существующие состояния
    waiting_add_adm = State()
    waiting_add_channel = State()
    waiting_upload_data = State()

    # Добавление аккаунтов из JSON
    reviewing_accounts = State()          # просмотр/редактирование текущего аккаунта по кнопкам
    editing_account_field = State()      # ожидание текстового ввода нового значения поля

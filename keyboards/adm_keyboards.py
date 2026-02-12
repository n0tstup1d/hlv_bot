from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

##############################################################################################################################
# INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE INLINE     #
##############################################################################################################################

def main_menu_panel():
    builder = ReplyKeyboardBuilder()
    builder.button(text="СТАРТ")
    builder.button(text="СТОП")
    builder.button(text="админ панель")
    builder.adjust(2)
    
    return builder.as_markup()

def admin_panel():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить канал(ы)", callback_data="add_channel")
    builder.button(text="Добавить администратора", callback_data="add_adm")
    builder.button(text="Добавить аккаунт", callback_data="upload_data")
    builder.button(text="Аккаунты (БД)", callback_data="manage_accounts")
    builder.button(text="Запустить подписку ❌", callback_data="start_sub_all_channel")
    builder.button(text="Backup БД", callback_data="backup_bd")
    builder.button(text="Запостить дайджест", callback_data="post_daydjest")
    builder.adjust(2)
    
    return builder.as_markup()

def cancel_to_adm_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data="adm_cancel_to_panel")
    builder.adjust(1)
    
    return builder.as_markup()

def start_sub():
    builder = InlineKeyboardBuilder()
    builder.button(text="Запустить подписку ❌", callback_data="start_sub_all_channel")
    builder.button(text="Назад в меню", callback_data="adm_cancel_to_panel")
    builder.adjust(1)
    
    return builder.as_markup()

def main_menu_panel():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Меню запуска")
    builder.button(text="админ панель")
    builder.adjust(2)
    
    return builder.as_markup()

def menu_start_stop_client():
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 ХКП | MAIN", callback_data="start_main_client")
    builder.button(text="🛑 MAIN", callback_data="stop_main_client")
    builder.button(text="🛑 ALL STOP 🛑", callback_data="start_all_client")
    builder.adjust(2)
    
    return builder.as_markup()
# builder.button(text="🟢 ХКП | SALES", callback_data="start_sub_all_channel")
#     builder.button(text="🛑 SALES", callback_data="adm_cancel_to_panel")
#     builder.button(text="🟢 ХКП | CYBER", callback_data="start_sub_all_channel")
#     builder.button(text="🛑 CYBER", callback_data="adm_cancel_to_panel")

##############################################################################################################################
# REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY REPLY    #
##############################################################################################################################

def accounts_review_start():
    """
    Клавиатура после загрузки JSON-файла с аккаунтами.
    Предлагает начать пошаговый просмотр/редактирование.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Начать просмотр", callback_data="acc_start_review")
    builder.button(text="Отмена", callback_data="adm_cancel_to_panel")
    builder.adjust(1)
    return builder.as_markup()


def account_edit_keyboard():
    """
    Клавиатура для редактирования одного аккаунта:
    кнопки по полям + сохранить/пропустить.
    """
    builder = InlineKeyboardBuilder()    # Основные поля аккаунта
    builder.button(text="api_id", callback_data="acc_edit_api_id")
    builder.button(text="api_hash", callback_data="acc_edit_api_hash")
    builder.button(text="app_version", callback_data="acc_edit_app_version")
    builder.button(text="lang_code", callback_data="acc_edit_lang_code")
    builder.button(text="system_lang_code", callback_data="acc_edit_system_lang_code")
    builder.button(text="lang_pack", callback_data="acc_edit_lang_pack")
    builder.button(text="type_account", callback_data="acc_edit_type_account")

    # Поля прокси
    builder.button(text="proxy host", callback_data="acc_edit_proxy_host")
    builder.button(text="proxy port", callback_data="acc_edit_proxy_port")
    builder.button(text="proxy user", callback_data="acc_edit_proxy_username")
    builder.button(text="proxy pass", callback_data="acc_edit_proxy_password")
    builder.button(text="proxy type", callback_data="acc_edit_proxy_type")

    # Управление
    builder.button(text="✅ Сохранить", callback_data="acc_save")
    builder.button(text="⏭ Пропустить", callback_data="acc_skip")
    builder.button(text="🗑 Удалить", callback_data="acc_delete")
    builder.button(text="Отмена", callback_data="adm_cancel_to_panel")

    builder.adjust(2)
    return builder.as_markup()

from aiogram import Bot
from parametrs.config import CHANNEL_POST, ADMIN_ID
from aiogram.types import InlineKeyboardMarkup, FSInputFile, InlineKeyboardButton
import re
import unicodedata
import random
import html
import os
from utils.get_file_type import get_file_type_from_path
async def send_message_aiogram(user_id, text, bot: Bot):
    """Отправляет сообщение через aiogram бота."""
    try:
        await bot.send_message(chat_id=user_id, text=text)
        
    except Exception as e:
        print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
    return

async def send_post_in_channel(text: str, bot: Bot, file_path: str, post_url: str,  file_type=None):
    """Оптимизированная отправка поста с фото и кнопкой."""
    
    # 1. Лаконичная очистка URL
    clean_url = ''.join(ch for ch in post_url if unicodedata.category(ch)[0] != 'C').strip()
    clean_url = clean_url.replace(' ', '')
    EMOJI = ['🎯' , '🏆' , '🥇']
    emojis1 = random.choice(EMOJI)
    # 2. Подготовка клавиатуры
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emojis1} Участвовать", url=clean_url)]
    ])

    try:
        if file_path and os.path.exists(file_path):
            # Если тип не указан, определяем по пути
            if not file_type:
                file_type = await get_file_type_from_path(file_path)
            
            # Отправляем в зависимости от типа
            if file_type == 'video':
                return await bot.send_video(
                    chat_id=CHANNEL_POST,
                    video=FSInputFile(file_path),
                    caption=text[:1024] if text else None,  # Ограничение длины
                    reply_markup=keyboard
                )
            elif file_type == 'photo':
                return await bot.send_photo(
                    chat_id=CHANNEL_POST,
                    photo=FSInputFile(file_path),
                    caption=text[:1024] if text else None,
                    reply_markup=keyboard
                )
        else:
            # Только текст
            return await bot.send_message(
                chat_id=CHANNEL_POST,
                text=text,
                reply_markup=keyboard
            )
        print(f"✅ Пост успешно отправлен в {CHANNEL_POST}")
        return message  # Возвращаем сообщение

    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        # Запасной вариант: текст, если фото не прошло
        try:
            message = await bot.send_message(
                chat_id=CHANNEL_POST,
                text=text[:4096],
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            print(f"✅ Пост отправлен текстом в {CHANNEL_POST}")
            return message  # Возвращаем сообщение
        except Exception as e_text:
            print(f"❌ Критическая ошибка: {e_text}")
            return None

async def send_daily_digest(db, bot: Bot):
    try:
        await bot.send_message(chat_id=ADMIN_ID, text="Начинаем постить ДАЙДЖЕСТ")
        items = await db.get_today_giveaways()  # Получаем розыгрыши на 48 часов
        
        if not items:
            print("Нет розыгрышей для дайджеста")
            await bot.send_message(chat_id=ADMIN_ID, text="Нет розыгрышей для дайджеста")
            return
        
        # Разделяем посты на сегодня и завтра
        from datetime import datetime, timedelta, date
        import pytz
        
        today_items = []
        tomorrow_items = []
        
        # Определяем временную зону (если нужно)
        tz = pytz.timezone('Asia/Yekaterinburg')  # или ваша временная зона
        
        current_date = datetime.now(tz).date()
        
        for row in items:
            if not row['end_date_gift']:
                continue
                
            # Приводим дату к локальному времени
            end_date = row['end_date_gift']
            if hasattr(end_date, 'astimezone'):
                end_date = end_date.astimezone(tz)
            
            # Определяем, к какому дню относится пост
            post_date = end_date.date()
            
            if post_date == current_date:
                today_items.append(row)
            elif post_date == current_date + timedelta(days=1):
                tomorrow_items.append(row)
        
        # Формируем текст дайджеста
        text_parts = []
        
        # Заголовок дайджеста
        if today_items or tomorrow_items:
            text_parts.append("🎁 <b>ЕЖЕДНЕВНЫЙ ДАЙДЖЕСТ</b>")
            text_parts.append("Все самые горячие розыгрыши под рукой!\n")
        
        # Секция "СЕГОДНЯ"
        if today_items:
            today_text = today_items[0]['end_date_gift'].astimezone(tz).strftime("%d.%m.%Y") if today_items else current_date.strftime("%d.%m.%Y")
            text_parts.append(f"<b>🎯 СЕГОДНЯ ({today_text})</b>\n")
            
            for i, row in enumerate(today_items, 1):
                # Форматируем заголовок (первая строка или первые слова)
                title = row.get('filtered_message_text') or row.get('channel_username', 'Розыгрыш')
                
                # Берем только первую строку или первые 80 символов
                if '\n' in title:
                    title = title.split('\n')[0].strip()
                
                # Обрезаем если слишком длинный
                if len(title) > 80:
                    title = title[:77] + "..."
                
                # Форматируем ссылку
                post_link = row.get('post_link', '')
                
                # Добавляем пост в список - простой формат: номер + название (ссылка)
                emoji_number = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1] if i <= 10 else f"{i}."
                if post_link:
                    text_parts.append(f"{emoji_number} <a href=\"{post_link}\">{title}</a>\n")
                else:
                    text_parts.append(f"{emoji_number} {title}")
            
            text_parts.append("")  # Пустая строка для разделения
        
        # Секция "ЗАВТРА"
        if tomorrow_items:
            tomorrow_date = current_date + timedelta(days=1)
            text_parts.append(f"<b>📅 ЗАВТРА ({tomorrow_date.strftime('%d.%m.%Y')})</b>\n")
            
            for i, row in enumerate(tomorrow_items, 1):
                title = row.get('filtered_message_text') or row.get('channel_username', 'Розыгрыш')
                
                if '\n' in title:
                    title = title.split('\n')[0].strip()
                
                if len(title) > 80:
                    title = title[:77] + "..."
                
                post_link = row.get('post_link', '')
                
                emoji_number = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1] if i <= 10 else f"{i}."
                if post_link:
                    text_parts.append(f"{emoji_number} <a href=\"{post_link}\">{title}</a>")
                else:
                    text_parts.append(f"{emoji_number} {title}")
            
            text_parts.append("")  # Пустая строка для разделения
        
        # Если есть посты, добавляем заключение
        if today_items or tomorrow_items:
            text_parts.append("────────────────")
            text_parts.append("<i>Перешли другу, чтобы шансов на победу было больше! 🍀</i>")
        
        # Собираем финальный текст
        final_text = "\n".join(text_parts)
        
        # Проверяем наличие видео файла
        video_path = "./media/cherry-pie.mp4"
        
        if os.path.exists(video_path):
            # Отправляем видео с подписью
            try:
                message = await bot.send_video(
                    chat_id=CHANNEL_POST,
                    video=FSInputFile(video_path),
                    caption=final_text,
                    parse_mode="HTML",
                      # Разрешаем превью ссылок
                )
                print(f"✅ Дайджест с видео успешно отправлен в канал {CHANNEL_POST}")
            except Exception as video_error:
                print(f"❌ Ошибка при отправке видео: {video_error}")
                # Если не удалось отправить видео, отправляем текстом
                message = await bot.send_message(
                    chat_id=CHANNEL_POST,
                    text=final_text,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                    
                )
        else:
            print(f"❌ Видео файл не найден: {video_path}")
            # Отправляем текстом
            message = await bot.send_message(
                chat_id=CHANNEL_POST,
                text=final_text,
                parse_mode="HTML",
                disable_web_page_preview=False
               
            )
        
        # if message:
        #     try:
        #         await bot.pin_chat_message(chat_id=CHANNEL_POST, message_id=message.message_id, disable_notification=True)
        #     except Exception as e:
        #         print(f"Не удалось закрепить сообщение: {e}")

        
        
        # Отправляем статистику админу
        stats_text = f"""
✅ Дайджест успешно отправлен!

📊 Статистика:
• Всего розыгрышей: {len(items)}
• Сегодня: {len(today_items)} шт.
• Завтра: {len(tomorrow_items)} шт.
• Остальные: {len(items) - len(today_items) - len(tomorrow_items)} шт.
        """
        
        print(f"✅ Дайджест успешно отправлен в канал {CHANNEL_POST}")
        await bot.send_message(chat_id=ADMIN_ID, text=stats_text)
        
    except Exception as e:
        print(f"❌ Ошибка дайджеста: {e}")
        await bot.send_message(chat_id=ADMIN_ID, text=f"❌ Ошибка при отправке дайджеста: {e}")
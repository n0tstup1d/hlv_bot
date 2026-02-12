import re
from telethon.tl.types import Message


class PostAnalyzer:
    """Анализатор постов для определения розыгрышей (возвращает только True/False)"""
    
    def __init__(self):
        # Ключевые слова для розыгрышей
        self.giveaway_keywords = [
            'розыгрыш', 'giveaway', 'конкурс', 'приз', 'выиграть',
            'победитель', 'участвовать', 'розыгрываем', 'разыгрываем',
            'лотерея', 'участие', 'подарок', 'награда', 'разыгрываю',
            'winner', 'gift', 'reward', 'выиграй', 'выигрыш'
        ]
        
        # Фразы для розыгрышей
        self.giveaway_phrases = [
            'что нужно сделать',
            'условия участия',
            'подписывайтесь на',
            'репостни этот пост',
            'оставь комментарий',
            'отметь друзей',
            'жди результатов',
            'итоги будут',
            'объявим победителя',
            'правила участия',
            'для участия нужно',
            'участвуй в розыгрыше'
        ]
        
        # Текст для кнопок участия
        self.participation_buttons = [
            'участвую', 'участвовать', 'принять участие',
            'participate', 'join', 'enter', 'хочу участвовать',
            'присоединиться', 'try', 'take part'
        ]
    
    def is_giveaway(self, message: Message) -> bool:
        """
        Определяет, является ли пост розыгрышем.
        Возвращает True если это розыгрыш, False если нет.
        """
        
        # Извлекаем данные
        text = message.message or ""
        buttons = message.reply_markup
        
        # Анализ текста
        text_lower = text.lower()
        
        # 1. Проверка ключевых слов розыгрыша (минимум 1 должно быть)
        found_keywords = 0
        for keyword in self.giveaway_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                found_keywords += 1
                if found_keywords >= 1:  # Нашли хотя бы одно ключевое слово
                    # Проверяем дополнительные условия
                    return self._check_additional_conditions(text_lower, buttons, found_keywords)
        
        # 2. Проверка фраз розыгрыша
        for phrase in self.giveaway_phrases:
            if phrase in text_lower:
                return True
        
        # 3. Проверка кнопок участия
        if buttons and hasattr(buttons, 'rows'):
            for row in buttons.rows:
                for button in row.buttons:
                    button_text = getattr(button, 'text', '').lower()
                    for participation_word in self.participation_buttons:
                        if participation_word in button_text:
                            return True
        
        return False
    
    def _check_additional_conditions(self, text_lower: str, buttons, found_keywords: int) -> bool:
        """Проверка дополнительных условий для подтверждения розыгрыша"""
        
        # Если есть 2+ ключевых слова - точно розыгрыш
        if found_keywords >= 2:
            return True
        
        # Проверка на наличие кнопок
        has_buttons = bool(buttons)
        
        # Проверка на наличие дат/сроков
        has_dates = self._check_for_dates(text_lower)
        
        # Проверка на наличие ссылок
        has_links = 'http://' in text_lower or 'https://' in text_lower or 't.me/' in text_lower
        
        # Проверка на наличие цифр (суммы приза)
        has_numbers = bool(re.search(r'\d+[₽$€]', text_lower) or re.search(r'\d+\s*(тыс|к|руб|дол|евро)', text_lower))
        
        # Комбинации признаков:
        # 1 ключевое слово + дата
        if has_dates:
            return True
        
        # 1 ключевое слово + кнопки
        if has_buttons:
            return True
        
        # 1 ключевое слово + ссылка + цифры (сумма)
        if has_links and has_numbers:
            return True
        
        # 1 ключевое слово + хотя бы одна фраза
        for phrase in self.giveaway_phrases:
            if phrase in text_lower:
                return True
        
        return False
    
    def _check_for_dates(self, text: str) -> bool:
        """Проверка на наличие дат в тексте"""
        date_patterns = [
            r'\d{1,2}\s*[а-я]+\.?\s*\d{4}',  # 5 февраля 2024
            r'\d{1,2}\.\d{1,2}\.\d{4}',      # 05.02.2024
            r'\d{1,2}\s*[а-я]+\s*в\s*\d{1,2}:\d{2}',  # 5 февраля в 18:00
            r'итоги\s*\d{1,2}',  # итоги 5
            r'до\s*\d{1,2}',     # до 5
            r'до\s*\d{1,2}\s*[а-я]+'  # до 5 февраля
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def get_post_analysis_data(self, message: Message) -> dict:
        """Получить данные анализа поста для записи в БД"""
        text = message.message or ""
        buttons = message.reply_markup
        
        # Анализируем пост
        is_giveaway = self.is_giveaway(message)
        
        # Собираем ключевые слова
        text_lower = text.lower()
        found_keywords = []
        for keyword in self.giveaway_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                found_keywords.append(keyword)
        
        # Определяем тип медиа
        media_type = None
        if hasattr(message, 'media'):
            if message.photo:
                media_type = 'photo'
            elif message.video:
                media_type = 'video'
            elif message.document:
                media_type = 'document'
        
        # Подсчитываем кнопки
        button_count = 0
        giveaway_buttons = 0
        if buttons and hasattr(buttons, 'rows'):
            for row in buttons.rows:
                button_count += len(row.buttons)
                for button in row.buttons:
                    button_text = getattr(button, 'text', '').lower()
                    for participation_word in self.participation_buttons:
                        if participation_word in button_text:
                            giveaway_buttons += 1
        
        # Определяем решение
        decision = 'GIVEAWAY' if is_giveaway else 'NEUTRAL'
        
        # Причина решения
        decision_reason = []
        if is_giveaway:
            if found_keywords:
                decision_reason.append(f"Ключевые слова: {', '.join(found_keywords[:3])}")
            if button_count > 0:
                decision_reason.append(f"Кнопки: {button_count}")
        
        # Подсчет хэштегов
        hashtags = []
        if hasattr(message, 'entities'):
            for entity in message.entities:
                if hasattr(entity, '_') and entity._ == 'MessageEntityHashtag':
                    hashtag = text[entity.offset:entity.offset + entity.length]
                    hashtags.append(hashtag)
        
        return {
            'is_giveaway': is_giveaway,
            'decision': decision,
            'decision_reason': '; '.join(decision_reason) if decision_reason else 'Нет признаков розыгрыша',
            'matched_keywords': found_keywords,
            'hashtags': hashtags,
            'button_count': button_count,
            'giveaway_buttons': giveaway_buttons,
            'media_type': media_type,
            'text_length': len(text),
            'has_media': bool(message.media),
            'has_buttons': bool(buttons),
            'is_forwarded': bool(getattr(message, 'fwd_from', None)),
            'giveaway_score': len(found_keywords) * 0.3,  # Простая оценка
            'ad_score': 0,  # Пока не считаем
            'total_score': len(found_keywords) * 0.3
        }


# Упрощенная функция для быстрого использования
def is_giveaway_post(message: Message) -> bool:
    """
    Быстрая проверка - является ли пост розыгрышем.
    Использование: result = is_giveaway_post(msg)
    """
    analyzer = PostAnalyzer()
    return analyzer.is_giveaway(message)
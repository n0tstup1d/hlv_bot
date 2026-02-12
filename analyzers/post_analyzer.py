# file name: post_analyzer.py
import re
from typing import Dict, List, Tuple
from datetime import datetime

class PostAnalyzer:
    def __init__(self, db):
        self.db = db
    
    def is_digest_post(self, text: str) -> bool:
        """
        Определяет, является ли пост дайджестом (списком розыгрышей).
        """
        if not text:
            return False
        
        # Считаем ссылки на t.me
        import re
        tme_links = re.findall(r't\.me/[\w@]+/\d+', text)
        
        # Если много ссылок (например, больше 5) - это явный признак дайджеста
        if len(tme_links) > 5:
            return True
        
        # Проверяем структуру текста
        lines = text.split('\n')
        
        # Считаем строки со ссылками и короткие строки
        link_lines = 0
        short_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Строка содержит ссылку на t.me
            if 't.me/' in line:
                link_lines += 1
            
            # Очень короткие строки (только ссылка или короткое описание)
            if len(line.split()) <= 3:
                short_lines += 1
        
        # Если много строк со ссылками (больше 3) И много коротких строк - вероятно дайджест
        if link_lines > 3 and short_lines > link_lines * 0.7:
            return True
        
        # Проверяем на наличие перечисления
        if text.count('\n') > 8 and link_lines > 2:
            # Много строк и несколько ссылок - похоже на список
            return True
        
        return False
    
    async def analyze_message(self, msg) -> Tuple[bool, Dict]:
        """
        Анализирует сообщение и возвращает:
        - True если это розыгрыш, False если нет
        - Словарь с данными для сохранения в БД
        """
        message_obj = msg.message
        # Извлекаем данные из сообщения
        if hasattr(message_obj, 'message'):
            text = message_obj.message
        else:
        # Иначе, возможно, это уже строка
            text = message_obj or ""
        
        if self.is_digest_post(text):
            print(f"📋 Обнаружен пост-дайджест, пропускаем")
            
            # Извлекаем базовую информацию для БД
            buttons = self._extract_buttons(msg)
            entities = msg.entities or []
            media = msg.media
            hashtags = self._extract_hashtags(entities, text)
            media_type = self._get_media_type(media)
            
            analysis_data = {
                'decision': 'DIGEST',
                'decision_reason': 'Пост является дайджестом (списком розыгрышей)',
                'giveaway_score': 0,
                'ad_score': 0,
                'total_score': 0,
                'matched_keywords': [],
                'hashtags': hashtags,
                'button_count': len(buttons),
                'giveaway_buttons': 0,
                'media_type': media_type,
                'has_media': bool(media),
                'has_buttons': len(buttons) > 0,
                'filtered_message_text': '',
                'end_date': None,
            }
            return False, analysis_data
        # text = msg.message.message or ""
        buttons = self._extract_buttons(msg)
        entities = msg.entities or []
        media = msg.media
        
        # Проверяем основные признаки розыгрыша
        giveaway_score = 0
        ad_score = 0
        matched_keywords = []
        giveaway_buttons = 0
        hashtags = self._extract_hashtags(entities, text)
        media_type = self._get_media_type(media)
        
        # Получаем ключевые слова из БД
        keywords = await self.db.get_keywords_by_type()
        giveaway_keywords = keywords.get('giveaway', {})
        ad_keywords = keywords.get('ad', {})
        blacklist_keywords = keywords.get('blacklist', {})
        
        # Приводим текст к нижнему регистру для поиска
        text_lower = text.lower()
        
        # Проверка на черный список (немедленный отказ)
        for keyword, weight in blacklist_keywords.items():
            if keyword in text_lower:
                return False, {
                    'giveaway_score': 0,
                    'ad_score': weight,
                    'total_score': weight,
                    'decision': 'BLACKLIST',
                    'decision_reason': f'Найдено запрещенное слово: {keyword}',
                    'matched_keywords': [keyword],
                    'hashtags': hashtags,
                    'button_count': len(buttons),
                    'giveaway_buttons': 0,
                    'media_type': media_type,
                    'has_media': bool(media),
                    'has_buttons': len(buttons) > 0
                }
        
        # Анализ текста на ключевые слова розыгрыша
        for keyword, weight in giveaway_keywords.items():
            if keyword in text_lower:
                giveaway_score += weight
                matched_keywords.append(keyword)
                
        # Анализ текста на рекламные ключевые слова
        for keyword, weight in ad_keywords.items():
            if keyword in text_lower:
                ad_score += weight
                matched_keywords.append(keyword)
        
        # Анализ кнопок
        for button in buttons:
            button_text = button.text.lower() if hasattr(button, 'text') else ""
            
            # Проверяем кнопки на наличие слов розыгрыша
            for keyword in giveaway_keywords:
                if keyword in button_text:
                    giveaway_score += giveaway_keywords[keyword] * 0.5
                    giveaway_buttons += 1
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)
            
            # Проверяем кнопки на ссылки (признак рекламы)
            if hasattr(button, 'url'):
                ad_score += 0.3
        
        # Проверка наличия даты окончания розыгрыша
        end_date = None
        if giveaway_score > 0.5:  # Если уже есть признаки розыгрыша
            end_date = self._extract_end_date(text)
            if end_date:
                giveaway_score += 1.0
        
        # Проверка на наличие ссылок в тексте (кроме телеграм)
        if self._has_external_links(entities, text):
            ad_score += 0.5
        
        # Дополнительные признаки розыгрыша
        if self._has_giveaway_patterns(text):
            giveaway_score += 1.0
            
        if self._has_conditions(text):  # "Что нужно сделать"
            giveaway_score += 0.8
            
        if end_date:  # Есть дата окончания
            giveaway_score += 1.0
        
        # Итоговый подсчет
        total_score = giveaway_score - ad_score
        
        # Принятие решения
        if total_score >= 1.5:
            decision = 'GIVEAWAY'
            decision_reason = f'Высокий балл розыгрыша: {total_score:.2f}. Найдены ключевые слова: {", ".join(matched_keywords[:3])}'
            is_giveaway = True
        elif ad_score >= 1.0:
            decision = 'AD'
            decision_reason = f'Обнаружена реклама. Балл: {ad_score:.2f}'
            is_giveaway = False
        else:
            decision = 'NEUTRAL'
            decision_reason = 'Недостаточно признаков для классификации'
            is_giveaway = False
        
        # Подготовка данных для БД
        analysis_data = {
            'giveaway_score': giveaway_score,
            'ad_score': ad_score,
            'total_score': total_score,
            'decision': decision,
            'decision_reason': decision_reason,
            'matched_keywords': matched_keywords,
            'hashtags': hashtags,
            'button_count': len(buttons),
            'giveaway_buttons': giveaway_buttons,
            'media_type': media_type,
            'has_media': bool(media),
            'has_buttons': len(buttons) > 0,
            'end_date': end_date
        }
        
        return is_giveaway, analysis_data
    
    def _extract_buttons(self, msg):
        """Извлекает кнопки из сообщения"""
        buttons = []
        if hasattr(msg, 'reply_markup') and msg.reply_markup:
            if hasattr(msg.reply_markup, 'rows'):
                for row in msg.reply_markup.rows:
                    if hasattr(row, 'buttons'):
                        buttons.extend(row.buttons)
        return buttons
    
    def _extract_hashtags(self, entities, text):
        """Извлекает хэштеги из сообщения"""
        hashtags = []
        for entity in entities:
            if hasattr(entity, 'type') and entity.type == 'hashtag':
                hashtag = text[entity.offset:entity.offset + entity.length]
                hashtags.append(hashtag)
        return hashtags
    
    def _get_media_type(self, media):
        """Определяет тип медиа"""
        if not media:
            return 'none'
        
        if hasattr(media, 'photo'):
            return 'photo'
        elif hasattr(media, 'video'):
            return 'video'
        elif hasattr(media, 'document'):
            return 'document'
        elif hasattr(media, 'poll'):
            return 'poll'
        else:
            return 'other'
    
    def _extract_end_date(self, text):
        """Извлекает дату окончания розыгрыша из текста"""
        # Паттерны для поиска дат
        date_patterns = [
            r'(\d{1,2}\s*(?:февраля|января|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря))',
            r'(\d{1,2}\.\d{1,2}\.\d{2,4})',
            r'(\d{1,2}/\d{1,2}/\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)
        
        # Поиск по ключевым фразам
        giveaway_phrases = [
            'итоги', 'завершится', 'до', 'розыгрыш до', 'конкурс до'
        ]
        
        for phrase in giveaway_phrases:
            if phrase in text.lower():
                # Ищем ближайшую дату после фразы
                idx = text.lower().find(phrase)
                if idx != -1:
                    # Ищем дату в следующих 50 символах
                    substr = text[idx:idx+50]
                    for pattern in date_patterns:
                        match = re.search(pattern, substr)
                        if match:
                            return match.group(1)
        
        return None
    
    def _has_external_links(self, entities, text):
        """Проверяет наличие внешних ссылок (не телеграм)"""
        for entity in entities:
            if hasattr(entity, 'type') and entity.type == 'textUrl':
                url = entity.url
                if not url.startswith('https://t.me/') and not url.startswith('tg://'):
                    return True
        return False
    
    def _has_giveaway_patterns(self, text):
        """Проверяет наличие паттернов розыгрыша"""
        patterns = [
            r'розыгрыш.*\d+',
            r'разыгрываю.*\d+',
            r'подарок.*\d+',
            r'приз.*\d+',
            r'выиграй.*\d+',
            r'конкурс.*\d+',
            r'разыгрываем.*\d+', 
            r'дарим.*\d+',
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True
        
        if "внимание" in text_lower and ("конкурс" in text_lower or "розыгрыш" in text_lower):
            return True

        return False
    
    def _has_conditions(self, text):
        """Проверяет наличие условий участия"""
        conditions = [
            'что нужно сделать',
            'условия участия',
            'для участия',
            'требования',
            'правила',
            'подпишись',
            'подписаться'
        ]
        
        text_lower = text.lower()
        for condition in conditions:
            if condition in text_lower:
                return True
        return False
import os
import json
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta

# Настройки для управления нагрузкой
MAX_CONCURRENT_REQUESTS = 3
MAX_RETRIES = 3
RETRY_DELAY = 2

# Настройки для облачного Ollama API
OLLAMA_API_KEY = '9a59055e7054461a9c8649ea6b15b5c4.57qbYygjhxcFYIx6MxdPAgWF'
# Устанавливаем переменную окружения для ollama библиотеки
os.environ['OLLAMA_API_KEY'] = OLLAMA_API_KEY

# Импортируем библиотеку ollama после установки переменной окружения
from ollama import AsyncClient

# Семафор для ограничения одновременных запросов
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# Инициализируем клиента для облачного Ollama
client = AsyncClient(
    host='https://api.ollama.com',
    headers={'Authorization': f'Bearer {OLLAMA_API_KEY}'}
)

text_for_giga = """
<system_instructions>
Ты анализируешь тексты Telegram-постов на наличие розыгрышей и конкурсов.
Верни ответ СТРОГО в формате JSON без пояснений.

{
"is_giveaway": true/false,
"giveaway_name": "название или null",
"conditions": ["условие 1", "условие 2"],
"prizes": ["приз 1", "приз 2"],
"end_date": "ДД.ММ.ГГГГ или null",
"audience_scale": "local / regional / federal / unknown",
"quality_score": 1-10,
"trash_reason": "причина или пустая строка"
}
</system_instructions>

<rule_block_1_definition>
### ОПРЕДЕЛЕНИЕ РОЗЫГРЫША
is_giveaway = true, если:
- Есть приз И
- Есть условия участия
Даже если условия простые (подписка, лайк, комментарий).
Если это просто скидки, новости, реклама без условий выигрыша — false.
</rule_block_1_definition>

<rule_block_2_scale>
### ОПРЕДЕЛЕНИЕ МАСШТАБА (audience_scale)
- **local:** Указан конкретный город; Малый бизнес (цветы, кафе, салон красоты, ресторан, барбершоп); Призы актуальны только в одном городе.
- **regional:** Указан регион (область, край); Несколько городов; Средний бизнес.
- **federal:** Вся Россия; Онлайн участие без гео-ограничений; Крупный бренд; Денежные переводы, техника с доставкой.
- **unknown:** Невозможно определить масштаб.
</rule_block_2_scale>

<rule_block_3_scoring>
### ИНСТРУКЦИИ ПО ОЦЕНКЕ QUALITY_SCORE (1-10)

**1-4: ОТКЛОНЯТЬ**
- Локальный бизнес
- Призы бытовые (цветы, торт, ужин, косметика, одежда без бренда)
- Сертификаты до 5000 рублей
- Мелкие денежные суммы (< 5000₽)
- Подписка на 3+ каналов
- Малый масштаб
- Нет понятной ценности
- Сувениры, маски → ВСЕГДА quality_score 1-4

*ПРИМЕРЫ ОТСЕЧЕНИЯ:*
- "Билеты в кино + мерч" → quality_score 3
- "Подписка на 3 канала" → quality_score 4
- "Мерч фильма" → quality_score 2
- "Сертификат 3000₽" → quality_score 4

**НЕ ДЕЛАЙ ИСКЛЮЧЕНИЙ ДЛЯ КОЛЛАБОРАЦИЙ!**

**5-7: СРЕДНИЙ УРОВЕНЬ**
- Призы 5000–20000 рублей
- Подписка максимум на 2 канала
- Прозрачные условия
- audience_scale = regional или federal

**8-10: ПРИОРИТЕТ**
- Призы от 20000 рублей
- Деньги, техника (iPhone, MacBook), крупные суммы
- Минимум условий
- Известные бренды
- audience_scale = federal

**ВАЖНО ПО СУММАМ:**
- Если audience_scale = local → НЕ ставь выше 4.
- до 5000₽ → максимум 4
- если ровно 5000₽ → максимум 5
- 5000–20000₽ → максимум 7
- 20000₽+ → можно 8–10

Если quality_score 1-4 → укажи причину в trash_reason.
</rule_block_3_scoring>

<rule_block_4_formatting>
### ФОРМАТ ПОЛЕЙ
- **giveaway_name:** Краткое название, убери лишние эмодзи.
- **conditions:** В инфинитиве (подписаться, поставить лайк, оставить комментарий).
- **prizes:** Грамматически исправленные, согласованные числительные, в именительном падеже, каждая строка — законченная фраза.
- **end_date:** Формат строго ДД.ММ.ГГГГ. Если невозможно определить — null.
</rule_block_4_formatting>

<rule_block_5_dates>
### ИНСТРУКЦИИ ПО ДАТАМ
1. Преобразуй любую дату в формат ДД.ММ.ГГГГ.
2. Если указана без года — используй текущий год.
3. Если указана относительная дата — вычисли конкретную.
4. Если определить невозможно — null.
</rule_block_5_dates>

<final_constraint>
НЕ ДОБАВЛЯЙ НИЧЕГО КРОМЕ JSON.
Ниже представлен текст для анализа:
--------------------------------------------------
</final_constraint>

"""


async def make_request_with_retry(func, *args, **kwargs):
    """Универсальная функция для выполнения запроса с повторными попытками"""
    for attempt in range(MAX_RETRIES):
        try:
            async with semaphore:
                result = await func(*args, **kwargs)
                return result
        except Exception as e:
            error_str = str(e)
            
            if "503" in error_str or "Service Unavailable" in error_str or "overloaded" in error_str.lower():
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"⚠️  Сервер перегружен (503). Попытка {attempt + 1}/{MAX_RETRIES}. Жду {wait_time} сек...")
                await asyncio.sleep(wait_time)
                
                if attempt == MAX_RETRIES - 1:
                    print(f"❌ Превышено максимальное количество попыток. Ошибка: {error_str}")
                    raise
            elif "401" in error_str or "unauthorized" in error_str.lower():
                print(f"❌ Ошибка авторизации (401). Проверьте API ключ.")
                raise
            else:
                print(f"❌ Ошибка при запросе: {error_str}")
                raise
    
    return None

async def extract_giveaway_info(post_text):
    """Извлекает структурированную информацию о розыгрыше"""
    prompt = text_for_giga + "\n\n<post_to_analyze>\n" + post_text + "\n</post_to_analyze>"
    
    messages = [
        {
            "role": "system", 
            "content": "Ты AI-ассистент, который строго отвечает только в формате JSON без дополнительных объяснений."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    async def make_request():
        try:
            response = await client.chat(
                model='deepseek-v3.1:671b-cloud',  # Попробуем другую модель
                messages=messages,
                options={
                    'temperature': 0.1,
                    'num_predict': 500
                }
            )
            
            # Ищем JSON в тексте ответа
            response_text = response.message.content
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                return data
            else:
                print("⚠️ Не удалось найти JSON в ответе")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка API (извлечение информации): {e}")
            raise
    
    try:
        result = await make_request_with_retry(make_request)
        return result
    except Exception:
        return None

async def request_gigachat_filter_post(text_post):
    """Основная функция для фильтрации постов"""
    try:
        print(f"📨 Обрабатываю пост ({len(text_post)} символов)...")
        
        # Пропускаем слишком короткие посты
        if len(text_post) < 20:
            print("📭 Пост слишком короткий")
            return {
                "is_giveaway": False,
                "giveaway_name": None,
                "conditions": [],
                "prizes": [],
                "end_date": None,
                "quality_score": 5,
                "trash_reason": "Пост слишком короткий"
            }
        
        # Сразу извлекаем детальную информацию
        print("🎯 Анализирую пост на наличие розыгрыша...")
        data = await extract_giveaway_info(text_post)
        
        if data is None:
            print("❌ Не удалось получить ответ от API")
            return {
                "is_giveaway": False,
                "giveaway_name": None,
                "conditions": [],
                "prizes": [],
                "end_date": None,
                "quality_score": 5,
                "trash_reason": "Ошибка получения данных от API"
            }
        
        print(f"✅ Данные успешно извлечены! is_giveaway: {data.get('is_giveaway')}")
        
        # Если это не розыгрыш, все равно возвращаем структуру
        if not data.get('is_giveaway', False):
            print("📭 Пост не является розыгрышем")
            return {
                "is_giveaway": False,
                "giveaway_name": None,
                "conditions": [],
                "prizes": [],
                "end_date": None,
                "quality_score": 5,
                "trash_reason": data.get('trash_reason', 'Не является розыгрышем')
            }
        
        # Печать результатов для розыгрыша
        print(f"📋 Заголовок: {data.get('giveaway_name')}")
        print(f"🎁 Что разыгрывают: {', '.join(data.get('prizes', []))}")
        print(f"📝 Условия: {', '.join(data.get('conditions', []))}")
        print(f"📅 До какого числа: {data.get('end_date')}")
        print(f"📊 Качество: {data.get('quality_score', 5)}/10")

        return data

    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")
        return {
            "is_giveaway": False,
            "giveaway_name": None,
            "conditions": [],
            "prizes": [],
            "end_date": None,
            "quality_score": 5,
            "trash_reason": f"Ошибка обработки: {str(e)[:100]}"
        }

# Тестовая функция
async def test_iphone_giveaway():
    """Тестовая функция для проверки работы с розыгрышем iPhone"""
    test_text = """🎉 РОЗЫГРЫШ 3x iPhone 15 Pro Max! 🎉

Друзья, запускаем мега-розыгрыш! 
Разыгрываем 3 новейших iPhone 15 Pro Max!

Для участия:
1. Подпишись на этот канал
2. Поставь лайк этому посту
3. Сделай репост в любой свой чат
4. Напиши в комментариях "Хочу iPhone!"

Итоги подведём 27 февраля 2026 года.
Победителей определим с помощью рандомайзера.

Условия:
- Аккаунт должен быть не младше 3 месяцев
- Фейковые аккаунты будут дисквалифицированы
- Один участник = один шанс

Удачи всем! 🍀"""
    
    print("=" * 50)
    print("🧪 Тестирование с розыгрышем iPhone")
    print("=" * 50)
    
    result = await request_gigachat_filter_post(test_text)
    print(f"\n📊 Результат анализа:")
    print(f"is_giveaway: {result.get('is_giveaway')}")
    print(f"giveaway_name: {result.get('giveaway_name')}")
    print(f"prizes: {result.get('prizes')}")
    print(f"conditions: {result.get('conditions')}")
    print(f"end_date: {result.get('end_date')}")
    print(f"quality_score: {result.get('quality_score')}")
    print(f"trash_reason: {result.get('trash_reason')}")

if __name__ == "__main__":
    print("🚀 Запуск тестового сценария с розыгрышем iPhone...")
    asyncio.run(test_iphone_giveaway())
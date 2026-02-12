import os
import json
import re
import asyncio
import aiohttp
from datetime import datetime
from ollama import AsyncClient
from datetime import datetime, timedelta
import re

# Настройки для управления нагрузкой
MAX_CONCURRENT_REQUESTS = 3  # Максимальное количество одновременных запросов
MAX_RETRIES = 3  # Максимальное количество повторных попыток при ошибке 503
RETRY_DELAY = 2  # Базовая задержка между повторными попытками в секундах

# Семафор для ограничения одновременных запросов
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# Настройка клиента для облачного Ollama API
client = AsyncClient(
    host='https://api.ollama.com',
    headers={'Authorization': 'Bearer ' + '9a59055e7054461a9c8649ea6b15b5c4.57qbYygjhxcFYIx6MxdPAgWF'}
)

text_for_giga = """Ты анализируешь тексты на наличие розыгрышей и конкурсов. 
Верни ответ строго в формате JSON со следующей структурой:

{
"is_giveaway": true/false,
"giveaway_name": "название или null",
"conditions": ["условие 1", "условие 2", ...],
"prizes": ["приз 1", "приз 2", ...],
"end_date": "дата или null",
"quality_score": 1-10,
"trash_reason": "причина или пустая строка"
}


Инструкции по обработке текста:
is_giveaway: true, если в тексте есть призы и условия участия.
giveaway_name: краткое название. Очищай от лишних эмодзи в начале и конце.
conditions: формулируй условия в инфинитиве (например: "подписаться", "поставить лайк").
prizes:
Исправляй грамматические ошибки и согласование падежей.
Числительные должны быть согласованы с существительными (например, вместо "6 сеты" пиши "6 наборов (сетов)").
Каждый приз должен быть законченной фразой в именительном падеже.
end_date: формат ДД.ММ.ГГГГ. Если дата не указана, пиши null. Сегодня 2026год.
Пример исправления:
Вход: "Призы:6 сеты с глиттером" -> Выход в JSON: "6 наборов с глиттером".

Сегодня 2026 год.

ИНСТРУКЦИИ ПО ДАТАМ:
1. Если указана конкретная дата в любом формате (например: "2 февраля", "02.02.2026", "02/02/2026"), преобразуй в формат ДД.ММ.ГГГГ
2. Если указана относительная дата (например: "через неделю", "через 3 дня", "завтра", "послезавтра"), ВЫЧИСЛИ КОНКРЕТНУЮ ДАТУ и верни в формате ДД.ММ.ГГГГ
3. Правила вычисления относительных дат:
   - "через неделю" = +7 дней → 16.02.2026
   - "через 7 дней" = +7 дней → 16.02.2026  
   - "через 3 дня" = +3 дня → 12.02.2026
   - "завтра" = +1 день → 10.02.2026
   - "послезавтра" = +2 дня → 11.02.2026
   - "в течение недели" = +7 дней → 16.02.2026
   - "через месяц" = +30 дней → 11.03.2026
4. Если дата не указана или её невозможно определить, верни null
5. НЕ оставляй относительные фразы, ВСЕГДА преобразуй в конкретную дату!

ПРИМЕРЫ:
1. Текст: "Розыгрыш через неделю" → "16.02.2026"
2. Текст: "Итоги подведем завтра" → "10.02.2026"
3. Текст: "Конкурс до 15 февраля" → "15.02.2026"
4. Текст: "Розыгрыш 20.02" → "20.02.2026"
5. Текст: "Дата окончания не указана" → "null"

Общие инструкции:
1. giveaway_name: краткое название, очищай от эмодзи
2. conditions: формулируй в инфинитиве (например: "подписаться", "поставить лайк")
3. prizes: исправляй грамматику, согласуй падежи
4. Каждый приз должен быть законченной фразой в именительном падеже

ИНСТРУКЦИИ ПО ОЦЕНКЕ QUALITY_SCORE (1-10):

1-3: МУСОР (отклонять):
   - Просят подписаться на 10+ каналов
   - Подозрительные боты в условиях (типа "нажми на бота")
   - Призы не указаны или очень размытые ("что-то интересное")
   - Условия неясные ("просто напиши", "угадай")
   - Организатор не указан или анонимен
   - Требуют денег или предоплаты

4-7: НОРМАЛЬНЫЕ (публиковать):
   - Подписка на 1-2 канала
   - Стандартные условия (лайк, репост, комментарий, тег друга)
   - Четко указанные призы (конкретные товары, деньги, услуги)
   - Ясные сроки окончания
   - Известный или указанный организатор

8-10: ОТЛИЧНЫЕ (приоритет):
   - Крупные бренды/известные компании
   - Дорогие призы (от 5000₽, техника, путешествия)
   - Минимум условий или творческие задания
   - Полная прозрачность правил
   - Легальные контакты организатора

В ПОЛЕ "trash_reason" укажи причину, если quality_score 1-3.
Например: "слишком много условий", "призы не указаны", "подозрительный бот", "просят деньги".

Не добавляй никакого текста кроме JSON.


"""

def parse_relative_date(text, reference_date=None):
    """
    Парсит относительные даты из текста.
    Примеры: "через неделю", "через 3 дня", "завтра", "через 2 недели"
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    text_lower = text.lower()
    
    # Паттерны для поиска
    patterns = [
        (r'через\s*(\d+)\s*день', lambda d: timedelta(days=int(d))),
        (r'через\s*(\d+)\s*дня', lambda d: timedelta(days=int(d))),
        (r'через\s*(\d+)\s*дней', lambda d: timedelta(days=int(d))),
        (r'через\s*(\d+)\s*недел[юи]', lambda w: timedelta(weeks=int(w))),
        (r'через\s*(\d+)\s*месяц[аев]?', lambda m: timedelta(days=30*int(m))),
        (r'завтра', lambda _: timedelta(days=1)),
        (r'послезавтра', lambda _: timedelta(days=2)),
        (r'через неделю', lambda _: timedelta(weeks=1)),
        (r'через месяц', lambda _: timedelta(days=30)),
    ]
    
    for pattern, delta_func in patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                if pattern in ['завтра', 'послезавтра', 'через неделю', 'через месяц']:
                    delta = delta_func(1)
                else:
                    num = int(match.group(1))
                    delta = delta_func(num)
                
                result_date = reference_date + delta
                return result_date.strftime('%d.%m.%Y')
            except (ValueError, IndexError):
                continue
    
    return None

async def make_request_with_retry(func, *args, **kwargs):
    """Универсальная функция для выполнения запроса с повторными попытками"""
    for attempt in range(MAX_RETRIES):
        try:
            async with semaphore:  # Ограничиваем количество одновременных запросов
                result = await func(*args, **kwargs)
                return result
        except Exception as e:
            error_str = str(e)
            
            # Проверяем, является ли ошибка 503 или перегрузкой сервера
            if "503" in error_str or "Service Unavailable" in error_str or "overloaded" in error_str.lower():
                wait_time = RETRY_DELAY * (2 ** attempt)  # Экспоненциальная задержка
                print(f"⚠️  Сервер перегружен (503). Попытка {attempt + 1}/{MAX_RETRIES}. Жду {wait_time} сек...")
                await asyncio.sleep(wait_time)
                
                # Последняя попытка
                if attempt == MAX_RETRIES - 1:
                    print(f"❌ Превышено максимальное количество попыток. Ошибка: {error_str}")
                    raise
            else:
                # Другие ошибки не перезапускаем
                print(f"❌ Ошибка при запросе: {error_str}")
                raise
    
    return None


async def check_if_giveaway(post_text):
    """Проверяет, является ли текст розыгрышем с повторными попытками"""
    messages = [
        {
            "role": "system",
            "content": "Ты бот-классификатор, который определяет, является ли текст розыгрышем или конкурсом. Ответь строго одним словом: ДА или НЕТ."
        },
        {
            "role": "user",
            "content": post_text
        }
    ]
    
    async def make_request():
        try:
            response = await client.chat(
                model='deepseek-v3.1:671b-cloud',
                messages=messages,
                options={
                    'temperature': 0.1,
                    'num_predict': 10
                }
            )
            
            answer = response.message.content.strip().upper()
            print(f"✅ Ответ API (классификация): {answer}")
            return "ДА" in answer or "YES" in answer
            
        except Exception as e:
            print(f"❌ Ошибка API (классификация): {e}")
            raise
    
    try:
        result = await make_request_with_retry(make_request)
        return result if result is not None else False
    except Exception:
        return False


async def extract_giveaway_info(post_text):
    """Извлекает структурированную информацию о розыгрыше с повторными попытками"""
    prompt = text_for_giga + "\n\nТекст который нужно обработать:\n" + post_text
    
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
                model='deepseek-v3.1:671b-cloud',
                messages=messages,
                options={
                    'temperature': 0.1,
                    'num_predict': 500
                }
            )
            
            # Извлекаем JSON из ответа
            response_text = response.message.content
            
            # Ищем JSON в тексте ответа
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
    """Основная функция для фильтрации постов с обработкой перегрузки сервера"""
    try:
        print(f"📨 Обрабатываю пост ({len(text_post)} символов)...")
        
        # Сначала проверяем классификатором
        print("🔍 Проверяю, является ли пост розыгрышем...")
        is_giveaway = await check_if_giveaway(text_post)
        
        if not is_giveaway:
            print("📭 Классификатор определил, что это не розыгрыш")
            return {
                "is_giveaway": False,
                "giveaway_name": None,
                "conditions": [],
                "prizes": [],
                "end_date": None
            }
        
        print("🎯 Извлекаю детальную информацию о розыгрыше...")
        # Извлекаем детальную информацию
        full_prompt = f"{text_for_giga}\n\nТекст для обработки:\n{text_post}"
        
        messages = [
            {
                "role": "system", 
                "content": "Ты AI-ассистент, который строго отвечает только в формате JSON без дополнительных объяснений."
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ]
        
        async def make_request():
            response = await client.chat(
                model='deepseek-v3.1:671b-cloud',
                messages=messages,
                options={
                    'temperature': 0.1,
                    'num_predict': 500
                }
            )
            return response.message.content
        
        content = await make_request_with_retry(make_request)
        
        if content is None:
            print("❌ Не удалось получить ответ от API после всех попыток")
            return None

        # 1. Извлекаем JSON из текста
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            print("⚠️ JSON не найден в ответе")
            return None

        # 2. Десериализация
        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка декодирования JSON: {e}")
            return None
        
        print("✅ Данные успешно извлечены!")
        
        # 3. Печать результатов
        print(f"📋 Заголовок: {data.get('giveaway_name')}")
        print(f"🎁 Что разыгрывают: {', '.join(data.get('prizes', []))}")
        print(f"📝 Условия: {', '.join(data.get('conditions', []))}")
        print(f"📅 До какого числа: {data.get('end_date')}")

        return data

    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")
        return None


# Дополнительная функция для массовой обработки с контролем нагрузки
async def process_multiple_posts(posts):
    """Обрабатывает несколько постов с контролем нагрузки"""
    tasks = []
    results = []
    
    for i, post in enumerate(posts):
        print(f"\n📄 Обработка поста {i+1}/{len(posts)}...")
        task = asyncio.create_task(request_gigachat_filter_post(post))
        tasks.append(task)
        
        # Небольшая задержка между запуском задач для равномерной нагрузки
        if i % MAX_CONCURRENT_REQUESTS == 0 and i > 0:
            await asyncio.sleep(1)
    
    # Ждем завершения всех задач
    for task in tasks:
        try:
            result = await task
            results.append(result)
        except Exception as e:
            print(f"❌ Ошибка при обработке задачи: {e}")
            results.append(None)
    
    return results


# Асинхронная версия для тестирования
async def test_ollama():
    """Тестовая функция для проверки работы Ollama"""
    test_text = """🥝🍅🍆🥑🥑

2 февраля в КАРО 11 Октябрь состоится светская премьера романтической комедии «Равиоли Оли». В главных ролях: Ольга Бузова, Владимир Яглыч, Вольфганг Черни , Максим Лагашкин, Ева Смирнова, Марина Федункив и Эвелина Блёданс.

Мы разыгрываем три пары билетов на премьерный показ фильма в Москве.

Для участия в конкурсе:

1. Будь подписан на канал КАРО 
2. Поставь  🔥 этой записи
3. Нажми кнопку «Участвовать»

Итоги конкурса подведем 2 февраля под этим постом.

Ольга Бузова, звезда сцены и экрана, мечтает о романтическом будущем с идеальным мужчиной — красавцем-немцем Генрихом, который вот-вот сделает ей предложение. Она планирует купить квартиру, но Генрих предлагает ей рискнуть и вложить средства в его бизнес — завод по производству пельменей в Нижних Теплышках. Влюблённая и полная надежд Оля соглашается, но вскоре узнает, что возлюбленный оказался аферистом…

📌«Равиоли Оли» в кино с 5 февраля!
📌Билеты уже в продаже"""
    
    print("=" * 50)
    print("🧪 Тестирование классификатора")
    print("=" * 50)
    
    is_giveaway = await check_if_giveaway(test_text)
    
    if is_giveaway:
        print("---")
        print("✅ Результат классификации: Это розыгрыш!")
        print("---")
        
        # Извлекаем детальную информацию
        data = await extract_giveaway_info(test_text)
        
        if data:
            print("📊 Детальная информация о розыгрыше:")
            print(f"📌 Название: {data.get('giveaway_name', 'Не указано')}")
            print(f"🎁 Призы: {', '.join(data.get('prizes', []))}")
            print(f"📝 Условия: {', '.join(data.get('conditions', []))}")
            print(f"📅 Дата окончания: {data.get('end_date', 'Не указана')}")
    else:
        print("---")
        print("❌ Результат классификации: Это не розыгрыш.")


if __name__ == "__main__":
    # Запуск тестовой функции
    print("🚀 Запуск тестового сценария...")
    asyncio.run(test_ollama())
import os
import json
import re
import asyncio
from ollama import AsyncClient

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
"end_date": "дата или null"
}

Инструкции:
1. Если в тексте есть призы и условия участия - is_giveaway: true
2. giveaway_name: извлеки название из текста или используй первую строку
3. conditions: только конкретные требования к участникам
4. prizes: все призы, включая денежные, товары, услуги
5. end_date: если дата указана, верни в формате ДД.ММ.ГГГГ

{
"is_giveaway": true/false,
"giveaway_name": "название или null",
"conditions": ["условие 1", "условие 2", ...],
"prizes": ["приз 1", "приз 2", ...],
"end_date": "дата или null"
}
Инструкции по обработке текста:
is_giveaway: true, если в тексте есть призы и условия участия.
giveaway_name: краткое название. Очищай от лишних эмодзи в начале и конце.
conditions: формулируй условия в инфинитиве (например: "подписаться", "поставить лайк").
prizes:
Исправляй грамматические ошибки и согласование падежей.
Числительные должны быть согласованы с существительными (например, вместо "6 сеты" пиши "6 наборов (сетов)").
Каждый приз должен быть законченной фразой в именительном падеже.
end_date: формат ДД.ММ.ГГГГ. Если дата не указана, пиши null.
Пример исправления:
Вход: "Призы:6 сеты с глиттером" -> Выход в JSON: "6 наборов с глиттером".
Не добавляй никакого текста кроме JSON.
"""


async def check_if_giveaway(post_text):
    """Проверяет, является ли текст розыгрышем"""
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
        print(f"Ответ API (классификация): {answer}")
        return "ДА" in answer or "YES" in answer
        
    except Exception as e:
        print(f"Ошибка API (классификация): {e}")
        return False


async def extract_giveaway_info(post_text):
    """Извлекает структурированную информацию о розыгрыше"""
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
            print("Не удалось найти JSON в ответе")
            return None
            
    except Exception as e:
        print(f"Ошибка API (извлечение информации): {e}")
        return None


async def request_gigachat_filter_post(text_post):
    """Основная функция для фильтрации постов (аналог оригинальной функции)"""
    try:
        # Сначала проверяем классификатором (опционально, можно пропустить)
        is_giveaway = await check_if_giveaway(text_post)
        
        if not is_giveaway:
            print("Классификатор определил, что это не розыгрыш")
            return {
                "is_giveaway": False,
                "giveaway_name": None,
                "conditions": [],
                "prizes": [],
                "end_date": None
            }
        
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
        
        response = await client.chat(
            model='deepseek-v3.1:671b-cloud',
            messages=messages,
            options={
                'temperature': 0.1,
                'num_predict': 500
            }
        )
        
        content = response.message.content

        # 1. Извлекаем JSON из текста (на случай лишних слов от модели)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            print("JSON не найден в ответе")
            return None

        # 2. Десериализация
        data = json.loads(json_match.group(0))
        print(data)
        
        # 3. Печать (используем ключи, которые просили в промпте!)
        print(f"Заголовок: {data.get('giveaway_name')}")
        print(f"Что разыгрывают: {', '.join(data.get('prizes', []))}")
        print(f"Условия: {', '.join(data.get('conditions', []))}")
        print(f"До какого числа: {data.get('end_date')}")

        return data

    except Exception as e:
        print(f"Ошибка при обработке: {e}")
        return None


# Асинхронная версия для тестирования
async def test_ollama():
    """Тестовая функция для проверки работы Ollama"""
    test_text = """Помнишь наши лимитированные косметички в честь года Красной лошади? Приберегли несколько для особого случая 💃

Накануне Дня подружек отправим 6 победительницам сеты с глиттером для волос и тела, тушью, аксессуарами, матирующими салфетками, бомбочкой для ванны, украшениями и бальзамом для губ LP CARE.

Условия конкурса:
🍓 Подписывайся на канал @podrygka_ru
🍓 Ставь сердечко этому посту
🍓 Нажимай на кнопку «участвую» ниже

Победителей определим случайным образом 9 февраля."""
    
    print("=== Тестирование классификатора ===")
    is_giveaway = await check_if_giveaway(test_text)
    
    if is_giveaway:
        print("---")
        print("Результат классификации: Это розыгрыш!")
        print("---")
        
        # Извлекаем детальную информацию
        data = await extract_giveaway_info(test_text)
        
        if data:
            print("Детальная информация о розыгрыше:")
            print(f"Название: {data.get('giveaway_name', 'Не указано')}")
            print(f"Призы: {', '.join(data.get('prizes', []))}")
            print(f"Условия: {', '.join(data.get('conditions', []))}")
            print(f"Дата окончания: {data.get('end_date', 'Не указана')}")
    else:
        print("---")
        print("Результат классификации: Это не розыгрыш.")


if __name__ == "__main__":
    # Запуск тестовой функции
    asyncio.run(test_ollama())
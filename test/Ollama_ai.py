import os
import json
import re
from ollama import Client

# Настройка клиента для облачного Ollama API
client = Client(
    host='https://api.ollama.com',  # Или другой хост, если используете другой сервис
    headers={'Authorization': 'Bearer ' + '9a59055e7054461a9c8649ea6b15b5c4.57qbYygjhxcFYIx6MxdPAgWF'}
)

# Текст для анализа
text_post = """🥝🍅🍆🥑🥑

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

def check_if_giveaway(post_text):
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
        # Используем не потоковый запрос для простоты
        response = client.chat(
            model='deepseek-v3.1:671b-cloud',  # или 'deepseek-r1:latest'
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

def extract_giveaway_info(post_text):
    """Извлекает структурированную информацию о розыгрыше"""
    prompt = """Ты анализируешь тексты на наличие розыгрышей и конкурсов. 
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

Пример:
{
"is_giveaway": true,
"giveaway_name": "Розыгрыш 8000 рублей в ресторане",
"conditions": ["подписаться на аккаунт", "поставить лайки"],
"prizes": ["8000 рублей в Rusty Rat & Pizza"],
"end_date": "03.02.2024"
}

Не добавляй никакого текста кроме JSON.

Текст который нужно обработать:""" + post_text
    
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
        response = client.chat(
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

if __name__ == "__main__":
    # Установите переменную окружения или вставьте токен напрямую
    # Способ 1: Установите переменную окружения
    # export OLLAMA_API_KEY="ваш_токен"
    
    # Способ 2: Укажите токен прямо в коде (не рекомендуется для продакшена)
    # os.environ['OLLAMA_API_KEY'] = 'ваш_токен_здесь'
    
    # Проверка классификатором
    is_giveaway = check_if_giveaway(text_post)
    
    if is_giveaway:
        print("---")
        print("Результат классификации: Это розыгрыш!")
        print("---")
        
        # Извлекаем детальную информацию
        data = extract_giveaway_info(text_post)
        
        if data:
            print("Детальная информация о розыгрыше:")
            print(f"Название: {data.get('giveaway_name', 'Не указано')}")
            print(f"Призы: {', '.join(data.get('prizes', []))}")
            print(f"Условия: {', '.join(data.get('conditions', []))}")
            print(f"Дата окончания: {data.get('end_date', 'Не указана')}")
    else:
        print("---")
        print("Результат классификации: Это не розыгрыш.")
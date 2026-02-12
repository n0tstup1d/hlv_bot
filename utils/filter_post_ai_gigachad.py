from gigachat import GigaChat
import ssl
import urllib3
import json
import re

# Отключение предупреждений о SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

api_key = 'MDE5YzE4ZTctZjFlZC03NjYwLWIyZjUtYTdkMjYxODdlYTA3OmZiYjZhYTMwLTJhN2YtNGFiNy04OTU0LWNiNDc4ZTBlYTM4NQ=='

# Создаем пользовательский SSL контекст
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

giga = GigaChat(
    credentials=api_key,
    verify_ssl_certs=False  # Отключаем проверку SSL
)

text_for_giga = """Ты анализируешь тексты на наличие розыгрышей и конкурсов. 
                        Верни ответ строго в формате JSON со следующей структурой:

                        {
                        "is_giveaway": True/False,
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
                    """


async def request_gigachat_filter_post(text_post):
    try:
        full_prompt = f"{text_for_giga}\n\nТекст для обработки:\n{text_post}"
        response = giga.chat(full_prompt)
        content = response.choices[0].message.content

        # 1. Извлекаем JSON из текста (на случай лишних слов от модели)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            print("JSON не найден в ответе")
            return None

        # 2. Десериализация
        data = json.loads(json_match.group(0))
        print(data)
        # 3. Печать (используем ключи, которые просили в промпте!)
        # Используем .get(), чтобы код не ломался, если ключа нет
        print(f"Заголовок: {data.get('giveaway_name')}")
        print(f"Что разыгрывают: {', '.join(data.get('prizes', []))}")
        print(f"Условия: {', '.join(data.get('conditions', []))}")
        print(f"До какого числа: {data.get('end_date')}")

        return data

    except Exception as e:
        print(f"Ошибка при обработке: {e}")
        return None
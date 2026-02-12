# from huggingface_hub import InferenceClient

# # Твой токен
# HF_TOKEN = "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" 

# # Твой текст поста
# post_text = "Дарим 8 000 ₽ в Rusty Rat & Pizza\n\nRusty Rat & Pizza — это новый проект от команды Underdog в концепции Little Italy meets Brooklyn. Это не классическая Италия, а искренняя бруклинская история.\n\nВ меню 16 вариантов пиццы: например, с пепперони, моцареллой и каштановым медом или с тремя видами сыра и трюфельным медом.\n\nПобедителю мы советуем заказать итальянский свадебный суп или стриплойн с картофелем и соусом пепперкорн, а также коктейль Pickle street на основе текилы с лаймом, огуречным рассолом и агавой.\n\nПравила участия:\n- подпишитесь на @afisharestaurants;\n- нажмите на кнопку «Хочу депозит»;\n- поставьте сердечко на ближайшие три поста.\n\n🍕Подсказка: присылайте этот пост тому, кто в случае выигрыша пригласит вас на ужин.\n\nПобедителя выберет бот-рандомайзер 3 февраля и укажет его имя в этом же посте."

# # Инициализируем клиента (модель укажем внутри функции)
# HF_TOKEN = "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" 
# client = InferenceClient(api_key=HF_TOKEN)

# def check_if_giveaway(post_text_to_analyze):
#     # Формируем промпт на русском языке
#     messages = [
#         {
#             "role": "system",
#             "content": "Ты бот-классификатор, который определяет, является ли текст розыгрышем или конкурсом. Ответь строго одним словом: ДА или НЕТ.",
#         },
#         {
#             "role": "user",
#             "content": post_text_to_analyze # Вставляем текст поста сюда
#         }
#     ]
    
#     try:
#         completion = client.chat.completions.create(
#             model="zai-org/GLM-4.7-Flash:zai-org", # Ваша рабочая модель
#             messages=messages,
#             max_tokens=15, # Ограничиваем ответ для скорости
#         )
        
#         # Получаем ответ из структуры, которую вы показали
#         answer = completion.choices[0].message.content.strip().upper()
#         print(f"Ответ API: {answer}")
#         return "ДА" in answer or "YES" in answer
        
#     except Exception as e:
#         print(f"Ошибка API: {e}")
#         return False

# if __name__ == "__main__":
#     is_giveaway = check_if_giveaway(post_text)
#     if is_giveaway:
#         print("---")
#         print("Результат: Это розыгрыш, пост будет отфильтрован!")
#     else:
#         print("---")
#         print("Результат: Это не розыгрыш.")



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

text_post = "🥝🍅🍆🥑🥑\n\n2 февраля в КАРО 11 Октябрь состоится светская премьера романтической комедии «Равиоли Оли». В главных ролях: Ольга Бузова, Владимир Яглыч, Вольфганг Черни , Максим Лагашкин, Ева Смирнова, Марина Федункив и Эвелина Блёданс.\n\nМы разыгрываем три пары билетов на премьерный показ фильма в Москве.\n\nДля участия в конкурсе:\n\n1. Будь подписан на канал КАРО \n2. Поставь  🔥 этой записи\n3. Нажми кнопку «Участвовать»\n\nИтоги конкурса подведем 2 февраля под этим постом.\n\nОльга Бузова, звезда сцены и экрана, мечтает о романтическом будущем с идеальным мужчиной — красавцем-немцем Генрихом, который вот-вот сделает ей предложение. Она планирует купить квартиру, но Генрих предлагает ей рискнуть и вложить средства в его бизнес — завод по производству пельменей в Нижних Теплышках. Влюблённая и полная надежд Оля соглашается, но вскоре узнает, что возлюбленный оказался аферистом…\n\n📌«Равиоли Оли» в кино с 5 февраля!\n📌Билеты уже в продаже"

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

                        Пример:
                        {
                        "is_giveaway": true,
                        "giveaway_name": "Розыгрыш 8000 рублей в ресторане",
                        "conditions": ["подписаться на аккаунт", "поставить лайки"],
                        "prizes": ["8000 рублей в Rusty Rat & Pizza"],
                        "end_date": "03.02.2024"
                        }

                        Не добавляй никакого текста кроме JSON.
                        
                        Текст который нужно обработать:
                    """
text_for_giga += text_post


response = giga.chat(text_for_giga)

response_text = response.choices[0].message.content

data = json.loads(response_text)

json_match = re.search(r'\{.*\}', data, re.DOTALL)
if json_match:
        data = json.loads(json_match.group(0))
        
        # Теперь твой принт будет работать идеально
        print(f"Заголовок: {data['title']}")
        print(f"Что разыгрывают: {', '.join(data['prizes'])}")
        print(f"Условия: {', '.join(data['conditions'])}")
        print(f"До какого числа: {data['deadline']}")
        
        
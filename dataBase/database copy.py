import asyncpg
import os
from dotenv import load_dotenv
from parametrs.database_parametr import DB_CONFIG
from apscheduler.schedulers.asyncio import AsyncIOScheduler 
from parametrs.config import ADMIN_ID as AD
from aiogram import Bot
from aiogram.types import FSInputFile
from datetime import datetime
import asyncio

load_dotenv()

class Database:
    def __init__(self,bot_instance: Bot = None):
        self.pool = None
        
        #self.sheduler = AsyncIOScheduler()
        self.admin_user_id = int(AD)
        
        self.bot = bot_instance
    
    async def close(self):
        """Закрытие соединения с БД"""
        if self.pool:
            await self.pool.close()
            print("✅ Соединение с БД закрыто")
        
        # if self.sheduler.running:
        #     self.sheduler.shutdown()
        #     print("✅ Планировщик остановлен")
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(user = DB_CONFIG["user"]
                                              ,password=DB_CONFIG["password"],
                                                database=DB_CONFIG["database"],
                                                host=DB_CONFIG["host"],
                                                port=DB_CONFIG["port"],
                                                )
       
        
        await self.created_tables()
        await self.insert_initial_data()
        print(f"✅ Подключились к базе {DB_CONFIG['database']}!")
        
        # self.sheduler.add_job(
        #     self.backup_database_and_send_to_admin,
        #     'interval',
        #     hours = 24,
        #     next_run_time=datetime.now()
        # )
        # self.sheduler.start()
        # print("✅ Планировщик бэкапов запущен (каждые 24 часа).")
        
    async def created_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS channels (
                                    id_channels SERIAL PRIMARY KEY,
                                    channel_username VARCHAR(255) NOT NULL,
                                    channel_id BIGINT UNIQUE,
                                    is_active BOOLEAN DEFAULT TRUE,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                   )''')
        
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS admins (
                                   id_adm SERIAL PRIMARY KEY,
                                   user_id BIGINT UNIQUE
                                   )''')
            
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS posts (
                                    id_post SERIAL PRIMARY KEY,
                                    original_id BIGINT NOT NULL,
                                    channel_id BIGINT NOT NULL,
                                    title TEXT, 
                                    post_link TEXT,
                                    message_text TEXT,
                                    content_hash VARCHAR(100),
                                    has_media BOOLEAN DEFAULT FALSE,
                                    has_buttons BOOLEAN DEFAULT FALSE,
                                    end_date_gift TIMESTAMP, 
                                    post_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    UNIQUE(original_id, channel_id)
                                                    )''')
            
            # await conn.execute('''
            #                    CREATE TABLE IF NOT EXISTS forwared_posts (
            #                        id_forwared_post SERIAL PRIMARY KEY,
            #                        id_channels BIGINT NOT NULL,
            #                        original_id BIGINT NOT NULL UNIQUE,
                                   
            #                        FOREIGN KEY (id_channels) REFERENCES channels(id_channels),
            #                        FOREIGN KEY (original_id) REFERENCES posts(original_id)
            #                    )''')
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS client_acccounts (
                                   id_accounts_client SERIAL PRIMARY KEY,
                                   id_channels BIGINT NOT NULL,
                                   original_id BIGINT NOT NULL,
                                   
                                   
                                   FOREIGN KEY (original_id, id_channels) REFERENCES posts(original_id, channel_id)
                               )''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS post_analysis (
                    id_analysis SERIAL PRIMARY KEY,
                    post_id INTEGER REFERENCES posts(id_post),
                    giveaway_score FLOAT DEFAULT 0,
                    ad_score FLOAT DEFAULT 0,
                    total_score FLOAT DEFAULT 0,
                    decision VARCHAR(50),
                    decision_reason TEXT,
                    matched_keywords TEXT[],
                    hashtags TEXT[],
                    button_count INTEGER DEFAULT 0,
                    giveaway_buttons INTEGER DEFAULT 0,
                    media_type VARCHAR(50),
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    forwarded BOOLEAN DEFAULT FALSE,
                    forwarded_to_channel VARCHAR(255),
                    is_manual_override BOOLEAN DEFAULT FALSE,
                    manual_decision VARCHAR(50)
                )''')
            
            # Таблица для ключевых слов (можно обновлять динамически)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id_keyword SERIAL PRIMARY KEY,
                    keyword VARCHAR(100) UNIQUE NOT NULL,
                    keyword_type VARCHAR(50), -- 'giveaway', 'ad', 'blacklist'
                    weight FLOAT DEFAULT 1.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
            
            # Таблица для статистики каналов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_stats (
                    id_stat SERIAL PRIMARY KEY,
                    channel_id BIGINT REFERENCES channels(channel_id),
                    total_posts INTEGER DEFAULT 0,
                    giveaway_posts INTEGER DEFAULT 0,
                    ad_posts INTEGER DEFAULT 0,
                    last_giveaway_date TIMESTAMP,
                    avg_giveaway_score FLOAT DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS forwarded_posts (
                    id_forwarded_post SERIAL PRIMARY KEY,
                    post_id INTEGER REFERENCES posts(id_post),
                    forwarded_to VARCHAR(255),
                    forwarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE
                )''')
            
             # Индексы для быстрого поиска
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_channel_date ON posts(channel_id, post_date)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_analysis_score ON post_analysis(total_score)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_analysis_decision ON post_analysis(decision)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_keywords_type ON keywords(keyword_type, is_active)')
            
    async def insert_initial_data(self):
        async with self.pool.acquire() as conn:
            initial_users = [
                (7957920325)                
            ]
            
            giveaway_keywords = [
            'розыгрыш', 'разыгрываю', 'конкурс', 'giveaway', 'гив',
            'выиграй', 'выигрыш', 'победитель', 'приз', 'награда',
            'участвуй', 'участие', 'дарим', 'раздаем', 'подарок',
            'бесплатн', 'даром', 'лотерея', 'розыгрываю', 'конкурс',
            'гивевей', 'соревнование', 'призы', 'разыграю'
            ]
            
            ad_keywords = [
                'реклама', 'оплачено', 'заказ', 'сотрудничество',
                'партнер', 'спонсор', 'sponsored', 'ad', 'промо',
                'промокод', 'купить', 'цена', 'стоимость', 'заказать',
                'скидк', 'акция', 'распродаж'
            ]
            
            blacklist_keywords = [
                'ставк', 'казин', 'беттин', 'гемблинг', 'азарт',
                'крипт', 'биткоин', 'ставки', 'пари', 'порно',
                'xxx', '18+', 'наркот', 'закладк'
            ]
            
            for keyword in giveaway_keywords:
                await conn.execute('''
                    INSERT INTO keywords (keyword, keyword_type, weight)
                    VALUES ($1, 'giveaway', 1.0)
                    ON CONFLICT (keyword) DO NOTHING
                ''', keyword)
            
            for keyword in ad_keywords:
                await conn.execute('''
                    INSERT INTO keywords (keyword, keyword_type, weight)
                    VALUES ($1, 'ad', 1.0)
                    ON CONFLICT (keyword) DO NOTHING
                ''', keyword)
            
            for keyword in blacklist_keywords:
                await conn.execute('''
                    INSERT INTO keywords (keyword, keyword_type, weight)
                    VALUES ($1, 'blacklist', 5.0)
                    ON CONFLICT (keyword) DO NOTHING
                ''', keyword)
                
            for user_id in initial_users:
                await conn.execute('''
                                   INSERT INTO admins (user_id)
                                   VALUES ($1)
                                   ON CONFLICT (user_id) DO NOTHING
                                   ''', (user_id))
           
    async def send_backup_file_to_admin(self, filename, user_id):
        if not self.bot:
            await self.bot.send_message(chat_id=user_id,text = "❌ Ошибка: Объект бота не был предоставлен классу Database. Отправка бэкапа невозможна.")
            if os.path.exists(filename):
                os.remove(filename)
            return
        try:
            with open(filename, 'rb') as f:
                document_file = FSInputFile(path = filename) 
                await self.bot.send_document(chat_id=user_id, document=document_file)    
            if os.path.exists(filename):
                os.remove(filename)
            print(f"✅ Файл бэкапа отправлен и удален.")
        except Exception as e:
            if os.path.exists(filename):
                os.remove(filename)
            await self.bot.send_message(chat_id=user_id,text = f"❌ Не удалось отправить бэкап администратору: {e}")
    
    async def backup_database_and_send_to_admin(self, user_id: int = None):
        
        if user_id is None:
            final_user_id = AD
        else:
            final_user_id = user_id 
        db_name = DB_CONFIG['database']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{db_name}_backu_{timestamp}.sql"
        PG_DUMP_PATH = DB_CONFIG["pg_dump_path"] 
        
        try:
            process = await asyncio.create_subprocess_exec(
                PG_DUMP_PATH,
                '-U', DB_CONFIG["user"],
                '-d', db_name,
                '-h', DB_CONFIG["host"],
                '-p', str(DB_CONFIG["port"]),
                '-F', 'p',
                '-f', backup_filename,
                env={'PGPASSWORD': DB_CONFIG["password"], **os.environ} # Передача пароля через переменную окружения
            )
            await process.wait()
            if process.returncode == 0:
                print(f"✅ Бэкап успешно создан: {backup_filename}")
                await self.send_backup_file_to_admin(backup_filename, final_user_id)
            else:
                await self.bot.send_message(chat_id=final_user_id,text = f"❌ Ошибка при создании бэкапа. Код возврата: {process.returncode}")
        except FileNotFoundError:
            await self.bot.send_message(chat_id=final_user_id,text = "❌ Ошибка: Утилита 'pg_dump' не найдена. Убедитесь, что PostgreSQL установлен и 'pg_dump' добавлен в PATH.")
        except Exception as e:
            await self.bot.send_message(chat_id=final_user_id,text = f"❌ Неожиданная ошибка при бэкапе: {e}")
            
##########################################################################################################################################################################################################
# ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD ADD# 
##########################################################################################################################################################################################################

    async def add_admin(self, user_id: int):
        """Получить все user_id"""
        async with self.pool.acquire() as conn:
            await conn.execute('INSERT INTO admins (user_id) VALUES ($1)', user_id)
    
    async def add_new_post(self, post_id: int, channel_id: int):
        """Добавить новый пост и связать его с существующим каналом"""
        async with self.pool.acquire() as conn:
            # База данных проверит, существует ли этот channel_id в таблице channels
            await conn.execute(
                'INSERT INTO posts (post_id, channel_id) VALUES ($1, $2)',
                post_id, channel_id
            )

    async def add_channel(self, channel_username: str):
        """"Добавление тгк в бд"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO channels (channel_username) VALUES ($1)', channel_username
            )


##########################################################################################################################################################################################################
# EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT EDIT# 
##########################################################################################################################################################################################################

##########################################################################################################################################################################################################
# READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ READ# 
##########################################################################################################################################################################################################

    
    async def get_today_giveaways(self):
        """Ищем розыгрыши, которые закончатся в ближайшие 24 часа"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    p.title,
                    p.post_link,  # ← Уже готовая ссылка!
                    p.end_date_gift,
                    p.original_id,
                    p.channel_id,
                    c.channel_username  # ← На всякий случай сохраняем
                FROM posts p
                JOIN post_analysis pa ON p.id_post = pa.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                WHERE 
                    p.end_date_gift IS NOT NULL 
                    AND p.end_date_gift >= NOW() 
                    AND p.end_date_gift <= NOW() + INTERVAL '24 hours'
                    AND pa.decision = 'GIVEAWAY'
                    AND pa.forwarded = TRUE
                    AND p.post_link IS NOT NULL  # ← Только с ссылками
                ORDER BY p.end_date_gift ASC
                LIMIT 15
            """)
            return rows
            
    async def get_all_user_ids(self):
        """Получить все user_id"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT user_id FROM admins')
            return [row['user_id'] for row in rows]
    
    async def get_all_channel_ids(self):
        """Получить все user_id"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT channel_username FROM channels')
            return [row['channel_username'] for row in rows]
    
    async def get_posts_by_channel_username(self, username: str):
        """Получить все post_id из канала по его username"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT p.post_id 
                FROM posts p
                JOIN channels c ON p.channel_id = c.channel_id
                WHERE c.channel_username = $1
            """
            rows = await conn.fetch(query, username)
            return [row['post_id'] for row in rows]

##########################################################################################################################################################################################################
# DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL DEL# 
##########################################################################################################################################################################################################

##########################################################################################################################################################################################################
# OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER OTHER  # 
##########################################################################################################################################################################################################

#для анализа постов
async def save_post_analysis(self, analysis_data, event=None):
    """Сохранение результата анализа поста с ссылкой"""
    async with self.pool.acquire() as conn:
        # 1. Получаем username канала (если есть event)
        post_link = ""
        if event and event.chat:
            chat = event.chat
            
            # Если у канала есть username
            if hasattr(chat, 'username') and chat.username:
                post_link = f"https://t.me/{chat.username}/{event.message.id}"
            
            # Если канал приватный (без username)
            elif hasattr(chat, 'id'):
                # Используем формат для приватных каналов
                # Обрабатываем отрицательные ID (Telegram формат)
                channel_id = chat.id
                if channel_id < 0:
                    # Для каналов: -1001234567890 → 1234567890
                    if str(channel_id).startswith('-100'):
                        short_id = str(channel_id)[4:]  # Убираем '-100'
                    else:
                        short_id = str(abs(channel_id))
                    post_link = f"https://t.me/c/{short_id}/{event.message.id}"
        
        # 2. Сохраняем пост С ссылкой
        post_id = await conn.fetchval('''
            INSERT INTO posts (
                original_id, channel_id, message_text, content_hash, 
                has_media, has_buttons, title, post_link, end_date_gift
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (original_id, channel_id) 
            DO UPDATE SET 
                post_link = COALESCE(EXCLUDED.post_link, posts.post_link)
            RETURNING id_post
        ''', 
        analysis_data['original_id'],
        analysis_data['channel_id'],
        analysis_data.get('message_text', '')[:5000],
        analysis_data.get('content_hash', ''),
        analysis_data.get('has_media', False),
        analysis_data.get('has_buttons', False),
        analysis_data.get('title', 'Розыгрыш'),
        post_link,  # ← Сохраняем ссылку!
        analysis_data.get('end_date_gift')
        )
        
        # Сохраняем анализ
        await conn.execute('''
            INSERT INTO post_analysis (
                post_id, giveaway_score, ad_score, total_score,
                decision, decision_reason, matched_keywords, hashtags,
                button_count, giveaway_buttons, media_type, forwarded,
                forwarded_to_channel
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (post_id) DO UPDATE SET
                giveaway_score = EXCLUDED.giveaway_score,
                ad_score = EXCLUDED.ad_score,
                total_score = EXCLUDED.total_score,
                decision = EXCLUDED.decision,
                decision_reason = EXCLUDED.decision_reason,
                analyzed_at = CURRENT_TIMESTAMP
        ''',
        post_id,
        analysis_data['giveaway_score'],
        analysis_data['ad_score'],
        analysis_data['total_score'],
        analysis_data['decision'],
        analysis_data['decision_reason'],
        analysis_data['matched_keywords'],
        analysis_data['hashtags'],
        analysis_data['button_count'],
        analysis_data['giveaway_buttons'],
        analysis_data['media_type'],
        analysis_data['forwarded'],
        analysis_data.get('forwarded_to_channel', '')
        )
        
        # Обновляем статистику канала
        await self.update_channel_stats(analysis_data['channel_id'], analysis_data['decision'])
        
        return post_id

async def update_channel_stats(self, channel_id, decision):
    """Обновление статистики канала"""
    async with self.pool.acquire() as conn:
        # Получаем текущую статистику
        stats = await conn.fetchrow('''
            SELECT * FROM channel_stats 
            WHERE channel_id = $1
        ''', channel_id)
        
        if not stats:
            # Создаем новую запись
            await conn.execute('''
                INSERT INTO channel_stats (channel_id, total_posts, giveaway_posts, ad_posts)
                VALUES ($1, 1, $2, $3)
            ''', channel_id, 
            1 if decision == 'GIVEAWAY' else 0,
            1 if decision == 'AD' else 0)
        else:
            # Обновляем существующую
            update_query = '''
                UPDATE channel_stats 
                SET total_posts = total_posts + 1,
                    updated_at = CURRENT_TIMESTAMP
            '''
            params = [channel_id]
            
            if decision == 'GIVEAWAY':
                update_query += ', giveaway_posts = giveaway_posts + 1, last_giveaway_date = CURRENT_TIMESTAMP'
            elif decision == 'AD':
                update_query += ', ad_posts = ad_posts + 1'
            
            update_query += ' WHERE channel_id = $1'
            await conn.execute(update_query, channel_id)

async def get_keywords_by_type(self, keyword_type=None):
    """Получение ключевых слов из БД"""
    async with self.pool.acquire() as conn:
        if keyword_type:
            rows = await conn.fetch('''
                SELECT keyword, weight FROM keywords 
                WHERE keyword_type = $1 AND is_active = TRUE
                ORDER BY weight DESC
            ''', keyword_type)
        else:
            rows = await conn.fetch('''
                SELECT keyword, keyword_type, weight FROM keywords 
                WHERE is_active = TRUE
                ORDER BY keyword_type, weight DESC
            ''')
        
        if keyword_type:
            return {row['keyword']: row['weight'] for row in rows}
        else:
            result = {}
            for row in rows:
                if row['keyword_type'] not in result:
                    result[row['keyword_type']] = {}
                result[row['keyword_type']][row['keyword']] = row['weight']
            return result

async def is_post_processed(self, original_id, channel_id):
    """Проверка, был ли уже обработан пост"""
    async with self.pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT p.id_post FROM posts p
            WHERE p.original_id = $1 AND p.channel_id = $2
        ''', original_id, channel_id)
        return row is not None

async def get_channel_stats(self, channel_id):
    """Получение статистики канала"""
    async with self.pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT * FROM channel_stats 
            WHERE channel_id = $1
        ''', channel_id)

async def add_keyword(self, keyword, keyword_type, weight=1.0):
    """Добавление нового ключевого слова"""
    async with self.pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO keywords (keyword, keyword_type, weight)
            VALUES ($1, $2, $3)
            ON CONFLICT (keyword) DO UPDATE SET
                keyword_type = EXCLUDED.keyword_type,
                weight = EXCLUDED.weight,
                is_active = TRUE
        ''', keyword, keyword_type, weight)

async def get_analysis_stats(self, days=7):
    """Получение статистики анализа за период"""
    async with self.pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT 
                COUNT(*) as total_posts,
                SUM(CASE WHEN decision = 'GIVEAWAY' THEN 1 ELSE 0 END) as giveaway_posts,
                SUM(CASE WHEN decision = 'AD' THEN 1 ELSE 0 END) as ad_posts,
                SUM(CASE WHEN decision = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral_posts,
                SUM(CASE WHEN forwarded = TRUE THEN 1 ELSE 0 END) as forwarded_posts,
                AVG(total_score) as avg_score
            FROM post_analysis pa
            JOIN posts p ON pa.post_id = p.id_post
            WHERE pa.analyzed_at >= NOW() - INTERVAL '$1 days'
        ''', days)
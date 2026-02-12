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
    def __init__(self, bot_instance: Bot = None):
        self.pool = None
        self.admin_user_id = int(AD)
        self.sheduler = AsyncIOScheduler()
        self.bot = bot_instance
    
    async def close(self):
        """Закрытие соединения с БД"""
        if self.pool:
            await self.pool.close()
            print("✅ Соединение с БД закрыто")
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
        )
       
        await self.created_tables()
        await self.insert_initial_data()
        print(f"✅ Подключились к базе {DB_CONFIG['database']}!")
        
        self.sheduler.add_job(
            self.backup_database_and_send_to_admin,
            'interval',
            hours=24,
            next_run_time=datetime.now()
        )
        self.sheduler.start()
        print("✅ Планировщик бэкапов запущен (каждые 24 часа).")
        
    async def created_tables(self):
        async with self.pool.acquire() as conn:
            # Таблица каналов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id_channels SERIAL PRIMARY KEY,
                    channel_username VARCHAR(255) NOT NULL UNIQUE,
                    channel_id BIGINT UNIQUE,
                    is_active BOOLEAN DEFAULT TRUE
                )''')
        
            # Таблица администраторов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id_adm SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE
                )''')
            
            # Таблица постов (основная)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id_post SERIAL PRIMARY KEY,
                    original_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    filtered_message_text TEXT,
                    post_link TEXT,
                    our_post_link TEXT,
                    message_text TEXT,
                    has_media BOOLEAN DEFAULT FALSE,
                    has_buttons BOOLEAN DEFAULT FALSE,
                    end_date_gift TIMESTAMP,
                    UNIQUE(original_id, channel_id)
                )''')
            
            # Таблица анализа постов
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
                    quality_score INTEGER DEFAULT 5
                )''')
            
            # Таблица для ключевых слов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id_keyword SERIAL PRIMARY KEY,
                    keyword VARCHAR(100) UNIQUE NOT NULL,
                    keyword_type VARCHAR(50),
                    weight FLOAT DEFAULT 1.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
            
            # Таблица для статистики каналов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_stats (
                    id_stat SERIAL PRIMARY KEY,
                    channel_id BIGINT,
                    total_posts INTEGER DEFAULT 0,
                    giveaway_posts INTEGER DEFAULT 0,
                    ad_posts INTEGER DEFAULT 0,
                    last_giveaway_date TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    
    async def insert_initial_data(self):
        async with self.pool.acquire() as conn:
            # Добавляем администратора
            initial_users = [7957920325]
            for user_id in initial_users:
                await conn.execute('''
                    INSERT INTO admins (user_id)
                    VALUES ($1)
                    ON CONFLICT (user_id) DO NOTHING
                ''', user_id)
                # ('бренд', 'ad', 0.5),
                # ('производитель', 'ad', 0.5),
                # ('сеть', 'ad', 0.4),
                # ('фирма', 'ad', 0.4),
                # ('компания', 'ad', 0.4),
            # Добавляем начальные ключевые слова
            initial_keywords = [
                ('розыгрыш', 'giveaway', 1.0),
                ('конкурс', 'giveaway', 1.0),
                ('приз', 'giveaway', 1.0),
                ('дарим', 'giveaway', 1.0),
                ('разыгрываем', 'giveaway', 1.0),
                ('выиграй', 'giveaway', 1.0),
                ('подарок', 'giveaway', 1.0),
                ('разыгрываю', 'giveaway', 1.0),
                ('выигрыш', 'giveaway', 1.0),
                ('победитель', 'giveaway', 0.8),
                ('лотерея', 'giveaway', 1.0),
                ('участвуй', 'giveaway', 0.8),
                ('участвовать', 'giveaway', 0.8),
                ('голосование', 'giveaway', 0.7),
                ('акция', 'giveaway', 0.6),
                ('халява', 'giveaway', 1.0),
                ('бесплатно', 'giveaway', 0.7),
                ('бесплатный', 'giveaway', 0.7),
                ('даром', 'giveaway', 0.8),
                ('поздравляем', 'giveaway', 0.5),
                ('объявляем', 'giveaway', 0.5),
                ('счастливчик', 'giveaway', 0.8),
                ('финалист', 'giveaway', 0.7),
                ('награда', 'giveaway', 0.8),
                ('призовой', 'giveaway', 0.8),
                ('выиграть', 'giveaway', 1.0),
                ('забрать', 'giveaway', 0.7),
                ('получить', 'giveaway', 0.7),
                ('поздравления', 'giveaway', 0.5),
                ('удача', 'giveaway', 0.6),
                ('везунчик', 'giveaway', 0.7),
                ('подарочный', 'giveaway', 0.8),
                ('конкурсный', 'giveaway', 0.9),
                ('случайный', 'giveaway', 0.6),
                ('розыгрышный', 'giveaway', 0.9),
                ('дарю', 'giveaway', 0.8),
                ('разыграем', 'giveaway', 1.0),
                ('набор', 'giveaway', 0.6),
                ('билет', 'giveaway', 0.7),
                ('промокод', 'giveaway', 0.8),
                ('скидка', 'giveaway', 0.5),
                ('бонус', 'giveaway', 0.6),
                ('плюшка', 'giveaway', 0.7),
                
                
                
                ('реклама', 'ad', 1.0),
                ('ИП', 'ad', 1.0),
                ('ИНН', 'ad', 1.0),
                ('Часы работы', 'ad', 1.0),
                ('Адрес магазина', 'ad', 1.0),
                ('купить', 'ad', 1.0),
                ('заказать', 'ad', 1.0),
                ('продажа', 'ad', 0.9),
                ('скидка', 'ad', 0.6),
                ('распродажа', 'ad', 0.8),
                ('акция', 'ad', 0.5),
                ('товар', 'ad', 0.8),
                ('магазин', 'ad', 0.8),
                ('доставка', 'ad', 0.7),
                ('цена', 'ad', 0.6),
                ('стоимость', 'ad', 0.6),
                ('оплата', 'ad', 0.6),
                ('заказ', 'ad', 0.7),
                ('оформление', 'ad', 0.6),
                ('скидке', 'ad', 1.0),
                ('рекордной скидке', 'ad', 1.0),
                ('скидка', 'ad', 1.0),
                ('поздравляем победителей', 'ad', 0.3),
                ('победитель', 'ad', 1.0),
                ('победители', 'ad', 1.0),
                ('Спасибо всем за участие в конкурсе', 'ad', 2.0),
                ('Для участия', 'ad', 2.0),
                ('Отправьте кружок в бот', 'ad', 3.0),
                ('Запишите кружок', 'ad', 3.0),
                ('Оформить доставку', 'ad', 3.0),
                ('мобильном приложении', 'ad', 3.0),
                ('мобильное приложение', 'ad', 3.0),
                ('за кэшбэк', 'ad', 3.0),
                ('в приложении', 'ad', 3.0),
                ('в приложение', 'ad', 3.0),
                ('за кэшбэк', 'ad', 3.0),
                ('совершаете покупку', 'ad', 5.0),
                ('торт', 'ad', 5.0),
                ('отправить пост друзьям', 'ad', 10.0),
                ('переслать сообщение одному другу', 'ad', 10.0),
                ('лайки на все посты', 'ad', 10.0),
                ('ВКонтакте', 'ad', 3.0),
                
                
                ('скам', 'blacklist', 2.0),
                ('обман', 'blacklist', 2.0),
                ('мошенничество', 'blacklist', 2.0),
                ('развод', 'blacklist', 2.0),
                ('лохотрон', 'blacklist', 2.0),
                ('афера', 'blacklist', 2.0),
                ('купи чтобы выиграть', 'blacklist', 1.8),
                ('оплати участие', 'blacklist', 1.8),
                ('взнос', 'blacklist', 1.7),
                ('предоплата', 'blacklist', 1.7),
                ('плати', 'blacklist', 1.5),
                ('переведи деньги', 'blacklist', 2.0),
                ('отправь смс', 'blacklist', 1.8),
                ('платное участие', 'blacklist', 1.8),
                ('деньги за участие', 'blacklist', 2.0),
                ('Местные власти', 'blacklist', 2.0),
                ('Добровольцам', 'blacklist', 2.0),
                ('Добровольцы', 'blacklist', 2.0),
                ('Работать нужно', 'blacklist', 2.0),
                ('вести учёт', 'blacklist', 2.0),
                ('работать вечером', 'blacklist', 2.0),
                ('книга', 'blacklist', 2.0),
                ('книгу', 'blacklist', 2.0),
                ('книги', 'blacklist', 2.0),
                ('MAX', 'blacklist', 2.0),
                ('фрибетов', 'blacklist', 2.0),
                ('фрибет', 'blacklist', 2.0),
                ('winline', 'blacklist', 2.0),
                ('betboom', 'blacklist', 2.0),
                
                
                
                 
                
            ]
            
            for keyword, keyword_type, weight in initial_keywords:
                await conn.execute('''
                    INSERT INTO keywords (keyword, keyword_type, weight)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (keyword) DO NOTHING
                ''', keyword, keyword_type, weight)
    
    
    async def send_backup_file_to_admin(self, filename, user_id):
        if not self.bot:
            await self.bot.send_message(
                chat_id=user_id,
                text="❌ Ошибка: Объект бота не был предоставлен классу Database. Отправка бэкапа невозможна."
            )
            if os.path.exists(filename):
                os.remove(filename)
            return
        try:
            document_file = FSInputFile(path=filename) 
            await self.bot.send_document(chat_id=user_id, document=document_file)
            if os.path.exists(filename):
                os.remove(filename)
            print(f"✅ Файл бэкапа отправлен и удален.")
        except Exception as e:
            if os.path.exists(filename):
                os.remove(filename)
            await self.bot.send_message(
                chat_id=user_id,
                text=f"❌ Не удалось отправить бэкап администратору: {e}"
            )
    
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
                env={'PGPASSWORD': DB_CONFIG["password"], **os.environ}
            )
            await process.wait()
            if process.returncode == 0:
                print(f"✅ Бэкап успешно создан: {backup_filename}")
                await self.send_backup_file_to_admin(backup_filename, final_user_id)
            else:
                await self.bot.send_message(
                    chat_id=final_user_id,
                    text=f"❌ Ошибка при создании бэкапа. Код возврата: {process.returncode}"
                )
        except FileNotFoundError:
            await self.bot.send_message(
                chat_id=final_user_id,
                text="❌ Ошибка: Утилита 'pg_dump' не найдена. Убедитесь, что PostgreSQL установлен и 'pg_dump' добавлен в PATH."
            )
        except Exception as e:
            await self.bot.send_message(
                chat_id=final_user_id,
                text=f"❌ Неожиданная ошибка при бэкапе: {e}"
            )

    ##########################################################################
    # ADD METHODS
    ##########################################################################
    
    async def add_admin(self, user_id: int):
        """Добавить нового администратора"""
        async with self.pool.acquire() as conn:
            await conn.execute('INSERT INTO admins (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING', user_id)
    
    async def add_channel(self, channel_username: str):
        """Добавление канала в БД"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO channels (channel_username) VALUES ($1)',
                channel_username
            )

    ##########################################################################
    # READ METHODS
    ##########################################################################
    
    
            
    async def get_all_user_ids(self):
        """Получить все user_id администраторов"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT user_id FROM admins')
            return [row['user_id'] for row in rows]
    
    async def get_all_channel_ids(self):
        """Получить все username каналов"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT channel_username FROM channels')
            return [row['channel_username'] for row in rows]
    
    async def get_posts_by_channel_username(self, username: str):
        """Получить все original_id из канала по его username"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT p.original_id 
                FROM posts p
                JOIN channels c ON p.channel_id = c.channel_id
                WHERE c.channel_username = $1
            """
            rows = await conn.fetch(query, username)
            return [row['original_id'] for row in rows]

    ##########################################################################
    # POST ANALYSIS METHODS
    ##########################################################################
    
    """async def save_post_analysis_simple(self, analysis_data: dict, channel_id: int, original_id: int, message_text: str = ""):
        
        async with self.pool.acquire() as conn:
            try:
                # 1. Проверяем, есть ли канал в БД, если нет - создаем
                channel_exists = await conn.fetchval(
                    'SELECT 1 FROM channels WHERE channel_id = $1',
                    channel_id
                )
                
                if not channel_exists:
                    # Пытаемся получить username канала (будет заполнен позже)
                    await conn.execute('''
                        INSERT INTO channels (channel_id, channel_username)
                        VALUES ($1, $2)
                        ON CONFLICT (channel_id) DO NOTHING
                    ''', channel_id, f"unknown_{channel_id}")
                
                # 2. Сохраняем пост в таблицу posts
                post_id = await conn.fetchval('''
                    INSERT INTO posts (
                        original_id, channel_id, message_text, filtered_message_text,
                        has_media, has_buttons, end_date_gift, post_link
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (original_id, channel_id) 
                    DO UPDATE SET 
                        message_text = EXCLUDED.message_text,
                        filtered_message_text = EXCLUDED.filtered_message_text,
                        has_media = EXCLUDED.has_media,
                        has_buttons = EXCLUDED.has_buttons,
                        end_date_gift = EXCLUDED.end_date_gift,
                        post_link = EXCLUDED.post_link
                    RETURNING id_post
                ''', 
                original_id,
                channel_id,
                message_text[:5000] if message_text else '',
                analysis_data.get('filtered_message_text', '')[:5000],
                analysis_data.get('has_media', False),
                analysis_data.get('has_buttons', False),
                analysis_data.get('end_date'),
                analysis_data.get('post_link', '')
                )
                
                # 3. Сохраняем анализ в таблицу post_analysis
                await conn.execute('''
                    INSERT INTO post_analysis (
                        post_id, giveaway_score, ad_score, total_score,
                        decision, decision_reason, matched_keywords, hashtags,
                        button_count, giveaway_buttons, media_type
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (post_id) DO UPDATE SET
                        giveaway_score = EXCLUDED.giveaway_score,
                        ad_score = EXCLUDED.ad_score,
                        total_score = EXCLUDED.total_score,
                        decision = EXCLUDED.decision,
                        decision_reason = EXCLUDED.decision_reason,
                        matched_keywords = EXCLUDED.matched_keywords,
                        hashtags = EXCLUDED.hashtags,
                        button_count = EXCLUDED.button_count,
                        giveaway_buttons = EXCLUDED.giveaway_buttons,
                        media_type = EXCLUDED.media_type,
                        analyzed_at = CURRENT_TIMESTAMP
                ''',
                post_id,
                analysis_data.get('giveaway_score', 0),
                analysis_data.get('ad_score', 0),
                analysis_data.get('total_score', 0),
                analysis_data.get('decision', 'NEUTRAL'),
                analysis_data.get('decision_reason', ''),
                analysis_data.get('matched_keywords', []),
                analysis_data.get('hashtags', []),
                analysis_data.get('button_count', 0),
                analysis_data.get('giveaway_buttons', 0),
                analysis_data.get('media_type', '')
                )
                
                # 4. Обновляем статистику канала
                await self._update_channel_stats_simple(conn, channel_id, analysis_data.get('decision'))
                
                return post_id
                
            except Exception as e:
                print(f"Ошибка при сохранении анализа поста: {e}")
                return None
 """
    async def save_post_analysis_simple(self, analysis_data: dict, channel_id: int, original_id: int, message_text: str = ""):
        """Упрощенное сохранение анализа поста в БД"""
        async with self.pool.acquire() as conn:
            try:
                print(f"📝 Начинаю сохранение анализа поста в БД...")
                print(f"   channel_id: {channel_id}")
                print(f"   original_id: {original_id}")
                
                # 1. Проверяем, существует ли уже пост
                existing_post = await conn.fetchrow('''
                    SELECT id_post FROM posts 
                    WHERE original_id = $1 AND channel_id = $2
                ''', original_id, channel_id)
                
                post_id = None
                
                if existing_post:
                    # Пост уже существует - обновляем его
                    post_id = existing_post['id_post']
                    print(f"   Пост уже существует с ID: {post_id}")
                    
                    await conn.execute('''
                        UPDATE posts SET
                            message_text = $3,
                            filtered_message_text = $4,
                            has_media = $5,
                            has_buttons = $6,
                            end_date_gift = $7,
                            post_link = $8
                        WHERE id_post = $1
                    ''', 
                    post_id,
                    message_text[:5000] if message_text else '',
                    analysis_data.get('filtered_message_text', '')[:5000],
                    analysis_data.get('has_media', False),
                    analysis_data.get('has_buttons', False),
                    analysis_data.get('end_date'),
                    analysis_data.get('post_link', '')
                    )
                    
                else:
                    # Создаем новый пост
                    print(f"   Создаю новый пост...")
                    post_id = await conn.fetchval('''
                        INSERT INTO posts (
                            original_id, channel_id, message_text, filtered_message_text,
                            has_media, has_buttons, end_date_gift, post_link
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING id_post
                    ''', 
                    original_id,
                    channel_id,
                    message_text[:5000] if message_text else '',
                    analysis_data.get('filtered_message_text', '')[:5000],
                    analysis_data.get('has_media', False),
                    analysis_data.get('has_buttons', False),
                    analysis_data.get('end_date'),
                    analysis_data.get('post_link', '')
                    )
                    print(f"   Post создан с ID: {post_id}")
                
                # 2. Теперь сохраняем/обновляем анализ
                # Сначала проверяем, есть ли уже анализ для этого поста
                existing_analysis = await conn.fetchrow('''
                    SELECT 1 FROM post_analysis WHERE post_id = $1
                ''', post_id)
                
                if existing_analysis:
                    # Обновляем существующий анализ
                    print(f"   Обновляю существующий анализ...")
                    await conn.execute('''
                        UPDATE post_analysis SET
                            giveaway_score = $2,
                            ad_score = $3,
                            total_score = $4,
                            decision = $5,
                            decision_reason = $6,
                            matched_keywords = $7,
                            hashtags = $8,
                            button_count = $9,
                            giveaway_buttons = $10,
                            media_type = $11,
                            analyzed_at = CURRENT_TIMESTAMP,
                            forwarded = $12,
                            forwarded_to_channel = $13
                        WHERE post_id = $1
                    ''',
                    post_id,
                    analysis_data.get('giveaway_score', 0),
                    analysis_data.get('ad_score', 0),
                    analysis_data.get('total_score', 0),
                    analysis_data.get('decision', 'NEUTRAL'),
                    analysis_data.get('decision_reason', '')[:1000],
                    analysis_data.get('matched_keywords', []),
                    analysis_data.get('hashtags', []),
                    analysis_data.get('button_count', 0),
                    analysis_data.get('giveaway_buttons', 0),
                    analysis_data.get('media_type', ''),
                    analysis_data.get('forwarded', False),
                    analysis_data.get('forwarded_to_channel', '')
                    )
                else:
                    # Создаем новый анализ
                    print(f"   Создаю новый анализ...")
                    await conn.execute('''
                        INSERT INTO post_analysis (
                            post_id, giveaway_score, ad_score, total_score,
                            decision, decision_reason, matched_keywords, hashtags,
                            button_count, giveaway_buttons, media_type,
                            forwarded, forwarded_to_channel
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ''',
                    post_id,
                    analysis_data.get('giveaway_score', 0),
                    analysis_data.get('ad_score', 0),
                    analysis_data.get('total_score', 0),
                    analysis_data.get('decision', 'NEUTRAL'),
                    analysis_data.get('decision_reason', '')[:1000],
                    analysis_data.get('matched_keywords', []),
                    analysis_data.get('hashtags', []),
                    analysis_data.get('button_count', 0),
                    analysis_data.get('giveaway_buttons', 0),
                    analysis_data.get('media_type', ''),
                    analysis_data.get('forwarded', False),
                    analysis_data.get('forwarded_to_channel', '')
                    )
                
                print(f"✅ Анализ успешно сохранен в БД с ID: {post_id}")
                
                # 3. Обновляем статистику канала (если канал существует)
                channel_exists = await conn.fetchval(
                    'SELECT 1 FROM channels WHERE channel_id = $1',
                    channel_id
                )
                if channel_exists:
                    await self._update_channel_stats_simple(conn, channel_id, analysis_data.get('decision'))
                
                return post_id
                
            except Exception as e:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при сохранении анализа поста: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                return None

    async def _update_channel_stats_simple(self, conn, channel_id: int, decision: str):
        """Упрощенное обновление статистики канала"""
        try:
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
                
                if decision == 'GIVEAWAY':
                    update_query += ', giveaway_posts = giveaway_posts + 1, last_giveaway_date = CURRENT_TIMESTAMP'
                elif decision == 'AD':
                    update_query += ', ad_posts = ad_posts + 1'
                
                update_query += ' WHERE channel_id = $1'
                await conn.execute(update_query, channel_id)
                
        except Exception as e:
            print(f"Ошибка при обновлении статистики канала: {e}")

    async def mark_post_as_forwarded(self, post_id: int, forwarded_to: str = "your_channel", post_link: str = None, our_post_link: str = None):
        """Отметить пост как пересланный с сохранением ссылки на наш пост"""
        async with self.pool.acquire() as conn:
            try:
                # Обновляем запись анализа
                await conn.execute('''
                    UPDATE post_analysis 
                    SET forwarded = TRUE, 
                        forwarded_to_channel = $2,
                        analyzed_at = CURRENT_TIMESTAMP
                    WHERE post_id = $1
                ''', post_id, forwarded_to)
                
                # Если есть ссылка на оригинальный пост, обновляем в posts
                if post_link:
                    await conn.execute('''
                        UPDATE posts 
                        SET post_link = $2
                        WHERE id_post = $1
                    ''', post_id, post_link)
                
                # Если есть ссылка на наш пост, сохраняем ее
                if our_post_link:
                    await conn.execute('''
                        UPDATE posts 
                        SET our_post_link = $2
                        WHERE id_post = $1
                    ''', post_id, our_post_link)
                
                return True
                
            except Exception as e:
                print(f"Ошибка при отметке поста как пересланного: {e}")
                return False

    ##########################################################################
    # KEYWORDS METHODS (ВАЖНО!)
    ##########################################################################
    
    async def get_keywords_by_type(self, keyword_type=None):
        """Получение ключевых слов из БД"""
        async with self.pool.acquire() as conn:
            if keyword_type:
                rows = await conn.fetch('''
                    SELECT keyword, weight FROM keywords 
                    WHERE keyword_type = $1 AND is_active = TRUE
                    ORDER BY weight DESC
                ''', keyword_type)
                return {row['keyword']: row['weight'] for row in rows}
            else:
                rows = await conn.fetch('''
                    SELECT keyword, keyword_type, weight FROM keywords 
                    WHERE is_active = TRUE
                    ORDER BY keyword_type, weight DESC
                ''')
                result = {}
                for row in rows:
                    if row['keyword_type'] not in result:
                        result[row['keyword_type']] = {}
                    result[row['keyword_type']][row['keyword']] = row['weight']
                return result
    
    async def add_keyword(self, keyword: str, keyword_type: str, weight: float = 1.0):
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
    
    async def update_keyword(self, keyword: str, is_active: bool = None, weight: float = None):
        """Обновление ключевого слова"""
        async with self.pool.acquire() as conn:
            updates = []
            params = [keyword]
            
            if is_active is not None:
                updates.append(f"is_active = ${len(params) + 1}")
                params.append(is_active)
            
            if weight is not None:
                updates.append(f"weight = ${len(params) + 1}")
                params.append(weight)
            
            if updates:
                query = f"UPDATE keywords SET {', '.join(updates)} WHERE keyword = $1"
                await conn.execute(query, *params)

    ##########################################################################
    # OTHER METHODS
    ##########################################################################
    
    '''async def get_today_giveaways(self):
        """Ищем розыгрыши, которые закончатся в ближайшие 24 часа"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    p.filtered_message_text,
                    COALESCE(p.our_post_link, p.post_link) as post_link,  
                    p.end_date_gift,
                    p.original_id,
                    p.channel_id,
                    c.channel_username
                FROM posts p
                JOIN post_analysis pa ON p.id_post = pa.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                WHERE 
                    p.end_date_gift IS NOT NULL 
                    AND p.end_date_gift >= NOW() 
                    AND p.end_date_gift <= NOW() + INTERVAL '24 hours'
                    AND pa.decision = 'GIVEAWAY'
                    AND pa.forwarded = TRUE
                    AND (p.our_post_link IS NOT NULL OR p.post_link IS NOT NULL)  
                ORDER BY p.end_date_gift ASC
                LIMIT 15
            """)
            return rows
    '''
    
    async def debug_today_giveaways(self):
        """Отладочный метод для проверки условий"""
        async with self.pool.acquire() as conn:
            # Проверяем количество постов по каждому условию
            total = await conn.fetchval("SELECT COUNT(*) FROM posts WHERE end_date_gift IS NOT NULL")
            today = await conn.fetchval("SELECT COUNT(*) FROM posts WHERE DATE(end_date_gift) = CURRENT_DATE")
            giveaway = await conn.fetchval("""
                SELECT COUNT(*) FROM posts p
                JOIN post_analysis pa ON p.id_post = pa.post_id
                WHERE DATE(p.end_date_gift) = CURRENT_DATE AND pa.decision = 'GIVEAWAY'
            """)
            forwarded = await conn.fetchval("""
                SELECT COUNT(*) FROM posts p
                JOIN post_analysis pa ON p.id_post = pa.post_id
                WHERE DATE(p.end_date_gift) = CURRENT_DATE 
                AND pa.decision = 'GIVEAWAY' 
                AND pa.forwarded = TRUE
            """)
            
            print(f"Всего постов с датами: {total}")
            print(f"Постов на сегодня: {today}")
            print(f"Розыгрышей на сегодня: {giveaway}")
            print(f"Пересланных розыгрышей на сегодня: {forwarded}")
            
            # Получаем примеры постов на сегодня
            rows = await conn.fetch("""
                SELECT 
                    p.original_id,
                    p.filtered_message_text,
                    DATE(p.end_date_gift) as end_date,
                    pa.decision,
                    pa.forwarded,
                    p.our_post_link,
                    p.post_link
                FROM posts p
                LEFT JOIN post_analysis pa ON p.id_post = pa.post_id
                WHERE DATE(p.end_date_gift) = CURRENT_DATE
                LIMIT 5
            """)
            
            for row in rows:
                print(f"Пост {row['original_id']}: дата={row['end_date']}, решение={row['decision']}, forwarded={row['forwarded']}")
                print(f"  Ссылки: our={row['our_post_link']}, original={row['post_link']}")
        
    async def get_today_giveaways(self):
        """Ищем розыгрыши, которые закончатся сегодня"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    p.filtered_message_text,
                    COALESCE(p.our_post_link, p.post_link) as post_link,  
                    p.end_date_gift,
                    p.original_id,
                    p.channel_id,
                    c.channel_username
                FROM posts p
                JOIN post_analysis pa ON p.id_post = pa.post_id
                LEFT JOIN channels c ON p.channel_id = c.channel_id
                WHERE 
                    p.end_date_gift IS NOT NULL 
                    AND DATE(p.end_date_gift) = CURRENT_DATE
                    AND pa.decision = 'GIVEAWAY'
                    AND pa.forwarded = TRUE
                    AND (p.our_post_link IS NOT NULL OR p.post_link IS NOT NULL)  
                ORDER BY p.end_date_gift ASC
                LIMIT 15
            """)
            return rows
    
    async def is_post_processed(self, original_id, channel_id):
        """Проверка, был ли уже обработан пост"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT p.id_post FROM posts p
                WHERE p.original_id = $1 AND p.channel_id = $2
            ''', original_id, channel_id)
            return row is not None
    
    async def update_channel_username(self, channel_id: int, channel_username: str):
        """Обновление username канала"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE channels 
                SET channel_username = $2 
                WHERE channel_id = $1
            ''', channel_id, channel_username)
    """ async def save_post_analysis_simple(self, analysis_data: dict, channel_id: int, original_id: int, message_text: str = ""):
        async with self.pool.acquire() as conn:
            try:
                print(f"📝 Начинаю сохранение анализа поста в БД...")
                print(f"   channel_id: {channel_id}")
                print(f"   original_id: {original_id}")
                print(f"   message_text type: {type(message_text)}")
                print(f"   message_text preview: {str(message_text)[:100] if message_text else 'Empty'}")
                
                # 1. Проверяем, есть ли канал в БД, если нет - создаем
                channel_exists = await conn.fetchval(
                    'SELECT 1 FROM channels WHERE channel_id = $1',
                    channel_id
                )
                
                print(f"   Канал существует: {bool(channel_exists)}")
                
                if not channel_exists:
                    print(f"   Создаю новый канал с ID: {channel_id}")
                    await conn.execute('''
                        INSERT INTO channels (channel_id, channel_username)
                        VALUES ($1, $2)
                        ON CONFLICT (channel_id) DO NOTHING
                    ''', channel_id, f"unknown_{channel_id}")
                
                # 2. Преобразуем message_text в строку если нужно
                if message_text and not isinstance(message_text, str):
                    try:
                        message_text = str(message_text)
                        print(f"   Преобразовал message_text в строку")
                    except Exception as e:
                        print(f"   Ошибка преобразования message_text: {e}")
                        message_text = ""
                
                # 3. Подготовим данные для сохранения
                filtered_text = analysis_data.get('filtered_message_text', '')
                if filtered_text and not isinstance(filtered_text, str):
                    try:
                        filtered_text = str(filtered_text)
                    except:
                        filtered_text = ""
                
                # 4. Обработка даты
                end_date = analysis_data.get('end_date')
                end_date_timestamp = None
                
                if end_date:
                    try:
                        if isinstance(end_date, str):
                            # Пытаемся распарсить дату
                            print(f"   Парсим дату: {end_date}")
                            date_obj = datetime.strptime(end_date, '%d.%m.%Y')
                            end_date_timestamp = date_obj
                            print(f"   Дата успешно спарсена: {date_obj}")
                        else:
                            end_date_timestamp = end_date
                    except Exception as e:
                        print(f"   Ошибка парсинга даты {end_date}: {e}")
                        end_date_timestamp = None
                
                # 5. Сохраняем пост в таблицу posts
                print(f"   Сохраняю пост в таблицу posts...")
                post_id = await conn.fetchval('''
                    INSERT INTO posts (
                        original_id, channel_id, message_text, filtered_message_text,
                        has_media, has_buttons, end_date_gift, post_link
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (original_id, channel_id) 
                    DO UPDATE SET 
                        message_text = EXCLUDED.message_text,
                        filtered_message_text = EXCLUDED.filtered_message_text,
                        has_media = EXCLUDED.has_media,
                        has_buttons = EXCLUDED.has_buttons,
                        end_date_gift = EXCLUDED.end_date_gift,
                        post_link = EXCLUDED.post_link
                    RETURNING id_post
                ''', 
                original_id,
                channel_id,
                message_text[:5000] if message_text else '',
                filtered_text[:5000],
                analysis_data.get('has_media', False),
                analysis_data.get('has_buttons', False),
                end_date_timestamp,
                analysis_data.get('post_link', '')
                )
                
                print(f"   Post сохранен с ID: {post_id}")
                
                # 6. Сохраняем анализ в таблицу post_analysis
                print(f"   Сохраняю анализ в таблицу post_analysis...")
                await conn.execute('''
                    INSERT INTO post_analysis (
                        post_id, giveaway_score, ad_score, total_score,
                        decision, decision_reason, matched_keywords, hashtags,
                        button_count, giveaway_buttons, media_type
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (post_id) DO UPDATE SET
                        giveaway_score = EXCLUDED.giveaway_score,
                        ad_score = EXCLUDED.ad_score,
                        total_score = EXCLUDED.total_score,
                        decision = EXCLUDED.decision,
                        decision_reason = EXCLUDED.decision_reason,
                        matched_keywords = EXCLUDED.matched_keywords,
                        hashtags = EXCLUDED.hashtags,
                        button_count = EXCLUDED.button_count,
                        giveaway_buttons = EXCLUDED.giveaway_buttons,
                        media_type = EXCLUDED.media_type,
                        analyzed_at = CURRENT_TIMESTAMP
                ''',
                post_id,
                analysis_data.get('giveaway_score', 0),
                analysis_data.get('ad_score', 0),
                analysis_data.get('total_score', 0),
                analysis_data.get('decision', 'NEUTRAL'),
                analysis_data.get('decision_reason', '')[:1000],
                analysis_data.get('matched_keywords', []),
                analysis_data.get('hashtags', []),
                analysis_data.get('button_count', 0),
                analysis_data.get('giveaway_buttons', 0),
                analysis_data.get('media_type', '')
                )
                
                print(f"✅ Анализ успешно сохранен в БД")
                
                # 7. Обновляем статистику канала
                await self._update_channel_stats_simple(conn, channel_id, analysis_data.get('decision'))
                
                return post_id
                
            except Exception as e:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при сохранении анализа поста: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()  # Полный стектрейс
                return None
    """
    """async def _update_channel_stats_simple(self, conn, channel_id: int, decision: str):
        
        try:
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
                
                if decision == 'GIVEAWAY':
                    update_query += ', giveaway_posts = giveaway_posts + 1, last_giveaway_date = CURRENT_TIMESTAMP'
                elif decision == 'AD':
                    update_query += ', ad_posts = ad_posts + 1'
                
                update_query += ' WHERE channel_id = $1'
                await conn.execute(update_query, channel_id)
                
        except Exception as e:
            print(f"Ошибка при обновлении статистики канала: {e}")
    """
    """async def mark_post_as_forwarded(self, post_id: int, forwarded_to: str = "your_channel", post_link: str = None):
        
        async with self.pool.acquire() as conn:
            try:
                # Обновляем запись анализа
                await conn.execute('''
                    UPDATE post_analysis 
                    SET forwarded = TRUE, 
                        forwarded_to_channel = $2,
                        analyzed_at = CURRENT_TIMESTAMP
                    WHERE post_id = $1
                ''', post_id, forwarded_to)
                
                # Если есть ссылка на пост, обновляем в posts
                if post_link:
                    await conn.execute('''
                        UPDATE posts 
                        SET post_link = $2
                        WHERE id_post = $1
                    ''', post_id, post_link)
                
                return True
                
            except Exception as e:
                print(f"Ошибка при отметке поста как пересланного: {e}")
                return False
        """    
            
    async def get_recent_giveaways(self, limit: int = 10):
        """Получить последние розыгрыши"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT 
                    p.original_id,
                    p.channel_id,
                    p.message_text,
                    p.filtered_message_text,
                    pa.analyzed_at,
                    pa.decision,
                    pa.total_score,
                    c.channel_username
                FROM posts p
                JOIN post_analysis pa ON p.id_post = pa.post_id
                LEFT JOIN channels c ON p.channel_id = c.channel_id
                WHERE pa.decision = 'GIVEAWAY'
                ORDER BY pa.analyzed_at DESC
                LIMIT $1
            ''', limit)
            
            return rows
    
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
                
                if decision == 'GIVEAWAY':
                    update_query += ', giveaway_posts = giveaway_posts + 1, last_giveaway_date = CURRENT_TIMESTAMP'
                elif decision == 'AD':
                    update_query += ', ad_posts = ad_posts + 1'
                
                update_query += ' WHERE channel_id = $1'
                await conn.execute(update_query, channel_id)

    """async def is_post_processed(self, original_id, channel_id):
       
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT p.id_post FROM posts p
                WHERE p.original_id = $1 AND p.channel_id = $2
            ''', original_id, channel_id)
            return row is not None"""

    async def get_channel_stats(self, channel_id):
        """Получение статистики канала"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('''
                SELECT * FROM channel_stats 
                WHERE channel_id = $1
            ''', channel_id)

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
    
    ##########################################################################
    # KEYWORDS METHODS (ВАЖНО!)
    ##########################################################################
    
    """async def get_keywords_by_type(self, keyword_type=None):
        
        async with self.pool.acquire() as conn:
            if keyword_type:
                rows = await conn.fetch('''
                    SELECT keyword, weight FROM keywords 
                    WHERE keyword_type = $1 AND is_active = TRUE
                    ORDER BY weight DESC
                ''', keyword_type)
                return {row['keyword']: row['weight'] for row in rows}
            else:
                rows = await conn.fetch('''
                    SELECT keyword, keyword_type, weight FROM keywords 
                    WHERE is_active = TRUE
                    ORDER BY keyword_type, weight DESC
                ''')
                result = {}
                for row in rows:
                    if row['keyword_type'] not in result:
                        result[row['keyword_type']] = {}
                    result[row['keyword_type']][row['keyword']] = row['weight']
                return result"""
    
    """async def add_keyword(self, keyword: str, keyword_type: str, weight: float = 1.0):
        
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO keywords (keyword, keyword_type, weight)
                VALUES ($1, $2, $3)
                ON CONFLICT (keyword) DO UPDATE SET
                    keyword_type = EXCLUDED.keyword_type,
                    weight = EXCLUDED.weight,
                    is_active = TRUE
            ''', keyword, keyword_type, weight)"""
    
    """async def update_keyword(self, keyword: str, is_active: bool = None, weight: float = None):
       
        async with self.pool.acquire() as conn:
            updates = []
            params = [keyword]
            
            if is_active is not None:
                updates.append(f"is_active = ${len(params) + 1}")
                params.append(is_active)
            
            if weight is not None:
                updates.append(f"weight = ${len(params) + 1}")
                params.append(weight)
            
            if updates:
                query = f"UPDATE keywords SET {', '.join(updates)} WHERE keyword = $1"
                await conn.execute(query, *params)"""

    ##########################################################################
    # OTHER METHODS
    ##########################################################################
    
    '''async def get_today_giveaways(self):
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    p.filtered_message_text,
                    p.post_link,
                    p.end_date_gift,
                    p.original_id,
                    p.channel_id,
                    c.channel_username
                FROM posts p
                JOIN post_analysis pa ON p.id_post = pa.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                WHERE 
                    p.end_date_gift IS NOT NULL 
                    AND p.end_date_gift >= NOW() 
                    AND p.end_date_gift <= NOW() + INTERVAL '24 hours'
                    AND pa.decision = 'GIVEAWAY'
                    AND pa.forwarded = TRUE
                    AND p.post_link IS NOT NULL
                ORDER BY p.end_date_gift ASC
                LIMIT 15
            """)
            return rows'''
    
    """async def update_channel_username(self, channel_id: int, channel_username: str):
       
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE channels 
                SET channel_username = $2 
                WHERE channel_id = $1
            ''', channel_id, channel_username)"""
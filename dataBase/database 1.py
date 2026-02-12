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
        
        self.sheduler = AsyncIOScheduler()
        self.admin_user_id = int(AD)
        
        self.bot = bot_instance
    
    async def close(self):
        """Закрытие соединения с БД"""
        if self.pool:
            await self.pool.close()
            print("✅ Соединение с БД закрыто")
        
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("✅ Планировщик остановлен")
    
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
        
        self.sheduler.add_job(
            self.backup_database_and_send_to_admin,
            'interval',
            hours = 24,
            next_run_time=datetime.now()
        )
        self.sheduler.start()
        print("✅ Планировщик бэкапов запущен (каждые 24 часа).")
        
    async def created_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS channels (
                                   id_channels SERIAL PRIMARY KEY,
                                   channel_username VARCHAR(255) NOT NULL
                                   )''')
        
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS admins (
                                   id_adm SERIAL PRIMARY KEY,
                                   user_id BIGINT UNIQUE
                                   )''')
            
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS posts (
                                   id_post SERIAL PRIMARY KEY,
                                   original_id BIGINT UNIQUE,
                                   content_hash VARCHAR(100) NOT NULL,
                                   is_gift BOOLEAN NOT NULL
                                   )''')
            
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS forwared_posts (
                                   id_forwared_post SERIAL PRIMARY KEY,
                                   id_channels BIGINT NOT NULL,
                                   original_id BIGINT NOT NULL UNIQUE,
                                   
                                   FOREIGN KEY (id_channels) REFERENCES channels(id_channels),
                                   FOREIGN KEY (original_id) REFERENCES posts(original_id)
                               )''')
            await conn.execute('''
                               CREATE TABLE IF NOT EXISTS client_acccounts (
                                   id_accounts_client SERIAL PRIMARY KEY,
                                   id_channels BIGINT NOT NULL,
                                   original_id BIGINT NOT NULL UNIQUE,
                                   
                                   FOREIGN KEY (id_channels) REFERENCES channels(id_channels),
                                   FOREIGN KEY (original_id) REFERENCES posts(original_id)
                               )''')
            
    async def insert_initial_data(self):
        async with self.pool.acquire() as conn:
            initial_users = [
                (7957920325)                
            ]
            
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
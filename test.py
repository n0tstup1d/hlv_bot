import asyncio
from dataBase.database import Database

async def test():
    db = Database()
    result = await db.connect()
    print(f"Подключение: {result}")
    print(f"Пул: {db.pool}")
    
    if db.pool:
        admins = await db.get_all_user_ids()
        print(f"Админы: {admins}")
    
    await db.close()

asyncio.run(test())
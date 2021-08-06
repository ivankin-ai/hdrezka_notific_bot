from gino import Gino
from gino.schema import GinoSchemaVisitor
from data.config import db_user, db_pass, host

db = Gino()


# Документация
# http://gino.fantix.pro/en/latest/tutorials/tutorial.html


async def create_db():
    # print("Начали")
    await db.set_bind(f'postgresql://{db_user}:{db_pass}@{host}/gino')
    db.gino: GinoSchemaVisitor
    # await db.gino.drop_all()
    # await db.gino.create_all()
    # print('Создана бд')

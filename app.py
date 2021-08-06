import asyncio
import middlewares, handlers
from utils.db_api.database import create_db
from utils.db_api.db_commands import update_serials, check_subs
from utils.notify_admins import on_startup_notify
from utils.parser.rezka_parser import check_site
from utils.set_bot_commands import set_default_commands


# db = SQLighter('Serials.db')


async def on_startup(dispatcher):
    # # Создаёт БД
    # await create_db()

    # Устанавливаем дефолтные команды
    await set_default_commands(dispatcher)

    # Уведомляет про запуск
    await on_startup_notify(dispatcher)


async def check_homepage():
    # TODO: проверить, есть ли на сайте одинаковые сериалы
    # Ежеминутная проверка сайта на наличие новых обновлений
    await create_db()
    print("Create DB")
    while True:
        serials = check_site()
        print("На сайте найдено " + str(len(serials)) + " сериалов")
        new_serials = await update_serials(serials)

        print('новые сериалы', new_serials)
        if new_serials:
            data = await check_subs(new_serials)
            print('новые сериалы', data)
            for user_id, message in data.items():
                await dp.bot.send_message(user_id, message)
        await asyncio.sleep(60)
        pass


if __name__ == '__main__':
    from aiogram import executor
    from loader import dp

    loop = asyncio.get_event_loop()
    loop.create_task(check_homepage())
    executor.start_polling(dp, on_startup=on_startup)



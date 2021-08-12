import asyncio
from utils.db_api import models
from utils.db_api.db_commands import update_serials, check_subs
from utils.notify_admins import on_startup_notify
from utils.parser.rezka_parser import check_site
from utils.set_bot_commands import set_default_commands
import handlers


# db = SQLighter('Serials.db')


async def on_startup(dispatcher):

    # Устанавливаем дефолтные команды
    await set_default_commands(dispatcher)

    # Уведомляет про запуск
    await on_startup_notify(dispatcher)


async def check_homepage():
    # TODO: проверить, есть ли на сайте одинаковые сериалы
    # Ежеминутная проверка сайта на наличие новых обновлений
    while True:
        serials = check_site()
        new_serials = update_serials(serials)
        if new_serials:
            data = await check_subs(new_serials)
            for user_id, message in data.items():
                await dp.bot.send_message(user_id, message)
        await asyncio.sleep(5*60)


if __name__ == '__main__':
    from aiogram import executor
    from loader import dp

    loop = asyncio.get_event_loop()
    loop.create_task(check_homepage())
    executor.start_polling(dp, on_startup=on_startup)



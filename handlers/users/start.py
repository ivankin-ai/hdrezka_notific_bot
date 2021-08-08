from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart

from loader import dp
from utils.db_api.db_commands import add_new_user


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    # user_id = message.from_user.id
    # full_name = message.from_user.full_name

    user = add_new_user(types.User.get_current())
    if user:
        await message.answer(f"Привет, {message.from_user.full_name}!\n"
                             f"Для того, чтобы начать пользоваться ботом, нажмите /menu\n"
                             f"если потребуется помощь: /help")

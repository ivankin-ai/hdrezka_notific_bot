from typing import Union

from aiogram import types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import menu_keyboard as menu_kb

from loader import dp

from utils.parser.rezka_parser import search_serial

from utils.db_api.db_commands import get_subs_user, get_sub, add_subscription, del_subs, del_sub


class StateMenu(StatesGroup):
    home_menu = State()
    search = State()
    type = State()


@dp.callback_query_handler(menu_kb.menu_cd.filter(func="close"))
async def close_menu(call: CallbackQuery):
    await call.message.edit_text("До встречи!", reply_markup=None)


@dp.message_handler(Command('menu'))
async def command_menu(message: types.Message):
    await message.answer("Привет")
    await show_menu(message)


# Главное меню
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="menu"))
async def show_menu(message: Union[CallbackQuery, Message]):
    markup = menu_kb.get_menu()
    if isinstance(message, Message):
        await message.answer('Меню бота', reply_markup=markup)
    if isinstance(message, CallbackQuery):
        call = message
        await call.message.edit_text(text='Меню бота:', reply_markup=markup)


# Все уведомления вкл/выкл
# TODO: func notification sound or notification stop
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="notific"))
async def notification(call: CallbackQuery, callback_data: dict):
    await call.answer('Функция в разработке')


# Включаем поиск по имени сериала
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="search"))
async def enter_serial_name(call: CallbackQuery):
    text = "Введите название сериала:"
    await call.message.edit_reply_markup()
    await call.message.edit_text(text=text)
    await StateMenu.search.set()


# Показываем найденные сериалы и клавиатуру к ним
# Клавиатура: подписки/ новый поиск/ меню/ закрыть.
@dp.message_handler(state=StateMenu.search)
async def show_search(message: Message,
                      state: FSMContext):

    await message.answer(text="Пожалуйста подождите.")
    serial = message.text
    serials = await search_serial(name=serial)
    markup = menu_kb.get_keyboard_serials(len(serials))
    text = "Выберите один из вариантов: \n\n"
    if not len(serials):
        text = "К сожалению ничего не нашлось.\nПопробовать еще?"
    for number, film in enumerate(serials):
        number += 1
        text += f"{number}. {film['name_serial']}\n{film['info']}\n\n"
        async with state.proxy() as data:
            data[number] = film
    # Получаем клавиатуру где callback_data это порядковый номер
    await message.answer(text=text, reply_markup=markup)
    await state.reset_state(with_data=False)


# Показываем выбраный сериал и клавиатуру с выбором типа подписки
# Клавиатура:
# выбор озвучки(1,2....n)\n
# все\n последняя серия\n новый поиск; меню; закрыть
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="select"))
async def select_type_subscribe(call: CallbackQuery,
                                state: FSMContext,
                                callback_data: dict):
    number = int(callback_data['number'])
    data = await state.get_data()
    # State может прийти из меню изменения или создания подписки
    # если мы его взяли из создания, тогда берем state с ключом subscription
    # а если из изменения, то создаём новый serial из search_serial(link).
    # key = "subscription" if "subscription" in data else number
    serial = data[number]
    serial["user_id"] = call.from_user.id
    voices = serial.get("voices", [])
    markup = menu_kb.get_keyboard_type(len(voices))
    text = f"{serial['name_serial']}\n{serial['info']}\n\n"
    text += "Выберите тип подписки:\n"
    if len(voices) > 1:
        text += f"📌 1 - {len(voices)} - новые серии в выбранной озвучке\n"
    elif len(voices) == 1:
        text += f"📌 1 - новые серии в выбранной озвучке\n"
    text += "📌 Все изменения - любые изменения по выбранному сериалу\n" \
            "📌 Последняя серия - уведомления будут приходить при любых " \
            "изменениях на сайте в последней вышедшей серии " \
            "Как только выйдет новая серия, уведомления будут приходить по ней, и т.д.. \n\n"
    if voices:
        text += "Выбор по озвучке:\n"
        for num, voice in enumerate(voices):
            num += 1
            text += f"{num}. {voice}\n"

    await StateMenu.type.set()
    # Кладём в установленный State все данные по нашему сериалу:
    # Кроме type
    # {user_id, serial_name, info, voices, season, episode, link}
    state = dp.get_current().current_state()
    async with state.proxy() as data:
        data['subscription'] = serial
    await state.reset_state(with_data=False)
    await call.message.edit_text(text=text, reply_markup=markup)


# сюда прилетает вся обработка от нажатий на type
# показываем воарианты озвучек данного сериала .
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="type"))
async def set_type_subscription(call: CallbackQuery,
                                callback_data: dict):
    await StateMenu.type.set()
    state = dp.get_current().current_state()
    data = await state.get_data()
    serial = data["subscription"]
    serial["type"] = int(callback_data["cd_type"])
    num = callback_data["number"]
    voices = serial.pop("voices", None)
    if serial["type"] == 1:
        serial["voice"] = voices[num]
    print(serial)
    await add_subscription(serial)
    await state.finish()
    await call.answer(text="Подписка успешно добавлена.", show_alert=True)
    await show_menu(call)


# Показываем все подписки пользователя с клавиатурой
# в клавиатуру зашили id подписок
# Подписки 1,2,....n/ удалить все подписки/ меню, закрыть.
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="show_subs"))
async def show_subs(call: CallbackQuery):
    subs = await get_subs_user(call.from_user.id)
    # необходимо показать Имя/ info / тип/
    # Если все, то больше ничего.
    # Если по озв, то только озвучку,
    # Если по последней серии, то последнюю серию.
    text = "Ваши подписки:\n\n" if len(subs) else "У вас пока еще нет подписок"
    for num, sub in enumerate(subs):
        num += 1
        if sub["type"] == 0:
            text += f"{num}. {sub['name']}\n{sub['info']}\n{sub['type']}\n\n"
        elif sub["type"] == 1:
            text += f"{num}. {sub['name']}\n{sub['info']}\n{sub['type']}\n" \
                    f"{sub['voice']}\n\n"
        elif sub["type"] == 2:
            text += f"{num}. {sub['name']}\n{sub['info']}\n{sub['type']}\n" \
                    f"Сезон {sub['season']}, серия {sub['episode']}\n\n"
    markup = menu_kb.get_keyboard_subs(subs)

    await call.message.edit_text(text=text, reply_markup=markup)


# показываем подписку
# Изменить, Удалить/ назад, меню, закрыть
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="show_sub"))
async def show_sub(call: CallbackQuery, callback_data: dict):
    sub_id = callback_data["sub_id"]
    sub = await get_sub(sub_id)
    sub = sub[0]
    text = ""
    if sub["type"] == 0:
        text += f"{sub['serial_name']}\n{sub['info']}\n{sub['type']}\n\n"
    elif sub["type"] == 1:
        text += f"{sub['serial_name']}\n{sub['info']}\n{sub['type']}\n" \
                f"{sub['voice']}\n\n"
    elif sub["type"] == 2:
        text += f"{sub['serial_name']}\n{sub['info']}\n{sub['type']}\n" \
                f"Сезон {sub['season']}, серия {sub['episode']}\n\n"
    data_serial = search_serial(link=sub["link"])
    # Кладём в установленный State все данные по нашему сериалу:
    # Кроме type
    # {user_id, serial_name, info, voices, season, episode, link}
    await StateMenu.type.set()
    state = dp.get_current().current_state()
    async with state.proxy() as data:
        data['subscription'] = data_serial
    await state.reset_state(with_data=False)
    markup = menu_kb.get_keyboard_sub()
    await call.message.edit_text(text=text, reply_markup=markup)


# Удалить всё
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="del_all"))
async def delete_all_subs(call: CallbackQuery):
    user_id = call.from_user.id
    await del_subs(user_id)
    await show_menu(call)


# Удалить подписку
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="del_one"))
async def delete_one_sub(call: CallbackQuery, callback_data: dict):
    await del_sub(callback_data["id"])
    await show_subs(call)

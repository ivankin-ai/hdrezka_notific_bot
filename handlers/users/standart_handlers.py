from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from keyboards.inline import menu_keyboard as menu_kb
from loader import dp
from utils.db_api.db_commands import get_subs_user, get_sub, add_subscription, del_subs, del_sub, row2dict
from utils.parser.rezka_parser import search_serial, search_by_link


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
# TODO: Сделать возможность отключения звука
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

    # await message.answer(text="Пожалуйста подождите.")
    serial = message.text
    serials = await search_serial(name=serial) # [{link, name_serial, info}]
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
    # State может прийти или из меню изменения, или из создания подписки

    serial = data[number] # {link, name_serial, info}
    serial = await search_by_link(serial)
    serial["user_id"] = call.from_user.id
    sub_id = data[number].get('id', None)
    if sub_id:
        serial["id"] = sub_id
    voices = serial["voices"] # [{voices_id, title, last_episode, last_season}]
    markup = menu_kb.get_keyboard_type(len(voices))
    text = f"{serial['name_serial']}\n{serial['info']}\n\n"
    text += "Выберите тип подписки:\n"
    if len(voices) > 1:
        text += f"📌 1 - {len(voices)} - новые серии в выбранной озвучке\n"
    elif len(voices) == 1:
        text += f"📌 1 - новые серии в выбранной озвучке\n"
    text += "📌 Все изменения - любые изменения по выбранному сериалу\n\n"
            # "📌 Последняя серия - уведомления будут приходить при любых " \
            # "изменениях на сайте в последней вышедшей серии " \
            # "Как только выйдет новая серия, уведомления будут приходить по ней, и т.д.. \n\n"
    if voices:
        text += "Выбор по озвучке:\n"
        for num, voice in enumerate(voices):
            num += 1
            text += f"{num}. {voice['title']}\n"

    await StateMenu.type.set()
    # Кладём в установленный State все данные по нашему сериалу:
    # Кроме type
    # {user_id, serial_name, info, voices, link}
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
    # TODO: отработать одинаковые подписки пользователя
    await StateMenu.type.set()
    state = dp.get_current().current_state()
    data = await state.get_data()
    serial = data["subscription"]
    serial["type"] = int(callback_data["cd_type"])
    num = int(callback_data["number"]) - 1
    voices = serial.pop("voices", None)
    if serial["type"] == 1:
        serial["voice_name"] = voices[num]['title']
        serial["voice_id"] = voices[num]['voice_id']
        serial["last_season"] = voices[num]['last_season']
        serial["last_episode"] = voices[num]['last_episode']
    add_subscription(serial)
    await state.finish()
    await call.answer(text="Подписка успешно добавлена.", show_alert=True)
    await show_menu(call)


# Показываем все подписки пользователя с клавиатурой
# в клавиатуру зашили id подписок
# Подписки 1,2,....n/ удалить все подписки/ меню, закрыть.
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="show_subs"))
async def show_subs(call: CallbackQuery):
    subs = get_subs_user(call.from_user.id)
    # необходимо показать Имя/ info / тип/
    # Если все, то больше ничего.
    # Если по озв, то только озвучку,
    # Если по последней серии, то последнюю серию.
    text = "Ваши подписки:\n\n" if len(subs) else "У вас пока еще нет подписок"
    sub_type = {0: "Все обновления", 1: "По озвучке", 2: "По последней серии"}
    for num, sub in enumerate(subs):
        num += 1
        if sub["type"] == 0:
            text += f"{num}. {sub['name_serial']}\n{sub['info']}\nТип подписки: {sub_type[sub['type']]}\n\n"
        elif sub["type"] == 1:
            text += f"{num}. {sub['name_serial']}\n{sub['info']}\nТип подписки: {sub_type[sub['type']]}\n" \
                    f"{sub['voice_name']}\n\n"
        elif sub["type"] == 2:
            text += f"{num}. {sub['name_serial']}\n{sub['info']}\nТип подписки: {sub_type[sub['type']]}\n" \
                    f"Сезон {sub['last_season']}, серия {sub['last_episode']}\n\n"
    markup = menu_kb.get_keyboard_subs(subs)

    await call.message.edit_text(text=text, reply_markup=markup)


# показываем подписку
# Изменить, Удалить/ назад, меню, закрыть
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="show_sub"))
async def show_sub(call: CallbackQuery, callback_data: dict):
    sub_id = int(callback_data["sub_id"])
    sub = row2dict(get_sub(sub_id))
    text = ""
    sub_type = {0: "Все обновления", 1: "По озвучке", 2: "По последней серии"}
    if sub["type"] == 0:
        text += f"{sub['name_serial']}\n{sub['info']}\nТип подписки: {sub_type[sub['type']]}\n\n"
    elif sub["type"] == 1:
        text += f"{sub['name_serial']}\n{sub['info']}\nТип подписки: {sub_type[sub['type']]}\n" \
                f"{sub['voice_name']}\n\n"
    elif sub["type"] == 2:
        text += f"{sub['name_serial']}\n{sub['info']}\nТип подписки: {sub_type[sub['type']]}\n" \
                f"Сезон {sub['season']}, серия {sub['episode']}\n\n"
    markup = menu_kb.get_keyboard_sub(sub_id)
    await call.message.edit_text(text=text, reply_markup=markup)
    # Кладём в установленный State подписку:
    await StateMenu.search.set()
    state = dp.get_current().current_state()
    async with state.proxy() as data:
        data[0] = sub
    await state.reset_state(with_data=False)


# Удалить всё
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="del_all"))
async def delete_all_subs(call: CallbackQuery):
    user_id = call.from_user.id
    del_subs(user_id)
    await show_menu(call)


# Удалить подписку
@dp.callback_query_handler(menu_kb.menu_cd.filter(func="del_one"))
async def delete_one_sub(call: CallbackQuery, callback_data: dict):
    await del_sub(int(callback_data["sub_id"]))
    await show_subs(call)

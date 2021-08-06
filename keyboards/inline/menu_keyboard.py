from aiogram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB
from aiogram.utils.callback_data import CallbackData

menu_cd = CallbackData("menu", "func", "number", "cd_type", "sub_id")


def make_menu_cd(func="x", number=0, cd_type=1, sub_id=0):
    return menu_cd.new(func=func, number=number, cd_type=cd_type, sub_id=sub_id)


def get_menu():
    km = IKM()
    km.add(IKB('Новая подписка',
               callback_data=make_menu_cd(func="search")))
    km.insert(IKB('Показать все подписки',
                  callback_data=make_menu_cd(func="show_subs")))
    km.add(IKB(text='Вкл. уведомления',
               callback_data=make_menu_cd(func="notific", number=1)))
    km.insert(IKB(text='Выкл. уведомления',
                  callback_data=make_menu_cd(func="notific")))
    km.add(IKB(text='Закрыть',
               callback_data=make_menu_cd(func="close")))
    return km


def get_keyboard_serials(serials: int):
    """
    Получаем количество фильмов
    Возвращает кнопки
    екнопки с номерами
    Найти другой, Главная, Закрыть
    """
    km = IKM(row_width=5)
    for number in range(1, serials + 1):
        callback_data = make_menu_cd(number=number, func='select')
        km.insert(IKB(text=str(number), callback_data=callback_data))

    km.add(IKB(text='Найти другой',
               callback_data=make_menu_cd(func="search")))
    km.insert(IKB(text='Главная',
                  callback_data=make_menu_cd(func="menu")))
    km.insert(IKB(text='Закрыть',
                  callback_data=make_menu_cd(func="close")))
    return km


def get_keyboard_type(voices: int):
    km = IKM(row_width=5)
    for number in range(1, voices + 1):
        callback_data = make_menu_cd(number=number, func="type")
        km.insert(IKB(str(number), callback_data=callback_data))
    km.add(IKB("Все изменения",
               callback_data=make_menu_cd(func="type", cd_type=0)))
    km.add(IKB("Последняя серия",
               callback_data=make_menu_cd(func="type", cd_type=2)))
    km.add(IKB(text='Найти другой',
               callback_data=make_menu_cd(func="search")))
    km.insert(IKB(text='Главная',
                  callback_data=make_menu_cd(func="menu")))
    km.insert(IKB(text='Закрыть',
                  callback_data=make_menu_cd(func="close")))


    return km


def get_keyboard_subs(subs: list):
    """
    Принимает список словарей из подписок {id,name,voice,season,name}
    Возвращает клавиатуру:
    Порядковые номера их callback_data
    Удалить всё
    Главная, Закрыть
    """
    km = IKM(row_width=5)
    for number, sub in enumerate(subs):
        number += 1
        sub_id = sub["id"]
        callback_data = make_menu_cd(func="show_sub", sub_id=sub_id)
        km.insert(IKB(str(number), callback_data=callback_data))
    if len(subs):
        km.add(IKB(text='Удалить всё',
                   callback_data=make_menu_cd(func="del_all")))
    # km.add(IKB(text='Назад',
    #            callback_data=make_menu_cd(func="show_subs")))
    km.add(IKB(text='Главная',
                  callback_data=make_menu_cd(func="menu")))
    km.insert(IKB(text='Закрыть',
                  callback_data=make_menu_cd(func="close")))
    return km


def get_keyboard_sub():
    km = IKM()
    km.add(IKB(text='Изменить',
               callback_data=make_menu_cd(func="select")))
    km.insert(IKB(text='Удалить',
                  callback_data=make_menu_cd(func="del_one")))
    km.add(IKB(text='Назад',
               callback_data=make_menu_cd(func="show_subs")))
    km.insert(IKB(text='Главная',
                  callback_data=make_menu_cd(func="menu")))
    km.insert(IKB(text='Закрыть',
                  callback_data=make_menu_cd(func="close")))
    return km




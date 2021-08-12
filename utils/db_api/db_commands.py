import copy
import time

from utils.db_api.models import s
from utils.db_api.models import User, Subscriptions, Serials

import asyncio
import aiohttp
import sqlalchemy

from aiogram import types
from bs4 import BeautifulSoup
from utils.parser.rezka_parser import update_new_serials, search_serial, search_by_link
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, or_



def rows2list(rows) -> list:
    """ Принимает и отдает значения только одного столбца"""
    rows_list = list()
    if rows:
        for row in rows:
            rows_list.append(row[0])
    return rows_list


def row2dict(row) -> dict:
    """принимает объект строки, отдаёт словарь {column_name: value,...}"""
    d = dict()
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)
    return d


def rows2dict_in_list(rows) -> list:
    """Принимает список объектов строк
    Возвращает список словарей [{columnName: value, ...}, {...},...]"""
    rows_list = list()
    for row in rows:
        rows_list.append(row2dict(row))
    return rows_list


# Обработка users
def get_user(user_id: int) -> User:
    """Возвращает объект User по user_id"""
    user = s.query(User).filter(User.user_id == user_id).first()
    return user


def add_new_user(user: types.User.get_current(), status_sub=1, notification=True) -> User:
    old_user = get_user(user.id)
    if old_user:
        return old_user
    new_user = User()
    new_user.user_id = user.id
    new_user.username = user.username
    new_user.fullname = user.full_name
    new_user.notification = notification
    new_user.status_sub = status_sub
    s.add(new_user)
    s.commit()
    return new_user


# Обновление статуса пользователя
def update_status(user_id, status_sub):
    user = get_user(user_id)
    user.status_sub = status_sub
    s.commit()


# Обновление статуса уведомлений
def change_notification(user_id, notification):
    user = get_user(user_id)
    user.notification = notification
    s.commit()


# Обработка serials
def update_serials(serials) -> list:
    """Принимает сериалы с главной страницы, получаем хеш из БД
    сравниваем и получаем новые сериалы, записываем их в БД
    Возвращаем новые сериалы
    """
    str_hash_db = rows2list(s.query(Serials.str_hash).all())
    new_serials = update_new_serials(serials, str_hash_db)
    if len(new_serials):
        serials4db = copy.deepcopy(new_serials)
        for serial in serials4db:
            del serial["data_site"]
        serials4db = [(Serials(**serial)) for serial in serials4db]
        s.add_all(serials4db)
        s.commit()
        return new_serials


async def compar_all(sub, new_serials: list, session, s):
    user_id = sub["user_id"]
    message = str()
    for serial in new_serials:
        if serial["link"] == sub["link"]:
            message += f"Обновление в сериале {sub['name_serial']}\n{serial['data_site']}\n\n"
    if len(message):
        return {"user_id": user_id, "message": message}


async def compar_voice(sub, new_serials, session, s: sqlalchemy.orm.Session):
    user_id = sub["user_id"]
    message = str()
    for serial in new_serials:
        if serial["link"] == sub["link"]:
            url = sub["link"] + f"#t:{sub['voice_id']}-s:1-e:1"
            async with session.get(url=url, cookies={"1": "1"}) as r:
                html = await r.text()
                soup = BeautifulSoup(html, 'lxml')
                last = soup.findAll("li", {"class": "b-simple_episode__item"})[-1]
                last_episode = last["data-episode_id"]
                last_season = last["data-season_id"]
                if int(last_season) > sub["last_season"] or \
                       int (last_episode) > sub['last_episode']:
                    message += f"Обновление в сериале {sub['name_serial']}\nОзвучка: {sub['voice_name']}\n" \
                               f"Сезон: {last_season}, серия: {last_episode}.\n\n"
                    sub['last_episode'] = last_episode
                    sub['last_season'] = last_season
                    s.commit()

    if len(message):
        return {"user_id": user_id, "message": message}


async def compar_last_ep(sub, new_serials, session, s: sqlalchemy.orm.Session):
    # TODO: функция не реализована. Неправильная логика
    #  Сделать подписку по последней серии.
    user_id = sub['user_id']
    message = str()
    for serial in new_serials:
        if sub['name_serial'] == serial["name_serial"]:
            serial = await search_by_link(serial, session)
            if serial["last_season"] > sub['last_season'] or \
                    serial["last_episode"] > sub['last_episode']:
                sub['last_season'] = serial["last_season"]
                sub['last_episode'] = serial["last_episode"]
                sub['voice_name'] = serial['last_voice']
            elif serial['last_voice'] != sub['voice_name']:
                sub['voice_name'] = serial["last_voice"]
            s.commit()
            message += f"Обновление в сериале {sub['name_serial']}\nОзвучка: {sub['voice_name']}\n" \
                       f"Сезон: {sub['last_season']}, серия: {sub['last_episode']}.\n\n"
    if len(message):
        return {"user_id": user_id, "message": message}


# возвращает словарь key=user_id, value=message
async def check_subs(new_serials: list) -> dict:
    """примниает на вход новые сериалы
    срвавнивает с подписками, перезаписывает последнюю серию
    возвращает словарь key=user_id, value=message"""
    messages = dict()
    subs = s.query(Subscriptions).\
        filter(or_(Subscriptions.link == serial["link"] for serial in new_serials)).all()
    subs = rows2dict_in_list(subs)
    # TODO: Сделать быстрее???
    tasks = []
    sub_filter = {
        0: compar_all,
        1: compar_voice,
        2: compar_last_ep
    }
    async with aiohttp.ClientSession() as session:
        for sub in subs:
            current_func = sub_filter[sub["type"]]
            task = asyncio.create_task(current_func(sub, new_serials, session, s))
            tasks.append(task)
        messages_data = await asyncio.gather(*tasks)
    for message_data in messages_data:
        user_id = message_data["user_id"]
        message = message_data["message"]
        if messages.get(user_id):
            messages[user_id] += message
        else:
            messages[user_id] = message
    return messages


# Обработка subscriptions
# Добавляем подписку
def add_subscription(serial: dict):
    sub_id = serial.pop("id", None)
    if sub_id:
        sub = get_sub(sub_id)
        sub.update(sub, **serial)
    else:
        sub = Subscriptions()
        sub.update(sub, **serial)
        s.add(sub)
    s.commit()


# Получаем подписку по id
def get_sub(sub_id):
    sub = s.query(Subscriptions).filter(Subscriptions.id == sub_id).first()
    return sub


# Получаем подписки по user_id
def get_subs_user(user_id) -> list:
    subs_user = s.query(Subscriptions).filter(Subscriptions.user_id == user_id).all()
    subs_user = rows2dict_in_list(subs_user)
    return subs_user


# Удалить все подписки пользователя
def del_subs(user_id):
    try:
        s.query(Subscriptions).filter(Subscriptions.user_id == user_id).delete(synchronize_session=False)
        s.commit()
        return True
    except:
        return False


async def del_sub(sub_id):
    try:
        s.query(Subscriptions).filter(Subscriptions.id == sub_id).delete(synchronize_session=False)
        s.commit()
        return True
    except:
        return False

# TODO: сделать обработку донатов

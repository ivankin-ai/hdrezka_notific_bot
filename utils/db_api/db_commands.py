from utils.db_api.models import User, Subscriptions, Serials, Donats
from utils.db_api.database import db
from utils.parser.rezka_parser import update_new_serials


def rows2dict_in_list(rows) -> list:
    rows_list = list()
    for row in rows:
        d = dict()
        for column in row.__table__.columns:
            d[column] = getattr(row, column.name)
        rows_list.append(d)
    # if len(rows_list):
    #     return rows_list
    # for row in rows:
    #     d = dict()
    #     for name, value in row.items():
    #         d[name] = value
    #     rows_list.append(d)
    # if len(rows_list):
    print(rows_list)
    return rows_list


def rows2list(rows) -> list:
    """ Принимает и отдает значения только одного столбца"""
    rows_list = list()
    for row in rows:
        rows_list.append(row[0])
    return rows_list


# Обработка users
async def get_user(user_id: int) -> User:
    user = await User.query.where(User.user_id == user_id).gino.first()
    return user


async def add_new_user(user, status_sub=1, notification=True) -> User:
    # user = types.User.get_current()
    old_user = await get_user(user.id)
    if old_user:
        return old_user
    new_user = User()
    new_user.user_id = user.id
    new_user.username = user.username
    new_user.fullname = user.full_name
    new_user.notification = notification
    new_user.status_sub = status_sub
    print(
        new_user.user_id,
        new_user.username,
        new_user.fullname,
        new_user.notification,
        new_user.status_sub, sep="\n"
    )
    await new_user.create()
    return new_user


# Обновление статуса пользователя
async def update_status(user_id, status_sub):
    user = await get_user(user_id)
    await user.update(status_sub=status_sub).apply()


# Обновление статуса уведомлений
async def change_notification(user_id, notification):
    user = await get_user(user_id)
    await user.update(notification=notification).apply()


# Обработка serials
async def update_serials(serials) -> list:
    """Принимает сериалы с главной страницы, получаем хеш из БД
    сравниваем и получаем новые сериалы, записываем их в БД
    Возвращаем новые сериалы
    """

    str_hash_db = await Serials.select("str_hash").gino.all()
    print(f"В БД сейчас фильмов: {len(str_hash_db)}")
    str_hash_db = rows2list(str_hash_db)
    new_serials = update_new_serials(serials, str_hash_db)
    print(f"найдено {len(new_serials)} новых сериалов.")
    if len(new_serials):
        for serial in new_serials:
            print(serial)
    if len(new_serials):
        await Serials.insert().gino.all(new_serials)
        return new_serials


# возвращает словарь key=user_id, value=message
async def check_subs(new_serials: list) -> dict:
    """примниает на вход новые сериалы
    срвавнивает с подписками, перезаписывает последнюю серию
    возвращает словарь key=user_id, value=message"""
    messages = dict()
    for serial in new_serials:
        subs = await Subscriptions.query.where(
            Subscriptions.name_serial == serial["name_serial"]
        ).gino.all()
        print("подписки из вышедших", subs)
        # TODO: Перевести в список словарей значения из таблицы
        for sub in subs:
            message = str()
            user_id = sub[1]
            message += f"Обновление в сериале {sub[2]}\n" \
                       f"Озвучка: {sub[4]}\n" \
                       f"Сезон {sub[5]}. Серия {sub[6]}\n\n"
            sub_filter = {
                0: "Фильтр: все уведомления\n"+message,
                1: "Фильтр: по озвучке\n"+message,
                2: "Фильтр: послдняя серия\n"+message
            }
            # все уведомления:
            message += sub_filter[0] if sub[3] == 0 else ''
            if sub[3] == 1 and sub[4] == serial["voice"]:
                # озвучка
                message += sub_filter[1]

            elif sub[5] > serial["season"] or (sub[5] == serial["season"] and sub[6]>serial["episode"]):
                # Последняя серия
                await update_sub_last_serials(sub[0], sub[6], sub[5])
                message += sub_filter[2]
            if messages.get(user_id, None):
                messages[user_id] += message
            else:
                messages[user_id] = message
    return messages


# Обработка subscriptions
# Добавляем подписку
async def add_subscription(serial: dict):
    sub_id = serial.pop("id", None)
    if sub_id:
        await Subscriptions.update(serial).where(Subscriptions.id == sub_id)
    else:
        await Subscriptions.insert().gino.all(serial)


# Записывает последнюю вышедшую серию в подписку юзера с заданным id
async def update_sub_last_serials(sub_id, episode, season=None):
    if season:
        await Subscriptions.update(season=season,
                                   episode=episode
                                   ).where(Subscriptions.id == sub_id).apply()


# Получаем подписку по id
async def get_sub(sub_id) -> list:
    sub = Subscriptions.query.where(Subscriptions.id == sub_id).gino.first()
    sub = rows2dict_in_list(sub)
    return sub


# Получаем подписки по user_id
async def get_subs_user(user_id) -> list:
    # subs_user = await Subscriptions.query.where(
    #     Subscriptions.user_id == user_id
    # ).gino.all()
    # subs_user = await Subscriptions.query.where(
    #     Subscriptions.user_id == user_id
    # ).first()
    subs_user = []
    user = await User.query.where(User.user_id == user_id)
    user = user.gino.first().to_dict()
    print(type(user))
    print(user)
    print(type(subs_user))
    print(list(subs_user))
    for sub in subs_user:
        print(type(sub))
        print(sub)
        for f in sub:
            print(f, sep="  ")
        print()
    print(subs_user)
    subs_user = rows2dict_in_list(subs_user)
    # if subs_user:
    return subs_user


async def del_subs(user_id):
    await Subscriptions.delete.where(
        Subscriptions.user_id == user_id).gino.status()


async def del_sub(sub_id):
    await Subscriptions.delete.where(
        Subscriptions.id == sub_id).gino.status()

# TODO: сделать обработку донатов

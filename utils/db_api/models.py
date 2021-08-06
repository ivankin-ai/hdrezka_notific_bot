from sqlalchemy import Column, Integer, BigInteger, String, Sequence, Boolean, TIMESTAMP
from sqlalchemy import sql
from utils.db_api.database import db


class User(db.Model):
    __tablename__ = 'users'
    query: sql.Select

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
    user_id = Column(BigInteger)
    username = Column(String(200))
    fullname = Column(String(200))
    notification = Column(Boolean, default=True)
    # 123: Admins
    # 0: Block
    # 1: Standard
    # 2: Premium
    # ????: Friends
    status_sub = Column(Integer, default='1')


class Serials(db.Model):
    __tablename__ = 'serials'
    # query: sql.Select

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
    name_serial = Column(String(100))
    voice = Column(String(50))
    season = Column(Integer)
    episode = Column(Integer)
    link = Column(String(200))
    str_hash = Column(String(32))


class Subscriptions(db.Model):
    __tablename__ = 'subscriptions'
    query: sql.Select

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
    user_id = Column(BigInteger)
    name_serial = Column(String(100))
    info = Column(String(100))
    type = Column(Integer, default="0")
    # 0: Уведомления обо всех обновлениях по сериалу
    # 1: Уведомления о выходе определённой озвучки
    # 2: Уведомление о последней вышедшей серии
    voice = Column(String(50))
    season = Column(Integer)
    episode = Column(Integer)
    link = Column(String(200))


class Donats(db.Model):
    __tablename__ = 'donats'
    query: sql.Select

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
    user_id = Column(BigInteger)
    donat_time = Column(TIMESTAMP)
    amount = Column(Integer)
    email = Column(String(200))
    successful = Column(Boolean, default=False)

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, TIMESTAMP, create_engine
from sqlalchemy.ext.declarative import declarative_base

from data.config import db_user, db_pass, host, db_name


engine = create_engine(f'postgresql://{db_user}:{db_pass}@{host}/{db_name}', echo=True)
Base = declarative_base(bind=engine)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
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

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class Serials(Base):
    __tablename__ = 'serials'

    id = Column(Integer, primary_key=True)
    name_serial = Column(String(100))
    link = Column(String)
    str_hash = Column(String)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class Subscriptions(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    name_serial = Column(String(100))
    type = Column(Integer, default="0")
    # 0: Уведомления обо всех обновлениях по сериалу
    # 1: Уведомления о выходе определённой озвучки
    # 2: Уведомление о последней вышедшей серии
    voice_id = Column(Integer)
    voice_name = Column(String)
    last_season = Column(Integer)
    last_episode = Column(Integer)
    # voices_data = Column(JSON) #####??????????????????
    info = Column(String(100))
    link = Column(String(200))

    def update(self, sub, **kwargs):
        for key, value in kwargs.items():
            if hasattr(sub, key):
                setattr(sub, key, value)


class Donats(Base):
    __tablename__ = 'donats'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    donat_time = Column(TIMESTAMP)
    amount = Column(Integer)
    email = Column(String(200))
    successful = Column(Boolean, default=False)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


Base.metadata.create_all(engine)

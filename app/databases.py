import json
import requests

from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///database.sqlite', echo=True)  # создание базы
Base = declarative_base()  # создание базового класса


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String, nullable=False)
    password = Column(String, nullable=False)
    default_parser_num = Column(Integer, default=-1)


class Templates(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.id'))
    # столбцы в файле и порядковый номер шаблона начинаются с 1
    number = Column(Integer, default=1)
    article_column_number = Column(Integer, default=1)
    producer_column_number = Column(Integer, default=1)


class AuthData(Base):
    __tablename__ = "auth_datas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    website_name = Column(String, nullable=False)
    login = Column(String, nullable=False)
    password = Column(String, nullable=False)
    # Токен полученный от сайта - используется например на сайте ком транс
    site_token = Column(String, nullable=True, default=None)
    # ID пользователя на конкретном сайте - например на сайте авто питер
    site_id = Column(String, nullable=True, default=None)


class ProducerSynonyms(Base):
    __tablename__ = "producers_synonyms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    all_names = Column(String, nullable=False)


class UserParsers(Base):
    __tablename__ = "users_parsers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    parsers_id_list = Column(String, nullable=False)  # список id парсеров (разделитель - ";"), используемых user


class ParserInfo(Base):
    __tablename__ = "parsers_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parser_name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    parser_site_done = Column(Boolean, default=False)
    parser_api_done = Column(Boolean, default=False)

# создание всех описанных таблиц
# Base.metadata.create_all(engine)


class DatabaseActions:
    def __init__(self):
        self.engine = create_engine('sqlite:///database.sqlite', echo=True)
        # создание сессии
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def create_new_user(self, login: str, password: str) -> bool:
        if len(self.session.query(User).filter(and_(User.login == login, User.password == password)).all()) > 0:
            return False
        self.session.add(User(login=login, password=password))
        self.session.commit()
        return True

    def get_user_id(self, login: str, password: str) -> int | Column[int]:
        user_result = self.session.query(User).filter_by(login=login, password=password).one_or_none()
        if user_result is None:
            return -1
        return user_result.id

    def add_new_site(self, user_id: int, web_site: str, login: str, password: str) -> bool:
        if len(self.session.query(AuthData).filter(
                and_(AuthData.user_id == user_id, AuthData.website_name == web_site)).all()) > 0:
            return False
        self.session.add(AuthData(user_id=user_id, website_name=web_site, login=login,
                                  password=password))
        self.session.commit()
        return True

    # заполнение таблицы бд с синонимами автомобильных брендов
    def filling_synonyms_database(self):
        for brand_id in range(1, 2629):
            url = (f"https://olimpgroup.auto-vision.ru/api/v1/brands/{brand_id}/"
                   f"?token=здесь должен быть токен")
            resp = json.loads(requests.get(url, verify=False).content)
            self.session.add(ProducerSynonyms(name=resp["result"][0]["brandName"],
                                              all_names="; ".join(resp["result"][0]["brandAllNames"])))
        self.session.commit()
        print("Синонимы по всем брендам скачаны с помощью стороннего api успешно")


if __name__ == "__main__":
    bd_act = DatabaseActions()
    # print(bd_act.get_user_id(login="admin", password="admin_password"))
    # print(bd_act.add_new_site(bd_act.get_user_id(), ""))

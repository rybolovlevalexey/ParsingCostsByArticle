import json
from typing import Dict

import requests

from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, and_, or_, select, update, insert
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

engine = create_engine('sqlite:///database.sqlite', echo=False)  # создание базы
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
    parser_name = Column(String, unique=True, nullable=False)
    base_url = Column(String, nullable=False)
    parser_site_done = Column(Boolean, default=False)
    parser_api_done = Column(Boolean, default=False)

    def to_dict(self) -> dict[str, Column[str] | Column[bool]]:
        return {
            "parser_id": self.id,
            "parser_name": self.parser_name,
            "base_url": self.base_url,
            "parser_site_done": self.parser_site_done,
            "parser_api_done": self.parser_api_done
        }


# создание всех описанных таблиц
# Base.metadata.create_all(engine)


class DatabaseActions:
    def __init__(self):
        self.engine = create_engine('sqlite:///database.sqlite', echo=True)
        # создание сессии
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    # создание нового пользователя с введёнными логином и паролем
    def create_new_user(self, login: str, password: str) -> bool:
        if len(self.session.query(User).filter(and_(User.login == login, User.password == password)).all()) > 0:
            return False
        self.session.add(User(login=login, password=password))
        self.session.commit()
        return True

    # получение списка словарей с информацией о каждом парсере;
    # ключи словаря: имя парсера, реализована обработка сайта, реализована работа с api
    def get_parsers_names(self) -> list[dict[str: str | bool | Column[str] | Column[bool]]]:
        output_result: list[dict[str: str | bool]] = list()
        with Session(self.engine) as session:
            result = session.query(ParserInfo).all()
            for elem in result:
                output_result.append(elem.to_dict())
        return output_result

    # получение id пользователя по переданным логину и паролю, если логин и пароль неверные будет получено -1
    def get_user_id(self, login: str, password: str) -> int | Column[int]:
        user_result = self.session.query(User).filter_by(login=login, password=password).one_or_none()
        if user_result is None:
            return -1
        return user_result.id

    # добавление нового сайта для конкретного пользователя, с необходимыми для авторизации на этом сайте данными
    def add_new_site(self, user_id: int, web_site: str, login: str, password: str) -> bool:
        if len(self.session.query(AuthData).filter(
                and_(AuthData.user_id == user_id, AuthData.website_name == web_site)).all()) > 0:
            return False
        self.session.add(AuthData(user_id=user_id, website_name=web_site, login=login,
                                  password=password))
        self.session.commit()
        return True

    # получение id парсера по его имени, если такого парсера нет - будет получен -1
    def get_parser_id_by_name(self, parser_name: str) -> int:
        with Session(self.engine) as session:
            query = select(ParserInfo.id).where(ParserInfo.parser_name == parser_name)
            parser_id = session.execute(query).scalar_one_or_none()
            if parser_id is None:
                return -1
            return parser_id

    # Установка парсеров по умолчанию для конкретного пользователя.
    # Возвращает список id парсеров, которых не существует.
    # Если возвращает пустой список, то вся переданная информация успешно сохранена
    def set_default_parsers(self, user_id: int, parsers_id_final: list[int]) -> list[int]:
        bad_ids: list[int] = list()  # Список с плохими id парсеров, т.е. парсера с таким id не существует

        with Session(self.engine) as session:
            # проверка списка с id парсеров
            for parser_id in parsers_id_final:
                parsers_count = session.query(ParserInfo).filter(ParserInfo.id == parser_id).count()
                if parsers_count == 0:
                    bad_ids.append(parser_id)

            # создание строки с id пасеров по умолчанию только тех, которые прошли проверку на существование
            st_id_parsers = ""
            for parser_id in parsers_id_final:
                if parser_id not in bad_ids:
                    st_id_parsers += str(parser_id) + ";"

            # если о пользователе уже есть инфа с его парсерами по умолчанию, тогда update
            if session.query(UserParsers).filter(UserParsers.user_id == user_id).count() > 0:
                query = update(UserParsers).where(UserParsers.user_id == user_id).values(parsers_id_list=st_id_parsers)
            # иначе insert - создание новой записи
            else:
                query = insert(UserParsers).values(user_id=user_id, parsers_id_list=st_id_parsers)
            session.execute(query)
            session.commit()

        return bad_ids

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
    # print(bd_act.get_parser_id_by_name("track_motors"))
    # print(bd_act.set_default_parsers(1, [1, 2, 3]))
    from pprint import pprint
    pprint(bd_act.get_parsers_names())

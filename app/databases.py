from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


engine = create_engine('sqlite:///parsing_info.sqlite', echo=True)  # создание базы
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


class ProducerSynonyms(Base):
    __tablename__ = "producers_synonyms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    all_names = Column(String, nullable=False)


Base.metadata.create_all(engine)


class DatabaseActions:
    def __init__(self):
        self.engine = create_engine('sqlite:///parsing_info.sqlite', echo=True)
        # создание сессии
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def create_new_user(self, login, password):
        pass
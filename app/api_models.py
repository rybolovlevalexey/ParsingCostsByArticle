from pydantic import BaseModel
from sqladmin import ModelView
from databases import User


class NewUser(BaseModel):
    login: str
    password: str


class WebSiteData(BaseModel):
    site_url: str
    login: str
    password: str


class ParsingInfo(BaseModel):
    article: str
    producer: str


class DefaultParsers(BaseModel):
    parsers_ids: list[str | int]
    parsers_names: list[str]


# модель данных для админки, отображаются id и логин пользователя
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.login]

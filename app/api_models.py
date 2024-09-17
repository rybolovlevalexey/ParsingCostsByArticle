from pydantic import BaseModel


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

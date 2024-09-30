# ParsingCostsByArticle

Проект по парсингу информации с сайтов поставщиков автомобильных деталей на основе переданной информации об артикуле и производителе товара. Данная информация передаётся в api в формате json или excel файла после прохождения аутентификации конкретным пользователем. Для каждого пользователя хранится информация, которая используется при запуске парсеров с настройками по умолчанию. 

### Использованные технологии:
#### Парсинг - requests, selenium
#### API - FastApi, pydantic, sqladmin(создание панели администратора)
#### DataBase - sqlalchemy, sqlite, alembic
#### Тестирование - pytests

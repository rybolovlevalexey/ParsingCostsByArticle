import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import pickle
import os
from pprint import pprint
from requests.auth import HTTPBasicAuth
from dataclasses import dataclass
import time
import json

"""Может быть когда-нибудь это всё пригодится"""


@dataclass
class InfoRequest:
    """Планировалось, что тут будет храниться вся необходимая информация"""
    auth_url = "https://www.comtt.ru/login.php"
    search_url = "https://www.comtt.ru/search.php"
    # search_url_v2 = "https://www.comtt.ru/k/a/example/ws_search/search.php"
    search_url_v2 = "https://www.comtt.ru/k/t/t.php"
    with open("комтранс_авторизация.txt", "r") as auth_data_file:
        username_omega = auth_data_file.readline().strip()
        password_omega = auth_data_file.readline().strip()
        auth_data = {"username": username_omega,
                     "password": password_omega}
        auth_data_v2 = {"login": username_omega,
                        "pass": password_omega}
    user_agent = UserAgent().random
    waiting_time = 10


class ParsingWithRequests:
    """Авторизация сессии, сохранение и выгрузка информации о сессии, а также парсинг с помощью requests"""
    session_file = 'session.pkl'

    def save_session(self):
        with open(self.session_file, 'wb') as file:
            cookies_info = list({"domain": key.domain, "name": key.name,
                                 "path": key.path, "value": key.value}
                                for key in self.cur_session.cookies)
            pickle.dump({
                "cookies": cookies_info,
                "headers": self.cur_session.headers,
            }, file)
        print("Выполнено сохранение информации о текущей сессии")

    def load_session_from_file(self):
        self.cur_session = requests.Session()
        with open(self.session_file, 'rb') as file:
            data = pickle.load(file)
            for cook in data["cookies"]:
                self.cur_session.cookies.set(**cook)
            self.cur_session.headers.update(data["headers"])
        print("Выполнена выгрузка информации о прошедшей сессии в текущую")

    @staticmethod
    def is_logged_in(check_session) -> bool:
        resp = check_session.get(InfoRequest.search_url,
                                 headers={"User-Agent": InfoRequest.user_agent})
        soup = BeautifulSoup(resp.content, "html.parser")
        if ("Внимание! Вы не авторизованы!" in
                list(elem.text.strip() for elem in soup.find_all("p"))):
            return False
        return resp.status_code == 200

    def exists_session_info(self) -> bool:
        return os.path.exists(self.session_file)

    def session_ready_without_files(self):
        self.cur_session = requests.Session()
        print("Начата авторизация")
        cur_session_resp = self.cur_session.post(InfoRequest.auth_url,
                                                 data=InfoRequest.auth_data_v2,
                                                 headers={"User-Agent": InfoRequest.user_agent})
        print(BeautifulSoup(cur_session_resp.content, "html.parser").prettify())
        print("Создана новая сессия и выполнена её авторизация")

    def session_ready_to_work(self):
        if self.cur_session is requests.Session and self.cur_session != requests.Session():
            if self.is_logged_in(self.cur_session):
                print("Текущая сессия авторизована")
                return True
        else:
            if self.cur_session is not requests.Session:
                self.cur_session = requests.Session()
                print("Создана новая пустая сессия")
            elif self.cur_session == requests.Session():
                print("Сессия на данный момент является пустой")

        if self.exists_session_info():
            self.load_session_from_file()
            print("Найден файл с инфой о сессии")
        if self.is_logged_in(self.cur_session):
            print("Из найденного файла о сессии получены актуальные данные")
            return True

        cur_session_resp = self.cur_session.post(InfoRequest.auth_url,
                                                 data=InfoRequest.auth_data_v2)
        if cur_session_resp.status_code == 200:
            if "ОМЕГА ТРАК ООО" in cur_session_resp.text:
                print("Создана новая сессия и выполнена её авторизация")
                self.save_session()
                print("Информация об этой сессии перезаписана в файл")
            else:
                print("Создана новая сессия, но НЕ выполнена её авторизация")
            return True
        print("Создана новая сессия, но произошла ошибка при авторизации")
        return False

    def search_product_by_article(self, article: str):
        search_response = self.cur_session.get(InfoRequest.search_url, params={"fnd": article},
                                               headers={"User-Agent": InfoRequest.user_agent},
                                               stream=True)
        time.sleep(20)
        soup = BeautifulSoup(search_response.content, "html.parser")
        print(soup.prettify())
        print(soup.find_all("tbody")[1])

    def search_product_by_article_v2(self, article: str):
        search_response = self.cur_session.post(InfoRequest.search_url_v2,
                                                data={'search': article},
                                                headers={"User-Agent": InfoRequest.user_agent,
                                                         "Content-Type":
                                                             "application/x-www-form-urlencoded"})
        soup = BeautifulSoup(search_response.content, "html.parser")
        print(soup.prettify())
        print("-------------------")
        # print(soup.find_all("tbody")[1])
        print(search_response.content)

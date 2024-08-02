import fake_useragent
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

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def func_timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_result = func(*args, **kwargs)
        end_time = time.time()
        result_time = end_time - start_time
        print(f"Время выполнения запроса {result_time:.4f} секунд")
        return func_result
    return wrapper


class BaseParser:
    session_dir = "all_sessions"

    @staticmethod
    def auth_selenium(driver, authorization_dict: dict[str, str]):
        """Метод для выполнения авторизации на сайте
        :param driver: хром-драйвер, для которого необходимо выполнить авторизацию
        :param authorization_dict: авторизационная информация (логин, пароль) - порядок важен
            ключ - название поля для ввода логина/пароля на форме
            значение - логин/пароль для данного пользователя"""
        # Поиск и заполнение полей для ввода логина и пароля
        username_field = driver.find_element(By.NAME, list(authorization_dict.keys())[0])
        password_field = driver.find_element(By.NAME, list(authorization_dict.keys())[1])
        print("найдены поля логин и пароль")

        username_field.send_keys(list(authorization_dict.values())[0])
        password_field.send_keys(list(authorization_dict.values())[1])
        password_field.send_keys(Keys.RETURN)
        print("введены данные и нажат enter")
        return driver

    @staticmethod
    def load_selenium(driver, parser_name):
        """Метод для выгрузки информации о сессии с целью не повторять
         заново процесс авторизации, если он уже ранее был произведён"""
        driver.delete_all_cookies()
        with open(os.path.join(BaseParser.session_dir, parser_name + ".pkl"), "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        return driver

    @staticmethod
    def save_selenium(driver, parser_name):
        """Метод по сохранению/обновлению информации о текущей сессии
        для дальнейшего её использования без повторной авторизации"""
        cookies = driver.get_cookies()
        with open(os.path.join(BaseParser.session_dir, parser_name + ".pkl"), "wb") as file:
            pickle.dump(cookies, file)


class ParserKomTrans(BaseParser):
    parser_name = "kom_trans"

    def __init__(self):
        self.cur_session = requests.Session()
        auth_data = json.load(open("authorization.json", "r"))
        self._authorization_dict = {"login": auth_data["kom_trans"]["login"],
                                    "pass": auth_data["kom_trans"]["password"]}
        self.auth_url = "https://www.comtt.ru/login.php"
        self.search_url = "https://www.comtt.ru/search.php"
        self.waiting_time = 15

    @func_timer
    def parsing_article(self, article: str):
        chrome_options = Options()
        chrome_options.add_argument(
            "--headless")  # Запуск браузера в фоновом режиме (без графического интерфейса)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # driver.implicitly_wait(10)
        print("До блока try нет никаких ошибок")

        # Открытие страницы авторизации
        driver.get(self.auth_url)
        print("страница авторизации открыта успешно")

        if os.path.exists(os.path.join(BaseParser.session_dir, self.parser_name + ".pkl")):
            driver = self.load_selenium(driver, self.parser_name)
            print("В драйвер подгружена информация об актуальной сессии")
        else:
            driver = self.auth_selenium(driver, self._authorization_dict)
            self.save_selenium(driver, self.parser_name)
            print("Информация о сессии сохранена в файл")

        # Переход к защищенной странице
        driver.get(self.search_url + f"?fnd={article}")
        print("выполнение поиска по артикулу")
        # wait = WebDriverWait(driver, 10)  # ожидание до 10 секунд
        # wait.until_not(EC.visibility_of_element_located((
        #     By.XPATH, "//h3[text()='Выполняется расширенный поиск, результаты будут отображены.']")))
        time.sleep(self.waiting_time)

        if (driver.find_element(By.XPATH, "//font[@color='red']") and
                "Внимание! Вы не авторизованы!" in
                driver.find_element(By.XPATH, "//font[@color='red']").text.strip()):
            print("Текущая сессия не зарегистрирована")
            driver = self.auth_selenium(driver, self._authorization_dict)
            driver.get(self.search_url + f"?fnd={article}")
            print("выполнение поиска по артикулу после повторной регистрации")
            time.sleep(self.waiting_time)
            # wait = WebDriverWait(driver, 10)  # ожидание до 10 секунд
            # wait.until_not(EC.visibility_of_element_located((
            #     By.XPATH, "//h3[text()='Выполняется расширенный поиск, результаты будут отображены.']")))
            self.save_selenium(driver, self.parser_name)
            print("обновление информации о сессии")

        # Парсинг содержимого защищенной страницы
        print("начат парсинг")
        # сохранение в html файл ответа для дальнейших проверок
        html_source = driver.page_source
        with open('page.html', 'w', encoding='utf-8') as file:
            file.write(html_source)

        content = driver.find_element(By.TAG_NAME, 'body')
        tag_name = "tbody"
        class_name = "sort"
        info_by_article = list()
        for line in content.find_element(By.CSS_SELECTOR,
                                         f"{tag_name}.{class_name}").find_elements(
                By.TAG_NAME, "tr"):
            info_by_article.append([line.find_elements(By.TAG_NAME, "td")[1].text.strip(),
                                    line.find_elements(By.TAG_NAME, "td")[2].text.strip(),
                                    line.find_elements(By.TAG_NAME, "td")[6].text.strip()])
        print(f"Кол-во товаров найденных по артикулу {len(info_by_article)}")
        info_by_article = list(filter(lambda info_part: info_part[0] == article, info_by_article))
        print(f"Кол-во товаров с точным соответствием артикула {len(info_by_article)}")
        info_by_article = sorted(info_by_article, key=lambda info_part: info_part[2])
        pprint(info_by_article)
        if len(info_by_article) > 0:
            print(f"Самая низкая цена - {info_by_article[0][2]} \n"
                  f"самая высокая цена - {info_by_article[-1][2]}")
        else:
            print("Информации по данному артикулу не найдено")

    @func_timer
    def parsing_list_articles(self, articles: list[str]):
        if len(articles) == 0:
            return False
        result_answer: dict[str: list[str]] = dict()

        chrome_options = Options()
        chrome_options.add_argument(
            "--headless")  # Запуск браузера в фоновом режиме (без графического интерфейса)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(20)
        print("До блока try нет никаких ошибок")

        # Открытие страницы авторизации
        driver.get(self.auth_url)
        print("страница авторизации открыта успешно")

        if os.path.exists(os.path.join(BaseParser.session_dir, self.parser_name + ".pkl")):
            driver = self.load_selenium(driver, self.parser_name)
            print("В драйвер сохранена информация об актуальной сессии")
        else:
            driver = self.auth_selenium(driver, self._authorization_dict)
            self.save_selenium(driver, self.parser_name)
            print("Информация о сессии сохранена в файл")

        for i in range(len(articles)):
            # Переход к защищенной странице
            driver.get(self.search_url + f"?fnd={articles[i]}")
            print("выполнение поиска по артикулу")
            time.sleep(self.waiting_time)

            # Проверка - авторизована ли текущая сессия
            if (i == 0 and driver.find_element(By.XPATH, "//font[@color='red']") and
                    "Внимание! Вы не авторизованы!" in
                    driver.find_element(By.XPATH, "//font[@color='red']").text.strip()):
                print("Текущая сессия не зарегистрирована")
                driver = self.auth_selenium(driver, self._authorization_dict)
                driver.get(self.search_url + f"?fnd={articles[i]}")
                print("выполнение поиска по артикулу после повторной регистрации")
                time.sleep(self.waiting_time)
                self.save_selenium(driver, self.parser_name)
                print("обновление информации о сессии")

            # Парсинг содержимого защищенной страницы
            print("начат парсинг")
            content = driver.find_element(By.TAG_NAME, 'body')
            tag_name = "tbody"
            class_name = "sort"
            info_by_article = list()
            for line in content.find_element(By.CSS_SELECTOR,
                                             f"{tag_name}.{class_name}").find_elements(
                By.TAG_NAME, "tr"):
                info_by_article.append([line.find_elements(By.TAG_NAME, "td")[1].text.strip(),
                                        line.find_elements(By.TAG_NAME, "td")[2].text.strip(),
                                        line.find_elements(By.TAG_NAME, "td")[6].text.strip()])
            print(f"Кол-во товаров найденных по артикулу {len(info_by_article)}")
            info_by_article = list(filter(
                lambda info_part: info_part[0] == articles[i], info_by_article))
            print(f"Кол-во товаров с точным соответствием артикула {len(info_by_article)}")
            info_by_article = sorted(info_by_article, key=lambda info_part: info_part[2])
            pprint(info_by_article)
            if len(info_by_article) > 0:
                print(f"Самая низкая цена - {info_by_article[0][2]} \n"
                      f"самая высокая цена - {info_by_article[-1][2]}")
            if len(info_by_article) == 0:
                result_answer[articles[i]] = None
            elif len(info_by_article) == 1:
                result_answer[articles[i]] = list(info_by_article[0][2])
            else:
                result_answer[articles[i]] = [info_by_article[0][2], info_by_article[-1][2]]
        return result_answer


class ParserTrackMotors(BaseParser):
    parser_name = "track_motors"

    # session = requests.Session()
    # resp = session.post("https://market.tmtr.ru/auth/login",
    #                     data={"Login": "a.bezgodov@omegamb.ru", "Password": "LfOm7l3D2h7"},
    #                     headers={"User-Agent": fake_useragent.FakeUserAgent().random})

    def __init__(self):
        self.cur_session = requests.Session()
        auth_data = json.load(open("authorization.json", "r"))
        self._authorization_dict = {"login": auth_data[self.parser_name]["login"],
                                    "password": auth_data[self.parser_name]["password"]}
        self.auth_url = "https://market.tmtr.ru/#/login"
        self.search_url = ""
        self.waiting_time = 10

    @func_timer
    def parsing_article(self, article: str):
        chrome_options = Options()
        chrome_options.add_argument(
            "--headless")  # Запуск браузера в фоновом режиме (без графического интерфейса)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # driver.implicitly_wait(10)
        print("До блока try нет никаких ошибок")

        # Открытие страницы авторизации
        driver.get(self.auth_url)
        print("страница авторизации открыта успешно")

        if os.path.exists(os.path.join(BaseParser.session_dir, self.parser_name + ".pkl")):
            driver = self.load_selenium(driver, self.parser_name)
            print("В драйвер подгружена информация об актуальной сессии")
        else:
            driver = self.auth_selenium(driver, self._authorization_dict)
            self.save_selenium(driver, self.parser_name)
            print("Информация о сессии сохранена в файл")

        # Переход к защищенной странице
        driver.get(self.search_url + f"?fnd={article}")
        print("выполнение поиска по артикулу")
        # wait = WebDriverWait(driver, 10)  # ожидание до 10 секунд
        # wait.until_not(EC.visibility_of_element_located((
        #     By.XPATH, "//h3[text()='Выполняется расширенный поиск, результаты будут отображены.']")))
        time.sleep(self.waiting_time)

        if (driver.find_element(By.XPATH, "//font[@color='red']") and
                "Внимание! Вы не авторизованы!" in
                driver.find_element(By.XPATH, "//font[@color='red']").text.strip()):
            print("Текущая сессия не зарегистрирована")
            driver = self.auth_selenium(driver, self._authorization_dict)
            driver.get(self.search_url + f"?fnd={article}")
            print("выполнение поиска по артикулу после повторной регистрации")
            time.sleep(self.waiting_time)
            # wait = WebDriverWait(driver, 10)  # ожидание до 10 секунд
            # wait.until_not(EC.visibility_of_element_located((
            #     By.XPATH, "//h3[text()='Выполняется расширенный поиск, результаты будут отображены.']")))
            self.save_selenium(driver, self.parser_name)
            print("обновление информации о сессии")

        # Парсинг содержимого защищенной страницы
        print("начат парсинг")
        # сохранение в html файл ответа для дальнейших проверок
        html_source = driver.page_source
        with open('page.html', 'w', encoding='utf-8') as file:
            file.write(html_source)

        content = driver.find_element(By.TAG_NAME, 'body')
        tag_name = "tbody"
        class_name = "sort"
        info_by_article = list()
        for line in content.find_element(By.CSS_SELECTOR,
                                         f"{tag_name}.{class_name}").find_elements(
            By.TAG_NAME, "tr"):
            info_by_article.append([line.find_elements(By.TAG_NAME, "td")[1].text.strip(),
                                    line.find_elements(By.TAG_NAME, "td")[2].text.strip(),
                                    line.find_elements(By.TAG_NAME, "td")[6].text.strip()])
        print(f"Кол-во товаров найденных по артикулу {len(info_by_article)}")
        info_by_article = list(filter(lambda info_part: info_part[0] == article, info_by_article))
        print(f"Кол-во товаров с точным соответствием артикула {len(info_by_article)}")
        info_by_article = sorted(info_by_article, key=lambda info_part: info_part[2])
        pprint(info_by_article)
        if len(info_by_article) > 0:
            print(f"Самая низкая цена - {info_by_article[0][2]} \n"
                  f"самая высокая цена - {info_by_article[-1][2]}")
        else:
            print("Информации по данному артикулу не найдено")


if __name__ == "__main__":
    parser = ParserKomTrans()
    parser.parsing_article("003310")

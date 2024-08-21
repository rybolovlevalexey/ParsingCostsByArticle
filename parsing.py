import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import pickle
import os
from pprint import pprint
import time
import json
from concurrent.futures import ThreadPoolExecutor
from requests_html import HTMLSession

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
    def auth_selenium(driver, authorization_dict: dict[str, str], flag_sleep=False):
        """Метод для выполнения авторизации на сайте
        :param flag_sleep: нужна ли пауза для загрузки страницы после введения авторизационных данных
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

        if flag_sleep:
            time.sleep(3)
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


class ParserKomTrans(BaseParser):  # https://www.comtt.ru/
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
    def parsing_article(self, article: str) -> dict[str: None | list[int]]:
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
        # with open('page.html', 'w', encoding='utf-8') as file:
        #     file.write(html_source)

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
        info_by_article = list(map(lambda info_elem: [info_elem[0], info_elem[1], float(info_elem[2].split()[0])],
                                   filter(lambda info_part: info_part[0] == article, info_by_article)))
        print(f"Кол-во товаров с точным соответствием артикула {len(info_by_article)}")
        info_by_article = sorted(info_by_article, key=lambda info_part: info_part[2])
        pprint(info_by_article)
        if len(info_by_article) > 0:
            print(f"Самая низкая цена - {info_by_article[0][2]} \n"
                  f"самая высокая цена - {info_by_article[-1][2]}")
        else:
            print("Информации по данному артикулу не найдено")

        if len(info_by_article) == 0:
            return {self.parser_name: None}
        if len(info_by_article) == 1:
            return {self.parser_name: [info_by_article[0][2]]}
        return {self.parser_name: [info_by_article[0][2], info_by_article[-1][2]]}

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
            info_by_article = sorted(info_by_article, key=lambda info_part: int(info_part[2]))
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

    @func_timer
    def parsing_article_faster(self, article: str):
        session = HTMLSession()
        session.browser = session.browser(executable_path=r"C:\Users\Alexey\Downloads\chrome-win")
        resp_auth = session.post(self.auth_url, data=self._authorization_dict)
        if int(resp_auth.status_code) != 200:
            return {"done": False, "text": "Регистрация не пройдена"}

        print("Регистрация пройдена")
        response = session.get(self.search_url, params={"fnd": article})
        print(response.text)
        response.html.render(sleep=5)
        title = response.html.find('title', first=True)
        print(title)


class ParserTrackMotors(BaseParser):  # https://market.tmtr.ru
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
        # self.search_url = ""
        self.waiting_time = 10

    @func_timer
    def parsing_article(self, article: str) -> dict[str: None | list[int]]:
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
        driver = self.auth_selenium(driver, self._authorization_dict, flag_sleep=True)
        print("Произведена авторизация и информация сохранена в файл")
        self.save_selenium(driver, self.parser_name)
        art_input = driver.find_element(By.NAME, "q")

        art_input.send_keys(article)
        art_input.send_keys(Keys.ENTER)
        time.sleep(self.waiting_time)

        info_by_article = list()
        try:
            if len(driver.find_elements(By.CLASS_NAME, "mat-mdc-paginator-range-label")) == 0:
                print("на странице не была найдена информация, ждём ещё 5 сек")
                time.sleep(self.waiting_time)
            pages_count = int(driver.find_element(By.CLASS_NAME,
                                                  "mat-mdc-paginator-range-label").text.strip().split()[-1])
        except Exception:  # не нашёл информации о количестве страниц, следовательно ответ пустой
            return {self.parser_name: None}
        if pages_count == 1:
            for line in driver.find_element(
                    By.XPATH, "//tbody[@role='rowgroup']").find_elements(By.TAG_NAME, "tr"):
                try:
                    if len(line.find_element(By.TAG_NAME, "td").find_element(
                            By.TAG_NAME, "div").find_elements(By.CLASS_NAME, "article")) > 0:
                        line_article = line.find_element(By.TAG_NAME, "td").find_element(
                            By.TAG_NAME, "div").find_element(By.CLASS_NAME, "article").text
                    else:
                        line_article = line.find_element(By.TAG_NAME, "td").find_element(
                            By.TAG_NAME, "div").find_element(By.CLASS_NAME, "good_article").text
                    line_name = line.find_element(By.TAG_NAME, "td").find_elements(By.TAG_NAME, "span")[-2].text
                    line_cost = line.find_elements(By.TAG_NAME, "td")[1].find_element(
                        By.TAG_NAME, "div").find_element(By.TAG_NAME, "span").text
                    line_cost = line_cost.split()[1:-1]
                    line_cost = "".join(line_cost)
                    info_by_article.append([line_article, line_name, line_cost])
                except Exception:
                    continue
        elif pages_count > 1:
            cur_page_number = 0
            while cur_page_number < pages_count:
                cur_page_number = int(driver.find_element(
                    By.CLASS_NAME, "mat-mdc-paginator-range-label").text.strip().split()[1])
                for line in driver.find_element(
                        By.XPATH, "//tbody[@role='rowgroup']").find_elements(By.TAG_NAME, "tr"):
                    try:
                        if len(line.find_element(By.TAG_NAME, "td").find_element(
                                By.TAG_NAME, "div").find_elements(By.CLASS_NAME, "article")) > 0:
                            line_article = line.find_element(By.TAG_NAME, "td").find_element(
                                By.TAG_NAME, "div").find_element(By.CLASS_NAME, "article").text
                        else:
                            line_article = line.find_element(By.TAG_NAME, "td").find_element(
                                By.TAG_NAME, "div").find_element(By.CLASS_NAME, "good_article").text
                        line_name = line.find_element(By.TAG_NAME, "td").find_elements(By.TAG_NAME, "span")[-2].text
                        line_cost = line.find_elements(By.TAG_NAME, "td")[1].find_element(
                            By.TAG_NAME, "div").find_element(By.TAG_NAME, "span").text
                        line_cost = line_cost.split()[1:-1]
                        line_cost = "".join(line_cost)
                        info_by_article.append([line_article, line_name, line_cost])
                    except Exception:
                        continue
                if cur_page_number == pages_count:
                    break
                try:
                    driver.find_elements(By.CLASS_NAME, "mat-mdc-button-touch-target")[2].click()
                    print(cur_page_number, pages_count)
                except Exception:
                    continue
        else:
            print("Информации по данному артикулу не найдено")
            return {self.parser_name: None}

        pprint(info_by_article)
        print(f"Кол-во найденных товаров по введённому артикулу {len(info_by_article)}")
        info_by_article = list(filter(lambda info_part: info_part[0] == article, info_by_article))
        print(f"Кол-во товаров с точным соответствием артикула {len(info_by_article)}")
        info_by_article = list(map(lambda info_part: [info_part[0], info_part[1],
                                                      float(info_part[2].replace(",", "."))], info_by_article))
        info_by_article = sorted(info_by_article, key=lambda info_part: info_part[2])
        pprint(info_by_article)
        if len(info_by_article) > 0:
            print(f"Самая низкая цена - {info_by_article[0][2]} \n"
                  f"самая высокая цена - {info_by_article[-1][2]}")
        else:
            print("Информации по данному артикулу после фильтрации не найдено")

        if len(info_by_article) == 0:
            return {self.parser_name: None}
        if len(info_by_article) == 1:
            return {self.parser_name: [info_by_article[0][2]]}
        return {self.parser_name: [info_by_article[0][2], info_by_article[-1][2]]}


class ParserAutoPiter(BaseParser):  # https://autopiter.ru/
    parser_name = "auto_piter"

    def __init__(self):
        self.cur_session = requests.Session()
        auth_data = json.load(open("authorization.json", "r"))
        self._authorization_dict = {"login": auth_data[self.parser_name]["login"],
                                    "password": auth_data[self.parser_name]["password"]}
        self.auth_url = ""
        self.search_url = ""
        self.waiting_time = 10

    @func_timer
    def parsing_article(self, article: str, producer: str | None = None) -> dict[str: None | list[int]]:
        user_agent = UserAgent().random
        auth_url = "https://autopiter.ru/api/graphql"
        search_url = f"https://autopiter.ru/api/api/searchdetails?detailNumber={article}&isFullQuery=true"
        costs_url = "https://autopiter.ru/api/api/appraise/getcosts?"

        auth_resp = self.cur_session.post(auth_url, json={"query": "mutation login($login:String!$password:String!)"
                                                          "{login(loginForm:{login:$login password:$password})}",
                                          "variables": self._authorization_dict},
                                          headers={"User-Agent": user_agent})
        resp_search = self.cur_session.get(search_url, headers={"User-Agent": user_agent})
        search_data = json.loads(resp_search.content.decode("utf-8"))
        # pprint(search_data)
        for elem in search_data["data"]["catalogs"]:
            if (producer is not None and "catalogName" in elem and producer.lower() == elem["catalogName"].lower()
                    or producer is None):
                costs_url += "idArticles=" + str(elem["id"]) + "&"
        costs_url = costs_url[:-1]
        resp_costs = self.cur_session.get(costs_url, headers={"User-Agent": user_agent})
        json_content = json.loads(resp_costs.content)
        pprint(json_content)
        all_costs = list()
        print(search_url, costs_url)
        print("------------")
        if "code" in json_content and json_content["code"] == "429":
            return {"stop_flag": True}
        if "data" not in json_content:
            return {"no_data": True}
        for elem in json.loads(resp_costs.content)["data"]:
            if elem["originalPrice"] > 0:
                all_costs.append(elem["originalPrice"])
        if len(all_costs) == 0:
            return {self.parser_name: None}
        if len(all_costs) == 1:
            return {self.parser_name: [all_costs[0]]}
        return {self.parser_name: [min(all_costs), max(all_costs)]}


if __name__ == "__main__":
    parser1 = ParserKomTrans()
    parser2 = ParserTrackMotors()
    parser3 = ParserAutoPiter()
    print(parser3.parsing_article("30219", "BRINGER LIGHT"))  # 003310, 85696, 00-00000114, 40119
    # parser1.parsing_article_faster("003310")
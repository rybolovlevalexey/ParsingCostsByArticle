from datetime import datetime, timedelta
import requests
from fake_useragent import UserAgent
import pickle
import os
from pprint import pprint
import time
import json
import xmltodict

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
    session_dir = "../all_sessions"
    parser_name: str = "base_parser"

    def parsing_article(self, article: str, producer: str | None = None,
                        api_version: bool = True, waiting_flag: bool = False) -> dict[str: None | list[int | float]]:
        pass

    @staticmethod
    def cleaning_input_article(input_article: str) -> str:
        # в артикуле могут быть цифры, буквы различного регистра, знак тире
        result_article = ""
        for elem in input_article:
            if elem.isalpha() or elem.isdigit() or elem == "-" or elem == "—":
                result_article += elem

        return result_article

    def create_output_json(self, costs: list[float | int], delivery_days: list[int],
                           delivery_variants: list[dict]):
        # создание и наполнение итогового словаря
        result_output_dict = {"parser_name": self.parser_name}
        if len(costs) == 0:
            result_output_dict["costs"] = list()
        elif len(costs) == 1:
            result_output_dict["costs"] = costs
        else:
            result_output_dict["costs"] = [min(costs), max(costs)]

        if len(delivery_days) == 0:
            result_output_dict["delivery_days"] = list()
        elif len(delivery_days) == 1:
            result_output_dict["delivery_days"] = delivery_days
        else:
            result_output_dict["delivery_days"] = [min(delivery_days), max(delivery_days)]

        result_output_dict["variants"] = delivery_variants
        result_output_dict["variants_count"] = len(delivery_variants)

        return result_output_dict

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


# https://www.comtt.ru/
class ParserKomTrans(BaseParser):
    parser_name = "kom_trans"

    # http://catalogs.comtt.ru/api/ документация по api

    def __init__(self):
        self.cur_session = requests.Session()
        auth_data = json.load(open("authorization.json", "r"))
        self._authorization_dict = {"login": auth_data[self.parser_name]["login"],
                                    "pass": auth_data[self.parser_name]["password"]}
        self.auth_url = "https://www.comtt.ru/login.php"
        self.search_url = "https://www.comtt.ru/search.php"
        self.waiting_time = 15

        self._authorization_api_dict = {"login": auth_data[self.parser_name]["login"],
                                        "password": auth_data[self.parser_name]["password"]}
        self.api_auth_url = "http://catalogs.comtt.ru/api/login.php"
        self.api_search_url = "http://catalogs.comtt.ru/api/search.php"
        self.api_waiting_time = 10

    @func_timer
    def parsing_article(self, article: str, producer: str | None = None,
                        api_version: bool = True, waiting_flag: bool = False) -> dict[str: None | list[int]]:
        article = self.cleaning_input_article(article)
        if waiting_flag:
            time.sleep(self.waiting_time)
        if api_version:
            auth_data = json.load(open("authorization.json", "r"))
            if "token" in auth_data[self.parser_name].keys():
                auth_token = auth_data[self.parser_name]["token"]
            else:
                api_auth_resp = requests.post(self.api_auth_url, json=self._authorization_api_dict)
                pprint(json.loads(api_auth_resp.content))
                auth_token = json.loads(api_auth_resp.content)["token"]
                auth_data[self.parser_name]["token"] = auth_token
                open("authorization.json", "w").write(json.dumps(auth_data))

            api_search_resp = requests.post(self.api_search_url,
                                            json={"search": article, "token": auth_token})
            search_result = json.loads(api_search_resp.content)
            # pprint(search_result)

            if "search_result" not in search_result or search_result["search_result"] == "Ничего не найдено!":
                return {"parser_name": self.parser_name, "error": "По переданному артикулу ничего не найдено"}

            all_costs: list[float] = list()
            all_delivery_days: list[int] = list()
            variants: list[dict[str: int | None]] = list()

            for key, value in search_result["search_result"].items():
                if key == "код_валюты":
                    continue
                if ("артикул" not in value or value["артикул"] != article.strip()
                        or producer is not None and
                        ("производитель" not in value or value["производитель"].strip().lower() != producer.lower())):
                    continue

                if "цена" in value and value["цена"] is not None:
                    all_costs.append(float(value["цена"]))

                if "остатки" not in value:
                    variants.append({"cost": float(value["цена"]), "delivery_days": None})
                else:
                    for line in value["остатки"]:
                        seconds_since_2000 = int(line["срок_доставки_в_сек"])  # 779997600
                        start_date = datetime(2000, 1, 1)
                        target_date = start_date + timedelta(seconds=seconds_since_2000)
                        current_date = datetime.now()
                        difference = abs(current_date - target_date)
                        days_difference = difference.days

                        all_delivery_days.append(days_difference)
                        variants.append({"cost": float(value["цена"]), "delivery_days": days_difference})

            result_output = self.create_output_json(all_costs, all_delivery_days, variants)
            return result_output
        else:
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

            """
            if os.path.exists(os.path.join(BaseParser.session_dir, self.parser_name + ".pkl")):
                driver = self.load_selenium(driver, self.parser_name)
                print("В драйвер подгружена информация об актуальной сессии")
            else:
                driver = self.auth_selenium(driver, self._authorization_dict)
                self.save_selenium(driver, self.parser_name)
                print("Информация о сессии сохранена в файл")
    
            """

            # регистрация без попытки сохранения информации о сессии
            driver = self.auth_selenium(driver, self._authorization_dict)
            driver.get(self.search_url + f"?fnd={article}")
            # Переход к защищенной странице
            # driver.get(self.search_url + f"?fnd={article}")
            print("выполнение поиска по артикулу")
            # wait = WebDriverWait(driver, 10)  # ожидание до 10 секунд
            # wait.until_not(EC.visibility_of_element_located((
            #     By.XPATH, "//h3[text()='Выполняется расширенный поиск, результаты будут отображены.']")))
            time.sleep(self.waiting_time)

            """
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
            """

            # Парсинг содержимого защищенной страницы
            print("начат парсинг")
            # сохранение в html файл ответа для дальнейших проверок
            html_source = driver.page_source

            # with open('page.html', 'w', encoding='utf-8') as file:
            #     file.write(html_source)

            # driver.save_screenshot("")

            if len(driver.find_elements(By.CLASS_NAME, "orangebtn")) > 0:
                driver.find_element(By.CLASS_NAME, "orangebtn").click()
                print("Нажата кнопка попробовать снова")
                time.sleep(5)

            content = driver.find_element(By.TAG_NAME, 'body')
            tag_name = "tbody"
            class_name = "sort"
            info_by_article = list()
            for line in content.find_element(By.CSS_SELECTOR,
                                             f"{tag_name}.{class_name}").find_elements(
                By.TAG_NAME, "tr"):
                info_by_article.append([line.find_elements(By.TAG_NAME, "td")[1].text.strip(),  # артикул
                                        line.find_elements(By.TAG_NAME, "td")[2].text.strip(),  # производитель
                                        line.find_elements(By.TAG_NAME, "td")[6].text.strip()])  # цена
            print(f"Кол-во товаров найденных по артикулу {len(info_by_article)}")
            if producer is None:
                info_by_article = list(
                    map(lambda info_elem: [info_elem[0], info_elem[1], float(info_elem[2].split()[0])],
                        filter(lambda info_part: info_part[0] == article, info_by_article)))
                print(f"Кол-во товаров с точным соответствием артикула {len(info_by_article)}")
            else:
                info_by_article = list(
                    map(lambda info_elem: [info_elem[0], info_elem[1], float(info_elem[2].split()[0])],
                        filter(lambda info_part:
                               info_part[0] == article and info_part[1].lower() == producer.lower(),
                               info_by_article)))
                print(f"Кол-во товаров с точным соответствием артикула и производителя {len(info_by_article)}")
            info_by_article = sorted(info_by_article, key=lambda info_part: info_part[2])
            pprint(info_by_article)
            if len(info_by_article) > 0:
                print(f"Самая низкая цена - {info_by_article[0][2]} \n"
                      f"самая высокая цена - {info_by_article[-1][2]}")
            else:
                print("Информации по данному артикулу не найдено")

            if len(info_by_article) == 0:
                return {"parser_name": self.parser_name, "costs": None}
            if len(info_by_article) == 1:
                return {"parser_name": self.parser_name, "costs": [info_by_article[0][2]]}
            return {"parser_name": self.parser_name, "costs": [info_by_article[0][2], info_by_article[-1][2]]}


# https://market.tmtr.ru/
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
        self.search_url = "http://api.tmtr.ru/API.asmx/Proboy"
        self.waiting_time = 10

    @func_timer
    def parsing_article(self, article: str, producer: str | None = None,
                        api_version: bool = True, waiting_flag: bool = False) -> dict[str: None | list[float]]:
        article = self.cleaning_input_article(article)
        if waiting_flag:
            time.sleep(5)
        if api_version:
            # надо учесть, что бренд может быть None
            if producer is None:
                # print("Без информации о необходимом производителе невозможно получить однозначную информацию")
                return {"parser_name": self.parser_name, "error": "no info about producer or brand"}
            resp = requests.post(self.search_url, headers=self._authorization_dict,
                                 json={"article": article, "brand": producer})
            if resp.status_code == 200:
                # print(f"Получен корректный ответ по артикулу {article} в парсере {self.parser_name}")
                pass
            else:
                # print(f"Получен НЕ корректный ответ по артикулу {article} в парсере {self.parser_name}")
                return {"parser_name": self.parser_name, "error": f"получен некорректный ответ по артикулу {article}"}
            # pprint(json.dumps(resp.content.decode("utf-8")))
            if resp.text.endswith('{"d":null}'):
                resp_content = resp.text[:-10]
            else:
                resp_content = resp.text
            json_data = json.loads(resp_content)
            # pprint(json_data)
            all_costs = list()
            all_delivery_days = list()
            all_variants = list()

            for elem in json_data:
                if elem["Article"] != article or elem["Producer"].lower().strip() != producer.lower().strip():
                    continue
                try:
                    all_costs.append(float(elem["Price"]))
                    if datetime.fromisoformat(elem["DeliveryDate"]) >= datetime.now():
                        all_delivery_days.append((datetime.fromisoformat(elem["DeliveryDate"]) - datetime.now()).days +
                                                 (1 if (datetime.fromisoformat(elem["DeliveryDate"]) -
                                                        datetime.now()).seconds >= 12 else 0))
                        all_variants.append({"cost": elem["Price"],
                                             "delivery_days":
                                                 (datetime.fromisoformat(elem["DeliveryDate"]) - datetime.now()).days +
                                                 (1 if (datetime.fromisoformat(elem["DeliveryDate"]) -
                                                        datetime.now()).seconds >= 12 else 0)})
                    else:
                        all_variants.append({"cost": elem["Price"], "delivery_days": None})
                except Exception:
                    break
            if len(all_costs) > 0:
                # print(f"Цены в парсере {self.parser_name} обработаны успешно: "
                #       f"минимум - {min(all_costs)}, максимум - {max(all_costs)}")
                pass
            else:
                # print(f"По артикулу {article} и производителю {producer} "
                #       f"в парсере {self.parser_name} ничего не найдено")
                pass

            result_output = self.create_output_json(all_costs, all_delivery_days, all_variants)
            return result_output
        else:
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
                return {"parser_name": self.parser_name, "costs": None}
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
                return {"parser_name": self.parser_name, "costs": None}

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
                return {"parser_name": self.parser_name, "costs": None}
            if len(info_by_article) == 1:
                return {"parser_name": self.parser_name, "costs": [info_by_article[0][2]]}
            return {"parser_name": self.parser_name, "costs": [info_by_article[0][2], info_by_article[-1][2]]}


# https://autopiter.ru/
class ParserAutoPiter(BaseParser):
    parser_name = "auto_piter"

    def __init__(self):
        self.cur_session = requests.Session()
        auth_data = json.load(open("authorization.json", "r"))
        self._authorization_dict = {"login": auth_data[self.parser_name]["login"],
                                    "password": auth_data[self.parser_name]["password"]}
        self.auth_url = "https://autopiter.ru/api/graphql"

        self.api_auth_url = "http://www.autopiter.ru/Authorization"
        self.waiting_time = 10

    @func_timer
    def parsing_article(self, article: str, producer: str | None = None,
                        api_version: bool = True, waiting_flag: bool = False) -> dict[str: None | list[int]]:
        article = self.cleaning_input_article(article)

        # auth_resp = self.cur_session.post(self.api_auth_url, data={"UserID": self._authorization_dict["login"],
        #                                                            "Password": self._authorization_dict["password"],
        #                                                            "Save": True})
        # pprint(auth_resp.text)
        # URL для запроса
        auth_url = "http://service.autopiter.ru/v2/price"

        # Заголовки запроса
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://www.autopiter.ru/Authorization"
        }

        # Тело запроса на авторизацию (SOAP)
        auth_body = f'''<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                       xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <Authorization xmlns="http://www.autopiter.ru/">
              <UserID>{self._authorization_dict["login"]}</UserID>
              <Password>{self._authorization_dict["password"]}</Password>
              <Save>true</Save> <!-- или false в зависимости от вашего запроса -->
            </Authorization>
          </soap:Body>
        </soap:Envelope>'''

        auth_resp = requests.post(auth_url, headers=headers, data=auth_body)
        resp_dict = json.loads(json.dumps(xmltodict.parse(auth_resp.text)))

        if resp_dict["soap:Envelope"]["soap:Body"]["AuthorizationResponse"]["AuthorizationResult"]:
            pass

        # Вывод ответа
        pprint(resp_dict)

    @func_timer
    def old_parsing_article(self, article: str, producer: str | None = None,
                            api_version: bool = True, waiting_flag: bool = False) -> dict[str: None | list[int]]:
        user_agent = UserAgent().random
        search_url = f"https://autopiter.ru/api/api/searchdetails?detailNumber={article}&isFullQuery=true"
        costs_url = "https://autopiter.ru/api/api/appraise/getcosts?"
        url_more_info = f"https://autopiter.ru/api/api/appraise?"

        if producer is not None:
            if ";" not in producer and "," not in producer:
                producer += ";"
            elif "," in producer:
                producer = producer.replace(",", ";")
            producer = list(filter(lambda st: len(st) > 0, map(lambda name: name.strip().lower(), producer.split(";"))))
        print(producer)
        auth_resp = self.cur_session.post(self.auth_url,
                                          json={"query": "mutation login($login:String!$password:String!)"
                                                         "{login(loginForm:{login:$login password:$password})}",
                                                "variables": self._authorization_dict},
                                          headers={"User-Agent": user_agent})
        resp_search = self.cur_session.get(search_url, headers={"User-Agent": user_agent})
        search_data = json.loads(resp_search.content.decode("utf-8"))
        # pprint(search_data)

        for elem in search_data["data"]["catalogs"]:
            if (producer is not None and "catalogName" in elem and elem["catalogName"].lower() in producer
                    or producer is None):
                costs_url += "idArticles=" + str(elem["id"]) + "&"
                url_more_info += "id=" + str(elem["id"]) + "&"

        costs_url = costs_url[:-1]
        url_more_info = url_more_info[:-1]

        resp_costs = self.cur_session.get(costs_url, headers={"User-Agent": user_agent})
        json_content = json.loads(resp_costs.content)
        # pprint(json_content)

        more_info_search = self.cur_session.get(url_more_info, headers={"User-Agent": user_agent})
        more_info = json.loads(more_info_search.content)
        pprint(more_info)

        all_costs = list()
        all_delivery_days = list()
        variants = list()

        print(search_url, costs_url)
        if "code" in json_content and json_content["code"] == "429":
            return {"parser_name": self.parser_name, "stop_flag": True}
        if "data" not in json_content:
            return {"parser_name": self.parser_name, "no_data": True}
        for elem in more_info["data"]:
            if elem["catalogName"].lower() != producer:
                continue
            if elem["price"] > 0:
                all_costs.append(elem["price"])
            if "deliveryDays" in elem and elem["deliveryDays"] is not None:
                all_delivery_days.append(elem["deliveryDays"])
            if elem["price"] > 0 and "deliveryDays" in elem and elem["deliveryDays"] is not None:
                variants.append({"cost": elem["price"], "delivery_days": elem["deliveryDays"]})

        result_output = self.create_output_json(all_costs, all_delivery_days, variants)
        return result_output


if __name__ == "__main__":
    parser1 = ParserKomTrans()
    parser2 = ParserTrackMotors()
    parser3 = ParserAutoPiter()

    # AZ9925520250 HOWO
    # print(parser1.parsing_article("30219", "BRINGER LIGHT"))
    # print(parser1.parsing_article("AZ9925520250", "HOWO"))
    # print(parser1.parsing_article("1802905005830", "ROSTAR"))

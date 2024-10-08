import json

import requests
from pprint import pprint


def test_articles():
    resp = requests.get("http://127.0.0.1:8000/costs_by_article/003310")
    print(resp)
    pprint(resp.content)


def test_articles_with_producer():
    resp = requests.get("http://127.0.0.1:8000/costs_by_article/003310/BRINGER LIGHT")
    print(resp)
    pprint(resp.content)


def test_files():
    url = "http://127.0.0.1:8000/costs_by_file"
    url_faster = "http://127.0.0.1:8000/costs_by_file_costs_by_file_fastest"

    file_path = "../input_files/укороченный новый файл.xlsx"
    new_file_path = "../input_files/Товары1.xlsx"

    with open(new_file_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)

    print(response.status_code)
    print(response.content)


def test_massive_articles():
    url = "http://127.0.0.1:8000/post_costs_by_massive_articles/"
    data = ["00-00000114", "003310", "85696"]

    response = requests.post(url, json=data)
    pprint(response.json())


def test_online_massive():
    url = "https://parse-costs-rybolovlevalexey.amvera.io/post_costs_by_massive_articles/"
    data = ["00-00000114", "003310", "85696"]

    response = requests.post(url, json=data)
    print(response.status_code)
    pprint(response.json())


def test_online_one_art():
    url1 = "https://parse-costs-rybolovlevalexey.amvera.io/costs_by_article/003310"
    url2 = "https://parse-costs-rybolovlevalexey.amvera.io/"
    resp = requests.get(url1)
    print(resp)
    pprint(resp.content)


def test_selectively_auto_piter():
    url = "http://127.0.0.1:8000/costs_by_file_selectively"
    file_path = "../input_files/Ост 20240820 мерс_норм.xlsx"

    data = {
        "parsers_on": {
            "kom_trans": False,
            "track_motors": False,
            "auto_piter": True
        }
    }
    response = requests.post(url, data={"info": json.dumps(data)},
                             files={"file": open(file_path, "rb")})
    print(response.content)


def test_selectively_kom_trans():
    url = "http://127.0.0.1:8000/costs_by_file_selectively"
    file_path = "../input_files/Ост 20240820 мерс_норм.xlsx"

    data = {
        "parsers_on": {
            "kom_trans": True,
            "track_motors": False,
            "auto_piter": False
        }
    }
    response = requests.post(url, data={"info": json.dumps(data)},
                             files={"file": open(file_path, "rb")})
    print(response.content)


def test_post_new_user():
    url = "http://127.0.0.1:8000/create_user"
    data = {"login": "admin", "password": "admin_password"}
    resp = requests.post(url, data=json.dumps(data))


def test_json_info():
    url = "http://127.0.0.1:8000/costs_by_json"

    resp = requests.post(url, data=json.dumps({"info": [
        {"article": "A4722000154", "producer": "MERCEDES-BENZ"},
        {"article": "WG9925955059", "producer": "HOWO"}
    ]}))

    pprint(json.loads(resp.content))


# test_selectively_auto_piter()
# test_articles_with_producer()
# test_post_new_user()
# test_files()
test_json_info()

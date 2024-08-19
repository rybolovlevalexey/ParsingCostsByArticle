import requests
from pprint import pprint


def test_articles():
    resp = requests.get("http://127.0.0.1:8000/costs_by_article/003310")
    print(resp)
    pprint(resp.content)


def test_files():
    url = "http://127.0.0.1:8000/costs_by_file_futures"
    file_path = "Остатки_bigger_short.xlsx"

    with open(file_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)

    print(response.status_code)
    print(response.content)


def test_massive_articles():
    url = "http://127.0.0.1:8000/costs_by_massive_articles/"
    data = ["00-00000114", "003310", "85696"]

    response = requests.post(url, json=data)
    pprint(response.json())


def test_online_massive():
    url = "https://parse-costs-rybolovlevalexey.amvera.io/costs_by_massive_articles/"
    data = ["00-00000114", "003310", "85696"]

    response = requests.post(url, json=data)
    print(response.status_code)
    pprint(response.json())


def test_online_one_art():
    url1 = "https://parse-costs-rybolovlevalexey.amvera.io/costs_by_article/003310"
    url2 = "https://parse-costs-rybolovlevalexey.amvera.io/"
    resp = requests.get(url2)
    print(resp)
    pprint(resp.content)


test_online_one_art()

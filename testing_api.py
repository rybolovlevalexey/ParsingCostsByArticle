import requests
from pprint import pprint


def test__articles():
    resp = requests.get("http://127.0.0.1:8000/test")
    print(resp)
    pprint(resp.content)


def test_files():
    url = "http://127.0.0.1:8000/costs_by_file"
    file_path = "Остатки_bigger_short.xlsx"

    with open(file_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)

    print(response.status_code)
    print(response.content)


test_files()
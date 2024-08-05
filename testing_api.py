import requests
from pprint import pprint

resp = requests.get("http://127.0.0.1:8000/get_costs/003310/")
pprint(resp)
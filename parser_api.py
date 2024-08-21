import time

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from parsing import ParserKomTrans, ParserTrackMotors, ParserAutoPiter
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from io import BytesIO
import threading
import multiprocessing
import uvicorn
import json


app = FastAPI(title="Parsing product costs by its article",
              version="1.0.0")


@app.get("/costs_by_article/{article}")
def get_costs_by_article(article: str):
    with ThreadPoolExecutor(max_workers=3) as executor:
        parser1, parser2, parser3 = ParserKomTrans(), ParserTrackMotors(), ParserAutoPiter()
        futures = [
            executor.submit(parser1.parsing_article, article),
            executor.submit(parser2.parsing_article, article),
            executor.submit(parser3.parsing_article, article)
        ]
        results = [future.result() for future in futures]
    return {"article": article, "costs": results}


@app.post("/costs_by_file")
def post_costs_by_file(file: UploadFile = File(...)):
    content_file = file.file.read()
    data_frame = pd.read_excel(BytesIO(content_file))
    rows, cols = data_frame.shape

    for index, row in data_frame.iterrows():
        row_article = row.iloc[0]
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                parser1, parser2, parser3 = ParserKomTrans(), ParserTrackMotors(), ParserAutoPiter()
                futures = [
                    executor.submit(parser1.parsing_article, row_article),
                    executor.submit(parser2.parsing_article, row_article),
                    executor.submit(parser3.parsing_article, row_article)
                ]
                results = [future.result() for future in futures]
        except Exception:
            print(f"ПРОИЗОШЛА ОШИБКА ПРИ ПАРСИНГЕ article={row_article}")
            continue
        print(results)
        for elem in results:
            if list(elem.values())[0] is None:
                data_frame.at[index, list(elem.keys())[0]] = list(elem.values())[0]
            elif len(list(elem.values())[0]) == 1:
                data_frame.at[index, list(elem.keys())[0]] = list(elem.values())[0][0]
            else:
                data_frame.at[index, list(elem.keys())[0]] = "-".join(list(map(str, list(elem.values())[0])))

    data_frame.to_excel("новый_файл_updated.xlsx", index=False)
    return {"done": True}


@app.post("/costs_by_file_threading")
def post_costs_by_file_threading(file: UploadFile = File(...)):
    def parsing_func(row_art, ind):
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                parser1, parser2, parser3 = ParserKomTrans(), ParserTrackMotors(), ParserAutoPiter()
                futures = [
                    executor.submit(parser1.parsing_article, row_art),
                    executor.submit(parser2.parsing_article, row_art),
                    executor.submit(parser3.parsing_article, row_art)
                ]
                results = [future.result() for future in futures]
        except Exception:
            print(f"ПРОИЗОШЛА ОШИБКА ПРИ ПАРСИНГЕ article={row_art}")
            return
        print(results)
        for elem in results:
            if list(elem.values())[0] is None:
                data_frame.at[ind, list(elem.keys())[0]] = list(elem.values())[0]
            elif len(list(elem.values())[0]) == 1:
                data_frame.at[ind, list(elem.keys())[0]] = list(elem.values())[0][0]
            else:
                data_frame.at[ind, list(elem.keys())[0]] = "-".join(list(map(str, list(elem.values())[0])))

    content_file = file.file.read()
    data_frame = pd.read_excel(BytesIO(content_file))
    rows, cols = data_frame.shape

    threads = list()

    for index, row in data_frame.iterrows():
        row_article = row.iloc[0]
        thread = threading.Thread(target=parsing_func, args=(row_article, index))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    data_frame.to_excel("остатки_updated_threading.xlsx", index=False)
    return {"done": True}


@app.post("/costs_by_file_fastest")
def post_costs_by_file_fastest(file: UploadFile = File(...)):
    def parsing_func(row_art, ind):
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                parser1, parser2, parser3 = ParserKomTrans(), ParserTrackMotors(), ParserAutoPiter()
                futures = [
                    executor.submit(parser1.parsing_article, row_art),
                    executor.submit(parser2.parsing_article, row_art),
                    executor.submit(parser3.parsing_article, row_art)
                ]
                results = [future.result() for future in futures]
        except Exception:
            print(f"ПРОИЗОШЛА ОШИБКА ПРИ ПАРСИНГЕ article={row_art}")
            return
        print(results)
        for elem in results:
            if list(elem.values())[0] is None:
                data_frame.at[ind, list(elem.keys())[0]] = list(elem.values())[0]
            elif len(list(elem.values())[0]) == 1:
                data_frame.at[ind, list(elem.keys())[0]] = list(elem.values())[0][0]
            else:
                data_frame.at[ind, list(elem.keys())[0]] = "-".join(list(map(str, list(elem.values())[0])))

    content_file = file.file.read()
    data_frame = pd.read_excel(BytesIO(content_file))
    rows, cols = data_frame.shape

    def wrapper(args):
        return parsing_func(args[1].iloc[0], args[0])

    with ThreadPoolExecutor() as pool_executor:
        results = list(pool_executor.map(wrapper, data_frame.iterrows()))

    data_frame.to_excel("остатки_updated_futures_bigger.xlsx", index=False)
    return {"done": True}


@app.post("/costs_by_massive_articles/")
def post_costs_by_massive_articles(items: list[str]):
    def parsing_func(article):
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                parser1, parser2, parser3 = ParserKomTrans(), ParserTrackMotors(), ParserAutoPiter()
                futures = [
                    executor.submit(parser1.parsing_article, article),
                    executor.submit(parser2.parsing_article, article),
                    executor.submit(parser3.parsing_article, article)
                ]
                results = [future.result() for future in futures]
        except Exception:
            print(f"ПРОИЗОШЛА ОШИБКА ПРИ ПАРСИНГЕ article={article}")
            return
        print(results)
        return results

    with ThreadPoolExecutor() as pool_executor:
        pool_results = list(pool_executor.map(parsing_func, items))
    return {"results": pool_results}


@app.post("/costs_by_file_selectively/")
def post_costs_by_file_selectively(info: str = Form(...), file: UploadFile = File(...)):
    content_file = file.file.read()
    file_name_output = "".join(file.filename.split(".")[0:-1]).strip() + " updated." + file.filename.split(".")[-1]
    data_frame = pd.read_excel(BytesIO(content_file))
    additional_info = json.loads(info)
    rows, cols = data_frame.shape
    dict_codes_result = dict()

    if (additional_info["parsers_on"]["auto_piter"] and
            not additional_info["parsers_on"]["kom_trans"] and
            not additional_info["parsers_on"]["track_motors"]):
        for index, row in data_frame.iterrows():
            time.sleep(5)
            if int(index) % 10 == 0 and int(index) != 0:
                print(f"ПРОГРЕСС ПАРСИНГА {index} из {rows}. Отчёт об ошибках - {dict_codes_result}")
            if int(index) % 100 == 0 and int(index) != 0:
                print("Сохранён новый промежуточный файл")
                data_frame.to_excel(str(int(index) // 100) + file_name_output + "x", index=False)
            row_article = row.iloc[0]
            row_prod = row.iloc[2]
            parser = ParserAutoPiter()
            elem = parser.parsing_article(row_article, row_prod)
            print(elem)

            if "no_data" in elem and elem["no_data"]:
                dict_codes_result["409"] = dict_codes_result.get("409", 0) + 1
                continue
            if "stop_flag" in elem and elem["stop_flag"]:
                dict_codes_result["429"] = dict_codes_result.get("429", 0) + 1
                print("Web Api url blocked, ЖДЁМ МИНУТУ")
                time.sleep(60)
                continue

            dict_codes_result["200"] = dict_codes_result.get("200", 0) + 1
            if list(elem.values())[0] is None:
                data_frame.at[index, list(elem.keys())[0]] = list(elem.values())[0]
            elif len(list(elem.values())[0]) == 1:
                data_frame.at[index, list(elem.keys())[0]] = list(elem.values())[0][0]
            else:
                data_frame.at[index, list(elem.keys())[0]] = "-".join(list(map(str, list(elem.values())[0])))

        data_frame.to_excel(file_name_output, index=False)
        return {"done": True, "codes_counter": dict_codes_result}


@app.get("/")
def get_index():
    return {"index": "done"}


# время работы без ускорений на файле из 10 строк - 5 минут
# ускорение обработки файла вариант через threading, время работы - 1 минута 20 секунд
# multiprocessing ускорения не выдал
# concurrent.futures ускорил время работы до 50 секунд
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from parsing import ParserKomTrans, ParserTrackMotors, ParserAutoPiter
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from io import BytesIO
import threading
import multiprocessing


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
            print("ПРОИЗОШЛА ОШИБКА ПРИ ПАРСИНГЕ")
            continue
        print(results)
        for elem in results:
            if list(elem.values())[0] is None:
                data_frame.at[index, list(elem.keys())[0]] = list(elem.values())[0]
            elif len(list(elem.values())[0]) == 1:
                data_frame.at[index, list(elem.keys())[0]] = list(elem.values())[0][0]
            else:
                data_frame.at[index, list(elem.keys())[0]] = "-".join(list(map(str, list(elem.values())[0])))

    data_frame.to_excel("остатки_updated.xlsx", index=False)
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
            print("ПРОИЗОШЛА ОШИБКА ПРИ ПАРСИНГЕ")
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


@app.post("/costs_by_file_futures")
def post_costs_by_file_futures(file: UploadFile = File(...)):
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
            print("ПРОИЗОШЛА ОШИБКА ПРИ ПАРСИНГЕ")
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


@app.get("/")
def get_index():
    return {"index": "done"}


# время работы без ускорений на файле из 10 строк - 5 минут
# ускорение обработки файла вариант через threading, время работы - 1 минута 20 секунд
# multiprocessing ускорения не выдал
# concurrent.futures ускорил время работы до 50 секунд
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request, Header
from fastapi.responses import JSONResponse
from parsing import ParserKomTrans, ParserTrackMotors, ParserAutoPiter
from concurrent.futures import ThreadPoolExecutor
import uvicorn
import json

from api_models import NewUser, WebSiteData
from databases import DatabaseActions
from parser_api_router_v1 import router_v1


app = FastAPI(title="Parsing product costs by its article",
              version="1.0.0")
app.include_router(router_v1)


@app.post("/costs_by_json",
          summary="Получение информации в формате json",
          description="Получение информации в формате json о ценах и сроках поставки по артикулу и производителю, "
                      "переданных в формате json. Одновременный парсинг сайтов КомТранс, ТракМоторс, АвтоПитер.")
async def post_costs_by_json(request: Request):  # info: str = Form(...)
    info = await request.json()
    print(info)
    output_info = list()

    for elem in info["info"]:
        row_article, row_prod = elem["article"], elem["producer"]
        with ThreadPoolExecutor(max_workers=3) as executor:
            parser1, parser2, parser3 = ParserKomTrans(), ParserTrackMotors(), ParserAutoPiter()
            futures = [
                executor.submit(parser1.parsing_article, row_article, row_prod, True, False),
                executor.submit(parser2.parsing_article, row_article, row_prod, True, False),
                executor.submit(parser3.parsing_article, row_article, row_prod, True, False)
            ]
            row_results = [future.result() for future in futures]
        print(row_results)
        output_info.append({"article": row_article, "results": row_results})
    return output_info


@app.post("/create_user")
def post_create_user(info: NewUser):
    result = DatabaseActions().create_new_user(info.login, info.password)
    if result:
        return JSONResponse(status_code=201, content={"message": f"Новый пользователь {info.login} успешно добавлен"})
    return JSONResponse(status_code=422,
                        content={"message": "Новый пользователь не добавлен, попробуйте что-то другое"})


@app.post("/create_template")
def post_create_template(x_login: str = Header(...), x_password: str = Header(...)):
    pass


@app.post("/new_web_site_data")
def post_new_web_site_data(info: WebSiteData, x_login: str = Header(...), x_password: str = Header(...)):
    """Добавление информации о новом сайте для конкретного пользователя.
    Необходимы базовая ссылка на сайт, логин и пароль от этого сайта"""
    user_id: int = DatabaseActions().get_user_id(x_login, x_password)
    if user_id == -1:
        return JSONResponse(status_code=422, content={"message": "Получены некорректные данные для авторизации"})
    action_result = DatabaseActions().add_new_site(user_id, info.site_url, x_login, x_password)
    if action_result:
        return JSONResponse(status_code=201,
                            content={"message": f"Для пользователя {x_login} успешно добавлены данные "
                                                f"для авторизации на сайте {info.site_url}"})
    return JSONResponse(status_code=422,
                        content={"message": f"Информация о сайте не добавлена"})


@app.get("/")
def get_index():
    return {"index": "done"}


# время работы без ускорений на файле из 10 строк - 5 минут
# ускорение обработки файла вариант через threading, время работы - 1 минута 20 секунд
# multiprocessing ускорения не выдал
# concurrent.futures ускорил время работы до 50 секунд
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

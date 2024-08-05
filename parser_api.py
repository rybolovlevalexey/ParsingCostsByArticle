from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from parsing import ParserKomTrans, ParserTrackMotors, ParserAutoPiter
from concurrent.futures import ThreadPoolExecutor


app = FastAPI(title="Parsing product costs by its article",
              version="1.0.0")


@app.get("/get_costs/{article}")
def get_costs(article: str):
    with ThreadPoolExecutor(max_workers=3) as executor:
        parser1, parser2, parser3 = ParserKomTrans(), ParserTrackMotors(), ParserAutoPiter()
        futures = [
            executor.submit(parser1.parsing_article, article),
            executor.submit(parser2.parsing_article, article),
            executor.submit(parser3.parsing_article, article)
        ]
        results = [future.result() for future in futures]
    return {"article": article, "costs": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
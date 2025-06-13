import json
import uvicorn
from argparse import ArgumentParser
from typing import Annotated
import random
from fastapi import Cookie, FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime

from backend_server import Server

parser = ArgumentParser(description="server for crowdsourcing")
parser.add_argument("--config", type=str, default="config.toml", help="config file")
args, unknown = parser.parse_known_args()
server = Server(str(args.config))

app = FastAPI()
app.mount("/assets", StaticFiles(directory=server.assets), name="assets")


@app.get("/")
async def root():
    with open(server.sign_in, "r") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/sign_in")
async def root():
    with open(server.sign_in, "r") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.post("/session/")
def session(prolific_id: Annotated[str, Form()]):
    response = RedirectResponse(url="/guidelines")
    # if cookie is already in DB do not reassign
    # cookie value is the same as the prolific id
    cookie = server.retrieve_cookie_from_prolific_id(prolific_id)
    if cookie is None:
        server.assign_cookie(prolific_id, prolific_id, datetime.now())
        # batches = server.retrieve_batches()

    response.set_cookie(key="session_key", value=prolific_id)
    return response


@app.get("/guidelines")
@app.post("/guidelines")
async def guidelines_page():
    with open(server.guidelines, "r") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/prolific_id")
async def prolific_id_page(session_key: Annotated[str | None, Cookie()]):
    # retrieve the prolific ID from the cookie
    prolific_id = server.retrieve_prolific_id_from_cookie(session_key)
    return JSONResponse(content={"prolific_id": prolific_id})


@app.get("/data_collection")
async def data_collection_page(session_key: Annotated[str | None, Cookie()]):
    # check if this cookies has already been assigned a batch
    batch_id = server.retrieve_batch_from_cookie(session_key)
    if batch_id == None:
        batches = server.retrieve_unassigned_batches()
        if batches == []:
            batches = server.retrieve_batches()
        server.assign_batch_to_cookie(session_key, random.choice(batches))
    with open(server.data_collection, "r") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/data_collection/get_narrative")
async def elicitation_form(session_key: Annotated[str | None, Cookie()]):
    expired = server.check_if_expired(session_key)
    if expired:
        return JSONResponse(content={"narrative": "no more narratives"})
        # check if it is the first time the user is accessing the page
    if server.retrieve_first_narrative_timestamp(session_key) == None:
        print("first time")
        server.insert_first_narrative_timestamp(session_key, datetime.now())
    else:
        print("not first time")
    # get narratives from batch
    uncompleted = server.retrieve_uncompleted_narratives(session_key)
    # uncompleted.sort()
    print(uncompleted)
    if len(uncompleted) > 0:
        choice = uncompleted[0]
        narratives = server.retrieve_narrative_from_id(choice)
        json_narratives = json.loads(narratives)
        return JSONResponse(content=json_narratives)
    else:
        # if no more, expire the cookie
        expired = server.check_if_expired(session_key)
        if not expired:
            server.expire_cookie(session_key)
            completion = server.retrieve_completion_code(session_key)
            if completion == None:
                # generate completion code
                completion = server.generate_completion_code(session_key)
        return JSONResponse(content={"narrative": "no more narratives"})


@app.post("/data_collection/get_narrative")
async def elicitation_form(
    elicitation: Annotated[str, Form()],
    narrative_id: Annotated[str, Form()],
    session_key: Annotated[str | None, Cookie()],
):
    expired = server.check_if_expired(session_key)
    if expired:
        return JSONResponse(content={"narrative": "no more narratives"})
    # track the form
    server.track_completion(session_key, narrative_id, elicitation, datetime.now())
    print(narrative_id)
    # get narratives from batch
    uncompleted = server.retrieve_uncompleted_narratives(session_key)
    # uncompleted.sort()
    if len(uncompleted) > 0:
        choice = uncompleted[0]
        narratives = server.retrieve_narrative_from_id(choice)
        json_narratives = json.loads(narratives)
        return JSONResponse(content=json_narratives)
    else:
        # if no more, expire the cookie
        expired = server.check_if_expired(session_key)
        if not expired:
            # if no more, expire the cookie
            expired = server.check_if_expired(session_key)
            if not expired:
                server.expire_cookie(session_key)
                completion = server.retrieve_completion_code(session_key)
                if completion == None:
                    # generate completion code
                    completion = server.generate_completion_code(
                        session_key, datetime.now()
                    )
        return JSONResponse(content={"narrative": "no more narratives"})


@app.post("/check_cookie")
async def check_cookie(session_key: Annotated[str | None, Cookie()]):
    expired = server.check_if_expired(session_key)
    return JSONResponse(content={"expired": expired})


@app.get("/completion")
async def completion_page():
    with open(server.completion, "r") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/data_collection/get_counts")
async def get_counts(session_key: Annotated[str | None, Cookie()]):
    batch_id = server.retrieve_batch_from_cookie(session_key)
    narratives = server.retrieve_narratives_from_batch(batch_id)
    completed = server.retrieve_completed_narratives(session_key)
    return JSONResponse(
        content={
            "total": len(narratives),
            "completed": len(completed),
            "remaining": len(narratives) - len(completed),
        }
    )


@app.get("/completion/get_completion_code")
async def get_completion_code(session_key: Annotated[str | None, Cookie()]):
    # check if cookie expired
    expired = server.check_if_expired(session_key)
    if expired:
        # check if code exists
        code = server.retrieve_completion_code(session_key)
        if code == None:
            code = server.generate_completion_code(session_key, datetime.now())
    else:
        # check if they have completed all narratives
        narratives = server.retrieve_narratives_from_batch(
            server.retrieve_batch_from_cookie(session_key)
        )
        completed = server.retrieve_completed_narratives(session_key)
        if len(narratives) != len(completed):
            return JSONResponse(
                content={
                    "completion_code": "Non hai completato tutte le narrative",
                    "done": False,
                }
            )
        # check if code exists
        code = server.retrieve_completion_code(session_key)
        if code == None:
            code = server.generate_completion_code(session_key, datetime.now())
        server.expire_cookie(session_key)
    return JSONResponse(content={"completion_code": code, "done": True})


@app.get("/example")
async def example_page(session_key: Annotated[str | None, Cookie()]):
    with open(server.example, "r") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.post("/example/form")
async def example_form(
    session_key: Annotated[str | None, Cookie()],
    form_id: Annotated[str, Form()],
    flexRadioDefault: Annotated[str, Form()],
):
    server.track_example(session_key, form_id, flexRadioDefault, datetime.now())
    return JSONResponse(content={"done": True})


@app.get("/get_statistics")
async def get_statistics(session_key: str):
    expired = server.check_if_expired(session_key)
    if expired:
        data = server.retrieve_all(session_key)
        initial_timestamp = datetime.strptime(
            data["first_accessed_timestamp"], "%Y-%m-%d %H:%M:%S.%f"
        )
        first_narrative_timestamp = datetime.strptime(
            data["first_narrative_timestamp"], "%Y-%m-%d %H:%M:%S.%f"
        )
        data["guidelines_time"] = (
            first_narrative_timestamp - initial_timestamp
        ).total_seconds()
        start_time = datetime.strptime(
            data["first_narrative_timestamp"], "%Y-%m-%d %H:%M:%S.%f"
        )
        for narrative in data["narratives"]:
            narrative["tokens"] = len(narrative["narrative"]["text"].split(" "))
            end_time = datetime.strptime(
                narrative["completion_timestamp"], "%Y-%m-%d %H:%M:%S.%f"
            )
            narrative["duration"] = (end_time - start_time).total_seconds()
            start_time = end_time
            narrative["correlation"] = narrative["duration"] / narrative["tokens"]
        try:
            final_time = datetime.strptime(
                data["completion_time"], "%Y-%m-%d %H:%M:%S.%f"
            )
        except ValueError:
            final_time = end_time
        data["total_time"] = (final_time - initial_timestamp).total_seconds()
        return JSONResponse(content=data)
    else:
        return JSONResponse(content={"expired": False})


@app.get("/get_all_completed_narratives")
async def get_all_completed_narratives():
    narratives_ids = server.retrieve_all_completed_narratives()
    return JSONResponse(content=narratives_ids)


@app.get("/get_all_cookies")
async def get_all_cookies():
    cookies = server.retrieve_all_cookies()
    return JSONResponse(content=cookies)


if __name__ == "__main__":
    uvicorn.run(app, host=server.host, port=server.port)

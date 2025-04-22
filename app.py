from fastapi import FastAPI, Request, Form # type: ignore
from fastapi.responses import HTMLResponse # type: ignore
from fastapi.templating import Jinja2Templates # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore
from pydantic import BaseModel # type: ignore
from controller.main import search_track, get_token  # type: ignore

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

class YouTubeRequest(BaseModel):
    youtube_url: str
    artist_name: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search_song/")
async def search_song(request: Request, youtube_url: str = Form(...)):
    token = get_token()
    result = search_track(token, youtube_url)
    
    if "error" in result:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": result["error"]
        })
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "music": result
    })

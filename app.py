# Import necessary FastAPI modules and utilities
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from controller.main import search_track, get_token
import os

# Create FastAPI application instance
app = FastAPI()

# Set the directory for HTML templates
templates = Jinja2Templates(directory="templates")

# Mount the /static route to serve static files like CSS, JS, images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load Google Ads environment variables
GOOGLE_AD_CLIENT = os.getenv('GOOGLE_AD_CLIENT')
DATA_AD_SLOT = os.getenv("DATA_AD_SLOT")

# Pydantic model for expected JSON body (currently unused, kept for possible future use)
class YouTubeRequest(BaseModel):
    youtube_url: str
    artist_name: str

# Route for GET / — returns the home page with the search form
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "google_ad_client": GOOGLE_AD_CLIENT,
        "data_ad_slot": DATA_AD_SLOT
    })

# Route for POST /search_song/ — processes the submitted YouTube link and searches for the track
@app.post("/search_song/")
async def search_song(request: Request, youtube_url: str = Form(...)):
    token = get_token()  # Get Spotify access token
    result = search_track(token, youtube_url)  # Search the song using Spotify API

    # If an error occurred during the search, return the index page with the error message
    if "error" in result:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": result["error"],
            "google_ad_client": GOOGLE_AD_CLIENT,
            "DATA_AD_SLOT": DATA_AD_SLOT
        })
    
    # If song found, return the index page with the song info
    return templates.TemplateResponse("index.html", {
        "request": request,
        "music": result,
        "google_ad_client": GOOGLE_AD_CLIENT,
        "DATA_AD_SLOT": DATA_AD_SLOT
    })

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from controller.main import search_track, get_token, get_spotify_tracks_from_playlist, is_playlist_or_video
import os

# Create FastAPI instance
app = FastAPI()

# Set the directory for HTML templates
templates = Jinja2Templates(directory="templates")

# Mount the /static route to serve static files like CSS, JS, images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Environment variables for Google Ads
GOOGLE_AD_CLIENT = os.getenv('GOOGLE_AD_CLIENT')
DATA_AD_SLOT = os.getenv("DATA_AD_SLOT")

# Route for the home page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "google_ad_client": GOOGLE_AD_CLIENT,
        "data_ad_slot": DATA_AD_SLOT
    })

# Route to search for the song or playlist
@app.post("/search_song/")
async def search_song(request: Request, youtube_url: str = Form(...)):
    token = get_token()  # Get Spotify access token

    # Check if the URL is a playlist or a video
    content_type = is_playlist_or_video(youtube_url)
    if content_type == "playlist":
        # If it's a playlist, get the tracks from the playlist
        result = get_spotify_tracks_from_playlist(youtube_url, token)
        if "error" in result:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": result["error"],
                "google_ad_client": GOOGLE_AD_CLIENT,
                "DATA_AD_SLOT": DATA_AD_SLOT
            })
        # If the playlist is found and processed
        return templates.TemplateResponse("index.html", {
            "request": request,
            "music": result,
            "type": "playlist",  # 👈 Adicionado
            "google_ad_client": GOOGLE_AD_CLIENT,
            "DATA_AD_SLOT": DATA_AD_SLOT
        })

    # If it's a single track, search for the track
    result = search_track(token, youtube_url)
    if "error" in result:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": result["error"],
            "google_ad_client": GOOGLE_AD_CLIENT,
            "DATA_AD_SLOT": DATA_AD_SLOT
        })
    
    # If the track is found
    return templates.TemplateResponse("index.html", {
        "request": request,
        "music": result,
        "type": "track",  # 👈 Adicionado
        "google_ad_client": GOOGLE_AD_CLIENT,
        "DATA_AD_SLOT": DATA_AD_SLOT
    })

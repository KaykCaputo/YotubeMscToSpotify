import os
import json
import base64
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from dotenv import load_dotenv
from requests import post, get #type: ignore
import yt_dlp # type:ignore


client_id = os.getenv("CLIENT_ID") 
client_secret = os.getenv("CLIENT_SECRET") 


def get_token():
    for attempt in range(3):
        auth_string = client_id + ":" + client_secret
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": "Basic " + auth_base64,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}

        result = post(url, headers=headers, data=data)

        print("Status Code:", result.status_code)
        print("Response Text:", result.text)

        try:
            json_result = result.json()
            token = json_result["access_token"]
            return token
        except Exception as e:
            print("Error parsing JSON:", e)
            if attempt < 2:  # Se falhar, tenta novamente
                time.sleep(2)  # Espera 2 segundos antes de tentar de novo
            else:
                return None

def get_auth_headers(token):
    return {"Authorization": "Bearer " + token}

def search_for_artist(token, artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_headers(token=token)
    query = f"?q={artist_name}&type=artist&limit=1"
    
    query_url = url + query
    result = get(url=query_url, headers=headers)
    json_result = result.json()
    artist = json_result["artists"]["items"][0]
    return({
        "id": artist["id"],
        "name": artist["name"],
        "spotify_url": artist["external_urls"]["spotify"],
        "image": artist["images"][0]["url"]
    })
    
def search_track(token: str, youtube_url: str):
    youtube_url = convert_youtube_music_link(youtube_url)
    
    song_name = get_youtube_title(youtube_url)
    
    url = f"https://api.spotify.com/v1/search?q={song_name}&type=track&limit=1"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = get(url, headers=headers)
    data = response.json()

    if data["tracks"]["items"]:
        item = data["tracks"]["items"][0]
        return {
            "name": item["name"],
            "artist": item["artists"][0]["name"],
            "spotify_url": item["external_urls"]["spotify"],
            "image": item["album"]["images"][0]["url"] if item["album"]["images"] else None
        }
    else:
        return {"error": "Not found"}


def get_youtube_title(youtube_url: str) -> str:
    ydl_opts = {
        'quiet': True,
        'force_generic_extractor': True,
        'extract_flat': True,  
        'cookiefile': 'cookies.txt',
    }
    youtube_url = convert_youtube_music_link(youtube_url)
    print(youtube_url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        title = info.get('title', None)
        title = title.lower()
        unwanted_phrases = [
                "official video", "remix", "audio", "hd", "music video", "official",
                "-", "(", ")", "1080p", "performance", "in concert", "full", "version"
            ]
        for phrase in unwanted_phrases:
            title = title.replace(phrase, "")
        
        return title.strip()

def convert_youtube_music_link(link: str) -> str:
    parsed = urlparse(link)


    if "music.youtube.com" in parsed.netloc:
        new_netloc = "www.youtube.com"  
        query_params = parse_qs(parsed.query)
        query_params.pop("si", None)  
        new_path = f"/watch?v={query_params.get('v')[0]}"  #type: ignore

        new_url = urlunparse((
            parsed.scheme,
            new_netloc,
            new_path,
            '',
            urlencode(query_params, doseq=True),
            ''
        ))
        return new_url

    return link


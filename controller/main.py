import os
import base64
import re
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from requests import post, get #type: ignore


client_id = os.getenv("CLIENT_ID") 
client_secret = os.getenv("CLIENT_SECRET") 
api_key = os.getenv("API_KEY")

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
            if attempt < 2:  
                time.sleep(2) 
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
    
    title_and_artist = get_youtube_title_and_artist(youtube_url, get_api_key())
    song_name = title_and_artist.get("song_name")
    artist_name = title_and_artist.get("artist_name")
    
    url = f"https://api.spotify.com/v1/search?q=track:{song_name} artist:{artist_name}&type=track&limit=1"
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


def get_youtube_title_and_artist(youtube_url: str, api_key) -> dict:
    print(f"URL do YouTube: {youtube_url}")
    youtube_url = convert_youtube_music_link(youtube_url)
    video_id = get_video_id(youtube_url)
    print(f"ID do vídeo: {video_id}")
    
    url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=snippet&key={api_key}"
    print(f"URL da requisição: {url}")
    
    response = get(url)
    if response.status_code == 200:
        data = response.json()
        if 'items' in data and len(data['items']) > 0:
            title = data['items'][0]['snippet']['title']
            channel_title = data['items'][0]['snippet']['channelTitle'] 
            
            unwanted_phrases = [
                "official video", "remix", "audio", "hd", "music video", "official",
                "-", "(", ")", "1080p", "performance", "in concert", "full", "version",
                "lyrics"
            ]
            for phrase in unwanted_phrases:
                title = title.replace(phrase, "")
            title_parts = title.split('-')
            if len(title_parts) > 1:
                artist_name = title_parts[0].strip()
                song_name = title_parts[1].strip()
            else:     
                artist_name = channel_title.strip()  
                song_name = title

            return {
                "song_name": song_name,
                "artist_name": artist_name
            }
        else:
            return {"error": "No video found"}
    else:
        return {"error": f"API Error: {response.status_code}"}

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

def get_video_id(youtube_url: str) -> str:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)", youtube_url)
    if match:
        return match.group(1)
    return None # type: ignore

def get_api_key():
    return api_key

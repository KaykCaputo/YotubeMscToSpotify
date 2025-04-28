import os
import base64
import re
import time
import logging
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse
from requests import post, get  # type: ignore
from unidecode import unidecode  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Environment variables
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
api_key = os.getenv("API_KEY")

def get_token():
    for attempt in range(3):
        try:
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
            result.raise_for_status()
            json_result = result.json()
            token = json_result["access_token"]
            logging.info("Access token obtained successfully.")
            return token
        except Exception as e:
            logging.error(f"Error obtaining token (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(2)
    return None

def get_auth_headers(token):
    return {"Authorization": "Bearer " + token}

def search_for_artist(token, artist_name):
    try:
        url = "https://api.spotify.com/v1/search"
        headers = get_auth_headers(token=token)
        query = f"?q={artist_name}&type=artist&limit=1"
        query_url = url + query

        result = get(query_url, headers=headers)
        result.raise_for_status()
        artist = result.json()["artists"]["items"][0]

        logging.info(f"Found artist: {artist['name']}")
        return {
            "id": artist["id"],
            "name": artist["name"],
            "spotify_url": artist["external_urls"]["spotify"],
            "image": artist["images"][0]["url"]
        }
    except Exception as e:
        logging.error(f"Error searching for artist: {e}")
        return {"error": str(e)}

def search_track(token: str, youtube_url: str):
    youtube_url = convert_youtube_music_link(youtube_url)
    title_and_artist = get_youtube_title_and_artist(youtube_url, get_api_key())
    if isinstance(title_and_artist, dict) and "error" in title_and_artist:
        return title_and_artist

    song_name = title_and_artist.get("song_name")
    artist_name = title_and_artist.get("artist_name")
    artist_name = search_for_artist(token, artist_name).get("name", artist_name)

    headers = {"Authorization": f"Bearer {token}"}

    def build_url(query: str):
        return f"https://api.spotify.com/v1/search?q={quote_plus(query)}&type=track&limit=1"

    for query in [
        f'track:"{song_name}" artist:"{artist_name}"',
        f'track:"{song_name}"',
        f'track:{song_name}'
    ]:
        response = get(build_url(query), headers=headers)
        data = response.json()
        if data["tracks"]["items"]:
            item = data["tracks"]["items"][0]
            logging.info(f"Found track: {item['name']} by {item['artists'][0]['name']}")
            return {
                "name": item["name"],
                "artist": item["artists"][0]["name"],
                "spotify_url": item["external_urls"]["spotify"],
                "image": item["album"]["images"][0]["url"] if item["album"]["images"] else None
            }

    logging.warning(f"Track not found for: {song_name} - {artist_name}")
    return {"error": "Not found :("}

def get_youtube_title_and_artist(youtube_url: str, api_key) -> dict:
    converted = convert_youtube_music_link(youtube_url)
    if isinstance(converted, dict) and "error" in converted:
        return converted
    youtube_url = converted

    vid = get_video_id(youtube_url)
    if not isinstance(vid, str):
        return {"error": "Invalid video ID"}

    url = f"https://www.googleapis.com/youtube/v3/videos?id={vid}&part=snippet&key={api_key}"
    r = get(url)
    if r.status_code != 200:
        return {"error": f"API Error: {r.status_code}"}
    items = r.json().get("items", [])
    if not items:
        return {"error": "No video found"}

    original = items[0]["snippet"]["title"]
    original_channel = items[0]["snippet"]["channelTitle"]
    original_channel = re.sub(r"\s?- Topic$", "", original_channel).replace("VEVO", "").strip()

    channel = unidecode(original_channel.lower())
    song_name = unidecode(original)

    song_name = re.sub(rf"(?i)^{re.escape(channel)}\s*[-–:]\s*", "", song_name)
    song_name = re.sub(r"\(.*?\)", "", song_name)
    for w in channel.split():
        song_name = re.sub(rf"(?i)\b{re.escape(w)}\b", "", song_name)

    unwanted = ["official video", "remix", "audio", "hd", "music video", "official",
                "1080p", "performance", "in concert", "full", "lyrics", "video", "clipe",
                "oficial", "[", "]", "(", ")", "'", "|", ":", original_channel, channel, ","]
    for w in unwanted:
        song_name = re.sub(rf"(?i)\b{re.escape(w)}\b", "", song_name)

    song_name = re.sub(r"[-_]", " ", song_name)
    song_name = re.sub(r"\s{2,}", " ", song_name).strip()

    logging.info(f"Extracted song: '{song_name}' by '{original_channel}'")
    return {"artist_name": original_channel, "song_name": song_name}

def convert_youtube_music_link(link: str) -> str | dict:
    if not ("music.youtube.com" in link or "youtube.com" in link or "youtu.be" in link):
        return {"error": "Invalid URL"}

    parsed = urlparse(link)

    if "music.youtube.com" in parsed.netloc:
        query_params = parse_qs(parsed.query)
        v = query_params.get("v")
        if not v:
            return {"error": "Invalid YouTube Music link"}
        new_query = urlencode({"v": v[0]})
        parsed = parsed._replace(
            netloc="www.youtube.com",
            path="/watch",
            query=new_query
        )
        return urlunparse(parsed)

    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip('/')
        return f"https://www.youtube.com/watch?v={video_id}"

    return link

def get_video_id(youtube_url: str) -> str:
    match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[&?]|$)", youtube_url)
    if match:
        return match.group(1)

    match_youtu_be = re.search(r"youtu.be/([0-9A-Za-z_-]{11})", youtube_url)
    if match_youtu_be:
        return match_youtu_be.group(1)

    return None  # type: ignore

def get_playlist_id(youtube_url: str) -> str:
    match = re.search(r"(?:list=|/)([0-9A-Za-z_-]{11})(?:[&?]|$)", youtube_url)
    if match:
        return match.group(1)

    return None  # type: ignore

def get_playlist_items(playlist_id: str, api_key: str, max_results: int = 50) -> list:
    videos = []
    base_url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": max_results,
        "key": api_key
    }

    while True:
        response = get(base_url, params=params)
        if response.status_code != 200:
            return {"error": f"API Error: {response.status_code}"}

        data = response.json()
        for item in data.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "channelTitle": snippet["channelTitle"]
            })

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        params["pageToken"] = next_page_token

    logging.info(f"Fetched {len(videos)} videos from playlist.")
    return videos

def is_playlist_or_video(url: str):
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    if parsed.path.startswith("/watch") and "v" in query_params:
        logging.info("Detected YouTube video URL.")
        return "video"
    elif parsed.path.startswith("/playlist") and "list" in query_params:
        logging.info("Detected YouTube playlist URL.")
        return "playlist"
    else:
        logging.warning("Invalid YouTube URL.")
        return "invalid"

def get_api_key():
    return api_key

def get_spotify_tracks_from_playlist(url: str, token: str) -> list:
    if is_playlist_or_video(url) == "playlist":
        playlist_id = get_playlist_id(url)
        if not playlist_id:
            return {"error": "Invalid playlist URL"}

        youtube_videos = get_playlist_items(playlist_id, get_api_key())
        if isinstance(youtube_videos, dict) and "error" in youtube_videos:
            return youtube_videos

        spotify_tracks = []
        for video in youtube_videos:
            youtube_url = f"https://www.youtube.com/watch?v={video['video_id']}"
            track = search_track(token, youtube_url)
            if "error" not in track:
                spotify_tracks.append(track)
        logging.info(f"Successfully mapped {len(spotify_tracks)} tracks from YouTube to Spotify.")
        return spotify_tracks
    else:
        return {"error": "Provided URL is not a playlist."}

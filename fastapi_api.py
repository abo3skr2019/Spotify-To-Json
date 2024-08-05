# mainapi_fastapi.py

import logging
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import csv
import io

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log_file_handler = logging.FileHandler('app.log')
log_file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file_handler.setFormatter(formatter)
logger.addHandler(log_file_handler)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
SCOPE = 'playlist-read-private user-library-read'
sp_oauth = SpotifyOAuth(client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=REDIRECT_URI,
                        scope=SCOPE)

def fetch_tracks(sp, fetch_method, availability, market, *args):
    tracks = []
    try:
        results = fetch_method(*args, market=market)
        while results:
            for item in results['items']:
                track = item['track'] if 'track' in item else item
                if availability == 'all' or (availability == 'unavailable' and not track['is_playable']):
                    tracks.append(track)
            results = sp.next(results) if results['next'] else None
    except Exception as e:
        logger.error(f"Error fetching tracks: {e}")
    return tracks

def get_token(session: dict):
    logger.info(f"Getting token from session {session.get('token_info')}")
    token_info = session.get('token_info', None)
    if not token_info:
        logger.info("No token_info found in session")
        return None

    if sp_oauth.is_token_expired(token_info):
        logger.info("Token expired, refreshing token")
        try:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info
            logger.info("Token refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    return token_info

@app.get("/index")
async def index():
    return {"message": "Welcome to the FastAPI Spotify API"}

@app.get("/unavailable_tracks")
async def unavailable_tracks(request: Request):
    session = request.session
    token_info = get_token(session)
    if not token_info:
        return JSONResponse({"redirect": "/login"}, status_code=401)

    sp = Spotify(auth=token_info['access_token'])
    source = request.query_params.get('source', 'liked')
    availability = request.query_params.get('availability', 'unavailable')
    market = request.query_params.get('market', 'SA')

    logger.info(f"Received query parameters - Source: {source}, Availability: {availability}, Market: {market}")

    tracks = []

    try:
        if source in ['playlist', 'both']:
            playlists = sp.current_user_playlists()
            for playlist in playlists['items']:
                playlist_tracks = fetch_tracks(sp, sp.playlist_tracks, availability, market, playlist['id'])
                tracks.extend(playlist_tracks)

        if source in ['liked', 'both']:
            saved_tracks = fetch_tracks(sp, sp.current_user_saved_tracks, availability, market)
            tracks.extend(saved_tracks)

    except Exception as e:
        logger.error(f"Error fetching tracks: {e}")
        return JSONResponse({"error": "Unable to fetch tracks"}, status_code=500)

    try:
        logger.info("Starting to write tracks to CSV")
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['Artist', 'Title', 'Album', 'Length'])
        for track in tracks:
            artist_names = ', '.join([artist['name'] for artist in track['artists']])
            title = track['name']
            album = track['album']['name']
            length = track['duration_ms'] // 1000
            writer.writerow([artist_names, title, album, length])
        
        csv_file.seek(0)
        logger.info("Finished writing tracks to CSV")

    except Exception as e:
        logger.error(f"Error writing tracks to CSV: {e}")
        return JSONResponse({"error": "Unable to fetch tracks"}, status_code=500)

    try:
        return StreamingResponse(io.BytesIO(csv_file.getvalue().encode()), media_type='text/csv', headers={"Content-Disposition": "attachment; filename=unavailable_tracks.csv"})
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        return JSONResponse({"error": "Unable to send file"}, status_code=500)

@app.get("/")
async def login():
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)

@app.get("/callback")
async def callback(request: Request):
    code = request.query_params.get('code')
    try:
        token_info = sp_oauth.get_access_token(code)
        request.session['token_info'] = token_info
    except Exception as e:
        logger.error(f"Error during callback: {e}")
        return RedirectResponse('/')

    return RedirectResponse('/unavailable_tracks')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
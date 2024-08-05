import logging
from flask import Flask, request, redirect, session, url_for, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create a file handler
log_file_handler = logging.FileHandler('app.log')
log_file_handler.setLevel(logging.INFO)

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(log_file_handler)

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
app.secret_key = os.getenv('SECRET_KEY')
app.config['SESSION_COOKIE_NAME'] = 'Spotify Login Session'

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
SCOPE = 'playlist-read-private user-library-read'
sp_oauth = SpotifyOAuth(client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=REDIRECT_URI,
                        scope=SCOPE)

def fetch_tracks(sp, fetch_method, availability, *args):
    tracks = []
    try:
        results = fetch_method(*args)
        while results:
            for item in results['items']:
                track = item['track'] if 'track' in item else item
                if availability == 'unavailable' and not track['is_playable']:
                    tracks.append(track)
                elif availability == 'all':
                    tracks.append(track)
            results = sp.next(results) if results['next'] else None
    except Exception as e:
        logger.error(f"Error fetching tracks: {e}")
    return tracks

def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    return token_info

@app.route('/unavailable_tracks')
def unavailable_tracks():
    token_info = get_token()
    if not token_info:
        return jsonify({"redirect": url_for('login', _external=True)}), 401

    sp = spotipy.Spotify(auth=token_info['access_token'])
    source = request.args.get('source', 'both')
    availability = request.args.get('availability', 'unavailable')
    tracks = []

    try:
        if source in ['playlist', 'both']:
            playlists = sp.current_user_playlists()
            for playlist in playlists['items']:
                playlist_tracks = fetch_tracks(sp, sp.playlist_tracks, availability, playlist['id'])
                tracks.extend(playlist_tracks)

        if source in ['liked', 'both']:
            saved_tracks = fetch_tracks(sp, sp.current_user_saved_tracks, availability)
            tracks.extend(saved_tracks)

    except Exception as e:
        logger.error(f"Error fetching tracks: {e}")
        return jsonify({"error": "Unable to fetch tracks"}), 500

    return jsonify(tracks)

@app.route('/')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    try:
        token_info = sp_oauth.get_cached_token(code)
        session['token_info'] = token_info
    except Exception as e:
        logger.error(f"Error during callback: {e}")
        return redirect('/')

    return redirect(url_for('unavailable_tracks'))

if __name__ == "__main__":
    app.run(debug=True, port=os.getenv('PORT', 5000))
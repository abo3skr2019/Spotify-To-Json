import logging
from flask import Flask, request, redirect, session, url_for, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
app.secret_key = os.getenv('SECRET_KEY')
app.config['SESSION_COOKIE_NAME'] = 'Spotify Login Session'

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/callback'
SCOPE = 'playlist-read-private user-library-read'
sp_oauth = SpotifyOAuth(client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=REDIRECT_URI,
                        scope=SCOPE)

def fetch_unavailable_tracks(sp, fetch_method, *args):
    unavailable_tracks = []
    try:
        results = fetch_method(*args)
        while results:
            for item in results['items']:
                track = item['track'] if 'track' in item else item
                if not track['is_playable']:
                    unavailable_tracks.append(track)
            results = sp.next(results) if results['next'] else None
    except Exception as e:
        logger.error(f"Error fetching tracks: {e}")
    return unavailable_tracks

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
        print(url_for('login', _external=True))
        return jsonify({"redirect": url_for('login', _external=True)}), 401

    sp = spotipy.Spotify(auth=token_info['access_token'])
    unavailable_tracks = []

    try:
        playlists = sp.current_user_playlists()
        for playlist in playlists['items']:
            tracks = fetch_unavailable_tracks(sp, sp.playlist_tracks, playlist['id'])
            unavailable_tracks.extend(tracks)

        saved_tracks = fetch_unavailable_tracks(sp, sp.current_user_saved_tracks)
        unavailable_tracks.extend(saved_tracks)

    except Exception as e:
        logger.error(f"Error fetching unavailable tracks: {e}")
        return jsonify({"error": "Unable to fetch tracks"}), 500

    return jsonify(unavailable_tracks)

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

    return redirect(url_for('get_playlists'))

@app.route('/get_playlists')
def get_playlists():
    token_info = get_token()
    if not token_info:
        print(url_for('login', _external=True))
        return jsonify({"redirect": url_for('login', _external=True)}), 401

    sp = spotipy.Spotify(auth=token_info['access_token'])
    try:
        playlists = sp.current_user_playlists()
    except Exception as e:
        logger.error(f"Error fetching playlists: {e}")
        return jsonify({"error": "Unable to fetch playlists"}), 500

    return jsonify(playlists)

if __name__ == "__main__":
    app.run(debug=True)
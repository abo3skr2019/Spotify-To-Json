import logging
from flask import Flask, request, redirect, session, url_for, jsonify, render_template, send_file
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from flask_cors import CORS
from dotenv import load_dotenv
import csv
import io

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
app.config['SESSION_COOKIE_HTTPONLY'] = False  # Allow JavaScript to access the cookie

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

def get_token():
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

@app.route('/index')
def index():
    return render_template(os.path.join('index.html'))

@app.route('/unavailable_tracks')
def unavailable_tracks():
    token_info = get_token()
    if not token_info:
        return jsonify({"redirect": url_for('login', _external=True)}), 401

    sp = spotipy.Spotify(auth=token_info['access_token'])
    source = request.args.get('source', 'liked')
    availability = request.args.get('availability', 'unavailable')
    market = request.args.get('market', 'SA')  # Default market to 'US' if not provided

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
        return jsonify({"error": "Unable to fetch tracks"}), 500

    # Write tracks to CSV in memory
    try:
        logger.info("Starting to write tracks to CSV")
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['Artist', 'Title', 'Album', 'Length'])
        for track in tracks:
            artist_names = ', '.join([artist['name'] for artist in track['artists']])
            title = track['name']
            album = track['album']['name']
            length = track['duration_ms'] // 1000  # Convert milliseconds to seconds
            writer.writerow([artist_names, title, album, length])
        
        csv_file.seek(0)
        logger.info("Finished writing tracks to CSV")

    except Exception as e:
        logger.error(f"Error writing tracks to CSV: {e}")
        return jsonify({"error": "Unable to fetch tracks"}), 500

    try:
        return send_file(io.BytesIO(csv_file.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='unavailable_tracks.csv')
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        return jsonify({"error": "Unable to send file"}), 500
            
@app.route('/')
def login():
    next_url = request.args.get('next')
    auth_url = sp_oauth.get_authorize_url()
    if next_url:
        auth_url += f"&next={next_url}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    next_url = request.args.get('next')
    try:
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
    except Exception as e:
        logger.error(f"Error during callback: {e}")
        return redirect('/')

    if next_url:
        return redirect(next_url)
    return redirect(url_for('unavailable_tracks'))

if __name__ == "__main__":
    app.run(debug=True, port=os.getenv('PORT', 5000))
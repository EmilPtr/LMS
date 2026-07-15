import os
import json
import sys
import re
from moviepy import VideoFileClip
from mutagen import File as MutagenFile
from config import get_sources

MANIFEST_FILE = "manifest.json"
SUPPORTED_MOVIE_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm')
SUPPORTED_AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.wav', '.ogg')
SUPPORTED_COVER_FILENAMES = ('cover.jpg', 'cover.jpeg', 'cover.png')
SUPPORTED_THUMBNAIL_EXTENSIONS = ('.jpg', '.jpeg', '.png')

def get_video_duration(file_path):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    try:
        with VideoFileClip(file_path) as video:
            duration = int(video.duration)
            return duration
    except Exception:
        return 0
    finally:
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr

def get_audio_duration(file_path):
    try:
        audio = MutagenFile(file_path)
        if audio and audio.info:
            return int(audio.info.length)
    except Exception:
        pass
    return 0

def convert_to_media_url(file_path, source_name, source_path):
    if not file_path:
        return None
    # Get the relative path from the source root
    try:
        # Use relpath to find path relative to source directory
        relative_path = os.path.relpath(file_path, source_path)
        # Convert any Windows backslashes to forward slashes for URLs
        relative_path = relative_path.replace(os.sep, '/')
        # Return the formatted URL
        return f"/media/{source_name}/{relative_path}"
    except ValueError:
        return None # If it's not relative to the source

def find_thumbnail(thumbnails_dir, movie_name):
    if not os.path.exists(thumbnails_dir) or not os.path.isdir(thumbnails_dir):
        return None
    
    for ext in SUPPORTED_THUMBNAIL_EXTENSIONS:
        thumb_path = os.path.join(thumbnails_dir, movie_name + ext)
        if os.path.exists(thumb_path):
            return os.path.abspath(thumb_path)
    return None

def find_subtitles(video_path, source_name, source_path):
    subtitles = []
    video_dir = os.path.dirname(video_path)
    video_filename = os.path.basename(video_path)
    video_base, _ = os.path.splitext(video_filename)
    
    if not os.path.exists(video_dir):
        return subtitles
        
    for filename in os.listdir(video_dir):
        file_path = os.path.join(video_dir, filename)
        if not os.path.isfile(file_path):
            continue
            
        # Look for subtitle files associated with this video
        # e.g., MyVideo.vtt, MyVideo.en.vtt, MyVideo.ja.vtt
        if filename.lower().startswith(video_base.lower() + ".") and filename.lower().endswith('.vtt'):
            suffix = filename[len(video_base):] # ".en.vtt" or ".vtt"
            if suffix.lower().endswith('.vtt'):
                part = suffix[:-4] # remove .vtt
                if part.startswith('.'):
                    code = part[1:].lower()
                else:
                    code = 'en' # default code
            else:
                code = 'en'
                
            if not code:
                code = 'en'
                
            language_map = {
                'en': 'English',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'it': 'Italian',
                'ja': 'Japanese',
                'ko': 'Korean',
                'zh': 'Chinese',
                'pt': 'Portuguese',
                'ru': 'Russian',
                'ar': 'Arabic',
                'hi': 'Hindi',
                'nl': 'Dutch',
                'sv': 'Swedish',
                'no': 'Norwegian',
                'da': 'Danish',
                'fi': 'Finnish',
                'pl': 'Polish',
                'tr': 'Turkish',
            }
            language = language_map.get(code.lower(), code.upper())
            
            sub_url = convert_to_media_url(os.path.abspath(file_path), source_name, source_path)
            if sub_url:
                subtitles.append({
                    "language": language,
                    "code": code,
                    "location": sub_url
                })
                print(f"[OK] Located subtitle track: {language} ({code}) -> {sub_url}")
                
    return subtitles

def scan_movies():
    sources = get_sources()
    movies = []

    for source_name, source_path in sources.items():
        movies_dir = os.path.join(source_path, "Movies")
        thumbnails_dir = os.path.join(movies_dir, "Thumbnails")
        if not os.path.exists(thumbnails_dir) or not os.path.isdir(thumbnails_dir):
            print(f"[ERROR] No Thumbnails directory found in '{source_name}'")
            
        # Check if movie dir exists
        if os.path.exists(movies_dir) and os.path.isdir(movies_dir):
            print(f"Scanning movies in: {movies_dir}")

            # Scan movie folder
            for filename in os.listdir(movies_dir):
                file_path = os.path.abspath(os.path.join(movies_dir, filename))
                
                # Validate file
                if os.path.isfile(file_path) and filename.lower().endswith(SUPPORTED_MOVIE_EXTENSIONS):

                    # Gather information
                    name = os.path.splitext(filename)[0]
                    movie_id = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
                    duration = get_video_duration(file_path)
                    thumbnail_path = find_thumbnail(thumbnails_dir, name)
                    
                    media_location = convert_to_media_url(file_path, source_name, source_path)
                    thumbnail = convert_to_media_url(thumbnail_path, source_name, source_path)

                    if thumbnail: print(f"[OK] Thumbnail located in '{thumbnail}'")
                    else: print(f"[WARN] Thumbnail not found for {name}")

                    # Add to manifest
                    subtitles = find_subtitles(file_path, source_name, source_path)
                    movies.append({
                        "id": movie_id,
                        "name": name,
                        "location": media_location,
                        "length": duration,
                        "thumbnail": thumbnail,
                        "subtitles": subtitles
                    })

                    print(f"[OK] Added Movie: {name} from source '{source_name}'")
                elif not filename == "Thumbnails": print(f"[WARN] Invalid file at {file_path}")
        else: print(f"[ERROR] No Movies directory found in {source_name}")
    return movies

def scan_music():
    sources = get_sources()
    releases = []

    for source_name, source_path in sources.items():
        music_dir = os.path.join(source_path, "Music")
        if os.path.exists(music_dir) and os.path.isdir(music_dir):
            print(f"Scanning music in: {music_dir}")
            # Every immediate subdirectory is a release
            for release_folder in os.listdir(music_dir):
                release_path = os.path.join(music_dir, release_folder)
                if os.path.isdir(release_path):
                    print(f"[OK] Found Release: {release_folder} from source '{source_name}'")
                    
                    # Find cover image
                    cover_path = None
                    for filename in os.listdir(release_path):
                        if filename.lower() in SUPPORTED_COVER_FILENAMES:
                            cover_path = os.path.abspath(os.path.join(release_path, filename))
                            print(f"[OK] Cover image located in '{cover_path}'")
                            break
                    if cover_path == None: print(f"[WARN] Cover file not found in {release_path}")

                    cover_url = convert_to_media_url(cover_path, source_name, source_path)

                    songs = []
                    # Scan for audio files in release folder
                    for filename in os.listdir(release_path):
                        file_path = os.path.abspath(os.path.join(release_path, filename))
                        if os.path.isfile(file_path) and filename.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS):
                            name = os.path.splitext(filename)[0]
                            duration = get_audio_duration(file_path)
                            song_url = convert_to_media_url(file_path, source_name, source_path)
                            songs.append({
                                "name": name,
                                "location": song_url,
                                "duration": duration
                            })
                            print(f"[OK] Added song for {release_folder}: '{name}'")
                        elif os.path.isfile(file_path) and not filename.lower().endswith(SUPPORTED_COVER_FILENAMES): print(f"[WARN] Invalid file at {file_path}")
                    
                    if songs: # Only add release if it has songs
                        release_id = re.sub(r'[^a-zA-Z0-9]+', '-', release_folder.lower()).strip('-')
                        releases.append({
                            "id": release_id,
                            "name": release_folder,
                            "cover": cover_url,
                            "songs": songs
                        })
                else: print(f"[ERROR] {release_path} is not a Directory")
        else: print(f"[ERROR] No Music directory found in {source_name}")
    return releases

def scan_shows():
    sources = get_sources()
    shows = []

    for source_name, source_path in sources.items():
        shows_dir = os.path.join(source_path, "Shows")
        if os.path.exists(shows_dir) and os.path.isdir(shows_dir):
            print(f"Scanning shows in: {shows_dir}")
            
            # Every subdirectory inside Shows represents a show
            for show_folder in os.listdir(shows_dir):
                show_path = os.path.join(shows_dir, show_folder)
                if os.path.isdir(show_path):
                    print(f"[OK] Found Show: {show_folder} from source '{source_name}'")
                    
                    # 1. Search for thumbnail
                    thumbnail_file = None
                    for ext in SUPPORTED_THUMBNAIL_EXTENSIONS:
                        thumb_name = "thumbnail" + ext
                        thumb_path = os.path.join(show_path, thumb_name)
                        if os.path.exists(thumb_path):
                            thumbnail_file = os.path.abspath(thumb_path)
                            break
                    
                    thumbnail_url = convert_to_media_url(thumbnail_file, source_name, source_path)
                    if thumbnail_url:
                        print(f"[OK] Show thumbnail located in '{thumbnail_url}'")
                    else:
                        print(f"[WARN] Thumbnail not found for show {show_folder}")
                        
                    # 2. Find and sort seasons S1, S2, etc.
                    seasons_dict = {}
                    for item in os.listdir(show_path):
                        item_path = os.path.join(show_path, item)
                        if os.path.isdir(item_path):
                            match = re.match(r'^S(\d+)$', item, re.IGNORECASE)
                            if match:
                                season_num = int(match.group(1))
                                seasons_dict[season_num] = item_path
                                
                    # Sort seasons numerically
                    sorted_seasons = sorted(seasons_dict.keys())
                    seasons_list = []
                    
                    for season_num in sorted_seasons:
                        season_path = seasons_dict[season_num]
                        episodes = []
                        
                        # Find all files with supported video extensions inside the season dir
                        files_in_season = []
                        for filename in os.listdir(season_path):
                            file_path = os.path.abspath(os.path.join(season_path, filename))
                            if os.path.isfile(file_path) and filename.lower().endswith(SUPPORTED_MOVIE_EXTENSIONS):
                                files_in_season.append(filename)
                                
                        # Sort episodes alphabetically
                        files_in_season.sort()
                        
                        for index, filename in enumerate(files_in_season):
                            file_path = os.path.abspath(os.path.join(season_path, filename))
                            episode_num = index + 1
                            episode_name = f"{show_folder} - S{season_num}E{episode_num}"
                            episode_url = convert_to_media_url(file_path, source_name, source_path)
                            subtitles = find_subtitles(file_path, source_name, source_path)
                            
                            episodes.append({
                                "name": episode_name,
                                "location": episode_url,
                                "subtitles": subtitles
                            })
                            print(f"[OK] Added episode: '{episode_name}'")
                            
                        if episodes:
                            seasons_list.append({
                                "season": season_num,
                                "episodes": episodes
                            })
                    
                    shows.append({
                        "name": show_folder,
                        "thumbnail": thumbnail_url,
                        "seasons": seasons_list
                    })
                else:
                    print(f"[ERROR] {show_path} is not a Directory")
        else:
            print(f"[ERROR] No Shows directory found in {source_name}")
            
    return shows

def generate_manifest():
    manifest = {}

    # Scan movies
    manifest["movies"] = scan_movies()
    
    # Scan music
    manifest["releases"] = scan_music()
    
    # Scan shows
    manifest["shows"] = scan_shows()

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=4)
    
    print(f"Successfully generated {MANIFEST_FILE}")

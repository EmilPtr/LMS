import os
import json
import sys
from moviepy import VideoFileClip
from mutagen import File as MutagenFile
from config import get_sources

MANIFEST_FILE = "web/manifest.json"
SUPPORTED_MOVIE_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv')
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

def find_thumbnail(thumbnails_dir, movie_name):
    if not os.path.exists(thumbnails_dir) or not os.path.isdir(thumbnails_dir):
        return None
    
    for ext in SUPPORTED_THUMBNAIL_EXTENSIONS:
        thumb_path = os.path.join(thumbnails_dir, movie_name + ext)
        if os.path.exists(thumb_path):
            return os.path.abspath(thumb_path)
    return None

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
                    duration = get_video_duration(file_path)
                    thumbnail = find_thumbnail(thumbnails_dir, name)
                    if thumbnail: print(f"[OK] Thumbnail located in '{thumbnail}'")
                    else: print(f"[WARN] Thumbnail not found for {name}")

                    # Add to manifest
                    movies.append({
                        "name": name,
                        "location": file_path,
                        "length": duration,
                        "thumbnail": thumbnail
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

                    songs = []
                    # Scan for audio files in release folder
                    for filename in os.listdir(release_path):
                        file_path = os.path.abspath(os.path.join(release_path, filename))
                        if os.path.isfile(file_path) and filename.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS):
                            name = os.path.splitext(filename)[0]
                            duration = get_audio_duration(file_path)
                            songs.append({
                                "name": name,
                                "location": file_path,
                                "duration": duration
                            })
                            print(f"[OK] Added song for {release_folder}: '{name}'")
                        elif os.path.isfile(file_path) and not filename.lower().endswith(SUPPORTED_COVER_FILENAMES): print(f"[WARN] Invalid file at {file_path}")
                    
                    if songs: # Only add release if it has songs
                        releases.append({
                            "name": release_folder,
                            "cover": cover_path,
                            "songs": songs
                        })
                else: print(f"[ERROR] {release_path} is not a Directory")
        else: print(f"[ERROR] No Music directory found in {source_name}")
    return releases

def generate_manifest():
    manifest = {}

    # Scan movies
    manifest["movies"] = scan_movies()
    
    # Scan music
    manifest["releases"] = scan_music()

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=4)
    
    print(f"Successfully generated {MANIFEST_FILE}")

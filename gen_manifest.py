import os
import json
import sys
import re
from pathlib import Path
from moviepy import VideoFileClip
from mutagen import File as MutagenFile
from config import get_sources
from paths import MANIFEST_FILE, LMS_HOME

SUPPORTED_MOVIE_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm')
SUPPORTED_AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.wav', '.ogg')
SUPPORTED_COVER_FILENAMES = ('cover.jpg', 'cover.jpeg', 'cover.png')
SUPPORTED_THUMBNAIL_EXTENSIONS = ('.jpg', '.jpeg', '.png')
SUPPORTED_SUBTITLE_EXTENSIONS = ('.vtt', '.srt')

def get_video_duration(file_path):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    try:
        # moviepy expects a string path
        with VideoFileClip(str(file_path)) as video:
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
        audio = MutagenFile(str(file_path))
        if audio and audio.info:
            return int(audio.info.length)
    except Exception:
        pass
    return 0

def convert_to_media_url(file_path, source_name, source_path):
    if not file_path:
        return None
    try:
        # Ensure we're working with Path objects
        file_path = Path(file_path).resolve()
        source_path = Path(source_path).resolve()
        
        # Get the relative path from the source root
        relative_path = file_path.relative_to(source_path)
        # Path.as_posix() converts to forward slashes
        return f"/media/{source_name}/{relative_path.as_posix()}"
    except (ValueError, Exception):
        return None

def find_thumbnail(thumbnails_dir, movie_name):
    thumbnails_dir = Path(thumbnails_dir)
    if not thumbnails_dir.exists() or not thumbnails_dir.is_dir():
        return None
    
    for ext in SUPPORTED_THUMBNAIL_EXTENSIONS:
        thumb_path = thumbnails_dir / (movie_name + ext)
        if thumb_path.exists():
            return thumb_path.resolve()
    return None

def find_subtitles(video_path, source_name, source_path):
    subtitles = []
    video_path = Path(video_path)
    video_dir = video_path.parent
    video_base = video_path.stem
    
    if not video_dir.exists():
        return subtitles
        
    for item in video_dir.iterdir():
        if not item.is_file():
            continue
            
        filename = item.name
        # Look for subtitle files associated with this video
        # e.g., MyVideo.vtt, MyVideo.en.vtt, MyVideo.ja.vtt, MyVideo.srt
        if filename.lower().startswith(video_base.lower() + ".") and item.suffix.lower() in SUPPORTED_SUBTITLE_EXTENSIONS:
            suffix = filename[len(video_base):] # ".en.vtt" or ".vtt" or ".srt"
            
            # Extract parts between dots
            parts = suffix.split('.')
            # parts will be like ['', 'en', 'vtt'] or ['', 'vtt']
            if len(parts) >= 3:
                code = parts[1].lower()
            else:
                code = 'en'
                
            if not code:
                code = 'en'
                
            language_map = {
                'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese',
                'pt': 'Portuguese', 'ru': 'Russian', 'ar': 'Arabic', 'hi': 'Hindi',
                'nl': 'Dutch', 'sv': 'Swedish', 'no': 'Norwegian', 'da': 'Danish',
                'fi': 'Finnish', 'pl': 'Polish', 'tr': 'Turkish',
            }
            language = language_map.get(code.lower(), code.upper())
            
            sub_url = convert_to_media_url(item, source_name, source_path)
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
        source_path = Path(source_path)
        movies_dir = source_path / "Movies"
        thumbnails_dir = movies_dir / "Thumbnails"
        
        if not thumbnails_dir.exists() or not thumbnails_dir.is_dir():
            print(f"[ERROR] No Thumbnails directory found in '{source_name}'")
            
        if movies_dir.exists() and movies_dir.is_dir():
            print(f"Scanning movies in: {movies_dir}")

            for item in movies_dir.iterdir():
                if item.is_file() and item.suffix.lower() in SUPPORTED_MOVIE_EXTENSIONS:
                    name = item.stem
                    movie_id = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
                    duration = get_video_duration(item)
                    thumbnail_path = find_thumbnail(thumbnails_dir, name)
                    
                    media_location = convert_to_media_url(item, source_name, source_path)
                    thumbnail = convert_to_media_url(thumbnail_path, source_name, source_path)

                    if thumbnail: print(f"[OK] Thumbnail located in '{thumbnail}'")
                    else: print(f"[WARN] Thumbnail not found for {name}")

                    subtitles = find_subtitles(item, source_name, source_path)
                    movies.append({
                        "id": movie_id,
                        "name": name,
                        "location": media_location,
                        "length": duration,
                        "thumbnail": thumbnail,
                        "subtitles": subtitles
                    })

                    print(f"[OK] Added Movie: {name} from source '{source_name}'")
                elif item.is_file() and item.name != "Thumbnails" and item.suffix.lower() not in SUPPORTED_SUBTITLE_EXTENSIONS:
                    print(f"[WARN] Invalid file at {item}")
        else: print(f"[ERROR] No Movies directory found in {source_name}")
    return movies

def scan_music():
    sources = get_sources()
    releases = []

    for source_name, source_path in sources.items():
        source_path = Path(source_path)
        music_dir = source_path / "Music"
        if music_dir.exists() and music_dir.is_dir():
            print(f"Scanning music in: {music_dir}")
            for release_folder in music_dir.iterdir():
                if release_folder.is_dir():
                    print(f"[OK] Found Release: {release_folder.name} from source '{source_name}'")
                    
                    cover_path = None
                    for item in release_folder.iterdir():
                        if item.is_file() and item.name.lower() in SUPPORTED_COVER_FILENAMES:
                            cover_path = item.resolve()
                            print(f"[OK] Cover image located in '{cover_path}'")
                            break
                    if cover_path is None: print(f"[WARN] Cover file not found in {release_folder}")

                    cover_url = convert_to_media_url(cover_path, source_name, source_path)

                    songs = []
                    for item in release_folder.iterdir():
                        if item.is_file() and item.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
                            name = item.stem
                            duration = get_audio_duration(item)
                            song_url = convert_to_media_url(item, source_name, source_path)
                            songs.append({
                                "name": name,
                                "location": song_url,
                                "duration": duration
                            })
                            print(f"[OK] Added song for {release_folder.name}: '{name}'")
                        elif item.is_file() and item.name.lower() not in SUPPORTED_COVER_FILENAMES:
                            print(f"[WARN] Invalid file at {item}")
                    
                    if songs:
                        release_id = re.sub(r'[^a-zA-Z0-9]+', '-', release_folder.name.lower()).strip('-')
                        releases.append({
                            "id": release_id,
                            "name": release_folder.name,
                            "cover": cover_url,
                            "songs": songs
                        })
                else: print(f"[ERROR] {release_folder} is not a Directory")
        else: print(f"[ERROR] No Music directory found in {source_name}")
    return releases

def scan_shows():
    sources = get_sources()
    shows = []

    for source_name, source_path in sources.items():
        source_path = Path(source_path)
        shows_dir = source_path / "Shows"
        if shows_dir.exists() and shows_dir.is_dir():
            print(f"Scanning shows in: {shows_dir}")
            
            for show_folder in shows_dir.iterdir():
                if show_folder.is_dir():
                    print(f"[OK] Found Show: {show_folder.name} from source '{source_name}'")
                    
                    thumbnail_file = None
                    for ext in SUPPORTED_THUMBNAIL_EXTENSIONS:
                        thumb_name = "thumbnail" + ext
                        thumb_path = show_folder / thumb_name
                        if thumb_path.exists():
                            thumbnail_file = thumb_path.resolve()
                            break
                    
                    thumbnail_url = convert_to_media_url(thumbnail_file, source_name, source_path)
                    if thumbnail_url:
                        print(f"[OK] Show thumbnail located in '{thumbnail_url}'")
                    else:
                        print(f"[WARN] Thumbnail not found for show {show_folder.name}")
                        
                    seasons_dict = {}
                    for item in show_folder.iterdir():
                        if item.is_dir():
                            match = re.match(r'^S(\d+)$', item.name, re.IGNORECASE)
                            if match:
                                season_num = int(match.group(1))
                                seasons_dict[season_num] = item
                                
                    sorted_seasons = sorted(seasons_dict.keys())
                    seasons_list = []
                    
                    for season_num in sorted_seasons:
                        season_path = seasons_dict[season_num]
                        episodes = []
                        
                        files_in_season = []
                        for item in season_path.iterdir():
                            if item.is_file() and item.suffix.lower() in SUPPORTED_MOVIE_EXTENSIONS:
                                files_in_season.append(item.name)
                                
                        files_in_season.sort()
                        
                        for index, filename in enumerate(files_in_season):
                            item = season_path / filename
                            episode_num = index + 1
                            episode_name = f"{show_folder.name} - S{season_num}E{episode_num}"
                            episode_url = convert_to_media_url(item, source_name, source_path)
                            subtitles = find_subtitles(item, source_name, source_path)
                            
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
                        "name": show_folder.name,
                        "thumbnail": thumbnail_url,
                        "seasons": seasons_list
                    })
                else:
                    print(f"[ERROR] {show_folder} is not a Directory")
        else:
            print(f"[ERROR] No Shows directory found in {source_name}")
            
    return shows

def generate_manifest():
    manifest = {}
    manifest["movies"] = scan_movies()
    manifest["releases"] = scan_music()
    manifest["shows"] = scan_shows()

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=4)
    
    print(f"Successfully generated {MANIFEST_FILE}")
    return manifest

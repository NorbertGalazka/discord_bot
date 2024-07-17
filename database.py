import sqlite3
import re
import unicodedata




def normalize_text(text):
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text.lower()


def init_db():
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS main_playlist (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def create_playlist(playlist_name):
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {playlist_name} (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def get_all_playlists():
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';
    ''')
    playlists = cursor.fetchall()

    playlist_counts = []
    for playlist in playlists:
        playlist_name = playlist[0]
        cursor.execute(f'SELECT COUNT(*) FROM {playlist_name}')
        song_count = cursor.fetchone()[0]
        playlist_counts.append((playlist_name, song_count))

    conn.close()
    return playlist_counts


def remove_playlist(playlist_name):
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    cursor.execute(f'DROP TABLE IF EXISTS {playlist_name}')
    conn.commit()
    conn.close()


def add_song_to_playlist(playlist_name, url, title):
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    cursor.execute(f'INSERT INTO {playlist_name} (url, title) VALUES (?, ?)', (url, title))
    conn.commit()
    conn.close()


def get_random_songs(playlist_name):
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT url FROM {playlist_name}')
    songs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return songs


def remove_song_from_playlist(playlist_name, title):
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    cursor.execute(f'DELETE FROM {playlist_name} WHERE title = ?', (title,))
    conn.commit()
    conn.close()


def get_all_songs(playlist_name):
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT title FROM {playlist_name} ORDER BY LOWER(title)')
    songs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return songs


def search_song_in_playlist(playlist_name, keyword):
    conn = sqlite3.connect('music.db')
    cursor = conn.cursor()
    normalized_keyword = normalize_text(keyword)
    cursor.execute(f'SELECT title, url FROM {playlist_name}')
    songs = cursor.fetchall()
    for title, url in songs:
        if all(word in normalize_text(title) for word in normalized_keyword.split()):
            conn.close()
            return title, url
    conn.close()
    return None








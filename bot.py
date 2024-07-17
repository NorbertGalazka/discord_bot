import discord
from discord.ext import commands
import asyncio
import os
import yt_dlp as youtube_dl
from yt_dlp.utils import DownloadError
from dotenv import load_dotenv
import re
import shutil
import random

import owner_id
from database import init_db, add_song_to_playlist, get_random_songs, remove_song_from_playlist, get_all_songs, \
    search_song_in_playlist, create_playlist, get_all_playlists, remove_playlist



load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize the database
init_db()

# Music folder path
music_folder = 'C:\\Users\\Norbert\\PycharmProjects\\discord_bot\\music'
os.makedirs(music_folder, exist_ok=True)

bot.owner_id = owner_id.OWNER_ID

ytdl_format_options = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'outtmpl': os.path.join(music_folder, '%(extractor)s-%(id)s-%(title)s.%(ext)s'),
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, max_duration=600):
        loop = loop or asyncio.get_event_loop()
        try:
            clear_music_folder()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            if data.get('is_live', False):
                raise ValueError('Link prowadzi do transmisji na żywo, co jest niedozwolone.')
            if data.get('duration', 0) > max_duration:
                raise ValueError('Film jest zbyt długi. Maksymalna dozwolona długość to 10 minut.')
            if stream:
                filename = data['url']
            else:
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
                filename = ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except DownloadError as e:
            raise ValueError(f'Nie udało się pobrać: {str(e)}')


queue = []
last_played = []
current_playlist = 'main_playlist'  # Default playlist


@bot.event
async def on_ready():
    print(f'Bot {bot.user} jest gotowy!')


def is_valid_url(url):
    regex = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    )
    return re.match(regex, url) is not None


@bot.command(name='play', help='Odtwarza muzykę z YouTube lub playlisty')
async def play(ctx, *query):
    global current_playlist
    query = ' '.join(query)
    if is_valid_url(query):
        await add_song(ctx, current_playlist, query)
    else:
        song = search_song_in_playlist(current_playlist, query)
        if song:
            title, url = song
            await add_song(ctx, current_playlist, url)
        else:
            await ctx.send(f'Nie znaleziono piosenki dla zapytania: {query}')


async def play_next(ctx):
    global current_playlist
    if queue:
        url = queue.pop(0)
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop)
            ctx.voice_client.play(player, after=lambda e: bot.loop.create_task(play_next(ctx)))
            await ctx.send(f'Odgrywam: {player.title}')
        except ValueError as e:
            await ctx.send(f'Wystąpił błąd podczas odtwarzania piosenki: {e}')
            await play_next(ctx)
    else:
        random_songs = get_random_songs(current_playlist)
        if random_songs:
            random_url = await get_random_song(random_songs)
            try:
                player = await YTDLSource.from_url(random_url, loop=bot.loop)
                ctx.voice_client.play(player, after=lambda e: bot.loop.create_task(play_next(ctx)))
                await ctx.send(f'Odgrywam losową piosenkę: {player.title}')
            except ValueError as e:
                await ctx.send(f'Wystąpił błąd podczas odtwarzania losowej piosenki: {e}')
                await play_next(ctx)


@bot.command(name='stop', help='Zatrzymuje odtwarzanie muzyki')
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
    queue.clear()
    await voice_client.disconnect()
    clear_music_folder()
    await ctx.send('Muzyka zatrzymana i folder opróżniony.')


@bot.command(name='skip', help='Pomija aktualnie odtwarzany utwór')
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send('Pomijanie utworu...')


async def add_song(ctx, playlist_name, url):
    async with ctx.typing():
        if ctx.voice_client is None:
            if ctx.author.voice:
                try:
                    channel = ctx.author.voice.channel
                    await channel.connect()
                except asyncio.TimeoutError:
                    await ctx.send('Timeout podczas łączenia z kanałem głosowym. Spróbuj ponownie.')
                    return
                except discord.errors.ClientException as e:
                    await ctx.send(f'Błąd podczas łączenia z kanałem głosowym: {e}')
                    return
            else:
                await ctx.send("Musisz być na kanale głosowym, aby użyć tej komendy.")
                return

        queue.append(url)
        await ctx.send(f'Dodano do kolejki: {url}')

        if not ctx.voice_client.is_playing():
            await play_next(ctx)


def clear_music_folder():
    for filename in os.listdir(music_folder):
        file_path = os.path.join(music_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Błąd podczas usuwania pliku {file_path}: {e}')


async def get_random_song(songs):
    global last_played
    random.shuffle(songs)

    for song_url in songs:
        if song_url not in last_played:
            try:
                data = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info(song_url, download=False))
                duration = data.get('duration', 0)

                if duration > 600:
                    continue

                last_played.append(song_url)
                if len(last_played) > 5:
                    last_played.pop(0)
                return song_url
            except Exception as e:
                print(f'Błąd podczas pobierania informacji o losowej piosence: {e}')

    return random.choice(songs) if songs else None


@bot.command(name='add_song', help='Dodaje piosenkę do playlisty')
async def add_song_command(ctx, playlist_name, url):
    if not is_valid_url(url):
        await ctx.send('Proszę podać prawidłowy link do YouTube.')
        return
    data = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    title = data.get('title', 'Nieznany tytuł')
    add_song_to_playlist(playlist_name, url, title)
    await ctx.send(f'Dodano do playlisty {playlist_name}: {url}')


@bot.command(name='remove_song', help='Usuwa piosenkę z playlisty')
async def remove_song_command(ctx, playlist_name, *, title):
    song = search_song_in_playlist(playlist_name, title)
    if song:
        remove_song_from_playlist(playlist_name, title)
        await ctx.send(f'Usunięto z playlisty {playlist_name}: {title}')
    else:
        await ctx.send(f'Nie znaleziono piosenki o tytule: {title}')


# Komendy do odtwarzania z nazwanych piosenek
songs = {
    'norbi': 'https://www.youtube.com/watch?v=u1I9ITfzqFs',
    'przemek': 'https://www.youtube.com/watch?v=PSg7Zs5vlBQ',
    'wirus': 'https://www.youtube.com/watch?v=M9XbJxKSTlk',
    'filip': 'https://www.youtube.com/watch?v=_UpJBdXrYjo',
    'chwaster': 'https://www.youtube.com/watch?v=SzzERnsKMFg',
    'stasiak': 'https://www.youtube.com/watch?v=EssaGhC29zo',
    'gamala': 'https://youtu.be/bpOSxM0rNPM?si=QKxKQ_2R4R3yd4iO',
    'gralak': 'https://www.youtube.com/watch?v=5Jp9VADgkUk',
    'panek': 'https://www.youtube.com/watch?v=z6IuSQ5Tn-o',

}


async def create_song_command(ctx, playlist_name, song_name):
    url = songs.get(song_name)
    if url:
        await add_song(ctx, playlist_name, url)
    else:
        await ctx.send(f'Nie znaleziono piosenki o nazwie "{song_name}".')


for command in songs.keys():
    async def song_command(ctx, command=command):
        await create_song_command(ctx, 'main_playlist', command)

    bot.command(name=command, help=f'Dodaje do kolejki piosenkę "{command}"')(song_command)


# Usuń istniejącą komendę 'help'
bot.remove_command('help')

@bot.command(name='help', help='Wyświetla wszystkie dostępne komendy')
async def help_command(ctx):
    commands_list = [
        f'**!add_song <playlista> <link>**: Dodaje piosenkę do playlisty',
        f'**!remove_song <playlista> <tytuł>**: Usuwa piosenkę z playlisty',
        f'**!show_playlist <playlista>**: Wyświetla wszystkie piosenki w playliście',
        f'**!show_playlists**: Wyświetla nazwy wszystkich playlist i liczby zawartych w nich utworów',
        f'**!play <link lub zapytanie>**: Odtwarza muzykę z YouTube lub playlisty',
        f'**!stop**: Zatrzymuje odtwarzanie muzyki',
        f'**!skip**: Pomija aktualnie odtwarzany utwór',
        f'**!add_playlist <playlista>**: Dodaje nową playlistę do bazy danych',
        f'**!playlist <playlista>**: Ustawia aktualną playlistę'
    ]

    # Dodajemy komendy do odtwarzania z nazwanych piosenek
    for command in songs.keys():
        commands_list.append(f'**!{command}**: Dodaje do kolejki piosenkę "{command}"')

    help_message = "Oto dostępne komendy:\n" + "\n".join(commands_list)
    await ctx.send(help_message)


@bot.command(name='commands', help='Wyświetla wszystkie dostępne komendy (alias dla komendy help)')
async def commands_command(ctx):
    await help_command(ctx)


@bot.command(name='show_playlist', help='Wyświetla wszystkie piosenki w playliście')
async def show_playlist(ctx, playlist_name=None):
    global current_playlist

    if not playlist_name:
        playlist_name = current_playlist

    songs = get_all_songs(playlist_name)
    if not songs:
        await ctx.send(f'Playlista "{playlist_name}" jest pusta.')
        return

    max_length = 2000
    current_length = 0
    message_parts = []
    current_message = f'PLAYLISTA "{playlist_name.upper()}"\n\n'

    for idx, title in enumerate(songs):
        song_entry = f"{idx + 1}. {title}\n"
        entry_length = len(song_entry)

        if current_length + entry_length > max_length:
            message_parts.append(current_message)
            current_message = song_entry
            current_length = entry_length
        else:
            current_message += song_entry
            current_length += entry_length

    # Add the last message
    if current_message:
        message_parts.append(current_message)

    for part in message_parts:
        await ctx.send(part)


@bot.command(name='add_playlist', help='Dodaje nową playlistę do bazy danych')
async def add_playlist_command(ctx, playlist_name):
    create_playlist(playlist_name)
    await ctx.send(f'Dodano nową playlistę: {playlist_name}')


@bot.command(name='playlist', help='Ustawia aktualną playlistę')
async def set_playlist_command(ctx, playlist_name):
    global current_playlist
    current_playlist = playlist_name
    await ctx.send(f'Ustawiono aktualną playlistę na: {playlist_name}')


@bot.command(name='show_playlists', help='Wyświetla nazwy wszystkich playlist i liczby zawartych w nich utworów')
async def show_playlists(ctx):
    playlists = get_all_playlists()
    if not playlists:
        await ctx.send('Nie znaleziono żadnych playlist.')
        return

    message = "Oto dostępne playlisty:\n"
    for playlist_name, song_count in playlists:
        if song_count == 1:
            word = 'song'
        else:
            word = 'songs'
        message += f'{playlist_name} - {song_count} {word} \n'

    await ctx.send(message)


@bot.command(name='secret_remove_playlist', help='(Ukryta komenda) Usuwa podaną playlistę z bazy danych')
async def secret_remove_playlist(ctx, playlist_name):
    # Sprawdzamy, czy użytkownik jest właścicielem bota lub ma odpowiednie uprawnienia
    if ctx.author.id == bot.owner_id:
        try:
            remove_playlist(playlist_name)
            await ctx.send(f'Playlista "{playlist_name}" została usunięta.')
        except Exception as e:
            await ctx.send(f'Wystąpił błąd podczas usuwania playlisty "{playlist_name}": {e}')
    else:
        await ctx.send("Nie masz uprawnień do użycia tej komendy.")



# Start the bot
bot.run(DISCORD_BOT_TOKEN)



































import discord
from discord.ext import commands
import asyncio
import os
import yt_dlp as youtube_dl
from yt_dlp.utils import DownloadError
from dotenv import load_dotenv
import re
import shutil

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Ścieżka do folderu music
music_folder = 'C:\\Users\\Norbert\\PycharmProjects\\discord_bot\\music'

# Upewnij się, że folder istnieje
if not os.path.exists(music_folder):
    os.makedirs(music_folder)

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
            # Opróżnij folder przed pobraniem nowego pliku
            clear_music_folder()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
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


@bot.event
async def on_ready():
    print(f'Bot {bot.user} jest gotowy!')


def is_valid_url(url):
    regex = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    )
    return re.match(regex, url) is not None


@bot.command(name='play', help='Odtwarza muzykę z YouTube')
async def play(ctx, url):
    if not is_valid_url(url):
        await ctx.send('Proszę podać prawidłowy link do YouTube.')
        return
    await add_song(ctx, url)


async def play_next(ctx):
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
        await ctx.voice_client.disconnect()


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


async def add_song(ctx, url):
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


# Dodawanie określonych piosenek do kolejki za pomocą wspólnej funkcji add_song
songs = {
    'norbi': 'https://www.youtube.com/watch?v=u1I9ITfzqFs',
    'panek': 'https://www.youtube.com/watch?v=GAZU62dMhkg',
    'wirus': 'https://www.youtube.com/watch?v=M9XbJxKSTlk',
    'filip': 'https://www.youtube.com/watch?v=_UpJBdXrYjo',
    'chwaster': 'https://www.youtube.com/watch?v=SzzERnsKMFg',
    'stasiak': 'https://www.youtube.com/watch?v=EssaGhC29zo',
    'przemek': 'https://www.youtube.com/watch?v=PSg7Zs5vlBQ',
    'gamala': 'https://youtu.be/bpOSxM0rNPM?si=QKxKQ_2R4R3yd4iO',
    'gralak': 'https://www.youtube.com/watch?v=5Jp9VADgkUk'  # Nowa piosenka dodana do słownika
}


# Tworzenie asynchronicznych funkcji dla każdej piosenki
async def create_song_command(ctx, song_name):
    url = songs.get(song_name)
    if url:
        await add_song(ctx, url)
    else:
        await ctx.send(f'Nie znaleziono piosenki o nazwie "{song_name}".')


for command in songs.keys():
    async def song_command(ctx, command=command):
        await create_song_command(ctx, command)


    bot.command(name=command, help=f'Dodaje do kolejki piosenkę "{command}"')(song_command)


@bot.command(name='change', help='Zmienia link przypisany do komendy')
async def change(ctx, command, new_url):
    if command not in songs:
        await ctx.send(f'Nie ma komendy o nazwie {command}.')
        return

    if not is_valid_url(new_url):
        await ctx.send('Proszę podać prawidłowy link do YouTube.')
        return

    songs[command] = new_url
    await ctx.send(f'Link przypisany do komendy "{command}" został zmieniony na {new_url}.')


# Dodanie komend do zmiany linków
for command in songs.keys():
    async def change_command(ctx, new_url, command=command):
        await change(ctx, command, new_url)


    bot.command(name=f'{command}_change', help=f'Zmienia link przypisany do komendy "{command}"')(change_command)

# Uruchomienie bota
bot.run(DISCORD_BOT_TOKEN)





















